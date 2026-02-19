"""
Ingredient matching and pantry diff utilities.

Core idea: every specific ingredient (e.g. "Goat Milk", "Penne") maps to
a canonical ingredient_type (e.g. "Milk", "Pasta") via the ingredient_aliases
table. Recipe requirements and pantry items are compared by ingredient_type_id,
not by text — so any specific variant satisfies the canonical requirement.
"""

import streamlit as st
from utils.supabase_client import get_client


@st.cache_data(ttl=300)
def get_all_types() -> dict:
    """Returns {name.lower(): {id, name, category}} for all ingredient types."""
    sb = get_client()
    result = sb.table("ingredient_types").select("id, name, category").execute()
    return {row["name"].lower(): row for row in result.data}


@st.cache_data(ttl=300)
def get_all_aliases() -> dict:
    """Returns {alias.lower(): ingredient_type_id} for all aliases."""
    sb = get_client()
    result = sb.table("ingredient_aliases").select("alias, ingredient_type_id").execute()
    return {row["alias"].lower(): row["ingredient_type_id"] for row in result.data}


def find_canonical_id(name: str):
    """
    Given any ingredient name (e.g. "Goat Milk", "penne pasta", "EVOO"),
    returns the ingredient_type_id it maps to, or None if not recognized.

    Resolution order:
      1. Exact match in ingredient_types (case-insensitive)
      2. Exact match in ingredient_aliases (case-insensitive)
      3. Substring match — does the name contain a known type/alias?
    """
    name_lower = name.strip().lower()
    types = get_all_types()
    aliases = get_all_aliases()

    # 1. Exact type match
    if name_lower in types:
        return types[name_lower]["id"]

    # 2. Exact alias match
    if name_lower in aliases:
        return aliases[name_lower]

    # 3. Substring: does the entered name contain a known alias or type?
    for alias, type_id in aliases.items():
        if alias in name_lower or name_lower in alias:
            return type_id
    for type_name, type_row in types.items():
        if type_name in name_lower or name_lower in type_name:
            return type_row["id"]

    return None


def get_pantry_type_ids(household_id: str) -> set:
    """Returns a set of ingredient_type_ids currently in the household's pantry."""
    sb = get_client()
    result = (
        sb.table("pantry_items")
        .select("ingredient_type_id")
        .eq("household_id", household_id)
        .execute()
    )
    return {row["ingredient_type_id"] for row in result.data}


def check_recipe_against_pantry(recipe_id: str, household_id: str) -> dict:
    """
    Compares a recipe's ingredients against the household pantry.

    Returns:
        {
          "have": [ingredient_type rows],
          "missing": [ingredient_type rows],
          "match_pct": float (0-100),
          "total": int,
        }
    """
    sb = get_client()
    ingredients = (
        sb.table("recipe_ingredients")
        .select("ingredient_type_id, quantity, unit, note, ingredient_types(name, category)")
        .eq("recipe_id", recipe_id)
        .execute()
    ).data

    if not ingredients:
        return {"have": [], "missing": [], "match_pct": 0.0, "total": 0}

    pantry_ids = get_pantry_type_ids(household_id)
    have, missing = [], []
    for ing in ingredients:
        if ing["ingredient_type_id"] in pantry_ids:
            have.append(ing)
        else:
            missing.append(ing)

    total = len(ingredients)
    match_pct = (len(have) / total * 100) if total > 0 else 0.0
    return {"have": have, "missing": missing, "match_pct": match_pct, "total": total}


def deduct_from_pantry(recipe_id: str, household_id: str, servings: int = 1, recipe_servings: int = 4):
    """
    Subtracts recipe ingredient quantities from the household pantry
    proportional to the number of servings being cooked.

    Returns a list of human-readable strings describing what was deducted.
    E.g. ["2.0 cups Goat Milk", "3.0 count Eggs"]
    """
    sb = get_client()
    scale = servings / max(recipe_servings, 1)

    ingredients = (
        sb.table("recipe_ingredients")
        .select("ingredient_type_id, quantity, unit, ingredient_types(name)")
        .eq("recipe_id", recipe_id)
        .execute()
    ).data

    log = []
    for ing in ingredients:
        type_id = ing["ingredient_type_id"]
        needed_qty = (ing["quantity"] or 1) * scale
        unit = ing["unit"] or "count"
        type_name = ing["ingredient_types"]["name"]

        # Find a matching pantry item for this household
        pantry = (
            sb.table("pantry_items")
            .select("id, quantity, unit, specific_name")
            .eq("household_id", household_id)
            .eq("ingredient_type_id", type_id)
            .limit(1)
            .execute()
        ).data

        if not pantry:
            continue

        item = pantry[0]
        new_qty = (item["quantity"] or 0) - needed_qty

        if new_qty <= 0:
            sb.table("pantry_items").delete().eq("id", item["id"]).execute()
            log.append(f"Used all {item['specific_name']} ({type_name})")
        else:
            sb.table("pantry_items").update({"quantity": round(new_qty, 2)}).eq("id", item["id"]).execute()
            log.append(f"{round(needed_qty, 2)} {unit} {item['specific_name']}")

    return log
