from aiogram import Router, Bot
from aiogram.types import InlineQuery, InlineQueryResultCachedAudio

inline_share_router = Router()


@inline_share_router.inline_query()
async def share_audio_inline(inline_query: InlineQuery, bot: Bot):
    """
    Handles inline query when user taps "Guruhga Qo'shish +" button.
    The query contains the file_id of the audio to share.
    """
    file_id = inline_query.query.strip()

    if not file_id:
        await inline_query.answer([], cache_time=1)
        return

    try:
        results = [
            InlineQueryResultCachedAudio(
                id="share_audio",
                audio_file_id=file_id,
            )
        ]
        await inline_query.answer(results, cache_time=1)
    except Exception as e:
        print(f"ERROR in share_audio_inline: {e}")
        await inline_query.answer([], cache_time=1)
