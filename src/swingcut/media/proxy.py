"""Generation and verification of the only cloud-eligible media artifact."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import Field

from swingcut.contracts import ContractModel
from swingcut.media.probe import MediaProbe, MediaProbeError, probe_media, sha256_file

PROXY_PROFILE_VERSION = "silent-h264-480w-15fps-v1"
PROXY_MAX_WIDTH = 480
PROXY_FRAME_RATE = 15.0


class ProxyGenerationError(RuntimeError):
    """A sanitized proxy could not be generated or verified."""


class ProxyArtifact(ContractModel):
    """Typed evidence required before a provider may accept a proxy path."""

    profile_version: str = Field(default=PROXY_PROFILE_VERSION, frozen=True)
    path: Path
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    proxy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duration_s: float = Field(gt=0)
    width: int = Field(gt=0, le=PROXY_MAX_WIDTH)
    height: int = Field(gt=0)
    frame_rate: float = Field(gt=0)
    sanitizer_verified: bool = Field(default=True, frozen=True)


def generate_proxy(
    source: MediaProbe,
    destination: Path,
    *,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> ProxyArtifact:
    """Create a full-duration, silent, low-resolution, metadata-stripped proxy."""
    destination = destination.resolve()
    if destination == source.path:
        raise ProxyGenerationError("proxy destination must differ from source")
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source.path),
        "-map",
        "0:v:0",
        "-vf",
        "scale='min(480,iw)':-2:flags=lanczos,fps=15,setsar=1,format=yuv420p",
        "-an",
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "28",
        "-movflags",
        "+faststart",
        str(destination),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        proxy = probe_media(destination, ffprobe=ffprobe)
        _verify_proxy(source, proxy)
    except (subprocess.CalledProcessError, OSError, MediaProbeError, ValueError) as error:
        destination.unlink(missing_ok=True)
        detail = (
            error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) else str(error)
        )
        raise ProxyGenerationError(f"proxy generation failed: {detail}") from error
    if source.content_sha256 != _rehash_source(source):
        destination.unlink(missing_ok=True)
        raise ProxyGenerationError("source changed while generating proxy")
    return ProxyArtifact(
        path=proxy.path,
        source_sha256=source.content_sha256,
        proxy_sha256=proxy.content_sha256,
        duration_s=proxy.duration_s,
        width=proxy.display_width,
        height=proxy.display_height,
        frame_rate=proxy.frame_rate,
    )


def _verify_proxy(source: MediaProbe, proxy: MediaProbe) -> None:
    if proxy.video_codec != "h264" or proxy.pixel_format != "yuv420p":
        raise ValueError("proxy is not H.264 yuv420p")
    if proxy.has_audio:
        raise ValueError("proxy contains audio")
    if proxy.display_width > min(PROXY_MAX_WIDTH, source.display_width):
        raise ValueError("proxy exceeds the source-bounded width policy")
    if abs(proxy.frame_rate - PROXY_FRAME_RATE) > 0.05:
        raise ValueError("proxy frame rate does not match policy")
    if abs(proxy.duration_s - source.duration_s) > max(0.2, 1 / PROXY_FRAME_RATE * 2):
        raise ValueError("proxy is not full duration")
    prohibited = ("location", "creation", "date", "device", "make", "model", "title", "comment")
    if any(any(token in key for token in prohibited) for key in proxy.metadata):
        raise ValueError("proxy contains prohibited metadata")


def _rehash_source(source: MediaProbe) -> str:
    return sha256_file(source.path)
