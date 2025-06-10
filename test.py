
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
sheet = spreadsheet.worksheet("Sheet9")        # Trader data sheet (read-only for deposit)
authorized_sheet = spreadsheet.worksheet("Sheet11")  # Authorized users sheet
pocketlink = os.getenv("POCKET_LINK")
supportacccount = os.getenv("SUPPORT_LINK")
otc_pairs = [
    "AED/CNY OTC", "AUD/CAD OTC", "BHD/CNY OTC", "EUR/USD OTC", "GBP/USD OTC", "AUD/NZD OTC",
    "NZD/USD OTC", "EUR/JPY OTC", "CAD/JPY OTC", "AUD/USD OTC",  "AUD/CHF OTC", "GBP/AUD OTC"]
expiry_options = ["S5", "S10", "S15", "S30", "M1", "M2"]
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
            await asyncio.sleep(300)  # Every 4 minutes
    asyncio.create_task(self_ping_loop())
    yield
    await client.aclose()
async def delayed_verification_check(client, SEND_MESSAGE, chat_id, po_id, user_id, user, save_authorized_user, otc_pairs):
    await asyncio.sleep(0.9)
    dep = get_deposit_for_trader(po_id)
    if dep is None:
        keyboard = {
                "inline_keyboard": [
                    [{"text": "📌 Registration Link", "url": pocketlink}],
                    [{"text": "✅ Check ID", "callback_data": "check_id"}]
                ]
            }
        payload = {
            "chat_id": chat_id,
            "text": (
                "⚠️ Looks like your account wasn't made using our official link.\n\n"
                "To continue, follow these quick steps:\n"
                "1️⃣ Tap the 📌 Registration Link and sign up using a fresh, unused email. Make sure to use the exact link provided.\n\n"
                "2️⃣ Copy your Account ID from your profile.\n\n"
                "3️⃣ Tap ✅ Check ID and send your ID here to get verified."
            ),
            "reply_markup": keyboard
        }
        await client.post(SEND_MESSAGE, json=payload)
        return
    if dep >= 20:
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
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Check Deposit", "callback_data": "check_deposit"}],
            [{"text": "💬 Contact Support", "url": supportacccount}],
        ]
    }
    payload = {
        "chat_id": chat_id,
        "text": (
            "✅ Your account has been registered!\n\n"
            "🔓 You're almost there — just one last step to unlock full access.\n\n"
            f"💰 Current Deposit: ${dep}\n\n"
            "⛔️ To complete your verification, you need to fund your account with a minimum total deposit of $20.\n\n"
            "📌 Once your total deposit reaches $20 or more, click the button below to continue verification."
        ),
        "reply_markup": keyboard
    }
    await client.post(SEND_MESSAGE, json=payload)

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
                    {"text": "🚀 Start Using the Bot", "url": os.getenv("BOT_LINK")},
                    {"text": "✅ Get the Bot for Free", "url": os.getenv("BOT_LINK")},
                    {"text": "🔥 Claim Your Free Bot", "url": os.getenv("BOT_LINK")},
                    {"text": "⚡ Launch the Bot Now", "url": os.getenv("BOT_LINK")},
                    {"text": "📈 Boost Trades with the Bot", "url": os.getenv("BOT_LINK")},
                    {"text": "🤖 Try the Bot", "url": os.getenv("BOT_LINK")},
                    {"text": "💼 Use the Bot Today", "url": os.getenv("BOT_LINK")},
                    {"text": "🆓 Start Trading with the Bot", "url": os.getenv("BOT_LINK")},
                    {"text": "👆 Tap Here to Get the Bot", "url": os.getenv("BOT_LINK")},
                    {"text": "✨ Use the Bot", "url": os.getenv("BOT_LINK")},
                    {"text": "📲 Grab the Bot ", "url": os.getenv("BOT_LINK")},
                ]
                chosen_button = random.choice(button_options)
                inline_keyboard = {
                    "inline_keyboard": [[chosen_button]]
                }
                payload = {
                    "chat_id": -1002567612473,
                    "video": video_file_id,
                    "caption": caption,
                    "reply_markup": inline_keyboard,
                    "parse_mode": "HTML"}
                send_video_url = f"{API_BASE}/sendVideo"
                background_tasks.add_task(client.post, send_video_url, json=payload)
                return {"ok": True}
        
        if text and text.startswith("/start"):
            parts = text.split(" ")
            start_payload = parts[1] if len(parts) > 1 else None
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
                        "⚠️ Not financial advice. ⚠️ \n\nTrading is risky - play smart, play sharp.\n"
                        "If you’re here to win, let’s make it worth it.\n\n"
                        "👇 Pick an OTC pair and let’s go get it:"
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
                    [{"text": "📌 Registration Link", "url": pocketlink}],
                    [{"text": "✅ Check ID", "callback_data": "check_id"}]
                ]
            }
            payload = {
                "chat_id": chat_id,
                "text": (
                   f"👋 Welcome, {full_name}!\n\n"
                    "You're just a few simple steps away from getting started:\n\n"
                    "1️⃣ Tap the 📌 Registration Link and sign up using a fresh, unused email. Make sure to use the exact link provided.\n\n"
                    "2️⃣ Copy your Account ID from your profile.\n\n"
                    "3️⃣ Tap ✅ Check ID and send your ID here to get verified."
                ),
                "reply_markup": keyboard
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            pair_payload = {
                "chat_id": -1002294677733,
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

        
        if text.isdigit() and len(text) > 5:
            po_id = text.strip()
            checking_steps = [
                "🔍 Checking Account ID.",
                "🔍 Checking Account ID..",
                "🔍 Checking Account ID...",
                "🔎 Still checking...",
                "⏳ Almost there...",
                "🔄 Cross-checking registration...",
                "🧠 Cheking deposit data...",
                "📊 Reading account info...",
                "💾 Finalizing verification...",
                "✅ Checking complete!"
            ]
            # Send first message and store message_id
            resp = await client.post(SEND_MESSAGE, json={
                "chat_id": chat_id,
                "text": checking_steps[0]
            })
            message_id = resp.json().get("result", {}).get("message_id")
        
            # Edit the message with animation steps
            for step in checking_steps[1:]:
                await asyncio.sleep(0.7)
                await client.post(EDIT_MESSAGE, json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": step
                })
                
            # Wait briefly then delete the message
            await asyncio.sleep(1.2)
            await client.post(DELETE_MESSAGE, json={
                "chat_id": chat_id,
                "message_id": message_id
            })
            
            existing_po_ids = authorized_sheet.col_values(4)
            if po_id in existing_po_ids:
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "📌 Registration Link", "url": pocketlink}],
                        [{"text": "✅ Check ID", "callback_data": "check_id"}]
                    ]
                }
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        "⚠️ Looks like this Account ID was already registered by someone else.\n\n"
                        "To continue, follow these quick steps:\n"
                        "1️⃣ Tap the 📌 Registration Link and sign up using a fresh, unused email. Make sure to use the exact link provided.\n\n"
                        "2️⃣ Copy your Account ID from your profile.\n\n"
                        "3️⃣ Tap ✅ Check ID and send your ID here to get verified."
                    ),
                    "reply_markup": keyboard
                }
                await client.post(SEND_MESSAGE, json=payload)
                return {"ok": True}
            background_tasks.add_task(
                delayed_verification_check,
                client, SEND_MESSAGE, chat_id, po_id, user_id, user, save_authorized_user, otc_pairs
            )

            return {"ok": True}
            

##############################################################################################################################################
         # Handle OTC Pair Selection
        if text in otc_pairs:
            tg_ids = authorized_sheet.col_values(1)
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            username = user.get("username")
            username_display = f"@{username}" if username else "Not set"
            if str(user_id) not in tg_ids:
                payload = {
                    "chat_id": chat_id,
                    "text": "❌ You are not authorized to use this command.\nPlease press /start to begin."
                }
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
##############################################################################################################################################
        payload = {
            "chat_id": chat_id,
            "text": f"Unknown command. \nClick this 👉 /start."}
        background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
        return {"ok": True}
##############################################################################################################################################
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
                "text": "Please send your Account ID (numbers only)."
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}

        if data_str == "check_deposit":
            payload = {
                "chat_id": chat_id,
                "text": "Please send your Account ID (numbers only)."
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
            
        _, pair, expiry = data_str.split("|", 2)
        background_tasks.add_task(simulate_analysis, chat_id, pair, expiry)
        return {"ok": True}

        if __name__ == "__main__":
            import uvicorn
            port = int(os.environ.get("PORT", 10000))
            uvicorn.run("app:app", host="0.0.0.0", port=port)
