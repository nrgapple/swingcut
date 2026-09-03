# Swing analysis prompt v1

Identify every candidate golf swing in this video. Include a candidate only when an apparent ball strike is visually supported. Reject practice-only, false-start, aborted, incomplete, occluded, no-apparent-strike, no-swing, and uncertain events rather than guessing.

For accepted candidates report takeaway, impact, and finish times in seconds from video start. For rejected candidates provide no timestamps. Return only the requested JSON object conforming to `schemas/swing-analysis-v1.schema.json`.
