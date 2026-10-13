"""
Logika Douyin, versi 3.

Pelajaran dari error terakhir: cookie SUDAH terkirim (yt-dlp menampilkan pesan
"report this issue" yang hanya muncul kalau s_v_web_id ada), tapi API detail
Douyin tetap menolak. Sebabnya: API itu kini menuntut tanda tangan permintaan
(a_bogus) yang dihitung JavaScript — dan yt-dlp memang tidak membuatnya
(ada TODO di kode yt-dlp sendiri). Menambah cookie tidak akan pernah cukup.

Jalan keluar yang dipakai downloader Douyin yang benar-benar jalan: baca
HALAMAN SHARE https://www.iesdouyin.com/share/video/<id>/ . Halaman itu
menanamkan JSON data video (judul, cover, durasi, dan link mp4) langsung di
HTML — tanpa signature, tanpa cookie. Modul ini menjadikannya jalur UTAMA;
yt-dlp hanya cadangan.
"""

import json
import os
import re
import time
import urllib.parse
import uuid

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOUYIN_HOME = "https://www.douyin.com/"

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Halaman share menyajikan data paling lengkap kalau diakses seperti HP.
MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)

_URL_RE = re.compile(r"https?://[^\s，,、。]+", re.IGNORECASE)
_ID_RE = re.compile(r"(?:/video/|/note/|modal_id=|/share/video/|aweme_id=|group_id=)(\d{6,})")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

_VALID_BROWSERS = {
    "brave", "chrome", "chromium", "edge",
    "firefox", "opera", "safari", "vivaldi", "whale",
}


def is_douyin(url):
    return "douyin.com" in (url or "").lower()


def is_tiktok(url):
    return "tiktok.com" in (url or "").lower()


def is_tiktok_or_douyin(url):
    u = (url or "").lower()
    return "douyin.com" in u or "tiktok.com" in u or "tikwm.com" in u


def douyin_headers():
    return {"User-Agent": DESKTOP_UA, "Referer": DOUYIN_HOME}


def is_douyin_media_host(url):
    low = (url or "").lower()
    markers = (
        "douyin", "douyinvod", "iesdouyin", "amemv", "bytecdn", "ixigua",
        "zjcdn", "snssdk", "bytevod", "ibyteimg", "ibytedtos",
        "douyinpic", "douyinstatic",
    )
    return any(m in low for m in markers)


# --- Normalisasi URL -------------------------------------------------------

def _first_url(text):
    m = _URL_RE.search(text or "")
    return m.group(0).rstrip("/") if m else (text or "").strip()


def extract_video_id(url):
    if not url:
        return None
    m = _ID_RE.search(url)
    return m.group(1) if m else None


def resolve_douyin_url(raw):
    """Ubah link pendek / teks share Douyin secara presisi tanpa menggantung."""
    url = _first_url(raw)
    if is_tiktok(url):
        return url

    # 1. Jika URL sudah punya video ID 18-19 digit
    vid = extract_video_id(url)
    if vid and is_douyin(url):
        return f"https://www.douyin.com/video/{vid}"

    # 2. Jika link pendek (v.douyin.com), ikuti redirect HEAD / GET stream secara kilat
    if "v.douyin.com" in url.lower():
        try:
            r = requests.head(url, headers={"User-Agent": MOBILE_UA}, allow_redirects=False, timeout=3, verify=False)
            loc = r.headers.get("Location") or ""
            if loc.startswith("sslocal://") or loc.startswith("snssdk") or loc.startswith("douyin://"):
                vid = extract_video_id(loc)
                if vid:
                    return f"https://www.douyin.com/video/{vid}"
                raise Exception("Tautan yang dimasukkan adalah link Chat/Toko Douyin, bukan link video. Silakan gunakan link video Douyin.")
            vid = extract_video_id(loc)
            if vid:
                return f"https://www.douyin.com/video/{vid}"
        except Exception as e:
            if "Chat/Toko" in str(e):
                raise e

        try:
            resp = requests.get(url, headers={"User-Agent": MOBILE_UA}, allow_redirects=True, stream=True, timeout=4, verify=False)
            vid = extract_video_id(resp.url)
            if vid:
                return f"https://www.douyin.com/video/{vid}"
        except Exception:
            pass

    return url


