import os
import random
import asyncio
import threading 
import requests
import time
import json
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, Updater, CallbackContext
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
spreadsheet = client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet3")  # Us


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
    "🇦🇪/🇨🇳 AED/CNY OTC",  
    "🇦🇺/🇨🇦 AUD/CAD OTC", 
    "🇪🇺/🇺🇸 EUR/USD OTC", 
    "🇧🇭/🇨🇳 BHD/CNY OTC"
]

# AI-like responses
responses_json = os.getenv("RESPONSES", "[]")
responses = json.loads(responses_json)["RESPONSES"]  

def home():
    return "Bot is running!"


def keep_alive():
    render_url = "https://jamespocket2-k9lz.onrender.com"
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
    asyncio.create_task(log_activity(context, f"✅ User Started\n{user.full_name} | @{user.username} | {user.id}"))
    
    if user.id not in AUTHORIZED_USERS:
        keyboard = [
    [
        InlineKeyboardButton("🔹 Join Channel 🔹", url="https://t.me/+zPRC_d9dHMM0NDBl")
    ],
    [
        InlineKeyboardButton("☝️ Click Here To Get Access ☝️", url="https://t.me/+zPRC_d9dHMM0NDBl")
    ]
]
        reply_markup = InlineKeyboardMarkup(keyboard)

        photo_file_id = "AgACAgUAAxkBAAK-MGfmEiS9TQABGbrCW1zX9XImAAERgYQAAsTDMRtNaDhX9l3iGZFTwTkBAAMCAANtAAM2BA"  # Replace with your actual file ID

        await update.message.reply_photo(
    photo=photo_file_id,
    caption=(
        "*You need to get verified to access this bot.*\n\n"
        "🔹 *How to Get Verified:*\n"
        "👉 Join our channel: [Click Here](https://t.me/+zPRC_d9dHMM0NDBl)\n"
        "👉 Read the instructions posted in the channel.\n"
        "👉 If you have questions, message @JoinLunaX.\n"
        "👇 Click the buttons below: 👇"
    ),
    parse_mode="Markdown",
    reply_markup=reply_markup
)
        return  # <-- This was incorrectly indented before

    
    photo_id = "AgACAgUAAxkBAAK-5GfmzGVZc5gQEmPD0v0Q-e5VaRBpAAIVyjEbNTgxV8zN_n29nXRLAQADAgADeAADNgQ"  # Replace with your actual Telegram file ID

    welcome_message = """
📊 *Welcome to the Binary Trading Assistant!*

🚀 Our bot provides real-time trading signals for OTC Forex pairs.

🔹 *How It Works:*
✅ Select an OTC Forex pair from the options below.
✅ Receive a trading signal with market analysis.
✅ Execute the trade quickly for optimal results.

⚠️ *Disclaimer:* Trading involves risk. Always trade responsibly.
    """

    # Define the keyboard layout (pairs in 2 columns)
    keyboard = [otc_pairs[i:i + 2] for i in range(0, len(otc_pairs), 2)]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    # Send photo with caption
    await update.message.reply_photo(photo=photo_id, caption=welcome_message, parse_mode="Markdown", reply_markup=reply_markup)
    
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
        ["🛰️ Processing data for {pair}...", "📡 Gathering insights for {pair}...", "🔍 Extracting indicators for {pair}..."],
        ["🤖 Running AI model for {pair}...", "🧠 Predicting trends for {pair}...", "🔬 Simulating movement for {pair}..."],
        ["✅ Generating signal for {pair}...", "📊 Finalizing analysis for {pair}...", "📌 Confirming trade for {pair}..."]
    ]

    # steps = [random.choice(variation) for variation in step_variations]
    steps = [random.choice(variation).format(pair=pair) for variation in step_variations]

    for step in steps:
        await asyncio.sleep(random.uniform(1.5, 2.0)) 
        await analyzing_message.edit_text(step, parse_mode="Markdown")

    BUY_IMAGES = [
        "AgACAgUAAxkBAAK_Z2fnJgcirpQMyCQSqJy21s87I3y7AAKpyjEbNTg5VwXQT6lCyekyAQADAgADbQADNgQ",
        "AgACAgUAAxkBAAK_aWfnJhwxFQSeRAEKK7raXD6MFqvoAAKqyjEbNTg5V8amj2NdCMQaAQADAgADdwADNgQ",
        "AgACAgUAAxkBAAK_a2fnJiYX1vBmzpnd2c5wQKHDMRfOAAKryjEbNTg5V74iEW5fn9nsAQADAgADbQADNgQ",
        "AgACAgUAAxkBAAK_bWfnJi8ID30rDCmyZAcoCBNQ15RfAAKsyjEbNTg5V_SbLw9MSi9cAQADAgADeAADNgQ",
        "AgACAgUAAxkBAAK_b2fnJsJg2D4k1PwvctbR7IRjpLKyAAKtyjEbNTg5V2CMwEJUmPQiAQADAgADcwADNgQ",
        "AgACAgUAAxkBAAK_cWfnJsjYB3hzyGmYzG2KlcQ1gicvAAKuyjEbNTg5V6SqlEKEA7wDAQADAgADcwADNgQ",
        "AgACAgUAAxkBAAK_c2fnJtCj3N-IEJqV33V_SY8suCrGAAKvyjEbNTg5V9dt2bx4Bw1oAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAK_dWfnJttgZ7R7ovxBs4Dbsmb2upmKAAKwyjEbNTg5V6RA25hyoS6HAQADAgADeAADNgQ"
    ]
    SELL_IMAGES = [
        "AgACAgUAAxkBAAK_k2fnX8CWVMhf9acST3JcttYkJy32AALSyjEbNTg5V-usN4GH9uPXAQADAgADcwADNgQ",
        "AgACAgUAAxkBAAK_lWfnX8kah3XKf7rP0ynR33s7ES7TAALTyjEbNTg5Vz-dSgXpwqCCAQADAgADcwADNgQ",
        "AgACAgUAAxkBAAK_l2fnX9B1EgmwSYHdoCb892tjkGNaAALVyjEbNTg5V7DbDLPlVtWaAQADAgADbQADNgQ",
        "AgACAgUAAxkBAAK_mWfnX9fEG2t3jnEiRK1eYWY_4dbvAALWyjEbNTg5V3QKed9zCSr2AQADAgADeQADNgQ",
        "AgACAgUAAxkBAAK_e2fnLsp-9L0qHIf5HcBcOUI-n-pTAAKxyjEbNTg5V40GKdsSGYmAAQADAgADcwADNgQ",
        "AgACAgUAAxkBAAK_fWfnLs9JhCXAYuMYiEpZeDdlK2FRAAKyyjEbNTg5V2aow0dyeq0sAQADAgADbQADNgQ",
        "AgACAgUAAxkBAAK_f2fnLtYe4LFCbEYWQqbF4QggAwFwAAKzyjEbNTg5V_naxTJWbRKqAQADAgADeAADNgQ",
        "AgACAgUAAxkBAAK_gWfnLt9EOLKlSj9z31Y-SefdjEi3AAK0yjEbNTg5VwEUY5mmQ42sAQADAgADcwADNgQ"
    ]
    buy_image_id = random.choice(BUY_IMAGES)
    sell_image_id = random.choice(SELL_IMAGES)
    
    confidence = random.randint(75, 80)
    signal_type = "BUY" if random.random() > 0.5 else "SELL"
    image_id = buy_image_id if signal_type == "BUY" else sell_image_id
    response_template = random.choice([r for r in responses if signal_type in r])
    caption = response_template.format(pair=pair, confidence=confidence)

    # Delete the last message before sending final response with image
    await analyzing_message.delete()
    await update.message.reply_photo(photo=image_id, caption=caption, parse_mode="Markdown")

    follow_up_messages = [
        "🔄 Ready for the next trade? Choose another OTC pair.",
        "📈 Let's keep it going! Select another pair.",
        "🧐 What's next? Drop another OTC pair below.",
        "⚡ Keep the momentum! Enter another OTC pair.",
        "🚀 Ready for more signals? Send your next OTC pair."
    ]
    await asyncio.sleep(random.uniform(0.5, 1.0))    # Small delay before follow-up
    await update.message.reply_text(random.choice(follow_up_messages))
    

