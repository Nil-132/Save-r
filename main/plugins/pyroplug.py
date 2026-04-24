# main/plugins/pyroplug.py - IMPROVED RESOLVE with resolve_peer
import asyncio
import os
import re
import tempfile
from .. import bot as Drone
from pyrogram import Client
from pyrogram.errors import (
    PeerIdInvalid, UserNotParticipant, ChannelPrivate,
    ChatForwardsRestricted, FloodWait, UsernameInvalid
)
from pyrogram.enums import MessageMediaType

def thumbnail(sender):
    if os.path.exists(f'{sender}.jpg'):
        return f'{sender}.jpg'
    return None


async def resolve_chat_id(userbot, chat_id_str):
    """
    Robustly resolves a private numeric chat ID (from t.me/c/ links).
    Tries multiple formats: -100 prefix (supergroup), raw int, - prefix (old group),
    and finally resolve_peer.
    """
    # Keep only digits
    clean_id = re.sub(r'[^0-9]', '', chat_id_str)
    if not clean_id:
        raise ValueError("Invalid chat ID")

    errors_list = []

    # Attempt 1: -100 prefix (the most common for private channels/supergroups)
    try:
        return await userbot.get_chat(int(f"-100{clean_id}"))
    except Exception as e:
        errors_list.append(f"-100:{e}")

    # Attempt 2: raw positive integer (almost never works, but try)
    try:
        return await userbot.get_chat(int(clean_id))
    except Exception as e:
        errors_list.append(f"raw:{e}")

    # Attempt 3: - prefix (old standard groups)
    try:
        return await userbot.get_chat(int(f"-{clean_id}"))
    except Exception as e:
        errors_list.append(f"-:{e}")

    # Attempt 4: Use resolve_peer (works even if chat is not in dialog list)
    try:
        # resolve_peer accepts string like "-100123456789"
        peer = await userbot.resolve_peer(f"-100{clean_id}")
        return await userbot.get_chat(peer)
    except Exception as e:
        errors_list.append(f"resolve_peer:{e}")

    raise PeerIdInvalid(
        f"Could not resolve chat ID {clean_id}.\nAttempts: {errors_list}"
    )


async def get_msg(userbot, client, bot, sender, edit_id, msg_link, i):
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]

    edit = await client.edit_message_text(sender, edit_id, "🔍 Parsing link...")

    parts = msg_link.split('/')
    # Identify chat identifier
    if 't.me/b/' in msg_link:
        # Bot link: t.me/b/bot_username/message_id
        chat_id_str = parts[4]          # bot username
        is_private = False              # treat as public username
    elif 't.me/c/' in msg_link:
        # Private channel: t.me/c/chat_id/message_id
        chat_id_str = parts[4]          # numeric ID
        is_private = True
    else:
        # Public link: t.me/username/message_id
        chat_id_str = parts[3]          # username
        is_private = False

    msg_id = int(parts[-1]) + int(i)

    try:
        if is_private and 't.me/b/' not in msg_link:
            chat = await resolve_chat_id(userbot, chat_id_str)
        else:
            chat = await userbot.get_chat(chat_id_str)

        await edit.edit("📥 Fetching message...")
        message = await userbot.get_messages(chat.id, msg_id)
        if not message:
            await edit.edit("❌ Message not found (may be deleted).")
            return

        # Try fast copy first
        try:
            await userbot.copy_message(sender, chat.id, msg_id)
            await edit.delete()
            return
        except ChatForwardsRestricted:
            await edit.edit("🚫 Forward restricted. Downloading & re-uploading...")
        except FloodWait as e:
            await edit.edit(f"⏳ Flood wait: {e.value} seconds.")
            return

        # If no media, just send text
        if not message.media:
            await client.send_message(sender, message.text or "")
            await edit.delete()
            return

        # Determine extension
        ext = ""
        if message.photo:
            ext = ".jpg"
        elif message.video:
            ext = ".mp4"
        elif message.document and message.document.file_name:
            ext = os.path.splitext(message.document.file_name)[1]
        elif message.audio:
            ext = ".mp3"
        elif message.voice:
            ext = ".ogg"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            file_path = tmp.name

        await edit.edit("📥 Downloading...")
        file_path = await userbot.download_media(message, file_name=file_path)

        await edit.edit("📤 Uploading...")
        caption = message.caption or message.text or ""

        if message.media == MessageMediaType.PHOTO:
            await client.send_photo(sender, file_path, caption=caption)
        elif message.media == MessageMediaType.VIDEO:
            await client.send_video(sender, file_path, caption=caption, thumb=thumbnail(sender))
        elif message.media == MessageMediaType.DOCUMENT:
            await client.send_document(sender, file_path, caption=caption, thumb=thumbnail(sender))
        elif message.media == MessageMediaType.AUDIO:
            await client.send_audio(sender, file_path, caption=caption, thumb=thumbnail(sender))
        elif message.media == MessageMediaType.VOICE:
            await client.send_voice(sender, file_path, caption=caption)
        else:
            await client.send_document(sender, file_path, caption=caption)

        os.unlink(file_path)
        await edit.delete()

    except UsernameInvalid:
        await edit.edit("❌ Invalid username or link format.")
    except (PeerIdInvalid, ChannelPrivate, UserNotParticipant) as e:
        await edit.edit(f"❌ Access denied: {type(e).__name__}. Ensure userbot is a member.")
    except Exception as e:
        await edit.edit(f"❌ Unexpected error: {type(e).__name__}: {str(e)}")


async def get_bulk_msg(userbot, client, sender, msg_link, i):
    x = await client.send_message(sender, "⏳ Processing...")
    await get_msg(userbot, client, Drone, sender, x.id, msg_link, i)
