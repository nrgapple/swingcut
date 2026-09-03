# Privacy boundary

Swingcut is local-first, not local-only.

- Originals stay local and are never uploaded at original resolution.
- The selected cloud mode may upload one full-length, low-resolution proxy per source to Gemini.
- Proxies must be stripped of location and unrelated source metadata.
- Proxy audio is disabled until an explicit evaluation proves it necessary and the policy is approved.
- Uploaded Gemini files must be deleted after analysis; failed deletion remains recorded for cleanup.
- Photos-library assets are read-only. Staged copies and proxies are deleted after a successful verified render.
- Routine tests use mocks and synthetic media. Live API tests require explicit opt-in and a spend bound.

No implementation may silently widen this boundary.
