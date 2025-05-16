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
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
gs_creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(gs_creds)
spreadsheet = gs_client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet7")

# Lifespan hook
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
            await asyncio.sleep(240)
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
            float(sumdep) if dep == "true" and sumdep else 0.0
        ]

        while len(row) < 7:
            row.append(None)

        if trader_id and trader_id != "false":
            cell = sheet.find(trader_id)
            if cell:
                row_number = cell.row
                existing_row = sheet.row_values(row_number)
                while len(existing_row) < 7:
                    existing_row.append("")

                current_sumdep = float(existing_row[1]) if existing_row[1] else 0.0
                current_totaldep = float(existing_row[2]) if existing_row[2] else 0.0
                current_reg = int(existing_row[3]) if existing_row[3] else 0
                current_conf = int(existing_row[4]) if existing_row[4] else 0
                current_ftd = int(existing_row[5]) if existing_row[5] else 0
                current_dep = float(existing_row[6]) if existing_row[6] else 0.0

                updated_sumdep = current_sumdep
                updated_totaldep = current_totaldep
                updated_reg = current_reg
                updated_conf = current_conf
                updated_ftd = current_ftd
                updated_dep = current_dep

                if reg == "true":
                    updated_reg = 1
                if conf == "true":
                    updated_conf = 1
                if ftd == "true":
                    updated_ftd = 1
                if dep == "true":
                    try:
                        new_dep = float(sumdep) if sumdep else 0.0
                        updated_sumdep += new_dep
                        updated_totaldep += new_dep
                        updated_dep = new_dep
                    except ValueError:
                        pass

                final_row = [
                    trader_id,
                    updated_sumdep,
                    updated_totaldep,
                    updated_reg,
                    updated_conf,
                    updated_ftd,
                    updated_dep
                ]

                sheet.update(f"A{row_number}:G{row_number}", [final_row])
                print(f"✅ Updated row {row_number} with selective values: {final_row}")
            else:
                sheet.append_row(row)
                print("✅ Appended to Google Sheet:", row)

    except Exception as e:
        print("❌ Error updating/appending to Google Sheet.")
        print("   ➤ Raw values:", trader_id, sumdep, totaldep, reg, conf, ftd, dep)
        print("   ➤ Exception:", e)

    return {"status": "success"}
