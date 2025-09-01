import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return "성CK 디스코드 봇이 작동 중입니다! (health ok)"

def _run():
    port = int(os.getenv("PORT", "8080"))  # ← 환경변수 PORT 우선 사용
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=_run, daemon=True)
    t.start()
