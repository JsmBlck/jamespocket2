import os
import random
import asyncio
import threading 
import requests
import time
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
import json
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("TelegramBotMembers").sheet1

# List of Admin IDs
ADMIN_IDS = [6992481448, 7947707536]  

# Channel ID for logging user activity (replace with your actual channel ID)
LOG_CHANNEL_ID = -1002666027470  # Replace with your log channel ID

# Load authorized users from Google Sheets
def load_users():
    try:
        users = sheet.col_values(1)
        return set(map(int, users)) | set(ADMIN_IDS)
    except Exception as e:
        print(f"Error loading users: {e}")
        return set(ADMIN_IDS)

# Save authorized users to Google Sheets
def save_users():
    sheet.clear()
    for idx, user_id in enumerate(AUTHORIZED_USERS):
        sheet.update_cell(idx + 1, 1, user_id)

# Authorized users list
AUTHORIZED_USERS = load_users()

# List of OTC pairs
otc_pairs = [
    "AED/CNY OTC", "AUD/CHF OTC", "BHD/CNY OTC", "EUR/USD OTC", 
    "CAD/CHF OTC", "NZD/JPY OTC", "EUR/CHF OTC", "GBP/JPY OTC"
]

# AI-like responses
responses = [
    "📈 **Signal: BUY {pair}** \nConfidence: {confidence}%",
    "📉 **Signal: SELL {pair}** \nConfidence: {confidence}%"
]

# Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def keep_alive():
    render_url = "https://jamespocket2.onrender.com"
    while True:
        try:
            requests.get(render_url)
            print("✅ Self-ping successful!")
        except Exception as e:
            print(f"❌ Ping failed: {e}")
        time.sleep(300)

async def log_activity(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send logs to the log channel."""
    asyncio.create_task(context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=message))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    print(f"User {user.id} ({user.username}) started the bot.")

    asyncio.create_task(log_activity(context, f"👤 **User Started:**\n🆔 ID: {user.id}\n👤 Username: @{user.username}"))

    if user.id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Access Denied. You are not authorized to use this bot.")
        return

    welcome_message = """
📊 *Welcome to the Binary Trading Assistant!*

Our bot provides real-time trading signals for OTC Forex pairs.

🔹 *How It Works:*
✔️ Select an OTC Forex pair from the options below.
✔️ Receive a trading signal with market analysis.
✔️ Execute the trade quickly for optimal results.

⚠️ *Disclaimer:* Trading involves risk. Always trade responsibly.
    """
    keyboard = [otc_pairs[i:i + 2] for i in range(0, len(otc_pairs), 2)]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="Markdown")

async def simulate_analysis(update: Update, pair: str) -> None:
    analyzing_message = await update.message.reply_text(f"🔍 Scanning {pair}...", parse_mode="Markdown")

    steps = [
        "📊 Detecting market patterns...",
        "🔎 Analyzing price action...",
        "📌 Finalizing signal..."
    ]

    for step in steps:
        await asyncio.sleep(2)
        await analyzing_message.edit_text(step, parse_mode="Markdown")

    confidence = random.randint(75, 80)
    response_template = random.choice(responses)
    response = response_template.format(pair=pair, confidence=confidence)

    await analyzing_message.edit_text(response, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    
    asyncio.create_task(log_activity(context, f"📩 **Message Received:**\n🆔 ID: {user.id}\n👤 Username: @{user.username}\n💬 Message: {update.message.text}"))

    if user.id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Access Denied. You are not authorized to use this bot.")
        return
    
    user_message = update.message.text
    if user_message in otc_pairs:
        print(f"User {user.id} ({user.username}) selected: {user_message}")
        asyncio.create_task(log_activity(context, f"📌 **Trade Selection:**\n🆔 ID: {user.id}\n👤 Username: @{user.username}\n📈 Pair: {user_message}"))
        asyncio.create_task(simulate_analysis(update, user_message))
    else:
        await update.message.reply_text("Please select a valid OTC pair from the keyboard.")

def run_flask():
    app.run(host="0.0.0.0", port=8080)

def main() -> None:
    application = Application.builder().token(TOKEN).concurrent_updates(True).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    threading.Thread(target=keep_alive).start()
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
