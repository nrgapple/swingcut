# Swingcut Repository Instructions

## Purpose and boundaries

Swingcut is a local-first macOS golf-video editing tool. It detects apparent ball-striking swings and produces source-derived compilations. It must not provide coaching, biomechanics, medical analysis, identity recognition, or generative alteration of the golfer or swing.

## Safety and privacy

- Never commit, log, or copy personal videos, Photos-library exports, proxies, location metadata, or API credentials.
- Never upload original-resolution media. Gemini may receive only the explicitly generated low-resolution proxy selected by the user.
- Strip source metadata from every cloud proxy. Keep proxy audio disabled unless the approved evaluation changes that policy.
- Never silently broaden the cloud boundary or fall back to uploading an original.
- Never read the internal Photos database directly or automate `icloud.com`; use authorized PhotoKit APIs.
- Treat all existing Photos assets and albums as immutable. The sole permitted Photos write is adding one newly rendered Swingcut output as a new asset through the approved PhotoKit bridge, followed by creation verification. Never edit, delete, replace, reorganize, or add/remove assets from albums.
- Cut and render only from controlled local staged copies. Verify source hashes remain unchanged.
- Delete staged media and proxies after a successful verified render. Preserve failed-run media only according to the eventual documented retention policy.
- Live Gemini tests must be explicit, opt-in, spend-bounded, and must delete uploaded Files API resources.

## Architecture rules

- Python 3.12+ owns orchestration. Swift owns the narrow PhotoKit bridge. FFmpeg/ffprobe own media transformation and inspection.
- Keep probabilistic analysis separate from deterministic rendering through versioned Pydantic/JSON schemas and a validated edit plan.
- Keep Gemini behind `providers/base.py`; do not call provider APIs from media or source modules.
- Keep PhotoKit behind the Swift JSONL bridge; Python must not depend on Photos database internals.
- Pin concrete model, prompt, schema, and proxy-setting versions in run manifests.
- Fail closed on malformed model output, impossible timelines, missing media, permission denial, or uncertain candidates.
- Do not implement Gemini Omni or other pixel-generating edits.

## Planned source layout

- `src/swingcut/sources/` — local, iCloud Drive, and Photos source adapters
- `src/swingcut/media/` — probe, proxy, local analysis, render, and verification
- `src/swingcut/providers/` — model-provider boundary and Gemini adapter
- `src/swingcut/planning/` — classification and validated edit plans
- `src/swingcut/state/` — resumable runs, cache, and cleanup
- `native/SwingcutPhotosBridge/` — read-only PhotoKit bridge
- `prompts/` and `schemas/` — versioned model contracts
- `tests/` — synthetic fixtures and uncommitted private-corpus guidance

## Development workflow

```bash
make setup
make check
```

Focused commands:

```bash
make doctor
make test
make test-swift
make lint
make format-check
make build
```

- Add tests with every behavior change.
- Use mocked Gemini responses in routine tests. Never make a live provider call from the default test suite.
- Use generated synthetic media in committed tests. Keep the private golden corpus outside Git.
- Run `make check` before reporting completion.
- Do not weaken privacy assertions, coverage thresholds, lint rules, or timeline validation to make tests pass.
- Record durable architectural decisions under `docs/`; keep disposable feasibility experiments outside this repository under the workspace `scratch/` directory until promoted.

## Current phase

This repository is an initialized scaffold. Implement the approved milestones in order: deterministic core before provider integration, then Photos/iCloud Photos before iCloud Drive. Representative private footage must resolve proxy, audio, HDR, slow-motion, and retention settings before those behaviors are treated as production defaults.
