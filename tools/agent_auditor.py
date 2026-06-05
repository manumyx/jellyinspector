"""
JellyInspector - Deep Auditor
==============================
Performs a FULL audit of a series in Jellyfin: Series → Seasons → ALL Episodes.
Reports missing titles, missing overviews, missing artwork, ghost seasons,
and OriginalTitle pollution.

Usage:
    python agent_auditor.py --series_id <JELLYFIN_SERIES_ID>

Exit codes:
    0  – All checks passed
    1  – Issues found (details printed to stdout)
"""

import sys
import argparse
import requests
from dotenv import load_dotenv
from jellyfin_api import JellyfinClient

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")


def check_images(item):
    tags = item.get("ImageTags", {})
    return "Primary" in tags


def audit_series(client, series_id):
    """
    Run a full audit on a series. Returns a dict with:
        ok: bool
        issues: list[str]
        stats: dict
    """
    issues = []
    stats = {"seasons": 0, "episodes": 0, "missing_titles": 0, "missing_overviews": 0, "missing_art": 0, "ghost_seasons": 0}

    # ── Series-level check ────────────────────────────────────────
    series = client.get_item(series_id)
    print(f"{'='*60}")
    print(f"SERIES: {series.get('Name')}  (ID: {series_id})")
    print(f"{'='*60}")

    orig = series.get("OriginalTitle", "")
    if orig and orig != series.get("Name", ""):
        issues.append(f"[SERIES] OriginalTitle pollution: '{orig}'")
    if not check_images(series):
        issues.append("[SERIES] Missing Primary artwork")
        stats["missing_art"] += 1

    # ── Season-level check ────────────────────────────────────────
    seasons = client.get_seasons(series_id)
    print(f"\n{'─'*60}")
    print(f"SEASONS ({len(seasons)} found)")
    print(f"{'─'*60}")

    seen_indices = {}
    for s in seasons:
        s_item = client.get_item(s["Id"])
        s_idx = s_item.get("IndexNumber")
        s_name = s_item.get("Name", "")
        stats["seasons"] += 1

        status_flags = []

        # Ghost season detection (duplicate IndexNumber)
        if s_idx is not None and s_idx in seen_indices:
            issues.append(f"[SEASON] Ghost duplicate: '{s_name}' and '{seen_indices[s_idx]}' both have IndexNumber={s_idx}")
            stats["ghost_seasons"] += 1
            status_flags.append("⚠ GHOST")
        if s_idx is not None:
            seen_indices[s_idx] = s_name

        # Season with no IndexNumber (orphan from bad folder naming)
        if s_idx is None:
            issues.append(f"[SEASON] '{s_name}' has no IndexNumber (orphan season)")
            stats["ghost_seasons"] += 1
            status_flags.append("⚠ ORPHAN")

        # Generic name detection
        if s_name.startswith("Season ") and s_idx is not None and s_idx > 0:
            # Only flag if it looks like a non-renamed TMDB season
            status_flags.append("ℹ Generic name")

        if not check_images(s_item):
            issues.append(f"[SEASON] '{s_name}' missing Primary artwork")
            stats["missing_art"] += 1
            status_flags.append("⚠ NO ART")

        # OriginalTitle pollution
        s_orig = s_item.get("OriginalTitle", "")
        if s_orig and s_orig != s_name:
            issues.append(f"[SEASON] '{s_name}' has OriginalTitle pollution: '{s_orig}'")
            status_flags.append("⚠ ORIG_TITLE")

        flag_str = f"  [{', '.join(status_flags)}]" if status_flags else ""
        locked = s_item.get("LockedFields", [])
        print(f"  S{s_idx or '?'}: {s_name}  (locked: {locked}){flag_str}")

    # ── Episode-level check ───────────────────────────────────────
    episodes = client.get_episodes(series_id)
    print(f"\n{'─'*60}")
    print(f"EPISODES ({len(episodes)} found)")
    print(f"{'─'*60}")

    for e in episodes:
        e_item = client.get_item(e["Id"])
        e_idx = e_item.get("IndexNumber")
        s_idx = e_item.get("ParentIndexNumber")
        e_name = e_item.get("Name", "")
        e_overview = e_item.get("Overview", "")
        stats["episodes"] += 1

        ep_issues = []

        # Missing or generic title
        if e_name.startswith("Episode ") or e_name.startswith("第") or not e_name:
            issues.append(f"[EPISODE] S{s_idx}E{e_idx}: Missing custom title (current: '{e_name}')")
            stats["missing_titles"] += 1
            ep_issues.append("NO_TITLE")

        # Missing overview
        if not e_overview or len(e_overview.strip()) < 10:
            issues.append(f"[EPISODE] S{s_idx}E{e_idx}: Missing overview")
            stats["missing_overviews"] += 1
            ep_issues.append("NO_OVERVIEW")

        # OriginalTitle pollution
        e_orig = e_item.get("OriginalTitle", "")
        if e_orig and e_orig != e_name and e_orig != "":
            ep_issues.append("ORIG_TITLE")

        flag_str = f"  ⚠ {', '.join(ep_issues)}" if ep_issues else "  ✓"
        print(f"  S{s_idx}E{e_idx}: {e_name}{flag_str}")

    # ── Summary ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("AUDIT SUMMARY")
    print(f"{'='*60}")
    print(f"  Seasons:           {stats['seasons']}")
    print(f"  Episodes:          {stats['episodes']}")
    print(f"  Missing titles:    {stats['missing_titles']}")
    print(f"  Missing overviews: {stats['missing_overviews']}")
    print(f"  Missing artwork:   {stats['missing_art']}")
    print(f"  Ghost seasons:     {stats['ghost_seasons']}")
    print(f"  Total issues:      {len(issues)}")

    if issues:
        print(f"\n{'─'*60}")
        print("ALL ISSUES:")
        print(f"{'─'*60}")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")

    return {"ok": len(issues) == 0, "issues": issues, "stats": stats}


def main():
    parser = argparse.ArgumentParser(description="Deep audit a Jellyfin series")
    parser.add_argument("--series_id", required=True, help="Jellyfin Series ID")
    args = parser.parse_args()

    client = JellyfinClient()
    result = audit_series(client, args.series_id)

    if result["ok"]:
        print("\n✅ ALL CHECKS PASSED. Series is clean.")
        sys.exit(0)
    else:
        print(f"\n❌ {len(result['issues'])} ISSUES FOUND. Series needs attention.")
        sys.exit(1)


if __name__ == "__main__":
    main()
