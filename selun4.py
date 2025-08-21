import os
import httpx
import asyncio
import random
import json
import gspread
import itertools
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks
from contextlib import asynccontextmanager
from oauth2client.service_account import ServiceAccountCredentials
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEND_MESSAGE = f"{API_BASE}/sendMessage"
SEND_CHAT_ACTION = f"{API_BASE}/sendChatAction"
EDIT_MESSAGE = f"{API_BASE}/editMessageText"
DELETE_MESSAGE = f"{API_BASE}/deleteMessage"
SEND_PHOTO = f"{API_BASE}/sendPhoto"

RENDER_URL = "https://selun4.onrender.com"
channel_link = os.getenv("CHANNEL_LINK")
pocketlink = os.getenv("POCKET_LINK")
BUY_URL = os.getenv("BUY_URL")
SELL_URL = os.getenv("SELL_URL")

client = None
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS2"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
spreadsheet = client.open("LyraExclusiveAccess")
sheet = spreadsheet.worksheet("Sheet6")

otc_pairs = [
    ["🇦🇺/🇺🇸 AUD/USD OTC 💵"],
    ["🇦🇺/🇨🇦 AUD/CAD OTC 🍁"],
    ["🇧🇭/🇨🇳 BHD/CNY OTC 🏮"],
    ["🇪🇺/🇺🇸 EUR/USD OTC 💶"],
    ["🇦🇪/🇨🇳 AED/CNY OTC 🕌"]
]

otc_pairs2 = [
    ["⏱️ 5S", "⏱️ 10S", "⏱️ 15S"],
    ["🇦🇺/🇺🇸 AUD/USD OTC 💵"],
    ["🇦🇺/🇨🇦 AUD/CAD OTC 🍁"],
    ["🇧🇭/🇨🇳 BHD/CNY OTC 🏮"],
    ["🇪🇺/🇺🇸 EUR/USD OTC 💶"],
    ["🇦🇪/🇨🇳 AED/CNY OTC 🕌"]
]


# Flatten for quick "if text in PAIR_SET" checks
PAIR_SET = {p for row in otc_pairs for p in row}
PAIR_SET2 = {p for row in otc_pairs2 for p in row}



expiry_options = ["5 Seconds", "10 Seconds", "15 Seconds"]
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
    direction = random.choice(["⬆️⬆️", "⬇️⬇️"])
    photo_url = BUY_URL if "⬆️" in direction else SELL_URL

    await client.post(SEND_PHOTO, json={
        "chat_id": chat_id,
        "photo": photo_url
    })




