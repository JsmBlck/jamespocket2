import os
import httpx
import asyncio
import random
import json
import gspread
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks
from contextlib import asynccontextmanager
from oauth2client.service_account import ServiceAccountCredentials
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEND_MESSAGE = f"{API_BASE}/sendMessage"
SEND_CHAT_ACTION = f"{API_BASE}/sendChatAction"
EDIT_MESSAGE = f"{API_BASE}/editMessageText"
DELETE_MESSAGE = f"{API_BASE}/deleteMessage"

RENDER_URL = "https://jamespocket2-x6nh.onrender.com"
channel_link = os.getenv("CHANNEL_LINK")
pocketlink = os.getenv("POCKET_LINK")

client = None
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS2"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
spreadsheet = client.open("LyraExclusiveAccess")
sheet = spreadsheet.worksheet("Sheet2")
tg_channel = "t.me/ZentraAiRegister"

otc_pairs = [
    "S5 AUD/CHF OTC", "S5 GBP/JPY OTC", "S5 QAR/CNY OTC", "S5 CAD/JPY OTC", "S5 AED/CNY OTC", "S5 AUD/NZD OTC",
    "S5 EUR/USD OTC", "S5 BHD/CNY OTC", "S5 EUR/GBP OTC", "S5 NZD/USD OTC", "S5 LBP/USD OTC", "S5 GBP/USD OTC",
    "Change Time Expiry"
]
crypto_pairs = [
    "S10 AUD/CHF OTC", "S10 GBP/JPY OTC", "S10 QAR/CNY OTC", "S10 CAD/JPY OTC", "S10 AED/CNY OTC", "S10 AUD/NZD OTC",
    "S10 EUR/USD OTC", "S10 BHD/CNY OTC", "S10 EUR/GBP OTC", "S10 NZD/USD OTC", "S10 LBP/USD OTC", "S10 GBP/USD OTC",
    "Change Time Expiry"
]
stocks = [
    "S15 AUD/CHF OTC", "S15 GBP/JPY OTC", "S15 QAR/CNY OTC", "S15 CAD/JPY OTC", "S15 AED/CNY OTC", "S15 AUD/NZD OTC",
    "S15 EUR/USD OTC", "S15 BHD/CNY OTC", "S15 EUR/GBP OTC", "S15 NZD/USD OTC", "S15 LBP/USD OTC", "S15 GBP/USD OTC",
    "Change Time Expiry"
]
def load_authorized_users():
    global AUTHORIZED_USERS
    AUTHORIZED_USERS = set()
    user_ids = sheet.col_values(1)
    print(f"Fetched user IDs from GSheet: {user_ids}")
    for user_id in user_ids[1:]:
        if user_id.strip():
            try:
                AUTHORIZED_USERS.add(int(user_id))
            except ValueError:
                print(f"Skipping invalid ID: {user_id}")
    print(f"Loaded authorized users: {AUTHORIZED_USERS}")
def save_users():
    user_ids = sheet.col_values(1)
    if not user_ids:
        sheet.append_row(["TG ID", "TG Username", "TG Name", "PocketOption ID"])
        user_ids = sheet.col_values(1) 
    for user_id in AUTHORIZED_USERS:
        user_info = user_data.get(user_id, {})
        tg_username = user_info.get("username", "Unknown")
        tg_name = user_info.get("first_name", "Trader")
        pocket_option_id = user_info.get("pocket_option_id", "N/A")
        user_id_str = str(user_id)
        if user_id_str in user_ids:
            row_number = user_ids.index(user_id_str) + 1  
            sheet.update(f"B{row_number}", [[tg_username]])  
            sheet.update(f"C{row_number}", [[tg_name]])
            sheet.update(f"D{row_number}", [[pocket_option_id]])
        else:
            sheet.append_row([user_id, tg_username, tg_name, pocket_option_id])
    print("✅ Users saved successfully!")
load_authorized_users()
@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = httpx.AsyncClient(timeout=10)
    async def self_ping_loop():
        await asyncio.sleep(5)
        while True:
            try:
                await client.get(RENDER_URL)
                print("✅ Self-ping successful!")
            except Exception as e:
                print(f"❌ Ping failed: {e}")
            await asyncio.sleep(300)
    asyncio.create_task(self_ping_loop())
    yield
    await client.aclose()  # Clean up
