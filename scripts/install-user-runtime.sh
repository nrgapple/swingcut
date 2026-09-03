#!/bin/sh
set -eu

umask 077
project_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
install_root="${SWINGCUT_INSTALL_ROOT:-$HOME/Library/Application Support/Swingcut}"
backend_root="$install_root/backend"

fail() {
  printf 'Swingcut setup: %s\n' "$1" >&2
  exit 1
}

[ "$(uname -s)" = "Darwin" ] || fail "macOS is required"
for command in uv swift codesign security ditto ffprobe; do
  command -v "$command" >/dev/null 2>&1 || fail "required command not found: $command"
done

ffmpeg_path="${SWINGCUT_FFMPEG:-}"
if [ -z "$ffmpeg_path" ]; then
  for candidate in /opt/homebrew/opt/ffmpeg-full/bin/ffmpeg /usr/local/opt/ffmpeg-full/bin/ffmpeg; do
    if [ -x "$candidate" ]; then
      ffmpeg_path="$candidate"
      break
    fi
  done
fi
[ -n "$ffmpeg_path" ] && [ -x "$ffmpeg_path" ] \
  || fail "ffmpeg-full is required (brew install ffmpeg-full or set SWINGCUT_FFMPEG)"
filters="$($ffmpeg_path -hide_banner -filters 2>/dev/null)"
printf '%s\n' "$filters" | grep -q ' zscale ' || fail "selected FFmpeg lacks zscale"
printf '%s\n' "$filters" | grep -q ' tonemap ' || fail "selected FFmpeg lacks tonemap"

revision="$(git -C "$project_root" rev-parse --verify HEAD 2>/dev/null \
  || shasum -a 256 "$project_root/uv.lock" | awk '{print $1}')"
case "$revision" in
  *[!0-9a-f]*) fail "could not determine a safe package revision" ;;
esac
release="$backend_root/releases/$revision"
python="$release/.venv/bin/python"
executable="$release/.venv/bin/swingcut"

mkdir -p "$install_root" "$backend_root" "$backend_root/bin" "$backend_root/releases"
chmod 700 "$install_root" "$backend_root" "$backend_root/bin" "$backend_root/releases"

if [ ! -x "$executable" ]; then
  [ ! -e "$release" ] || fail "incomplete backend release exists at $release"
  mkdir -p "$release"
  chmod 700 "$release"
  cleanup_release=1
  trap '[ "${cleanup_release:-0}" = 0 ] || rm -rf "$release"' EXIT HUP INT TERM

  UV_PYTHON_PREFERENCE=only-managed uv venv --python 3.12 "$release/.venv"
  UV_PROJECT_ENVIRONMENT="$release/.venv" UV_PYTHON_PREFERENCE=only-managed \
    uv sync --project "$project_root" --frozen --no-dev --no-install-project
  wheel_dir="$release/wheel"
  mkdir -p "$wheel_dir"
  UV_PYTHON_PREFERENCE=only-managed uv build --project "$project_root" --wheel --out-dir "$wheel_dir"
  wheel="$(find "$wheel_dir" -type f -name 'swingcut-*.whl' -print | head -n 1)"
  [ -n "$wheel" ] || fail "backend wheel was not produced"
  uv pip install --python "$python" --no-deps "$wheel"
  rm -rf "$wheel_dir"
  "$executable" --version >/dev/null
  cleanup_release=0
  trap - EXIT HUP INT TERM
fi

temporary_link="$backend_root/.current.$$"
rm -f "$temporary_link"
ln -s "releases/$revision" "$temporary_link"
mv -f -h "$temporary_link" "$backend_root/current"

printf '%s\n' "$ffmpeg_path" >"$backend_root/ffmpeg-path"
chmod 600 "$backend_root/ffmpeg-path"
launcher="$backend_root/bin/swingcut"
temporary_launcher="$backend_root/bin/.swingcut.$$"
cat >"$temporary_launcher" <<'EOF'
#!/bin/sh
set -eu
backend_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SWINGCUT_FFMPEG="$(cat "$backend_root/ffmpeg-path")"
export SWINGCUT_FFMPEG
exec "$backend_root/current/.venv/bin/swingcut" "$@"
EOF
chmod 755 "$temporary_launcher"
mv -f "$temporary_launcher" "$launcher"

SWINGCUT_INSTALL_ROOT="$install_root" "$project_root/scripts/install-photos-bridge-app.sh" >/dev/null
codesign --verify --strict "$install_root/SwingcutPhotosBridge.app"
SWINGCUT_INSTALL_ROOT="$install_root" SWINGCUT_REQUIRE_INSTALLED=1 "$launcher" doctor
printf 'Swingcut backend: %s\n' "$launcher"
printf 'Swingcut Photos helper: %s\n' "$install_root/SwingcutPhotosBridge.app"
