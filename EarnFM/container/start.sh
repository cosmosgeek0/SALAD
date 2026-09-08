#!/bin/sh
set -u
: "${EARNFM_TOKEN:?EarnFM client key is required}"
umask 077
ef_dir=$(mktemp -d /tmp/earnfm.XXXXXX)
ef_instance=${SALAD_INSTANCE_ID:-local}
ef_machine=${SALAD_MACHINE_ID:-local}
ef_start=$(date +%s)
ef_run="$ef_instance/$ef_start/$$"
ef_child=''; ef_seq=-1; ef_event_seq=0; ef_rx=0; ef_tx=0
ef_total_rx=0; ef_total_tx=0; ef_last=$ef_start
ef_state=starting; ef_error=none; ef_control=-1; ef_generation=0
ef_ip=''; ef_country=''; ef_retry_at=0
ef_auth_delay=900
ef_window_start=0; ef_window_bytes=0; ef_activity_due=0; ef_window_valid=1
# Activity windows are measurements only. Healthy clients retain their connection at zero traffic.
ef_activity_seconds=${EARNFM_ACTIVITY_SECONDS:-900}
# Preserve the legacy numeric telemetry field; old configured floors no longer trigger recovery.
ef_min_bytes=0
ef_expected_country=${EARNFM_COUNTRY:-US}
case "$ef_expected_country" in [A-Z][A-Z]) ;; *) printf 'EF_CONFIG_ERROR invalid country\n'; exit 1 ;; esac
for ef_value in "$ef_activity_seconds"; do
  case "$ef_value" in *[!0-9]*|'') printf 'EF_CONFIG_ERROR invalid activity policy\n'; exit 1 ;; esac
