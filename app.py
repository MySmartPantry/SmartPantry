import streamlit as st
from utils.supabase_client import get_client, get_session, sign_in, sign_up, sign_out

st.set_page_config(
    page_title="SmartPantry",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session bootstrap ─────────────────────────────────────────
# Restore session from st.session_state if available
if "session" not in st.session_state:
    st.session_state.session = None

session = st.session_state.session

# ── Logged-in sidebar ─────────────────────────────────────────
if session:
    email = session.user.email
    st.sidebar.markdown(f"**{email}**")
    if st.sidebar.button("Sign out"):
        sign_out()
        st.session_state.session = None
        st.rerun()

    # Show household info if available
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
            email = st.text_input("Email", key="su_email")
            password = st.text_input("Password (min 6 characters)", type="password", key="su_pw")
            household_name = st.text_input("Household name (e.g. 'The Parisi House')")
            submitted = st.form_submit_button("Create Account")
        if submitted:
            result = sign_up(email, password, household_name)
            if result:
                st.session_state.session = result
                st.rerun()

else:
    # Logged in — load household into session state if not already loaded
    if "household" not in st.session_state:
        from utils.supabase_client import get_household
        st.session_state.household = get_household()

    st.title("🍎 SmartPantry")
    st.markdown("Use the sidebar to navigate to **Pantry**, **Recipes**, **Meal Plan**, or **Shopping**.")

    if not st.session_state.get("household"):
        st.warning("You're not in a household yet. Go to the **Pantry** page to create or join one.")
    else:
        h = st.session_state.household
        st.success(f"Welcome to **{h['name']}**! Use the sidebar to get started.")
