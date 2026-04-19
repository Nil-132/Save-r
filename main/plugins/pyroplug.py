# main/plugins/pyroplug.py - HANDLES FORWARD RESTRICTIONS
import asyncio
import os
import tempfile
from .. import bot as Drone
from pyrogram import Client
from pyrogram.errors import (
    PeerIdInvalid, UserNotParticipant, ChannelPrivate,
    ChatForwardsRestricted, FloodWait
)
from pyrogram.types import Message
from pyrogram.enums import MessageMediaType

def thumbnail(sender):
    if os.path.exists(f'{sender}.jpg'):
        return f'{sender}.jpg'
    else:
        return None

async def get_msg(userbot, client, bot, sender, edit_id, msg_link, i):
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]

    # Extract message ID (last numeric part)
    parts = msg_link.rstrip('/').split('/')
    msg_id = int(parts[-1]) + int(i)

    edit = await client.edit_message_text(sender, edit_id, "🔍 Resolving chat...")

    try:
        # Get chat entity using the full link
        chat = await userbot.get_chat(msg_link)
    except (PeerIdInvalid, ChannelPrivate, UserNotParticipant) as e:
        await edit.edit(f"❌ Cannot access chat: {type(e).__name__}")
        return
    except Exception as e:
        await edit.edit(f"❌ Unexpected error: {e}")
        return

    try:
        # Fetch the message
        message: Message = await userbot.get_messages(chat.id, msg_id)
        if not message:
            await edit.edit("❌ Message not found (may be deleted).")
            return

        # Attempt 1: Try copy_message (fast)
        try:
            await userbot.copy_message(sender, chat.id, msg_id)
            await edit.delete()
            return
        except ChatForwardsRestricted:
            await edit.edit("🚫 Forwarding restricted. Downloading & re-uploading...")
        except FloodWait as e:
            await edit.edit(f"⏳ Flood wait: {e.value} seconds. Please wait.")
            return

        # Attempt 2: Manual download & re-upload (bypasses forward restriction)
        if message.media:
            # Download media to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=get_file_extension(message)) as tmp:
                file_path = tmp.name

            await edit.edit("📥 Downloading media...")
            file_path = await userbot.download_media(message, file_name=file_path)

            await edit.edit("📤 Uploading as new file...")
            # Prepare caption (preserve original text)
            caption = message.caption or message.text or ""

            # Send as document/photo based on media type
            if message.media == MessageMediaType.PHOTO:
                await client.send_photo(sender, file_path, caption=caption)
            elif message.media == MessageMediaType.VIDEO:
                await client.send_video(sender, file_path, caption=caption,
                                       thumb=thumbnail(sender))
            elif message.media == MessageMediaType.DOCUMENT:
                await client.send_document(sender, file_path, caption=caption,
                                          thumb=thumbnail(sender))
            elif message.media == MessageMediaType.AUDIO:
                await client.send_audio(sender, file_path, caption=caption,
                                       thumb=thumbnail(sender))
            elif message.media == MessageMediaType.VOICE:
                await client.send_voice(sender, file_path, caption=caption)
            else:
                await client.send_document(sender, file_path, caption=caption)

            # Clean up temp file
            os.unlink(file_path)
            await edit.delete()
        else:
            # No media, just text
            await client.send_message(sender, message.text or "")
            await edit.delete()

    except Exception as e:
        await edit.edit(f"❌ Failed: {type(e).__name__}: {str(e)}")

def get_file_extension(message: Message) -> str:
    """Guess file extension from media type."""
    if message.photo:
        return ".jpg"
    elif message.video:
        return ".mp4"
    elif message.document:
        # Try to get extension from original filename
        if message.document.file_name:
            return os.path.splitext(message.document.file_name)[1]
        return ""
    elif message.audio:
        return ".mp3"
    elif message.voice:
        return ".ogg"
    return ""

async def get_bulk_msg(userbot, client, sender, msg_link, i):
    x = await client.send_message(sender, "⏳ Processing...")
    await get_msg(userbot, client, Drone, sender, x.id, msg_link, i)
