"""
JellyInspector - Universal Season Fixer
========================================
Corrects season-level metadata for any series in Jellyfin:
  - Injects proper season names from AniList (NOVEL or ANIME search)
  - Uploads cover art from AniList
  - Cleans OriginalTitle pollution
  - Locks fields to prevent TMDB scraper from reverting changes

Designed to be data-driven: pass a JSON mapping of season corrections.

Usage:
    python agent_universal_fixer.py --series_id <ID> --mapping <JSON_FILE>

    The JSON mapping file should contain an object like:
    {
        "1": {"name": "Bakemonogatari", "search_type": "ANIME"},
        "2": {"name": "Kizumonogatari", "search_type": "NOVEL"},
        ...
    }

    If --mapping is not provided, the script will only clean OriginalTitle
    and lock existing Name fields on all seasons.
"""

import sys
import json
import argparse
import requests
from dotenv import load_dotenv
from jellyfin_api import JellyfinClient

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")


# ── AniList GraphQL Helpers ───────────────────────────────────────

def search_anilist(query_str, media_format="ANIME"):
    """
    Search AniList for a title. Returns {title, cover_url} or None.

    Args:
        query_str: Title to search for.
        media_format: "ANIME" or "NOVEL" (light novel covers are often
                      better for multi-arc series like Monogatari).
    """
    media_type = "ANIME" if media_format == "ANIME" else "MANGA"
    format_filter = f', format: {media_format}' if media_format != "ANIME" else ""

    query = f"""
    query ($search: String) {{
      Page(page: 1, perPage: 1) {{
        media(search: $search, type: {media_type}{format_filter}) {{
          title {{ romaji english }}
          coverImage {{ extraLarge }}
        }}
      }}
    }}
    """
    try:
        resp = requests.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": {"search": query_str}},
            timeout=10,
        )
        if resp.status_code == 200:
            media = resp.json().get("data", {}).get("Page", {}).get("media", [])
            if media:
                return {
                    "title": media[0]["title"].get("english") or media[0]["title"]["romaji"],
                    "cover_url": media[0]["coverImage"]["extraLarge"],
                }
    except Exception as e:
        print(f"  ⚠ AniList error: {e}")
    return None


def update_item_clean(client, item_id, updates):
    """
    Safely update an item's metadata.

    - Reads the full BaseItemDto
    - Applies updates
    - Adds Name/Overview to LockedFields (only safe fields!)
    - Cleans OriginalTitle to "" (never None)
    - POSTs the full object back
    """
    item = client.get_item(item_id)

    locked = item.get("LockedFields", [])
    changed = False

    for key, value in updates.items():
        if value is not None and item.get(key) != value:
            item[key] = value
            changed = True
        # Only lock safe fields
        if key in ("Name", "Overview") and key not in locked:
            locked.append(key)

    if changed or len(locked) > len(item.get("LockedFields", [])):
        item["LockedFields"] = locked
        client.update_item_metadata(item_id, item)
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Fix season metadata for a Jellyfin series")
    parser.add_argument("--series_id", required=True, help="Jellyfin Series ID")
    parser.add_argument("--mapping", help="Path to JSON mapping file (optional)")
    args = parser.parse_args()

    client = JellyfinClient()

    # Load mapping if provided
    arc_map = {}
    if args.mapping:
        with open(args.mapping, "r", encoding="utf-8") as f:
            arc_map = json.load(f)

    # ── Series-level cleanup ──────────────────────────────────────
    series = client.get_item(args.series_id)
    print(f"Series: {series.get('Name')}")
    update_item_clean(client, args.series_id, {"OriginalTitle": ""})
    print("  ✓ Series OriginalTitle cleaned and locked.\n")

    # ── Season-level fixes ────────────────────────────────────────
    seasons = client.get_seasons(args.series_id)
    print(f"Processing {len(seasons)} seasons...\n")

    for s in seasons:
        s_id = s["Id"]
        s_idx = s.get("IndexNumber")
        s_name = s.get("Name", "")
        print(f"Season {s_idx}: {s_name}")

        updates = {"OriginalTitle": ""}

        # If we have a mapping entry for this season index
        s_key = str(s_idx) if s_idx is not None else None
        if s_key and s_key in arc_map:
            entry = arc_map[s_key]
            search_name = entry.get("name", s_name)
            search_type = entry.get("search_type", "ANIME")

            # Try primary search type first, fall back to ANIME
            ani = search_anilist(search_name, search_type)
            if not ani and search_type == "NOVEL":
                ani = search_anilist(search_name, "ANIME")

            if ani:
                updates["Name"] = ani["title"]
                print(f"  → Name: {ani['title']}")
                try:
                    client.upload_image(s_id, ani["cover_url"], "Primary")
                    print(f"  → Cover uploaded from AniList")
                except Exception as e:
                    print(f"  ⚠ Cover upload failed: {e}")

        update_item_clean(client, s_id, updates)
        print(f"  ✓ Updated and locked.\n")

    print("✅ All seasons processed.")


if __name__ == "__main__":
    main()
