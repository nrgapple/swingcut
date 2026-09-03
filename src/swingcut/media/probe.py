"""Deterministic ffprobe inventory for staged local media."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from swingcut.contracts import ContractModel


class MediaProbeError(RuntimeError):
    """Media could not be safely inspected."""


class MediaProbe(ContractModel):
    """Normalized facts needed by proxy and render policy."""

    path: Path
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duration_s: float = Field(gt=0)
    encoded_width: int = Field(gt=0)
    encoded_height: int = Field(gt=0)
    display_width: int = Field(gt=0)
    display_height: int = Field(gt=0)
    rotation_degrees: int
    frame_rate: float = Field(gt=0)
    video_codec: str = Field(min_length=1)
    pixel_format: str | None
    color_space: str | None
    color_transfer: str | None
    color_primaries: str | None
    has_audio: bool
    audio_codec: str | None
    format_names: tuple[str, ...]
    metadata: dict[str, str]

    @field_validator("duration_s", "frame_rate")
    @classmethod
    def finite_number(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("media values must be finite")
        return value


def sha256_file(path: Path) -> str:
    """Hash a file without modifying it."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_media(path: Path, *, ffprobe: str = "ffprobe") -> MediaProbe:
    """Inspect one local file with ffprobe and normalize rotation and frame rate."""
    path = path.resolve(strict=True)
    command = [
        ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        payload = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, OSError) as error:
        detail = (
            error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) else str(error)
        )
        raise MediaProbeError(f"ffprobe failed: {detail}") from error

    streams = payload.get("streams")
    file_format = payload.get("format")
    if not isinstance(streams, list) or not isinstance(file_format, dict):
        raise MediaProbeError("ffprobe returned an incomplete inventory")
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audios = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if not isinstance(video, dict):
        raise MediaProbeError("media has no video stream")

    try:
        width = int(video["width"])
        height = int(video["height"])
        duration_value = file_format.get("duration", video.get("duration"))
        if not isinstance(duration_value, (str, int, float)):
            raise ValueError("missing duration")
        duration = float(duration_value)
        rate = _parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
        codec = str(video["codec_name"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        raise MediaProbeError("ffprobe returned invalid video properties") from error
    rotation = _rotation(video)
    display_width, display_height = (height, width) if rotation % 180 else (width, height)
    audio_codec = str(audios[0].get("codec_name")) if audios else None
    format_names = tuple(str(file_format.get("format_name", "")).split(","))
    metadata = _metadata(file_format, streams)
    try:
        return MediaProbe(
            path=path,
            content_sha256=sha256_file(path),
            duration_s=duration,
            encoded_width=width,
            encoded_height=height,
            display_width=display_width,
            display_height=display_height,
            rotation_degrees=rotation,
            frame_rate=rate,
            video_codec=codec,
            pixel_format=video.get("pix_fmt"),
            color_space=video.get("color_space"),
            color_transfer=video.get("color_transfer"),
            color_primaries=video.get("color_primaries"),
            has_audio=bool(audios),
            audio_codec=audio_codec,
            format_names=format_names,
            metadata=metadata,
        )
    except ValueError as error:
        raise MediaProbeError("ffprobe returned invalid video properties") from error


def _parse_rate(value: Any) -> float:
    if not isinstance(value, str):
        raise ValueError("missing frame rate")
    return float(Fraction(value))


def _rotation(video: dict[str, Any]) -> int:
    rotation: Any = video.get("tags", {}).get("rotate")
    for side_data in video.get("side_data_list", []):
        if isinstance(side_data, dict) and "rotation" in side_data:
            rotation = side_data["rotation"]
            break
    try:
        normalized = int(round(float(rotation or 0))) % 360
    except (TypeError, ValueError) as error:
        raise MediaProbeError("invalid video rotation") from error
    if normalized not in {0, 90, 180, 270}:
        raise MediaProbeError("unsupported video rotation")
    return normalized


def _metadata(file_format: dict[str, Any], streams: list[dict[str, Any]]) -> dict[str, str]:
    combined: dict[str, str] = {}
    for owner, tags in [
        ("format", file_format.get("tags", {})),
        *[(f"stream.{index}", stream.get("tags", {})) for index, stream in enumerate(streams)],
    ]:
        if isinstance(tags, dict):
            for key, value in tags.items():
                combined[f"{owner}.{str(key).lower()}"] = str(value)
    return combined
