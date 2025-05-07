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
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
spreadsheet = client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet5")
tg_channel = "t.me/ZentraAiRegister"
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
otc_pairs = [
    "AED/CNY OTC", "AUD/CAD OTC", "BHD/CNY OTC", "EUR/USD OTC", "GBP/USD OTC", "AUD/NZD OTC",
    "NZD/USD OTC", "EUR/JPY OTC", "CAD/JPY OTC", "AUD/USD OTC",  "AUD/CHF OTC", "GBP/AUD OTC"]
expiry_options = ["S5", "S10", "S15", "S30", "M1", "M2"]
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




async def simulate_analysis(chat_id: int, pair: str, expiry: str):
    analysis_steps = [
        f"🤖 You selected {pair} ☑️\n\n⏳ Time: {expiry}\n\n🔎 Analyzing.",
        f"🤖 You selected {pair} ☑️\n\n⌛ Time: {expiry}\n\n🔎 Analyzing..",
        f"🤖 You selected {pair} ☑️\n\n⏳ Time: {expiry}\n\n🔎 Analyzing...",
        f"🤖 You selected {pair} ☑️\n\n⌛ Time: {expiry}\n\n📊 Gathering data.",
        f"🤖 You selected {pair} ☑️\n\n⏳ Time: {expiry}\n\n📊 Gathering data..",
        f"🤖 You selected {pair} ☑️\n\n⌛ Time: {expiry}\n\n📊 Gathering data...",
        f"🤖 You selected {pair} ☑️\n\n⏳ Time: {expiry}\n\n📈 Calculating signal.",
        f"🤖 You selected {pair} ☑️\n\n⌛ Time: {expiry}\n\n📉 Calculating signal..",
        f"🤖 You selected {pair} ☑️\n\n⏳ Time: {expiry}\n\n📈 Calculating signal...",
        f"🤖 You selected {pair} ✅\n\n⌛ Time: {expiry}\n\n✅ Analysis complete."]
    resp = await client.post(SEND_MESSAGE, json={"chat_id": chat_id, "text": analysis_steps[0]})
    message_id = resp.json().get("result", {}).get("message_id")
    for step in analysis_steps[1:]:
        await client.post(EDIT_MESSAGE, json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": step})
    signal = random.choice(["↗️", "↘️"])
    final_text = f"{signal}"
    await client.post(EDIT_MESSAGE, json={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": final_text})




@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    # --- HANDLE NORMAL TEXT MESSAGES ---
    if msg := data.get("message"):
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        user = msg["from"]
        user_id = user["id"]
        # Handle /start
        if text == "/start":
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            username = user.get("username")
            username_display = f"@{username}" if username else "Not set"
            if user_id not in AUTHORIZED_USERS:
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        "You don't have access to use this bot yet.\n\n"
                        f"To get verified:\n\nJoin {tg_channel} and tap the 📌 Pinned message to register."),
                    "parse_mode": "Markdown"}
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                admin_payload = {
                "chat_id": -1002294677733, 
                "text": f"✅ User Started\n\n"
                        f"*Full Name:* {full_name}\n"
                        f"*Username:* {username_display}\n"
                        f"*Telegram ID:* `{user_id}`",
                "parse_mode": "Markdown"}
                background_tasks.add_task(client.post, SEND_MESSAGE, json=admin_payload)
                return {"ok": True}
            keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
            payload = {
                "chat_id": chat_id,
                "text": (
                    "⚠️ Not financial advice. ⚠️ \n\nTrading is risky - play smart, play sharp.\n"
                    "If you’re here to win, let’s make it worth it.\n\n"
                    "👇 Pick an OTC pair and let’s go get it:"),
                "parse_mode": "Markdown",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}}
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            admin_payload = {
                "chat_id": -1002294677733, 
                "text": f"✅ User Started\n\n"
                        f"*Full Name:* {full_name}\n"
                        f"*Username:* {username_display}\n"
                        f"*Telegram ID:* `{user_id}`",
                "parse_mode": "Markdown"}
            background_tasks.add_task(client.post, SEND_MESSAGE, json=admin_payload)
            return {"ok": True}

        # Handle OTC Pair Selection
        if text in otc_pairs:
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            username = user.get("username")
            username_display = f"@{username}" if username else "Not set"
            if user_id not in AUTHORIZED_USERS:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nMessage my support to gain access!"}
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            inline_kb = [
                [{"text": expiry_options[i], "callback_data": f"expiry|{text}|{expiry_options[i]}"} 
                 for i in range(row, row + 3)]
                for row in range(0, len(expiry_options), 3)]
            payload = {
                "chat_id": chat_id,
                "text": f"🤖 You selected {text} ☑️\n\n⌛ Select Time:",
                "reply_markup": {"inline_keyboard": inline_kb}}
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            pair_payload = {
                "chat_id": -1002294677733, 
                "text": (
                    "📊 *User Trade Action*\n\n"
                    f"*Full Name:* {full_name}\n"
                    f"*Username:* {username_display}\n"
                    f"*Telegram ID:* `{user_id}`\n"
                    f"*Selected Pair:* {text}"
                ),
                "parse_mode": "Markdown"}
            background_tasks.add_task(client.post, SEND_MESSAGE, json=pair_payload)

            return {"ok": True}

        # Handle /addmember
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
                    "text": f"✅ User {new_user_id} added with Pocket Option ID: {pocket_option_id}"}
                await client.post(SEND_MESSAGE, json=payload)
            except ValueError:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ Invalid user ID. Please enter a valid number."}
                await client.post(SEND_MESSAGE, json=payload)
            return {"ok": True}

        # Handle /removemember
        if text.startswith(("/removemember", "/remove")):
            if user_id not in ADMIN_IDS:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nMessage my support to gain access!"}
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            parts = text.strip().split()
            if len(parts) < 2:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ Usage: /removemember <user_id>"}
                await client.post(SEND_MESSAGE, json=payload)
                return {"ok": True}
            try:
                remove_user_id = str(parts[1])
                user_ids = sheet.col_values(1)
                if remove_user_id in user_ids:
                    row = user_ids.index(remove_user_id) + 1
                    sheet.delete_rows(row)
                    AUTHORIZED_USERS.discard(int(remove_user_id))
                    payload = {
                        "chat_id": chat_id,
                        "text": f"✅ User {remove_user_id} has been removed successfully."}
                else:
                    payload = {
                        "chat_id": chat_id,
                        "text": "⚠️ User ID not found in the list."}
            except ValueError:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ Invalid user ID. Please enter a valid number."}
            await client.post(SEND_MESSAGE, json=payload)
            return {"ok": True}
        
        # Fallback for any other message
        payload = {
            "chat_id": chat_id,
            "text": f"Unknown command."}
        background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
        return {"ok": True}

    # --- HANDLE CALLBACKS ---
    if cq := data.get("callback_query"):
        data_str = cq.get("data", "")
        chat_id = cq["message"]["chat"]["id"]
        message_id = cq["message"]["message_id"]
        cq_id = cq.get("id")
        background_tasks.add_task(client.post, f"{API_BASE}/answerCallbackQuery", json={"callback_query_id": cq_id})
        background_tasks.add_task(client.post, DELETE_MESSAGE, json={"chat_id": chat_id, "message_id": message_id})
        _, pair, expiry = data_str.split("|", 2)
        background_tasks.add_task(simulate_analysis, chat_id, pair, expiry)
        return {"ok": True}
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
