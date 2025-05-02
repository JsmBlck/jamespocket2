import os
import httpx
import asyncio
import random
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

load_dotenv()  # Load environment variables from .env if present

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEND_MESSAGE = f"{API_BASE}/sendMessage"
SEND_CHAT_ACTION = f"{API_BASE}/sendChatAction"
EDIT_MESSAGE = f"{API_BASE}/editMessageText"
RENDER_URL = "https://jamespocket2-k9lz.onrender.com"

# List of OTC pairs for reply keyboard
otc_pairs = [
    "AED/CNY OTC", 
    "AUD/CAD OTC",   
    "BHD/CNY OTC",  
    "EUR/USD OTC",
    "GBP/USD OTC",
    "NZD/USD OTC"
]

# Lifespan manager to start self-ping loop
@asynccontextmanager
async def lifespan(app: FastAPI):
    async def self_ping_loop():
        await asyncio.sleep(5)  # wait for server startup
        while True:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.get(RENDER_URL)
                print("✅ Self-ping successful!")
            except Exception as e:
                print(f"❌ Ping failed: {e}")
            await asyncio.sleep(300)  # wait 5 minutes

    # Schedule self-ping in background
    asyncio.create_task(self_ping_loop())
    yield
    # (optional) shutdown cleanup here

app = FastAPI(lifespan=lifespan)

@app.api_route("/", methods=["GET", "HEAD"])
async def healthcheck(request: Request):
    return {"status": "ok"}

async def simulate_analysis(chat_id: int, pair: str):
    # Optional: send an "Analyzing..." placeholder
    async with httpx.AsyncClient() as client:
        resp = await client.post(SEND_MESSAGE, json={
            "chat_id": chat_id,
            "text": f"🔎 Analyzing {pair}..."
        })
        result = resp.json()
        msg_id = result.get("result", {}).get("message_id")

    # Show typing action
    async with httpx.AsyncClient() as client:
        await client.post(SEND_CHAT_ACTION, json={"chat_id": chat_id, "action": "typing"})
    await asyncio.sleep(random.uniform(2, 4))

    # Send final signal by editing the same message if possible
    signal = random.choice(["🔺", "🔻"])
    if msg_id:
        await httpx.AsyncClient().post(EDIT_MESSAGE, json={
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": f"{signal} {pair}"
        })
    else:
        # Fallback to sending a new message
        await httpx.AsyncClient().post(SEND_MESSAGE, json={
            "chat_id": chat_id,
            "text": f"{signal} {pair}"
        })

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    # 1) Handle /start: send reply keyboard
    if data.get("message") and data["message"].get("text") == "/start":
        chat_id = data["message"]["chat"]["id"]
        keyboard = [[pair] for pair in otc_pairs]
        payload = {
            "chat_id": chat_id,
            "text": "Select an OTC pair:",
            "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
        }
        async with httpx.AsyncClient() as client:
            await client.post(SEND_MESSAGE, json=payload)
        return {"ok": True}

    # 2) Handle user selecting a pair via keyboard
    if data.get("message") and data["message"].get("text") in otc_pairs:
        chat_id = data["message"]["chat"]["id"]
        selected = data["message"]["text"]
        # simulate analysis with typing and editing placeholder
        asyncio.create_task(simulate_analysis(chat_id, selected))
        return {"ok": True}

    # 3) Fallback echo for other messages
    if data.get("message") and data["message"].get("text"):
        chat_id = data["message"]["chat"]["id"]
        text    = data["message"]["text"]
        async def send_reply():
            async with httpx.AsyncClient() as client:
                await client.post(SEND_MESSAGE, json={
                    "chat_id": chat_id,
                    "text": f"You said: {text}"
                })
        asyncio.create_task(send_reply())

    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
