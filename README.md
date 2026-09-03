# Swingcut

Swingcut is a local-first macOS tool that finds apparent ball-striking golf swings in iPhone videos and combines them into one high-quality, Apple Photos-compatible video.

The repository contains a global Pi extension, strict run contracts, a deterministic FFmpeg media engine, a bounded Gemini 3.7 Flash agentic-analysis provider with a reviewed Gemini 3.5 structured fallback for persistent HTTP 429 responses, a LaunchServices PhotoKit client, a signed add-only native bridge, and resumable end-to-end backend orchestration with exact incremental caching and terminal cleanup.

## Product behavior

The approved workflow is:

1. Read videos from a local directory or an exact Apple Photos album; iCloud Photos is the first cloud-backed source.
2. Materialize originals locally without modifying the Photos library.
3. Create a full-length, low-resolution proxy stripped of source metadata.
4. Send only that proxy—not the original-resolution video—to Gemini 3.7 agentic analysis, with Gemini 3.5 strict structured fallback only after bounded primary HTTP 429 failures.
5. Keep confident apparent ball strikes; exclude practice-only, incomplete, and uncertain motions with warnings.
6. Cut each accepted segment from about two seconds before takeaway through three seconds after finish.
7. Order segments by capture time, preserve source audio, letterbox mixed orientations, and render a high-quality Photos-compatible result.
8. Delete staged copies and proxies after the output is verified. Never delete Photos assets.

Swingcut is an editor, not a golf coach or a biomechanics/medical analysis tool.

## Intended stack

- Python 3.12+ for orchestration, schemas, Gemini integration, and tests
- FFmpeg/ffprobe for media inspection, proxies, cuts, concatenation, and verification
- OpenCV/MediaPipe as optional local analysis dependencies after feasibility testing
- Swift 6 and PhotoKit for authorized Apple Photos/iCloud Photos access
- Pydantic structured data and the official `google-genai` SDK

## Prerequisites

- Apple-silicon Mac
- [uv](https://docs.astral.sh/uv/) for a project-managed Python 3.12 environment
- FFmpeg and ffprobe
- Swift 6 / Xcode Command Line Tools
- An authenticated Google Cloud CLI and project for creating the restricted Gemini API key

On Homebrew-based systems:

```bash
brew install uv ffmpeg ffmpeg-full
```

## Install for Pi

From any directory:

```bash
pi install git:github.com/nrgapple/swingcut@main
```

Restart or `/reload` Pi, run `/swingcut-setup` once, then create a compilation from any Pi project:

```text
/swingcut "Exact Photos Album"
```

The `swingcut_create` tool provides the equivalent natural-language interface. Both entry points use the same estimate, repeat-mode, confirmation, progress, and privacy-safe output logic. See [`docs/pi-package.md`](docs/pi-package.md) for prerequisites, stable install paths, updates, and safe uninstall steps.

## Development

```bash
make setup       # installs locked Python and TypeScript development dependencies
make doctor
make check
```

Common commands:

```bash
make dev                  # doctor plus CLI help
make configure-gemini-key      # create a restricted key with gcloud and store it privately
make provision-signing-identity # provision/check Swingcut's dedicated local identity
make test                      # Python tests with coverage
make test-extension            # fake-backend Pi interface tests
make test-swift                 # Swift bridge build/version smoke test
make build-photos-app           # build and sign the PhotoKit helper app bundle
make install-photos-app         # install the signed bundle at its stable user path
make lint          # Ruff, mypy, and swift-format
make format        # apply Python and Swift formatting
make build         # Python package and Swift bridge builds
make check         # full validation
```

The `.pi-web/tasks.json` file exposes setup, doctor, test, format, and check commands in PI WEB's Tasks panel.

## Current backend CLI

```bash
swingcut --version
swingcut doctor
swingcut inspect --photos-album "Exact Album" --json
swingcut run --photos-album "Exact Album" --mode incremental --import-to-photos --confirmed --json-events
swingcut run --photos-album "Exact Album" --mode rebuild --import-to-photos --confirmed --json-events
swingcut status RUN_ID --json
swingcut cancel RUN_ID
swingcut clean
```

`doctor` is local-only. It checks the standard FFmpeg tools, the keg-only `ffmpeg-full` HDR filters, whether a Gemini key exists in the environment or Swingcut's mode-`0600` private runtime file, and an aggregate stale-run count. It never reads or prints the secret, contacts Gemini, inspects Photos, requests Photos permission, or uploads media. Set `SWINGCUT_FFMPEG` to another FFmpeg build only when it provides both `zscale` and `tonemap`. Run output is aggregate and bounded; private inventory and diagnostics stay in mode-restricted Application Support storage. See [`docs/run-orchestration.md`](docs/run-orchestration.md).

## Gemini API key

Authenticate the Google Cloud CLI and select a project, then let Swingcut enable the required services and create an API key restricted to `generativelanguage.googleapis.com`:

```bash
gcloud auth login
gcloud config set project PROJECT_ID
make configure-gemini-key
```

The command suppresses provider output that could contain the secret and stores the key outside the repository at:

```text
~/Library/Application Support/Swingcut/secrets/gemini_api_key
```

The directory is mode `0700` and secret files are mode `0600`. Confirm configuration without displaying the key:

```bash
./scripts/configure-gemini-key.sh --check
make doctor
```

The provider adapter can use this private runtime credential once orchestration supplies it. Routine tests never read the key or contact Gemini. See [`docs/gemini-provider.md`](docs/gemini-provider.md) for the explicit live-test gate and cost policy.

## Private test media

Never commit personal videos, iCloud exports, generated proxies, or API credentials. Put private golden-corpus media outside the repository and follow [`tests/golden/README.md`](tests/golden/README.md). Synthetic fixtures may be generated under the ignored `tests/fixtures/generated/` directory.

Run state lives under:

```text
~/Library/Application Support/Swingcut/
```

See [`docs/privacy.md`](docs/privacy.md), [`docs/gemini-provider.md`](docs/gemini-provider.md), [`docs/icloud-sources.md`](docs/icloud-sources.md), [`docs/pi-package.md`](docs/pi-package.md), and [`docs/validation.md`](docs/validation.md).

## Status and unresolved technical choices

A representative private spike established the 480-pixel-wide, 15 fps, silent H.264 proxy. The provider enforces primary agentic processing, strict structured output on both reviewed paths, combined-path estimate-before-confirmation accounting without a hard cap, bounded retries, and immediate cloud-file deletion. The approved private album validated mixed HDR/SDR rendering and fallback discovery of eight additional apparent-strike swings; slow-motion handling and failed-run retention remain reviewable production concerns.
