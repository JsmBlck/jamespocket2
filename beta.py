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
            background_tasks.add_task(httpx.post, SEND_MESSAGE, json=payload)
            return {"ok": True}

        if dep >= 30:
            save_authorized_user(user_id, po_id, user.get("username"), user.get("first_name"))
            payload = {
                "chat_id": chat_id,
                "text": f"✅ Deposit found: ${dep:.2f}\n\n🎉 You have been verified and now have full access to the bot!"
            }
        else:
            keyboard = {
                "inline_keyboard": [
                    [{"text": "💸 I've Funded", "callback_data": f"check_funding:{po_id}"}]
                ]
            }
            payload = {
                "chat_id": chat_id,
                "text": (
                    f"Deposit found: ${dep:.2f}\n\n⛔ You need at least $30 to access the bot.\n"
                    "Once you've added more, click the button below to check again."
                ),
                "reply_markup": keyboard
            }

        background_tasks.add_task(httpx.post, SEND_MESSAGE, json=payload)
        return {"ok": True}

    return {"ok": True}

# === HANDLE BUTTON CLICK CALLBACK ===
@app.post("/callback")
async def callback_handler(update: Request, background_tasks: BackgroundTasks):
    data = await update.json()
    callback = data.get("callback_query", {})
    data_text = callback.get("data", "")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    user = callback.get("from", {})
    user_id = user.get("id")

    if data_text.startswith("check_funding:"):
        po_id = data_text.split(":")[1]
        dep = get_deposit_for_trader(po_id)
        if dep and dep >= 30:
            save_authorized_user(user_id, po_id, user.get("username"), user.get("first_name"))
            payload = {
                "chat_id": chat_id,
                "text": f"✅ Deposit verified: ${dep:.2f}\n\n🎉 You now have full access to the bot!"
            }
        else:
            payload = {
                "chat_id": chat_id,
                "text": (
                    f"🚫 Deposit still below $30. Current: ${dep or 0:.2f}\n"
                    "Please fund more and try again later."
                )
            }

        background_tasks.add_task(httpx.post, SEND_MESSAGE, json=payload)
        return {"ok": True}

    return {"ok": True}

# === PING FOR KEEP-ALIVE (optional for Render) ===
@app.get("/")
def home():
    return {"status": "Bot is running."}

# === RUN LOCAL (optional) ===
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
