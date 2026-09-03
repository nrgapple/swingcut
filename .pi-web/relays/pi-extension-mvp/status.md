# Relay Status: pi-extension-mvp

State: INTERVENTION REQUIRED — corrected per-user trust placement requires one interactive authorization

## Position

- Last completed leg: 2 (deterministic media engine)
- Next leg to run: 3-acceptance (resume external acceptance only)
- Current task: authorize the already-created Swingcut certificate, then finish stable-install and real PhotoKit acceptance
- Distribution: public GitHub `origin`, MIT licensed; passing routine changes are on `main`

## Durable Leg 3 implementation

- The passing PhotoKit source/add-only destination implementation remains unchanged from commit `0700cfb`; mocked Python tests and native capability smoke tests pass.
- `scripts/provision-signing-identity.sh` idempotently creates only `~/Library/Application Support/Swingcut/signing/swingcut-signing.keychain-db`, a self-signed `Swingcut Local Code Signing` identity, its public certificate, and a generated private keychain-password file. Files are mode `0600`; parent directories are mode `0700`. It now verifies certificate trust with `security verify-cert` rather than accepting an untrusted `find-identity` match.
- The signing keychain is not added to the user search list. The provisioner grants `/usr/bin/codesign` access to the dedicated key only. The private key/password remain there; only the public certificate and its code-signing trust record go into the per-user login keychain, as macOS requires. It does not inspect, reuse, unlock, or change the Codex Voice Memo keychain.
- App builds now use only the dedicated keychain. Installation rejects ad-hoc signatures and refuses to replace an installed helper when its designated requirement changes.
- Removal/recovery and idempotence checks are documented in `docs/icloud-sources.md` and `docs/validation.md`.
- Validation: shell syntax and `git diff --check` pass; `make check` passes with 33 tests and 85.24% coverage.

## Intervention required

After a second user trust attempt, `security verify-cert` still returned `CSSMERR_TP_NOT_TRUSTED`. The cause was trust placement: macOS requires a per-user trust anchor's public certificate in the login keychain even though the private signing key remains isolated in Swingcut's dedicated keychain. The provisioner and removal documentation now implement that separation. No app was installed and no PhotoKit operation ran.

The user must:

1. Pull/use current `main`, then in an interactive macOS Terminal run `cd /Users/nrgapple/Projects/swingcut && make provision-signing-identity`. Complete the macOS account-authorization dialog specifically for **Swingcut Local Code Signing**. Wait for the command to exit successfully and print a certificate fingerprint. Do not authorize or alter the Codex Voice Memo identity.
2. Confirm successful command completion to resume this Relay. If known, also provide the exact private acceptance album name; it is not present in the bounded Relay context.

## Resume instructions

Resume Leg `3-acceptance` only. Run the provisioner twice and confirm one stable fingerprint, install twice and confirm one stable designated requirement with no key-use prompt, then invoke only the installed app's non-prompting `status` operation. If status is `not-determined`, stop before any permission request. If authorized/limited and the exact album is known, complete the exact inventory/export and clearly named synthetic add-only import exit condition. Do not spawn Leg 4 until all Leg 3 exit conditions pass.
