#Github.com-Vasusen-code

import asyncio, time, os

from .. import bot as Drone
from main.plugins.progress import progress_for_pyrogram
from main.plugins.helpers import screenshot

from pyrogram import Client, filters
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid
from pyrogram.enums import MessageMediaType
from ethon.pyfunc import video_metadata
from ethon.telefunc import fast_upload
from telethon.tl.types import DocumentAttributeVideo
from telethon import events

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
    height, width, duration, thumb_path = 90, 90, 0, None

    # FIXED LINK PARSING
    if 't.me/c/' in msg_link or 't.me/b/' in msg_link:
        if 't.me/b/' in msg_link:
            chat = str(msg_link.split("/")[-2])
        else:
            chat = int('-100' + str(msg_link.split("/")[-2]))
    else:
        # Public channel with username
        chat = msg_link.split("t.me")[1].split("/")[1]

    edit = await client.edit_message_text(sender, edit_id, "Cloning...")

    # === MAIN FIX: Try copy_message first (works perfectly for public videos) ===
    try:
        await client.copy_message(sender, chat, msg_id)
        await edit.delete()
        return
    except Exception as e:
        print(f"Copy failed for {msg_link}, trying download method: {e}")

    # === Fallback: Download + Upload (for restricted content) ===
    try:
        msg = await userbot.get_messages(chat, msg_id)

        if msg.empty:
            new_link = f't.me/b/{chat}/{msg_id}'
            return await get_msg(userbot, client, bot, sender, edit_id, new_link, i)

        if msg.text and not msg.media:
            await client.send_message(sender, msg.text.markdown)
            await edit.delete()
            return

        edit = await client.edit_message_text(sender, edit_id, "Trying to Download.")
        file = await userbot.download_media(
            msg,
            progress=progress_for_pyrogram,
            progress_args=(client, "**DOWNLOADING:**\n", edit, time.time())
        )

        await edit.edit('Preparing to Upload!')
        caption = msg.caption if msg.caption else None

        # Video Note
        if msg.media == MessageMediaType.VIDEO_NOTE:
            round_message = True
            data = video_metadata(file)
            height, width, duration = data["height"], data["width"], data["duration"]
            try:
                thumb_path = await screenshot(file, duration, sender)
            except:
                thumb_path = None
            await client.send_video_note(
                chat_id=sender, video_note=file, length=height, duration=duration,
                thumb=thumb_path, progress=progress_for_pyrogram,
                progress_args=(client, '**UPLOADING:**\n', edit, time.time())
            )

        # Regular Video
        elif msg.media == MessageMediaType.VIDEO:
            data = video_metadata(file)
            height, width, duration = data["height"], data["width"], data["duration"]
            try:
                thumb_path = await screenshot(file, duration, sender)
            except:
                thumb_path = None
            await client.send_video(
                chat_id=sender, video=file, caption=caption, supports_streaming=True,
                height=height, width=width, duration=duration, thumb=thumb_path,
                progress=progress_for_pyrogram, progress_args=(client, '**UPLOADING:**\n', edit, time.time())
            )

        # Photo
        elif msg.media == MessageMediaType.PHOTO:
            await bot.send_file(sender, file, caption=caption)

        # Other files
        else:
            thumb_path = thumbnail(sender)
            await client.send_document(
                sender, file, caption=caption, thumb=thumb_path,
                progress=progress_for_pyrogram, progress_args=(client, '**UPLOADING:**\n', edit, time.time())
            )

        # Cleanup
        try:
            os.remove(file)
            if os.path.isfile(file):
                os.remove(file)
        except:
            pass
        await edit.delete()

    except (ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid):
        await client.edit_message_text(sender, edit_id, "Have you joined the channel?")
        return

    except PeerIdInvalid:
        chat = msg_link.split("/")[-3]
        if chat.isdigit():
            new_link = f"t.me/c/{chat}/{msg_id}"
        else:
            new_link = f"t.me/b/{chat}/{msg_id}"
        return await get_msg(userbot, client, bot, sender, edit_id, new_link, i)

    except Exception as e:
        print(f"Final error: {e}")
        await client.edit_message_text(sender, edit_id, f'Failed to save: `{msg_link}`\n\nError: {str(e)}')
        try:
            os.remove(file)
        except:
            pass

async def get_bulk_msg(userbot, client, sender, msg_link, i):
    x = await client.send_message(sender, "Processing!")
    await get_msg(userbot, client, Drone, sender, x.id, msg_link, i)
