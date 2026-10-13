import os
import re
import time
import uuid
import logging
import shutil
from collections import OrderedDict
from typing import Optional, Dict, Any, Literal
from urllib.parse import urlsplit

import urllib3
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response, JSONResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field, model_validator
from celery.result import AsyncResult

from config import settings
from celery_app import celery_app
from storage import storage_manager
from scraper import extract_media_info, clean_url, DESKTOP_UA, MOBILE_UA
from converter import convert_media, download_media_sources, safe_remove
from network import open_public_stream, UnsafeURL

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("api.main")

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description="Production-grade Media Downloader & Converter Service API"
)

# CORS Middleware (Allow All for Web UI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Content-Length", "Accept-Ranges", "Content-Disposition"],
)


# ---------------------------------------------------------------------------
# Header Cache untuk Stream Video Preview Proxy (7 Platform Sosmed)
# ---------------------------------------------------------------------------
_STREAM_HEADERS: "OrderedDict[str, dict]" = OrderedDict()
_STREAM_HEADERS_MAX = 256


def _clean_url_key(url: str) -> str:
    if not url:
        return ""
    return url.strip()


def _remember_stream_headers(url: str, headers: dict):
    if not url or not headers:
        return
    key = _clean_url_key(url)
    _STREAM_HEADERS[key] = {k: v for k, v in headers.items() if k.lower() != "range"}
    _STREAM_HEADERS.move_to_end(key)
    while len(_STREAM_HEADERS) > _STREAM_HEADERS_MAX:
        _STREAM_HEADERS.popitem(last=False)


def _get_stream_headers(url: str) -> dict:
    return dict(_STREAM_HEADERS.get(_clean_url_key(url), {}))


def _fallback_headers_for(url: str) -> dict:
    low = (url or "").lower()
    host = (urlsplit(url).hostname or "").lower()

    if any(s in host or s in low for s in ("douyin", "iesdouyin", "bytecdn", "zjcdn")):
        return {"User-Agent": MOBILE_UA, "Referer": "https://www.douyin.com/", "Accept": "*/*"}
    if "tikwm" in host or "tikwm" in low:
        return {"User-Agent": DESKTOP_UA, "Referer": "https://www.tikwm.com/", "Accept": "*/*"}
    if any(s in host or s in low for s in ("tiktok", "ttwstatic", "byteoversea", "tiktokcdn")):
        return {"User-Agent": DESKTOP_UA, "Accept": "*/*"}
    if any(s in host or s in low for s in ("xhscdn", "xiaohongshu", "rednote", "xhslink", "sns-video")):
        return {"User-Agent": MOBILE_UA, "Referer": "https://www.xiaohongshu.com/", "Accept": "*/*"}
    if any(s in host or s in low for s in ("cdninstagram", "instagram.com", "instagr.am", "fbcdn", "facebook.com", "fb.watch")):
        return {"User-Agent": DESKTOP_UA, "Referer": "https://www.instagram.com/", "Accept": "*/*", "Sec-Fetch-Mode": "cors"}
    if any(s in host or s in low for s in ("googlevideo.com", "youtube.com", "youtu.be", "ytimg")):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Mode": "navigate"
        }
    if any(s in host or s in low for s in ("twimg.com", "twitter.com", "x.com", "t.co")):
        return {"User-Agent": DESKTOP_UA, "Referer": "https://x.com/", "Accept": "*/*"}
    return {"User-Agent": DESKTOP_UA, "Accept": "*/*"}


# ---------------------------------------------------------------------------
# PYDANTIC REQUEST / RESPONSE SCHEMAS
# ---------------------------------------------------------------------------

class URLRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)


class ProcessRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)
    start_time: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    end_time: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    format: Literal["mp4", "mp3"] = "mp4"
    resolution: str = Field(default="best", pattern=r"^(best|[1-9][0-9]{1,3})$")

    @model_validator(mode="after")
    def valid_range(self):
        if self.end_time and self.end_time <= self.start_time:
            raise ValueError("Waktu selesai harus lebih besar dari waktu mulai.")
        return self


class JobAcceptedResponse(BaseModel):
    job_id: str
    status: str = "PENDING"
    message: str


class StatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[int] = 0
    step: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# FRONTEND INTERACTIVE ENDPOINTS (/api/info, /api/stream, /api/process)
# ---------------------------------------------------------------------------

