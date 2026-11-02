import asyncio
import logging
import os
import sqlite3
import sys
import html 
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiohttp import web

Initialize logging

logging.basicConfig(
level=logging.INFO,
format="%(asctime)s - %(levelname)s - %(message)s",
datefmt="%Y-%m-%d %H:%M:%S",
handlers=[
logging.StreamHandler(sys.stdout)
]
)
logger = logging.getLogger("telegram_auto_approver")

Load environment variables

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "Hello! Your request to join our channel has been approved. Welcome!")
AUTO_APPROVE_STR = os.getenv("AUTO_APPROVE", "true").lower()
AUTO_APPROVE = AUTO_APPROVE_STR in ("true", "1", "yes", "on")

ADMIN_ID_STR = os.getenv("ADMIN_ID")
ADMIN_ID = int(ADMIN_ID_STR) if ADMIN_ID_STR and ADMIN_ID_STR.isdigit() else None

START_MESSAGE = """
<b>Hey {username} I am a Cat Bot who can approve request instantly. I can approve your channel or group join requests.😉</b>

<blockquote>➲ Add bot as admin
➲ Enable Join Requests
➲ It will approve instantly</blockquote>

With love by - @YoruichiTheBlackCat 🐈‍⬛🤍
"""

if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
logger.error("Error: BOT_TOKEN is not set in the .env file.")
logger.error("Please edit the .env file and paste your Telegram Bot Token from @BotFather.")
sys.exit(1)

SQLite Database Setup

DB_FILE = "users.db"

def init_db():
try:
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY,
username TEXT,
full_name TEXT,
joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()
conn.close()
logger.info("Database initialized successfully.")
except Exception as e:
logger.critical(f"Failed to initialize database: {e}")
sys.exit(1)

def add_user(user_id: int, username: str = None, full_name: str = None):
try:
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute(
"INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
(user_id, username, full_name)
)
conn.commit()
conn.close()
logger.info(f"Saved user {user_id} to database.")
except Exception as e:
logger.error(f"Error saving user {user_id} to database: {e}")

def get_all_users():
try:
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("SELECT user_id FROM users")
rows = cursor.fetchall()
conn.close()
return [row[0] for row in rows]
except Exception as e:
logger.error(f"Error fetching users from database: {e}")
return []

def format_message(template: str, user, chat=None) -> str:
# Handle literal backslash-n first
text = template.replace("\n", "\n")

# Define replacement mapping  
placeholders = {  
    "{first_name}": user.first_name or "",  
    "{last_name}": user.last_name or "",  
    "{full_name}": user.full_name or "",  
    "{username}": user.username or "",  
    "{user_id}": str(user.id),  
}  
  
if chat:  
    placeholders["{chat_title}"] = chat.title or ""  
    placeholders["{chat_id}"] = str(chat.id)  
      
for key, val in placeholders.items():  
    text = text.replace(key, val)  
      
return text

TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY")

Initialize bot and dispatcher

if TELEGRAM_PROXY:
logger.info(f"Using proxy configuration: {TELEGRAM_PROXY}")
session = AiohttpSession(proxy=TELEGRAM_PROXY)
bot = Bot(token=BOT_TOKEN, session=session)
else:
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

@router.chat_join_request()
async def handle_chat_join_request(request: types.ChatJoinRequest):
user = request.from_user
chat = request.chat

# Save user to DB  
add_user(user.id, user.username, user.full_name)  
  
user_name_info = f"{user.full_name}"  
if user.username:  
    user_name_info += f" (@{user.username})"  
  
logger.info(f"Received join request from {user_name_info} (ID: {user.id}) for chat '{chat.title}' (ID: {chat.id})")  
  
# 1. Send private message first while we still have permission (via user_chat_id)  
pm_sent = False  
try:  
    # aiogram types.ChatJoinRequest exposes user_chat_id which is the chat ID for the PM.  
    # If user_chat_id is not available, fall back to user.id  
    pm_chat_id = getattr(request, "user_chat_id", user.id)  
      
    logger.info(f"Attempting to send private message to user {user.id} using chat_id {pm_chat_id}...")  
    await bot.send_message(  
        chat_id=pm_chat_id,  
        text=format_message(WELCOME_MESSAGE, user, chat)  
    )  
    logger.info(f"Successfully sent private message to {user_name_info}")  
    pm_sent = True  
except TelegramAPIError as e:  
    logger.warning(  
        f"Could not send private message to {user_name_info} (ID: {user.id}). "  
        f"Reason: {e.message if hasattr(e, 'message') else str(e)}"  
    )  
    logger.warning("This is usually because the user's privacy settings prevent direct messaging from bots.")  
