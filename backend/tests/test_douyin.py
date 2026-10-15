import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scraper
from douyin import parse_share_video
from douyin import parse_video_data
import douyin_browser

VIDEO_ID = "7675505205047348543"
SHARE_URL = f"https://www.iesdouyin.com/share/video/{VIDEO_ID}/?share_sign=test&from_ssr=1"


def state_html(items):
    data = {"loaderData": {"video_(id)/page": {"videoInfoRes": {"item_list": items}}}}
    return "<script>window._ROUTER_DATA = " + json.dumps(data) + ";</script>"


def test_nested_share_video_identity_urls_and_subsecond_duration():
    item = {"aweme_id": VIDEO_ID, "desc": "requested", "video": {
        "duration": 700, "width": 720, "height": 1280,
        "play_addr": {"url_list": ["https://cdn.example/playwm?v=1", "https://cdn.example/backup?v=1"]},
    }}
    wrong = {"aweme_id": "123", "desc": "recommendation", "video": {"play_addr": {"url_list": ["https://cdn.example/wrong"]}}}
    info = parse_share_video(state_html([wrong, item]), VIDEO_ID, SHARE_URL, {})
    assert info["title"] == "requested"
    assert info["duration"] == 0.7
    assert info["canonical_url"] == SHARE_URL
    assert info["direct_url"] == "https://cdn.example/playwm?v=1"
    assert info["_formats"][0]["backup_urls"] == ["https://cdn.example/backup?v=1"]
    assert info["_formats"][0]["height"] == 1280


@pytest.mark.parametrize("html", ["<html>verification</html>", "window._ROUTER_DATA = invalid", "window._ROUTER_DATA = []", state_html([])])
def test_page_without_video_is_not_success(html):
    assert parse_share_video(html, VIDEO_ID, SHARE_URL, {}) is None


def test_share_request_preserves_parameters_and_closes_connections(monkeypatch):
    monkeypatch.setattr(scraper, "validate_media_page", lambda url: url)
    response = Mock(status=200)
    response.read.return_value = state_html([]).encode()
    pool = Mock()
    request = Mock(return_value=(response, pool))
    monkeypatch.setattr(scraper, "open_public_stream", request)
    assert scraper._extract_douyin_share_page(VIDEO_ID, SHARE_URL) is None
    assert request.call_args.args[0] == SHARE_URL
    response.close.assert_called_once()
    pool.close.assert_called_once()


def test_dispatch_uses_anonymous_browser_and_never_cookie_extractor(monkeypatch):
    monkeypatch.setattr(scraper, "validate_media_page", lambda url: url)
    monkeypatch.setattr(scraper, "resolve_canonical_url", lambda url: SHARE_URL)
    share = Mock(return_value=None)
    browser = Mock(return_value={"direct_url": "https://cdn.example/video.mp4", "_formats": []})
    ytdlp = Mock(side_effect=AssertionError("Cookie-based extractor must not run"))
    monkeypatch.setattr(scraper, "_extract_douyin_share_page", share)
    monkeypatch.setattr(douyin_browser, "extract_browser_video", browser)
    monkeypatch.setattr(scraper, "_extract_with_ytdlp", ytdlp)
    monkeypatch.setenv("DOUYIN_COOKIES", "must not be loaded")
    info = scraper.extract_media_info("https://v.douyin.com/Q4d8B5M0l2I/")
    share.assert_called_once_with(VIDEO_ID, SHARE_URL)
    browser.assert_called_once_with(VIDEO_ID, scraper.DESKTOP_UA)
    ytdlp.assert_not_called()
    assert info["direct_url"] == "https://cdn.example/video.mp4"


def test_browser_detail_selects_complete_mp4_not_silent_dash():
    detail = {"aweme_detail": {"aweme_id": VIDEO_ID, "video": {"duration": 1501823, "bit_rate": [
        {"format": "dash", "play_addr": {"url_list": ["https://cdn.example/silent"]}},
        {"format": "mp4", "is_h265": 1, "bit_rate": 200000, "play_addr": {"url_list": ["https://cdn.example/hevc"], "height": 540}},
        {"format": "mp4", "is_h265": 0, "play_addr": {"url_list": ["https://cdn.example/avc"], "height": 1080}},
    ]}}}
    info = parse_video_data(detail, VIDEO_ID, SHARE_URL, {})
    assert info["duration"] == 1501.823
    assert info["direct_url"] == "https://cdn.example/avc"
    assert len(info["_formats"]) == 2
    assert info["_formats"][0]["vcodec"] == "h265"
    assert parse_video_data(detail, "123", SHARE_URL, {}) is None


def test_douyin_download_failure_never_imports_login_cookies(monkeypatch, tmp_path):
    import converter
    import yt_dlp
    response = Mock(status=403)
    monkeypatch.setattr(converter, "open_public_stream", Mock(return_value=(response, Mock())))
    factory = Mock(side_effect=AssertionError("Cookie-based download must not run"))
    monkeypatch.setattr(yt_dlp, "YoutubeDL", factory)
    with pytest.raises(Exception, match="Gagal mengunduh"):
        converter.download_raw_media("https://cdn.example/video", str(tmp_path / "raw.mp4"), original_url=SHARE_URL, format_id="best")
    factory.assert_not_called()


def test_unresolved_share_link_is_not_reported_as_geo_restriction(monkeypatch):
    monkeypatch.setattr(scraper, "validate_media_page", lambda url: url)
    monkeypatch.setattr(scraper, "resolve_canonical_url", lambda url: url)
    with pytest.raises(ValueError, match="belum dapat dibuka"):
        scraper.extract_media_info("https://v.douyin.com/example/")
