# Swingcut Pi Extension MVP Plan

Status: proposed for approval and Relay execution  
Date: 2026-09-02  
Repository: `/Users/nrgapple/Projects/swingcut`

## Problem

The PhotoKit and Gemini feasibility spikes work, but Swingcut is not yet an end-to-end product. The desired experience is available from Pi in any project: name an exact iCloud Photos album, confirm the run, and receive a high-quality golf-swing highlight video in Apple Photos.

## Goals and finish line

The MVP is complete when all of the following are true:

1. Swingcut is a public MIT-licensed GitHub repository and installs globally as a Git-backed Pi package, independent of Pi's current project directory.
2. It exposes both:
   - `/swingcut <exact album name>`; and
   - an LLM-callable `swingcut_create` tool for natural-language requests.
3. A run inventories only the exact named Photos album, then confirms the album, video count, total duration, cloud-proxy disclosure, estimated Gemini cost, and repeat mode before doing paid or mutating work.
4. On repeat runs, the user chooses either:
   - **incremental:** reuse valid cached analysis for unchanged assets, analyze new/changed assets, and render a fresh compilation from the current album; or
   - **rebuild:** invalidate/recompute analysis and render from every current source asset.
5. Gemini receives only full-duration, low-resolution, silent, metadata-stripped proxies. Original-resolution media never leaves the Mac. Swingcut shows a dated Gemini estimate before explicit confirmation; actual agentic usage may exceed it and has no hard per-run maximum.
6. Swingcut includes only confident apparent ball-striking swings. It excludes uncertain, practice-only, false-start, aborted, incomplete, occluded, and no-apparent-strike candidates and reports them.
7. Accepted clips retain source audio, start two seconds before takeaway where source bounds allow, end three seconds after finish where bounds allow, and are ordered by source capture time then in-source time.
8. The renderer produces one high-quality Apple Photos-compatible video and letterboxes mixed orientations without cropping. The concrete codec/color/canvas profile is selected by tested source properties and recorded in the run manifest.
9. The native helper adds only the newly rendered output to the Photos library, verifies that the created Photos asset exists, and never edits, deletes, replaces, or reorganizes any existing Photos asset or album.
10. After successful verified import, Swingcut deletes the local rendered master, staged source copies, proxies, and Gemini file uploads. Privacy-safe manifests and diagnostics remain under Application Support.
11. Individual source failures do not abort otherwise valid work. If no confident swing remains, no output is imported and the run reports why.
12. Synthetic automated tests and approved real integration tests pass, including a clearly named real Photos import. `make check` passes.
13. A first-time user can run `pi install git:github.com/<owner>/swingcut@main`, invoke `/swingcut-setup` once, then use `/swingcut <album>` without manually configuring repository paths, Python environments, or the native helper.

## Confirmed product decisions

- Interface: slash command and natural-language tool.
- Scope: global across all Pi projects.
- Source: one exact iCloud Photos album.
- User flow: one confirmation, then automatic processing.
- Repeat behavior: ask between incremental and rebuild.
- Destination: Photos library only, not a destination album.
- Local master: temporary; delete after verified Photos import.
- Failure behavior: strict exclusion and continue past individual source failures.
- Test behavior: real, clearly named Photos test imports are approved. Tests must not delete those Photos assets automatically.
- Gemini cost policy: estimate and disclose before explicit confirmation; actual agentic usage may exceed the estimate, with no hard per-run cap.
- Gemini model: `gemini-3.7-flash`, selected after an approved private comparison completed with schema-valid agentic analysis and cleanup while 3.8 showed higher usage and availability failures.
- Build method: Relay with milestone-sized legs and safety stops.
- Distribution: public GitHub repository, MIT License, Git-backed Pi package.
- Delivery: every passing Relay leg commits and pushes directly to `main`; no pull-request workflow is required.
- Setup UX: `pi install` followed by a one-time `/swingcut-setup` command.

## Observed starting point

