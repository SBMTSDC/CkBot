import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return "CK Bot is alive!"

def _run():
    port = int(os.getenv("PORT", "8080"))  # Render가 지정해주는 PORT 우선
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=_run, daemon=True).start()
