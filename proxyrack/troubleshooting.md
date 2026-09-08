# PR recovery and troubleshooting

[Start here](README.md) · [Setup](setup.md) · [Deployment](deployment.md) · [Recording](monitoring.md)

## In-container policy

The official native client is supervised by `pr-worker.js`. Its checks are asynchronous, so provider calls do not block process/connection monitoring.

| Condition | Action |
|---|---|
| Native download/version/startup fails | Record the error; request IMDS reallocation after bounded download attempts |
| Native child exits | Record final measurements and request reallocation |
| Initial/reconnecting home connection does not complete | Request reallocation after the configured 60-second threshold |
| Native process remains stopped/traced or blocked in OS state T/t/D | Request reallocation after the configured 60-second threshold |
| Non-account registration failure persists | Retry with backoff; a configured 15-minute deadline bounds that attempt |
| Account quota or authentication failure | Show the cause and retry with cooldown; do not replace the node to repair an account problem |
| Provider reports the device offline in repeated status checks | Reallocate after offline observations spanning at least 10 minutes |
| Healthy connected but idle, low traffic, unchanged/missing provider counter | Keep running and record observations; no byte floor or earnings replacement timer |
| Operator TERM/INT | Stop the native child, emit the final record and exit cleanly without reallocation |

Replacement time also depends on Salad scheduling. A frozen host cannot run its own supervisor; platform recovery remains necessary. Individual destination connection errors do not establish that the whole peer is broken. They remain visible with source times rather than being silently relabeled healthy or blindly causing repeated replacement.

IMDS requests go to `http://169.254.169.254/v1/reallocate`, with `Metadata: true` and a JSON reason. HTTP 200/204 are accepted. Up to three bounded attempts are recorded, followed by exit 75 as the platform fallback. The worker never needs a Salad account key.

Registration initially waits 60–180 seconds, then backs off with jitter. A DNS resolver failure retries through HTTPS DNS with TLS verification enabled. Already-owned IDs are checked before acceptance. Provider status and bandwidth alternate at approximately five-minute intervals per worker; the account/retired-device reader makes at most one request per 90 seconds. This is pacing with retry/cooldown, not a guarantee that independently starting replicas can never encounter an account rate limit.

## Known failure remedies

| Symptom | Diagnosis/action |
|---|---|
| Old `go1.monetizemyapp.net:80` refusal | The vendor Node launcher’s log uploader produced this failure. The current worker keeps the official native client and its connection arguments, without that uploader. |
| Native `dial tcp … i/o timeout` | Inspect the actual source error and connection state. A failed requested destination is not proof of a failed whole node. |
| Missing/stale status | Check recorder/source times and log collection errors. Unknown is not zero and does not justify discarding history. |
| Registration/API quota error | Keep the account-level cooldown. More concurrent polling or machine churn does not create quota. |
| Invalid API key/authorization | Restore the correct credential through the existing secret store and the scoped key synchronization procedure in deployment.md. Node replacement cannot repair it. |
| Record page reaches its cap | Keep recursive time splitting; do not advance from a truncated slice. |
| Reset or replacement produces a spike | Keep independent run baselines and instance/machine/run scoping. Never difference across the boundary. |
| Provider unit unclear | Keep the original numeric counter and observation time. The public payout rate does not establish the API field’s unit. |
| Public page differs from local source | Check the actual installed PR source and shared integration hashes; editing Desktop does not deploy. |

## Stop the paid group deliberately

Use [Salad PR](https://portal.salad.com/organizations/ssh1/projects/default/containers/pr), or the scoped command below from an installed runtime. Stopping a recorder does not stop paid Salad instances.

```bash
python3 -B - <<'PY_STOP'
import proxyrack as pr
api = pr.salad_api()
group = api(pr.GROUPS + '/pr')
if group['id'] != pr.configuration()['group_id']:
    raise SystemExit('Group identity changed; no stop requested')
api(pr.GROUPS + '/pr/stop', 'POST')
print('PR stop requested; verify stopped in Salad')
PY_STOP
```

## Back up history

Use SQLite’s online backup API while the writer runs. Copy the cursor **before** the database backup so it cannot point beyond the copied data. Keep the source folder and credentials separately.

```bash
python3 -B - <<'PY_BACKUP'
from pathlib import Path
from datetime import datetime, timezone
import os, shutil, sqlite3
import proxyrack as pr
os.umask(0o077)
backup = Path.home() / 'Desktop/salad/proxyrack/backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup.mkdir(parents=True)
for name in ('deployment.json', 'cursor.json', 'provider.json'):
    if (pr.DATA / name).exists():
        shutil.copy2(pr.DATA / name, backup / name)
with sqlite3.connect('file:' + str(pr.DATA / 'traffic.sqlite3') + '?mode=ro', uri=True) as source:
    with sqlite3.connect(backup / 'traffic.sqlite3') as target:
        source.backup(target)
print(backup)
PY_BACKUP
```

Restore a consistent set with the writer stopped, verify group identity and restart only the owner recorder. Do not relabel old data with a new group ID, detach old provider devices merely for tidiness, or reset an experiment to repair the page.

Primary references: [Salad IMDS](https://docs.salad.com/reference/imds/reallocate), [vendor image](https://hub.docker.com/r/proxyrack/pop), [Peer API reference](https://peer.proxyrack.com/api-doc), [provider payout explanation](https://help.proxyrack.com/en/articles/9722403-what-is-the-payout-rate-for-the-peer-program). Source/setup recreation does not guarantee future traffic or profit.
