from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from src.app.keyboards.inline import auido_effect_kbd, songs_keyboard
from src.app.services.media_downloaders.seekers.search import YouTubeSearcher
from src.app.utils.i18n import get_translator

user_commands_router = Router()

DEFAULT_REGION = "Uzbekistan"


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
async def handled_command_top(message: Message, lang: str):
    _ = get_translator(lang).gettext
    searcher = YouTubeSearcher()

    # Allow custom region: /top Russia  (defaults to Uzbekistan)
    args = message.text.split(maxsplit=1)
    region = args[1].strip() if len(args) > 1 else DEFAULT_REGION

    songs = await searcher.get_top_by_region(region, limit=50)

    if not songs:
        await message.answer("Top musiqalarni olishda xatolik yuz berdi.")
        return

    await message.answer(_("Top songs"), reply_markup=songs_keyboard(songs, page=1))


@user_commands_router.callback_query(F.data.startswith("page:"))
async def page_handler(callback: CallbackQuery, lang: str):
    _ = get_translator(lang).gettext
    searcher = YouTubeSearcher()

    # Region is not stored in callback; use default
    songs = await searcher.get_top_by_region(DEFAULT_REGION, limit=50)
    _, page_s = callback.data.split(":")
    page = int(page_s)

    await callback.message.edit_text(
        text=_("Top popular songs"),
        reply_markup=songs_keyboard(songs, page=page),
    )


@user_commands_router.callback_query(F.data.in_(["close", "delete_list_music"]))
async def close_handler(callback: CallbackQuery):
    await callback.message.delete()
