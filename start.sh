#!/bin/bash
set -e

# Build/update DB at startup (persistent disk is available here)
if [ ! -f /opt/render/project/.cache/kalx/kalx.db ]; then
  echo "First run — building database (30 days)..."
  python kalx.py build-db --days 30
  echo "Tagging top artists..."
  python kalx.py tag-artists --limit 200
  echo "Done."
else
  echo "Updating database (last 3 days)..."
  python kalx.py build-db --days 3
fi

exec gunicorn web:app --bind 0.0.0.0:$PORT --workers 2 --timeout 600
