#!/bin/bash
set -u
ps_client_pid=""
ps_final=0
ps_state=starting
ps_error=none
record_minute() {
  [[ -n "${ps_started_ms:-}" && -n "${ps_sequence+x}" ]] || return
  local ps_now_ms ps_rx ps_tx
  ps_now_ms="$(date +%s)000"
  read -r ps_rx </sys/class/net/eth0/statistics/rx_bytes || return
  read -r ps_tx </sys/class/net/eth0/statistics/tx_bytes || return
  printf 'PS_MINUTE_V2 instance=%s machine=%s observer=%s seq=%s start_ms=%s end_ms=%s rx=%s tx=%s total_rx=%s total_tx=%s ip=%s state=%s error=%s final=%s bucket_ms=%s\n' \
    "${SALAD_INSTANCE_ID:-local}" "${SALAD_MACHINE_ID:-local}" "$ps_started_ms" "$ps_sequence" "$ps_previous_ms" "$ps_now_ms" \
    "$((ps_rx-ps_previous_rx))" "$((ps_tx-ps_previous_tx))" "$((ps_rx-ps_base_rx))" "$((ps_tx-ps_base_tx))" "$ps_ip" "$ps_state" "$ps_error" "$1" "$ps_bucket_ms"
  ps_previous_rx=$ps_rx; ps_previous_tx=$ps_tx; ps_previous_ms=$ps_now_ms
  ps_sequence=$((ps_sequence+1))
  ps_bucket_ms=$((ps_now_ms / 60000 * 60000))
}
stop_client() {
  (( ps_final == 0 )) || return
  ps_final=1
  if [[ -n "$ps_client_pid" ]]; then
    kill "$ps_client_pid" 2>/dev/null || true
    sleep 1
    kill -KILL "$ps_client_pid" 2>/dev/null || true
    wait "$ps_client_pid" 2>/dev/null || true
  fi
  record_minute 1
}
trap 'stop_client; exit 0' TERM INT
ps_ip=$(/usr/bin/timeout 6 /usr/bin/perl -MIO::Socket::INET -e '
  alarm 5; my $s=IO::Socket::INET->new(PeerAddr=>"api.ipify.org",PeerPort=>80,Proto=>"tcp",Timeout=>3) or exit;
  print $s "GET / HTTP/1.0\r\nHost: api.ipify.org\r\nConnection: close\r\n\r\n";
  local $/; my $r=<$s>; $r=~s/^.*?\r\n\r\n//s; $r=~s/\s+//g;
  print $r if $r=~/^\d{1,3}(?:\.\d{1,3}){3}$/;
' 2>/dev/null) || ps_ip=''
[[ -n "$ps_ip" ]] || ps_ip='-'
ps_started_ms="$(date +%s)000"
read -r ps_base_rx </sys/class/net/eth0/statistics/rx_bytes
read -r ps_base_tx </sys/class/net/eth0/statistics/tx_bytes
ps_previous_rx=$ps_base_rx; ps_previous_tx=$ps_base_tx; ps_previous_ms=$ps_started_ms
ps_sequence=0
ps_bucket_ms=$((ps_started_ms / 60000 * 60000))
record_minute 0
exec 3< <(exec /usr/local/bin/pslauncher 2>&1)
ps_client_pid=$!
ps_error_since=-1
ps_connect_deadline=$((SECONDS+60))
ps_reason=""
printf 'PS_SELF_START instance=%s machine=%s controller=imds\n' "${SALAD_INSTANCE_ID:-local}" "${SALAD_MACHINE_ID:-local}"
while :; do
  if IFS= read -r -t 0.2 ps_line <&3; then
    if [[ "$ps_line" == *'msg="Status:'* ]]; then
      printf 'PS_NATIVE instance=%s %s\n' "${SALAD_INSTANCE_ID:-local}" "$ps_line"
    else
      printf '%s\n' "$ps_line"
    fi
    case "${ps_line,,}" in
      *'msg="status: packetstream is running"'*) ps_error_since=-1; ps_state=running; ps_error=none ;;
      *'error communicating with packetstream server'*)
        ps_state=error; ps_error=communication_error
        if (( ps_error_since < 0 )); then ps_error_since=$SECONDS; fi ;;
      *'1 client per ip address'*) ps_state=error; ps_error=duplicate_ip; ps_reason='PacketStream rejected duplicate public IP'; break ;;
      *'non-residential'*|*'non residential'*) ps_state=error; ps_error=non_residential; ps_reason='PacketStream rejected non-residential IP'; break ;;
      *'msg="status: error'*) ps_state=error; ps_error=client_error; ps_reason='PacketStream reported a client error'; break ;;
    esac
  elif ! kill -0 "$ps_client_pid" 2>/dev/null; then
    ps_state=exited; ps_error=client_exited; ps_reason='PacketStream client exited'; break
  fi
  if (( EPOCHSECONDS * 1000 >= ps_bucket_ms + 60000 )); then record_minute 0; fi
  if [[ "$ps_state" == starting ]] && (( SECONDS >= ps_connect_deadline )); then ps_error=connection_timeout; ps_reason='PacketStream did not connect within 60 seconds'; break; fi
  if (( ps_error_since >= 0 && SECONDS - ps_error_since >= 30 )); then
    ps_reason='PacketStream server communication error persisted for 30 seconds'; break
  fi
done
ps_state=reallocating
stop_client
printf 'PS_SELF_REALLOCATE instance=%s machine=%s reason=%s\n' "${SALAD_INSTANCE_ID:-local}" "${SALAD_MACHINE_ID:-local}" "$ps_reason"
if /usr/bin/timeout 10 /bin/bash -c '
  ps_body="{\"reason\":\"$1\"}"
  exec 4<>/dev/tcp/169.254.169.254/80 || exit 1
  printf "POST /v1/reallocate HTTP/1.1\r\nHost: 169.254.169.254\r\nMetadata: true\r\nContent-Type: application/json\r\nContent-Length: %s\r\nConnection: close\r\n\r\n" "${#ps_body}" >&4
  printf "%s" "$ps_body" >&4
  IFS= read -r ps_response <&4 || exit 1
  printf "PS_SELF_IMDS_RESPONSE %s\n" "$ps_response"
  [[ "$ps_response" =~ ^HTTP/1\.[01][[:space:]]+(200|204)[[:space:]] ]]
' ps-imds "$ps_reason"; then
  printf 'PS_SELF_IMDS_ACCEPTED instance=%s\n' "${SALAD_INSTANCE_ID:-local}"
else
  printf 'PS_SELF_IMDS_FAILED instance=%s fallback=nonzero_exit\n' "${SALAD_INSTANCE_ID:-local}"
fi
# Salad also reallocates failed containers; never leave a failed client burning credits.
exit 75
