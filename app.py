from flask import Flask, request
import requests

app = Flask(__name__)
BOT_TOKEN = '7825687335:AAEYhy1h9hujIGqBuS_fAmFYbywRRKoDlGE'
URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        message = data['message'].get('text', '')
        reply = f"You said: {message}"
        requests.post(URL, json={"chat_id": chat_id, "text": reply})
    return 'ok'

@app.route('/')
def home():
    return 'Bot is running!'

