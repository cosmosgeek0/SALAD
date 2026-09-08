"""One TraffMonetizer client, measured traffic, and container-local recovery."""
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import time
import urllib.request

TOKEN = os.environ.get("TM_TOKEN", "")
INSTANCE = os.environ.get("SALAD_INSTANCE_ID", "local")
MACHINE = os.environ.get("SALAD_MACHINE_ID", "local")
DEVICE = "ssh4-tm-" + MACHINE
STATUS = re.compile(r"Connected:\s*(?:\[[^\]]*\]\s*-\s*)?(true|false)\s*;\s*Accepting:\s*(true|false)", re.I)
CONNECTION = re.compile(r"^Status:\s*\[[^\]]*\]\s*-\s*(connected|disconnected|connecting)\s*$", re.I)
STATS = re.compile(r"Inbound:\s*(.*?);\s*Outgoing:\s*(.*?);\s*Requests:\s*(\d+)", re.I)
started_ms = int(time.time() * 1000)
process = None
stopping = False


def emit(kind, **fields):
    record = dict(kind=kind, schema_version=2, time_ms=int(time.time() * 1000), instance=INSTANCE,
                  machine=MACHINE, device=DEVICE, observer_start_ms=started_ms, **fields)
    print("TM_V1 " + json.dumps(record, separators=(",", ":")), flush=True)


def terminate(*_):
    global stopping
    stopping = True


def counters():
    return tuple(int(Path("/sys/class/net/eth0/statistics/" + name).read_text())
                 for name in ("rx_bytes", "tx_bytes"))


def stop_client():
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def reallocate(reason):
    stop_client()
    emit("reallocate", reason=reason)
    request = urllib.request.Request("http://169.254.169.254/v1/reallocate",
        json.dumps({"reason": reason}).encode(),
        {"Metadata": "true", "Content-Type": "application/json"}, method="POST")
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                accepted = 200 <= response.status < 300
                emit("reallocate_result", attempt=attempt, http_status=response.status, accepted=accepted)
                if accepted:
                    break
        except Exception as error:
            emit("reallocate_result", attempt=attempt, accepted=False,
                 http_status=getattr(error, "code", None), error=type(error).__name__, fallback="nonzero_exit")
        if attempt < 3:
            time.sleep(2 * attempt)
    raise SystemExit(75)


