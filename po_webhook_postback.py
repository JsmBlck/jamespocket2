import asyncio
import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# Set up FastAPI app
app = FastAPI()

# Define the URL to keep alive
RENDER_URL = "https://jamespocket2.onrender.com/webhook?trader_id=123456&sumdep=0&totaldep=25&reg=1&conf=1&ftd=1&dep=25"  # Replace with your actual Render URL

# Set up Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
spreadsheet = client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet7")

# Postback data model
class PostbackData(BaseModel):
    trader_id: int
    sumdep: float
    totaldep: float
    reg: int
    conf: int
    ftd: int
    dep: int

# Self-ping function to keep the service alive
async def lifespan(app: FastAPI):
    global client
    client = httpx.AsyncClient(timeout=10)

    async def self_ping_loop():
        await asyncio.sleep(5)  # Wait for initial startup time
        while True:
            try:
                await client.get(RENDER_URL)
                print("✅ Self-ping successful!")
            except Exception as e:
                print(f"❌ Ping failed: {e}")
            await asyncio.sleep(300)  # Ping every 5 minutes

    asyncio.create_task(self_ping_loop())
    yield
    await client.aclose()  # Clean up when shutdown

app = FastAPI(lifespan=lifespan)

# Webhook route for GET requests with query parameters
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
