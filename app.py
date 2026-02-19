import streamlit as st
import streamlit.components.v1 as components
from utils.supabase_client import get_client, get_session, sign_in, sign_up, sign_out

st.set_page_config(
    page_title="SmartPantry",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session bootstrap ─────────────────────────────────────────
if "session" not in st.session_state:
    st.session_state.session = None

# ── Handle email confirmation callback ────────────────────────
# Supabase sends tokens in the URL hash (#access_token=...) which browsers
# don't forward to the server. This JS snippet reads the hash and rewrites
# the URL as query params so Python can see them on the next render.
components.html("""
<script>
(function() {
    var hash = window.location.hash;
    if (hash && hash.includes('access_token')) {
        var params = new URLSearchParams(hash.substring(1));
        var access_token = params.get('access_token');
        var refresh_token = params.get('refresh_token');
        if (access_token) {
            // Rewrite the URL with query params instead of hash so Python can read them
            var newUrl = window.location.pathname
                + '?access_token=' + encodeURIComponent(access_token)
                + '&refresh_token=' + encodeURIComponent(refresh_token || '');
            window.location.replace(newUrl);
        }
    }
})();
</script>
""", height=0)

# Handle PKCE flow (code param) — future signups after the redirect URL is fixed
params = st.query_params
if "code" in params and not st.session_state.session:
    try:
        sb = get_client()
        result = sb.auth.exchange_code_for_session({"auth_code": params["code"]})
        if result.session:
            st.session_state.session = result.session
            st.query_params.clear()
            st.rerun()
    except Exception as e:
        st.error(f"Could not confirm account: {e}")

# Handle implicit flow (access_token in hash, now converted to query param above)
if "access_token" in params and not st.session_state.session:
    try:
        sb = get_client()
        result = sb.auth.set_session(params["access_token"], params.get("refresh_token", ""))
        if result.session:
            st.session_state.session = result.session
            st.query_params.clear()
            st.rerun()
    except Exception as e:
        st.error(f"Could not confirm account: {e}")

session = st.session_state.session

# ── Logged-in sidebar ─────────────────────────────────────────
if session:
    email = session.user.email
    st.sidebar.markdown(f"**{email}**")
    if st.sidebar.button("Sign out"):
        sign_out()
        st.session_state.session = None
        st.rerun()

    if "household" in st.session_state and st.session_state.household:
        st.sidebar.markdown(f"Household: **{st.session_state.household['name']}**")
        invite = st.session_state.household.get("invite_code", "")
        st.sidebar.caption(f"Invite code: `{invite}`")

    st.sidebar.markdown("---")
    st.sidebar.markdown("Navigate using the pages above.")

# ── Auth gate ─────────────────────────────────────────────────
if not session:
    st.title("🍎 SmartPantry")
    st.markdown("Plan meals, manage your pantry, and order groceries — shared across your household.")
    st.markdown("---")

    tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In")
        if submitted:
            result = sign_in(email, password)
            if result:
                st.session_state.session = result
                st.rerun()

    with tab_signup:
        st.markdown("Create a new account, then set up or join a household from the Pantry page.")
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="su_email")
            new_password = st.text_input("Password (min 6 characters)", type="password", key="su_pw")
            household_name = st.text_input("Household name (e.g. 'The Parisi House')")
            submitted = st.form_submit_button("Create Account")

        if submitted:
            if not new_email or not new_password:
                st.error("Please enter both an email and password.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                success = sign_up(new_email, new_password, household_name)
                if success:
                    st.success(
                        f"Account created for **{new_email}**! "
                        "Check your email for a confirmation link, then come back here and sign in."
                    )
                    st.info("Tip: If you don't see the email, check your spam folder.")

else:
    if "household" not in st.session_state:
        from utils.supabase_client import get_household, _create_household, get_client as _gc
        st.session_state.household = get_household()

        # If no household yet, check if one was requested at signup time
        if not st.session_state.household:
            pending_name = (
                session.user.user_metadata.get("pending_household_name")
                or st.session_state.get("pending_household_name")
            )
            if pending_name:
                _create_household(pending_name, session.user.id, _gc())
                st.session_state.household = get_household()

    st.title("🍎 SmartPantry")
    st.markdown("Use the sidebar to navigate to **Pantry**, **Recipes**, **Meal Plan**, or **Shopping**.")

    if not st.session_state.get("household"):
        st.warning("You're not in a household yet. Go to the **Pantry** page to create or join one.")
    else:
        h = st.session_state.household
        st.success(f"Welcome to **{h['name']}**! Use the sidebar to get started.")
