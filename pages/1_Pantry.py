import streamlit as st
from utils.supabase_client import get_client, get_session, get_household, join_household
from utils.ingredient_matcher import find_canonical_id, get_all_types

st.set_page_config(page_title="Pantry | SmartPantry", page_icon="📦", layout="wide")

# ── Auth check ────────────────────────────────────────────────
session = get_session()
if not session:
    st.warning("Please sign in from the Home page.")
    st.stop()

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

# ── Add item form ─────────────────────────────────────────────
with st.expander("➕ Add an item to your pantry", expanded=False):
    with st.form("add_item"):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            specific_name = st.text_input("Item name", placeholder="e.g. Goat Milk, Penne, EVOO")
        with col2:
            quantity = st.number_input("Qty", min_value=0.0, value=1.0, step=0.5)
        with col3:
            unit = st.selectbox("Unit", ["count", "cups", "oz", "lbs", "tbsp", "tsp", "liters", "ml", "grams", "kg", "bunch", "clove", "slice"])

        submitted = st.form_submit_button("Add to Pantry")

    if submitted and specific_name:
        type_id = find_canonical_id(specific_name)
        if type_id:
            # Check if a pantry item of this type already exists; update quantity instead of duplicating
            existing = (
                sb.table("pantry_items")
                .select("id, quantity")
                .eq("household_id", hh_id)
                .eq("ingredient_type_id", type_id)
                .limit(1)
                .execute()
            ).data

            if existing:
                new_qty = existing[0]["quantity"] + quantity
                sb.table("pantry_items").update({"quantity": new_qty, "specific_name": specific_name, "updated_at": "now()"}).eq("id", existing[0]["id"]).execute()
                st.success(f"Updated **{specific_name}** — now {new_qty} {unit} on hand.")
            else:
                sb.table("pantry_items").insert({
                    "household_id": hh_id,
                    "ingredient_type_id": type_id,
                    "specific_name": specific_name,
                    "quantity": quantity,
                    "unit": unit,
                }).execute()
                st.success(f"Added **{specific_name}** to pantry.")
        else:
            st.warning(
                f"**'{specific_name}'** wasn't recognized as a known ingredient. "
                "It was added with no canonical type, so it won't match recipes automatically. "
                "Try a simpler name (e.g. 'milk' instead of 'cold pressed A2 milk')."
            )
            sb.table("pantry_items").insert({
                "household_id": hh_id,
                "ingredient_type_id": None,
                "specific_name": specific_name,
                "quantity": quantity,
                "unit": unit,
            }).execute()
        st.rerun()

st.markdown("---")

# ── Alias manager ─────────────────────────────────────────────
with st.expander("🔗 Add a custom substitution (e.g. 'A2 Milk' = Milk)", expanded=False):
    all_types = get_all_types()
    type_options = sorted(all_types.keys())
    with st.form("add_alias"):
        alias_name = st.text_input("Your specific ingredient name", placeholder="e.g. A2 Milk")
        canonical = st.selectbox("It counts as...", type_options)
        if st.form_submit_button("Save substitution"):
            if alias_name and canonical:
                type_id = all_types[canonical]["id"]
                try:
                    sb.table("ingredient_aliases").insert({"alias": alias_name.strip(), "ingredient_type_id": type_id}).execute()
                    get_all_types.clear()
                    st.success(f"'{alias_name}' will now be recognized as **{canonical.title()}**.")
                except Exception:
                    st.info(f"'{alias_name}' is already mapped.")

st.markdown("---")

# ── Current pantry inventory ──────────────────────────────────
st.subheader("Current Inventory")

items = (
    sb.table("pantry_items")
    .select("id, specific_name, quantity, unit, ingredient_types(name, category)")
    .eq("household_id", hh_id)
    .order("ingredient_types(category)")
    .execute()
).data

if not items:
    st.info("Your pantry is empty. Add items above.")
else:
    # Group by category
    from collections import defaultdict
    by_category = defaultdict(list)
    for item in items:
        cat = item.get("ingredient_types", {}).get("category", "Other") if item.get("ingredient_types") else "Uncategorized"
        by_category[cat].append(item)

    for category, cat_items in sorted(by_category.items()):
        st.markdown(f"**{category}**")
        for item in cat_items:
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
                    label_visibility="collapsed"
                )
                if new_qty != item["quantity"]:
                    sb.table("pantry_items").update({"quantity": new_qty}).eq("id", item["id"]).execute()
                    st.rerun()
            with col4:
                if st.button("🗑️", key=f"del_{item['id']}"):
                    sb.table("pantry_items").delete().eq("id", item["id"]).execute()
                    st.rerun()
        st.markdown("")
