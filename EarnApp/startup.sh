set -u
umask 077
observer=$(date +%s%3N)
child=""
state=starting
error=none
sequence=0
event_sequence=0
finished=0
stopping=0
measuring=0
deadline=$((SECONDS+120))
registered_ms=0
geo=null

event() {
    printf 'EARNAPP_EVENT {"group_id":"%s","instance":"%s","machine":"%s","observer":%s,"seq":%s,"time_ms":%s,"kind":"%s","reason":"%s","http_status":%s,"exit_code":%s,"geo":%s}\n' "$SALAD_CONTAINER_GROUP_ID" "$SALAD_INSTANCE_ID" "$SALAD_MACHINE_ID" "$observer" "$event_sequence" "$(date +%s%3N)" "$1" "$2" "${3:-null}" "${4:-null}" "$geo"
    event_sequence=$((event_sequence+1))
}

sample() {
    (( measuring )) || return 0
    local end rx tx process valid amount_rx amount_tx
    end=$(date +%s%3N)
    read -r rx </sys/class/net/eth0/statistics/rx_bytes || return 1
    read -r tx </sys/class/net/eth0/statistics/tx_bytes || return 1
    process=stopped
    if [[ -n "$child" ]]; then read -r process <"/proc/$child/comm" 2>/dev/null || process=stopped; fi
    valid=true; amount_rx=$((rx-previous_rx)); amount_tx=$((tx-previous_tx))
    if (( sequence == 0 )); then amount_rx=0; amount_tx=0; start=$end; fi
    if (( amount_rx < 0 || amount_tx < 0 || end < start )); then valid=false; amount_rx=null; amount_tx=null; fi
    printf 'EARNAPP_SAMPLE {"group_id":"%s","instance":"%s","machine":"%s","observer":%s,"seq":%s,"event_seq":%s,"start_ms":%s,"end_ms":%s,"rx":%s,"tx":%s,"raw_rx":%s,"raw_tx":%s,"geo":%s,"process":"%s","state":"%s","error":"%s","valid":%s,"final":%s,"client_pid":%s,"registered_ms":%s,"deadline_ms":%s}\n' "$SALAD_CONTAINER_GROUP_ID" "$SALAD_INSTANCE_ID" "$SALAD_MACHINE_ID" "$observer" "$sequence" "$((event_sequence-1))" "$start" "$end" "$amount_rx" "$amount_tx" "$rx" "$tx" "$geo" "$process" "$state" "$error" "$valid" "$1" "${child:-0}" "$registered_ms" "$((deadline>0 ? end+(deadline-SECONDS)*1000 : 0))"
    printf '%s\n' "$EPOCHSECONDS" > /tmp/earnapp-heartbeat
    previous_rx=$rx; previous_tx=$tx; start=$end
    sequence=$((sequence+1))
    next_sample=$((SECONDS+10))
}

stop_client() {
    (( finished == 0 )) || return
    finished=1
    if [[ -n "$child" ]]; then
        kill -- "-$child" 2>/dev/null || true
        sleep 1
        kill -KILL -- "-$child" 2>/dev/null || true
        wait "$child" 2>/dev/null || true
        child=""
    fi
    sample true || true
}

stop_if_requested() {
    (( stopping )) || return 0
    state=stopped; error=operator_stop
    stop_client
    event stopped operator_stop
    exit 0
}

reallocate() {
    stop_if_requested
    state=reallocating; error=$1
    stop_client
    event requested "$1"
    local attempt response code
    for attempt in 1 2 3; do
        stop_if_requested
        response=$(wget -qS --timeout=10 --tries=1 --header='Metadata: true' --header='Content-Type: application/json' --post-data="{\"reason\":\"EarnApp $1\"}" http://169.254.169.254/v1/reallocate -O /dev/null 2>&1)
        code=$(printf '%s\n' "$response" | sed -nE 's/^[[:space:]]*HTTP\/[0-9.]+ ([0-9]{3}).*/\1/p' | tail -n 1)
        if [[ "$code" == 200 || "$code" == 204 ]]; then event accepted "$1" "$code"; stop_if_requested; exit 75; fi
        event request_failed "$1" "${code:-null}"
        (( attempt == 3 )) || sleep 15
    done
    event fallback "$1" null 75
    exit 75
}

trap 'stopping=1' TERM INT
event starting startup
mkdir -p /etc/earnapp || reallocate setup_failed
for geo_attempt in 1 2 3; do
    if geo_result=$(wget -q --timeout=8 --tries=1 https://api.country.is -O -); then
        if [[ "$geo_result" =~ \"country\"[[:space:]]*:[[:space:]]*\"([A-Z]{2})\" ]]; then
            country=${BASH_REMATCH[1]}
            if [[ "$geo_result" =~ \"ip\"[[:space:]]*:[[:space:]]*\"([0-9a-fA-F:.]+)\" ]]; then
                geo="{\"country\":\"$country\",\"ip\":\"${BASH_REMATCH[1]}\"}"
                [[ "$country" == US ]] || reallocate country_not_us
                break
            fi
        fi
    fi
    event country_unverified country_lookup_failed
    (( geo_attempt == 3 )) || sleep 5
done
[[ "$geo" != null ]] || reallocate country_unverified
stop_if_requested
wget -q --timeout=30 --tries=1 https://cdn-earnapp.b-cdn.net/static/earnapp-x64-1.665.73 -O /tmp/earnapp || reallocate client_download_failed
chmod 755 /tmp/earnapp || reallocate setup_failed
/tmp/earnapp --version || reallocate client_binary_failed
if [[ -n "${EARNAPP_UUID:-}" ]]; then
    mv /tmp/earnapp /usr/bin/earnapp || reallocate setup_failed
    printf '%s' "$EARNAPP_UUID" > /etc/earnapp/uuid || reallocate setup_failed
else
    /tmp/earnapp install --auto || reallocate installation_failed
fi
/usr/bin/earnapp showid
stop_if_requested
read -r previous_rx </sys/class/net/eth0/statistics/rx_bytes || reallocate sampler_failed
read -r previous_tx </sys/class/net/eth0/statistics/tx_bytes || reallocate sampler_failed
start=$(date +%s%3N)
measuring=1
sample false || reallocate sampler_failed
exec 3< <(exec setsid /bin/bash -c '/usr/bin/earnapp start && exec /usr/bin/earnapp run --verbose' 2>&1)
child=$!
deadline=$((SECONDS+120))
while :; do
    stop_if_requested
    if IFS= read -r -t 0.2 line <&3; then
        stop_if_requested
        printf '%s\n' "$line"
        case "$line" in
            *'✔ Registered'*) state=registered; error=none; deadline=0; registered_ms=$(date +%s%3N); event registered native_registered ;;
            *'Failed registration'*) reallocate registration_failed ;;
            *EAI_AGAIN*)
                if [[ "$state" != dns_error ]]; then deadline=$((SECONDS+120)); event error dns_lookup_failed; fi
                state=dns_error; error=dns_lookup_failed ;;
        esac
    else
        sleep 0.2
    fi
    stop_if_requested
    if ! kill -0 "$child" 2>/dev/null; then
        wait "$child"; code=$?; child=""
        event client_exited client_exited null "$code"
        reallocate client_exited
    fi
    if (( SECONDS >= next_sample )); then sample false || reallocate sampler_failed; fi
    if (( deadline > 0 && SECONDS >= deadline )); then reallocate connection_timeout; fi
done
