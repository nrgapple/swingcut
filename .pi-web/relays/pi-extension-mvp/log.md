# Relay Log: pi-extension-mvp

## 2026-09-02 — Leg 0 planning

Created the stable MVP plan and Relay packet after resolving interface, destination, automation, repeat, failure, Photos-test, cleanup, spend-cap, and Relay-policy decisions with the user. Revised the agreement at the user's request to make Swingcut a public MIT-licensed GitHub Pi package, installed with `pi install` plus `/swingcut-setup`, with every passing Relay leg pushed directly to `main`. The user explicitly approved and dispatched the Relay. Added the MIT license and established the public GitHub `origin`; no product implementation was started in Leg 0. After the initial push, detected that Git had inferred a local-machine email address for public commit metadata and triggered the privacy intervention rule before spawning Leg 1. The user specified their GitHub author identity and approved the correction. Rewrote both public commits, removed the local-machine email from current history, force-pushed with lease, and configured the repository identity for future Relay commits.

## Leg 1 — contracts, state, and policy alignment

- Updated repository policy to permit only verified add-only import of a newly rendered output while preserving immutability of existing Photos assets/albums.
- Added strict versioned Pydantic contracts for private source/analysis/edit data, privacy-safe retained manifests, bounded enum-based JSONL events, and a validated run-state transition history.
- Added deterministic planning policy for 0.90 confidence gating, explicit rejection, source bounds, two-/three-second padding, duplicate/overlap exclusion, and capture-time/timeline sorting.
- Updated analysis/edit schemas and added synchronized event/manifest schemas; added 21-test coverage of timelines, exclusions, bounds, transitions, and redaction.
- Validation passed: focused Ruff/mypy/unit suite and full `make check` (89% coverage). No intervention trigger fired. Handing off to Leg 2.

## Leg 2 — deterministic media engine (2026-09-02)

- Implemented ffprobe inventory, source hashing, the verified silent 480px/15fps metadata-stripped proxy, source-bounded canvas selection, direct H.264/BT.709/AAC rendering with source audio and silent-segment synthesis, full output decoding checks, and post-operation source hash assertions.
- Selected and documented `photos-h264-aac-sdr-v1`; mixed orientation is letterboxed on a source-bounded landscape canvas, all-portrait uses portrait, and unvalidated PQ/HLG input fails closed rather than being relabelled.
- Added generated synthetic media tests spanning portrait/landscape, audio/silent, mixed frame rates, sanitization, hand-authored plans, audio retention, output verification failures, and unchanged source files.
- Validation passed: focused Ruff/mypy/media tests and `make check` (28 tests, 86% coverage).
- Updated status for Leg 3; no blockers or intervention triggers. Handoff will occur after commit and push to `origin/main`.

## Leg 3 — 2026-09-03

Implemented and routinely validated the productized PhotoKit subsystem: a private bounded LaunchServices Python client, strict exact-album inventory, cancellable sequential iCloud-backed exports with per-source failures and hashes, a Swift add-only `import-output` command with post-create fetch verification, explicit capability smoke coverage, and a stable-path non-ad-hoc installer. Updated source/validation documentation. `make check` passed (33 tests, 85% coverage). Two bounded install attempts stalled at `codesign` awaiting the only local identity's private key; no Photos operation ran and the interrupted build bundle is invalid. Marked `INTERVENTION REQUIRED` for signing-key authorization, permission confirmation, and an exact acceptance album; pushed the coherent passing implementation to `origin/main` and stopped without handoff.

## Intervention resolution — 2026-09-03

The user declined password/keychain work for the unrelated Codex Voice Memo signing identity and explicitly approved creating a dedicated local Swingcut signing identity. Reactivated Leg 3 as `3-acceptance`; the next runner must provision that identity privately and idempotently, validate stable installation, then stop before any fresh Photos permission prompt unless separately approved.

## Leg 3-acceptance — 2026-09-03

Implemented the dedicated, mode-restricted Swingcut self-signed identity/keychain provisioner; integrated it as the only default app-signing source; added designated-requirement stability enforcement and removal/recovery/idempotence documentation. The dedicated artifacts were created without inspecting or modifying the Codex Voice Memo keychain, but macOS's first-time certificate trust authorization waited beyond the bounded 120-second attempt. The certificate remains untrusted, so no signing, installation, or PhotoKit call occurred. Shell checks and `make check` pass (33 tests, 85.24% coverage). Stopped with `INTERVENTION REQUIRED`: the user must approve trust for **Swingcut Local Code Signing** interactively, then resume Leg 3-acceptance and provide the exact private album name if available.

### Leg 3-acceptance trust retry — 2026-09-03

