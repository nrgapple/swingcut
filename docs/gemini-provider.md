# Gemini provider boundary

Swingcut pins video analysis to the Gemini Interactions API model `gemini-3.7-flash`, prompt `swing-analysis-v1`, agentic processing, and a strict JSON response schema. Model capability, pricing, and pricing expiry live together in the reviewed `MODEL_POLICIES` registry; changing the default requires adding/reviewing one policy rather than editing request logic. The provider accepts only a `ProxyArtifact` for `silent-h264-480w-15fps-v1` and re-probes and re-hashes its bytes immediately before upload. A missing sanitizer flag, changed hash, audio, excessive width, wrong frame rate/codec, or prohibited metadata blocks the upload.

Every interaction must include matched `processing_call` and `processing_result` steps. Output must be schema-valid, candidate identifiers must be unique, and accepted timelines must fit the proxy duration. The adapter stores only bounded token/cost records; it does not persist provider prose.

## Cost policy

The pricing snapshot is the official Gemini 3.7 Flash Standard paid-tier price through 2026-12-31: US$0.75 per million input tokens and US$3.75 per million output tokens, including thinking tokens. The snapshot expires closed on 2027-01-01.

Preflight assumes 258 video tokens per second, multiplies that by four for agentic-processing uncertainty, adds 4,096 prompt tokens, reserves the full 4,096 output-token limit, and includes both permitted attempts. Each potentially billable attempt is charged to a shared `SpendBudget` before the request. A failed request keeps its conservative charge because usage is unknown. A successful request reconciles only when complete usage is returned, counting output, thought, and tool-use tokens conservatively. No run budget may exceed US$1.

The model capability and token/rate assumptions must be checked before updating the pinned model or pricing:

- <https://ai.google.dev/gemini-api/docs/video-understanding#agentic-video-understanding>
- <https://ai.google.dev/gemini-api/docs/pricing>
- <https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash>

## Retry and deletion policy

The SDK's implicit retries are disabled. Swingcut makes at most two interaction attempts and retries only timeouts, connection failures, HTTP 408/429, and HTTP 5xx errors. The uploaded file is deleted in `finally`; deletion itself receives three bounded attempts. Any remaining deletion failure raises `DeletionDebtError` and must stop orchestration until cleanup succeeds.

## Live acceptance gate

Routine `make check` uses mocked provider responses and never contacts Gemini. A private live test requires all three explicit environment variables and is not authorized merely by running the normal suite:

```bash
SWINGCUT_RUN_LIVE_GEMINI=1 \
GEMINI_API_KEY='...' \
SWINGCUT_LIVE_VIDEO='/private/path/to/source.mov' \
.venv/bin/pytest -q tests/integration/test_gemini_live.py
```

The test generates the approved proxy in a temporary directory, performs the conservative preflight, uploads only that proxy, validates agentic analysis, and requires immediate provider-file deletion. An approved private comparison on the shortest test-album source returned one schema-valid accepted candidate at US$0.019455 and deleted all provider/local temporary media; this evidence selected 3.7 over 3.8. Private paths, media, responses, and credentials must not be committed or copied into validation notes.
