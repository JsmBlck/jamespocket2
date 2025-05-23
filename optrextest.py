import os
import random
import asyncio
import threading 
import requests
import time
import json
import gspread
import re
from telegram.constants import ParseMode
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
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



def load_authorized_users():
    global AUTHORIZED_USERS
    AUTHORIZED_USERS = set()  # Reset the set

    user_ids = sheet.col_values(1)  # Get all user IDs from column 1

    print(f"Fetched user IDs from GSheet: {user_ids}")  # Debugging

    for user_id in user_ids[1:]:  # Skip the first row (header)
        if user_id.strip():  # Avoid empty cells
            try:
                AUTHORIZED_USERS.add(int(user_id))  # Convert to integer
            except ValueError:
                print(f"Skipping invalid ID: {user_id}")  # Debugging for non-numeric values

    print(f"Loaded authorized users: {AUTHORIZED_USERS}")  # Debugging

# Save authorized users to Google Sheets		
def save_users():
    """Save authorized users in Google Sheets without altering existing data."""
    
    # Get all user IDs currently stored in the sheet
    user_ids = sheet.col_values(1)  # Column A (TG ID)

    # Add headers if the sheet is empty
    if not user_ids:
        sheet.append_row(["TG ID", "TG Username", "TG Name", "PocketOption ID"])
        user_ids = sheet.col_values(1)  # Refresh after adding headers

    for user_id in AUTHORIZED_USERS:
        user_info = user_data.get(user_id, {})
        tg_username = user_info.get("username", "Unknown")
        tg_name = user_info.get("first_name", "Trader")
        pocket_option_id = user_info.get("pocket_option_id", "N/A")

        user_id_str = str(user_id)  # Ensure ID matches the format in Sheets

        if user_id_str in user_ids:
            # Update existing row for the user
            row_number = user_ids.index(user_id_str) + 1  # Find row number
            sheet.update(f"B{row_number}", [[tg_username]])  # Update Username
            sheet.update(f"C{row_number}", [[tg_name]])  # Update Name
            sheet.update(f"D{row_number}", [[pocket_option_id]])  # Update PocketOption ID
        else:
            # Append new user as a new row
            sheet.append_row([user_id, tg_username, tg_name, pocket_option_id])

    print("✅ Users saved successfully!")
    
load_authorized_users()

# List of OTC pairs
otc_pairs = [
    "🇦🇪🇨🇳 AED/CNY OTC",  # United Arab Emirates / China
    "🇧🇭🇨🇳 BHD/CNY OTC",  # Bahrain / China
    "🇦🇺🇨🇦 AUD/CAD OTC",  # Australia / Canada
    "🇪🇺🇺🇸 EUR/USD OTC",  # Euro / US Dollar
    "🇨🇦🇨🇭 CAD/CHF OTC",  # Canada / Switzerland
    "🇳🇿🇯🇵 NZD/JPY OTC",  # New Zealand / Japan
    "🇬🇧🇯🇵 GBP/JPY OTC"   # Great Britain / Japan
]
# AI-like responses
responses_json = os.getenv("RESPONSES", "[]")
responses = json.loads(responses_json)["RESPONSES"]  

# Flask app
app = Flask(__name__)

@app.route('/')
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    asyncio.create_task(log_activity(context, f"✅ User Started\n{user.full_name} | @{user.username} | {user.id}"))
    
    if user.id not in AUTHORIZED_USERS:
        keyboard = [
    [
        InlineKeyboardButton(" Join Channel ", url="https://t.me/+8zp8vEziM-VhYTY1")
    ],
    [
        InlineKeyboardButton("☝️Click Here To Get Access☝️", url="https://t.me/+8zp8vEziM-VhYTY1")
    ]
]
        reply_markup = InlineKeyboardMarkup(keyboard)

        photo_file_id = "AgACAgUAAxkBAAL2zGgTqGq8yndVpEOIIJR5ltEcbBDlAAKWyDEbMDOhVP-tNvKclpmnAQADAgADcwADNgQ"  # Replace with your actual file ID

        await update.message.reply_photo(
    photo=photo_file_id,
    caption=(
        "<b>You need to get verified to access this bot.</b>\n\n"
        "🔹 <b>How to Get Verified:</b>\n"
        "✅ Join our channel: <a href=\"https://t.me/+8zp8vEziM-VhYTY1\">Click Here</a>\n"
        "✅ Read the instructions posted in the channel.\n"
        "✅ If you have questions, message @SynthBotSupport.\n"
        "👇 Click the buttons below: 👇"
    ), 
    parse_mode=ParseMode.HTML,
    reply_markup=reply_markup
)
        return  

    
    photo_id = "AgACAgUAAxkBAAL2zGgTqGq8yndVpEOIIJR5ltEcbBDlAAKWyDEbMDOhVP-tNvKclpmnAQADAgADcwADNgQ"  # Replace with your actual Telegram file ID

    welcome_message = """

🚀 Our bot provides real-time trading signals for 10-second trades on OTC Forex pairs.

🔹 *How It Works:*
✅ Select an OTC Forex pair from the options below.  
✅ Receive a trading signal with market analysis.  
✅ Execute the trade quickly for the best results.  

⚠️ *Disclaimer:* Trading involves risk. Always trade responsibly.
    """
    # Define the keyboard layout (pairs in 2 columns)
    keyboard = [otc_pairs[i:i + 2] for i in range(0, len(otc_pairs), 2)]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    # Send photo with caption
    await update.message.reply_photo(photo=photo_id, caption=welcome_message, parse_mode="Markdown", reply_markup=reply_markup)


