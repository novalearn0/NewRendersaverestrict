# bot.py — Render single-service version (free plan compatible)
# ================================================
import os
import sys
import time
import threading
import traceback
from flask import Flask
from pyrogram import Client

# --- Fix import path ---
project_root = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Local imports ---
from config import API_ID, API_HASH, BOT_TOKEN, STRING_SESSION, LOGIN_SYSTEM

# --- Logging helper ---
def _log(msg: str):
    print(f"[bot] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}", flush=True)

# --- Flask health check server ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive and running on Render!"

def run_flask():
    """Run Flask server in a background thread (for Render uptime checks)."""
    port = int(os.environ.get("PORT", 10000))
    _log(f"Starting Flask health server on port {port}...")
    # 👇 FIXED LINE — ensure proper port binding
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)

# --- Optional user session (if login system disabled) ---
user_client = None
try:
    if STRING_SESSION and (LOGIN_SYSTEM is False or str(LOGIN_SYSTEM).lower() in ("false", "0", "no")):
        user_client = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)
        _log("User client created (not started yet).")
except Exception as e:
    _log(f"Failed to create user client: {e}")

# --- Bot client ---
class Bot(Client):
    def __init__(self):
        super().__init__(
            "main_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="plugins"),
            workers=100,
            sleep_threshold=5
        )

    async def start(self):
        await super().start()
        _log("✅ Bot started successfully.")
        try:
            _log(f"Loaded {len(self.plugins)} plugin modules.")
        except Exception:
            pass

    async def stop(self, *args):
        try:
            await super().stop()
            _log("🛑 Bot stopped cleanly.")
        except Exception as e:
            _log(f"Error during stop: {e}\n{traceback.format_exc()}")

# --- Main entry ---
if __name__ == "__main__":
    # Start Flask in a background thread
    threading.Thread(target=run_flask, daemon=True).start()

    try:
        bot = Bot()
        import signal
        def handle_shutdown(signum, frame):
            _log(f"Received signal {signum}, stopping bot...")
            try:
                bot.stop()
            except Exception as ee:
                _log(f"Error during shutdown: {ee}")
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)
        bot.run()
    except Exception as e:
        _log(f"Fatal error running bot: {e}\n{traceback.format_exc()}")
