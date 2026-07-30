import asyncio
import os
from typing import Optional

from shazamio import Shazam
from yt_dlp import YoutubeDL

from src.app.services.media_downloaders.utils.files import get_audio_file_name


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

        # Download best audio without re-encoding — much faster than FFmpeg mp3 conversion.
        # Telegram accepts m4a/opus natively so no conversion is needed.
        yt_dlp_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
            "outtmpl": music_output_path + ".%(ext)s",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 15,
            # No postprocessors — skip FFmpeg re-encoding entirely
        }

        def download_sync():
            with YoutubeDL(yt_dlp_opts) as ydl:
                return ydl.extract_info(video_url, download=True)

        try:
            info = await asyncio.to_thread(download_sync)

            if not info:
                return None

            title = info["entries"][0]["title"] if "entries" in info else info.get("title", "")
            ext = info["entries"][0].get("ext", "m4a") if "entries" in info else info.get("ext", "m4a")

            final_path = f"{music_output_path}.{ext}"

            # Fallback: scan for any matching file if ext guess is wrong
            if not os.path.exists(final_path):
                for candidate_ext in ("m4a", "webm", "opus", "ogg", "mp3"):
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
