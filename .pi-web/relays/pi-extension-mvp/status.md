# Relay Status: pi-extension-mvp

State: ACTIVE — Leg 2 complete; ready for Leg 3

## Position

- Last completed leg: 2 (deterministic media engine)
- Next leg to run: 3
- Current task: Leg 3 — productize PhotoKit source and add-only destination
- Distribution: public GitHub `origin`, MIT licensed; passing legs push directly to `main`

## Completed in Leg 2

- Added normalized ffprobe inventory with content hashes, display-orientation handling, frame rates, audio/video/color facts, and metadata visibility.
- Added verified `silent-h264-480w-15fps-v1` proxy generation: full-duration, no audio, no upscaling, metadata/chapter stripping, prohibited-metadata checks, and unchanged-source hashing.
- Added source-bounded portrait/landscape canvas selection and direct-from-source H.264 High/BT.709/AAC rendering with mixed-orientation letterboxing, source-audio retention, generated silence for silent clips, full decode verification, and unchanged-source hashing.
- Documented the deterministic profiles and explicit fail-closed behavior for unvalidated PQ/HLG tone mapping in `docs/media-engine.md`.
- Added runtime-generated synthetic coverage for portrait/landscape, audio/silent, 24 and 30000/1001 fps, proxy sanitization, hand-authored plans, mixed rendering, audible output, validation failures, and immutable source hashes.
- Validation: focused Ruff, mypy, and media tests passed; `make check` passed with 28 tests and 86% coverage.

## Relevant context for Leg 3

Read:

- `.pi-web/relays/pi-extension-mvp/charter.md`
- this file
- `docs/pi-extension-mvp-plan.md`: Architecture / Native PhotoKit helper, Leg 3, and Validation
- `AGENTS.md`
- existing `native/SwingcutPhotosBridge/` sources and tests
- existing PhotoKit/source-related Python and script layout only as needed
- `src/swingcut/contracts.py` for strict/private contract conventions

Implement only the PhotoKit source/add-only destination subsystem: Python LaunchServices client with bounded polling/cancellation/private result files, hardened exact-album inventory and sequential export, narrow native `import-output` with post-create verification, and stable signed-app user installation. Do not add edit/delete/album-mutation capabilities. A real clearly named test import is approved, but stop if fresh manual authorization or interaction is required.

## Required durable progress

Implement only Leg 3. Add tests, run focused checks and `make check`, update this status, append one concise log entry, commit coherent changes, push the passing leg to `origin/main`, then hand off exactly once if no intervention trigger fires.

## Blockers / intervention

- No blocker or intervention trigger is currently known.
- PQ/HLG rendering intentionally fails closed pending future approved private-corpus tone-map validation; this does not block Leg 3.
