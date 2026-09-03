# Relay Status: pi-extension-mvp

State: INTERVENTION REQUIRED — live Gemini usage disproved the conservative cost bound

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
- No retry or second paid call was made.

## Required user intervention

The observed agentic usage invalidates the current duration-based conservative estimate. Official Interactions controls bound final output tokens but do not document a hard server-side ceiling for agentic processing/thought/tool-use tokens. The runner therefore cannot demonstrate that a request will stay below US$1 without guessing.

The user must decide whether to keep the current stable hard-cap requirement and require an enforceable provider/project quota mechanism or another demonstrably bounded request design, or explicitly approve a change to the stable cost-control requirement/plan. If a bounded design is selected, another private live call also requires explicit authorization. Do not spawn Leg 5 until a validated analysis completes under the resolved bound and provider deletion is verified.
