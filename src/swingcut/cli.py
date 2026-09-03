"""Command-line entry point for the Swingcut scaffold."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


@dataclass(frozen=True)
class Check:
    """One local readiness check."""

    name: str
    ok: bool
    detail: str
    required: bool = True


def package_version() -> str:
    """Return the installed package version."""
    try:
        return version("swingcut")
    except PackageNotFoundError:
        return "0.1.0"


def _gemini_key_check() -> Check:
    if os.environ.get("GEMINI_API_KEY"):
        return Check("Gemini API key", True, "configured in environment", required=False)

    secret_file = (
        Path.home() / "Library" / "Application Support" / "Swingcut" / "secrets" / "gemini_api_key"
    )
    if secret_file.is_file() and secret_file.stat().st_size > 0:
        permissions = stat.S_IMODE(secret_file.stat().st_mode)
        if permissions == 0o600:
            return Check(
                "Gemini API key",
                True,
                "configured in private runtime storage",
                required=False,
            )
        return Check(
            "Gemini API key",
            False,
            f"secret file permissions are {permissions:o}; expected 600",
            required=False,
        )

    return Check("Gemini API key", False, "not configured (needed later)", required=False)


def collect_checks() -> list[Check]:
    """Inspect local prerequisites without network or Photos access."""
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
        _command_check("swift"),
        _gemini_key_check(),
    ]


def _command_check(command: str) -> Check:
    path = shutil.which(command)
    return Check(command, path is not None, path or "not found")


def doctor() -> int:
    """Print local prerequisite status and return nonzero for required failures."""
    checks = collect_checks()
    for check in checks:
        status = "ok" if check.ok else ("optional" if not check.required else "missing")
        print(f"[{status:8}] {check.name}: {check.detail}")
    return 1 if any(check.required and not check.ok for check in checks) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swingcut",
        description="Local-first golf swing video editor (project scaffold)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {package_version()}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "doctor",
        help="check local prerequisites without accessing Photos or the network",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        return doctor()
    return 2
