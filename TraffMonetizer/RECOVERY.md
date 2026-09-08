# Recovery, troubleshooting and backups

## Automatic replacement policy

Each Salad replica runs one official TM client and the Python worker. The worker reads the client, samples `eth0` RX/TX once per second, and sends ten-sample batches to stdout with the `TM_V1 ` prefix. It asks the client for `status` and `statistics` every ten seconds and also reads asynchronous connection events.

The [worker source](source/traffmonetizer/worker.py) applies these rules inside each Salad container:

1. A client exit requests replacement immediately.
2. Unavailable connection time accumulates across short reconnects. At 30 seconds it requests replacement. Only 60 uninterrupted healthy seconds clear that failure budget.
3. Status replies and numeric statistics replies have separate 60-second deadlines. One responding command cannot hide the other being stuck. These deadlines use the monotonic clock.
4. A connected, accepting client stays on its machine even when native relay payload is zero or unchanged. `TM_IDLE_SECONDS` is obsolete and ignored. Telemetry publishes `reallocate_on_idle:false`; payload idle time is an observation only.
5. IMDS replacement uses `POST http://169.254.169.254/v1/reallocate`, `Metadata: true`, and a reason. There are at most three attempts, each with a ten-second timeout, with two- and four-second retry delays. Every result is recorded, then the worker exits 75; no local client restart loop is used.
6. Operator stop emits a final stopped sample and does not deliberately request replacement. A replacement decision emits a final reallocating sample.

The recorder stores request acceptance separately from subsequent retirement and full-fleet confirmation. A saved `fleet_confirmed_ms` is a historical confirmation, not a claim that every worker stays healthy afterward. If the host itself is offline, Salad’s platform must detect it; an offline process cannot contact IMDS. The Mac is not needed for any worker decision.

## Logs and manual recovery

In Salad, open the group → Container Logs. Filter using `TM_V1 ` or a machine ID. Relevant events are `start`, `client_start`, `batch`, `client_log`, `client_error`, `configuration_error`, `reallocate`, `reallocate_result`, and `stopped`. Historical older worker logs can also contain `retry`; the current worker does not perform that local retry.

Useful vendor strings include:

```text
Connected: [any ip] - true; Accepting: true
Status: [any ip] - disconnected
Status: [any ip] - connecting
Status: [any ip] - connected
Inbound: ...; Outgoing: ...; Requests: ...
```

| Observation | Meaning and next step |
|---|---|
| `TM_TOKEN is missing` | Restore the worker application token environment variable |
| Provider HTTP 401/403 | Refresh the Keychain dashboard session; inspect application-token errors separately |
| Salad log API HTTP 408 | Recorder request timed out; its next cycle retries with overlap. Do not infer every client died |
| Image update pending | Wait for actual instances to show the applied version; group version alone is insufficient |
| Old logs, running badge, unreachable terminal | Investigate host/network state and Salad System Events; running metadata can lag |
| `Instance Interrupted (Node Offline)` | Salad host disappeared; platform replacement is separate from application IMDS recovery |
| `reallocate_result accepted:true` | Request accepted; verify a new instance/machine actually becomes healthy |
| Connected but native bytes unchanged | Keep the client running; no-payload age is not a failure or replacement trigger |
| Increasing RX/TX but flat credits | Check native counters and delayed provider updates; raw overhead is not paid payload |

A recorded node clock was about **220 seconds ahead** of receipt time. Schema 2 stores both the original source clock and Salad receipt time and requires both to be recent before confirming a client. It does not rewrite historical clocks. Old rows without receipts remain unknown until actual retained logs provide those receipts; never fabricate a receipt timestamp from the time a backfill was run.

The wrapper parses status/statistics and forwards the remaining nonempty vendor lines with the application token redacted. It records native connection changes immediately. The vendor does not expose a guaranteed per-request success/error API; absence of a logged error is not proof that every target request succeeded.

Manual self-reallocation from the affected container's Salad terminal requires no Salad API key:

```bash
python3 - <<'PY_REALLOCATE'
import json,urllib.request
request=urllib.request.Request("http://169.254.169.254/v1/reallocate",
    data=json.dumps({"reason":"Operator verified persistent connection failure"}).encode(),
    headers={"Metadata":"true","Content-Type":"application/json"},method="POST")
with urllib.request.urlopen(request,timeout=10) as response:
    print("Reallocation request HTTP",response.status)
PY_REALLOCATE
```

If the host is unreachable, use the instance's **Reallocate** button in Salad. Check its ID again first because the platform may already have replaced it. Do not repeatedly rotate all ten: a quiet worker in one measured window later became the largest contributor without any change. Neither this policy nor US placement guarantees high demand or profitable traffic.

To stop the cloud test and its compute charges, use Salad's group **Stop** action, or from the recovery directory:

```bash
python3 - <<'PY_STOP'
import sys
sys.path.insert(0,"traffmonetizer")
from control import api,GROUP_PATH
api(GROUP_PATH+"/stop","POST")
print("Cloud group stop requested; verify stopped state in Salad")
PY_STOP
```

Closing the local dashboard, stopping launchd, or deleting local files does **not** stop cloud workers or billing.

## Runtime locations and data backup

| Component | Location |
|---|---|
| Editable TM source | `~/Desktop/salad/TraffMonetizer/source/traffmonetizer/` |
| Retired Mac recorder (disabled) | `/Users/cosmosgeek/Library/Application Support/Salad Bandwidth Dashboard/traffmonetizer/` |
| Keychain helper source | [source/scripts/keychain-store.swift](source/scripts/keychain-store.swift) |
| Worker/deployment/account history | `~/.hg1/traffmonetizer/traffic.sqlite3` |
| Identity and monetary baseline | `~/.hg1/traffmonetizer/deployment.json` |
| Current derived view | `~/.hg1/traffmonetizer/latest.json` |
| Recorder logs and lock | `~/.hg1/traffmonetizer/observer.*` |
| Original observer LaunchAgent | `~/Library/LaunchAgents/com.cosmosgeek.tm-observer.plist` |
| Shared production dashboard | `https://salad.cosmosgeek.org/#tm` |
| AWS recorder / state | `/opt/salad/traffmonetizer` / `/home/salad/.hg1/traffmonetizer` |
| AWS recorder unit | `salad-traffmonetizer.service` |

Back up SQLite with its backup API or while the observer is stopped; copying only a live `.sqlite3` file can omit its WAL data. A consistent backup command, when the original database still exists:

```bash
python3 - <<'PY_BACKUP'
from pathlib import Path
import sqlite3,shutil
source=Path.home()/".hg1/traffmonetizer"
target=Path.home()/"Desktop/salad/TraffMonetizer/backups/tm-data"
target.mkdir(parents=True,exist_ok=False)
with sqlite3.connect("file:"+str(source/"traffic.sqlite3")+"?mode=ro",uri=True) as src:
    with sqlite3.connect(target/"traffic.sqlite3") as dst:
        src.backup(dst)
shutil.copy2(source/"deployment.json",target/"deployment.json")
print("Copy this folder to separate storage:",target)
PY_BACKUP
```

The historical ten-worker baseline on the original Mac was 7 September 2026 02:50:03 IST (`1788729603014` milliseconds), balance `$0.0269`, traffic `129348` bytes, and reported earning `$0`. These values are historical facts only: **do not paste them into a new deployment baseline.**
