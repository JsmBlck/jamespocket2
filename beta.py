import os
import httpx
import gspread
from fastapi import FastAPI, Request, BackgroundTasks
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

app = FastAPI()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SEND_MESSAGE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
ANSWER_CALLBACK = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
client = httpx.AsyncClient()

sheet_name = "TelegramBotMembers"
worksheet_name = "Sheet7"
google_creds = "google-credentials.json"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(google_creds, scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open(sheet_name).worksheet(worksheet_name)

tg_channel = os.getenv("TELEGRAM_CHANNEL_LINK")


def get_deposit_for_trader(trader_id):
    try:
        records = sheet.get_all_records()
        for row in records:
            if str(row["trader_id"]) == str(trader_id):
                return float(row.get("sumdep", 0))
    except Exception:
        pass
    return None


def save_authorized_user(user_id, trader_id, username, first_name):
    sheet.append_row([str(user_id), str(trader_id), username or "", first_name or ""])


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

            # ✅ Auto-verify if deposit >= $30
            if dep >= 30:
                username = user.get("username")
                first_name = user.get("first_name")
                save_authorized_user(user_id, po_id, username, first_name)
                payload = {
                    "chat_id": chat_id,
                    "text": "🎉 Congratulations! You have been verified automatically and now have access to the bot."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}

            keyboard = {
                "inline_keyboard": [
                    [{"text": "💸 I've Funded", "callback_data": f"check_funding:{po_id}"}]
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

    elif callback := data.get("callback_query"):
        query_id = callback["id"]
        user = callback["from"]
        user_id = user["id"]
        chat_id = callback["message"]["chat"]["id"]
        data = callback.get("data", "")

        if data == "check_id":
            payload = {
                "chat_id": chat_id,
                "text": "Please send your Pocket Option Account ID (a number) to continue."
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            background_tasks.add_task(client.post, ANSWER_CALLBACK, json={"callback_query_id": query_id})
            return {"ok": True}

        if data.startswith("check_funding:"):
            po_id = data.split(":")[1]
            dep = get_deposit_for_trader(po_id)
            if dep is not None and dep >= 30:
                username = user.get("username")
                first_name = user.get("first_name")
                save_authorized_user(user_id, po_id, username, first_name)
                payload = {
                    "chat_id": chat_id,
                    "text": "✅ Verified! You now have access to the bot. Welcome aboard!"
                }
            else:
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        f"⛔ Still showing ${dep:.2f} deposited.\n\n"
                        "Please wait a few minutes and try again if you just funded."
                    )
                }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            background_tasks.add_task(client.post, ANSWER_CALLBACK, json={"callback_query_id": query_id})
            return {"ok": True}

    return {"ok": True}
