#!/bin/bash
# ============================================
#  StockPilot — VDS Deployment Script
#  Ubuntu 22.04+ / Debian 12+
# ============================================
set -e

echo "========================================"
echo "  StockPilot VDS Kurulum"
echo "========================================"

# --- 1. Sistem Paketleri ---
echo "[1/6] Sistem paketleri kuruluyor..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv tesseract-ocr nginx

# --- 2. Proje Dizini ---
APP_DIR=/opt/stockpilot
echo "[2/6] Proje dizini: $APP_DIR"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Dosyalari kopyala (bu script'in oldugu yerden)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ "$SCRIPT_DIR" != "$APP_DIR" ]; then
    cp -r "$SCRIPT_DIR"/* "$APP_DIR/"
fi
cd $APP_DIR

# --- 3. Python Sanal Ortam ---
echo "[3/6] Python venv kuruluyor..."
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt
pip install -q gunicorn

# --- 4. .env Dosyasi ---
if [ ! -f .env ]; then
    echo "[4/6] .env dosyasi olusturuluyor..."
    cp .env.example .env
    echo "!!! Lutfen .env dosyasini duzenleyin: nano .env"
    echo "!!! TG_API_ID ve TG_API_HASH zorunlu!"
fi

# --- 5. Telegram Session ---
if [ ! -f stockpilot_session.session ]; then
    echo "[5/6] Telegram session dosyasi bulunamadi!"
    echo "     Windows'tan stockpilot_session.session dosyasini"
    echo "     $APP_DIR/ altina kopyalayin."
    echo "     Veya sunucuda: python setup_telegram.py"
fi

# --- 6. Systemd Servisi ---
echo "[6/6] Systemd servisi kuruluyor..."
sudo tee /etc/systemd/system/stockpilot.service > /dev/null << 'SERVICE'
[Unit]
Description=StockPilot BIST Analysis Platform
After=network.target

[Service]
Type=simple
User=USER_PLACEHOLDER
WorkingDirectory=/opt/stockpilot
Environment="STOCKPILOT_PROD=1"
EnvironmentFile=/opt/stockpilot/.env
ExecStart=/opt/stockpilot/venv/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

sudo sed -i "s/USER_PLACEHOLDER/$USER/" /etc/systemd/system/stockpilot.service
sudo systemctl daemon-reload
sudo systemctl enable stockpilot

# --- Nginx ---
sudo tee /etc/nginx/sites-available/stockpilot > /dev/null << 'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/stockpilot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo ""
echo "========================================"
echo "  KURULUM TAMAMLANDI!"
echo "========================================"
echo ""
echo "  Baslatmak icin:"
echo "    sudo systemctl start stockpilot"
echo ""
echo "  Durum kontrol:"
echo "    sudo systemctl status stockpilot"
echo ""
echo "  Loglar:"
echo "    journalctl -u stockpilot -f"
echo ""
echo "  O N E M L I:"
echo "  1. .env dosyasini duzenleyin: nano /opt/stockpilot/.env"
echo "  2. Session dosyasini kopyalayin"
echo "  3. sudo systemctl start stockpilot"
echo ""
