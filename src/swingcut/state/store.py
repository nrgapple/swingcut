"""Mode-restricted durable run records, exact analysis cache, and cleanup."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import Field

from swingcut.contracts import AnalyzedSource, ContractModel, RunManifest, RunState

STATE_FILE = "state.json"
MANIFEST_FILE = "manifest.json"
PRIVATE_FILE = "private.json"
CANCEL_FILE = "cancel"
CACHE_SCHEMA_VERSION = 1
DEFAULT_RETENTION = timedelta(hours=24)


class StateStoreError(RuntimeError):
    """Durable state was absent, malformed, or unsafe."""


class CacheKey(ContractModel):
    """All evidence that must match before probabilistic analysis can be reused."""

    schema_version: int = Field(default=CACHE_SCHEMA_VERSION, frozen=True)
    source_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_version_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    proxy_profile: str
    model: str
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    validator_version: str

    def digest(self) -> str:
        payload = self.model_dump_json(exclude_none=False)
        return hashlib.sha256(payload.encode()).hexdigest()


class AnalysisCacheEntry(ContractModel):
    schema_version: int = Field(default=CACHE_SCHEMA_VERSION, frozen=True)
    key: CacheKey
    analysis: AnalyzedSource


class RunStore:
    """Own private Application Support storage without following symlinks."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_runtime_root()).expanduser()
        self.runs = self.root / "runs"
        self.cache = self.root / "cache" / "analysis"
        self.albums = self.root / "cache" / "albums"
        for path in (self.root, self.runs, self.cache, self.albums):
            _private_directory(path)

    def create(self, state: RunState) -> Path:
        run_dir = self.run_dir(state.run_id)
        if run_dir.exists():
            raise StateStoreError("run identifier already exists")
        _private_directory(run_dir)
        self.save_state(state)
        return run_dir

    def run_dir(self, run_id: str) -> Path:
        if not run_id or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in run_id
        ):
            raise StateStoreError("invalid run identifier")
        return self.runs / run_id

    def save_state(self, state: RunState) -> None:
        _write_private_json(self.run_dir(state.run_id) / STATE_FILE, state.model_dump(mode="json"))

    def load_state(self, run_id: str) -> RunState:
        return RunState.model_validate_json(_read_private_text(self.run_dir(run_id) / STATE_FILE))

    def save_manifest(self, manifest: RunManifest) -> None:
        _write_private_json(
            self.run_dir(manifest.run_id) / MANIFEST_FILE, manifest.model_dump(mode="json")
        )

    def load_manifest(self, run_id: str) -> RunManifest | None:
        path = self.run_dir(run_id) / MANIFEST_FILE
        return RunManifest.model_validate_json(_read_private_text(path)) if path.exists() else None

    def save_private(self, run_id: str, payload: dict[str, Any]) -> None:
        _write_private_json(self.run_dir(run_id) / PRIVATE_FILE, payload)

    def load_private(self, run_id: str) -> dict[str, Any]:
        payload = _read_private_json(self.run_dir(run_id) / PRIVATE_FILE)
        if not isinstance(payload, dict):
            raise StateStoreError("private run record is malformed")
        return payload

    def remove_private_record(self, run_id: str) -> None:
        (self.run_dir(run_id) / PRIVATE_FILE).unlink(missing_ok=True)

    def request_cancel(self, run_id: str) -> None:
        state = self.load_state(run_id)
        if state.stage.value in {"succeeded", "failed", "cancelled"}:
            raise StateStoreError("run is already terminal")
        _write_private_text(self.run_dir(run_id) / CANCEL_FILE, "cancel\n")

    def cancelled(self, run_id: str) -> bool:
        return (self.run_dir(run_id) / CANCEL_FILE).exists()

    def cache_get(self, key: CacheKey) -> AnalyzedSource | None:
        path = self.cache / f"{key.digest()}.json"
        if not path.exists():
            return None
        try:
            entry = AnalysisCacheEntry.model_validate_json(_read_private_text(path))
        except (ValueError, OSError):
            path.unlink(missing_ok=True)
            return None
        return entry.analysis if entry.key == key else None

    def cache_put(self, key: CacheKey, analysis: AnalyzedSource) -> None:
        entry = AnalysisCacheEntry(key=key, analysis=analysis)
        _write_private_json(self.cache / f"{key.digest()}.json", entry.model_dump(mode="json"))

    def album_seen(self, fingerprint: str) -> bool:
        return (self.albums / f"{fingerprint}.seen").is_file()

    def mark_album_seen(self, fingerprint: str) -> None:
        _write_private_text(self.albums / f"{fingerprint}.seen", "seen\n")

    def clean_run_media(self, run_id: str) -> None:
        run_dir = self.run_dir(run_id)
        for name in ("staged", "proxies", "output"):
            target = run_dir / name
            if target.is_symlink():
                target.unlink()
            elif target.exists():
                shutil.rmtree(target)

    def stale_resumable_count(
        self, *, now: datetime | None = None, retention: timedelta = DEFAULT_RETENTION
    ) -> int:
        now = now or datetime.now(UTC)
        count = 0
        for run_dir in self.runs.iterdir():
            if not run_dir.is_dir() or run_dir.is_symlink():
                continue
            try:
                state = self.load_state(run_dir.name)
            except (OSError, ValueError, StateStoreError):
                continue
            age = now - datetime.fromtimestamp(run_dir.stat().st_mtime, UTC)
            if state.stage.value not in {"succeeded", "failed", "cancelled"} and age > retention:
                count += 1
        return count

    def clean(
        self, *, now: datetime | None = None, retention: timedelta = DEFAULT_RETENTION
    ) -> dict[str, int]:
        now = now or datetime.now(UTC)
        cleaned = 0
        stale = 0
        for run_dir in self.runs.iterdir():
            if not run_dir.is_dir() or run_dir.is_symlink():
                continue
            try:
                state = self.load_state(run_dir.name)
            except (OSError, ValueError, StateStoreError):
                continue
            age = now - datetime.fromtimestamp(run_dir.stat().st_mtime, UTC)
            if state.stage.value in {"succeeded", "failed", "cancelled"}:
                self.clean_run_media(state.run_id)
                cleaned += 1
            elif age > retention:
                stale += 1
        return {"cleaned_terminal_runs": cleaned, "stale_resumable_runs": stale}


def default_runtime_root() -> Path:
    return Path.home() / "Library" / "Application Support" / "Swingcut"


def _private_directory(path: Path) -> None:
    if path.exists() and path.is_symlink():
        raise StateStoreError("private storage cannot be a symbolic link")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def _write_private_text(path: Path, text: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _write_private_json(path: Path, payload: object) -> None:
    _write_private_text(path, json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _read_private_text(path: Path) -> str:
    file_stat = path.lstat()
    if path.is_symlink() or not path.is_file() or file_stat.st_mode & 0o077:
        raise StateStoreError("private state file is unsafe")
    return path.read_text(encoding="utf-8")


def _read_private_json(path: Path) -> object:
    return json.loads(_read_private_text(path))
