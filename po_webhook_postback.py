from fastapi import FastAPI, Request
from pydantic import BaseModel
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fastapi.concurrency import run_in_threadpool
import json
import os

app = FastAPI()

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", 
         "https://www.googleapis.com/auth/spreadsheets", 
         "https://www.googleapis.com/auth/drive"]

creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
spreadsheet = client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet7")

# Postback data model
class PostbackData(BaseModel):
    trader_id: int
    sumdep: float
    totaldep: float
    reg: int
    conf: int
    ftd: int
    dep: int

@app.post("/webhook")
async def handle_postback(data: PostbackData):
    print(f"Received data: {data}")

    row = [
        data.trader_id, 
        data.sumdep, 
        data.totaldep, 
        data.reg, 
        data.conf, 
        data.ftd, 
        data.dep
    ]

    try:
        await run_in_threadpool(sheet.append_row, row)
        return {"status": "success"}
    except Exception as e:
        print(f"Error saving to sheet: {e}")
        return {"status": "error", "detail": str(e)}
