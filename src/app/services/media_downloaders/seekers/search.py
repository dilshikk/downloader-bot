import asyncio
import math
import re
import time
from typing import Dict, List, Any, Optional, Tuple

from shazamio import Shazam
from yt_dlp import YoutubeDL

from src.app.utils.enums.error import DownloadError

# ── Module-level caches ────────────────────────────────────────────────
_SEARCH_CACHE: Dict[str, tuple] = {}
SEARCH_CACHE_TTL = 30 * 60   # 30 min

_INFO_CACHE: Dict[str, tuple] = {}
INFO_CACHE_TTL = 60 * 60     # 1 hour

_NEG_CACHE: Dict[str, float] = {}
NEG_CACHE_TTL = 60

# ── Quality constants ──────────────────────────────────────────────────
QUALITY_OFFICIAL = "official"
QUALITY_LIVE     = "live"
QUALITY_COVER    = "cover"
QUALITY_KARAOKE  = "karaoke"
QUALITY_NORMAL   = "normal"

_RE_TOPIC = re.compile(r" - Topic$", re.IGNORECASE)

_LIVE_KEYWORDS    = ("live", "concert", "live performance", "in concert")
_KARAOKE_KEYWORDS = ("karaoke", "instrumental", "backing track", "minus track", "no vocals")
_COVER_KEYWORDS   = ("cover", "tribute", "performed by")
_LYRIC_KEYWORDS   = ("lyrics", "lyric video", "official lyric")
_OFFICIAL_TITLE   = ("official video", "official audio", "official music video", "official mv")


# ── Quality classifier ─────────────────────────────────────────────────

def _classify_quality(title: str, uploader: str) -> str:
    t = title.lower()
    u = (uploader or "").lower()

    # YouTube Music "Artist - Topic" channels = guaranteed official audio
    if _RE_TOPIC.search(uploader or ""):
        return QUALITY_OFFICIAL
    # VEVO channels
    if "vevo" in u:
        return QUALITY_OFFICIAL

    # Karaoke / instrumental (most penalized)
    if any(k in t for k in _KARAOKE_KEYWORDS):
        return QUALITY_KARAOKE

    # Live performance
    if any(k in t for k in _LIVE_KEYWORDS):
        return QUALITY_LIVE

    # Cover
    if any(k in t for k in _COVER_KEYWORDS):
        return QUALITY_COVER

    # Official by title keywords
    if any(k in t for k in _OFFICIAL_TITLE):
        return QUALITY_OFFICIAL
    if "official" in u:
        return QUALITY_OFFICIAL

    return QUALITY_NORMAL


# ── Artist / title extraction ─────────────────────────────────────────

_RE_PARENS_SUFFIX = re.compile(r'\s*[\(\[][^\)\]]{1,40}[\)\]]\s*$')
_RE_MULTI_PARENS  = re.compile(r'\s*[\(\[][^\)\]]{1,40}[\)\]]')


def _extract_artist(title: str, uploader: str) -> Tuple[str, str]:
    """
    Returns (artist, clean_title).
    Handles:
      - 'Artist - Title'  (YouTube standard)
      - 'Artist - Topic'  uploader channel
      - 'ArtistVEVO'      VEVO channels
    """
    clean = _RE_PARENS_SUFFIX.sub('', title).strip()

    for sep in (" - ", " - "):
        if sep in title:
            parts = title.split(sep, 1)
            artist = parts[0].strip()
            track  = _RE_PARENS_SUFFIX.sub('', parts[1]).strip()
            return artist, track

    # "Artist - Topic" uploader
    if _RE_TOPIC.search(uploader or ""):
        artist = _RE_TOPIC.sub("", uploader).strip()
        return artist, clean

    # "ArtistVEVO" uploader
    if uploader and uploader.lower().endswith("vevo"):
        return uploader[:-4].strip(), clean

    return "", clean


