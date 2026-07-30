import asyncpg
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from src.app.keyboards.callback_data import TopFilterCD
from src.app.keyboards.inline import auido_effect_kbd, songs_keyboard, top_chart_keyboard
from src.app.database.queries.favorites import FavoritesDataBaseActions
from src.app.services.media_downloaders.seekers.search import YouTubeSearcher
from src.app.utils.i18n import get_translator

user_commands_router = Router()

_DEFAULT_REGION = "global"
_DEFAULT_PERIOD = "today"

_REGION_EMOJI = {
    "global": "🌍",
    "russia": "🇷🇺",
    "uzbekistan": "🇺🇿",
    "english": "🇺🇸",
}

_PERIOD_LABEL = {
    "today": "Bugun",
    "week": "Hafta",
    "month": "Oy",
}

_FAV_PAGE_SIZE = 10


def _top_header(region: str, period: str) -> str:
    emoji = _REGION_EMOJI.get(region, "🌍")
    period_label = _PERIOD_LABEL.get(period, period.capitalize())
    return (
        f"🏆 Top Musiqalar \n"
        f"{emoji} {region.capitalize()} • 📅 {period_label} \n\n"
        f"Trekni bosib yuklab oling 👇"
    )


def _favorites_keyboard(favorites: list, page: int = 1) -> InlineKeyboardMarkup:
    """Build paginated inline keyboard for favorite tracks.

    Each track row has two buttons:
      - Left wide button: play track (title, left-aligned with index)
      - Right narrow button: 🗑 remove from favorites immediately

    callback_data stores the 0-based global index so file_id never goes
    into callback_data (Telegram's 64-byte limit would be exceeded).
    """
    total = len(favorites)
    total_pages = max(1, (total + _FAV_PAGE_SIZE - 1) // _FAV_PAGE_SIZE)
    start = (page - 1) * _FAV_PAGE_SIZE
    end = start + _FAV_PAGE_SIZE

    inline_keyboard = []

    for global_idx in range(start, min(end, total)):
        fav = favorites[global_idx]
        title = fav.get("title") if isinstance(fav, dict) else (fav[1] if len(fav) > 1 else "Track")
        # Left-aligned: number + title, no centering emoji padding
        label = f"{global_idx + 1}. {title or 'Track'}"
        if len(label) > 55:
            label = label[:52] + "..."

        inline_keyboard.append([
            # Play button — takes most of the row width
            InlineKeyboardButton(
                text=f"▶️ {label}",
                callback_data=f"fav_play:{global_idx}"
            ),
            # Remove button — compact, on the right
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"fav_del:{global_idx}"
            ),
        ])

    # Navigation row
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"fav_page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"fav_page:{page + 1}"))
    if nav:
        inline_keyboard.append(nav)

    inline_keyboard.append([InlineKeyboardButton(text="❌ Yopish", callback_data="close")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def _fav_message_text(count: int) -> str:
    return (
        f"❤️ Sevimli treklar ({count})\n\n"
        f"▶️ — tinglash    🗑 — o'chirish"
    )


@user_commands_router.message(Command("about"))
async def handled_command_about(message: Message, lang: str):
    _ = get_translator(lang).gettext
    await message.answer(_("About"))


@user_commands_router.message(Command("media_effect"))
async def handled_command_media_effect(message: Message, lang: str):
    _ = get_translator(lang).gettext
    await message.answer(
        _("Media effect"),
        reply_markup=auido_effect_kbd(actions="by_command", lang=lang)
    )


@user_commands_router.message(Command("top"))
async def handled_command_top(message: Message, lang: str):
    region = _DEFAULT_REGION
    period = _DEFAULT_PERIOD
    searcher = YouTubeSearcher()
    songs = await searcher.get_top_by_region_period(region, period, limit=50)

    if not songs:
        await message.answer("Top musiqalarni olishda xatolik yuz berdi.")
        return

    await message.answer(
        _top_header(region, period),
        parse_mode="HTML",
        reply_markup=top_chart_keyboard(songs, region=region, period=period, page=1)
    )


@user_commands_router.message(Command("my"))
async def handled_command_my(message: Message, lang: str, pool: asyncpg.Pool):
    """Show user's favorite tracks list."""
    db = FavoritesDataBaseActions(pool)
    tg_id = message.from_user.id

    favorites = await db.get_favorites(tg_id)

    if not favorites:
        await message.answer(
            "❤️ Sevimli treklar \n\n"
            "Sizda hali sevimli treklar yo'q.\n"
            "Trekni yuklab, 🤍 tugmasini bosing.",
            parse_mode="HTML"
        )
        return

    fav_list = [{"file_id": r["file_id"], "title": r["title"]} for r in favorites]

    await message.answer(
        _fav_message_text(len(fav_list)),
        parse_mode="HTML",
        reply_markup=_favorites_keyboard(fav_list, page=1)
    )


@user_commands_router.callback_query(F.data.startswith("fav_page:"))
async def fav_page_handler(callback: CallbackQuery, pool: asyncpg.Pool):
    """Paginate favorites list."""
    db = FavoritesDataBaseActions(pool)
    tg_id = callback.from_user.id

    _, page_s = callback.data.split(":", 1)
    page = int(page_s)

    favorites = await db.get_favorites(tg_id)
    fav_list = [{"file_id": r["file_id"], "title": r["title"]} for r in favorites]

    try:
        await callback.message.edit_text(
            _fav_message_text(len(fav_list)),
            parse_mode="HTML",
            reply_markup=_favorites_keyboard(fav_list, page=page)
        )
    except TelegramBadRequest:
        pass

    await callback.answer()


@user_commands_router.callback_query(F.data.startswith("fav_del:"))
async def fav_del_handler(callback: CallbackQuery, pool: asyncpg.Pool):
    """Remove a track from favorites immediately and refresh the list."""
    tg_id = callback.from_user.id
    _, idx_s = callback.data.split(":", 1)
    idx = int(idx_s)

    db = FavoritesDataBaseActions(pool)
    favorites = await db.get_favorites(tg_id)

    if idx < 0 or idx >= len(favorites):
        await callback.answer("Trek allaqachon o'chirilgan.", show_alert=False)
        return

    # Remove the track from DB
    file_id_to_remove: str = favorites[idx]["file_id"]
    await db.remove_favorite(tg_id, file_id_to_remove)

    # Reload updated list
    favorites = await db.get_favorites(tg_id)
    fav_list = [{"file_id": r["file_id"], "title": r["title"]} for r in favorites]

    if not fav_list:
        try:
            await callback.message.edit_text(
                "❤️ Sevimli treklar \n\n"
                "Sizda hali sevimli treklar yo'q.\n"
                "Trekni yuklab, 🤍 tugmasini bosing.",
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            pass
        await callback.answer("O'chirildi ✓")
        return

    # Stay on the same page if possible, else go to last page
    total_pages = max(1, (len(fav_list) + _FAV_PAGE_SIZE - 1) // _FAV_PAGE_SIZE)
    # Figure out which page the deleted item was on
    current_page = (idx // _FAV_PAGE_SIZE) + 1
    page = min(current_page, total_pages)

    try:
        await callback.message.edit_text(
            _fav_message_text(len(fav_list)),
            parse_mode="HTML",
            reply_markup=_favorites_keyboard(fav_list, page=page)
        )
    except TelegramBadRequest:
        pass

    await callback.answer("O'chirildi ✓")


@user_commands_router.callback_query(F.data.startswith("fav_play:"))
async def fav_play_handler(callback: CallbackQuery, lang: str, pool: asyncpg.Pool):
    """Send favorite track — looks up full file_id from DB by index."""
    gettext = get_translator(lang).gettext
    tg_id = callback.from_user.id

    _, idx_s = callback.data.split(":", 1)
    idx = int(idx_s)

    db = FavoritesDataBaseActions(pool)
    favorites = await db.get_favorites(tg_id)

    if idx < 0 or idx >= len(favorites):
        await callback.answer("Trek topilmadi. Ro'yxat yangilandi.", show_alert=True)
        return

    row = favorites[idx]
    file_id: str = row["file_id"]
    title: str = row["title"] or ""

    try:
        from src.app.keyboards.inline import audio_keyboard
        await callback.message.reply_audio(
            audio=file_id,
            caption=gettext("Downloaded by"),
            reply_markup=audio_keyboard(lang, file_id=file_id, title=title, is_favorite=True)
        )
    except Exception as e:
        print("ERROR in fav_play_handler:", e)
        await callback.answer("Trekni yuborishda xatolik. Qayta qo'shing.", show_alert=True)
        return

    await callback.answer()


@user_commands_router.callback_query(TopFilterCD.filter())
async def top_filter_handler(callback: CallbackQuery, callback_data: TopFilterCD, lang: str):
    region = callback_data.region
    period = callback_data.period
    page = callback_data.page

    searcher = YouTubeSearcher()
    songs = await searcher.get_top_by_region_period(region, period, limit=50)

    if not songs:
        await callback.answer("Xatolik yuz berdi, qayta urinib ko'ring.", show_alert=True)
        return

    kb = top_chart_keyboard(songs, region=region, period=period, page=page)

    try:
        await callback.message.edit_text(
            _top_header(region, period),
            parse_mode="HTML",
            reply_markup=kb
        )
    except TelegramBadRequest:
        pass

    await callback.answer()


@user_commands_router.callback_query(F.data.startswith("page:"))
async def page_handler(callback: CallbackQuery, lang: str):
    _ = get_translator(lang).gettext

    searcher = YouTubeSearcher()
    songs = await searcher.get_top_music(limit=50)
    _, page_s = callback.data.split(":", 1)
    page = int(page_s)
    kb = songs_keyboard(songs, page=page)

    try:
        await callback.message.edit_text(text=_("Top popular songs"), reply_markup=kb)
    except TelegramBadRequest:
        pass


@user_commands_router.callback_query(F.data.in_(["close", "delete_list_music"]))
async def close_handler(callback: CallbackQuery):
    await callback.message.delete()


@user_commands_router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()
