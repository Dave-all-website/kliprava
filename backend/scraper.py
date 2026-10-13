import asyncio
import json
import logging
import os
import random
import re
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import uuid

import requests
import urllib3
from config import settings
from network import validate_media_page, open_public_stream

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

URL_RE = re.compile(r"https?://[^\s，,、。]+", re.IGNORECASE)
DOUYIN_ID_RE = re.compile(r"(?:/video/|/note/|modal_id=|/share/video/|aweme_id=|group_id=)(\d{6,})")
REDNOTE_ID_RE = re.compile(r"(?:/explore/|/discovery/item/|/user/\w+/)?([a-f0-9]{24})", re.IGNORECASE)


def clean_url(text: str) -> str:
    """Mengambil URL HTTP/HTTPS pertama dari teks share media sosial."""
    if not text:
        return ""
    text = text.strip()
    match = URL_RE.search(text)
    if match:
        return match.group(0).rstrip("/")
    return text


def resolve_canonical_url(url: str) -> str:
    """
    Menelusuri redirect tautan pendek (vm.tiktok.com, vt.tiktok.com, v.douyin.com,
    xhslink.com, t.co, fb.watch) menjadi URL kanonikal lengkap.
    """
    if not url:
        return ""
    low = url.lower()
    short_markers = ("vm.tiktok.com", "vt.tiktok.com", "v.douyin.com", "xhslink.com", "t.co", "fb.watch", "bit.ly")
    if any(m in low for m in short_markers):
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
                        video_id = data.get("id")

                        direct_url = None
                        if video_id:
                            direct_url = f"https://www.tikwm.com/video/media/play/{video_id}.mp4"

                        if not direct_url:
                            direct_url = data.get("hdplay") or data.get("play") or data.get("wmplay")

                        if direct_url and direct_url.startswith("//"):
                            direct_url = "https:" + direct_url

                        if direct_url:
                            cover_url = data.get("cover")
                            if cover_url and cover_url.startswith("/"):
                                cover_url = "https://www.tikwm.com" + cover_url
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

