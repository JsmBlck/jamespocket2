import asyncio
import httpx
from fastapi import FastAPI, Request
from typing import Optional
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# Define the URL to keep alive
RENDER_URL = "https://po-affiliate-webhook.onrender.com"

# Setup Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
gs_creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(gs_creds)
spreadsheet = gs_client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet7")

# Lifespan hook to self-ping
async def lifespan(app: FastAPI):
    ping_client = httpx.AsyncClient(timeout=10)
    async def self_ping_loop():
        await asyncio.sleep(5)
        while True:
            try:
                await ping_client.get(RENDER_URL)
                print("✅ Self-ping successful!")
            except Exception as e:
                print(f"❌ Ping failed: {e}")
            await asyncio.sleep(300)
    asyncio.create_task(self_ping_loop())
    yield
    await ping_client.aclose()

app = FastAPI(lifespan=lifespan)

# Health check
@app.get("/")
async def healthcheck():
    return {"status": "ok"}

# Webhook route (now accepting all as strings)
@app.get("/webhook")
async def handle_get_webhook(
    trader_id: Optional[str] = None,
    sumdep: Optional[str] = None,
    totaldep: Optional[str] = None,
    reg: Optional[str] = None,
    conf: Optional[str] = None,
    ftd: Optional[str] = None,
    dep: Optional[str] = None,
    request: Request = None
):
    print(f"📥 Raw request: {request.url}")

    try:
        row = [
            int(trader_id) if trader_id and trader_id != "false" else None,
            float(sumdep) if sumdep and sumdep != "false" else None,
            float(totaldep) if totaldep and totaldep != "false" else None,
            int(reg == "true") if reg else 0,
            int(conf == "true") if conf else 0,
            int(ftd == "true") if ftd else 0,
            float(dep) if dep and dep != "false" else None
        ]
        sheet.append_row(row)
        print("✅ Appended to Google Sheet:", row)
    except Exception as e:
        print(f"❌ Error parsing or appending: {e}")

    return {"status": "success"}
