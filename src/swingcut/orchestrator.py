"""End-to-end local-first Swingcut orchestration."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import TypeAdapter

from swingcut.contracts import (
    AnalyzedSource,
    EventMessage,
    EventType,
    NoticeCode,
    RunEvent,
    RunManifest,
    RunStage,
    RunState,
    SourceAsset,
)
from swingcut.media.probe import MediaProbeError, probe_media
from swingcut.media.proxy import (
    PROXY_PROFILE_VERSION,
    ProxyArtifact,
    ProxyGenerationError,
    generate_proxy,
)
from swingcut.media.render import RenderResult, render_compilation
from swingcut.planning.edit_plan import build_edit_plan
from swingcut.providers.base import (
    AnalysisProvider,
    CostEstimateError,
    DeletionDebtError,
    ProviderError,
    UsageLedger,
)
from swingcut.providers.gemini import (
    ANALYSIS_POLICY_VERSION,
    PROMPT_SHA256,
    SCHEMA_SHA256,
)
from swingcut.sources.photos import (
    PhotoAlbumInventory,
    PhotosBridgeCancelled,
    PhotosBridgeClient,
)
from swingcut.state.store import CacheKey, RunStore

VALIDATOR_VERSION = "strict-edit-plan-v1"
_RUN_ID_PREFIX = "run-"


class OrchestrationError(RuntimeError):
    """A run failed closed without exposing private details."""


class AmbiguousImportError(OrchestrationError):
    """A resume cannot prove whether Photos already created the output."""


class RunCancelled(OrchestrationError):
    """Cancellation was observed before Photos mutation."""


EventSink = Callable[[RunEvent], None]


class SwingcutOrchestrator:
    def __init__(
        self,
        *,
        photos: PhotosBridgeClient,
        provider: AnalysisProvider,
        store: RunStore,
        probe: Callable[[Path], Any] = probe_media,
        proxy: Callable[[Any, Path], ProxyArtifact] = generate_proxy,
        render: Callable[[Any, Path], RenderResult] = render_compilation,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.photos = photos
        self.provider = provider
        self.store = store
        self.probe = probe
        self.proxy = proxy
        self.render = render
        self.now = now

    def inspect(self, album: str) -> dict[str, object]:
        inventory = self.photos.inventory_album(album)
        durations = tuple(asset.duration_seconds for asset in inventory.assets)
        estimate = self.provider.estimate_run_cost_for_durations(durations)
        return {
            "schema_version": 1,
            "album": album,
            "video_count": len(inventory.assets),
            "total_duration_s": round(sum(durations), 3),
            "cloud_disclosure": "full-duration silent metadata-stripped 480px proxies only",
            "estimated_gemini_cost_usd": str(estimate),
            "repeat_detected": self.store.album_seen(_album_fingerprint(album)),
            "repeat_modes": ["incremental", "rebuild"],
            "requires_confirmation": True,
        }

    def run(
        self,
        album: str,
        *,
        mode: Literal["incremental", "rebuild"],
        import_to_photos: bool,
        confirmed: bool,
        event_sink: EventSink | None = None,
        resume_run_id: str | None = None,
    ) -> dict[str, object]:
        if not confirmed:
            raise OrchestrationError("run requires explicit confirmation")
        if not import_to_photos:
            raise OrchestrationError("MVP output destination must be verified Photos import")
        state, private = self._open_run(album, mode, resume_run_id)
        run_id = state.run_id
        try:
            state, private = self._inventory(state, private, album, event_sink)
            state, private = self._stage(state, private, mode, event_sink)
            state, private = self._analyze(state, private, mode, event_sink)
            state, private, has_output = self._plan(state, private, event_sink)
            if has_output:
                state, private = self._render(state, private, event_sink)
                state, private = self._import(state, private, event_sink)
            state = self._cleanup(state, private, event_sink)
            self.store.mark_album_seen(_album_fingerprint(album))
            self.store.remove_private_record(run_id)
            self._emit(event_sink, state, EventType.COMPLETE, EventMessage.RUN_SUCCEEDED)
            return state.public_summary()
        except (RunCancelled, PhotosBridgeCancelled):
            current = self.store.load_state(run_id)
            if current.stage not in {RunStage.IMPORTING, RunStage.CLEANUP}:
                current = self._transition(current, RunStage.CANCELLED)
                self._emit(
                    event_sink,
                    current,
                    EventType.ERROR,
                    EventMessage.RUN_CANCELLED,
                    notice=NoticeCode.CANCELLED,
                )
            raise RunCancelled("run cancelled") from None
        except Exception as error:
            current = self.store.load_state(run_id)
            if current.stage not in {RunStage.SUCCEEDED, RunStage.FAILED, RunStage.CANCELLED}:
                current = self._transition(current, RunStage.FAILED)
            self._emit(
                event_sink,
                current,
                EventType.ERROR,
                EventMessage.RUN_FAILED,
                notice=_notice_for(error),
            )
            if isinstance(error, (CostEstimateError, DeletionDebtError, AmbiguousImportError)):
                raise
            raise OrchestrationError("run failed; private diagnostics retained") from error

    def _open_run(
        self, album: str, mode: str, resume_run_id: str | None
    ) -> tuple[RunState, dict[str, Any]]:
        if resume_run_id is not None:
            state = self.store.load_state(resume_run_id)
            private = self.store.load_private(resume_run_id)
            if private.get("album") != album or private.get("mode") != mode:
                raise OrchestrationError("resume arguments do not match the private run record")
            if state.stage in {RunStage.FAILED, RunStage.CANCELLED, RunStage.SUCCEEDED}:
                raise OrchestrationError("terminal runs cannot be resumed")
            return state, private
        run_id = _RUN_ID_PREFIX + uuid.uuid4().hex
        state = RunState(run_id=run_id)
        self.store.create(state)
        private = {"schema_version": 1, "album": album, "mode": mode, "failures": []}
        self.store.save_private(run_id, private)
        return state, private

    def _inventory(
        self,
        state: RunState,
        private: dict[str, Any],
        album: str,
        sink: EventSink | None,
    ) -> tuple[RunState, dict[str, Any]]:
        if state.stage is RunStage.CREATED:
            state = self._transition(state, RunStage.INVENTORY)
        if state.stage is RunStage.INVENTORY:
            self._cancel(state.run_id)
            self._emit(sink, state, EventType.STATUS, EventMessage.INVENTORY_STARTED)
            inventory = self.photos.inventory_album(
                album, cancelled=lambda: self.store.cancelled(state.run_id)
            )
            private["inventory"] = inventory.model_dump(mode="json")
            self.store.save_private(state.run_id, private)
            state = self._transition(state, RunStage.AWAITING_CONFIRMATION)
            self._emit(sink, state, EventType.STATUS, EventMessage.AWAITING_CONFIRMATION)
        return state, private

    def _stage(
        self,
        state: RunState,
        private: dict[str, Any],
        mode: str,
        sink: EventSink | None,
    ) -> tuple[RunState, dict[str, Any]]:
        if state.stage is RunStage.AWAITING_CONFIRMATION:
            state = self._transition(state, RunStage.STAGING)
        if state.stage is not RunStage.STAGING:
            return state, private
        self._cancel(state.run_id)
        self._emit(sink, state, EventType.STATUS, EventMessage.STAGING_MEDIA)
        run_dir = self.store.run_dir(state.run_id)
        for name in ("staged", "proxies"):
            target = run_dir / name
            if target.exists():
                shutil.rmtree(target)
        inventory = PhotoAlbumInventory.model_validate_json(json.dumps(private["inventory"]))
        batch = self.photos.export_album(
            inventory, run_dir / "staged", cancelled=lambda: self.store.cancelled(state.run_id)
        )
        failures: list[dict[str, str]] = [item.model_dump() for item in batch.failures]
        sources: list[dict[str, Any]] = []
        proxies: list[dict[str, Any]] = []
        keys: list[dict[str, Any]] = []
        records = {asset.asset_id: asset for asset in inventory.assets}
        for index, staged in enumerate(batch.exported, start=1):
            self._cancel(state.run_id)
            try:
                media = self.probe(staged.path)
                record = records[staged.asset_id]
                creation_time = _parse_creation_time(record.creation_date)
                source = SourceAsset(
                    source_id=staged.asset_id,
                    source_path=staged.path,
                    content_sha256=media.content_sha256,
                    duration_s=media.duration_s,
                    creation_time=creation_time,
                )
                artifact = self.proxy(media, run_dir / "proxies" / f"proxy-{index:05d}.mp4")
                key = _cache_key(record.model_dump(mode="json"), source, artifact)
                sources.append(source.model_dump(mode="json"))
                proxies.append(artifact.model_dump(mode="json"))
                keys.append(key.model_dump(mode="json"))
            except (OSError, ValueError, MediaProbeError, ProxyGenerationError) as error:
                failures.append({"asset_id": staged.asset_id, "reason": str(error)})
        private.update(
            {"sources": sources, "proxies": proxies, "cache_keys": keys, "failures": failures}
        )
        self.store.save_private(state.run_id, private)
        artifacts = TypeAdapter(tuple[ProxyArtifact, ...]).validate_json(json.dumps(proxies))
        cache_keys = TypeAdapter(tuple[CacheKey, ...]).validate_json(json.dumps(keys))
        paid_artifacts = tuple(
            artifact
            for artifact, key in zip(artifacts, cache_keys, strict=True)
            if mode == "rebuild" or self.store.cache_get(key) is None
        )
        estimate = self.provider.estimate_run_cost(paid_artifacts)
        private["estimated_provider_cost_usd"] = str(estimate)
        self.store.save_private(state.run_id, private)
        state = self._transition(state, RunStage.ANALYZING)
        return state, private

    def _analyze(
        self,
        state: RunState,
        private: dict[str, Any],
        mode: str,
        sink: EventSink | None,
    ) -> tuple[RunState, dict[str, Any]]:
        if state.stage is not RunStage.ANALYZING:
            return state, private
        artifacts = TypeAdapter(tuple[ProxyArtifact, ...]).validate_json(
            json.dumps(private["proxies"])
        )
        sources = TypeAdapter(tuple[SourceAsset, ...]).validate_json(json.dumps(private["sources"]))
        keys = TypeAdapter(tuple[CacheKey, ...]).validate_json(json.dumps(private["cache_keys"]))
        analyses_by_id = {
            item.source_id: item
            for item in TypeAdapter(tuple[AnalyzedSource, ...]).validate_json(
                json.dumps(private.get("analyses", []))
            )
        }
        ledger = UsageLedger(accounted_usd=Decimal(str(private.get("accounted_usage_usd", "0"))))
        total = len(sources)
        for index, (source, artifact, key) in enumerate(
            zip(sources, artifacts, keys, strict=True), start=1
        ):
            self._cancel(state.run_id)
            self._emit(
                sink, state, EventType.PROGRESS, EventMessage.ANALYZING_MEDIA, index - 1, total
            )
            if source.source_id in analyses_by_id:
                continue
            cached = self.store.cache_get(key) if mode == "incremental" else None
            try:
                if cached is not None:
                    analyses_by_id[source.source_id] = cached
                else:
                    try:
                        result = self.provider.analyze(
                            artifact, source_id=source.source_id, ledger=ledger
                        )
                        analyses_by_id[source.source_id] = result.analysis
                        self.store.cache_put(key, result.analysis)
                    except (CostEstimateError, DeletionDebtError):
                        raise
                    except ProviderError as error:
                        private["failures"].append(
                            {"asset_id": source.source_id, "reason": str(error)}
                        )
            finally:
                private["accounted_usage_usd"] = str(ledger.accounted_usd)
                private["analyses"] = [
                    item.model_dump(mode="json") for item in analyses_by_id.values()
                ]
                self.store.save_private(state.run_id, private)
        self._emit(sink, state, EventType.PROGRESS, EventMessage.ANALYZING_MEDIA, total, total)
        state = self._transition(state, RunStage.PLANNING)
        return state, private

    def _plan(
        self, state: RunState, private: dict[str, Any], sink: EventSink | None
    ) -> tuple[RunState, dict[str, Any], bool]:
        if state.stage is not RunStage.PLANNING:
            has_output = state.stage in {
                RunStage.RENDERING,
                RunStage.VERIFYING,
                RunStage.IMPORTING,
            } or bool(private.get("plan", {}).get("segments"))
            return state, private, has_output
        self._cancel(state.run_id)
        self._emit(sink, state, EventType.STATUS, EventMessage.PLANNING_EDIT)
        sources = TypeAdapter(tuple[SourceAsset, ...]).validate_json(json.dumps(private["sources"]))
        analyses = TypeAdapter(tuple[AnalyzedSource, ...]).validate_json(
            json.dumps(private.get("analyses", []))
        )
        result = build_edit_plan(sources, analyses)
        private["plan"] = result.plan.model_dump(mode="json")
        private["excluded_count"] = result.exclusions.total
        self.store.save_private(state.run_id, private)
        if not result.plan.segments:
            self._emit(
                sink,
                state,
                EventType.WARNING,
                EventMessage.NO_CONFIDENT_SWINGS,
                notice=NoticeCode.NO_CONFIDENT_SWINGS,
            )
            state = self._transition(state, RunStage.CLEANUP)
            return state, private, False
        state = self._transition(state, RunStage.RENDERING)
        return state, private, True

    def _render(
        self, state: RunState, private: dict[str, Any], sink: EventSink | None
    ) -> tuple[RunState, dict[str, Any]]:
        from swingcut.contracts import EditPlan

        if state.stage is RunStage.RENDERING:
            self._cancel(state.run_id)
            self._emit(sink, state, EventType.STATUS, EventMessage.RENDERING_OUTPUT)
            output_dir = self.store.run_dir(state.run_id) / "output"
            output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(output_dir, 0o700)
            output = output_dir / f"Swingcut Highlight {self.now():%Y-%m-%d %H%M%S}.mp4"
            result = self.render(EditPlan.model_validate_json(json.dumps(private["plan"])), output)
            private["render"] = result.model_dump(mode="json")
            self.store.save_private(state.run_id, private)
            state = self._transition(state, RunStage.VERIFYING)
        if state.stage is RunStage.VERIFYING:
            self._emit(sink, state, EventType.STATUS, EventMessage.VERIFYING_OUTPUT)
            state = self._transition(state, RunStage.IMPORTING)
        return state, private

    def _import(
        self, state: RunState, private: dict[str, Any], sink: EventSink | None
    ) -> tuple[RunState, dict[str, Any]]:
        if state.stage is not RunStage.IMPORTING:
            return state, private
        if "import" in private:
            state = self._transition(state, RunStage.CLEANUP)
            return state, private
        if private.get("import_started"):
            raise AmbiguousImportError(
                "Photos import may have completed; inspect Photos before deciding recovery"
            )
        self._cancel(state.run_id)
        self._emit(sink, state, EventType.STATUS, EventMessage.IMPORTING_OUTPUT)
        private["import_started"] = True
        self.store.save_private(state.run_id, private)
        render = RenderResult.model_validate_json(json.dumps(private["render"]))
        imported = self.photos.import_output(render.path)
        private["import"] = imported.model_dump(mode="json")
        self.store.save_private(state.run_id, private)
        state = self._transition(state, RunStage.CLEANUP)
        return state, private

    def _cleanup(
        self, state: RunState, private: dict[str, Any], sink: EventSink | None
    ) -> RunState:
        if state.stage is not RunStage.CLEANUP:
            return state
        self._emit(sink, state, EventType.STATUS, EventMessage.CLEANING_UP)
        self.store.clean_run_media(state.run_id)
        manifest = RunManifest(
            run_id=state.run_id,
            state=RunStage.SUCCEEDED,
            source_count=len(private.get("inventory", {}).get("assets", [])),
            source_duration_s=sum(
                asset.get("duration_seconds", 0)
                for asset in private.get("inventory", {}).get("assets", [])
            ),
            accepted_count=len(private.get("plan", {}).get("segments", [])),
            excluded_count=int(private.get("excluded_count", 0)),
            failed_source_count=len(private.get("failures", [])),
            estimated_provider_cost_usd=Decimal(
                str(private.get("estimated_provider_cost_usd", "0"))
            ),
            accounted_provider_cost_usd=Decimal(str(private.get("accounted_usage_usd", "0"))),
            proxy_profile_version=PROXY_PROFILE_VERSION,
            model_version=ANALYSIS_POLICY_VERSION,
            prompt_sha256=PROMPT_SHA256,
            analysis_schema_sha256=SCHEMA_SHA256,
            validator_version=VALIDATOR_VERSION,
            output_profile=(
                private.get("render", {}).get("profile", {}).get("version")
                if private.get("render")
                else None
            ),
        )
        self.store.save_manifest(manifest)
        return self._transition(state, RunStage.SUCCEEDED)

    def _transition(self, state: RunState, destination: RunStage) -> RunState:
        state = state.transition(destination, at=self.now())
        self.store.save_state(state)
        return state

    def _cancel(self, run_id: str) -> None:
        if self.store.cancelled(run_id):
            raise RunCancelled("run cancelled")

    def _emit(
        self,
        sink: EventSink | None,
        state: RunState,
        event: EventType,
        message: EventMessage,
        completed: int | None = None,
        total: int | None = None,
        *,
        notice: NoticeCode | None = None,
    ) -> None:
        if sink is not None:
            sink(
                RunEvent(
                    event=event,
                    run_id=state.run_id,
                    stage=state.stage,
                    message=message,
                    completed=completed,
                    total=total,
                    notice_code=notice,
                    occurred_at=self.now(),
                )
            )


def _parse_creation_time(value: str | None) -> datetime:
    if value is None:
        raise ValueError("source creation time is required for deterministic ordering")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("source creation time must include timezone")
    return parsed


def _album_fingerprint(album: str) -> str:
    return hashlib.sha256(album.encode()).hexdigest()


def _cache_key(record: dict[str, Any], source: SourceAsset, proxy: ProxyArtifact) -> CacheKey:
    identity = hashlib.sha256(source.source_id.encode()).hexdigest()
    version_payload = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return CacheKey(
        source_identity_sha256=identity,
        source_version_sha256=hashlib.sha256(version_payload.encode()).hexdigest(),
        content_sha256=source.content_sha256,
        proxy_profile=proxy.profile_version,
        model=ANALYSIS_POLICY_VERSION,
        prompt_sha256=PROMPT_SHA256,
        schema_sha256=SCHEMA_SHA256,
        validator_version=VALIDATOR_VERSION,
    )


def _notice_for(error: Exception) -> NoticeCode:
    if isinstance(error, CostEstimateError):
        return NoticeCode.COST_ESTIMATE_UNAVAILABLE
    if isinstance(error, PhotosBridgeCancelled):
        return NoticeCode.CANCELLED
    return (
        NoticeCode.IMPORT_FAILED
        if isinstance(error, AmbiguousImportError)
        else NoticeCode.SOURCE_FAILURE
    )
