import asyncio
import logging
import os
import re
import sqlite3

import requests
from bs4 import BeautifulSoup

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ==========================================
# BOT NAME
# ==========================================

BOT_NAME = "7𝕋ℍ 𝕆𝕋ℙ BOT"

# ==========================================
# CONFIG
# ==========================================

BOT_TOKEN = os.getenv("8895635098:AAFgdA2psdcfE2BoMWIVuWlT99H-xawVBbA")

IVASMS_USER = os.getenv("emmap4880@gmail.com")

IVASMS_PASS = os.getenv("Destiny2")

# ==========================================
# YOUR TELEGRAM DETAILS
# ==========================================

OWNER_ID = 8924829992

CHANNEL_USERNAME = "@the_7th_otp"

CHANNEL_ID = -1003876315009

# ==========================================
# BOT SETTINGS
# ==========================================

POLL_INTERVAL = 15

IVASMS_LOGIN_URL = "https://www.ivasms.com/login"

IVASMS_NUMBERS_URL = (
    "https://www.ivasms.com/client-system/my-numbers"
)

# ==========================================
# OWNER CHECK
# ==========================================

def is_owner(user_id):

    return user_id == OWNER_ID

# ==========================================
# PLATFORMS
# ==========================================

PLATFORMS = {
    "facebook": {
        "emoji": "📘",
        "name": "Facebook"
    },

    "whatsapp": {
        "emoji": "💬",
        "name": "WhatsApp"
    },

    "instagram": {
        "emoji": "📸",
        "name": "Instagram"
    },

    "tiktok": {
        "emoji": "🎵",
        "name": "TikTok"
    }
}

# ==========================================
# COUNTRY DETECTION
# ==========================================

COUNTRY_CODES = {
    "234": ("🇳🇬", "Nigeria"),
    "1": ("🇺🇸", "USA/Canada"),
    "44": ("🇬🇧", "United Kingdom"),
    "91": ("🇮🇳", "India"),
    "92": ("🇵🇰", "Pakistan"),
    "233": ("🇬🇭", "Ghana"),
    "254": ("🇰🇪", "Kenya"),
    "27": ("🇿🇦", "South Africa"),
}

def detect_country(number):

    clean = number.replace("+", "")

    for code, data in COUNTRY_CODES.items():

        if clean.startswith(code):

            return data

    return ("🌍", "Unknown")

# ==========================================
# LOGGING
# ==========================================

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(BOT_NAME)

# ==========================================
# DATABASE
# ==========================================

class Database:

    def __init__(self):

        self.conn = sqlite3.connect(
            "otp_bot.db",
            check_same_thread=False
        )

        self.setup()

    def setup(self):

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS numbers(
            number TEXT PRIMARY KEY,
            platform TEXT,
            status TEXT,
            user_id INTEGER
        )
        """)

        self.conn.commit()

    async def add_number(
        self,
        number,
        platform
    ):

        self.conn.execute(
            "INSERT OR IGNORE INTO numbers VALUES(?,?,?,?)",
            (
                number,
                platform,
                "available",
                None
            )
        )

        self.conn.commit()

    async def get_numbers(
        self,
        platform
    ):

        cur = self.conn.execute(
            "SELECT number FROM numbers WHERE platform=? AND status='available'",
            (platform,)
        )

        return [x[0] for x in cur.fetchall()]

    async def assign(
        self,
        number,
        user_id
    ):

        self.conn.execute(
            "UPDATE numbers SET status='assigned', user_id=? WHERE number=?",
            (
                user_id,
                number
            )
        )

        self.conn.commit()

db = Database()

# ==========================================
# IVASMS SCRAPER
# ==========================================

class SourceClient:

    def __init__(self):

        self.session = requests.Session()

    async def start(self):

        payload = {
            "email": IVASMS_USER,
            "password": IVASMS_PASS
        }

        headers = {
            "User-Agent": (
                "Mozilla/5.0"
            )
        }

        response = self.session.post(
            IVASMS_LOGIN_URL,
            data=payload,
            headers=headers
        )

        if response.status_code == 200:

            logger.info(
                "Logged into IVASMS successfully"
            )

        else:

            logger.error(
                "IVASMS login failed"
            )

    async def fetch_numbers(self):

        try:

            response = self.session.get(
                IVASMS_NUMBERS_URL
            )

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            text = soup.get_text()

            found = re.findall(
                r'\+?\d{7,15}',
                text
            )

            clean_numbers = []

            for num in found:

                clean = re.sub(
                    r"\D",
                    "",
                    num
                )

                if len(clean) >= 7:

                    clean_numbers.append(f"+{clean}")

            unique_numbers = list(
                set(clean_numbers)
            )

            logger.info(
                f"Fetched {len(unique_numbers)} numbers"
            )

            return unique_numbers

        except Exception as e:

            logger.error(
                f"Fetch error: {e}"
            )

            return []

source = SourceClient()

# ==========================================
# CHANNEL CHECK
# ==========================================

async def is_channel_member(
    user_id,
    app
):

    try:

        member = await app.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except:

        return False

# ==========================================
# START COMMAND
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    member = await is_channel_member(
        user.id,
        context.application
    )

    if not member:

        await update.message.reply_text(
            f"Join {CHANNEL_USERNAME} first."
        )

        return

    keyboard = []

    for key, info in PLATFORMS.items():

        keyboard.append([
            InlineKeyboardButton(
                f"{info['emoji']} {info['name']}",
                callback_data=f"platform:{key}"
            )
        ])

    if is_owner(user.id):

        await update.message.reply_text(
            f"👑 Welcome Owner to {BOT_NAME}",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

    else:

        await update.message.reply_text(
            f"Welcome to {BOT_NAME}\n\nChoose platform:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

# ==========================================
# BUTTON HANDLER
# ==========================================

async def button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    data = query.data

    if data.startswith("platform:"):

        platform = data.split(":")[1]

        numbers = await db.get_numbers(
            platform
        )

        keyboard = []

        for number in numbers:

            flag, country = detect_country(
                number
            )

            keyboard.append([
                InlineKeyboardButton(
                    f"{flag} {number}",
                    callback_data=f"pick:{platform}:{number}"
                )
            ])

        await query.edit_message_text(
            "Select number:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

    elif data.startswith("pick:"):

        parts = data.split(":")

        number = parts[2]

        await db.assign(
            number,
            update.effective_user.id
        )

        flag, country = detect_country(
            number
        )

        await query.edit_message_text(
            f"{flag} {country}\n\n"
            f"📱 Number:\n"
            f"`{number}`\n\n"
            f"Waiting for OTP...",
            parse_mode="Markdown"
        )

# ==========================================
# FETCH LOOP
# ==========================================

async def fetch_loop():

    while True:

        try:

            numbers = await source.fetch_numbers()

            for num in numbers:

                await db.add_number(
                    num,
                    "facebook"
                )

            logger.info(
                "Numbers updated."
            )

        except Exception as e:

            logger.error(e)

        await asyncio.sleep(300)

# ==========================================
# POST INIT
# ==========================================

async def post_init(app):

    await source.start()

    asyncio.create_task(
        fetch_loop()
    )

# ==========================================
# MAIN
# ==========================================

def main():

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button
        )
    )

    print(
        f"{BOT_NAME} STARTED"
    )

    app.run_polling(
        drop_pending_updates=True
    )

if __name__ == "__main__":

    main()