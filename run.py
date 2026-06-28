"""
StockPilot - Uygulama Baslatici
Dev: pywebview masaustu | Prod: Flask/SocketIO sunucu
"""

import subprocess
import sys
import os
import threading
import time

# Konsolsuz modda hata log
if sys.stdout is None or hasattr(sys, '_MEIPASS'):
    try:
        exe_dir = os.path.dirname(sys.executable) if hasattr(sys, '_MEIPASS') else os.path.dirname(os.path.abspath(__file__))
        log_file = open(os.path.join(exe_dir, 'stockpilot_debug.log'), 'w', encoding='utf-8')
        sys.stdout = log_file
        sys.stderr = log_file
    except Exception:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

def main():
    # .env dosyasindan ortam degiskenlerini yukle
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
    
    is_packaged = hasattr(sys, '_MEIPASS')
    is_prod = os.environ.get('STOCKPILOT_PROD', '').lower() in ('1', 'true', 'yes')
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
    req_file = os.path.join(backend_dir, 'requirements.txt')

    print("=" * 60)
    print("  StockPilot - BIST Hisse Analiz Botu")
    print(f"  Mod: {'PROD (sunucu)' if is_prod else 'DEV (masaustu)'}")
    print("=" * 60)
    print()

    if not is_packaged and not is_prod:
        print("[*] Bagimliliklar yukleniyor...")
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', '-r', req_file, '-q'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print("[OK] Bagimliliklar basariyla yuklendi.")
        except subprocess.CalledProcessError as e:
            print(f"[HATA] Bagimlilik yukleme hatasi: {e}")
            sys.exit(1)
        print()

    print("[*] StockPilot baslatiliyor...")
    print()

    if is_packaged:
        sys.path.insert(0, os.path.join(sys._MEIPASS, 'backend'))
    else:
        sys.path.insert(0, backend_dir)

    from app import app, socketio
    from telegram_depth import start_telegram_listener

    # Telegram baslat
    start_telegram_listener()

    if is_prod:
        # === PROD: Flask + SocketIO (gunicorn uyumlu) ===
        socketio.run(app, debug=False, port=5000, host='0.0.0.0', allow_unsafe_werkzeug=True)
    else:
        # === DEV: pywebview masaustu ===
        def run_flask():
            socketio.run(app, debug=False, port=5000, host='127.0.0.1', allow_unsafe_werkzeug=True)
        threading.Thread(target=run_flask, daemon=True).start()
        time.sleep(1.0)

        import webview
        webview.create_window(
            "StockPilot — Borsa Istanbul Analiz Platformu",
            "http://localhost:5000",
            width=1280, height=800,
            resizable=True, min_size=(1024, 700)
        )
        webview.start(debug=True)


if __name__ == '__main__':
    main()
