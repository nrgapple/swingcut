# Swingcut

Swingcut is a planned local-first macOS tool that will find apparent ball-striking golf swings in iPhone videos and combine them into one high-quality, Apple Photos-compatible video.

The repository currently contains strict run contracts, a deterministic FFmpeg media engine, a LaunchServices PhotoKit client, and a signed native bridge that can inventory exact albums, export read-only staging copies, and add one verified new output asset. A private feasibility spike also validated Gemini 3.8 Flash agentic video analysis. End-to-end pipeline orchestration is not implemented yet.

## Product behavior

The approved workflow is:

1. Read videos from a local directory or an exact Apple Photos album; iCloud Photos is the first cloud-backed source.
2. Materialize originals locally without modifying the Photos library.
3. Create a full-length, low-resolution proxy stripped of source metadata.
4. Send only that proxy—not the original-resolution video—to Gemini agentic video understanding.
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
brew install uv ffmpeg
```

## Development

```bash
make setup       # installs a uv-managed Python 3.12 and project dependencies
make doctor
make check
```

Common commands:

```bash
make dev                  # doctor plus CLI help
make configure-gemini-key # create a restricted key with gcloud and store it privately
make test                 # Python tests with coverage
make test-swift            # Swift bridge build/version smoke test
make build-photos-app       # build and sign the PhotoKit helper app bundle
make install-photos-app     # install the signed bundle at its stable user path
make lint          # Ruff, mypy, and swift-format
make format        # apply Python and Swift formatting
make build         # Python package and Swift bridge builds
make check         # full validation
```

The `.pi-web/tasks.json` file exposes setup, doctor, test, format, and check commands in PI WEB's Tasks panel.

## Current CLI

```bash
swingcut --version
swingcut doctor
```

`doctor` is local-only. It checks whether a Gemini key exists in the environment or Swingcut's mode-`0600` private runtime file, but it never reads or prints the secret, contacts Gemini, inspects Photos, requests Photos permission, or uploads media.

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

The Gemini feasibility spike reads this private runtime file. Production video-analysis orchestration is not implemented yet.

Planned interfaces include:

```bash
swingcut inspect --input /path/to/videos
swingcut run --photos-album "Golf Swings" --output golf-swings.mov
swingcut run --input /path/to/videos --output golf-swings.mov
swingcut resume <run-id>
swingcut show-plan <run-id>
swingcut clean --failed-runs
```

## Private test media

Never commit personal videos, iCloud exports, generated proxies, or API credentials. Put private golden-corpus media outside the repository and follow [`tests/golden/README.md`](tests/golden/README.md). Synthetic fixtures may be generated under the ignored `tests/fixtures/generated/` directory.

Run state will eventually live under:

```text
~/Library/Application Support/Swingcut/
```

See [`docs/privacy.md`](docs/privacy.md), [`docs/icloud-sources.md`](docs/icloud-sources.md), and [`docs/validation.md`](docs/validation.md).

## Status and unresolved technical choices

A representative private spike established a provisional 480-pixel-wide, 15 fps, silent H.264 proxy and successfully exercised Gemini 3.8 Flash agentic video processing with structured output and immediate cloud-file deletion. Broader footage must still determine whether those proxy settings preserve adequate recall, along with HDR/SDR rendering, slow-motion handling, and failed-run retention. Licensing/public distribution is also undecided, so no license file is included yet.
