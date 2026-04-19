# FINAL FIXED __init__.py for Nil-132/Save-r

print("🚀 main/__init__.py started")

import asyncio
import sys
from pyrogram import Client
from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError
from decouple import config

# Load config
try:
    API_ID = config("API_ID", cast=int)
    API_HASH = config("API_HASH")
    BOT_TOKEN = config("BOT_TOKEN")
    SESSION = config("SESSION")
    FORCESUB = config("FORCESUB", default=None)
    AUTH = config("AUTH", default=None, cast=int)
    print("✅ Config loaded")
except Exception as e:
    print(f"❌ Config error: {e}")
    sys.exit(1)

# Telethon Bot - define 'bot' at module level
bot = None

async def start_bot():
    global bot
    print("🔄 Starting Telethon Bot...")
    bot = TelegramClient('bot', API_ID, API_HASH)
    while True:
        try:
            await bot.start(bot_token=BOT_TOKEN)
            print("✅ Telethon Bot started!")
            return bot
        except FloodWaitError as e:
            wait = e.seconds + 10
            print(f"⏳ Flood wait {wait}s...")
            await asyncio.sleep(wait)
        except Exception as e:
            print(f"❌ Telethon error: {e}")
            await asyncio.sleep(30)

# Run startup
loop = asyncio.get_event_loop()
bot = loop.run_until_complete(start_bot())

# Pyrogram Userbot
print("🔄 Starting Userbot...")
userbot = Client("saverestricted", session_string=SESSION, api_id=API_ID, api_hash=API_HASH)
userbot.start()
print("✅ Userbot started!")

# Pyrogram Bot
print("🔄 Starting Pyrogram Bot...")
Bot = Client("SaveRestricted", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)
Bot.start()
print("✅ Pyrogram Bot started!")

print("🚀 ALL CLIENTS READY! Bot is online.")
