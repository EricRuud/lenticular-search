#!/bin/bash
set -e
pip install -r requirements.txt

# Build the database if it doesn't exist
if [ ! -f /opt/render/project/.cache/kalx/kalx.db ]; then
  echo "Building database..."
  python kalx.py build-db --days 30
  echo "Tagging top artists..."
  python kalx.py tag-artists --limit 200
  echo "Database build complete."
else
  echo "Database exists, updating last 3 days..."
  python kalx.py build-db --days 3
fi
