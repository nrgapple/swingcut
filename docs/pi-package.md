# Pi package installation and lifecycle

Swingcut is distributed as a public Git-backed Pi package. The Pi extension is a thin client; `/swingcut-setup` explicitly installs the locked Python backend and consistently signed PhotoKit helper under the user's stable Application Support directory. Merely installing the Pi package does not inspect Photos, request Photos access, or contact Gemini.

## Install

Prerequisites are macOS, `uv`, Swift/Xcode Command Line Tools, and an FFmpeg build with both `zscale` and `tonemap`. Homebrew users can install them with:

```bash
brew install uv ffmpeg ffmpeg-full
```

Install the package globally, from any directory:

```bash
pi install git:github.com/nrgapple/swingcut@main
```

Start or reload Pi, then run:

```text
/swingcut-setup
```

Setup first displays and confirms every destination. It then verifies prerequisites before making changes and idempotently deploys:

```text
~/Library/Application Support/Swingcut/backend/releases/<git-revision>/.venv/
~/Library/Application Support/Swingcut/backend/current
~/Library/Application Support/Swingcut/backend/bin/swingcut
~/Library/Application Support/Swingcut/SwingcutPhotosBridge.app
~/Library/Application Support/Swingcut/signing/
```

The backend is installed from a wheel into a lockfile-backed, revisioned environment—not as an editable checkout. `backend/current` is switched only after the new release passes its version check. The stable `backend/bin/swingcut` launcher also preserves the verified FFmpeg path for every project. The signed app keeps one stable destination and signing requirement so its TCC identity remains consistent. Setup does not request Photos permission or call Gemini. macOS may ask once for account authorization while trusting Swingcut's dedicated local signing certificate.

Configure the restricted Gemini key as described in [the README](../README.md#gemini-api-key). `swingcut doctor` reports the key as optional until a run needs it. Photos permission is requested only when an exact album is first inspected.

## Use

From any Pi project:

```text
/swingcut "Exact Photos Album"
```

The command inventories only that exact album and displays its video count, duration, low-resolution cloud-proxy disclosure, dated estimate for every possible Gemini path, repeat mode, and add-only Photos destination. Paid or mutating work starts only after explicit confirmation. Existing Photos assets and albums are never changed.

Natural-language requests use the same shared runner through the `swingcut_create` tool. In interactive Pi, the same selection and confirmation dialogs appear. In non-interactive modes, the tool fails safely unless `mode` and `confirmed=true` are explicit.

## Update

Git package refs are pinned. To refresh the `main` ref, repeat the install command, restart or `/reload` Pi, and rerun setup:

```bash
pi install git:github.com/nrgapple/swingcut@main
```

```text
/swingcut-setup
```

Setup creates a new revisioned backend only when needed, verifies it, atomically moves `backend/current`, and updates the helper only when its stable signing requirement matches. Existing secrets, cache, run recovery state, and signing identity are retained.

## Uninstall

First remove the globally registered Pi package:

```bash
pi remove git:github.com/nrgapple/swingcut
```

Remove only executable runtime components while preserving private run recovery data, cache, the Gemini key, and the stable signing identity:

```bash
rm -rf \
  "$HOME/Library/Application Support/Swingcut/backend" \
  "$HOME/Library/Application Support/Swingcut/SwingcutPhotosBridge.app"
```

No command above touches any Photos asset. To remove the dedicated signing identity and its user trust record, follow the narrowly scoped steps in [iCloud sources](icloud-sources.md#signing-removal-and-recovery); never remove another product's keychain or certificate.

After confirming that no interrupted run needs recovery, remove all remaining Swingcut-local state—including secrets, private diagnostics, and cache—with:

```bash
rm -rf "$HOME/Library/Application Support/Swingcut"
```

This final deletion is irreversible locally but still does not edit or delete anything in Photos or Gemini. Gemini uploads are deleted during each bounded provider call rather than by the uninstaller.