- The Python 3.12/uv scaffold, schemas, docs, tests, and `doctor` command exist.
- A developer-signed `SwingcutPhotosBridge.app` can persist PhotoKit authorization across rebuilds.
- The bridge can report status, enumerate albums/library counts, list an exact album, and export an asset read-only.
- A private test album scan found four portrait videos totaling 206.1 seconds.
- A private test exported HEVC with audio and generated a silent H.264 proxy at 480 pixels wide and 15 fps with sensitive metadata removed.
- Gemini 3.8 Flash via `google-genai` 2.x Interactions API accepted `processing: agentic`, emitted processing steps, returned schema-valid ordered timestamps on the short sample, and allowed immediate uploaded-file deletion.
- The end-to-end orchestration, deterministic renderer, import command, cache, CLI run command, and Pi extension do not exist.

## Architecture

### Public Git-backed Pi package

Add a package manifest at the Swingcut repository root with a Pi extension under `extensions/swingcut/index.ts`, plus an MIT `LICENSE`. Publish the repository to the authenticated user's GitHub account and install it globally with:

```bash
pi install git:github.com/<owner>/swingcut@main
```

`/swingcut-setup` performs the explicit one-time native/Python installation after package download. It must be idempotent, display exactly what it will install under `~/Library/Application Support/Swingcut/`, verify prerequisites before changes, build/deploy the consistently signed helper, provision the locked Python backend, and guide Photos/Gemini readiness without exposing credentials. Package installation itself must not silently request Photos access or make Gemini calls.

The extension is a thin local client, not the media engine. It:

- registers `/swingcut` and `swingcut_create`;
- resolves the installed Swingcut backend independent of `ctx.cwd`;
- inventories and asks for confirmation through `ctx.ui` when UI is available;
- reports compact progress and warnings;
- does not expose asset identifiers, filenames, or private metadata to the conversation or LLM;
- invokes the backend with argument arrays rather than shell interpolation; and
- supports non-UI invocation only when all required choices are explicit, otherwise fails safely.

A shared TypeScript runner must back both entry points so command and tool behavior cannot drift. The slash command is deterministic and does not need an extra model turn. The natural-language tool returns bounded details and never emits raw inventory or model output.

### Python backend

Python remains the orchestrator and provides a stable machine-readable command contract, provisionally:

```bash
swingcut inspect --photos-album "Album" --json
swingcut run --photos-album "Album" --mode incremental --import-to-photos --json-events
swingcut run --photos-album "Album" --mode rebuild --import-to-photos --json-events
swingcut status <run-id> --json
swingcut cancel <run-id>
swingcut clean
```

The extension must not depend on repository-relative `.venv` paths after installation. A user installer deploys the Python executable/environment and signed helper app to stable user locations under `~/Library/Application Support/Swingcut/`, while the Pi package remains globally registered. Installation and `doctor` verify all paths and signatures.

### Native PhotoKit helper

Extend the existing Swift app-bundle protocol with an explicit add-only output operation. Source operations remain read-only. The import operation:

- accepts only a caller-created local video path;
- creates a new `PHAsset` through supported PhotoKit change APIs;
- returns the placeholder/local identifier;
- fetches that identifier after the transaction to verify creation; and
- has no edit, delete, album-add, album-remove, or replacement commands.

The helper continues to launch through LaunchServices with private result/error files, because direct invocation does not receive the stable TCC identity. Python should launch asynchronously and poll bounded result files rather than rely on `open -W`.

### Run state and privacy

Use `~/Library/Application Support/Swingcut/runs/<run-id>/` with mode-0700 directories and mode-0600 sensitive files. Persist a versioned state machine and privacy-safe manifest. Media stays in run-private staging and proxy directories.

Cache keys include source identity/version evidence and content checksum, proxy profile, concrete Gemini model, prompt/schema hashes, and validator version. Incremental mode reuses only schema-valid cache entries with an exact key match. A fresh final compilation always represents the current album; it is not merely a reel of newly added videos.

