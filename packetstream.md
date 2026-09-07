# PacketStream — complete rebuild guide

**Reproducibility:** the embedded source and deployment settings are reproducible. New IPs, placement time, traffic demand, provider acceptance and earnings are not fixed outputs of this software. Identical MB or credits are not promised. This verification used isolated reconstruction tests and read-only live comparisons; it did not delete and recreate the paid fleet.

Verified against the running deployment and matching source on **7 September 2026, UTC**. This file contains the exact client wrapper, Salad deployment recipe, native census and minute recorder, SQLite/parser code, Keychain source and local service setup.

## Required external inputs

You need the Salad account/API key, the PacketStream account's **CID**, funded hyperlane/default access, the pinned official image, and macOS with Python 3.9+, curl and Xcode Command Line Tools. The CID is entered at rebuild time; do not copy somebody else's account identifier. No passwords, API keys, live browser sessions or traffic-history database are embedded.

This document recreates the software and a new run. Original sold-traffic/provider history and local minute history require their own surviving backup or still-retained provider logs. The closed-source vendor image requires the registry or an independently saved image archive.

## Exact deployed configuration

| Setting | Verified value |
|---|---|
| Organization / project / group | hyperlane / default / ps-test-us |
| Historical group ID | a36f8bba-0b01-4e86-9948-0cedb2fac3de |
| Layout | One group, ten replicas, one official PacketStream client per replica |
| Image | docker.io/packetstream/psclient@sha256:6e6a2cefe9f49c33f6c9d4bd41d21daf20c4767f2c66e82f57a5960ec9923987 |
| Runtime architecture | Linux amd64; official /usr/local/bin/pslauncher |
| CPU / memory / shared memory | 1 CPU / 1,024 MiB / 64 MiB per replica; no GPU |
| Placement / priority | US / batch |
| Restart policy / current auto-start flag | always / false; explicitly started |
| Public networking / probes | None configured |
| Current group revision | 7 |
| Cloud display name / image caching | PS Test US / enabled |
| Complete command SHA-256 | e55cd5a1c6e8ea102600732b775ba71bb7c42cf0ac51f8763b8f7202d2d0b948 |
| Environment | CID only; no Salad account API key inside the workload |
| Dashboard | http://127.0.0.1:8787/#ps1 |

**The URL fragment #ps1 is a UI name. The live Salad group is ps-test-us.** The old group ps1 and its custom port-8789 collector are retired paths. Do not bootstrap from scripts/ps1-control.py or allow the native recorder to fall back to its old ps1 branch. The binding file below is mandatory.

## Restore and start

1. Extract this document's verified source. It refuses to overwrite different files.

~~~~bash
python3 - "$HOME/Desktop/salad/packetstream.md" "$HOME/Library/Application Support/Salad Bandwidth Dashboard" <<'PY'
import hashlib, re, sys
from pathlib import Path
document=Path(sys.argv[1]);root=Path(sys.argv[2]).expanduser().resolve()
text=document.read_text()
pattern=r'^<!-- rebuild-file: ([^\n]+) sha256=([0-9a-f]{64}) -->\n~~~~~~[^\n]*\n(.*?)^~~~~~~\n'
files=re.findall(pattern,text,re.M|re.S)
if not files:raise SystemExit('No embedded source files found')
checked=[]
for name,digest,body in files:
    relative=Path(name)
    if relative.is_absolute() or '..' in relative.parts:raise SystemExit('Unsafe embedded path')
    target=root/relative;raw=body.encode()
    if hashlib.sha256(raw).hexdigest()!=digest:raise SystemExit('Damaged source block: '+name)
    if target.exists() and target.read_bytes()!=raw:raise SystemExit('Existing different file preserved: '+str(target))
    checked.append((target,raw))
for target,raw in checked:
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(raw)
print('Restored',len(checked),'verified files to',root)
PY
~~~~

2. Build the Keychain helper and enter the Salad API key.

~~~~bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
mkdir -p .runtime
chmod 700 .runtime
xcrun swiftc scripts/keychain-store.swift -o .runtime/keychain-store
chmod 700 .runtime/keychain-store
python3 scripts/save-secret.py salad-bandwidth-api
~~~~

Use the existing Salad API key for the account that can access the named organizations. The prompt is hidden; the key goes to macOS Keychain service **salad-bandwidth-api**, account **your macOS login name**. Never put the key in this Markdown, a command argument, or a copied cloud JSON response. A freshly compiled helper may trigger the normal macOS Keychain access prompt. Do not start multiple copies of an observer: each uses a lock.


3. Validate the payload without external actions.

~~~~bash
python3 scripts/rebuild-cloud.py packetstream plan
~~~~

4. Create/start the ten-replica deployment, entering your CID at the hidden prompt. This starts billable cloud workloads.

~~~~bash
python3 scripts/rebuild-cloud.py packetstream create
~~~~

If the cloud group already survives, use:

~~~~bash
python3 scripts/rebuild-cloud.py packetstream bind
~~~~

The script verifies the full documented configuration and a nonempty CID. In create mode, an existing group must also match the CID just entered; a mismatch stops before starting it. In bind mode, confirm that the surviving group belongs to your PacketStream account. Secret values are never printed. It saves the current, newly returned group ID to ~/.hg1/packetstream/observer-target.json:

~~~~json
{"mode":"native-census","organization":"hyperlane","project":"default","group":"ps-test-us","group_id":"ACTUAL_ID_FROM_SALAD"}
~~~~

Do not reuse the historical group ID after deleting/recreating the group.

5. Start the local observer:

~~~~bash
python3 scripts/install-services.py ps
~~~~

The installed ps1-native-recorder.py sees mode=native-census, sets PS_GROUP and PS_EXPECTED_GROUP_ID, then runs packetstream-monitor/native-census.py. It never starts Docker Desktop. Native census runs about every 30 seconds; minute collection runs independently about every 15 seconds.

Restore website.md to serve the graph. The minute recorder itself is usable without the website.

## Exact recovery and measurement behavior

The embedded packetstream-monitor/start-with-recovery.sh is the complete cloud wrapper. It starts the stock launcher, reads native log lines and measures eth0 counters.

| Event | Current action |
|---|---|
| Duplicate public IP or rejected non-residential IP | Stop client and request reallocation immediately |
| Native generic client error | Request reallocation immediately |
| Client process exits | Request reallocation immediately |
| Communication error persists | Replace after 30 seconds; a native running status clears that timer |
| No initial connection | Replace after 60 seconds |
| Operator stop | Stop the child and emit a final interval; do not classify as a new healthy client |

Each reallocation uses the instance metadata endpoint POST http://169.254.169.254/v1/reallocate, Metadata: true, Content-Type: application/json and a reason. HTTP 200/204 is success; the wrapper then exits 75. The native logs distinguish PS_SELF_REALLOCATE, PS_SELF_IMDS_RESPONSE, PS_SELF_IMDS_ACCEPTED and failure. [IMDS reference](https://docs.salad.com/reference/imds/reallocate).

A 7 September live incident confirmed this path: after a 30-second communication failure the wrapper logged a replacement request and HTTP 200, then the fleet recovered. An accepted request is still distinct from the next instance becoming connected.

## Command transport: do not lose this detail

The source is UTF-8, base64 encoded, and split into strings no longer than 900 characters. The launch command joins those base64 strings with printf "%s" "$@", decodes them to /tmp/ps-self-recovery.sh and execs Bash.

An earlier deployment split raw source into strings. Salad trimmed boundary whitespace, removing newlines and producing invalid programs. Base64 transports the exact bytes. The rebuild helper checks the tested command envelope: at most 100 arguments, at most 1,000 characters each. These are the bounds used by this recipe, not a promise about future provider limits.

Do not paste a password-bearing shell string, substitute a custom binary, reintroduce a gateway, or attach one public IP to several PacketStream clients.

## Minute-record contract

The cloud wrapper emits PS_MINUTE_V2 text lines. An example shape, with illustrative values only:

~~~~text
PS_MINUTE_V2 instance=UUID machine=UUID observer=START_MS seq=N start_ms=A end_ms=B rx=RX_DELTA tx=TX_DELTA total_rx=RUN_RX total_tx=RUN_TX ip=PUBLIC_IP state=running error=none final=0 bucket_ms=UTC_MINUTE_START
~~~~

