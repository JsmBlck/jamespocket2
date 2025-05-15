from fastapi import FastAPI, Request, BackgroundTasks
import httpx
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import uvicorn

app = FastAPI()

# === CONFIG ===
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
SEND_MESSAGE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
AUTHORIZED_USERS_SHEET = "TelegramBotMembers"
SHEET7_NAME = "Sheet7"

# === SETUP GOOGLE SHEETS ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client_gs = gspread.authorize(creds)
sheet = client_gs.open(AUTHORIZED_USERS_SHEET)
sheet7 = sheet.worksheet(SHEET7_NAME)

# === UTILS ===
def get_deposit_for_trader(po_id: str):
    try:
        records = sheet7.get_all_records()
        for row in records:
            if str(row.get("trader_id")) == str(po_id):
                return float(row.get("sumdep", 0))
    except Exception as e:
        print("Error fetching deposit:", e)
    return None

def is_user_already_authorized(user_id: int):
    try:
        sheet1 = sheet.worksheet("Sheet1")
        users = sheet1.col_values(1)
        return str(user_id) in users
    except Exception as e:
        print("Error checking user authorization:", e)
        return False

def save_authorized_user(user_id: int, po_id: str, username: str, name: str):
    try:
        sheet1 = sheet.worksheet("Sheet1")
        sheet1.append_row([str(user_id), po_id, username or "", name or ""])
    except Exception as e:
        print("Error saving authorized user:", e)

# === MAIN TELEGRAM ENDPOINT ===
@app.post("/")
async def telegram_webhook(update: Request, background_tasks: BackgroundTasks):
    data = await update.json()
    message = data.get("message") or {}
    text = message.get("text", "").strip()
    user = message.get("from", {})
    chat_id = message.get("chat", {}).get("id")
    user_id = user.get("id")

    if not chat_id or not user_id:
        return {"ok": True}

    # Start command
    if text == "/start":
        payload = {
            "chat_id": chat_id,
            "text": (
                "👋 Welcome! To get access, please register and fund your Pocket Option account.\n\n"
                "1. Register here: https://pocketoption.com/en/cabinet/registration/\n"
                "2. Send me your Pocket Option Account ID (numbers only) to verify your deposit."
            )
        }
        background_tasks.add_task(httpx.post, SEND_MESSAGE, json=payload)
        return {"ok": True}

    # User sends PO account ID
    if text.isdigit() and len(text) > 5:
        po_id = text
        dep = get_deposit_for_trader(po_id)
