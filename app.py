import os
import httpx
import asyncio
import random
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks
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
    "AED/CNY OTC", "AUD/CAD OTC", "BHD/CNY OTC", "EUR/USD OTC", "GBP/USD OTC", "AUD/NZD OTC",
    "NZD/USD OTC", "EUR/JPY OTC", "CAD/JPY OTC", "AUD/USD OTC",  "AUD/CHF OTC", "GBP/AUD OTC"
]
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

async def simulate_analysis(chat_id: int, pair: str, expiry: str):
    analysis_steps = [
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n🔎 Analyzing.",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n🔎 Analyzing..",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n🔎 Analyzing...",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n🔎 Analyzing....",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📊 Gathering data.",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📊 Gathering data..",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📊 Gathering data...",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📊 Gathering data....",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📈 Calculating signal.",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📈 Calculating signal..",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📈 Calculating signal...",
        f"🤖 {pair} ☑️\n\n⌛ Time: {expiry}\n\n📈 Calculating signal....",
        f"🤖 {pair} ✅\n\n⌛ Time: {expiry}\n\n📊 Analysis complete."
    ]

    # Send the first analysis message and get the message_id directly
    resp = await client.post(SEND_MESSAGE, json={"chat_id": chat_id, "text": analysis_steps[0]})
    message_id = resp.json().get("result", {}).get("message_id")

    # Show each analysis step with a minimal delay
    for step in analysis_steps[1:]:
        await client.post(EDIT_MESSAGE, json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": step
        })
    # Simulate final signal
    await asyncio.sleep(0.3)  # Reduced delay
    signal = random.choice(["↗️", "↘️"])
    final_text = f"{signal}"
    await client.post(EDIT_MESSAGE, json={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": final_text
    })

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    if msg := data.get("message"):
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        if text == "/start":
            keyboard = [otc_pairs[i:i+3] for i in range(0, len(otc_pairs), 3)]
            payload = {
                "chat_id": chat_id,
                "text": "Select an OTC pair:",
                "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        if text in otc_pairs:
            inline_kb = [[{"text": expiry_options[i], "callback_data": f"expiry|{text}|{expiry_options[i]}"} 
                for i in range(row, row + 3)]
                for row in range(0, len(expiry_options), 3)]
            payload = {
                "chat_id": chat_id,
                "text": f"🤖 {text} ☑️\n\n⌛ Select Time:",
                "reply_markup": {"inline_keyboard": inline_kb}
            }
            background_tasks.add_task(client.post, SEND_MESSAGE, json=payload)
            return {"ok": True}
        background_tasks.add_task(client.post, SEND_MESSAGE, json={"chat_id": chat_id, "text": f"You said: {text}"})
        return {"ok": True}
    if cq := data.get("callback_query"):
        data_str = cq.get("data", "")
        chat_id = cq["message"]["chat"]["id"]
        message_id = cq["message"]["message_id"]
        cq_id = cq.get("id")
        background_tasks.add_task(client.post, f"{API_BASE}/answerCallbackQuery", json={"callback_query_id": cq_id})
        background_tasks.add_task(client.post, DELETE_MESSAGE, json={"chat_id": chat_id, "message_id": message_id})
        _, pair, expiry = data_str.split("|", 2)
        # Start analysis in the background
        background_tasks.add_task(simulate_analysis, chat_id, pair, expiry)
        return {"ok": True}
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
