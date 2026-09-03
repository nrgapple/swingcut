"""Machine-readable backend and local readiness commands."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from swingcut.media.render import RenderError, resolve_render_ffmpeg
from swingcut.orchestrator import SwingcutOrchestrator
from swingcut.providers.gemini import GeminiProvider
from swingcut.sources.photos import PhotosBridgeClient
from swingcut.state.store import RunStore, StateStoreError


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def package_version() -> str:
    try:
        return version("swingcut")
    except PackageNotFoundError:
        return "0.1.0"


def _secret_path() -> Path:
    return (
        Path.home() / "Library" / "Application Support" / "Swingcut" / "secrets" / "gemini_api_key"
    )


def _gemini_key_check() -> Check:
    if os.environ.get("GEMINI_API_KEY"):
        return Check("Gemini API key", True, "configured in environment", required=False)
    secret_file = _secret_path()
    if secret_file.is_file() and secret_file.stat().st_size > 0:
        permissions = stat.S_IMODE(secret_file.stat().st_mode)
        if permissions == 0o600:
            return Check(
                "Gemini API key", True, "configured in private runtime storage", required=False
            )
        return Check(
            "Gemini API key",
            False,
            f"secret file permissions are {permissions:o}; expected 600",
            required=False,
        )
    return Check("Gemini API key", False, "not configured (needed later)", required=False)


def _hdr_ffmpeg_check() -> Check:
    try:
        executable = resolve_render_ffmpeg()
    except RenderError as error:
        return Check("FFmpeg HDR filters", False, str(error))
    return Check("FFmpeg HDR filters", True, executable)


def _run_state_check() -> Check:
    try:
        stale = RunStore().stale_resumable_count()
    except (OSError, ValueError, StateStoreError):
        return Check("Run state", False, "private runtime storage is unavailable", required=False)
    detail = f"{stale} stale resumable run(s)" if stale else "no stale resumable runs"
    return Check("Run state", stale == 0, detail, required=False)


def collect_checks() -> list[Check]:
    python_version = sys.version_info
    return [
        Check("macOS", platform.system() == "Darwin", platform.platform()),
        Check(
            "Python",
            python_version >= (3, 12),
            f"{python_version.major}.{python_version.minor}.{python_version.micro}",
        ),
        _command_check("ffmpeg"),
        _command_check("ffprobe"),
        _hdr_ffmpeg_check(),
        _command_check("swift"),
        _gemini_key_check(),
        _run_state_check(),
    ]


def _command_check(command: str) -> Check:
    path = shutil.which(command)
    return Check(command, path is not None, path or "not found")


def doctor() -> int:
    checks = collect_checks()
    for check in checks:
        status = "ok" if check.ok else ("optional" if not check.required else "missing")
        print(f"[{status:8}] {check.name}: {check.detail}")
    return 1 if any(check.required and not check.ok for check in checks) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swingcut", description="Local-first golf swing video editor"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {package_version()}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="check prerequisites without Photos or network access")

    inspect = subparsers.add_parser("inspect", help="inspect an exact Photos album")
    inspect.add_argument("--photos-album", required=True)
    inspect.add_argument("--json", action="store_true", required=True)

    run = subparsers.add_parser("run", help="process one confirmed exact Photos album")
    run.add_argument("--photos-album", required=True)
    run.add_argument("--mode", choices=("incremental", "rebuild"), required=True)
    run.add_argument("--import-to-photos", action="store_true", required=True)
    run.add_argument("--confirmed", action="store_true", required=True)
    run.add_argument("--json-events", action="store_true", required=True)
    run.add_argument("--resume-run-id")

    status = subparsers.add_parser("status", help="show privacy-safe run status")
    status.add_argument("run_id")
    status.add_argument("--json", action="store_true", required=True)

    cancel = subparsers.add_parser("cancel", help="request cooperative cancellation")
    cancel.add_argument("run_id")
    subparsers.add_parser("clean", help="clean terminal media and report stale resumable runs")
    return parser


def _provider() -> GeminiProvider:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        path = _secret_path()
        if not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise RuntimeError("Gemini API key is not configured in private storage")
        key = path.read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError("Gemini API key is empty")
    return GeminiProvider(api_key=key)


def _orchestrator() -> SwingcutOrchestrator:
    return SwingcutOrchestrator(photos=PhotosBridgeClient(), provider=_provider(), store=RunStore())


def _print_json(payload: object) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        return doctor()
    try:
        if args.command == "inspect":
            _print_json(_orchestrator().inspect(args.photos_album))
        elif args.command == "run":
            orchestrator = _orchestrator()
            result = orchestrator.run(
                args.photos_album,
                mode=args.mode,
                import_to_photos=args.import_to_photos,
                confirmed=args.confirmed,
                event_sink=lambda event: _print_json(event.model_dump(mode="json")),
                resume_run_id=args.resume_run_id,
            )
            _print_json(result)
        elif args.command == "status":
            store = RunStore()
            state = store.load_state(args.run_id)
            payload: dict[str, Any] = state.public_summary()
            manifest = store.load_manifest(args.run_id)
            if manifest is not None:
                payload["summary"] = manifest.model_dump(mode="json")
            _print_json(payload)
        elif args.command == "cancel":
            RunStore().request_cancel(args.run_id)
            _print_json({"cancel_requested": True, "run_id": args.run_id})
        elif args.command == "clean":
            _print_json(RunStore().clean())
        else:
            return 2
    except (RuntimeError, ValueError, OSError, StateStoreError):
        _print_json({"error": "swingcut command failed; run doctor or inspect private diagnostics"})
        return 1
    return 0
