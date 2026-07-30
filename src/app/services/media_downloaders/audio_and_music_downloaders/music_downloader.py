import asyncio
import os
import time
from functools import partial
from typing import Optional

from shazamio import Shazam
from yt_dlp import YoutubeDL

from src.app.services.media_downloaders.utils.files import get_audio_file_name

# ── In-process prefetch store ──────────────────────────────────────────
_prefetch_results: dict[str, tuple[str, str]] = {}
_prefetch_tasks:   dict[str, asyncio.Task] = {}       # type: ignore[type-arg]
_prefetch_ts:      dict[str, float] = {}
_PREFETCH_TTL = 300


def _cleanup_stale() -> None:
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


def _build_ydl_opts(output_path: str) -> dict:
    """yt-dlp options optimised for speed:
    - TV player client: avoids web throttling
    - aria2c external downloader: 8 parallel connections per fragment
    - concurrent_fragment_downloads: 5 parallel fragments
    Falls back gracefully if aria2c is not installed.
    """
    opts: dict = {
        "format": "251/bestaudio/best",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 15,
        "concurrent_fragment_downloads": 5,
        "extractor_args": {"youtube": {"player_client": ["tv"]}},
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    # Use aria2c if available — gives 3-5x speedup on large files
    import shutil
    if shutil.which("aria2c"):
        opts["external_downloader"] = "aria2c"
        opts["external_downloader_args"] = ["-x", "8", "-s", "8", "-k", "1M"]

    return opts


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
        ydl_opts = _build_ydl_opts(music_output_path)

        loop = asyncio.get_running_loop()

        def _download_sync() -> dict:
            with YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(video_url, download=True)

        try:
            info = await loop.run_in_executor(None, partial(_download_sync))
            if not info:
                return None

            title = (
                info["entries"][0]["title"]
                if "entries" in info
                else info.get("title", "")
            )

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
        _cleanup_stale()
        if video_id in _prefetch_results or video_id in _prefetch_tasks:
            return
        task = asyncio.create_task(self._prefetch_worker(video_id))
        _prefetch_tasks[video_id] = task

    def consume_prefetch(self, video_id: str) -> Optional[tuple[str, str]]:
        result = _prefetch_results.pop(video_id, None)
        _prefetch_ts.pop(video_id, None)
        return result

    async def wait_and_consume(
        self, video_id: str, timeout: float = 30.0
    ) -> Optional[tuple[str, str]]:
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
