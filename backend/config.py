import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General & App Settings
    APP_NAME: str = "Kliprava Converter Service"
    DEBUG: bool = False
    TEMP_DIR: str = Field(default="./temp_media", description="Path lokal folder temporary")

    # Task Queue & Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="URL Redis untuk Celery Broker & Backend")

    # Cloud Storage S3 / Cloudflare R2 Settings
    S3_ENDPOINT_URL: Optional[str] = Field(default=None, description="Endpoint S3 (misal: https://<account_id>.r2.cloudflarestorage.com untuk R2)")
    S3_ACCESS_KEY: Optional[str] = Field(default=None, description="Access Key ID S3/R2")
    S3_SECRET_KEY: Optional[str] = Field(default=None, description="Secret Access Key S3/R2")
    S3_BUCKET_NAME: str = Field(default="media-converter-bucket", description="Nama Bucket S3/R2")
    S3_REGION: str = Field(default="us-east-1", description="Region S3/R2")
    PRESIGNED_EXPIRATION: int = Field(default=3600, description="Masa berlaku Presigned URL (detik)")

    # Proxy & Anti-Bot Engine
    PROXIES: List[str] = Field(default_factory=list, description="Daftar proxy (HTTP/SOCKS5) untuk rotasi")
    PLAYWRIGHT_HEADLESS: bool = Field(default=True, description="Jalankan Playwright dalam mode Headless")
    PLAYWRIGHT_TIMEOUT: int = Field(default=30000, description="Timeout Playwright dalam milidetik")

    # Media Conversion Limits
    MAX_VIDEO_HEIGHT: int = Field(default=1080, description="Batas maksimal resolusi video height (0 untuk tanpa batas)")


settings = Settings()

# Pastikan folder temp lokal selalu tersedia
os.makedirs(settings.TEMP_DIR, exist_ok=True)
