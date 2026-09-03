"""Explicit, estimate-disclosed private Gemini acceptance test; skipped by default."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from swingcut.media.probe import probe_media
from swingcut.media.proxy import generate_proxy
from swingcut.providers.base import UsageLedger
from swingcut.providers.gemini import GeminiProvider

_LIVE = os.environ.get("SWINGCUT_RUN_LIVE_GEMINI") == "1"


@pytest.mark.skipif(not _LIVE, reason="requires explicit SWINGCUT_RUN_LIVE_GEMINI=1 opt-in")
def test_private_live_agentic_analysis_deletes_upload() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    source_value = os.environ.get("SWINGCUT_LIVE_VIDEO")
    if not api_key or not source_value:
        pytest.fail("live test requires GEMINI_API_KEY and SWINGCUT_LIVE_VIDEO")

    source = probe_media(Path(source_value))
    with tempfile.TemporaryDirectory(prefix="swingcut-live-") as directory:
        proxy = generate_proxy(source, Path(directory) / "proxy.mp4")
        provider = GeminiProvider(api_key=api_key)
        estimate = provider.estimate_run_cost((proxy,))
        assert estimate > 0
        result = provider.analyze(proxy, source_id="private-live-source", ledger=UsageLedger())
        assert result.uploaded_file_deleted is True
        assert result.usage