- Values are integer bytes and Unix milliseconds. Network MB = (rx+tx)/1,000,000; this includes overhead and both directions of relayed traffic.
- observer identifies the wrapper run; seq is monotonic within it. Never join counters from different runs.
- The first record establishes the baseline. Normal records cover UTC-aligned minutes; shutdown records can be partial.
- A final replacement record has state=reallocating and final=1. Its parser must accept that state.
- Counter resets/gaps/invalid records remain explicit. Missing data is not zero.
- Exact V2 minute buckets remain exact. Old V1/unaligned intervals are proportionally split and labelled estimated rather than erased.
- The group-wide log collector retains departed instances' measurements; it does not restrict history to current members.
- Full Salad result pages are recursively split into time windows; records are deduplicated in SQLite. Do not advance over unexamined capped pages.
- Country lookup uses api.country.is and is informational; geolocation is not proof the provider accepted a residential IP.

SQLite schema and calculations are fully embedded in dashboard/native_network.py. Its tables include minutes, countries and collector status; runtime code creates/migrates them. Preserve the whole database, not just the latest JSON census.

## Native client status and current inventory

packetstream-monitor/audit-client-status.py reads Salad instances and native Status lines. The PS_NATIVE prefix includes the actual runtime instance ID, because Salad log resource IDs can lag a rollout. The embedded ID must match the current API instance before claiming native acceptance.

The website checks source freshness separately from provider credit freshness. A node may be cloud-running but still starting, downloading, reallocating, or awaiting a client sample. A stale local feed must not become a new machine-failure signal.

## Provider-sold traffic is a separate feed

The current root graph is **container network traffic**, not automatically sold traffic. PacketStream earnings were not reliably available from the native client. The site must say Not reported until genuine provider observations exist; never multiply network bytes by a guessed payout rate.

The preserved optional browser bridge is dashboard/ps-paid-feed.js. It reads the logged-in PacketStream dashboard's own reportData and posts **only byte totals and observation time** to the local page. It never sends cookies or account credentials to localhost.

To restore that optional feed on your own signed-in browser:

1. In the local dashboard's console, set the channel and reload once:

~~~~javascript
sessionStorage.setItem('ps-billing-channel', crypto.randomUUID());
location.reload();
~~~~

2. After the local page finishes loading, open its provider child window from the local page's console:

~~~~javascript
window.open('https://app.packetstream.io/dashboard#ps-sync='+encodeURIComponent(sessionStorage.getItem('ps-billing-channel')), 'psBillingSync');
~~~~

3. Sign in to the correct PacketStream account. The embedded paid-feed source contains the old public referral/account guard psr=8ExP. If rebuilding for another account, replace only that guard with its real referral identifier, verified from the provider's own referral link. Then run the embedded paid-feed source in that child page's console. Keep both pages open.
4. /api/ps1/view must show actual fresh observations; at least two nondecreasing provider samples are needed for a credited delta. The graph remains network MB and the earnings field can still be Not reported.

The endpoint POST /api/ps1/credited requires the current X-PS-Token issued by /api/ps1/view. The bridge refreshes that token and retries once on 403. Do not hardcode a stale token. Refresh errors or a changed provider HTML/report format must fail visibly rather than post a zero reading.

## Locations and operations

| Location | Purpose |
|---|---|
| ~/Desktop/salad-bandwidth-stack/packetstream-monitor/start-with-recovery.sh | Editable cloud wrapper |
| ~/Library/Application Support/Salad Bandwidth Dashboard/ps1-native-recorder.py | LaunchAgent entry point |
| Same root / packetstream-monitor/native-census.py | Orchestrates status and minute collection |
| Same root / packetstream-monitor/audit-client-status.py | Current native acceptance |
| Same root / packetstream-monitor/native-network.py | Complete minute log collection |
| ~/.hg1/packetstream/observer-target.json | Current group binding; prevents retired-mode fallback |
| ~/.hg1/packetstream/native-census.json | Latest safe inventory and native state |
| ~/.hg1/packetstream/minutes.sqlite3 | Durable recorded minute history |
| ~/.hg1/packetstream/provider-observations.jsonl | Actual provider byte observations |
| ~/.hg1/packetstream/dashboard-periods-*.json | Observed group starts/stops, scoped to the group |
| ~/Library/LaunchAgents/com.cosmosgeek.ps1-recorder.plist | Local observer |

~~~~bash
launchctl print "gui/$(id -u)/com.cosmosgeek.ps1-recorder"
launchctl kickstart -k "gui/$(id -u)/com.cosmosgeek.ps1-recorder"
curl -fsS http://127.0.0.1:8787/api/ps1/minutes
~~~~

Check the actual plist's stdout/stderr filenames. The reconstruction installer uses native-recorder.out.log and native-recorder.err.log in ~/.hg1/packetstream.

## Verification and known failure remedies

Measured recheck on 7 September 2026: the printed extractor restored all twelve files from this document alone and validated every manifest hash. Isolated creation/start/rebind checks produced one ten-replica group, reused no historical UUID and added no duplicates. Wrong CID, missing CID and changed memory fixtures were rejected before any start request. Read-only Salad comparison matched the real ps-test-us configuration and command digest; the registry returned the exact Linux amd64 manifest. No new paid containers were launched by this check.

| Check/failure | Required result or remedy |
|---|---|
| Only “Salad running” is visible | Require fresh native running state before counting a confirmed client |
| Old ps1 group is queried | Fix observer-target.json and PS_GROUP=ps-test-us; do not launch the retired gateway collector |
| Ten-minute query returns a full capped page | Split windows; do not assume ordering or silently skip the rest |
| New container starts with a large lifetime counter | Establish its baseline; do not add that lifetime total as new traffic |
| Replacement disappears from the current table | Keep unassigned slots visible; do not invent IPs or metrics |
| Final reallocation minute rejected | Parser must allow reallocating and final=1 |
| Platform log ID differs after an update | Use the embedded PS_NATIVE/runtime identity |
| Need an API reallocation | Read exact current group and instance IDs, POST .../instances/ID/reallocate; verify the replacement |
| Need the prior chart history | Restore minutes.sqlite3 from a consistent backup; do not reuse an old collector cursor without its rows |
| Provider feed is stale | Re-establish the signed-in bridge or leave Not reported; network recording can continue |

No new schema, gateway, UI button collection, local Docker control loop, or benchmark-generated traffic is required for this deployment.

For a vendor-image backup:

~~~~bash
docker pull --platform linux/amd64 docker.io/packetstream/psclient@sha256:6e6a2cefe9f49c33f6c9d4bd41d21daf20c4767f2c66e82f57a5960ec9923987
docker save -o packetstream-amd64.tar docker.io/packetstream/psclient@sha256:6e6a2cefe9f49c33f6c9d4bd41d21daf20c4767f2c66e82f57a5960ec9923987
~~~~

