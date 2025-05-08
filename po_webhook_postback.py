from fastapi import FastAPI, Request
from pydantic import BaseModel
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# Set up FastAPI app
app = FastAPI()

# Google Sheets credentials and initialization
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name('path_to_your_credentials.json', SCOPE)
client = gspread.authorize(CREDS)
sheet = client.open("Your_Google_Sheet_Name").sheet1  # Change to your actual sheet name

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
    # Print the received data for debugging
    print(f"Received data: {data}")

    # Save the data to Google Sheets
    row = [
        data.trader_id, 
        data.sumdep, 
        data.totaldep, 
        data.reg, 
        data.conf, 
        data.ftd, 
        data.dep
    ]
    
    # Append the data to the next row in the sheet
    sheet.append_row(row)

    return {"status": "success"}
