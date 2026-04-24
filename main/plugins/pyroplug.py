# main/plugins/pyroplug.py - Forward-first + fallback to download (full features)
import asyncio, time, os, re, tempfile
from .. import bot as Drone
from main.plugins.progress import progress_for_pyrogram
from main.plugins.helpers import screenshot, get_link

from pyrogram import Client
from pyrogram.errors import (
    ChatForwardsRestricted, FloodWait, PeerIdInvalid,
    ChannelPrivate, UserNotParticipant, UsernameInvalid
)
from pyrogram.enums import MessageMediaType
from ethon.pyfunc import video_metadata
from ethon.telefunc import fast_upload
from telethon.tl.types import DocumentAttributeVideo

def thumbnail(sender):
    if os.path.exists(f'{sender}.jpg'):
        return f'{sender}.jpg'
    return None


async def resolve_private_chat(userbot, chat_id_str):
    """
    Convert a numeric private chat ID (from t.me/c/ links) to a Pyrogram chat object.
    Handles missing -100 prefix gracefully.
    """
    clean_id = re.sub(r'[^0-9]', '', chat_id_str)
    if not clean_id:
        raise ValueError("Invalid chat ID")

    # Try the standard -100 prefix first
    try:
        return await userbot.get_chat(int(f"-100{clean_id}"))
    except Exception:
        pass

    # Fallback: try raw int, then - prefix
    for prefix in ("", "-"):
        try:
            cid = int(f"{prefix}{clean_id}")
            return await userbot.get_chat(cid)
        except Exception:
            continue

    raise PeerIdInvalid(f"Cannot resolve chat {clean_id}. Userbot may not be a member.")


