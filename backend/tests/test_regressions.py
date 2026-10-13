import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import converter
import main
import network
from media_sources import select_sources


def dns(ip):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "::ffff:127.0.0.1", "fc00::1", "224.0.0.1"])
def test_private_and_special_addresses_rejected(monkeypatch, ip):
    monkeypatch.setattr(network.socket, "getaddrinfo", lambda *a, **k: dns(ip))
    with pytest.raises(network.UnsafeURL):
        network.resolve_public_url("https://cdn.example/video")


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/v", "https://user:pass@example.com/v", "http://example.com:8080/v"])
def test_unsafe_url_forms_rejected(url):
    with pytest.raises(network.UnsafeURL):
        network.resolve_public_url(url)


def test_connection_is_pinned_and_preserves_tls_host(monkeypatch):
    lookup = Mock(return_value=dns("93.184.216.34"))
    monkeypatch.setattr(network.socket, "getaddrinfo", lookup)
    response = Mock(status=200)
    pool = Mock()
    pool.request.return_value = response
    factory = Mock(return_value=pool)
    monkeypatch.setattr(network.urllib3, "HTTPSConnectionPool", factory)
    network.open_public_stream("https://cdn.example/video?token=x")
    assert lookup.call_count == 1
    assert factory.call_args.args == ("93.184.216.34",)
    assert factory.call_args.kwargs["server_hostname"] == "cdn.example"
    assert factory.call_args.kwargs["assert_hostname"] == "cdn.example"
    assert pool.request.call_args.args[1] == "/video?token=x"
    assert pool.request.call_args.kwargs["headers"]["Host"] == "cdn.example"


def test_redirect_to_internal_host_is_rejected(monkeypatch):
    monkeypatch.setattr(network.socket, "getaddrinfo", lambda host, *a, **k: dns("127.0.0.1" if host == "internal" else "93.184.216.34"))
    response = Mock(status=302, headers={"Location": "http://internal/secret"})
    pool = Mock()
    pool.request.return_value = response
    factory = Mock(return_value=pool)
    monkeypatch.setattr(network.urllib3, "HTTPSConnectionPool", factory)
    with pytest.raises(network.UnsafeURL):
        network.open_public_stream("https://cdn.example/video")
    assert factory.call_count == 1
    response.close.assert_called_once()
    pool.close.assert_called_once()


def test_mixed_public_private_dns_rejected(monkeypatch):
    monkeypatch.setattr(network.socket, "getaddrinfo", lambda *a, **k: dns("93.184.216.34") + dns("10.0.0.1"))
    with pytest.raises(network.UnsafeURL):
        network.resolve_public_url("https://cdn.example/video")


def test_media_page_domain_cannot_be_spoofed():
    with pytest.raises(network.UnsafeURL):
        network.validate_media_page("https://youtube.com.attacker.example/video")


def info_with_formats():
    return {"direct_url": "https://cdn.example/360.mp4", "_formats": [
        {"format_id": "18", "url": "https://cdn.example/360.mp4", "height": 360, "ext": "mp4", "vcodec": "h264", "acodec": "aac"},
        {"format_id": "137", "url": "https://cdn.example/1080.mp4", "height": 1080, "ext": "mp4", "vcodec": "h264", "acodec": "none"},
        {"format_id": "140", "url": "https://cdn.example/audio.m4a", "vcodec": "none", "acodec": "aac", "abr": 128},
    ]}


def test_high_resolution_uses_video_plus_audio_instead_of_low_preview():
    video, audio = select_sources(info_with_formats(), "1080")
    assert video["url"].endswith("1080.mp4")
    assert audio["url"].endswith("audio.m4a")
    video, audio = select_sources(info_with_formats(), "360")
    assert video["url"].endswith("360.mp4")
    assert audio is None


def test_resolution_cap_is_respected():
    video, _ = select_sources(info_with_formats(), "1080", max_height=480)
    assert video["url"].endswith("360.mp4")


def test_mp3_downloads_audio_source_only():
    primary, extra = select_sources(info_with_formats(), "best", "mp3")
    assert primary["url"].endswith("audio.m4a")
    assert extra is None


def test_fallback_separate_audio_is_not_lost():
    info = {"direct_url": "https://cdn.example/video", "audio_url": "https://cdn.example/audio"}
    video, audio = select_sources(info)
    assert audio["url"] == info["audio_url"]
    primary, _ = select_sources(info, output_format="mp3")
    assert primary["url"] == info["audio_url"]


def upstream(status, headers=None):
    response = Mock(status=status, headers={"Content-Type": "video/mp4", **(headers or {})})
    response.stream.return_value = iter([b"video-bytes"])
    return response, Mock()


def test_range_does_not_leak_to_next_request(monkeypatch):
    calls = []
    url = "https://cdn.example/video"
    main._remember_stream_headers(url, {"User-Agent": "test"})
    def open_stream(url, headers):
        calls.append(dict(headers))
        return upstream(206, {"Content-Range": "bytes 10-20/100"}) if "Range" in headers else upstream(200)
    monkeypatch.setattr(main, "open_public_stream", open_stream)
    with TestClient(main.app) as client:
        partial = client.get("/api/stream", params={"url": url}, headers={"Range": "bytes=10-20"})
        full = client.get("/api/stream", params={"url": url})
    assert partial.status_code == 206
    assert partial.headers["content-range"] == "bytes 10-20/100"
    assert full.status_code == 200
    assert "Range" not in calls[1]