# ── Smart scorer ──────────────────────────────────────────────────────

def _score_result(entry: Dict, query: str, quality: str) -> float:
    """Higher score = better match."""
    score = 50.0

    title  = (entry.get("title") or "").lower()
    dur    = entry.get("duration") or 0
    views  = entry.get("view_count") or 0

    # Quality bonus / penalty
    score += {
        QUALITY_OFFICIAL: 25,
        QUALITY_NORMAL:    5,
        QUALITY_COVER:   -10,
        QUALITY_LIVE:    -20,
        QUALITY_KARAOKE: -35,
    }.get(quality, 0)

    # Lyrics video slight penalty
    if any(k in title for k in _LYRIC_KEYWORDS):
        score -= 5

    # Duration sweet spot: 1:30 – 6:00
    if 90 <= dur <= 360:
        score += 12
    elif 60 <= dur < 90:
        score += 3
    elif dur > 480:
        score -= 10
    elif dur and dur < 60:
        score -= 25

    # View count log bonus (up to +15)
    if views > 0:
        score += min(15.0, math.log10(views + 1) * 2.0)

    # Query relevance: word overlap
    q_words = set(re.sub(r'[^\w\s]', '', query.lower()).split())
    t_words = set(re.sub(r'[^\w\s]', '', title).split())
    if q_words:
        overlap = len(q_words & t_words) / len(q_words)
        score += overlap * 20

    return score


# ── Deduplication ─────────────────────────────────────────────────────

def _normalize_for_dedup(title: str) -> str:
    t = _RE_MULTI_PARENS.sub('', title.lower())
    t = re.sub(r'[^\w\s]', '', t)
    return ' '.join(t.split())


def _dedup_results(results: List[Dict]) -> List[Dict]:
    seen: set = set()
    out: List[Dict] = []
    for r in results:
        key = _normalize_for_dedup(r.get("title", ""))
        if key and key not in seen:
            seen.add(key)
            out.append(r)
    return out


# ── Main searcher class ────────────────────────────────────────────────

