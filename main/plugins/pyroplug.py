# Github.com/Vasusen-code - ENHANCED UNIVERSAL VERSION
import asyncio
import os
from .. import bot as Drone
from main.plugins.progress import progress_for_pyrogram
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

async def resolve_chat(userbot, chat_identifier):
    """
    Universal chat resolver that tries multiple methods to find the correct entity.
    Returns the resolved chat object or raises PeerIdInvalid with helpful message.
    """
    errors = []
    
    # Try 1: Direct use of identifier (string username or integer ID)
    try:
        return await userbot.get_chat(chat_identifier)
    except Exception as e:
        errors.append(f"Raw ID/username failed: {e}")

    # Try 2: If numeric, try with -100 prefix (old supergroup format)
    if isinstance(chat_identifier, int) or (isinstance(chat_identifier, str) and chat_identifier.lstrip('-').isdigit()):
        # Ensure we have a string without existing -100
        raw_id = str(chat_identifier).replace('-100', '')
        for prefix in ['-100', '-']:
            try:
                prefixed_id = int(f"{prefix}{raw_id}")
                return await userbot.get_chat(prefixed_id)
            except Exception as e:
                errors.append(f"Prefix {prefix} failed: {e}")
                continue

    # If all attempts fail, raise a clear error
    error_msg = "Unable to resolve chat. Possible reasons:\n"
    error_msg += "- Userbot account is not a member of the private channel/group.\n"
    error_msg += "- The link is invalid or expired.\n"
    error_msg += "- The chat ID format is not recognized.\n"
    error_msg += f"Details: {' | '.join(errors)}"
    raise PeerIdInvalid(error_msg)

async def get_msg(userbot, client, bot, sender, edit_id, msg_link, i):
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]

    # Extract message ID (last numeric part)
    msg_id = int(msg_link.split("/")[-1]) + int(i)
    is_private = 't.me/c/' in msg_link or 't.me/b/' in msg_link

    # Extract chat identifier from link
    if is_private:
        if 't.me/b/' in msg_link:
            # Bot link: t.me/b/bot_username/123
            chat_identifier = msg_link.split("/")[-2]
        else:
            # Private channel link: t.me/c/3886775796/1889
            # Remove any trailing slash and get the numeric ID
            parts = msg_link.split("/")
            chat_identifier = parts[4]  # after /c/
    else:
        # Public link: t.me/username/123
        chat_identifier = msg_link.split("t.me/")[1].split("/")[0]

    edit = await client.edit_message_text(sender, edit_id, "Cloning...")

    try:
        # Resolve chat using the universal resolver
        chat = await resolve_chat(userbot, chat_identifier)
        
        # Copy the message
        await userbot.copy_message(sender, chat.id, msg_id)
        await edit.delete()
        return

    except PeerIdInvalid as e:
        await client.edit_message_text(
            sender,
            edit_id,
            f"❌ Failed to save: `{msg_link}`\n\n"
            f"**Error:** Peer ID invalid.\n\n"
            f"**Solution:** Make sure your userbot account **is a member** of this channel/group.\n\n"
            f"*Technical details: {str(e)}*"
        )
    except UserNotParticipant:
        await client.edit_message_text(
            sender,
            edit_id,
            f"❌ Failed to save: `{msg_link}`\n\n"
            f"**Error:** Userbot is not a participant in this chat.\n\n"
            f"**Action:** Add the userbot account to the channel/group first."
        )
    except Exception as e:
        await client.edit_message_text(
            sender,
            edit_id,
            f"❌ Failed to save: `{msg_link}`\n\n"
            f"**Error:** {type(e).__name__}: {str(e)}"
        )

async def get_bulk_msg(userbot, client, sender, msg_link, i):
    x = await client.send_message(sender, "Processing!")
    await get_msg(userbot, client, Drone, sender, x.id, msg_link, i)
