# Relay Charter: Swingcut Pi Extension MVP

## Relay identity

- Name: `pi-extension-mvp`
- Root: `/Users/nrgapple/Projects/swingcut/.pi-web/relays/pi-extension-mvp/`
- Repository: `/Users/nrgapple/Projects/swingcut`
- Stable supporting plan: `/Users/nrgapple/Projects/swingcut/docs/pi-extension-mvp-plan.md`

## Goal and finish line

Build and publish a public MIT-licensed, Git-backed Pi package and end-to-end Swingcut backend so that, from any project, the user can install it from GitHub, run `/swingcut-setup` once, then run `/swingcut <exact iCloud Photos album>` or make the equivalent natural-language request; confirm the source, cost, and repeat mode; and receive one verified high-quality apparent-ball-strike compilation in the Photos library.

Done means every finish-line requirement in `docs/pi-extension-mvp-plan.md` is satisfied, including public GitHub distribution, installation independent of the development checkout, estimate-before-confirmation Gemini cost disclosure, strict uncertainty exclusion, original-media cloud prohibition, add-only Photos import, verified post-import local-media cleanup, both Pi interfaces, cross-project operation, acceptance tests, documentation, and `make check` passing. That plan is part of this stable agreement.

Agreement amendments approved by the user:

- During Leg 4, the production model changed to Gemini 3.7 Flash rather than Gemini 3.8 Flash. Future model changes remain reviewable through a centralized capability/pricing policy and require explicit approval when they alter the stable plan.
- After the Leg 5 real run, the US$1 hard cap changed to estimate-only cost disclosure and explicit confirmation. Actual agentic usage may exceed the estimate and there is no hard per-run maximum. Pricing lookup and estimate failures still block paid work; retries remain bounded.

## Leg sizing

One leg implements and validates one milestone-sized subsystem from the plan. A leg must not absorb the next subsystem merely because time remains. It may perform small prerequisite repairs needed to leave its own subsystem coherent and tested.

## Task selection policy

Use the explicit next leg in `status.md`. If it is absent but the Relay is incomplete, select the earliest incomplete milestone in the plan's dependency order. Fix discovered defects within the current subsystem. Record non-blocking future work in status; do not jump ahead.

## Handover

Before any handoff, the runner must:

1. make code, tests, decisions, and documentation durable;
2. run relevant focused checks and `make check` when the leg changes integrated behavior;
3. update `status.md` with current position, last completed leg, next leg, narrow context pointers, and blockers;
4. append one concise entry to `log.md`; and
5. commit coherent repository changes unless a blocker makes the work knowingly incomplete; and
6. push every passing completed leg directly to the public GitHub repository's `main` branch.

Then spawn exactly one independent next session with a prompt beginning:

```text
Relay "pi-extension-mvp" leg <N> begins now.
```

The prompt must direct the runner to this charter and status file, instruct it not to read the full log by default, and require one leg plus durable handoff.

## Intervention signal

Stop without spawning and mark `status.md` with `INTERVENTION REQUIRED` when any of these occurs:

- a change is needed to the agreed goal, finish line, public MIT/GitHub distribution, direct-to-main policy, or stable supporting plan;
- any implementation would broaden Gemini disclosure or permit original-resolution upload;
- any implementation would edit, delete, replace, or reorganize existing Photos assets/albums;
- a credential or private media/metadata exposure is discovered or would be required;
- a real Photos/Gemini test requires fresh manual authorization or interaction;
- external-service failures persist after bounded documented retries;
- a Gemini estimate cannot be calculated and shown before confirmation;
- a destructive/irreversible migration is proposed;
- an architectural change crosses the Python orchestration, Swift PhotoKit, FFmpeg media, or thin TypeScript extension boundaries; or
- the runner cannot demonstrate its leg's exit condition without guessing.

The intervention note must state exactly what the user must decide or do. Real clearly named test imports are already approved and do not trigger intervention unless a new permission prompt or broader Photos capability is required.

## Reading discipline

Every runner reads only:

1. this charter;
2. `status.md`;
3. the plan sections and repository files specifically named by status; and
4. repository `AGENTS.md` plus any instructions governing files it changes.

Do not read `log.md` end-to-end. Use a targeted entry only when status points to it or an inconsistency must be resolved. Do not re-open broad workspace research unless the current task requires it.

## Fixed safety boundaries

- Originals and full-resolution exports stay local.
- Gemini receives only verified low-resolution, silent, metadata-stripped proxies.
- Existing Photos assets and albums are immutable to Swingcut.
- The only Photos write is adding a newly rendered output asset, followed by verification.
- User-visible/LLM-visible output is aggregate and bounded; raw private inventories and provider output stay in private runtime storage.
- Successful import removes all local media artifacts, including the local master.
- Routine tests never contact Gemini or the real Photos library.
- Public history contains no credentials, Photos inventories, personal media/metadata, or private model output.
- Completed passing legs are pushed directly to `main`; no pull request is required.
