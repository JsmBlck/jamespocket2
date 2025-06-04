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
RENDER_URL = "https://jamespocket2-n04b.onrender.com"

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
pocketlink = os.getenv("POCKET_LINK")
quotexlink = os.getenv("QUOTEX_LINK")
botlink = os.getenv("BOT_LINK")
expiry_options = ["S5", "S10", "S15"]
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
            await asyncio.sleep(300)  # Every 4 minutes

    asyncio.create_task(self_ping_loop())
    yield
    await client.aclose()

async def delayed_verification_check(client, SEND_MESSAGE, chat_id, po_id, user_id, user, save_authorized_user, otc_pairs):
    await asyncio.sleep(300)
    dep = get_deposit_for_trader(po_id)
    if dep is None:
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 Restart Process", "callback_data": "restart_process"}]
            ]
        }
        payload = {
            "chat_id": chat_id,
            "text": (
                "⚠️ Oops! It looks like your account isn’t registered through our official link.\n\n"
                "To proceed, please create a new account using the correct registration link provided earlier.\n\n"
                "Tap below to start over 👇"
            ),
            "reply_markup": keyboard
        }
        await client.post(SEND_MESSAGE, json=payload)
        return
    if dep >= 5:
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
        await client.post(SEND_MESSAGE, json=payload)
        return
    payload = {
        "chat_id": chat_id,
        "text": (
            "✅ Your account is registered!\n\n"
            "🔓 You're just one step away from full access.\n\n"
            "💰 Final Step:\nFund your account with any amount.\n\n"
            "Once you’ve made the deposit, simply send your Account ID again to complete verification."
        )
    }
    await client.post(SEND_MESSAGE, json=payload)


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
            message = data.get("message", {})  
            from_user = message.get("from", {}) 
            full_name = from_user.get("first_name", "Trader")
            username = from_user.get("username", "")
            username_display = f"@{username}" if username else "No username"
            user_id = from_user.get("id", "N/A")
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
                pair_payload = {
                    "chat_id": -1002676665035,
                    "text": (
                        f"✅ User Started\n\n"
                        f"*Full Name:* {full_name}\n"
                        f"*Username:* {username_display}\n"
                        f"*Telegram ID:* `{user_id}`"
                    ),
                    "parse_mode": "Markdown"
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=pair_payload)
                return {"ok": True}

    
            keyboard = {
                "inline_keyboard": [
                    [{"text": "Pocket Broker", "callback_data": "broker_pocket"}],
                    [{"text": "Quotex", "callback_data": "broker_quotex"}]
                ]
            }
            payload = {
                "chat_id": chat_id,
                "text": (
                    f"Hey {full_name}, welcome! 🙌\n\n"
                    "Which broker do you want to use?"
                ),
                "reply_markup": keyboard
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            pair_payload = {
                "chat_id": -1002676665035,
                "text": (
                    f"✅ User Started\n\n"
                    f"*Full Name:* {full_name}\n"
                    f"*Username:* {username_display}\n"
                    f"*Telegram ID:* `{user_id}`"
                ),
                "parse_mode": "Markdown"
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=pair_payload)
            return {"ok": True}
##############################################################################################################################################
        if text == "Change Time Expiry":
            tg_ids = authorized_sheet.col_values(1)
            if str(user_id) not in tg_ids:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nPlease press /start to begin."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = [["S5", "S10", "S15"]]
            payload = {
                "chat_id": chat_id,
                "text": "🔄 Select a Category you prefer:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        elif text == "S5":
            tg_ids = authorized_sheet.col_values(1)
            if str(user_id) not in tg_ids:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nPlease press /start to begin."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "You’ve successfully changed the Time Expiry to S5!",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        elif text == "S10":
            tg_ids = authorized_sheet.col_values(1)
            if str(user_id) not in tg_ids:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nPlease press /start to begin."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = [crypto_pairs[i:i+3] for i in range(0, len(stocks), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "You’ve successfully changed the Time Expiry to S10!",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        elif text == "S15":
            tg_ids = authorized_sheet.col_values(1)
            if str(user_id) not in tg_ids:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nPlease press /start to begin."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = [stocks[i:i+3] for i in range(0, len(crypto_pairs), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "You’ve successfully changed the Time Expiry to S15!",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
##############################################################################################################################################
        all_pairs = otc_pairs + crypto_pairs + stocks
        parts = text.split(" ", 1)
        if len(parts) == 2:
            expiry, pair = parts
            if pair in all_pairs and expiry in expiry_options:
                signals = ["⬆️", "⬇️"]
                signal = random.choice(signals)
        
                signal_message = f"{signal}"
                payload = {
                    "chat_id": chat_id,
                    "text": signal_message
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
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
