# Relay Status: pi-extension-mvp

State: INTERVENTION REQUIRED — Leg 4 implementation passes offline; private live Gemini acceptance is not authorized

## Position

- Last completed leg: 3 (productized PhotoKit source and add-only destination)
- Next leg to run: 4 continuation after intervention
- Current task: obtain explicit approval for one spend-bounded private Gemini test, run the gated acceptance command in `docs/gemini-provider.md`, and verify schema-valid agentic analysis plus provider-file deletion; do not change implementation scope unless the test exposes a Leg 4 defect
- Distribution: public GitHub `origin`, MIT licensed; passing work is pushed directly to `main`

## Leg 4 durable implementation

- `providers/base.py` defines the provider boundary, strict usage records, a thread-safe maximum-US$1 budget, and typed cost/output/deletion failures.
- `providers/gemini.py` pins Gemini 3.8 Flash, agentic Interactions processing, structured output, timeout/retry limits, dated conservative pricing, complete usage accounting, strict processing evidence, and `finally` deletion with bounded retries.
- The provider accepts only a typed `silent-h264-480w-15fps-v1` `ProxyArtifact`; `verify_cloud_proxy` re-probes and re-hashes bytes immediately before upload and rejects changed, unsanitized, wrong-profile, audio-bearing, oversized, wrong-codec/frame-rate, metadata-bearing, or source-identical artifacts.
- Mocked tests cover success, request shape, malformed/missing output, strict fields, missing/mismatched processing evidence, unsupported model, invalid usage, out-of-bounds/duplicate candidates, original-path prohibition, transient/permanent failures, bounded retries, spend refusal, expired pricing, untrackable uploads, and deletion debt.
- `docs/gemini-provider.md` records cost assumptions, retry/deletion behavior, official capability/pricing links, and the explicit live gate.
- `make check` passes with 52 tests, 1 gated live test skipped, and 85.86% coverage.

## Required user intervention

Explicitly authorize one private live Gemini analysis under the adapter's conservative US$1 cap and identify/approve the private source video to use (or run the three-environment-variable command in `docs/gemini-provider.md` locally). This test will generate and upload only the verified low-resolution silent metadata-stripped proxy, never the original. If authorization is granted, resume Leg 4, run exactly that test, record only aggregate evidence, and confirm no provider file remains before marking Leg 4 complete and handing off to Leg 5.

Do not spawn Leg 5 before this evidence exists. External-service failure after bounded retries, inability to verify deletion, or any proposed cloud-boundary/cost-policy change remains an intervention stop.
