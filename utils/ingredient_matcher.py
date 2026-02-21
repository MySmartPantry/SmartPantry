from __future__ import annotations

"""
Ingredient matching and pantry diff utilities.

Matching order for any two ingredient names:
  1. Exact match (case-insensitive)
  2. Either name appears in a household substitution pair
  3. Fuzzy match via token_sort_ratio >= FUZZY_THRESHOLD

Both strings are lowercased before comparison — rapidfuzz scores differ
meaningfully by case (e.g. "Goat Milk" vs "goat milk" = 77 without lowering).
"""

import streamlit as st
from rapidfuzz.fuzz import token_sort_ratio
from utils.supabase_client import get_client

FUZZY_THRESHOLD = 82


@st.cache_data(ttl=300)
def get_substitutions() -> list:
    """Returns all substitution pairs as a list of {id, household_id, ingredient_a, ingredient_b}."""
    sb = get_client()
    result = (
        sb.table("ingredient_substitutions")
        .select("id, household_id, ingredient_a, ingredient_b")
        .execute()
    )
    return result.data or []


def names_match(a: str, b: str, substitutions: list | None = None) -> bool:
    """
    Returns True if a and b refer to the same ingredient via:
      1. Exact match (case-insensitive)
      2. Either order appears in a substitution pair
      3. Fuzzy token_sort_ratio >= FUZZY_THRESHOLD
    """
    a_low = a.strip().lower()
    b_low = b.strip().lower()

    if a_low == b_low:
        return True

    if substitutions is None:
        substitutions = get_substitutions()

    for pair in substitutions:
        pa = pair["ingredient_a"].strip().lower()
        pb = pair["ingredient_b"].strip().lower()
        if (a_low in (pa, pb)) and (b_low in (pa, pb)):
            return True

    return token_sort_ratio(a_low, b_low) >= FUZZY_THRESHOLD


def find_match(needle: str, name_list: list[str], substitutions: list | None = None) -> str | None:
    """
    Returns the first name in name_list that matches needle, or None.
    name_list should be strings (e.g. specific_name values from pantry).
    """
    if substitutions is None:
        substitutions = get_substitutions()
    for name in name_list:
        if names_match(needle, name, substitutions):
            return name
    return None


def get_pantry_items(household_id: str) -> list:
    """Returns all pantry items for the household as a list of dicts."""
    sb = get_client()
    result = (
        sb.table("pantry_items")
        .select("id, specific_name, quantity, unit")
        .eq("household_id", household_id)
        .order("specific_name")
        .execute()
    )
    return result.data or []


def check_recipe_against_pantry(recipe_id: str, household_id: str) -> dict:
    """
    Compares a recipe's ingredients against the household pantry by name matching.

    Returns:
        {
          "have": [ingredient rows],
          "missing": [ingredient rows],
          "match_pct": float (0–100),
          "total": int,
        }
    """
    sb = get_client()
    ingredients = (
        sb.table("recipe_ingredients")
        .select("ingredient_type_id, quantity, unit, note, ingredient_types(name, category)")
        .eq("recipe_id", recipe_id)
        .execute()
    ).data or []

    if not ingredients:
        return {"have": [], "missing": [], "match_pct": 0.0, "total": 0}

    pantry = get_pantry_items(household_id)
    pantry_names = [item["specific_name"] for item in pantry]
    subs = get_substitutions()

    have, missing = [], []
    for ing in ingredients:
        # recipe_ingredients still stores ingredient_type_id; get the canonical name
        ing_name = ing.get("ingredient_types", {}).get("name", "") if ing.get("ingredient_types") else ""
        if ing_name and find_match(ing_name, pantry_names, subs) is not None:
            have.append(ing)
        else:
            missing.append(ing)

    total = len(ingredients)
    match_pct = (len(have) / total * 100) if total > 0 else 0.0
    return {"have": have, "missing": missing, "match_pct": match_pct, "total": total}


def deduct_from_pantry(recipe_id: str, household_id: str, servings: int = 1, recipe_servings: int = 4) -> list:
    """
    Subtracts recipe ingredient quantities from the household pantry
    proportional to the number of servings being cooked.

    Returns a list of human-readable strings describing what was deducted.
    """
    sb = get_client()
    scale = servings / max(recipe_servings, 1)

    ingredients = (
        sb.table("recipe_ingredients")
        .select("quantity, unit, ingredient_types(name)")
        .eq("recipe_id", recipe_id)
        .execute()
    ).data or []

    pantry = get_pantry_items(household_id)
    subs = get_substitutions()
    log = []

    for ing in ingredients:
        ing_name = ing.get("ingredient_types", {}).get("name", "") if ing.get("ingredient_types") else ""
        if not ing_name:
            continue

        needed_qty = (ing["quantity"] or 1) * scale
        unit = ing["unit"] or "count"

        matched_name = find_match(ing_name, [item["specific_name"] for item in pantry], subs)
        if matched_name is None:
            continue

        item = next(i for i in pantry if i["specific_name"] == matched_name)
        new_qty = (item["quantity"] or 0) - needed_qty

        if new_qty <= 0:
            sb.table("pantry_items").delete().eq("id", item["id"]).execute()
            log.append(f"Used all {item['specific_name']}")
        else:
            sb.table("pantry_items").update({"quantity": round(new_qty, 2)}).eq("id", item["id"]).execute()
            log.append(f"{round(needed_qty, 2)} {unit} {item['specific_name']}")
            # Update local copy so subsequent ingredients see the reduced quantity
            item["quantity"] = new_qty

    return log
