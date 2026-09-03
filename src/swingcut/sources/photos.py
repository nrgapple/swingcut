"""Private LaunchServices boundary for the narrow PhotoKit app bridge."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field

from swingcut.contracts import ContractModel
from swingcut.media.probe import sha256_file

_MAX_BRIDGE_RESPONSE_BYTES = 4 * 1024 * 1024
_DEFAULT_APP_PATH = (
    Path.home() / "Library" / "Application Support" / "Swingcut" / "SwingcutPhotosBridge.app"
)


class PhotosBridgeError(RuntimeError):
    """The native Photos bridge failed or returned an unsafe response."""


class PhotosBridgeTimeout(PhotosBridgeError):
    """The native Photos bridge exceeded its bounded execution time."""


class PhotosBridgeCancelled(PhotosBridgeError):
    """The caller cancelled a native Photos operation."""


class PhotoAssetRecord(ContractModel):
    """Private PhotoKit inventory record. Never expose this object to Pi output."""

    asset_id: str = Field(
        min_length=1,
        max_length=512,
        validation_alias=AliasChoices("asset_id", "assetID"),
    )
    filename: str = Field(min_length=1, max_length=1024)
    creation_date: str | None = Field(
        default=None,
        validation_alias=AliasChoices("creation_date", "creationDate"),
    )
    duration_seconds: float = Field(
        ge=0,
        validation_alias=AliasChoices("duration_seconds", "durationSeconds"),
    )
    width: int = Field(ge=0)
    height: int = Field(ge=0)


class PhotoAlbumInventory(ContractModel):
    album: str = Field(min_length=1, max_length=1024)
    assets: list[PhotoAssetRecord]


class PhotoExportResult(ContractModel):
    asset_id: str = Field(validation_alias=AliasChoices("asset_id", "assetID"))
    output_path: str = Field(validation_alias=AliasChoices("output_path", "outputPath"))
    bytes: int = Field(gt=0)


class PhotoImportResult(ContractModel):
    asset_id: str = Field(validation_alias=AliasChoices("asset_id", "assetID"))
    verified: bool


class StagedPhotoAsset(ContractModel):
    """Verified local copy of one immutable Photos source asset."""

    asset_id: str = Field(min_length=1, max_length=512)
    path: Path
    bytes: int = Field(gt=0)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PhotoExportFailure(ContractModel):
    """Private per-source failure; details must remain in private run state."""

    asset_id: str = Field(min_length=1, max_length=512)
    reason: str = Field(min_length=1, max_length=2048)


class PhotoExportBatch(ContractModel):
    exported: tuple[StagedPhotoAsset, ...]
    failures: tuple[PhotoExportFailure, ...]


class PhotosBridgeClient:
    """Launch the signed helper through LaunchServices and poll private files."""

    def __init__(
        self,
        app_path: Path = _DEFAULT_APP_PATH,
        *,
        timeout_seconds: float = 900,
        poll_seconds: float = 0.05,
        open_command: Path = Path("/usr/bin/open"),
    ) -> None:
        if timeout_seconds <= 0 or poll_seconds <= 0:
            raise ValueError("bridge timeout and poll interval must be positive")
        self.app_path = app_path.expanduser().resolve()
        self.timeout_seconds = timeout_seconds
        self.poll_seconds = poll_seconds
        self.open_command = open_command

    def inventory_album(
        self,
        album: str,
        *,
        cancelled: Callable[[], bool] | None = None,
    ) -> PhotoAlbumInventory:
        if not album or "\x00" in album:
            raise ValueError("an exact non-empty album name is required")
        payload = self._invoke_json(["list", "--album", album], cancelled=cancelled)
        inventory = PhotoAlbumInventory.model_validate(payload)
        if inventory.album != album:
            raise PhotosBridgeError("PhotoKit returned a different album than requested")
        return inventory

    def export_album(
        self,
        inventory: PhotoAlbumInventory,
        destination: Path,
        *,
        cancelled: Callable[[], bool] | None = None,
    ) -> PhotoExportBatch:
        """Export assets sequentially, preserving failures without touching originals."""
        destination.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(destination, 0o700)
        destination = destination.resolve(strict=True)
        exported: list[StagedPhotoAsset] = []
        failures: list[PhotoExportFailure] = []
        for index, asset in enumerate(inventory.assets, start=1):
            if cancelled is not None and cancelled():
                raise PhotosBridgeCancelled("Photos export was cancelled")
            suffix = _safe_video_suffix(asset.filename)
            output = destination / f"asset-{index:05d}{suffix}"
            if output.exists():
                raise PhotosBridgeError(f"refusing to overwrite staged output {output.name}")
            try:
                payload = self._invoke_json(
                    ["export", "--asset-id", asset.asset_id, "--output", str(output)],
                    cancelled=cancelled,
                )
                result = PhotoExportResult.model_validate(payload)
                resolved = output.resolve(strict=True)
                if (
                    result.asset_id != asset.asset_id
                    or Path(result.output_path).resolve() != resolved
                ):
                    raise PhotosBridgeError("PhotoKit export response did not match the request")
                actual_bytes = resolved.stat().st_size
                if actual_bytes <= 0 or result.bytes != actual_bytes:
                    raise PhotosBridgeError("PhotoKit export size verification failed")
                exported.append(
                    StagedPhotoAsset(
                        asset_id=asset.asset_id,
                        path=resolved,
                        bytes=actual_bytes,
                        content_sha256=sha256_file(resolved),
                    )
                )
            except PhotosBridgeCancelled:
                raise
            except (PhotosBridgeError, OSError, ValueError) as error:
                output.unlink(missing_ok=True)
                failures.append(PhotoExportFailure(asset_id=asset.asset_id, reason=str(error)))
        return PhotoExportBatch(exported=tuple(exported), failures=tuple(failures))

    def import_output(
        self,
        output: Path,
        *,
        cancelled: Callable[[], bool] | None = None,
    ) -> PhotoImportResult:
        if output.is_symlink():
            raise PhotosBridgeError("Photos import refuses symbolic links")
        output = output.resolve(strict=True)
        file_stat = output.stat()
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size <= 0:
            raise PhotosBridgeError("Photos import requires a non-empty regular local file")
        payload = self._invoke_json(["import-output", "--input", str(output)], cancelled=cancelled)
        result = PhotoImportResult.model_validate(payload)
        if not result.verified:
            raise PhotosBridgeError("Photos did not verify the newly created output asset")
        return result

    def _invoke_json(
        self,
        arguments: Sequence[str],
        *,
        cancelled: Callable[[], bool] | None,
    ) -> Any:
        if not self.app_path.is_dir():
            raise PhotosBridgeError(f"installed Photos bridge is missing: {self.app_path}")
        with tempfile.TemporaryDirectory(prefix="swingcut-photos-") as temporary:
            private_dir = Path(temporary)
            os.chmod(private_dir, 0o700)
            result_path = private_dir / "result.json"
            error_path = private_dir / "error.txt"
            cancel_path = private_dir / "cancel"
            command = [
                str(self.open_command),
                "-n",
                "-a",
                str(self.app_path),
                "--args",
                *arguments,
                "--result-file",
                str(result_path),
                "--error-file",
                str(error_path),
                "--cancel-file",
                str(cancel_path),
            ]
            try:
                launcher = subprocess.Popen(  # noqa: S603 - fixed executable, argument array only
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except OSError as error:
                raise PhotosBridgeError(f"could not launch Photos bridge: {error}") from error

            deadline = time.monotonic() + self.timeout_seconds
            cancellation_requested = False
            while True:
                if error_path.exists():
                    raise PhotosBridgeError(_read_private_text(error_path).strip())
                if result_path.exists():
                    text = _read_private_text(result_path)
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError as error:
                        raise PhotosBridgeError("Photos bridge returned malformed JSON") from error

                launcher_status = launcher.poll()
                if launcher_status not in (None, 0):
                    stderr = (launcher.stderr.read() if launcher.stderr else "").strip()
                    detail = stderr or str(launcher_status)
                    raise PhotosBridgeError(
                        f"LaunchServices could not open the Photos bridge: {detail}"
                    )

                now = time.monotonic()
                if cancelled is not None and cancelled():
                    cancellation_requested = True
                if cancellation_requested or now >= deadline:
                    cancel_path.write_text("cancel\n", encoding="utf-8")
                    os.chmod(cancel_path, 0o600)
                    # Give the helper one bounded interval to acknowledge and remove partial output.
                    grace_deadline = time.monotonic() + max(1.0, self.poll_seconds * 4)
                    while time.monotonic() < grace_deadline:
                        if error_path.exists() or result_path.exists():
                            break
                        time.sleep(self.poll_seconds)
                    if error_path.exists():
                        _read_private_text(error_path)
                    if cancellation_requested:
                        raise PhotosBridgeCancelled("Photos bridge operation was cancelled")
                    raise PhotosBridgeTimeout("Photos bridge operation timed out")
                time.sleep(self.poll_seconds)


def _read_private_text(path: Path) -> str:
    file_stat = path.lstat()
    if stat.S_ISLNK(file_stat.st_mode) or not stat.S_ISREG(file_stat.st_mode):
        raise PhotosBridgeError("Photos bridge response was not a regular private file")
    if file_stat.st_size > _MAX_BRIDGE_RESPONSE_BYTES:
        raise PhotosBridgeError("Photos bridge response exceeded the size limit")
    if stat.S_IMODE(file_stat.st_mode) & 0o077:
        raise PhotosBridgeError("Photos bridge response permissions were not private")
    return path.read_text(encoding="utf-8")


def _safe_video_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".mov", ".mp4", ".m4v", ".hevc"}:
        return suffix
    return ".mov"
