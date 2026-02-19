# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Run the Streamlit web app (primary interface)
python3 -m streamlit run web_pantry.py

# Run the legacy terminal-only version
python3 pantry.py
```

The web app runs locally at `http://localhost:8501` and auto-reloads on file save.

## Architecture

This is an early-stage Streamlit prototype with no database — pantry state is persisted in `pantry_list.txt` (one item per line, lowercased on read).

**`web_pantry.py`** — the main app, all logic in a single file:
- Reads/writes `pantry_list.txt` directly using Python file I/O
- Recipes are hardcoded as a Python dict (`name -> list of ingredients`)
- Fuzzy ingredient matching: `i in p or p in i` allows "goat milk" to satisfy a "milk" requirement
- Missing ingredients are compiled into a Samsung Food (Whisk) URL to send to Amazon Fresh

**`pantry.py`** — original CLI prototype, now superseded by `web_pantry.py`. Both share the same `pantry_list.txt` file.

## Key Design Decisions

- **Fuzzy matching** (`any(i in p or p in i for p in inventory)`): matches ingredient substrings bidirectionally so pantry entries like "sheep milk" satisfy recipe requirements for "milk".
- **Flat file storage**: `pantry_list.txt` is the source of truth. Items are stored as entered; lowercased only at read time via `.strip().lower()`.
- **No session state persistence for recipes**: recipes are hardcoded in `web_pantry.py` and must be edited in the source to add/change them.
- **Grocery ordering**: uses Samsung Food (Whisk) `https://my.samsungfood.com` URL with URL-encoded ingredient list — not a direct Amazon API integration.

## Planned Expansion (from project history)

The goal is to evolve toward: Spoonacular/Edamam API for recipe search, SQLite or Supabase for multi-user pantry storage, and direct Amazon Fresh/Whole Foods cart integration via the Amazon SP-API or Whisk widget.
