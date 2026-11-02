
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


# ==============================
# LOGGING
# ==============================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("telegram_auto_approver")


# ==============================
# ENVIRONMENT VARIABLES
# ==============================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

WELCOME_MESSAGE = os.getenv(
    "WELCOME_MESSAGE",
    "Hello! Your request to join our channel has been approved. Welcome!"
)
WELCOME_IMAGE = "https://imgyx.pages.dev/CgJga"

AUTO_APPROVE_STR = os.getenv("AUTO_APPROVE", "true").lower()
AUTO_APPROVE = AUTO_APPROVE_STR in ("true", "1", "yes", "on")

ADMIN_ID_STR = os.getenv("ADMIN_ID")
ADMIN_ID = (
    int(ADMIN_ID_STR)
    if ADMIN_ID_STR and ADMIN_ID_STR.isdigit()
    else None
)

START_MESSAGE = """
<b>Hey {username} I am a Cat Bot who can approve request instantly. I can approve your channel or group join requests.😉</b>

<blockquote>➲ Add bot as admin
➲ Enable Join Requests
➲ It will approve instantly</blockquote>

With love by - @YoruichiTheBlackCat 🐈‍⬛🤍
"""

if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
    logger.error("BOT_TOKEN is not set.")
    sys.exit(1)


# ==============================
# SQLITE DATABASE
# ==============================

DB_FILE = "users.db"


def init_db():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        logger.info("Database initialized successfully.")

    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}")
        sys.exit(1)


