"""Parse the requested video from Douyin's public share-page state."""
import json
import re


def parse_share_video(html, video_id, canonical_url, headers):
    marker = re.search(r"window\._ROUTER_DATA\s*=\s*", html)
    if not marker:
        return None
    try:
        state, _ = json.JSONDecoder().raw_decode(html[marker.end():])
    except ValueError:
        return None
    if not isinstance(state, dict):
        return None

    def find_item(value):
        if isinstance(value, dict):
            if str(value.get("aweme_id") or value.get("id") or "") == video_id and isinstance(value.get("video"), dict):
                return value
            for child in value.values():
                found = find_item(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = find_item(child)
                if found:
                    return found
        return None

    item = find_item(state.get("loaderData") or state)
    if not item:
        return None
    video = item["video"]
    formats = []
    addresses = [video.get("play_addr") or {}]
    addresses.extend(rate.get("play_addr") or {} for rate in video.get("bit_rate") or [] if isinstance(rate, dict))
    for address in addresses:
        urls = list(dict.fromkeys(u for u in address.get("url_list") or [] if isinstance(u, str) and u.startswith(("http://", "https://"))))
        if not urls:
            continue
        formats.append({
            "url": urls[0], "backup_urls": urls[1:], "ext": "mp4",
            "height": address.get("height") or video.get("height"),
            "width": address.get("width") or video.get("width"),
            "vcodec": "h264", "acodec": "aac", "http_headers": headers,
        })
    if not formats:
        return None
    covers = (video.get("cover") or {}).get("url_list") or []
    duration_ms = video.get("duration") or item.get("duration") or 0
    return {
        "title": item.get("desc") or f"Douyin Video ({video_id})",
        "thumbnail": covers[0] if covers else None,
        "duration": float(duration_ms) / 1000 if duration_ms else 0,
        "direct_url": formats[0]["url"], "canonical_url": canonical_url,
        "_formats": formats, "stream_headers": headers,
    }
