import asyncio
import json
import logging
import random
import re
from typing import Any, Dict, List, Optional
import urllib.parse

import requests
import urllib3
from config import settings
from network import validate_media_page, open_public_stream
from ytdlp_options import platform_name, ytdlp_options

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# --- UA & Platform Header Constants ---
DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
)

URL_RE = re.compile(r"https?://[^\s，,、。<>\"'\[\]()]+", re.IGNORECASE)
DOUYIN_ID_RE = re.compile(r"(?:/video/|/note/|modal_id=|/share/video/|aweme_id=|group_id=)(\d{6,})")
REDNOTE_ID_RE = re.compile(r"(?:/explore/|/discovery/item/|/user/\w+/)?([a-f0-9]{24})", re.IGNORECASE)


def clean_url(text: str) -> str:
    """Mengambil URL HTTP/HTTPS pertama dari teks share media sosial."""
    if not text:
        return ""
    text = text.strip()
    match = URL_RE.search(text)
    if match:
        return match.group(0).rstrip(")]}>\"'.,;")
    return text


def resolve_canonical_url(url: str) -> str:
    """
    Menelusuri redirect tautan pendek (vm.tiktok.com, vt.tiktok.com, v.douyin.com,
    xhslink.com, t.co, fb.watch) menjadi URL kanonikal lengkap.
    """
    if not url:
        return ""
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    short_markers = ("vm.tiktok.com", "vt.tiktok.com", "tt.site", "v.douyin.com", "xhslink.com", "t.co", "fb.watch", "bit.ly")
    if any(host == m or host.endswith("." + m) for m in short_markers):
        try:
            # Gunakan Mobile UA untuk redirect TikTok/Douyin/XHS agar tidak tersangkut bot verification
            headers = {"User-Agent": MOBILE_UA}
            resp, pool = open_public_stream(url, headers, timeout=(6, 8))
            try:
                resolved = resp.media_url
                validate_media_page(resolved)
                return resolved
            finally:
                resp.close()
                pool.close()
        except Exception as e:
            logger.debug(f"Gagal resolve redirect: {e}")
    return url


def get_random_proxy() -> Optional[dict]:
    """Mengembalikan proxy dict jika tersedia di settings."""
    if not settings.PROXIES:
        return None
    proxy_url = random.choice(settings.PROXIES)
    return {"http": proxy_url, "https": proxy_url}


def _quality_ladder(formats: List[dict]) -> List[dict]:
    """Menyusun daftar resolusi video yang tersedia."""
    heights = set()
    for f in formats or []:
        h = f.get("height")
        if h and f.get("vcodec") not in (None, "none"):
            h = int(h)
            if settings.MAX_VIDEO_HEIGHT and h > settings.MAX_VIDEO_HEIGHT:
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


# ============================================================================
# 1. TIKWM API ENGINE (Khusus TikTok & Douyin - No Watermark & Kilat 0.5s)
# ============================================================================

def fetch_tikwm_info(raw_url: str) -> Optional[Dict[str, Any]]:
    """Mengambil media tanpa watermark secara instan via Savetik/TikWM API."""
    canonical = resolve_canonical_url(raw_url) or raw_url
    clean_canonical = canonical.split('?')[0].split('#')[0]
    clean_raw = raw_url.split('?')[0].split('#')[0]
    
    # Hanya gunakan URL valid yang memiliki format normal
    urls_to_try = []
    for u in [clean_canonical, clean_raw, canonical, raw_url]:
        if u and u not in urls_to_try:
            urls_to_try.append(u)

    for target in urls_to_try[:2]:
        for ep in ["https://www.tikwm.com/api/", "https://tikwm.com/api/"]:
            try:
                resp = requests.post(
                    ep,
                    data={"url": target, "count": 12, "cursor": 0, "web": 1, "hd": 1},
                    timeout=7.0,
                    verify=False,
                    headers={
                        "User-Agent": DESKTOP_UA,
                        "Referer": "https://www.tikwm.com/",
                        "Accept": "application/json, text/javascript, */*; q=0.01",
                    },
                )
                if resp.status_code == 200:
                    res = resp.json()
                    if res.get("code") == 0:
                        data = res.get("data") or {}
                        direct_url = data.get("hdplay") or data.get("play") or data.get("wmplay")
                        if direct_url:
                            direct_url = urllib.parse.urljoin(ep, direct_url)

                        if direct_url:
                            cover_url = data.get("cover")
                            if cover_url:
                                cover_url = urllib.parse.urljoin(ep, cover_url)
                            return {
                                "title": data.get("title") or "Video TikTok",
                                "thumbnail": cover_url,
                                "duration": int(data.get("duration") or 60),
                                "direct_url": direct_url,
                                "canonical_url": canonical or target,
                                "qualities": _quality_ladder([]),
                                "stream_headers": {
                                    "User-Agent": DESKTOP_UA,
                                    "Referer": "https://www.tikwm.com/"
                                }
                            }
            except Exception:
                pass
    return None


