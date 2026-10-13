"""Choose export sources independently from the browser preview format."""

def select_sources(info, resolution="best", output_format="mp4", max_height=1080):
    formats = info.get("_formats") or []
    audio = [f for f in formats if f.get("url") and f.get("acodec") not in (None, "none")]
    audio.sort(key=lambda f: (f.get("vcodec") in (None, "none"), float(f.get("abr") or f.get("tbr") or 0)))
    fallback_headers = info.get("stream_headers") or {}

    def source(url, headers=None, format_id=None):
        return {"url": url, "headers": headers or fallback_headers, "format_id": format_id}

    def from_format(fmt):
        return source(fmt["url"], fmt.get("http_headers"), fmt.get("format_id"))

    if output_format == "mp3":
        if audio:
            return from_format(audio[-1]), None
        return source(info.get("audio_url") or info["direct_url"], info.get("audio_headers")), None

    requested = int(resolution) if resolution != "best" else 0
    limit = min(requested, max_height) if requested and max_height else requested or max_height
    videos = [f for f in formats if f.get("url") and f.get("vcodec") not in (None, "none")]
    eligible = [f for f in videos if not limit or int(f.get("height") or 0) <= limit]
    if not eligible and videos:
        # All sources exceed the requested height: download the smallest and downscale.
        lowest = min(int(f.get("height") or 0) for f in videos)
        eligible = [f for f in videos if int(f.get("height") or 0) == lowest]
    if eligible:
        chosen = max(eligible, key=lambda f: (int(f.get("height") or 0), f.get("ext") == "mp4", float(f.get("tbr") or 0)))
        extra = None
        if chosen.get("acodec") in (None, "none"):
            if audio:
                extra = from_format(audio[-1])
            elif info.get("audio_url"):
                extra = source(info["audio_url"], info.get("audio_headers"))
        return from_format(chosen), extra
    return source(info["direct_url"]), source(info["audio_url"], info.get("audio_headers")) if info.get("audio_url") else None
