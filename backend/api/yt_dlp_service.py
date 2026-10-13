import os
import re
import time
import urllib.parse


from api import douyin_service


def clean_input_url(text: str) -> str:
    """Ekstrak URL HTTP(S) pertama dari teks (membersihkan teks share medsos)."""
    if not text:
        return ""
    text = text.strip()
    match = re.search(r"https?://[^\s，,、。]+", text, re.IGNORECASE)
    if match:
        return match.group(0).rstrip("/")
    return text


_INFO_CACHE = {}
_CACHE_MAX_AGE = 600  # 10 menit cache metadata


def extract_video_info(url: str):
    clean_url = clean_input_url(url)
    now = time.time()
    if clean_url in _INFO_CACHE:
        cached_time, cached_data = _INFO_CACHE[clean_url]
        # Hapus cache lama jika TikTok URL tidak sengaja menyimpan data Douyin
        if douyin_service.is_tiktok(clean_url) and ("iesdouyin" in str(cached_data.get("direct_url", "")) or "Douyin Video" in str(cached_data.get("title", ""))):
            del _INFO_CACHE[clean_url]
        elif now - cached_time < _CACHE_MAX_AGE:
            return cached_data

    info = None
    if douyin_service.is_douyin(clean_url):
        try:
            info = _extract_douyin_info(clean_url)
        except Exception:
            pass

    if not info:
        info = _extract_with_ytdlp(clean_url, douyin=False)

    _INFO_CACHE[clean_url] = (now, info)
    return info


def _extract_douyin_info(url: str):
    canonical = douyin_service.resolve_douyin_url(url)
    target = canonical or url

    # 1. Jalur Utama: yt-dlp dengan Cookie Official ByteDance (ttwid resmi)
    try:
        info = _extract_with_ytdlp(target, douyin=True)
        if info and info.get("direct_url"):
            return info
    except Exception:
        pass

    # 2. Jalur Cadangan 1: API Savetik/TikWM
    tikwm_res = douyin_service.fetch_tikwm_info(url) or douyin_service.fetch_tikwm_info(target)
    if tikwm_res:
        tikwm_res["qualities"] = _quality_ladder([])
        tikwm_res["stream_headers"] = {
            "User-Agent": douyin_service.DESKTOP_UA,
            "Referer": "https://www.tikwm.com/",
        }
        return tikwm_res

    # 3. Jalur Cadangan 2: Halaman Share iesdouyin
    video_id = douyin_service.extract_video_id(target) or douyin_service.extract_video_id(url)
    if video_id:
        try:
            info = douyin_service.share_page_info(video_id)
            if info and info.get("direct_url") and not info["direct_url"].startswith("https://www.iesdouyin.com/aweme/v1/play/"):
                info["qualities"] = _quality_ladder([])
                info["stream_headers"] = {
                    "User-Agent": douyin_service.DESKTOP_UA,
                    "Referer": douyin_service.DOUYIN_HOME,
                }
                return info
        except Exception:
            pass

    return _extract_with_ytdlp(target, douyin=True)


def _quality_ladder(formats):
    try:
        max_h = int(os.environ.get("MAX_HEIGHT", "0") or 0)
    except ValueError:
        max_h = 0
    heights = set()
    for f in formats or []:
        h = f.get("height")
        if h and f.get("vcodec") not in (None, "none"):
            h = int(h)
            if max_h and max_h > 0 and h > max_h:
                continue
            if h >= 144:
                heights.add(h)
    ladder = [{"label": f"{h}p", "height": h} for h in sorted(heights, reverse=True)]
    if not ladder:
        ladder = [
            {"label": "1080p Full HD", "height": 1080},
            {"label": "720p HD", "height": 720},
            {"label": "480p SD", "height": 480},
            {"label": "360p SD", "height": 360},
        ]
    return ladder


def _cookie_header(cookiejar, stream_url):
    try:
        host = (urllib.parse.urlsplit(stream_url).hostname or "").lower()
    except Exception:
        return ""
    if not host or cookiejar is None:
        return ""
    pairs = []
    for c in cookiejar:
        dom = (c.domain or "").lstrip(".").lower()
        if dom and (host == dom or host.endswith("." + dom)):
            pairs.append(f"{c.name}={c.value}")
    return "; ".join(pairs)


