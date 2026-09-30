#!/bin/sh
set -eu

# The inference service is private to this container. Gunicorn is deliberately
# the foreground process so Hugging Face can supervise the public application.
uvicorn postal_ocr.service:app --host 127.0.0.1 --port 8001 &
exec gunicorn config.wsgi:application \
  --chdir /app/back \
  --bind "0.0.0.0:${PORT:-7860}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-60}"
