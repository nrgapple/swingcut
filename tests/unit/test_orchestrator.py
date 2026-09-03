from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from swingcut.contracts import (
    AnalyzedSource,
    RunStage,
    RunState,
    SwingAnalysis,
)
from swingcut.media.proxy import ProxyArtifact
from swingcut.media.render import OutputProfile, RenderResult
from swingcut.orchestrator import AmbiguousImportError, SwingcutOrchestrator
from swingcut.providers.base import AnalysisProvider, AnalysisResult, UsageLedger
from swingcut.sources.photos import (
    PhotoAlbumInventory,
    PhotoAssetRecord,
    PhotoExportBatch,
    PhotoExportFailure,
    PhotoImportResult,
    StagedPhotoAsset,
)
from swingcut.state.store import RunStore, StateStoreError


class FakePhotos:
    def __init__(self, *, fail_second: bool = False) -> None:
        self.fail_second = fail_second
        self.imported = 0
        self.contents = {"asset-a": b"source-a", "asset-b": b"source-b"}

    def inventory_album(self, album: str, *, cancelled=None):  # type: ignore[no-untyped-def]
        return PhotoAlbumInventory(
            album=album,
            assets=[
                PhotoAssetRecord(
                    asset_id=asset_id,
                    filename=f"{asset_id}.mov",
                    creation_date=f"2024-01-0{index}T00:00:00Z",
                    duration_seconds=10,
                    width=1080,
                    height=1920,
                )
                for index, asset_id in enumerate(self.contents, start=1)
            ],
        )

    def export_album(self, inventory, destination, *, cancelled=None):  # type: ignore[no-untyped-def]
        destination.mkdir(parents=True, exist_ok=True)
        exported = []
        failures = []
        for index, asset in enumerate(inventory.assets, start=1):
            if self.fail_second and index == 2:
                failures.append(PhotoExportFailure(asset_id=asset.asset_id, reason="synthetic"))
                continue
            path = destination / f"asset-{index}.mov"
            path.write_bytes(self.contents[asset.asset_id])
            exported.append(
                StagedPhotoAsset(
                    asset_id=asset.asset_id,
                    path=path,
                    bytes=path.stat().st_size,
                    content_sha256=_hash(path.read_bytes()),
                )
            )
        return PhotoExportBatch(exported=tuple(exported), failures=tuple(failures))

    def import_output(self, output: Path, *, cancelled=None):  # type: ignore[no-untyped-def]
        assert output.is_file()
        self.imported += 1
        return PhotoImportResult(asset_id=f"new-{self.imported}", verified=True)


class FakeProvider(AnalysisProvider):
    @property
    def pricing_valid_through(self) -> date:
        return date(2026, 12, 31)

    def __init__(self, *, no_swings: bool = False) -> None:
        self.calls: list[str] = []
        self.no_swings = no_swings

    def estimate_run_cost_for_durations(self, durations_s: tuple[float, ...]) -> Decimal:
        return Decimal("0.10")

    def estimate_run_cost(self, proxies: tuple[ProxyArtifact, ...]) -> Decimal:
        return Decimal("0.10")

    def analyze(
        self, proxy: ProxyArtifact, *, source_id: str, ledger: UsageLedger
    ) -> AnalysisResult:
        self.calls.append(source_id)
        candidates: tuple[SwingAnalysis, ...] = ()
        if not self.no_swings:
            candidates = (
                SwingAnalysis(
                    candidate_id=f"candidate-{source_id}",
                    contains_apparent_ball_strike=True,
                    takeaway_s=2,
                    impact_s=3,
                    finish_s=5,
                    confidence=0.99,
                ),
            )
        return AnalysisResult(
            analysis=AnalyzedSource(source_id=source_id, candidates=candidates), usage=()
        )


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _probe(path: Path) -> SimpleNamespace:
    return SimpleNamespace(path=path, content_sha256=_hash(path.read_bytes()), duration_s=10.0)


def _proxy(source: SimpleNamespace, destination: Path) -> ProxyArtifact:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"proxy-" + source.path.read_bytes())
    return ProxyArtifact(
        path=destination,
        source_sha256=source.content_sha256,
        proxy_sha256=_hash(destination.read_bytes()),
        duration_s=source.duration_s,
        width=480,
        height=854,
        frame_rate=15,
    )


def _render(plan, destination: Path) -> RenderResult:  # type: ignore[no-untyped-def]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"rendered")
    return RenderResult(
        path=destination,
        content_sha256=_hash(destination.read_bytes()),
        duration_s=6,
        profile=OutputProfile(canvas="portrait-9x16", width=1080, height=1920),
        segment_count=len(plan.segments),
    )


def _orchestrator(
    tmp_path: Path, photos: FakePhotos, provider: FakeProvider
) -> SwingcutOrchestrator:
    return SwingcutOrchestrator(
        photos=photos,  # type: ignore[arg-type]
        provider=provider,
        store=RunStore(tmp_path / "runtime"),
        probe=_probe,
        proxy=_proxy,
        render=_render,
        now=lambda: datetime(2026, 9, 5, tzinfo=UTC),
    )


