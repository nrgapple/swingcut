# Relay Status: pi-extension-mvp

State: ACTIVE — User resolved the Leg 5 cost-policy intervention; ready for Leg 5 continuation

## Position

- Last completed leg: 4 (Gemini provider and strict proxy policy)
- Next leg to run: 5-continuation
- Current task: finish Plan Leg 5 under the newly approved estimate-only policy, validate the real end-to-end import/cleanup, then hand off to Leg 6 if passing
- Distribution: public GitHub `origin`, MIT licensed; passing legs push directly to `main`

## Approved agreement amendment

The user explicitly selected **no hard cap; estimate and confirm** after the Leg 5 live cost-bound stop. Charter and stable plan now state:

- calculate and display a dated Gemini estimate before explicit confirmation;
- actual agentic usage may exceed that estimate and has no hard per-run maximum;
- pricing lookup or estimate failure still blocks paid work;
- retries remain bounded and returned usage remains tracked.

This resolves the prior intervention. The existing approved real test-album run may continue without another cost-cap decision.

## Durable Leg 5 implementation at `0d57c47`

- `orchestrator.py` connects exact Photos inventory/export, probe/proxy, Gemini, strict planning, deterministic render, verified add-only import, and ordered terminal cleanup.
- `state/store.py` provides atomic mode-0600 records, mode-0700 run/cache directories, versioned state, cooperative cancellation, aggregate status/clean behavior, resumable completed-source analysis, and cumulative usage state.
- Exact cache keys cover hashed identity/version evidence, source checksum, proxy profile, concrete model, prompt/schema hashes, and validator version. Incremental reuses only strict exact hits; rebuild bypasses cache; both render the current album.
- Individual export/probe/proxy/provider failures continue, except deletion debt. No-confident-swing runs import nothing and cleanly succeed.
- CLI implements `inspect`, confirmed `run`, `status`, `cancel`, and `clean`; public output is aggregate and bounded. See `docs/run-orchestration.md`.
- `make check` passed with 56 tests, one gated live test skipped, 83.57% coverage, Swift checks, and package builds.

## Bounded Leg 5-continuation task

1. Replace the obsolete US$1 authorization/refusal behavior with estimate-only accounting: estimates never claim a hard maximum, returned usage above an estimate is recorded rather than rejected, pricing/estimate failures still block, and retries remain bounded.
2. Update provider/orchestration tests and docs so no user-facing or code contract implies a hard cap. Preserve strict proxy verification, immediate upload deletion, and deletion-debt failure.
3. Run focused checks and `make check`.
4. Rerun the already-approved real exact private album through one backend command. Retain only aggregate evidence. Require a verified highlight import and absence of staged sources, proxies, provider uploads, and local master afterward.
5. If the real exit condition passes, mark Leg 5 complete and hand off to Leg 6. If a fresh authorization prompt, deletion debt, external-service retry exhaustion, or another charter trigger appears, stop with `INTERVENTION REQUIRED`.

## Prior real-run evidence

- Unique approved album aggregate: four videos, 206.069 seconds; dated estimate US$0.466450 under the old retry-inclusive formula.
- The first request exceeded its US$0.019929 reservation and failed closed before accepting analysis. Its Gemini upload was deleted, no render/import occurred, and failed-run staged/proxy media was removed and verified absent.
- No private names, IDs, paths, media, provider output, or credentials entered Git.

Blockers: none after the approved cost-policy amendment.
