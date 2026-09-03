# Swing analysis prompt v1

Status: contract placeholder; do not use for live analysis until the Gemini feasibility spike validates the model, structured-output schema, proxy settings, and deletion behavior.

The production prompt must identify every confident apparent ball-striking golf swing, distinguish practice-only or incomplete motions, report takeaway/impact/finish timestamps relative to the supplied proxy, and conform to `schemas/swing-analysis-v1.schema.json`. Uncertain events must be rejected as `uncertain`, not guessed.