@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    # --- HANDLE NORMAL TEXT MESSAGES ---
    if msg := data.get("message"):
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        user = msg["from"]
        user_id = user["id"]
        if user_id in ADMIN_IDS:
            media_type = None
            media_file_id = None
            # Check if message has photo or video
            if "photo" in msg and "caption" in msg:
                media_type = "photo"
                media_file_id = msg["photo"][-1]["file_id"]  # highest resolution photo
                caption = msg["caption"]
            elif "video" in msg and "caption" in msg:
                media_type = "video"
                media_file_id = msg["video"]["file_id"]
                caption = msg["caption"]
            if media_type and media_file_id and caption:
                inline_keyboard = {
                    "inline_keyboard": [[
                        {
                            "text": "Access",
                            "url": f"https://t.me/{os.getenv('BOT_USERNAME')}?start=register"
                        }
                    ]]
                }
                payload = {
                    "chat_id": -1002713918801,  # channel hub
                    "caption": caption,
                    "reply_markup": inline_keyboard,
                    "parse_mode": "HTML"
                }
                if media_type == "photo":
                    payload["photo"] = media_file_id
                    send_method = "sendPhoto"
                else:  # video
                    payload["video"] = media_file_id
                    send_method = "sendVideo"
                send_url = f"{API_BASE}/{send_method}"
                background_tasks.add_task(client.post, send_url, json=payload)
                return {"ok": True}
        if text.startswith("/start"):
            parts = text.split()
            param = parts[1] if len(parts) > 1 else None
            if param == "register":
                if user_id not in AUTHORIZED_USERS:
                    # User not authorized - send welcome/register instructions
                    payload = {
                        "chat_id": chat_id,
                        "text": (
                            "🌙 <b>Welcome aboard Seluna Bot</b>\n\n"
                            "Here’s how to get started:\n"
                            "1️⃣ Register through our <a href=\"{pocketlink}\">official link</a>\n"
                            "2️⃣ Copy your <b>Pocket Option ID</b>\n"
                            "3️⃣ Send it to support and unlock your access instantly 🚀"
                        ).replace("{pocketlink}", pocketlink),
                        "parse_mode": "HTML",
                        "reply_markup": {
                            "inline_keyboard": [
                                [
                                    {"text": "🚀 Create Your Account", "url": pocketlink},
                                    {"text": "💬 Contact Support", "url": os.getenv("SUPPORT")}
                                ]
                            ]
                        }
                    }
                    background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            
                elif user_id in AUTHORIZED_USERS:
                    # Authorized user - show OTC pair keyboard
                    keyboard = otc_pairs
                    payload = {
                        "chat_id": chat_id,
                        "text": (
                            "Select a pair to get Signal:"
                        ),
                        "parse_mode": "Markdown",
                        "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
                    }
                    background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            # Default /start behavior
            if user_id not in AUTHORIZED_USERS:
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        "🌙 <b>Welcome aboard Seluna Bot</b>\n\n"
                        "Here’s how to get started:\n"
                        "1️⃣ Register through our <a href=\"{pocketlink}\">official link</a>\n"
                        "2️⃣ Copy your <b>Pocket Option ID</b>\n"
                        "3️⃣ Send it to support and unlock your access instantly 🚀"
                    ).replace("{pocketlink}", pocketlink),
                    "parse_mode": "HTML",
                    "reply_markup": {
                        "inline_keyboard": [
                            [
                                {"text": "🚀 Create Your Account", "url": pocketlink},
                                {"text": "💬 Contact Support", "url": os.getenv("SUPPORT")}
                            ]
                        ]
                    }
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = otc_pairs
            payload = {
                "chat_id": chat_id,
                "text": (
                    "Select an OTC pair:"),
                "parse_mode": "Markdown",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        

        # Handle OTC Pair Selection
        if text in PAIR_SET:
            if user_id not in AUTHORIZED_USERS:
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "Join Channel", "url": channel_link}],]}
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        "⚠️ Access Denied\n\nYou’re not authorized to use this command yet.\n\nJoin the Seluna Bot channel to unlock access — just tap the button below 🌙"),
                    "reply_markup": keyboard}
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = otc_pairs2
            payload = {
                "chat_id": chat_id,
                "text": (
                    "Choose time to trade:"
                ),
                "parse_mode": "Markdown",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
            
        if text in PAIR_SET2:
            if user_id not in AUTHORIZED_USERS:
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "Join Channel", "url": channel_link}],]}
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        "⚠️ Access Denied\n\nYou’re not authorized to use this command yet.\n\nJoin the Seluna Bot channel to unlock access — just tap the button below 🌙"),
                    "reply_markup": keyboard}
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            direction = random.choice(["⬆️⬆️", "⬇️⬇️"])
            photo_url = BUY_URL if "⬆️" in direction else SELL_URL
            
            reply_kb = {
                "keyboard": otc_pairs,
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            
            await client.post(SEND_PHOTO, json={
                "chat_id": chat_id,
                "photo": photo_url,
                "reply_markup": reply_kb
            })
            return {"ok": True}

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
            
                # Prepare full name and username display
                full_name = first_name
                username_display = f"@{username}" if username != "Unknown" else "No username"
            
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
                    "text": f"✅ Added Successful!\n\n{full_name} | {username_display} | {new_user_id} \nPocket Option ID: {pocket_option_id}"
                }
                await client.post(SEND_MESSAGE, json=payload)

            except ValueError:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ Invalid user ID. Please enter a valid number."}
                await client.post(SEND_MESSAGE, json=payload)
            return {"ok": True}
        payload = {
            "chat_id": chat_id,
            "text": f"Unknown command. \nUse /start to get started."}
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
    uvicorn.run("4l60Shark:app", host="0.0.0.0", port=port)
