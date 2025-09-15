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

RENDER_URL = "https://oner1s.onrender.com"
BUY_URL = os.getenv("BUY_URL")
SELL_URL = os.getenv("SELL_URL")

client = None


otc_pairs = [
    ["AUD/USD OTC", "AUD/CAD OTC"],
    ["BHD/CNY OTC", "EUR/USD OTC"],
    ["AED/CNY OTC", "GBP/JPY OTC"],
    ["CHF/JPY OTC", "EUR/GBP OTC"],
    ["USD/JPY OTC", "NZD/USD OTC"],
    ["CAD/JPY OTC", "AUD/CHF OTC"]
]

otc_pairs2 = [
    ["AUD/USD OTC", "AUD/CAD OTC"],
    ["BHD/CNY OTC", "EUR/USD OTC"],
    ["AED/CNY OTC", "GBP/JPY OTC"],
    ["CHF/JPY OTC", "EUR/GBP OTC"],
    ["USD/JPY OTC", "NZD/USD OTC"],
    ["CAD/JPY OTC", "AUD/CHF OTC"]
    ["5 Sec", "10 Sec", "15 Sec"]
]
# Flatten for quick "if text in PAIR_SET" checks
PAIR_SET = {p for row in otc_pairs for p in row}
PAIR_SET2 = {p for row in otc_pairs2 for p in row}

expiry_options = ["5 Seconds", "10 Seconds", "15 Seconds"]

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
