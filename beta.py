import os
import httpx
import gspread
import json
from fastapi import FastAPI, Request, BackgroundTasks
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
client = httpx.AsyncClient()

# Telegram and Pocket Option Config
BOT_TOKEN = os.getenv("BOT_TOKEN")
tg_channel = os.getenv("TG_CHANNEL")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEND_MESSAGE = f"{API_BASE}/sendMessage"
DELETE_MESSAGE = f"{API_BASE}/deleteMessage"

# Google Sheets Config
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

sheet = gc.open("TelegramBotMembers")
members_sheet = sheet.worksheet("Sheet8")
data_sheet = sheet.worksheet("Sheet7")

# Utils
def get_deposit_for_trader(po_id):
    try:
        records = data_sheet.get_all_records()
        for row in records:
            if str(row.get("trader_id")) == str(po_id):
                return float(row.get("sumdep", 0))
        return None
    except Exception:
        return None

def save_authorized_user(tg_id, po_id, username, firstname):
    members_sheet.append_row([str(tg_id), str(po_id), str(username), str(firstname)])

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
                    [{"text": "📌 Registration Link", "url": tg_channel}],
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
                # Auto verify
                save_authorized_user(user_id, po_id, user.get("username"), user.get("first_name"))
                payload = {
                    "chat_id": chat_id,
                    "text": f"🎉 Your account is verified! Total deposit: ${dep:.2f}.\nYou now have access to the bot."
                }
            else:
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        f"✅ We found your account. Current deposit: ${dep:.2f}.\n\n"
                        "Please fund at least $30 to activate your access."
                    )
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

    return {"ok": True}
