from fastapi import FastAPI, Request
from typing import Optional
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

app = FastAPI()

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
gs_creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(gs_creds)
spreadsheet = gs_client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet7")

@app.get("/")
def root():
    return {"message": "ZentraFx Postback Webhook is live."}

@app.get("/webhook")
async def webhook(trader_id: Optional[str] = None, totaldep: Optional[str] = "0", reg: Optional[str] = None):
    print(f"📥 Raw request received with trader_id={trader_id}, totaldep={totaldep}, reg={reg}")

    if not trader_id:
        return {"status": "error", "message": "Missing trader_id"}

    try:
        dep_amount = float(totaldep or "0")
    except ValueError:
        dep_amount = 0.0

    try:
        cell = sheet.find(str(trader_id))
        row = cell.row
        current_dep = sheet.cell(row, 2).value or "0"
        updated_dep = float(current_dep) + dep_amount
        sheet.update_cell(row, 2, str(updated_dep))
        print(f"✅ Updated trader {trader_id}: new total deposit = {updated_dep}")
        return {"status": "updated", "trader_id": trader_id, "totaldep": updated_dep}

    except Exception as e:
        sheet.append_row([trader_id, dep_amount])
        print(f"🆕 New trader {trader_id} registered with deposit = {dep_amount}")
        return {"status": "registered", "trader_id": trader_id, "totaldep": dep_amount}
