#!/bin/sh
set -eu

secret_dir="$HOME/Library/Application Support/Swingcut/secrets"
secret_file="$secret_dir/gemini_api_key"
resource_file="$secret_dir/gemini_api_key_resource"

if [ "${1:-}" = "--check" ]; then
  if [ -s "$secret_file" ]; then
    echo "Swingcut Gemini API key is configured in private runtime storage."
    exit 0
  fi
  echo "Swingcut Gemini API key is not configured." >&2
  exit 1
fi

if [ -s "$secret_file" ]; then
  echo "Swingcut already has a configured Gemini API key." >&2
  echo "Refusing to create a duplicate. Use --check to verify it." >&2
  exit 1
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud is required. Install the Google Cloud CLI first." >&2
  exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | grep -q .; then
  echo "No active gcloud login. Run: gcloud auth login" >&2
  exit 1
fi

project="$(gcloud config get-value project 2>/dev/null)"
if [ -z "$project" ] || [ "$project" = "(unset)" ]; then
  echo "No gcloud project is selected. Run: gcloud config set project PROJECT_ID" >&2
  exit 1
fi

key_id="swingcut-$(date -u +%Y%m%d%H%M%S)-$$"
resource="projects/$project/locations/global/keys/$key_id"

printf 'Enabling the API Keys and Gemini APIs in the configured gcloud project...\n'
gcloud services enable \
  apikeys.googleapis.com \
  generativelanguage.googleapis.com \
  --project="$project" \
  --quiet >/dev/null

printf 'Creating a key restricted to the Gemini API...\n'
# gcloud may include the secret in normal operation output, so suppress both streams.
if ! gcloud services api-keys create \
  --project="$project" \
  --key-id="$key_id" \
  --display-name="Swingcut Gemini API" \
  --api-target=service=generativelanguage.googleapis.com \
  --quiet >/dev/null 2>&1; then
  echo "Key creation failed. Inspect gcloud configuration and try again." >&2
  exit 1
fi

key="$(gcloud services api-keys get-key-string "$resource" --format='value(keyString)' 2>/dev/null)"
case "$key" in
  AIza*) ;;
  *)
    echo "The key was created but could not be retrieved safely." >&2
    echo "Key resource requiring cleanup: $resource" >&2
    exit 1
    ;;
esac

umask 077
mkdir -p "$secret_dir"
printf '%s' "$key" > "$secret_file"
printf '%s' "$resource" > "$resource_file"
chmod 700 "$HOME/Library/Application Support/Swingcut" "$secret_dir"
chmod 600 "$secret_file" "$resource_file"
unset key

echo "Stored the restricted Gemini key in Swingcut private runtime storage."