async def get_msg(userbot, client, bot, sender, edit_id, msg_link, i):
    """
    userbot: Pyrogram userbot (Client)
    client: Pyrogram bot client (Client)
    bot: Telethon bot client (Drone)
    sender: Telegram user ID of the requester
    edit_id: message ID of the "Processing..." message to edit
    msg_link: full link like https://t.me/.../msg_id
    i: offset added to message ID (for batch)
    """
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]

    edit = await client.edit_message_text(sender, edit_id, "🔍 Parsing link...")
    parts = msg_link.split('/')
    msg_id = int(parts[-1]) + int(i)

    # Identify chat identifier
    if 't.me/b/' in msg_link:
        chat_id_str = parts[4]          # bot username
        is_private = False
    elif 't.me/c/' in msg_link:
        chat_id_str = parts[4]          # numeric private ID
        is_private = True
    else:
        chat_id_str = parts[3]          # public username
        is_private = False

    # 1) Resolve the chat
    try:
        if is_private and 't.me/b/' not in msg_link:
            await edit.edit("🔍 Resolving private chat...")
            chat = await resolve_private_chat(userbot, chat_id_str)
        else:
            await edit.edit("🔍 Resolving public chat...")
            chat = await userbot.get_chat(chat_id_str)
    except (UsernameInvalid, PeerIdInvalid, ChannelPrivate, UserNotParticipant) as e:
        await edit.edit(f"❌ Cannot access chat: {type(e).__name__}. Make sure the userbot is a member.")
        return
    except Exception as e:
        await edit.edit(f"❌ Error resolving chat: {str(e)}")
        return

    # 2) Try server‑side forward (copy_message) first – works for all chats
    try:
        await edit.edit("📤 Forwarding...")
        await userbot.copy_message(sender, int(chat.id), msg_id)
        await edit.edit("✅ Forwarded successfully!")
        await asyncio.sleep(1)
        await edit.delete()
        return
    except ChatForwardsRestricted:
        await edit.edit("🚫 Forward restricted, downloading & re-uploading...")
    except FloodWait as e:
        await edit.edit(f"⏳ Flood wait: {e.value} seconds. Please wait.")
        return
    except Exception as e:
        # If forward fails for any other reason, fall through to download
        await edit.edit(f"⚠️ Forward failed ({type(e).__name__}), trying download...")

    # 3) Download & re-upload (because forwarding was blocked or failed)
    height, width, duration, thumb_path = 90, 90, 0, None
    round_message = False

    try:
        msg = await userbot.get_messages(chat.id, msg_id)
        if not msg:
            await edit.edit("❌ Message not found (may be deleted).")
            return

        # Text / webpage only
        if msg.media and msg.media == MessageMediaType.WEB_PAGE:
            await client.send_message(sender, msg.text.markdown if msg.text else "")
            await edit.delete()
            return
        if not msg.media:
            await client.send_message(sender, msg.text.markdown if msg.text else "")
            await edit.delete()
            return

        # Download
        edit = await client.edit_message_text(sender, edit_id, "📥 Downloading...")
        file = await userbot.download_media(
            msg,
            progress=progress_for_pyrogram,
            progress_args=(client, "**DOWNLOADING:**\n", edit, time.time())
        )

        await edit.edit("📤 Preparing to upload...")
        caption = msg.caption if msg.caption else None

        # Media type specific handling
        if msg.media == MessageMediaType.VIDEO_NOTE:
            round_message = True
            data = video_metadata(file)
            height, width, duration = data["height"], data["width"], data["duration"]
            try:
                thumb_path = await screenshot(file, duration, sender)
            except Exception:
                thumb_path = None
            await client.send_video_note(
                chat_id=sender, video_note=file,
                length=height, duration=duration,
                thumb=thumb_path,
                progress=progress_for_pyrogram,
                progress_args=(client, "**UPLOADING:**\n", edit, time.time())
            )
        elif msg.media == MessageMediaType.VIDEO and msg.video.mime_type in ["video/mp4", "video/x-matroska"]:
            data = video_metadata(file)
            height, width, duration = data["height"], data["width"], data["duration"]
            try:
                thumb_path = await screenshot(file, duration, sender)
            except Exception:
                thumb_path = None
            await client.send_video(
                chat_id=sender, video=file,
                caption=caption,
                supports_streaming=True,
                height=height, width=width, duration=duration,
                thumb=thumb_path,
                progress=progress_for_pyrogram,
                progress_args=(client, "**UPLOADING:**\n", edit, time.time())
            )
        elif msg.media == MessageMediaType.PHOTO:
            await bot.send_file(sender, file, caption=caption)
        else:
            # Document, audio, voice, or any other file
            thumb = thumbnail(sender)
            await client.send_document(
                sender, file,
                caption=caption,
                thumb=thumb,
                progress=progress_for_pyrogram,
                progress_args=(client, "**UPLOADING:**\n", edit, time.time())
            )

        # Cleanup
        try:
            os.remove(file)
        except:
            pass
        await edit.delete()

    except FloodWait as fw:
        await client.send_message(sender, f"⏳ Flood wait {fw.x} seconds, try later.")
    except Exception as e:
        # Fallback: use Telethon fast_upload if Pyrogram upload fails
        err_str = str(e)
        if "messages.SendMedia" in err_str or "SaveBigFilePartRequest" in err_str or "SendMediaRequest" in err_str or err_str == "File size equals to 0 B":
            await edit.edit("⚠️ Pyrogram upload failed, trying Telethon...")
            try:
                UT = time.time()
                uploader = await fast_upload(f'{file}', f'{file}', UT, bot, edit, '**UPLOADING:**')
                if msg.media == MessageMediaType.VIDEO and msg.video.mime_type in ["video/mp4", "video/x-matroska"]:
                    attributes = [DocumentAttributeVideo(
                        duration=duration, w=width, h=height, round_message=False, supports_streaming=True
                    )]
                    await bot.send_file(sender, uploader, caption=caption, thumb=thumb_path, attributes=attributes, force_document=False)
                elif msg.media == MessageMediaType.VIDEO_NOTE:
                    attributes = [DocumentAttributeVideo(
                        duration=duration, w=width, h=height, round_message=True, supports_streaming=True
                    )]
                    await bot.send_file(sender, uploader, caption=caption, thumb=thumb_path, attributes=attributes, force_document=False)
                else:
                    await bot.send_file(sender, uploader, caption=caption, thumb=thumb_path, force_document=True)
                await edit.delete()
            except Exception as e2:
                await edit.edit(f"❌ Failed to upload: {str(e2)}")
            finally:
                try:
                    os.remove(file)
                except:
                    pass
        else:
            await edit.edit(f"❌ Failed to save: `{msg_link}`\nError: {str(e)}")
            try:
                os.remove(file)
            except:
                pass


async def get_bulk_msg(userbot, client, sender, msg_link, i):
    x = await client.send_message(sender, "⏳ Processing...")
    await get_msg(userbot, client, Drone, sender, x.id, msg_link, i)
