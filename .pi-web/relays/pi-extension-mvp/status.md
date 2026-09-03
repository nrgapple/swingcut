# Relay Status: pi-extension-mvp

State: INTERVENTION REQUIRED — successful Gemini 3.5 structured diagnostic awaits explicit production model/API amendment

## Position

- Last completed leg: 5 (end-to-end orchestration, estimate-only accounting, HDR rendering, verified import, and cleanup)
- Attempted leg: 5-diagnostic-continuation
- Next leg to run: none until the user explicitly approves or rejects the production model/API amendment below
- Distribution: passing completed legs through `916d59a` are on public `origin/main`; diagnostic commits `20b33b5` and `e2dc6b2` remain local

## Existing production blocker

- Gemini 3.7 Flash Interactions returned persistent HTTP 429 for the 109.277-second June source after bounded attempts.
- A minimal text-only call through the official Gemini CLI succeeded, proving the API key/general account is functional. The CLI silently routed the requested model to `gemini-3.5-flash` through GenerateContent.
- The blocker is therefore specific to the production 3.7 Interactions model/API availability, not Pi credits, general Gemini credentials, video classification, or the former timeout.

## Approved diagnostic results (aggregate only)

- Official Gemini CLI 0.58.0 was run noninteractively from a temporary directory using the configured private API key and only the strict low-resolution silent metadata-stripped June proxy.
- The CLI/3.5 diagnostic reported nine swing candidates; five of its free-form timelines were immediately structurally valid.
- A second direct 3.5 Flash GenerateContent diagnostic used Swingcut's exact JSON schema, prompt, strict candidate models, 8,192-token output allowance, and one attempt. It returned one schema-valid response with nine apparent-strike candidates and nine valid ordered in-bounds timelines; no candidates were rejected.
- Every diagnostic upload was deleted, all temporary staged exports/proxies/private output were removed, and no raw provider response, media, identity, path, or credential entered Git or relay records.

## Proposed stable-plan amendment requiring explicit approval

Change production analysis from:

- `gemini-3.7-flash` Interactions with required agentic `processing_call`/`processing_result` evidence

to:

- `gemini-3.5-flash` GenerateContent with strict JSON-schema output and the existing uncertainty/timeline validator.

Current reviewed paid-tier rates would change from US$0.75/M input + US$3.75/M output to US$1.50/M input + US$9/M output, including thinking tokens. Estimate-before-confirmation remains mandatory with no hard cap. Full-duration sanitized proxies, original-media prohibition, strict uncertainty exclusion, bounded retries/timeouts, returned-usage accounting, immediate upload deletion, and deletion-debt failure remain unchanged.

This changes the charter-designated stable plan's production model and agentic-processing requirement. The user must explicitly approve or reject it. If approved, update the charter and stable plan before implementation, then run mocked checks, one June-only live analysis/cache fill, and one incremental verified Photos compilation/cleanup.

Do not make another provider call or spawn Leg 6 until the user decides.

Blockers: explicit stable-plan/model/API approval.
