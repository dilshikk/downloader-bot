import asyncio
import os
import shutil
from typing import Optional

from shazamio import Shazam
from yt_dlp import YoutubeDL

from src.app.services.media_downloaders.utils.files import get_audio_file_name

# Use aria2c as external downloader if available — opens 16 parallel connections
# Install on VPS: apt install aria2 -y
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


class MusicDownloader:
    def __init__(self):
        self.shazam = Shazam()

    async def find_song_name_by_video_audio_voice_video_note(self, media_path: str) -> str:
        try:
            out = await self.shazam.recognize(media_path)
            track = out.get("track", {})
            title = track.get("title", "")
            subtitle = track.get("subtitle", "")
            music_title = f"{title} {subtitle}".strip()
            return music_title
        except Exception as e:
            print("ERROR in Shazam recognize:", e)
            return ""

    async def download_music_from_youtube(self, video_id: str) -> Optional[tuple[str, str]]:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        music_output_path = f"./media/audios/{get_audio_file_name()}"

        yt_dlp_opts: dict = {
            # android client bypasses bot-detection; don't restrict by ext —
            # android returns webm/opus, not m4a, so just take bestaudio
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"],
                }
            },
            "format": "bestaudio/best",
            "outtmpl": music_output_path + ".%(ext)s",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 15,
            "writethumbnail": False,
            "writesubtitles": False,
            "writeautomaticsub": False,
            # No postprocessors — skip FFmpeg re-encoding entirely
        }

        if _ARIA2C_AVAILABLE:
            yt_dlp_opts.update(_ARIA2C_OPTS)
        else:
            yt_dlp_opts["concurrent_fragment_downloads"] = 5

        def download_sync():
            with YoutubeDL(yt_dlp_opts) as ydl:
                return ydl.extract_info(video_url, download=True)

        try:
            info = await asyncio.to_thread(download_sync)

            if not info:
                return None

            title = info["entries"][0]["title"] if "entries" in info else info.get("title", "")
            ext = info["entries"][0].get("ext", "webm") if "entries" in info else info.get("ext", "webm")

            final_path = f"{music_output_path}.{ext}"

            if not os.path.exists(final_path):
                for candidate_ext in ("webm", "m4a", "opus", "ogg", "mp3"):
                    candidate = f"{music_output_path}.{candidate_ext}"
                    if os.path.exists(candidate):
                        final_path = candidate
                        break

            if not os.path.exists(final_path):
                return None

            return final_path, title
        except Exception as e:
            print("ERROR in YouTube download:", e)
            return None