def test_end_to_end_cleanup_incremental_cache_and_rebuild(tmp_path: Path) -> None:
    photos = FakePhotos()
    provider = FakeProvider()
    orchestrator = _orchestrator(tmp_path, photos, provider)

    inspected = orchestrator.inspect("Exact Album")
    assert inspected["video_count"] == 2
    assert inspected["pricing_valid_through"] == "2026-12-31"
    assert inspected["repeat_detected"] is False
    first = orchestrator.run(
        "Exact Album", mode="incremental", import_to_photos=True, confirmed=True
    )

    assert first["stage"] == "succeeded"
    assert provider.calls == ["asset-a", "asset-b"]
    run_dir = orchestrator.store.run_dir(str(first["run_id"]))
    assert not (run_dir / "staged").exists()
    assert not (run_dir / "proxies").exists()
    assert not (run_dir / "output").exists()
    assert not (run_dir / "private.json").exists()
    manifest = orchestrator.store.load_manifest(str(first["run_id"]))
    assert manifest is not None
    assert manifest.accepted_count == 2
    assert manifest.estimated_provider_cost_usd == Decimal("0.10")
    assert manifest.accounted_provider_cost_usd == Decimal("0")
    assert orchestrator.inspect("Exact Album")["repeat_detected"] is True

    orchestrator.run("Exact Album", mode="incremental", import_to_photos=True, confirmed=True)
    assert provider.calls == ["asset-a", "asset-b"]

    orchestrator.run("Exact Album", mode="rebuild", import_to_photos=True, confirmed=True)
    assert provider.calls == ["asset-a", "asset-b", "asset-a", "asset-b"]
    assert photos.imported == 3


def test_source_change_invalidates_only_exact_cache_entry(tmp_path: Path) -> None:
    photos = FakePhotos()
    provider = FakeProvider()
    orchestrator = _orchestrator(tmp_path, photos, provider)
    orchestrator.run("Exact", mode="incremental", import_to_photos=True, confirmed=True)
    photos.contents["asset-b"] = b"changed-source-b"

    orchestrator.run("Exact", mode="incremental", import_to_photos=True, confirmed=True)

    assert provider.calls == ["asset-a", "asset-b", "asset-b"]


def test_individual_source_failure_continues_and_no_swing_skips_import(tmp_path: Path) -> None:
    photos = FakePhotos(fail_second=True)
    provider = FakeProvider()
    orchestrator = _orchestrator(tmp_path, photos, provider)
    result = orchestrator.run("Exact", mode="incremental", import_to_photos=True, confirmed=True)
    manifest = orchestrator.store.load_manifest(str(result["run_id"]))
    assert manifest is not None
    assert manifest.failed_source_count == 1
    assert manifest.accepted_count == 1
    assert photos.imported == 1

    no_swing_photos = FakePhotos()
    no_swing = _orchestrator(tmp_path / "other", no_swing_photos, FakeProvider(no_swings=True))
    result = no_swing.run("Exact", mode="incremental", import_to_photos=True, confirmed=True)
    assert result["stage"] == "succeeded"
    assert no_swing_photos.imported == 0


def test_cancel_status_clean_and_ambiguous_import_fail_closed(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runtime")
    active = RunState(run_id="run-active")
    store.create(active)
    store.save_private(active.run_id, {"schema_version": 1})
    store.request_cancel(active.run_id)
    assert store.cancelled(active.run_id)
    with pytest.raises(StateStoreError, match="terminal"):
        terminal = RunState(run_id="run-terminal").transition(RunStage.FAILED)
        store.create(terminal)
        store.request_cancel(terminal.run_id)

    old = datetime.now(UTC) + timedelta(days=2)
    assert store.clean(now=old)["stale_resumable_runs"] == 1

    photos = FakePhotos()
    orchestrator = _orchestrator(tmp_path / "ambiguous", photos, FakeProvider())
    ambiguous = RunState(run_id="run-ambiguous")
    orchestrator.store.create(ambiguous)
    for stage in (
        RunStage.INVENTORY,
        RunStage.AWAITING_CONFIRMATION,
        RunStage.STAGING,
        RunStage.ANALYZING,
        RunStage.PLANNING,
        RunStage.RENDERING,
        RunStage.VERIFYING,
        RunStage.IMPORTING,
    ):
        ambiguous = ambiguous.transition(stage)
    orchestrator.store.save_state(ambiguous)
    orchestrator.store.save_private(
        ambiguous.run_id,
        {"schema_version": 1, "album": "Exact", "mode": "incremental", "import_started": True},
    )
    with pytest.raises(AmbiguousImportError):
        orchestrator.run(
            "Exact",
            mode="incremental",
            import_to_photos=True,
            confirmed=True,
            resume_run_id=ambiguous.run_id,
        )