[Salad create-group API](https://docs.salad.com/reference/saladcloud-api/container-groups/create-container-group).

## Complete source appendix

| Restored file | SHA-256 |
|---|---|
| dashboard/__init__.py | 9e72baa6472e739d23291c979acefeba840fee3e9075376a188bf94f66f8f106 |
| dashboard/native_network.py | 7aebbb480bab2244e47d768994e8530bec1c529bc819e7878875c6b99e2f8a7d |
| dashboard/ps-paid-feed.js | a0809b7941d4cb91621cd499a383161e7a0005644ba3f24f3dc0747b0dad6acc |
| packetstream-monitor/audit-client-status.py | dedb9113f45026be32a9a8e80d74da971e31ef3b462a3e6d55766ac8abab46b4 |
| packetstream-monitor/native-census.py | 400b1d22f26fab942eaf503940b94f4fdac1bf8c3b75a3d5ead12302ca5e16f8 |
| packetstream-monitor/native-network.py | 6c656033e0ca0121885da58a740f3df5fe614e5ed5af776037d6bd6e046e9f7c |
| packetstream-monitor/start-with-recovery.sh | a1352f21f52114bfdb716894303b29dc2d7cff1f9893950904716c1dd5ee2dbf |
| ps1-native-recorder.py | a950adc2e25afad35a0085c1830ad681e5a4351f31fc46ef3f55134f00c63138 |
| scripts/install-services.py | 3c75ac6e7c82f8b1e06104d59b02c13b073685e0c5f19a4a25a3e7534a7ee4e9 |
| scripts/keychain-store.swift | 490eadaf1afb87a0f64bf6248254ccc48ac1171af9e2fc4c796c74c12c5ca045 |
| scripts/rebuild-cloud.py | 4fde37bb6ea6402a3ab1ce7fe46d935503ee7b6038af0f3c2ec48c0c401c08b9 |
| scripts/save-secret.py | 98e37bb083dd0c10773d1dfdc187780af29f7a62beb361cfc99ec0fc92822e9e |

### dashboard/__init__.py

<!-- rebuild-file: dashboard/__init__.py sha256=9e72baa6472e739d23291c979acefeba840fee3e9075376a188bf94f66f8f106 -->
~~~~~~python
"""Local Salad bandwidth dashboard."""
~~~~~~

### dashboard/native_network.py

<!-- rebuild-file: dashboard/native_network.py sha256=7aebbb480bab2244e47d768994e8530bec1c529bc819e7878875c6b99e2f8a7d -->
~~~~~~python
from contextlib import closing
"""Exact per-container minute records, durable storage, and dashboard summaries."""
from datetime import datetime
import ipaddress
from pathlib import Path
import re
import sqlite3
import threading
import time

UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z")
FIELDS = ("group_id", "instance", "machine", "observer", "seq", "start_ms", "end_ms",
          "rx", "tx", "total_rx", "total_tx", "ip", "state", "error", "final", "valid",
          "received_ms", "record_bytes", "bucket_ms")
ERRORS = {"communication_error": "Cannot communicate with PacketStream",
          "duplicate_ip": "PacketStream permits one client per public IP",
          "non_residential": "PacketStream rejected this IP as non-residential",
          "client_exited": "PacketStream client exited", "client_error": "PacketStream client reported an error; replacing this machine",
          "connection_timeout": "PacketStream did not connect within 60 seconds"}


def instance_run(value):
    parts = value.split("/") if isinstance(value, str) else []
    return "/".join(parts[:2]) if len(parts) >= 2 and all(UUID.fullmatch(p) for p in parts[:2]) else None


def stamp(value):
    if not value:
        return None
    value = re.sub(r"\.(\d+)(?=[+-])", lambda m: "." + m.group(1)[:6].ljust(6, "0"), value.replace("Z", "+00:00"))
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def parse_minute(item, group_id, received_ms=None):
    line = item.get("text_log", "")
    if not line.startswith(("PS_MINUTE_V1 ", "PS_MINUTE_V2 ")):
        return None
    try:
        values = dict(part.split("=", 1) for part in line.split()[1:])
        if not all(UUID.fullmatch(values[k]) for k in ("instance", "machine")):
            return None
        numbers = {key: int(values[key]) for key in
                   ("observer", "seq", "start_ms", "end_ms", "rx", "tx", "total_rx", "total_tx", "final")}
        if any(abs(v) > 2**53 - 1 for v in numbers.values()):
            return None
        if not (0 < numbers["observer"] <= numbers["start_ms"] <= numbers["end_ms"]
                and numbers["seq"] >= 0 and numbers["final"] in (0, 1)):
            return None
        if values["state"] not in ("starting", "running", "error", "exited", "reallocating"):
            return None
        ip = str(ipaddress.ip_address(values["ip"])) if values["ip"] != "-" else None
        result = dict(numbers, group_id=group_id, instance=values["instance"], machine=values["machine"],
                      ip=ip, state=values["state"], error=values.get("error", "none"),
                      valid=int(all(numbers[k] >= 0 for k in ("rx", "tx", "total_rx", "total_tx"))),
                      received_ms=received_ms or int(time.time() * 1000),
                      record_bytes=len(line.encode("utf-8")) + 1,
                      bucket_ms=int(values["bucket_ms"]) if "bucket_ms" in values else None)
        if result["bucket_ms"] is not None and (result["bucket_ms"] % 60000 or result["bucket_ms"] < 0):
            return None
        bucket = result["bucket_ms"]
        if bucket is not None and not bucket <= numbers["start_ms"] <= numbers["end_ms"] <= bucket + 60000:
            result["bucket_ms"] = None
        return result
    except (ValueError, KeyError, TypeError):
        return None


class NetworkMinutes:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS minutes (
                group_id TEXT, instance TEXT, machine TEXT, observer INTEGER, seq INTEGER,
                start_ms INTEGER, end_ms INTEGER, rx INTEGER, tx INTEGER,
                total_rx INTEGER, total_tx INTEGER, ip TEXT, state TEXT, error TEXT,
                final INTEGER, valid INTEGER, received_ms INTEGER, record_bytes INTEGER, bucket_ms INTEGER,
                PRIMARY KEY(group_id, instance, observer, seq));
            CREATE INDEX IF NOT EXISTS minutes_received ON minutes(group_id, received_ms);
            CREATE TABLE IF NOT EXISTS countries (ip TEXT PRIMARY KEY, country TEXT);
            CREATE TABLE IF NOT EXISTS collector (group_id TEXT PRIMARY KEY, time_ms INTEGER,
                cursor TEXT, error TEXT, inserted INTEGER);
        """)
        if "bucket_ms" not in {row[1] for row in self.db.execute("PRAGMA table_info(minutes)")}:
            self.db.execute("ALTER TABLE minutes ADD COLUMN bucket_ms INTEGER")
        self.db.commit()

    def ingest(self, records):
        inserted = 0
        with self.lock, self.db:
            for row in records:
                values = tuple(row.get(k) for k in FIELDS)
                result = self.db.execute("INSERT OR IGNORE INTO minutes VALUES (" + ",".join("?" * len(FIELDS)) + ")", values)
                inserted += result.rowcount
                if not result.rowcount:
                    old = self.db.execute(
                        "SELECT * FROM minutes WHERE group_id=? AND instance=? AND observer=? AND seq=?",
                        (row["group_id"], row["instance"], row["observer"], row["seq"])).fetchone()
                    core = [k for k in FIELDS if k not in ("received_ms", "record_bytes")]
                    if any(old[k] != row.get(k) for k in core if k != "valid"):
                        self.db.execute("UPDATE minutes SET valid=0 WHERE group_id=? AND instance=? AND observer=? AND seq=?",
                                        (row["group_id"], row["instance"], row["observer"], row["seq"]))
        return inserted

    def collector_status(self, group_id, cursor=None, error=None, inserted=0):
        with self.lock:
            if cursor is None:
                row = self.db.execute("SELECT * FROM collector WHERE group_id=?", (group_id,)).fetchone()
                return dict(row) if row else {}
            with self.db:
                self.db.execute("INSERT OR REPLACE INTO collector VALUES (?,?,?,?,?)",
                                (group_id, int(time.time() * 1000), cursor, error, inserted))

    def latest(self, group_id):
        with self.lock:
            rows = self.db.execute("""
                SELECT m.* FROM minutes m JOIN (
                    SELECT instance, MAX(observer) observer FROM minutes WHERE group_id=? GROUP BY instance
                ) r ON m.instance=r.instance AND m.observer=r.observer
                WHERE m.group_id=? AND m.seq=(SELECT MAX(seq) FROM minutes
                    WHERE group_id=m.group_id AND instance=m.instance AND observer=m.observer)
            """, (group_id, group_id)).fetchall()
            return {row["instance"]: dict(row) for row in rows}

    def minute(self, group_id, minute_ms):
        with self.lock:
            rows=self.db.execute("""SELECT m.*, c.country FROM minutes m LEFT JOIN countries c ON m.ip=c.ip
                WHERE m.group_id=? AND m.seq>0 AND m.valid=1 AND m.end_ms>=? AND m.start_ms<?""",
                (group_id,minute_ms,minute_ms+60000)).fetchall()
        points=bucket_minutes(rows,minute_ms,minute_ms)
        return points[0] if points else {"minute_ms":minute_ms,"mb":None,"count":0,"nodes":[]}

    def snapshot(self, census, now_ms=None):
        now = now_ms or int(time.time() * 1000)
        group_id = census.get("group_id", "")
        census_at = stamp(census.get("last_success_at") or census.get("checked_at"))
        census_fresh = census_at is not None and 0 <= now - census_at < 120_000 and not census.get("poll_error")
        current = {row["instance_id"]: row for row in census.get("nodes", [])}
        desired = int(census.get("desired_replicas") or len(current))
        end = now // 60000 * 60000
        start = end - 1439 * 60000
        nodes = []
        with self.lock, self.db:
            self.db.execute("BEGIN")
            latest = self.latest(group_id)
            rows=self.db.execute("SELECT * FROM minutes WHERE group_id=? AND valid=1 AND seq>0 AND end_ms>=? AND start_ms<?",(group_id,start,end+60000)).fetchall()
            points={p["minute_ms"]:p for p in bucket_minutes(rows,start,end)}
            candles=[]
            for minute in range(start,end+1,60000):
                point=points.get(minute)
                candles.append({"minute_ms":minute,"mb":point["mb"] if point else None,
                                "estimated":bool(point and point["estimated"]),
                                "partial":bool(not point or point["partial"] or point["count"]<desired or minute+60000>now)})
            for instance, member in current.items():
                last = latest.get(instance)
                observer = last["observer"] if last else None
                client = (member or {}).get("client_status") or {}
                client_at = stamp(client.get("source_time"))
                client_fresh = census_fresh and client_at is not None and -10_000 <= now - client_at <= 240_000
                state = client.get("state") if client_fresh else None
                error = client.get("message") if state == "error" else None
                if last and (not client_at or last["end_ms"] >= client_at) and -10_000 <= now - last["end_ms"] <= 150_000:
                    state = "stopped" if last["final"] and last["state"] == "running" else last["state"]
                    error = ERRORS.get(last["error"], last["error"]) if last["error"] != "none" else None
                salad_state = member.get("salad_state") if member else "previous"
                if not census_fresh:
                    label = "Status feed stale"
                elif state == "running":
                    label = "Running"
                elif state == "stopped":
                    label = "Stopped"
                elif state == "reallocating":
                    label = "Reallocating"
                elif state in ("error", "exited"):
                    label = "Error"
                elif salad_state != "running":
                    label = (salad_state or "starting").capitalize()
                else:
                    label = "Checking client"
                total, captured, latest_rate, first_at, last_at = None, 0, None, None, None
                gaps = False
                if last:
                    stats = self.db.execute("""
                        SELECT SUM(CASE WHEN valid=1 THEN rx+tx ELSE 0 END) recorded,
                               MIN(valid) valid, COUNT(CASE WHEN seq>0 THEN 1 END) count,
                               MIN(start_ms) first, MAX(end_ms) last, MAX(seq) seq
                        FROM minutes WHERE group_id=? AND instance=? AND observer=?
                    """, (group_id, instance, observer)).fetchone()
                    first_at, last_at = stats["first"], stats["last"]
                    gaps = stats["count"] < stats["seq"] or not stats["valid"]
                    total = (last["total_rx"] + last["total_tx"]) / 1e6 if stats["valid"] else stats["recorded"] / 1e6
                    captured = stats["count"]
                    seconds = (last["end_ms"] - last["start_ms"]) / 1000
                    if last["seq"] > 0 and last["valid"] and seconds > 0:
                        latest_rate = (last["rx"] + last["tx"]) / 1e6 * 60 / seconds
                metrics_fresh = last is not None and -10_000 <= now - last["end_ms"] <= 150_000 and not last["final"]
                nodes.append({"id": instance + "/" + str(observer or "pending"), "instance": instance,
                              "machine": member["machine"],
                              "current": True, "ip": last["ip"] if last else None,
                              "status": label, "salad_state": salad_state, "client_state": state, "error": error,
                              "start_ms": observer, "end_ms": last_at,
                              "elapsed_seconds": (last_at - first_at) / 1000 if first_at is not None else None,
                              "total_mb": total, "latest_mb_per_minute": latest_rate,
                              "minutes_recorded": captured, "metrics_fresh": bool(metrics_fresh),
                              "has_gaps": gaps, "sample_age_ms": now - last["end_ms"] if last else None})
            disk_minute = end - 60000
            saved = self.db.execute("""
                SELECT COUNT(*) records, COALESCE(SUM(record_bytes),0) bytes FROM minutes
                WHERE group_id=? AND received_ms>=? AND received_ms<?
            """, (group_id, disk_minute, disk_minute + 60000)).fetchone()
            totals = self.db.execute("SELECT COUNT(*) records, COALESCE(SUM(record_bytes),0) bytes, SUM(CASE WHEN valid=1 THEN rx+tx ELSE 0 END) network_bytes, MIN(start_ms) started_ms FROM minutes WHERE group_id=?", (group_id,)).fetchone()
        file_size = sum(path.stat().st_size for path in (self.path, Path(str(self.path) + "-wal")) if path.exists())
        return {"time_ms": now, "group": census.get("group"), "desired": desired, "assigned": len(current),
                "allocating": max(0, desired - len(current)), "inventory_fresh": census_fresh,
                "inventory_age_ms": now - census_at if census_at else None,
                "running": sum(n["status"] == "Running" for n in nodes),
                "errors": sum(n["status"] == "Error" for n in nodes),
                "nodes": nodes, "candles": candles, "collector": self.collector_status(group_id),
                "total_mb": totals["network_bytes"]/1e6 if totals["records"] else None, "started_ms": totals["started_ms"],
                "disk": {"minute_ms": disk_minute, "minute_bytes": saved["bytes"], "minute_records": saved["records"],
                         "total_record_bytes": totals["bytes"], "total_records": totals["records"],
                         "database_bytes": file_size,
                         "basis": "Telemetry payload bytes saved; excludes database/index overhead."}}


def saved_minutes(path, now_ms=None, group_id=None):
    """Read minute records from a provider's existing database without changing it."""
    now_ms = now_ms or int(time.time()*1000)
    first = now_ms//60000*60000 - 1439*60000
    if not Path(path).exists():
        return []
    with closing(sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)) as db:
        db.row_factory=sqlite3.Row
        query="SELECT * FROM minutes WHERE valid=1 AND seq>0 AND end_ms>=?"
        params=[first]
        if group_id is not None:
            query+=" AND group_id=?"
            params.append(group_id)
        rows=db.execute(query+" ORDER BY end_ms",params).fetchall()
    return bucket_minutes(rows,first,now_ms//60000*60000)


def bucket_minutes(rows, first, last):
    buckets={}
    for row in rows:
        start,end=row["start_ms"],row["end_ms"]
        amount=(row["rx"]+row["tx"])/1e6
        if end<start:
            continue
        exact=row["bucket_ms"]
        splits=[(exact,amount,False)] if exact is not None else []
        if exact is None and end==start:
            splits=[(end//60000*60000,amount,True)]
        elif exact is None:
            for minute in range(max(first,start//60000*60000),min(last,max(start,end-1)//60000*60000)+1,60000):
                overlap=min(end,minute+60000)-max(start,minute)
                if overlap>0:splits.append((minute,amount*overlap/(end-start),True))
        for minute,mb,estimated in splits:
            if not first<=minute<=last:
                continue
            bucket=buckets.setdefault(minute,{"minute_ms":minute,"mb":0,"estimated":False,"partial":False,"nodes":{}})
            bucket["mb"]+=mb;bucket["estimated"]|=estimated
            bucket["partial"]|=estimated or start!=minute or end!=minute+60000
            key=(row["instance"],row["machine"],row["ip"])
            node=bucket["nodes"].setdefault(key,{"instance":row["instance"],"machine":row["machine"],"ip":row["ip"],"country":row["country"] if "country" in row.keys() else None,"mb":0})
            node["mb"]+=mb
    result=[]
    for minute,bucket in sorted(buckets.items()):
        nodes=sorted(bucket["nodes"].values(),key=lambda n:(-n["mb"],n["instance"]))
        result.append(dict(bucket,count=len(nodes),nodes=nodes[:20]))
    return result
~~~~~~

### dashboard/ps-paid-feed.js

<!-- rebuild-file: dashboard/ps-paid-feed.js sha256=a0809b7941d4cb91621cd499a383161e7a0005644ba3f24f3dc0747b0dad6acc -->
~~~~~~javascript
// Run in the PacketStream tab opened by the local PS dashboard. No credentials
// are exported: only the provider's credited-byte total and observation time.
(async () => {
  const channel = new URLSearchParams(location.hash.slice(1)).get('ps-sync');
  if (!channel || !window.opener) throw new Error('Open from the local PS dashboard first.');
  if (window.__psPaidFeed) clearInterval(window.__psPaidFeed);
  let badge = document.getElementById('ps-local-feed');
  if (!badge) {
    badge = document.createElement('div'); badge.id = 'ps-local-feed';
    badge.style.cssText = 'position:fixed;bottom:16px;right:16px;z-index:99999;padding:12px 16px;border-radius:8px;background:#163d30;color:white;font:13px system-ui;box-shadow:0 3px 16px #0003';
    document.body.append(badge);
  }
  const send = data => window.opener.postMessage({type:'ps-credited',channel,...data}, 'http://127.0.0.1:8787');
  async function poll() {
    try {
      const response = await fetch('/dashboard', {credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(8000)});
      if (!response.ok) throw new Error('PacketStream could not be refreshed.');
      const doc = new DOMParser().parseFromString(await response.text(),'text/html');
      if (!(doc.querySelector('#referral-link')?.value || '').includes('psr=8ExP')) throw new Error('Sign in to the expected PacketStream account.');
      const source = [...doc.scripts].find(s => !s.src && s.textContent.includes('window.reportData'))?.textContent || '';
      const match = source.match(/const rd\s*=\s*("(?:\\.|[^"\\])*")\s*;/);
      if (!match) throw new Error('Provider report format changed.');
      const report = JSON.parse(JSON.parse(match[1]));
      if (!Array.isArray(report.exitnode)) throw new Error('Credited-byte records unavailable.');
      const bytes = report.exitnode.reduce((sum, row) => sum + Number(row.bandwidth.up) + Number(row.bandwidth.down), 0);
      if (!Number.isSafeInteger(bytes) || bytes < 0) throw new Error('Invalid credited-byte records.');
      send({gb:bytes/1e9,bytes,time_ms:Date.now()});
      // Refresh the existing provider UI using its own rendering function.
      window.reportData = report;
      if (typeof renderTrafficHistory === 'function') {
        document.getElementById('traffic-history-body')?.replaceChildren();
        renderTrafficHistory();
      }
      badge.textContent = 'PS dashboard connected · '+(bytes/1e6).toFixed(3)+' MB credited total · updates automatically';
      return bytes;
    } catch (error) { badge.textContent='PS feed: '+error.message; send({error:error.message}); }
  }
  await poll(); window.__psPaidFeed = setInterval(poll, 60000);
})();
~~~~~~

### packetstream-monitor/audit-client-status.py

<!-- rebuild-file: packetstream-monitor/audit-client-status.py sha256=dedb9113f45026be32a9a8e80d74da971e31ef3b462a3e6d55766ac8abab46b4 -->
~~~~~~python
#!/usr/bin/env python3
"""Read-only native-status census for PS1; never treat absent logs as failure."""
import concurrent.futures
from datetime import datetime, timedelta, timezone
import getpass
import json
import os
from pathlib import Path
import re
import subprocess


def collect():
    root = Path(__file__).resolve().parents[1]
    key = subprocess.check_output([str(root / ".runtime/keychain-store"), "--read", "--service",
                                   "salad-bandwidth-api", "--account", getpass.getuser()], text=True).strip()
    base = "https://api.salad.com/api/public/organizations/hyperlane"
    group = os.environ.get("PS_GROUP", "ps1")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,61}[a-z0-9]", group):
        raise ValueError("Invalid PacketStream group name")
    now = datetime.now(timezone.utc)

    def api(path, body=None):
        cfg = "header = " + json.dumps("Salad-Api-Key: " + key) + '\nheader = "Content-Type: application/json"\n'
        if body is not None:
            cfg += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
        result = subprocess.run(["curl", "-sS", "--max-time", "20", "--config", "-", "--write-out",
                                 "\n%{http_code}", base + path], input=cfg, text=True, capture_output=True, timeout=25)
        raw, code = result.stdout.rsplit("\n", 1)
        if result.returncode or code != "200":
            raise RuntimeError("Salad read failed HTTP " + code)
        return json.loads(raw)

    deployment = api("/projects/default/containers/" + group)
    expected_id = os.environ.get("PS_EXPECTED_GROUP_ID")
    if expected_id and deployment["id"] != expected_id:
        raise RuntimeError("PacketStream deployment identity changed")
    instances = api("/projects/default/containers/" + group + "/instances")["instances"]

    def one(instance):
        query = ('resource.type = "container" and resource.labels.container_group_name = "' + group + '" and '
                 'resource.labels.machine_id = "' + instance["machine_id"] + '" and text_log contains "Status:"')
        body = {"query": query, "start_time": (now-timedelta(minutes=10)).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "end_time": now.isoformat(timespec="milliseconds").replace("+00:00", "Z"), "page_size": 100, "sort_order": "desc"}
        row = {"machine": instance["machine_id"], "instance_id": instance["id"], "salad_state": instance["state"],
               "salad_ready": instance.get("ready"), "version": instance["version"], "client_status": None}
        try:
            result = api("/log-entries", body)
            statuses = []
            for item in result.get("items", []):
                text = item.get("text_log", "")
                embedded = re.match(r'PS_NATIVE instance=([^ ]+) ', text)
                recorded_instance = embedded.group(1) if embedded else item.get("resource", {}).get("labels", {}).get("instance_id")
                if recorded_instance != instance["id"]:
                    continue
                match = re.search(r'time="([^" ]+)".*msg="(Status: [^"]+)"', text)
                if match:
                    statuses.append((match.group(1), item.get("time", ""), match.group(2)))
            if statuses:
                at, indexed_at, message = max(statuses)
                state = "running" if message == "Status: PacketStream is running" else "error" if "error" in message.lower() else "unknown"
                row["client_status"] = {"state": state, "message": message, "source_time": at, "indexed_at": indexed_at,
                                         "source": "Salad native client logs; exact current instance"}
            row["returned_log_records"] = len(result.get("items", []))
        except (RuntimeError, subprocess.TimeoutExpired, ValueError):
            row["query_failed"] = True
        return row

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(one, instances))
    for row in rows:
        status = row.get("client_status")
        row["client_status_age_seconds"] = None
        if status:
            row["client_status_age_seconds"] = (now-datetime.fromisoformat(status["source_time"].replace("Z", "+00:00"))).total_seconds()
    result = {"schema_version": 1, "checked_at": now.isoformat(), "group": "hyperlane/default/" + group,
              "group_id": deployment["id"], "group_state": deployment["current_state"], "desired_replicas": deployment["replicas"], "nodes": rows,
              "running_instances": sum(row["salad_state"] == "running" for row in rows),
              "ready_instances": sum(bool(row["salad_ready"]) for row in rows),
              "accepted_clients": sum(row.get("client_status", {}).get("state") == "running" and row["client_status_age_seconds"] is not None and -10 <= row["client_status_age_seconds"] < 600 for row in rows if row.get("client_status")),
              "network_available": False, "network_note": "Plain official client has no network-counter exporter; missing network values are not zero traffic.",
              "limitations": "Up to 100 latest indexed logs per current instance over ten minutes. Missing status is unknown, not zero traffic or rejected."}
    return result


def main():
    root = Path(__file__).resolve().parents[1]
    result = collect()
    path = root / ".runtime/ps1-monitor/independent-test/client-census-latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
~~~~~~

### packetstream-monitor/native-census.py

<!-- rebuild-file: packetstream-monitor/native-census.py sha256=400b1d22f26fab942eaf503940b94f4fdac1bf8c3b75a3d5ead12302ca5e16f8 -->
~~~~~~python
#!/usr/bin/env python3
"""Continuously record native PS client acceptance without changing cloud clients."""
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import time


def main():
    source = Path(__file__).with_name("audit-client-status.py")
    spec = importlib.util.spec_from_file_location("ps_native_audit", source)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    network_spec = importlib.util.spec_from_file_location("ps_native_network", Path(__file__).with_name("native-network.py"))
    network_module = importlib.util.module_from_spec(network_spec)
    network_spec.loader.exec_module(network_module)
    network = network_module.NetworkObserver(Path(__file__).resolve().parents[1], os.environ["PS_GROUP"], os.environ["PS_EXPECTED_GROUP_ID"])
    target = Path.home()/".hg1/packetstream/native-census.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    last = {}
    while True:
        started = time.monotonic()
        try:
            result = audit.collect()
            network.update_members(result["nodes"])
            measurements = network.snapshots()
            for node in result["nodes"]:
                node["network"] = measurements.get(node["instance_id"], {"available": False, "reason": "Waiting for the first minute record"})
                node["ip"] = node["network"].get("ip")
            result["network_available"] = any(node["network"]["available"] for node in result["nodes"])
            result["network_note"] = "Minute records from each container are saved in minutes.sqlite3. Missing records are not zero traffic."
            result["last_success_at"] = result["checked_at"]
            result["poll_interval_seconds"] = 30
            last = result
        except Exception as error:
            result = dict(last, poll_error=type(error).__name__,
                          poll_failed_at=datetime.now(timezone.utc).isoformat(),
                          network_available=False)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, indent=2))
        os.replace(temporary, target)
        time.sleep(max(1, 30-(time.monotonic()-started)))


if __name__ == "__main__":
    main()
~~~~~~

### packetstream-monitor/native-network.py

<!-- rebuild-file: packetstream-monitor/native-network.py sha256=6c656033e0ca0121885da58a740f3df5fe614e5ed5af776037d6bd6e046e9f7c -->
~~~~~~python
"""Collect complete minute records from Salad logs, including replaced instances."""
from datetime import datetime, timedelta, timezone
import getpass
import json
from pathlib import Path
import re
import subprocess
import threading
import time

from dashboard.native_network import NetworkMinutes, parse_minute


def provider_datetime(value):
    value = re.sub(r"\.(\d+)(?=Z$|[+-]\d\d:\d\d$)", lambda m: "." + (m[1] + "000000")[:6], value)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class NetworkObserver:
    def __init__(self, app_root, group, group_id, data_dir=None):
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,61}[a-z0-9]", group):
            raise ValueError("Invalid PacketStream group")
        self.group, self.group_id = group, group_id
        self.key = subprocess.check_output(
            [str(app_root / ".runtime/keychain-store"), "--read", "--service",
             "salad-bandwidth-api", "--account", getpass.getuser()], text=True).strip()
        self.store = NetworkMinutes((data_dir or Path.home() / ".hg1/packetstream") / "minutes.sqlite3")
        self.members = []
        self.lock = threading.Lock()
        threading.Thread(target=self.run, daemon=True).start()

    def request(self, path, body=None):
        config = "header = " + json.dumps("Salad-Api-Key: " + self.key) + '\nheader = "Content-Type: application/json"\n'
        if body is not None:
            config += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
        response = subprocess.run(
            ["curl", "-sS", "--max-time", "20", "--config", "-", "--write-out", "\n%{http_code}",
             "https://api.salad.com/api/public/organizations/hyperlane" + path],
            input=config, text=True, capture_output=True, timeout=25)
        raw, code = response.stdout.rsplit("\n", 1)
        if response.returncode or code != "200":
            raise RuntimeError("Salad log request HTTP " + code)
        return json.loads(raw)

    def update_members(self, nodes):
        with self.lock:
            self.members = [node["instance_id"] for node in nodes]

    def snapshots(self):
        now = int(time.time() * 1000)
        latest = self.store.latest(self.group_id)
        with self.lock:
            members = list(self.members)
        result = {}
        for instance in members:
            row = latest.get(instance)
            if not row or not row["valid"]:
                continue
            seconds = (row["end_ms"] - row["start_ms"]) / 1000
            result[instance] = {
                "available": True, "source": "sysfs-minute-via-salad-logs",
                "observer": row["observer"], "time_ms": row["end_ms"], "received_ms": row["received_ms"],
                "ip": row["ip"], "observed_rx_bytes": row["total_rx"], "observed_tx_bytes": row["total_tx"],
                "observed_total_bytes": row["total_rx"] + row["total_tx"],
                "source_age_seconds": (now - row["end_ms"]) / 1000,
                "receipt_age_seconds": (now - row["received_ms"]) / 1000,
                "last_interval_seconds": seconds, "last_delta_bytes": row["rx"] + row["tx"],
                "bytes_per_second": (row["rx"] + row["tx"]) / seconds if seconds > 0 else None,
                "nominal_interval_ms": 60000, "samples": row["seq"] + 1}
        return result

    def poll(self):
        group = self.request("/projects/default/containers/" + self.group)
        if group.get("id") != self.group_id:
            raise RuntimeError("PacketStream deployment identity changed")
        now = datetime.now(timezone.utc)
        saved = self.store.collector_status(self.group_id)
        cursor = provider_datetime(saved["cursor"]) if saved.get("cursor") else now
        start = min(cursor, now) - timedelta(minutes=10)
        calls = 0

        def fetch(begin, end):
            nonlocal calls
            calls += 1
            if calls > 512:
                raise RuntimeError("Minute log catch-up has too many pages")
            body = {
                "query": 'resource.type = "container" and resource.labels.project_name = "default" and '
                         'resource.labels.container_group_name = "' + self.group + '" and text_log startswith "PS_MINUTE_V"',
                "start_time": begin.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "end_time": end.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "page_size": 100, "sort_order": "asc"}
            items = self.request("/log-entries", body).get("items")
            if not isinstance(items, list):
                raise RuntimeError("Invalid Salad log response")
            if len(items) < 100:
                return items
            if end - begin <= timedelta(milliseconds=1):
                raise RuntimeError("Too many minute records share a pagination timestamp")
            middle = begin + (end - begin) / 2
            return fetch(begin, middle) + fetch(middle, end)

        items = fetch(start, now)
        records = [parse_minute(item, self.group_id) for item in items]
        invalid = sum(row is None for row in records)
        inserted = self.store.ingest([row for row in records if row is not None])
        self.store.collector_status(self.group_id, now.isoformat(),
                                    "Invalid minute records: " + str(invalid) if invalid else None, inserted)

    def lookup_countries(self):
        with self.store.lock:
            ips = [r[0] for r in self.store.db.execute(
                "SELECT DISTINCT ip FROM minutes WHERE ip IS NOT NULL AND ip NOT IN (SELECT ip FROM countries) LIMIT 100")]
        if not ips:
            return
        response = subprocess.run(["curl", "-fsS", "--max-time", "8", "-H", "Content-Type: application/json",
                                   "--data-binary", "@-", "https://api.country.is/"],
                                  input=json.dumps(ips), text=True, capture_output=True, timeout=10)
        if response.returncode:
            return
        countries = json.loads(response.stdout)
        with self.store.lock, self.store.db:
            for row in countries:
                country = row.get("country")
                if row.get("ip") in ips and (country is None or re.fullmatch(r"[A-Z]{2}", country)):
                    self.store.db.execute("INSERT OR REPLACE INTO countries VALUES (?,?)", (row["ip"], country))

    def run(self):
        while True:
            began = time.monotonic()
            try:
                self.poll()
                self.lookup_countries()
            except Exception as error:
                saved = self.store.collector_status(self.group_id)
                cursor = saved.get("cursor") or datetime.now(timezone.utc).isoformat()
                message = str(error) if isinstance(error, RuntimeError) else type(error).__name__
                self.store.collector_status(self.group_id, cursor, message)
                print("PS minute recording failed:", message, flush=True)
            time.sleep(max(1, 15 - (time.monotonic() - began)))