After the user reported trust completion, acceptance correctly failed at signing: the certificate still returned `CSSMERR_TP_NOT_TRUSTED` and no app or PhotoKit operation ran. Fixed the provisioner's false-positive parser by requiring `security verify-cert` before returning the certificate fingerprint. A second bounded trust attempt waited 180 seconds for macOS authorization. `make check` again passes (33 tests, 85.24% coverage). Remained at `INTERVENTION REQUIRED` for successful interactive trust authorization; no handoff.

### Leg 3-acceptance trust placement repair — 2026-09-03

A second user attempt still left the certificate untrusted. Corrected the macOS trust model: the private identity/password remain only in Swingcut's dedicated keychain, while a public certificate copy and per-user code-signing trust record are installed in the login keychain. Updated targeted removal documentation; the Codex product keychain remains untouched. `make check` passes (33 tests, 85.24% coverage). Stopped for one interactive authorization using the corrected provisioner; no app install, PhotoKit call, or handoff occurred.

### Leg 3-acceptance stable install — 2026-09-03

Ran the corrected provisioner; macOS persisted code-signing trust despite the initial command timing out. Added a narrow signing wrapper to temporarily expose only Swingcut's keychain for identity pairing and restore the exact original search list afterward. Two provision checks and two release installations proved a stable fingerprint, designated requirement, CDHash, app path, strict signature, and prompt-free key use. The non-prompting PhotoKit status returned `not-determined`; no Photos authorization request or library operation ran. Updated validation evidence, reran `make check` (33 tests, 85.24% coverage), and stopped with `INTERVENTION REQUIRED` for explicit Photos-prompt approval and the exact private album name; no handoff.

### Leg 3-acceptance completion — 2026-09-03

After explicit user approval of the Photos prompt and an exact private album supplied out-of-band, completed bounded real acceptance. The helper became authorized, inventoried/exported all four assets with zero failures, verified one newly added generated synthetic video, confirmed the exact album remained unchanged and library video count increased by one, and removed all temporary local media. Final capabilities still expose only add-new `import-output` as a write. Recorded aggregate evidence only, reran `make check` (33 tests, 85.24% coverage), marked Leg 3 complete, and handed off to Leg 4 after pushing `main`.

## Leg 4 — Gemini provider and proxy policy (offline implementation; intervention stop)

Implemented the provider-neutral boundary and Gemini 3.8 Flash Interactions adapter with pinned agentic processing, strict structured output, matched processing evidence, explicit timeout/transient retry limits, dated conservative pricing, shared maximum-US$1 attempt authorization, bounded usage records, and `finally` deletion of the sole uploaded file. Added immediate pre-upload proxy re-probe/re-hash enforcement and fail-closed handling for original paths, wrong/unsanitized profiles, changed media, malformed or out-of-bounds responses, unsupported capabilities, unknown usage, untrackable uploads, and deletion debt. Promoted the multi-candidate prompt/schema, documented the pricing and live-test gate, and added comprehensive mocked tests plus a default-skipped private live acceptance test. `make check` passed with 52 tests, 1 gated live test skipped, and 85.86% coverage. Stopped without spawning because the charter requires fresh explicit authorization before the private Gemini call needed to demonstrate Leg 4's exit condition; status states exactly how to authorize/resume.

## Leg 4 continuation — authorized private live test exposed cost-bound blocker

After the user explicitly authorized the existing private test album, privately selected the unique test-marked exact album, confirmed its previously approved aggregate four-video inventory, exported only its shortest source, and generated the approved silent sanitized proxy. Gemini returned a completed interaction and usage, but the calculated usage exceeded the adapter's reserved worst-case estimate, so the adapter failed closed with `CostCapError` before accepting analysis. The `finally` path deleted the provider upload without error, temporary local staging/proxy storage was removed, and no retry or second paid call occurred. No private identifiers, names, paths, media, model prose, or credentials were retained. Official documentation does not expose a hard per-request ceiling for agentic processing/thought/tool-use tokens, so conservative enforcement of the stable US$1 cap cannot currently be demonstrated without guessing. Stopped without spawning and requested a user decision on an enforceable quota/request design versus an explicit stable-plan cost-control change; any second live call also needs approval.

## Leg 4 continuation — approved test-only retry stopped on provider demand

The user authorized another run and a one-time test-only budget override while retaining the production US$1 policy. Repeated the same bounded shortest-source flow from the approved private test album. Gemini 3.8 Flash returned HTTP 500 high-demand failures through the adapter's bounded retry path, so no analysis or usage was returned. The provider upload was deleted in `finally` without error and temporary staged/proxy media was removed. Per the charter's persistent external-service failure trigger, made no further call, kept Leg 5 blocked, and updated status with the cost-bound and provider-availability interventions.

## Leg 4 continuation — Gemini 3.7 comparison succeeded

