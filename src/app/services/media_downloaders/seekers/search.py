import asyncio
import time
from typing import Dict, List, Any, Optional

from shazamio import Shazam
from yt_dlp import YoutubeDL

from src.app.utils.enums.error import DownloadError

_API_CACHE: Dict[str, tuple] = {}
CACHE_TTL = 60 * 60

_NEG_CACHE: Dict[str, float] = {}
NEG_CACHE_TTL = 60


class YouTubeSearcher:

    def __init__(self, shazam: Optional[Shazam] = None):
        self.shazam = shazam or Shazam()

    # ── Cache ─────────────────────────────────────────────────────────

    def _cache_get(self, key: str):
        rec = _API_CACHE.get(key)
        if not rec:
            return None
        ts, val = rec
        if time.time() - ts > CACHE_TTL:
            _API_CACHE.pop(key, None)
            return None
        return val

    def _cache_set(self, key: str, val):
        _API_CACHE[key] = (time.time(), val)

    def _neg_ok(self, key: str) -> bool:
        ts = _NEG_CACHE.get(key)
        return ts is not None and time.time() - ts < NEG_CACHE_TTL

    def _neg_set(self, key: str):
        _NEG_CACHE[key] = time.time()

    # ── Media info ────────────────────────────────────────────────────

    async def get_media_info(self, video_url: str) -> Optional[Dict[str, Any]]:
        key = f"info:{video_url}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        try:
            def _run():
                with YoutubeDL({"quiet": True}) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    if "entries" in info:
                        info = info["entries"][0]
                    fs = info.get("filesize") or info.get("filesize_approx")
                    return {
                        "title": info.get("title"),
                        "duration": info.get("duration"),
                        "filesize_mb": round(fs / 1024 / 1024, 2) if fs else None,
                    }
            result = await asyncio.to_thread(_run)
            if result:
                self._cache_set(key, result)
            return result
        except Exception as e:
            print("ERROR get_media_info:", e)
            return None

    # ── Search ────────────────────────────────────────────────────────

    async def search_music(
        self,
        query: str,
        max_count: int = 10,
    ) -> tuple[List[Dict[str, Any]], Any, List[str]]:
        """
        Search via yt-dlp ytsearch (extract_flat — no download).
        Returns (results, raw_entries, errors).
        NOTE: filesize_mb is always None — do NOT filter on it.
        """
        if not query or not query.strip():
            return [], [], [DownloadError.MUSIC_NOT_FOUND]

        def _run():
            opts = {
                "quiet": True,
                "skip_download": True,
                "extract_flat": True,
                "noplaylist": True,
            }
            try:
                with YoutubeDL(opts) as ydl:
                    data = ydl.extract_info(f"ytsearch{max_count}:{query.strip()}", download=False)
                if not data:
                    return [], [], [DownloadError.MUSIC_NOT_FOUND]
                results = []
                for e in data.get("entries", []):
                    if not e:
                        continue
                    dur = e.get("duration") or 0
                    results.append({
                        "title": e.get("title", ""),
                        "id": e.get("id", ""),
                        "duration": f"{int(dur)//60}:{int(dur)%60:02d}" if dur else None,
                        "filesize_mb": None,
                    })
                return results, data.get("entries", []), []
            except Exception as ex:
                print("ERROR search_music:", ex)
                return [], [], [str(ex)]

        return await asyncio.to_thread(_run)

    # ── Shazam top charts ─────────────────────────────────────────────

    def _parse_tracks(self, raw: dict) -> List[Dict[str, str]]:
        return [
            {"artist": t.get("subtitle", ""), "title": t.get("title", "")}
            for t in raw.get("tracks", [])
        ]

    async def get_top_music(self, limit: int = 50) -> List[Dict[str, str]]:
        key = f"shazam:world:{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        if self._neg_ok(key):
            raise RuntimeError("Shazam temporarily unavailable")
        try:
            raw = await self.shazam.top_world_tracks(limit=limit)
        except Exception as e:
            self._neg_set(key)
            raise
        result = self._parse_tracks(raw)
        self._cache_set(key, result)
        return result

    async def get_top_by_region(self, region_code: str, limit: int = 50) -> List[Dict[str, str]]:
        iso = region_code.upper()
        key = f"shazam:{iso}:{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        if self._neg_ok(key):
            raise RuntimeError("Shazam temporarily unavailable")
        try:
            raw = await self.shazam.top_country_tracks(iso, limit)
        except Exception as e:
            self._neg_set(key)
            raise
        result = self._parse_tracks(raw)
        self._cache_set(key, result)
        return result