def test_upstream_ignoring_range_remains_200(monkeypatch):
    monkeypatch.setattr(main, "open_public_stream", lambda *a: upstream(200, {"Content-Length": "11"}))
    with TestClient(main.app) as client:
        response = client.get("/api/stream", params={"url": "https://cdn.example/video"}, headers={"Range": "bytes=5-10"})
    assert response.status_code == 200
    assert "content-range" not in response.headers


def test_stream_rejection_is_client_error(monkeypatch):
    def reject(*args):
        raise network.UnsafeURL("Private address")
    monkeypatch.setattr(main, "open_public_stream", reject)
    with TestClient(main.app) as client:
        assert client.get("/api/stream", params={"url": "http://127.0.0.1"}).status_code == 400


@pytest.mark.parametrize("fields", [{"start_time": -1}, {"start_time": 5, "end_time": 2}, {"format": "../../bad"}, {"resolution": "oops"}])
def test_invalid_conversion_rejected(fields):
    with TestClient(main.app) as client:
        assert client.post("/api/process", json={"url": "https://youtube.com/watch?v=test", **fields}).status_code == 422


def test_queue_without_storage_fails_before_enqueuing(monkeypatch):
    monkeypatch.setattr(main.storage_manager, "is_configured", lambda: False)
    send = Mock()
    monkeypatch.setattr(main.celery_app, "send_task", send)
    with TestClient(main.app) as client:
        assert client.post("/api/convert", json={"url": "https://youtu.be/test"}).status_code == 503
    send.assert_not_called()


@pytest.mark.parametrize("available", [True, False])
def test_health_checks_ffmpeg_without_requiring_optional_queue(monkeypatch, available):
    import redis
    monkeypatch.setattr(main.shutil, "which", lambda _: "ffmpeg" if available else None)
    monkeypatch.setattr(redis.Redis, "from_url", Mock(side_effect=ConnectionError("Redis offline")))
    with TestClient(main.app) as client:
        response = client.get("/api/health")
    assert response.status_code == (200 if available else 503)
    assert response.json()["ffmpeg_available"] is available
    assert response.json()["queue_available"] is False


def test_failed_audio_download_cleans_partial_sources(monkeypatch, tmp_path):
    raw = tmp_path / "raw.tmp"
    audio = tmp_path / "audio.tmp"
    def download(url, target, *args):
        Path(target).write_bytes(b"partial")
        if target == str(audio):
            raise RuntimeError("Audio download failed")
    monkeypatch.setattr(converter, "download_raw_media", download)
    with pytest.raises(RuntimeError):
        converter.download_media_sources(info_with_formats(), str(raw), str(audio), "https://youtube.com/watch?v=test")
    assert not raw.exists()
    assert not audio.exists()


def test_process_passes_separate_audio_and_cleans_all_files(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "TEMP_DIR", str(tmp_path))
    monkeypatch.setattr(main, "extract_media_info", lambda _: {"direct_url": "video", "audio_url": "audio"})
    def download(info, raw, audio, *args):
        Path(raw).write_bytes(b"raw")
        Path(audio).write_bytes(b"audio")
        return audio
    def convert(**kwargs):
        assert Path(kwargs["audio_path"]).read_bytes() == b"audio"
        Path(kwargs["output_path"]).write_bytes(b"finished")
    monkeypatch.setattr(main, "download_media_sources", download)
    monkeypatch.setattr(main, "convert_media", convert)
    with TestClient(main.app) as client:
        response = client.post("/api/process", json={"url": "https://youtu.be/test"})
    assert response.status_code == 200
    assert response.content == b"finished"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("output_format", ["mp4", "mp3"])
def test_real_ffmpeg_trims_separate_audio(monkeypatch, tmp_path, output_format):
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    run = subprocess.run
    video = tmp_path / "video.mp4"
    audio = tmp_path / "audio.wav"
    output = tmp_path / f"output.{output_format}"
    run([ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc2=size=256x144:rate=25", "-t", "2", "-an", "-c:v", "libx264", str(video)], check=True, capture_output=True)
    run([ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-t", "2", str(audio)], check=True, capture_output=True)
    def run_converter(cmd, **kwargs):
        return run([ffmpeg, *cmd[1:]], **kwargs)
    monkeypatch.setattr(converter.subprocess, "run", run_converter)
    converter.convert_media(str(video), str(output), output_format, 0.5, 1.5, audio_path=str(audio))
    pcm = run([ffmpeg, "-v", "error", "-i", str(output), "-map", "0:a:0", "-ac", "1", "-ar", "44100", "-f", "s16le", "pipe:1"], check=True, capture_output=True).stdout
    duration = len(pcm) / (44100 * 2)
    assert 0.9 <= duration <= 1.15
    assert any(pcm)
