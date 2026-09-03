# Gemini provider boundary

Swingcut's primary video analysis is Gemini Interactions model `gemini-3.7-flash` with prompt `swing-analysis-v1`, agentic processing, and a strict JSON response schema. Only after both bounded primary attempts end in HTTP 429 may it use reviewed fallback `gemini-3.5-flash` through GenerateContent with the same prompt/schema and strict validators. No other primary failure activates fallback. Model capability, API mode, pricing, and pricing expiry live together in `MODEL_POLICIES`. The provider accepts only a `ProxyArtifact` for `silent-h264-480w-15fps-v1` and re-probes and re-hashes its bytes immediately before upload. A missing sanitizer flag, changed hash, audio, excessive width, wrong frame rate/codec, or prohibited metadata blocks the upload.

Primary Interactions responses must include matched `processing_call` and `processing_result` steps. Both paths must return schema-valid output with unique candidate identifiers and in-bounds timelines. The adapter stores only bounded token/cost records; it does not persist provider prose.

## Cost policy

Pricing snapshots through 2026-12-31 are US$0.75/M input and US$3.75/M output for Gemini 3.7 Flash Standard, and US$1.50/M input and US$9/M output for Gemini 3.5 Flash, including thinking tokens. Either expired snapshot blocks all paid work on 2027-01-01.

Preflight includes both attempts for both possible paths: 258 video tokens per second, a 4× uncertainty multiplier for agentic primary input, one documented-rate fallback input, 4,096 prompt tokens per model attempt, and the full 4,096 output-token limit. The dated combined estimate is disclosed before explicit confirmation; it is not a maximum. Each potentially billable attempt is recorded in a shared `UsageLedger` before the request. A failed request keeps its conservative estimated charge because usage is unknown. A successful request replaces that estimate with complete returned usage, counting output, thought, and tool-use tokens conservatively even when actual usage costs more than estimated. There is no hard per-run cap.

The model capability and token/rate assumptions must be checked before updating the pinned model or pricing:

- <https://ai.google.dev/gemini-api/docs/video-understanding#agentic-video-understanding>
- <https://ai.google.dev/gemini-api/docs/pricing>
- <https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash>

## Retry and deletion policy

The SDK's implicit retries are disabled. Swingcut makes at most two attempts per possible API path, each with a 600-second timeout, and retries only timeouts, connection failures, HTTP 408/429, and HTTP 5xx errors. The fallback is entered only when the final primary error is HTTP 429. A final request failure is retained only as a privacy-safe timeout, connection, HTTP-status, or generic provider category; response bodies and provider prose are never persisted. The uploaded file is deleted in `finally`; deletion itself receives three bounded attempts. Any remaining deletion failure raises `DeletionDebtError` and must stop orchestration until cleanup succeeds.

## Live acceptance gate

Routine `make check` uses mocked provider responses and never contacts Gemini. A private live test requires all three explicit environment variables and is not authorized merely by running the normal suite:

```bash
SWINGCUT_RUN_LIVE_GEMINI=1 \
GEMINI_API_KEY='...' \
SWINGCUT_LIVE_VIDEO='/private/path/to/source.mov' \
.venv/bin/pytest -q tests/integration/test_gemini_live.py
```

The test generates the approved proxy in a temporary directory, performs the conservative preflight, uploads only that proxy, validates the selected primary/fallback path, and requires immediate provider-file deletion. An approved private comparison on the shortest test-album source returned one schema-valid accepted candidate at US$0.019455 and deleted all provider/local temporary media; this evidence selected 3.7 over 3.8. Private paths, media, responses, and credentials must not be committed or copied into validation notes.
