import asyncio
import os
import time
from typing import Optional

from shazamio import Shazam
from yt_dlp import YoutubeDL

from src.app.services.media_downloaders.utils.files import get_audio_file_name

# ── In-process prefetch store ──────────────────────────────────────────
# Stores already-downloaded (file_path, title) keyed by YouTube video_id.
# Consumed on first click → file is sent instantly instead of re-downloading.
# TODO: replace with Redis + shared filesystem for multi-process deployments.

_prefetch_results: dict[str, tuple[str, str]] = {}
_prefetch_tasks:   dict[str, asyncio.Task] = {}       # type: ignore[type-arg]
_prefetch_ts:      dict[str, float] = {}

_PREFETCH_TTL = 300  # seconds; stale files are deleted automatically


def _cleanup_stale() -> None:
    """Remove prefetch entries older than TTL and delete their files."""
    now = time.time()
    stale = [vid for vid, ts in _prefetch_ts.items() if now - ts > _PREFETCH_TTL]
    for vid in stale:
        result = _prefetch_results.pop(vid, None)
        _prefetch_tasks.pop(vid, None)
        _prefetch_ts.pop(vid, None)
        if result:
            path, _ = result
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass


class MusicDownloader:
    def __init__(self) -> None:
        self.shazam = Shazam()

    # ── Shazam ────────────────────────────────────────────────────────

    async def find_song_name_by_video_audio_voice_video_note(
        self, media_path: str
    ) -> str:
        try:
            out = await self.shazam.recognize(media_path)
            track = out.get("track", {})
            title = track.get("title", "")
            subtitle = track.get("subtitle", "")
            return f"{title} {subtitle}".strip()
        except Exception as e:
            print("ERROR in Shazam recognize:", e)
            return ""

    # ── Core download ─────────────────────────────────────────────────

    async def download_music_from_youtube(
        self, video_id: str
    ) -> Optional[tuple[str, str]]:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        music_output_path = f"./media/audios/{get_audio_file_name()}"
        yt_dlp_opts = {
            "format": "251/bestaudio/best",
            "outtmpl": music_output_path,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 15,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

        def _download_sync() -> dict:
            with YoutubeDL(yt_dlp_opts) as ydl:
                return ydl.extract_info(video_url, download=True)

        try:
            info = await asyncio.to_thread(_download_sync)
            if not info:
                return None

            title = (
                info["entries"][0]["title"]
                if "entries" in info
                else info.get("title", "")
            )

            # yt-dlp + FFmpegExtractAudio appends .mp3
            final_path = music_output_path + ".mp3"
            if not os.path.exists(final_path):
                if os.path.exists(music_output_path):
                    final_path = music_output_path
                else:
                    for ext in (".m4a", ".webm", ".opus", ".ogg"):
                        candidate = music_output_path + ext
                        if os.path.exists(candidate):
                            final_path = candidate
                            break

            return final_path, title
        except Exception as e:
            print("ERROR in YouTube download:", e)
            return None

    # ── Prefetch helpers ──────────────────────────────────────────────

    async def _prefetch_worker(self, video_id: str) -> None:
        try:
            result = await self.download_music_from_youtube(video_id)
            if result:
                _prefetch_results[video_id] = result
                _prefetch_ts[video_id] = time.time()
        except Exception:
            pass
        finally:
            _prefetch_tasks.pop(video_id, None)

    def prefetch(self, video_id: str) -> None:
        """Fire-and-forget: start downloading video_id in background."""
        _cleanup_stale()
        if video_id in _prefetch_results or video_id in _prefetch_tasks:
            return
        task = asyncio.create_task(self._prefetch_worker(video_id))
        _prefetch_tasks[video_id] = task

    def consume_prefetch(self, video_id: str) -> Optional[tuple[str, str]]:
        """Pop and return a completed prefetch result (or None)."""
        result = _prefetch_results.pop(video_id, None)
        _prefetch_ts.pop(video_id, None)
        return result

    async def wait_and_consume(
        self, video_id: str, timeout: float = 30.0
    ) -> Optional[tuple[str, str]]:
        """
        1. Already done  → return instantly.
        2. Still running → wait up to `timeout` seconds, then return.
        3. Not started   → return None (caller should download normally).
        """
        if video_id in _prefetch_results:
            return self.consume_prefetch(video_id)

        task = _prefetch_tasks.get(video_id)
        if task is None:
            return None

        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        except (asyncio.TimeoutError, Exception):
            pass

        return self.consume_prefetch(video_id)
