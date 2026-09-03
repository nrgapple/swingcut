# Run orchestration, cache, and cleanup

The Python backend owns the complete stateful workflow:

```bash
swingcut inspect --photos-album "Exact Album" --json
swingcut run --photos-album "Exact Album" --mode incremental --import-to-photos --confirmed --json-events
swingcut status RUN_ID --json
swingcut cancel RUN_ID
swingcut clean
```

`inspect` performs an exact read-only PhotoKit inventory and reports only the album name and aggregate counts, duration, conservative Gemini estimate, disclosure, and repeat choices. `run` requires the exact album, an explicit repeat mode, the Photos-only destination, and explicit confirmation. JSON events and status never contain source identifiers, filenames, paths, or provider output.

## Private state and resume

Runs live under `~/Library/Application Support/Swingcut/runs/<run-id>/`. Directories are mode `0700`; JSON records and cancellation markers are atomically written mode `0600`. Active runs persist their versioned transition history, private inventory, artifacts, completed per-source analyses, and cumulative spend. `--resume-run-id RUN_ID` continues an interrupted nonterminal run without repeating completed paid analyses. A resume at an import attempt with no persisted verified result fails closed because creating a duplicate Photos asset cannot be ruled out.

Cancellation is cooperative and is honored before Photos mutation. Once verified import starts, Swingcut finishes the safety-critical import/cleanup path rather than pretending cancellation can undo a Photos creation.

Interrupted runs are explicitly resumable for 24 hours. `doctor` reports the aggregate stale-run count, and `clean` reports stale resumable runs while removing media from terminal runs. It never deletes Photos assets or Gemini resources; Gemini uploads are deleted immediately by the provider adapter.

## Exact incremental cache

Analysis cache entries are accepted only when their entire versioned key matches:

- hashed PhotoKit source identity;
- hashed source version evidence (creation time, dimensions, duration, and other inventory fields);
- staged source content SHA-256;
- proxy profile;
- concrete Gemini model;
- prompt and response-schema SHA-256 values; and
- deterministic validator version.

Entries are strict-schema validated on read. Invalid entries are deleted and treated as misses. Incremental mode reuses exact hits and analyzes only misses; rebuild mode bypasses every hit. Both modes build a fresh edit plan and compilation from the current exact album.

## Failure and cleanup behavior

Export, probe, proxy, and provider failures are private per-source diagnostics. They do not stop eligible sources. Cost-cap and upload-deletion-debt failures stop the run. If no confident segment remains, Swingcut imports nothing and still reaches a cleaned terminal state.

On verified success, provider uploads have already been deleted, then run-owned staged sources and proxies are removed, and finally the local rendered master is removed after PhotoKit returns verified creation. The private run record is deleted; only the privacy-safe manifest/state and mode-restricted exact cache remain.
