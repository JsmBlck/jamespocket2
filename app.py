import os
import httpx
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

load_dotenv()  # Load environment variables from .env if present

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
RENDER_URL = "https://jamespocket2-k9lz.onrender.com"

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

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    if 'message' in data and 'text' in data['message']:
        chat_id = data['message']['chat']['id']
        text = data['message']['text']

        async def send_reply():
            async with httpx.AsyncClient() as client:
                await client.post(TELEGRAM_API, json={
                    "chat_id": chat_id,
                    "text": f"You said: {text}"
                })

        # fire-and-forget reply
        asyncio.create_task(send_reply())

    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
