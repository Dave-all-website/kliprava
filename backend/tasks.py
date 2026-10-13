import os
import uuid
import logging
from typing import Dict, Any

from celery_app import celery_app
from config import settings
from scraper import extract_media_info
from converter import download_media_sources, convert_media, extract_metadata, safe_remove
from storage import storage_manager

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def process_media_task(self, job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Celery Pipeline:
    1. Scrape Direct Media URL & Metadata
    2. Download Raw Media Stream ke Disk Lokal
    3. Re-encode / Transcode via FFmpeg (MP3 320kbps atau MP4)
    4. Upload Hasil ke Cloudflare R2 / AWS S3 Storage
    5. Generate Presigned Download URL
    6. Pembersihan safe_remove file lokal otomatis di block finally
    """
    url = payload.get("url")
    output_format = (payload.get("format") or "mp4").lower().strip()
    resolution = payload.get("resolution") or "best"
    start_time = float(payload.get("start_time") or 0.0)
    end_time = float(payload.get("end_time") or 0.0)

    raw_file = os.path.join(settings.TEMP_DIR, f"{job_id}_raw.tmp")
    audio_file = os.path.join(settings.TEMP_DIR, f"{job_id}_audio.tmp")
    final_file = os.path.join(settings.TEMP_DIR, f"{job_id}_final.{output_format}")
    s3_key = f"conversions/{job_id}.{output_format}"

    logger.info(f"[Task {job_id}] Mengawali pemrosesan URL: {url} (Format: {output_format})")

    try:
        if not storage_manager.is_configured():
            raise RuntimeError("Antrean konversi membutuhkan storage S3/R2.")
        # STEP 1: Scraping Raw URL
        self.update_state(state="PROCESSING", meta={"progress": 10, "step": "Ekstraksi URL & Metadata"})
        media_info = extract_media_info(url)
        direct_url = media_info.get("direct_url")
        stream_headers = media_info.get("stream_headers")
        title = media_info.get("title", "Media Download")
        thumbnail = media_info.get("thumbnail")

        if not direct_url:
            raise Exception("Gagal mengekstrak URL stream langsung dari media sasaran.")

        # STEP 2: Unduh Stream Mentah ke Lokal
        self.update_state(state="PROCESSING", meta={"progress": 35, "step": "Mengunduh Stream Mentah"})
        separate_audio = download_media_sources(
            media_info, raw_file, audio_file, media_info.get("canonical_url") or url, resolution, output_format
        )

        # STEP 3: Transcoding & Pemotongan FFmpeg
        self.update_state(state="PROCESSING", meta={"progress": 65, "step": f"Mengonversi Media ke {output_format.upper()}"})
        convert_media(
            input_path=raw_file,
            output_path=final_file,
            output_format=output_format,
            start_time=start_time,
            end_time=end_time,
            resolution=resolution,
            audio_path=separate_audio
        )

        # Extrak metadata teknis hasil konversi
        tech_meta = extract_metadata(final_file)

        # STEP 4: Upload ke Cloud Storage (S3 / R2)
        self.update_state(state="PROCESSING", meta={"progress": 85, "step": "Mengunggah ke Cloud Storage"})
        content_type = "audio/mpeg" if output_format == "mp3" else "video/mp4"

        is_uploaded = storage_manager.upload_file(final_file, s3_key, content_type=content_type)
        
        # STEP 5: Generate Presigned URL
        self.update_state(state="PROCESSING", meta={"progress": 95, "step": "Membuat Presigned Download URL"})
        download_url = storage_manager.generate_presigned_url(s3_key)

        logger.info(f"[Task {job_id}] Selesai diproses dengan sukses!")

        return {
            "job_id": job_id,
            "status": "SUCCESS",
            "download_url": download_url,
            "filename": f"{title[:40]}.{output_format}",
            "format": output_format,
            "metadata": {
                "title": title,
                "thumbnail": thumbnail,
                "duration": tech_meta.get("duration", media_info.get("duration", 0)),
                "size_bytes": tech_meta.get("size_bytes", 0),
                "is_remote_storage": is_uploaded
            }
        }

    except Exception as exc:
        logger.error(f"[Task {job_id}] Terjadi kegagalan: {exc}")
        # Lakukan Retry untuk error sementara
        if self.request.retries < self.max_retries and any(err in str(exc).lower() for err in ("timeout", "connection", "503", "429")):
            logger.info(f"[Task {job_id}] Melakukan retry ke-{self.request.retries + 1}...")
            raise self.retry(exc=exc)

        return {
            "job_id": job_id,
            "status": "FAILURE",
            "error": str(exc)
        }

    finally:
        # STEP 6: Automatic Pembersihan File Lokal
        safe_remove(raw_file)
        safe_remove(audio_file)
        safe_remove(final_file)
        logger.info(f"[Task {job_id}] Pembersihan file temporary lokal selesai.")