~~~~~~

### packetstream-monitor/start-with-recovery.sh

<!-- rebuild-file: packetstream-monitor/start-with-recovery.sh sha256=a1352f21f52114bfdb716894303b29dc2d7cff1f9893950904716c1dd5ee2dbf -->
~~~~~~bash
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
~~~~~~

### ps1-native-recorder.py

<!-- rebuild-file: ps1-native-recorder.py sha256=a950adc2e25afad35a0085c1830ad681e5a4351f31fc46ef3f55134f00c63138 -->
~~~~~~python
#!/usr/bin/env python3
"""Start only the PS1 recorder on macOS, without starting Docker or other apps."""
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
import runpy


def main():
    root = Path.home() / "Library/Application Support/Salad Bandwidth Dashboard"
    target_file = Path.home()/".hg1/packetstream/observer-target.json"
    if target_file.exists():
        target = json.loads(target_file.read_text())
        if target.get("mode") == "native-census":
            os.environ["PS_GROUP"] = target["group"]
            os.environ["PS_EXPECTED_GROUP_ID"] = target["group_id"]
            runpy.run_path(str(root/"packetstream-monitor/native-census.py"), run_name="__main__")
            return
    helper = root / ".runtime/keychain-store"
    key = subprocess.check_output([str(helper), "--read", "--service", "salad-bandwidth-api",
                                   "--account", getpass.getuser()], text=True).strip()
    if not key:
        raise RuntimeError("Salad credential is unavailable")
    config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\n"
    result = subprocess.run(["/usr/bin/curl", "-sS", "--max-time", "20", "--config", "-",
                             "--write-out", "\n%{http_code}",
                             "https://api.salad.com/api/public/organizations/hyperlane/projects/default/containers/ps1"],
                            input=config, text=True, capture_output=True, timeout=25)
    raw, code = result.stdout.rsplit("\n", 1)
    if result.returncode or code != "200":
        raise RuntimeError("PS1 configuration could not be read")
    group = json.loads(raw)
    if group.get("id") != "1c7c9cbd-0cc2-4f10-a1ad-76f56d7492ba":
        raise RuntimeError("PS1 deployment identity changed")
    env = group["container"]["environment_variables"]
    if env.get("CID") != "8ExP" or len(env.get("PS_STREAM_TOKEN", "")) < 32:
        raise RuntimeError("PS1 recorder configuration changed")
    data = Path.home() / ".hg1/packetstream/network"
    data.mkdir(parents=True, exist_ok=True)
    child_env = os.environ.copy()
    child_env.update(SALAD_API_KEY=key, PS_STREAM_TOKEN=env["PS_STREAM_TOKEN"],
                     PS_ORGANIZATION="hyperlane", PS_GROUP="ps1")
    executable = str(root / "ps1-collector")
    print("Starting native PS1 device recorder on 127.0.0.1:8789", flush=True)
    os.execve(executable, [executable, "-data", str(data), "-listen", "127.0.0.1:8789"], child_env)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never emit the provider response or credentials into service logs.
        print("PS1 native recorder could not start:", type(exc).__name__, file=sys.stderr)
        sys.exit(1)
