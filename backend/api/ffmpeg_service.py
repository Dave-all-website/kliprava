import os
import uuid



from api import douyin_service

# --- PAGAR RESOLUSI (trik untuk hosting RAM kecil, mis. Render free 512 MB) ---
# Server tidak akan pernah mengunduh video lebih tinggi dari batas ini,
# berapa pun pilihan user. Ubah lewat env var MAX_HEIGHT di dashboard hosting
# (contoh: 480 kalau masih berat, 1080 kalau nanti pindah server besar).
# Isi 0 untuk mematikan pagar.
try:
    _MAX_HEIGHT = int(os.environ.get("MAX_HEIGHT", "0") or 0)
except ValueError:
    _MAX_HEIGHT = 0


def _resolution_format(resolution):
    """Bangun format-selector yt-dlp dari pilihan resolusi yang presisi & jernih."""
    res_str = str(resolution or "").lower()
    
    digits = "".join(c for c in res_str if c.isdigit())
    target_height = int(digits) if digits else None
    if _MAX_HEIGHT and _MAX_HEIGHT > 0:
        target_height = min(target_height, _MAX_HEIGHT) if target_height else _MAX_HEIGHT

    if not target_height or target_height >= 1080:
        return "bv*[vcodec^=avc1]+ba[acodec^=mp4a]/bv*+ba/b[vcodec^=avc1]/b/best"
    
    h = target_height
    return (
        f"bv*[height<={h}][vcodec^=avc1]+ba[acodec^=mp4a]/"
        f"bv*[height<={h}]+ba/"
        f"b[height<={h}]/"
        f"best[height<={h}]"
    )


import time

def _safe_remove(filepath):
    """Hapus file secara aman tanpa memicu PermissionError di Windows."""
    if not filepath or not os.path.exists(filepath):
        return
    for _ in range(5):
        try:
            os.remove(filepath)
            break
        except Exception:
            time.sleep(0.1)


def process_media(original_url, start_time, end_time, output_format="mp4", resolution="best"):
    from api.yt_dlp_service import clean_input_url, _INFO_CACHE
    clean_url = clean_input_url(original_url)

    os.makedirs("temp_media", exist_ok=True)

    file_id = str(uuid.uuid4())
    temp_raw_file = f"temp_media/{file_id}_raw.mp4"
    output_filename = f"temp_media/{file_id}_final.{output_format}"

    try:
        downloaded = False

        # Coba unduh kilat dari cached direct_url (1-2 detik)
        is_douyin_url = douyin_service.is_douyin(clean_url)
        if clean_url in _INFO_CACHE and (resolution == "best" or is_douyin_url):
            _, cached_info = _INFO_CACHE[clean_url]
            direct_url = cached_info.get("direct_url")
            stream_headers = cached_info.get("stream_headers")
            if direct_url:
                try:
                    ref = stream_headers.get("Referer") if stream_headers else None
                    douyin_service.download_direct(direct_url, temp_raw_file, referer=ref, stream_headers=stream_headers)
                    if os.path.exists(temp_raw_file) and os.path.getsize(temp_raw_file) > 1024:
                        downloaded = True
                except Exception:
                    if os.path.exists(temp_raw_file):
                        _safe_remove(temp_raw_file)

        if not downloaded:
            if douyin_service.is_douyin(clean_url):
                _download_douyin(clean_url, temp_raw_file)
            else:
                _download_with_ytdlp(clean_url, temp_raw_file, resolution=resolution)

        if not os.path.exists(temp_raw_file):
            raise Exception("Gagal menyimpan video dari server asal.")

        _cut(temp_raw_file, output_filename, start_time, end_time, output_format)

        _safe_remove(temp_raw_file)
        return output_filename

    except Exception as e:
        _safe_remove(temp_raw_file)
        raise Exception(douyin_service.clean_error(str(e)))


