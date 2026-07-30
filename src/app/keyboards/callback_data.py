from aiogram.filters.callback_data import CallbackData

from src.app.database.queries.channels import ChannelDataBaseActions
from src.app.utils.enums.actions import AdminMenuActions, BotActions, ChannelActions, AddMandatorySubscriptionActions, \
    ReferalsActions
from src.app.utils.enums.general import GeneralEffectAction


class MusicCD(CallbackData, prefix="music"):
    video_id: str
    title: str = ""  # track title for DRM fallback search


class TopPopularMusicCD(CallbackData, prefix="pop"):
    music_name: str


class SearchMusicInVideoCD(CallbackData, prefix="search_music"):
    action: str


class AudioCD(CallbackData, prefix="audio"):
    action: str


class MediaEffectsCD(CallbackData, prefix="media_effect"):
    actions: str
    effect: GeneralEffectAction


class AdminMainMenuCD(CallbackData, prefix="admin_mani_menu"):
    actions: AdminMenuActions


class ChannelCD(CallbackData, prefix="channel"):
    id: int
    action: ChannelActions


class BotCD(CallbackData, prefix="bot"):
    username: str
    action: BotActions


class ReferralCD(CallbackData, prefix="referral"):
    referral_id: str
    action: ReferalsActions


class AddMandatorySubscriptionCD(CallbackData, prefix="mandatory_subscription"):
    actions: AddMandatorySubscriptionActions


# Only action stored — file_id and title are read from call.message.audio at runtime
class FavoriteCD(CallbackData, prefix="fav"):
    action: str  # "add" or "remove"


class TopFilterCD(CallbackData, prefix="topf"):
    region: str   # global | russia | uzbekistan | english
    period: str   # today | week | month
    page: int
