from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from src.app.keyboards.callback_data import TopFilterCD
from src.app.keyboards.inline import auido_effect_kbd, songs_keyboard, top_chart_keyboard
from src.app.services.media_downloaders.seekers.search import YouTubeSearcher
from src.app.utils.i18n import get_translator

user_commands_router = Router()

_DEFAULT_REGION = "global"
_DEFAULT_PERIOD = "today"

_REGION_EMOJI = {
    "global":     "🌍",
    "russia":     "🇷🇺",
    "uzbekistan": "🇺🇿",
    "english":    "🇺🇸",
}

_PERIOD_LABEL = {
    "today": "Bugun",
    "week":  "Hafta",
    "month": "Oy",
}


def _top_header(region: str, period: str) -> str:
    emoji = _REGION_EMOJI.get(region, "🌍")
    period_label = _PERIOD_LABEL.get(period, period.capitalize())
    return (
        f"🏆 <b>Top Musiqalar</b>\n"
        f"{emoji} <b>{region.capitalize()}</b>  •  📅 <b>{period_label}</b>\n\n"
        f"Trекni bosib yuklab oling 👇"
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
    except Exception:
        # Message text unchanged — just update keyboard
        await callback.message.edit_reply_markup(reply_markup=kb)

    await callback.answer()


@user_commands_router.callback_query(F.data.startswith("page:"))
async def page_handler(callback: CallbackQuery, lang: str):
    _ = get_translator(lang).gettext

    searcher = YouTubeSearcher()
    songs = await searcher.get_top_music(limit=50)
    _, page_s = callback.data.split(":")
    page = int(page_s)
    kb = songs_keyboard(songs, page=page)

    await callback.message.edit_text(text=_("Top popular songs"), reply_markup=kb)


@user_commands_router.callback_query(F.data.in_(["close", "delete_list_music"]))
async def close_handler(callback: CallbackQuery):
    await callback.message.delete()


@user_commands_router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()
