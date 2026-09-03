# Relay Status: pi-extension-mvp

State: ACTIVE — Leg 1 complete; ready for Leg 2

## Position

- Last completed leg: 1 (contracts, state, and policy alignment)
- Next leg to run: 2
- Current task: Leg 2 — deterministic media engine
- Distribution: public GitHub `origin`, MIT licensed; passing legs push directly to `main`

## Completed in Leg 1

- Aligned `AGENTS.md` with the approved add-only, post-create-verified Photos output boundary while keeping all existing assets and albums immutable.
- Added strict Pydantic source, analysis, edit-plan, privacy-safe manifest, bounded event, and durable run-state contracts in `src/swingcut/contracts.py`.
- Added deterministic confidence/exclusion, source-bound padding, overlap/duplicate handling, and capture-time/timeline ordering in `src/swingcut/planning/edit_plan.py`.
- Updated analysis/edit-plan schemas and added synchronized public run-event/run-manifest JSON schemas.
- Added unit coverage for malformed timelines, uncertainty and confidence exclusions, source bounds, padding/sorting, state transitions/history, and sensitive-field exclusion.
- Validation: focused Ruff, mypy, and unit tests passed; `make check` passed with 21 tests and 89% coverage.

## Relevant context for Leg 2

Read:

- `.pi-web/relays/pi-extension-mvp/charter.md`
- this file
- `docs/pi-extension-mvp-plan.md`: Architecture, Media and planning pipeline, Leg 2, and Validation
- `AGENTS.md`
- `src/swingcut/contracts.py`
- `src/swingcut/planning/edit_plan.py`
- `schemas/edit-plan-v1.schema.json`
- existing media layout, Makefile, and unit-test conventions

Implement only the deterministic media-engine subsystem: ffprobe inventory, sanitized proxy generation, segment rendering with source audio, orientation/canvas profile selection, output verification, synthetic fixtures, and unchanged-source hash assertions. Keep the existing low-resolution silent 480px/15fps proxy policy; changing cloud disclosure requires intervention.

## Required durable progress

Implement only Leg 2. Add tests, run focused checks and `make check`, update this status, append one concise log entry, commit coherent changes, push the passing leg to `origin/main`, then hand off exactly once if no intervention trigger fires.

## Blockers / intervention

- No blocker or intervention trigger is currently known.
