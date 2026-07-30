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

# Quality icon mapping — matches quality constants in search.py
_QUALITY_ICON: Dict[str, str] = {
    "official": "✅",
    "live":     "🎤",
    "cover":    "🎸",
    "karaoke":  "🎹",
    "normal":   "🎵",
}

# Max bytes for music_name in callback_data (64 total - prefix "pop:" = 4 bytes)
_MAX_MUSIC_NAME_BYTES = 59
# Max bytes for title in MusicCD
_MAX_TITLE_BYTES = 40

# Telegram button text practical limit
_BTN_TEXT_LIMIT = 60


def _safe_callback_value(text: str, max_bytes: int) -> str:
    """Sanitize and truncate text for use in callback_data."""
    text = text.replace(":", "")
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def _build_track_label(music: dict) -> str:
    """
    Build a rich button label for a track.
    Format: "✅ Artist — Title · 3:45"
    """
    quality = music.get("quality", "normal")
    icon = _QUALITY_ICON.get(quality, "🎵")

    artist      = (music.get("artist") or "").strip()
    clean_title = (music.get("clean_title") or music.get("title") or "").strip()
    duration    = music.get("duration") or ""

    body  = f"{artist} — {clean_title}" if artist else clean_title
    label = f"{icon} {body}"
    if duration:
        label = f"{label} · {duration}"

    if len(label) > _BTN_TEXT_LIMIT:
        if duration:
            suffix   = f" · {duration}"
            max_body = _BTN_TEXT_LIMIT - len(icon) - 1 - len(suffix)
            body     = body[:max(4, max_body - 1)] + "…"
            label    = f"{icon} {body}{suffix}"
        else:
            label = label[:_BTN_TEXT_LIMIT - 1] + "…"

    return label


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
        InlineKeyboardButton(text="🔊 mp3", callback_data=AudioCD(action="download_audio").pack())
    )
    return keyboard_builder.as_markup()


def music_keyboards(music_list: list) -> InlineKeyboardMarkup:
    """
    Rich track list keyboard.
    Each track gets its own full-width row: icon + artist + title + duration.
    """
    keyboard_builder = InlineKeyboardBuilder()

    for music in music_list:
        label = _build_track_label(music)
        raw_title  = music.get("title") or ""
        safe_title = _safe_callback_value(raw_title, _MAX_TITLE_BYTES)
        keyboard_builder.row(
            InlineKeyboardButton(
                text=label,
                callback_data=MusicCD(video_id=music["id"], title=safe_title).pack()
            )
        )

    keyboard_builder.row(InlineKeyboardButton(text="❌", callback_data="delete_list_music"))
    return keyboard_builder.as_markup()


