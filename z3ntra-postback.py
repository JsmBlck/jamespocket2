from fastapi import FastAPI
from typing import Optional
import gspread
import json
import httpx
import asyncio
from oauth2client.service_account import ServiceAccountCredentials
import os

# Constants
RENDER_URL = "https://z3ntra-postback.onrender.com"
SPREADSHEET_NAME = "TelegramBotMembers"
WORKSHEET_NAME = "Sheet9"

# Lifespan hook for self-ping (keep-alive)
async def lifespan(app: FastAPI):
    ping_client = httpx.AsyncClient(timeout=10)

    async def self_ping_loop():
        await asyncio.sleep(5)  # initial delay
        while True:
            try:
                await ping_client.get(RENDER_URL)
                print("✅ Self-ping successful!")
            except Exception as e:
                print(f"❌ Self-ping failed: {e}")
            await asyncio.sleep(300)  # every 5 minutes

    asyncio.create_task(self_ping_loop())
    yield
    await ping_client.aclose()

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Google Sheets authorization
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
gs_creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(gs_creds)
spreadsheet = gs_client.open(SPREADSHEET_NAME)
sheet = spreadsheet.worksheet(WORKSHEET_NAME)

@app.get("/")
def root():
    return {"message": "✅ ZentraFx Postback Webhook is live."}

@app.get("/webhook")
async def webhook(
    trader_id: Optional[str] = None,
    totaldep: Optional[str] = "0",
    reg: Optional[str] = "",
    sumdep: Optional[str] = "",
    dep: Optional[str] = "",
    ftd: Optional[str] = ""
):
    print(f"📥 Incoming: trader_id={trader_id}, totaldep={totaldep}")

    if not trader_id:
        return {"status": "error", "message": "❌ Missing trader_id"}

    try:
        deposit = float(totaldep or "0")
    except ValueError:
        deposit = 0.0

    try:
        # Try to find the trader ID in the sheet
        cell = sheet.find(str(trader_id))

        if cell is None:
            raise ValueError("Trader not found")

        row = cell.row
        # Overwrite with latest totaldep (do not add)
        sheet.update_cell(row, 2, str(deposit))

        print(f"✅ Updated trader {trader_id}: totaldep={deposit}")
        return {
            "status": "updated",
            "trader_id": trader_id,
            "totaldep": deposit
        }

    except (ValueError, gspread.exceptions.GSpreadException):
        # Trader not found — register new
        sheet.append_row([trader_id, deposit])
        print(f"🆕 Registered new trader {trader_id}")
        return {
            "status": "registered",
            "trader_id": trader_id,
            "totaldep": deposit
        }

    except Exception as e:
        print(f"❌ Error handling trader_id={trader_id}: {e}")
        return {"status": "error", "message": str(e)}
