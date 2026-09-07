#!/usr/bin/env python3
"""Deploy and observe PR: one Salad group with ten replicas in SSH1."""
import argparse
import base64
from datetime import datetime, timedelta, timezone
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent
DATA = Path.home() / ".hg1/proxyrack"
HELPER = Path.home() / "Library/Application Support/Salad Bandwidth Dashboard/.runtime/keychain-store"
BASE = "https://api.salad.com/api/public/organizations/ssh1"
GROUPS = "/projects/default/containers"
IMAGE = "docker.io/proxyrack/pop@sha256:7de6719f37b31d5dd354f8cdd3ae601b4ed401832d0935ff460f968e0b6731bc"
sys.path.insert(0, str(ROOT.parent / "salad-bandwidth-stack"))
from dashboard.native_network import NetworkMinutes, parse_minute

STARTUP = r'''#!/bin/bash
set -u
umask 077
: "${PR_NAMESPACE:?}" "${PR_API_KEY:?}" "${SALAD_INSTANCE_ID:?}" "${SALAD_MACHINE_ID:?}"
pr_key=$PR_API_KEY; unset PR_API_KEY
[[ "$pr_key" =~ ^[A-Za-z0-9]+$ ]] || exit 1
UUID=$(printf '%s:%s' "$PR_NAMESPACE" "$SALAD_INSTANCE_ID" | sha256sum | cut -c1-64 | tr a-f A-F)
PR_WORKER="PR-${SALAD_INSTANCE_ID:0:8}"
pr_pid=""; pr_state=starting; pr_error=none; pr_registered=0
record_minute() {
  [[ -n "${pr_started:-}" ]] || return
  local now rx tx state=$pr_state error=$pr_error
  if [[ "$state" == running && "$pr_registered" == 0 ]]; then
    state=starting; error=registration_pending
  fi
  now="$(date +%s)000"
  read -r rx </sys/class/net/eth0/statistics/rx_bytes || return
  read -r tx </sys/class/net/eth0/statistics/tx_bytes || return
  printf 'PR_MINUTE_V1 worker=%s device=%s instance=%s machine=%s observer=%s seq=%s start_ms=%s end_ms=%s rx=%s tx=%s total_rx=%s total_tx=%s state=%s error=%s final=%s registered=%s\n' \
    "$PR_WORKER" "$UUID" "$SALAD_INSTANCE_ID" "$SALAD_MACHINE_ID" "$pr_started" "$pr_seq" "$pr_previous_ms" "$now" \
    "$((rx-pr_previous_rx))" "$((tx-pr_previous_tx))" "$((rx-pr_base_rx))" "$((tx-pr_base_tx))" "$state" "$error" "$1" "$pr_registered"
  pr_previous_rx=$rx; pr_previous_tx=$tx; pr_previous_ms=$now
  pr_seq=$((pr_seq+1)); pr_recorded=$SECONDS
}
stop_client() {
  exec 4>&-
  if [[ -n "$pr_pid" ]]; then
    kill "$pr_pid" 2>/dev/null || true
    sleep 1
    kill -KILL "$pr_pid" 2>/dev/null || true
    wait "$pr_pid" 2>/dev/null || true
  fi
  pr_pid=""
  exec 3<&-
}
reallocate() {
  stop_client
  pr_state=reallocating
  record_minute 1
  printf 'PR_SELF_REALLOCATE worker=%s instance=%s machine=%s reason=%s\n' "$PR_WORKER" "$SALAD_INSTANCE_ID" "$SALAD_MACHINE_ID" "$1"
  for attempt in 1 2 3; do
    code=$(curl --noproxy '*' -sS --connect-timeout 3 --max-time 10 -o /dev/null -w '%{http_code}' -X POST http://169.254.169.254/v1/reallocate -H 'Metadata: true' -H 'Content-Type: application/json' --data "{\"reason\":\"$1\"}") || code=000
    printf 'PR_SELF_IMDS_RESPONSE worker=%s instance=%s http=%s\n' "$PR_WORKER" "$SALAD_INSTANCE_ID" "$code"
    [[ "$code" == 200 || "$code" == 204 ]] && break
    sleep 5
  done
  exit 75
}
register_device() {
  local endpoint body code resolver
  local -a dns_args
  for endpoint in device/add device/status; do
    body="{\"device_id\":\"$UUID\",\"device_name\":\"$PR_WORKER\"}"
    for resolver in default doh; do
      dns_args=()
      [[ "$resolver" == doh ]] && dns_args=(--doh-url https://1.1.1.1/dns-query)
      code=$(printf 'header = "Api-Key: %s"\nheader = "Content-Type: application/json"\nheader = "Accept: application/json"\n' "$pr_key" | curl -sS --config - "${dns_args[@]}" --connect-timeout 5 --max-time 15 -X POST "https://peer.proxyrack.com/api/$endpoint" --data "$body" -o /tmp/pr-registration.json -w '%{http_code}' 2>/tmp/pr-registration.err) || code=000
      if [[ "$resolver" == default && "$code" == 000 ]] && grep -qiE 'Could not resolve host|Resolving timed out' /tmp/pr-registration.err; then
        printf 'PR_DNS_FALLBACK worker=%s instance=%s resolver=https\n' "$PR_WORKER" "$SALAD_INSTANCE_ID"
        continue
      fi
      cat /tmp/pr-registration.err >&2
      break
    done
    if [[ "$code" == 200 ]] && node -e 'const r=require("/tmp/pr-registration.json");process.exit(r.status==="success"&&r.data&&r.data.device_id===process.argv[1]?0:1)' "$UUID" 2>/dev/null; then
      pr_registered=1
      printf 'PR_REGISTERED worker=%s device=%s instance=%s\n' "$PR_WORKER" "$UUID" "$SALAD_INSTANCE_ID"
      rm -f /tmp/pr-registration.json /tmp/pr-registration.err
      pr_key=""
      return
    fi
    printf 'PR_REGISTRATION_RETRY worker=%s endpoint=%s http=%s\n' "$PR_WORKER" "$endpoint" "$code"
    [[ "$endpoint" == device/add && "$code" == 400 ]] && node -e 'const r=require("/tmp/pr-registration.json");process.exit(JSON.stringify(r).includes("already been taken")?0:1)' 2>/dev/null || break
  done
  rm -f /tmp/pr-registration.json /tmp/pr-registration.err
}
trap 'pr_state=exited; pr_error=operator_stop; stop_client; record_minute 1; exit 0' TERM INT
if ! curl -fsS --retry 2 --retry-delay 3 --connect-timeout 8 --max-time 45 https://app-updates.sock.sh/peerclient/go/client -o /app/pr-client; then
  pr_error=download_failed; reallocate 'PR native client download failed after retries'
fi
version=$(curl -fsS --retry 2 --retry-delay 3 --connect-timeout 8 --max-time 20 https://app-updates.sock.sh/peerclient/go/version.txt) || reallocate 'PR version download failed after retries'
[[ "$version" =~ ^[0-9]+$ ]] || reallocate 'PR returned an invalid client version'
chmod 700 /app/pr-client
pr_started="$(date +%s)000"
read -r pr_base_rx </sys/class/net/eth0/statistics/rx_bytes
read -r pr_base_tx </sys/class/net/eth0/statistics/tx_bytes
pr_previous_rx=$pr_base_rx; pr_previous_tx=$pr_base_tx; pr_previous_ms=$pr_started; pr_seq=0; pr_recorded=$SECONDS
record_minute 0
start_client() {
  rm -f /tmp/pr-input; mkfifo /tmp/pr-input
  exec 3< <(exec /app/pr-client --homeIp point-of-presence.sock.sh --homePort 443 --id "$UUID" --version "$version" --clientKey proxyrack-pop-client --clientType PoP --ppid $$ --osType Linux --osRelease "$(uname -r)" --osArch x64 </tmp/pr-input 2>&1)
  pr_pid=$!; exec 4>/tmp/pr-input
  pr_state=starting; pr_connect_since=$SECONDS
  printf 'PR_SELF_START worker=%s device=%s instance=%s machine=%s client_version=%s native=1\n' "$PR_WORKER" "$UUID" "$SALAD_INSTANCE_ID" "$SALAD_MACHINE_ID" "$version"
}
pr_register_delay=60; pr_register_at=$((SECONDS+60+RANDOM%120))
start_client
while :; do
  if IFS= read -r -t 1 line <&3; then
    printf 'PR_LOG worker=%s instance=%s %s\n' "$PR_WORKER" "$SALAD_INSTANCE_ID" "$line"
    case "$line" in
      *'connected to home:'*) pr_state=running; pr_error=none; pr_connect_since=-1 ;;
      *'connecting to home:'*)
        pr_state=starting; pr_error=connecting
        if (( pr_connect_since < 0 )); then pr_connect_since=$SECONDS; fi ;;
    esac
  elif ! kill -0 "$pr_pid" 2>/dev/null; then
    pr_state=exited; pr_error=client_exited
    reallocate 'Proxyrack native client exited'
  fi
  if (( pr_registered == 0 && SECONDS >= pr_register_at )); then
    register_device
    pr_register_at=$((SECONDS+pr_register_delay+RANDOM%90))
    (( pr_register_delay < 600 )) && pr_register_delay=$((pr_register_delay*2))
    (( pr_register_delay > 600 )) && pr_register_delay=600
  fi
  if (( SECONDS-pr_recorded >= 60 )); then record_minute 0; fi
  if (( pr_connect_since >= 0 && SECONDS-pr_connect_since >= 60 )); then
    pr_state=error; pr_error=connection_timeout; reallocate 'Proxyrack home connection unavailable for 60 seconds'
  fi
done
'''


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2))
    os.replace(temp, path)


