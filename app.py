import os
import httpx
import asyncio
import random
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks
from contextlib import asynccontextmanager
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
client = None  # Global httpx client
# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
spreadsheet = client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet5")  # Us

def load_authorized_users():
    global AUTHORIZED_USERS
    AUTHORIZED_USERS = set()  # Reset the set

    user_ids = sheet.col_values(1)  # Get all user IDs from column 1

    print(f"Fetched user IDs from GSheet: {user_ids}")  # Debugging

    for user_id in user_ids[1:]:  # Skip the first row (header)
        if user_id.strip():  # Avoid empty cells
            try:
                AUTHORIZED_USERS.add(int(user_id))  # Convert to integer
            except ValueError:
                print(f"Skipping invalid ID: {user_id}")  # Debugging for non-numeric values

    print(f"Loaded authorized users: {AUTHORIZED_USERS}")  # Debugging

# Save authorized users to Google Sheets		
def save_users():
    """Save authorized users in Google Sheets without altering existing data."""
    
    # Get all user IDs currently stored in the sheet
    user_ids = sheet.col_values(1)  # Column A (TG ID)

    # Add headers if the sheet is empty
    if not user_ids:
        sheet.append_row(["TG ID", "TG Username", "TG Name", "PocketOption ID"])
        user_ids = sheet.col_values(1)  # Refresh after adding headers

    for user_id in AUTHORIZED_USERS:
        user_info = user_data.get(user_id, {})
        tg_username = user_info.get("username", "Unknown")
        tg_name = user_info.get("first_name", "Trader")
        pocket_option_id = user_info.get("pocket_option_id", "N/A")

        user_id_str = str(user_id)  # Ensure ID matches the format in Sheets

        if user_id_str in user_ids:
            # Update existing row for the user
            row_number = user_ids.index(user_id_str) + 1  # Find row number
            sheet.update(f"B{row_number}", [[tg_username]])  # Update Username
            sheet.update(f"C{row_number}", [[tg_name]])  # Update Name
            sheet.update(f"D{row_number}", [[pocket_option_id]])  # Update PocketOption ID
        else:
            # Append new user as a new row
            sheet.append_row([user_id, tg_username, tg_name, pocket_option_id])

    print("✅ Users saved successfully!")
    
load_authorized_users()



otc_pairs = [
    "AED/CNY OTC", "AUD/CAD OTC", "BHD/CNY OTC", "EUR/USD OTC", "GBP/USD OTC", "AUD/NZD OTC",
    "NZD/USD OTC", "EUR/JPY OTC", "CAD/JPY OTC", "AUD/USD OTC",  "AUD/CHF OTC", "GBP/AUD OTC"
]
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
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n🔎 Analyzing.",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n🔎 Analyzing..",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n🔎 Analyzing...",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n🔎 Analyzing....",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📊 Gathering data.",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📊 Gathering data..",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📊 Gathering data...",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📊 Gathering data....",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📈 Calculating signal.",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📈 Calculating signal..",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📈 Calculating signal...",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📈 Calculating signal....",
        f"🤖 {pair} ✅\n\n⌛ Time: {expiry}\n\n📊 Analysis complete."
    ]

    # Send the first analysis message and get the message_id directly
    resp = await client.post(SEND_MESSAGE, json={"chat_id": chat_id, "text": analysis_steps[0]})
    message_id = resp.json().get("result", {}).get("message_id")

    # Show each analysis step with a minimal delay
    for step in analysis_steps[1:]:
        await client.post(EDIT_MESSAGE, json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": step
        })
    # Simulate final signal
    await asyncio.sleep(0.3)  # Reduced delay
    signal = random.choice(["↗️", "↘️"])
    final_text = f"{signal}"
    await client.post(EDIT_MESSAGE, json={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": final_text
    })

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    if msg := data.get("message"):
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]  # Add this line

        if text == "/start":
            if user_id not in AUTHORIZED_USERS:
                payload = {
                    "chat_id": chat_id,
                    "text": "❌ Access Denied.\nYou are not authorized to use this bot."
                }
                client.post(SEND_MESSAGE, json=payload)
                return {"ok": True}

            keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "Select an OTC pair:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}

        if text in otc_pairs:
            inline_kb = [
                [{"text": expiry_options[i], "callback_data": f"expiry|{text}|{expiry_options[i]}"} 
                 for i in range(row, row + 3)]
                for row in range(0, len(expiry_options), 3)
            ]
            payload = {
                "chat_id": chat_id,
                "text": f"🤖 {text} ☑️\n\n⌛ Select Time:",
                "reply_markup": {"inline_keyboard": inline_kb}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}

        background_tasks.add_task(client.post, SEND_MESSAGE, json={"chat_id": chat_id, "text": f"You said: {text}"})
        return {"ok": True}

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
