# Relay Status: pi-extension-mvp

State: ACTIVE — Leg 4 complete; ready for end-to-end orchestration milestone

## Position

- Last completed leg: 4 (Gemini provider and strict proxy/cost policy)
- Next leg to run: 5
- Current task: implement only Plan Leg 5 in `docs/pi-extension-mvp-plan.md` lines 184-191: end-to-end inspect/run/status/cancel/clean orchestration, exact incremental cache invalidation, resumable state, individual-source continuation, import, and terminal cleanup
- Distribution: public GitHub `origin`, MIT licensed; passing legs are pushed directly to `main`

## Completed Leg 4 evidence

- `providers/base.py` defines the provider boundary, strict usage records, typed failures, and a thread-safe maximum-US$1 budget that authorizes every potentially billable attempt.
- `providers/gemini.py` pins Gemini 3.7 Flash through a centralized reviewed `MODEL_POLICIES` capability/pricing registry, making future approved upgrades localized while unknown models fail closed.
- The adapter enforces agentic Interactions processing, strict structured output and matched processing evidence, bounded timeout/transient retries, complete usage accounting, and `finally` deletion with deletion-debt failure.
- Only a typed `silent-h264-480w-15fps-v1` proxy can reach upload; bytes are re-probed and re-hashed immediately beforehand. Originals, changed/unsanitized media, audio, excess resolution, wrong codec/rate, and prohibited metadata fail closed.
- The user explicitly approved amending the stable plan from Gemini 3.8 to 3.7 after a private comparison. Charter, plan, provider docs, README, and validation evidence were updated.
- The approved private 3.7 run returned one schema-valid accepted candidate at US$0.019455 and left no provider upload or local temporary media. The full four-source test-album preflight, including one retry per source, is US$0.466450 under the current dated conservative policy.
- Mocked tests cover all identified success, malformed output, missing processing, unsupported model, usage, retry, spend, proxy-boundary, upload-tracking, and deletion-debt paths.
- `make check` passes with 52 tests, 1 explicitly gated live test skipped, and 85.95% coverage.

## Leg 5 context

- Read Plan Leg 5 and the Python backend/run-state/privacy/cache sections it references, repository `AGENTS.md`, and only the contracts, Photos client, media/planning/provider modules and tests needed to connect the pipeline.
- Use `GeminiProvider.estimate_run_cost` before paid work and one shared `SpendBudget` for the run. Do not bypass the budget in production orchestration.
- A real end-to-end run against the existing private test album is approved, including one clearly named new Photos output. Existing Photos assets/albums remain immutable and the imported output must not be deleted.
- On verified success, delete Gemini uploads first (already immediate in the adapter), then staged sources/proxies, then the local rendered master after verified add-only Photos import.
- Keep private inventory, IDs, paths, cache contents, and model output under mode-restricted runtime storage; retain only aggregate validation evidence in Git.
- Blockers: none. Stop under charter rules if fresh authorization appears, conservative preflight exceeds US$1, deletion debt occurs, or a boundary change is needed.