# --- JALUR UTAMA: halaman share iesdouyin ----------------------------------

def _extract_embedded_json(html):
    """Ambil JSON yang ditanam di halaman share (dua format yang dikenal)."""
    m = re.search(r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>", html, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(
        r'<script id="RENDER_DATA" type="application/json">([^<]+)</script>', html
    )
    if m:
        try:
            return json.loads(urllib.parse.unquote(m.group(1)))
        except json.JSONDecodeError:
            pass
    return None


def _find_item(obj, depth=0):
    """Cari item video pertama (dict yang punya item_list) di JSON bersarang."""
    if depth > 7:
        return None
    if isinstance(obj, dict):
        il = obj.get("item_list")
        if isinstance(il, list) and il and isinstance(il[0], dict):
            return il[0]
        for v in obj.values():
            r = _find_item(v, depth + 1)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_item(v, depth + 1)
            if r:
                return r
    return None


def fetch_tikwm_info(raw_url):
    """Jalur API Savetik/TikWM: ambil metadata & link tanpa watermark secara kilat."""
    for attempt in range(2):
        try:
            resp = requests.post(
                "https://www.tikwm.com/api/",
                data={"url": raw_url},
                timeout=3.5,
                verify=False,
                headers={"User-Agent": DESKTOP_UA},
            )
            if resp.status_code == 200:
                res = resp.json()
                if res.get("code") == 0:
                    data = res.get("data") or {}
                    play_url = data.get("play") or data.get("wmplay")
                    if play_url:
                        if play_url.startswith("//"):
                            play_url = "https:" + play_url
                        return {
                            "title": data.get("title") or "Video",
                            "thumbnail": data.get("cover"),
                            "duration": int(data.get("duration") or 60),
                            "direct_url": play_url,
                        }
        except Exception:
            if attempt == 0:
                time.sleep(0.5)
    return None


def share_page_info(video_id):
    """Ambil info video (judul, cover, durasi, link mp4) dari halaman share Douyin."""
    play_fallback = f"https://www.iesdouyin.com/aweme/v1/play/?video_id={video_id}&ratio=1080p&line=0"
    url = f"https://www.iesdouyin.com/share/video/{video_id}/"

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": MOBILE_UA, "Referer": DOUYIN_HOME},
            timeout=5,
            verify=False,
        )
        data = _extract_embedded_json(resp.text)
        if data:
            item = _find_item(data)
            if item:
                video = item.get("video") or {}
                play_addr = video.get("play_addr") or {}
                url_list = play_addr.get("url_list") or []

                play_url = None
                if url_list:
                    play_url = url_list[0].replace("playwm", "play")
                elif play_addr.get("uri"):
                    play_url = (
                        "https://www.iesdouyin.com/aweme/v1/play/"
                        f"?video_id={play_addr['uri']}&ratio=1080p&line=0"
                    )

                dur = video.get("duration") or item.get("duration") or 0
                duration = round(dur / 1000) if dur > 1000 else int(dur or 0)
                cover = (video.get("cover") or {}).get("url_list") or []

                return {
                    "title": item.get("desc") or f"Douyin Video ({video_id})",
                    "thumbnail": cover[0] if cover else None,
                    "duration": duration or 60,
                    "direct_url": play_url or play_fallback,
                }
    except Exception:
        pass

    return {
        "title": f"Douyin Video ({video_id})",
        "thumbnail": None,
        "duration": 60,
        "direct_url": play_fallback,
    }


