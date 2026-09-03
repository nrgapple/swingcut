from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from swingcut.contracts import EditPlan, EditSegment
from swingcut.media.probe import MediaProbeError, probe_media, sha256_file
from swingcut.media.proxy import PROXY_PROFILE_VERSION, ProxyGenerationError, generate_proxy
from swingcut.media.render import (
    RenderError,
    render_compilation,
    select_output_profile,
    verify_output,
)


def _synthetic_video(
    path: Path,
    *,
    size: str,
    rate: str,
    audio: bool,
    duration: float = 2.4,
) -> Path:
    command = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size={size}:rate={rate}:duration={duration}",
    ]
    if audio:
        command.extend(
            [
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=880:sample_rate=48000:duration={duration}",
                "-shortest",
            ]
        )
    command.extend(
        [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-metadata",
            "title=PRIVATE FIXTURE TITLE",
            "-metadata",
            "creation_time=2020-01-02T03:04:05Z",
        ]
    )
    if audio:
        command.extend(["-c:a", "aac"])
    command.append(str(path))
    subprocess.run(command, check=True)
    return path


@pytest.fixture
def landscape(tmp_path: Path) -> Path:
    return _synthetic_video(
        tmp_path / "landscape.mp4", size="640x360", rate="30000/1001", audio=True
    )


@pytest.fixture
def portrait(tmp_path: Path) -> Path:
    return _synthetic_video(tmp_path / "portrait.mp4", size="180x320", rate="24", audio=False)


def _segment(path: Path, source_id: str, start: float = 0.2, end: float = 1.5) -> EditSegment:
    return EditSegment(
        source_id=source_id,
        source_path=path,
        candidate_id=f"candidate-{source_id}",
        start_s=start,
        takeaway_s=start + 0.1,
        impact_s=start + 0.4,
        finish_s=end - 0.1,
        end_s=end,
    )


def test_probe_inventories_orientation_audio_rate_and_metadata(
    landscape: Path, portrait: Path
) -> None:
    wide = probe_media(landscape)
    tall = probe_media(portrait)

    assert (wide.display_width, wide.display_height) == (640, 360)
    assert wide.has_audio is True
    assert wide.audio_codec == "aac"
    assert wide.frame_rate == pytest.approx(30000 / 1001)
    assert any("title" in key for key in wide.metadata)
    assert (tall.display_width, tall.display_height) == (180, 320)
    assert tall.has_audio is False
    assert tall.audio_codec is None
    assert tall.content_sha256 == sha256_file(portrait)


def test_probe_rejects_missing_and_non_video_media(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        probe_media(tmp_path / "missing.mp4")

    audio = tmp_path / "audio.m4a"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=duration=0.2",
            "-c:a",
            "aac",
            str(audio),
        ],
        check=True,
    )
    with pytest.raises(MediaProbeError, match="no video"):
        probe_media(audio)


def test_proxy_is_full_duration_silent_bounded_and_sanitized(
    landscape: Path, tmp_path: Path
) -> None:
    source = probe_media(landscape)
    before = sha256_file(landscape)
    artifact = generate_proxy(source, tmp_path / "private" / "proxy.mp4")
    proxy = probe_media(artifact.path)

    assert artifact.profile_version == PROXY_PROFILE_VERSION
    assert artifact.sanitizer_verified is True
    assert artifact.source_sha256 == before == sha256_file(landscape)
    assert artifact.proxy_sha256 == proxy.content_sha256
    assert proxy.has_audio is False
    assert proxy.display_width == 480
    assert proxy.frame_rate == pytest.approx(15.0)
    assert proxy.duration_s == pytest.approx(source.duration_s, abs=0.15)
    assert not any("title" in key or "creation" in key for key in proxy.metadata)


def test_proxy_refuses_source_destination(landscape: Path) -> None:
    source = probe_media(landscape)
    with pytest.raises(ProxyGenerationError, match="must differ"):
        generate_proxy(source, landscape)


def test_mixed_render_letterboxes_retains_audio_and_preserves_sources(
    landscape: Path, portrait: Path, tmp_path: Path
) -> None:
    before = {path: sha256_file(path) for path in (landscape, portrait)}
    plan = EditPlan(segments=(_segment(landscape, "wide"), _segment(portrait, "tall")))

    result = render_compilation(plan, tmp_path / "output.mp4")
    output = probe_media(result.path)

    assert result.profile.canvas == "landscape-16x9"
    assert (output.display_width, output.display_height) == (640, 360)
    assert output.video_codec == "h264"
    assert output.pixel_format == "yuv420p"
    assert (output.color_space, output.color_transfer, output.color_primaries) == (
        "bt709",
        "bt709",
        "bt709",
    )
    assert output.audio_codec == "aac"
    assert output.duration_s == pytest.approx(2.6, abs=0.25)
    assert result.segment_count == 2
    assert result.source_hashes_unchanged is True
    assert {path: sha256_file(path) for path in before} == before

    volume = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-i",
            str(result.path),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "mean_volume: -inf" not in volume.stderr


def test_portrait_profile_and_render(portrait: Path, tmp_path: Path) -> None:
    source = probe_media(portrait)
    profile = select_output_profile((source,))
    assert (profile.canvas, profile.width, profile.height) == ("portrait-9x16", 180, 320)

    result = render_compilation(
        EditPlan(segments=(_segment(portrait, "portrait"),)), tmp_path / "portrait-output.mp4"
    )
    assert result.profile == profile


def test_render_and_verification_fail_closed(landscape: Path, tmp_path: Path) -> None:
    with pytest.raises(RenderError, match="empty"):
        render_compilation(EditPlan(segments=()), tmp_path / "empty.mp4")
    with pytest.raises(RenderError, match="must differ"):
        render_compilation(EditPlan(segments=(_segment(landscape, "same"),)), landscape)
    with pytest.raises(ValueError, match="at least one"):
        select_output_profile(())
    hdr = probe_media(landscape).model_copy(update={"color_transfer": "smpte2084"})
    with pytest.raises(ValueError, match="HDR"):
        select_output_profile((hdr,))

    valid = render_compilation(
        EditPlan(segments=(_segment(landscape, "valid"),)), tmp_path / "valid.mp4"
    )
    with pytest.raises(ValueError, match="duration"):
        verify_output(valid.path, expected_duration_s=9.0, profile=valid.profile)

    out_of_bounds = _segment(landscape, "bounds", start=1.0, end=3.0)
    with pytest.raises(RenderError, match="exceeds"):
        render_compilation(EditPlan(segments=(out_of_bounds,)), tmp_path / "bounds.mp4")
