# Relay Status: pi-extension-mvp

State: ACTIVE — Leg 3 complete; ready for Gemini provider milestone

## Position

- Last completed leg: 3 (productized PhotoKit source and add-only destination)
- Next leg to run: 4
- Current task: implement the bounded Gemini provider and proxy-policy milestone from `docs/pi-extension-mvp-plan.md` lines 173-182 and the provider/privacy boundaries in repository `AGENTS.md`
- Distribution: public GitHub `origin`, MIT licensed; passing legs are pushed directly to `main`

## Completed Leg 3 evidence

- The Python LaunchServices client provides bounded private transport, exact-album inventory, cancellable sequential export, per-source failures, strict response checks, and SHA-256 staging evidence.
- The Swift 0.2.0 helper's only write operation is `import-output`, which creates and verifies one new video asset. Capability inspection exposes no edit/delete/replace/album mutation operations.
- Swingcut's dedicated self-signed identity is private and mode-restricted under `~/Library/Application Support/Swingcut/signing/`; the unrelated Codex Voice Memo keychain was never opened or changed.
- Two provision checks and two release installs demonstrated one stable certificate fingerprint, designated requirement, CDHash, and stable app path without key-use prompts. Temporary keychain search-list changes were fully restored.
- After explicit user authorization, a bounded real PhotoKit run inventoried and exported all four assets from the exact private test album with zero failures, added and verified one clearly named generated synthetic compilation, confirmed the exact album inventory was unchanged and total video count increased by exactly one, and removed all local acceptance media.
- Final PhotoKit status is `authorized`. Aggregate evidence is in `docs/validation.md`; no private album name, asset ID, filename, metadata, or media was committed.
- `make check` passes with 33 tests and 85.24% coverage.

## Leg 4 task

Implement only Plan Leg 4:

- add `providers/base.py` and a Gemini 3.8 Flash Interactions adapter;
- enforce agentic processing, structured output, timeout/retry rules, a conservative US$1 cap, usage records, and `finally` deletion of every uploaded file;
- fail closed on malformed output, missing processing evidence, unsupported capability, deletion debt, or any attempt to upload outside the verified low-resolution silent metadata-stripped proxy boundary;
- use mocked provider tests by default and gate any live private test explicitly.

Exit only when mocked tests cover all failure/cleanup paths and an explicitly approved private live run produces validated analysis without leaving provider files. Follow charter intervention rules for service failures, spending uncertainty, credentials, cloud-boundary changes, or any live call not already explicitly approved.

## Relevant context

- Read only Plan Leg 4 and the architecture/privacy sections it references, `AGENTS.md`, existing contracts/edit-plan/proxy code, and provider test files needed for this milestone.
- Do not read Relay `log.md` end-to-end or revisit private PhotoKit acceptance details.
- Blockers: none at handoff; a live Gemini call still requires the plan's explicit opt-in and spend bound.