def _cut(src, dst, start_time, end_time, output_format):
    import ffmpeg  # Lazy import to speed up initial backend load
    """Potong media dengan presisi tinggi menggunakan Fast Seek + Ultrafast Re-encoding."""
    start = max(0.0, float(start_time))
    duration = max(0.5, float(end_time) - start)
    start = round(start, 3)
    duration = round(duration, 3)

    is_mp3 = str(output_format).lower() == "mp3"

    try:
        input_stream = ffmpeg.input(src, ss=start)
        if is_mp3:
            (
                ffmpeg
                .output(
                    input_stream,
                    dst,
                    t=duration,
                    acodec="libmp3lame",
                    audio_bitrate="192k",
                    timelimit=120,
                )
                .run(overwrite_output=True, quiet=True)
            )
        else:
            (
                ffmpeg
                .output(
                    input_stream,
                    dst,
                    t=duration,
                    vcodec="libx264",
                    preset="ultrafast",
                    crf=23,
                    threads=0,
                    pix_fmt="yuv420p",
                    acodec="aac",
                    audio_bitrate="192k",
                    avoid_negative_ts="make_zero",
                    movflags="+faststart",
                    timelimit=120,
                )
                .run(overwrite_output=True, quiet=True)
            )
        if os.path.exists(dst) and os.path.getsize(dst) > 1024:
            return
    except Exception as e:
        if os.path.exists(dst):
            _safe_remove(dst)
        raise Exception("Gagal memotong video secara presisi.")


def _download_douyin(original_url, dest_path):
    canonical = douyin_service.resolve_douyin_url(original_url)
    target = canonical or original_url

    # 1. Jalur Utama: yt-dlp dengan Official ByteDance ttwid cookie
    try:
        _download_with_ytdlp(target, dest_path, douyin=True)
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
            return
    except Exception:
        if os.path.exists(dest_path):
            _safe_remove(dest_path)

    # 2. Jalur Cadangan: TikWM API
    tikwm_info = douyin_service.fetch_tikwm_info(original_url) or douyin_service.fetch_tikwm_info(target)
    if tikwm_info and tikwm_info.get("direct_url"):
        try:
            ref = "https://www.tikwm.com/" if douyin_service.is_tiktok(original_url) else douyin_service.DOUYIN_HOME
            douyin_service.download_direct(tikwm_info["direct_url"], dest_path, referer=ref)
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
                return
        except Exception:
            if os.path.exists(dest_path):
                _safe_remove(dest_path)

    # 3. Jalur Cadangan 2: iesdouyin share page
    video_id = douyin_service.extract_video_id(target) or douyin_service.extract_video_id(original_url)
    if video_id:
        try:
            info = douyin_service.share_page_info(video_id)
            if info and info.get("direct_url") and not info["direct_url"].startswith("https://www.iesdouyin.com/aweme/v1/play/"):
                douyin_service.download_direct(info["direct_url"], dest_path)
                if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
                    return
        except Exception:
            if os.path.exists(dest_path):
                _safe_remove(dest_path)


def _download_with_ytdlp(url, dest_path, douyin=False, resolution="best"):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "format": _resolution_format(resolution),
        "outtmpl": dest_path,
        "nopart": True,
        "socket_timeout": 8 if douyin else 15,
        "retries": 1 if douyin else 2,
        "fragment_retries": 1 if douyin else 2,
        "noplaylist": True,
        "concurrent_fragment_downloads": 8,
        "buffersize": 1048576,
        "http_chunk_size": 10485760,
        "merge_output_format": "mp4",
        "format_sort": ["vcodec:h264", "acodec:aac"],
    }

    temp_cookie = None
    url_low = url.lower()
    if douyin:
        temp_cookie = douyin_service.apply_douyin_auth(ydl_opts)
    elif any(s in url_low for s in ("tiktok.com", "ttwstatic", "byteoversea", "tiktokcdn")):
        ydl_opts["http_headers"] = {"User-Agent": douyin_service.DESKTOP_UA, "Referer": "https://www.tiktok.com/"}
    elif any(s in url_low for s in ("xiaohongshu.com", "xhslink.com", "rednote")):
        ydl_opts["http_headers"] = {"User-Agent": douyin_service.MOBILE_UA, "Referer": "https://www.xiaohongshu.com/"}
    elif any(s in url_low for s in ("instagram.com", "instagr.am", "facebook.com", "fb.watch", "fb.com", "twitter.com", "x.com", "t.co")):
        ydl_opts["http_headers"] = {"User-Agent": douyin_service.DESKTOP_UA}

    import yt_dlp
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    finally:
        if temp_cookie and os.path.exists(temp_cookie):
            try:
                os.remove(temp_cookie)
            except OSError:
                pass

