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
    "💸 EUR/USD OTC 🚀", "💸 CAD/JPY OTC 🚀", "💸 AUD/CAD OTC 🚀", "💸 EUR/JPY OTC 🚀",
    "💸 NZD/USD OTC 🚀", "💸 BHD/CNY OTC 🚀", "💸 AUD/USD OTC 🚀", "💸 AED/CNY OTC 🚀"]
expiry_options = ["S5", "S10", "S15"]
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
    # Send initial message with pair and expiry
    await client.post(SEND_MESSAGE, json={
        "chat_id": chat_id,
        "text": f"{pair}\nTime Frame: {expiry}"
    })
    current_percent = random.randint(0, 30)
    filled_blocks = int(current_percent / 10)
    progress_bar = "█" * filled_blocks + "░" * (10 - filled_blocks)
    resp = await client.post(SEND_MESSAGE, json={
        "chat_id": chat_id,
        "text": f"🔄 Analyzing.\n{progress_bar} {current_percent}%"
    })
    message_id = resp.json().get("result", {}).get("message_id")
    dot_states = [".", "..", "..."]
    dot_index = 0
    while current_percent < 100:
        await asyncio.sleep(random.uniform(0.3, 0.5))
        current_percent += random.randint(3, 17)
        current_percent = min(current_percent, 100)

        filled_blocks = int(current_percent / 10)
        progress_bar = "█" * filled_blocks + "░" * (10 - filled_blocks)

        dots = dot_states[dot_index % len(dot_states)]
        dot_index += 1

        await client.post(EDIT_MESSAGE, json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": f"🔄 Analyzing{dots}\n{progress_bar} {current_percent}%"
        })
    signal = random.choice(["⬆️⬆️⬆️", "⬇️⬇️⬇️"])
    await asyncio.sleep(0.5)
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
            keyboard = [otc_pairs[i:i+2] for i in range(0, len(otc_pairs), 2)]
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
                 for i in range(len(expiry_options))]
            ]
            payload = {
                "chat_id": chat_id,
                "text": f"Pair selected {text}\nTime Frame: ❔ ",
                "reply_markup": {"inline_keyboard": inline_kb}}
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
