#!/bin/bash
set -e

# Start the web server immediately, backfill data in background
python backfill.py &
exec gunicorn web:app --bind 0.0.0.0:$PORT --workers 2 --timeout 600
