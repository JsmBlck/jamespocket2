import asyncio
import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# Define the URL to keep alive
RENDER_URL = "https://jamespocket2.onrender.com"

# Set up Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
gs_creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(gs_creds)
spreadsheet = gs_client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet7")

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
                print(f"❌ Ping failed: {e}")
            await asyncio.sleep(300)
    asyncio.create_task(self_ping_loop())
    yield
    await ping_client.aclose()

app = FastAPI(lifespan=lifespan)

# Health check endpoint for self-ping
@app.api_route("/", methods=["GET", "HEAD"])
async def healthcheck(request: Request):
    return {"status": "ok"}

# Webhook route for GET requests from Pocket Option
@app.get("/webhook")
async def handle_get_webhook(
    trader_id: int,
    sumdep: float,
    totaldep: float,
    reg: int,
    conf: int,
    ftd: int,
    dep: float
):
    print(f"✅ Received: trader_id={trader_id}, sumdep={sumdep}, totaldep={totaldep}, reg={reg}, conf={conf}, ftd={ftd}, dep={dep}")
    
    # Append to Google Sheet
    row = [trader_id, sumdep, totaldep, reg, conf, ftd, dep]
    sheet.append_row(row)

    return {"status": "success"}
