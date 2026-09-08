# Verification and evidence

## Check this package

From the package root:

```bash
shasum -a 256 -c SHA256SUMS
python3 -B restore-control.py plan > deployment-plan.json
```

The checksum manifest covers the included source and guides. The deployment plan contains placeholders, not credentials. Read [Deployment](DEPLOYMENT.md) before any account operation. The original source was extracted from the recovery document, then the worker, recorder and RP page were repaired in their actual source files. The historical section below verifies that older edition only; current checks are recorded separately.

- For a group matching this edition's US recipe, `restore-control.py inspect` must show the correct image/source, ten requested replicas and eventually ten running. Check the live Salad page if allocation is delayed.
- `http://127.0.0.1:8787/api/repocket` must return a recent `generated_ms`, `error: null`, current workers and `workers[].policy`. A running container is not necessarily a connected client.
- Each worker should get a public IP, a `docker-…` device hash, diagnostic snapshots and target traffic. `phase: connected` proves the **control link**, not that every request succeeded or earned money.
- After the initial window, `policy.state` becomes `keeping` or the worker emits `kind: recovery`. A replacement should show a new machine/instance/run and a new observation window. Inspect the reason and HTTP status; reallocation acknowledgement and completed startup are separate facts.
- Network and target counters should change over saved intervals. A short quiet interval does not itself prove failure. Error counts are diagnostic evidence; they are not the current low-traffic replacement trigger.

Read-only status check: run on AWS as the `salad` service user for production, or locally only for a restored local recorder:

```bash
python3 - <<'PY_STATUS'
from pathlib import Path
import json,time
v=json.loads((Path.home()/'.hg1/repocket/view.json').read_text())
print('Recorder age seconds:',round((time.time()*1000-v['generated_ms'])/1000,1),'error:',v.get('error'))
print('Running:',v.get('running'),'control-connected:',v.get('connected'))
for w in v.get('workers',[]):
    p=w.get('policy') or {}
    print(w.get('ip'),w.get('status'),p.get('state'),'window MB:',p.get('target_bytes',0)/1e6)
for event in v.get('recent_recovery',[]):
    print('Replacement:',event.get('ip'),event.get('http_status'),event.get('reason'))
PY_STATUS
```

## Current reliability repair — 2026-09-07

Worker source 11 is deployed with SHA-256 `1b374c1b092b03b8f2e96398da1220ec03ae0c70f5fd7ee0755b42209a0b54d4`. Recorder SHA-256 is `cb24e602913381a3cdb2dacf79bbfb3891ec33f97000954cf01a323072e92274`.

- **Live at 15:01:07 UTC:** 10 running / 10 native control-connected; view age 25 seconds, inventory age 31 seconds, collector error null. 52,662 records, zero invalid records. View and SQLite both reported **16,396.256878 MB** of interface RX + TX. This is recorded network use, not sold traffic or payment.
- **Self-reallocation:** source-11 worker `67.218.106.119` requested replacement at 14:50:48 UTC for 615,976 target bytes in 600 seconds, below the configured 1 MB floor. Attempt 1 returned HTTP 200. The inventory recorder subsequently confirmed the old machine had left. This event proves automatic request/acceptance/removal; it does not assign a particular later host to that request.
- **Rebuild HTTP check:** the standalone viewer served all four bundled assets byte-identically and returned the recorder's prepared chart/provider fields. A deliberately unreadable test database proved that the prepared-chart route did not fall back to a history scan. Reconstruction into an empty directory verified all 26 manifest files, decoded the exact cloud worker and passed the saved regression checks.
- **History/performance:** an online SQLite backup of 50,799 old records migrated without changing its 14,996.710288 MB total or inventing receipt times. The final recorder snapshot took 205 ms on the existing AWS host with its CPU setting unchanged, against 52,662 records. Earlier pre-repair code took 502 ms on 51,275 records. The once-per-poll chart avoids repeating this work for each browser refresh.
- **Failure checks:** worker fixtures passed bounded three-attempt metadata retries, HTTP 204 acceptance, buffered credential rejection, sequenced group identity and invalid counter intervals. The pinned native SDK passed intercepted-socket checks for relay handshake, authentication rejection and obsolete-socket isolation. Metadata/network calls were intercepted in these tests; they did not reallocate paid hosts.
- **Hosted page:** all 1/6/12/24-hour controls changed the chart and period total. The minute popup returned the contributing IP, United Kingdom and measured MB. The page showed current provider values as **Not reported**, retained the dated account observation, and displayed allocating/downloading rows during automatic turnover. No browser console errors were observed.
- **Independent review:** seven reproduced recorder/UI edge cases were corrected and rechecked, including the pre-hour outage and stale exact-instance fallback. No findings remained in that bounded follow-up review.