def salad_api():
    key = subprocess.check_output([str(HELPER), "--read", "--service", "salad-bandwidth-api",
                                   "--account", getpass.getuser()], text=True).strip()

    def request(path, method="GET", body=None):
        if not (path == GROUPS or path.startswith(GROUPS + "/") or path == "/log-entries"):
            raise ValueError("Outside the requested SSH1 deployment")
        media = "application/merge-patch+json" if method == "PATCH" else "application/json"
        config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\nheader = " + json.dumps("Content-Type: " + media) + "\n"
        if body is not None:
            config += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
        result = subprocess.run(["curl", "-sS", "--max-time", "25", "--config", "-", "--request", method,
                                 "--write-out", "\n%{http_code}", BASE + path], input=config, text=True,
                                capture_output=True, timeout=30)
        raw, code = result.stdout.rsplit("\n", 1)
        if result.returncode or not 200 <= int(code) < 300:
            raise RuntimeError("Salad " + method + " " + path + " returned HTTP " + code)
        return json.loads(raw) if raw.strip() else {}
    return request


def peer_api():
    key = subprocess.check_output([str(HELPER), "--read", "--service", "proxyrack-peer-api",
                                   "--account", getpass.getuser()], text=True, stderr=subprocess.DEVNULL).strip()

    def request(method, payload=None):
        if method not in ("balance", "bandwidth", "device/status"):
            raise ValueError("Unsupported ProxyRack operation")
        config = "header = " + json.dumps("Api-Key: " + key) + '\nheader = "Content-Type: application/json"\nheader = "Accept: application/json"\n'
        config += "data-binary = " + json.dumps(json.dumps(payload or {})) + "\n"
        result = subprocess.run(["curl", "-sS", "--max-time", "20", "--config", "-", "--request", "POST",
                                 "--write-out", "\n%{http_code}", "https://peer.proxyrack.com/api/" + method],
                                input=config, text=True, capture_output=True, timeout=25)
        raw, code = result.stdout.rsplit("\n", 1)
        if result.returncode or code not in ("200", "400"):
            try:
                detail = str(json.loads(raw).get("error", "")).replace(key, "[redacted]")[:160]
            except (ValueError, AttributeError):
                detail = ""
            raise RuntimeError("ProxyRack " + method + " returned HTTP " + code + (": " + detail if detail else ""))
        try:
            return json.loads(raw)
        except ValueError:
            raise RuntimeError("ProxyRack returned a non-JSON response") from None
    return request


