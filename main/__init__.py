#Github.com/Vasusen-code

from pyrogram import Client
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError
from decouple import config
import logging, time, sys, asyncio

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

# variables
API_ID = config("API_ID", default=None, cast=int)
API_HASH = config("API_HASH", default=None)
BOT_TOKEN = config("BOT_TOKEN", default=None)
SESSION = config("SESSION", default=None)
FORCESUB = config("FORCESUB", default=None)
AUTH = config("AUTH", default=None, cast=int)

# ==================== FIXED TELETHON BOT WITH FLOOD WAIT HANDLING ====================
async def start_telethon_bot():
    bot = TelegramClient('bot', API_ID, API_HASH)
    while True:
        try:
            await bot.start(bot_token=BOT_TOKEN)
            print("✅ Telethon Bot started successfully!")
            return bot
        except FloodWaitError as e:
            wait_time = e.seconds + 10  # extra 10s safety
            print(f"⏳ FloodWaitError: Waiting {wait_time} seconds before retrying login...")
            await asyncio.sleep(wait_time)
        except Exception as e:
            print(f"❌ Unexpected error starting Telethon bot: {e}")
            await asyncio.sleep(30)  # safety delay

# Run the async startup
loop = asyncio.get_event_loop()
bot = loop.run_until_complete(start_telethon_bot())

# ==================== PYROGRAM USERBOT ====================
userbot = Client(
    "saverestricted",
    session_string=SESSION,
    api_hash=API_HASH,
    api_id=API_ID
)

try:
    userbot.start()
    print("✅ Pyrogram Userbot started successfully!")
except BaseException:
    print("❌ Userbot Error! Have you added SESSION while deploying??")
    sys.exit(1)

# ==================== PYROGRAM BOT CLIENT ====================
Bot = Client(
    "SaveRestricted",
    bot_token=BOT_TOKEN,
    api_id=int(API_ID),
    api_hash=API_HASH
)

try:
    Bot.start()
    print("✅ Pyrogram Bot started successfully!")
except Exception as e:
    print(f"❌ Pyrogram Bot Error: {e}")
    sys.exit(1)

print("🚀 All clients started! Bot is now online.")
