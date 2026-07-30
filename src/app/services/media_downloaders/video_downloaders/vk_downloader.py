import asyncio

from yt_dlp import YoutubeDL

from src.app.services.media_downloaders.utils.files import get_video_file_name
from src.app.utils.enums.error import DownloadError


class VKDownloader:
    """Download videos from VK using yt-dlp."""

    async def vk_video_downloader(self, video_url: str):
        file_name = get_video_file_name()
        video_output_path = f'./media/videos/{file_name}'
        errors = []

        def _download():
            ydl_opts = {
                'format': 'best[filesize<2000M]/best',
                'outtmpl': video_output_path + '.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 20,
            }
            with YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(video_url, download=True)

        try:
            info = await asyncio.to_thread(_download)

            if not info:
                errors.append(DownloadError.DOWNLOAD_ERROR)
                return None, errors

            ext = info.get('ext', 'mp4')
            final_path = f'{video_output_path}.{ext}'

            # Fallback scan if ext is wrong
            import os
            if not os.path.exists(final_path):
                for candidate_ext in ('mp4', 'webm', 'mkv', 'avi'):
                    candidate = f'{video_output_path}.{candidate_ext}'
                    if os.path.exists(candidate):
                        final_path = candidate
                        break

            filesize = info.get('filesize') or info.get('filesize_approx') or 0
            if filesize and filesize / 1024 / 1024 > 2000:
                errors.append(DownloadError.FILE_TOO_BIG)
                return None, errors

            return final_path, errors

        except Exception as e:
            print(f'ERROR in VKDownloader: {e}')
            errors.append(DownloadError.DOWNLOAD_ERROR)
            return None, errors
