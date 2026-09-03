# Relay Status: pi-extension-mvp

State: INTERVENTION REQUIRED — Leg 5 real exit test exposed unsupported HLG rendering and one Gemini interaction failure

## Position

- Last completed leg: 4 (Gemini provider and strict proxy policy)
- Attempted leg: 5-continuation
- Next leg to run: none until the user resolves the intervention below
- Distribution: public GitHub `origin`, MIT licensed; only passing completed legs push directly to `main`

## Durable Leg 5-continuation work

- Replaced the obsolete US$1 cap/reservation contract with estimate-only accounting.
- `UsageLedger` records conservative unknown usage for failed attempts and returned usage for successful attempts, including actual cost above the estimate. Estimates above US$1 no longer fail.
- Missing/expired pricing and incalculable estimates still block; Gemini interaction and deletion retries remain bounded; strict proxy verification, immediate upload deletion, and deletion-debt failure remain unchanged.
- Renamed the public notice from `cost_cap_exceeded` to `cost_estimate_unavailable`; updated tests, schemas, repository instructions, README, stable plan wording, and provider/orchestration docs.
- Focused provider/orchestration tests passed. `make check` passed with 56 tests, one gated live test skipped, 83.94% coverage, Swift checks, and package builds.

## Real exit-test result (aggregate evidence only)

- Ran the previously approved exact four-video, 206.069-second album through one confirmed backend command.
- All four sources were staged and proxied under the strict cloud profile. Three analyses were accepted into state; one provider interaction failed. Every created Gemini upload was deleted and no deletion debt was reported.
- Planning retained four confident segments, then rendering failed closed because the selected album mixes BT.709 and HLG/BT.2020 sources. The production output profile intentionally has no unvalidated HDR-to-SDR conversion, and this machine's Homebrew FFmpeg lacks `zscale`.
- No Photos import occurred and no local master exists. The failed run retains four staged sources and four proxies under private mode-restricted runtime storage for diagnosis/recovery; this is consistent with failed-run retention but does not satisfy Leg 5 cleanup exit criteria.
- No private album name, identifiers, paths, media, provider output, or credentials entered Git or relay records.

## INTERVENTION REQUIRED

The user must decide whether to authorize a prerequisite media-engine continuation that:

1. adds a pinned FFmpeg capability/dependency providing a real HLG/PQ-to-BT.709 tone-map path (the current FFmpeg has `tonemap` but not `zscale`);
2. validates that profile technically and by manual visual review on the approved private footage before enabling it in production; and
3. authorizes one further bounded Gemini retry for the source whose interaction failed, followed by the real end-to-end rerun.

Do not spawn Leg 6 or make another paid/provider call until the user explicitly resolves this intervention. The local continuation commit is intentionally not pushed to `origin/main` because Leg 5 has not passed its real exit condition.

Blockers: validated HDR-to-SDR render profile/dependency; explicit authorization for the follow-up provider retry and private visual validation.