~~~~~~

### scripts/install-services.py

<!-- rebuild-file: scripts/install-services.py sha256=3c75ac6e7c82f8b1e06104d59b02c13b073685e0c5f19a4a25a3e7534a7ee4e9 -->
~~~~~~python
#!/usr/bin/env python3
"""Install only explicitly named local observers; never alter Salad workloads."""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess
root=Path(__file__).resolve().parents[1];data=Path.home()/'.hg1';agents=Path.home()/'Library/LaunchAgents'
jobs={
 'dashboard':('com.cosmosgeek.salad-bandwidth-dashboard',['-m','dashboard.server','--port','8787','--data-dir',str(data),'--no-poll'],'dashboard'),
 'hg-provider':('com.cosmosgeek.salad-hg-provider-observer',[str(root/'scripts/hg-provider-observer.py'),'--interval','60'],'hg-fleet/provider-observer'),
 'hg-fleet':('com.cosmosgeek.salad-hg-fleet-observer',[str(root/'scripts/hg-fleet-observer.py'),'--interval','60'],'hg-fleet/observer'),
 'fleet':('com.cosmosgeek.salad-fleet-test-recorder',[str(root/'fleet-test-recorder.py'),'run'],'fleet-tests/recorder'),
 'ps':('com.cosmosgeek.ps1-recorder',['-B',str(root/'ps1-native-recorder.py')],'packetstream/native-recorder'),
 'pr':('com.cosmosgeek.proxyrack-recorder',['-B',str(root/'proxyrack.py'),'observe'],'proxyrack/observer'),
 'rp':('com.cosmosgeek.repocket-recorder',['-B',str(root/'repocket-monitor/observe.py')],'repocket/observer'),
 'rfm':('com.cosmosgeek.earnfm-recorder',['-B',str(root/'scripts/earnfm-recorder.py')],'earnfm/recorder'),
 'tm':('com.cosmosgeek.tm-observer',['-B',str(root/'traffmonetizer/observer.py')],'traffmonetizer/observer')}