def _extract_with_ytdlp(url: str, douyin: bool = False):
    if not url or not str(url).startswith("http") or any(s in str(url) for s in ("sslocal://", "snssdk", "douyin://")):
        raise Exception("Tautan yang dimasukkan adalah link Chat/Toko Douyin, bukan link video. Silakan gunakan link postingan video Douyin.")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "noplaylist": True,
        "skip_download": True,
        "socket_timeout": 10,
        "retries": 2,
        "check_formats": False,
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
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])

            # Cari kandidat format video terbaik untuk preview (diurutkan berdasarkan resolusi tertinggi)
            stream_url = None
            chosen = None

            # Standard 1: H.264 + Audio + MP4
            cands_h264 = [
                f for f in formats
                if f.get("ext") == "mp4"
                and f.get("vcodec") not in (None, "none")
                and f.get("acodec") not in (None, "none")
                and str(f.get("vcodec", "")).startswith("avc")
                and f.get("url")
            ]
            if cands_h264:
                cands_h264.sort(key=lambda x: int(x.get("height") or 0))
                chosen = cands_h264[-1]
                stream_url = chosen.get("url")

            # Standard 2: Audio+Video (any extension/container)
            if not stream_url:
                cands_combined = [
                    f for f in formats
                    if f.get("vcodec") not in (None, "none")
                    and f.get("acodec") not in (None, "none")
                    and f.get("url")
                ]
                if cands_combined:
                    cands_combined.sort(key=lambda x: int(x.get("height") or 0))
                    chosen = cands_combined[-1]
                    stream_url = chosen.get("url")

            # Standard 3: Video MP4 (meski audio terpisah)
            if not stream_url:
                cands_video_only = [
                    f for f in formats
                    if f.get("vcodec") not in (None, "none")
                    and f.get("url")
                ]
                if cands_video_only:
                    cands_video_only.sort(key=lambda x: int(x.get("height") or 0))
                    chosen = cands_video_only[-1]
                    stream_url = chosen.get("url")

            final_url = stream_url or info.get("url")

            stream_headers = {}
            if chosen and isinstance(chosen.get("http_headers"), dict):
                for k in ("User-Agent", "Referer", "Origin", "Accept"):
                    if chosen["http_headers"].get(k):
                        stream_headers[k] = chosen["http_headers"][k]

            cookie = _cookie_header(getattr(ydl, "cookiejar", None), final_url or "")
            if cookie:
                stream_headers["Cookie"] = cookie

            # Set Referer bawaan per platform jika belum ada
            if "Referer" not in stream_headers:
                if any(s in url_low for s in ("tiktok.com", "ttwstatic", "tiktokcdn")):
                    stream_headers["Referer"] = "https://www.tiktok.com/"
                elif any(s in url_low for s in ("instagram.com", "instagr.am", "facebook.com", "fb.watch")):
                    stream_headers["Referer"] = "https://www.instagram.com/"
                elif any(s in url_low for s in ("xiaohongshu.com", "xhslink.com", "rednote")):
                    stream_headers["Referer"] = "https://www.xiaohongshu.com/"
                elif any(s in url_low for s in ("youtube.com", "youtu.be", "googlevideo")):
                    stream_headers["Referer"] = "https://www.youtube.com/"
                elif any(s in url_low for s in ("twitter.com", "x.com", "t.co")):
                    stream_headers["Referer"] = "https://x.com/"

            if "User-Agent" not in stream_headers:
                if any(s in url_low for s in ("xiaohongshu.com", "xhslink.com", "rednote")):
                    stream_headers["User-Agent"] = douyin_service.MOBILE_UA
                else:
                    stream_headers["User-Agent"] = douyin_service.DESKTOP_UA

            return {
                "title": info.get("title", "Unknown Video"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration", 60),
                "direct_url": final_url,
                "qualities": _quality_ladder(formats),
                "stream_headers": stream_headers,
            }
    except Exception as e:
        raise Exception(douyin_service.clean_error(str(e)))
    finally:
        if temp_cookie and os.path.exists(temp_cookie):
            try:
                os.remove(temp_cookie)
            except OSError:
                pass


