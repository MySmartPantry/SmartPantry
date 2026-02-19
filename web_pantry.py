import streamlit as st
import urllib.parse

st.set_page_config(page_title="My SmartPantry", page_icon="🍎")
st.title("🍎 My SmartPantry")

def get_pantry():
    try:
        with open("pantry_list.txt", "r") as file:
            return [line.strip().lower() for line in file.readlines()]
    except FileNotFoundError: return []

st.sidebar.header("Pantry Controls")
new_item = st.sidebar.text_input("Add an ingredient:")
if st.sidebar.button("Add to Pantry"):
    if new_item:
        with open("pantry_list.txt", "a") as file:
            file.write(new_item.strip() + "\n")
        st.rerun()

if st.sidebar.button("🗑️ Clear Pantry"):
    open("pantry_list.txt", "w").close()
    st.rerun()

st.header("📦 Current Inventory")
inventory = get_pantry()
st.write(", ".join([f"**{i.title()}**" for i in inventory]) if inventory else "Empty")

st.header("🍳 Meal Plan")
recipes = {
    "Hamburger Corn Casserole": ["hamburger", "corn", "green pepper", "onion", "rice", "tomato sauce"],
    "Morning Omelette": ["eggs", "cheese", "milk", "spinach"]
}

all_missing = []
for name, ingredients in recipes.items():
    missing = [i for i in ingredients if not any(i in p or p in i for p in inventory)]
    all_missing.extend(missing)
    with st.expander(name):
        if not missing:
            st.success("Ready!")
        else:
            st.warning(f"Need: {', '.join(missing)}")

st.header("🛒 Grocery List")
shopping_list = list(set(all_missing))

if shopping_list:
    st.write(f"To buy: {', '.join(shopping_list)}")
    ingredients_str = ",".join(shopping_list)
    # This URL is the "magic" bridge to Amazon/Whole Foods
    whisk_url = f"https://my.samsungfood.com{urllib.parse.quote(ingredients_str)}"
    st.link_button("🚀 Send to Amazon Fresh / Whole Foods", whisk_url)
else:
    st.success("Stocked!")
