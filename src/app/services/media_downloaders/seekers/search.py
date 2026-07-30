import asyncio
import time
from functools import partial
from typing import Dict, List, Any, Optional

from shazamio import Shazam
from ytmusicapi import YTMusic
from yt_dlp import YoutubeDL

from src.app.utils.enums.error import DownloadError

_API_CACHE: Dict[str, tuple] = {}
CACHE_TTL_SECONDS = 60 * 60

_NEGATIVE_CACHE: Dict[str, float] = {}
NEGATIVE_CACHE_TTL = 60

# YTMusic instance — reused across calls (no auth needed for search)
_ytmusic = YTMusic()


class YouTubeSearcher:

    def __init__(self, shazam: Optional[Shazam] = None):
        self.shazam = shazam or Shazam()

    # ── Cache helpers ─────────────────────────────────────────────────

    def cache_get(self, key: str):
        rec = _API_CACHE.get(key)
        if not rec:
            return None
        ts, value = rec
        if time.time() - ts > CACHE_TTL_SECONDS:
            _API_CACHE.pop(key, None)
            return None
        return value

    def cache_set(self, key: str, value):
        _API_CACHE[key] = (time.time(), value)

    def _check_negative(self, key: str) -> bool:
        ts = _NEGATIVE_CACHE.get(key)
        return ts is not None and time.time() - ts < NEGATIVE_CACHE_TTL

    def _set_negative(self, key: str) -> None:
        _NEGATIVE_CACHE[key] = time.time()

    # ── Media info ────────────────────────────────────────────────────

    async def get_media_info(self, video_url: str) -> Optional[Dict[str, Any]]:
        cache_key = f"media_info:{video_url}"
        cached = self.cache_get(cache_key)
        if cached is not None:
            return cached

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

            result = await asyncio.to_thread(extract_info)
            if result is not None:
                self.cache_set(cache_key, result)
            return result

        except Exception as e:
            print("ERROR get_media_info:", e)
            return None

    # ── Music search (YTMusic — faster than yt-dlp ytsearch) ─────────

    async def search_music(
        self,
        query: str,
        max_count: int = 10,
    ) -> tuple[List[Dict[str, Any]], Any, List[str]]:
        """
        Search YouTube Music via ytmusicapi.
        Falls back to yt-dlp ytsearch if ytmusicapi fails.
        Returns (results, raw_entries, errors).
        """
        loop = asyncio.get_running_loop()

        try:
            raw = await loop.run_in_executor(
                None, partial(_ytmusic.search, query, "songs", None, max_count)
            )
        except Exception as e:
            print("ERROR YTMusic search, falling back to yt-dlp:", e)
            return await self._search_music_ytdlp(query, max_count)

        if not raw:
            return [], [], [DownloadError.MUSIC_NOT_FOUND]

        results = []
        for entry in raw:
            video_id = entry.get("videoId")
            if not video_id:
                continue
            duration_sec = entry.get("duration_seconds") or 0
            if duration_sec > 700:  # skip tracks > ~11 min
                continue
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            results.append({
                "title": entry.get("title", ""),
                "id": video_id,
                "duration": f"{minutes}:{seconds:02d}" if duration_sec else None,
                "filesize_mb": None,
            })

        return results, raw, []

    async def _search_music_ytdlp(
        self, query: str, max_count: int
    ) -> tuple[List[Dict[str, Any]], Any, List[str]]:
        """Fallback search using yt-dlp ytsearch."""

        def extract_search():
            ydl_opts = {"quiet": True, "skip_download": True, "extract_flat": True}
            results = []
            errors = []
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    data = ydl.extract_info(f"ytsearch{max_count}:{query}", download=False)
                if not data:
                    return [], [], [DownloadError.MUSIC_NOT_FOUND]
                for entry in data.get("entries", []):
                    if not entry:
                        continue
                    duration = entry.get("duration") or 0
                    results.append({
                        "title": entry.get("title", ""),
                        "id": entry.get("id", ""),
                        "duration": f"{int(duration) // 60}:{int(duration) % 60:02d}" if duration else None,
                        "filesize_mb": None,
                    })
                return results, data.get("entries", []), errors
            except Exception as e:
                print("ERROR _search_music_ytdlp:", e)
                return [], [], [str(e)]

        return await asyncio.to_thread(extract_search)

    # ── Shazam top charts ─────────────────────────────────────────────

    def _parse_tracks(self, raw: dict) -> List[Dict[str, str]]:
        result: List[Dict[str, str]] = []
        for track in raw.get("tracks", []):
            title = track.get("title") or ""
            subtitle = track.get("subtitle") or ""
            result.append({"artist": subtitle, "title": title})
        return result

    async def get_top_music(self, limit: int = 50) -> List[Dict[str, str]]:
        cache_key = f"shazam:world:{limit}"
        cached = self.cache_get(cache_key)
        if cached is not None:
            return cached
        if self._check_negative(cache_key):
            raise RuntimeError("Shazam temporarily unavailable (negative cache)")
        try:
            raw = await self.shazam.top_world_tracks(limit=limit)
        except Exception as e:
            self._set_negative(cache_key)
            print("ERROR get_top_music:", e)
            raise
        result = self._parse_tracks(raw)
        self.cache_set(cache_key, result)
        return result

    async def get_top_by_region(self, region_code: str, limit: int = 50) -> List[Dict[str, str]]:
        key = region_code.upper()
        cache_key = f"shazam:{key}:{limit}"
        cached = self.cache_get(cache_key)
        if cached is not None:
            return cached
        if self._check_negative(cache_key):
            raise RuntimeError("Shazam temporarily unavailable (negative cache)")
        try:
            raw = await self.shazam.top_country_tracks(key, limit)
        except Exception as e:
            self._set_negative(cache_key)
            print("ERROR get_top_by_region:", e)
            raise
        result = self._parse_tracks(raw)
        self.cache_set(cache_key, result)
        return result