def main():
    global process
    if not TOKEN:
        emit("configuration_error", error="TM_TOKEN is missing")
        raise SystemExit(64)
    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    ip = None
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as response:
            candidate = response.read(100).decode().strip()
            if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", candidate):
                ip = candidate
    except Exception:
        pass
    previous_rx, previous_tx = counters()
    previous_mono = time.monotonic()
    previous_ms = int(time.time() * 1000)
    total_rx = total_tx = seq = 0
    bad_seconds = 0
    health_checked_at = time.monotonic()
    status_at = statistics_at = payload_at = health_checked_at
    healthy_since = None
    was_healthy = False
    native_total = None
    final_state = None
    selector = selectors.DefaultSelector()
    buffer = b""
    connected = accepting = False
    status_ms = None
    native_in = native_out = None
    native_requests = None
    last_error = None
    next_sample = time.monotonic() + 1
    next_command = time.monotonic()
    batch = []

    def sample(final=False):
        nonlocal previous_rx, previous_tx, previous_mono, previous_ms, total_rx, total_tx, seq
        now = time.monotonic()
        rx, tx = counters()
        end_ms = int(time.time() * 1000)
        interval_ms = (now - previous_mono) * 1000
        reset = rx < previous_rx or tx < previous_tx
        delta_rx = None if reset else rx - previous_rx
        delta_tx = None if reset else tx - previous_tx
        if not reset:
            total_rx += delta_rx
            total_tx += delta_tx
        current_status = status_ms is not None and now - status_at <= 60
        state = final_state or ("connected" if current_status and connected and accepting and process is not None and process.poll() is None else "starting" if not current_status else "disconnected")
        batch.append([seq, end_ms, previous_ms, round(interval_ms, 3), delta_rx, delta_tx,
                      total_rx, total_tx, state, status_ms, 0, connected, accepting,
                      round((now - status_at) * 1000), round((now - statistics_at) * 1000)])
        previous_rx, previous_tx, previous_mono, previous_ms = rx, tx, now, end_ms
        seq += 1
        if len(batch) >= 10 or final:
            emit("batch", samples=batch, final=final, ip=ip, native_inbound=native_in,
                 native_outgoing=native_out, native_requests=native_requests, error=last_error,
                 unavailable_seconds=round(bad_seconds, 1),
                 policy={"state": final_state or ("observing_payload" if connected and accepting else "waiting_connection"),
                         "unavailable_seconds": round(bad_seconds, 1), "failure_limit_seconds": 30,
                         "silence_limit_seconds": 60, "reallocate_on_idle": False,
                         "payload_idle_seconds": round(now - payload_at, 1)})
            batch.clear()

    emit("start", controller="imds", ip=ip)
    while not stopping:
        now = time.monotonic()
        if process is None:
            process = subprocess.Popen(["/usr/local/bin/cli", "start", "accept", "--token", TOKEN,
                "--device-name", DEVICE], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, bufsize=0)
            os.set_blocking(process.stdout.fileno(), False)
            selector.register(process.stdout, selectors.EVENT_READ)
            buffer = b""
            connected = accepting = False
            status_ms = None
            native_in = native_out = native_requests = None
            bad_seconds = 0
            health_checked_at = now
            status_at = statistics_at = payload_at = now
            healthy_since = None
            was_healthy = False
            native_total = None
            next_command = now + 3
            emit("client_start", client_run=0)
        for key, _ in selector.select(timeout=max(0, min(0.2, next_sample - now))):
            chunk = os.read(key.fd, 16384)
            if not chunk:
                selector.unregister(key.fileobj)
                if not buffer:
                    continue
                chunk = b"\n"
            buffer += chunk
            if len(buffer) > 262144:
                buffer = buffer[-65536:]
            while b"\n" in buffer:
                raw, buffer = buffer.split(b"\n", 1)
                line = re.sub(r"\x1b\[[0-9;]*m", "", raw.decode(errors="replace")).strip()
                status = STATUS.search(line)
                connection = CONNECTION.fullmatch(line)
                stats = STATS.search(line)
                if status:
                    connected, accepting = (value.lower() == "true" for value in status.groups())
                    status_ms = int(time.time() * 1000)
                    status_at = time.monotonic()
                    if not (connected and accepting):
                        healthy_since = None
                elif connection:
                    connected = connection[1].lower() == "connected"
                    if not connected:
                        accepting = False
                        status_ms = int(time.time() * 1000)
                        healthy_since = None
                        last_error = "Last connection event: " + connection[1].lower()
                    emit("client_log", message=line.replace(TOKEN, "[redacted]")[:500])
                elif stats:
                    native_in, native_out, requests = stats.groups()
                    native_requests = int(requests)
                    if native_in.isdigit() and native_out.isdigit():
                        statistics_at = time.monotonic()
                        total = int(native_in) + int(native_out)
                        if (native_total is None and total > 0) or (native_total is not None and total > native_total):
                            payload_at = statistics_at
                        native_total = total
                elif any(word in line.lower() for word in ("error", "failed", "invalid", "denied")):
                    clean = line.replace(TOKEN, "[redacted]")[:500]
                    if clean != last_error:
                        last_error = clean
                        emit("client_error", message=clean)
                elif line:
                    emit("client_log", message=line.replace(TOKEN, "[redacted]")[:500])
        now = time.monotonic()
        if stopping:
            break
        if process is not None and process.poll() is None and now >= next_command:
            try:
                process.stdin.write(b"status\nstatistics\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                last_error = "Client command input closed"
            next_command = now + 10
        stale = now - status_at >= 60
        if stale:
            connected = accepting = False
            last_error = "Client status stopped responding"
        failed = process is not None and process.poll() is not None
        healthy = connected and accepting and process is not None and not failed and not stale
        if not was_healthy and status_ms is not None and not stale:
            bad_seconds += max(0, now - health_checked_at)
        if healthy:
            if healthy_since is None:
                healthy_since = now
            elif now - healthy_since >= 60:
                bad_seconds = 0
                last_error = None
        else:
            healthy_since = None
        was_healthy = healthy
        health_checked_at = now
        unavailable = bad_seconds >= 30
        unresponsive = now - status_at >= 60 or now - statistics_at >= 60
        # No customer payload is an activity observation, not a client failure.
        if failed or unavailable or unresponsive:
            reason = ("Traffic Monetizer client exited" if failed else
                      "Traffic Monetizer status or statistics stopped replying for 60 seconds" if unresponsive else
                      "Traffic Monetizer accumulated 30 seconds of unavailable connection")
            final_state = "reallocating"
            stop_client()
            sample(final=True)
            reallocate(reason)
        if now >= next_sample:
            sample()
            next_sample = now + 1
    stop_client()
    final_state = "stopped"
    sample(final=True)
    emit("stopped")


if __name__ == "__main__":
    main()
