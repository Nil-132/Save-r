# Github.com/Vasusen-code - FIXED UNIVERSAL VERSION
import asyncio
import time
import os
from .. import bot as Drone
from main.plugins.progress import progress_for_pyrogram
from main.plugins.helpers import screenshot
from pyrogram import Client, filters
from pyrogram.errors import (
    ChannelBanned, ChannelInvalid, ChannelPrivate,
    ChatIdInvalid, ChatInvalid, PeerIdInvalid, UserNotParticipant
)
from pyrogram.enums import MessageMediaType
from ethon.pyfunc import video_metadata
from ethon.telefunc import fast_upload
from telethon.tl.types import DocumentAttributeVideo


def thumbnail(sender):
    if os.path.exists(f'{sender}.jpg'):
        return f'{sender}.jpg'
    else:
        return None


async def get_msg(userbot, client, bot, sender, edit_id, msg_link, i):
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]

    msg_id = int(msg_link.split("/")[-1]) + int(i)
    is_private = 't.me/c/' in msg_link or 't.me/b/' in msg_link

    # ---------- FIXED: Universal Chat ID Resolution ----------
    if is_private:
        # Extract the raw ID from the URL without forcing any prefix
        if 't.me/b/' in msg_link:
            # For bot links: t.me/b/bot_username/123
            chat = str(msg_link.split("/")[-2])
        else:
            # For private channel links: t.me/c/3270489384/268293
            # Just use the number as it is - Telethon/Pyrogram will resolve it correctly
            chat = int(msg_link.split("/")[-2])
    else:
        # For public links: t.me/username/123
        chat = msg_link.split("t.me/")[1].split("/")[0]
    # ---------------------------------------------------------

    edit = await client.edit_message_text(sender, edit_id, "Cloning...")

    try:
        if is_private:
            # FIX: Use the correct entity resolution method
            # This works for both old (-100) and new (no -100) private channel IDs
            try:
                # First attempt: resolve using get_chat with the raw ID
                await userbot.get_chat(chat)
            except PeerIdInvalid:
                # If that fails, try with the -100 prefix (for older channels)
                if not str(chat).startswith('-100'):
                    chat = int(f'-100{chat}')
                await userbot.get_chat(chat)

            # Now copy the message
            await userbot.copy_message(sender, chat, msg_id)
        else:
            await client.copy_message(sender, chat, msg_id)

        await edit.delete()
        return

    except Exception as e:
        print(f"Real error while saving {msg_link}: {e}")
        await client.edit_message_text(
            sender,
            edit_id,
            f'Failed to save: `{msg_link}`\n\nError: {str(e)}\n\n'
            'Make sure your userbot account is joined to the channel/group.'
        )


async def get_bulk_msg(userbot, client, sender, msg_link, i):
    x = await client.send_message(sender, "Processing!")
    await get_msg(userbot, client, Drone, sender, x.id, msg_link, i)
