
import os
import requests
from flask import Flask, request, redirect, session, render_template_string

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET"]

TOKEN = os.environ["BOT_TOKEN"]
PASSWORD = os.environ["ADMIN_PASSWORD"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

chats = {}
active_chat = None

def telegram(method, data):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    return requests.post(url, json=data, timeout=20).json()

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return "Unauthorized", 401

    update = request.get_json(silent=True) or {}
    msg = update.get("message", {})
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    text = msg.get("text")

    if chat_id and text:
        chats.setdefault(str(chat_id), []).append({
            "who": "Pessoa",
            "text": text
        })
    return "OK"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PASSWORD:
            session["logged"] = True
            return redirect("/")
        return "Senha incorreta"
    return """
    <h2>Painel privado</h2>
    <form method="post">
    <input name="password" type="password" placeholder="Senha">
    <button>Entrar</button>
    </form>
    """

@app.route("/")
def home():
    if not session.get("logged"):
        return redirect("/login")

    global active_chat

    options = "".join(
        f'<option value="{cid}" {"selected" if cid == active_chat else ""}>{cid}</option>'
        for cid in chats
    )

    messages = ""
    if active_chat and active_chat in chats:
        for m in chats[active_chat]:
            messages += f'<p><b>{m["who"]}:</b> {m["text"]}</p>'

    return render_template_string("""
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="8">
    <h2>Meu painel Telegram</h2>
    <form action="/select" method="post">
      <select name="chat_id">{{ options|safe }}</select>
      <button>Selecionar conversa</button>
    </form>
    <hr>
    <div>{{ messages|safe }}</div>
    <form action="/send" method="post">
      <input name="text" placeholder="Digite sua mensagem" required>
      <button>Enviar</button>
    </form>
    <p><a href="/logout">Sair</a></p>
    """, options=options, messages=messages)

@app.route("/select", methods=["POST"])
def select():
    if not session.get("logged"):
        return redirect("/login")
    global active_chat
    active_chat = request.form.get("chat_id")
    return redirect("/")

@app.route("/send", methods=["POST"])
def send():
    if not session.get("logged"):
        return redirect("/login")
    if not active_chat:
        return "Selecione uma conversa primeiro."
    text = request.form.get("text", "").strip()
    if text:
        result = telegram("sendMessage", {
            "chat_id": active_chat,
            "text": text
        })
        if result.get("ok"):
            chats[active_chat].append({"who": "Você", "text": text})
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/health")
def health():
    return "OK"

if os.environ.get("PUBLIC_URL"):
    telegram("setWebhook", {
        "url": os.environ["PUBLIC_URL"].rstrip("/") + "/webhook",
        "secret_token": WEBHOOK_SECRET
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
