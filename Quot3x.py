from fastapi import FastAPI
from typing import Optional
import gspread
import json
import httpx
import asyncio
from oauth2client.service_account import ServiceAccountCredentials
import os

# Constants
RENDER_URL = "https://jamespocket2-c99h.onrender.com"
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
async def quotex_webhook(
    status: Optional[str] = None,
    uid: Optional[str] = None,
    payout: Optional[str] = "0"
):
    print(f"📥 Quotex Incoming: status={status}, uid={uid}, payout={payout}")

    if not uid or not status:
        return {"status": "error", "message": "Missing required params"}

    try:
        deposit = float(payout or "0")
    except ValueError:
        deposit = 0.0

    # Use a different worksheet for Quotex
    quotex_sheet = spreadsheet.worksheet("Quotex")

    try:
        cell = quotex_sheet.find(str(uid))

        if cell is None:
            raise ValueError("User not found")

        row = cell.row
        current_total = quotex_sheet.cell(row, 2).value or "0"
        updated_total = float(current_total) + deposit

        quotex_sheet.update_cell(row, 2, str(updated_total))

        print(f"✅ Updated Quotex user {uid}: total={updated_total}")
        return {
            "status": "updated",
            "user_id": uid,
            "total": updated_total
        }

    except (ValueError, gspread.exceptions.GSpreadException):
        quotex_sheet.append_row([uid, deposit])
        print(f"🆕 Registered new Quotex user {uid}")
        return {
            "status": "registered",
            "user_id": uid,
            "total": deposit
        }

    except Exception as e:
        print(f"❌ Quotex error: {e}")
        return {"status": "error", "message": str(e)}
