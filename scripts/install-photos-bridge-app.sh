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
    echo "The Photos bridge must use Swingcut's stable dedicated signing identity." >&2
    exit 1
    ;;
esac
source_requirement="$(codesign --display --requirements - "$source_app" 2>&1 \
  | awk '/^designated =>/ { print; exit }')"
[ -n "$source_requirement" ] || { echo "Missing designated signing requirement." >&2; exit 1; }

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
if [ -e "$destination" ]; then
  codesign --verify --strict "$destination"
  installed_requirement="$(codesign --display --requirements - "$destination" 2>&1 \
    | awk '/^designated =>/ { print; exit }')"
  if [ "$installed_requirement" != "$source_requirement" ]; then
    echo "Refusing to replace a helper with a different signing requirement." >&2
    echo "Follow the signing recovery instructions in docs/icloud-sources.md." >&2
    exit 1
  fi
fi
rm -rf "$destination"
mv "$temporary" "$destination"
trap - EXIT HUP INT TERM
codesign --verify --strict "$destination"
printf '%s\n' "$destination"
