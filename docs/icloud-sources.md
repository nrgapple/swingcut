# iCloud sources

## iCloud Photos

This is the first iCloud integration. The narrow Swift PhotoKit bridge requests user authorization, resolves one exact and unique album name, and materializes local or iCloud-backed video resources into private staging with network access enabled. It uses supported PhotoKit APIs and never inspects Photos database internals.

Build or install the LaunchServices helper with:

```bash
make build-photos-app
make install-photos-app
```

The build script creates `build/SwingcutPhotosBridge.app`, embeds the Photos entitlement and usage descriptions, and signs it with Swingcut's dedicated self-signed local identity. `make provision-signing-identity` creates that identity once in `~/Library/Application Support/Swingcut/signing/swingcut-signing.keychain-db`, stores its generated keychain password in a mode-`0600` file beside it, and grants `/usr/bin/codesign` access to only the dedicated private key. The signing keychain is not added to the user's keychain search list and no unrelated signing identity or keychain is inspected or changed. macOS may request the user's account authorization once when the self-signed certificate is first trusted; subsequent builds unlock only the dedicated keychain with its private stored password and do not show a key-use prompt.

The installer rejects ad-hoc signatures and atomically deploys the bundle to the stable path `~/Library/Application Support/Swingcut/SwingcutPhotosBridge.app`. Re-running provisioning, building, and installation reuses the same certificate. If an app is already installed, the installer also refuses a replacement whose designated signing requirement differs, preserving its stable TCC identity.

### Signing removal and recovery

To remove Swingcut's local identity, first remove the installed helper. Then remove the user trust entry using the persisted public certificate and delete only Swingcut's signing directory:

```bash
rm -rf "$HOME/Library/Application Support/Swingcut/SwingcutPhotosBridge.app"
security remove-trusted-cert "$HOME/Library/Application Support/Swingcut/signing/swingcut-code-signing.cer"
rm -rf "$HOME/Library/Application Support/Swingcut/signing"
```

Never remove another product's keychain. If Swingcut's keychain, password, or certificate is missing or damaged, use the same removal steps for the remaining files and rerun `make provision-signing-identity`. Recovery creates a new certificate and therefore a new TCC identity; install it only after removing the old app, and expect Photos authorization to be requested again when a separately approved operation first needs access.

Production Python always launches that app through `/usr/bin/open -n -a ... --args`; it never invokes the inner executable. Each invocation uses a mode-`0700` temporary directory, mode-`0600` bounded result/error files, bounded polling, and a cancellation marker. The helper checks cancellation and cancels in-progress iCloud resource requests, removing partial exports. Album assets are exported sequentially into a mode-`0700` staging directory; every copy is checked for matching asset ID/path/size and hashed before use. Per-asset failures remain private and do not prevent safe copies of other assets from being reported.

Read operations are `status`, `albums`, `library-counts`, `list --album`, and `export --asset-id --output`. The sole write operation is `import-output --input`: it accepts a non-empty regular local video, creates one new `PHAsset`, then fetches the returned local identifier and verifies that the created asset is a video. There are no edit, delete, replace, album-add, album-remove, or reorganization operations. Existing assets and albums remain immutable.

## iCloud Drive

A later source adapter will accept a Finder-visible folder and materialize on-demand files before analysis. Production code must use supported file APIs and must not depend on undocumented `brctl` behavior.

## Unsupported

Swingcut will not automate `icloud.com`, store Apple credentials, bypass MFA, or call undocumented iCloud Photos web endpoints.
