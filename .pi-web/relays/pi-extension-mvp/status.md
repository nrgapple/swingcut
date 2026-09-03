# Relay Status: pi-extension-mvp

State: INTERVENTION REQUIRED — June 29 remains unanalyzed after the authorized diagnostic strategy change and retry

## Position

- Last completed leg: 5 (end-to-end orchestration, estimate-only accounting, HDR rendering, verified import, and cleanup)
- Attempted leg: 5-diagnostic-continuation
- Next leg to run: none until the user authorizes a further diagnostic provider call
- Distribution: public GitHub `origin`, MIT licensed; passing completed legs push directly to `main`

## Previously completed and pushed

- Estimate-only Gemini accounting has no hard cap; pricing/estimate failure still blocks and retries remain bounded.
- Strict proxy verification, immediate upload deletion, deletion-debt failure, exact incremental cache, add-only verified Photos import, and terminal cleanup are active.
- `photos-h264-aac-sdr-v2` provides user-approved zscale/Hable HLG/PQ-to-BT.709 rendering through capability-checked `ffmpeg-full`.
- Leg 5 implementation through commit `916d59a` is on `origin/main`.

## Diagnostic continuation result

- The user explicitly required extraction from the June 29 source and authorized provider changes plus a retry.
- The source is 109.277 seconds at 2160×3840. Prior failures took long enough that the 180-second request timeout was a plausible cause.
- Increased the bounded per-attempt timeout from 180 to 600 seconds while retaining exactly two maximum attempts and disabled SDK retries.
- Added `ProviderInteractionError` with privacy-safe timeout, connection, HTTP-status, or generic provider categories; response bodies and provider prose remain unpersisted. Tests prove bounded timeout exhaustion, immediate upload deletion, and no private exception text disclosure.
- Updated provider documentation. Focused tests and `make check` passed with 57 tests, one gated live test skipped, 83.96% coverage, Swift checks, and package builds.
- Ran one authorized incremental backend retry. The three existing analyses were exact cache hits; June 29 was the sole provider call. It returned/finalized in about 94 seconds, so the old timeout was not the cause, but again produced no accepted analysis/cache entry.
- The workflow correctly continued, imported another verified four-segment compilation from the other sources, and cleaned all run-owned staged media, proxies, local master, and private record. The privacy-safe manifest reports one failed source and four accepted segments.
- Because successful cleanup removes the private record, the safe failure category was also removed before it could be inspected. No provider response, media, identifiers, paths, or credentials entered Git.

## INTERVENTION REQUIRED

The external/provider analysis failure persists after the newly authorized call. Before another paid call, the implementation should retain only aggregate safe failure categories in the privacy-safe manifest (never provider prose or source identity), then perform a diagnostic retry to determine whether the response is malformed, lacks processing evidence, is out of bounds, or fails at transport/status level.

The user must explicitly authorize that further paid diagnostic retry. Depending on its category, a later strategy may require prompt/schema adjustment while preserving strict uncertainty exclusion, full-duration sanitized proxies, bounded retries, and immediate upload deletion.

Do not make another Gemini call or spawn Leg 6 until authorized. The passing timeout/diagnostic code is committed locally but intentionally not pushed because this continuation did not achieve June 29 extraction.

Blockers: one further authorized paid diagnostic call with durable aggregate failure-category retention.
