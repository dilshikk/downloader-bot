import asyncio
import time
from typing import Dict, List, Any, Optional

import aiohttp
from yt_dlp import YoutubeDL

from src.app.core.config import Settings
from src.app.utils.enums.error import DownloadError

LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"

_API_CACHE: Dict[str, tuple] = {}
CACHE_TTL_BY_PERIOD: Dict[str, int] = {
    "today": 60 * 60,       # 1 hour — freshest
    "week": 60 * 60 * 6,    # 6 hours
    "month": 60 * 60 * 24,  # 24 hours
}

REGION_LASTFM_COUNTRY: Dict[str, Optional[str]] = {
    "global": None,
    "russia": "russia",
    "uzbekistan": "uzbekistan",
    "english": "united states",
}

MAX_TRACKS_PER_ARTIST = 3

class YouTubeSearcher:

    def __init__(self):
        self.settings = Settings()

    async def get_media_info(self, video_url: str) -> Optional[Dict[str, Any]]:
        try:
            def extract_info():
                with YoutubeDL({"quiet": True}) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    if "entries" in info:
                        info = info["entries"][0]

                    filesize = info.get("filesize") or info.get("filesize_approx")
                    return {
                        "title": info.get("title"),
                        "duration": info.get("duration"),
                        "filesize_mb": round(filesize / (1024 * 1024), 2) if filesize else None,
                    }

            return await asyncio.to_thread(extract_info)

        except Exception as e:
            print("ERROR", e)
            return None

    async def search_music(
        self,
        query: str,
        max_count: int = 5
    ):
        """Fast YouTube search using extract_flat for speed.

        Returns (results_list, entries_list, errors_list).
        Uses extract_flat=True to avoid fetching full video info — ~10x faster.
        """
        def extract_search():
            ydl_opts = {
                "quiet": True,
                # Use True instead of "in_playlist" — compatible with all yt-dlp versions
                # and required for ytsearch: scheme to be handled by yt-dlp's own extractor
                "extract_flat": True,
                "skip_download": True,
                "socket_timeout": 10,
            }

            search_query = f"ytsearch{max_count}:{query}"
            results = []
            errors = []

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    data = ydl.extract_info(search_query, download=False)

                    if not data:
                        errors.append(DownloadError.MUSIC_NOT_FOUND)
                        return [], [], errors

                    entries = data.get("entries", []) or []

                    for entry in entries:
                        if not entry:
                            continue
                        duration_secs = entry.get("duration") or 0
                        # Skip if longer than 10 minutes
                        if duration_secs > 600:
                            continue
                        duration_str = f"{duration_secs // 60}:{duration_secs % 60:02d}" if duration_secs else None
                        results.append({
                            "title": entry.get("title", ""),
                            "id": entry.get("id", entry.get("url", "")),
                            "duration": duration_str,
                            "filesize_mb": None,
                            "thumbnail": entry.get("thumbnail") or entry.get("thumbnails", [{}])[0].get("url", "") if entry.get("thumbnails") else "",
                        })

                    if not results:
                        errors.append(DownloadError.MUSIC_NOT_FOUND)

                    return results, entries, errors

            except Exception as e:
                print("ERROR search_music:", e)
                return [], [], [str(e)]

        return await asyncio.to_thread(extract_search)

    def cache_get(self, key: str, ttl: int):
        rec = _API_CACHE.get(key)
        if not rec:
            return None
        ts, value = rec
        if time.time() - ts > ttl:
            _API_CACHE.pop(key, None)
            return None
        return value

    def cache_set(self, key: str, value):
        _API_CACHE[key] = (time.time(), value)

    @staticmethod
    def _deduplicate_artists(tracks: List[Dict[str, str]], max_per_artist: int = MAX_TRACKS_PER_ARTIST) -> List[Dict[str, str]]:
        """Limit tracks per artist to ensure diversity."""
        artist_count: Dict[str, int] = {}
        result = []
        for t in tracks:
            artist = t.get("artist", "").lower().strip()
            if not artist:
                result.append(t)
                continue
            count = artist_count.get(artist, 0)
            if count < max_per_artist:
                result.append(t)
                artist_count[artist] = count + 1
        return result

    # ------------------------------------------------------------------ #
    # Legacy helper kept for backward compat (used by old /top handler)  #
    # ------------------------------------------------------------------ #
    async def get_top_music(self, limit: int = 50) -> List[Dict[str, str]]:
        return await self.get_top_by_region_period("global", "today", limit)

    # ------------------------------------------------------------------ #
    # Main method: region + period aware top chart (Last.fm only)        #
    # ------------------------------------------------------------------ #
    async def get_top_by_region_period(
        self,
        region: str = "global",
        period: str = "today",
        limit: int = 50,
    ) -> List[Dict[str, str]]:
        cache_key = f"lastfm:{region}:{period}:{limit}"
        ttl = CACHE_TTL_BY_PERIOD.get(period, 3600)
        cached = self.cache_get(cache_key, ttl)
        if cached is not None:
            return cached

        country = REGION_LASTFM_COUNTRY.get(region)

        if country is None:
            # Global chart
            params = {
                "method": "chart.gettoptracks",
                "api_key": self.settings.lastfm_api_key,
                "format": "json",
                "limit": limit,
            }
        else:
            params = {
                "method": "geo.gettoptracks",
                "country": country,
                "api_key": self.settings.lastfm_api_key,
                "format": "json",
                "limit": limit,
            }

        result: List[Dict[str, str]] = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(LASTFM_API_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()

                    tracks_data = data.get("tracks", {}).get("track", []) or []
                    for t in tracks_data:
                        artist_obj = t.get("artist")
                        artist = artist_obj.get("name") if isinstance(artist_obj, dict) else (artist_obj or "")
                        title = t.get("name") or ""
                        result.append({"artist": artist, "title": title})

        except Exception as e:
            print("ERROR get_top_by_region_period:", e)
            return []

        # Deduplicate — max 3 tracks per artist
        result = self._deduplicate_artists(result)

        # Fallback: if regional chart returned nothing, use global
        if not result and country is not None:
            result = await self.get_top_by_region_period("global", period, limit)

        if result:
            self.cache_set(cache_key, result)
        return result