# -----------------------------------------------------# 

async def simulate_analysis(update: Update, pair: str) -> None:

    # Send initial analyzing message
    pleasemsg = await update.message.reply_text(
        f"🤖 Analyzing {pair}...", 
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["⏳ Please Wait..."]], resize_keyboard=True)
    )

    # Send progress bar message
    analyzing_message = await update.message.reply_text(f"░░░░░░░░░░ 0%", parse_mode="Markdown")
    current_percent = 1

    # Simulate analysis progress
    while current_percent < 100:
        await asyncio.sleep(random.uniform(0.05, 0.07))  # Simulate progress timing
        current_percent += random.randint(3, 17)
        current_percent = min(current_percent, 100)

        # Update progress bar dynamically
        filled_blocks = int(current_percent / 10)
        progress_bar = "█" * filled_blocks + "░" * (10 - filled_blocks)

        # Edit the scanning message safely
        try:
            await analyzing_message.edit_text(f"{progress_bar} {current_percent}%", parse_mode="Markdown")
        except Exception as e:
            print(f"Error updating progress: {e}")
            break  # Stop updating if there's an error

    # Final completion message
    await asyncio.sleep(0.5)
    try:
        await analyzing_message.edit_text(f"Analysis complete for {pair} ✅ ", parse_mode="Markdown")
    except Exception as e:
        print(f"Error finalizing message: {e}")

    # Randomly choose between Uptrend (⬆️) and Downtrend (⬇️)
    signal_type = random.choice(["⬆️", "⬇️"])
    if signal_type == "⬇️":
        photo_id = random.choice([
            "AgACAgUAAxkBAAL25GgTqj-ponXm_HMsHnkbHjJVrNM2AAKqyDEbMDOhVKgKmfJUCMc9AQADAgADeQADNgQ",
            "AgACAgUAAxkBAAL24mgTqje4R75dXWBasXYh4qgF68BzAAKpyDEbMDOhVF4IqwxsS_CmAQADAgADbQADNgQ",
            "AgACAgUAAxkBAAL24GgTqjG17G0RNtMlO1VgY82RO1jTAAKoyDEbMDOhVO2zvHF0xBUCAQADAgADeAADNgQ",
            "AgACAgUAAxkBAAL23mgTqil7jt3NaQjeF_BCOoO8Fm_TAAKnyDEbMDOhVN5IO_8VdClqAQADAgADbQADNgQ"
        ])
    else:
        photo_id = random.choice([
            "AgACAgUAAxkBAAL22GgTqXps-sGh1Xuifz1vvqJkWJRQAAKlyDEbMDOhVFzd9SVMSA4nAQADAgADdwADNgQ",
            "AgACAgUAAxkBAAL21mgTqXSOWg91iP_51LhI-hxkUHqRAAKkyDEbMDOhVAztDE547MilAQADAgADdwADNgQ",
            "AgACAgUAAxkBAAL21GgTqWzMTMwMkicm2phLpCkipRrTAAKjyDEbMDOhVLR1OB1iM3wQAQADAgADdwADNgQ",
            "AgACAgUAAxkBAAL20mgTqWRBUQ0zFg0D9e1xBquzS0TOAAKiyDEbMDOhVGFQfrqs58yJAQADAgADcwADNgQ"
        ])
    # Delete the analysis message
    await analyzing_message.delete()

    # Prepare keyboard layout for OTC pairs
    keyboard = [otc_pairs[i:i + 2] for i in range(0, len(otc_pairs), 2)]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    # Send the signal (with emoji) and appropriate photo based on the trend
    await update.message.reply_photo(
        photo=photo_id,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

    # Delete the initial "Analyzing..." message
    await pleasemsg.delete()

    # Prompt the user to select an OTC pair
    await update.message.reply_text("Select an OTC pair:")


# ----------------------------------------------------#



async def add_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user

    # Check if user is an admin
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    # Ensure arguments (user_id and pocket_option_id) are provided
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: /addmember <user_id> <pocket_option_id>")
        return

    try:
        new_user_id = int(context.args[0])
        pocket_option_id = context.args[1]

        # Add user to authorized list
        AUTHORIZED_USERS.add(new_user_id)

        # Fetch user info
        try:
            chat = await context.bot.get_chat(new_user_id)
            username = chat.username if chat.username else "Unknown"
            first_name = chat.first_name if chat.first_name else "Trader"
        except Exception as e:
            print(f"⚠️ Failed to retrieve user info: {e}")
            username = "Unknown"
            first_name = "Trader"

        # Update Google Sheet directly
        user_ids = sheet.col_values(1)
        user_id_str = str(new_user_id)

        if user_id_str in user_ids:
            row_number = user_ids.index(user_id_str) + 1
            sheet.update(f"B{row_number}", [[username]])
            sheet.update(f"C{row_number}", [[first_name]])
            sheet.update(f"D{row_number}", [[pocket_option_id]])
        else:
            sheet.append_row([new_user_id, username, first_name, pocket_option_id])

        print("✅ User saved to Google Sheet")

        await update.message.reply_text(
            f"✅ User {new_user_id} added successfully with Pocket Option ID: {pocket_option_id}"
        )

        # Send welcome message
        try:
            photo_id = "AgACAgUAAxkBAAL2ymgTqF_WEcYxx3MomwwVOPK017iFAAKVyDEbMDOhVJNQC6UwJvzTAQADAgADcwADNgQ"

            welcome_message = f"""
🚀 Hey *{first_name}*! You are now Verified!✅

🚀 Bot provides real-time trading signals for 10-second trades on OTC Forex pairs.

🔹 *How It Works:*
✅ Select an OTC Forex pair from the options below.  
✅ Receive a trading signal with market analysis.  
✅ Execute the trade quickly for the best results.  

⚠️ *Disclaimer:* Trading involves risk. Always trade responsibly.
            """

            keyboard = [otc_pairs[i:i + 2] for i in range(0, len(otc_pairs), 2)]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await context.bot.send_photo(
                chat_id=new_user_id,
                photo=photo_id,
                caption=welcome_message,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        except Exception as e:
            print(f"⚠️ Failed to send welcome message: {e}")

    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID. Please enter a valid number.")

async def remove_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user

    # Check if user is an admin
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    # Ensure an argument (user_id) is provided
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /removemember <user_id>")
        return

    try:
        remove_user_id = str(context.args[0])  # Convert to string for easier comparison

        # Get all user IDs from the sheet (Column A)
        user_ids = sheet.col_values(1)

        if remove_user_id in user_ids:
            row = user_ids.index(remove_user_id) + 1  # Find row number

            # Remove the row from Google Sheets
            sheet.delete_rows(row)

            # Remove from AUTHORIZED_USERS if needed
            AUTHORIZED_USERS.discard(int(remove_user_id))

            await update.message.reply_text(f"✅ User {remove_user_id} has been removed successfully.")
        else:
            await update.message.reply_text("⚠️ User ID not found in the list.")

    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID. Please enter a valid number.")

async def get_id(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    await update.message.reply_text("🔹 Your Exclusive Access ID:")
    await update.message.reply_text(f"`{user.id}`", parse_mode="Markdown")
    await update.message.reply_text("☝️ Copy this and send it to @SynthBotSupport to verify your access.")

def get_pocket_option_id(user_id):
    user_ids = sheet.col_values(1)  # Get all Telegram user IDs from column 1
    if str(user_id) in user_ids:
        row = user_ids.index(str(user_id)) + 1  # Get the row number
        return sheet.cell(row, 4).value  # Pocket Option ID is in column 4
    return "N/A"  # If not found, return "N/A"

async def log_activity(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send logs to the log channel."""
    asyncio.create_task(
        context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=message))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_message = update.message.text
    pocket_option_id = get_pocket_option_id(user.id)

    
    if user.id not in AUTHORIZED_USERS:
        await update.message.reply_text(
    "❌ Access Denied. You are not authorized to use this bot.",
    parse_mode="Markdown",
    reply_markup=ReplyKeyboardRemove())
        return

    if user_message == "⏳ Please Wait...":
        try:
            await update.message.delete()
        except Exception as e:
            print(f"Error deleting 'Please Wait' message: {e}")
        return 
        
    if user_message in otc_pairs:
        print(f"User {user.id} ({user.username}) selected: {user_message}")
        await log_activity(context, f"Trade Selection📊:\nPocket Option ID: `{pocket_option_id}`\n@{user.username} | {user.full_name} | {user.id}\nSelected: {user_message}")
        await simulate_analysis(update, user_message)
    elif not user_message.startswith("/"):
        await log_activity(context, f"Message Received: {user.id} @{user.username} \nMessage: {user_message}")
        await update.message.reply_text("Please select a valid OTC pair from the keyboard.")


def run_flask():
    app.run(host="0.0.0.0", port=8080)

def main() -> None:
    application = Application.builder().token(TOKEN).concurrent_updates(True).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("AccessID", get_id))
    application.add_handler(CommandHandler("addmember", add_member))  
    application.add_handler(CommandHandler("removemember", remove_member))  
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    threading.Thread(target=keep_alive).start()
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
