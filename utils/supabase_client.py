import os
import json
import streamlit as st
import streamlit.components.v1 as _components
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_SUPABASE_URL = os.getenv("SUPABASE_URL")
_SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")


@st.cache_resource
def _base_client() -> Client:
    """Shared anonymous Supabase client. Never used directly — always go through get_client()."""
    if not _SUPABASE_URL or not _SUPABASE_KEY:
        st.error("Missing SUPABASE_URL or SUPABASE_ANON_KEY. Check your .env file.")
        st.stop()
    return create_client(_SUPABASE_URL, _SUPABASE_KEY)


class _AuthClient:
    """Wraps a Supabase client and injects the user's JWT into every table() call.

    supabase-py 2.x does not reliably propagate auth state to PostgREST when
    set on the shared client object. Chaining .auth(token) per request is the
    only approach that works consistently (per supabase-py issue #272/#915).
    """

    def __init__(self, sb, token):
        self._sb = sb
        self._token = token

    def table(self, name):
        builder = self._sb.table(name)
        if self._token:
            # builder.auth is a BasicAuth field (None by default), NOT a method.
            # Inject the user JWT directly into the builder's request headers.
            builder.headers["Authorization"] = f"Bearer {self._token}"
        return builder

    def __getattr__(self, name):
        # Proxy everything else (auth, storage, functions, etc.) to the real client
        return getattr(self._sb, name)


def get_client():
    """Returns a Supabase client wrapper that automatically injects the current
    user's JWT on every table() call so RLS policies work correctly."""
    sb = _base_client()
    session = st.session_state.get("session")
    token = session.access_token if session else None
    return _AuthClient(sb, token)


def get_session():
    return st.session_state.get("session")


def sign_in(email: str, password: str):
    try:
        sb = _base_client()
        result = sb.auth.sign_in_with_password({"email": email, "password": password})
        return result.session
    except Exception as e:
        st.error(f"Sign-in failed: {e}")
        return None


def sign_up(email: str, password: str, household_name: str):
    """
    Creates a new account. With email confirmation enabled, Supabase sends a
    confirmation email and result.session is None until the user confirms.
    We store the household name temporarily so we can create it after confirmation.
    Returns True on success, False on failure.
    """
    try:
        sb = _base_client()
        result = sb.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"pending_household_name": household_name}},
        })
        if result.user:
            st.session_state["pending_household_name"] = household_name
            return True
        return False
    except Exception as e:
        st.error(f"Sign-up failed: {e}")
        return False


def sign_out():
    try:
        _base_client().auth.sign_out()
    except Exception:
        pass


def _create_household(name: str, user_id: str, sb):
    """Create a household via direct REST calls.

    Uses requests instead of supabase-py to reliably send the user JWT.
    The table requires GRANT + RLS (authenticated role), both set in migrations.
    """
    import requests as _req

    session = st.session_state.get("session")
    if not session:
        st.error("Cannot create household: no active session.")
        return

    headers = {
        "apikey": _SUPABASE_KEY,
        "Authorization": f"Bearer {session.access_token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    resp = _req.post(
        f"{_SUPABASE_URL}/rest/v1/households",
        json={"name": name},
        headers=headers,
    )
    if not resp.ok:
        st.error(f"Could not create household: {resp.status_code} {resp.text}")
        return

    hh_id = resp.json()[0]["id"]

    resp2 = _req.post(
        f"{_SUPABASE_URL}/rest/v1/household_members",
        json={"user_id": user_id, "household_id": hh_id, "role": "owner"},
        headers=headers,
    )
    if not resp2.ok:
        st.error(f"Could not add household member: {resp2.status_code} {resp2.text}")


def get_household():
    """Returns the current user's household, or None if not in one."""
    session = get_session()
    if not session:
        return None
    try:
        sb = get_client()
        result = (
            sb.table("household_members")
            .select("household_id, role, households(id, name, invite_code)")
            .eq("user_id", session.user.id)
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            hh = row["households"]
            hh["role"] = row["role"]
            return hh
        return None
    except Exception as e:
        st.error(f"Could not load household: {e}")
        return None


def join_household(invite_code: str) -> bool:
    """Adds the current user to a household via invite code."""
    session = get_session()
    if not session:
        return False
    try:
        sb = get_client()
        result = sb.table("households").select("id").eq("invite_code", invite_code).limit(1).execute()
        if not result.data:
            st.error("Invalid invite code.")
            return False
        hh_id = result.data[0]["id"]
        sb.table("household_members").insert({
            "user_id": session.user.id,
            "household_id": hh_id,
            "role": "member",
        }).execute()
        return True
    except Exception as e:
        st.error(f"Could not join household: {e}")
        return False


# ── Session persistence via localStorage ──────────────────────

_LS_KEY = "sp_session"


def persist_auth():
    """
    Saves the current session's tokens to localStorage so the session survives
    browser refreshes and Streamlit restarts. Call this on every authenticated page.
    """
    session = get_session()
    if not session:
        return
    data = json.dumps({"at": session.access_token, "rt": session.refresh_token})
    _components.html(
        f"<script>try{{window.parent.localStorage.setItem({json.dumps(_LS_KEY)},{json.dumps(data)})}}catch(e){{}}</script>",
        height=0,
    )


def clear_persisted_auth():
    """Removes saved tokens from localStorage. Call on sign-out."""
    _components.html(
        f"<script>try{{window.parent.localStorage.removeItem({json.dumps(_LS_KEY)})}}catch(e){{}}</script>",
        height=0,
    )
