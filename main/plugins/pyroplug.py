# main/plugins/pyroplug.py - FULLY FIXED with bot link support
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
    """Try to resolve a numeric private chat ID to a valid Pyrogram chat object."""
    clean_id = re.sub(r'[^0-9]', '', chat_id_str)
    if not clean_id:
        raise ValueError("Invalid chat ID")
    
    attempts = []
    # Try raw integer, then -100 prefix (supergroups), then - prefix (normal groups)
    for prefix in ("", "-100", "-"):
        try:
            cid = int(f"{prefix}{clean_id}")
            return await userbot.get_chat(cid)
        except Exception as e:
            attempts.append(f"{prefix}:{e}")
    raise PeerIdInvalid(f"Could not resolve chat ID {clean_id}. Attempts: {attempts}")

async def get_msg(userbot, client, bot, sender, edit_id, msg_link, i):
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]

    edit = await client.edit_message_text(sender, edit_id, "🔍 Parsing link...")

    # Split link into parts
    parts = msg_link.split('/')
    # Extract chat identifier
    if 't.me/b/' in msg_link:
        # Bot link: t.me/b/bot_username/message_id
        chat_id_str = parts[4]          # bot username
        is_private = False              # treat as public username for get_chat
    elif 't.me/c/' in msg_link:
        # Private channel: t.me/c/chat_id/message_id
        chat_id_str = parts[4]          # numeric ID
        is_private = True
    else:
        # Public link: t.me/username/message_id
        chat_id_str = parts[3]          # username
        is_private = False

    # Message ID is always the last part + offset
    msg_id = int(parts[-1]) + int(i)

    try:
        if is_private and 't.me/b/' not in msg_link:
            chat = await resolve_chat_id(userbot, chat_id_str)
        else:
            # Public username or bot username
            chat = await userbot.get_chat(chat_id_str)

        await edit.edit("📥 Fetching message...")
        message = await userbot.get_messages(chat.id, msg_id)
        if not message:
            await edit.edit("❌ Message not found (may be deleted).")
            return

        # Fast forward: try copy first
        try:
            await userbot.copy_message(sender, chat.id, msg_id)
            await edit.delete()
            return
        except ChatForwardsRestricted:
            await edit.edit("🚫 Forward restricted. Downloading & re-uploading...")
        except FloodWait as e:
            await edit.edit(f"⏳ Flood wait: {e.value} seconds.")
            return

        # Download & re-upload (bypasses forward restriction)
        if not message.media:
            # Text-only message
            await client.send_message(sender, message.text or "")
            await edit.delete()
            return

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

    except UsernameInvalid:
        await edit.edit("❌ Invalid username or link format.")
    except (PeerIdInvalid, ChannelPrivate, UserNotParticipant) as e:
        await edit.edit(f"❌ Access denied: {type(e).__name__}. Ensure userbot is a member.")
    except Exception as e:
        await edit.edit(f"❌ Unexpected error: {type(e).__name__}: {str(e)}")

async def get_bulk_msg(userbot, client, sender, msg_link, i):
    x = await client.send_message(sender, "⏳ Processing...")
    await get_msg(userbot, client, Drone, sender, x.id, msg_link, i)
