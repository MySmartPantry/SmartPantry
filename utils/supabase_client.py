import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_SUPABASE_URL = os.getenv("SUPABASE_URL")
_SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")


@st.cache_resource
def get_client() -> Client:
    if not _SUPABASE_URL or not _SUPABASE_KEY:
        st.error("Missing SUPABASE_URL or SUPABASE_ANON_KEY. Check your .env file.")
        st.stop()
    return create_client(_SUPABASE_URL, _SUPABASE_KEY)


def get_session():
    return st.session_state.get("session")


def sign_in(email: str, password: str):
    try:
        sb = get_client()
        result = sb.auth.sign_in_with_password({"email": email, "password": password})
        return result.session
    except Exception as e:
        st.error(f"Sign-in failed: {e}")
        return None


def sign_up(email: str, password: str, household_name: str):
    try:
        sb = get_client()
        result = sb.auth.sign_up({"email": email, "password": password})
        session = result.session
        if session and household_name:
            # Create a household for this new user
            _create_household(household_name, session.user.id, sb)
        return session
    except Exception as e:
        st.error(f"Sign-up failed: {e}")
        return None


def sign_out():
    try:
        get_client().auth.sign_out()
    except Exception:
        pass


def _create_household(name: str, user_id: str, sb: Client):
    result = sb.table("households").insert({"name": name}).execute()
    if result.data:
        hh_id = result.data[0]["id"]
        sb.table("household_members").insert({
            "user_id": user_id,
            "household_id": hh_id,
            "role": "owner",
        }).execute()


def get_household() -> dict | None:
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
