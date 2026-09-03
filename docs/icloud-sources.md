# iCloud sources

## iCloud Photos

This is the first iCloud integration. The narrow Swift PhotoKit bridge requests user authorization, lists videos from an exact album, and materializes local or iCloud-backed original resources into private staging with network access enabled. It uses supported PhotoKit APIs, does not inspect Photos database internals, and has no library mutation commands.

Build the LaunchServices helper with:

```bash
make build-photos-app
```

The build script creates `build/SwingcutPhotosBridge.app`, signs it with the first available Apple code-signing identity (or an ad-hoc fallback), and embeds the Photos entitlement and usage description. Launch the app bundle rather than invoking its inner executable directly: macOS attributes Photos consent to the responsible app identity. App-bundle invocations support `--result-file` and `--error-file` so a CLI adapter can launch the short-lived helper asynchronously and poll for completion without relying on inherited standard streams.

Implemented bridge commands are `status`, `albums`, `library-counts`, `list --album`, and `export --asset-id --output`. Export writes a staging copy only; it never alters the source asset.

## iCloud Drive

A later source adapter will accept a Finder-visible folder and materialize on-demand files before analysis. Production code must use supported file APIs and must not depend on undocumented `brctl` behavior.

## Unsupported

Swingcut will not automate `icloud.com`, store Apple credentials, bypass MFA, or call undocumented iCloud Photos web endpoints.
