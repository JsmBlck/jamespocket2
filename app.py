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
DELETE_MESSAGE = f"{API_BASE}/deleteMessage"
RENDER_URL = "https://jamespocket2-k9lz.onrender.com"

client = None  # Global httpx client

otc_pairs = [
    "🇦🇪🇨🇳 AED/CNY OTC", "🇦🇺🇨🇦 AUD/CAD OTC", "🇧🇭🇨🇳 BHD/CNY OTC",
    "🇪🇺🇺🇸 EUR/USD OTC", "🇬🇧🇺🇸 GBP/USD OTC", "🇳🇿🇺🇸 NZD/USD OTC"
]

expiry_options = ["5s", "10s", "15s", "30s"]

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

import random
import asyncio
import httpx

import random
import asyncio
import httpx

async def simulate_analysis(chat_id: int, pair: str, expiry: str):
    # Analysis steps (loading animation included)
    analysis_steps = [
        f"{pair} 🔎 Analyzing.",
        f"{pair} 🔎 Analyzing..",
        f"{pair} 📊 Gathering data.",
        f"{pair} 📊 Gathering data..",
        f"{pair} 📈 Calculating signal.",
        f"{pair} 📈 Calculating signal.."
    ]

    # Responses for final signal
    RESPONSES = [
        "🟢 **Up {pair}** \n\n🤖 Possible uptrend forming.\n\n📈 Market showing strength.",
        "🔴 **Down {pair}** \n\n🤖 Possible downtrend forming.\n\n📉 Market losing momentum.",
        "🟢 **Up Signal {pair}** \n\n🤖 Upward movement detected.\n\n💰 Trend gaining strength.",
        "🔴 **Down Signal {pair}** \n\n🤖 Downward movement detected.\n\n📉 Weakness in the market.",
        "🟢 **Up {pair}** \n\n🤖 Price holding strong.\n\n🛑 Momentum shifting upwards.",
        "🔴 **Down {pair}** \n\n🤖 Resistance spotted.\n\n📉 Market struggling to push higher.",
        "🟢 **Up Setup {pair}** \n\n🤖 Favorable conditions detected.\n\n💹 Trend leaning upwards.",
        "🔴 **Down Setup {pair}** \n\n🤖 Signs of weakness appearing.\n\n📉 Trend leaning downwards.",
        "🟢 **Up Confirmed {pair}** \n\n🤖 Trend sustaining upwards.\n\n📈 Positive movement expected.",
        "🔴 **Down Confirmed {pair}** \n\n🤖 Trend weakening further.\n\n📉 Market slowing down."
    ]

    # Send the initial analysis message
    message_id = None
    async with httpx.AsyncClient() as client:
        resp = await client.post(SEND_MESSAGE, json={"chat_id": chat_id, "text": analysis_steps[0]})
        message_id = resp.json().get("result", {}).get("message_id")

    # Show each analysis step with a short delay
    for step in analysis_steps[1:]:
        await asyncio.sleep(0.07)  # Delay for animation effect
        async with httpx.AsyncClient() as client:
            await client.post(EDIT_MESSAGE, json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": step
            })

    # Simulate the final signal (separate signal step)
    await asyncio.sleep(random.uniform(0.5, 1.5))  # Delay before showing final signal
    signal = random.choice(["↗️", "↘️"])  # Choose up or down signal

    # Send the signal first (without final message)
    async with httpx.AsyncClient() as client:
        await client.post(EDIT_MESSAGE, json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": f"{signal}"
        })

    # Filter appropriate responses based on the signal
    if signal == "↗️":
        possible_msgs = [msg for msg in RESPONSES if "🟢" in msg]
    else:
        possible_msgs = [msg for msg in RESPONSES if "🔴" in msg]

    # Select a random response
    final_message = random.choice(possible_msgs).format(pair=pair)

    # Send the final signal response separately
    async with httpx.AsyncClient() as client:
        await client.post(SEND_MESSAGE, json={
            "chat_id": chat_id,
            "text": final_message,
            "parse_mode": "Markdown"
        })

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    if msg := data.get("message"):
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]

        if text == "/start":
            keyboard = [otc_pairs[i:i+2] for i in range(0, len(otc_pairs), 2)]
            payload = {
                "chat_id": chat_id,
                "text": "Select an OTC pair:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            await client.post(SEND_MESSAGE, json=payload)
            return {"ok": True}

        if text in otc_pairs:
            inline_kb = [
                [{"text": expiry_options[i], "callback_data": f"expiry|{text}|{expiry_options[i]}"},
                 {"text": expiry_options[i+1], "callback_data": f"expiry|{text}|{expiry_options[i+1]}"}]
                for i in range(0, len(expiry_options), 2)
            ]
            payload = {
                "chat_id": chat_id,
                "text": f"{text} selected. Choose Time:",
                "reply_markup": {"inline_keyboard": inline_kb}
            }
            await client.post(SEND_MESSAGE, json=payload)
            return {"ok": True}

        asyncio.create_task(client.post(SEND_MESSAGE, json={"chat_id": chat_id, "text": f"You said: {text}"}))
        return {"ok": True}

    if cq := data.get("callback_query"):
        data_str = cq.get("data", "")
        chat_id = cq["message"]["chat"]["id"]
        message_id = cq["message"]["message_id"]
        cq_id = cq.get("id")

        await client.post(f"{API_BASE}/answerCallbackQuery", json={"callback_query_id": cq_id})
        await client.post(DELETE_MESSAGE, json={"chat_id": chat_id, "message_id": message_id})

        _, pair, expiry = data_str.split("|", 2)
        asyncio.create_task(simulate_analysis(chat_id, pair, expiry))
        return {"ok": True}

    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