async def add_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    
    # Check if user is an admin
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    # Ensure an argument (user_id) is provided
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /addmember <user_id>")
        return

    try:
        new_user_id = int(context.args[0])
        AUTHORIZED_USERS.add(new_user_id)
        
        # Ensure save_users() function exists
        if "save_users" in globals():
            save_users()  
        
        await update.message.reply_text(f"✅ User {new_user_id} has been added successfully.")


        try:
            chat = await context.bot.get_chat(new_user_id)
            first_name = chat.first_name if chat.first_name else "Trader"  # Default name if unavailable
        except Exception as e:
            print(f"⚠️ Failed to retrieve user info for {new_user_id}: {e}")
            first_name = "Trader"  # Use a fallback name


        # Send verification message with a photo and keyboard to the user
        try:
            photo_id = "AgACAgUAAxkBAAK_D2fm5vj4L07Nm7tZHcsGJPbvT5i0AAKOyjEbNTg5V9RWc1P7RewiAQADAgADcwADNgQ"  # Replace with your actual Telegram file ID
            
            welcome_message = f"""
🚀 Hey *{first_name}*! You are now Verified!✅

Our bot provides real-time trading signals for OTC Forex pairs.

🔹 *How It Works:*
✅ Select an OTC Forex pair from the options below.
✅ Receive a trading signal with market analysis.
✅ Execute the trade quickly for optimal results.

⚠️ *Disclaimer:* Trading involves risk. Always trade responsibly.
"""

            # Define the keyboard layout (pairs in 2 columns)
            keyboard = [otc_pairs[i:i + 2] for i in range(0, len(otc_pairs), 2)]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

            # Send photo with caption and buttons
            await context.bot.send_photo(chat_id=new_user_id, photo=photo_id, caption=welcome_message, parse_mode="Markdown", reply_markup=reply_markup)

        except Exception as e:
            print(f"⚠️ Failed to send message to {new_user_id}: {e}")  # Debugging/logging
        
        # Log new user addition (check if function exists)
        if "log_activity" in globals():
            await log_activity(context, f"✅ **User Added:** {new_user_id} by @{user.username}")

    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID. Please enter a valid number.")

