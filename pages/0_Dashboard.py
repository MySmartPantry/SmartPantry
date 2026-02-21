import streamlit as st
from utils.supabase_client import get_client, get_session, get_household, sign_out, persist_auth, clear_persisted_auth

st.set_page_config(page_title="Dashboard | SmartPantry", page_icon="🍎", layout="wide")

# ── Auth check ────────────────────────────────────────────────
session = get_session()
if not session:
    st.switch_page("app.py")

persist_auth()  # Keep tokens fresh in localStorage across browser refreshes

# ── Household bootstrap ───────────────────────────────────────
if "household" not in st.session_state:
    st.session_state.household = get_household()

    if not st.session_state.household:
        pending_name = (
            session.user.user_metadata.get("pending_household_name")
            or st.session_state.get("pending_household_name")
        )
        if pending_name:
            from utils.supabase_client import _create_household, get_client as _gc
            _create_household(pending_name, session.user.id, _gc())
            st.session_state.household = get_household()

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.markdown(f"**{session.user.email}**")
if st.sidebar.button("Sign out"):
    clear_persisted_auth()
    sign_out()
    st.session_state.session = None
    st.session_state.pop("household", None)
    st.rerun()

household = st.session_state.get("household")
if household:
    st.sidebar.markdown(f"Household: **{household['name']}**")
    st.sidebar.caption(f"Invite code: `{household.get('invite_code', '')}`")

# ── Dashboard ─────────────────────────────────────────────────
st.title("🍎 SmartPantry")

if not household:
    st.warning("You're not in a household yet. Go to the **Pantry** page to create or join one.")
    st.stop()

hh = household
st.subheader(f"Welcome to {hh['name']}")

col_invite, col_spacer = st.columns([2, 3])
with col_invite:
    st.info(f"Invite code: **`{hh.get('invite_code', '')}`** — share this to add household members")

st.markdown("---")

# ── Summary cards ─────────────────────────────────────────────
sb = get_client()
pantry_result = (
    sb.table("pantry_items")
    .select("id", count="exact")
    .eq("household_id", hh["id"])
    .execute()
)
pantry_count = pantry_result.count or 0

card1, card2, card3 = st.columns(3)
with card1:
    st.metric("Pantry Items", pantry_count)
with card2:
    st.metric("Saved Recipes", "—")
with card3:
    st.metric("This Week's Meals", "—")

st.markdown("---")

col_meals, col_shopping = st.columns(2)
with col_meals:
    st.subheader("Upcoming Meals")
    st.caption("Meal planning coming soon.")

with col_shopping:
    st.subheader("Shopping List")
    st.caption("Shopping list coming soon.")
