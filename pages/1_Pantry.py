import streamlit as st
from utils.supabase_client import get_client, get_session, get_household, join_household, persist_auth
from utils.ingredient_matcher import names_match, get_substitutions

st.set_page_config(page_title="Pantry | SmartPantry", page_icon="📦", layout="wide")

# ── Auth check ────────────────────────────────────────────────
session = get_session()
if not session:
    st.switch_page("app.py")

persist_auth()  # Keep tokens fresh in localStorage across browser refreshes

# ── Household check ───────────────────────────────────────────
if "household" not in st.session_state:
    st.session_state.household = get_household()

household = st.session_state.household

if not household:
    st.title("📦 Set Up Your Household")
    tab_create, tab_join = st.tabs(["Create a Household", "Join with Invite Code"])

    with tab_create:
        with st.form("create_hh"):
            name = st.text_input("Household name (e.g. 'The Parisi House')")
            if st.form_submit_button("Create"):
                if name:
                    from utils.supabase_client import _create_household, get_client
                    _create_household(name, session.user.id, get_client())
                    st.session_state.household = get_household()
                    st.rerun()

    with tab_join:
        with st.form("join_hh"):
            code = st.text_input("Invite code")
            if st.form_submit_button("Join"):
                if join_household(code):
                    st.session_state.household = get_household()
                    st.rerun()
    st.stop()

sb = get_client()
hh_id = household["id"]

# ── Page ──────────────────────────────────────────────────────
st.title("📦 My Pantry")
st.caption(f"Household: **{household['name']}** · Invite code: `{household['invite_code']}`")

# Flash message from previous add (shown after form resets)
if "_pantry_msg" in st.session_state:
    msg, kind = st.session_state.pop("_pantry_msg")
    (st.success if kind == "success" else st.info)(msg)

# ── Add item form ─────────────────────────────────────────────
if "add_item_n" not in st.session_state:
    st.session_state.add_item_n = 0

with st.expander("➕ Add an item to your pantry", expanded=False):
    with st.form(f"add_item_{st.session_state.add_item_n}"):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            specific_name = st.text_input("Item name", placeholder="e.g. Goat Milk, Penne, EVOO")
        with col2:
            quantity = st.number_input("Qty", min_value=0.0, value=1.0, step=0.5)
        with col3:
            unit = st.text_input("Unit", value="count", placeholder="count, cups, oz, lbs…")

        submitted = st.form_submit_button("Add to Pantry")

    if submitted and specific_name:
        all_items = (
            sb.table("pantry_items")
            .select("id, specific_name, quantity")
            .eq("household_id", hh_id)
            .execute()
        ).data
        subs = get_substitutions()
        existing = next(
            (i for i in all_items if names_match(specific_name, i["specific_name"], subs)),
            None,
        )

        if existing:
            new_qty = (existing["quantity"] or 0) + quantity
            sb.table("pantry_items").update({
                "quantity": new_qty,
                "specific_name": specific_name,
            }).eq("id", existing["id"]).execute()
            st.session_state["_pantry_msg"] = (f"Updated **{specific_name}** — now {new_qty} {unit} on hand.", "success")
        else:
            sb.table("pantry_items").insert({
                "household_id": hh_id,
                "specific_name": specific_name,
                "quantity": quantity,
                "unit": unit,
            }).execute()
            st.session_state["_pantry_msg"] = (f"Added **{specific_name}** to pantry.", "success")

        st.session_state.add_item_n += 1
        st.rerun()

st.markdown("---")

# ── Substitution pair manager ─────────────────────────────────
if "add_sub_n" not in st.session_state:
    st.session_state.add_sub_n = 0

with st.expander("🔄 Substitutions — treat these ingredients as interchangeable", expanded=False):
    subs = get_substitutions()
    hh_subs = [s for s in subs if s.get("household_id") == hh_id]

    with st.form(f"add_sub_{st.session_state.add_sub_n}"):
        col_a, col_b = st.columns(2)
        with col_a:
            sub_a = st.text_input("Ingredient A", placeholder="e.g. EVOO")
        with col_b:
            sub_b = st.text_input("Ingredient B", placeholder="e.g. Olive Oil")
        if st.form_submit_button("Add Pair"):
            if sub_a and sub_b:
                try:
                    sb.table("ingredient_substitutions").insert({
                        "household_id": hh_id,
                        "ingredient_a": sub_a.strip(),
                        "ingredient_b": sub_b.strip(),
                    }).execute()
                    get_substitutions.clear()
                    st.session_state.add_sub_n += 1
                    st.rerun()
                except Exception:
                    st.info("That pair already exists.")

    if hh_subs:
        for pair in hh_subs:
            c1, c2 = st.columns([5, 1])
            with c1:
                st.write(f"{pair['ingredient_a']} ↔ {pair['ingredient_b']}")
            with c2:
                if st.button("🗑️", key=f"del_sub_{pair['id']}"):
                    sb.table("ingredient_substitutions").delete().eq("id", pair["id"]).execute()
                    get_substitutions.clear()
                    st.rerun()
    else:
        st.caption("No substitutions yet. Add pairs above.")

st.markdown("---")

# ── Current pantry inventory ──────────────────────────────────
st.subheader("Current Inventory")

items = (
    sb.table("pantry_items")
    .select("id, specific_name, quantity, unit")
    .eq("household_id", hh_id)
    .order("specific_name")
    .execute()
).data

if not items:
    st.info("Your pantry is empty. Add items above.")
else:
    for item in items:
        col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
        with col1:
            st.write(item["specific_name"])
        with col2:
            st.write(f"{item['quantity']} {item['unit']}")
        with col3:
            new_qty = st.number_input(
                "Adj",
                min_value=0.0,
                value=float(item["quantity"]),
                step=0.5,
                key=f"qty_{item['id']}",
                label_visibility="collapsed",
            )
            if new_qty != item["quantity"]:
                sb.table("pantry_items").update({"quantity": new_qty}).eq("id", item["id"]).execute()
                st.rerun()
        with col4:
            if st.button("🗑️", key=f"del_{item['id']}"):
                sb.table("pantry_items").delete().eq("id", item["id"]).execute()
                st.rerun()
