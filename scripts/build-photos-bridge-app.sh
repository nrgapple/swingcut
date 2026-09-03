#!/bin/sh
set -eu

project_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
package="$project_root/native/SwingcutPhotosBridge"
configuration="${1:-debug}"
case "$configuration" in
  debug|release) ;;
  *) echo "Usage: $0 [debug|release]" >&2; exit 2 ;;
esac

swift build --package-path "$package" --configuration "$configuration"
bin_dir="$(swift build --package-path "$package" --configuration "$configuration" --show-bin-path)"
app="$project_root/build/SwingcutPhotosBridge.app"
contents="$app/Contents"

python3 - "$app" <<'PY'
import shutil
import sys
from pathlib import Path
path = Path(sys.argv[1])
if path.exists():
    shutil.rmtree(path)
PY
mkdir -p "$contents/MacOS"
cp "$package/Info.plist" "$contents/Info.plist"
cp "$bin_dir/swingcut-photos-bridge" "$contents/MacOS/swingcut-photos-bridge"
chmod 755 "$contents/MacOS/swingcut-photos-bridge"

identity="${SWINGCUT_CODESIGN_IDENTITY:-$(security find-identity -v -p codesigning 2>/dev/null | awk '/"/ { print $2; exit }')}"
if [ -z "$identity" ]; then
  identity="-"
  echo "warning: no Apple code-signing identity found; using an ad-hoc signature" >&2
fi

codesign \
  --force \
  --sign "$identity" \
  --identifier dev.swingcut.photos-bridge \
  --entitlements "$package/SwingcutPhotosBridge.entitlements" \
  "$app"

codesign --verify --strict "$app"
printf '%s\n' "$app"