class YouTubeSearcher:

    def __init__(self, shazam: Optional[Shazam] = None):
        self.shazam = shazam or Shazam()

    # ── Cache helpers ─────────────────────────────────────────────────

    @staticmethod
    def _cache_get(store: Dict, key: str, ttl: float):
        rec = store.get(key)
        if not rec:
            return None
        ts, val = rec
        if time.time() - ts > ttl:
            store.pop(key, None)
            return None
        return val

    @staticmethod
    def _cache_set(store: Dict, key: str, val):
        store[key] = (time.time(), val)

    def _neg_ok(self, key: str) -> bool:
        ts = _NEG_CACHE.get(key)
        return ts is not None and time.time() - ts < NEG_CACHE_TTL

    def _neg_set(self, key: str):
        _NEG_CACHE[key] = time.time()

    # ── Media info ────────────────────────────────────────────────────

    async def get_media_info(self, video_url: str) -> Optional[Dict[str, Any]]:
        key = f"info:{video_url}"
        cached = self._cache_get(_INFO_CACHE, key, INFO_CACHE_TTL)
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
                self._cache_set(_INFO_CACHE, key, result)
            return result
        except Exception as e:
            print("ERROR get_media_info:", e)
            return None

    # ── Smart search ──────────────────────────────────────────────────

    async def search_music(
        self,
        query: str,
        max_count: int = 10,
    ) -> tuple[List[Dict[str, Any]], Any, List[str]]:
        """
        Smart music search: quality scoring, artist extraction, deduplication.

        Each result dict contains:
          id, title, clean_title, artist, duration, duration_sec,
          quality, score, uploader, filesize_mb (always None)

        Returns (results, raw_entries, errors).
        """
        if not query or not query.strip():
            return [], [], [DownloadError.MUSIC_NOT_FOUND]

        q = query.strip()
        cache_key = f"search:{q}:{max_count}"
        cached = self._cache_get(_SEARCH_CACHE, cache_key, SEARCH_CACHE_TTL)
        if cached is not None:
            return cached

        # Fetch more candidates so we have room to rank and dedup
        fetch_n = max(max_count * 2, 20)

        def _run():
            opts = {
                "quiet": True,
                "skip_download": True,
                "extract_flat": True,
                "noplaylist": True,
            }
            try:
                with YoutubeDL(opts) as ydl:
                    data = ydl.extract_info(f"ytsearch{fetch_n}:{q}", download=False)
                if not data:
                    return [], None, [DownloadError.MUSIC_NOT_FOUND]
                return data.get("entries") or [], data, []
            except Exception as ex:
                print("ERROR search_music yt-dlp:", ex)
                return [], None, [str(ex)]

        raw_entries, raw_data, errors = await asyncio.to_thread(_run)

        if not raw_entries:
            return [], raw_data, errors or [DownloadError.MUSIC_NOT_FOUND]

        scored: List[Dict] = []
        for e in raw_entries:
            if not e or not e.get("id"):
                continue
            dur = e.get("duration") or 0
            # Hard filter: skip very short junk and overly long content
            if dur and (dur < 30 or dur > 720):
                continue

            title    = e.get("title") or ""
            uploader = e.get("uploader") or e.get("channel") or ""
            quality  = _classify_quality(title, uploader)
            artist, clean_title = _extract_artist(title, uploader)
            score    = _score_result(e, q, quality)

            m, s = divmod(int(dur), 60) if dur else (0, 0)

            scored.append({
                "id":           e["id"],
                "title":        title,
                "clean_title":  clean_title,
                "artist":       artist,
                "duration":     f"{m}:{s:02d}" if dur else None,
                "duration_sec": dur,
                "quality":      quality,
                "score":        score,
                "uploader":     uploader,
                "filesize_mb":  None,
            })

        # Rank by score, deduplicate near-identical titles, take top N
        scored.sort(key=lambda x: x["score"], reverse=True)
        deduped = _dedup_results(scored)[:max_count]

        if not deduped:
            return [], raw_entries, [DownloadError.MUSIC_NOT_FOUND]

        result = (deduped, raw_entries, [])
        self._cache_set(_SEARCH_CACHE, cache_key, result)
        return result

    # ── Shazam top charts ─────────────────────────────────────────────

    def _parse_tracks(self, raw: dict) -> List[Dict[str, str]]:
        return [
            {"artist": t.get("subtitle", ""), "title": t.get("title", "")}
            for t in raw.get("tracks", [])
        ]

    async def get_top_music(self, limit: int = 50) -> List[Dict[str, str]]:
        key = f"shazam:world:{limit}"
        cached = self._cache_get(_SEARCH_CACHE, key, SEARCH_CACHE_TTL * 2)
        if cached is not None:
            return cached
        if self._neg_ok(key):
            raise RuntimeError("Shazam temporarily unavailable")
        try:
            raw = await self.shazam.top_world_tracks(limit=limit)
        except Exception:
            self._neg_set(key)
            raise
        result = self._parse_tracks(raw)
        self._cache_set(_SEARCH_CACHE, key, result)
        return result

    async def get_top_by_region(self, region_code: str, limit: int = 50) -> List[Dict[str, str]]:
        iso = region_code.upper()
        key = f"shazam:{iso}:{limit}"
        cached = self._cache_get(_SEARCH_CACHE, key, SEARCH_CACHE_TTL * 2)
        if cached is not None:
            return cached
        if self._neg_ok(key):
            raise RuntimeError("Shazam temporarily unavailable")
        try:
            raw = await self.shazam.top_country_tracks(iso, limit)
        except Exception:
            self._neg_set(key)
            raise
        result = self._parse_tracks(raw)
        self._cache_set(_SEARCH_CACHE, key, result)
        return result
