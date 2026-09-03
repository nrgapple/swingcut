# Relay Status: pi-extension-mvp

State: ACTIVE — Leg 5 and its diagnostic continuation are complete; ready for Leg 6

## Position

- Last completed leg: 5 (end-to-end orchestration, fallback recovery, verified import, and cleanup)
- Next leg to run: 6
- Current task: implement the global Pi extension package milestone from the stable plan
- Distribution: public GitHub `origin`, MIT licensed; passing completed legs push directly to `main`

## Completed backend behavior

- Exact Photos inventory/export, strict low-resolution silent metadata-stripped proxies, deterministic planning/rendering, verified add-only import, and terminal cleanup are integrated.
- Cost policy is estimate-before-confirmation with no hard cap. Completed privacy-safe manifests retain aggregate estimated and accounted provider cost.
- Primary analysis remains Gemini 3.7 Flash Interactions with required agentic evidence. After two bounded primary HTTP 429 failures only, Gemini 3.5 Flash GenerateContent is the reviewed strict-schema fallback.
- Combined estimates include both possible paths. At current reviewed rates, June-only combined worst case is US$0.376620; full four-video combined worst case is US$0.970010. When a prior 3.7 failure is already established and primary is intentionally skipped, June fallback retry allowance is US$0.170596.
- Strict proxy verification, uncertainty exclusion, bounded retries/timeouts, returned-usage accounting, immediate upload deletion, and deletion-debt failure apply to both paths.
- Mixed HLG/PQ and BT.709 media renders through capability-checked zscale/Hable profile `photos-h264-aac-sdr-v2`, technically validated and user-approved.
- Exact cache keys now include the complete primary/fallback analysis strategy. Existing valid primary cache entries were safely migrated locally for the approved acceptance run; future incompatible policy changes invalidate exactly.

## Final real acceptance evidence (aggregate only)

- The approved June fallback call returned eight strict apparent-strike swings. Actual conservatively accounted cost was US$0.102528 versus the approved US$0.170596 retry-inclusive estimate. Its upload was deleted and its validated analysis was cached.
- The final incremental backend command used four exact cache hits, so additional Gemini estimate and accounted cost were both US$0.00.
- It built a 12-segment `photos-h264-aac-sdr-v2` compilation, verified and added it to Photos, reported zero failed sources, and reached `succeeded`.
- Post-import cleanup removed staged sources, proxies, the local master, and private run state. No deletion debt occurred.
- `make check` passed with 58 tests, one gated live test skipped, 84.09% coverage, Swift checks, and package builds.
- No raw provider output, private media, source identity/path, Photos inventory, or credential entered Git.

## Leg 6 bounded task

Implement only Plan Leg 6:

1. add the root Pi package manifest and TypeScript extension;
2. register `/swingcut-setup`, `/swingcut`, and `swingcut_create` over shared stable-path runner/configuration logic;
3. make setup idempotently deploy the locked Python backend and signed helper under stable Application Support paths, including `ffmpeg-full`/HDR capability checks;
4. implement estimate/disclosure/repeat confirmation, safe completion/selection where possible, progress, bounded outputs, and actionable notices;
5. test with a fake backend and prove both interfaces work from two unrelated project directories without development-checkout runtime paths; and
6. update installer/update/uninstaller documentation, run focused checks and `make check`, commit, and push passing work to `origin/main`.

Relevant files: `docs/pi-extension-mvp-plan.md` Leg 6 and Pi packaging/interface sections; `src/swingcut/cli.py`; `docs/run-orchestration.md`; repository `AGENTS.md`. Read Pi extension/package/TUI docs per the workspace instructions before implementation.

Blockers: none.
