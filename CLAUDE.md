# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

**Migrating from Streamlit → SvelteKit.** The Streamlit app is complete and working; the SvelteKit app is being built in `web/`. Once `web/` is verified, the Streamlit code (`app.py`, `pages/`, `utils/`) will be deleted.

## Running the apps

```bash
# Streamlit (current, working)
python3 -m streamlit run app.py
# → http://localhost:8501

# SvelteKit (in progress)
cd web && npm run dev
# → http://localhost:5173

# Python API microservice (future, recipe scraping + Safeway)
cd api && uvicorn main:app --reload
```

Supabase CLI (at `/opt/homebrew/bin/supabase`):
```bash
/opt/homebrew/bin/supabase db push   # apply new migrations
/opt/homebrew/bin/supabase db diff   # preview pending changes
```

## Tech Stack

| Layer | Streamlit (current) | SvelteKit (target) |
|---|---|---|
| UI | Streamlit 1.32+ | SvelteKit 2 + Svelte 5 + Tailwind |
| Language | Python 3.9 | TypeScript |
| Auth + DB client | supabase-py 2.x | @supabase/ssr + @supabase/supabase-js |
| Fuzzy matching | rapidfuzz (Python) | fuse.js (JS) |
| Deployment | Streamlit Community Cloud | Vercel |

## Architecture

### Database (Supabase / PostgreSQL)
All schema is in `supabase/migrations/`. Key tables:
- `households` — id, name, invite_code
- `household_members` — user_id, household_id, role (owner/member)
- `pantry_items` — id, household_id, specific_name, quantity, unit (ingredient_type_id is nullable legacy)
- `ingredient_substitutions` — id, household_id, ingredient_a, ingredient_b (bidirectional pairs)
- `recipes`, `recipe_ingredients` — recipe storage (TheMealDB cache + user imports)
- `meal_plans`, `meal_plan_recipes` — weekly planner
- `shopping_list_items` — generated from pantry diff

RLS is enabled on all tables. Every migration must include explicit `GRANT ALL ON <table> TO authenticated` — Supabase's `db push` does NOT add grants automatically.

### Ingredient Matching Logic
Resolution order (applies in both Streamlit and SvelteKit):
1. Exact match (case-insensitive)
2. Bidirectional substitution pair lookup (`ingredient_substitutions` table)
3. Fuzzy match — rapidfuzz `token_sort_ratio ≥ 82` (Streamlit) / fuse.js threshold ≤ 0.18 (SvelteKit)

**Important:** Always lowercase both strings before fuzzy comparison. `token_sort_ratio("Goat Milk", "goat milk")` scores 77.8 (below threshold); lowercased scores 100.

### Streamlit Auth (supabase-py quirks)
- `supabase-py` 2.x does not reliably propagate JWT to PostgREST. The `_AuthClient` wrapper in `utils/supabase_client.py` injects `Authorization: Bearer <token>` into every `table()` call's headers manually.
- `_create_household()` uses the `requests` library directly (bypasses supabase-py JWT issues entirely).
- Session persistence across browser refreshes uses a custom localStorage JS bridge (`persist_auth()` / `clear_persisted_auth()` in `supabase_client.py`).
- None of these workarounds are needed in the SvelteKit app — `@supabase/ssr` handles all of it.

### SvelteKit App Structure (target)
```
web/src/
  lib/
    supabase.ts          ← createBrowserClient / createServerClient
    ingredient_matcher.ts ← fuzzy matching (fuse.js)
    types.ts             ← DB row types
  routes/
    +layout.svelte       ← auth guard, sidebar
    +layout.server.ts    ← session SSR load
    login/+page.svelte
    (app)/               ← auth-gated group
      +page.svelte       ← Dashboard
      pantry/+page.svelte
      recipes/+page.svelte
      meal-plan/+page.svelte
      shopping/+page.svelte
    auth/callback/+server.ts  ← Supabase OAuth callback
```

## Key Decisions

- **Name-based matching** (not canonical types): `pantry_items.ingredient_type_id` is nullable; matching is done on `specific_name` text with fuzzy + substitution pairs. The old `ingredient_types`/`ingredient_aliases` taxonomy was dropped in migration `20260219000003`.
- **Substitution pairs are bidirectional**: "EVOO ↔ Olive Oil" stored once; the matcher checks both orderings.
- **No auto-commit**: never commit unless explicitly asked.
- **Python 3.9**: use `from __future__ import annotations` for `X | Y` union type hints.
