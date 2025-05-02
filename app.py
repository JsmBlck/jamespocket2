from fastapi import FastAPI, Request
import httpx
import os
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import Update

app = FastAPI()

# List of OTC pairs
otc_pairs = [
    "AED/CNY OTC", 
    "AUD/CAD OTC",   
    "BHD/CNY OTC",  
    "EUR/USD OTC",
    "GBP/USD OTC",
    "NZD/USD OTC"
]

BOT_TOKEN = "your_bot_token_here"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# Inline Keyboard Button for OTC Pairs
def get_otc_keyboard():
    keyboard = [[InlineKeyboardButton(pair, callback_data=pair)] for pair in otc_pairs]
    return InlineKeyboardMarkup(keyboard)

# Random signal generator (Up/Down)
def get_random_signal():
    return random.choice(["UP", "DOWN"])

# Command to send OTC pairs with inline buttons
async def send_otc_buttons(update: Update, context):
    chat_id = update.message.chat_id
    message = "Please select an OTC pair:"
    await update.message.reply_text(message, reply_markup=get_otc_keyboard())

# Callback handler for the selected OTC pair
async def handle_otc_callback(update: Update, context):
    query = update.callback_query
    selected_pair = query.data  # Pair selected by the user
    random_signal = get_random_signal()
    
    # Send the random signal to the user
    await query.answer()
    await query.edit_message_text(f"The signal for {selected_pair} is: {random_signal}")

# Initialize the Updater and Dispatcher
updater = Updater(BOT_TOKEN, use_context=True)
dp = updater.dispatcher

# Add handlers for /start and callback queries
dp.add_handler(CommandHandler("start", send_otc_buttons))
dp.add_handler(CallbackQueryHandler(handle_otc_callback))

@app.post("/webhook")
async def handle_webhook(req: Request):
    data = await req.json()
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')
        # Send the message using the Telegram API (this is just a fallback)
        async with httpx.AsyncClient() as client:
            await client.post(TELEGRAM_API, json={
                "chat_id": chat_id,
                "text": f"You said: {text}"
            })
    return {"ok": True}

@app.get("/")
async def home():
    return {"status": "Bot running!"}

if __name__ == "__main__":
    # Start polling for updates (used for testing locally, will not be used on Render)
    updater.start_polling()
    updater.idle()
