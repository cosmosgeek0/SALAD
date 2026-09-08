import concurrent.futures
from email.utils import parsedate_to_datetime
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time
import uuid

SAMPLE_SECONDS = 10
CONNECTION_SECONDS = 120
PROVIDER_SECONDS = 60
IDLE_SECONDS = 1800
HEALTH_SECONDS = 30
HEALTH_FILE = Path("/tmp/pawns-health")
COUNTERS = Path("/sys/class/net/eth0/statistics")


def api(path, token=None, payload=None):
    config = 'header = "Content-Type: application/json"\nheader = "X-Locale: EN"\nheader = "X-App-Version: 2.0.0"\nheader = "X-App-OS: Windows"\n'
    if token:
        config += "header = " + json.dumps("Authorization: Bearer " + token) + "\n"
    if payload is not None:
        config += "data-binary = " + json.dumps(json.dumps(payload)) + "\n"
    response = subprocess.run(["curl", "-sS", "--max-time", "10", "--dump-header", "/dev/stderr",
        "--config", "-", "--write-out", "\n%{http_code}", "https://api.pawns.app/api/v1/" + path],
        input=config, text=True, capture_output=True, timeout=12)
    raw, _, code = response.stdout.rpartition("\n")
    status = int(code) if code.isdigit() and not response.returncode else 0
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    retry = PROVIDER_SECONDS
    match = re.search(r"(?im)^retry-after:\s*([^\r\n]+)", response.stderr)
    if match:
        try:
            value = match[1].strip()
            retry = max(retry, int(value) if value.isdigit() else parsedate_to_datetime(value).timestamp() - time.time())
        except (ValueError, TypeError, OverflowError):
            pass
    return status, data, retry


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else None


def api_error(label, status):
    return label + (" returned invalid data" if status == 200 else " request failed without an HTTP response" if not status else " HTTP " + str(status))


def read_provider(token, account):
    result = {"account_id": account, "balance_ms": None, "device_ms": None, "active": None,
              "sold_gb": None, "sharing_usd": None, "balance_usd": None,
              "ip": None, "country": None, "error": None, "retry_seconds": PROVIDER_SECONDS}
    began = time.monotonic()
    try:
        location = subprocess.run(["curl", "-fsS", "--max-time", "8", "https://ipinfo.io/json"],
                                  text=True, capture_output=True, timeout=10)
        geo = json.loads(location.stdout)
        result["ip"] = str(ipaddress.ip_address(geo["ip"]))
        result["country"] = geo.get("country")
        if account is None:
            status, user, delay = api("users/me", token)
            result["retry_seconds"] = max(result["retry_seconds"], delay)
            if status != 200 or not isinstance(user, dict) or not user.get("id"):
                result.update(error=api_error("Pawns account lookup", status), http=status)
                return result
            result["account_id"] = user["id"]
        status, balance, delay = api("users/me/balance", token)
        result["retry_seconds"] = max(result["retry_seconds"], delay)
        if status == 200 and isinstance(balance, dict):
            result.update(balance_ms=int(time.time() * 1000), sold_gb=number(balance.get("traffic_sold")),
                          sharing_usd=number((balance.get("money_details") or {}).get("shared")),
                          balance_usd=number(balance.get("balance_current")))
        else:
            result.update(error=api_error("Pawns balance", status), http=status)
        page, devices = 1, []
        while True:
            if time.monotonic() - began >= 30:
                result["error"] = "Pawns device scan exceeded its time limit"
                return result
            status, data, delay = api("users/me/devices?page=" + str(page) + "&items_per_page=5", token)
            result["retry_seconds"] = max(result["retry_seconds"], delay)
            if status != 200 or not isinstance(data, dict) or not isinstance(data.get("data"), list):
                result.update(error=api_error("Pawns device lookup", status), http=status)
                return result
            if not all(isinstance(d, dict) for d in data["data"]):
                result["error"] = "Pawns device response is invalid"
                return result
            devices.extend(data["data"])
            meta = data.get("meta", {})
            if meta.get("current_page") != page or not isinstance(meta.get("last_page"), int):
                result["error"] = "Pawns device pagination is invalid"
                return result
            if page >= meta["last_page"]:
                break
            page += 1
        matches = [d for d in devices if d.get("last_peer_ip") == result["ip"]]
        if any(not isinstance(d.get("active"), bool) for d in matches):
            result["error"] = "Pawns device status is invalid"
            return result
        result.update(device_ms=int(time.time() * 1000), active=any(d["active"] for d in matches),
                      device_ids=[d.get("id") for d in matches],
                      device_last_active_at=[d.get("last_active_at") for d in matches],
                      active_devices=sum(d["active"] for d in devices) if all(isinstance(d.get("active"), bool) for d in devices) else None)
    except (ValueError, KeyError, TypeError, AttributeError, OSError, subprocess.TimeoutExpired) as exc:
        result["error"] = "Pawns provider check failed: " + type(exc).__name__
    return result


