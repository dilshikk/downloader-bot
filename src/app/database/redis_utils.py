import asyncio
import hashlib
import json
from typing import List, Dict, Optional

from redis import asyncio as aioredis

from src.app.core.config import Settings

# Module-level connection (lazy init)
_redis_pool: Optional[aioredis.Redis] = None


async def get_redis(settings: Settings) -> aioredis.Redis:
    """Get or create a shared Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        redis_url = f"redis://{settings.redis_host}:6379/{settings.redis_db_name}"
        _redis_pool = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


def get_cache_key(url: str) -> str:
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return f"media:{url_hash}"


async def get_cached_media(url: str, settings: Settings) -> List[Dict] | None:
    redis_client = await get_redis(settings)
    cache_key = get_cache_key(url)
    cached_data = await redis_client.get(cache_key)

    if cached_data:
        try:
            return json.loads(cached_data)
        except json.JSONDecodeError:
            return None
    return None


async def cache_media(url: str, media_list: List[Dict], settings: Settings):
    redis_client = await get_redis(settings)
    cache_key = get_cache_key(url)
    cache_data = json.dumps(media_list)
    await redis_client.setex(cache_key, 10800, cache_data)


# ── Audio file_id cache ─────────────────────────────────────────────── #
# Caches Telegram file_id for downloaded audio by YouTube video_id.
# TTL: 7 days (Telegram file_ids stay valid indefinitely but we refresh
# periodically in case the bot token changes).

_AUDIO_CACHE_TTL = 60 * 60 * 24 * 7  # 7 days


def _audio_cache_key(video_id: str) -> str:
    return f"audio_fid:{video_id}"


async def get_cached_audio_file_id(video_id: str, settings: Settings) -> Optional[str]:
    """Return cached Telegram file_id for a YouTube video_id, or None."""
    redis_client = await get_redis(settings)
    return await redis_client.get(_audio_cache_key(video_id))


async def cache_audio_file_id(video_id: str, file_id: str, settings: Settings):
    """Cache Telegram file_id for a YouTube video_id."""
    redis_client = await get_redis(settings)
    await redis_client.setex(_audio_cache_key(video_id), _AUDIO_CACHE_TTL, file_id)
