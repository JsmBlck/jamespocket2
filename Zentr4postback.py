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
async def webhook(trader_id: Optional[str] = None, totaldep: Optional[float] = 0.0, reg: Optional[str] = None):
    print(f"📥 Raw request received with trader_id={trader_id}, totaldep={totaldep}, reg={reg}")

    # Ensure totaldep is set to 0 if not provided
    if totaldep is None or totaldep == "":
        totaldep = 0.0
    
    if not trader_id:
        return {"status": "error", "message": "Missing trader_id"}

    try:
        # Try to find trader_id in column A
        cell = sheet.find(str(trader_id))
        row = cell.row
        current_dep = sheet.cell(row, 2).value or "0"
        updated_dep = float(current_dep) + float(totaldep)
        sheet.update_cell(row, 2, str(updated_dep))
        print(f"✅ Updated trader {trader_id}: new total deposit = {updated_dep}")
        return {"status": "updated", "trader_id": trader_id, "totaldep": updated_dep}

    except Exception as e:
        # If not found or another error, treat it as new registration
        sheet.append_row([trader_id, totaldep])
        print(f"🆕 New trader {trader_id} registered with deposit = {totaldep}")
        return {"status": "registered", "trader_id": trader_id, "totaldep": totaldep}
