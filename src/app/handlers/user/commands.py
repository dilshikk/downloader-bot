from enum import Enum

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.app.keyboards.callback_data import TopPopularMusicCD
from src.app.keyboards.inline import auido_effect_kbd
from src.app.services.media_downloaders.seekers.search import YouTubeSearcher
from src.app.utils.i18n import get_translator

user_commands_router = Router()

_searcher = YouTubeSearcher()

# region code -> (flag emoji, ISO 3166-1 alpha-2 для Shazam)
REGIONS = {
    "uz": ("🇺🇿", "UZ"),
    "ru": ("🇷🇺", "RU"),
    "gb": ("🇬🇧", "GB"),
    "kz": ("🇰🇿", "KZ"),
    "tr": ("🇹🇷", "TR"),
    "az": ("🇦🇿", "AZ"),
}

PAGE_SIZE = 10
DEFAULT_REGION = "uz"


class ChartState(Enum):
    OK = "ok"
    EMPTY = "empty"
    ERROR = "error"


async def fetch_chart_safe(region_iso: str) -> tuple[ChartState, list[dict]]:
    try:
        songs = await _searcher.get_top_by_region(region_iso, limit=50)
    except Exception as e:
        print("ERROR fetch_chart_safe:", e)
        return ChartState.ERROR, []
    if not songs:
        return ChartState.EMPTY, []
    return ChartState.OK, songs


def build_top_keyboard(
    active_region: str,
    songs_chunk: list[dict],
    page: int = 0,
    has_next: bool = False,
    has_prev: bool = False,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Row: region flags
    for code, (flag, _) in REGIONS.items():
        text = f"{flag} ✅" if code == active_region else flag
        builder.button(text=text, callback_data=f"top_region:{code}:0")
    builder.adjust(len(REGIONS))

    # Rows: numbered track buttons (5 per row)
    start = page * PAGE_SIZE
    for i, track in enumerate(songs_chunk, start=start + 1):
        name = f"{track.get('artist', '')} — {track.get('title', '')}"
        builder.button(
            text=str(i),
            callback_data=TopPopularMusicCD(music_name=name[:40]).pack(),
        )
    builder.adjust(len(REGIONS), 5)

    # Navigation
    nav: list[InlineKeyboardButton] = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"top_page:{active_region}:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"top_page:{active_region}:{page + 1}"))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text="❌", callback_data="top_close"))
    return builder.as_markup()


def build_top_text(songs: list[dict], page: int) -> str:
    start = page * PAGE_SIZE
    chunk = songs[start: start + PAGE_SIZE]
    lines = ["🎵 <b>TOP Popular Songs</b>", ""]
    for i, track in enumerate(chunk, start=start + 1):
        artist = track.get("artist", "Unknown")
        title = track.get("title", "Unknown")
        lines.append(f"{i}. {artist} — {title}")
    return "\n".join(lines)


async def render_chart(
    target: Message | CallbackQuery,
    region_code: str,
    page: int,
    is_edit: bool,
) -> None:
    flag, region_iso = REGIONS.get(region_code, REGIONS[DEFAULT_REGION])
    state, songs = await fetch_chart_safe(region_iso)

    if state == ChartState.ERROR:
        text = "⚠️ Не удалось загрузить чарт. Shazam недоступен, попробуйте позже."
        keyboard = build_top_keyboard(region_code, songs_chunk=[], page=0)
    elif state == ChartState.EMPTY:
        text = f"{flag} Для этого региона треков не найдено."
        keyboard = build_top_keyboard(region_code, songs_chunk=[], page=0)
    else:
        max_page = (len(songs) - 1) // PAGE_SIZE
        page = min(max(page, 0), max_page)
        start = page * PAGE_SIZE
        chunk = songs[start: start + PAGE_SIZE]
        text = build_top_text(songs, page)
        keyboard = build_top_keyboard(
            region_code,
            songs_chunk=chunk,
            page=page,
            has_next=page < max_page,
            has_prev=page > 0,
        )

    if is_edit:
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ── Handlers ──────────────────────────────────────────────────────────

@user_commands_router.message(Command("about"))
async def handled_command_about(message: Message, lang: str):
    _ = get_translator(lang).gettext
    await message.answer(_("About"))


@user_commands_router.message(Command("media_effect"))
async def handled_command_media_effect(message: Message, lang: str):
    _ = get_translator(lang).gettext
    await message.answer(
        _("Media effect"),
        reply_markup=auido_effect_kbd(actions="by_command", lang=lang),
    )


@user_commands_router.message(Command("top"))
async def handled_command_top(message: Message):
    await render_chart(message, region_code=DEFAULT_REGION, page=0, is_edit=False)


@user_commands_router.callback_query(F.data.startswith("top_region:"))
async def handle_region_switch(callback: CallbackQuery):
    _, region_code, page_str = callback.data.split(":")
    await render_chart(callback, region_code, int(page_str), is_edit=True)
    await callback.answer()


@user_commands_router.callback_query(F.data.startswith("top_page:"))
async def handle_page_switch(callback: CallbackQuery):
    _, region_code, page_str = callback.data.split(":")
    await render_chart(callback, region_code, int(page_str), is_edit=True)
    await callback.answer()


@user_commands_router.callback_query(F.data == "top_close")
async def handle_top_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@user_commands_router.callback_query(F.data.in_(["close", "delete_list_music"]))
async def close_handler(callback: CallbackQuery):
    await callback.message.delete()
