# Relay Status: pi-extension-mvp

State: INTERVENTION REQUIRED — Gemini 3.7 comparison passed; production model decision required

## Position

- Last completed leg: 3 (productized PhotoKit source and add-only destination)
- Next leg to run: 4 continuation after intervention
- Current task: resolve how the stable US$1 hard cap can be conservatively enforced for Gemini agentic processing, then obtain approval for another bounded private live test
- Distribution: public GitHub `origin`, MIT licensed; passing work is pushed directly to `main`

## Leg 4 durable implementation

- Commit `1ff35f3` implements the provider boundary, Gemini 3.8 Flash Interactions adapter, strict structured output and processing evidence, typed usage, retries/timeouts, pre-upload proxy re-verification, and `finally` provider-file deletion.
- Mocked tests cover success and all identified output, capability, usage, retry, budget, proxy-boundary, upload-tracking, and deletion-debt failures.
- `docs/gemini-provider.md` records the current dated pricing assumptions and explicit live gate.
- `make check` passes with 52 tests, 1 gated live test skipped, and 85.86% coverage.

## Live test result

- The user authorized the existing private test album. The bridge privately selected the unique test-marked exact album and confirmed it still matched the approved aggregate four-video corpus.
- One shortest source was exported privately, converted locally to the approved `silent-h264-480w-15fps-v1` proxy, and uploaded. The original was not uploaded.
- Gemini returned a completed interaction and usage, but calculated usage cost exceeded the adapter's reserved per-attempt worst-case estimate. The adapter failed closed with `CostCapError` before accepting analysis.
- The provider upload was deleted by the adapter's `finally` path without deletion error. Temporary staged source and proxy storage was removed automatically. No private album name, asset ID, filename, path, model prose, media, or credential was retained or committed.
- The user then authorized one additional test-only run without the production estimate gate. The same bounded private source/proxy path was used, but Gemini 3.8 Flash returned HTTP 500 high-demand errors through the adapter's bounded retry path. No analysis response or usage was returned for that run.
- The second run's provider upload was also deleted without error and all local temporary media was removed.
- The user then explicitly requested a one-time Gemini 3.7 Flash comparison. Without changing repository code, the same shortest-source sanitized-proxy flow completed successfully: one schema-valid candidate was accepted, aggregate paid-tier calculated cost was US$0.019455, and provider/local cleanup completed. No private data or model prose was retained.

## Required user intervention

The observed agentic usage invalidates the current duration-based conservative estimate. Official Interactions controls bound final output tokens but do not document a hard server-side ceiling for agentic processing/thought/tool-use tokens. The runner therefore cannot demonstrate that a request will stay below US$1 without guessing.

The user must explicitly decide whether to amend the stable plan from Gemini 3.8 Flash to Gemini 3.7 Flash based on this successful comparison, or retain 3.8 and wait for availability. A switch requires updating the charter-designated plan, pinned adapter model/pricing documentation, and tests before another validation. The US$1 enforcement design also still needs resolution because the earlier 3.8 usage exceeded its claimed per-attempt worst-case estimate, although the 3.7 comparison cost remained below that estimate and far below US$1. Do not spawn Leg 5 until the production model and conservative bound are resolved.
