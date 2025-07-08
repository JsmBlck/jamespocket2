import os
import httpx
import asyncio
import random
import json
import gspread
from collections import defaultdict
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
RENDER_URL = "https://fourlgosh4rk.onrender.com"

client = None
AUTHORIZED_USERS = set()

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client_gsheet = gspread.authorize(creds)
spreadsheet = client_gsheet.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet19")        # Trader data sheet (read-only for deposit)
authorized_sheet = spreadsheet.worksheet("Sheet14")  # Authorized users sheet

pocketlink = os.getenv("POCKET_LINK")
quotexlink = os.getenv("QUOTEX_LINK")
botlink = os.getenv("BOT_LINK")
joinchannel = os.getenv("CHANNEL_LINK")
channelusername = os.getenv("CHANNEL_USERNAME")  

expiry_options = ["S5", "S10", "S15"]
otc_pairs = [
    "AUD/CHF OTC", "GBP/JPY OTC", "QAR/CNY OTC", "CAD/JPY OTC", "AED/CNY OTC", "AUD/NZD OTC",
    "EUR/USD OTC", "BHD/CNY OTC", "EUR/GBP OTC", "NZD/USD OTC", "LBP/USD OTC", "GBP/USD OTC",
    "NGN/USD OTC", "AUD/USD OTC", "GBP/AUD OTC", "EUR/JPY OTC", "CHF/NOK OTC", "AUD/CAD OTC"
]

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
def load_authorized_users():
    global AUTHORIZED_USERS
    AUTHORIZED_USERS = set()
    user_ids = authorized_sheet.col_values(1)
    print(f"Fetched user IDs from GSheet: {user_ids}")
    for user_id in user_ids[1:]:
        if user_id.strip():
            try:
                AUTHORIZED_USERS.add(int(user_id))
            except ValueError:
                print(f"Skipping invalid ID: {user_id}")
    print(f"Loaded authorized users: {AUTHORIZED_USERS}")
def save_authorized_user(tg_id: int, po_id: str, username: str = None, first_name: str = None):
    tg_ids = authorized_sheet.col_values(1)
    if str(tg_id) in tg_ids:
        row = tg_ids.index(str(tg_id)) + 1
        authorized_sheet.update(f"B{row}", [[username or "Unknown"]])
        authorized_sheet.update(f"C{row}", [[first_name or "Trader"]])
        authorized_sheet.update(f"D{row}", [[po_id]])
    else:
        authorized_sheet.append_row([tg_id, username or "Unknown", first_name or "Trader", po_id])
    AUTHORIZED_USERS.add(tg_id)
    print(f"✅ Authorized user saved: TG ID {tg_id}, PO ID {po_id}")
@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = httpx.AsyncClient(timeout=10)
    load_authorized_users()  # Load once on startup
    async def self_ping_loop():
        await asyncio.sleep(5)
        while True:
            try:
                await client.get(RENDER_URL)
                print("✅ Self-ping successful!")
            except Exception as e:
                print(f"❌ Ping failed: {e}")
            try:
                load_authorized_users()  # Refresh the authorized users
                print("🔄 Refreshed authorized users.")
            except Exception as e:
                print(f"❌ Failed to load authorized users: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes
    asyncio.create_task(self_ping_loop())
    yield
    await client.aclose()

async def check_user_joined_channel(user_id: int) -> bool:
    url = f"{API_BASE}/getChatMember"
    params = {
        "chat_id": channelusername, # Replace with your channel username or -100123456789
        "user_id": user_id
    }
    try:
        resp = await client.get(url, params=params)
        data = resp.json()
        if data.get("ok"):
            status = data["result"]["status"]
            return status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"❌ Failed to check channel membership: {e}")
    return False


async def delayed_verification_check(client, SEND_MESSAGE, chat_id, po_id, user_id, user, save_authorized_user, otc_pairs):
    await asyncio.sleep(0.9)
    dep = get_deposit_for_trader(po_id)
    if dep is None:
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 Restart Process", "callback_data": "restart_process"}]
            ]
        }
        payload = {
            "chat_id": chat_id,
            "text": (
                "⚠️ Uh-oh! Your account isn’t linked through our official registration link.\n\n"
                "To continue, please sign up again using the correct link we shared earlier.\n\n"
                "Tap the button below to get started 👇"
            ),
            "reply_markup": keyboard
        }
        await client.post(SEND_MESSAGE, json=payload)
        return
    if dep >= 30:
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

    payload = {
        "chat_id": chat_id,
        "text": (
        f"✅ Account ID: {po_id}\n\n"
        f"💰 Total Deposit: ${dep}\n\n"
        "✅ Your account is registered!\n\n"
        "🔓 Almost there! Just one more step to unlock full access.\n\n"
        "💵 To proceed:\nMake a minimum deposit of $30 to your account.\n\n"
        "Once done, resend your Account ID to complete the verification process."
        )
    }
    await client.post(SEND_MESSAGE, json=payload)

app = FastAPI(lifespan=lifespan)

@app.api_route("/", methods=["GET", "HEAD"])
async def healthcheck(request: Request):
    return {"status": "ok"}


