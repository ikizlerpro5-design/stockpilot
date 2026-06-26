"""
StockPilot - Uygulama Baslatici
Bagimlilikları yukler ve Flask sunucusunu baslatir.
"""

import subprocess
import sys
import os

# Konsolsuz (Windowed) modda çökmesini önlemek ve hataları yakalamak için log dosyası oluşturalım
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
    is_packaged = hasattr(sys, '_MEIPASS')
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
    req_file = os.path.join(backend_dir, 'requirements.txt')

    # Bagimlilikları yukle
    print("=" * 60)
    print("  StockPilot - BIST Hisse Analiz Botu")
    print("=" * 60)
    print()

    if not is_packaged:
        print("[*] Bagimliliklar yukleniyor...")
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', '-r', req_file, '-q'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("[OK] Bagimliliklar basariyla yuklendi.")
        except subprocess.CalledProcessError as e:
            print(f"[HATA] Bagimlilik yukleme hatasi: {e}")
            print("   Manuel olarak deneyin: pip install -r backend/requirements.txt")
            sys.exit(1)
        print()

    print("[*] StockPilot baslatiliyor...")
    print()

    # Backend klasorunu Python path'ine ekle ve uygulamayi baslat
    if is_packaged:
        sys.path.insert(0, os.path.join(sys._MEIPASS, 'backend'))
    else:
        sys.path.insert(0, backend_dir)

    import threading
    import time
    import webview
    
    from app import app

    # Flask sunucusunu arka planda çalıştıralım
    def run_flask():
        app.run(debug=False, port=5000, host='127.0.0.1', use_reloader=False)

    threading.Thread(target=run_flask, daemon=True).start()
    
    # Sunucunun boot edilmesi için 1 saniye bekleyelim
    time.sleep(1.0)

    # Yerel masaüstü penceresini başlatalım
    webview.create_window(
        "StockPilot — Borsa İstanbul Analiz Platformu",
        "http://localhost:5000",
        width=1280,
        height=800,
        resizable=True,
        min_size=(1024, 700)
    )
    webview.start(debug=True)


if __name__ == '__main__':
    main()
