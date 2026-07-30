from typing import List, Dict

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, SwitchInlineQueryChosenChat
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.app.keyboards.callback_data import (
    MusicCD, SearchMusicInVideoCD, AudioCD, MediaEffectsCD, AdminMainMenuCD,
    ChannelCD, BotCD, AddMandatorySubscriptionCD, ReferralCD,
    TopPopularMusicCD, FavoriteCD, TopFilterCD,
)
from src.app.utils.enums.actions import AdminMenuActions, ChannelActions, BotActions, AddMandatorySubscriptionActions, \
    ReferalsActions
from src.app.utils.enums.general import GeneralEffectAction
from src.app.utils.i18n import get_translator

# Medal emojis for top-3
_MEDALS = {0: "🥇", 1: "🥈", 2: "🥉"}

REGION_LABELS: Dict[str, str] = {
    "global":     "🌍 Global",
    "russia":     "🇷🇺 Russia",
    "uzbekistan": "🇺🇿 Uzbek",
    "english":    "🇺🇸 English",
}

PERIOD_LABELS: Dict[str, str] = {
    "today": "🔥 Bugun",
    "week":  "📅 Hafta",
    "month": "📆 Oy",
}


def video_keyboards(lang: str):
    _ = get_translator(lang).gettext

    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.row(
        InlineKeyboardButton(
            text=_("Download Music"),
            callback_data=SearchMusicInVideoCD(action="search_music").pack()
        )
    )
    keyboard_builder.row(
        InlineKeyboardButton(
            text="🔊 mp3",
            callback_data=AudioCD(action="download_audio").pack()
        )
    )
    return keyboard_builder.as_markup()


def music_keyboards(music_list: list) -> InlineKeyboardMarkup:
    keyboard_builder = InlineKeyboardBuilder()

    for i, music in enumerate(music_list, start=1):
        keyboard_builder.add(
            InlineKeyboardButton(
                text=str(i),
                callback_data=MusicCD(video_id=music["id"]).pack()
            )
        )

    keyboard_builder.adjust(5)
    keyboard_builder.row(
        InlineKeyboardButton(text="❌", callback_data="delete_list_music")
    )

    return keyboard_builder.as_markup()


