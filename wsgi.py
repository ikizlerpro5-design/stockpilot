"""
StockPilot - WSGI Entry Point (Web Deployment)
Render / Railway / Fly.io icin gunicorn ile calistirilir.
Kullanim: gunicorn wsgi:app
"""
import os
import sys

# Backend yolunu ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import app

# Production ayarlari
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