A terminal cleanup state is required. On success, deletion order is: Gemini uploads, staged originals/proxies, verified imported local master. On errors, make a best effort to delete Gemini uploads immediately. Retain resumable local media only while the run remains explicitly resumable; stale interrupted runs are surfaced by `doctor`/`clean` and subject to a documented short retention policy.

### Media and planning pipeline

```text
exact Photos album
  -> private inventory and repeat-mode choice
  -> sequential PhotoKit staging with checksums
  -> ffprobe normalization
  -> full-duration sanitized proxy
  -> Gemini agentic analysis
  -> strict schema/timeline validation
  -> versioned edit plan
  -> high-quality FFmpeg render from staged originals
  -> ffprobe/QuickTime-compatible verification
  -> PhotoKit add-only import and verification
  -> cleanup
```

The model never directly constructs FFmpeg commands. Pydantic models validate every provider response, source bounds, event ordering, duplicate/overlapping detections, and confidence policy before an edit plan is renderable.

The initial measured proxy candidate remains silent H.264, 480 pixels wide, 15 fps. It is provisional until tested on the longer private footage. Any change that broadens cloud disclosure requires human approval.

### Cost control

Before upload, calculate a dated estimate from total proxy duration, bounded retry allowance, and the current concrete model price/configuration. Show it before explicit confirmation and track returned usage when available. Actual agentic processing usage may exceed the estimate and has no hard per-run maximum. A pricing lookup or estimate failure blocks paid analysis rather than assuming zero cost, and retries remain bounded.

## Milestones / Relay legs

Each Relay leg owns one tested subsystem and leaves the repository passing its relevant checks.

### Leg 1 — Contracts, state, and policy alignment

- Update repository instructions to permit only add-only import of newly rendered output, reflecting the user's explicit approval.
- Implement Pydantic source, analysis, edit-plan, manifest, event, and run-state models.
- Implement strict timeline validation, confidence exclusion, padding, sorting, and privacy-safe serialization.
- Define JSON event contracts consumed by the extension.

Exit: unit tests cover valid/invalid timelines, exclusions, source bounds, state transitions, and sensitive-field redaction.

### Leg 2 — Deterministic media engine

- Implement ffprobe inventory, metadata-stripped proxy generation, deterministic segment rendering, audio retention, orientation canvas selection, and output verification.
- Generate synthetic fixtures for portrait/landscape, audio/silent, and mixed frame rates.
- Select and document a Photos-compatible output profile through tests; avoid unnecessary upscaling and intermediate quality encodes.

Exit: hand-authored plans create verified compilations from synthetic sources, and source hashes remain unchanged.

### Leg 3 — Productize PhotoKit source and add-only destination

- Add a Python LaunchServices client with timeout, polling, cancellation, and private result/error files.
- Harden exact-album inventory and sequential iCloud-backed export.
- Add and test the narrowly scoped native `import-output` operation and post-create verification.
- Add stable user installation for the signed app bundle.

Exit: an exact test album can be inventoried/exported and a clearly named synthetic compilation can be added and verified in Photos without altering existing assets.

### Leg 4 — Gemini provider and proxy policy

- Implement `providers/base.py` and a policy-pinned Gemini 3.7 Flash Interactions adapter whose reviewed model policy is centralized for future upgrades.
- Enforce agentic processing, structured output, timeout/bounded-retry rules, dated cost estimates, usage records, and `finally` upload deletion.
- Fail closed on malformed output, missing processing evidence, unsupported model capability, or deletion debt.
- Use mocked provider tests by default; gate live private tests explicitly.

Exit: mocked tests cover all failure/cleanup paths and an approved private live run produces a validated analysis without leaving provider files.

### Leg 5 — End-to-end orchestration, incremental cache, and cleanup

- Implement inspect/run/status/cancel/clean commands and the versioned resumable state machine.
- Connect Photos, media, Gemini, planning, rendering, import, and cleanup.
- Implement repeat detection and exact cache invalidation.
- Continue around individual source failures while preserving strict output eligibility.

Exit: one backend command processes the selected real album end to end, imports a verified highlight, and removes local media artifacts; rerun behavior supports both cache reuse and rebuild.

