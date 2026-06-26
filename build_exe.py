import subprocess
import sys
import os

def install_pyinstaller():
    print("[*] PyInstaller kuruluyor/kontrol ediliyor...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])
        print("[OK] PyInstaller hazır.")
    except Exception as e:
        print(f"[HATA] PyInstaller kurulamadı: {e}")
        sys.exit(1)

def run_build():
    print("[*] Derleme işlemi başlatılıyor (bu işlem birkaç dakika sürebilir)...")
    
    # Path separators: PyInstaller uses semicolon (;) on Windows
    add_data_frontend = "frontend;frontend"
    add_data_db = "backend/stockpilot.db;backend"
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=StockPilot",
        "--onefile",
        "--clean",
        "--noconsole",
        "--paths", "backend",
        "--add-data", add_data_frontend,
        "--add-data", add_data_db,
        "--hidden-import=webview",
        "--hidden-import=flask",
        "--hidden-import=flask_cors",
        "--hidden-import=yfinance",
        "--hidden-import=pandas",
        "--hidden-import=numpy",
        "--hidden-import=vaderSentiment",
        "--hidden-import=requests",
        "--hidden-import=sqlite3",
        "--collect-all", "yfinance",
        "--collect-all", "pandas",
        "--collect-all", "vaderSentiment",
        "run.py"
    ]
    
    print(f"Çalıştırılan komut: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        print("\n" + "=" * 60)
        print("[OK] Derleme işlemi başarıyla tamamlandı!")
        print("[*] Tek başına çalışan exe dosyanız 'dist' klasörünün içindedir:")
        print(f"    Yol: {os.path.abspath('dist/StockPilot.exe')}")
        print("=" * 60 + "\n")
    except subprocess.CalledProcessError as e:
        print(f"[HATA] Derleme sırasında hata oluştu (Exit Code {e.returncode})")
        sys.exit(1)
    except Exception as e:
        print(f"[HATA] Beklenmeyen hata: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_pyinstaller()
    run_build()
