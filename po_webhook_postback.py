from fastapi import FastAPI, Request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# Set up FastAPI app
app = FastAPI()

# Google Sheets authentication
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Access the sheet
spreadsheet = client.open("TelegramBotMembers")
sheet = spreadsheet.worksheet("Sheet7")

@app.get("/webhook")
async def handle_postback(request: Request):
    # Extract query parameters from the request
    params = request.query_params

    # Prepare the data for the sheet
    row = [
        params.get("trader_id"),
        params.get("sumdep"),
        params.get("totaldep"),
        params.get("reg"),
        params.get("conf"),
        params.get("ftd"),
        params.get("dep"),
    ]
    
    # Print the received data for debugging
    print(f"Received data: {row}")
    
    # Append the data to the next row in the sheet
    sheet.append_row(row)

    return {"status": "success"}