def add_user(user_id: int, username: str = None, full_name: str = None):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO users
                (user_id, username, full_name)
                VALUES (?, ?, ?)
                """,
                (user_id, username, full_name)
            )

    except Exception as e:
        logger.error(f"Error saving user {user_id}: {e}")


def get_all_users():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            rows = conn.execute(
                "SELECT user_id FROM users"
            ).fetchall()

        return [row[0] for row in rows]

    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return []


# ==============================
# MESSAGE FORMATTER
# ==============================

def format_message(template: str, user, chat=None) -> str:

    placeholders = {
        "{first_name}": html.escape(user.first_name or ""),
        "{last_name}": html.escape(user.last_name or ""),
        "{full_name}": html.escape(user.full_name or ""),
        "{username}": html.escape(
            f"@{user.username}" if user.username else user.first_name or "there"
        ),
        "{user_id}": str(user.id),
    }

    if chat:
        placeholders["{chat_title}"] = html.escape(chat.title or "")
        placeholders["{chat_id}"] = str(chat.id)

    for key, value in placeholders.items():
        template = template.replace(key, value)

    return template


# ==============================
# BOT INITIALIZATION
# ==============================

TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY")

if TELEGRAM_PROXY:
    logger.info("Using proxy configuration.")
    session = AiohttpSession(proxy=TELEGRAM_PROXY)
    bot = Bot(token=BOT_TOKEN, session=session)
else:
    bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()
router = Router()


# ==============================
# START COMMAND
# ==============================

@router.message(Command("start"))
async def cmd_start(message: types.Message):

    user = message.from_user

    if not user:
        return

    add_user(user.id, user.username, user.full_name)

    await message.answer(
        format_message(START_MESSAGE, user),
        parse_mode="HTML"
    )


# ==============================
# JOIN REQUEST HANDLER
# ==============================


@router.chat_join_request()
async def handle_chat_join_request(request: types.ChatJoinRequest):
    user = request.from_user
    chat = request.chat

    add_user(user.id, user.username, user.full_name)

    user_name_info = user.full_name

    if user.username:
        user_name_info += f" (@{user.username})"

    logger.info(f"Join request received from {user_name_info}")

    # Send welcome image
    try:
        pm_chat_id = getattr(request, "user_chat_id", user.id)

        await bot.send_photo(
            chat_id=pm_chat_id,
            photo=WELCOME_IMAGE,
            caption=format_message(WELCOME_MESSAGE, user, chat),
            parse_mode="HTML"
        )

        logger.info(f"Welcome image sent to {user_name_info}")

    except TelegramAPIError as e:
        logger.warning(f"Could not send welcome image: {e}")

    except Exception as e:
        logger.error(f"Welcome image error: {e}")

    # Approve join request
    if AUTO_APPROVE:
        try:
            await request.approve()
            logger.info(f"Successfully approved {user_name_info}")

        except TelegramAPIError as e:
            logger.error(f"Approval failed: {e}")

        except Exception as e:
            logger.error(f"Unexpected approval error: {e}")

    else:
        logger.info("Auto-approval is disabled.")



# ==============================
# BROADCAST COMMAND
# ==============================

@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):

    # Check admin
    if not ADMIN_ID or message.from_user.id != ADMIN_ID:
        await message.answer(
            "⚠️ You are not authorized to use this command."
        )
        return

    # Check reply or text
    is_reply = message.reply_to_message is not None
    broadcast_msg = message.reply_to_message if is_reply else None

    broadcast_text = ""

    if not is_reply:
        parts = message.text.split(maxsplit=1)

        if len(parts) > 1:
            broadcast_text = parts[1]
        else:
            await message.answer(
                "Usage: /broadcast Your message\n"
                "Or reply to a message with /broadcast."
            )
            return

    # Get users
    users = get_all_users()

    if not users:
        await message.answer("No users found in database.")
        return

    status_message = await message.answer(
        f"⏳ Starting broadcast to {len(users)} users..."
    )

    success_count = 0
    fail_count = 0

    # Send broadcast
    for user_id in users:

        await asyncio.sleep(0.05)

        try:
            if is_reply:
                await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=message.chat.id,
                    message_id=broadcast_msg.message_id
                )
            else:
                await bot.send_message(
                    chat_id=user_id,
                    text=broadcast_text
                )

            success_count += 1

        except TelegramAPIError as e:
            logger.warning(
                f"Broadcast failed for {user_id}: {e}"
            )
            fail_count += 1

        except Exception as e:
            logger.error(
                f"Unexpected broadcast error for {user_id}: {e}"
            )
            fail_count += 1

    await status_message.edit_text(
        f"✅ Broadcast Completed!\n\n"
        f"👤 Total users: {len(users)}\n"
        f"✔️ Successful: {success_count}\n"
        f"❌ Failed: {fail_count}"
    )


# ==============================
# BOT LIFECYCLE
# ==============================

async def bot_lifecycle(app):

    init_db()

    dp.include_router(router)

    try:
        bot_user = await bot.get_me()

        logger.info("Bot initialized successfully!")
        logger.info(f"Username: @{bot_user.username}")
        logger.info(f"Name: {bot_user.first_name}")
        logger.info(f"Auto-Approve: {AUTO_APPROVE}")
        logger.info("Listening for join requests...")

    except TelegramAPIError as e:
        logger.critical(f"Telegram connection failed: {e}")
        raise

    polling_task = asyncio.create_task(
        dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            skip_updates=True
        )
    )

    try:
        yield

    finally:
        logger.info("Shutting down bot polling...")

        await dp.stop_polling()

        if not polling_task.done():
            polling_task.cancel()

        try:
            await polling_task
        except asyncio.CancelledError:
            pass

        await bot.session.close()

        logger.info("Bot session closed.")


# ==============================
# WEB SERVER
# ==============================

async def handle_ping(request):
    return web.Response(text="Bot is running!")


app = web.Application()

app.router.add_get("/", handle_ping)
app.cleanup_ctx.append(bot_lifecycle)


# ==============================
# START APPLICATION
# ==============================

if __name__ == "__main__":

    PORT = int(os.getenv("PORT", "8080"))

    try:
        logger.info(f"Starting web server on port {PORT}...")

        web.run_app(
            app,
            host="0.0.0.0",
            port=PORT,
            access_log=None
        )

    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
