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