def _extract_douyin_share_page(video_id: str) -> Optional[Dict[str, Any]]:
    """Mengekstrak direct mp4 dari halaman share iesdouyin tanpa signature."""
    url = f"https://www.iesdouyin.com/share/video/{video_id}/"
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": MOBILE_UA, "Referer": "https://www.douyin.com/"},
            timeout=5,
            verify=False,
        )
        if resp.status_code == 200:
            m = re.search(r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>", resp.text, re.S)
            if m:
                data = json.loads(m.group(1))
                item = None
                for k, v in data.items():
                    if isinstance(v, dict) and "item_list" in v:
                        item = v["item_list"][0]
                        break
                if not item and "loaderData" in data and isinstance(data["loaderData"], dict):
                    for lv in data["loaderData"].values():
                        if isinstance(lv, dict):
                            if "videoDetail" in lv and isinstance(lv["videoDetail"], dict):
                                item = lv["videoDetail"]
                                break
                            elif "itemInfo" in lv and isinstance(lv["itemInfo"], dict):
                                item = lv["itemInfo"]
                                break

                if item:
                    video = item.get("video") or {}
                    play_addr = video.get("play_addr") or {}
                    url_list = play_addr.get("url_list") or []
                    play_url = None
                    if url_list:
                        play_url = url_list[0].replace("playwm", "play")
                    elif play_addr.get("uri"):
                        play_url = f"https://www.iesdouyin.com/aweme/v1/play/?video_id={play_addr['uri']}&ratio=1080p&line=0"

                    dur = video.get("duration") or item.get("duration") or 0
                    duration = round(dur / 1000) if dur > 1000 else int(dur or 60)
                    cover = (video.get("cover") or {}).get("url_list") or []

                    if play_url:
                        return {
                            "title": item.get("desc") or f"Douyin Video ({video_id})",
                            "thumbnail": cover[0] if cover else None,
                            "duration": duration or 60,
                            "direct_url": play_url,
                            "canonical_url": f"https://www.douyin.com/video/{video_id}",
                            "qualities": _quality_ladder([]),
                            "stream_headers": {
                                "User-Agent": MOBILE_UA,
                                "Referer": "https://www.douyin.com/"
                            }
                        }
    except Exception as e:
        logger.debug(f"Douyin share page extraction error: {e}")
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
            m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", html, re.S)
            if m:
                clean_json = m.group(1).replace("undefined", "null")
                data = json.loads(clean_json)
                note_dict = data.get("note", {})
                detail_map = note_dict.get("noteDetailMap", {})

                target_note = None
                if detail_map:
                    target_note = list(detail_map.values())[0].get("note", {})
                elif "firstNote" in note_dict:
                    target_note = note_dict.get("firstNote", {})

                if target_note:
                    raw_title = target_note.get("title") or target_note.get("desc") or "RedNote Video"
                    title = raw_title.strip().split("\n")[0][:100] or "RedNote Video"

                    video = target_note.get("video") or {}
                    media = video.get("media") or {}
                    stream = media.get("stream") or {}

                    video_url = None
                    for codec in ("h264", "h265", "h266", "av1"):
                        entries = stream.get(codec) or []
                        for entry in entries:
                            cand = entry.get("masterUrl") or entry.get("mainUrl") or entry.get("backupUrl")
                            if cand and ("http://" in cand or "https://" in cand):
                                video_url = cand
                                break
                        if video_url:
                            break

                    image_list = target_note.get("imageList") or []
                    thumbnail = image_list[0].get("urlDefault") or image_list[0].get("url") if image_list else None

                    if video_url:
                        return {
                            "title": title,
                            "thumbnail": thumbnail,
                            "duration": int(video.get("duration", 60)),
                            "direct_url": video_url,
                            "qualities": _quality_ladder([]),
                            "stream_headers": {
                                "User-Agent": DESKTOP_UA,
                                "Referer": "https://www.xiaohongshu.com/"
                            }
                        }

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


def _extract_youtube_fallback(url: str) -> Optional[Dict[str, Any]]:
    """
    Fallback extractor untuk YouTube ketika IP datacenter (seperti Railway) terkena bot protection.
    Memanfaatkan instance Invidious publik sehat yang dideteksi secara dinamis.
    """
    logger.info(f"[YouTube Fallback] Mencoba fallback API terdistribusi untuk: {url}")
    
    yt_id_match = re.search(r"(?:v=|\/|embed\/|shorts\/)([a-zA-Z0-9_-]{11})", url)
    video_id = yt_id_match.group(1) if yt_id_match else None
    
    if not video_id:
        return None

    # Dapatkan daftar instance Invidious yang sedang sehat & aktif
    invidious_instances = [
        "https://invidious.f5.si",
        "https://yt.chocolatemoo53.com",
        "https://invidious.tiekoetter.com",
        "https://inv.nadeko.net",
        "https://yewtu.be",
    ]
    try:
        health_resp = requests.get("https://api.invidious.io/instances.json?sort_by=health", timeout=3)
        if health_resp.status_code == 200:
            dyn_list = []
            for item in health_resp.json():
                if isinstance(item, list) and len(item) > 1:
                    info_dict = item[1]
                    if info_dict.get("type") == "https" and info_dict.get("api"):
                        uri = info_dict.get("uri") or f"https://{item[0]}"
                        dyn_list.append(uri.rstrip("/"))
            if dyn_list:
                invidious_instances = dyn_list[:6] + invidious_instances
    except Exception as he:
        logger.debug(f"Gagal mengambil dynamic invidious instances: {he}")

    for inv_base in invidious_instances:
        api_url = f"{inv_base}/api/v1/videos/{video_id}"
        try:
            resp = requests.get(api_url, headers={"User-Agent": DESKTOP_UA}, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                title = data.get("title", "YouTube Video")
                duration = int(data.get("lengthSeconds") or 60)
                thumb_list = data.get("videoThumbnails") or []
                thumb = thumb_list[0].get("url") if thumb_list else None

                # 1. Coba format gabungan (video + audio)
                streams = data.get("formatStreams") or []
                export_formats = []
                for entry in streams + (data.get("adaptiveFormats") or []):
                    if not entry.get("url"):
                        continue
                    mime = entry.get("type", "")
                    is_audio = mime.startswith("audio")
                    resolution_text = str(entry.get("resolution") or entry.get("qualityLabel") or "0").split("x")[-1]
                    height_match = re.search(r"\d+", resolution_text)
                    export_formats.append({
                        "url": entry["url"],
                        "height": int(height_match.group()) if height_match and not is_audio else 0,
                        "ext": entry.get("container") or ("m4a" if is_audio else "mp4"),
                        "vcodec": "none" if is_audio else "video",
                        "acodec": "audio" if is_audio or entry in streams else "none",
                        "tbr": float(entry.get("bitrate") or 0) / 1000,
                    })
                chosen_url = None
                for s in streams:
                    if s.get("url") and s.get("container") in ("mp4", "webm"):
                        chosen_url = s["url"]
                        break
                
                if not chosen_url and streams:
                    chosen_url = streams[0].get("url")

                # 2. Coba adaptiveFormats (video + audio terpisah)
                audio_url = None
                adaptive = data.get("adaptiveFormats") or []
                if not chosen_url and adaptive:
                    v_cands = [f for f in adaptive if f.get("type", "").startswith("video") and f.get("url")]
                    a_cands = [f for f in adaptive if f.get("type", "").startswith("audio") and f.get("url")]
                    if v_cands:
                        v_cands.sort(key=lambda x: next((f["height"] for f in export_formats if f["url"] == x["url"]), 0))
                        chosen_url = v_cands[-1]["url"]
                    if a_cands:
                        audio_url = a_cands[-1]["url"]

                if chosen_url:
                    logger.info(f"[YouTube Fallback] Berhasil via Invidious ({inv_base})")
                    return {
                        "title": title,
                        "thumbnail": thumb,
                        "duration": duration,
                        "direct_url": chosen_url,
                        "audio_url": audio_url,
                        "_formats": export_formats,
                        "qualities": _quality_ladder(export_formats),
                        "stream_headers": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
                            "Accept": "*/*",
                            "Referer": f"{inv_base}/"
                        }
                    }
        except Exception as e:
            logger.debug(f"Invidious instance {inv_base} failed: {e}")
            continue

    return None


# ============================================================================
# 5. YT-DLP EXTRACTION ENGINE (YouTube, IG, FB, X, TikTok)
# ============================================================================

def _extract_with_ytdlp(url: str, custom_headers: Optional[dict] = None) -> Dict[str, Any]:
    """Ekstraksi metadata & direct media URL menggunakan yt-dlp."""
    import yt_dlp

    is_yt = "youtube.com" in url.lower() or "youtu.be" in url.lower()
    client_strategies = (
        [
            ["mweb"],
            ["android"],
            ["web"],
            ["ios"],
            ["tv"],
            None
        ]
        if is_yt
        else [None]
    )

    cookie_path = os.path.join(os.path.dirname(__file__), "cookies.txt")
    if not os.path.exists(cookie_path):
        root_cookie = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies.txt")
        if os.path.exists(root_cookie):
            cookie_path = root_cookie

    last_error = None
    info = None

    for clients in client_strategies:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "noplaylist": True,
            "skip_download": True,
            "socket_timeout": 15,
            "retries": 3,
            "check_formats": False,
            "js_runtimes": {"node": {}, "deno": {}},
        }

        if clients:
            ydl_opts["extractor_args"] = {
                "youtube": {
                    "player_client": clients,
                }
            }

        if custom_headers and not is_yt:
            ydl_opts["http_headers"] = custom_headers

        # Dukungan file cookies.txt lokal
        cookie_candidates = [
            cookie_path,
            os.path.join(os.getcwd(), "cookies.txt"),
            os.path.join(os.path.dirname(__file__), "cookies.txt"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies.txt"),
            "/app/cookies.txt"
        ]
        active_cookie = None
        for cp in cookie_candidates:
            if cp and os.path.exists(cp) and os.path.getsize(cp) > 10:
                active_cookie = cp
                break

        if active_cookie:
            ydl_opts["cookiefile"] = active_cookie

        # Dukungan cookie via Environment Variable YOUTUBE_COOKIES (Plain text atau Base64)
        cookies_env = os.environ.get("YOUTUBE_COOKIES", "").strip()
        if cookies_env:
            try:
                import base64
                if not ("\t" in cookies_env or "# Netscape" in cookies_env):
                    try:
                        decoded = base64.b64decode(cookies_env).decode("utf-8")
                        if "# Netscape" in decoded or "\t" in decoded:
                            cookies_env = decoded
                    except Exception:
                        pass
                temp_cookie = os.path.join(os.path.dirname(__file__), "env_cookies.txt")
                with open(temp_cookie, "w", encoding="utf-8") as cf:
                    cf.write(cookies_env)
                ydl_opts["cookiefile"] = temp_cookie
            except Exception as ce:
                logger.warning(f"Gagal memuat env YOUTUBE_COOKIES: {ce}")

        # Dukungan Proxy khusus YouTube (YOUTUBE_PROXY) atau PROXIES
        yt_proxy = os.environ.get("YOUTUBE_PROXY", "").strip()
        if is_yt and yt_proxy:
            ydl_opts["proxy"] = yt_proxy
        elif settings.PROXIES:
            p_url = random.choice(settings.PROXIES)
            ydl_opts["proxy"] = p_url

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    break
        except Exception as e:
            last_error = e
            if not is_yt:
                raise e
            logger.warning(f"YouTube extractor strategy {clients} failed: {e}. Trying fallback...")
            continue
    else:
        if is_yt:
            fallback = _extract_youtube_fallback(url)
            if fallback:
                return fallback

        if last_error:
            err_msg = str(last_error)
            if "Sign in to confirm you’re not a bot" in err_msg or "bot" in err_msg.lower():
                raise Exception(
                    "YouTube mendeteksi IP datacenter server (Bot Protection). "
                    "Solusi: Pasang variabel 'YOUTUBE_COOKIES' atau 'YOUTUBE_PROXY' di dashboard Railway, atau gunakan platform lain seperti TikTok, Douyin, IG, FB, X, RedNote."
                )
            raise last_error
        raise Exception("Gagal mengekstrak media.")

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
    if "tiktok.com" in url_low or "tikwm.com" in url_low:
        logger.info(f"[Platform TikTok] Memproses: {target_url}")
        # Jalur Utama 1: TikWM API (Paling Cepat, No Watermark, Resolusi Penuh)
        info = fetch_tikwm_info(target_url) or fetch_tikwm_info(clean_target)
        if info:
            return info

        # Jalur Cadangan 2: TikSave API
        info_backup = fetch_tiksave_info(target_url) or fetch_tiksave_info(clean_target)
        if info_backup:
            return info_backup

        # Jalur Cadangan 3: yt-dlp
        try:
            return _extract_with_ytdlp(target_url, custom_headers={"User-Agent": MOBILE_UA, "Referer": "https://www.tiktok.com/"})
        except Exception as e:
            logger.error(f"Gagal mengambil video TikTok: {e}")
            raise Exception("Layanan TikTok sedang sibuk atau URL tidak dapat diakses saat ini. Silakan coba sesaat lagi.")

    # --- 2. DOUYIN ---
    elif "douyin.com" in url_low or "iesdouyin.com" in url_low:
        logger.info(f"[Platform Douyin] Memproses: {target_url}")
        vid_match = DOUYIN_ID_RE.search(target_url) or DOUYIN_ID_RE.search(clean_target)
        douyin_urls = []
        video_id = None
        if vid_match:
            video_id = vid_match.group(1)
            douyin_urls = [
                f"https://www.douyin.com/video/{video_id}",
                f"https://www.iesdouyin.com/share/video/{video_id}/",
            ]
        else:
            douyin_urls = [target_url]

        # Jalur 1: TikWM API (Cepat, No-Watermark)
        for d_url in douyin_urls:
            info = fetch_tikwm_info(d_url)
            if info:
                return info

        # Jalur 2: Halaman Share iesdouyin
        if video_id:
            info = _extract_douyin_share_page(video_id)
            if info:
                return info

        # Jalur 3: yt-dlp dengan URL kanonikal
        for d_url in douyin_urls:
            try:
                return _extract_with_ytdlp(d_url, custom_headers={"User-Agent": DESKTOP_UA, "Referer": "https://www.douyin.com/"})
            except Exception:
                pass

        raise Exception(
            "Video Douyin tidak dapat diekstrak karena pembatasan wilayah (geo-restriction/anti-bot) dari server Douyin China. "
            "Saran: Silakan gunakan fitur 'Salin Tautan' (share link) dari aplikasi Douyin (format v.douyin.com/...) atau gunakan tautan versi TikTok."
        )

    # --- 3. REDNOTE / XIAOHONGSHU ---
    elif any(s in url_low for s in ("xiaohongshu.com", "xhslink.com", "rednote")):
        logger.info(f"[Platform RedNote] Memproses: {target_url}")
        # Jalur 1: Fast HTML State & CDN Stream Extractor
        info = _extract_rednote_html(target_url) or _extract_rednote_html(clean_target)
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
        try:
            return _extract_with_ytdlp(target_url, custom_headers=headers)
        except Exception as e:
            logger.warning(f"yt-dlp failed for YouTube: {e}. Attempting fallback...")
            fb = _extract_youtube_fallback(target_url)
            if fb:
                return fb
            raise e

    # --- DEFAULT GENERIC ---
    else:
        logger.info(f"[Generic Platform] Memproses via yt-dlp: {target_url}")
        return _extract_with_ytdlp(target_url, custom_headers={"User-Agent": DESKTOP_UA})