done
[ "$ef_activity_seconds" -ge 60 ] || exit 1
mkfifo "$ef_dir/log"
exec 3<>"$ef_dir/log"
monotonic() { read -r ef_up ef_rest < /proc/uptime; printf '%s\n' "${ef_up%%.*}"; }
event() {
  ef_event_seq=$((ef_event_seq+1))
  printf '{"kind":"earnfm_event","revision":2,"run":"%s","event_seq":%s,"instance":"%s","machine":"%s","time_ms":%s000,"action":"%s","reason":"%s","http_status":%s,"retry_at_ms":%s}\n' "$ef_run" "$ef_event_seq" "$ef_instance" "$ef_machine" "$(date +%s)" "$1" "$2" "${3:-0}" "$ef_retry_at"
}
sample() {
  ef_now=$(date +%s)
  read -r ef_next_rx < /sys/class/net/eth0/statistics/rx_bytes || { ef_window_valid=0; event observer_error counter_unavailable; return; }
  read -r ef_next_tx < /sys/class/net/eth0/statistics/tx_bytes || { ef_window_valid=0; event observer_error counter_unavailable; return; }
  ef_seq=$((ef_seq+1)); ef_dr=$((ef_next_rx-ef_rx)); ef_dt=$((ef_next_tx-ef_tx)); ef_valid=1
  if [ "$ef_seq" -eq 0 ]; then ef_dr=0; ef_dt=0; fi
  if [ "$ef_dr" -lt 0 ] || [ "$ef_dt" -lt 0 ] || [ "$ef_now" -lt "$ef_last" ]; then ef_valid=0; ef_window_valid=0; ef_dr=0; ef_dt=0; fi
  ef_total_rx=$((ef_total_rx+ef_dr)); ef_total_tx=$((ef_total_tx+ef_dt))
  ef_observed_activity=$((ef_total_rx+ef_total_tx-ef_window_bytes))
  ef_observing=0; [ "$ef_window_start" -eq 0 ] || ef_observing=1
  ef_activity_elapsed=0
  [ "$ef_window_start" -eq 0 ] || ef_activity_elapsed=$(( $(monotonic)-ef_window_start ))
  printf '{"kind":"earnfm_sample","revision":2,"instance":"%s","machine":"%s","run":"%s","seq":%s,"start_ms":%s000,"end_ms":%s000,"rx":%s,"tx":%s,"total_rx":%s,"total_tx":%s,"state":"%s","valid":%s,"final":%s,"clock_resolution_ms":1000,"ip":"%s","country":"%s","control_sockets":%s,"client_generation":%s,"error":"%s","retry_at_ms":%s,"activity_observing":%s,"activity_window_ms":%s000,"activity_min_bytes":%s,"activity_bytes":%s,"activity_elapsed_ms":%s,"activity_due_ms":%s}\n' "$ef_instance" "$ef_machine" "$ef_run" "$ef_seq" "$ef_last" "$ef_now" "$ef_dr" "$ef_dt" "$ef_total_rx" "$ef_total_tx" "$ef_state" "$ef_valid" "$1" "$ef_ip" "$ef_country" "$ef_control" "$ef_generation" "$ef_error" "$ef_retry_at" "$ef_observing" "$ef_activity_seconds" "$ef_min_bytes" "$ef_observed_activity" "$((ef_activity_elapsed*1000))" "$ef_activity_due"
  ef_rx=$ef_next_rx; ef_tx=$ef_next_tx; ef_last=$ef_now
}
stop_client() {
  if [ -n "$ef_child" ]; then
    kill "$ef_child" 2>/dev/null || true
    sleep 1
    kill -KILL "$ef_child" 2>/dev/null || true
    wait "$ef_child" 2>/dev/null || true
    ef_child=''
  fi
  ef_control=0
}
shutdown() {
  trap '' TERM INT
  ef_state=${1:-stopping}
  stop_client
  sample 1
  rm -rf "$ef_dir"
}
trap 'shutdown; exit 0' TERM INT
reallocate() {
  ef_state=reallocating; ef_error=$1; ef_retry_at=0
  stop_client; sample 0; event reallocate_requested "$1"
  for ef_attempt in 1 2 3; do
    ef_status=0
    if timeout 12 wget -S -q -T 10 -O /dev/null --header 'Metadata: true' --header 'Content-Type: application/json' --post-data "{\"reason\":\"EarnFM $1\"}" http://169.254.169.254/v1/reallocate 2>"$ef_dir/imds"; then
      ef_status=$(sed -n 's/.*HTTP\/[0-9.]* \([0-9][0-9][0-9]\).*/\1/p' "$ef_dir/imds" | tail -n 1)
      event reallocate_accepted "$1" "${ef_status:-200}"
      shutdown reallocating; exit 75
    fi
    ef_status=$(sed -n 's/.*HTTP\/[0-9.]* \([0-9][0-9][0-9]\).*/\1/p' "$ef_dir/imds" | tail -n 1)
    event reallocate_failed "$1" "${ef_status:-0}"
    sleep 5
  done
  shutdown reallocating; exit 75
}
control_sockets() {
  [ -n "$ef_child" ] && [ -r "/proc/$ef_child/net/tcp" ] || { printf '%s\n' -1; return; }
  ef_inodes=''
  for ef_fd in /proc/"$ef_child"/fd/*; do
    ef_link=$(readlink "$ef_fd" 2>/dev/null) || continue
    case "$ef_link" in socket:\[*\]) ef_link=${ef_link#socket:[}; ef_link=${ef_link%]}; ef_inodes="$ef_inodes $ef_link" ;; esac
  done
  set -- "/proc/$ef_child/net/tcp"
  [ ! -r "/proc/$ef_child/net/tcp6" ] || set -- "$@" "/proc/$ef_child/net/tcp6"
  ef_socket_count=$(awk -v ids="$ef_inodes" 'BEGIN{split(ids,a," ");for(i in a)own[a[i]]=1;n=0} $4=="01"&&substr($3,length($3)-3)=="20FB"&&($10 in own){n++} END{print n}' "$@" 2>/dev/null) || { printf '%s\n' -1; return; }
  printf '%s\n' "$ef_socket_count"
}
pause_client() {
  ef_until=$1; ef_state=${3:-rate_limited}; ef_error=${2:-rate_limited}; ef_retry_at=$((ef_until*1000))
  stop_client; ef_activity_due=0; event cooldown_started "$ef_error"
  while [ "$(date +%s)" -lt "$ef_until" ]; do sample 0; sleep 10 & wait $!; done
  ef_retry_at=0; event cooldown_finished "$ef_error"
}
sample 0
for ef_hold in ${EARNFM_COOLDOWNS:-}; do
  [ "${ef_hold%:*}" = "$ef_machine" ] || continue
  ef_until=${ef_hold##*:}; case "$ef_until" in *[!0-9]*|'') continue ;; esac
  [ "$ef_until" -le "$(date +%s)" ] || pause_client "$ef_until"
done
ef_info=$(timeout 15 wget -q -T 10 -O - https://ipinfo.io/json 2>/dev/null) || ef_info=''
ef_ip=$(printf '%s' "$ef_info" | sed -n 's/.*"ip"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
ef_country_a=$(printf '%s' "$ef_info" | sed -n 's/.*"country"[[:space:]]*:[[:space:]]*"\([A-Z][A-Z]\)".*/\1/p')
case "$ef_ip" in *[!0-9a-fA-F:.]*|'') ef_ip='' ;; *)
  ef_info=$(timeout 15 wget -q -T 10 -O - "https://api.db-ip.com/v2/free/$ef_ip" 2>/dev/null) || ef_info=''
  ef_country_b=$(printf '%s' "$ef_info" | sed -n 's/.*"countryCode"[[:space:]]*:[[:space:]]*"\([A-Z][A-Z]\)".*/\1/p')
  if [ -n "$ef_country_a" ] && [ "$ef_country_a" = "$ef_country_b" ]; then ef_country=$ef_country_a; fi