p=argparse.ArgumentParser(description=__doc__);p.add_argument('services',nargs='+',choices=jobs);p.add_argument('--write-only',action='store_true');args=p.parse_args()
env=dict(PYTHONPATH=str(root),PYTHONDONTWRITEBYTECODE='1',HG_FLEET_DIR=str(data/'hg-fleet'),HG_KEYCHAIN_HELPER=str(root/'.runtime/keychain-store'),PS_ORGANIZATION='hyperlane',PS_PROJECT='default',PS_GROUP='ps-test-us')
os.umask(0o077);agents.mkdir(parents=True,exist_ok=True)
for name in args.services:
 label,arguments,logs=jobs[name]
 for value in arguments:
  if value.endswith('.py') and not Path(value).exists():raise SystemExit('Missing embedded source: '+value)
 (data/logs).parent.mkdir(parents=True,exist_ok=True)
 document=dict(Label=label,ProgramArguments=['/usr/bin/python3',*arguments],WorkingDirectory=str(root),EnvironmentVariables=env,
     KeepAlive=True,RunAtLoad=True,ThrottleInterval=15,StandardOutPath=str(data/(logs+'.out.log')),StandardErrorPath=str(data/(logs+'.err.log')))
 path=agents/(label+'.plist');path.write_bytes(plistlib.dumps(document));path.chmod(0o600)
 if not args.write_only:
  domain='gui/'+str(os.getuid())
  subprocess.run(['launchctl','bootout',domain+'/'+label],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  subprocess.run(['launchctl','bootstrap',domain,str(path)],check=True)
 print(('Wrote ' if args.write_only else 'Started ')+label)
~~~~~~

### scripts/keychain-store.swift

<!-- rebuild-file: scripts/keychain-store.swift sha256=490eadaf1afb87a0f64bf6248254ccc48ac1171af9e2fc4c796c74c12c5ca045 -->
~~~~~~swift
import Foundation
import Security

func fail(_ message: String, code: Int32 = 2) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(code)
}

