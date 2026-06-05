"""
JellyInspector - Ghost Season Merger
=====================================
Detects and fixes orphan/ghost seasons in a Jellyfin series.

Ghost seasons appear when:
  - Jellyfin creates virtual seasons from TMDB metadata (with IndexNumber 1, 2, 3...)
  - Your physical folders have non-standard names and get IndexNumber: null
  - Result: duplicate seasons visible in the UI

This tool detects orphan seasons (IndexNumber: null) and prompts the agent
to assign the correct index, which merges them with the TMDB virtual seasons.

Usage:
    python agent_ghost_merger.py --series_id <ID>

    For automated use (no prompts):
    python agent_ghost_merger.py --series_id <ID> --mapping '{"Season 2": 2, "Season 3": 3}'
"""

import sys
import json
import argparse
from dotenv import load_dotenv
from jellyfin_api import JellyfinClient

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Detect and fix ghost/orphan seasons")
    parser.add_argument("--series_id", required=True, help="Jellyfin Series ID")
    parser.add_argument("--mapping", help="JSON string mapping season names to IndexNumbers")
    args = parser.parse_args()

    client = JellyfinClient()
    seasons = client.get_seasons(args.series_id)

    # Parse mapping if provided
    name_to_index = {}
    if args.mapping:
        name_to_index = json.loads(args.mapping)

    # ── Detect ghosts ─────────────────────────────────────────────
    orphans = []
    indexed = {}

    for s in seasons:
        s_item = client.get_item(s["Id"])
        s_idx = s_item.get("IndexNumber")
        s_name = s_item.get("Name", "???")

        if s_idx is None:
            orphans.append(s_item)
            print(f"  👻 ORPHAN: '{s_name}' (ID: {s_item['Id']}) — no IndexNumber")
        else:
            if s_idx in indexed:
                print(f"  ⚠️  DUPLICATE: '{s_name}' and '{indexed[s_idx]}' both have IndexNumber={s_idx}")
            else:
                indexed[s_idx] = s_name
                print(f"  ✓ S{s_idx}: {s_name}")

    if not orphans:
        print("\n✅ No ghost seasons found. Nothing to fix.")
        return

    # ── Fix orphans ───────────────────────────────────────────────
    print(f"\n{len(orphans)} orphan season(s) found. Attempting fix...\n")

    fixed = 0
    for orphan in orphans:
        name = orphan.get("Name", "???")

        # Try to find the correct index from the mapping
        target_idx = name_to_index.get(name)

        if target_idx is None:
            print(f"  ⚠️  '{name}': No mapping provided. Skipping.")
            print(f"       → Add it to --mapping: '{{\"{name}\": <correct_index>}}'")
            continue

        # Apply the fix
        orphan["IndexNumber"] = target_idx
        orphan["OriginalTitle"] = ""
        if "LockedFields" in orphan:
            del orphan["LockedFields"]  # Avoid 400 from invalid locked fields

        client.update_item_metadata(orphan["Id"], orphan)
        print(f"  ✓ '{name}' → assigned IndexNumber={target_idx}")
        fixed += 1

    if fixed > 0:
        print(f"\n✅ Fixed {fixed} orphan season(s). Run agent_refresh.py to merge them.")
    else:
        print(f"\n⚠️  No orphans were fixed. Provide --mapping for the remaining ones.")


if __name__ == "__main__":
    main()
