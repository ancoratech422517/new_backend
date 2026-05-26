import os
import hmac
import hashlib
import time
import requests
import traceback
from flask import Blueprint, request, jsonify
from models.database import Carteira_Digital_Depositar, db
from flask_cors import cross_origin

Depositar_Dinheiro = Blueprint("Depositar_Dinheiro", __name__)

# --- Função de verificação de segurança (HMAC) ---
def verifyLinkPagaWebhook(raw_body, header_signature, header_timestamp, secret):
    try:
        ts = int(header_timestamp)
        if abs(time.time() - ts) > 300: # 5 minutos de tolerância
            return False
    except (ValueError, TypeError):
        return False

    if not header_signature or 'v1=' not in header_signature:
        return False

    parts = dict(part.split('=') for part in header_signature.split(','))
    provided_signature = parts.get('v1')

    message = f"{header_timestamp}.{raw_body}".encode('utf-8')
    secret_bytes = secret.encode('utf-8')

    expected_signature = hmac.new(
        secret_bytes, 
        message, 
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, provided_signature)

# --- Rota para iniciar o pedido de cobrança ---
@Depositar_Dinheiro.route("/depositar_pinheiro", methods=["POST", "OPTIONS"])
@cross_origin(origins=["https://ancora-ecommerce.vercel.app", "http://127.0.0.1:5173"], supports_credentials=True)
def DepositarDinheiro():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({"status": "erro", "message": "Nenhum dado recebido"}), 400

        numero_conta = dados.get("numero_conta")
        valor = dados.get("valor_sacar_conta")
        id_usuario = dados.get("id_usuario")

        if not all([numero_conta, valor, id_usuario]):
            return jsonify({"status": "erro", "message": "Campos incompletos"}), 400

        # Integração com a API da LinkPaga
        url = "https://gbzazmhfsrwyecxazadm.supabase.co/functions/v1/api-v1/payment-links"
        headers = {
            "Authorization": f"Bearer {os.getenv('LINKPAGA_KEY')}:{os.getenv('LINKPAGA_SECRET')}",
            "Content-Type": "application/json"
        }
        payload = {
            "valor": valor,
            "referencia": str(id_usuario),
            "descricao": "Depósito via Multicaixa Express"
        }

        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            # Salvar pendência no banco
            novo_deposito = Carteira_Digital_Depositar(
                numero_conta=numero_conta, 
                valor_sacar_conta=valor, 
                id_usuario=id_usuario,
                status="pendente"
            )
            db.session.add(novo_deposito)
            db.session.commit()
            
            return jsonify({"status": "sucesso", "message": "Pedido de pagamento enviado"}), 200
        
        return jsonify({"status": "erro", "message": "Falha na API LinkPaga"}), response.status_code

    except Exception as erro:
        traceback.print_exc()
        return jsonify({"status": "erro", "message": str(erro)}), 500

# --- Rota para o Webhook (Confirmação automática) ---
@Depositar_Dinheiro.route("/linkpaga-webhook", methods=["POST"])
def webhook():
    raw_body = request.data.decode('utf-8')
    sig = request.headers.get("X-LinkPaga-Signature")
    ts = request.headers.get("X-LinkPaga-Timestamp")
    secret = os.getenv('WEBHOOK_SECRET')

    if not verifyLinkPagaWebhook(raw_body, sig, ts, secret):
        return "Invalid signature", 401

    evento = request.json
    if evento["evento"] == "payment.succeeded":
        # Lógica de sucesso: Atualizar saldo do usuário no banco aqui
        print(f"Pagamento aprovado para usuário: {evento['data']['referencia']}")
        
    return "ok", 200
