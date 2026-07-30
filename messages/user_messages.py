def cancel():
    return "✖️ Cancel"

def welcome_message():
    return (
        "🔥 Здравствуйте. Добро пожаловать в бота. Через бота можно скачать следующее:\n\n"
        "• <b>Instagram</b> - <a href='https://instagram.com'>пост и IGTV + аудио</a>;\n"
        "• <b>TikTok</b> - <a href='https://tiktok.com'>видео без водяного знака + аудио</a>;\n"
        "• <b>YouTube</b> - <a href='https://youtube.com'>Видео и shorts + аудио</a>;\n"
        "• <b>Snapchat</b> - <a href='https://snapchat.com'>видео без водяного знака + аудио</a>;\n"
        "• <b>Likee</b> - <a href='https://likee.video'>видео без водяного знака + аудио</a>;\n"
        "• <b>Pinterest</b> - <a href='https://pinterest.com'>видео и изображение без водяных знаков</a>\n"
        "• <b>Threads</b> - <a href='https://threads.net'>видео и изображение + аудио</a>\n\n"
        "🚀 Отправьте мне ссылку на видео, которое хотите скачать!\n"
        "😎 Бот тоже может работать в группах!"
    )

def settings():
    return (
        " ⚙️ Settings \n"
        "Use the buttons below to customize how downloads are sent. "
        "These changes apply only to your account."
    )

def settings_private_only():
    return (
        "Settings are available only in private chat. Open DM with the bot to change preferences."
    )

def get_field_text(field: str):
    texts = {
        "captions": (
            " 📝 Descriptions \n"
            "Show or hide post captions in downloaded media. "
            "Some sources may not provide captions."
        ),
        "delete_message": (
            " 🗑️ Delete Messages \n"
            "Automatically remove your link once the download is handled."
        ),
        "info_buttons": (
            " ℹ️ Info Buttons \n"
            "Toggle additional info buttons under downloaded media."
        ),
        "url_button": (
            " 🔗 URL Button \n"
            "Show or hide a button with the original post link."
        ),
        "audio_button": (
            " 🎧 MP3 Button \n"
            "Toggle the Download MP3 button when audio is available."
        ),
        "file_button": (
            " 📄 File Button \n"
            "Show or hide the Download File button under videos to get original uncompressed files on demand."
        ),
        "video_quality": (
            " 🎬 Video Quality \n"
            "Select your preferred video download resolution:\n\n"
            "• Best (1080p+): Maximum possible resolution.\n"
            "• Balanced (720p): Great balance of quality and speed.\n"
            "• Data Saver (480p): Faster downloads with minimal data usage."
        ),
        "as_document": (
            " 📄 Send as File \n"
            "When enabled, videos and photos will be sent as uncompressed documents (.mp4 / .jpg) preserving 100% original quality."
        ),
        "audio_format": (
            " 🎵 Audio Format \n"
            "Choose default audio format for music downloads:\n\n"
            "• MP3: Standard universal audio format.\n"
            "• M4A (AAC): High quality compact format for iOS & Mac.\n"
            "• FLAC / Original: Uncompressed lossless audio where available."
        ),
    }
    return texts.get(field, " Settings \nThis option doesn't have a description yet.")

def captions(user_captions, post_caption, bot_url, *, limit: int = 1024):
    import html

    def _truncate_escaped(value: str, max_len: int) -> str:
        if max_len <= 0:
            return ""
        if len(value) <= max_len:
            return value
        cut = value[:max_len]
        amp = cut.rfind("&")
        semi = cut.rfind(";")
        if amp > semi:
            cut = cut[:amp]
        return cut

    footer = ' 🚀 Powered by MaxLoad '.format(bot_url=bot_url)

    if user_captions == "on" and post_caption:
        body = html.escape(str(post_caption))
        sep = "\n\n"
        # Keep footer intact; only shrink the body.
        budget = limit - len(sep) - len(footer)
        if budget <= 0:
            return _truncate_escaped(footer, limit)

        if len(body) > budget:
            suffix = "…"
            body = _truncate_escaped(body, max(0, budget - len(suffix))).rstrip() + suffix

        return f"{body}{sep}{footer}"

    return _truncate_escaped(footer, limit)

