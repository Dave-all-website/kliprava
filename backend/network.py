"""HTTP streaming with public-address validation and DNS-pinned connections."""
import ipaddress
import socket
from urllib.parse import urlsplit, urljoin

import urllib3


class UnsafeURL(ValueError):
    pass


def validate_media_page(url):
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    domains = ("youtube.com", "youtu.be", "tiktok.com", "tikwm.com", "douyin.com", "iesdouyin.com",
               "instagram.com", "instagr.am", "facebook.com", "fb.com", "fb.watch", "x.com", "twitter.com",
               "t.co", "xiaohongshu.com", "xhslink.com")
    if not any(host == domain or host.endswith("." + domain) for domain in domains):
        raise UnsafeURL("Gunakan tautan dari salah satu platform media sosial yang didukung.")
    resolve_public_url(url)
    return url


def resolve_public_url(url):
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username is not None or parts.password is not None:
            raise UnsafeURL("URL harus berupa HTTP(S) tanpa kredensial.")
        port = parts.port or (443 if parts.scheme == "https" else 80)
        if port not in (80, 443):
            raise UnsafeURL("Port URL tidak diizinkan.")
        addresses = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
        ips = list(dict.fromkeys(row[4][0] for row in addresses))
        if not ips:
            raise UnsafeURL("Alamat server tidak ditemukan.")
        for ip in ips:
            addr = ipaddress.ip_address(ip)
            if not addr.is_global or addr.is_multicast or (getattr(addr, "ipv4_mapped", None) and not addr.ipv4_mapped.is_global):
                raise UnsafeURL("URL menuju jaringan privat atau lokal tidak diizinkan.")
        return parts, port, ips[0]
    except (ValueError, socket.gaierror) as exc:
        raise UnsafeURL(str(exc)) from exc


def open_public_stream(url, headers=None, timeout=(6, 60)):
    # Connecting to the validated IP avoids a second DNS lookup (DNS rebinding).
    request_headers = {k: v for k, v in (headers or {}).items() if k.lower() not in ("host", "connection", "proxy-authorization")}
    for _ in range(6):
        parts, port, ip = resolve_public_url(url)
        pool_class = urllib3.HTTPSConnectionPool if parts.scheme == "https" else urllib3.HTTPConnectionPool
        tls = {"server_hostname": parts.hostname, "assert_hostname": parts.hostname, "cert_reqs": "CERT_REQUIRED"} if parts.scheme == "https" else {}
        pool = pool_class(ip, port=port, maxsize=1, **tls)
        host = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
        request_headers["Host"] = host + (f":{parts.port}" if parts.port else "")
        target = (parts.path or "/") + ("?" + parts.query if parts.query else "")
        try:
            response = pool.request("GET", target, headers=request_headers, preload_content=False,
                                    redirect=False, retries=False, timeout=urllib3.Timeout(connect=timeout[0], read=timeout[1]))
        except Exception:
            pool.close()
            raise
        if response.status not in (301, 302, 303, 307, 308):
            response.media_url = url
            return response, pool
        location = response.headers.get("Location")
        response.close()
        pool.close()
        if not location:
            raise UnsafeURL("Redirect tidak memiliki URL tujuan.")
        next_url = urljoin(url, location)
        if urlsplit(next_url).netloc != parts.netloc or urlsplit(next_url).scheme != parts.scheme:
            request_headers = {k: v for k, v in request_headers.items() if k.lower() not in ("cookie", "authorization", "host")}
        url = next_url
    raise UnsafeURL("Terlalu banyak redirect.")
