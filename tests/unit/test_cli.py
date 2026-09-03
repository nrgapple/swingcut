from __future__ import annotations

from pathlib import Path

import pytest

from swingcut import __version__
from swingcut.cli import Check, _gemini_key_check, collect_checks, main


def test_version_is_initial_release() -> None:
    assert __version__ == "0.1.0"


def test_collect_checks_has_required_tooling() -> None:
    checks = {check.name: check for check in collect_checks()}
    assert {"macOS", "Python", "ffmpeg", "ffprobe", "swift"} <= checks.keys()
    assert all(isinstance(check, Check) for check in checks.values())


def test_gemini_key_check_accepts_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-value")
    check = _gemini_key_check()
    assert check.ok
    assert check.detail == "configured in environment"


def test_gemini_key_check_handles_missing_private_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("swingcut.cli.Path.home", lambda: tmp_path)
    check = _gemini_key_check()
    assert not check.ok
    assert not check.required


def test_gemini_key_check_accepts_mode_600_private_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("swingcut.cli.Path.home", lambda: tmp_path)
    secret = tmp_path / "Library/Application Support/Swingcut/secrets/gemini_api_key"
    secret.parent.mkdir(parents=True)
    secret.write_text("not-a-real-key")
    secret.chmod(0o600)
    check = _gemini_key_check()
    assert check.ok
    assert check.detail == "configured in private runtime storage"


def test_doctor_succeeds_on_supported_development_host(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["doctor"]) == 0
    output = capsys.readouterr().out
    assert "ffmpeg" in output
    assert "Gemini API key" in output
