#!/bin/sh
set -eu

project_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
install_root="${SWINGCUT_INSTALL_ROOT:-$HOME/Library/Application Support/Swingcut}"
destination="$install_root/SwingcutPhotosBridge.app"

"$project_root/scripts/build-photos-bridge-app.sh" release >/dev/null
source_app="$project_root/build/SwingcutPhotosBridge.app"

signature_details="$(codesign --display --verbose=4 "$source_app" 2>&1)"
case "$signature_details" in
  *"Signature=adhoc"*)
    echo "A stable Apple code-signing identity is required for installation." >&2
    echo "Set SWINGCUT_CODESIGN_IDENTITY or install an Apple Development certificate." >&2
    exit 1
    ;;
esac

mkdir -p "$install_root"
chmod 700 "$install_root"
temporary="$install_root/.SwingcutPhotosBridge.app.$$"
trap 'rm -rf "$temporary"' EXIT HUP INT TERM
rm -rf "$temporary"
ditto "$source_app" "$temporary"
codesign --verify --strict "$temporary"
identifier="$(defaults read "$temporary/Contents/Info" CFBundleIdentifier)"
if [ "$identifier" != "dev.swingcut.photos-bridge" ]; then
  echo "Unexpected helper bundle identifier: $identifier" >&2
  exit 1
fi
rm -rf "$destination"
mv "$temporary" "$destination"
trap - EXIT HUP INT TERM
codesign --verify --strict "$destination"
printf '%s\n' "$destination"
