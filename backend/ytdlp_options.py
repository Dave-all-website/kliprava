"""Shared extraction/download settings, with request-local cookie files."""
import base64
import os
import random
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

from config import settings


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
    proxy = os.environ.get(f"{platform}_PROXY", "").strip()
    if proxy:
        options["proxy"] = proxy
    elif settings.PROXIES:
        options["proxy"] = random.choice(settings.PROXIES)

    cookie_text = os.environ.get(f"{platform}_COOKIES", "").strip()
    temporary = None
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
        else:
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
