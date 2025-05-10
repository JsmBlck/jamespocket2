import asyncio
import httpx
from fastapi import FastAPI, Request
from typing import Optional
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

RENDER_URL = "https://jamespocket2.onrender.com"

# Setup Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
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

@app.get("/")
async def healthcheck():
    return {"status": "ok"}

@app.get("/webhook")
async def handle_get_webhook(
    trader_id: Optional[str] = None,
    totaldep: Optional[str] = None,
    reg: Optional[str] = None,
    request: Request = None
):
    print(f"📥 Raw request: {request.url}")

    try:
        if not trader_id or trader_id == "false":
            raise ValueError("Invalid or missing trader_id")

        clean_trader_id = trader_id.strip()
        clean_totaldep = float(totaldep) if totaldep and totaldep != "false" else 0.0
        clean_reg = 1 if reg == "true" else 0

        row = [clean_trader_id, clean_totaldep, clean_reg]

        try:
            cell = sheet.find(clean_trader_id)
            row_number = cell.row
            sheet.update(f"A{row_number}:C{row_number}", [row])
            print(f"✅ Updated row {row_number}: {row}")
        except gspread.exceptions.CellNotFound:
            sheet.append_row(row)
            print("✅ Appended to Google Sheet:", row)

    except Exception as e:
        print("❌ Error during webhook processing.")
        print("   ➤ trader_id:", trader_id)
        print("   ➤ totaldep:", totaldep)
        print("   ➤ reg:", reg)
        print("   ➤ Exception:", e)

    return {"status": "success"}
