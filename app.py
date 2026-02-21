import streamlit as st
import streamlit.components.v1 as components
from utils.supabase_client import get_client, get_session, sign_in, sign_up, sign_out, clear_persisted_auth

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
            var newUrl = window.location.pathname
                + '?access_token=' + encodeURIComponent(access_token)
                + '&refresh_token=' + encodeURIComponent(refresh_token || '');
            window.location.replace(newUrl);
        }
    }
})();
</script>
""", height=0)

params = st.query_params

# ── Restore session from localStorage (browser refresh / server restart) ──
# Only inject the restore script when there's no session and no tokens already
# coming in via URL (email confirmation / PKCE flows take priority).
if not st.session_state.session and "access_token" not in params and "code" not in params:
    components.html("""
<script>
(function() {
    try {
        var d = JSON.parse(window.parent.localStorage.getItem('sp_session') || 'null');
        if (d && d.at && d.rt) {
            window.parent.location.replace(
                window.parent.location.pathname
                + '?access_token=' + encodeURIComponent(d.at)
                + '&refresh_token=' + encodeURIComponent(d.rt)
            );
        }
    } catch(e) {}
})();
</script>
""", height=0)

# Handle PKCE flow (code param)
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

# Handle access_token param (email confirmation hash→param conversion OR localStorage restore)
if "access_token" in params and not st.session_state.session:
    try:
        sb = get_client()
        result = sb.auth.set_session(params["access_token"], params.get("refresh_token", ""))
        if result.session:
            st.session_state.session = result.session
            st.query_params.clear()
            st.rerun()
    except Exception as e:
        # Token may be expired — clear localStorage so we don't loop
        clear_persisted_auth()
        st.query_params.clear()

session = st.session_state.session

# ── Already logged in → go to Dashboard ──────────────────────
if session:
    st.switch_page("pages/0_Dashboard.py")

# ── Auth forms ────────────────────────────────────────────────
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
