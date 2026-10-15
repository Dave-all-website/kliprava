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
    return parse_video_data(state, video_id, canonical_url, headers)


def parse_video_data(state, video_id, canonical_url, headers):
    """Accept share-page state or the browser's video-detail response."""
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
    # DASH entries can be video-only; prefer complete MP4 sources with audio.
    rates = [r for r in video.get("bit_rate") or [] if isinstance(r, dict) and r.get("format", "mp4") == "mp4"]
    addresses = [(r.get("play_addr") or {}, "h265" if r.get("is_h265") else "h264", r.get("bit_rate")) for r in rates]
    if not rates:
        addresses = [(video.get("play_addr_h264") or video.get("play_addr") or {}, "h264", None)]
    for address, codec, bitrate in addresses:
        urls = list(dict.fromkeys(u for u in address.get("url_list") or [] if isinstance(u, str) and u.startswith(("http://", "https://"))))
        if not urls:
            continue
        formats.append({
            "url": urls[0], "backup_urls": urls[1:], "ext": "mp4",
            "height": address.get("height") or video.get("height"),
            "width": address.get("width") or video.get("width"),
            "vcodec": codec, "acodec": "aac", "http_headers": headers,
            "tbr": float(bitrate or 0) / 1000,
        })
    if not formats:
        return None
    covers = (video.get("cover") or {}).get("url_list") or []
    duration_ms = video.get("duration") or item.get("duration") or 0
    preview = next((f for f in formats if f["vcodec"] == "h264"), formats[0])
    return {
        "title": item.get("desc") or f"Douyin Video ({video_id})",
        "thumbnail": covers[0] if covers else None,
        "duration": float(duration_ms) / 1000 if duration_ms else 0,
        "direct_url": preview["url"], "canonical_url": canonical_url,
        "_formats": formats, "stream_headers": headers,
    }
