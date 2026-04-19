#Github.com/Vasusen-code - FIXED FOR PRIVATE CHANNELS (Error fixed)

import asyncio, time, os

from .. import bot as Drone
from main.plugins.progress import progress_for_pyrogram
from main.plugins.helpers import screenshot

from pyrogram import Client, filters
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid, UserNotParticipant
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
    """ userbot: PyrogramUserBot
    client: PyrogramBotClient
    bot: TelethonBotClient """
    
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

    # PRIVATE CHANNELS - Force peer resolution + copy
    if is_private:
        try:
            await userbot.get_chat(chat)          # This caches the peer ID
            print(f"✅ Peer resolved for private chat: {chat}")
            await userbot.copy_message(sender, chat, msg_id)
            await edit.delete()
            return
        except Exception as e:
            print(f"Private copy failed: {e}")

    # PUBLIC CHANNELS or fallback
    try:
        await client.copy_message(sender, chat, msg_id)
        await edit.delete()
        return
    except Exception as e:
        print(f"Copy failed: {e}")

    # Final safe error message (fixed - no more 'e' reference error)
    error_msg = str(e) if 'e' in locals() else "Unknown error"
    await client.edit_message_text(sender, edit_id, 
        f'Failed to save: `{msg_link}`\n\nError: {error_msg}\n\n'
        'Make sure your userbot account is joined to the channel/group.'
    )

async def get_bulk_msg(userbot, client, sender, msg_link, i):
    x = await client.send_message(sender, "Processing!")
    await get_msg(userbot, client, Drone, sender, x.id, msg_link, i)
