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

expiry_options = ["S5", "S10", "S15"]
otc_pairs = [
    "AUD/CHF OTC", "GBP/JPY OTC", "QAR/CNY OTC", "CAD/JPY OTC", "AED/CNY OTC", "AUD/NZD OTC",
    "EUR/USD OTC", "BHD/CNY OTC", "EUR/GBP OTC", "NZD/USD OTC", "LBP/USD OTC", "GBP/USD OTC",
    "NGN/USD OTC", "AUD/USD OTC", "GBP/AUD OTC", "EUR/JPY OTC", "CHF/NOK OTC", "AUD/CAD OTC",
    "🔄 Change Category"
]

crypto_pairs = [
    "Bitcoin OTC", "Ethereum OTC", "Polkadot OTC", "Polygon OTC", "Bitcoin ETF OTC", "TRON OTC",
    "Chainlink OTC", "Dogecoin OTC", "Solana OTC", "Cardano OTC", "Toncoin OTC", "Avalanche OTC",
    "Bitcoin Cash OTC", "Bonk OTC", "Litecoin OTC", "Pepe OTC", "Ripple OTC", "Shiba Inu OTC",
    "🔄 Change Category"
]

stocks = [
    "Apple OTC", "FACEBOOK INC OTC", "Intel OTC", "American Express OTC", "Johnson & Johnson OTC", "McDonald's OTC", "Tesla OTC", "Amazon OTC",
    "GameStop Corp OTC", "Netflix OTC", "VIX OTC", "VISA OTC", "🔄 Change Category"
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
                "⚠️ Oops! It looks like your account isn’t registered through our official link.\n\n"
                "To proceed, please create a new account using the correct registration link provided earlier.\n\n"
                "Tap below to start over 👇"
            ),
            "reply_markup": keyboard
        }
        await client.post(SEND_MESSAGE, json=payload)
        return
    if dep >= 5:
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
            "✅ Your account is registered!\n\n"
            "🔓 You're just one step away from full access.\n\n"
            "💰 Final Step:\nFund your account with any amount.\n\n"
            "Once you’ve made the deposit, simply send your Account ID again to complete verification."
        )
    }
    await client.post(SEND_MESSAGE, json=payload)

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

        if user_id in ADMIN_IDS:
            # Check if message contains video and caption
            if "video" in msg and "caption" in msg:
                video_file_id = msg["video"]["file_id"]
                caption = msg["caption"]
                button_options = [
                    {"text": "🚀 Start Using the Bot for Free", "url": os.getenv("BOT_LINK")},
                    {"text": "🤖 Launch the Free Trading Bot Now", "url": os.getenv("BOT_LINK")},
                    {"text": "✅ Click Here to Get the Bot for Free", "url": os.getenv("BOT_LINK")},
                    {"text": "🚀 Start the Bot – No Cost!", "url": os.getenv("BOT_LINK")},
                    {"text": "🔥 Grab Your Free Bot Access!", "url": os.getenv("BOT_LINK")},
                    {"text": "⚡ Activate Your Trading Bot Today", "url": os.getenv("BOT_LINK")},
                    {"text": "🎯 Get the Bot and Start Winning!", "url": os.getenv("BOT_LINK")},
                    {"text": "💥 Don’t Miss Out – Get the Bot Now", "url": os.getenv("BOT_LINK")},
                    {"text": "📈 Boost Your Trades with This Bot!", "url": os.getenv("BOT_LINK")},
                    {"text": "🚀 Ready to Trade? Get Your Bot Here!", "url": os.getenv("BOT_LINK")},
                ]
                chosen_button = random.choice(button_options)
                inline_keyboard = {
                    "inline_keyboard": [[chosen_button]]
                }
                payload = {
                    "chat_id": -1002549064084,
                    "video": video_file_id,
                    "caption": caption,
                    "reply_markup": inline_keyboard,
                    "parse_mode": "HTML"}
                send_video_url = f"{API_BASE}/sendVideo"
                background_tasks.add_task(client.post, send_video_url, json=payload)
                return {"ok": True}
        
        if text == "/start":
            message = data.get("message", {})  
            from_user = message.get("from", {}) 
            full_name = from_user.get("first_name", "Trader")
            username = from_user.get("username", "")
            username_display = f"@{username}" if username else "No username"
            user_id = from_user.get("id", "N/A")
            tg_ids = authorized_sheet.col_values(1)
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
        if text == "🔄 Change Category":
            if user_id not in AUTHORIZED_USERS:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nPlease press /start to begin."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = [["Currencies", "Stocks", "Crypto"]]
            payload = {
                "chat_id": chat_id,
                "text": "🔄 Select a Category you prefer:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        elif text == "Currencies":
            if user_id not in AUTHORIZED_USERS:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nPlease press /start to begin."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "You chose the Currencies category. 🕒 Choose an OTC pair to trade:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        elif text == "Stocks":
            if user_id not in AUTHORIZED_USERS:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nPlease press /start to begin."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = [stocks[i:i+3] for i in range(0, len(stocks), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "You chose the Stocks category. 🕒 Choose a stock to trade:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        elif text == "Crypto":
            if user_id not in AUTHORIZED_USERS:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nPlease press /start to begin."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            keyboard = [crypto_pairs[i:i+3] for i in range(0, len(crypto_pairs), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "You chose the Cryptocurrencies category. 💰 Choose a crypto currency to trade:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
##############################################################################################################################################
        if text in crypto_pairs or text in otc_pairs or text in stocks:
            if user_id not in AUTHORIZED_USERS:
                payload = {
                    "chat_id": chat_id,
                    "text": "⚠️ You need to get verified to use this bot.\nPlease press /start to begin."
                }
                background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
                return {"ok": True}
            inline_kb = [
                [{"text": expiry_options[i], "callback_data": f"expiry|{text}|{expiry_options[i]}"} 
                 for i in range(len(expiry_options))]
            ]
            payload = {
                "chat_id": chat_id,
                "text": f"Choose your expiry time.",
                "reply_markup": {"inline_keyboard": inline_kb}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
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

        if data_str in ["broker_pocket", "broker_quotex"]:
            broker_name = "Pocket Broker" if data_str == "broker_pocket" else "Quotex"
            register_link = pocketlink if data_str == "broker_pocket" else quotexlink
        
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📌 Registration Link", "url": register_link}],
                    [{"text": "✅ Check ID", "callback_data": "check_id"}]
                ]
            }
            payload = {
                "chat_id": chat_id,
                "text": (
                    f"Great choice! Let's set you up with {broker_name} 🛠️\n\n"
                    "Just follow these 4 quick steps:\n\n"
                    "1️⃣ Create an Account\nTap the “📌 Registration Link” and sign up with a new, unused email.\n\n"
                    "2️⃣ Copy Your Account ID\nAfter registration, head to your profile and copy your account ID.\n\n"
                    "3️⃣ Verify Your ID\nClick the “✅ Check ID” button and send your account ID (numbers only).\n\n"
                    "4️⃣ Fund Your Account\nDeposit any amount to unlock full access to the bot features.\n\n"
                ),
                "reply_markup": keyboard
            }
        
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}

        
        
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

        if data_str == "restart_process":
            message = cq.get("message", {})
            from_user = cq.get("from", {})
            full_name = from_user.get("first_name", "Trader")
            keyboard = {
                "inline_keyboard": [
                    [{"text": "Pocket Broker", "callback_data": "broker_pocket"}],
                    [{"text": "Quotex", "callback_data": "broker_quotex"}]
                ]
            }
            payload = {
                "chat_id": chat_id,
                "text": (
                    f"Hey {full_name}, welcome back! 🙌\n\n"
                    "Which broker do you want to use?"
                ),
                "reply_markup": keyboard
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
