FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The inference API is reachable only from the Docker network on port 8001.
CMD ["uvicorn", "postal_ocr.service:app", "--host", "0.0.0.0", "--port", "8001"]
