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

tg_channel = "t.me/ZentraAiRegister"

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
        authorized_sheet.update(f"B{row}", username or "Unknown")
        authorized_sheet.update(f"C{row}", first_name or "Trader")
        authorized_sheet.update(f"D{row}", po_id)
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
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📌  Registration Link", "url": tg_channel}],
                    [{"text": "✅ Check ID", "callback_data": "check_id"}]
                ]
            }
            payload = {
                "chat_id": chat_id,
                "text": (
                    "Welcome! To use this bot, please register your Pocket Option account.\n\n"
                    "Click the registration link below to register.\n\n"
                    "Or if you already registered, click 'Check ID' to verify your account."
                ),
                "reply_markup": keyboard
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}

        if text.isdigit() and len(text) > 5:
            po_id = text.strip()
            dep = get_deposit_for_trader(po_id)
            if dep is None:
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        "⚠️ That Pocket Option Account ID was not found in our records.\n"
                        "Please check your ID or register first."
                    )
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}

            if dep >= 30:
                tg_id = user_id
                username = user.get("username")
                first_name = user.get("first_name")
                save_authorized_user(tg_id, po_id, username, first_name)
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        f"Your account with a total deposit of ${dep:.2f} has been verified!\n"
                        "You now have full access to the bot."
                    )
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}

            keyboard = {
                "inline_keyboard": [
                    [{"text": "I've Funded", "callback_data": f"check_funding:{po_id}"}]
                ]
            }
            payload = {
                "chat_id": chat_id,
                "text": (
                    f"Great! We found your account with a total deposit of ${dep:.2f}.\n\n"
                    "Please fund at least $30 to get full access.\n\n"
                    "Once you have funded, click the button below to confirm."
                ),
                "reply_markup": keyboard
            }
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
                "text": "Please send your Pocket Option Account ID (numbers only)."
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
                        f"Your total deposit is ${dep if dep is not None else 0:.2f}, which is less than $30.\n"
                        "Please fund your account and try again."
                    )
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}

            from_user = cq.get("from", {})
            tg_id = from_user.get("id")
            username = from_user.get("username")
            first_name = from_user.get("first_name")
            save_authorized_user(tg_id, po_id, username, first_name)

            payload = {
                "chat_id": chat_id,
                "text": "You are now verified and have full access to the bot!"
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}

    return {"ok": True}