The separate live country trial had moved the group to GB while retaining source 11. Historical US readings were preserved. Provider dashboard sign-in was unavailable: the last account observation was retained with its real timestamp, and current credits/earnings remain unverified. Source alone cannot recreate an earning rate or those missing account observations.

Repeat the saved deterministic recorder and frontend regressions without credentials or cloud mutations:

```bash
python3 -B tests/test_recording.py
node tests/test_frontend.cjs
node tests/test_worker.cjs
```

## Historical checks of the original recovery document

Measured against the original document's extracted files and the pinned image:

| Check | Result |
|---|---|
| Embedded files | All 17 SHA-256 values matched; exact document extractor works in an empty directory. |
| Live cloud comparison | Embedded worker decoded byte-for-byte identical to Salad configuration version 14; SHA-256 in [Worker behavior](WORKER.md). |
| Keychain bootstrap | Embedded Swift helper compiled; created/read/deleted a disposable test entry with unchanged contents. Existing-key permission limitation is described in setup. |
| Recovery with no saved data | At 2026-09-07T05:44:09+00:00, an isolated empty RP database collected 41 fresh provider log records and a new recorded minute; 10 running / 10 control-connected; recorder error null. No historical DB was copied into this test. |
| Restored dashboard | Real fresh records served over HTTP 200; all four UI assets matched the extracted files exactly. |
| Cloud command encoding | Generated command reconstructed the worker and passed Node syntax checking inside the actual pinned Linux/amd64 image with external networking disabled. |
| Worker policy behavior | The exact extracted worker passed isolated tests inside the pinned image for the 1 MB boundary, diagnostic-only outcome ratios, 60-second availability rules, immediate process-exit replacement, and recognized credential rejection. Metadata requests were intercepted in the test; no real host was reallocated. |
| Image preservation | Explicit Linux/amd64 save produced a 46,104,576-byte tar; platform manifest checked and `docker image load --platform linux/amd64` succeeded. |
| Control-helper paths | Create/attach/start/stop/idempotency and wrong-group refusal passed mocked checks; actual inspect/attach-to-isolated-local-state used live read-only Salad GETs. |

**Not performed in this verification:** creating a second paid cloud group, deleting/restarting the existing group, installing the recovered LaunchAgents, or proving a repeatable earning rate. The active fleet and original recorder were left running. The recovered recorder/viewer were temporary test processes and were stopped afterward. This distinction prevents local tests from being presented as a new full cloud deployment.

## Healthy-idle correction — 2026-09-07

Version-15 / worker-11 recovery evidence above is historical. Version 16 uses worker revision 12 and removes both the 1 MB/10-minute floor and quiet-relay-age replacement. The exact source hash is `937d35e7c59fdd9c2afac80ffb3f45fbf2fbc8f06e21d43c3f66fe6a03a7ae8b`. Offline tests pass for 31 simulated idle minutes, later work on the same client, native disconnect/diagnostics failure, bounded IMDS retries, recorded zero and explicit reset gaps. Command readback matched the source at 16:50 UTC; runtime evidence is recorded separately below.

At 16:53 UTC the read-only runtime check found 9 current machines emitting the new disabled-idle policy, with cloud state counts {"running": 9}. 9 of those emitted connected native state. This is a rollout observation, not evidence of paid traffic; recent source/receipt freshness is checked separately.

At 17:02 UTC production recording showed 10 running, 10 connected, all 10 with `traffic_reallocation:false`, and no recorder error. Instance `f5d3a450-a75b-444f-81b3-e95d00ca6215` remained connected with exactly zero target bytes over a 600,347 ms window; four other connected instances were also below the former 1 MB floor. This directly verifies that healthy low/zero traffic no longer replaces those live workers. The ledger had 58,039 records and 16,874.542579 MB; an earlier consistent read showed the chart total exactly matched saved valid minute bytes (16,811,600,038 bytes).
