import base64
import json
import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import converter
import network
import scraper
from media_sources import select_sources
from ytdlp_options import ytdlp_options


def test_tt_site_share_link_is_allowed_and_dispatched(monkeypatch):
    monkeypatch.setattr(network.socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    url = "https://www.tt.site/t/ZSgeFKy6c/"
    network.validate_media_page(url)
    monkeypatch.setattr(scraper, "resolve_canonical_url", lambda u: u)
    extract = Mock(return_value={"direct_url": "https://cdn.example/video.mp4"})
    monkeypatch.setattr(scraper, "fetch_tikwm_info", extract)
    assert scraper.extract_media_info(f"[{url}]({url})")["direct_url"].endswith("video.mp4")
    assert extract.call_count == 1
    extract.assert_called_once_with(url)
    with pytest.raises(network.UnsafeURL):
        network.validate_media_page("https://tt.site.evil.example/video")


def test_tikwm_uses_returned_media_url_not_guessed_id(monkeypatch):
    monkeypatch.setattr(scraper, "resolve_canonical_url", lambda u: u)
    response = Mock(status_code=200)
    response.json.return_value = {"code": 0, "data": {"id": "123", "hdplay": "/video/actual.mp4?token=abc", "duration": 118}}
    monkeypatch.setattr(scraper.requests, "post", Mock(return_value=response))
    info = scraper.fetch_tikwm_info("https://www.tiktok.com/@user/video/123")
    assert info["direct_url"] == "https://www.tikwm.com/video/actual.mp4?token=abc"


def test_rednote_selects_requested_note_and_preserves_signed_url(monkeypatch):
    note_id = "6acb1275000000001a028eba"
    url = f"https://www.xiaohongshu.com/discovery/item/{note_id}?xsec_token=test"
    note = {"title": "undefined title", "video": {"media": {"stream": {"h264": [
        {"masterUrl": "https://cdn.example/main.mp4", "backupUrls": ["https://cdn.example/backup.mp4"], "duration": 12500, "height": 721, "width": 405}
    ]}}}}
    state = {"note": {"noteDetailMap": {"recommendation": {"note": {"title": "Wrong video"}}, note_id: {"note": note}}}}
    html = "<script>window.__INITIAL_STATE__=" + json.dumps(state) + ";</script>"
    monkeypatch.setattr(scraper.requests, "get", Mock(return_value=Mock(status_code=200, text=html)))
    info = scraper._extract_rednote_html(url)
    assert info["title"] == "undefined title"
    assert info["canonical_url"] == url
    assert info["duration"] == 12.5
    primary, _ = select_sources(info)
    assert primary["backup_urls"] == ["https://cdn.example/backup.mp4"]


def test_rednote_does_not_export_a_recommendation(monkeypatch):
    html = '<script>window.__INITIAL_STATE__={"note":{"noteDetailMap":{"other":{"note":{}}}}};</script>'
    monkeypatch.setattr(scraper.requests, "get", Mock(return_value=Mock(status_code=200, text=html)))
    assert scraper._extract_rednote_html("https://www.xiaohongshu.com/explore/6acb1275000000001a028eba") is None


def test_download_tries_backup_cdn_before_extracting_again(monkeypatch, tmp_path):
    def open_stream(url, *args, **kwargs):
        response = Mock(status=403 if "main" in url else 200, headers={"Content-Type": "video/mp4"})
        response.stream.return_value = [b"v" * 2048]
        return response, Mock()
    monkeypatch.setattr(converter, "open_public_stream", open_stream)
    target = tmp_path / "source.mp4"
    converter.download_raw_media("https://cdn.example/main.mp4", str(target), backup_urls=["https://cdn.example/backup.mp4"])
    assert target.stat().st_size == 2048


def test_cookies_decoded_isolated_and_removed(monkeypatch):
    jar = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\ttest\tvalue\n"
    monkeypatch.setenv("YOUTUBE_COOKIES", base64.b64encode(jar.encode()).decode())
    monkeypatch.setenv("YOUTUBE_PROXY", "http://proxy.example:8080")
    monkeypatch.delenv("TIKTOK_COOKIES", raising=False)
    monkeypatch.delenv("TIKTOK_PROXY", raising=False)
    with ytdlp_options("https://youtu.be/abc") as first:
        path = Path(first["cookiefile"])
        assert path.read_text() == jar
        assert "extractor_args" not in first
        with ytdlp_options("https://youtu.be/abc") as second:
            assert second["cookiefile"] != first["cookiefile"]
        with ytdlp_options("https://www.tt.site/t/example/") as other:
            assert other.get("proxy") != first["proxy"]
            assert other.get("cookiefile") != first["cookiefile"]
    assert not path.exists()
    assert not Path(second["cookiefile"]).exists()


def test_youtube_bot_error_is_not_retried_through_six_clients(monkeypatch):
    import yt_dlp
    factory = Mock()
    factory.return_value.__enter__ = Mock(return_value=Mock(extract_info=Mock(side_effect=Exception("Sign in to confirm you're not a bot"))))
    factory.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(yt_dlp, "YoutubeDL", factory)
    with pytest.raises(ValueError, match="YouTube meminta verifikasi"):
        scraper._extract_with_ytdlp("https://youtu.be/abc")
    assert factory.call_count == 1


@pytest.mark.parametrize("max_height", [1080, 0])
def test_odd_size_video_converts_to_playable_mp4(monkeypatch, tmp_path, max_height):
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    run = subprocess.run
    source, target = tmp_path / "odd.mkv", tmp_path / "result.mp4"
    run([ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc=size=321x241:rate=25", "-t", "1", "-c:v", "ffv1", str(source)], check=True, capture_output=True)
    monkeypatch.setattr(converter.settings, "MAX_VIDEO_HEIGHT", max_height)
    monkeypatch.setattr(converter.subprocess, "run", lambda cmd, **kw: run([ffmpeg, *cmd[1:]], **kw))
    converter.convert_media(str(source), str(target), end_time=0.5)
    run([ffmpeg, "-v", "error", "-i", str(target), "-f", "null", "-"], check=True, capture_output=True)
