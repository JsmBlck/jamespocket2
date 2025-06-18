from fastapi import FastAPI
from typing import Optional
import gspread
import json
import httpx
import asyncio
from oauth2client.service_account import ServiceAccountCredentials
import os

# Constants
RENDER_URL = "https://jamespocket2-xce2.onrender.com"
SPREADSHEET_NAME = "TelegramBotMembers"
WORKSHEET_NAME = "Sheet12"

# Lifespan hook for keep-alive
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

# Initialize FastAPI app
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
    return {"message": "✅ ZentraFx Postback Webhook is live."}

@app.get("/webhook")
async def webhook(
    trader_id: Optional[str] = None,
    sumdep: Optional[str] = None,
    event: Optional[str] = "",
    ac: Optional[str] = None
):
    print(f"📥 Event={event} | Trader ID={trader_id} | SumDep={sumdep} | AC={ac}")

    if not trader_id:
        return {"status": "error", "message": "❌ Missing trader_id"}

    try:
        reported_amount = float(sumdep or 0)
        # Reverse 6% fee (to get original deposit)
        original_amount = round(reported_amount / 0.94)
    except ValueError:
        original_amount = 0

    trader_ids = sheet.col_values(1)  # Column A: trader_id

    try:
        if event == "registration":
            if trader_id not in trader_ids:
                sheet.append_row([trader_id, "0", ac or ""])
                print(f"🆕 Registered new trader {trader_id}")
                return {"status": "registered", "trader_id": trader_id}
            else:
                print(f"ℹ️ Trader {trader_id} already registered.")
                return {"status": "already_registered", "trader_id": trader_id}

        elif event in ["ftd", "redeposit"]:
            sheet.append_row([trader_id, str(original_amount), ac or ""])
            print(f"💰 Logged deposit: trader_id={trader_id}, amount={original_amount}, ac={ac}")
            return {
                "status": "logged",
                "trader_id": trader_id,
                "amount": original_amount
            }

        else:
            print("⚠️ Event ignored.")
            return {"status": "ignored", "event": event}

    except Exception as e:
        print(f"❌ Error processing {trader_id}: {e}")
        return {"status": "error", "message": str(e)}
