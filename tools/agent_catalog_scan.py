"""
JellyInspector - Full Catalog Scanner
=======================================
Scans ALL series in the Jellyfin library and runs a quick health check
on each one. Useful for identifying which series need attention.

Usage:
    python agent_catalog_scan.py

Output:
    A summary table of all series with their health status.
"""

import sys
from dotenv import load_dotenv
from jellyfin_api import JellyfinClient

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")


def quick_health_check(client, series_id):
    """
    Run a lightweight health check on a series.
    Returns a dict with counts of issues found.
    """
    issues = 0
    details = []

    try:
        series = client.get_item(series_id)
    except Exception:
        return {"issues": -1, "details": ["Cannot access series"]}

    # Check series OriginalTitle
    orig = series.get("OriginalTitle", "")
    if orig and orig != series.get("Name", ""):
        issues += 1
        details.append("Series has OriginalTitle pollution")

    # Check seasons
    try:
        seasons = client.get_seasons(series_id)
    except Exception:
        return {"issues": -1, "details": ["Cannot access seasons"]}

    seen_idx = {}
    for s in seasons:
        s_idx = s.get("IndexNumber")
        s_name = s.get("Name", "")

        if s_idx is None:
            issues += 1
            details.append(f"Orphan season: '{s_name}'")
        elif s_idx in seen_idx:
            issues += 1
            details.append(f"Ghost duplicate: S{s_idx}")
        else:
            seen_idx[s_idx] = s_name

    # Check episodes (lightweight: only check names and overviews from list endpoint)
    try:
        episodes = client.get_episodes(series_id)
    except Exception:
        return {"issues": issues, "details": details + ["Cannot access episodes"]}

    missing_titles = 0
    missing_overviews = 0
    for e in episodes:
        name = e.get("Name", "")
        overview = e.get("Overview", "")
        if name.startswith("Episode ") or name.startswith("第") or not name:
            missing_titles += 1
        if not overview or len(overview.strip()) < 10:
            missing_overviews += 1

    if missing_titles:
        issues += missing_titles
        details.append(f"{missing_titles} episodes with generic/missing titles")
    if missing_overviews:
        issues += missing_overviews
        details.append(f"{missing_overviews} episodes with missing overviews")

    return {
        "issues": issues,
        "seasons": len(seasons),
        "episodes": len(episodes),
        "missing_titles": missing_titles,
        "missing_overviews": missing_overviews,
        "details": details,
    }


def main():
    client = JellyfinClient()

    # Get all series
    all_series = client.get_items(include_item_types="Series", recursive=True)

    print(f"{'='*70}")
    print(f"FULL CATALOG SCAN — {len(all_series)} series found")
    print(f"{'='*70}\n")

    healthy = 0
    sick = 0

    for s in all_series:
        name = s.get("Name", "???")
        sid = s.get("Id")

        result = quick_health_check(client, sid)

        if result["issues"] == 0:
            print(f"  ✅ {name}")
            healthy += 1
        elif result["issues"] == -1:
            print(f"  ⚠️  {name} — CANNOT ACCESS")
            sick += 1
        else:
            print(f"  ❌ {name} — {result['issues']} issues")
            for d in result["details"]:
                print(f"       → {d}")
            sick += 1

    print(f"\n{'='*70}")
    print(f"CATALOG SUMMARY")
    print(f"{'='*70}")
    print(f"  Healthy: {healthy}")
    print(f"  Needs attention: {sick}")
    print(f"  Total: {len(all_series)}")

    if sick > 0:
        print(f"\n💡 Run `python agent_auditor.py --series_id <ID>` on each ❌ series for a deep audit.")
        sys.exit(1)
    else:
        print(f"\n✅ All series are clean!")
        sys.exit(0)


if __name__ == "__main__":
    main()