async def remove_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        remove_user_id = int(context.args[0])
        if remove_user_id in AUTHORIZED_USERS:
            AUTHORIZED_USERS.remove(remove_user_id)
            save_users()  # Now removes ID from Google Sheets
            await update.message.reply_text(f"✅ User {remove_user_id} has been removed successfully.")

            # Log user removal
            await log_activity(context, f"❌ **User Removed:** {remove_user_id} by @{user.username}")

        else:
            await update.message.reply_text("⚠️ User ID not found in the authorized list.")

    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: /removemember <user_id>")


async def get_id(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    await update.message.reply_text("🔹 Your Exclusive Access ID:")
    await update.message.reply_text(f"`{user.id}`", parse_mode="Markdown")
    await update.message.reply_text("☝️ Copy this and send it to @JoinLunaX to verify your access.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_message = update.message.text
    
    if user.id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Access Denied. You are not authorized to use this bot.")
        return
    
    if user_message in otc_pairs:
        print(f"User {user.id} ({user.username}) selected: {user_message}")
        await log_activity(context, f"Trade Selection📊: \n{user.full_name} | @{user.username} | {user.id}\nSelected: {user_message}")
        await simulate_analysis(update, user_message)
    elif not user_message.startswith("/"):
        await log_activity(context, f"Message Received: {user.id} @{user.username} \nMessage: {user_message}")
        await update.message.reply_text("Please select a valid OTC pair from the keyboard.")

def escape_markdown_v2(text):
    """Escape special characters for MarkdownV2"""
    return re.sub(r"([_*[\]()~`>#+\-=|{}.!])", r"\\\1", text)

def run_flask():
    app.run(host="0.0.0.0", port=8080)

application = Application.builder().token(TOKEN).concurrent_updates(True).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("AccessID", get_id))
application.add_handler(CommandHandler("addmember", add_member))  
application.add_handler(CommandHandler("removemember", remove_member))  
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Flask route for webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    application.update_queue.put(update)
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    # Start Flask in a separate thread
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Set the webhook
    application.bot.setWebhook(WEBHOOK_URL)

    print("Bot is running with Webhook...")
    application.run_webhook(
        listen="0.0.0.0",
        port=5000,
        url_path="/webhook",
        webhook_url=WEBHOOK_URL
    )
