import asyncio
import json
import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from shazamio import Shazam
from yt_dlp import YoutubeDL

from src.app.services.media_downloaders.utils.files import get_audio_file_name

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# aria2c
# ---------------------------------------------------------------------------
_ARIA2C_AVAILABLE = shutil.which("aria2c") is not None

_ARIA2C_OPTS = {
    "external_downloader": "aria2c",
    "external_downloader_args": {
        "aria2c": [
            "--max-connection-per-server=16",
            "--split=16",
            "--min-split-size=1M",
            "--max-concurrent-downloads=1",
            "--quiet=true",
        ]
    },
}

# ---------------------------------------------------------------------------
# Semaphore — max N simultaneous YouTube downloads to avoid IP ban/throttle.
# 3-5 is a safe range for a single VPS; raise only if you have proxy rotation.
# ---------------------------------------------------------------------------
_DOWNLOAD_SEMAPHORE = asyncio.Semaphore(4)

# ---------------------------------------------------------------------------
# Dedicated thread-pool for yt-dlp blocking calls.
# Default ThreadPoolExecutor uses min(32, cpu+4) threads — fine for light load,
# but under heavy traffic it becomes a bottleneck.  Set explicitly.
# ---------------------------------------------------------------------------
_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="ytdlp")

# ---------------------------------------------------------------------------
# Simple in-process cache: video_id -> (file_path, title)
# Replace with Redis/Postgres for multi-process / persistent caching.
#
# Redis example:
#   cached = await redis.get(f"track:{video_id}")
#   if cached:
#       return json.loads(cached)   # (file_path, title) or (file_id, title)
# ---------------------------------------------------------------------------
_TRACK_CACHE: dict[str, tuple[str, str]] = {}


class MusicDownloader:
    def __init__(self) -> None:
        self.shazam = Shazam()

    async def find_song_name_by_video_audio_voice_video_note(self, media_path: str) -> str:
        """Recognise a track via Shazam and return "Title Artist" string."""
        try:
            out = await self.shazam.recognize(media_path)
            track = out.get("track", {})
            title = track.get("title", "")
            subtitle = track.get("subtitle", "")
            return f"{title} {subtitle}".strip()
        except Exception:
            logger.exception("Shazam recognition failed for %s", media_path)
            return ""

    async def download_music_from_youtube(
        self, video_id: str
    ) -> Optional[tuple[str, str]]:
        """Download audio from YouTube and return (file_path, title).

        Optimisations applied
        ─────────────────────
        1. In-process cache keyed by video_id — zero I/O for repeated requests.
        2. asyncio.Semaphore(4) — limits concurrent YT connections to avoid ban.
        3. noplaylist: True — skip playlist parsing on accidental playlist URLs.
        4. format priority: 251 (webm/opus) → bestaudio — removes format scan
           round-trip for the common android-client case.
        5. ios fallback — if android fails, retry with ios client (better direct
           URLs in some regions / less throttling).
        6. Explicit ThreadPoolExecutor — predictable thread budget under load.
        """
        # ── 1. Cache hit ────────────────────────────────────────────────────
        if video_id in _TRACK_CACHE:
            logger.debug("Cache hit for video_id=%s", video_id)
            return _TRACK_CACHE[video_id]

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        music_output_path = f"./media/audios/{get_audio_file_name()}"

        def _make_opts(player_client: str) -> dict:
            opts: dict = {
                "extractor_args": {
                    "youtube": {
                        "player_client": [player_client],
                    }
                },
                # Try format 251 (webm/opus) first — android client almost
                # always exposes it, skipping the full format-list scan.
                # Falls back to bestaudio/best if 251 is unavailable.
                "format": "251/bestaudio/best",
                "noplaylist": True,          # never expand playlist URLs
                "outtmpl": music_output_path + ".%(ext)s",
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 15,
                "writethumbnail": False,
                "writesubtitles": False,
                "writeautomaticsub": False,
            }
            if _ARIA2C_AVAILABLE:
                opts.update(_ARIA2C_OPTS)
            else:
                opts["concurrent_fragment_downloads"] = 5
            return opts

        def _download_sync(player_client: str) -> Optional[dict]:
            with YoutubeDL(_make_opts(player_client)) as ydl:
                return ydl.extract_info(video_url, download=True)

        # ── 2. Semaphore guards concurrent download count ───────────────────
        async with _DOWNLOAD_SEMAPHORE:
            info: Optional[dict] = None

            # ── 4 & 5. Try android first, fall back to ios ──────────────────
            for client in ("android", "ios"):
                try:
                    info = await asyncio.get_event_loop().run_in_executor(
                        _EXECUTOR, _download_sync, client
                    )
                    if info:
                        break
                except Exception:
                    logger.warning(
                        "yt-dlp failed with client=%s for %s, trying next",
                        client,
                        video_id,
                    )

        if not info:
            logger.error("All yt-dlp clients failed for video_id=%s", video_id)
            return None

        entry = info["entries"][0] if "entries" in info else info
        title: str = entry.get("title", "")
        ext: str = entry.get("ext", "webm")

        final_path = f"{music_output_path}.{ext}"

        if not os.path.exists(final_path):
            for candidate_ext in ("webm", "m4a", "opus", "ogg", "mp3"):
                candidate = f"{music_output_path}.{candidate_ext}"
                if os.path.exists(candidate):
                    final_path = candidate
                    break

        if not os.path.exists(final_path):
            logger.error("Downloaded file not found at %s", final_path)
            return None

        result = (final_path, title)

        # ── 1. Populate cache ────────────────────────────────────────────────
        # TODO: replace with Redis for persistent/multi-process caching:
        #   await redis.set(f"track:{video_id}", json.dumps(result))
        _TRACK_CACHE[video_id] = result
        logger.debug("Cached video_id=%s -> %s", video_id, final_path)

        return result
