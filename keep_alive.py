import os
from flask import Flask, jsonify
from threading import Thread

app = Flask(__name__)

@app.get("/")
def root():
    # Render 기본 헬스체크 경로로 써도 되고, 외부 모니터에도 사용 가능
    return "CK Bot is alive!", 200

@app.get("/healthz")
def healthz():
    # Render 대시보드에서 Health Check Path를 /healthz 로 잡아도 OK
    return jsonify(status="ok"), 200

def _run():
    # Render는 PORT 환경변수를 내려주며, Free 환경 기본은 10000
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, threaded=True)

def keep_alive():
    Thread(target=_run, daemon=True).start()
