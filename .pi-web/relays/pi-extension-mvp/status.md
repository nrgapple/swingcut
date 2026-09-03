# Relay Status: pi-extension-mvp

State: ACTIVE — Leg 3 signing intervention resolved; ready for Leg 3 acceptance retry

## Position

- Last completed leg: 2 (deterministic media engine)
- Next leg to run: 3-acceptance
- Current task: finish Leg 3 stable signing/install and real PhotoKit acceptance without redoing the passing subsystem
- Distribution: public GitHub `origin`, MIT licensed; passing implementation commit `0700cfb` is on `main`

## Durable Leg 3 implementation

- `src/swingcut/sources/photos.py` provides LaunchServices-only invocation, mode-0700 temporary transport, mode-0600 bounded result/error files, bounded polling, timeout/cancellation, strict exact-album inventory, sequential export, per-source failures, size/path/ID checks, and SHA-256 staging evidence.
- The Swift 0.2.0 helper provides cancellable network-backed export and the sole write capability `import-output`, which creates one new video asset and verifies it by fetching the placeholder identifier. No edit/delete/replace/album mutation APIs exist.
- `scripts/install-photos-bridge-app.sh` targets the stable path `~/Library/Application Support/Swingcut/SwingcutPhotosBridge.app` and currently requires a non-ad-hoc identity.
- Mocked Python tests and native capability smoke tests pass. `make check` passed with 33 tests and 85% coverage.

## Leg 3-acceptance task

The user explicitly approved creating a dedicated local Swingcut signing identity instead of using the unrelated `Codex Local Voice Memo Agent` identity. Implement a minimal idempotent local-signing provisioner and integrate it with build/install:

- create a dedicated self-signed code-signing identity/keychain under mode-restricted `~/Library/Application Support/Swingcut/` storage;
- generate and store any keychain password privately (never print, log, or commit it);
- authorize `/usr/bin/codesign` to use only that dedicated key without a GUI password prompt;
- keep a consistent certificate identity across rebuilds so the installed app has stable TCC identity;
- never modify or reuse the Codex Voice Memo keychain;
- document removal/recovery and test idempotent stable installation.

After installation, query PhotoKit authorization with the non-prompting `status` operation. If status is `not-determined` or any real test would show a fresh permission dialog, stop with `INTERVENTION REQUIRED` before triggering it; the user has approved local signing but has not yet explicitly approved a fresh Photos prompt. If already authorized, complete the exact-album/export/import exit condition using the previously validated private test album only if its exact name is safely discoverable without broad history/log reading; otherwise stop and request the exact name. Use a clearly named generated synthetic compilation, do not commit private inventories/media, verify creation, and confirm the helper exposes no existing-asset mutations.

Run focused checks and `make check`, update status, append one concise log entry, commit and push passing changes directly to `origin/main`, then either hand off to Leg 4 exactly once only if all Leg 3 exit conditions pass, or stop with a precise intervention note.

## Blockers / intervention

- Signing blocker resolved by explicit user approval for a dedicated local Swingcut identity.
- A fresh Photos permission prompt and the exact private acceptance album remain unapproved/unknown; follow the stop rules above.
