import asyncio
import os.path
from typing import Optional, Union

from aiogram.types import Message

from src.app.services.media_downloaders.audio_and_music_downloaders.music_downloader import MusicDownloader
from src.app.services.media_downloaders.seekers.search import YouTubeSearcher
from src.app.services.media_downloaders.utils.audio import AudioUtils
from src.app.services.media_downloaders.utils.downlaod_media import download_media_in_internet
from src.app.services.media_downloaders.utils.files import (
    get_video_file_name, get_audio_file_name, get_photo_file_name
)
from src.app.services.media_downloaders.video_downloaders.instagram_downloader import InstagramDownloader
from src.app.services.media_downloaders.video_downloaders.tiktok_downloader import TikTokDownloader
from src.app.services.media_downloaders.video_downloaders.vk_downloader import VKDownloader
from src.app.services.media_downloaders.video_downloaders.youtube_downloader import YouTubeDownloader
from src.app.utils.enums.audio import MusicAction
from src.app.utils.enums.error import DownloadError
from src.app.utils.enums.general import MediaType
from src.app.utils.enums.video import InstagramMediaType
from src.app.utils.i18n import get_translator


def _clean_title(title: str) -> str:
    return " ".join(w for w in str(title).split() if not w.startswith("#") and not w.startswith("@"))


