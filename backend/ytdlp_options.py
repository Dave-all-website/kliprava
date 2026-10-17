"""Shared extraction/download settings, with request-local cookie files."""
import base64
import os
import random
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

from config import settings


_youtube_pot_slot = threading.BoundedSemaphore(1)


def platform_name(url):
    host = (urlsplit(url).hostname or "").lower()
    for name, domains in {
        "YOUTUBE": ("youtube.com", "youtu.be"),
        "TIKTOK": ("tiktok.com", "tt.site", "tikwm.com"),
        "REDNOTE": ("xiaohongshu.com", "xhslink.com", "rednote.com"),
        "DOUYIN": ("douyin.com", "iesdouyin.com"),
    }.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            return name
    return "MEDIA"


@contextmanager
def ytdlp_options(url, **overrides):
    platform = platform_name(url)
    options = {
        "quiet": True,
        "noplaylist": True,
        "socket_timeout": 15,
        "retries": 1,
        "extractor_retries": 1,
        "js_runtimes": {"node": {}, "deno": {}},
    }
    if platform == "YOUTUBE":
        ip_family = os.environ.get("YOUTUBE_IP_FAMILY", "").strip()
        if ip_family not in ("", "4", "6"):
            raise ValueError("YOUTUBE_IP_FAMILY harus kosong, 4, atau 6.")
        if ip_family:
            # Also passed to the PO Token provider so attestation and extraction
            # use the same network family. Never applies to other platforms.
            options["source_address"] = "::" if ip_family == "6" else "0.0.0.0"
    # An explicitly configured provider enables anonymous YouTube extraction.
    # Tokens are minted locally; no account cookie jar is imported in this mode.
    pot_home = os.environ.get("YOUTUBE_POT_SERVER_HOME", "").strip() if platform == "YOUTUBE" else ""
    if pot_home:
        if not (Path(pot_home) / "build" / "generate_once.js").is_file():
            raise ValueError("Penyedia PO Token YouTube belum terpasang dengan benar di server.")
        options["extractor_args"] = {
            "youtube": {"player_client": ["mweb"], "fetch_pot": ["always"]},
            "youtubepot-bgutilscript": {"server_home": [pot_home]},
        }
    proxy = os.environ.get(f"{platform}_PROXY", "").strip()
    if proxy:
        options["proxy"] = proxy
    elif settings.PROXIES:
        options["proxy"] = random.choice(settings.PROXIES)

    cookie_text = "" if pot_home else os.environ.get(f"{platform}_COOKIES", "").strip()
    temporary = None
    # The script provider shares its cache; serialize it and bound CPU usage.
    if pot_home and not _youtube_pot_slot.acquire(timeout=3):
        raise ValueError("YouTube sedang memproses video lain. Coba lagi sebentar.")
    try:
        if cookie_text:
            if "\t" not in cookie_text and not cookie_text.startswith("#"):
                try:
                    cookie_text = base64.b64decode(cookie_text, validate=True).decode("utf-8")
                except (ValueError, UnicodeError) as exc:
                    raise ValueError(f"{platform}_COOKIES harus berformat Netscape atau Base64 Netscape.") from exc
            if "\t" not in cookie_text:
                raise ValueError(f"{platform}_COOKIES tidak memuat cookie berformat Netscape.")
            if not cookie_text.startswith("# Netscape") and not cookie_text.startswith("# HTTP Cookie File"):
                cookie_text = "# Netscape HTTP Cookie File\n" + cookie_text
            # Never share a writable cookie jar across concurrent requests/platforms.
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="cookies-", suffix=".txt", delete=False) as handle:
                temporary = handle.name
                handle.write(cookie_text.rstrip() + "\n")
            options["cookiefile"] = temporary
        elif not pot_home:
            backend = Path(__file__).resolve().parent
            candidates = [backend / f"cookies_{platform.lower()}.txt", backend / "cookies.txt", backend.parent / "cookies.txt"]
            for path in candidates:
                if path.is_file():
                    options["cookiefile"] = str(path)
                    break
        options.update(overrides)
        yield options
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)
        if pot_home:
            _youtube_pot_slot.release()
