# Validation strategy

Routine validation is local and deterministic:

```bash
make check
```

This runs Python linting, static typing, formatting checks, unit tests with coverage, Swift formatting, a bridge build/version/capability smoke test, and Python/Swift builds. Routine PhotoKit tests mock LaunchServices and verify exact-name forwarding, private bounded result files, cancellation/timeouts, sequential exports, checksums, partial failures, and verified import responses. PhotoKit authorization, real exact-album inventory, iCloud-backed export, and creation verification still require an explicitly approved signed app-bundle integration test on macOS because they depend on TCC and a real Photos library.

For native installation acceptance, run `make provision-signing-identity` twice and confirm both invocations print the same certificate fingerprint. Run `make install-photos-app` twice and compare `codesign --display --requirements -` for the installed app; the installer itself refuses a changed designated requirement. The dedicated keychain and password must remain mode `0600`, their parent directories mode `0700`, and `/usr/bin/codesign` must rebuild without a GUI key-use prompt. Query the installed app's `status` operation before any other real operation: `not-determined` is a stop condition because status itself does not request authorization.

## 2026-09-03 stable-signing checkpoint

The dedicated identity passed two idempotent provision checks. Two release builds/installations produced the same designated requirement and CDHash at the stable app path, without a private-key prompt, and the keychain search list matched its original value afterward. The installed helper passed strict signature verification. Its non-prompting PhotoKit `status` operation initially returned `not-determined`, so acceptance stopped without requesting Photos authorization or reading the library.

After explicit user approval, the helper received Photos authorization and completed a bounded private acceptance run without recording private names or identifiers in the repository. It inventoried and sequentially exported all four assets from the exact test album with zero failures, verified every staged copy, added one clearly named generated synthetic compilation, verified the new video asset, confirmed the exact album inventory was unchanged, and observed the library video count increase by exactly one. The temporary staging and generated local master were removed. A final capability check exposed only `import-output` as a write operation and no existing-asset mutation operation.

Private iPhone footage must remain outside Git. The future golden corpus should cover single and multiple apparent strikes, practice-only and aborted motions, no-swing negatives, portrait and landscape, H.264 and HEVC, HDR/SDR, varied frame rates, and local versus iCloud-only Photos assets.

Model upgrades must be compared on discovery recall, invalid inclusion, timestamp error, schema validity, latency, and cost before changing the default model. Output acceptance requires successful decoding in QuickTime and manual import into Apple Photos without source mutation. The tested deterministic proxy and output profiles are specified in [`media-engine.md`](media-engine.md).

## 2026-09-04 provider selection checkpoint

An approved private comparison used the shortest source from the existing exact test album. Gemini 3.7 Flash completed agentic processing, returned one schema-valid accepted candidate, reported a calculated paid-tier cost of US$0.019455, and left no provider upload or local temporary media. Gemini 3.8 Flash had previously returned completed usage above Swingcut's conservative estimate and then persistent high-demand HTTP 500 errors. The user explicitly approved 3.7 as the production primary.

A later 109.277-second source repeatedly received HTTP 429 from 3.7 Interactions while Gemini 3.5 Flash GenerateContent returned nine valid strict timelines in diagnostic evaluation. The user approved 3.5 as an HTTP-429-only fallback. The production fallback accepted eight apparent-strike swings at an actual conservatively accounted cost of US$0.102528, deleted its upload, and produced a verified 12-segment compilation with zero failed sources and complete local cleanup. `MODEL_POLICIES` centralizes both reviewed paths and pricing.

## 2026-09-02 feasibility checkpoint

A private, developer-signed integration run validated:

- persistent PhotoKit authorization after rebuilding the app bundle (at the former development build path);
- exact-album inventory of four portrait videos totaling 206.1 seconds;
- read-only export of one iCloud Photos asset to private staging;
- ffprobe inspection of HEVC source media with audio;
- full-duration conversion to a 480-pixel-wide, 15 fps, silent H.264 proxy;
- removal of source metadata, with no location, device, or creation-time keys in the proxy;
- Gemini 3.8 Flash Interactions API analysis using `processing: agentic` and a JSON schema;
- an in-bounds, ordered timestamp result on the sampled clip; and
- deletion of the Gemini Files API upload in a `finally` cleanup path.

The sample was only about two seconds long, so this proves integration behavior—not recall or timestamp accuracy on long, multi-swing footage. Those require the private golden corpus.