class AllDownloader:
    def __init__(self, message: Message = None, lang: str = None):
        self.message = message
        self.lang = lang
        self.instagram_downloader = InstagramDownloader()
        self.youtube_downloader = YouTubeDownloader()
        self.tiktok_downloader = TikTokDownloader()
        self.vk_downloader = VKDownloader()
        self.music_downloader = MusicDownloader()
        self.search = YouTubeSearcher()
        self.audio_utils = AudioUtils()
        self._ = get_translator(lang).gettext

    async def instagram_downloaders(
        self,
        url: str,
        media_type: InstagramMediaType,
    ) -> Optional[Union[str, list[dict]]]:
        errors = []
        file_path = None

        parsing_types = [InstagramMediaType.HIGHLIGHT, InstagramMediaType.STORIES]
        if media_type in parsing_types:
            file_path = await self.instagram_downloader.get_instagram_links_async(url)
        if media_type == InstagramMediaType.POST:
            file_path = await self.instagram_downloader.instagram_post_downloader(url)
        elif media_type == InstagramMediaType.REELS:
            file_path, errors = await self.instagram_downloader.instagram_reels_downloader(url)
        elif media_type == InstagramMediaType.PROFILE_PHOTO:
            file_path, errors = await self.instagram_downloader.instagram_profil_photo_downloader(url)

        if DownloadError.FILE_TOO_BIG in errors:
            if self.message:
                await self.message.answer(self._("File size bigger than 2GB"))
            return None
        if not file_path or DownloadError.DOWNLOAD_ERROR in errors:
            if self.message:
                await self.message.answer(self._("Error in loading file"))
            return None
        return file_path

    async def youtube_downloaders(self, url: str):
        file_path, errors = await self.youtube_downloader.youtube_video_and_shorts_downloader(url)
        if DownloadError.FILE_TOO_BIG in errors:
            await self.message.answer(self._("File size big to 2 gb"))
        elif DownloadError.DOWNLOAD_ERROR in errors:
            await self.message.answer(self._("Error in loading file"))
        return file_path

    async def tiktok_downloaders(self, url: str):
        file_path, errors = await self.tiktok_downloader.tiktok_video_downloader(url)
        if DownloadError.FILE_TOO_BIG in errors:
            await self.message.answer(self._("File size big to 2 gb"))
        elif DownloadError.DOWNLOAD_ERROR in errors:
            await self.message.answer(self._("Error in loading file"))
        return file_path

    async def vk_downloaders(self, url: str):
        file_path, errors = await self.vk_downloader.vk_video_downloader(url)
        if DownloadError.FILE_TOO_BIG in errors:
            await self.message.answer(self._("File size big to 2 gb"))
        elif DownloadError.DOWNLOAD_ERROR in errors:
            await self.message.answer(self._("Error in loading file"))
        return file_path

    async def _download_with_drm_fallback(
        self, video_id: str, title: str
    ) -> Optional[tuple[str, str]]:
        """Try video_id first. On DRM/error -> fallback to ytsearch by title."""
        result = await self.music_downloader.download_music_from_youtube(video_id)
        if result:
            return result
        print(f"Falling back to title search for: {title!r}")
        return await self.music_downloader.download_music_by_query(title, skip_ids=[video_id])

    async def music_downloaders(
        self,
        actions: MusicAction,
        media_type: MediaType = None,
        some_data: str = None,
    ):
        media_path = None
        thumbnail_path = None

        try:
            # ── SEARCH BY TEXT ────────────────────────────────────────────────
            if actions == MusicAction.SEARCH_BY_TEXT:
                musics_data, entries, errors = await self.search.search_music(some_data, 10)

                if not musics_data:
                    await self.message.answer(self._("Music not found"))
                    return [], "", None

                # Thumbnail from first raw entry
                for entry in (entries or []):
                    thumb = (
                        entry.get("thumbnail")
                        or (entry.get("thumbnails") or [{}])[0].get("url", "")
                    )
                    if thumb:
                        thumbnail_path = await download_media_in_internet(
                            thumb, get_photo_file_name(), MediaType.PHOTO
                        )
                    break

                # Filter and cap at 10 — scoring already sorted by quality
                musics_list = []
                for music_data in musics_data:
                    if not music_data.get("title"):
                        continue
                    dur_sec = music_data.get("duration_sec") or 0
                    if dur_sec and dur_sec > 600:
                        continue
                    musics_list.append(music_data)
                    if len(musics_list) >= 10:
                        break

                if not musics_list:
                    await self.message.answer(self._("Music not found"))
                    return [], "", None

                # Caption is now minimal — buttons show full track info
                q = (some_data or "").strip()
                display_q = q if len(q) <= 40 else q[:37] + "..."
                music_title = f"<b>{display_q}</b> — {len(musics_list)} ta natija"
                return musics_list, music_title, thumbnail_path

            # ── DOWNLOAD ──────────────────────────────────────────────────────
            if actions == MusicAction.DOWNLOAD:
                if "|||" in str(some_data):
                    video_id, track_title = some_data.split("|||", 1)
                else:
                    video_id = some_data
                    track_title = some_data

                result = await self._download_with_drm_fallback(video_id, track_title)
                if not result:
                    await self.message.answer(self._("Error in loading music"))
                    return None
                music_output_path, title = result
                if not music_output_path or not await asyncio.to_thread(os.path.exists, music_output_path):
                    await self.message.answer(self._("Error in loading music"))
                    return None
                return music_output_path, title

            # ── SEARCH BY MEDIA ───────────────────────────────────────────────
            if actions == MusicAction.SEARCH_BY_MEDIA:
                media_file_id = None
                if media_type == MediaType.VIDEO:
                    media_file_id = self.message.video.file_id
                    media_path = f"./media/videos/{get_video_file_name()}"
                elif media_type == MediaType.VIDEO_NOTE:
                    media_file_id = self.message.video_note.file_id
                    media_path = f"./media/videos/{get_video_file_name()}"
                elif media_type == MediaType.AUDIO:
                    media_file_id = self.message.audio.file_id
                    media_path = f"./media/audios/{get_audio_file_name()}"
                elif media_type == MediaType.VOICE:
                    media_file_id = self.message.voice.file_id
                    media_path = f"./media/audios/{get_audio_file_name()}"

                await self.message.bot.download(file=media_file_id, destination=media_path)

                if media_type in [MediaType.VOICE, MediaType.VIDEO_NOTE]:
                    audio_path = None
                    if media_type == MediaType.VIDEO_NOTE:
                        audio_path = f"./media/audios/{get_audio_file_name()}"
                        await asyncio.to_thread(
                            self.audio_utils.extract_audio_from_video, media_path, audio_path
                        )

                    music_texts = await asyncio.to_thread(
                        self.audio_utils.speech_to_text, audio_path or media_path, some_data
                    )

                    musics_data, entries, errors = await self.search.search_music(music_texts, 10)

                    for entry in (entries or []):
                        thumb = entry.get("thumbnail") or ""
                        if thumb:
                            thumbnail_path = await download_media_in_internet(
                                thumb, get_photo_file_name(), MediaType.PHOTO
                            )
                        break

                    if not musics_data:
                        await self.message.answer(self._("Music not found"))

                    musics_list = [md for md in (musics_data or []) if md.get("title") and (not md.get("duration_sec") or md["duration_sec"] <= 600)]

                    for f in [audio_path, media_path]:
                        if f and await asyncio.to_thread(os.path.exists, f):
                            await asyncio.to_thread(os.remove, f)

                    q = (music_texts or "").strip()
                    display_q = q if len(q) <= 40 else q[:37] + "..."
                    music_title = f"<b>{display_q}</b> — {len(musics_list)} ta natija"
                    return musics_list, music_title, thumbnail_path

                # Audio / Video -> Shazam recognition
                music_name = await self.music_downloader.find_song_name_by_video_audio_voice_video_note(media_path)
                if not music_name:
                    await self.message.answer(self._("Music not found"))
                    return [], "", None

                musics_data, entries, errors = await self.search.search_music(music_name, 10)

                for entry in (entries or []):
                    thumb = entry.get("thumbnail") or ""
                    if thumb:
                        thumbnail_path = await download_media_in_internet(
                            thumb, get_photo_file_name(), MediaType.PHOTO
                        )
                    break

                if not musics_data:
                    await self.message.answer(self._("Music not found"))

                if media_path and await asyncio.to_thread(os.path.exists, media_path):
                    await asyncio.to_thread(os.remove, media_path)

                musics_list = [md for md in (musics_data or []) if md.get("title") and (not md.get("duration_sec") or md["duration_sec"] <= 600)]

                q = music_name.strip()
                display_q = q if len(q) <= 40 else q[:37] + "..."
                music_title = f"<b>{display_q}</b> — {len(musics_list)} ta natija"
                return musics_list, music_title, thumbnail_path

        except Exception as e:
            print("ERROR in music_downloaders:", e)
            import traceback
            traceback.print_exc()
            return None, None, None

    async def extract_video_to_audio(self, video_path: str):
        audio_path_file = f"./media/audios/{get_audio_file_name()}.mp3"
        audio_path = await asyncio.to_thread(
            self.audio_utils.extract_audio_from_video, video_path, audio_path_file
        )
        if audio_path:
            return audio_path_file
        return None
