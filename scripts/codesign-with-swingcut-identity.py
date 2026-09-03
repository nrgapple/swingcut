#!/usr/bin/env python3
"""Sign one bundle while exposing only Swingcut's keychain to codesign lookup."""

from __future__ import annotations

import signal
import subprocess
import sys
from pathlib import Path

SECURITY = "/usr/bin/security"
CODESIGN = "/usr/bin/codesign"
IDENTITY = "Swingcut Local Code Signing"


def user_keychains() -> list[str]:
    result = subprocess.run(
        [SECURITY, "list-keychains", "-d", "user"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip().strip('"') for line in result.stdout.splitlines() if line.strip()]


def set_user_keychains(keychains: list[str]) -> None:
    subprocess.run(
        [SECURITY, "list-keychains", "-d", "user", "-s", *keychains],
        check=True,
    )


def interrupted(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


def main() -> int:
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} KEYCHAIN ENTITLEMENTS APP", file=sys.stderr)
        return 2

    keychain = Path(sys.argv[1]).resolve(strict=True)
    entitlements = Path(sys.argv[2]).resolve(strict=True)
    app = Path(sys.argv[3]).resolve(strict=True)
    password_file = keychain.parent / "keychain-password"
    password = password_file.read_text(encoding="utf-8").strip()
    if not password:
        raise RuntimeError("Swingcut signing keychain password is empty")

    original = user_keychains()
    temporary = [str(keychain), *(item for item in original if item != str(keychain))]
    for signal_number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(signal_number, interrupted)
    try:
        set_user_keychains(temporary)
        subprocess.run([SECURITY, "unlock-keychain", "-p", password, str(keychain)], check=True)
        subprocess.run(
            [
                CODESIGN,
                "--force",
                "--timestamp=none",
                "--keychain",
                str(keychain),
                "--sign",
                IDENTITY,
                "--identifier",
                "dev.swingcut.photos-bridge",
                "--entitlements",
                str(entitlements),
                str(app),
            ],
            check=True,
        )
    finally:
        set_user_keychains(original)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
