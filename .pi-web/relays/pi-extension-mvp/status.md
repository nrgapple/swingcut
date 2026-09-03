# Relay Status: pi-extension-mvp

State: INTERVENTION REQUIRED — stable signing passes; fresh Photos authorization is required

## Position

- Last completed leg: 2 (deterministic media engine)
- Next leg to run: 3-acceptance (finish real PhotoKit exit condition only)
- Current task: after explicit user approval, authorize Photos and complete exact-album/export/add-only-import acceptance
- Distribution: public GitHub `origin`, MIT licensed; all passing routine changes are on `main`

## Durable Leg 3 implementation and acceptance

- The passing PhotoKit source/add-only destination implementation remains unchanged from commit `0700cfb`; no existing-asset mutation operations are exposed.
- `scripts/provision-signing-identity.sh` idempotently maintains the dedicated `Swingcut Local Code Signing` identity/private key/password under mode-restricted `~/Library/Application Support/Swingcut/signing/`. Only the public trust certificate is copied to the login keychain; the Codex Voice Memo keychain was never opened or changed.
- `scripts/codesign-with-swingcut-identity.py` temporarily prepends only Swingcut's keychain to the user search list for signing and restores the exact original list in `finally`, including ordinary termination signals.
- Two provision checks returned the same certificate fingerprint. Two release installations at `~/Library/Application Support/Swingcut/SwingcutPhotosBridge.app` produced the same designated requirement and CDHash with no private-key prompt; strict signature verification passed and the original keychain search list was restored.
- The installed app's non-prompting `status` operation returned `not-determined`. No authorization request, Photos inventory, export, import, or other library access ran.
- Removal/recovery and acceptance evidence are documented in `docs/icloud-sources.md` and `docs/validation.md`.
- Validation: focused shell/Ruff checks and real signing/install checks pass; `make check` passes with 33 tests and 85.24% coverage.

## Intervention required

The charter requires stopping before a fresh Photos permission dialog. The user must:

1. explicitly approve triggering and handling the macOS Photos read/write permission prompt for **Swingcut Photos Bridge**; and
2. provide the exact name of the private acceptance album (it is not present in the bounded Relay context).

## Resume instructions

Resume Leg `3-acceptance` only. First request authorization through one approved read operation and confirm status becomes `authorized` or `limited`. Then inventory/export only the exact named test album, generate a clearly named synthetic compilation from generated media, import it once through `import-output`, verify creation, and confirm no existing asset mutation capability or behavior. Do not commit private inventories, asset IDs, filenames, media, or metadata. Run focused checks and `make check`, commit/push the passing leg to `origin/main`, and spawn Leg 4 exactly once only after every Leg 3 exit condition passes.