def downloading_audio_status():
    return "🎧 Downloading audio..."

def downloading_video_status():
    return " 🎬 Downloading video..."

def uploading_status():
    return "☁️ Uploading file to Telegram..."

def retrying_again_status(next_attempt: int, total_attempts: int):
    return f"Error, trying again... ({next_attempt}/{total_attempts})"

def dm_start_required():
    return " 🔒 First-time setup needed: open DM, press Start, and resend the link."

def duplicate_link_processing():
    return "This link is already being processed. Wait a few seconds."

def duplicate_link_recently_processed():
    return "This link was just handled. If you still need it, try again in a few seconds."

def settings_admin_only():
    return "Only group admins can open /settings in group chats."

def invalid_settings_option():
    return "Invalid settings option."

def join_group(chat_title: str) -> str:
    return (
        "🔥 Здравствуйте. Добро пожаловать в бота. Через бота можно скачать следующее:\n\n"
        "• <b>Instagram</b> - <a href='https://instagram.com'>пост и IGTV + аудио</a>;\n"
        "• <b>TikTok</b> - <a href='https://tiktok.com'>видео без водяного знака + аудио</a>;\n"
        "• <b>YouTube</b> - <a href='https://youtube.com'>Видео и shorts + аудио</a>;\n"
        "• <b>Snapchat</b> - <a href='https://snapchat.com'>видео без водяного знака + аудио</a>;\n"
        "• <b>Likee</b> - <a href='https://likee.video'>видео без водяного знака + аудио</a>;\n"
        "• <b>Pinterest</b> - <a href='https://pinterest.com'>видео и изображение без водяных знаков</a>\n"
        "• <b>Threads</b> - <a href='https://threads.net'>видео и изображение + аудио</a>\n\n"
        "🚀 Отправьте мне ссылку на видео, которое хотите скачать!\n"
        "😎 Бот тоже может работать в группах!"
    )

def admin_rights_granted(chat_title: str) -> str:
    return (
        "Thanks for granting admin rights in {chat_title} 🌸 \n"
        "💻 I'll keep downloads running smoothly."
    ).format(chat_title=chat_title)

def keyboard_removed():
    return "Reply keyboard removed."

def tiktok_live_not_supported():
    return "TikTok LIVE streams aren't supported yet. Send a regular TikTok post link."

def delete_permission_warning():
    return "Auto-delete failed: missing permission to delete messages in this chat. Please grant delete permissions or turn off auto-delete in settings."

def stats_temporarily_unavailable():
    return "Couldn't generate stats right now. Please try again later."

def no_queue_metrics_yet():
    return "No queue metrics yet."

def open_bot_for_audio():
    return "Open the bot in private chat to download audio."

def audio_fetch_failed():
    return "Failed to get audio info. Please try again later."

def audio_download_failed():
    return "Audio download failed. Please try again later."

def spotify_metadata_failed():
    return "Couldn't read this Spotify track. Please check the link and try again."

def spotify_source_not_found():
    return "Couldn't find a matching audio source for this Spotify track."

def inline_album_link_invalid():
    return "This album link is expired or invalid."

def inline_photo_title(service_name: str):
    return f"{service_name} Photo"

def inline_photo_description():
    return "Single photo"

def inline_album_title(service_name: str):
    return f"{service_name} Album"

def inline_album_description():
    return "Open full album in bot"

def inline_open_full_album_button():
    return "Open Full Album"

def inline_photos_title(service_name: str):
    return f"{service_name} Photos"

def inline_photos_not_supported(service_name: str):
    return f"{service_name} photos are not supported inline."

def inline_send_video_button():
    return "Send video inline"

def inline_send_video_prompt(service_name: str):
    return f"{service_name} video is being prepared...\nIf it does not start automatically, tap the button below."

def inline_send_audio_prompt(service_name: str):
    return f"{service_name} audio is being prepared...\nIf it does not start automatically, tap the button below."