def healthy():
    try:
        return 0 <= time.time() - HEALTH_FILE.stat().st_mtime <= HEALTH_SECONDS
    except OSError:
        return False


def main():
    email = os.environ.pop("PAWNS_EMAIL")
    password = os.environ.pop("PAWNS_PASSWORD")
    identity = {"group_id": os.environ.get("SALAD_CONTAINER_GROUP_ID"),
                "instance": os.environ.get("SALAD_INSTANCE_ID") or str(uuid.uuid4()),
                "machine": os.environ.get("SALAD_MACHINE_ID"), "observer": int(time.time() * 1000)}
    secrets = [email, password]
    state = {"state": "starting", "error": None, "sdk_at": None}
    location = {"ip": None, "country": None}
    baseline = previous = [int((COUNTERS / name).read_text()) for name in ("rx_bytes", "tx_bytes")]
    start_ms = identity["observer"]
    sequence = event_sequence = 0
    final_sent = False
    deadline = None
    stopping = False
    child = None

    def clean_text(value):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[redacted]").replace(json.dumps(secret)[1:-1], "[redacted]")
        return value

    def emit(kind, values):
        nonlocal event_sequence
        row = dict(identity, **values)
        if kind != "SAMPLE":
            row.update(seq=event_sequence, time_ms=int(time.time() * 1000))
            event_sequence += 1
        line = "PAWNS_" + kind + " " + json.dumps(row, separators=(",", ":"), allow_nan=False)
        print(line, flush=True)

    def sample(final=False, boundary=False):
        nonlocal sequence, previous, baseline, start_ms, final_sent
        end_ms = int(time.time() * 1000)
        current = [int((COUNTERS / name).read_text()) for name in ("rx_bytes", "tx_bytes")]
        if any(a < b for a, b in zip(current, previous)):
            baseline = current
            boundary = True
        valid = sequence > 0 and end_ms > start_ms and not boundary and all(a >= b for a, b in zip(current, previous))
        emit("SAMPLE", dict(state, **location, seq=sequence, start_ms=start_ms, end_ms=end_ms,
             rx=current[0] - previous[0] if valid else None, tx=current[1] - previous[1] if valid else None,
             total_rx=current[0] - baseline[0], total_tx=current[1] - baseline[1], final=final,
             valid=valid, bucket_ms=None, deadline_ms=int(time.time() * 1000 + max(0, deadline - time.monotonic()) * 1000) if deadline is not None else None))
        sequence += 1
        final_sent = final_sent or final
        previous, start_ms = current, end_ms

    def shutdown(*_):
        nonlocal stopping
        stopping = True

    def pause(seconds):
        end = time.monotonic() + seconds
        next_sample = time.monotonic()
        while not stopping and time.monotonic() < end:
            HEALTH_FILE.touch()
            if time.monotonic() >= next_sample:
                sample()
                next_sample = time.monotonic() + SAMPLE_SECONDS
            time.sleep(min(1, max(0, end - time.monotonic())))

    def stop_child():
        if child is None or child.poll() is not None:
            return
        try:
            child.stdin.write(b"stop\n")
            child.stdin.flush()
            child.wait(timeout=5)
        except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait(timeout=5)

    def recover(reason, action="reallocate"):
        nonlocal deadline
        state.update(state="reallocating" if action == "reallocate" else "restarting", error=reason)
        deadline = None
        sample()
        emit("RECOVERY", {"action": action, "phase": "requested", "reason": reason,
                          "client_exit_code": child.poll() if child is not None else None})
        stop_child()
        accepted = False
        if action == "reallocate":
            for attempt in range(1, 4):
                if stopping:
                    break
                HEALTH_FILE.touch()
                try:
                    result = subprocess.run(["curl", "--noproxy", "*", "-sS", "--max-time", "10", "-o", "/dev/null",
                        "--write-out", "%{http_code}", "-H", "Metadata: true", "-H", "Content-Type: application/json",
                        "--data", json.dumps({"reason": "Pawns: " + reason}), "http://169.254.169.254/v1/reallocate"],
                        text=True, capture_output=True, timeout=12)
                    code = int(result.stdout) if result.stdout.isdigit() else 0
                    accepted = not result.returncode and code in (200, 204)
                except (OSError, subprocess.TimeoutExpired):
                    code, accepted = 0, False
                emit("RECOVERY", {"action": action, "phase": "accepted" if accepted else "failed",
                     "reason": reason, "attempt": attempt, "http": code})
                if accepted:
                    break
                if attempt < 3:
                    pause(15)
        elif not stopping:
            emit("RECOVERY", {"action": action, "phase": "container_exit", "reason": reason})
        if stopping and not accepted:
            state.update(state="stopped", error=None)
            emit("RECOVERY", {"action": action, "phase": "interrupted", "reason": reason})
            sample(final=True)
            return 0
        sample(final=True)
        return 75

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    HEALTH_FILE.touch()
    sample()
    token = None
    for attempt in range(3):
        try:
            status, data, delay = api("users/tokens", payload={"email": email, "password": password, "identifier": identity["instance"]})
        except (OSError, subprocess.TimeoutExpired):
            status, data, delay = 0, None, PROVIDER_SECONDS
        if status == 200 and isinstance(data, dict) and isinstance(data.get("access_token"), str) and data["access_token"]:
            token = data["access_token"]
            secrets.append(token)
            break
        state.update(state="authorization_error" if status in (401, 403, 422) else "login_error",
                     error=api_error("Pawns login", status))
        sample()
        pause(delay)
        if stopping or status in (401, 403, 422):
            break
    if not token or stopping:
        sample(final=True)
        return 0 if stopping else 78
    emit("LOGIN", {"state": "authenticated"})
    os.environ.update(PAWNS_ACCESS_TOKEN=token, PAWNS_DEVICE_ID=identity["instance"])
    os.environ["XDG_RUNTIME_DIR"] = "/tmp/pawns-runtime"
    Path(os.environ["XDG_RUNTIME_DIR"]).mkdir(mode=0o700, exist_ok=True)
    state.update(state="starting", error=None)
    deadline = time.monotonic() + CONNECTION_SECONDS
    child = subprocess.Popen(["/usr/lib/wine/wine64", "Z:\\app\\runner.exe"], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, start_new_session=True)
    selector = selectors.DefaultSelector()
    selector.register(child.stdout, selectors.EVENT_READ)
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    provider_job = None
    provider_due = next_sample = time.monotonic()
    provider_inactive_since = None
    provider_inactive_scope = None
    provider_account = None
    progress = None
    buffer = b""
    try:
        while not stopping:
            HEALTH_FILE.touch()
            now = time.monotonic()
            if child.poll() is not None:
                return recover("client_exited")
            try:
                process_status = Path("/proc") / str(child.pid) / "status"
                if "\nState:\tT" in process_status.read_text():
                    return recover("client_suspended")
            except FileNotFoundError:
                continue
            if provider_job is None and now >= provider_due:
                provider_job = pool.submit(read_provider, token, provider_account)
            if provider_job is not None and provider_job.done():
                provider = provider_job.result()
                provider_job = None
                provider_due = now + provider["retry_seconds"]
                provider_account = provider.get("account_id") or provider_account
                if provider.get("ip") and provider["ip"] != location["ip"]:
                    sample(boundary=location["ip"] is not None)
                location.update(ip=provider.get("ip"), country=provider.get("country"))
                eligible = (state["state"] == "running" and provider.get("active") is True
                            and provider.get("active_devices") == 1 and provider.get("sold_gb") is not None
                            and provider.get("balance_ms") is not None)
                if eligible:
                    scope = (provider_account, provider["ip"])
                    if progress is None or progress["scope"] != scope or progress["sold_gb"] != provider["sold_gb"]:
                        progress = {"scope": scope, "sold_gb": provider["sold_gb"], "since": now,
                                    "started_ms": int(time.time() * 1000), "observations": 0}
                    progress["observations"] += 1
                    provider.update(idle_state="idle" if now - progress["since"] >= IDLE_SECONDS else "observing", idle_started_ms=progress["started_ms"],
                                    idle_elapsed_ms=int((now - progress["since"]) * 1000),
                                    idle_window_ms=IDLE_SECONDS * 1000, idle_observations=progress["observations"])
                else:
                    progress = None
                    provider.update(idle_state="multiple_active_devices" if (provider.get("active_devices") or 0) > 1 else "waiting_for_fresh_single_ip_evidence",
                                    idle_window_ms=IDLE_SECONDS * 1000)
                emit("PROVIDER", provider)
                if provider.get("http") == 401:
                    return recover("session_expired", "restart")
                scope = (provider_account, provider.get("ip"))
                if provider.get("active") is False and all(scope) and provider.get("device_ms"):
                    if provider_inactive_since is None or provider_inactive_scope != scope:
                        provider_inactive_since = now
                    provider_inactive_scope = scope
                    if now - provider_inactive_since >= CONNECTION_SECONDS:
                        return recover("provider_ip_offline")
                else:
                    provider_inactive_since = None
                    provider_inactive_scope = None
            if deadline is not None and now >= deadline:
                return recover("startup_timeout" if state["state"] == "starting" else state["error"] or "connection_timeout")
            if now >= next_sample:
                sample()
                next_sample = now + SAMPLE_SECONDS
            for _key, _mask in selector.select(timeout=0.5):
                chunk = os.read(child.stdout.fileno(), 65536)
                if not chunk:
                    return recover("client_output_closed")
                buffer += chunk
                while b"\n" in buffer:
                    raw, buffer = buffer.split(b"\n", 1)
                    line = raw.decode(errors="replace")
                    if not line.startswith("PAWNS_SDK "):
                        print(clean_text(line), flush=True)
                        continue
                    try:
                        event = json.loads(line.removeprefix("PAWNS_SDK "))
                        if not isinstance(event, dict):
                            raise ValueError("Invalid SDK event")
                    except ValueError:
                        print("PAWNS_SDK invalid JSON event", flush=True)
                        state.update(state="not_running", error="invalid_sdk_event")
                        if deadline is None:
                            deadline = now + CONNECTION_SECONDS
                        continue
                    name = event.get("name")
                    if name not in ("starting", "running", "not_running"):
                        continue
                    error = (event.get("parameters") or {}).get("error")
                    error = str(error) if error is not None else None
                    safe_error = clean_text(error) if error else None
                    sdk_at = event.get("happened_at")
                    if not isinstance(sdk_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", sdk_at):
                        sdk_at = None
                    print("PAWNS_SDK " + json.dumps({"name": name, "happened_at": sdk_at, "parameters": {"error": safe_error} if error else {}}), flush=True)
                    state.update(state=name, error=safe_error, sdk_at=sdk_at)
                    if (name == "running" and not error) or error in ("ip_used", "non_residential_ip", "unauthorized", "unsupported_version"):
                        deadline = None
                    elif deadline is None:
                        deadline = now + CONNECTION_SECONDS
                    sample()
                    if error in ("ip_used", "non_residential_ip"):
                        return recover(error)
                    if error == "unauthorized":
                        return recover("session_expired", "restart")
                    if error == "unsupported_version":
                        stop_child()
                        pause(PROVIDER_SECONDS)
                        sample(final=True)
                        return 78
    finally:
        stop_child()
        if not final_sent:
            state.update(state="stopped" if stopping else "exited", error=None if stopping else "supervisor_error")
            sample(final=True)
        selector.close()
        pool.shutdown(wait=False, cancel_futures=True)
    return 0


if __name__ == "__main__":
    sys.exit(0 if healthy() else 1) if sys.argv[1:] == ["--healthcheck"] else sys.exit(main())