async def process_media_group(group_id):
    await asyncio.sleep(3)  # Wait to collect all parts

    items = media_buffer.pop(group_id, [])
    caption = media_captions.pop(group_id, "")

    if not items:
        return

    # Attach caption only to first media
    items[0]["caption"] = caption
    items[0]["parse_mode"] = "HTML"

    await client.post(
        f"{API_BASE}/sendMediaGroup",
        json={
            "chat_id": -1002750311750,
            "media": items
        }
    )

    # Send the inline button after the album
    inline_keyboard = {
        "inline_keyboard": [[
            {
                "text": "🚀 Get Started for Free",
                "url": f"https://t.me/{os.getenv('BOT_USERNAME')}?start=register"
            }
        ]]
    }

    await client.post(
        f"{API_BASE}/sendMessage",
        json={
            "chat_id": -1002750311750,
            "text": f"{caption}",
            "reply_markup": inline_keyboard
        }
    )

media_buffer = defaultdict(list)
media_captions = {}

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    if msg := data.get("message"):
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        user = msg["from"]
        user_id = user["id"]
        
        if user_id in ADMIN_IDS:
            media_type = None
            media_file_id = None
            caption = msg.get("caption")
            media_group_id = msg.get("media_group_id")
        
            # Detect photo
            if "photo" in msg:
                media_type = "photo"
                media_file_id = msg["photo"][-1]["file_id"]
            # Detect video
            elif "video" in msg:
                media_type = "video"
                media_file_id = msg["video"]["file_id"]
        
            # ✅ If it's part of a media group (album)
            if media_group_id and media_type and media_file_id:
                media_buffer[media_group_id].append({
                    "type": media_type,
                    "media": media_file_id
                })
                if caption:
                    media_captions[media_group_id] = caption
                background_tasks.add_task(process_media_group, media_group_id)
                return {"ok": "album buffering"}
        
            # ✅ Single media file (not album)
            if media_type and media_file_id and caption:
                inline_keyboard = {
                    "inline_keyboard": [[
                        {
                            "text": "🚀 Get Started for Free",
                            "url": f"https://t.me/{os.getenv('BOT_USERNAME')}?start=register"
                        }
                    ]]
                }
        
                payload = {
                    "chat_id": -1002750311750,
                    "caption": caption,
                    "reply_markup": inline_keyboard,
                    "parse_mode": "HTML"
                }
        
                if media_type == "photo":
                    payload["photo"] = media_file_id
                    send_method = "sendPhoto"
                else:
                    payload["video"] = media_file_id
                    send_method = "sendVideo"
        
                send_url = f"{API_BASE}/{send_method}"
                background_tasks.add_task(client.post, send_url, json=payload)
                return {"ok": "single media sent"}

        
        if text == "/start":
            message = data.get("message", {})  
            from_user = message.get("from", {}) 
            full_name = from_user.get("first_name", "Trader")
            username = from_user.get("username", "")
            username_display = f"@{username}" if username else "No username"
            user_id = from_user.get("id", "N/A")
            
            # Check if user joined the required channel
            is_member = await check_user_joined_channel(user_id)
            if not is_member:
                join_payload = {
                    "chat_id": chat_id,
                    "text": (
                        "📢 *Join Required*\n\n"
                        "To use this bot, you need to join our official Telegram channel first.\n\n"
                        "Once you've joined, press /start again."
                    ),
                    "parse_mode": "Markdown",
                    "reply_markup": {
                        "inline_keyboard": [
                            [{"text": "🔗 Join Channel", "url": joinchannel}]
                        ]
                    }
                }

                background_tasks.add_task(client.post, SEND_MESSAGE, json=join_payload)
                return {"ok": True}
        
            # Continue if the user is a member
            if user_id in AUTHORIZED_USERS:
                keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
                payload = {
                    "chat_id": chat_id,
                    "text": (
                        "👇 Please choose a pair to get signal:"
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
                    [{"text": "Pocket Broker", "callback_data": "broker_pocket"}],
                    [{"text": "Quotex", "callback_data": "broker_quotex"}]
                ]
            }
            payload = {
                "chat_id": chat_id,
                "text": (
                    f"Hey {full_name}, welcome! 🙌\n\n"
                    "Which broker do you want to use?"
                ),
                "reply_markup": keyboard
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

        if text in otc_pairs:
            tg_ids = authorized_sheet.col_values(1)
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            username = user.get("username")
            username_display = f"@{username}" if username else "Not set"
            if user_id not in AUTHORIZED_USERS:
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
            "text": "Unknown command. Please press /start to begin."}
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
                "text": "Please send your Account ID (numbers only).\n❌ : id 123123123\n✅ : 123123123"
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        
            from_user = cq.get("from", {})
            tg_id = from_user.get("id")
            username = from_user.get("username")
            first_name = from_user.get("first_name")
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
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}

        if data_str.startswith("expiry|"):
            _, pair, expiry = data_str.split("|", 2)
            signals = ["⬆️", "⬇️"]
            signal = random.choice(signals)
            
            # Send signal to user
            signal_message = f"{signal}"
            payload = {
                "chat_id": chat_id,
                "text": signal_message
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
        
            # Safe user info extraction
            message = cq.get("message", {})
            from_user = cq.get("from", {})
            full_name = from_user.get("first_name", "Unknown")
            username = from_user.get("username", "")
            username_display = f"@{username}" if username else "No username"
            user_id = from_user.get("id", "N/A")
        
            # Send user trade log to channel/group
            pair_payload = {
                "chat_id": -1002676665035,
                "text": (
                    "📊 *User Trade Action*\n\n"
                    f"*Full Name:* {full_name}\n"
                    f"*Username:* {username_display}\n"
                    f"*Telegram ID:* `{user_id}`\n"
                    f"*Selected Pair:* {pair}\n"
                    f"*Selected Time:* {expiry}\n"
                    f"*Signal:* {signal}"
                ),
                "parse_mode": "Markdown"
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=pair_payload)
            return {"ok": True}