At the user's explicit request, ran a one-time Gemini 3.7 Flash comparison without changing the repository's pinned 3.8 implementation. The same bounded shortest source from the approved private test album was exported and converted to the approved sanitized proxy. Gemini 3.7 returned one schema-valid accepted candidate at an aggregate calculated paid-tier cost of US$0.019455. Provider-file deletion and local temporary cleanup both completed. No private data or model prose was retained. Stopped without spawning because adopting 3.7 changes the charter-designated stable plan's explicit model and needs an explicit user decision; the production US$1 conservative-bound issue also remains unresolved.

## Leg 4 completion — approved production switch to Gemini 3.7

The user explicitly approved changing the stable plan from Gemini 3.8 Flash to Gemini 3.7 Flash and asked to move on. Updated the charter-designated plan and charter amendment, pinned 3.7 in production, and centralized model name, capability review, paid-tier pricing, and expiry in `MODEL_POLICIES` so future approved upgrades are localized and unknown models fail closed. Updated tests and documentation. The approved 3.7 private run had already produced one schema-valid accepted candidate for US$0.019455 with provider/local cleanup; the conservative two-attempt preflight for all four current test-album sources is US$0.466450. `make check` passes with 52 tests, 1 gated live test skipped, and 85.95% coverage. Marked Leg 4 complete and prepared handoff to Leg 5.

## Leg 5 — end-to-end orchestration implementation; cost-bound intervention stop

Implemented the full Python backend orchestration and machine-readable inspect/run/status/cancel/clean commands, atomic private resumable state, cumulative spend carry-forward, exact versioned incremental cache/rebuild behavior, strict per-source continuation, verified add-only import path, no-swing handling, and ordered terminal cleanup. Added synthetic end-to-end/cache/failure/cancellation/import-ambiguity coverage and durable run documentation. `make check` passes with 56 tests, one gated live test skipped, 83.57% coverage, Swift checks, and package builds. The approved real four-video/206.069-second album preflight was US$0.466450. The first Gemini 3.7 source exceeded its US$0.019929 reserved attempt amount, so the provider failed closed before accepting analysis or making another call; its upload was deleted, no Photos import occurred, and staged/proxy media was removed and verified absent. Marked `INTERVENTION REQUIRED`: a documented enforceable per-request usage ceiling or explicit stable-plan/cost-control change is required; no further paid call or Leg 6 handoff is allowed meanwhile.

### Leg 5 intervention resolution — estimate-only cost policy approved

The user explicitly selected no hard per-run cap: Swingcut must calculate and disclose a dated estimate before explicit confirmation, but actual Gemini agentic usage may exceed it without a fixed maximum. Pricing/estimate failure still blocks paid work, retries remain bounded, and returned usage remains tracked. Amended the charter and stable plan, reactivated the relay, and bounded Leg 5-continuation to remove obsolete cap enforcement, update tests/docs, rerun `make check`, and complete the already-approved real import/cleanup exit test before any Leg 6 handoff.

## Leg 5 continuation — estimate policy and HDR completion; persistent-source intervention

Replaced cap authorization with uncapped estimate/actual usage accounting and updated the public notice, schemas, tests, instructions, plan wording, and docs. The first real continuation analyzed three of four sources, deleted all provider uploads, then correctly failed before import because the album mixed BT.709 and unsupported HLG/BT.2020. With explicit user approval, installed keg-only `ffmpeg-full`, added fail-closed zscale/Hable HDR-to-BT.709 profile `photos-h264-aac-sdr-v2`, synthetic HLG and capability checks, and technical validation. The user visually approved a verified four-segment private review; its local copy was deleted after a verified Photos import. `make check` passed with 57 tests, one gated live test skipped, and 83.84% coverage. A final incremental backend run reused three analyses and retried only the June 29 source; that provider path failed again, but individual-source continuation produced a verified four-segment Photos import and complete terminal cleanup. Marked Leg 5 complete, but stopped before Leg 6 under the persistent external-service intervention trigger: the user must choose another explicit diagnostic/retry, defer the source, or request a bounded provider strategy change.

## Leg 5 continuation — uncapped accounting complete; HDR/provider intervention stop

Replaced cap authorization with an uncapped cumulative usage ledger, allowing estimates above US$1 and returned usage above estimates while retaining estimate/pricing failure gates, bounded retries, strict proxy verification, and deletion debt. Updated public notice/schema, tests, instructions, stable-plan wording, and docs. Focused tests and `make check` passed (56 tests, 1 gated skip, 83.94% coverage, Swift checks, package builds). The approved real four-source run completed strict staging/proxying and reached planning with three accepted source analyses plus one private aggregate provider-interaction failure; all uploads were deleted without debt. Four confident segments were planned, but render failed closed because the album includes HLG/BT.2020 media and the current production profile has no validated HDR-to-SDR path; installed FFmpeg lacks `zscale`. No Photos import or local master exists; four staged sources/proxies remain in private failed-run storage. Marked `INTERVENTION REQUIRED` for a pinned tone-map dependency/profile plus private visual validation and authorization for one provider retry. No handoff or push; Leg 5 did not pass its real exit condition.