def configuration():
    return json.loads((DATA / "deployment.json").read_text())


def command():
    encoded = base64.b64encode(STARTUP.encode()).decode()
    args = ["/bin/bash", "-c", 'umask 077; printf "%s" "$@" | base64 -d > /tmp/pr-start.sh; exec /bin/bash /tmp/pr-start.sh',
            "pr-start", *[encoded[i:i+900] for i in range(0, len(encoded), 900)]]
    if len(args) > 100 or any(not value or len(value) > 1000 for value in args):
        raise ValueError("Startup command exceeds Salad command limits")
    return args


def deploy():
    api = salad_api()
    config = configuration()
    if "workers" in config:
        old = config
        for worker in old["workers"]:
            group = api(GROUPS + "/" + worker["name"])
            if group["id"] != worker["group_id"] or group["current_state"]["status"] != "stopped":
                raise RuntimeError("Stop the previous deployment before replacing it")
        config = {"organization": "ssh1", "project": "default", "name": "pr", "replicas": 10,
                  "created_at": datetime.now(timezone.utc).isoformat(), "namespace": secrets.token_hex(16),
                  "image": IMAGE, "replaced_groups": old["workers"]}
        save(DATA / "deployment.json", config)
    key = subprocess.check_output([str(HELPER), "--read", "--service", "proxyrack-peer-api",
                                   "--account", getpass.getuser()], text=True).strip()
    existing = {g["name"]: g for g in api(GROUPS).get("items", [])}
    if "pr" in existing:
        group = api(GROUPS + "/pr")
        if group["container"]["environment_variables"].get("PR_NAMESPACE") != config["namespace"]:
            raise RuntimeError("Existing PR group has a different deployment identity")
        if group["container"]["command"] != command():
            raise RuntimeError("Use update to change an existing PR deployment")
    else:
        payload = {"name": "pr", "display_name": "PR", "replicas": 10,
                   "autostart_policy": True, "restart_policy": "always", "country_codes": ["us"],
                   "container": {"image": IMAGE, "priority": "batch", "resources": {"cpu": 1, "memory": 1024},
                                 "command": command(), "environment_variables": {
                                     "PR_NAMESPACE": config["namespace"], "PR_API_KEY": key}}}
        group = api(GROUPS, "POST", payload)
    config["group_id"] = group["id"]
    save(DATA / "deployment.json", config)
    for _ in range(30):
        group = api(GROUPS + "/pr")
        if group["current_state"]["status"] != "preparing":
            break
        time.sleep(2)
    if group["current_state"]["status"] == "stopped":
        api(GROUPS + "/pr/start", "POST")
    elif group["current_state"]["status"] not in ("deploying", "running"):
        raise RuntimeError("PR is not ready to start: " + group["current_state"]["status"])
    print("PR requested: one group, ten replicas, US, 1 CPU / 1 GB each", flush=True)