def fetch_tiksave_info(raw_url: str) -> Optional[Dict[str, Any]]:
    """Cadangan scraper TikTok via TikSave API (no watermark)."""
    try:
        canonical = resolve_canonical_url(raw_url) or raw_url
        clean_url = canonical.split('?')[0].split('#')[0]
        resp = requests.post(
            "https://tiksave.io/api/ajaxSearch",
            data={"q": clean_url},
            headers={"User-Agent": DESKTOP_UA, "Referer": "https://tiksave.io/"},
            timeout=7.0,
            verify=False,
        )
        if resp.status_code == 200:
            html = resp.json().get("data", "")
            if html:
                dl_matches = re.findall(r'href=[\'"](https?://[^\'"]+)[\'"]', html)
                direct_url = None
                for link in dl_matches:
                    if "download" in link or "snapcdn" in link or "tik" in link:
                        direct_url = link
                        break
                if not direct_url and dl_matches:
                    direct_url = dl_matches[0]

                title_match = re.search(r'<h3>(.*?)</h3>', html)
                title = title_match.group(1) if title_match else "Video TikTok"
                img_match = re.search(r'<img[^>]+src=[\'"](https?://[^\'"]+)[\'"]', html)
                thumbnail = img_match.group(1) if img_match else ""

                if direct_url:
                    return {
                        "title": title,
                        "thumbnail": thumbnail,
                        "duration": 60,
                        "direct_url": direct_url,
                        "canonical_url": clean_url,
                        "qualities": _quality_ladder([]),
                        "stream_headers": {"User-Agent": DESKTOP_UA}
                    }
    except Exception as e:
        logger.warning(f"fetch_tiksave_info failed: {e}")
    return None


# ============================================================================
# 2. DOUYIN SHARE PAGE ENGINE (HTML JSON Embedded Extractor)
# ============================================================================

