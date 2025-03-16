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
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))


# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
import json
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("TelegramBotMembers").sheet1

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
    "⬆️ **BUY Signal for {pair}** \n\n🔥 Confidence: {confidence}%\n\n🤖 LunaX Signal Bot",
    "⬇️ **SELL Signal for {pair}** \n\n📉 Confidence: {confidence}%\n\n🚀 LunaX Signal Bot",
    "⬆️ **BUY Opportunity for {pair}** \n\n📈 Confidence: {confidence}%\n\n⚡ LunaX Signal Bot",
    "⬇️ **SELL Alert for {pair}** \n\n⏳ Confidence: {confidence}%\n\n💡 LunaX Signal Bot",
    "⬆️ **Potential BUY for {pair}** \n\n💰 Confidence: {confidence}%\n\n🔍 LunaX Signal Bot",
    "⬇️ **Strong SELL Signal for {pair}** \n\n⚠️ Confidence: {confidence}%\n\n📊 LunaX Signal Bot",
    "⬆️ **BUY Setup for {pair}** \n\n📌 Confidence: {confidence}%\n\n📡 LunaX Signal Bot",
    "⬇️ **SELL Opportunity for {pair}** \n\n🔴 Confidence: {confidence}%\n\n🛰️ LunaX Signal Bot"
]

# Image file IDs (replace with actual Telegram file IDs)
buy_image_id = "AgACAgUAAxkBAAKoeGfXFrnEQl8MM1xgIsN2tPB9e6q5AAJTwTEbswi5VgbbUQFoQg5PAQADAgADcwADNgQ"
sell_image_id = "AgACAgUAAxkBAAKodmfXFrYnjhxh-wsJcDm1pcjGjC8UAAJSwTEbswi5VtcdWgjFsLqrAQADAgADeAADNgQ"

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

    asyncio.create_task(log_activity(context, f"User Started: \n{user.id} \n@{user.username}"))

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
    analyzing_messages = [
        "⚡ Scanning {pair}...",
        "🤖 AI analyzing {pair}...",
        "📡 Data crunching {pair}...",
        "🔍 Processing {pair}...",
        "📊 Evaluating {pair}..."
    ]
    
    analyzing_message = await update.message.reply_text(random.choice(analyzing_messages).format(pair=pair), parse_mode="Markdown")

    step_variations = [
        ["🛰️ Processing data...", "📡 Gathering insights...", "🔍 Extracting indicators..."],
        ["🤖 Running AI model...", "🧠 Predicting trends...", "🔬 Simulating movement..."],
        ["✅ Generating signal...", "📊 Finalizing analysis...", "📌 Confirming trade..."]
    ]

    steps = [random.choice(variation) for variation in step_variations]

    for step in steps:
        await asyncio.sleep(1)
        await analyzing_message.edit_text(step, parse_mode="Markdown")

    confidence = random.randint(75, 80)
    signal_type = "BUY" if random.random() > 0.5 else "SELL"
    image_id = buy_image_id if signal_type == "BUY" else sell_image_id
    response_template = random.choice([r for r in responses if signal_type in r])
    caption = response_template.format(pair=pair, confidence=confidence)

    # Delete the last message before sending final response with image
    await analyzing_message.delete()
    await update.message.reply_photo(photo=image_id, caption=caption, parse_mode="Markdown")
    
async def add_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        new_user_id = int(context.args[0])
        AUTHORIZED_USERS.add(new_user_id)
        save_users()
        await update.message.reply_text(f"✅ User {new_user_id} has been added successfully.")

        # Log new user addition
        await log_activity(context, f"✅ **User Added:** {new_user_id} by @{user.username}")

    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: /addmember <user_id>")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_message = update.message.text
    
    if user.id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Access Denied. You are not authorized to use this bot.")
        return
    
    if user_message in otc_pairs:
        print(f"User {user.id} ({user.username}) selected: {user_message}")
        await log_activity(context, f"Trade Selection: {user.id} @{user.username} \nSelected: {user_message}")
        await simulate_analysis(update, user_message)
    elif not user_message.startswith("/"):
        await log_activity(context, f"Message Received: {user.id} @{user.username} \nMessage: {user_message}")
        await update.message.reply_text("Please select a valid OTC pair from the keyboard.")

def run_flask():
    app.run(host="0.0.0.0", port=8080)

def main() -> None:
    application = Application.builder().token(TOKEN).concurrent_updates(True).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addmember", add_member))  
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    threading.Thread(target=keep_alive).start()
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
