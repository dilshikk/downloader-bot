import asyncio
import time
from typing import Dict, List, Any, Optional

from shazamio import Shazam
from yt_dlp import YoutubeDL

from src.app.utils.enums.error import DownloadError

_API_CACHE: Dict[str, tuple] = {}
CACHE_TTL_SECONDS = 60 * 60

# Negative cache: не бить повторно при даунтайме Shazam
_NEGATIVE_CACHE: Dict[str, float] = {}
NEGATIVE_CACHE_TTL = 60


class YouTubeSearcher:

    def __init__(self, shazam: Optional[Shazam] = None):
        # Переиспользуем инстанс — не плодим лишних HTTP-сессий
        self.shazam = shazam or Shazam()

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
            print("ERROR", e)
            return None

    async def search_music(
        self,
        query: str,
        max_count: int = 5,
    ) -> tuple[List[Dict[str, Any]], Any, List[str]]:

        def extract_search():
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "extract_flat": True,
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

                entries = data.get("entries", [])
                for entry in entries:
                    if not entry:
                        continue
                    duration = entry.get("duration") or 0
                    results.append({
                        "title": entry.get("title", ""),
                        "id": entry.get("id", ""),
                        "duration": f"{int(duration) // 60}:{int(duration) % 60:02d}" if duration else None,
                        "filesize_mb": None,
                    })
                return results, entries, errors

            except Exception as e:
                print("ERROR search_music:", e)
                return [], [], [str(e)]

        return await asyncio.to_thread(extract_search)

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

    def _check_negative(self, cache_key: str) -> bool:
        ts = _NEGATIVE_CACHE.get(cache_key)
        return ts is not None and time.time() - ts < NEGATIVE_CACHE_TTL

    def _set_negative(self, cache_key: str) -> None:
        _NEGATIVE_CACHE[cache_key] = time.time()

    def _parse_tracks(self, raw: dict) -> List[Dict[str, str]]:
        result: List[Dict[str, str]] = []
        for track in raw.get("tracks", []):
            title = track.get("title") or ""
            subtitle = track.get("subtitle") or ""  # subtitle = артист в Shazam
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
        # region_code — ISO 3166-1 alpha-2, например "UZ", "RU", "GB"
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
