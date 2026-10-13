import os
import logging
from typing import Optional
import boto3
from botocore.client import Config
from config import settings

logger = logging.getLogger(__name__)


class StorageManager:
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.region = settings.S3_REGION
        self.s3_client = None

        if self.access_key and self.secret_key:
            try:
                # Setup Boto3 S3 Client (Kompatibel dengan AWS S3 & Cloudflare R2)
                client_kwargs = {
                    "service_name": "s3",
                    "aws_access_key_id": self.access_key,
                    "aws_secret_access_key": self.secret_key,
                    "region_name": self.region,
                    "config": Config(
                        signature_version="s3v4",
                        s3={"addressing_style": "virtual" if not self.endpoint_url else "path"}
                    )
                }
                if self.endpoint_url:
                    client_kwargs["endpoint_url"] = self.endpoint_url

                self.s3_client = boto3.client(**client_kwargs)
                logger.info("S3 / Cloudflare R2 Storage Client berhasil diinisialisasi.")
            except Exception as e:
                logger.error(f"Gagal menginisialisasi S3 client: {e}")
        else:
            logger.warning("Kredensial S3_ACCESS_KEY / S3_SECRET_KEY tidak ditemukan. Storage akan berjalan dalam mode fallback lokal.")

    def is_configured(self) -> bool:
        return self.s3_client is not None

    def upload_file(self, local_filepath: str, object_key: str, content_type: Optional[str] = None) -> bool:
        """Unggah file lokal ke S3/R2 bucket."""
        if not self.is_configured():
            logger.warning("Storage S3 belum terkonfigurasi. Melewati proses upload S3.")
            return False

        if not os.path.exists(local_filepath):
            raise FileNotFoundError(f"File lokal tidak ditemukan: {local_filepath}")

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            logger.info(f"Mengunggah {local_filepath} ke bucket '{self.bucket_name}' key '{object_key}'...")
            self.s3_client.upload_file(
                Filename=local_filepath,
                Bucket=self.bucket_name,
                Key=object_key,
                ExtraArgs=extra_args if extra_args else None
            )
            logger.info(f"Upload berhasil: {object_key}")
            return True
        except Exception as e:
            logger.error(f"Error saat mengunggah file ke S3: {e}")
            raise Exception(f"Gagal mengunggah file ke S3/R2 storage: {str(e)}")

    def generate_presigned_url(self, object_key: str, expiration: Optional[int] = None) -> str:
        """Buat Presigned Download URL sementara dengan waktu kadaluarsa."""
        if not self.is_configured():
            raise RuntimeError("Storage S3/R2 belum dikonfigurasi untuk unduhan hasil antrean.")

        exp = expiration or settings.PRESIGNED_EXPIRATION
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": object_key
                },
                ExpiresIn=exp
            )
            return url
        except Exception as e:
            logger.error(f"Error pembuatan Presigned URL: {e}")
            raise Exception(f"Gagal meng-generate presigned URL: {str(e)}")


storage_manager = StorageManager()
