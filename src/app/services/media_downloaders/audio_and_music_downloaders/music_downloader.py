import asyncio
import os
import time
from functools import partial
from typing import Optional

from shazamio import Shazam
from yt_dlp import YoutubeDL

from src.app.services.media_downloaders.seekers.search import is_topic_channel
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


def _is_drm_error(e: Exception) -> bool:
    msg = str(e).lower()
    return "drm" in msg or "drm protected" in msg


def _build_ydl_opts(output_path: str) -> dict:
    """
    yt-dlp options for speed and broad compatibility.

    Format strategy:
    - bestaudio: always available, yt-dlp picks best audio-only stream
      (webm/opus where available, m4a/mp4a otherwise)
    - No format codes like "251" — those are codec-specific and absent on
      many regional / older uploads (causes "Requested format not available")
    - No FFmpeg postprocessor — file served as-is, saves 2-5s per track

    Player clients: web + android avoid DRM-heavy tv/ios clients.
    """
    import shutil
    opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 15,
        "concurrent_fragment_downloads": 5,
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "android"],
            }
        },
        # No postprocessors — skip FFmpeg conversion entirely
    }
    if shutil.which("aria2c"):
        opts["external_downloader"] = "aria2c"
        opts["external_downloader_args"] = ["-x", "8", "-s", "8", "-k", "1M"]
    return opts


def _resolve_path(base: str) -> Optional[str]:
    """Return the actual downloaded file (no FFmpeg, native container)."""
    for suffix in ("", ".webm", ".m4a", ".mp4", ".mp3", ".opus", ".ogg"):
        candidate = base + suffix
        if os.path.exists(candidate):
            return candidate
    return None


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
        """
        Download audio for a single video_id.
        Returns None on DRM or any error so the caller can try the next result.
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        music_output_path = f"./media/audios/{get_audio_file_name()}"
        ydl_opts = _build_ydl_opts(music_output_path)

        loop = asyncio.get_running_loop()

        def _download_sync() -> dict:
            with YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(video_url, download=True)

        try:
            info = await loop.run_in_executor(None, partial(_download_sync))
        except Exception as e:
            if _is_drm_error(e):
                print(f"DRM skip {video_id}: {e}")
                return None
            print("ERROR in YouTube download:", e)
            return None

        if not info:
            return None

        title = (
            info["entries"][0]["title"]
            if "entries" in info
            else info.get("title", "")
        )

        final_path = _resolve_path(music_output_path)
        if not final_path:
            return None

        return final_path, title

    async def download_music_by_query(
        self, query: str, skip_ids: list[str] | None = None
    ) -> Optional[tuple[str, str]]:
        """
        DRM fallback: flat ytsearch → filter out Topic channels and known bad IDs
        → try each candidate until one downloads successfully.
        """
        skip_set = set(skip_ids or [])
        loop = asyncio.get_running_loop()

        def _flat_search() -> list[tuple[str, str]]:
            opts = {
                "quiet": True,
                "skip_download": True,
                "extract_flat": True,
                "noplaylist": True,
            }
            try:
                with YoutubeDL(opts) as ydl:
                    data = ydl.extract_info(f"ytsearch20:{query}", download=False)
                if not data:
                    return []
                results = []
                for e in data.get("entries", []):
                    if not e or not e.get("id"):
                        continue
                    vid = e["id"]
                    if vid in skip_set:
                        continue
                    uploader = e.get("uploader") or e.get("channel") or ""
                    if is_topic_channel(uploader):
                        print(f"fallback: skipping Topic channel {uploader!r} ({vid})")
                        continue
                    results.append((vid, uploader))
                return results
            except Exception as ex:
                print("ERROR flat search:", ex)
                return []

        candidates = await loop.run_in_executor(None, _flat_search)
        if not candidates:
            return None

        for vid, uploader in candidates:
            result = await self.download_music_from_youtube(vid)
            if result:
                return result

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
