import asyncio
import time
from typing import Dict, List, Any, Optional

import aiohttp
from yt_dlp import YoutubeDL

from src.app.core.config import Settings
from src.app.utils.enums.error import DownloadError

LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"

_API_CACHE: Dict[str, tuple] = {}
CACHE_TTL_SECONDS = 60 * 60

# Negative cache: при ошибке API не бить повторно 60 сек
_NEGATIVE_CACHE: Dict[str, float] = {}
NEGATIVE_CACHE_TTL = 60


class YouTubeSearcher:

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.settings = Settings()
        self._session = session
        self._owns_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

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

    async def _fetch_top_tracks(
        self,
        method: str,
        cache_key: str,
        extra_params: Optional[Dict[str, Any]] = None,
        limit: int = 50,
    ) -> List[Dict[str, str]]:
        cached = self.cache_get(cache_key)
        if cached is not None:
            return cached

        # Negative cache: если недавно была ошибка — не бьём API снова
        neg_ts = _NEGATIVE_CACHE.get(cache_key)
        if neg_ts and time.time() - neg_ts < NEGATIVE_CACHE_TTL:
            raise RuntimeError("Last.fm temporarily unavailable (negative cache)")

        params = {
            "method": method,
            "api_key": self.settings.lastfm_api_key,
            "format": "json",
            "limit": limit,
        }
        if extra_params:
            params.update(extra_params)

        try:
            session = await self._get_session()
            async with session.get(LASTFM_API_URL, params=params, timeout=15) as resp:
                if resp.status != 200:
                    _NEGATIVE_CACHE[cache_key] = time.time()
                    raise RuntimeError(f"Last.fm HTTP {resp.status}")
                data = await resp.json()
        except RuntimeError:
            raise
        except Exception as e:
            _NEGATIVE_CACHE[cache_key] = time.time()
            print("ERROR _fetch_top_tracks:", e)
            raise

        tracks = data.get("tracks", {}).get("track", []) or []
        result: List[Dict[str, str]] = []
        for t in tracks:
            artist_obj = t.get("artist")
            artist = artist_obj.get("name") if isinstance(artist_obj, dict) else (artist_obj or "")
            title = t.get("name") or ""
            result.append({"artist": artist, "title": title})

        self.cache_set(cache_key, result)
        return result

    async def get_top_music(self, limit: int = 50) -> List[Dict[str, str]]:
        cache_key = f"lastfm:global:{limit}"
        return await self._fetch_top_tracks(
            method="chart.gettoptracks",
            cache_key=cache_key,
            limit=limit,
        )

    async def get_top_by_region(self, region: str, limit: int = 50) -> List[Dict[str, str]]:
        cache_key = f"lastfm:{region}:{limit}"
        return await self._fetch_top_tracks(
            method="geo.gettoptracks",
            cache_key=cache_key,
            extra_params={"country": region},
            limit=limit,
        )
