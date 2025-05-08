from fastapi import FastAPI, Request
from pydantic import BaseModel
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

app = FastAPI()

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Load credentials from environment variable
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Open your Google Sheet and specific worksheet
spreadsheet = client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet7")

# Define expected fields from postback
class PostbackData(BaseModel):
    trader_id: int
    sumdep: float
    totaldep: float
    reg: int
    conf: int
    ftd: int
    dep: int

@app.post("/webhook")
async def receive_postback(data: PostbackData):
    print(f"Received data: {data}")
    row = [
        data.trader_id, data.sumdep, data.totaldep,
        data.reg, data.conf, data.ftd, data.dep
    ]
    sheet.append_row(row)
    return {"status": "success"}

@app.get("/")
def home():
    return {"status": "ok"}

