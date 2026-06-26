#!/bin/sh
# StockPilot Railway Start Script
cd /app
pip install -r requirements.txt
PYTHONPATH=/app/backend gunicorn backend.app:app --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120