func option(_ name: String) -> String? {
    let arguments = CommandLine.arguments
    guard let index = arguments.firstIndex(of: name), index + 1 < arguments.count else {
        return nil
    }
    return arguments[index + 1]
}

guard let service = option("--service"), !service.isEmpty else {
    fail("missing --service")
}
guard let account = option("--account"), !account.isEmpty else {
    fail("missing --account")
}

let query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrService as String: service,
    kSecAttrAccount as String: account,
]

let wantsRead = CommandLine.arguments.contains("--read")
let wantsDelete = CommandLine.arguments.contains("--delete")
guard !(wantsRead && wantsDelete) else {
    fail("choose only one operation")
}

if wantsRead {
    var readQuery = query
    readQuery[kSecReturnData as String] = true
    readQuery[kSecMatchLimit as String] = kSecMatchLimitOne
    var result: CFTypeRef?
    let status = SecItemCopyMatching(readQuery as CFDictionary, &result)
    guard status == errSecSuccess, let password = result as? Data else {
        let explanation = SecCopyErrorMessageString(status, nil) as String? ?? "unknown error"
        fail("keychain error \(status): \(explanation)", code: 1)
    }
    FileHandle.standardOutput.write(password)
    exit(0)
}

if wantsDelete {
    let status = SecItemDelete(query as CFDictionary)
    guard status == errSecSuccess || status == errSecItemNotFound else {
        let explanation = SecCopyErrorMessageString(status, nil) as String? ?? "unknown error"
        fail("keychain error \(status): \(explanation)", code: 1)
    }
    exit(0)
}

var password = FileHandle.standardInput.readDataToEndOfFile()
while password.last == 10 || password.last == 13 {
    password.removeLast()
}
guard !password.isEmpty else {
    fail("empty password data")
}

let update: [String: Any] = [
    kSecValueData as String: password,
]

var status = SecItemUpdate(query as CFDictionary, update as CFDictionary)
if status == errSecItemNotFound {
    var item = query
    item[kSecValueData as String] = password
    status = SecItemAdd(item as CFDictionary, nil)
}

guard status == errSecSuccess else {
    let explanation = SecCopyErrorMessageString(status, nil) as String? ?? "unknown error"
    fail("keychain error \(status): \(explanation)", code: 1)
}
~~~~~~

### scripts/rebuild-cloud.py

<!-- rebuild-file: scripts/rebuild-cloud.py sha256=4fde37bb6ea6402a3ab1ce7fe46d935503ee7b6038af0f3c2ec48c0c401c08b9 -->
~~~~~~python
#!/usr/bin/env python3
"""Recreate only the documented Honeygain or PacketStream deployment."""
import argparse
import base64
import getpass
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / '.hg1'
PS_IMAGE = 'docker.io/packetstream/psclient@sha256:6e6a2cefe9f49c33f6c9d4bd41d21daf20c4767f2c66e82f57a5960ec9923987'

