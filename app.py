from fastapi import FastAPI, Request
import httpx
import os
import uvicorn
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

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
async def send_otc_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    message = "Please select an OTC pair:"
    await update.message.reply_text(message, reply_markup=get_otc_keyboard())

# Callback handler for the selected OTC pair
async def handle_otc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    selected_pair = query.data  # Pair selected by the user
    random_signal = get_random_signal()
    
    # Send the random signal to the user
    await query.answer()
    await query.edit_message_text(f"The signal for {selected_pair} is: {random_signal}")

# Initialize the Application (Updated for v20+)
application = Application.builder().token(BOT_TOKEN).build()

# Add handlers for /start and callback queries
application.add_handler(CommandHandler("start", send_otc_buttons))
application.add_handler(CallbackQueryHandler(handle_otc_callback))

@app.post("/webhook")
async def handle_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    
    # Process the update using the application
    await application.process_update(update)
    
    return {"ok": True}


# This is optional, if you don't need the `/` endpoint
@app.get("/")
async def home():
    return {"status": "Bot is ready and running!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Use environment variable PORT
    uvicorn.run(app, host="0.0.0.0", port=port)  # Bind to all addresses