@app.post("/api/info")
@app.post("/info")
def get_media_info(request: URLRequest):
    """Ekstraksi metadata & direct streaming URL untuk Preview di Frontend."""
    try:
        url = clean_url(request.url)
        info = extract_media_info(url)
        
        # Tambahkan quality ladder standar jika belum ada
        if not info.get("qualities"):
            info["qualities"] = [
                {"label": "1080p Full HD", "height": 1080},
                {"label": "720p HD", "height": 720},
                {"label": "480p SD", "height": 480},
                {"label": "360p SD", "height": 360},
            ]

        # Simpan header stream ke cache preview proxy
        if info.get("direct_url") and info.get("stream_headers"):
            _remember_stream_headers(info["direct_url"], info["stream_headers"])

        if info.get("audio_url"):
            _remember_stream_headers(info["audio_url"], info.get("audio_headers") or info.get("stream_headers") or {})
        public_info = {k: v for k, v in info.items() if k not in ("_formats", "stream_headers", "audio_headers")}
        return {"status": "success", "data": public_info}
    except Exception as e:
        logger.error(f"Error di /api/info: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/stream")
@app.get("/stream")
def stream_video_proxy(url: str, request: Request, vid: Optional[str] = None):
    """Proxy public CDN media without trusting client-supplied hosts or redirects."""
    response = pool = None
    try:
        req_url = url.strip()
        headers = dict(_get_stream_headers(req_url) or _fallback_headers_for(req_url))
        headers.pop("Range", None)
        range_header = request.headers.get("range")
        if range_header:
            headers["Range"] = range_header
        attempts = [headers, _fallback_headers_for(req_url), {"User-Agent": DESKTOP_UA, "Accept": "*/*"}]
        for candidate in attempts:
            candidate = dict(candidate)
            if range_header:
                candidate["Range"] = range_header
            response, pool = open_public_stream(req_url, candidate)
            if response.status not in (400, 401, 403):
                break
            response.close()
            pool.close()
        upstream_status = response.status
        resp_headers = {
            k: v for k, v in response.headers.items()
            if k.lower() in ("content-type", "content-range", "accept-ranges", "etag", "last-modified")
        }
        if upstream_status == 416:
            response.close()
            pool.close()
            return Response(status_code=416, headers=resp_headers)
        if upstream_status not in (200, 206):
            raise HTTPException(status_code=502, detail=f"CDN server status: {upstream_status}")
        if upstream_status == 206 and not response.headers.get("Content-Range"):
            raise HTTPException(status_code=502, detail="CDN mengirim partial content tanpa Content-Range.")
        content_type = response.headers.get("Content-Type", "").lower()
        if any(kind in content_type for kind in ("text/", "application/json")):
            raise HTTPException(status_code=502, detail="CDN tidak mengembalikan media.")

        def close_stream():
            response.close()
            pool.close()

        def generate():
            try:
                yield from response.stream(amt=128 * 1024, decode_content=True)
            finally:
                close_stream()

        # Preserve the actual upstream status/range. Never fabricate a 206 response.
        return StreamingResponse(generate(), status_code=upstream_status, headers=resp_headers,
                                 background=BackgroundTask(close_stream))
    except Exception as exc:
        if response is not None:
            response.close()
        if pool is not None:
            pool.close()
        if isinstance(exc, HTTPException):
            raise
        if isinstance(exc, UnsafeURL):
            raise HTTPException(status_code=400, detail=str(exc))
        logger.warning("Preview stream failed: %s", exc)
        raise HTTPException(status_code=502, detail="Gagal menghubungi server media.")