app = FastAPI(lifespan=lifespan)
@app.api_route("/", methods=["GET", "HEAD"])
async def healthcheck(request: Request):
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    if msg := data.get("message"):
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        user = msg["from"]
        user_id = user["id"]

        if user_id in ADMIN_IDS:
            # Check if message contains video and caption
            if "video" in msg and "caption" in msg:
                video_file_id = msg["video"]["file_id"]
                caption = msg["caption"]
                button_options = [
                    {"text": "🚀 Start Using the Bot for Free", "url": os.getenv("BOT_LINK")},
                    {"text": "🤖 Launch the Free Trading Bot Now", "url": os.getenv("BOT_LINK")},
                    {"text": "✅ Click Here to Get the Bot for Free", "url": os.getenv("BOT_LINK")},
                    {"text": "🚀 Start the Bot – No Cost!", "url": os.getenv("BOT_LINK")},
                    {"text": "🔥 Grab Your Free Bot Access!", "url": os.getenv("BOT_LINK")},
                    {"text": "⚡ Activate Your Trading Bot Today", "url": os.getenv("BOT_LINK")},
                    {"text": "🎯 Get the Bot and Start Winning!", "url": os.getenv("BOT_LINK")},
                    {"text": "💥 Don’t Miss Out – Get the Bot Now", "url": os.getenv("BOT_LINK")},
                    {"text": "📈 Boost Your Trades with This Bot!", "url": os.getenv("BOT_LINK")},
                    {"text": "🚀 Ready to Trade? Get Your Bot Here!", "url": os.getenv("BOT_LINK")},
                ]
                chosen_button = random.choice(button_options)
                inline_keyboard = {
                    "inline_keyboard": [[chosen_button]]
                }
                payload = {
                    "chat_id": -1002549064084,
                    "video": video_file_id,
                    "caption": caption,
                    "reply_markup": inline_keyboard,
                    "parse_mode": "HTML"}
                send_video_url = f"{API_BASE}/sendVideo"
                background_tasks.add_task(client.post, send_video_url, json=payload)
                return {"ok": True}
        
        if text == "/start":
            keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
            payload = {
                "chat_id": chat_id,
                "text": (
                    "👇 Please choose a pair to get signal:"
                ),
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}

    
        
##############################################################################################################################################
        if text == "Change Time Expiry":
            keyboard = [["S5", "S10", "S15"]]
            payload = {
                "chat_id": chat_id,
                "text": "🔄 Select a Category you prefer:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        elif text == "S5":
            keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "You’ve successfully changed the Time Expiry to S5!",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        elif text == "S10":
            keyboard = [crypto_pairs[i:i+3] for i in range(0, len(stocks), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "You’ve successfully changed the Time Expiry to S10!",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        elif text == "S15":
            keyboard = [stocks[i:i+3] for i in range(0, len(crypto_pairs), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "You’ve successfully changed the Time Expiry to S15!",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
##############################################################################################################################################
        if text in crypto_pairs or text in otc_pairs or text in stocks:
            signals = ["⬆️", "⬇️"]
            signal = random.choice(signals)
        
            signal_message = f"{signal}"
            payload = {
                "chat_id": chat_id,
                "text": signal_message
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}

        if text.startswith(("/addmember", "/add")):
            parts = text.strip().split()
            if len(parts) < 3:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ Usage: /addmember <user_id> <pocket_option_id>"}
                await client.post(SEND_MESSAGE, json=payload)
                return {"ok": True}
            if user_id not in ADMIN_IDS:
                payload = {
                    "chat_id": chat_id,
                    "text": "❌ You are not authorized to use this command."}
                await client.post(SEND_MESSAGE, json=payload)
                return {"ok": True}
            try:
                new_user_id = int(parts[1])
                pocket_option_id = parts[2]
                AUTHORIZED_USERS.add(new_user_id)
            
                try:
                    resp = await client.get(f"{API_BASE}/getChat", params={"chat_id": new_user_id})
                    user_info = resp.json().get("result", {})
                    username = user_info.get("username", "Unknown")
                    first_name = user_info.get("first_name", "Trader")
                except Exception as e:
                    print(f"⚠️ Failed to fetch user info: {e}")
                    username = "Unknown"
                    first_name = "Trader"
            
                # Prepare full name and username display
                full_name = first_name
                username_display = f"@{username}" if username != "Unknown" else "No username"
            
                user_ids = sheet.col_values(1)
                user_id_str = str(new_user_id)
                if user_id_str in user_ids:
                    row_number = user_ids.index(user_id_str) + 1
                    sheet.update(f"B{row_number}", [[username]])
                    sheet.update(f"C{row_number}", [[first_name]])
                    sheet.update(f"D{row_number}", [[pocket_option_id]])
                else:
                    sheet.append_row([new_user_id, username, first_name, pocket_option_id])
            
                payload = {
                    "chat_id": chat_id,
                    "text": f"✅ Added Successful!\n\n{full_name} | {username_display} | {new_user_id} \nPocket Option ID: {pocket_option_id}"
                }
                await client.post(SEND_MESSAGE, json=payload)

            except ValueError:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ Invalid user ID. Please enter a valid number."}
                await client.post(SEND_MESSAGE, json=payload)
            return {"ok": True}



        payload = {
            "chat_id": chat_id,
            "text": "Unknown command. Please press /start to begin."}
        background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
        return {"ok": True}

    
    if cq := data.get("callback_query"):
        data_str = cq.get("data", "")
        chat_id = cq["message"]["chat"]["id"]
        message_id = cq["message"]["message_id"]
        cq_id = cq.get("id")
        background_tasks.add_task(client.post, f"{API_BASE}/answerCallbackQuery", json={"callback_query_id": cq_id})
        background_tasks.add_task(client.post, DELETE_MESSAGE, json={"chat_id": chat_id, "message_id": message_id})
