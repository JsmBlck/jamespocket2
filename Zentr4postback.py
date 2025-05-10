import asyncio
import httpx
from fastapi import FastAPI, Request
from typing import Optional
import gspread
from gspread import CellNotFound
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

RENDER_URL = "https://jamespocket2.onrender.com"

# Setup Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
gs_creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(gs_creds)
spreadsheet = gs_client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet7")

# Lifespan hook for Render self-ping
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
async def handle_webhook(
    trader_id: Optional[str] = None,
    totaldep: Optional[str] = None,
    reg: Optional[str] = None,
    request: Request = None
):
    print(f"📥 Raw request: {request.url}")
    print(f"   ➤ trader_id: {trader_id}")
    print(f"   ➤ totaldep: {totaldep}")
    print(f"   ➤ reg: {reg}")

    try:
        # Clean and convert inputs
        clean_trader_id = str(trader_id).strip() if trader_id and trader_id != "false" else None
        new_deposit = float(totaldep) if totaldep and totaldep != "false" else 0.0
        is_reg = reg == "true"

        if not clean_trader_id:
            return {"status": "error", "message": "Missing trader_id"}

        try:
            cell = sheet.find(clean_trader_id)
            row_number = cell.row
            existing_row = sheet.row_values(row_number)

            # Ensure existing row has at least 3 columns
            while len(existing_row) < 3:
                existing_row.append("")

            existing_totaldep = float(existing_row[1]) if existing_row[1] else 0.0
            existing_reg = int(existing_row[2]) if existing_row[2] else 0

            updated_totaldep = existing_totaldep + new_deposit
            updated_reg = 1 if is_reg else existing_reg

            updated_row = [clean_trader_id, updated_totaldep, updated_reg]
            sheet.update(f"A{row_number}:C{row_number}", [updated_row])
            print(f"✅ Updated row {row_number}: {updated_row}")

        except CellNotFound:
            # New trader ID
            row = [
                clean_trader_id,
                new_deposit,
                1 if is_reg else 0
            ]
            sheet.append_row(row)
            print("✅ Appended new user:", row)

        return {"status": "success"}

    except Exception as e:
        print("❌ Error during webhook processing.")
        print("   ➤ trader_id:", trader_id)
        print("   ➤ totaldep:", totaldep)
        print("   ➤ reg:", reg)
        print("   ➤ Exception:", e)
        return {"status": "error", "message": str(e)}