except Exception as e:  
    logger.error(f"Unexpected error while sending private message to {user.id}: {e}")  

# 2. Approve the request if configured to do so  
if AUTO_APPROVE:  
    try:  
        logger.info(f"Approving join request for {user_name_info} in chat '{chat.title}'...")  
        await request.approve()  
        logger.info(f"Successfully approved join request for {user_name_info}")  
    except TelegramAPIError as e:  
        logger.error(  
            f"Failed to approve join request for {user_name_info}. "  
            f"Ensure the bot is an admin in the chat and has the 'can_invite_users' (Invite Users via Link) permission. "  
            f"Error: {e.message if hasattr(e, 'message') else str(e)}"  
        )  
    except Exception as e:  
        logger.error(f"Unexpected error while approving join request for {user.id}: {e}")  
else:  
    logger.info(f"Auto-approval is disabled. Join request for {user_name_info} left pending.")

--- Command Handlers ---

await message.answer(
    format_message(START_MESSAGE, user),
    parse_mode="HTML"
)

@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
# 1. Authorize admin
if not ADMIN_ID or message.from_user.id != ADMIN_ID:
await message.answer("⚠️ You are not authorized to use this command.")
return

# 2. Determine what message to send  
is_reply = message.reply_to_message is not None  
broadcast_msg = message.reply_to_message if is_reply else None  
  
broadcast_text = ""  
if not is_reply:  
    parts = message.text.split(maxsplit=1)  
    if len(parts) > 1:  
        broadcast_text = parts[1]  
    else:  
        await message.answer(  
            "❌ **Usage Error:**\n\n"  
            "1. Send `/broadcast <text>` to send a text message.\n"  
            "2. Reply to any message (text, image, video, file) with `/broadcast` to copy and send it."  
        )  
        return  

# Get all users from database  
users = get_all_users()  
if not users:  
    await message.answer("ℹ️ No users found in the database to broadcast to.")  
    return  

status_message = await message.answer(f"⏳ Starting broadcast to {len(users)} users...")  
  
success_count = 0  
fail_count = 0  
  
# Broadcast loop  
for user_id in users:  
    # Don't spam Telegram servers: add a small delay  
    await asyncio.sleep(0.05)  
    try:  
        if is_reply:  
            # Copy the replied message to the user  
            await broadcast_msg.copy_to(chat_id=user_id)  
        else:  
            # Send the text message  
            await bot.send_message(chat_id=user_id, text=broadcast_text)  
        success_count += 1  
    except TelegramAPIError as e:  
        logger.warning(f"Failed to send broadcast to user {user_id}: {e}")  
        fail_count += 1  
    except Exception as e:  
        logger.error(f"Unexpected error broadcasting to {user_id}: {e}")  
        fail_count += 1  

await status_message.edit_text(  
    f"✅ **Broadcast Completed!**\n\n"  
    f"👤 Total users: {len(users)}\n"  
    f"✔️ Successful: {success_count}\n"  
    f"❌ Failed: {fail_count}"  
)

async def bot_lifecycle(app):
init_db()
dp.include_router(router)

# Get bot info to verify credentials  
try:  
    bot_user = await bot.get_me()  
    logger.info(f"Bot initialized successfully!")  
    logger.info(f"Username: @{bot_user.username}")  
    logger.info(f"Name: {bot_user.first_name}")  
    logger.info(f"Auto-Approve: {AUTO_APPROVE}")  
    logger.info("Listening for join requests... Press Ctrl+C to stop.")  
except TelegramAPIError as e:  
    logger.critical(f"Failed to connect to Telegram API: {e}")  
    sys.exit(1)  
except Exception as e:  
    logger.critical(f"An unexpected error occurred during startup: {e}")  
    sys.exit(1)  
      
# Start polling.   
# Skip updates that occurred while the bot was offline to avoid double-processing.  
polling_task = asyncio.create_task(  
    dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), skip_updates=True)  
)  
  
yield  
  
logger.info("Shutting down bot polling...")  
await dp.stop_polling()  
polling_task.cancel()  
try:  
    await polling_task  
except asyncio.CancelledError:  
    pass  
await bot.session.close()  
logger.info("Bot session closed.")

async def handle_ping(request):
return web.Response(text="Bot is running!")

app = web.Application()
app.router.add_get("/", handle_ping)
app.cleanup_ctx.append(bot_lifecycle)

if name == "main":
PORT = int(os.getenv("PORT", "8080"))
try:
logger.info(f"Starting web server on port {PORT}...")
web.run_app(app, host="0.0.0.0", port=PORT, access_log=None)
except (KeyboardInterrupt, SystemExit):
logger.info("Bot stopped.")

