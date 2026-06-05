"""
JellyInspector - Jellyfin REST API Client
==========================================
Core client for all Jellyfin server interactions.
Handles authentication, item CRUD, image uploads, and library management.

Usage:
    from jellyfin_api import JellyfinClient
    client = JellyfinClient()  # reads from .env
"""

import os
import requests


class JellyfinClient:
    """
    Stateful client for the Jellyfin REST API.

    Reads connection details from environment variables:
        JELLYFIN_URL      – Base URL of the Jellyfin server (default: http://localhost:8096)
        JELLYFIN_API_KEY  – API key with admin privileges
        JELLYFIN_USER_ID  – (Optional) User ID; auto-resolved if omitted
    """

    def __init__(self):
        self.base_url = os.environ.get("JELLYFIN_URL", "http://localhost:8096").rstrip("/")
        self.api_key = os.environ.get("JELLYFIN_API_KEY", "")
        self.user_id = os.environ.get("JELLYFIN_USER_ID", "")
        self.headers = {
            "X-Emby-Token": self.api_key,
            "Content-Type": "application/json",
        }

        # Auto-resolve user_id if not provided
        if not self.user_id:
            self._resolve_user_id()

    def _resolve_user_id(self):
        """Fetch the first admin user ID from the server."""
        try:
            users = requests.get(
                f"{self.base_url}/Users", headers=self.headers, timeout=10
            ).json()
            if users:
                self.user_id = users[0]["Id"]
        except Exception:
            pass  # Will fail later on endpoints that require user_id

    # ── Item Retrieval ────────────────────────────────────────────────

    def get_items(self, search_term=None, include_item_types="Series", recursive=True, fields=None):
        """
        Search or list items from the library.

        Args:
            search_term: Optional text filter.
            include_item_types: Comma-separated types (Series, Season, Episode, Movie).
            recursive: Search all nested folders.
            fields: Comma-separated extra fields (Path, Overview, etc.).
        """
        params = {
            "includeItemTypes": include_item_types,
            "recursive": str(recursive).lower(),
            "fields": fields or "Path,Overview,IndexNumber,ParentIndexNumber",
        }
        if search_term:
            params["searchTerm"] = search_term
        if self.user_id:
            params["userId"] = self.user_id

        resp = requests.get(f"{self.base_url}/Items", headers=self.headers, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("Items", [])

    def get_item(self, item_id):
        """Retrieve the full BaseItemDto for a single item."""
        url = (
            f"{self.base_url}/Users/{self.user_id}/Items/{item_id}"
            if self.user_id
            else f"{self.base_url}/Items/{item_id}"
        )
        resp = requests.get(url, headers=self.headers, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_seasons(self, series_id):
        """Return all Season items for a given series."""
        resp = requests.get(
            f"{self.base_url}/Shows/{series_id}/Seasons",
            headers=self.headers,
            params={"userId": self.user_id},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("Items", [])

    def get_episodes(self, series_id, fields="Overview,Path"):
        """Return all Episode items for a given series."""
        resp = requests.get(
            f"{self.base_url}/Shows/{series_id}/Episodes",
            headers=self.headers,
            params={"userId": self.user_id, "fields": fields},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("Items", [])

    # ── Item Updates ──────────────────────────────────────────────────

    def update_item_metadata(self, item_id, item_data):
        """
        POST the full BaseItemDto back to Jellyfin to save changes.

        IMPORTANT API QUIRKS (discovered empirically):
        - OriginalTitle must be set to "" (empty string), never None.
        - LockedFields only accepts "Name" and "Overview" safely.
          Adding "OriginalTitle" or "IndexNumber" causes 400 Bad Request.
        - You must send the ENTIRE item object back, not a partial patch.
        """
        resp = requests.post(
            f"{self.base_url}/Items/{item_id}",
            headers=self.headers,
            json=item_data,
            timeout=15,
        )
        resp.raise_for_status()
        return True

    # ── Library Management ────────────────────────────────────────────

    def refresh_library(self):
        """Trigger a full library scan. Required after metadata injections."""
        resp = requests.post(
            f"{self.base_url}/Library/Refresh",
            headers={"X-Emby-Token": self.api_key},
            timeout=15,
        )
        resp.raise_for_status()
        return True

    # ── Image Management ──────────────────────────────────────────────

    def upload_image(self, item_id, image_url, image_type="Primary"):
        """
        Tell Jellyfin to download and set a remote image.

        Uses the /RemoteImages/Download endpoint which delegates the actual
        HTTP download to the server. Never upload raw binary from the agent.
        """
        resp = requests.post(
            f"{self.base_url}/Items/{item_id}/RemoteImages/Download",
            headers={"X-Emby-Token": self.api_key, "accept": "application/json"},
            params={"type": image_type, "imageUrl": image_url},
            timeout=30,
        )
        resp.raise_for_status()
        return True
