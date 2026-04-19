# main/plugins/pyroplug.py - FIXED: Universal private chat support + topics
import asyncio
import os
from .. import bot as Drone
from pyrogram import Client
from pyrogram.errors import PeerIdInvalid, UserNotParticipant, ChannelPrivate
import pyrogram.utils as utils

# ---------- FIX: Patch Pyrogram for newer chat ID formats ----------
def get_peer_type_fixed(peer_id: int) -> str:
    peer_id_str = str(peer_id)
    if not peer_id_str.startswith("-"):
        return "user"
    elif peer_id_str.startswith("-100"):
        return "channel"
    else:
        return "chat"

utils.get_peer_type = get_peer_type_fixed
# --------------------------------------------------------------------

def thumbnail(sender):
    if os.path.exists(f'{sender}.jpg'):
        return f'{sender}.jpg'
    else:
        return None

async def get_msg(userbot, client, bot, sender, edit_id, msg_link, i):
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]

    # Parse the link
    parts = msg_link.rstrip('/').split('/')
    msg_id = int(parts[-1]) + int(i)

    edit = await client.edit_message_text(sender, edit_id, "🔍 Resolving chat...")

    try:
        # Determine chat ID based on link type
        if 't.me/c/' in msg_link:
            # Private channel: format = https://t.me/c/3270489384/[thread_id/]msg_id
            raw_id = parts[4]
            chat_id = int(f"-100{raw_id}")
        elif 't.me/b/' in msg_link:
            # Bot link (rarely used)
            chat_id = parts[4]
        else:
            # Public username: t.me/username/msg_id
            chat_id = parts[3] if len(parts) > 3 else parts[2]

        # Get chat entity
        chat = await userbot.get_chat(chat_id)

        # Copy the message
        await userbot.copy_message(
            sender,
            chat.id,
            msg_id
        )
        await edit.delete()

    except (PeerIdInvalid, ChannelPrivate, UserNotParticipant) as e:
        await edit.edit(
            f"❌ Cannot access chat.\n\n"
            f"Error: {type(e).__name__}\n\n"
            f"Make sure the userbot account is a member of this channel."
        )
    except Exception as e:
        await edit.edit(f"❌ Failed: {type(e).__name__}: {e}")

async def get_bulk_msg(userbot, client, sender, msg_link, i):
    x = await client.send_message(sender, "⏳ Processing...")
    await get_msg(userbot, client, Drone, sender, x.id, msg_link, i)
