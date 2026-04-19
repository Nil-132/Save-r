# main/plugins/pyroplug.py - FULLY FIXED CHAT RESOLUTION
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
from pyrogram.types import Message
from pyrogram.enums import MessageMediaType

def thumbnail(sender):
    if os.path.exists(f'{sender}.jpg'):
        return f'{sender}.jpg'
    else:
        return None

async def resolve_chat_id(userbot, chat_id_str):
    """
    Tries to resolve a chat ID string (numeric) to a valid Pyrogram chat object.
    Handles both -100 prefixed and non-prefixed IDs.
    """
    # Remove any non-numeric characters
    clean_id = re.sub(r'[^0-9]', '', chat_id_str)
    if not clean_id:
        raise ValueError("Invalid chat ID")

    attempts = []
    
    # Attempt 1: Raw integer
    try:
        return await userbot.get_chat(int(clean_id))
    except Exception as e:
        attempts.append(f"raw:{e}")

    # Attempt 2: With -100 prefix (old supergroup)
    try:
        return await userbot.get_chat(int(f"-100{clean_id}"))
    except Exception as e:
        attempts.append(f"-100:{e}")

    # Attempt 3: With - prefix (basic group)
    try:
        return await userbot.get_chat(int(f"-{clean_id}"))
    except Exception as e:
        attempts.append(f"-:{e}")

    raise PeerIdInvalid(f"Could not resolve chat ID {clean_id}. Attempts: {attempts}")

async def get_msg(userbot, client, bot, sender, edit_id, msg_link, i):
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]

    # Parse the link to extract chat ID and message ID
    # Link formats:
    # - Public: https://t.me/username/123
    # - Private: https://t.me/c/3886775796/1889/7755  (thread then msg)
    # - Private simple: https://t.me/c/3886775796/7755

    edit = await client.edit_message_text(sender, edit_id, "🔍 Parsing link...")

    # Extract chat identifier
    if 't.me/c/' in msg_link:
        # Private channel: parts[4] is chat_id
        parts = msg_link.split('/')
        chat_id_str = parts[4]
        is_private = True
    elif 't.me/b/' in msg_link:
        # Bot link
        parts = msg_link.split('/')
        chat_id_str = parts[4]
        is_private = True
    else:
        # Public link: t.me/username/msg_id
        parts = msg_link.split('/')
        chat_id_str = parts[3]  # username
        is_private = False

    # Extract message ID (always the last part)
    msg_id = int(parts[-1]) + int(i)

    try:
        # Resolve chat
        if is_private:
            chat = await resolve_chat_id(userbot, chat_id_str)
        else:
            chat = await userbot.get_chat(chat_id_str)  # public username

        await edit.edit("📥 Fetching message...")
        message: Message = await userbot.get_messages(chat.id, msg_id)
        if not message:
            await edit.edit("❌ Message not found (may be deleted).")
            return

        # Try copy_message first (fast)
        try:
            await userbot.copy_message(sender, chat.id, msg_id)
            await edit.delete()
            return
        except ChatForwardsRestricted:
            await edit.edit("🚫 Forward restricted. Downloading & re-uploading...")
        except FloodWait as e:
            await edit.edit(f"⏳ Flood wait: {e.value} seconds.")
            return

        # Manual download & re-upload (bypasses forward restriction)
        if message.media:
            # Determine file extension
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

            # Send based on media type
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
        else:
            # Text only
            await client.send_message(sender, message.text or "")
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
