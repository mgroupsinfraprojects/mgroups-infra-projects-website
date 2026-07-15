#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m pip install --user -r requirements.txt
export MGROUPS_HOST=${MGROUPS_HOST:-0.0.0.0}
export MGROUPS_PORT=${MGROUPS_PORT:-5000}
export MGROUPS_DEBUG=${MGROUPS_DEBUG:-0}
while true; do
  python3 app.py
  code=$?
  if [ "$code" = "3" ]; then
    echo "App restart requested after backup restore. Restarting..."
    sleep 2
    continue
  fi
  exit "$code"
done
