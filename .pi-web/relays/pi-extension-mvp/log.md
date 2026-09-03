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
