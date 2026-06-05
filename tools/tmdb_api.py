"""
JellyInspector - TMDB API Client
=================================
Client for The Movie Database (TMDB) API v3.
Used to cross-reference series metadata, fetch episode groups,
and download poster artwork.

Usage:
    from tmdb_api import TMDBClient
    client = TMDBClient()  # reads TMDB_API_KEY from .env
"""

import os
import requests
from dotenv import load_dotenv


class TMDBClient:
    """
    Client for TMDB API v3.

    Reads TMDB_API_KEY from environment variables.
    """

    def __init__(self):
        load_dotenv()
        self.api_key = os.environ.get("TMDB_API_KEY", "")
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/original"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "accept": "application/json",
        }

    def search_tv(self, query):
        """Search for TV series by name."""
        resp = requests.get(
            f"{self.base_url}/search/tv",
            headers=self.headers,
            params={"query": query},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    def get_episode_groups(self, series_id):
        """Get available episode group definitions for a series."""
        resp = requests.get(
            f"{self.base_url}/tv/{series_id}/episode_groups",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    def get_episode_group_details(self, group_id):
        """Get the full episode list for a specific group."""
        resp = requests.get(
            f"{self.base_url}/tv/episode_group/{group_id}",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_episode_details(self, series_id, season_number, episode_number):
        """Get metadata for a single episode."""
        resp = requests.get(
            f"{self.base_url}/tv/{series_id}/season/{season_number}/episode/{episode_number}",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_poster_url(self, image_path):
        """Build a full-resolution poster URL from a TMDB image path."""
        if not image_path:
            return None
        return f"{self.image_base_url}{image_path}"
