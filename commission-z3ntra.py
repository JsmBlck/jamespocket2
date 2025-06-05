from fastapi import FastAPI
from typing import Optional
import gspread
import json
import httpx
import asyncio
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime

# Constants
RENDER_URL = "https://z3ntra-postback.onrender.com"
SPREADSHEET_NAME = "TelegramBotMembers"
WORKSHEET_NAME = "Sheet12"

# Lifespan hook for self-ping
async def lifespan(app: FastAPI):
    ping_client = httpx.AsyncClient(timeout=10)

    async def self_ping_loop():
        await asyncio.sleep(5)
        while True:
            try:
                await ping_client.get(RENDER_URL)
                print("✅ Self-ping successful!")
            except Exception as e:
                print(f"❌ Self-ping failed: {e}")
            await asyncio.sleep(300)

    asyncio.create_task(self_ping_loop())
    yield
    await ping_client.aclose()

app = FastAPI(lifespan=lifespan)

# Google Sheets setup
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
gs_creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(gs_creds)
sheet = gs_client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)

@app.get("/")
def root():
    return {"message": "✅ ZentraFx Commission Postback is live."}

@app.get("/postback")
async def postback(
    event: Optional[str] = None,
    commission: Optional[str] = "0",
    date_time: Optional[str] = None
):
    if event != "commission":
        return {"status": "ignored", "reason": "event not commission"}

    try:
        commission_value = float(commission)
    except ValueError:
        commission_value = 0.0

    timestamp = date_time or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Append commission and date to sheet
    sheet.append_row([timestamp, commission_value])
    print(f"✅ Logged: {timestamp} | ${commission_value}")

    return {"status": "logged", "date": timestamp, "commission": commission_value}
