# Validation strategy

Routine validation is local and deterministic:

```bash
make check
```

This runs Python linting, static typing, formatting checks, unit tests with coverage, Swift formatting, a bridge build/version/capability smoke test, and Python/Swift builds. Routine PhotoKit tests mock LaunchServices and verify exact-name forwarding, private bounded result files, cancellation/timeouts, sequential exports, checksums, partial failures, and verified import responses. PhotoKit authorization, real exact-album inventory, iCloud-backed export, and creation verification still require an explicitly approved signed app-bundle integration test on macOS because they depend on TCC and a real Photos library.

For native installation acceptance, run `make provision-signing-identity` twice and confirm both invocations print the same certificate fingerprint. Run `make install-photos-app` twice and compare `codesign --display --requirements -` for the installed app; the installer itself refuses a changed designated requirement. The dedicated keychain and password must remain mode `0600`, their parent directories mode `0700`, and `/usr/bin/codesign` must rebuild without a GUI key-use prompt. Query the installed app's `status` operation before any other real operation: `not-determined` is a stop condition because status itself does not request authorization.

Private iPhone footage must remain outside Git. The future golden corpus should cover single and multiple apparent strikes, practice-only and aborted motions, no-swing negatives, portrait and landscape, H.264 and HEVC, HDR/SDR, varied frame rates, and local versus iCloud-only Photos assets.

Model upgrades must be compared on discovery recall, invalid inclusion, timestamp error, schema validity, latency, and cost before changing the default model. Output acceptance requires successful decoding in QuickTime and manual import into Apple Photos without source mutation. The tested deterministic proxy and output profiles are specified in [`media-engine.md`](media-engine.md).

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
