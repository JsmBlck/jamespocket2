import os
import httpx
import asyncio
import random
import json
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks
from contextlib import asynccontextmanager
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEND_MESSAGE = f"{API_BASE}/sendMessage"
SEND_CHAT_ACTION = f"{API_BASE}/sendChatAction"
EDIT_MESSAGE = f"{API_BASE}/editMessageText"
DELETE_MESSAGE = f"{API_BASE}/deleteMessage"
RENDER_URL = "https://jamespocket2-uhlu.onrender.com"
client = None
tg_channel = "t.me/ZentraAiRegister"
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




import asyncio
import random

async def simulate_analysis(chat_id: int, pair: str, expiry: str):
    loading_bars = [
        "▯▯▯▯▯",
        "▮▯▯▯▯",
        "▮▮▯▯▯",
        "▮▮▮▯▯",
        "▮▮▮▮▯",
        "▮▮▮▮▮"
    ]

    total_steps = len(loading_bars)
    # Random start percent between 0 and 50
    current_percent = random.randint(0, 50)

    resp = await client.post(SEND_MESSAGE, json={
        "chat_id": chat_id,
        "text": f"🤖 You selected {pair} ☑️\n\n⏳ Time: {expiry}\n\n🔄 Processing... {loading_bars[0]} {current_percent}%"
    })
    message_id = resp.json().get("result", {}).get("message_id")

    # Calculate step increment so that it reaches 100 at the end
    percent_increment = (100 - current_percent) / (total_steps - 1)

    for i, bar in enumerate(loading_bars[1:], start=1):
        await asyncio.sleep(0.8)  # delay between steps
        current_percent = min(100, int(current_percent + percent_increment))
        await client.post(EDIT_MESSAGE, json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": f"🤖 You selected {pair} ☑️\n\n⏳ Time: {expiry}\n\n🔄 Processing... {bar} {current_percent}%"
        })

    signal = random.choice(["⬆️⬆️⬆️", "⬇️⬇️⬇️"])
    await client.post(EDIT_MESSAGE, json={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": f"{signal}"
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
        # Handle /start
        if text == "/start":
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            username = user.get("username")
            username_display = f"@{username}" if username else "Not set"
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

        # Fallback for any other message
        payload = {
            "chat_id": chat_id,
            "text": f"Unknown command. \nClick this 👉 /start."}
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
