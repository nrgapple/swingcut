# iCloud sources

## iCloud Photos

This is the first iCloud integration. The narrow Swift PhotoKit bridge requests user authorization, resolves one exact and unique album name, and materializes local or iCloud-backed video resources into private staging with network access enabled. It uses supported PhotoKit APIs and never inspects Photos database internals.

Build or install the LaunchServices helper with:

```bash
make build-photos-app
make install-photos-app
```

The build script creates `build/SwingcutPhotosBridge.app`, embeds the Photos entitlement and usage descriptions, and signs with `SWINGCUT_CODESIGN_IDENTITY`, the first available Apple code-signing identity, or an ad-hoc development fallback. The installer intentionally rejects an ad-hoc signature and atomically deploys the consistently signed bundle to the stable path `~/Library/Application Support/Swingcut/SwingcutPhotosBridge.app`. Re-running installation is idempotent. A signing identity may require its owner to authorize private-key use.

Production Python always launches that app through `/usr/bin/open -n -a ... --args`; it never invokes the inner executable. Each invocation uses a mode-`0700` temporary directory, mode-`0600` bounded result/error files, bounded polling, and a cancellation marker. The helper checks cancellation and cancels in-progress iCloud resource requests, removing partial exports. Album assets are exported sequentially into a mode-`0700` staging directory; every copy is checked for matching asset ID/path/size and hashed before use. Per-asset failures remain private and do not prevent safe copies of other assets from being reported.

Read operations are `status`, `albums`, `library-counts`, `list --album`, and `export --asset-id --output`. The sole write operation is `import-output --input`: it accepts a non-empty regular local video, creates one new `PHAsset`, then fetches the returned local identifier and verifies that the created asset is a video. There are no edit, delete, replace, album-add, album-remove, or reorganization operations. Existing assets and albums remain immutable.

## iCloud Drive

A later source adapter will accept a Finder-visible folder and materialize on-demand files before analysis. Production code must use supported file APIs and must not depend on undocumented `brctl` behavior.

## Unsupported

Swingcut will not automate `icloud.com`, store Apple credentials, bypass MFA, or call undocumented iCloud Photos web endpoints.
