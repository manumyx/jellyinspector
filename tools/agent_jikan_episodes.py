"""
JellyInspector - Episode Metadata Injector (Jikan/MAL)
=======================================================
Fetches episode titles and synopses from MyAnimeList via the Jikan API
and injects them into Jellyfin episodes.

Features:
  - Incremental: skips episodes that already have a custom title AND overview
  - Rate-limited: respects Jikan's 3 req/sec limit with configurable delays
  - Fault-tolerant: catches timeouts/429s and continues, can be re-run safely
  - Supports both TV episodes and movie collections (e.g., Kizumonogatari)

Usage:
    python agent_jikan_episodes.py --series_id <ID> --mapping <JSON_FILE>

    The JSON mapping file should contain:
    {
        "1": {"mal_id": 5081, "offset": 0, "is_movie": false},
        "2": {"mal_ids": [9260, 31757, 31758], "is_movie": true},
        ...
    }

    Each key is the Jellyfin season IndexNumber (as string).
    - For TV: "mal_id" (int) + "offset" (int, default 0)
      Jikan episode = Jellyfin episode index + offset
    - For Movies: "mal_ids" (list of MAL anime IDs, one per "episode")
"""

import sys
import json
import argparse
import time
import requests
from dotenv import load_dotenv
from jellyfin_api import JellyfinClient

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

JIKAN_DELAY = 0.5  # seconds between requests (Jikan rate limit: 3/sec)
JIKAN_TIMEOUT = 15  # seconds before giving up on a request
MAX_RETRIES = 2     # retry failed requests this many times


# ── Jikan API Helpers ─────────────────────────────────────────────

def get_jikan_episode(mal_id, ep_num):
    """Fetch a single episode's metadata from Jikan."""
    url = f"https://api.jikan.moe/v4/anime/{mal_id}/episodes/{ep_num}"
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=JIKAN_TIMEOUT)
            time.sleep(JIKAN_DELAY)
            if resp.status_code == 200:
                return resp.json().get("data", {})
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"    ⚠ Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
                continue
        except requests.exceptions.Timeout:
            print(f"    ⚠ Timeout (attempt {attempt + 1}/{MAX_RETRIES + 1})")
        except Exception as e:
            print(f"    ⚠ Jikan error: {e}")
            break
    return {}


def get_jikan_anime(mal_id):
    """Fetch a full anime entry from Jikan (used for movies)."""
    url = f"https://api.jikan.moe/v4/anime/{mal_id}"
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=JIKAN_TIMEOUT)
            time.sleep(JIKAN_DELAY)
            if resp.status_code == 200:
                return resp.json().get("data", {})
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"    ⚠ Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
                continue
        except requests.exceptions.Timeout:
            print(f"    ⚠ Timeout (attempt {attempt + 1}/{MAX_RETRIES + 1})")
        except Exception as e:
            print(f"    ⚠ Jikan error: {e}")
            break
    return {}


# ── Jellyfin Update Helper ───────────────────────────────────────

def update_episode_clean(client, item_id, updates):
    """
    Update an episode with proper LockedFields handling.
    Only locks Name and Overview (safe fields).
    """
    item = client.get_item(item_id)

    locked = item.get("LockedFields", [])
    changed = False

    for key, value in updates.items():
        if value is not None and item.get(key) != value:
            item[key] = value
            changed = True
        if key in ("Name", "Overview") and key not in locked:
            locked.append(key)

    if changed or len(locked) > len(item.get("LockedFields", [])):
        item["LockedFields"] = locked
        client.update_item_metadata(item_id, item)
        return True
    return False


# ── Main Logic ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Inject episode metadata from Jikan/MAL")
    parser.add_argument("--series_id", required=True, help="Jellyfin Series ID")
    parser.add_argument("--mapping", required=True, help="Path to JSON mapping file")
    args = parser.parse_args()

    client = JellyfinClient()

    # Load the season→MAL mapping
    with open(args.mapping, "r", encoding="utf-8") as f:
        jikan_map = json.load(f)

    # Fetch all episodes
    print("\nFetching episodes from Jellyfin...")
    episodes = client.get_episodes(args.series_id)
    episodes.sort(key=lambda x: (x.get("ParentIndexNumber", 0), x.get("IndexNumber", 0)))
    print(f"Found {len(episodes)} episodes.\n")

    updated = 0
    skipped = 0
    failed = 0

    for e in episodes:
        e_id = e["Id"]
        s_idx = e.get("ParentIndexNumber")
        e_idx = e.get("IndexNumber")
        s_key = str(s_idx)

        if s_key not in jikan_map:
            continue

        mapping = jikan_map[s_key]
        is_movie = mapping.get("is_movie", False)

        # ── Incremental check: skip if already complete ───────
        name = e.get("Name", "")
        overview = e.get("Overview", "")
        has_custom_title = not name.startswith("Episode ") and not name.startswith("第") and name != ""
        has_overview = overview and len(overview.strip()) > 10

        if has_custom_title and has_overview:
            print(f"  S{s_idx}E{e_idx}: ✓ Already complete. Skipping.")
            skipped += 1
            continue

        print(f"  S{s_idx}E{e_idx}: Fetching from Jikan...", end=" ")

        # ── Fetch from Jikan ──────────────────────────────────
        title = None
        synopsis = None

        if is_movie:
            mal_ids = mapping.get("mal_ids", [])
            if e_idx and e_idx - 1 < len(mal_ids):
                data = get_jikan_anime(mal_ids[e_idx - 1])
                title = data.get("title_english") or data.get("title")
                synopsis = data.get("synopsis")
        else:
            mal_id = mapping.get("mal_id")
            offset = mapping.get("offset", 0)
            if mal_id and e_idx:
                data = get_jikan_episode(mal_id, e_idx + offset)
                title = data.get("title")
                synopsis = data.get("synopsis")

        # ── Apply updates ─────────────────────────────────────
        if title or synopsis:
            updates = {"OriginalTitle": ""}
            if title and not has_custom_title:
                updates["Name"] = title.replace("  ", " ").strip()
            if synopsis and not has_overview:
                updates["Overview"] = synopsis

            update_episode_clean(client, e_id, updates)
            print(f"→ {updates.get('Name', title or '(overview only)')}")
            updated += 1
        else:
            print("⚠ No data from Jikan.")
            failed += 1

    # ── Summary ───────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"INJECTION COMPLETE")
    print(f"{'='*50}")
    print(f"  Updated:  {updated}")
    print(f"  Skipped:  {skipped} (already complete)")
    print(f"  Failed:   {failed} (Jikan returned no data)")
    print(f"  Total:    {len(episodes)}")

    if failed > 0:
        print(f"\n💡 TIP: Re-run this script to retry the {failed} failed episodes.")
        print("   The incremental logic will skip everything that's already done.")


if __name__ == "__main__":
    main()
