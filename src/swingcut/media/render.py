"""Deterministic source-derived compilation rendering and verification."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import Field

from swingcut.contracts import ContractModel, EditPlan
from swingcut.media.probe import MediaProbe, MediaProbeError, probe_media, sha256_file

OUTPUT_PROFILE_VERSION = "photos-h264-aac-sdr-v1"
OUTPUT_FRAME_RATE = 30.0
MAX_LANDSCAPE_WIDTH = 1920
MAX_PORTRAIT_HEIGHT = 1920


class RenderError(RuntimeError):
    """A compilation could not be safely rendered or verified."""


class OutputProfile(ContractModel):
    version: str = Field(default=OUTPUT_PROFILE_VERSION, frozen=True)
    canvas: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frame_rate: float = Field(default=OUTPUT_FRAME_RATE, frozen=True)
    video_codec: str = Field(default="h264", frozen=True)
    audio_codec: str = Field(default="aac", frozen=True)
    pixel_format: str = Field(default="yuv420p", frozen=True)
    color_profile: str = Field(default="bt709-sdr", frozen=True)


class RenderResult(ContractModel):
    path: Path
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duration_s: float = Field(gt=0)
    profile: OutputProfile
    segment_count: int = Field(gt=0)
    source_hashes_unchanged: bool = Field(default=True, frozen=True)


def select_output_profile(probes: tuple[MediaProbe, ...]) -> OutputProfile:
    """Choose a source-bounded 16:9/9:16 canvas; mixed media uses landscape."""
    if not probes:
        raise ValueError("at least one media probe is required")
    all_portrait = all(probe.display_height > probe.display_width for probe in probes)
    _require_supported_color(probes)
    if all_portrait:
        height = _even(min(MAX_PORTRAIT_HEIGHT, max(probe.display_height for probe in probes)))
        width = _even(height * 9 // 16)
        return OutputProfile(canvas="portrait-9x16", width=width, height=height)
    landscape = tuple(probe for probe in probes if probe.display_width >= probe.display_height)
    width = _even(min(MAX_LANDSCAPE_WIDTH, max(probe.display_width for probe in landscape)))
    height = _even(width * 9 // 16)
    return OutputProfile(canvas="landscape-16x9", width=width, height=height)


def render_compilation(
    plan: EditPlan,
    destination: Path,
    *,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> RenderResult:
    """Render validated plan segments from originals, retaining source audio."""
    if not plan.segments:
        raise RenderError("cannot render an empty edit plan")
    destination = destination.resolve()
    paths = tuple(
        dict.fromkeys(segment.source_path.resolve(strict=True) for segment in plan.segments)
    )
    if destination in paths:
        raise RenderError("output destination must differ from every source")
    try:
        probes_by_path = {path: probe_media(path, ffprobe=ffprobe) for path in paths}
    except (OSError, MediaProbeError) as error:
        raise RenderError(f"source inventory failed: {error}") from error
    before_hashes = {path: probe.content_sha256 for path, probe in probes_by_path.items()}
    segment_probes = tuple(
        probes_by_path[segment.source_path.resolve()] for segment in plan.segments
    )
    profile = select_output_profile(segment_probes)
    _validate_plan_bounds(plan, probes_by_path)

    command = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
    for segment in plan.segments:
        command.extend(["-i", str(segment.source_path.resolve())])
    filter_parts: list[str] = []
    concat_inputs: list[str] = []
    for index, (segment, probe) in enumerate(zip(plan.segments, segment_probes, strict=True)):
        duration = segment.end_s - segment.start_s
        scale = (
            f"scale=w='min(iw,{profile.width})':h='min(ih,{profile.height})':"
            "force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos"
        )
        filter_parts.append(
            f"[{index}:v:0]trim=start={segment.start_s}:end={segment.end_s},"
            f"setpts=PTS-STARTPTS,{scale},pad={profile.width}:{profile.height}:"
            "(ow-iw)/2:(oh-ih)/2:black,setsar=1,"
            f"fps={profile.frame_rate},format=yuv420p[v{index}]"
        )
        if probe.has_audio:
            filter_parts.append(
                f"[{index}:a:0]atrim=start={segment.start_s}:end={segment.end_s},"
                "asetpts=PTS-STARTPTS,aresample=48000,"
                f"aformat=sample_fmts=fltp:channel_layouts=stereo[a{index}]"
            )
        else:
            filter_parts.append(
                f"anullsrc=r=48000:cl=stereo,atrim=duration={duration},"
                f"asetpts=PTS-STARTPTS[a{index}]"
            )
        concat_inputs.extend([f"[v{index}]", f"[a{index}]"])
    filter_parts.append(
        f"{''.join(concat_inputs)}concat=n={len(plan.segments)}:v=1:a=1[vout][aout]"
    )
    command.extend(
        [
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "18",
            "-profile:v",
            "high",
            "-x264-params",
            "colorprim=bt709:transfer=bt709:colormatrix=bt709",
            "-pix_fmt",
            "yuv420p",
            "-colorspace",
            "bt709",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-color_range",
            "tv",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(destination),
        ]
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        expected_duration = sum(segment.end_s - segment.start_s for segment in plan.segments)
        output = verify_output(
            destination,
            expected_duration_s=expected_duration,
            profile=profile,
            ffmpeg=ffmpeg,
            ffprobe=ffprobe,
        )
    except (subprocess.CalledProcessError, OSError, MediaProbeError, ValueError) as error:
        destination.unlink(missing_ok=True)
        detail = (
            error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) else str(error)
        )
        raise RenderError(f"render failed: {detail}") from error
    if any(sha256_file(path) != digest for path, digest in before_hashes.items()):
        destination.unlink(missing_ok=True)
        raise RenderError("a staged source changed during rendering")
    return RenderResult(
        path=output.path,
        content_sha256=output.content_sha256,
        duration_s=output.duration_s,
        profile=profile,
        segment_count=len(plan.segments),
    )


def verify_output(
    path: Path,
    *,
    expected_duration_s: float,
    profile: OutputProfile,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> MediaProbe:
    """Require the selected Photos-compatible profile and decode every output frame."""
    output = probe_media(path, ffprobe=ffprobe)
    if (output.display_width, output.display_height) != (profile.width, profile.height):
        raise ValueError("output canvas does not match selected profile")
    if output.video_codec != profile.video_codec or output.pixel_format != profile.pixel_format:
        raise ValueError("output video profile is incompatible")
    if not output.has_audio or output.audio_codec != profile.audio_codec:
        raise ValueError("output must contain AAC audio")
    if abs(output.frame_rate - profile.frame_rate) > 0.05:
        raise ValueError("output frame rate does not match selected profile")
    if (output.color_space, output.color_transfer, output.color_primaries) != (
        "bt709",
        "bt709",
        "bt709",
    ):
        raise ValueError("output color profile is not BT.709 SDR")
    if abs(output.duration_s - expected_duration_s) > 0.25:
        raise ValueError("output duration does not match edit plan")
    subprocess.run(
        [ffmpeg, "-nostdin", "-v", "error", "-i", str(path), "-f", "null", "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return output


def _validate_plan_bounds(plan: EditPlan, probes_by_path: dict[Path, MediaProbe]) -> None:
    for segment in plan.segments:
        probe = probes_by_path[segment.source_path.resolve()]
        if segment.end_s > probe.duration_s + 0.05:
            raise RenderError("edit plan segment exceeds probed source duration")


def _require_supported_color(probes: tuple[MediaProbe, ...]) -> None:
    hdr_transfers = {"smpte2084", "arib-std-b67"}
    if any(probe.color_transfer in hdr_transfers for probe in probes):
        raise ValueError("HDR input requires a validated tone-mapping profile")


def _even(value: int) -> int:
    return max(2, value - value % 2)