def inspect():
    api = salad_api()
    config = configuration()
    group = api(GROUPS + "/pr")
    if group["id"] != config["group_id"]:
        raise RuntimeError("Deployment identity changed")
    instances = api(GROUPS + "/pr/instances").get("instances", [])
    print("PR", group["current_state"], [{k:i.get(k) for k in ("id", "machine_id", "state", "ready")} for i in instances])


def update_startup():
    api = salad_api()
    config = configuration()
    group = api(GROUPS + "/pr")
    if group["id"] != config["group_id"]:
        raise RuntimeError("Deployment identity changed")
    if group["container"]["command"] != command():
        api(GROUPS + "/pr", "PATCH", {"container": {"command": command()}})
    after = api(GROUPS + "/pr")
    if after["container"]["command"] != command():
        raise RuntimeError("Startup command was not applied")
    print("PR startup verified", flush=True)


def device_id(config, instance):
    return hashlib.sha256((config["namespace"] + ":" + instance).encode()).hexdigest().upper()


def parsed_time(value):
    value = re.sub(r"\.(\d+)(?=Z$|[+-]\d\d:\d\d$)",
                   lambda m: "." + (m[1] + "000000")[:6], value)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def provider_loop(config, members, meter, stopped):
    path = DATA / "provider.json"
    state = json.loads(path.read_text()) if path.exists() else {}
    if state.get("group_id") != config["group_id"]:
        state = {"group_id": config["group_id"], "workers": {}}
    api = peer_api()
    while not stopped.is_set():
        current = {w["device_id"]: w for w in members.get("workers", [])}
        for instance in meter.latest(config["group_id"]):
            state["workers"].setdefault(device_id(config, instance), {})
        now, jobs = int(time.time() * 1000), []
        for device, row in state["workers"].items():
            live = current.get(device, {})
            connected = live.get("fresh") and live.get("client_state") == "running"
            if connected:
                due = row.get("status_attempted_ms", 0) + (120_000 if row.get("error") else 1_800_000)
                if due <= now:
                    jobs.append((due, "device/status", device))
            interval = 300_000 if device in current else 3_600_000
            due = row.get("bandwidth_attempted_ms", 0) + interval
            if due <= now:
                jobs.append((due, "bandwidth", device))
        due = state.get("balance_attempted_ms", 0) + (120_000 if state.get("balance_error") else 600_000)
        if due <= now:
            jobs.append((due, "balance", ""))
        if not jobs:
            stopped.wait(5)
            continue
        _, method, device = min(jobs)
        row = state if method == "balance" else state["workers"][device]
        kind = "status" if method == "device/status" else method
        row[kind + "_attempted_ms"] = now
        payload = {"device_id": device} if device else {}
        if method == "bandwidth":
            payload.update(date_start=(parsed_time(config["created_at"]).date() - timedelta(days=1)).isoformat(),
                           date_end=datetime.now(timezone.utc).date().isoformat())
        try:
            result = api(method, payload)
            if result.get("status") != "success":
                raise RuntimeError(result.get("error", "PR has not returned this reading"))
            data, checked = result["data"], int(time.time() * 1000)
            if method == "device/status":
                row.update(status=data.get("status", "Not reported"), checked_ms=checked, error=None)
            elif method == "bandwidth":
                days = data.get("bandwidth", {})
                if not isinstance(days, dict) or not all(isinstance(v, (int, float)) and v >= 0 for v in days.values()):
                    raise ValueError("PR returned invalid bandwidth values")
                row.update(credited_mb=sum(days.values()) * 1000, bandwidth_state=data.get("state"),
                           bandwidth_checked_ms=checked, bandwidth_error=None)
            else:
                row.update(balance=data.get("balance"), balance_checked_ms=checked, balance_error=None)
        except Exception as error:
            row["error" if method == "device/status" else kind + "_error"] = str(error)[:200]
        save(path, state)
        # The measured account limit is five requests/minute; leave capacity for replica registration.
        stopped.wait(20)