def download_direct(url, dest_path, referer=None, stream_headers=None):
    """Unduh mp4 langsung dari CDN dengan kecepatan KILAT dan verifikasi Content-Type."""
    headers = {
        "User-Agent": DESKTOP_UA,
        "Accept": "*/*",
    }
    if stream_headers and isinstance(stream_headers, dict):
        headers.update(stream_headers)
    if referer:
        headers["Referer"] = referer
    elif "Referer" not in headers:
        low = (url or "").lower()
        if "tiktok" in low:
            headers["Referer"] = "https://www.tiktok.com/"
        else:
            headers["Referer"] = DOUYIN_HOME

    with requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=30, verify=False) as r:
        r.raise_for_status()
        ct = (r.headers.get("Content-Type") or "").lower()
        if "text/html" in ct or "application/json" in ct:
            raise Exception(f"CDN mengembalikan respon non-video ({ct}).")

        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    if not os.path.exists(dest_path) or os.path.getsize(dest_path) < 1024:
        raise Exception("File video dari CDN kosong / terlalu kecil.")


# --- CADANGAN: yt-dlp dengan cookie (dipertahankan sebagai fallback) --------

def real_cookie_file():
    candidates = [
        os.environ.get("DOUYIN_COOKIES"),
        os.path.join(os.getcwd(), "cookies_douyin.txt"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies_douyin.txt"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def browser_cookiespec():
    b = os.environ.get("DOUYIN_BROWSER", "").strip().lower()
    return (b,) if b in _VALID_BROWSERS else None


def get_official_ttwid():
    """Dapatkan cookie ttwid resmi dari ByteDance endpoint."""
    try:
        url = "https://ttwid.bytedance.com/ttwid/union/register/"
        payload = {
            "region": "cn",
            "aid": 6383,
            "needFp": "true",
            "fp": f"verify_{uuid.uuid4().hex}",
            "service": "www.douyin.com",
            "client_type": "web",
        }
        r = requests.post(url, json=payload, headers={"User-Agent": DESKTOP_UA}, timeout=4, verify=False)
        ttwid = r.cookies.get("ttwid")
        if ttwid:
            return ttwid
    except Exception:
        pass
    return None


def fallback_cookiefile():
    os.makedirs("temp_media", exist_ok=True)
    cookie_path = os.path.join(os.getcwd(), "temp_media", f"cookie_{uuid.uuid4().hex}.txt")
    expires = int(time.time()) + 365 * 24 * 3600
    s_v_web_id = f"verify_{uuid.uuid4().hex}"
    ttwid = get_official_ttwid() or uuid.uuid4().hex
    domains = [
        ".douyin.com", "www.douyin.com", "v.douyin.com", "douyin.com",
        ".iesdouyin.com", "www.iesdouyin.com",
        ".tiktok.com", "www.tiktok.com", "vm.tiktok.com", "vt.tiktok.com",
    ]
    lines = ["# Netscape HTTP Cookie File", "# Generated. Do not edit.", ""]
    for d in domains:
        inc_sub = "TRUE" if d.startswith(".") else "FALSE"
        lines.append(f"{d}\t{inc_sub}\t/\tFALSE\t{expires}\ts_v_web_id\t{s_v_web_id}")
        lines.append(f"{d}\t{inc_sub}\t/\tFALSE\t{expires}\tttwid\t{ttwid}")
    with open(cookie_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return cookie_path


def apply_douyin_auth(ydl_opts):
    """Set header + cookie untuk jalur cadangan yt-dlp.
    Return path cookie sementara yang perlu dihapus, atau None."""
    ydl_opts["http_headers"] = douyin_headers()

    real = real_cookie_file()
    if real:
        ydl_opts["cookiefile"] = real
        return None

    spec = browser_cookiespec()
    if spec:
        ydl_opts["cookiesfrombrowser"] = spec
        return None

    fake = fallback_cookiefile()
    ydl_opts["cookiefile"] = fake
    return fake


def clean_error(msg):
    """Buang kode warna ANSI dan rapikan pesan supaya terbaca di layar."""
    clean = _ANSI_RE.sub("", msg or "").strip()
    if any(s in clean for s in ("InvalidSchema", "sslocal://", "No connection adapters", "Chat/Toko")):
        return "Tautan yang dimasukkan adalah link Chat/Toko Douyin, bukan link video. Silakan gunakan link postingan video Douyin."
    if "Fresh cookies are needed" in clean:
        return "Video Douyin ini diproteksi oleh platform. Silakan gunakan link video Douyin publik lainnya."
    return clean