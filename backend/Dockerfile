# Backend Kliprava — Docker deployment dengan build context backend/
FROM node:24-bookworm-slim AS js-runtime
FROM brainicism/bgutil-ytdlp-pot-provider:2.0.2@sha256:d7d34108b76e52c7d3b575fe9e797e4bf41c1b2a08f80c5292eff6f851ce8472 AS youtube-pot
FROM python:3.12-slim-bookworm

COPY --from=js-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=youtube-pot /app /opt/youtube-pot
ENV YOUTUBE_POT_SERVER_HOME=/opt/youtube-pot
RUN node /opt/youtube-pot/build/generate_once.js --version

# ffmpeg & nodejs wajib ada untuk memotong video & menyelesaikan JS challenge yt-dlp
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
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