def make_view(meter, config, inventory, cloud_error=None):
    now = int(time.time() * 1000)
    provider_path = DATA / "provider.json"
    provider = json.loads(provider_path.read_text()) if provider_path.exists() else {}
    if provider.get("group_id") != config["group_id"]:
        provider = {}
    with meter.lock:
        rows = [dict(row) for row in meter.db.execute(
            "SELECT * FROM minutes WHERE group_id=? ORDER BY end_ms,observer,seq", (config["group_id"],))]
    totals, timeline, total = {}, [], 0
    for row in rows:
        if not row["valid"]:
            continue
        run = (row["instance"], row["observer"])
        amount = row["total_rx"] + row["total_tx"]
        previous = totals.get(run, 0)
        if amount < previous:
            continue
        total += amount - previous
        totals[run] = amount
        if timeline and timeline[-1]["time_ms"] == row["end_ms"]:
            timeline[-1]["mb"] = total / 1e6
        else:
            timeline.append({"time_ms": row["end_ms"], "mb": total / 1e6})
    workers = []
    for member in inventory.get("instances", []):
        machine_rows = [r for r in rows if r["machine"] == member["machine_id"] and r["instance"] == member["id"]]
        last = max(machine_rows, key=lambda r:(r["observer"], r["seq"]), default=None)
        instance = member["id"]
        device = device_id(config, instance)
        age = now - last["end_ms"] if last else None
        fresh = bool(not cloud_error and last and last["valid"] and -10_000 <= age <= 150_000 and not last["final"])
        status_fresh = bool(not cloud_error and last and -10_000 <= age <= 150_000)
        seconds = (last["end_ms"] - last["start_ms"]) / 1000 if last else None
        amount = (last["rx"] + last["tx"]) / 1e6 if last and last["valid"] and last["seq"] > 0 else None
        prov = provider.get("workers", {}).get(device, {})
        p_age = now - prov["checked_ms"] if prov.get("checked_ms") else None
        raw_status = prov.get("status", "Waiting for registration")
        online = p_age is not None and p_age < 240_000 and raw_status.startswith("Online") and not prov.get("error")
        if cloud_error:
            state = "Status unavailable"
        elif inventory.get("status") == "stopped":
            state = "Stopped"
        elif member["state"] != "running":
            state = member["state"].capitalize()
        elif status_fresh and last["state"] == "reallocating":
            state = "Reallocating"
        elif fresh:
            state = "Running" if last["state"] == "running" else "Recovering" if last["state"] in ("error", "exited") else "Starting client"
        else:
            state = "Checking client"
        workers.append({"name": "PR-" + instance[:8], "instance": instance, "device_id": device,
            "salad_instance": member["id"], "machine": member["machine_id"], "salad_state": member["state"], "status": state,
            "client_state": last["state"] if status_fresh else None,
            "provider_status": raw_status, "provider_online": bool(online), "provider_age_ms": p_age,
            "provider_error": prov.get("error"), "credited_mb": prov.get("credited_mb"),
            "bandwidth_state": prov.get("bandwidth_error") or prov.get("bandwidth_state"),
            "bandwidth_checked_ms": prov.get("bandwidth_checked_ms"),
            "network_mb": sum(v for k,v in totals.items() if k[0] == instance) / 1e6 if last else None,
            "interval_mb": amount, "interval_seconds": seconds,
            "mb_per_minute": amount * 60 / seconds if amount is not None and seconds else None,
            "sample_age_ms": age, "fresh": fresh, "last_sample_ms": last["end_ms"] if last else None,
            "client_error": last["error"] if last and last["error"] != "none" else None,
            "samples": sum(r["seq"] > 0 for r in machine_rows),
            "group_url": "https://portal.salad.com/organizations/ssh1/projects/default/containers/pr/instances/" + member["id"]})
    credited = [p["credited_mb"] for p in provider.get("workers", {}).values() if p.get("credited_mb") is not None]
    return {"generated_ms": now, "organization": "SSH1", "group": "PR", "requested": config["replicas"],
            "group_id": config["group_id"], "workers": workers,
            "reporting": sum(w["fresh"] for w in workers), "online": sum(w["provider_online"] for w in workers),
            "network_mb": total / 1e6, "credited_mb": sum(credited) if credited else None,
            "credited_devices": sum(w["credited_mb"] is not None for w in workers),
            "balance": provider.get("balance"), "balance_checked_ms": provider.get("balance_checked_ms"),
            "timeline": timeline, "cloud_error": cloud_error, "started_at": config["created_at"]}


