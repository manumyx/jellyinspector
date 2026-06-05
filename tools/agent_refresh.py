"""
JellyInspector - Library Refresh Trigger
=========================================
Forces Jellyfin to rescan all libraries and propagate metadata changes.
Must be run after any batch metadata injection to update the UI cache.

Usage:
    python agent_refresh.py
"""

import sys
from dotenv import load_dotenv
from jellyfin_api import JellyfinClient

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")


def main():
    print("Triggering full library scan via Jellyfin API...")
    try:
        client = JellyfinClient()
        client.refresh_library()
        print("✅ Library scan started successfully.")
        print("   Jellyfin will now re-read all metadata from its database.")
        print("   Changes should appear in the UI within 30-60 seconds.")
    except Exception as e:
        print(f"❌ Error triggering scan: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
