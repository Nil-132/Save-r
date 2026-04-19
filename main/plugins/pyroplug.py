#Github.com/Vasusen-code - FIXED FOR CHAT_ID_INVALID ERROR

import time, os

from .. import bot as Drone
from main.plugins.progress import progress_for_pyrogram
from main.plugins.helpers import screenshot

from pyrogram import Client
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid, UserNotParticipant
from pyrogram.enums import MessageMediaType
from ethon.pyfunc import video_metadata
from ethon.telefunc import fast_upload
from telethon.tl.types import DocumentAttributeVideo

def thumbnail(sender):
    return f'{sender}.jpg' if os.path.exists(f'{sender}.jpg') else None

async def get_msg(userbot, client, bot, sender, edit_id, msg_link, i):
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]
    
    msg_id = int(msg_link.split("/")[-1]) + int(i)

    is_private = 't.me/c/' in msg_link or 't.me/b/' in msg_link

    if is_private:
        if 't.me/b/' in msg_link:
            chat = str(msg_link.split("/")[-2])
        else:
            chat = int('-100' + str(msg_link.split("/")[-2]))
    else:
        chat = msg_link.split("t.me")[1].split("/")[1]

    edit = await client.edit_message_text(sender, edit_id, "Cloning...")

    try:
        if is_private:
            # ← THIS LINE FIXES CHAT_ID_INVALID
            await userbot.get_chat(chat)      # Forces Telegram to cache the peer ID
            await userbot.copy_message(sender, chat, msg_id)
        else:
            await client.copy_message(sender, chat, msg_id)
        
        await edit.delete()
        return

    except Exception as e:
        error_str = str(e)
        print(f"Real error for {msg_link}: {error_str}")
        
        await client.edit_message_text(sender, edit_id, 
            f'Failed to save: `{msg_link}`\n\n'
            f'Error: {error_str}\n\n'
            'Make sure your userbot account has **opened** this group/channel at least once.'
        )

async def get_bulk_msg(userbot, client, sender, msg_link, i):
    x = await client.send_message(sender, "Processing!")
    await get_msg(userbot, client, Drone, sender, x.id, msg_link, i)
