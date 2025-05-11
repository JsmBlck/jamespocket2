from fastapi import FastAPI
from typing import Optional
import gspread
import json
import httpx
import asyncio
from oauth2client.service_account import ServiceAccountCredentials
import os

# Constants
RENDER_URL = "https://jamespocket2.onrender.com"
SPREADSHEET_NAME = "TelegramBotMembers"
WORKSHEET_NAME = "Sheet7"

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
    sumdep: Optional[str] = "",
    totaldep: Optional[str] = "0",
    reg: Optional[str] = "",
    dep: Optional[str] = ""
):
    print(f"📥 Incoming: trader_id={trader_id}, totaldep={totaldep}, sumdep={sumdep}, reg={reg}, dep={dep}")

    if not trader_id:
        return {"status": "error", "message": "❌ Missing trader_id"}

    # Convert totaldep safely
    try:
        deposit = float(totaldep or "0")
    except ValueError:
        deposit = 0.0

    try:
        # Check if trader already exists
        cell = sheet.find(str(trader_id))
        row = cell.row
        current_total = sheet.cell(row, 2).value or "0"
        updated_total = float(current_total) + deposit

        # Update trader info
        sheet.update_cell(row, 2, str(updated_total))  # Total Deposit
        sheet.update_cell(row, 3, reg)                 # Registration flag
        sheet.update_cell(row, 4, dep)                 # Deposit event
        sheet.update_cell(row, 5, sumdep)              # Latest deposit amount

        print(f"✅ Updated trader {trader_id}: totaldep={updated_total}, reg={reg}, dep={dep}, sumdep={sumdep}")
        return {
            "status": "updated",
            "trader_id": trader_id,
            "totaldep": updated_total,
            "reg": reg,
            "dep": dep,
            "sumdep": sumdep
        }

    except gspread.exceptions.GSpreadException as e:
        if "Cell not found" in str(e):
            # New trader — append new row
            sheet.append_row([trader_id, deposit, reg, dep, sumdep])
            print(f"🆕 Registered new trader {trader_id}")
            return {
                "status": "registered",
                "trader_id": trader_id,
                "totaldep": deposit,
                "reg": reg,
                "dep": dep,
                "sumdep": sumdep
            }
        else:
            print(f"❌ GSpread error: {e}")
            return {"status": "error", "message": str(e)}

    except Exception as e:
        print(f"❌ Error handling trader_id={trader_id}: {e}")
        return {"status": "error", "message": str(e)}
