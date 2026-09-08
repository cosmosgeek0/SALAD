#!/bin/bash
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
runtime_dir="$repo_dir/.runtime"
helper="$runtime_dir/keychain-store"
source_file="$repo_dir/scripts/keychain-store.swift"
account="$(id -un)"

mkdir -p "$runtime_dir"
chmod 700 "$runtime_dir"
if [ ! -x "$helper" ] || [ "$source_file" -nt "$helper" ]; then
  /usr/bin/xcrun swiftc "$source_file" -o "$helper.next"
  chmod 700 "$helper.next"
  mv -f "$helper.next" "$helper"
fi

printf 'Paste the Salad API key, then press Return (typing stays hidden): ' >&2
IFS= read -r -s salad_key
printf '\n' >&2
if [ -z "$salad_key" ]; then
  echo "No key entered." >&2
  exit 1
fi
printf '%s' "$salad_key" | "$helper" --service salad-bandwidth-api --account "$account"
unset salad_key
"$helper" --read --service salad-bandwidth-api --account "$account" >/dev/null
echo "Salad API key saved and verified in macOS Keychain."
