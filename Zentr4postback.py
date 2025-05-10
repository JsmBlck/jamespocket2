from fastapi import FastAPI
from typing import Optional
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
import os

app = FastAPI()

# Google Sheets Auth
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]

creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
gs_creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(gs_creds)
spreadsheet = gs_client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet7")

@app.get("/")
def root():
    return {"message": "ZentraFx Postback Webhook is live."}

@app.get("/webhook")
async def webhook(
    trader_id: Optional[str] = None,
    sumdep: Optional[str] = "",
    totaldep: Optional[str] = "0",
    reg: Optional[str] = "",
    dep: Optional[str] = ""
):
    print(f"📥 Received: trader_id={trader_id}, totaldep={totaldep}, sumdep={sumdep}, reg={reg}, dep={dep}")

    if not trader_id:
        return {"status": "error", "message": "Missing trader_id"}

    # Handle deposit value
    try:
        deposit = float(totaldep or "0")
    except ValueError:
        deposit = 0.0

    try:
        # Check if trader already exists
        cell = sheet.find(str(trader_id))
        row = cell.row
        current_dep = sheet.cell(row, 2).value or "0"
        updated_dep = float(current_dep) + deposit

        # Update all columns for existing trader
        sheet.update_cell(row, 2, str(updated_dep))  # Total Deposit
        sheet.update_cell(row, 3, reg)               # reg
        sheet.update_cell(row, 4, dep)               # dep
        sheet.update_cell(row, 5, sumdep)            # sumdep

        print(f"✅ Updated trader {trader_id}: totaldep={updated_dep}, reg={reg}, dep={dep}, sumdep={sumdep}")
        return {
            "status": "updated",
            "trader_id": trader_id,
            "totaldep": updated_dep,
            "reg": reg,
            "dep": dep,
            "sumdep": sumdep
        }

    except Exception:
        # Register new trader
        sheet.append_row([trader_id, deposit, reg, dep, sumdep])
        print(f"🆕 New trader {trader_id} registered: totaldep={deposit}, reg={reg}, dep={dep}, sumdep={sumdep}")
        return {
            "status": "registered",
            "trader_id": trader_id,
            "totaldep": deposit,
            "reg": reg,
            "dep": dep,
            "sumdep": sumdep
        }
