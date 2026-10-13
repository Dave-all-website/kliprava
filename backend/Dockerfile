# Backend Kliprava — Docker deployment dengan build context backend/
FROM python:3.12-slim

# ffmpeg & nodejs wajib ada untuk memotong video & menyelesaikan JS challenge yt-dlp
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg nodejs curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install --with-deps chromium

COPY . .

# Penyimpanan sementara hasil konversi
RUN mkdir -p /app/temp_media && chmod 777 /app/temp_media

# Host dapat mengatur PORT; default container adalah 8080.
EXPOSE 8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
