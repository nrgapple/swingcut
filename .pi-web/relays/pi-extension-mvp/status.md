# Relay Status: pi-extension-mvp

State: INTERVENTION REQUIRED — Leg 5 implementation passes routine validation, but real exit run exposed an unenforceable per-request Gemini bound

## Position

- Last completed leg: 4 (Gemini provider and strict proxy/cost policy)
- Next leg to run: 5-continuation, only after the intervention below is resolved
- Current task remains Plan Leg 5 (`docs/pi-extension-mvp-plan.md` lines 184-191); do not start Leg 6
- Distribution: public GitHub `origin`, MIT licensed; this coherent blocked implementation is pushed to `main`

## Durable Leg 5 implementation

- `orchestrator.py` connects exact Photos inventory/export, probe/proxy, Gemini, strict planning, deterministic render, verified add-only import, and ordered terminal cleanup.
- `state/store.py` provides atomic mode-0600 records, mode-0700 run/cache directories, versioned state, cooperative cancellation, aggregate status/clean behavior, resumable completed-source analysis, and cumulative spend carried across resume.
- Exact cache keys cover hashed identity/version evidence, source checksum, proxy profile, concrete model, prompt/schema hashes, and validator version. Incremental reuses only strict exact hits; rebuild bypasses cache; both render the current album.
- Individual export/probe/proxy/provider failures continue, except deletion debt and cost-cap failures. No-confident-swing runs import nothing and cleanly succeed.
- CLI commands now implement `inspect`, confirmed `run`, `status`, `cancel`, and `clean`; retained/public output is aggregate and bounded. See `docs/run-orchestration.md`.
- Synthetic validation: `make check` passes with 56 tests, one explicitly gated live test skipped, 83.57% coverage, Swift checks, and package builds.

## Real acceptance result and cleanup

- The approved exact private album was selected by its unique prior aggregate fingerprint: four videos, 206.069 seconds.
- Read-only inspect estimated US$0.466450 including bounded retry allowance, below the US$1 cap.
- Inventory, sequential staging, probing, and sanitized proxy creation succeeded. On the first Gemini source, returned usage exceeded that request's US$0.019929 reserved worst-case amount; the adapter failed closed with `CostCapError` before accepting analysis or attempting another source.
- The adapter reported no deletion debt, so its uploaded Gemini file was deleted. No render or Photos import occurred. Run-owned staged sources and proxies were then removed and absence verified. Only the mode-restricted failed state/private diagnostics remain; no private names, IDs, paths, media, or model output entered Git.

## INTERVENTION REQUIRED

The stable US$1 cap cannot currently be demonstrated conservatively for full agentic processing: `max_output_tokens` does not establish a documented ceiling for processing/thought/tool-use usage, and the real 3.7 response exceeded the existing per-attempt bound. Do not make another paid call or weaken/relabel the estimate.

The user must approve a concrete stable-plan/cost-control change that supplies an enforceable per-request ceiling (for example, a provider/model/API quota mechanism with documented hard bounds), or explicitly approve a different finish-line policy. Any model or stable-plan change must be recorded in the charter/plan before Leg 5 continuation. No handoff is spawned while this intervention is active.
