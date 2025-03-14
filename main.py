import os
import random
import asyncio
import threading
import requests
import time
import json
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

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

# Keep-alive function
def keep_alive():
    render_url = "https://jamespocket2.onrender.com"
    while True:
        try:
            requests.get(render_url)
            print("✅ Self-ping successful!")
        except Exception as e:
            print(f"❌ Ping failed: {e}")
        time.sleep(300)

# Load members from file
def load_members():
    try:
        with open("members.txt", "r") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

# Save members to file
def save_members():
    with open("members.txt", "w") as f:
        json.dump(list(exclusive_members), f)

# Authorized members
exclusive_members = load_members()
ADMIN_ID = 6992481448  # Replace with your Telegram ID

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    print(f"User {user.id} ({user.username}) started the bot.")

    if user.id not in exclusive_members:
        await update.message.reply_text("❌ Access Denied: You're not an authorized member.")
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

# Simulate analysis
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

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    user = update.message.from_user

    if user.id not in exclusive_members:
        await update.message.reply_text("❌ Access Denied: You're not an authorized member.")
        return

    if user_message in otc_pairs:
        print(f"User {user.id} ({user.username}) selected: {user_message}")
        asyncio.create_task(simulate_analysis(update, user_message))
    else:
        await update.message.reply_text("Please select a valid OTC pair from the keyboard.")

# Add member (Admin only)
async def add_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addmember <user_id>")
        return

    try:
        new_member_id = int(context.args[0])
        exclusive_members.add(new_member_id)
        save_members()
        await update.message.reply_text(f"✅ Member {new_member_id} added successfully.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a valid number.")

# Run Flask server
def run_flask():
    app.run(host="0.0.0.0", port=8080)

# Main function
def main() -> None:
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addmember", add_member))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    keep_alive_thread = threading.Thread(target=keep_alive)
    keep_alive_thread.start()

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