def api(key, org, path, method='GET', body=None):
    config = 'header = '+json.dumps('Salad-Api-Key: '+key)+'\nheader = "Content-Type: application/json"\n'
    if body is not None:
        config += 'data-binary = '+json.dumps(json.dumps(body))+'\n'
    result = subprocess.run(['curl','-sS','--max-time','30','--config','-','--request',method,'--write-out','\n%{http_code}',
        'https://api.salad.com/api/public/organizations/'+org+path],input=config,text=True,capture_output=True,timeout=35)
    if result.returncode:
        raise RuntimeError('Salad transport failed')
    raw, code = result.stdout.rsplit('\n',1)
    if not 200 <= int(code) < 300:
        raise RuntimeError(f'Salad {method} {org}{path}: HTTP {code}')
    return json.loads(raw) if raw.strip() else {}

def specifications(protocol, secrets):
    if protocol == 'honeygain':
        spec=importlib.util.spec_from_file_location('hg_control',ROOT/'scripts/hg-fleet-control.py')
        hg=importlib.util.module_from_spec(spec);spec.loader.exec_module(hg)
        return 'deathadder', [dict(name=group,display_name='HG1 Native 0.6.6' if i==0 else 'HG Solo %02d'%(i+1),replicas=1,
            country_codes=['us'],restart_policy='always',autostart_policy=False,
            container=dict(image=hg.IMAGE,command=hg.recovery_command(),image_caching=True,priority='batch' if i==0 else 'low',
                resources=dict(cpu=1,memory=1024,shm_size=64,gpu_classes=[]),
                environment_variables=dict(HONEYGAIN_EMAIL=secrets['email'],HONEYGAIN_PASSWORD=secrets['password'],HONEYGAIN_DEVICE_NAME=hg.DEVICES[i])))
            for i,group in enumerate(hg.GROUPS)]
    code=(ROOT/'packetstream-monitor/start-with-recovery.sh').read_bytes()
    encoded=base64.b64encode(code).decode()
    command=['/bin/bash','-c','umask 077; printf "%s" "$@" | base64 -d > /tmp/ps-self-recovery.sh; exec /bin/bash /tmp/ps-self-recovery.sh',
             'policy-start',*[encoded[i:i+900] for i in range(0,len(encoded),900)]]
    assert len(command)<=100 and max(map(len,command))<=1000
    return 'hyperlane', [dict(name='ps-test-us',display_name='PS Test US',replicas=10,country_codes=['us'],
        restart_policy='always',autostart_policy=False,container=dict(image=PS_IMAGE,command=command,image_caching=True,priority='batch',
            resources=dict(cpu=1,memory=1024,shm_size=64,gpu_classes=[]),environment_variables=dict(CID=secrets['cid'])))]

def verify(actual, desired, compare_account):
    container=actual.get('container',{});expected=desired['container']
    different=[k for k in ('name','display_name','replicas','country_codes','restart_policy','autostart_policy') if actual.get(k)!=desired[k]]
    different += ['container.'+k for k in ('image','command','image_caching') if container.get(k)!=expected[k]]
    different += ['resources.'+k for k,v in expected['resources'].items() if container.get('resources',{}).get(k)!=v]
    if actual.get('priority')!=expected['priority']:different.append('priority')
    different += [k for k in ('networking','readiness_probe','liveness_probe','startup_probe') if actual.get(k) or container.get(k)]
    environment=container.get('environment_variables',{});wanted=expected['environment_variables']
    if set(environment)!=set(wanted) or not all(isinstance(v,str) and v for v in environment.values()):
        different.append('required account environment')
    elif compare_account and environment!=wanted:
        different.append('account environment')
    elif 'HONEYGAIN_DEVICE_NAME' in wanted and environment['HONEYGAIN_DEVICE_NAME']!=wanted['HONEYGAIN_DEVICE_NAME']:
        different.append('Honeygain registration')
    if different:
        raise RuntimeError('Deployment differs in '+', '.join(different)+': '+desired['name']+'; inspect it instead of overwriting it')

def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.chmod(0o600);temporary.replace(path)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('protocol',choices=['honeygain','packetstream'])
    p.add_argument('action',choices=['plan','create','bind'])
    args=p.parse_args();os.umask(0o077)
    values=dict(email='<HONEYGAIN_EMAIL>',password='<HONEYGAIN_PASSWORD>',cid='<PACKETSTREAM_CID>')
    if args.action=='create':
        if args.protocol=='honeygain':
            values.update(email=input('Honeygain account email: ').strip(),password=getpass.getpass('Honeygain password: '))
        else:
            values['cid']=getpass.getpass('PacketStream CID from your account: ').strip()
        if any(not value for value in values.values()):raise ValueError('An account value is empty')
    org, specs=specifications(args.protocol,values)
    if args.action=='plan':
        for item in specs:
            print(json.dumps({k:item[k] for k in ('name','replicas','country_codes','restart_policy','autostart_policy')},sort_keys=True))
        print('Offline plan only; no account access, files, or cloud changes.')
        return
    helper=ROOT/'.runtime/keychain-store'
    key=subprocess.check_output([str(helper),'--read','--service','salad-bandwidth-api','--account',getpass.getuser()],text=True).strip()
    existing={g['name']:g for g in api(key,org,'/projects/default/containers').get('items',[])}
    if args.protocol=='honeygain' and args.action=='create':
        registrations={g['container']['environment_variables']['HONEYGAIN_DEVICE_NAME'] for g in specs}
        intended={g['name'] for g in specs}
        for other_org in ('deathadder','cosmosgeeketh','hyperlane'):
            for group in api(key,other_org,'/projects/default/containers').get('items',[]):
                device=group.get('container',{}).get('environment_variables',{}).get('HONEYGAIN_DEVICE_NAME')
                if device in registrations and not (other_org==org and group['name'] in intended):
                    if api(key,other_org,'/projects/default/containers/'+group['name']+'/instances').get('instances'):
                        raise RuntimeError('A Honeygain registration is already running in '+other_org+'/'+group['name'])
    receipts=[]
    for desired in specs:
        name=desired['name'];path='/projects/default/containers/'+name
        if name in existing:
            actual=api(key,org,path)
        elif args.action=='bind':
            raise RuntimeError('Cannot bind a missing group: '+name)
        else:
            try:
                actual=api(key,org,'/projects/default/containers','POST',desired)
            except RuntimeError:
                # A rejected response can follow an applied creation. Read back once; never duplicate.
                actual=api(key,org,path)
        verify(actual,desired,args.action=='create')
        if args.action=='create':
            for _ in range(60):
                actual=api(key,org,path);state=actual.get('current_state',{}).get('status')
                if state=='stopped':
                    api(key,org,path+'/start','POST');break
                if state in ('running','deploying','starting'):break
                time.sleep(5)
            else:raise RuntimeError('Group did not become startable within five minutes: '+name)
        receipts.append(dict(organization=org,group=name,id=actual['id'],replicas=desired['replicas'],image=actual['container']['image'],version=actual['version']))
    if args.protocol=='packetstream':
        receipt=receipts[0]
        write(DATA/'packetstream/observer-target.json',dict(mode='native-census',organization=org,project='default',group=receipt['group'],group_id=receipt['id']))
    else:
        write(DATA/'hg-fleet/deployment.json',receipts)
    print(json.dumps(receipts,indent=2))
    print('Binding saved. Verify native logs/client acceptance before claiming the fleet is working.')

if __name__=='__main__':main()
~~~~~~

### scripts/save-secret.py

<!-- rebuild-file: scripts/save-secret.py sha256=98e37bb083dd0c10773d1dfdc187780af29f7a62beb361cfc99ec0fc92822e9e -->
~~~~~~python
#!/usr/bin/env python3
"""Save an operator-supplied value to the existing macOS Keychain helper."""
import argparse
import getpass
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__);p.add_argument('service');args=p.parse_args()
helper=Path(__file__).resolve().parents[1]/'.runtime/keychain-store'
secret=getpass.getpass('Value for '+args.service+' (hidden): ')
if not secret:raise SystemExit('Empty secret not saved')
subprocess.run([str(helper),'--service',args.service,'--account',getpass.getuser()],input=secret,text=True,check=True)
print('Saved '+args.service+'; value not printed.')
~~~~~~
