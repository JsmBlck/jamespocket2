import os
import httpx
import asyncio
import random
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEND_MESSAGE = f"{API_BASE}/sendMessage"
SEND_CHAT_ACTION = f"{API_BASE}/sendChatAction"
EDIT_MESSAGE = f"{API_BASE}/editMessageText"
RENDER_URL = "https://jamespocket2-k9lz.onrender.com"

# List of OTC pairs
otc_pairs = [
    "AED/CNY OTC", "AUD/CAD OTC", "BHD/CNY OTC",
    "EUR/USD OTC", "GBP/USD OTC", "NZD/USD OTC"
]
# Expiry options\expiry_options = ["30s", "1m", "5m", "15m"]

# Lifespan for self-ping
def create_self_ping(app: FastAPI):
    async def self_ping_loop():
        await asyncio.sleep(5)
        while True:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.get(RENDER_URL)
                print("✅ Self-ping successful!")
            except Exception as e:
                print(f"❌ Ping failed: {e}")
            await asyncio.sleep(300)
    return self_ping_loop

app = FastAPI(lifespan_factory=lambda app: (yield from (asyncio.create_task(create_self_ping(app)()), ())))

@app.api_route("/", methods=["GET","HEAD"])
async def healthcheck(request: Request):
    return {"status": "ok"}

async def simulate_analysis(chat_id: int, pair: str, expiry: str):
    # send placeholder
    async with httpx.AsyncClient() as client:
        resp = await client.post(SEND_MESSAGE, json={
            "chat_id": chat_id,
            "text": f"🔎 Analyzing {pair} for expiry {expiry}..."
        })
        msg_id = resp.json().get("result", {}).get("message_id")
    # typing
    async with httpx.AsyncClient() as client:
        await client.post(SEND_CHAT_ACTION, json={"chat_id": chat_id, "action": "typing"})
    await asyncio.sleep(random.uniform(2, 4))
    # final
    signal = random.choice(["🔺", "🔻"])
    text = f"{signal} {pair} expiring in {expiry}"
    if msg_id:
        await client.post(EDIT_MESSAGE, json={
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text
        })
    else:
        await client.post(SEND_MESSAGE, json={"chat_id": chat_id, "text": text})

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    # handle message text commands
    if msg := data.get("message"):
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        if text == "/start":
            # send inline keyboard of pairs
            keyboard = [[{"text": pair, "callback_data": f"pair|{pair}"}] for pair in otc_pairs]
            await httpx.AsyncClient().post(SEND_MESSAGE, json={
                "chat_id": chat_id,
                "text": "Select an OTC pair:",
                "reply_markup": {"inline_keyboard": keyboard}
            })
            return {"ok": True}
    # handle callback_query
    if cq := data.get("callback_query"):
        data_str = cq.get("data", "")
        chat_id = cq["message"]["chat"]["id"]
        cq_id = cq.get("id")
        # acknowledge
        await httpx.AsyncClient().post(f"{API_BASE}/answerCallbackQuery", json={"callback_query_id": cq_id})
        action, value = data_str.split("|", 1)
        if action == "pair":
            # user picked pair, now show expiry options
            keyboard = [[{"text": exp, "callback_data": f"expiry|{value}|{exp}"}] for exp in expiry_options]
            await httpx.AsyncClient().post(SEND_MESSAGE, json={
                "chat_id": chat_id,
                "text": f"Pair {value} selected. Choose expiry:",
                "reply_markup": {"inline_keyboard": keyboard}
            })
            return {"ok": True}
        if action == "expiry":
            # value contains pair, next token is expiry
            _, pair, expiry = data_str.split("|", 2)
            asyncio.create_task(simulate_analysis(chat_id, pair, expiry))
            return {"ok": True}
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
