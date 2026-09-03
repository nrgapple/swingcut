# Relay Status: pi-extension-mvp

State: INTERVENTION REQUIRED — Leg 3 implementation passes routine checks, but signed-app/Photos acceptance is blocked

## Position

- Last completed leg: 2 (deterministic media engine)
- Next leg to run: 3 (finish external acceptance only; do not redo passing implementation)
- Current task: complete Leg 3 stable-install and real PhotoKit acceptance after the manual authorization below
- Distribution: public GitHub `origin`, MIT licensed; passing implementation pushed directly to `main`

## Durable Leg 3 implementation

- Added `src/swingcut/sources/photos.py`: LaunchServices-only app invocation, mode-0700 temporary transport, mode-0600 bounded result/error files, bounded polling, timeout/cancellation marker, strict responses, exact-album checking, sequential export, per-source failures, size/path/ID checks, and SHA-256 staging evidence.
- Extended the Swift helper to version 0.2.0 with cancellable network-backed export and the sole write capability `import-output`, which creates one new video asset and verifies it by fetching the placeholder identifier. No edit/delete/replace/album mutation APIs exist.
- Added a capability smoke test and Python mocked tests for exact names, injection-safe argument arrays, private response permissions, sequential/partial export behavior, checksums, cancellation/timeouts, symlink rejection, and verified import responses.
- Added an idempotent stable-path installer at `scripts/install-photos-bridge-app.sh`; it rejects ad-hoc signatures and targets `~/Library/Application Support/Swingcut/SwingcutPhotosBridge.app`.
- Updated `README.md`, `docs/icloud-sources.md`, and `docs/validation.md`.
- Validation: `make check` passed with 33 tests, 85% coverage, strict Python/Swift formatting and typing, native version/capability smoke tests, and Python/Swift package builds.

## Intervention required

Two installer attempts (300 seconds and 180 seconds, the second with timestamping disabled) stalled at `codesign` while using the only available identity, `Codex Local Voice Memo Agent`. The process appears to require Keychain/private-key authorization; the interrupted `build/SwingcutPhotosBridge.app` is invalid and no stable app was installed. No Photos access or real import was attempted.

The user must:

1. unlock/authorize private-key use for that code-signing identity (or set `SWINGCUT_CODESIGN_IDENTITY` to another usable non-ad-hoc identity);
2. confirm that the next runner may handle any fresh Photos permission prompt for the newly installed stable app; and
3. provide/confirm the exact clearly named test album for the acceptance run.

Then rerun Leg 3 only: run `make install-photos-app`, confirm the stable signature/path, inventory and sequentially export that exact album, generate a clearly named synthetic compilation, import and verify the one new asset, confirm existing assets were not altered, rerun `make check`, update Relay state/log, commit any acceptance documentation, push `main`, and hand off to Leg 4. Do not spawn Leg 4 before this exit condition is demonstrated.