@app.post("/api/process")
@app.post("/process")
def process_and_download_sync(req: ProcessRequest):
    """Proses konversi & potong media secara instan untuk diunduh langsung oleh browser."""
    file_id = str(uuid.uuid4())
    ext = req.format.lower().strip() if req.format.lower().strip() in ("mp4", "mp3") else "mp4"
    raw_path = os.path.join(settings.TEMP_DIR, f"{file_id}_raw.tmp")
    final_path = os.path.join(settings.TEMP_DIR, f"{file_id}_final.{ext}")
    audio_path = os.path.join(settings.TEMP_DIR, f"{file_id}_audio.tmp")

    try:
        # Ekstrak link stream mentah
        target_url = clean_url(req.url)
        info = extract_media_info(target_url)
        direct_url = info.get("direct_url")
        if not direct_url:
            raise Exception("URL stream langsung tidak dapat ditemukan.")

        # Unduh stream mentah dengan fallback URL kanonikal
        separate_audio = download_media_sources(
            info, raw_path, audio_path, target_url, req.resolution, ext
        )

        # Konversi menggunakan FFmpeg
        convert_media(
            input_path=raw_path,
            output_path=final_path,
            output_format=ext,
            start_time=req.start_time,
            end_time=req.end_time,
            resolution=req.resolution,
            audio_path=separate_audio
        )

        safe_remove(raw_path)
        safe_remove(audio_path)

        download_filename = f"Kliprava_{int(time.time())}.{ext}"
        is_youtube = any(s in target_url.lower() for s in ("youtube.com", "youtu.be"))
        if is_youtube and info.get("title"):
            clean_title = re.sub(r'[\\/*?:"<>|]', "", str(info["title"])).strip()
            clean_title = re.sub(r'\s+', ' ', clean_title)[:120].strip()
            if clean_title:
                download_filename = f"{clean_title}.{ext}"

        return FileResponse(
            path=final_path,
            filename=download_filename,
            media_type="video/mp4" if ext == "mp4" else "audio/mpeg",
            background=BackgroundTask(safe_remove, final_path)
        )
    except Exception as e:
        safe_remove(raw_path)
        safe_remove(audio_path)
        safe_remove(final_path)
        logger.error(f"Error di /api/process: {e}")
        if isinstance(e, UnsafeURL):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# CELERY ASYNC QUEUE ENDPOINTS (/convert & /status/{job_id})
# ---------------------------------------------------------------------------

@app.post(
    "/convert",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue Job Konversi Asynchronous",
)
@app.post("/api/convert", response_model=JobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_convert_job(request: ProcessRequest):
    if not storage_manager.is_configured():
        raise HTTPException(status_code=503, detail="Antrean konversi membutuhkan S3/R2. Gunakan /api/process untuk unduhan langsung.")
    if not request.url or not request.url.strip():
        raise HTTPException(status_code=400, detail="Parameter 'url' wajib diisi.")

    job_id = str(uuid.uuid4())
    payload = request.model_dump()

    try:
        celery_app.send_task("tasks.process_media_task", args=[job_id, payload], task_id=job_id)
        return JobAcceptedResponse(
            job_id=job_id,
            status="PENDING",
            message="Tugas berhasil masuk ke dalam antrean Celery."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menghubungi broker Redis: {str(e)}")


@app.get("/status/{job_id}", response_model=StatusResponse)
@app.get("/api/status/{job_id}", response_model=StatusResponse)
def get_job_status(job_id: str):
    task_result = AsyncResult(job_id, app=celery_app)
    task_state = task_result.state

    if task_state in ("PENDING", "RECEIVED"):
        return StatusResponse(job_id=job_id, status="PENDING", progress=0, step="Menunggu Worker")
    elif task_state in ("PROCESSING", "STARTED"):
        meta = task_result.info if isinstance(task_result.info, dict) else {}
        return StatusResponse(
            job_id=job_id,
            status="PROCESSING",
            progress=meta.get("progress", 10),
            step=meta.get("step", "Sedang diproses")
        )
    elif task_state == "SUCCESS":
        result_data = task_result.result
        if isinstance(result_data, dict) and result_data.get("status") == "FAILURE":
            return StatusResponse(job_id=job_id, status="FAILURE", progress=100, error=result_data.get("error"))
        return StatusResponse(job_id=job_id, status="SUCCESS", progress=100, data=result_data)
    elif task_state in ("FAILURE", "REVOKED"):
        return StatusResponse(job_id=job_id, status="FAILURE", progress=100, error=str(task_result.result))

    return StatusResponse(job_id=job_id, status=task_state, progress=0)


@app.get("/")
def root():
    return {
        "status": "HEALTHY",
        "app_name": settings.APP_NAME,
        "message": "Kliprava Backend API is live and ready."
    }


@app.get("/api/health")
@app.get("/health")
def health_check():
    from redis import Redis
    redis_status = "UNAVAILABLE"
    try:
        with Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1) as conn:
            conn.ping()
        redis_status = "CONNECTED"
    except Exception:
        pass

    ffmpeg_ready = shutil.which("ffmpeg") is not None
    return JSONResponse(status_code=200 if ffmpeg_ready else 503, content={
        "status": "HEALTHY" if ffmpeg_ready else "UNHEALTHY",
        "app_name": settings.APP_NAME,
        "ffmpeg_available": ffmpeg_ready,
        "redis_broker": redis_status,
        "queue_available": redis_status == "CONNECTED" and storage_manager.is_configured(),
        "s3_storage_configured": storage_manager.is_configured(),
        "bucket_name": settings.S3_BUCKET_NAME
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
