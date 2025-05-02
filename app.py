import os
import httpx
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()  # Load environment variables from .env if present

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

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

    # immediately acknowledge to Telegram
    return {"ok": True}

@app.api_route("/", methods=["GET", "HEAD"])
async def healthcheck(request: Request):
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
