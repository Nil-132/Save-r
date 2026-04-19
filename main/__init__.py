# DEBUG VERSION - Github.com/Vasusen-code

print("🚀 main/__init__.py is being executed...")

import asyncio, sys, time
from pyrogram import Client
from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError
from decouple import config

print("✅ All imports successful")

# Load environment variables
try:
    API_ID = config("API_ID", cast=int)
    API_HASH = config("API_HASH")
    BOT_TOKEN = config("BOT_TOKEN")
    SESSION = config("SESSION")
    FORCESUB = config("FORCESUB", default=None)
    AUTH = config("AUTH", default=None, cast=int)
    print("✅ All environment variables loaded successfully")
    print(f"   API_ID: {API_ID} | SESSION length: {len(SESSION) if SESSION else 0}")
except Exception as e:
    print(f"❌ ERROR loading environment variables: {e}")
    sys.exit(1)

# Telethon Bot with flood wait handling
async def start_telethon_bot():
    print("🔄 Starting Telethon Bot...")
    bot = TelegramClient('bot', API_ID, API_HASH)
    while True:
        try:
            await bot.start(bot_token=BOT_TOKEN)
            print("✅ Telethon Bot started successfully!")
            return bot
        except FloodWaitError as e:
            wait = e.seconds + 10
            print(f"⏳ FloodWaitError: Waiting {wait} seconds...")
            await asyncio.sleep(wait)
        except Exception as e:
            print(f"❌ Telethon start error: {e}")
            await asyncio.sleep(30)

# Run async startup
loop = asyncio.get_event_loop()
bot = loop.run_until_complete(start_telethon_bot())

# Pyrogram Userbot
print("🔄 Starting Pyrogram Userbot...")
userbot = Client(
    "saverestricted",
    session_string=SESSION,
    api_id=API_ID,
    api_hash=API_HASH
)
try:
    userbot.start()
    print("✅ Pyrogram Userbot started successfully!")
except Exception as e:
    print(f"❌ Userbot Error: {e}")
    sys.exit(1)

# Pyrogram Bot Client
print("🔄 Starting Pyrogram Bot Client...")
Bot = Client(
    "SaveRestricted",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)
try:
    Bot.start()
    print("✅ Pyrogram Bot started successfully!")
except Exception as e:
    print(f"❌ Pyrogram Bot Error: {e}")
    sys.exit(1)

print("🚀 ALL CLIENTS STARTED SUCCESSFULLY! Bot is now online.")
