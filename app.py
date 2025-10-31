from flask import Flask
import threading, os, runpy, signal, time, sys

app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is alive'

def run_bot():
    # Prefer running bot.py directly as user requested start command python3 bot.py
    try:
        runpy.run_path('bot.py', run_name='__main__')
    except Exception as e:
        print('Failed to run bot.py via runpy:', e, file=sys.stderr)

if __name__ == '__main__':
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()

    def _shutdown(signum, frame):
        print('Signal received, shutting down...')
        try:
            import bot as b
            if hasattr(b, 'stop'):
                b.stop()
        except Exception:
            pass
        time.sleep(1)
        os._exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
