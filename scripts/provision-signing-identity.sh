#!/bin/sh
set -eu

umask 077

install_root="${SWINGCUT_INSTALL_ROOT:-$HOME/Library/Application Support/Swingcut}"
signing_root="${SWINGCUT_SIGNING_ROOT:-$install_root/signing}"
keychain="$signing_root/swingcut-signing.keychain-db"
password_file="$signing_root/keychain-password"
certificate_file="$signing_root/swingcut-code-signing.cer"
identity_name="Swingcut Local Code Signing"

fail_recovery() {
  echo "Swingcut's dedicated signing identity is incomplete or unusable." >&2
  echo "Follow the signing recovery instructions in docs/icloud-sources.md." >&2
  exit 1
}

case "${1:-}" in
  ""|--check) ;;
  *) echo "Usage: $0 [--check]" >&2; exit 2 ;;
esac

mkdir -p "$install_root" "$signing_root"
chmod 700 "$install_root" "$signing_root"

if [ -e "$keychain" ] || [ -e "$password_file" ] || [ -e "$certificate_file" ]; then
  [ -f "$keychain" ] && [ -f "$password_file" ] && [ -f "$certificate_file" ] \
    || fail_recovery
else
  temporary="$(mktemp -d "$signing_root/.provision.XXXXXX")"
  trap 'rm -rf "$temporary"' EXIT HUP INT TERM
  chmod 700 "$temporary"

  /usr/bin/openssl rand -hex 32 >"$temporary/keychain-password"
  chmod 600 "$temporary/keychain-password"
  password="$(cat "$temporary/keychain-password")"

  cat >"$temporary/openssl.cnf" <<'EOF'
[req]
distinguished_name = subject
prompt = no
x509_extensions = code_signing

[subject]
CN = Swingcut Local Code Signing
O = Swingcut Local

[code_signing]
basicConstraints = critical, CA:false
keyUsage = critical, digitalSignature
extendedKeyUsage = critical, codeSigning
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always
EOF

  /usr/bin/openssl req -new -x509 -newkey rsa:2048 -nodes \
    -days 3650 \
    -config "$temporary/openssl.cnf" \
    -keyout "$temporary/private-key.pem" \
    -out "$temporary/certificate.pem" >/dev/null 2>&1
  /usr/bin/openssl x509 -in "$temporary/certificate.pem" -outform der \
    -out "$temporary/certificate.cer"
  /usr/bin/openssl pkcs12 -export \
    -inkey "$temporary/private-key.pem" \
    -in "$temporary/certificate.pem" \
    -name "$identity_name" \
    -passout "pass:$password" \
    -out "$temporary/identity.p12"

  /usr/bin/security create-keychain -p "$password" "$temporary/swingcut-signing.keychain-db"
  /usr/bin/security unlock-keychain -p "$password" "$temporary/swingcut-signing.keychain-db"
  /usr/bin/security import "$temporary/identity.p12" \
    -k "$temporary/swingcut-signing.keychain-db" \
    -P "$password" -T /usr/bin/codesign >/dev/null

  mv "$temporary/keychain-password" "$password_file"
  mv "$temporary/certificate.cer" "$certificate_file"
  mv "$temporary/swingcut-signing.keychain-db" "$keychain"
  chmod 600 "$password_file" "$certificate_file" "$keychain"
  trap - EXIT HUP INT TERM
  rm -rf "$temporary"
fi

chmod 600 "$password_file" "$certificate_file" "$keychain"
password="$(cat "$password_file")"
/usr/bin/security unlock-keychain -p "$password" "$keychain"
/usr/bin/security set-keychain-settings -lut 21600 "$keychain"
/usr/bin/security set-key-partition-list \
  -S apple-tool:,apple: -s -k "$password" -l "$identity_name" "$keychain" >/dev/null

find_identity() {
  /usr/bin/security find-identity -v -p codesigning "$keychain" 2>/dev/null \
    | awk -v name="$identity_name" 'index($0, "\"" name "\"") { print $2; exit }'
}
identity="$(find_identity)"
if [ -z "$identity" ]; then
  /usr/bin/security add-trusted-cert -r trustRoot -p codeSign -k "$keychain" \
    "$certificate_file" >/dev/null
  identity="$(find_identity)"
fi
[ -n "$identity" ] || fail_recovery

printf '%s\n' "$identity"
