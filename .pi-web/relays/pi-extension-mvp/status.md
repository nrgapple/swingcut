# Relay Status: pi-extension-mvp

State: ACTIVE — Leg 6 complete and passing; ready for Leg 7

## Position

- Last completed leg: 6 (global Pi package, stable setup/runtime, both interfaces, fake-backend cross-project proof)
- Next leg to run: 7
- Current task: perform the acceptance, privacy audit, and release-handoff milestone from the stable plan
- Distribution: public GitHub `origin`, MIT licensed; passing completed legs push directly to `main`

## Completed product behavior

- The Python backend now covers exact Photos inventory/export, privacy-verified proxy analysis with reviewed 3.7/3.5 strategy, deterministic HDR/SDR rendering, verified add-only Photos import, exact cache/rebuild behavior, and terminal cleanup.
- Root `package.json` exposes `extensions/swingcut/index.ts` as a Git-backed Pi package.
- `/swingcut-setup` confirms destinations, verifies prerequisites, and idempotently deploys a lockfile-backed wheel environment under revisioned Application Support releases, a stable backend launcher/current symlink, and the consistently signed PhotoKit helper. Package installation itself requests no Photos access and makes no Gemini call.
- `/swingcut` and `swingcut_create` share one stable-path runner. They inspect before confirmation, select repeat mode, disclose exact album/count/duration/proxy policy/dated combined estimate/add-only destination, require confirmation, show compact progress, and expose only bounded aggregate results/notices.
- Non-UI tool invocation fails closed unless mode and `confirmed=true` are explicit. Album-name completion intentionally does not enumerate private Photos albums.
- Fake-backend tests exercise setup twice and the two creation interfaces from two unrelated project directories; all runtime calls use the Application Support launcher and never the development checkout or `ctx.cwd`.
- Installer/update/uninstaller guidance is in `docs/pi-package.md`; README contains public install and use steps.

## Validation

- `make check` passes: 58 Python tests, one gated live test skipped, 84.08% coverage, 5 TypeScript extension tests, TypeScript strict checking, Swift checks, and Python/Swift package builds.
- `npm pack --dry-run` includes the MIT license, package manifest, and extension.
- Credential/private-data scan found no committed credential, personal media path, Photos inventory, or provider output.

## Leg 7 bounded task

Implement only Plan Leg 7:

1. install the public package from `git:github.com/nrgapple/swingcut@main` after this leg's pushed commit and run `/swingcut-setup` once;
2. execute the complete synthetic suite plus the approved real Photos/Gemini workflow from unrelated Pi project directories;
3. verify repeat-mode confirmation, individual failure continuation, no-swing behavior, estimate-failure blocking, above-estimate accounting, cancellation/recovery, verified creation, and cleanup;
4. audit conversation-visible output, logs, manifests, package contents, and public history for secrets/private identifiers/metadata/provider prose;
5. fix only acceptance/release defects within the stable charter, update final user documentation/evidence, and run `make check`; and
6. commit and push the passing final leg to `origin/main`, then stop because the relay finish line is reached.

Relevant files: `docs/pi-extension-mvp-plan.md` Leg 7, finish line, validation, and risks; `docs/pi-package.md`; `README.md`; `docs/validation.md`; `extensions/swingcut/index.ts`; `docs/run-orchestration.md`. Real tests remain subject to the charter intervention triggers, especially fresh authorization/interaction and persistent external-service failures.

Blockers: none.
