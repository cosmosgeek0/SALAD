# Monitoring and earnings

Production recording is on AWS Mumbai under `/opt/salad`, with `/home/salad/.hg1/traffmonetizer` and `salad-traffmonetizer.service`. The commands below restore a Mac installation; do not enable it alongside the production recorder. Shared hosting/security ownership is described in [Website operations](../Website/OPERATIONS.md).

Run these commands from `~/Library/Application Support/TraffMonetizer Recovery/` after [DEPLOYMENT.md](DEPLOYMENT.md).

## Start the recorder and TM page

If a backup of `deployment.json` **and** `traffic.sqlite3` survived, restore them together under `~/.hg1/traffmonetizer/` and skip fresh-baseline creation. Preserve the matching group identity and baseline. If only one survives, use a separate archived copy and start a clearly new observation window rather than silently combining unrelated histories.

Run one foreground health-collection cycle first (provider refresh and historical catch-up start with the continuous service):

```bash
python3 -B traffmonetizer/observer.py --once
```

Expected output is a compact JSON line with `running`, `working`, `samples`, and `errors`. Allocation/startup is asynchronous: early counts may be below ten. `running=10` alone does not establish ten connected or earning clients. If `BlockingIOError` occurs, another observer owns the singleton lock; do not start a duplicate.

For a foreground smoke check, run these in two terminal windows in the recovery directory:

```bash
python3 -B traffmonetizer/observer.py
```

```bash
python3 -B recovery-server.py
```

Open <http://127.0.0.1:8787/>. The included page is a **TM-only recovery view**, with the last hour of minute bars, current workers, raw RX/TX totals, provider credits/earnings, and recovery events. It does not recreate the other protocols or their shared 6/12/24-hour UI. The full second-level TM history remains in SQLite for later integration.

The recovery server reads local snapshots and binds only to `127.0.0.1`; it never receives account credentials. The cloud workers keep running if the local page or the Mac stops. The recorder needs an online, awake host to collect new observations and refresh account metrics.

After the foreground check, stop those two terminal processes with Ctrl-C before installing background services. Run the following only on the clean recovery Mac. It refuses to replace an existing LaunchAgent and refuses an occupied port 8787:

```bash
python3 - <<'PY_SERVICES'
from pathlib import Path
import os,plistlib,socket,subprocess,sys
root=Path.cwd().resolve()
assert (root/"recovery-server.py").exists()
data=Path.home()/".hg1/traffmonetizer"
assert (data/"deployment.json").exists()
with socket.socket() as sock:
    sock.bind(("127.0.0.1",8787))
folder=Path.home()/"Library/LaunchAgents"
folder.mkdir(parents=True,exist_ok=True)
jobs=[
 ("com.cosmosgeek.tm-observer",[sys.executable,"-B",str(root/"traffmonetizer/observer.py")],"observer"),
 ("com.cosmosgeek.tm-recovery-dashboard",[sys.executable,"-B",str(root/"recovery-server.py")],"recovery-dashboard"),
]
assert all(not (folder/(label+".plist")).exists() for label,_,_ in jobs), "Existing service: inspect it instead of overwriting"
for label,args,log in jobs:
    path=folder/(label+".plist")
    config={"Label":label,"ProgramArguments":args,"WorkingDirectory":str(root),
        "RunAtLoad":True,"KeepAlive":True,"ThrottleInterval":15,
        "StandardOutPath":str(data/(log+".out.log")),
        "StandardErrorPath":str(data/(log+".err.log"))}
    path.write_bytes(plistlib.dumps(config))
    subprocess.run(["launchctl","bootstrap",f"gui/{os.getuid()}",str(path)],check=True)
    print("Installed",label)
PY_SERVICES
```

LaunchAgents run after the user logs in; they do not run while the Mac is off/asleep. A launchd restart is `launchctl kickstart -k gui/$(id -u)/com.cosmosgeek.tm-observer`. This restarts the **recorder**, not any Salad worker.

## Verify status and understand the numbers

Read only the safe deployment summary; never print the full container environment:

```bash
python3 -B traffmonetizer/control.py status
curl --fail --silent http://127.0.0.1:8787/api/traffmonetizer
```

The API output contains many samples but no credential values. Inspect `errors`, `stale`, each worker's `sample_age_ms`, `state`, `salad_state`, `native_recent_bytes`, `native_recent_requests`, and `native_recent_ms`.

| Value | Meaning |
|---|---|
| Salad running count | Container process allocation/state, not proof of usable TM traffic |
| Connected/accepting | Fresh client connection state; an idle client can be connected |
| Raw RX + TX | Real interface traffic, including both forwarding directions, startup/control traffic and overhead |
| Native relay bytes/requests | Counters reported by the official client; useful contribution evidence, not per-device credited earnings |
| Provider credited bytes | Account API traffic less the saved test baseline |
| Provider earned USD | Provider-reported earnings less the saved earnings baseline; gross, before Salad cost |
| Account balance / balance change | Separately updated account figure; not interchangeable with reported earnings |

The recorder uses decimal **MB = 1,000,000 bytes**. TM's own site has displayed binary MiB as “MB”; compare raw byte integers before calling a discrepancy. A newly allocated worker was observed to transfer about 2.25 MB of raw startup/control traffic before reporting any native payload. Raw network volume is never an earnings estimate.

Recorded minute bars assign each measured interval's bytes to its ending minute. The observer publishes `chart_minutes` for the last 24 hours once per minute and retains second-level rows in SQLite. The public page offers 1/6/12/24-hour views; the standalone recovery page displays the last hour. `chart_generated_ms` records chart freshness separately from current worker/inventory readings. Native contribution windows use same-client counter differences across up to fifteen minutes. The corrected minute rate is a measured approximately 60-second average, not a single second multiplied by sixty.

Provider account readings cover all traffic on that account. Use a dedicated account or account for other devices before attributing the whole account's earnings to this fleet. Preserve measurement baselines across ordinary restarts and image updates.

For faults, backups or stopping charges, use [RECOVERY.md](RECOVERY.md).

## Recording integrity

The schema migration adds `received_ms`, `log_ms`, reply ages and policy metadata while preserving every old sample and the original baseline. Missing historical receipts stay null. The source timestamp, interval start/end, monotonic duration, instance, machine and wrapper-run identity remain intact.

Foreground collection reads the newest 45 seconds of logs first, prioritizes the newest complete windows, and narrows dense windows. Current log requests allow up to ten seconds each within a twenty-second collection budget. Provider refresh and historical collection use a separate maintenance thread and SQLite connection, so they cannot delay current-health publication. Capped log pages are split into smaller time windows. Historical catch-up and ten-minute late-log reconciliation advance through saved one-minute slices, with at most three requests per cycle and smaller slices when a dense page exhausts that budget. Only complete windows advance the saved cursor; a later failure resumes after the completed portion. Current health can remain verified while a separate history warning reports an older collection problem. Cursor updates are monotonic across both connections, and a published view reads one consistent SQLite snapshot. A stopped/slow provider feed retains its last observation with a stale label. Identical samples deduplicate; conflicting values under the same run/sequence are reported with their instance and leave the original untouched. Invalid batches roll back rather than publishing half a batch.

The public API recomputes sample, receipt, inventory and provider freshness when read. Stale evidence is unverified, not an invented zero. Row notes show native payload progress and the automatic policy. Recovery details distinguish the request, its HTTP result and the time a full healthy fleet was observed after the old instance left.
