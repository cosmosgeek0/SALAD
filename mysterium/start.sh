#!/bin/sh
set -eu

: "${MYSTNODES_API_KEY:?MYSTNODES_API_KEY is required}"
ready=/var/run/mysterium-node/registered
rm -f "$ready"
printf 'nameserver 1.0.0.1\n' > /etc/resolv.conf

/usr/local/bin/docker-entrypoint.sh \
    --userspace --wireguard.mtu=1100 --log-level=info \
    --mmn.api-key="$MYSTNODES_API_KEY" \
    service --agreed-terms-and-conditions &
node_pid=$!
trap 'rm -f "$ready"; kill -TERM "$node_pid" 2>/dev/null || true' EXIT
trap 'exit 0' INT TERM

deadline=$(( $(date +%s) + 180 ))
until timeout 5 wget -qO /dev/null http://127.0.0.1:4050/healthcheck; do
    kill -0 "$node_pid" 2>/dev/null || { wait "$node_pid"; exit 1; }
    if [ "$(date +%s)" -ge "$deadline" ]; then
        printf 'Mysterium API startup timed out\n' >&2
        exit 1
    fi
    sleep 2
done

node_id=''
while [ -z "$node_id" ]; do
    node_id=$(timeout 10 myst cli identities list | grep -Eo '0x[0-9a-f]{40}' | head -n 1)
    [ -z "$node_id" ] || break
    kill -0 "$node_pid" 2>/dev/null || { wait "$node_pid"; exit 1; }
    if [ "$(date +%s)" -ge "$deadline" ]; then
        printf 'Mysterium identity creation timed out\n' >&2
        exit 1
    fi
    sleep 2
done
until timeout 30 myst cli mmn "$MYSTNODES_API_KEY"; do
    kill -0 "$node_pid" 2>/dev/null || { wait "$node_pid"; exit 1; }
    printf 'Account claiming failed; retaining identity and retrying\n' >&2
    sleep 30
done
printf 'Waiting for registration; retaining identity %s while unready\n' "$node_id"

while :; do
    kill -0 "$node_pid" 2>/dev/null || { wait "$node_pid"; exit 1; }
    state=$(timeout 15 myst cli identities get "$node_id" || true)
    case "$state" in
        *'Registration Status: Registered'*) break ;;
        *'Registration Status: Unregistered'*)
        eligible=$(timeout 15 wget -qO - "http://127.0.0.1:4050/identities/$node_id/eligibility" || true)
        if printf '%s' "$eligible" | grep -Eq '"eligible"[[:space:]]*:[[:space:]]*true'; then
            printf 'Requesting sponsored registration for %s\n' "$node_id"
            if ! timeout 30 myst cli identities register "$node_id" >/dev/null; then
                printf 'Registration request failed; retaining identity and checking status before retry\n' >&2
            fi
        fi
        ;;
    esac
    sleep 30
done

touch "$ready"
printf 'Mysterium identity registered: %s\n' "$node_id"
wait "$node_pid"