def songs_keyboard(tracks: List[Dict[str, str]], page: int = 1) -> InlineKeyboardMarkup:
    inline_keyboard: List[List[InlineKeyboardButton]] = []
    start = (page - 1) * 10
    for i, t in enumerate(tracks[start:start + 10], start=start):
        label = f"{i + 1}. {t.get('artist', 'Unknown')} — {t.get('title', 'Unknown')}"
        if len(label) > 64:
            label = label[:61] + "..."
        search_query = _safe_callback_value(f"{t.get('artist', '')} {t.get('title', '')}", _MAX_MUSIC_NAME_BYTES)
        inline_keyboard.append([InlineKeyboardButton(text=label, callback_data=TopPopularMusicCD(music_name=search_query).pack())])

    total_pages = (len(tracks) + 9) // 10 if tracks else 1
    nav: List[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"page:{page - 1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"page:{page + 1}"))
    if nav:
        inline_keyboard.append(nav)
    inline_keyboard.append([InlineKeyboardButton(text="❌", callback_data="close")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def top_chart_keyboard(
    tracks: List[Dict[str, str]],
    region: str,
    period: str,
    page: int = 1,
) -> InlineKeyboardMarkup:
    inline_keyboard: List[List[InlineKeyboardButton]] = []

    # Region selector
    region_row: List[InlineKeyboardButton] = []
    for key, label in REGION_LABELS.items():
        text = f"[ {label} ]" if key == region else label
        region_row.append(InlineKeyboardButton(text=text, callback_data=TopFilterCD(region=key, period=period, page=1).pack()))
    inline_keyboard.append(region_row)

    # Period selector
    period_row: List[InlineKeyboardButton] = []
    for key, label in PERIOD_LABELS.items():
        text = f"[ {label} ]" if key == period else label
        period_row.append(InlineKeyboardButton(text=text, callback_data=TopFilterCD(region=region, period=key, page=1).pack()))
    inline_keyboard.append(period_row)

    # Track list (10 per page)
    start = (page - 1) * 10
    for i, t in enumerate(tracks[start:start + 10], start=start):
        medal  = _MEDALS.get(i, "")
        prefix = f"{medal} " if medal else f"{i + 1}. "
        artist = t.get("artist", "Unknown")
        title  = t.get("title", "Unknown")
        label  = f"{prefix}{artist} — {title}"
        if len(label) > 64:
            label = label[:61] + "..."
        sq = _safe_callback_value(f"{artist} {title}", _MAX_MUSIC_NAME_BYTES)
        inline_keyboard.append([InlineKeyboardButton(text=label, callback_data=TopPopularMusicCD(music_name=sq).pack())])

    # Pagination
    total_pages = (len(tracks) + 9) // 10 if tracks else 1
    nav: List[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=TopFilterCD(region=region, period=period, page=page - 1).pack()))
    nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=TopFilterCD(region=region, period=period, page=page + 1).pack()))
    inline_keyboard.append(nav)
    inline_keyboard.append([InlineKeyboardButton(text="❌", callback_data="close")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def audio_keyboard(lang: str, file_id: str = "", title: str = "", is_favorite: bool = False):
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    if file_id:
        keyboard_builder.row(
            InlineKeyboardButton(text="❤️" if is_favorite else "🤍", callback_data=FavoriteCD(action="remove" if is_favorite else "add").pack()),
            InlineKeyboardButton(text="⊞", callback_data="effects"),
        )
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
        keyboard_builder.row(InlineKeyboardButton(text="⊞", callback_data="effects"))
    return keyboard_builder.as_markup()


def auido_effect_kbd(actions: str, lang: str):
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.row(
        InlineKeyboardButton(text="🎧 8D", callback_data=MediaEffectsCD(actions=actions, effect=GeneralEffectAction.EFFECT_8D).pack()),
        InlineKeyboardButton(text="🥁 Concert Hall", callback_data=MediaEffectsCD(actions=actions, effect=GeneralEffectAction.EFFECT_CONCERT_HALL).pack()),
    )
    keyboard_builder.row(
        InlineKeyboardButton(text="🐌 Slowed", callback_data=MediaEffectsCD(actions=actions, effect=GeneralEffectAction.EFFECT_SLOWED).pack()),
        InlineKeyboardButton(text="🎤 Minus", callback_data=MediaEffectsCD(actions=actions, effect=GeneralEffectAction.EFFECT_SPEED).pack()),
    )
    return keyboard_builder.as_markup()


def not_channels_button(channels: list) -> InlineKeyboardMarkup:
    keyboard_builder = InlineKeyboardBuilder()
    for channel in channels:
        channel_name = channel[1] if len(channel) > 1 else "Channel"
        channel_url  = channel[2] if len(channel) > 2 else None
        if channel_url:
            url = channel_url if channel_url.startswith("http") else f"https://t.me/{channel_url.lstrip('@')}"
        else:
            url = f"https://t.me/c/{str(channel[0]).lstrip('-100')}"
        keyboard_builder.row(InlineKeyboardButton(text=f"📢 {channel_name}", url=url))
    keyboard_builder.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"))
    return keyboard_builder.as_markup()


def admin_main_menu(lang: str):
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.row(InlineKeyboardButton(text=_("Mandatory subscription"), callback_data=AdminMainMenuCD(actions=AdminMenuActions.MANDATORY_SUBSCRIPTIONS_MENU).pack()))
    keyboard_builder.row(InlineKeyboardButton(text=_("Referals"), callback_data=AdminMainMenuCD(actions=AdminMenuActions.REFERALS_MENU).pack()))
    keyboard_builder.row(InlineKeyboardButton(text=_("Statistics"), callback_data=AdminMainMenuCD(actions=AdminMenuActions.STATISTICS_MENU).pack()))
    keyboard_builder.row(InlineKeyboardButton(text=_("Broadcast"), callback_data="boroadcasting"))
    keyboard_builder.row(InlineKeyboardButton(text=_("Quit from admin menu"), callback_data="quit_from_admin_menu"))
    return keyboard_builder.as_markup()


def create_mandatory_subs_keyboard(channels: list, bots: list, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    buttons = []
    if channels:
        buttons.append([InlineKeyboardButton(text=_("Channels start border"), callback_data="some_data")])
        for channel in channels:
            buttons.append([InlineKeyboardButton(text=channel[1], callback_data=ChannelCD(id=channel[0], action=ChannelActions.CHANNEL_SET_UP_MENU).pack())])
    if bots:
        buttons.append([InlineKeyboardButton(text=_("Bots start border"), callback_data="some_data")])
        for bot in bots:
            buttons.append([InlineKeyboardButton(text=bot[0], callback_data=BotCD(username=bot[1], action=BotActions.BOT_SET_UP_MENU).pack())])
    buttons.append([
        InlineKeyboardButton(text=_("Add channel"), callback_data=AddMandatorySubscriptionCD(actions=AddMandatorySubscriptionActions.ADD_CHANNEL).pack()),
        InlineKeyboardButton(text=_("Add bot"), callback_data=AddMandatorySubscriptionCD(actions=AddMandatorySubscriptionActions.ADD_BOT).pack()),
    ])
    buttons.append([InlineKeyboardButton(text=_("Back to admin menu"), callback_data="back_to_admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def referals_menu_kbd(referals: list, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    buttons = []
    for referal in referals:
        buttons.append([InlineKeyboardButton(text=referal[1] + " - " + str(referal[2]), callback_data=ReferralCD(referral_id=referal[0], action=ReferalsActions.REFERALS_SET_UP_MENU).pack())])
    buttons.append([InlineKeyboardButton(text=_("Add referal"), callback_data=ReferralCD(referral_id="some_id", action=ReferalsActions.ADD_REFERALS).pack())])
    buttons.append([InlineKeyboardButton(text=_("Back to admin menu"), callback_data="back_to_admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def modified_channel_menu(channel_id: int, is_mandatory: bool, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    if is_mandatory:
        op_btn = InlineKeyboardButton(text=_("Delete in mandatory sub"), callback_data=ChannelCD(id=channel_id, action=ChannelActions.DELETE_IN_MANDATORY_SUB).pack())
    else:
        op_btn = InlineKeyboardButton(text=_("Add in mandatry sub"), callback_data=ChannelCD(id=channel_id, action=ChannelActions.ADD_IN_MANDATORY_SUB).pack())
    keyboard_builder.row(InlineKeyboardButton(text=_("Delete channel"), callback_data=ChannelCD(id=channel_id, action=ChannelActions.DELETE_CHANNEL).pack()), op_btn)
    keyboard_builder.row(InlineKeyboardButton(text=_("Back"), callback_data="back_to_menu"))
    return keyboard_builder.as_markup()


def modified_bot_menu(is_op: bool, username: str, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    if is_op:
        op_btn = InlineKeyboardButton(text=_("Delete in mandatory sub"), callback_data=BotCD(username=username, action=BotActions.DELETE_IN_MANDATORY_SUB).pack())
    else:
        op_btn = InlineKeyboardButton(text=_("Add in mandatory sub"), callback_data=BotCD(username=username, action=BotActions.ADD_IN_MANDATORY_SUB).pack())
    keyboard_builder.row(op_btn, InlineKeyboardButton(text=_("Delete bot"), callback_data=BotCD(username=username, action=BotActions.DELETE_BOT).pack()))
    keyboard_builder.row(InlineKeyboardButton(text=_("Back"), callback_data="back_to_menu"))
    return keyboard_builder.as_markup()


def delite_channel_menu(channel_id: int, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.row(
        InlineKeyboardButton(text=_("Delete"), callback_data=ChannelCD(id=channel_id, action=ChannelActions.SURE_DELETE).pack()),
        InlineKeyboardButton(text=_("Not delete"), callback_data=ChannelCD(id=channel_id, action=ChannelActions.NOT_SURE_DELETE).pack()),
    )
    return keyboard_builder.as_markup()


def delite_referral_menu(referral_id: str, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.row(
        InlineKeyboardButton(text=_("Delete"), callback_data=ReferralCD(referral_id=referral_id, action=ReferalsActions.SURE_DELETE).pack()),
        InlineKeyboardButton(text=_("Not delete"), callback_data=ReferralCD(referral_id=referral_id, action=ReferalsActions.NOT_SURE_DELETE).pack()),
    )
    return keyboard_builder.as_markup()


def back_to_channel_menu(lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.row(InlineKeyboardButton(text=_("Back to admin menu"), callback_data="back_to_admin_menu"))
    return keyboard_builder.as_markup()


def back_to_subscription_menu(lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.row(InlineKeyboardButton(text=_("Back to admin menu"), callback_data="back_to_admin_menu"))
    return keyboard_builder.as_markup()


def add_chanel_url_defult(lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.row(InlineKeyboardButton(text=_("Default url"), callback_data=AddMandatorySubscriptionCD(actions=AddMandatorySubscriptionActions.ADD_CHANNEL_URL_DEFULT).pack()))
    keyboard_builder.row(InlineKeyboardButton(text=_("Back to admin menu"), callback_data="back_to_admin_menu"))
    return keyboard_builder.as_markup()


def delite_bot_menu(username: str, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.row(
        InlineKeyboardButton(text=_("Delete"), callback_data=BotCD(username=username, action=BotActions.SURE_DELETE).pack()),
        InlineKeyboardButton(text=_("Not delete"), callback_data=BotCD(username=username, action=BotActions.NOT_SURE_DELETE).pack()),
    )
    return keyboard_builder.as_markup()


def add_bot_url_defult(lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.row(InlineKeyboardButton(text=_("Default url"), callback_data=AddMandatorySubscriptionCD(actions=AddMandatorySubscriptionActions.ADD_BOT_URL_DEFULT).pack()))
    keyboard_builder.row(InlineKeyboardButton(text=_("Back to admin menu"), callback_data="back_to_admin_menu"))
    return keyboard_builder.as_markup()


def menu_referrals_kb(referral_id: str, lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.row(InlineKeyboardButton(text=_("Delete"), callback_data=ReferralCD(referral_id=referral_id, action=ReferalsActions.DELETE_REFERAL).pack()))
    keyboard_builder.row(InlineKeyboardButton(text=_("Back to admin menu"), callback_data="back_to_admin_menu"))
    return keyboard_builder.as_markup()


def back_to_admin_menu_keyboards(lang: str) -> InlineKeyboardMarkup:
    _ = get_translator(lang).gettext
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.row(InlineKeyboardButton(text=_("Back to admin menu"), callback_data="back_to_admin_menu"))
    return keyboard_builder.as_markup()