### Leg 6 — Global Pi extension package

- Add the root package manifest, MIT license, and TypeScript extension.
- Register `/swingcut-setup`, `/swingcut`, and `swingcut_create` over shared runner/configuration logic.
- Make setup idempotently deploy the locked Python backend and signed native helper to stable user paths.
- Add confirmation, album-name completion/selection where safe, progress, bounded outputs, and actionable failure notices.
- Add installer/update/uninstaller documentation and tests using a fake backend.

Exit: after installation from the GitHub URL and one `/swingcut-setup`, both creation interfaces work from at least two unrelated project directories and never depend on `ctx.cwd` or the original development checkout for runtime resources.

### Leg 7 — Acceptance, privacy audit, and release handoff

- Run the complete synthetic suite and approved real Photos/Gemini workflow.
- Verify repeat-mode prompt, individual failure continuation, no-swing behavior, estimate failure blocking, above-estimate usage accounting, cancellation/recovery, and post-success cleanup.
- Audit logs/manifests for secrets, asset identifiers, filenames, location/device metadata, and private model prose.
- Update README with exact installation and usage steps.

Exit: every finish-line condition is demonstrated, `make check` passes, and the user can run `/swingcut "Album Name"` from any Pi project.

## Validation

Routine tests must not access Photos or Gemini. They use generated media, mocked bridge results, and mocked model responses. Explicit integration suites are separately gated, estimate-disclosed, and bounded in retry count.

Required acceptance scenarios:

- exact album exists, is empty, is missing, or permission is denied;
- local and iCloud-only video export;
- one source fails while others succeed;
- no confident swing remains;
- malformed/uncertain/out-of-bounds Gemini results;
- metadata stripping and original-upload prohibition;
- mixed orientations and audio preservation;
- interrupted upload/render/import and safe resume;
- incremental cache hit, cache miss after source change, and full rebuild;
- estimated spend above US$1 proceeds only after estimate disclosure and explicit confirmation;
- verified Photos creation and complete local cleanup;
- invocation from unrelated current working directories.

## Risks and mitigations

- **TCC identity/path behavior:** install one consistently signed app at a stable path and always launch it through LaunchServices.
- **Accidental Photos mutation:** expose only list/export and add-new-output operations; test that no edit/delete paths exist.
- **Private data in Pi context:** extension results contain aggregate status only. Keep raw inventories, asset IDs, file paths, and provider output in mode-0600 run files.
- **Original upload regression:** provider accepts only a typed proxy artifact carrying a passed sanitizer verification record; reject any other path.
- **Gemini variability:** pin model/prompt/schema, require processing evidence, validate strictly, and exclude uncertainty.
- **API cost drift:** dated price-aware preflight and explicit confirmation, bounded retries, returned-usage tracking, and fail closed when an estimate cannot be calculated. Actual agentic usage can exceed the estimate and has no hard per-run maximum.
- **Rendering incompatibility:** automated ffprobe checks plus approved real Photos imports; profile decisions stay versioned.
- **Output duplication:** every successful rerun creates a new Photos asset; Swingcut never deletes or replaces prior compilations. Report this at confirmation.
- **Pi shutdown during work:** run state is durable and idempotent; cancellation and resume must not duplicate imports.

## Out of scope for this MVP

- iCloud Drive and local-folder sources.
- Mobile or GUI applications outside Pi.
- Coaching, scoring, biomechanics, identity recognition, or generative video alteration.
- Editing/deleting existing Photos assets or placing output into an album.
- npm or PyPI publication; distribution is through the public GitHub Pi package first.
- Automatic deletion of clearly named Photos test imports or prior compilations.

## Approval and change control

This document is the stable supporting plan for the Relay charter. Changing cloud disclosure, Photos mutation boundaries, the estimate-and-confirm cost policy, retained clip definition, destination/cleanup behavior, public MIT/GitHub distribution, direct-to-main delivery, or the finish line requires explicit user approval before Relay execution continues.