;; esac
event location_checked "${ef_country:-unknown}"
[ -z "$ef_country" ] || [ "$ef_country" = "$ef_expected_country" ] || reallocate foreign_egress
while :; do
  # Each generation gets its own pipe; a prior process cannot leave a queued rejection for its successor.
  exec 3>&-
  rm "$ef_dir/log"
  mkfifo "$ef_dir/log"
  exec 3<>"$ef_dir/log"
  ef_generation=$((ef_generation+1)); ef_state=starting; ef_error=none
  ef_failure_since=0; ef_failure_last=0; ef_reason=''
  ef_window_start=0; ef_activity_due=0; sample 0
  ef_started_mono=$(monotonic); ef_disconnected_since=$ef_started_mono
  ef_window_start=0; ef_ready_since=0; ef_window_valid=1; ef_window_bytes=$((ef_total_rx+ef_total_tx))
  ef_last_sample=$ef_started_mono; ef_retry_at=0; ef_control=-1
  ef_last_control=$((ef_started_mono-5)); ef_activity_due=0
  /app/main > "$ef_dir/log" 2>&1 & ef_child=$!
  event client_started none
  while :; do
    if IFS= read -r -t 1 ef_line <&3; then
      ef_clean=$(printf '%s\n' "$ef_line" | awk '{s=$0;k=ENVIRON["EARNFM_TOKEN"];while((p=index(s,k))>0){printf "%s[redacted]",substr(s,1,p-1);s=substr(s,p+length(k))}print s}')
      printf 'EF_LOG instance=%s machine=%s %s\n' "$ef_instance" "$ef_machine" "$ef_clean"
      case "$ef_line" in
        *'WebSocket dial '*'HTTP 429'*) ef_reason=rate_limited; break ;;
        *'WebSocket handshake rejected by '*'HTTP 401'*) ef_reason=authorization_error; break ;;
        *'WebSocket handshake rejected by '*'HTTP 403'*) ef_reason=provider_rejected; break ;;
        *'IP change detected with different location'*) ef_reason=ip_change_cooldown; break ;;
        *'WebSocket DNS lookup failed '*) ef_error=dns_failure ;;
        *'WebSocket dial '*'failed:'*|*'All '*'IP(s) for '*' exhausted'*|*'Primary connection failed: WebSocket connection error:'*) ef_error=connection_failure ;;
        *) ef_error=none ;;
      esac
      if [ "$ef_error" != none ]; then
        ef_now_mono=$(monotonic)
        [ "$ef_failure_since" -ne 0 ] && [ $((ef_now_mono-ef_failure_last)) -le 60 ] || ef_failure_since=$ef_now_mono
        ef_failure_last=$ef_now_mono
        event native_error "$ef_error"
      fi
    elif ! kill -0 "$ef_child" 2>/dev/null; then ef_reason=client_exited; break; fi
    ef_now_mono=$(monotonic)
    if [ $((ef_now_mono-ef_last_control)) -ge 5 ]; then ef_control=$(control_sockets); ef_last_control=$ef_now_mono; fi
    if [ "$ef_control" -gt 0 ]; then
      [ "$ef_ready_since" -ne 0 ] || ef_ready_since=$ef_now_mono
      ef_disconnected_since=0; ef_failure_since=0; ef_failure_last=0; ef_state=running; ef_error=none
    elif [ "$ef_control" -eq 0 ]; then
      [ "$ef_window_start" -gt 0 ] || ef_ready_since=0
      [ "$ef_disconnected_since" -ne 0 ] || ef_disconnected_since=$ef_now_mono
      ef_state=connecting
      if [ $((ef_now_mono-ef_disconnected_since)) -ge 120 ]; then ef_reason=control_offline; break; fi
      if [ "$ef_failure_since" -gt 0 ] && [ $((ef_now_mono-ef_failure_last)) -le 60 ]; then
        ef_state=connection_error
        if [ $((ef_failure_last-ef_failure_since)) -ge 30 ]; then ef_reason=connection_failure; break; fi
      fi
    else ef_state=observer_unknown; fi
    if [ $((ef_now_mono-ef_last_sample)) -ge 10 ]; then sample 0; ef_last_sample=$ef_now_mono; fi
    if [ "$ef_window_start" -eq 0 ] && [ "$ef_control" -gt 0 ] && [ $((ef_now_mono-ef_ready_since)) -ge 60 ]; then
      ef_window_valid=1; sample 0
      if [ "$ef_window_valid" -eq 1 ]; then
        ef_window_start=$ef_now_mono; ef_window_bytes=$((ef_total_rx+ef_total_tx))
        ef_activity_due=$(( ($(date +%s)+ef_activity_seconds)*1000 ))
        event activity_observation_started none
      fi
    fi
    if [ "$ef_window_start" -gt 0 ] && [ $((ef_now_mono-ef_window_start)) -ge "$ef_activity_seconds" ]; then
      sample 0
      ef_activity=$((ef_total_rx+ef_total_tx-ef_window_bytes))
      ef_auth_delay=900; ef_window_valid=1; ef_window_start=$ef_now_mono; ef_window_bytes=$((ef_total_rx+ef_total_tx)); ef_activity_due=$(( ($(date +%s)+ef_activity_seconds)*1000 ))
    fi
  done
  stop_client
  if [ "$ef_reason" = rate_limited ]; then pause_client $(( $(date +%s)+86400 )); continue; fi
  if [ "$ef_reason" = ip_change_cooldown ]; then pause_client $(( $(date +%s)+129600 )) ip_change_cooldown; continue; fi
  if [ "$ef_reason" = authorization_error ] || [ "$ef_reason" = provider_rejected ]; then
    pause_client $(( $(date +%s)+ef_auth_delay )) "$ef_reason" "$ef_reason"
    ef_auth_delay=$((ef_auth_delay*2)); [ "$ef_auth_delay" -le 3600 ] || ef_auth_delay=3600
    continue
  fi
  reallocate "$ef_reason"
done
