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
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEND_MESSAGE = f"{API_BASE}/sendMessage"
SEND_CHAT_ACTION = f"{API_BASE}/sendChatAction"
EDIT_MESSAGE = f"{API_BASE}/editMessageText"
DELETE_MESSAGE = f"{API_BASE}/deleteMessage"
RENDER_URL = "https://jamespocket2-k9lz.onrender.com"

client = None

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
spreadsheet = client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet7")        # Trader data sheet (read-only for deposit)
authorized_sheet = spreadsheet.worksheet("Sheet8")  # Authorized users sheet

tg_channel = "https://u3.shortink.io/register?utm_campaign=815367&utm_source=affiliate&utm_medium=sr&a=BaVC7XCAwnsCc6&ac=fluxmate&code=50START"
expiry_options = ["S5", "S10", "S15"]
otc_pairs = [
    "EUR/JPY OTC", "EUR/NZD OTC", "EUR/USD OTC", "GBP/AUD OTC", "GBP/JPY OTC", "UAH/USD OTC",
    "SAR/CNY OTC", "AED/CNY OTC", "CHF/JPY OTC", "BHD/CNY OTC",  "CAD/CHF OTC", "CAD/JPY OTC", "🔄 Change Category"]
crypto_pairs = [
    "Bitcoin OTC", "Ethereum OTC", "Polkadot OTC", "Polygon OTC", "Bitcoin ETF OTC", "TRON OTC", "Chainlink OTC", "Dogecoin OTC",
    "Solana OTC", "Cardano OTC", "Toncoin OTC", "Avalanche OTC", "🔄 Change Category"]
stocks = [
    "Apple OTC", "FACEBOOK INC OTC", "Intel OTC", "American Express OTC", "Johnson & Johnson OTC", "McDonald's OTC", "Tesla OTC", "Amazon OTC",
    "GameStop Corp OTC", "Netflix OTC", "VIX OTC", "VISA OTC", "🔄 Change Category"]
user_data = {}
def get_deposit_for_trader(trader_id: str) -> float | None:
    trader_ids = sheet.col_values(1)
    deposits = sheet.col_values(2)
    for idx, tid in enumerate(trader_ids[1:], start=1):
        if tid.strip() == trader_id:
            try:
                return float(deposits[idx])
            except (ValueError, IndexError):
                return None
    return None
def save_authorized_user(tg_id: int, po_id: str, username: str = None, first_name: str = None):
    tg_ids = authorized_sheet.col_values(1)
    if str(tg_id) in tg_ids:
        row = tg_ids.index(str(tg_id)) + 1
        authorized_sheet.update(f"B{row}", [[username or "Unknown"]])
        authorized_sheet.update(f"C{row}", [[first_name or "Trader"]])
        authorized_sheet.update(f"D{row}", [[po_id]])
    else:
        authorized_sheet.append_row([tg_id, username or "Unknown", first_name or "Trader", po_id])
    print(f"✅ Authorized user saved: TG ID {tg_id}, PO ID {po_id}")
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
    await client.aclose()
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

        if text == "/start":
            tg_ids = authorized_sheet.col_values(1)
            if str(user_id) in tg_ids:
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

    
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📌  Registration Link", "url": tg_channel}],
                    [{"text": "✅ Check ID", "callback_data": "check_id"}]
                ]
            }
            payload = {
                "chat_id": chat_id,
                "text": (
                    "To get access, you need to register/create a new account using the link below.\n\n"
                    "After you create your new account, just click the '✅ Check ID' button below and send your account ID to check and proceed to the next step."
                ),
                "reply_markup": keyboard
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}

        if text.isdigit() and len(text) > 5:
            po_id = text.strip()
            dep = get_deposit_for_trader(po_id)
            if dep is None:
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "📌  Registration Link", "url": tg_channel}],
                        [{"text": "✅ Check ID", "callback_data": "check_id"}]
                    ]
                }
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        "⚠️ That account is not registered or not signed up using my link.\n"
                        "Please register a new account and make sure to use the link I provided."
                    ),
                    "reply_markup": keyboard
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}

            if dep >= 30:
                tg_id = user_id
                username = user.get("username")
                first_name = user.get("first_name")
                save_authorized_user(tg_id, po_id, username, first_name)
                keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        "✅ You are now verified and can access the bot fully.\n\n"
                        "👇 Please choose a pair to get signal:"
                    ),
                    "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            payload = {
                "chat_id": chat_id,
                "text": (
                    "✅ Your account is registered!\n\n"
                    "To get full access, you need to fund your account with at least $30.\n"
                    "Once you've funded it, just send your Account ID again."
                )
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
##############################################################################################################################################
        if text == "🔄 Change Category":
            tg_ids = authorized_sheet.col_values(1)
            if str(user_id) not in tg_ids:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = [["Currencies", "Stocks", "Crypto"]]
            payload = {
                "chat_id": chat_id,
                "text": "🔄 Select a pair type to switch:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        elif text == "Currencies":
            tg_ids = authorized_sheet.col_values(1)
            if str(user_id) not in tg_ids:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "You chose the Currencies category. 🕒 Choose an OTC pair to trade:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        elif text == "Stocks":
            tg_ids = authorized_sheet.col_values(1)
            if str(user_id) not in tg_ids:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = [stocks[i:i+3] for i in range(0, len(stocks), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "You chose the Stocks category. 🕒 Choose a stock to trade:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        elif text == "Crypto":
            tg_ids = authorized_sheet.col_values(1)
            if str(user_id) not in tg_ids:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = [crypto_pairs[i:i+3] for i in range(0, len(crypto_pairs), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "You chose the Cryptocurrencies category. 💰 Choose a crypto currency to trade:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
##############################################################################################################################################
        if text in crypto_pairs or text in otc_pairs or text in stocks:
            tg_ids = authorized_sheet.col_values(1)
            if str(user_id) not in tg_ids:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nMessage my support to gain access!"
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            inline_kb = [
                [{"text": expiry_options[i], "callback_data": f"expiry|{text}|{expiry_options[i]}"} 
                 for i in range(len(expiry_options))]
            ]
            payload = {
                "chat_id": chat_id,
                "text": f"Choose your expiry time.",
                "reply_markup": {"inline_keyboard": inline_kb}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
##############################################################################################################################################
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
        if data_str == "check_id":
            payload = {
                "chat_id": chat_id,
                "text": "Please send your Pocket Option Account ID (numbers only).\n❌ : id 123123123\n✅ : 123123123"
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        if data_str.startswith("check_funding:"):
            po_id = data_str.split(":", 1)[1]
            dep = get_deposit_for_trader(po_id)
            if dep is None or dep < 30:
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        "✅ Your account is registered!\n\n"
                        "To get full access, you need to fund your account with at least $30.\n"
                        "Once you've funded it, just send your Account ID again."
                    )
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            from_user = cq.get("from", {})
            tg_id = from_user.get("id")
            username = from_user.get("username")
            first_name = from_user.get("first_name")
            save_authorized_user(tg_id, po_id, username, first_name)
            keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
            payload = {
                    "chat_id": chat_id,
                    "text": (
                        "✅ You are now verified and can access the bot fully.\n\n"
                        "👇 Please choose a pair to get signal:"
                    ),
                    "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        if data_str.startswith("expiry|"):
            _, pair, expiry = data_str.split("|", 2)
            signals = ["⬆️", "⬇️"]
            signal = random.choice(signals)
            signal_message = f"{signal}"
            payload = {
                "chat_id": chat_id,
                "text": signal_message
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}



