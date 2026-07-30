import re
from urllib.parse import urlparse, parse_qs, unquote

from src.app.utils.enums.url import URLType, URLInfo

# ==================== VALIDATOR CLASS ====================

class SocialMediaURLValidator:
    """
    Professional URL validator for social media platforms
    """

    # Domain patterns
    INSTAGRAM_DOMAINS = {
        "instagram.com", "instagr.am",
        "cdninstagram.com", "fbcdn.net"
    }

    YOUTUBE_DOMAINS = {
        "youtube.com", "youtu.be", "m.youtube.com",
        "ytimg.com", "googlevideo.com", "yt.be"
    }

    TIKTOK_DOMAINS = {
        "tiktok.com", "vt.tiktok.com", "vm.tiktok.com",
        "tiktokcdn.com", "tiktokv.com", "tiktokapi.com",
        "p16-sign-va.tiktokcdn.com"
    }

    # vkvideo.ru is the dedicated VK video domain
    VK_DOMAINS = {
        "vk.com", "vk.ru", "m.vk.com", "vkvideo.ru", "m.vkvideo.ru",
    }

    @staticmethod
    def _clean_url(url: str) -> str:
        """Clean and normalize URL"""
        if not url:
            return ""
        url = url.strip()
        url = unquote(url)
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            domain = re.sub(r"^(www\.|m\.|mobile\.)", "", domain)
            return domain
        except Exception as e:
            print("ERROR", e)
            return ""

    @staticmethod
    def _is_cdn_domain(domain: str, cdn_keywords: tuple) -> bool:
        return any(keyword in domain for keyword in cdn_keywords)

    @staticmethod
    def _get_file_type(url: str) -> str:
        url_lower = url.lower()
        video_exts = (".mp4", ".mov", ".avi", ".webm", ".m4a", ".mkv")
        if any(url_lower.endswith(ext) for ext in video_exts):
            return "video"
        photo_exts = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
        if any(url_lower.endswith(ext) for ext in photo_exts):
            return "photo"
        return "unknown"

    # ==================== INSTAGRAM ====================

    def _validate_instagram(self, url: str, domain: str) -> URLInfo:
        url_lower = url.lower()

        if self._is_cdn_domain(domain, ("cdninstagram", "fbcdn")):
            file_type = self._get_file_type(url)
            if "t51.2885-19" in url:
                return URLInfo(url_type=URLType.INSTAGRAM_PROFILE_PHOTO, platform="instagram", is_cdn=True, clean_url=url)
            if file_type == "video":
                return URLInfo(url_type=URLType.INSTAGRAM_CDN_VIDEO, platform="instagram", is_cdn=True, clean_url=url)
            elif file_type == "photo":
                return URLInfo(url_type=URLType.INSTAGRAM_CDN_PHOTO, platform="instagram", is_cdn=True, clean_url=url)
            else:
                return URLInfo(url_type=URLType.INSTAGRAM_CDN_UNKNOWN, platform="instagram", is_cdn=True, clean_url=url)

        if re.search(r"/p/[\w-]+", url_lower):
            post_id = re.search(r"/p/([\w-]+)", url_lower)
            return URLInfo(url_type=URLType.INSTAGRAM_POST, platform="instagram", is_cdn=False, video_id=post_id.group(1) if post_id else None, clean_url=url)

        if re.search(r"/reels?/[\w-]+", url_lower):
            reel_id = re.search(r"/reels?/([\w-]+)", url_lower)
            return URLInfo(url_type=URLType.INSTAGRAM_REEL, platform="instagram", is_cdn=False, video_id=reel_id.group(1) if reel_id else None, clean_url=url)

        if "/stories/highlights/" in url_lower or "/highlights/" in url_lower:
            highlight_id = re.search(r"/(?:stories/)?highlights?/([\w-]+)", url_lower)
            return URLInfo(url_type=URLType.INSTAGRAM_HIGHLIGHT, platform="instagram", is_cdn=False, video_id=highlight_id.group(1) if highlight_id else None, clean_url=url)

        if "/stories/" in url_lower:
            story_match = re.search(r"/stories/([\w.]+)/(\d+)", url_lower)
            return URLInfo(url_type=URLType.INSTAGRAM_STORIES, platform="instagram", is_cdn=False, username=story_match.group(1) if story_match else None, video_id=story_match.group(2) if story_match else None, clean_url=url)

        if "/tv/" in url_lower:
            tv_id = re.search(r"/tv/([\w-]+)", url, re.IGNORECASE)
            return URLInfo(url_type=URLType.INSTAGRAM_IGTV, platform="instagram", is_cdn=False, video_id=tv_id.group(1) if tv_id else None, clean_url=url)

        if "/highlights/" in url_lower:
            highlight_id = re.search(r"/highlights?/([\w-]+)", url, re.IGNORECASE)
            return URLInfo(url_type=URLType.INSTAGRAM_HIGHLIGHT, platform="instagram", is_cdn=False, video_id=highlight_id.group(1) if highlight_id else None, clean_url=url)

        if "/live/" in url_lower:
            return URLInfo(url_type=URLType.INSTAGRAM_LIVE, platform="instagram", is_cdn=False, clean_url=url)

        profile_match = re.match(r"^https?://(?:www\.)?instagram\.com/([\w.]+)/?$", url_lower)
        if profile_match:
            return URLInfo(url_type=URLType.INSTAGRAM_PROFILE_PHOTO, platform="instagram", is_cdn=False, username=profile_match.group(1), clean_url=url)

        return URLInfo(url_type=URLType.UNKNOWN, platform="instagram", is_cdn=False, clean_url=url)

    # ==================== YOUTUBE ====================

    def _validate_youtube(self, url: str, domain: str) -> URLInfo:
        url_lower = url.lower()

        if self._is_cdn_domain(domain, ("ytimg", "googlevideo")):
            file_type = self._get_file_type(url)
            if file_type == "video":
                return URLInfo(url_type=URLType.YOUTUBE_CDN_VIDEO, platform="youtube", is_cdn=True, clean_url=url)
            elif file_type == "photo":
                return URLInfo(url_type=URLType.YOUTUBE_CDN_PHOTO, platform="youtube", is_cdn=True, clean_url=url)
            else:
                return URLInfo(url_type=URLType.YOUTUBE_CDN_UNKNOWN, platform="youtube", is_cdn=True, clean_url=url)

        if "/shorts/" in url_lower:
            video_id = re.search(r"/shorts/([\w-]+)", url, re.IGNORECASE)
            return URLInfo(url_type=URLType.YOUTUBE_SHORTS, platform="youtube", is_cdn=False, video_id=video_id.group(1) if video_id else None, clean_url=url)

        video_id = None
        if "youtu.be" in domain:
            match = re.search(r"youtu\.be/([\w-]+)", url, re.IGNORECASE)
            if match:
                video_id = match.group(1)
        else:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if "v" in params and params["v"][0]:
                video_id = params["v"][0]
            if not video_id:
                match = re.search(r"[?&]v=([\w-]+)", url, re.IGNORECASE)
                if match:
                    video_id = match.group(1)

        if video_id:
            return URLInfo(url_type=URLType.YOUTUBE_VIDEO, platform="youtube", is_cdn=False, video_id=video_id, clean_url=f"https://www.youtube.com/watch?v={video_id}")

        if "/live/" in url_lower:
            live_id = re.search(r"/live/([\w-]+)", url, re.IGNORECASE)
            return URLInfo(url_type=URLType.YOUTUBE_LIVE, platform="youtube", is_cdn=False, video_id=live_id.group(1) if live_id else None, clean_url=url)

        if "list=" in url_lower:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            playlist_id = params.get("list", [None])[0]
            return URLInfo(url_type=URLType.YOUTUBE_PLAYLIST, platform="youtube", is_cdn=False, video_id=playlist_id, clean_url=url)

        return URLInfo(url_type=URLType.UNKNOWN, platform="youtube", is_cdn=False, clean_url=url)

    # ==================== TIKTOK ====================

    def _validate_tiktok(self, url: str, domain: str) -> URLInfo:
        url_lower = url.lower()

        if self._is_cdn_domain(domain, ("tiktokcdn", "tiktokv", "tiktokapi")):
            file_type = self._get_file_type(url)
            if file_type == "video":
                return URLInfo(url_type=URLType.TIKTOK_CDN_VIDEO, platform="tiktok", is_cdn=True, clean_url=url)
            elif file_type == "photo":
                return URLInfo(url_type=URLType.TIKTOK_CDN_PHOTO, platform="tiktok", is_cdn=True, clean_url=url)
            else:
                return URLInfo(url_type=URLType.TIKTOK_CDN_UNKNOWN, platform="tiktok", is_cdn=True, clean_url=url)

        if "/video/" in url_lower:
            video_match = re.search(r"/@([\w.]+)/video/(\d+)", url_lower)
            if video_match:
                return URLInfo(url_type=URLType.TIKTOK_VIDEO, platform="tiktok", is_cdn=False, username=video_match.group(1), video_id=video_match.group(2), clean_url=url)
            video_id = re.search(r"/video/(\d+)", url_lower)
            return URLInfo(url_type=URLType.TIKTOK_VIDEO, platform="tiktok", is_cdn=False, video_id=video_id.group(1) if video_id else None, clean_url=url)

        if "/photo/" in url_lower:
            photo_match = re.search(r"/@([\w.]+)/photo/(\d+)", url_lower)
            return URLInfo(url_type=URLType.TIKTOK_PHOTO, platform="tiktok", is_cdn=False, username=photo_match.group(1) if photo_match else None, video_id=photo_match.group(2) if photo_match else None, clean_url=url)

        if re.search(r"/@[\w.]+/live", url_lower):
            username_match = re.search(r"/@([\w.]+)/live", url_lower)
            return URLInfo(url_type=URLType.TIKTOK_LIVE, platform="tiktok", is_cdn=False, username=username_match.group(1) if username_match else None, clean_url=url)

        profile_match = re.search(r"/@([\w.]+)/?$", url_lower)
        if profile_match:
            return URLInfo(url_type=URLType.TIKTOK_PROFILE, platform="tiktok", is_cdn=False, username=profile_match.group(1), clean_url=url)

        return URLInfo(url_type=URLType.UNKNOWN, platform="tiktok", is_cdn=False, clean_url=url)

    # ==================== VK ====================

    def _validate_vk(self, url: str, domain: str) -> URLInfo:
        """Validate VK URL.

        Supported:
          https://vk.com/video-OWNERID_VIDEOID
          https://vkvideo.ru/video-OWNERID_VIDEOID   ← new dedicated domain
          https://vk.com/video?z=video-OWNERID_VIDEOID
          https://vk.com/clips-OWNERID?z=clip-...

        Not supported (audio): vk.com/audio-... → returns URLType.UNKNOWN
        """
        url_lower = url.lower()

        # Audio links — not downloadable, return UNKNOWN so handler shows "Wrong url"
        if "/audio" in url_lower or "audio-" in url_lower:
            return URLInfo(url_type=URLType.UNKNOWN, platform="vk", is_cdn=False, clean_url=url)

        # Clips
        if "/clips" in url_lower or "clip-" in url_lower:
            clip_match = re.search(r"clip-?(\d+_\d+)", url_lower)
            return URLInfo(url_type=URLType.VK_CLIP, platform="vk", is_cdn=False, video_id=clip_match.group(1) if clip_match else None, clean_url=url)

        # vkvideo.ru path format: /video-OWNERID_VIDEOID
        # Also vk.com/video-OWNERID_VIDEOID
        video_match = re.search(r"video-?(\d+_\d+)", url_lower)
        if video_match:
            return URLInfo(url_type=URLType.VK_VIDEO, platform="vk", is_cdn=False, video_id=video_match.group(1), clean_url=url)

        # /video?z=videoOWNER_ID
        parsed = urlparse(url)
        if parsed.path.rstrip("/").endswith("/video"):
            params = parse_qs(parsed.query)
            z = params.get("z", [None])[0]
            if z:
                vid = re.search(r"video-?(\d+_\d+)", z)
                if vid:
                    return URLInfo(url_type=URLType.VK_VIDEO, platform="vk", is_cdn=False, video_id=vid.group(1), clean_url=url)

        return URLInfo(url_type=URLType.VK_VIDEO, platform="vk", is_cdn=False, clean_url=url)

    # ==================== MAIN VALIDATOR ====================

    def validate(self, url: str) -> URLInfo:
        """Validate URL and return URLInfo"""
        url = self._clean_url(url)
        if not url:
            return URLInfo(url_type=URLType.UNKNOWN, platform="unknown", is_cdn=False, clean_url=url)

        domain = self._extract_domain(url)

        # Instagram
        if any(ig in domain for ig in ("instagram.com", "instagr.am", "cdninstagram", "fbcdn")):
            return self._validate_instagram(url, domain)

        # YouTube
        if any(yt in domain for yt in ("youtube.com", "youtu.be", "ytimg", "googlevideo", "yt.be")):
            return self._validate_youtube(url, domain)

        # TikTok
        if any(tt in domain for tt in ("tiktok.com", "tiktokcdn", "tiktokv", "tiktokapi")):
            return self._validate_tiktok(url, domain)

        # VK — includes vkvideo.ru
        if any(vk in domain for vk in ("vk.com", "vk.ru", "vkvideo.ru")):
            return self._validate_vk(url, domain)

        return URLInfo(url_type=URLType.UNKNOWN, platform="unknown", is_cdn=False, clean_url=url)