def songs_keyboard(tracks: List[Dict[str, str]], page: int = 1) -> InlineKeyboardMarkup:
    inline_keyboard: List[List[InlineKeyboardButton]] = []

    start = (page - 1) * 10
    end = start + 10
    sliced = tracks[start:end]
    for i, t in enumerate(sliced, start=start):
        label = f"{i + 1}. {t.get('artist', 'Unknown')} — {t.get('title', 'Unknown')}"
        if len(label) > 64:
            label = label[:61] + "..."
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=TopPopularMusicCD(music_name=label[:40]).pack()
                )
            ]
        )

    total = len(tracks)
    total_pages = (total + 10 - 1) // 10 if total else 1
    nav_buttons: List[InlineKeyboardButton] = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"page:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"page:{page + 1}"))
    if nav_buttons:
        inline_keyboard.append(nav_buttons)

    inline_keyboard.append([InlineKeyboardButton(text="❌", callback_data="close")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def top_chart_keyboard(
    tracks: List[Dict[str, str]],
    region: str,
    period: str,
    page: int = 1,
) -> InlineKeyboardMarkup:
    """Rich /top keyboard: region tabs, period tabs, track list, pagination."""
    inline_keyboard: List[List[InlineKeyboardButton]] = []

    # ── Row 1: Region selector ──────────────────────────────────────────
    region_row: List[InlineKeyboardButton] = []
    for key, label in REGION_LABELS.items():
        text = f"[ {label} ]" if key == region else label
        region_row.append(
            InlineKeyboardButton(
                text=text,
                callback_data=TopFilterCD(region=key, period=period, page=1).pack(),
            )
        )
    inline_keyboard.append(region_row)

    # ── Row 2: Period selector ──────────────────────────────────────────
    period_row: List[InlineKeyboardButton] = []
    for key, label in PERIOD_LABELS.items():
        text = f"[ {label} ]" if key == period else label
        period_row.append(
            InlineKeyboardButton(
                text=text,
                callback_data=TopFilterCD(region=region, period=key, page=1).pack(),
            )
        )
    inline_keyboard.append(period_row)

    # ── Track list (10 per page) ────────────────────────────────────────
    start = (page - 1) * 10
    end = start + 10
    for i, t in enumerate(tracks[start:end], start=start):
        medal = _MEDALS.get(i, "")
        prefix = f"{medal} " if medal else f"{i + 1}. "
        artist = t.get("artist", "Unknown")
        title = t.get("title", "Unknown")
        label = f"{prefix}{artist} — {title}"
        if len(label) > 64:
            label = label[:61] + "..."
        search_query = f"{artist} {title}"
        if len(search_query) > 40:
            search_query = search_query[:40]
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=TopPopularMusicCD(music_name=search_query).pack(),
                )
            ]
        )

    # ── Pagination ──────────────────────────────────────────────────────
    total = len(tracks)
    total_pages = (total + 9) // 10 if total else 1
    nav: List[InlineKeyboardButton] = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=TopFilterCD(region=region, period=period, page=page - 1).pack(),
            )
        )
    nav.append(
        InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
    )
    if page < total_pages:
        nav.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=TopFilterCD(region=region, period=period, page=page + 1).pack(),
            )
        )
    inline_keyboard.append(nav)

    # ── Close ───────────────────────────────────────────────────────────
    inline_keyboard.append([InlineKeyboardButton(text="❌", callback_data="close")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def audio_keyboard(lang: str, file_id: str = "", title: str = "", is_favorite: bool = False):
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()

    if file_id:
        fav_btn = InlineKeyboardButton(
            text="❤️" if is_favorite else "🤍",
            callback_data=FavoriteCD(action="remove" if is_favorite else "add").pack()
        )
        effects_btn = InlineKeyboardButton(text="⊞", callback_data="effects")
        keyboard_builder.row(fav_btn, effects_btn)

        keyboard_builder.row(
            InlineKeyboardButton(
                text=_("Guruhga Qo'shish") + " +",
                switch_inline_query_chosen_chat=SwitchInlineQueryChosenChat(
                    query=file_id,
                    allow_group_chats=True,
                    allow_channel_posts=True,
                    allow_bot_chats=False,
                    allow_user_chats=True,
                )
            )
        )
    else:
        keyboard_builder.row(
            InlineKeyboardButton(text="⊞", callback_data="effects")
        )

    return keyboard_builder.as_markup()


def auido_effect_kbd(actions: str, lang: str):
    keyboard_builder = InlineKeyboardBuilder()

    keyboard_builder.row(
        InlineKeyboardButton(
            text="🎧 8D",
            callback_data=MediaEffectsCD(actions=actions, effect=GeneralEffectAction.EFFECT_8D).pack()
        ),
        InlineKeyboardButton(
            text="🥁 Concert Hall",
            callback_data=MediaEffectsCD(actions=actions, effect=GeneralEffectAction.EFFECT_CONCERT_HALL).pack()
        )
    )
    keyboard_builder.row(
        InlineKeyboardButton(
            text="🐌 Slowed",
            callback_data=MediaEffectsCD(actions=actions, effect=GeneralEffectAction.EFFECT_SLOWED).pack()
        ),
        InlineKeyboardButton(
            text="🎤 Minus",
            callback_data=MediaEffectsCD(actions=actions, effect=GeneralEffectAction.EFFECT_SPEED).pack()
        )
    )
    return keyboard_builder.as_markup()


def admin_main_menu(lang: str):
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()

    keyboard_builder.row(
        InlineKeyboardButton(
            text=_("Mandatory subscription"),
            callback_data=AdminMainMenuCD(actions=AdminMenuActions.MANDATORY_SUBSCRIPTIONS_MENU).pack()
        )
    )
    keyboard_builder.row(
        InlineKeyboardButton(
            text=_("Referals"),
            callback_data=AdminMainMenuCD(actions=AdminMenuActions.REFERALS_MENU).pack()
        )
    )
    keyboard_builder.row(
        InlineKeyboardButton(
            text=_("Statistics"),
            callback_data=AdminMainMenuCD(actions=AdminMenuActions.STATISTICS_MENU).pack()
        )
    )
    keyboard_builder.row(
        InlineKeyboardButton(text=_("Broadcast"), callback_data="boroadcasting")
    )
    keyboard_builder.row(
        InlineKeyboardButton(text=_("Quit from admin menu"), callback_data="quit_from_admin_menu")
    )
    return keyboard_builder.as_markup()


def create_mandatory_subs_keyboard(channels: list, bots: list, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    buttons = []

    if channels:
        buttons.append([InlineKeyboardButton(text=_("Channels start border"), callback_data="some_data")])
        for channel in channels:
            buttons.append([
                InlineKeyboardButton(
                    text=channel[1],
                    callback_data=ChannelCD(id=channel[0], action=ChannelActions.CHANNEL_SET_UP_MENU).pack(),
                )
            ])

    if bots:
        buttons.append([InlineKeyboardButton(text=_("Bots start border"), callback_data="some_data")])
        for bot in bots:
            buttons.append([
                InlineKeyboardButton(
                    text=bot[0],
                    callback_data=BotCD(username=bot[1], action=BotActions.BOT_SET_UP_MENU).pack(),
                )
            ])

    buttons.append([
        InlineKeyboardButton(
            text=_("Add channel"),
            callback_data=AddMandatorySubscriptionCD(actions=AddMandatorySubscriptionActions.ADD_CHANNEL).pack()
        ),
        InlineKeyboardButton(
            text=_("Add bot"),
            callback_data=AddMandatorySubscriptionCD(actions=AddMandatorySubscriptionActions.ADD_BOT).pack()
        ),
    ])
    buttons.append([InlineKeyboardButton(text=_("Back to admin menu"), callback_data="back_to_admin_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def referals_menu_kbd(referals: list, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    buttons = []

    for referal in referals:
        buttons.append([
            InlineKeyboardButton(
                text=referal[1] + " - " + str(referal[2]),
                callback_data=ReferralCD(referral_id=referal[0], action=ReferalsActions.REFERALS_SET_UP_MENU).pack(),
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text=_("Add referal"),
            callback_data=ReferralCD(referral_id="some_id", action=ReferalsActions.ADD_REFERALS).pack()
        )
    ])
    buttons.append([InlineKeyboardButton(text=_("Back to admin menu"), callback_data="back_to_admin_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def modified_channel_menu(channel_id: int, is_mandatory: bool, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()

    if is_mandatory:
        remove_for_op = InlineKeyboardButton(
            text=_("Delete in mandatory sub"),
            callback_data=ChannelCD(id=channel_id, action=ChannelActions.DELETE_IN_MANDATORY_SUB).pack(),
        )
    else:
        remove_for_op = InlineKeyboardButton(
            text=_("Add in mandatry sub"),
            callback_data=ChannelCD(id=channel_id, action=ChannelActions.ADD_IN_MANDATORY_SUB).pack(),
        )

    delete_channel = InlineKeyboardButton(
        text=_("Delete channel"),
        callback_data=ChannelCD(id=channel_id, action=ChannelActions.DELETE_CHANNEL).pack(),
    )
    back = InlineKeyboardButton(text=_("Back"), callback_data="back_to_menu")
    keyboard_builder.row(delete_channel, remove_for_op)
    keyboard_builder.row(back)

    return keyboard_builder.as_markup()


def modified_bot_menu(is_op: bool, username: str, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()

    if is_op:
        remove_for_op = InlineKeyboardButton(
            text=_("Delete in mandatory sub"),
            callback_data=BotCD(username=username, action=BotActions.DELETE_IN_MANDATORY_SUB).pack(),
        )
    else:
        remove_for_op = InlineKeyboardButton(
            text=_("Add in mandatory sub"),
            callback_data=BotCD(username=username, action=BotActions.ADD_IN_MANDATORY_SUB).pack(),
        )

    delete_channel = InlineKeyboardButton(
        text=_("Delete bot"),
        callback_data=BotCD(username=username, action=BotActions.DELETE_BOT).pack(),
    )
    back = InlineKeyboardButton(text=_("Back"), callback_data="back_to_menu")
    keyboard_builder.row(remove_for_op, delete_channel)
    keyboard_builder.row(back)

    return keyboard_builder.as_markup()


def delite_channel_menu(channel_id: int, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()

    sure = InlineKeyboardButton(
        text=_("Delete"),
        callback_data=ChannelCD(id=channel_id, action=ChannelActions.SURE_DELETE).pack(),
    )
    not_sure = InlineKeyboardButton(
        text=_("Not delete"),
        callback_data=ChannelCD(id=channel_id, action=ChannelActions.NOT_SURE_DELETE).pack(),
    )
    keyboard_builder.row(sure, not_sure)

    return keyboard_builder.as_markup()


def delite_referral_menu(referral_id: str, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    inline_keyboard = InlineKeyboardBuilder()

    sure = InlineKeyboardButton(
        text=_("Delete"),
        callback_data=ReferralCD(referral_id=referral_id, action=ReferalsActions.SURE_DELETE).pack(),
    )
    not_sure = InlineKeyboardButton(
        text=_("Not delete"),
        callback_data=ReferralCD(referral_id=referral_id, action=ReferalsActions.NOT_SURE_DELETE).pack(),
    )
    inline_keyboard.row(sure, not_sure)

    return inline_keyboard.as_markup()
