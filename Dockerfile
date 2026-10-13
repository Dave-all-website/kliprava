# Backend Kliprava — Docker deployment for Render, Railway, or a VPS
FROM python:3.12-slim

# Install ffmpeg & nodejs (wajib untuk JS challenge solver yt-dlp)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg nodejs curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install --with-deps chromium

COPY backend/ .

RUN mkdir -p /app/temp_media && chmod 777 /app/temp_media

EXPOSE 8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
