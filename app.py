import os
import httpx
import asyncio
import random
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

load_dotenv()

BOT_TOKEN    = os.getenv("TELEGRAM_TOKEN")
API_BASE     = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEND_MESSAGE = f"{API_BASE}/sendMessage"
ANSWER_CB    = f"{API_BASE}/answerCallbackQuery"
RENDER_URL   = "https://jamespocket2-k9lz.onrender.com"

otc_pairs = [
    "AED/CNY OTC", 
    "AUD/CAD OTC",   
    "BHD/CNY OTC",  
    "EUR/USD OTC",
    "GBP/USD OTC",
    "NZD/USD OTC"
]

# --- Self-ping lifespan (unchanged) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
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
    asyncio.create_task(self_ping_loop())
    yield

app = FastAPI(lifespan=lifespan)

@app.api_route("/", methods=["GET", "HEAD"])
async def healthcheck():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    # 1) Handle /start: send inline keyboard
    if data.get("message") and data["message"].get("text") == "/start":
        chat_id = data["message"]["chat"]["id"]
        # build inline keyboard
        keyboard = [
            [{"text": pair, "callback_data": pair}]
            for pair in otc_pairs
        ]
        payload = {
            "chat_id": chat_id,
            "text": "Select an OTC pair:",
            "reply_markup": {"inline_keyboard": keyboard}
        }
        async with httpx.AsyncClient() as client:
            await client.post(SEND_MESSAGE, json=payload)
        return {"ok": True}

    # 2) Handle button clicks (callback_query)
    if data.get("callback_query"):
        cq   = data["callback_query"]
        pair = cq["data"]
        cq_id = cq["id"]
        chat_id = cq["message"]["chat"]["id"]

        # 2a) Acknowledge the button press so the loading spinner goes away
        async with httpx.AsyncClient() as client:
            await client.post(ANSWER_CB, json={"callback_query_id": cq_id})

        # 2b) Send random up/down emoji
        signal = random.choice(["🔺", "🔻"])
        await httpx.AsyncClient().post(SEND_MESSAGE, json={
            "chat_id": chat_id,
            "text": f"{signal} {pair}"
        })
        return {"ok": True}

    # 3) Fallback echo for other messages (optional)
    if data.get("message") and data["message"].get("text"):
        chat_id = data["message"]["chat"]["id"]
        text    = data["message"]["text"]
        # fire-and-forget reply
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
