import os
import httpx
import asyncio
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
RENDER_URL = os.getenv("RENDER_URL") or "https://yourapp.onrender.com"  # Put your actual Render URL here

# Initialize HTTP client globally
client: httpx.AsyncClient | None = None

# Google Sheets setup
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(creds)
spreadsheet = gs_client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet9")        # Deposits data sheet
authorized_sheet = spreadsheet.worksheet("Sheet11")  # Authorized users sheet

polink = os.getenv("POCKET_LINK")

# OTC pairs and keyboard options
otc_pairs = [
    "AUD/CHF OTC", "GBP/JPY OTC", "QAR/CNY OTC", "CAD/JPY OTC", "AED/CNY OTC",
    "AUD/NZD OTC", "EUR/USD OTC", "BHD/CNY OTC", "EUR/GBP OTC", "NZD/USD OTC",
    "LBP/USD OTC", "GBP/USD OTC", "NGN/USD OTC", "AUD/USD OTC", "GBP/AUD OTC",
    "EUR/JPY OTC", "CHF/NOK OTC", "AUD/CAD OTC", "🔄 Change Category"
]

@asynccontextmanager
async def get_deposit_for_trader(trader_id: str):
    trader_ids = sheet.col_values(1)
    deposits = sheet.col_values(2)
    for idx, tid in enumerate(trader_ids[1:], start=1):
        if tid.strip() == trader_id:
            try:
                yield float(deposits[idx])
            except (ValueError, IndexError):
                yield None
            return
    yield None

def save_authorized_user(tg_id: int, po_id: str, username: str | None, first_name: str | None):
    tg_ids = authorized_sheet.col_values(1)
    if str(tg_id) in tg_ids:
        row = tg_ids.index(str(tg_id)) + 1
        authorized_sheet.update(f"B{row}", [[username or "Unknown"]])
        authorized_sheet.update(f"C{row}", [[first_name or "Trader"]])
        authorized_sheet.update(f"D{row}", [[po_id]])
    else:
        authorized_sheet.append_row([tg_id, username or "Unknown", first_name or "Trader", po_id])
    print(f"✅ Authorized user saved: TG ID {tg_id}, PO ID {po_id}")

async def lifespan(app: FastAPI):
    global client
    client = httpx.AsyncClient(timeout=10)

    async def self_ping_loop():
        await asyncio.sleep(5)
        while True:
            try:
                await client.get(RENDER_URL)
                print("✅ Self-ping successful")
            except Exception as e:
                print(f"❌ Self-ping failed: {e}")
            await asyncio.sleep(300)  # Ping every 5 minutes

    asyncio.create_task(self_ping_loop())
    yield
    await client.aclose()

app = FastAPI(lifespan=lifespan)

@app.api_route("/", methods=["GET", "HEAD"])
async def healthcheck():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    if "message" in data:
        msg = data["message"]
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        user = msg["from"]
        user_id = user["id"]

        # If user is already authorized, send pair selection keyboard directly
        tg_ids = authorized_sheet.col_values(1)
        authorized = str(user_id) in tg_ids

        if text == "/start":
            full_name = user.get("first_name", "Trader")
            username = user.get("username", "")
            username_display = f"@{username}" if username else "No username"

            if authorized:
                keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
                payload = {
                    "chat_id": chat_id,
                    "text": "👇 Please choose a pair to get signal:",
                    "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)

                # Log user start in admin channel
                log_msg = (
                    f"✅ User Started\n\n"
                    f"*Full Name:* {full_name}\n"
                    f"*Username:* {username_display}\n"
                    f"*Telegram ID:* `{user_id}`"
                )
                background_tasks.add_task(client.post, SEND_MESSAGE, json={
                    "chat_id": LOG_CHANNEL_ID,
                    "text": log_msg,
                    "parse_mode": "Markdown"
                })
                return {"ok": True}

            # Not authorized yet - send registration steps
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📌 Registration Link", "url": polink}],
                    [{"text": "✅ Check ID", "callback_data": "check_id"}]
                ]
            }
            welcome_text = (
                f"Welcome {full_name}!\n\n"
                "Let’s get you started — just follow these quick steps below:\n\n"
                "1️⃣ Create an Account:\nClick the “📌 Registration Link” and sign up using a new and unused email address.\n\n"
                "2️⃣ Copy Your Account ID:\nOnce registered, Copy your account ID on your Profile.\n\n"
                "3️⃣ Verify Your ID:\nClick the “✅ Check ID” button and send your account ID, numbers only.\n\n"
                "4️⃣ Fund Your Account:\nAfter registration, simply fund your account with any amount to unlock full access to the bot.\n"
            )
            background_tasks.add_task(client.post, SEND_MESSAGE, json={
                "chat_id": chat_id,
                "text": welcome_text,
                "reply_markup": keyboard
            })

            # Log user start in admin channel
            log_msg = (
                f"✅ User Started\n\n"
                f"*Full Name:* {full_name}\n"
                f"*Username:* {username_display}\n"
                f"*Telegram ID:* `{user_id}`"
            )
            background_tasks.add_task(client.post, SEND_MESSAGE, json={
                "chat_id": LOG_CHANNEL_ID,
                "text": log_msg,
                "parse_mode": "Markdown"
            })
            return {"ok": True}

        # If user sends digits (PO ID)
        if text.isdigit() and len(text) > 5:
            po_id = text.strip()
            async with get_deposit_for_trader(po_id) as dep:
                if dep is None:
                    # Account not found or not registered via your link
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "📌 Registration Link", "url": polink}],
                            [{"text": "✅ Check ID", "callback_data": "check_id"}]
                        ]
                    }
                    msg_text = (
                        "⚠️ That account is not registered or not signed up using my link.\n"
                        "Please register a new account and make sure to use the link I provided."
                    )
                    background_tasks.add_task(client.post, SEND_MESSAGE, json={
                        "chat_id": chat_id,
                        "text": msg_text,
                        "reply_markup": keyboard
                    })
                    return {"ok": True}

                if dep >= 5:  # Minimum deposit required (change if needed)
                    save_authorized_user(user_id, po_id, user.get("username"), user.get("first_name"))
                    keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
                    msg_text = (
                        "✅ You are now verified and can access the bot fully.\n\n"
                        "👇 Please choose a pair to get signal:"
                    )
                    background_tasks.add_task(client.post, SEND_MESSAGE, json={
                        "chat_id": chat_id,
                        "text": msg_text,
                        "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
                    })
                    return {"ok": True}

                # Deposit < minimum required
                msg_text = (
                    "✅ Your account is registered!\n\n"
                    "🔓 You're just one step away from full access.\n\n"
                    "💰 Final Step:\nFund your account with any amount.\n\n"
                    "Once you’ve made the deposit, simply send your Account ID again to complete verification."
                )
                background_tasks.add_task(client.post, SEND_MESSAGE, json={
                    "chat_id": chat_id,
                    "text": msg_text
                })
                return {"ok": True}

        # User sends a pair choice from OTC pairs keyboard
        if text in otc_pairs:
            if not authorized:
                background_tasks.add_task(client.post, SEND_MESSAGE, json={
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nPlease press /start to begin."
                })
                return {"ok": True}

            # Here you could add your signal posting logic based on pair choice
            msg_text = f"📊 Signal for {text} will be sent here soon!"
            background_tasks.add_task(client.post, SEND_MESSAGE, json={
                "chat_id": chat_id,
                "text": msg_text
            })
            return {"ok": True}

    # Fallback response
    return {"ok": True}
