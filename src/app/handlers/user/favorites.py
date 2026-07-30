import asyncpg
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from src.app.database.queries.favorites import FavoritesDataBaseActions
from src.app.keyboards.callback_data import FavoriteCD
from src.app.keyboards.inline import audio_keyboard
from src.app.utils.i18n import get_translator
from aiogram import Router

favorites_router = Router()


@favorites_router.callback_query(FavoriteCD.filter())
async def handle_favorite(call: CallbackQuery, callback_data: FavoriteCD, lang: str, pool: asyncpg.Pool):
    _ = get_translator(lang).gettext
    db = FavoritesDataBaseActions(pool)
    tg_id = call.from_user.id

    if not call.message.audio:
        await call.answer(_("Error"))
        return

    file_id = call.message.audio.file_id
    title = call.message.audio.title or ""

    if callback_data.action == "add":
        await db.add_favorite(tg_id, file_id, title)
        await call.answer(_("Added to favorites") + " ❤️")
        try:
            await call.message.edit_reply_markup(
                reply_markup=audio_keyboard(lang, file_id=file_id, title=title, is_favorite=True)
            )
        except TelegramBadRequest:
            pass

    elif callback_data.action == "remove":
        await db.remove_favorite(tg_id, file_id)
        await call.answer(_("Removed from favorites") + " 🤍")
        try:
            await call.message.edit_reply_markup(
                reply_markup=audio_keyboard(lang, file_id=file_id, title=title, is_favorite=False)
            )
        except TelegramBadRequest:
            pass