def inline_video_already_processing():
    return "This inline video is already being prepared."

def inline_video_already_sent():
    return "This inline video was already sent."

def supported_sites_message(bot_username: str | None = None):
    return help_message(bot_username)

def category_settings_text(category: str) -> str:
    if category == "media":
        return (
            " 🎬 Media & Quality Settings \n\n"
            "Configure video resolution, file format, and audio options:"
        )
    if category == "appearance":
        return (
            " 🎨 Appearance & Buttons \n\n"
            "Customize post descriptions, original URL links, and action buttons:"
        )
    if category == "chat":
        return (
            " 💬 Chat & Clean-up \n\n"
            "Manage group chat behavior and message cleanup settings:"
        )
    return settings()

def help_message(bot_username: str | None = None) -> str:
    username = bot_username or "MaxLoadBot"
    return (
        " 📖 MaxLoad Help & Guide \n\n"
        "Send one link or paste multiple links in one message. The bot will automatically extract and deliver the media.\n\n"
        " 📷 Instagram & Threads \n"
        "• Download Posts, Reels, IGTV & Stories\n"
        "• Photo carousels & multi-media albums\n"
        "• Copy link via Share → Copy link \n\n"
        " 🎵 TikTok \n"
        "• Watermark-free video downloads\n"
        "• Photo carousels & slideshows\n"
        "• MP3 audio extraction supported \n\n"
        " ▶️ YouTube & YouTube Music \n"
        "• YouTube Shorts & regular Videos\n"
        "• High quality audio & video streams\n"
        "• Tap MP3 button to download audio \n\n"
        " 🐦 X / Twitter & 📌 Pinterest \n"
        "• X / Twitter videos, GIFs & images\n"
        "• Pinterest video and image Pins \n\n"
        " 🎧 SoundCloud & 🟢 Spotify \n"
        "• High quality SoundCloud audio tracks\n"
        "• Spotify track matching & audio download \n\n"
        f" ⚡ Inline Mode \n"
        f"• Type @{username} [link] in any chat\n"
        "• Instant preview and direct media sharing \n\n"
        " 📦 Batch Downloading \n"
        "• Paste up to 6 links in a single message\n"
        "• Delivered one by one to keep chat clean "
    )

def referral_message(bot_username: str, user_id: int, invited_count: int) -> str:
    username = bot_username or "MaxLoadBot"
    ref_link = f"https://t.me/{username}?start=ref_{user_id}"
    return (
        " 👥 Your Referral Program \n\n"
        "Invite friends to use MaxLoad! Share your personal referral link:\n"
        f" {ref_link} \n\n"
        f"Users invited: {invited_count} "
    )

def batch_links_started(processed_total: int, detected_total: int | None = None):
    if detected_total is not None and detected_total > processed_total:
        return (
            f"Found {detected_total} supported links. "
            f"I'll process the first {processed_total} one by one so the chat stays readable."
        )
    return f"Found {processed_total} supported links. I'll process them one by one so the chat stays readable."

def batch_link_progress(current: int, total: int, service_name: str):
    return f"Processing link {current}/{total}: {service_name}..."

def batch_links_finished(total: int):
    return f"Finished batch processing for {total} links."

def timeout_error():
    return "Request timed out. The source may be slow right now. Please try again later."

def something_went_wrong():
    return (
        "Couldn't process this link right now.\n"
        "It may be private, deleted, region-limited, or temporarily blocked by the source. "
        "Please try again later."
    )

def video_too_large():
    return "The video is too large for Telegram. Try a shorter video or an MP3/audio option if available."

def audio_too_large():
    return "The audio is too large for Telegram. Try a shorter track or another source link."

def nothing_found():
    return "No media found. The link may be private, removed, or from an unsupported source."

def build_rate_limit_text(wait_seconds: float | None = None) -> str:
    if wait_seconds and wait_seconds > 0:
        return f"Too many requests. Please wait {int(wait_seconds)} seconds before trying again."
    return "Too many requests. Please wait a moment before trying again."

def build_queue_busy_text() -> str:
    return "The download queue is full right now. Please try again in a few seconds."
