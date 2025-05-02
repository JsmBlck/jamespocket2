from flask import Flask, request
import requests
import os  # ← THIS was missing

app = Flask(__name__)
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'

@app.route('/webhook', methods=['POST'])
async def webhook():
    data = request.json
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')
        requests.post(TELEGRAM_API, json={"chat_id": chat_id, "text": f"You said: {text}"})
    return 'ok'

@app.route('/')
def home():
    return 'Bot running!'

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