def _extract_douyin_share_page(video_id: str, share_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Read public share state while preserving the original share parameters."""
    from douyin import parse_share_video
    url = share_url or f"https://www.iesdouyin.com/share/video/{video_id}/"
    headers = {"User-Agent": MOBILE_UA, "Referer": "https://www.douyin.com/"}
    try:
        validate_media_page(url)
        response, pool = open_public_stream(url, headers, timeout=(6, 10))
        try:
            if response.status != 200:
                logger.info("Douyin share page returned HTTP %s", response.status)
                return None
            html = response.read(2 * 1024 * 1024, decode_content=True).decode("utf-8", errors="replace")
            info = parse_share_video(html, video_id, url, headers)
            if info:
                info["qualities"] = _quality_ladder(info["_formats"])
            return info
        finally:
            response.close()
            pool.close()
    except Exception as exc:
        logger.debug("Douyin share page extraction failed: %s", exc)
    return None


# ============================================================================
# 3. REDNOTE (XIAOHONGSHU) FAST HTML EXTRACTOR
# ============================================================================

def _extract_rednote_html(raw_url: str) -> Optional[Dict[str, Any]]:
    """Mengekstrak data media Xiaohongshu langsung dari SSR HTML State dan direct stream CDN."""
    headers_list = [
        {
            "User-Agent": DESKTOP_UA,
            "Referer": "https://www.xiaohongshu.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        },
        {
            "User-Agent": MOBILE_UA,
            "Referer": "https://www.xiaohongshu.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
    ]

    for headers in headers_list:
        try:
            resp = requests.get(raw_url, headers=headers, timeout=8, allow_redirects=True, verify=False)
            if resp.status_code != 200:
                continue

            html = resp.text

            # 1. Ekstraksi dari window.__INITIAL_STATE__
            m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?\s*</script>", html, re.S)
            if m:
                from yt_dlp.utils import js_to_json
                data = json.loads(js_to_json(m.group(1)))
                note_dict = data.get("note", {})
                detail_map = note_dict.get("noteDetailMap", {})

                note_match = REDNOTE_ID_RE.search(urllib.parse.urlsplit(raw_url).path)
                note_id = note_match.group(1) if note_match else None
                target_note = (detail_map.get(note_id) or {}).get("note")
                if not target_note:
                    first = note_dict.get("firstNote") or {}
                    if not note_id or first.get("noteId") == note_id:
                        target_note = first

                if target_note:
                    raw_title = target_note.get("title") or target_note.get("desc") or "RedNote Video"
                    title = raw_title.strip().split("\n")[0][:100] or "RedNote Video"

                    video = target_note.get("video") or {}
                    media = video.get("media") or {}
                    stream = media.get("stream") or {}

                    formats = []
                    durations = []
                    for codec in ("h264", "h265", "h266", "av1"):
                        entries = stream.get(codec) or []
                        for entry in entries:
                            backups = entry.get("backupUrls") or entry.get("backupUrl") or []
                            if isinstance(backups, str):
                                backups = [backups]
                            urls = [entry.get("masterUrl"), entry.get("mainUrl"), *backups]
                            urls = list(dict.fromkeys(u for u in urls if isinstance(u, str) and u.startswith(("https://", "http://"))))
                            if not urls:
                                continue
                            if entry.get("duration"):
                                durations.append(float(entry["duration"]) / 1000)
                            formats.append({
                                "url": urls[0], "backup_urls": urls[1:],
                                "ext": "mp4",
                                "height": entry.get("height"), "width": entry.get("width"),
                                "vcodec": codec, "acodec": entry.get("audioCodec") or "aac",
                                "tbr": float(entry.get("avgBitrate") or 0) / 1000,
                            })

                    image_list = target_note.get("imageList") or []
                    thumbnail = image_list[0].get("urlDefault") or image_list[0].get("url") if image_list else None

                    if formats:
                        preview = next((f for f in formats if f["vcodec"] == "h264"), formats[0])
                        return {
                            "title": title,
                            "thumbnail": thumbnail,
                            "duration": max(durations) if durations else float(video.get("duration") or 60),
                            "direct_url": preview["url"],
                            "canonical_url": raw_url,
                            "_formats": formats,
                            "qualities": _quality_ladder(formats),
                            "stream_headers": {
                                "User-Agent": DESKTOP_UA,
                                "Referer": "https://www.xiaohongshu.com/"
                            }
                        }

                # A recommendation's stream must never replace the requested note.
                if detail_map:
                    continue

            # 2. Fallback: Regex scan langsung untuk URL stream video (.mp4 di sns-video CDN)
            v_match = re.search(r'(https?:\\?/\\?/[^"\'<>\s]+?(?:sns-video|xhscdn)[^"\'<>\s]+?\.mp4[^"\'<>\s]*)', html)
            if v_match:
                clean_v_url = v_match.group(1).replace(r"\/", "/").replace("\\u002F", "/")
                title_m = re.search(r"<title>(.*?)</title>", html)
                t = title_m.group(1).replace("- 小红书", "").replace(" - RED", "").strip() if title_m else "RedNote Video"
                return {
                    "title": t,
                    "thumbnail": None,
                    "duration": 60,
                    "direct_url": clean_v_url,
                    "canonical_url": raw_url,
                    "qualities": _quality_ladder([]),
                    "stream_headers": {
                        "User-Agent": DESKTOP_UA,
                        "Referer": "https://www.xiaohongshu.com/"
                    }
                }
        except Exception as e:
            logger.debug(f"RedNote fast html attempt failed: {e}")

    return None


# ============================================================================
# 4. PLAYWRIGHT STEALTH SCRAPER (Bypass Douyin & RedNote Signature Captcha)
# ============================================================================

async def _scrape_with_playwright_stealth(url: str, platform: str) -> Dict[str, Any]:
    """Bypass JavaScript signatures (X-Bogus/a_bogus/X-s) dengan Browser Headless Stealth."""
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth

    logger.info(f"[Playwright Stealth] Menjalankan browser stealth untuk {platform}: {url}")
    proxy_config = None
    if settings.PROXIES:
        p_url = random.choice(settings.PROXIES)
        proxy_config = {"server": p_url}

    captured_media_urls = []
    page_data = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=settings.PLAYWRIGHT_HEADLESS,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
            ],
            proxy=proxy_config
        )

        is_mobile = platform in ("rednote", "douyin")
        context = await browser.new_context(
            user_agent=MOBILE_UA if is_mobile else DESKTOP_UA,
            viewport={"width": 390, "height": 844} if is_mobile else {"width": 1280, "height": 720},
            locale="zh-CN"
        )
        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        async def handle_response(response):
            try:
                r_url = response.url.lower()
                content_type = (response.headers.get("content-type") or "").lower()
                if "video/mp4" in content_type or ".mp4" in r_url or "aweme/v1/play" in r_url or "douyinvod" in r_url or "sns-video" in r_url:
                    if r_url not in captured_media_urls and "verify" not in r_url:
                        captured_media_urls.append(response.url)
            except Exception:
                pass

        page.on("response", handle_response)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=settings.PLAYWRIGHT_TIMEOUT)
            await asyncio.sleep(2.5)
            if is_mobile:
                try:
                    await page.mouse.click(195, 350)
                    await asyncio.sleep(1.5)
                except Exception:
                    pass
            title = await page.title()
            page_data["title"] = title.replace(" - 抖音", "").replace("- 小红书", "").strip() or f"{platform.capitalize()} Video"
        except Exception as e:
            logger.warning(f"[Playwright Stealth] Warning saat memuat: {e}")
        finally:
            await browser.close()

    direct_url = captured_media_urls[0] if captured_media_urls else None
    if not direct_url:
        raise Exception(f"Playwright tidak menemukan direct stream video untuk {platform}.")

    return {
        "title": page_data.get("title", f"{platform.capitalize()} Media"),
        "thumbnail": None,
        "duration": 60,
        "direct_url": direct_url,
        "qualities": _quality_ladder([]),
        "stream_headers": {
            "User-Agent": MOBILE_UA if platform == "rednote" else DESKTOP_UA,
            "Referer": "https://www.xiaohongshu.com/" if platform == "rednote" else "https://www.douyin.com/"
        }
    }


def _extract_with_ytdlp(url: str, custom_headers: Optional[dict] = None) -> Dict[str, Any]:
    """Ekstraksi metadata & direct media URL menggunakan yt-dlp."""
    import yt_dlp

    overrides = {"skip_download": True, "check_formats": False}
    if custom_headers and platform_name(url) != "YOUTUBE":
        overrides["http_headers"] = custom_headers
    try:
        with ytdlp_options(url, **overrides) as options:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
    except Exception as exc:
        message = str(exc).lower()
        if platform_name(url) == "YOUTUBE" and ("not a bot" in message or "confirm you're" in message):
            raise ValueError(
                "YouTube meminta verifikasi untuk koneksi server ini. "
                "Administrator perlu mengatur YOUTUBE_COOKIES yang masih berlaku "
                "dan, bila diperlukan, YOUTUBE_PROXY di Railway."
            ) from exc
        raise
    if not info:
        raise ValueError("Gagal mengekstrak media.")

    formats = info.get("formats", [])

    def is_playable_stream(f):
        if not isinstance(f, dict):
            return False
        u = str(f.get("url", "")).lower()
        proto = str(f.get("protocol", "")).lower()
        if "manifest" in u or ".m3u8" in u or "m3u8" in proto or "dash" in proto or "f4m" in proto:
            return False
        return True

    stream_url = None
    chosen = None

    # 1. Kandidat Video Gabungan (Video + Audio)
    cands_combined = [
        f for f in formats
        if f.get("vcodec") not in (None, "none")
        and f.get("acodec") not in (None, "none")
        and f.get("url")
        and is_playable_stream(f)
    ]

    # 2. Kandidat Video (Video Only)
    cands_video_only = [
        f for f in formats
        if f.get("vcodec") not in (None, "none")
        and f.get("url")
        and is_playable_stream(f)
    ]

    if cands_combined:
        cands_combined.sort(key=lambda x: (1 if x.get("ext") == "mp4" else 0, int(x.get("height") or 0)))
        chosen = cands_combined[-1]
        stream_url = chosen.get("url")
    elif cands_video_only:
        cands_video_only.sort(key=lambda x: (1 if x.get("ext") == "mp4" else 0, int(x.get("height") or 0)))
        chosen = cands_video_only[-1]
        stream_url = chosen.get("url")

    # 3. URL bawaan info jika belum terpilih
    final_url = stream_url or (info.get("url") if is_playable_stream(info) else None)
    if not final_url and formats:
        for f in reversed(formats):
            if f.get("url") and is_playable_stream(f) and f.get("vcodec") not in (None, "none"):
                chosen = f
                final_url = f.get("url")
                break
        if not final_url and formats:
            chosen = formats[-1]
            final_url = formats[-1].get("url")

    if not final_url:
        raise Exception("yt-dlp tidak dapat menemukan URL stream video yang valid.")

    stream_headers = {}
    if chosen and isinstance(chosen.get("http_headers"), dict):
        stream_headers.update(chosen["http_headers"])
    elif custom_headers:
        stream_headers.update(custom_headers)
    else:
        stream_headers = {"User-Agent": DESKTOP_UA, "Referer": url}

    # 4. Ekstraksi dedicated audio stream jika video yang dipilih tidak memiliki audio
    audio_url = None
    audio_headers = None
    if chosen and chosen.get("acodec") in (None, "none"):
        audio_cands = [
            f for f in formats
            if f.get("acodec") not in (None, "none")
            and f.get("url")
            and is_playable_stream(f)
        ]
        if audio_cands:
            audio_cands.sort(key=lambda x: (1 if x.get("ext") in ("m4a", "mp4", "mp3") else 0, float(x.get("tbr") or x.get("abr") or 0)))
            audio_url = audio_cands[-1].get("url")
            audio_headers = audio_cands[-1].get("http_headers")

    dur = info.get("duration")
    duration = int(dur) if dur and dur > 0 else 0
    if not duration and final_url:
        import subprocess
        try:
            probe_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                final_url
            ]
            res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.strip():
                duration = int(float(res.stdout.strip()))
        except Exception:
            pass

    if not duration or duration <= 0:
        duration = 60

    return {
        "title": info.get("title") or "Social Media Video",
        "canonical_url": url,
        "thumbnail": info.get("thumbnail"),
        "duration": duration,
        "direct_url": final_url,
        "audio_url": audio_url,
        "audio_headers": audio_headers,
        "_formats": [f for f in formats if is_playable_stream(f)],
        "qualities": _quality_ladder(formats),
        "stream_headers": stream_headers
    }


# ============================================================================
# 6. UNIVERSAL DISPATCHER UNTUK 7 PLATFORM
# ============================================================================

def extract_media_info(raw_url: str) -> Dict[str, Any]:
    """
    Dispatcher utama untuk 7 platform sosmed:
    1. YouTube
    2. TikTok
    3. Instagram
    4. Facebook
    5. X (Twitter)
    6. Douyin
    7. RedNote (Xiaohongshu)
    """
    clean_target = clean_url(raw_url)
    if not clean_target or not clean_target.startswith("http"):
        raise ValueError("URL tidak valid. Harap sertakan URL lengkap http:// atau https://.")
    validate_media_page(clean_target)

    # Resolve tautan pendek (vm.tiktok.com, v.douyin.com, youtu.be, dll.)
    target_url = resolve_canonical_url(clean_target)
    url_low = target_url.lower()

    # --- 1. TIKTOK ---
    if platform_name(target_url) == "TIKTOK":
        logger.info(f"[Platform TikTok] Memproses: {target_url}")
        # Jalur Utama 1: TikWM API (Paling Cepat, No Watermark, Resolusi Penuh)
        info = fetch_tikwm_info(target_url)
        if info:
            return info

        # Jalur Cadangan 2: TikSave API
        info_backup = fetch_tiksave_info(target_url)
        if info_backup:
            return info_backup

        # Jalur Cadangan 3: yt-dlp
        try:
            return _extract_with_ytdlp(target_url, custom_headers={"User-Agent": MOBILE_UA, "Referer": "https://www.tiktok.com/"})
        except Exception as e:
            logger.error(f"Gagal mengambil video TikTok: {e}")
            raise Exception("Layanan TikTok sedang sibuk atau URL tidak dapat diakses saat ini. Silakan coba sesaat lagi.")

    # --- 2. DOUYIN ---
    elif platform_name(target_url) == "DOUYIN":
        logger.info("[Platform Douyin] Memproses: %s", target_url.split("?")[0])
        vid_match = DOUYIN_ID_RE.search(target_url) or DOUYIN_ID_RE.search(clean_target)
        if not vid_match:
            raise ValueError("Tautan pendek Douyin belum dapat dibuka. Coba salin ulang tautan postingan yang masih aktif.")
        video_id = vid_match.group(1)
        share_url = target_url if "iesdouyin.com" in (urllib.parse.urlsplit(target_url).hostname or "") else None
        info = _extract_douyin_share_page(video_id, share_url)
        if info:
            return info
        canonical_url = f"https://www.douyin.com/video/{video_id}"
        info = fetch_tikwm_info(canonical_url)
        if info:
            return info
        try:
            return _extract_with_ytdlp(canonical_url, custom_headers={"User-Agent": DESKTOP_UA, "Referer": "https://www.douyin.com/"})
        except Exception as exc:
            logger.warning("Douyin extraction failed for %s: %s", video_id, exc)
            message = str(exc).lower()
            if "fresh cookies" in message or "403" in message or "forbidden" in message:
                raise ValueError(
                    "Douyin menolak akses dari server dan meminta cookie sesi yang masih berlaku. "
                    "Link sudah dikenali. Administrator perlu mengatur DOUYIN_COOKIES di Railway; "
                    "jika koneksi server tetap ditolak, periksa DOUYIN_PROXY."
                ) from exc
            raise ValueError(
                "Data video Douyin belum dapat diambil. Pastikan postingan masih tersedia dan dapat dibuka di Douyin. "
                "Detail kegagalan telah dicatat di log server."
            ) from exc

    # --- 3. REDNOTE / XIAOHONGSHU ---
    elif platform_name(target_url) == "REDNOTE":
        logger.info(f"[Platform RedNote] Memproses: {target_url}")
        # Jalur 1: Fast HTML State & CDN Stream Extractor
        info = _extract_rednote_html(target_url)
        if info:
            return info

        # Jalur 2: yt-dlp
        try:
            return _extract_with_ytdlp(target_url, custom_headers={"User-Agent": DESKTOP_UA, "Referer": "https://www.xiaohongshu.com/"})
        except Exception:
            pass

        # Jalur 3: Playwright Stealth Browser Fallback
        try:
            return asyncio.run(_scrape_with_playwright_stealth(target_url, platform="rednote"))
        except Exception:
            pass

        raise Exception("Gagal mengekstrak video RedNote (Xiaohongshu). Pastikan link postingan bersifat publik dan masih aktif.")

    # --- 4. INSTAGRAM ---
    elif "instagram.com" in url_low or "instagr.am" in url_low:
        logger.info(f"[Platform Instagram] Memproses: {target_url}")
        headers = {
            "User-Agent": DESKTOP_UA,
            "X-IG-App-ID": "936619743392459",
            "X-ASBD-ID": "198387",
            "X-IG-WWW-Claim": "0",
            "Referer": "https://www.instagram.com/",
            "Origin": "https://www.instagram.com",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors"
        }
        return _extract_with_ytdlp(target_url, custom_headers=headers)

    # --- 5. FACEBOOK ---
    elif "facebook.com" in url_low or "fb.watch" in url_low or "fb.com" in url_low:
        logger.info(f"[Platform Facebook] Memproses: {target_url}")
        headers = {"User-Agent": DESKTOP_UA, "Referer": "https://www.facebook.com/"}
        return _extract_with_ytdlp(target_url, custom_headers=headers)

    # --- 6. X (TWITTER) ---
    elif "twitter.com" in url_low or "x.com" in url_low or "t.co" in url_low:
        logger.info(f"[Platform X/Twitter] Memproses: {target_url}")
        headers = {"User-Agent": DESKTOP_UA, "Referer": "https://x.com/"}
        return _extract_with_ytdlp(target_url, custom_headers=headers)

    # --- 7. YOUTUBE ---
    elif "youtube.com" in url_low or "youtu.be" in url_low:
        logger.info(f"[Platform YouTube] Memproses: {target_url}")
        headers = {"User-Agent": DESKTOP_UA, "Referer": "https://www.youtube.com/"}
        return _extract_with_ytdlp(target_url, custom_headers=headers)

    # --- DEFAULT GENERIC ---
    else:
        logger.info(f"[Generic Platform] Memproses via yt-dlp: {target_url}")
        return _extract_with_ytdlp(target_url, custom_headers={"User-Agent": DESKTOP_UA})