def observe():
    config = configuration()
    lock = (DATA / "observer.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    meter = NetworkMinutes(DATA / "traffic.sqlite3")
    api = salad_api()
    stopped, members = threading.Event(), {}
    threading.Thread(target=provider_loop, args=(config, members, meter, stopped), daemon=True).start()
    cursor = parsed_time(config["created_at"])
    state_path = DATA / "cursor.json"
    if state_path.exists():
        saved = json.loads(state_path.read_text())
        if saved.get("group_id") == config["group_id"]:
            cursor = parsed_time(saved["cursor"])
    inventory = {}
    try:
        while True:
            began = time.monotonic()
            error = None
            try:
                group = api(GROUPS + "/pr")
                if group["id"] != config["group_id"]:
                    raise RuntimeError("Deployment identity changed")
                inventory = {"status": group["current_state"]["status"],
                             "instances": api(GROUPS + "/pr/instances").get("instances", [])}
                end, start = datetime.now(timezone.utc), cursor - timedelta(minutes=10)
                for page in range(30):
                    entries = api("/log-entries", "POST", {
                        "query": 'resource.type = "container" and resource.labels.container_group_name = "pr" and text_log startswith "PR_MINUTE_V1"',
                        "start_time": start.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                        "end_time": end.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                        "page_size": 100, "sort_order": "asc"}).get("items", [])
                    records = []
                    for item in entries:
                        line = item.get("text_log", "")
                        try:
                            values = dict(part.split("=", 1) for part in line.split()[1:])
                            if values["device"] != device_id(config, values["instance"]):
                                continue
                            converted = dict(item, text_log=line.replace("PR_MINUTE_V1 ", "PS_MINUTE_V1 ", 1) + " ip=-")
                            record = parse_minute(converted, config["group_id"])
                            if record and record["end_ms"] <= int(time.time() * 1000) + 30_000:
                                record["record_bytes"] = len(line.encode()) + 1
                                records.append(record)
                        except (ValueError, KeyError, TypeError):
                            continue
                    meter.ingest(records)
                    times = [parsed_time(i["time"]) for i in entries if i.get("time")]
                    if times:
                        following = max(times)
                        cursor = max(cursor, following)
                    if len(entries) < 100 or not times:
                        break
                    following = following.replace(microsecond=following.microsecond//1000*1000)
                    if following <= start:
                        raise RuntimeError("PR log pagination made no progress")
                    start = following
                else:
                    raise RuntimeError("PR log backlog is still being collected")
                save(state_path, {"group_id": config["group_id"], "cursor": cursor.isoformat()})
            except Exception as caught:
                error = str(caught)[:200]
            view = make_view(meter, config, inventory, error)
            members["workers"] = view["workers"]
            save(DATA / "view.json", view)
            time.sleep(max(1, 15 - (time.monotonic() - began)))
    finally:
        stopped.set()


def main():
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["deploy", "status", "observe", "update"])
    args = parser.parse_args()
    if args.action == "deploy":
        deploy()
    elif args.action == "status":
        inspect()
    elif args.action == "update":
        update_startup()
    else:
        observe()


if __name__ == "__main__":
    main()
