"""
StockPilot - WSGI Entry Point (Web Deployment)
Railway / Render icin gunicorn ile calistirilir.
"""
import os
import sys

# Backend yolunu PYTHONPATH'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from app import app as application

# gunicorn bunu arar
app = application

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
