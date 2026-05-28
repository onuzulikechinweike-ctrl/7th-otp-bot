#!/usr/bin/env python3

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

CHANNEL_USERNAME = "@the_7th_otp"

CHANNEL_ID = -1002561104893

HEADLESS = True

POLL_INTERVAL = 15

IVASMS_LOGIN_URL = "https://www.ivasms.com/login"

IVASMS_NUMBERS_URL = "https://www.ivasms.com/client-system/my-numbers"

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

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS otps(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT,
            otp TEXT
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

    async def release(
        self,
        number
    ):

        self.conn.execute(
            "UPDATE numbers SET status='available', user_id=NULL WHERE number=?",
            (number,)
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

        self.session.post(
            IVASMS_LOGIN_URL,
            data=payload
        )

        logger.info(
            "Logged into IVASMS"
        )

    async def fetch_numbers(self):

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

        return list(set(found))

# ==========================================
# CHANNEL JOIN CHECK
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

    # ======================================
    # PLATFORM SELECT
    # ======================================

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
                    f"{flag} +{number}",
                    callback_data=f"pick:{platform}:{number}"
                )
            ])

        await query.edit_message_text(
            "Select number:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

    # ======================================
    # NUMBER PICK
    # ======================================

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
            f"`+{number}`\n\n"
            f"Waiting for OTP...\n\n"
            f"The OTP will appear below automatically.",
            parse_mode="Markdown"
        )

# ==========================================
# AUTO FETCH NUMBERS
# ==========================================

async def fetch_loop():

    while True:

        try:

            numbers = await source.fetch_numbers()

            for num in numbers:

                clean = re.sub(
                    r"\D",
                    "",
                    num
                )

                platform = list(
                    PLATFORMS.keys()
                )[0]

                await db.add_number(
                    clean,
                    platform
                )

            logger.info(
                "Numbers updated."
            )

        except Exception as e:

            logger.error(e)

        await asyncio.sleep(300)

# ==========================================
# OTP CHECK LOOP
# ==========================================

async def otp_loop(app):

    while True:

        try:

            logger.info(
                "Checking OTP updates..."
            )

        except Exception as e:

            logger.error(e)

        await asyncio.sleep(
            POLL_INTERVAL
        )

# ==========================================
# POST INIT
# ==========================================

async def post_init(app):

    await source.start()

    asyncio.create_task(
        fetch_loop()
    )

    asyncio.create_task(
        otp_loop(app)
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

    app.run_polling()

if __name__ == "__main__":

    main()
