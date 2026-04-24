# main/plugins/pyroplug.py - DEBUGGING IMPROVED
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
    Tries multiple formats and logs which one works.
    """
    clean_id = re.sub(r'[^0-9]', '', chat_id_str)
    if not clean_id:
        raise ValueError("Invalid chat ID")

    errors = []

    # Attempt 1: -100 prefix (most common for channels/supergroups)
    try:
        cid = int(f"-100{clean_id}")
        chat = await userbot.get_chat(cid)
        print(f"✅ Resolved via -100: {cid}")
        return chat
    except Exception as e:
        errors.append(f"-100: {e}")

    # Attempt 2: raw positive integer
    try:
        cid = int(clean_id)
        chat = await userbot.get_chat(cid)
        print(f"✅ Resolved via raw int: {cid}")
        return chat
    except Exception as e:
        errors.append(f"raw: {e}")

    # Attempt 3: - prefix (old normal groups)
    try:
        cid = int(f"-{clean_id}")
        chat = await userbot.get_chat(cid)
        print(f"✅ Resolved via - : {cid}")
        return chat
    except Exception as e:
        errors.append(f"-: {e}")

    # Attempt 4: resolve_peer
    try:
        peer = await userbot.resolve_peer(f"-100{clean_id}")
        chat = await userbot.get_chat(peer)
        print(f"✅ Resolved via resolve_peer")
        return chat
    except Exception as e:
        errors.append(f"resolve_peer: {e}")

    # If all fail, show the exact errors in the bot message
    raise PeerIdInvalid(
        f"Could not resolve chat ID {clean_id}. Errors: {errors}"
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
        is_private = False
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
        # 1) Resolve the chat
        if is_private and 't.me/b/' not in msg_link:
            await edit.edit("🔍 Resolving private chat...")
            chat = await resolve_chat_id(userbot, chat_id_str)
        else:
            await edit.edit("🔍 Resolving public chat...")
            chat = await userbot.get_chat(chat_id_str)

        # 2) Fetch the message
        await edit.edit("📥 Fetching message...")
        try:
            message = await userbot.get_messages(chat.id, msg_id)
        except PeerIdInvalid:
            await edit.edit("❌ Access denied when fetching the message. "
                            "The chat was found, but this message might be from a "
                            "private chat you aren't a member of, or the message ID is wrong.")
            return
        if not message:
            await edit.edit("❌ Message not found (may be deleted).")
            return

        # 3) Try copy (fast)
        try:
            await userbot.copy_message(sender, chat.id, msg_id)
            await edit.delete()
            return
        except ChatForwardsRestricted:
            await edit.edit("🚫 Forward restricted. Downloading & re-uploading...")
        except FloodWait as e:
            await edit.edit(f"⏳ Flood wait: {e.value} seconds.")
            return

        # 4) No media → just text
        if not message.media:
            await client.send_message(sender, message.text or "")
            await edit.delete()
            return

        # 5) Download & re-upload
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
        await edit.edit(f"❌ Invalid username: `{chat_id_str}`. Check the link.")
    except PeerIdInvalid as e:
        await edit.edit(f"❌ PeerIdInvalid: {str(e)}\n\n"
                        "🔹 The chat was not found or the account is not a member.\n"
                        "🔹 Make sure the session belongs to the right account and it has joined the chat.")
    except ChannelPrivate:
        await edit.edit("❌ Channel is private and the userbot is not a member.")
    except UserNotParticipant:
        await edit.edit("❌ Userbot is not a member of this chat.")
    except Exception as e:
        await edit.edit(f"❌ Unexpected error: {type(e).__name__}: {str(e)}")


async def get_bulk_msg(userbot, client, sender, msg_link, i):
    x = await client.send_message(sender, "⏳ Processing...")
    await get_msg(userbot, client, Drone, sender, x.id, msg_link, i)
