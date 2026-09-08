#!/bin/bash
set -euo pipefail
if [[ ! -t 0 || ! -t 2 ]]; then
  printf '%s\n' 'Run this command in an interactive terminal; piped input is refused.' >&2
  exit 2
fi
rp_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
rp_ssh_config="$rp_root/../Website/linux/ssh_config"
if [[ ! -r "$rp_ssh_config" ]]; then
  printf '%s\n' 'The sibling Website/linux/ssh_config is required.' >&2
  exit 2
fi
ssh -F "$rp_ssh_config" -tt salad-mumbai '
set -eu
rp_restart() {
  rp_status=$?
  trap - EXIT HUP INT TERM
  if ! sudo -n systemctl start salad-repocket-provider.service; then
    printf "%s\n" "RP provider collector could not restart; service attention is required." >&2
    if [ "$rp_status" -eq 0 ]; then rp_status=1; fi
  fi
  exit "$rp_status"
}
trap rp_restart EXIT
trap '\''exit 129'\'' HUP
trap '\''exit 130'\'' INT
trap '\''exit 143'\'' TERM
sudo -n systemctl stop salad-repocket-provider.service
sudo -n -u salad /usr/bin/python3 -B /opt/salad/scripts/save-provider-access.py --mode email_password
'
