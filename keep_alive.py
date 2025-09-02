import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return "CK Bot is alive!"

def _run():
    port = int(os.getenv("PORT", "8080"))  # Render에서 PORT 환경변수로 포트 지정
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=_run, daemon=True).start()
