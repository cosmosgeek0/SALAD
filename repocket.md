# bandwidth reel — Repocket (RP) recovery guide

This file is a self-contained recovery edition of the RP deployment and its monitoring page. Keep a copy of **this Markdown file outside the computer**. Losing the computer and this only copy cannot be repaired from this document.

Prepared 2026-09-07. Custom source and dashboard dependencies are embedded below as complete readable files, with SHA-256 checksums. The extraction command writes them to a new directory. No chat history, Codex installation, remembered paths, private repository, or hidden helper binary is needed.

**External requirements remain:** access to the Salad and Repocket accounts, their current API credentials, a credited Salad organization, and the pinned official Docker image (or a separately saved image archive). Credentials and historical traffic databases are deliberately not embedded. The source files contain no account API keys.

**Reproducibility boundary:** this guide restores the same pinned image, custom worker, configuration, recorder, page, and replacement policy. A new Salad deployment receives available hosts and IPs; customer traffic and provider earnings are variable measured outcomes. Identical throughput, earnings, balances, historical data, or host IPs are not guaranteed.

## What this edition actually preserves

The live Salad API was read on 2026-09-07, before writing this guide. It reported:

| Setting | Value |
|---|---|
| Organization | `ssh2` |
| Project | `default` |
| Group slug / visible name | `rp-test-us` / `RP` |
| Existing group UUID, for identifying this deployment only | `a3a77aae-085e-4c0c-a969-34d50b091a46` |
| Desired replicas | 10 |
| Country restriction | United States: `["us"]` |
| CPU / RAM / shared memory per replica | 1 vCPU / 1024 MiB / 64 MiB |
| GPU | None |
| Priority / restart policy | `batch` / `always` |
| Autostart policy | `false`; explicitly start after creating |
| Live Salad configuration version at capture | 14 |
| Worker telemetry `revision` field | 10 (a separate source label, not Salad's configuration version) |
| Incoming gateway / ports / queue / custom probes | Not used for this workload |
| Environment variables | `RP_EMAIL`, `RP_API_KEY` |

Pinned image:

```text
docker.io/repocket/repocket@sha256:5888d756de7e0e74b95b5eb08bb93f4240a0ce840c910a7e528d1143ad0c502b
```

The image contains Docker package 1.1.46 and its bundled peer client. Do not substitute `latest` when reproducing this edition: the custom worker hooks known module paths inside that exact image. A future vendor image needs a separate compatibility check. [Official image](https://hub.docker.com/r/repocket/repocket).

The decoded command deployed in Salad was byte-for-byte identical to the embedded `repocket-monitor/start.js`:

```text
SHA-256 f162447e703f157ac682a8d99b5e893a6500dc8370288be6802ed435941f6928
```

The capture showed 10 replicas running. That is a dated observation, not a promise about later availability.

**Current behavior supersedes earlier descriptions.** The live worker no longer uses the former 50% failure rule or the former restart-once/three-minute delay. Its current policy is:

- A new client gets a complete 600-second observation window. Thereafter the rolling window covers about the latest ten minutes, evaluated on diagnostic snapshots about every 15 seconds.
- Reallocate if the window has **fewer than 1,000,000 target RX + TX bytes**. Exactly 1,000,000 bytes is kept. This is a configured traffic floor, not a profitability calculation.
- Reallocate immediately if the vendor child process fails to start or exits unexpectedly.
- Reallocate if the control connection remains unavailable for 60 seconds, or if a connected client supplies neither diagnostics nor control activity for 60 seconds. These checks run every five seconds.
- Explicit credential rejection stops the child and reports `authorization_error`; it does not deliberately rotate nodes for a rejected account key. Operator credential repair is necessary. The exact string recognition is in `acceptLine`; unknown vendor errors still need diagnosis.
- Reallocation is a POST **from the container itself** to `http://169.254.169.254/v1/reallocate`, with `Metadata: true` and a reason. No Salad API key or Mac is required for this call. The wrapper exits with code 75 afterward; Salad's `always` policy is the restart fallback if the request cannot complete. HTTP 200 means the request was accepted, not that the replacement is already online. [Salad IMDS reference](https://docs.salad.com/container-engine/how-to-guides/imds/imds-reallocate).

**Preserved UI wording:** the archived RP footer says replacement decisions use “target traffic and connection outcomes.” That sentence is outdated: outcomes remain diagnostic only; the active automatic triggers are the traffic floor and client/control availability described above. The archived assets are preserved unchanged rather than silently rewriting the original page.

Salad maintains the requested replica count and replaces lost hosts. Allocation/download time can temporarily leave fewer than ten running. The ten-minute floor can cause repeated turnover on low-throughput nodes. The current implementation has no fleet-wide replacement cooldown or profit optimizer.

## Restore from this file on a new machine

For the original local recorder and page, use macOS with Python 3.9 or newer, `curl`, and Apple Command Line Tools (`xcrun swiftc`). Node is needed only for the optional local syntax check; the cloud image already has Node. Docker is optional for saving/testing the image locally. The cloud control helper itself uses Python's standard library plus `curl` and can prompt for its Salad key on non-macOS systems, but the bundled persistent recorder uses macOS Keychain and `fcntl` as originally deployed.

1. Save this file as `~/Desktop/salad/repocket.md` (or adjust the first argument below).
2. Extract into a **new, empty** `~/Library/Application Support/RP Recovered` directory:

```bash
python3 - "$HOME/Desktop/salad/repocket.md" "$HOME/Library/Application Support/RP Recovered" <<'PY_EXTRACT'
from pathlib import Path
import hashlib,re,sys
source=Path(sys.argv[1]).expanduser()
destination=Path(sys.argv[2]).expanduser()
if destination.exists() and any(destination.iterdir()):
    raise SystemExit('Choose an empty destination; existing files will not be overwritten')
blocks=re.findall(r'<!-- RP_FILE: ([^\n]+) SHA256: ([0-9a-f]{64}) -->\n`````[^\n]*\n(.*?)\n`````',source.read_text(),re.S)
if len(blocks)!=17:
    raise SystemExit('Expected 17 embedded recovery files; obtain a complete copy')
seen=set();checked=[]
for name,digest,body in blocks:
    relative=Path(name)
    if relative.is_absolute() or '..' in relative.parts or name in seen:
        raise SystemExit('Invalid or duplicate embedded path: '+name)
    seen.add(name);data=body.encode('utf-8')
    if hashlib.sha256(data).hexdigest()!=digest:
        raise SystemExit('Checksum mismatch: '+name+'; obtain an intact copy')
    checked.append((relative,data))
for relative,data in checked:
    output=destination/relative;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
print('Extracted and checksum-verified',len(checked),'files into',destination)
PY_EXTRACT
cd "$HOME/Library/Application Support/RP Recovered"
```

The source appendix can also be copied by hand, but the extractor verifies all embedded checksums before writing anything. It does not deploy, contact any account, or change the current fleet.

3. Save the **Salad API key** in Keychain for the recorder. The included script compiles the included Swift helper and reads the key with hidden input:

```bash
bash scripts/dashboard-configure-keychain.sh
```

Use a Salad account key that can access `ssh2/default`, read logs/inventory and manage this group. Obtain/recover it through the Salad account's API-key controls. Existing local storage uses Keychain service `salad-bandwidth-api`, account equal to the operating-system username. Run setup in the foreground with the login Keychain unlocked. When reusing an old entry, macOS may ask you to authorize the newly compiled helper; resolve that prompt before starting a background recorder. A successful compile alone does not establish permission to read an existing entry. The disposable new-entry test passed, but a fresh helper's read of the old live entry timed out during verification; the live recovery check used the existing authorized build of the same helper source. Do not run the helper's `--read` command directly into a visible terminal: it emits the key. Repocket's **Docker key is a different credential**, obtained from the logged-in [Repocket bandwidth page](https://repocket.com/dashboard/share-internet). The page labels it “Use this API key with Docker.” Use the Repocket account email, not an assumed Salad email.

4. Inspect the non-secret create plan:

```bash
python3 -B restore-control.py plan > deployment-plan.json
```

The plan contains placeholder Repocket values and the encoded worker, never real credentials. The helper constructs this exact command array: `/bin/sh`, `-c`, the base64-decoding shell command, `policy-start`, then 900-character pieces of the base64 source. The decoded file is `/tmp/repocket-start.js`; it runs `/usr/local/bin/node`. Do not paste each JavaScript line into Salad's command editor or change quoting. The helper validates command sizes and the worker checksum.

5. Choose the case that matches the cloud state.

**If this RP group still exists:**

```bash
python3 -B restore-control.py inspect
python3 -B restore-control.py attach
```

`inspect` compares the remote image, command and core configuration to this edition without printing credentials. `attach` records the current group UUID locally; it does not redeploy or restart it. A new local recorder begins capture at attachment time. An existing capture cursor/history is preserved. If configuration differs, stop and inspect that difference; do not overwrite a newer working deployment from an old guide.

**If the group was deleted:**

Make sure `ssh2` and project `default` exist, the organization has enough prepaid credit and quota for ten CPU replicas, and you can access the Repocket account. This guide assumes those account resources already exist. Then:

```bash
python3 -B restore-control.py create
python3 -B restore-control.py start
python3 -B restore-control.py inspect
```

`create` requires a confirmed HTTP 404 for `rp-test-us`, prompts for the Repocket email and Docker key, and sends them directly to Salad over HTTPS. It does not save those credentials to a local file. `start` is explicit because creation alone does not establish that containers are running. A newly created group gets a **new UUID and version**, not the historical UUID/version in the table. The helper records the returned values. [Create API](https://docs.salad.com/reference/saladcloud-api/container-groups/create-container-group), [start API](https://docs.salad.com/reference/saladcloud-api/container-groups/start-container-group).

If a create/start request times out, run `inspect` before retrying: the provider may have accepted it. If local `~/.hg1/repocket/deployment.json` belongs to a deleted group, move that entire local RP directory to a backup before creating another group; do not mix two groups' measurements. The helper refuses to overwrite an existing local deployment record during creation.

**Stop cloud spending when required:**

```bash
python3 -B restore-control.py stop
python3 -B restore-control.py inspect
```

Wait for Salad to report the group stopped; an accepted stop is not immediate completion. The [Salad group page](https://portal.salad.com/organizations/ssh2/projects/default/containers/rp-test-us) also provides Stop. Closing the monitoring page or shutting down the Mac does **not** stop cloud containers. The original organization was funded with $5 and auto-recharge was off; this guide does not add funds, enable recharge, or guarantee that credit remains.

## Restore the recorder and page

The RP worker emits `RP_MON ` JSON logs to Salad. `observe.py` reads them and persists them in SQLite. It makes no reallocation requests. The local page reads those saved measurements; it is not the fleet manager.

First, run the recorder in one terminal from the extracted directory:

```bash
python3 -B repocket-monitor/observe.py
```

In another terminal, start the preserved page with the recovery launcher:

```bash
cd "$HOME/Library/Application Support/RP Recovered"
python3 -B restore-dashboard.py --port 8787
```

Open [http://127.0.0.1:8787/#rp](http://127.0.0.1:8787/#rp). If another dashboard already owns port 8787, use `--port 8788` and open `http://127.0.0.1:8788/#rp` for this separate restored copy. Do not kill an unrelated service to free a port.

`restore-dashboard.py` uses the original `dashboard.server.make_handler` and original UI assets. It deliberately does not start the original server's Honeygain/PacketStream background pollers. The preserved common page still has other provider tabs; restoring their deployments/data is outside this RP backup. Use the **RP** tab. The `dashboard/*.py` dependencies are included because the original common server imports them, even though only the RP recorder is started by these instructions.

The current data directory is fixed in `observe.py` at `~/.hg1/repocket`. Organization/group constants and the log query are also fixed to `ssh2/default/rp-test-us`. To recreate under another organization/project/group, change **all** of the control helper's constants, the observer's API organization path, `GROUP`, log query, metadata and displayed portal links together. The recipe above needs no such changes.

### Start the two local processes automatically at login (macOS)

Do this only for a fresh recovery installation. Do not run a second recorder beside an existing one: its file lock intentionally refuses that. Existing original service labels are `com.cosmosgeek.repocket-recorder` and `com.cosmosgeek.salad-bandwidth-dashboard`; the recovery labels below are distinct. If the original service is already healthy, use it rather than installing duplicates.

Stop both foreground test processes with Ctrl+C first. The extraction directory is under Application Support so login agents do not depend on background access to a protected Desktop folder. Use the same port you verified in the foreground: change `8787` to `8788` below if you selected that alternate port. From the extracted directory:

```bash
python3 - 8787 <<'PY_AGENTS'
from pathlib import Path
import plistlib,sys
port=str(int(sys.argv[1]));root=Path.cwd().resolve();agents=Path.home()/'Library/LaunchAgents';agents.mkdir(parents=True,exist_ok=True)
data=Path.home()/'.hg1/repocket';data.mkdir(parents=True,exist_ok=True)
for label,script,extra in [
    ('com.cosmosgeek.rp-recovered-recorder','repocket-monitor/observe.py',[]),
    ('com.cosmosgeek.rp-recovered-dashboard','restore-dashboard.py',['--port',port])]:
    value={'Label':label,'ProgramArguments':[sys.executable,'-B',str(root/script),*extra],
           'WorkingDirectory':str(root),'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':15,
           'StandardOutPath':str(data/(label+'.out.log')),'StandardErrorPath':str(data/(label+'.err.log'))}
    (agents/(label+'.plist')).write_bytes(plistlib.dumps(value))
print('Wrote two login-agent definitions; use launchctl below to load them')
PY_AGENTS
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.cosmosgeek.rp-recovered-recorder.plist"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.cosmosgeek.rp-recovered-dashboard.plist"
```

Keep the extracted directory in place because these definitions point to it. LaunchAgents run while that user is logged in, and collection pauses when the Mac sleeps. Cloud recovery continues. To unload either recovery process, use `launchctl bootout "gui/$(id -u)/LABEL"` with its exact label above. That only stops the local process, not the Salad group. Delete its plist manually if you do not want it loaded next login.

## Verify the result without trusting a green label

- `restore-control.py inspect` must show the correct image/source, ten requested replicas and eventually ten running. Check the live Salad page if allocation is delayed.
- `http://127.0.0.1:8787/api/repocket` must return a recent `generated_ms`, `error: null`, current workers and `workers[].policy`. A running container is not necessarily a connected client.
- Each worker should get a public IP, a `docker-…` device hash, diagnostic snapshots and target traffic. `phase: connected` proves the **control link**, not that every request succeeded or earned money.
- After the initial window, `policy.state` becomes `keeping` or the worker emits `kind: recovery`. A replacement should show a new machine/instance/run and a new observation window. Inspect the reason and HTTP status; reallocation acknowledgement and completed startup are separate facts.
- Network and target counters should change over saved intervals. A short quiet interval does not itself prove failure. Error counts are diagnostic evidence; they are not the current low-traffic replacement trigger.

Useful local read-only check:

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

## Measurement and earnings definitions

- **Interface/network RX+TX:** real Linux `eth0` receive plus send byte deltas. A proxied payload commonly crosses the interface twice, once on each leg. This includes transport/control overhead and is not unique delivered content or earnings.
- **Target socket bytes:** bytes read/written on observed HTTP/HTTPS and SOCKS target connections. These avoid adding the relay's second leg, but still include target protocol overhead; they are not provider-credited bytes.
- **Reply outcome:** any target response bytes, including protocol/TLS bytes. It is not an HTTP 200 or proof of payment. Terminal failed-before-reply outcomes are counted once per observed connection; raw timeout logs can repeat.
- **Provider credited / earned:** a timestamped **account-level snapshot** from Repocket. It is not automatically synchronized by this recorder. The page marks a snapshot stale after three minutes. Do not fabricate fresh zero values when it is unavailable. Actual payable rewards remain governed by [Repocket's payment policy](https://repocket.com/payment-and-rewards-policy).
- **Profit:** requires corresponding provider earning and Salad spend readings over the same interval. The recorder's $0.05/hour value is an unreconciled estimate; its `budget_usd` field is informational and is not a spend limiter.

If you read fresh values directly from Repocket and want them shown locally, the optional file is `~/.hg1/repocket/provider.json`. Write only observed values and the actual UTC observation timestamp; the following structure uses descriptive placeholders and is **not** a live reading:

```json
{"observed_ms": 0, "today_traffic_text": "COPY OBSERVED MB", "today_earned_text": "COPY OBSERVED USD", "traffic_text": "COPY OBSERVED TOTAL", "earned_text": "COPY OBSERVED TOTAL", "source": "Repocket dashboard snapshot"}
```

Omit this file until a real reading exists. `observed_ms` is Unix milliseconds, not seconds. Account totals may include earlier devices and other locations, so do not call them earnings from this fleet alone.

## What was changed inside the official image

There is no custom image registry or build pipeline required. The container command reconstructs the embedded worker at startup and uses the pinned official image's dependencies.

1. The parent worker starts `/app/dist/index.js` with this same file as a Node preload and an IPC channel. The child-only `RP_DIAGNOSTICS=1` flag prevents recursively starting supervisors. Do not set that flag on the top-level Salad container.
2. The preload observes the vendor's HTTP/HTTPS and SOCKS target socket creation; it samples byte counters and records sanitized error categories. It does not log target hostnames or payload contents.
3. CONNECT tunnels use the vendor's direct byte-forwarding branch, preserving its SMTP branch. This corrected observed non-TLS data being discarded by a TLS record parser. CONNECT is an opaque tunnel, as described in [RFC 9110 §9.3.6](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.6).
4. Failed target-domain `dns.lookup` calls with `ENOTFOUND` may retry with `dns.resolve4` against the same configured resolver. Successful lookups, literal IPs, IPv6-only requests and non-target lookups keep their original path. The original error is preserved if fallback fails.
5. The parent consumes only safe log categories, prints `RP_MON` records, evaluates low traffic/activity, and requests its own reallocation.
6. `observe.py` reads Salad logs, deduplicates records, reconciles late arrivals, matches current runs to inventory and publishes `view.json`. A guarded fallback handles Salad instance-label lag on the same machine; inspect `snapshot` for the exact condition.

The source label `revision:10` stayed unchanged across later deployment edits. Compare the **checksum** and Salad configuration version, not that label alone. The old local `deployment.json` had still said version 10 at capture although the API said 14; this guide and its helper use the live API result rather than copying that stale metadata.

## Troubleshooting and scope of recovery

| Symptom | Check / action |
|---|---|
| No workers after create | Run explicit `start`, inspect group state, credit and replica quota. |
| `authorization_error` | Verify the Repocket email/Docker key in the account; node replacement does not repair account authorization. |
| `Salad read returned HTTP 401/403` | Repair Salad API access in Keychain; this is the local recorder credential, not the RP Docker key. |
| HTTP 408/429/timeouts | Let the recorder's next loop retry, check API access and source age; old values must remain labeled stale. |
| `BlockingIOError` from recorder | Another recorder holds `observer.lock`; run exactly one. Do not delete the lock file to bypass the process lock. |
| Port 8787 occupied | Use the healthy existing dashboard or select another port for the recovery viewer. |
| `ENETUNREACH` with IPv6 | The requested destination may be unreachable from that node; changing inbound listening addresses does not establish outbound reachability. Do not relabel the error as a DNS failure. |
| Many errors but useful traffic | Read recent target traffic and policy state; raw error counts are not earnings and no longer directly trigger the current replacement policy. |
| Replacement accepted but fewer than ten running | Wait for Salad allocation/download/startup and inspect those states. The worker cannot force provider capacity to exist. |
| Local history disappeared | Restore the SQLite backup; code alone cannot recreate already-expired provider logs. |
| Image digest unavailable | Load an earlier saved official image archive or obtain that exact image from a trusted source. The custom source cannot reconstruct the proprietary vendor image. |

For image preservation on a machine with Docker, before an outage:

```bash
docker pull --platform linux/amd64 docker.io/repocket/repocket@sha256:5888d756de7e0e74b95b5eb08bb93f4240a0ce840c910a7e528d1143ad0c502b
docker image save --platform linux/amd64 docker.io/repocket/repocket@sha256:5888d756de7e0e74b95b5eb08bb93f4240a0ce840c910a7e528d1143ad0c502b -o repocket-official-amd64.tar
```

Use Docker whose `docker image save --help` and `docker image load --help` list `--platform`. The unqualified save command failed on the measured multi-platform image; explicitly selecting `linux/amd64` succeeded. To load the saved platform on a Docker machine:

```bash
docker image load --platform linux/amd64 -i repocket-official-amd64.tar
```

Loading this untagged archive reports an image ID and need not recreate the original Docker Hub manifest-list name. Record the printed ID, inspect its platform with `docker image inspect IMAGE_ID`, and tag/publish it if a new registry is needed.

Store the tar outside this computer. A local archive is not automatically a Salad-accessible registry; if Docker Hub disappears, publish it to a registry you control and update the image reference only after verifying image contents/platform. Running the worker on an ordinary local Docker host does not reproduce Salad IMDS self-reallocation.

For **history backup**, stop the local recorder (not cloud workers) and copy `~/.hg1/repocket` including SQLite/WAL/SHM, `deployment.json`, `cursor.json`, `view.json` and any `provider.json`. Alternatively use SQLite's online backup API while the recorder runs. Preserve the group UUID and cursor with that history; never attach a different group's data under the same state. Secure account recovery and credentials separately in a password manager. This Markdown file restores program/configuration, not historical payments, balances, accounts or deleted logs.

## Reproduction checks performed on 2026-09-07

Measured against this document's extracted files and the pinned image:

| Check | Result |
|---|---|
| Embedded files | All 17 SHA-256 values matched; exact document extractor works in an empty directory. |
| Live cloud comparison | Embedded worker decoded byte-for-byte identical to Salad configuration version 14; SHA-256 shown above. |
| Keychain bootstrap | Embedded Swift helper compiled; created/read/deleted a disposable test entry with unchanged contents. Existing-key permission limitation is described in setup. |
| Recovery with no saved data | At 2026-09-07T05:44:09+00:00, an isolated empty RP database collected 41 fresh provider log records and a new recorded minute; 10 running / 10 control-connected; recorder error null. No historical DB was copied into this test. |
| Restored dashboard | Real fresh records served over HTTP 200; all four UI assets matched the extracted files exactly. |
| Cloud command encoding | Generated command reconstructed the worker and passed Node syntax checking inside the actual pinned Linux/amd64 image with external networking disabled. |
| Worker policy behavior | The exact extracted worker passed isolated tests inside the pinned image for the 1 MB boundary, diagnostic-only outcome ratios, 60-second availability rules, immediate process-exit replacement, and recognized credential rejection. Metadata requests were intercepted in the test; no real host was reallocated. |
| Image preservation | Explicit Linux/amd64 save produced a 46,104,576-byte tar; platform manifest checked and `docker image load --platform linux/amd64` succeeded. |
| Control-helper paths | Create/attach/start/stop/idempotency and wrong-group refusal passed mocked checks; actual inspect/attach-to-isolated-local-state used live read-only Salad GETs. |

**Not performed in this verification:** creating a second paid cloud group, deleting/restarting the existing group, installing the recovered LaunchAgents, or proving a repeatable earning rate. The active fleet and original recorder were left running. The recovered recorder/viewer were temporary test processes and were stopped afterward. This distinction prevents local tests from being presented as a new full cloud deployment.

## Source appendix and recovery utilities

The following blocks are the complete files extracted by the command above. The worker is the exact decoded cloud source; the recorder and UI/dependencies are snapshots of the installed working files. `restore-control.py` and `restore-dashboard.py` are recovery utilities included in this guide, not claims that those filenames existed in the original installation. Their plan/extraction/local-serving paths are verified without creating a second paid deployment.

| File | Lines | SHA-256 |
|---|---:|---|
| `dashboard/__init__.py` | 1 | `9e72baa6472e739d23291c979acefeba840fee3e9075376a188bf94f66f8f106` |
| `dashboard/fleet_test.py` | 623 | `135ddc358e127a15904b1e34d4ada9b65cb13fc54e3bc4f01369d747828844f1` |
| `dashboard/native_network.py` | 275 | `7aebbb480bab2244e47d768994e8530bec1c529bc819e7878875c6b99e2f8a7d` |
| `dashboard/packetstream.py` | 232 | `739b686480b8839fa9c1bb95abddc2cf74db1bea66b76a549a96b82653916848` |
| `dashboard/salad_api.py` | 137 | `fdfad086f5d12cfcc69dd0f3012ffc7502a84b14ffdf172bd7009159ccde5f86` |
| `dashboard/server.py` | 514 | `436a98372e33f7d261707c670b3afee82270b3f379455b0fd07732a07768f808` |
| `dashboard/static/fleet-test.js` | 204 | `249c8547b6ae702c92cc954f8b0453ec280f9e08366c604df7dddb521dd2fe89` |
| `dashboard/static/index.html` | 8 | `ee39d93054a6f9d5088780ee5edd41617998189df4870f6bbd9e895853decb3a` |
| `dashboard/static/ps1.js` | 156 | `a386aacc6db63b407dfa846d328b2860f98e6af6dfaabde98dc4382f57356558` |
| `dashboard/static/styles.css` | 11 | `b7c37ee6cd698d1b327a51a62849a51d817435d166170a70791ebb6e68d7c9eb` |
| `dashboard/store.py` | 1239 | `1217de0c6e729cb87df4eae1d8842ebd518ef83774d82e9048ccb8ea9f37f0da` |
| `repocket-monitor/observe.py` | 148 | `6c52ef8591ad9b02425517c4f82b4fd2972d044c1865e96c0598fe6239c1030c` |
| `repocket-monitor/start.js` | 109 | `f162447e703f157ac682a8d99b5e893a6500dc8370288be6802ed435941f6928` |
| `restore-control.py` | 173 | `9e31fef72e842faac72803107cfa0f6edff8f99c7e30f540b31be2ac2d07d23b` |
| `restore-dashboard.py` | 22 | `e6a4631de974ed7172667a1aacece0aa3b021be95a841997421d770e49bcc1b2` |
| `scripts/dashboard-configure-keychain.sh` | 28 | `f964f87eb082fc1805aaf4ef34a43af6b7f16f61b8acfde9022f372535d5f40f` |
| `scripts/keychain-store.swift` | 81 | `490eadaf1afb87a0f64bf6248254ccc48ac1171af9e2fc4c796c74c12c5ca045` |

### `dashboard/__init__.py`

<!-- RP_FILE: dashboard/__init__.py SHA256: 9e72baa6472e739d23291c979acefeba840fee3e9075376a188bf94f66f8f106 -->
`````python
"""Local Salad bandwidth dashboard."""

`````

### `dashboard/fleet_test.py`

<!-- RP_FILE: dashboard/fleet_test.py SHA256: 135ddc358e127a15904b1e34d4ada9b65cb13fc54e3bc4f01369d747828844f1 -->
`````python
"""Read-only, bounded independent-fleet experiment reporting.

Network counters and provider account credits have separate units and clocks.
Never infer paid traffic from interfaces, or client acceptance from Salad state.
"""

from __future__ import annotations

import csv
from bisect import bisect_left, bisect_right
from copy import deepcopy
from datetime import datetime
import io
import json
import math
import re
import threading
import time
from pathlib import Path

from dashboard.native_network import instance_run


BUCKET_MS = 600_000
GAP_MS = 180_000
MAX_BYTES = 128 * 1024 * 1024
MAX_ROWS = 20_000
MAX_BUCKETS = 2016  # Two weeks; older observations remain on disk.
MAX_TIMELINE_INTERVALS = 2000
HG_ERROR_CODES = frozenset({"device_limit", "device_already_active", "network_overused", "network_unusable", "authorization_error", "disconnected"})
HG_EXCLUDED_IPS = frozenset({"96.246.178.36"})


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def pick(source, strings=(), numbers=()):
    source = source if isinstance(source, dict) else {}
    result = {key: str(source[key])[:200] if source.get(key) is not None else None for key in strings}
    result.update({key: number(source.get(key)) for key in numbers})
    return result


def clean_hg_error(value):
    # Observer exception messages may contain private URLs or credentials.
    if isinstance(value, str) and value in HG_ERROR_CODES:
        return value
    return "observer_error" if value else None


def clean_ps_error(value):
    if isinstance(value, str) and "PacketStream allows packeting from 1 client per IP address." in value:
        return "duplicate_ip"
    return "client_error" if value else None


def timestamp_ms(value):
    if not isinstance(value, str) or len(value) > 100:
        return None
    try:
        # Salad emits seven fractional digits; older Python accepts six.
        value = re.sub(r"\.(\d+)(?=[+-])", lambda m: "." + m.group(1)[:6].ljust(6, "0"), value.replace("Z", "+00:00"))
        stamp = datetime.fromisoformat(value)
        return int(stamp.timestamp() * 1000) if stamp.tzinfo else None
    except (ValueError, OverflowError, OSError):
        return None


def clean_experiment(raw):
    result = pick(raw, ("id", "started_at", "status", "phase"), ("started_ms",))
    result["ps"] = pick(raw.get("ps"), ("organization", "group"), ("desired", "baseline_provider_bytes"))
    result["hg"] = pick(raw.get("hg"), ("organization", "phase"),
                        ("desired", "baseline_provider_gathering_credits", "baseline_provider_observed_ms", "baseline_started_ms"))
    result["archive_name"] = Path(str(raw.get("archive_path", ""))).name or None
    # Action descriptions are deliberately omitted: raw operational logs may
    # carry credential-bearing URLs. Only the intervention's time/type is public.
    result["interventions"] = [pick(row, ("service", "action", "recorded_at"), ("time_ms",))
                               for row in raw.get("interventions", [])[-100:] if isinstance(row, dict)]
    return result


def clean_observation(raw):
    result = pick(raw, ("recorded_at", "experiment_id", "phase"), ("time_ms",))
    ps = raw.get("ps") or {}
    hg = raw.get("hg") or {}
    result["ps"] = pick(ps, (), ("running", "reporting", "accepted", "monitor_connections", "provider_bytes", "provider_observed_ms",
                                 "network_rx_bytes", "network_tx_bytes", "network_total_bytes", "network_observed_ms", "status_observed_ms"))
    result["ps"]["network_complete"] = ps.get("network_complete") is True
    result["ps"]["workers"] = [{**pick(w, ("machine", "run", "ip", "state", "client_status", "sample_source"),
                                      ("network_bytes", "received_age_ms", "client_status_age_ms", "source_age_ms", "source_granularity_seconds", "last_interval_seconds")),
                                "native_status_only": w.get("native_status_only") is True or w.get("sample_source") in {"native_status_only", "sysfs_via_salad_logs_1s", "native_sysfs_1s"},
                                "error_code": clean_ps_error(w.get("error"))}
                                 for w in ps.get("workers", [])[:50] if isinstance(w, dict)]
    result["ps"]["native_status_only"] = ps.get("native_status_only") is True or any(w["native_status_only"] for w in result["ps"]["workers"])
    result["hg"] = pick(hg, (), ("running", "connected", "desired", "provider_gathering_credits", "provider_observed_ms",
                                 "network_rx_bytes", "network_tx_bytes", "network_total_bytes", "network_observed_ms", "status_observed_ms"))
    result["hg"]["network_complete"] = hg.get("network_complete") is True
    result["hg"]["workers"] = [{**pick(w, ("group", "device", "machine", "run", "ip", "state", "client_status"),
                                      ("credits", "credit_observed_ms", "network_bytes", "received_age_ms", "sample_ms")),
                                "error_code": clean_hg_error(w.get("error"))}
                                 for w in hg.get("workers", [])[:50] if isinstance(w, dict)]
    result["collection_error"] = bool(raw.get("errors") or raw.get("error"))
    return result


def distinct_points(points):
    unique = {}
    for at, value, complete in points:
        previous = unique.get(at)
        if previous:
            # Conflicting counters at one source time cannot support a rate.
            value = value if value == previous[1] else None
            complete = complete and previous[2]
        unique[at] = (at, value, complete)
    return sorted(unique.values())


def window_counter(rows, counter, timestamp, start_ms, end_ms):
    points = distinct_points((source[timestamp], number(source.get(counter)), source.get("network_complete") is True)
                             for row in rows for source in (row["ps"],)
                             if number(source.get(timestamp)) is not None and start_ms <= source[timestamp] <= end_ms)
    values = [p[1] for p in points]
    delta = values[-1] - values[0] if len(values) >= 2 and all(v is not None for v in values) and all(b >= a for a, b in zip(values, values[1:])) else None
    return points, delta


def measured_interval(previous=None, current=None, gap_ms=GAP_MS):
    result = {"start_ms": previous[0] if previous else None, "end_ms": current[0] if current else None,
              "delta": None, "per_second": None, "complete": False, "status": "missing"}
    if not previous or not current or previous[1] is None or current[1] is None:
        return result
    elapsed = current[0] - previous[0]
    if elapsed <= 0:
        return result
    if current[1] < previous[1]:
        result["status"] = "counter_reset"
        return result
    result["delta"] = current[1] - previous[1]
    if elapsed > gap_ms:
        result["status"] = "gap"
        return result
    result["complete"] = previous[2] and current[2]
    result["status"] = "complete" if result["complete"] else "incomplete"
    # A partial sum is useful activity evidence, but never full-fleet coverage.
    result["per_second"] = result["delta"] * 1000 / elapsed
    return result


def rate_timeline(rows, started_ms, end_ms, hg_started_ms=None, ps_started_ms=None):
    timeline = {service: {metric: [] for metric in ("network", "provider")} for service in ("ps", "hg")}
    truncated = False
    for service, metric, counter, timestamp in (
        ("ps", "network", "network_total_bytes", "network_observed_ms"),
        ("ps", "provider", "provider_bytes", "provider_observed_ms"),
        ("hg", "network", "network_total_bytes", "network_observed_ms"),
        ("hg", "provider", "provider_gathering_credits", "provider_observed_ms"),
    ):
        start = max(started_ms, hg_started_ms or started_ms) if service == "hg" and metric == "provider" else started_ms
        if service == "ps":
            start = max(start, ps_started_ms or start)
        points = []
        for row in rows:
            source = row.get(service) or {}
            at = number(source.get(timestamp))
            # Missing source timestamps never become recorder-time observations.
            if at is not None and start <= at <= end_ms:
                points.append((at, number(source.get(counter)), metric != "network" or source.get("network_complete") is True))
        points = distinct_points(points)
        truncated = truncated or len(points) - 1 > MAX_TIMELINE_INTERVALS
        points = points[-MAX_TIMELINE_INTERVALS - 1:]
        gap = 420_000 if service == "hg" and metric == "provider" else GAP_MS
        timeline[service][metric] = [measured_interval(a, b, gap) for a, b in zip(points, points[1:])]
    return timeline, truncated


def worker_identity(worker):
    identity = tuple(worker.get(field) for field in ("group", "device", "machine", "run"))
    return identity if any(identity) else None


def worker_sample_time(service, source, worker, row_ms):
    if service == "hg" and number(worker.get("sample_ms")) is not None:
        return worker["sample_ms"]
    if service == "ps":
        sample_age = number(worker.get("source_age_ms"))
        if sample_age is None:
            sample_age = number(worker.get("received_age_ms"))
        base = row_ms
    else:
        sample_age = number(worker.get("received_age_ms"))
        base = number(source.get("status_observed_ms"))
    if sample_age is not None and base is not None:
        return base - sample_age
    return number(source.get("network_observed_ms"))


def worker_intervals(rows, latest, started_ms, now_ms, ps_started_ms=None):
    for service in ("ps", "hg"):
        start = max(started_ms, ps_started_ms or started_ms) if service == "ps" else started_ms
        series = {}
        for row in rows:
            source = row.get(service) or {}
            for worker in source.get("workers", []):
                identity = worker_identity(worker)
                at = worker_sample_time(service, source, worker, row["time_ms"])
                if identity is not None and at is not None and start <= at <= now_ms:
                    series.setdefault(identity, []).append((at, number(worker.get("network_bytes")), True))
        for worker in latest[service]["workers"]:
            points = distinct_points(series.get(worker_identity(worker), []))
            current = points[-1] if points else None
            value = measured_interval(points[-2] if len(points) >= 2 else None, current)
            if worker.get("network_bytes") is None:
                value = measured_interval()
            elif current and now_ms - current[0] > (60_000 if service == "ps" else 120_000):
                value.update(per_second=None, complete=False, status="stale")
            worker["network_interval"] = value
            worker["network_first_ms"] = points[0][0] if points else None
            worker["network_last_ms"] = current[0] if current else None


def honeygain_minutes(rows, started_ms, end_ms):
    end = int(end_ms)//60000*60000
    start = end-1439*60000
    series = {}
    for row in rows:
        source = row.get("hg") or {}
        for worker in source.get("workers", []):
            at = worker_sample_time("hg", source, worker, row["time_ms"])
            value = number(worker.get("network_bytes"))
            identity = worker_identity(worker)
            if identity is not None and at is not None and max(started_ms,start-GAP_MS) <= at <= end_ms:
                series.setdefault(identity, []).append((at,value,worker.get("ip")))
    buckets = {}
    for identity, values in series.items():
        unique = {}
        for at,value,ip in values:
            point=(value,ip)
            unique[at]=point if at not in unique or unique[at]==point else (None,None)
        points=[(at,*point) for at,point in sorted(unique.items())]
        for previous, current in zip(points,points[1:]):
            if previous[2] != current[2]:
                continue
            interval = measured_interval((*previous[:2],True),(*current[:2],True))
            if interval["per_second"] is None:
                continue
            first,last = interval["start_ms"],interval["end_ms"]
            for minute in range(max(start,int(first)//60000*60000),min(end,int(last-1)//60000*60000)+1,60000):
                overlap = min(last,minute+60000)-max(first,minute)
                if overlap <= 0:
                    continue
                contribution = buckets.setdefault(minute,{}).setdefault(identity+(current[2],),{"instance":"/".join(x or "" for x in identity),"ip":current[2],"mb":0})
                contribution["mb"] += interval["delta"]*overlap/(last-first)/1e6
    result=[]
    for minute in range(start,end+1,60000):
        nodes=sorted(buckets.get(minute,{}).values(),key=lambda n:(-n["mb"],n["instance"]))
        result.append({"minute_ms":minute,"mb":sum(n["mb"] for n in nodes) if nodes else None,
                       "partial":True,"estimated":True,"count":len(nodes),"nodes":nodes[:20]})
    return result


def measured_delta(points, start, end, *, final=False, gap_ms=GAP_MS):
    selected = points[bisect_left(points, (start,)):bisect_right(points, (end, float("inf"), True))]
    result = {"delta": None, "per_10_min": None, "coverage_seconds": 0, "status": "missing", "change_percent": None}
    if len(selected) < 2:
        return result
    elapsed = selected[-1][0] - selected[0][0]
    result["coverage_seconds"] = elapsed / 1000
    if any(b[1] < a[1] for a, b in zip(selected, selected[1:])):
        result["status"] = "counter_reset"
        return result
    result["delta"] = selected[-1][1] - selected[0][1]
    if any(b[0] - a[0] > gap_ms for a, b in zip(selected, selected[1:])):
        result["status"] = "gap"
    elif any(not point[2] for point in selected):
        result["status"] = "incomplete"
    elif elapsed < BUCKET_MS * .9 or selected[0][0] - start >= 60_000 or end - selected[-1][0] >= 60_000 or final:
        result["status"] = "partial"
    else:
        result["status"] = "complete"
        result["per_10_min"] = result["delta"] * BUCKET_MS / elapsed
    return result


def rate_buckets(rows, started_ms, end_ms):
    sources = {"ps_credited": [], "ps_network": [], "hg_credits": [], "hg_network": []}
    for row in rows:
        for metric, service, counter, timestamp, divisor in (
            ("ps_credited", "ps", "provider_bytes", "provider_observed_ms", 1_000_000),
            ("ps_network", "ps", "network_total_bytes", "network_observed_ms", 1_000_000),
            ("hg_credits", "hg", "provider_gathering_credits", "provider_observed_ms", 1),
            ("hg_network", "hg", "network_total_bytes", "network_observed_ms", 1_000_000),
        ):
            source = row.get(service) or {}
            value = number(source.get(counter))
            at = number(source.get(timestamp))
            if metric.endswith("_network") and at is None:
                at = number(row.get("time_ms"))
            if value is not None and at is not None and started_ms <= at <= end_ms:
                sources[metric].append((at, value / divisor, not metric.endswith("_network") or source.get("network_complete") is True))
    for key, points in sources.items():
        # Repeated stale provider readings are one observation, not zero-growth
        # samples. Keep an incomplete flag if any same-time sample is incomplete.
        unique = {}
        for point in points:
            previous = unique.get(point[0])
            unique[point[0]] = (point[0], point[1], point[2] and (previous[2] if previous else True))
        sources[key] = sorted(unique.values())
    count = min(MAX_BUCKETS, max(1, math.ceil((end_ms - started_ms) / BUCKET_MS)))
    first_index = max(0, math.ceil((end_ms - started_ms) / BUCKET_MS) - count)
    buckets = []
    for index in range(first_index, first_index + count):
        start = started_ms + index * BUCKET_MS
        end = min(end_ms, start + BUCKET_MS)
        bucket = {"start_ms": start, "end_ms": end, "open": end - start < BUCKET_MS}
        for metric, points in sources.items():
            bucket[metric] = measured_delta(points, start, end, final=bucket["open"], gap_ms=420_000 if metric == "hg_credits" else GAP_MS)
            current = bucket[metric]
            previous = buckets[-1][metric] if buckets else None
            if previous and current["per_10_min"] is not None and previous["per_10_min"]:
                current["change_percent"] = 100 * (current["per_10_min"] / previous["per_10_min"] - 1)
        buckets.append(bucket)
    return buckets


class FleetTestView:
    def __init__(self, root):
        self.root = Path(root)
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._hg_sources = (None, {})

    @staticmethod
    def read_json(path):
        with path.open("rb") as handle:
            data = handle.read(128 * 1024 + 1)
        if len(data) > 128 * 1024:
            raise ValueError("Experiment metadata is too large")
        raw = json.loads(data)
        if not isinstance(raw, dict):
            raise ValueError("Experiment metadata is invalid")
        return raw

    def service_windows(self, experiment, now_ms, archived=False):
        start = experiment["started_ms"] or now_ms
        windows = {service: {"start_ms": start, "basis": "test", "observed_ms": None,
                             "stale": False if archived or service == "hg" else True,
                             "state": "archived" if archived else "unknown"} for service in ("ps", "hg")}
        if archived:
            return windows, None
        try:
            census = self.read_json(self.root.parent / "packetstream" / "native-census.json")
            target = experiment["ps"]
            if not target.get("organization") or not target.get("group") or census.get("group") != f'{target["organization"]}/default/{target["group"]}':
                return windows, None
            group_state = census.get("group_state") or {}
            restarted = timestamp_ms(group_state.get("start_time"))
            observed = timestamp_ms(census.get("last_success_at") or census.get("checked_at"))
            if restarted is None or restarted > now_ms or observed is None or restarted > observed:
                return windows, None
            state = group_state.get("status")
            if state not in {"running", "stopped", "stopping", "pending", "starting", "allocating", "creating", "deploying", "failed", "succeeded"}:
                state = "unknown"
            windows["ps"].update(start_ms=max(start, restarted), basis="native_restart" if restarted > start else "test",
                                 observed_ms=observed, stale=not 0 <= now_ms - observed <= 90_000, state=state)
            nodes = census.get("nodes")
            if not isinstance(nodes, list):
                return windows, None
            runs = set()
            for node in nodes[:50]:
                if not isinstance(node, dict):
                    continue
                machine, instance = node.get("machine"), node.get("instance_id")
                if all(isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value) for value in (machine, instance)):
                    runs.add(machine + "/" + instance)
            return windows, {"observed_ms": observed, "runs": runs}
        except (OSError, ValueError, TypeError, AttributeError):
            return windows, None

    def archives(self):
        result = []
        archive_root = self.root / "archives"
        if not archive_root.is_dir():
            return result
        for child in sorted(archive_root.iterdir(), reverse=True)[:100]:
            if child.is_symlink() or not child.is_dir() or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", child.name):
                continue
            try:
                metadata = clean_experiment(self.read_json(child / "current.json"))
                result.append({"id": child.name, "started_ms": metadata["started_ms"], "status": metadata["status"]})
            except (OSError, ValueError):
                continue
        return result

    def snapshot(self, now_ms=None, archive=None, include_observations=False, honeygain_only=False):
        if now_ms is not None or archive or include_observations:
            return self._snapshot(now_ms, archive, include_observations, honeygain_only)
        with self._cache_lock:
            cached = self._cache.get(honeygain_only)
            if cached is None or time.monotonic() - cached[0] >= 5:
                cached = (time.monotonic(), self._snapshot(honeygain_only=honeygain_only))
                self._cache[honeygain_only] = cached
            return cached[1]

    def _snapshot(self, now_ms=None, archive=None, include_observations=False, honeygain_only=False):
        now_ms = int(time.time() * 1000) if now_ms is None else now_ms
        directory = self.root
        if archive is not None:
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", archive):
                raise ValueError("Invalid archive identifier")
            directory = self.root / "archives" / archive
            if directory.is_symlink() or directory.resolve().parent != (self.root / "archives").resolve():
                raise ValueError("Invalid archive identifier")
        try:
            experiment = clean_experiment(self.read_json(directory / "current.json"))
        except FileNotFoundError:
            return {"experiment": None, "warnings": ["Independent test recorder has not started."], "archives": self.archives()}
        rows, invalid, truncated = [], 0, False
        previous_hg = None
        source_path = self.root.parent / "hg-fleet" / "observations.jsonl"
        if source_path.exists() and self._hg_sources[0] != source_path.stat().st_mtime_ns:
            sources = {}
            source_stamp = source_path.stat().st_mtime_ns
            for line in source_path.open():
                try:
                    source = json.loads(line)
                    sources[source["time_ms"]] = {w["group"]: w for w in source.get("workers", [])}
                except (ValueError, KeyError):
                    continue
            self._hg_sources = (source_stamp, sources)
        path = directory / "observations.jsonl"
        if path.exists():
            with path.open("rb") as handle:
                size = path.stat().st_size
                if size > MAX_BYTES:
                    handle.seek(size - MAX_BYTES)
                    handle.readline()
                    truncated = True
                lines = handle.read(MAX_BYTES).splitlines()
            truncated = truncated or len(lines) > MAX_ROWS
            for line in lines[-MAX_ROWS:]:
                try:
                    raw = json.loads(line)
                    if not isinstance(raw, dict):
                        raise ValueError("Invalid observation")
                    if raw.get("experiment_id") == experiment["id"]:
                        hg = raw.get("hg") or {}
                        source_workers = self._hg_sources[1].get(hg.get("status_observed_ms"), {})
                        for worker in hg.get("workers", []):
                            original = source_workers.get(worker.get("group"), {})
                            sample = original.get("sample") or {}
                            if original.get("machine") == worker.get("machine") and number(sample.get("rx_total")) is not None and number(sample.get("tx_total")) is not None and sample["rx_total"] + sample["tx_total"] == worker.get("network_bytes"):
                                worker.update(sample_ms=timestamp_ms(sample.get("time")), run=original.get("instance"))
                        if honeygain_only:
                            key = hg
                            if rows and key == previous_hg:
                                rows[-1]["time_ms"] = raw["time_ms"]
                                rows[-1]["recorded_at"] = raw.get("recorded_at")
                                continue
                            previous_hg = key
                            raw["ps"] = {}
                        row = clean_observation(raw)
                        if row["time_ms"] is not None and row["time_ms"] >= (experiment["started_ms"] or 0):
                            rows.append(row)
                except (ValueError, TypeError, AttributeError):
                    invalid += 1
        rows.sort(key=lambda row: row["time_ms"])
        excluded_last, excluded_bytes = {}, 0
        for row in rows:
            hg = row["hg"]
            for worker in hg["workers"]:
                if worker.get("ip") not in HG_EXCLUDED_IPS:
                    continue
                identity, value = worker_identity(worker), worker.get("network_bytes")
                if identity is not None and value is not None:
                    previous = excluded_last.get(identity, value)
                    excluded_bytes += max(0, value - previous)
                    excluded_last[identity] = value
                worker["network_bytes"] = None
            if excluded_bytes and hg["network_total_bytes"] is not None:
                hg["network_total_bytes"] = max(0, hg["network_total_bytes"] - excluded_bytes)
                hg["network_rx_bytes"] = hg["network_tx_bytes"] = None
                hg["network_complete"] = False
            if truncated:
                hg["network_total_bytes"] = None
                hg["network_complete"] = False
        # Keep ledger source ages unchanged while advancing the live view clock.
        latest = deepcopy(rows[-1]) if rows else None
        if latest:
            latest["hg"]["workers"] = [w for w in latest["hg"]["workers"] if w.get("ip") not in HG_EXCLUDED_IPS]
        age = max(0, now_ms - latest["time_ms"]) if latest else None
        stale = age is None or age > GAP_MS
        start = experiment["started_ms"] or now_ms
        end = latest["time_ms"] if archive and latest else now_ms
        windows, census = self.service_windows(experiment, now_ms, archived=bool(archive))
        ps_start = windows["ps"]["start_ms"]
        warnings = []
        if not archive and windows["ps"]["stale"]:
            warnings.append("PacketStream restart census is stale, missing, or does not match this test target. The current run boundary is not freshly verified.")
        if stale and not archive:
            warnings.append("Recorder is stale or has no observations. Last values are historical, not live.")
        if invalid:
            warnings.append("An incomplete or invalid ledger line was skipped; the next refresh will retry.")
        if truncated:
            warnings.append("Showing the bounded ledger tail. Older records remain in the saved ledger.")
        if latest and latest["collection_error"]:
            warnings.append("A collector reported an error. Inspect its local recorder log.")
        timeline, timeline_truncated = rate_timeline(rows, start, max(start, end), experiment["hg"].get("baseline_provider_observed_ms"), ps_start)
        if timeline_truncated:
            warnings.append("The activity graph shows the latest 2,000 measured intervals per source. Older observations remain in history.")
        summary = {"ps_credited_mb": None, "ps_network_mb": None, "hg_gathering_credits": None, "hg_network_mb": None}
        if latest:
            ps, hg = latest["ps"], latest["hg"]
            ps["inventory_status"] = "ledger"
            if census and (census["observed_ms"] >= (ps["status_observed_ms"] or 0) or latest["time_ms"] < ps_start):
                current_workers = [w for w in ps["workers"] if instance_run(w.get("run")) in census["runs"] and latest["time_ms"] >= ps_start]
                if len(current_workers) != len(ps["workers"]):
                    ps["workers"] = current_workers
                    ps["inventory_status"] = "awaiting_current_run"
                    for field in ("running", "accepted", "reporting", "monitor_connections", "network_rx_bytes", "network_tx_bytes", "network_total_bytes", "network_observed_ms"):
                        ps[field] = None
                    ps["network_complete"] = False
                    warnings.append("PacketStream restarted or changed instances. Older container rows are hidden while the recorder catches up with the current census.")
                else:
                    ps["inventory_status"] = "matched"
            if ps_start > start:
                for worker in ps["workers"]:
                    client_age = worker.get("client_status_age_ms")
                    if client_age is not None and latest["time_ms"] - client_age < ps_start:
                        worker.update(client_status="unknown", client_status_age_ms=None, error_code=None)
            worker_intervals(rows, latest, start, end, ps_start)
            ps["status_age_ms"] = max(0, now_ms - ps["status_observed_ms"]) if ps["status_observed_ms"] is not None else None
            ps["status_stale"] = ps["status_age_ms"] is None or ps["status_age_ms"] > 90_000
            if ps["status_stale"] and not archive:
                warnings.append("PacketStream worker census is stale or missing. Running and accepted counts are last recorded states.")
            hg["status_age_ms"] = max(0, now_ms - hg["status_observed_ms"]) if hg["status_observed_ms"] is not None else None
            hg["status_stale"] = hg["status_age_ms"] is None or hg["status_age_ms"] > 120_000
            if hg["status_stale"] and not archive:
                warnings.append("Honeygain worker observer is stale or missing. Running and connected counts are last recorded states.")
            # Source ages were captured at different times. Advance them to the
            # current snapshot clock; a healthy fleet recorder cannot freshen an
            # old Honeygain observer or an old PacketStream client sample.
            for service, elapsed in ((ps, age), (hg, hg["status_age_ms"])):
                for worker in service["workers"]:
                    worker_elapsed = elapsed
                    for field in ("received_age_ms", "client_status_age_ms", "source_age_ms"):
                        # PS event ages are already measured against the fleet
                        # recorder clock, including native census events.
                        field_elapsed = age if service is ps and field == "client_status_age_ms" else worker_elapsed
                        if worker.get(field) is not None and field_elapsed is not None:
                            worker[field] += field_elapsed
                    if service is ps:
                        client_age = worker.get("client_status_age_ms")
                        worker["client_status_stale"] = stale or ps["status_stale"] or client_age is None or client_age > (240_000 if worker.get("native_status_only") else 120_000)
            for service, timestamp in ((ps, "provider_observed_ms"), (hg, "provider_observed_ms")):
                service["provider_age_ms"] = max(0, now_ms - service[timestamp]) if service[timestamp] is not None else None
            baseline, current = experiment["ps"].get("baseline_provider_bytes"), ps["provider_bytes"]
            paid_values = [r["ps"]["provider_bytes"] for r in rows if r["ps"]["provider_bytes"] is not None
                           and (r["ps"]["provider_observed_ms"] or 0) >= ps_start]
            paid_reset = any(b < a for a, b in zip(paid_values, paid_values[1:]))
            if baseline is not None and current is not None and current >= baseline and not paid_reset and (ps["provider_observed_ms"] or 0) >= start:
                summary["ps_credited_mb"] = (current - baseline) / 1_000_000
            if paid_reset:
                warnings.append("PacketStream's account counter decreased during this window. Its total delta is unknown.")
            summary["ps_network_mb"] = ps["network_total_bytes"] / 1_000_000 if ps["network_total_bytes"] is not None else None
            if ps_start > start:
                paid_points, paid_delta = window_counter(rows, "provider_bytes", "provider_observed_ms", ps_start, end)
                network_points, network_delta = window_counter(rows, "network_total_bytes", "network_observed_ms", ps_start, end)
                windows["ps"].update(provider_baseline_ms=paid_points[0][0] if paid_points else None,
                                     provider_baseline_bytes=paid_points[0][1] if paid_points else None,
                                     network_baseline_ms=network_points[0][0] if network_points else None)
                paid_fresh = paid_points and 0 <= now_ms - paid_points[-1][0] <= GAP_MS and not windows["ps"]["stale"]
                summary["ps_credited_mb"] = paid_delta / 1_000_000 if paid_delta is not None and paid_fresh else None
                summary["ps_network_mb"] = network_delta / 1_000_000 if network_delta is not None else None
                ps["network_complete"] = ps["network_complete"] and network_delta is not None and all(p[2] for p in network_points)
            summary["hg_network_mb"] = hg["network_total_bytes"] / 1_000_000 if hg["network_total_bytes"] is not None else None
            hg_baseline = experiment["hg"].get("baseline_provider_gathering_credits")
            hg_baseline_at = experiment["hg"].get("baseline_provider_observed_ms")
            explicit_hg_baseline = hg_baseline is not None and hg_baseline_at is not None
            hg_readings = sorted({r["hg"]["provider_observed_ms"]: r["hg"]["provider_gathering_credits"] for r in rows
                                 if r["hg"]["provider_gathering_credits"] is not None
                                 and (r["hg"]["provider_observed_ms"] or 0) >= (hg_baseline_at if explicit_hg_baseline else start)}.items())
            if explicit_hg_baseline:
                # The explicit reading is the independent Honeygain baseline;
                # never fall back to startup credits if later readings are absent.
                valid_hg = [hg_baseline] + [value for at, value in hg_readings if at > hg_baseline_at]
            else:
                valid_hg = [value for at, value in hg_readings]
            if len(valid_hg) >= 2 and all(b >= a for a, b in zip(valid_hg, valid_hg[1:])):
                summary["hg_gathering_credits"] = valid_hg[-1] - valid_hg[0]
            # Pad missing inventory without manufacturing running clients.
            for service in ("ps", "hg"):
                wanted = min(50, int(experiment[service].get("desired") or 10))
                while len(latest[service]["workers"]) < wanted:
                    latest[service]["workers"].append({"state": "unknown", "client_status": "unknown"})
        result = {"experiment": experiment, "latest": latest, "summary": summary, "observation_count": len(rows),
                  "recorder_age_ms": age, "recorder_stale": stale, "invalid_lines": invalid, "truncated": truncated,
                  "warnings": warnings, "archives": self.archives(), "archived": bool(archive),
                  "service_windows": windows,
                  "timeline": timeline, "timeline_truncated": timeline_truncated,
                  "hg_minutes": honeygain_minutes(rows, start, end),
                  "buckets": rate_buckets(rows, start, max(start, end)), "generated_ms": now_ms}
        if include_observations:
            result["observations"] = rows
        return result


def fleet_csv(snapshot):
    output = io.StringIO(newline="")
    fields = ["start_ms", "end_ms", "ps_network_mb", "ps_network_status", "ps_credited_mb", "ps_credited_mb_per_10_min",
              "ps_credited_change_percent", "ps_credited_coverage_seconds", "ps_credited_status", "hg_network_mb", "hg_network_status", "hg_gathering_credits", "hg_status"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for bucket in snapshot.get("buckets", []):
        writer.writerow({"start_ms": bucket["start_ms"], "end_ms": bucket["end_ms"],
                         "ps_network_mb": bucket["ps_network"]["delta"], "ps_network_status": bucket["ps_network"]["status"],
                         "ps_credited_mb": bucket["ps_credited"]["delta"], "ps_credited_mb_per_10_min": bucket["ps_credited"]["per_10_min"],
                         "ps_credited_change_percent": bucket["ps_credited"]["change_percent"],
                         "ps_credited_coverage_seconds": bucket["ps_credited"]["coverage_seconds"],
                         "ps_credited_status": bucket["ps_credited"]["status"],
                         "hg_network_mb": bucket["hg_network"]["delta"], "hg_network_status": bucket["hg_network"]["status"],
                         "hg_gathering_credits": bucket["hg_credits"]["delta"], "hg_status": bucket["hg_credits"]["status"]})
    return output.getvalue().encode("utf-8")

`````

### `dashboard/native_network.py`

<!-- RP_FILE: dashboard/native_network.py SHA256: 7aebbb480bab2244e47d768994e8530bec1c529bc819e7878875c6b99e2f8a7d -->
`````python
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

`````

### `dashboard/packetstream.py`

<!-- RP_FILE: dashboard/packetstream.py SHA256: 739b686480b8839fa9c1bb95abddc2cf74db1bea66b76a549a96b82653916848 -->
`````python
"""Paid-traffic readings and deployment membership for the PS dashboard.

Billing values come only from the authenticated provider page. Interface counters
are used for node identity, never converted into credited traffic.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import threading
import time
from urllib.parse import quote


def millis(value):
    if not value:
        return 0
    normalized = re.sub(r"(\.\d{6})\d+", r"\1", value.replace("Z", "+00:00"))
    return int(datetime.fromisoformat(normalized).timestamp() * 1000)


def paid_window(readings, start, end):
    selected = [r for r in readings if start <= r["time_ms"] <= end]
    # Rounded historical display readings must not be mixed with exact provider
    # byte records. Use the newest available measurement basis within the window.
    if selected:
        basis = selected[-1].get("basis", "display_gb")
        selected = [r for r in selected if r.get("basis", "display_gb") == basis]
    result = {"readings": selected, "mb": None, "mb_per_minute": None,
              "first_ms": None, "last_ms": None, "error": None}
    if len(selected) < 2:
        result["error"] = "Two provider readings are needed in this period."
        return result
    first, last = selected[0], selected[-1]
    result.update(first_ms=first["time_ms"], last_ms=last["time_ms"])
    if any(b["gb"] < a["gb"] for a, b in zip(selected, selected[1:])):
        result["error"] = "The provider's rolling counter decreased; this period cannot be measured reliably."
        return result
    amount = round((last["gb"] - first["gb"]) * 1000, 6)
    elapsed = last["time_ms"] - first["time_ms"]
    if elapsed <= 0:
        result["error"] = "The provider readings have no elapsed time."
        return result
    result.update(mb=amount, mb_per_minute=amount * 60000 / elapsed)
    return result


def ordered_nodes(raw_nodes, members, restart_ms, countries):
    newest = {}
    for n in raw_nodes:
        if n["start"] > newest.get(n["machine"], {}).get("start", -1):
            newest[n["machine"]] = n
    rows = []
    for n in raw_nodes:
        current = (n["machine"] in members and newest[n["machine"]]["run"] == n["run"]
                   and n["start"] * 1000 >= restart_ms - 2000)
        receipt_age, source_age = n.get("sample_age_ms"), n.get("source_sample_age_ms")
        sample_source = n.get("sample_source")
        receipt_limit = 25000 if sample_source == "salad_logs_10s" else 15000
        fresh = (n.get("samples", 0) > 0 and isinstance(receipt_age, (int, float)) and 0 <= receipt_age <= receipt_limit
                 and isinstance(source_age, (int, float)) and -15000 <= source_age <= 60000)
        rows.append({"run": n["run"], "machine": n["machine"], "ip": n["ip"],
                     "start_ms": n["start"] * 1000, "current": current,
                     "state": members[n["machine"]] if current else "previous",
                     "observed_network_mb": n.get("mb") if n.get("samples", 0) > 0 else None,
                     "network_sample_age_ms": receipt_age if receipt_age is not None else -1,
                     "network_source_age_ms": source_age,
                     "network_sample_fresh": bool(fresh), "sample_source": sample_source,
                     "source_granularity_seconds": n.get("source_granularity_seconds"),
                     "country": "United States" if countries == ["us"] else " / ".join(countries),
                     "country_source": "Salad deployment placement"})
    for machine, state in members.items():
        if not any(r["machine"] == machine and r["current"] for r in rows):
            rows.append({"run": machine + "/pending", "machine": machine, "ip": "",
                         "start_ms": 0, "current": True, "state": state,
                         "observed_network_mb": None, "network_sample_age_ms": -1,
                         "network_source_age_ms": None, "network_sample_fresh": False,
                         "sample_source": None, "source_granularity_seconds": None,
                         "country": "United States" if countries == ["us"] else " / ".join(countries),
                         "country_source": "Salad deployment placement"})
    return sorted(rows, key=lambda n: (not n["current"], -n["start_ms"], n["machine"]))


class PacketStreamView:
    def __init__(self, runtime: Path, key_provider):
        self.runtime = Path(runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.key_provider = key_provider
        self.target = {name: os.environ.get(env, "").strip() or fallback for name, env, fallback in (
            ("organization", "PS_ORGANIZATION", "hyperlane"),
            ("project", "PS_PROJECT", "default"), ("group", "PS_GROUP", "ps1"))}
        target_key = "/".join(self.target.values())
        # Retain the original group's history without mixing it into replacement
        # deployments, whose current test must begin at their own start time.
        period_name = ("dashboard-periods.json" if target_key == "hyperlane/default/ps1"
                       else "dashboard-periods-" + quote(target_key, safe="") + ".json")
        self.periods_path = self.runtime / period_name
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.metadata = {}
        self.members = {}
        self.metadata_at = 0
        self.error = "Checking Salad deployment…"
        self.periods = {}
        self.last_bridge_ms = 0
        self.stop_event = threading.Event()
        try:
            self.periods = {p["id"]: p for p in json.loads(self.periods_path.read_text())}
        except (ValueError, OSError, KeyError):
            pass
        # These saved snapshots preserve starts/stops already observed before this UI.
        for path in sorted(self.runtime.glob("status-*.json")):
            try:
                value = json.loads(path.read_text())
                if value.get("name") == self.target["group"]:
                    self.remember_period(value)
            except (ValueError, OSError):
                pass

    def remember_period(self, group):
        state = group.get("current_state", {})
        start = millis(state.get("start_time"))
        if not start:
            return
        if state.get("status") == "stopped" and millis(state.get("finish_time")) <= start:
            self.periods.pop(str(start), None)
            return
        item = self.periods.setdefault(str(start), {"id": str(start), "start_ms": start, "end_ms": None})
        if state.get("status") == "stopped":
            finish = millis(state.get("finish_time"))
            if finish > start:
                item["end_ms"] = finish
        for other in self.periods.values():
            if other["start_ms"] < start and other["end_ms"] is None:
                other["end_ms"] = start

    def fetch_metadata(self):
        base = ("https://api.salad.com/api/public/organizations/" + quote(self.target["organization"], safe="")
                + "/projects/" + quote(self.target["project"], safe="")
                + "/containers/" + quote(self.target["group"], safe=""))
        key = self.key_provider()
        def get(path):
            config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\n"
            response = subprocess.run(["/usr/bin/curl", "-sS", "--max-time", "10", "--config", "-",
                                       "--write-out", "\n%{http_code}", path],
                                      input=config, capture_output=True, text=True, timeout=12)
            raw, code = response.stdout.rsplit("\n", 1)
            if response.returncode or code != "200":
                raise ValueError("Salad request failed")
            return json.loads(raw)
        try:
            group, instances = get(base), get(base + "/instances")
            with self.lock:
                self.metadata = {k: group.get(k) for k in ("name", "display_name", "current_state", "country_codes", "version")}
                self.members = {n["machine_id"]: n["state"] for n in instances["instances"]}
                self.metadata_at = int(time.time() * 1000)
                self.error = None
                self.remember_period(group)
                self.periods_path.write_text(json.dumps(list(self.periods.values())))
        except Exception:
            with self.lock:
                self.error = "Salad membership could not be refreshed."

    def run(self):
        while not self.stop_event.is_set():
            self.fetch_metadata()
            self.stop_event.wait(15)

    def readings(self):
        values = {}
        path = self.runtime / "provider-observations.jsonl"
        if not path.exists():
            return []
        for line in path.read_text().splitlines():
            try:
                value = json.loads(line)
                stamp = millis(value.get("recorded_at") or value.get("observed_at"))
                gb = float(value["traffic_sold_gb"])
                if stamp and math.isfinite(gb) and gb >= 0:
                    values[stamp] = {"time_ms": stamp, "gb": gb,
                                     "basis": "provider_bytes" if "provider_bytes" in value else "display_gb"}
            except (KeyError, ValueError, TypeError):
                pass
        return sorted(values.values(), key=lambda r: r["time_ms"])

    def ingest(self, body):
        now = int(time.time() * 1000)
        gb, stamp = float(body["gb"]), int(body["time_ms"])
        provider_bytes = body.get("bytes")
        if provider_bytes is not None:
            if not isinstance(provider_bytes, int) or not 0 <= provider_bytes <= 10**18:
                raise ValueError("Invalid provider bytes")
            gb = provider_bytes / 1e9
        if not math.isfinite(gb) or not 0 <= gb <= 1e9 or abs(now - stamp) > 120000:
            raise ValueError("Invalid provider reading")
        with self.lock:
            self.last_bridge_ms = now
            previous = self.readings()
            if previous and stamp - previous[-1]["time_ms"] < 10000:
                return
            record = {"observed_at": datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat(),
                      "traffic_sold_gb": gb, "source": "Authenticated PacketStream browser feed"}
            if provider_bytes is not None:
                record["provider_bytes"] = provider_bytes
            with (self.runtime / "provider-observations.jsonl").open("a") as out:
                out.write(json.dumps(record) + "\n")

    def snapshot(self, raw, start=None, end=None):
        now = int(time.time() * 1000)
        with self.lock:
            state = self.metadata.get("current_state", {})
            restart = millis(state.get("start_time"))
            start = restart if start is None else start
            end = now if end is None else end
            readings = self.readings()
            countries = self.metadata.get("country_codes") or ["us"]
            return {"time_ms": now, "target": dict(self.target), "restart_ms": restart, "status": state.get("status", "unknown"),
                    "running_nodes": sum(s == "running" for s in self.members.values()),
                    "membership_age_ms": now - self.metadata_at, "membership_error": self.error,
                    "nodes": ordered_nodes(raw.get("nodes", []), self.members, restart, countries),
                    "periods": sorted(self.periods.values(), key=lambda r: -r["start_ms"]),
                    "billing": paid_window(readings, start, end), "window": {"start_ms": start, "end_ms": end},
                    "recent_billing": paid_window(readings, max(restart, readings[-1]["time_ms"] - 301000), readings[-1]["time_ms"]) if readings else None,
                    "latest_reading": readings[-1] if readings else None,
                    "feed_age_ms": now - self.last_bridge_ms if self.last_bridge_ms else None,
                    "bridge_token": self.token}

`````

### `dashboard/salad_api.py`

<!-- RP_FILE: dashboard/salad_api.py SHA256: fdfad086f5d12cfcc69dd0f3012ffc7502a84b14ffdf172bd7009159ccde5f86 -->
`````python
"""Small standard-library client for Salad's structured Log Entries API."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List


class SaladAPIError(RuntimeError):
    pass


class AuthenticationError(SaladAPIError):
    pass


class RetryableAPIError(SaladAPIError):
    pass


def _parse_iso(value: str) -> datetime:
    value = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], value, count=1)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class SaladLogClient:
    def __init__(
        self,
        organization: str,
        project: str,
        container_group: str,
        key_provider: Callable[[], str],
        base_url: str = "https://api.salad.com/api/public",
        timeout: float = 30.0,
    ):
        self.organization = organization
        self.project = project
        self.container_group = container_group
        self.key_provider = key_provider
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def query(self) -> str:
        return (
            'resource.type = "container" and '
            f'resource.labels.project_name = "{self.project}" and '
            f'resource.labels.container_group_name = "{self.container_group}" and '
            '(json_log.kind = "bandwidth_sample" or '
            'json_log.kind = "honeygain_event" or '
            'json_log.kind = "bandwidth_monitor_status" or '
            'text_log = "Honeygain service disconnected")'
        )

    def fetch(self, start_time: str, end_time: str, page_size: int = 100) -> List[Dict[str, Any]]:
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")
        key = self.key_provider().strip()
        if not key:
            raise AuthenticationError("Salad API key is not configured")
        url = f"{self.base_url}/organizations/{urllib.parse.quote(self.organization, safe='')}/log-entries"
        cursor = _parse_iso(start_time)
        end = _parse_iso(end_time)
        if cursor >= end:
            return []
        request_count = 0

        def fetch_window(window_start: datetime, window_end: datetime, depth: int = 0) -> List[Dict[str, Any]]:
            nonlocal request_count
            request_count += 1
            if request_count > 4096 or depth > 64:
                raise RetryableAPIError("Salad API pagination limit reached")
            body = {
                "query": self.query,
                "start_time": _iso(window_start),
                "end_time": _iso(window_end),
                "page_size": page_size,
                "sort_order": "asc",
            }
            request = urllib.request.Request(
                url,
                json.dumps(body, separators=(",", ":")).encode("utf-8"),
                {
                    "Content-Type": "application/json",
                    "Salad-Api-Key": key,
                    "User-Agent": "salad-bandwidth-dashboard/1",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    page = json.load(response)
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403):
                    raise AuthenticationError(f"Salad API authentication failed ({exc.code})") from None
                if exc.code == 429 or exc.code >= 500:
                    raise RetryableAPIError(f"Salad API temporarily unavailable ({exc.code})") from None
                raise SaladAPIError(f"Salad API request failed ({exc.code})") from None
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                raise RetryableAPIError(f"Salad API request could not complete: {type(exc).__name__}") from None

            page_items = page.get("items")
            if not isinstance(page_items, list):
                raise RetryableAPIError("Salad API returned an invalid log page")
            if len(page_items) < page_size:
                return [item for item in page_items if isinstance(item, dict)]

            span = window_end - window_start
            midpoint = window_start + span / 2
            if midpoint <= window_start or midpoint >= window_end or span <= timedelta(milliseconds=1):
                raise RetryableAPIError("too many Salad logs share one pagination timestamp")
            return fetch_window(window_start, midpoint, depth + 1) + fetch_window(midpoint, window_end, depth + 1)

        items = fetch_window(cursor, end)
        unique: Dict[str, Dict[str, Any]] = {}
        for item in items:
            identity = json.dumps(item, sort_keys=True, separators=(",", ":"))
            unique[identity] = item
        return sorted(
            unique.values(),
            key=lambda item: (
                str(item.get("time") or ""),
                str(item.get("receive_time") or ""),
                str(((item.get("resource") or {}).get("labels") or {}).get("instance_id") or ""),
                int((item.get("json_log") or {}).get("sequence") or 0),
            ),
        )

`````

### `dashboard/server.py`

<!-- RP_FILE: dashboard/server.py SHA256: 436a98372e33f7d261707c670b3afee82270b3f379455b0fd07732a07768f808 -->
`````python
#!/usr/bin/env python3
"""Loopback-only API, poller, and static server for the bandwidth dashboard."""

from __future__ import annotations

import argparse
import csv
from http.client import HTTPConnection, HTTPException
import getpass
import io
import json
import sqlite3
from contextlib import closing
import math
import mimetypes
import os
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import parse_qs, urlparse

from dashboard.salad_api import SaladLogClient
from dashboard.store import APP_NAMES, Store, parse_time_ms
from dashboard.packetstream import PacketStreamView
from dashboard.fleet_test import FleetTestView, fleet_csv
from dashboard.native_network import NetworkMinutes, saved_minutes, bucket_minutes


HOST = "127.0.0.1"
DEFAULT_PORT = 8787
MAX_POINTS = 2000


def iso_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def query_window(query: Dict[str, list]) -> tuple:
    try:
        start = int(query.get("start", [""])[0])
        end = int(query.get("end", [""])[0])
        requested_bucket = int(query.get("bucket", ["1"])[0])
    except (TypeError, ValueError):
        raise ValueError("start, end, and bucket must be integers") from None
    if end <= start:
        raise ValueError("end must be after start")
    if requested_bucket < 1 or requested_bucket > 86400:
        raise ValueError("bucket must be between 1 and 86400 seconds")
    minimum_bucket = max(1, math.ceil((end - start) / 1000 / MAX_POINTS))
    return start, end, max(requested_bucket, minimum_bucket)


def csv_export(series: Dict[str, Any]) -> bytes:
    output = io.StringIO(newline="")
    fields = [
        "time_utc",
        "sample_count",
        "instance_ids",
        "coverage_percent",
        "eth0_rx_bytes_per_second",
        "eth0_tx_bytes_per_second",
        "captured_rx_bytes_per_second",
        "captured_tx_bytes_per_second",
        "unassigned_rx_bytes_per_second",
        "unassigned_tx_bytes_per_second",
    ]
    for app in APP_NAMES:
        fields.extend((f"{app}_rx_bytes_per_second", f"{app}_tx_bytes_per_second"))
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for point in series["points"]:
        row = {
            "time_utc": iso_ms(point["time_ms"]),
            "sample_count": point["sample_count"],
            "instance_ids": ";".join(point["instance_ids"]),
            "coverage_percent": point["coverage_percent"],
            "eth0_rx_bytes_per_second": point["eth0"]["rx_bytes_per_second"],
            "eth0_tx_bytes_per_second": point["eth0"]["tx_bytes_per_second"],
            "captured_rx_bytes_per_second": point["captured"]["rx_bytes_per_second"],
            "captured_tx_bytes_per_second": point["captured"]["tx_bytes_per_second"],
            "unassigned_rx_bytes_per_second": point["unassigned"]["rx_bytes_per_second"],
            "unassigned_tx_bytes_per_second": point["unassigned"]["tx_bytes_per_second"],
        }
        for app in APP_NAMES:
            row[f"{app}_rx_bytes_per_second"] = point["applications"][app]["rx_bytes_per_second"]
            row[f"{app}_tx_bytes_per_second"] = point["applications"][app]["tx_bytes_per_second"]
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def make_handler(store: Store, status_provider: Callable[[], Dict[str, Any]], static_dir: Path, ps_view=None, expected_reporters: int = 10, fleet_view=None, minute_view=None):
    static_dir = Path(static_dir)
    fleet_view = fleet_view or FleetTestView(Path(os.environ.get("FLEET_TEST_DIR", str(Path.home() / ".hg1" / "fleet-tests"))))

    class Handler(BaseHTTPRequestHandler):
        server_version = "SaladBandwidthDashboard/1"

        def log_message(self, *_args):
            return

        def headers_common(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")

        def send_bytes(self, status: int, body: bytes, content_type: str, disposition: str = "") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if disposition:
                self.send_header("Content-Disposition", disposition)
            self.headers_common()
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status: int, value: Any, disposition: str = "") -> None:
            body = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
            self.send_bytes(status, body, "application/json; charset=utf-8", disposition)

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/proxyrack":
                    result = json.loads((Path.home() / ".hg1/proxyrack/view.json").read_text())
                    path=Path.home()/".hg1/proxyrack/traffic.sqlite3"
                    result["minutes"] = saved_minutes(path, group_id=result["group_id"])
                    if path.exists():
                        with closing(sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)) as db:
                            amount=db.execute("SELECT SUM(rx+tx) FROM minutes WHERE valid=1 AND seq>0 AND group_id=?",(result["group_id"],)).fetchone()[0]
                        result["total_recorded_mb"]=amount/1e6 if amount is not None else None
                    self.send_json(200, result)
                    return
                if parsed.path == "/api/traffmonetizer":
                    from dashboard.traffmonetizer import snapshot
                    result = snapshot()
                    path = Path.home()/".hg1/traffmonetizer/traffic.sqlite3"
                    if path.exists() and parse_qs(parsed.query).get("chart")==["1"]:
                        now=int(time.time()*1000); first=now//60000*60000-1439*60000
                        test_start=result.get("deployment",{}).get("measurement_started_ms",0)
                        points={}
                        with closing(sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)) as db:
                            db.row_factory=sqlite3.Row; db.execute("BEGIN")
                            rows=db.execute("""SELECT CAST(time_ms/60000 AS INTEGER)*60000 minute,run,instance,machine,ip,
                                SUM(rx+tx)/1e6 mb,
                                SUM(time_ms-MAX(start_ms,CAST(time_ms/60000 AS INTEGER)*60000)) coverage_ms,
                                SUM(MAX(0,CAST(time_ms/60000 AS INTEGER)*60000-start_ms)) previous_coverage_ms
                                FROM samples WHERE time_ms>=? AND start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL
                                GROUP BY minute,run,instance,machine,ip ORDER BY minute""",(first,test_start)).fetchall()
                            total=db.execute("SELECT SUM(rx) rx,SUM(tx) tx,COUNT(*) samples,MIN(time_ms) first_ms,MAX(time_ms) last_ms FROM samples WHERE start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL",(test_start,)).fetchone()
                            result["recorded"]=dict(total)
                        for row in rows:
                            point=points.setdefault(row["minute"],{"minute_ms":row["minute"],"mb":0,"nodes":[],"duration_ms":0})
                            point["mb"]+=row["mb"];point["duration_ms"]+=row["coverage_ms"]
                            previous=points.get(row["minute"]-60000)
                            if previous is not None: previous["duration_ms"]+=row["previous_coverage_ms"]
                            point["nodes"].append({"instance":row["instance"],"ip":row["ip"],"mb":row["mb"]})
                        for point in points.values():
                            point["count"]=len(point["nodes"])
                            point["nodes"]=sorted(point["nodes"],key=lambda n:-n["mb"])[:20]
                            point["partial"]=point.pop("duration_ms")<result.get("deployment",{}).get("desired_replicas",10)*60000
                        result["chart_minutes"]=list(points.values())
                    self.send_json(200,result)
                    return
                if parsed.path == "/api/earnfm":
                    path = static_dir/"earnfm.json"
                    result=json.loads(path.read_text()) if path.exists() else {"error":"EarnFM recorder has not published data yet", "desired":10,"workers":[],"points":[]}
                    self.send_json(200,result)
                    return
                if parsed.path == "/api/repocket":
                    data_dir = Path.home() / ".hg1" / "repocket"
                    result = json.loads((data_dir / "view.json").read_text())
                    if (data_dir / "provider.json").exists():
                        result["provider"] = json.loads((data_dir / "provider.json").read_text())
                    if parse_qs(parsed.query).get("chart")==["1"] and (data_dir/"traffic.sqlite3").exists():
                        now=int(time.time()*1000); first=now//60000*60000-1439*60000
                        with closing(sqlite3.connect("file:"+str(data_dir/"traffic.sqlite3")+"?mode=ro",uri=True)) as db:
                            db.execute("BEGIN")
                            raw=[json.loads(row[0]) for row in db.execute("SELECT body FROM events WHERE kind='minute' AND time_ms>=?",(first,))]
                            total=db.execute("SELECT SUM(json_extract(body,'$.rx_bytes')+json_extract(body,'$.tx_bytes')),MIN(json_extract(body,'$.start_ms')) FROM events WHERE kind='minute' AND json_extract(body,'$.rx_bytes')>=0 AND json_extract(body,'$.tx_bytes')>=0").fetchone()
                        records=[]
                        for row in raw:
                            if row.get("rx_bytes") is None or row.get("tx_bytes") is None or row["rx_bytes"]<0 or row["tx_bytes"]<0:continue
                            record={"start_ms":row["start_ms"],"end_ms":row["end_ms"],"rx":row["rx_bytes"],"tx":row["tx_bytes"],"bucket_ms":None,"instance":row["instance"],"machine":row["machine"],"ip":row.get("ip")}
                            bucket=round(row["start_ms"]/60000)*60000
                            if not row.get("partial") and 59000<=row["end_ms"]-row["start_ms"]<=61000 and abs(row["start_ms"]-bucket)<=1000:
                                record.update(start_ms=bucket,end_ms=bucket+60000,bucket_ms=bucket)
                            records.append(record)
                        result["chart_minutes"]=bucket_minutes(records,first,now//60000*60000)
                        for point in result["chart_minutes"]:point["partial"]|=point["count"]<result["desired"]
                        result["total_network_mb"]=total[0]/1e6 if total[0] is not None else None
                        result["test_started_ms"]=total[1]
                    self.send_json(200, result)
                    return
                if parsed.path == "/api/ps1/minutes" and minute_view is not None:
                    query = parse_qs(parsed.query)
                    census = json.loads((minute_view.path.parent / "native-census.json").read_text())
                    selected = int(query["minute"][0]) if "minute" in query else None
                    if selected is not None and (selected < 0 or selected % 60000):
                        raise ValueError("Invalid selected minute")
                    self.send_json(200, minute_view.minute(census.get("group_id", ""), selected) if selected is not None else minute_view.snapshot(census))
                    return
                if parsed.path in ("/api/fleet-test", "/api/fleet-test/export.json", "/api/fleet-test/export.csv"):
                    archive = parse_qs(parsed.query).get("archive", [None])[0]
                    result = fleet_view.snapshot(archive=archive, include_observations=parsed.path.endswith(".json"), honeygain_only=parse_qs(parsed.query).get("service") == ["hg"])
                    if parsed.path.endswith(".csv"):
                        self.send_bytes(200, fleet_csv(result), "text/csv; charset=utf-8", 'attachment; filename="independent-fleet-test.csv"')
                    else:
                        self.send_json(200, result, 'attachment; filename="independent-fleet-test.json"' if parsed.path.endswith(".json") else "")
                    return
                if parsed.path == "/api/ps1/view" and ps_view is not None:
                    query = parse_qs(parsed.query)
                    start = int(query["start"][0]) if "start" in query else None
                    end = int(query["end"][0]) if "end" in query else None
                    if start is not None and (start < 0 or (end is not None and end <= start)):
                        raise ValueError("Invalid period")
                    raw = {}
                    connection = HTTPConnection("127.0.0.1", 8789, timeout=4)
                    try:
                        connection.request("GET", "/api/ps1/status")
                        response = connection.getresponse()
                        if response.status == 200:
                            raw = json.loads(response.read())
                    except (OSError, HTTPException, ValueError):
                        pass
                    finally:
                        connection.close()
                    self.send_json(200, ps_view.snapshot(raw, start, end))
                    return
                if parsed.path in ("/api/ps1/status", "/api/ps1/history"):
                    # Fixed loopback target; browser input cannot select an upstream.
                    target = parsed.path
                    if parsed.path.endswith("/history"):
                        after = int(parse_qs(parsed.query).get("after", ["0"])[0])
                        if after < 0:
                            raise ValueError("after must be a non-negative integer")
                        target += f"?after={after}"
                    connection = HTTPConnection("127.0.0.1", 8789, timeout=4)
                    try:
                        connection.request("GET", target, headers={"Accept": "application/json"})
                        upstream = connection.getresponse()
                        body = upstream.read()
                        if upstream.status != 200:
                            self.send_json(503, {"error": f"PS1 recorder returned HTTP {upstream.status}"})
                        else:
                            self.send_bytes(200, body, "application/json; charset=utf-8")
                    except (OSError, HTTPException):
                        self.send_json(503, {"error": "PS1 recorder is unavailable"})
                    finally:
                        connection.close()
                    return
                if parsed.path == "/api/status":
                    result = store.status()
                    result.update(status_provider())
                    last_sample_ms = result.get("last_sample_ms")
                    result["source_lag_ms"] = (
                        max(0, int(time.time() * 1000) - int(last_sample_ms))
                        if last_sample_ms is not None
                        else None
                    )
                    self.send_json(200, result)
                    return
                if parsed.path == "/api/boxes":
                    start, end, _bucket = query_window(parse_qs(parsed.query))
                    self.send_json(200, store.query_boxes(start, end, expected_reporters=expected_reporters))
                    return
                if parsed.path == "/api/events":
                    start, end, _bucket = query_window(parse_qs(parsed.query))
                    self.send_json(200, store.query_events(start, end))
                    return
                if parsed.path in ("/api/series", "/api/export.csv", "/api/export.json"):
                    start, end, bucket = query_window(parse_qs(parsed.query))
                    result = store.query_range(start, end, bucket)
                    if parsed.path == "/api/export.csv":
                        self.send_bytes(200, csv_export(result), "text/csv; charset=utf-8", 'attachment; filename="salad-bandwidth.csv"')
                    elif parsed.path == "/api/export.json":
                        self.send_json(200, result, 'attachment; filename="salad-bandwidth.json"')
                    else:
                        self.send_json(200, result)
                    return
                files = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/ps1.js": "ps1.js", "/fleet-test.js": "fleet-test.js", "/styles.css": "styles.css"}
                files.update({"/rp": "repocket.html", "/repocket": "repocket.html", "/repocket.html": "repocket.html"})
                files.update({"/proxyrack": "proxyrack.html", "/proxyrack.html": "proxyrack.html"})
                files.update({"/ef": "earnfm.html", "/earnfm": "earnfm.html", "/earnfm.html": "earnfm.html", "/ef.json": "earnfm.json", "/earnfm.json": "earnfm.json"})
                files.update({alias:"index.html" for path in ("/proxyrack","/rp","/repocket","/earnfm","/traffmonetizer","/tm") for alias in (path,path+".html")})
                filename = files.get(parsed.path)
                if filename is None:
                    self.send_json(404, {"error": "not found"})
                    return
                body = (static_dir / filename).read_bytes()
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                self.send_bytes(200, body, content_type + ("; charset=utf-8" if content_type.startswith("text/") or content_type.endswith("javascript") else ""))
            except ValueError as exc:
                self.send_json(400, {"error": str(exc)})
            except FileNotFoundError:
                self.send_json(404, {"error": "dashboard asset not found"})
            except Exception:
                self.send_json(500, {"error": "internal dashboard error"})

        def do_POST(self):  # noqa: N802
            if self.path != "/api/ps1/credited" or ps_view is None:
                self.send_json(404, {"error": "not found"})
                return
            if self.headers.get("X-PS-Token") != ps_view.token or self.headers.get("Origin", "http://127.0.0.1:8787") != "http://127.0.0.1:8787":
                self.send_json(403, {"error": "Local dashboard authentication required"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 2048:
                    raise ValueError("Invalid reading size")
                ps_view.ingest(json.loads(self.rfile.read(size)))
                self.send_json(200, {"ok": True})
            except (ValueError, TypeError, KeyError):
                self.send_json(400, {"error": "Invalid provider reading"})

    return Handler


class Poller:
    def __init__(
        self,
        store: Store,
        client: SaladLogClient,
        interval_seconds: int = 1,
        overlap_seconds: int = 2,
        settlement_seconds: int = 10,
        initial_lookback_seconds: int = 60,
        reconcile_horizon_seconds: int = 3600,
        reconcile_chunk_seconds: int = 60,
        reconcile_interval_seconds: int = 10,
    ):
        self.store = store
        self.client = client
        self.interval_seconds = interval_seconds
        self.overlap_ms = overlap_seconds * 1000
        self.settlement_ms = settlement_seconds * 1000
        self.initial_lookback_ms = initial_lookback_seconds * 1000
        self.reconcile_horizon_ms = reconcile_horizon_seconds * 1000
        self.reconcile_chunk_ms = reconcile_chunk_seconds * 1000
        self.reconcile_interval_ms = reconcile_interval_seconds * 1000
        self._reconcile_cursor_ms: Optional[int] = None
        self._next_reconcile_ms: Optional[int] = None
        self._last_reconcile_start_ms: Optional[int] = None
        self._last_reconcile_end_ms: Optional[int] = None
        self._last_reconcile_final_start_ms: Optional[int] = None
        self._last_reconcile_final_end_ms: Optional[int] = None
        self.stop_event = threading.Event()
        self._lock = threading.Lock()
        self._status: Dict[str, Any] = {"poll_state": "starting"}
        self._maintenance_at = 0.0

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._status)

    def run_once(self, now_ms: Optional[int] = None) -> int:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        settled_end_ms = max(0, now_ms - self.settlement_ms)
        watermark = self.store.watermark_ms()
        start_ms = max(
            0,
            (watermark - self.overlap_ms)
            if watermark is not None
            else settled_end_ms - self.initial_lookback_ms,
        )
        try:
            entries = self.client.fetch(iso_ms(start_ms), iso_ms(settled_end_ms), page_size=100)
            reconcile_due = self._next_reconcile_ms is None or now_ms >= self._next_reconcile_ms
            if (
                reconcile_due
                and self.reconcile_horizon_ms > 0
                and self.reconcile_chunk_ms > 0
                and self.reconcile_interval_ms > 0
            ):
                self._next_reconcile_ms = now_ms + self.reconcile_interval_ms
                reconcile_floor = max(0, settled_end_ms - self.reconcile_horizon_ms)
                reconcile_limit = max(reconcile_floor, settled_end_ms - self.overlap_ms)
                reconcile_slice_ms = max(1000, self.reconcile_chunk_ms // 2)
                if self._reconcile_cursor_ms is None:
                    self._reconcile_cursor_ms = reconcile_floor
                if self._reconcile_cursor_ms < reconcile_floor or self._reconcile_cursor_ms >= reconcile_limit:
                    self._reconcile_cursor_ms = reconcile_floor
                reconcile_start_ms = self._reconcile_cursor_ms
                reconcile_end_ms = min(reconcile_start_ms + reconcile_slice_ms, reconcile_limit)
                if reconcile_end_ms > reconcile_start_ms:
                    entries.extend(
                        self.client.fetch(iso_ms(reconcile_start_ms), iso_ms(reconcile_end_ms), page_size=100)
                    )
                    self._reconcile_cursor_ms = (
                        reconcile_floor if reconcile_end_ms >= reconcile_limit else reconcile_end_ms
                    )
                    self._last_reconcile_start_ms = reconcile_start_ms
                    self._last_reconcile_end_ms = reconcile_end_ms

                # Every event-time slice receives a final check as it reaches the
                # configured lateness horizon. This prevents a log that arrived
                # just after the rolling sweep from aging out unseen.
                final_start_ms = reconcile_floor
                final_end_ms = min(final_start_ms + reconcile_slice_ms, reconcile_limit)
                if final_end_ms > final_start_ms and (final_start_ms, final_end_ms) != (
                    reconcile_start_ms,
                    reconcile_end_ms,
                ):
                    entries.extend(self.client.fetch(iso_ms(final_start_ms), iso_ms(final_end_ms), page_size=100))
                if final_end_ms > final_start_ms:
                    self._last_reconcile_final_start_ms = final_start_ms
                    self._last_reconcile_final_end_ms = final_end_ms
            inserted = self.store.ingest_many(entries)
            next_watermark = settled_end_ms if entries else (watermark if watermark is not None else start_ms)
            self.store.record_poll(next_watermark, inserted, now_ms=now_ms)
            if time.monotonic() >= self._maintenance_at:
                self.store.rollup()
                self.store.prune(now_ms=now_ms)
                self._maintenance_at = time.monotonic() + 3600
            with self._lock:
                self._status = {
                    "poll_state": "ok",
                    "last_fetch_count": len(entries),
                    "last_insert_count": inserted,
                    "settled_through_ms": settled_end_ms,
                    "reconcile_start_ms": self._last_reconcile_start_ms,
                    "reconcile_end_ms": self._last_reconcile_end_ms,
                    "reconcile_final_start_ms": self._last_reconcile_final_start_ms,
                    "reconcile_final_end_ms": self._last_reconcile_final_end_ms,
                    "tail_fetch_interval_seconds": self.interval_seconds,
                    "tail_overlap_seconds": self.overlap_ms // 1000,
                    "settlement_seconds": self.settlement_ms // 1000,
                    "reconcile_interval_seconds": self.reconcile_interval_ms // 1000,
                }
            return inserted
        except Exception as exc:
            safe_error = f"{type(exc).__name__}: {exc}"
            self.store.record_poll(watermark or start_ms, 0, error=safe_error, now_ms=now_ms)
            with self._lock:
                self._status = {"poll_state": "error", "poll_error": safe_error[:500]}
            return 0

    def run(self) -> None:
        while not self.stop_event.is_set():
            self.run_once()
            self.stop_event.wait(self.interval_seconds)

    def stop(self) -> None:
        self.stop_event.set()


def key_provider(helper: Path) -> str:
    environment_key = os.environ.get("SALAD_API_KEY", "").strip()
    if environment_key:
        return environment_key
    result = subprocess.run(
        [str(helper), "--read", "--service", "salad-bandwidth-api", "--account", getpass.getuser()],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".salad-bandwidth-monitor")
    parser.add_argument("--no-poll", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    helper = repo_root / ".runtime" / "keychain-store"
    store = Store(args.data_dir / "bandwidth.sqlite3")
    poller: Optional[Poller] = None
    if not args.no_poll:
        client = SaladLogClient(
            os.environ.get("SALAD_ORGANIZATION", "cosmosgeeketh"),
            os.environ.get("SALAD_PROJECT", "default"),
            os.environ.get("SALAD_CONTAINER_GROUP", "honeygain-canary"),
            lambda: key_provider(helper),
        )
        poller = Poller(store, client)
        threading.Thread(target=poller.run, name="salad-log-poller", daemon=True).start()

    status = poller.status if poller else (lambda: {"poll_state": "disabled"})
    ps_runtime = Path(os.environ.get("PS_MONITOR_DIR", str(args.data_dir / "packetstream")))
    ps_view = PacketStreamView(ps_runtime, lambda: key_provider(helper))
    minute_view = NetworkMinutes(ps_runtime / "minutes.sqlite3")
    threading.Thread(target=ps_view.run, name="ps-deployment-metadata", daemon=True).start()
    expected_reporters = max(1, int(os.environ.get("SALAD_EXPECTED_REPORTERS", "10")))
    server = ThreadingHTTPServer((HOST, args.port), make_handler(store, status, Path(__file__).parent / "static", ps_view, expected_reporters, minute_view=minute_view))

    def stop_server(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop_server)
    signal.signal(signal.SIGINT, stop_server)
    print(f"dashboard: http://{HOST}:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        ps_view.stop_event.set()
        if poller:
            poller.stop()
        server.server_close()
        minute_view.db.close()
        store.close()


if __name__ == "__main__":
    main()

`````

### `dashboard/static/fleet-test.js`

<!-- RP_FILE: dashboard/static/fleet-test.js SHA256: 249c8547b6ae702c92cc954f8b0453ec280f9e08366c604df7dddb521dd2fe89 -->
`````javascript
"use strict";
(() => {
  const valid = value => typeof value === "number" && Number.isFinite(value);
  const num = (value, digits = 3) => valid(value) ? value.toLocaleString(undefined, {maximumFractionDigits: digits}) : "Unknown";
  const fresh = (age, limit) => valid(age) && age >= 0 && age <= limit;
  const CLIENTS = {running: "Accepted", error: "Client error", accepted: "Accepted", connected: "Connected", exited: "Client exited", device_limit: "Device limit", device_already_active: "Device already active", network_overused: "Network overused", network_unusable: "Network unusable", authorization_error: "Authorization failed", connected_last_observed_telemetry_stale: "Connection unverified", connected_last_observed_telemetry_unverified: "Connection unverified", starting: "Starting", waiting: "Waiting", rejected: "Rejected", unknown: "Unknown", unverified: "Unverified", disconnected: "Disconnected", reallocating: "Reallocating"};
  const ERRORS = {device_limit: "Provider device limit reached.", device_already_active: "Provider reports this device is already active.", network_overused: "Provider reports this network is overused.", network_unusable: "Provider cannot use this network.", authorization_error: "Provider authorization failed.", observer_error: "Observer could not verify this container.", disconnected: "Client disconnected; automatic reallocation after 2 minutes without recovery."};
  function workerState(service, worker, data) {
    const source = data.latest?.[service] || {};
    const native = service === "ps" && (worker.native_status_only === true || ["native_status_only", "native_sysfs_1s", "sysfs_via_salad_logs_1s"].includes(worker.sample_source));
    const observerFresh = !data.recorder_stale && (service !== "hg" || !source.status_stale) && (!native || fresh(source.status_age_ms, 90000));
    const clientFresh = observerFresh && fresh(service === "hg" ? worker.received_age_ms : worker.client_status_age_ms, native ? 240000 : 120000);
    const knownState = ["running", "stopped", "stopping", "pending", "starting", "allocating", "creating", "deploying", "failed", "succeeded"].includes(worker.state);
    const client = CLIENTS[worker.client_status] || "Unknown";
    const accepted = service === "hg" ? worker.client_status === "connected" : ["accepted", "running"].includes(worker.client_status);
    const bad = ["error", "exited", "device_limit", "device_already_active", "network_overused", "network_unusable", "authorization_error", "rejected"].includes(worker.client_status);
    const working = clientFresh && worker.state === "running" && accepted && !worker.error_code;
    const knownFailure = observerFresh && ((knownState && worker.state !== "running") || (clientFresh && (bad || Boolean(worker.error_code) && worker.error_code !== "observer_error")));
    const networkFresh = observerFresh && (service === "hg" ? fresh(worker.received_age_ms, 120000) : fresh(worker.received_age_ms, ["native_sysfs_1s", "sysfs_via_salad_logs_1s"].includes(worker.sample_source) ? 45000 : worker.sample_source === "salad_logs_10s" ? 25000 : 15000) && valid(worker.source_age_ms) && worker.source_age_ms >= -15000 && worker.source_age_ms <= 60000);
    return {working, unknown: !working && !knownFailure, client, networkFresh, observerFresh, clientFresh,
      label: working ? "Working" : knownFailure ? "Needs attention" : "Unknown",
      tone: working ? "ok" : knownFailure ? "bad" : "warn"};
  }
  function serviceModel(service, data) {
    const source = data.latest?.[service] || {};
    const desired = Math.min(50, data.experiment?.[service]?.desired || 10);
    const workers = [...(source.workers || [])];
    while (workers.length < desired) workers.push({state: "unknown", client_status: "unknown"});
    const states = workers.map(worker => workerState(service, worker, data));
    const providerFresh = !data.recorder_stale && fresh(source.provider_age_ms, service === "hg" ? 360000 : 180000);
    const earnings = data.summary?.[service === "hg" ? "hg_gathering_credits" : "ps_credited_mb"];
    const network = data.summary?.[`${service}_network_mb`];
    const networkKnown = !data.recorder_stale && (service !== "hg" || !source.status_stale) && source.network_complete === true && states.length >= desired && states.every(s => s.networkFresh) && valid(network);
    return {source, desired, workers, states, working: states.filter(s => s.working).length, unknown: states.filter(s => s.unknown).length,
      providerFresh, earnings, earningsKnown: providerFresh && valid(earnings), network, networkKnown};
  }
  function chartValue(metric) {
    if (!metric || !valid(metric.delta) || ["counter_reset", "gap"].includes(metric.status) || (metric.status === "incomplete" && metric.delta === 0)) return null;
    return metric.delta;
  }
  function windowStart(service, data) {
    const value = data.service_windows?.[service]?.start_ms;
    return valid(value) ? value : data.experiment?.started_ms;
  }
  function displayedIntervals(service, kind, data) {
    const start = windowStart(service, data);
    return (data.timeline?.[service]?.[kind] || []).filter(p => !valid(start) || p.start_ms >= start);
  }
  const SERVICES=[
    {id:'hg',hash:'#hg1',name:'Honeygain',url:'/api/fleet-test?service=hg'},
    {id:'ps',hash:'#ps1',name:'PacketStream',url:'/api/ps1/minutes'},
    {id:'proxyrack',hash:'#proxyrack',name:'Proxyrack',url:'/api/proxyrack'},
    {id:'rp',hash:'#rp',name:'Repocket',url:'/api/repocket?chart=1'},
    {id:'earnfm',hash:'#earnfm',name:'RFM',url:'/api/earnfm'},
    {id:'tm',hash:'#tm',name:'Traffic Monetizer',url:'/api/traffmonetizer?chart=1'}
  ];
  const shown=(value,digits=3)=>valid(value)?num(value,digits):'—';
  const mb=value=>valid(value)?shown(value)+' MB':'Not reported';
  const usd=value=>valid(value)?'$'+shown(value,6):'Not reported';
  const diff=(end,start)=>valid(end)&&valid(start)&&end>=start?end-start:null;
  const normalizeMinute=(time,amount,nodes=[],partial=false,estimated=false)=>({minute_ms:time,mb:valid(amount)?amount:null,partial,estimated,count:nodes.length,nodes:[...nodes].sort((a,b)=>b.mb-a.mb).slice(0,20)});
  function normalize(service,d,now=Date.now(),billing=null){
    const result={at:now,statusFresh:true,name:SERVICES.find(s=>s.id===service)?.name,desired:10,running:null,working:0,total:null,start:null,source:d.generated_ms,credited:'Not reported',earned:'Not reported',creditNote:'',notice:'',nodes:[],minutes:[],estimated:false};
    const delay=valid(d.generated_ms)?now-d.generated_ms:Infinity,recordingFresh=delay>=-10000&&delay<=90000;
    if(service==='hg'){
      const m=serviceModel('hg',d),s=m.source;
      result.desired=m.desired;result.running=s.running;result.working=m.working;result.total=valid(s.network_total_bytes)?s.network_total_bytes/1e6:m.network;result.start=windowStart('hg',d);result.source=s.status_observed_ms;result.minutes=d.hg_minutes||[];result.estimated=true;result.statusFresh=Boolean(d.latest?.hg)&&!d.recorder_stale&&!s.status_stale;
      const intervals=displayedIntervals('hg','provider',d).filter(p=>valid(p.per_second)&&chartValue(p)!==null),credits=intervals.length?intervals.reduce((sum,p)=>sum+p.delta,0):null;
      result.credited=valid(credits)?shown(credits)+' credits':'Not reported';result.earned=valid(credits)?shown(credits)+' credits':'Not reported';
      result.creditNote='Honeygain gathering credits from recorded intervals'+(m.providerFresh?'':'; provider reading is stale');
      if(d.recorder_stale||s.status_stale)result.notice='Honeygain recorder or client status is stale.';
      result.nodes=m.workers.map((w,i)=>({id:w.machine||w.group||String(i),ip:w.ip,status:m.states[i].clientFresh?m.states[i].client:'Unverified',salad:w.state,working:m.states[i].working,
        rate:m.states[i].networkFresh&&valid(w.network_interval?.per_second)?w.network_interval.per_second*60/1e6:null,total:valid(w.network_bytes)?w.network_bytes/1e6:null,
        duration:diff(w.network_last_ms,w.network_first_ms),age:w.received_age_ms,error:ERRORS[w.error_code]||''}));
    }else if(service==='ps'){
      result.desired=d.desired||10;result.running=(d.nodes||[]).filter(n=>n.salad_state==='running').length;result.working=d.running;result.total=d.total_mb;result.start=d.started_ms;result.source=valid(d.inventory_age_ms)?d.time_ms-d.inventory_age_ms:null;result.minutes=d.candles||[];result.estimated=result.minutes.some(m=>m.estimated);result.statusFresh=d.inventory_fresh;
      result.notice=d.collector?.error||(!d.inventory_fresh?'PacketStream inventory is stale.':'');
      result.nodes=(d.nodes||[]).map(n=>({id:n.instance,ip:n.ip,status:n.status,salad:n.salad_state,working:n.status==='Running',rate:n.metrics_fresh?n.latest_mb_per_minute:null,total:n.total_mb,duration:valid(n.elapsed_seconds)?n.elapsed_seconds*1000:null,age:n.sample_age_ms,error:n.error||''}));
      const readings=(billing?.billing?.readings||[]).filter(r=>valid(r.time_ms)&&valid(d.started_ms)&&r.time_ms>=d.started_ms&&valid(r.gb));
      if(readings.length>=2&&readings.every((r,i)=>!i||r.gb>=readings[i-1].gb))result.credited=mb((readings.at(-1).gb-readings[0].gb)*1000);
      result.creditNote=readings.length<2?'PacketStream has no provider baseline and follow-up for this recording. Earnings are not reported.':'Provider credited traffic comes from account readings; earnings are not reported.';
      if(!valid(billing?.feed_age_ms)||billing.feed_age_ms>180000)result.creditNote+=' Provider feed is stale.';
    }else if(service==='proxyrack'){
      result.desired=d.requested||10;result.running=recordingFresh&&!d.cloud_error?(d.workers||[]).filter(w=>w.salad_state?.toLowerCase()==='running').length:null;result.total=valid(d.total_recorded_mb)?d.total_recorded_mb:d.network_mb;result.start=Date.parse(d.started_at);result.minutes=(d.minutes||[]).map(m=>({...m,partial:m.partial||m.count<(d.requested||10)}));result.estimated=result.minutes.some(m=>m.estimated);result.statusFresh=recordingFresh&&!d.cloud_error;
      result.credited=mb(d.credited_mb);result.creditNote='Cached PR credited bandwidth includes replaced replicas. Readings available for '+(d.credited_devices||0)+'/'+result.desired+' current devices. Network RX + TX counts both sides of relayed traffic and includes overhead.'+(d.balance?' Account balance '+d.balance+' covers the whole account.':'')+' Earnings for this group are not reported. Connection status comes from registered client logs; provider API checks are paced below its five requests/minute limit.';
      result.notice=d.cloud_error||(!recordingFresh?'Proxyrack recorder is stale.':'');
      result.nodes=(d.workers||[]).map(w=>{
        const networkFresh=recordingFresh&&!d.cloud_error&&valid(w.sample_age_ms)&&fresh(w.sample_age_ms+delay,150000),ip=w.provider_status?.match(/(?:Online|Offline):\s*(\S+)/i)?.[1];
        const connected=networkFresh&&w.fresh&&!w.client_error&&w.client_state==='running'&&w.salad_state?.toLowerCase()==='running';
        return {id:w.name,ip,status:connected?'Connected':w.client_error==='registration_pending'?'Registration pending':w.status||'Unverified',salad:w.salad_state,working:connected,rate:networkFresh&&w.fresh?w.mb_per_minute:null,total:w.network_mb,duration:null,age:valid(w.sample_age_ms)?w.sample_age_ms+delay:null,error:w.client_error||w.provider_error||''};
      });result.working=result.nodes.filter(n=>n.working).length;
    }else if(service==='rp'){
      result.desired=d.desired||10;result.running=recordingFresh?d.running:null;result.total=d.total_network_mb;result.start=d.test_started_ms||Math.min(...(d.workers||[]).map(w=>w.started_ms).filter(valid));result.source=d.generated_ms;result.statusFresh=recordingFresh&&!d.error;
      result.notice=d.error||(!recordingFresh?'Repocket recorder is stale.':'');
      result.nodes=(d.workers||[]).filter(w=>w.current!==false).map(w=>{const recent=recordingFresh&&!d.error&&fresh(now-w.source_ms,60000),diag=w.diagnostics,notes=[];
        if(w.reason)notes.push(w.reason);const policy=w.policy;
        if(policy&&recent){notes.push(policy.state==='observing'?'Auto replacement: observing '+shown(policy.observed_ms/60000,1)+'/'+shown(policy.window_ms/60000,0)+' min':policy.state==='reallocating'?'Auto replacement: reallocating':policy.state==='keeping'?'Auto replacement: keeping this node':'Auto replacement: '+policy.state.replaceAll('_',' '));if(valid(policy.target_bytes)&&fresh(now-policy.checked_ms,60000))notes.push('Recent window: '+shown(policy.target_bytes/1e6)+' MB target traffic; '+policy.failures+'/'+policy.outcomes+' failed-before-reply outcomes');const errors=Object.entries(fresh(now-policy.checked_ms,60000)?policy.errors||{}:{}).sort((a,b)=>b[1]-a[1]).slice(0,3);if(errors.length)notes.push('Recent errors: '+errors.map(([name,n])=>name+': '+n).join('; '));}else notes.push('Replacement status not yet reported');
        if(!diag||!recent||!fresh(now-diag.time_ms,60000))notes.push('Target diagnostics unavailable');
        return {id:w.instance||w.run,ip:w.ip,status:recent?(w.status==='connected'?'Connected (control)':w.status):'Unverified',salad:w.salad_state,working:recent&&w.phase==='connected'&&w.salad_state==='running',rate:recent?w.last_mb_per_minute:null,total:w.total_mb,duration:diff(w.last_end_ms,w.started_ms),age:diff(now,w.source_ms),error:notes.join(' · ')};});
      result.working=result.nodes.filter(n=>n.working).length;
      result.minutes=d.chart_minutes||(d.minutes||[]).map(m=>normalizeMinute(m.time_ms,m.mb,(m.contributions||[]).map(n=>({instance:n.instance||n.run,ip:n.ip,mb:n.mb})),m.partial));
      result.earned=d.provider?.today_earned_text||d.provider?.earned_text||'Not reported';result.credited=d.provider?.today_traffic_text||d.provider?.traffic_text||'Not reported';
      const providerStale=d.provider&&!fresh(now-d.provider.observed_ms,180000);
      if(providerStale){if(result.earned!=='Not reported')result.earned+=' (stale)';if(result.credited!=='Not reported')result.credited+=' (stale)';}
      result.creditNote='Connected confirms the control link. Replacement decisions use recent HTTP/HTTPS and SOCKS target traffic and connection outcomes, not paid earnings or HTTP success. RP network totals are received + sent bytes, including both directions of relayed traffic; they are not provider-credited bandwidth. Provider-day account snapshot'+(valid(d.provider?.observed_ms)?' · '+new Date(d.provider.observed_ms).toLocaleString():' not published')+(providerStale?' · stale':'')+'.';
      const rule=(d.workers||[]).find(w=>w.policy)?.policy;if(rule)result.creditNote+=' Automatic replacement after '+shown(rule.window_ms/60000,0)+' min: below '+shown(rule.min_target_bytes/1e6)+' MB target traffic. Control connection failures are replaced after 60 seconds; client exits are replaced immediately. Destination errors are reported separately.';
      const action=d.recent_recovery?.[0];if(action)result.creditNote+=' Last automatic replacement request: '+(action.ip||action.machine?.slice(0,8)||'worker')+' · '+new Date(action.time_ms).toLocaleString()+' · '+(action.http_status>=200&&action.http_status<300?'accepted by Salad':action.http_status?'HTTP '+action.http_status:'request failed; container restart fallback')+' · '+action.reason+'.';
    }else if(service==='tm'){
      result.desired=d.deployment?.desired_replicas||10;result.running=recordingFresh&&!d.stale?d.running:null;result.working=recordingFresh&&!d.stale?d.working||0:0;result.total=valid(d.recorded?.rx)&&valid(d.recorded?.tx)?(d.recorded.rx+d.recorded.tx)/1e6:null;result.start=d.deployment?.measurement_started_ms||Date.parse(d.deployment?.started_at);result.source=d.generated_ms;result.statusFresh=recordingFresh&&!d.stale&&!d.errors?.recorder;
      result.credited=mb(d.credited?.credited_bytes/1e6);result.earned=usd(d.credited?.credited_usd);result.creditNote=(d.credited?.scope||'TM provider account figures')+(d.credited?.fresh?'':'; provider reading is stale');
      result.notice=Object.values(d.errors||{}).join(' · ')||(!recordingFresh||d.stale?'Traffic Monetizer recorder is stale.':'');
      result.nodes=(d.workers||[]).map(w=>{const recent=recordingFresh&&!d.stale&&fresh(now-w.time_ms,45000);return {id:w.instance,ip:w.ip,status:recent?w.state:'Unverified',salad:w.salad_state,working:recent&&w.working,rate:recent?w.raw_mb_per_minute:null,total:valid(w.test_rx)&&valid(w.test_tx)?(w.test_rx+w.test_tx)/1e6:null,duration:w.test_duration_ms,age:diff(now,w.time_ms),error:[w.error,valid(w.native_recent_bytes)?'Relay observed: '+mb(w.native_recent_bytes/1e6)+' / '+shown(w.native_recent_requests,0)+' requests over '+shown(w.native_recent_ms/60000,1)+' min':'Relay window not yet measured'].filter(Boolean).join('; ')};});
      result.working=result.nodes.filter(n=>n.working).length;
      result.minutes=d.chart_minutes||(d.minutes||[]).map(m=>normalizeMinute(m.time_ms,(m.rx_bytes+m.tx_bytes)/1e6,(m.workers||[]).map(w=>({instance:w.instance,ip:w.ip||(d.workers||[]).find(n=>n.run===w.run)?.ip,mb:(w.rx+w.tx)/1e6})),m.samples<result.desired*60));
    }else if(service==='earnfm'){
      result.desired=d.desired||10;result.running=recordingFresh?(d.workers||[]).filter(w=>w.salad_state==='running').length:null;result.total=d.total_mb;result.start=d.test_started_ms;result.source=d.inventory_ms||d.generated_ms;result.statusFresh=recordingFresh&&!d.error;result.notice=d.error||(!recordingFresh?'RFM recorder is stale.':'');
      result.nodes=(d.workers||[]).map(w=>{
        const recent=recordingFresh&&!d.error&&fresh(now-w.sample_ms,90000),providerFresh=fresh(now-d.provider?.observed_ms,180000)&&!d.provider?.error;
        const runtime=w.runtime_instance||w.instance,present=Array.isArray(d.provider?.devices)?d.provider.devices.some(device=>device.instance===runtime):w.provider_online===true?true:null;
        const working=recent&&!w.final&&w.client_state==='running'&&w.salad_state==='running'&&providerFresh&&present===true;
        let status=w.client_state;
        if(w.salad_state&&w.salad_state!=='running')status=w.salad_state;
        else if(!recent)status='Unverified';
        else if(w.client_state==='reallocating')status='Reallocating';
        else if(w.final)status='Stopped';
        else if(w.client_state==='running')status=!providerFresh?'Provider status unavailable':present===false?'Provider offline':working?'Connected':'Awaiting provider confirmation';
        return {id:runtime,ip:w.ip,status,salad:w.salad_state,working,rate:recent&&!w.final&&valid(w.kb_per_second)?w.kb_per_second*.06:null,total:w.total_mb,duration:null,age:diff(now,w.sample_ms),error:w.error||(w.client_state==='rate_limited'?'Provider cooldown':!providerFresh&&d.provider?.error?d.provider.error:'')};
      });result.working=result.nodes.filter(n=>n.working).length;
      result.minutes=(d.points||[]).map(m=>normalizeMinute(m.time_ms,m.mb,Object.entries(m.by_instance||{}).map(([id,amount])=>({instance:id,ip:(d.workers||[]).find(w=>(w.runtime_instance||w.instance)===id)?.ip,country:(d.workers||[]).find(w=>(w.runtime_instance||w.instance)===id)?.country,mb:amount})),m.partial));
      result.earned=usd(d.provider?.earned);result.credited=mb(d.provider?.credited_mb);result.creditNote='EarnFM gross account balance change and credited traffic since its recorded baseline'+(valid(d.provider?.baseline_ms)?' · '+new Date(d.provider.baseline_ms).toLocaleString():'')+(!fresh(now-d.provider?.observed_ms,180000)||d.provider?.error?' · provider reading is stale':'')+'.';
    }
    result.estimated=result.estimated||result.minutes.some(m=>m.estimated);
    if(result.statusFresh){
      for(const node of result.nodes){
        const state=node.salad?.toLowerCase();
        if(['allocating','downloading','creating','stopping','stopped'].includes(state)){
          node.status=state[0].toUpperCase()+state.slice(1);node.working=false;node.rate=null;
          if(['allocating','downloading','creating'].includes(state))node.error='Waiting for the client to start on this machine.';
        }
      }
      result.working=result.nodes.filter(node=>node.working).length;
      while(result.nodes.length<result.desired)result.nodes.push({id:service+'-pending-'+result.nodes.length,pending:true,status:'Awaiting inventory',working:false,error:'No machine listed in the latest inventory.'});
    }
    if(!result.statusFresh){result.working=null;result.running=null;result.nodes=result.nodes.map(n=>({...n,working:false,status:"Unverified",stale:true,rate:null}));}
    return result;
  }
  function periodMinutes(minutes,hours,now=Date.now()){
    const end=Math.floor(now/60000)*60000,start=end-(hours*60-1)*60000,byTime=new Map(minutes.map(m=>[m.minute_ms,m]));
    return Array.from({length:hours*60},(_,i)=>byTime.get(start+i*60000)||{minute_ms:start+i*60000,mb:null,partial:true,count:0,nodes:[]});
  }
  if(typeof module!=='undefined'&&module.exports){module.exports={workerState,serviceModel,chartValue,windowStart,displayedIntervals,normalize,periodMinutes,SERVICES};return;}
  const el=id=>document.getElementById(id),make=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;};
  const duration=ms=>!valid(ms)?'—':Math.floor(ms/3600000)+'h '+Math.floor(ms%3600000/60000)+'m';
  const age=ms=>!valid(ms)?'—':ms<60000?shown(ms/1000,0)+'s':shown(ms/60000,1)+'m';
  const statusNames={unverified:'Status not received',unknown:'Awaiting client status','checking client':'Awaiting client status',stale:'Monitor delayed','status feed stale':'Monitor delayed',rate_limited:'Provider cooldown',connection_error:'Connection failed',reallocating:'Reallocating',awaiting_sample:'Awaiting first sample','online / running':'Connected'};
  const aliases={'/proxyrack':'proxyrack','/rp':'rp','/repocket':'rp','/earnfm':'earnfm','/traffmonetizer':'tm','/tm':'tm'};
  let active=SERVICES.find(s=>s.hash===location.hash)||SERVICES.find(s=>s.id===aliases[location.pathname.replace(/\.html$/,'')])||SERVICES[1],hours=12,data=null,model=null,busy=false,generation=0,billing=null,billingPending=false,billingChecked=0;
  const buttons=new Map();el('services').replaceChildren();
  for(const service of SERVICES){const button=make('button',service.name);button.id='tab-'+service.id;button.setAttribute('role','tab');button.setAttribute('aria-controls','bandwidthPanel');button.onclick=()=>select(service);buttons.set(service.id,button);el('services').append(button);}
  const panel=el('bandwidthPanel');
  panel.innerHTML='<div id="totals" class="summary-line"></div><p id="notice" class="notice hidden" role="status"></p>'+ 
    '<div class="chart-controls"><h2 id="chartTitle">Network traffic</h2><label>Show <select id="hours" aria-label="Time range"><option value="1">1 hour</option><option value="6">6 hours</option><option value="12" selected>12 hours</option><option value="24">24 hours</option></select></label></div>'+ 
    '<div class="ps-chart"><div id="chartScroll" class="ps-chart-scroll"><canvas id="trafficChart" tabindex="0" role="img"></canvas></div><div id="minutePopup" class="ps-popup hidden" role="tooltip"></div></div>'+ 
    '<p id="chartNote" class="source-note"></p><div class="table-scroll"><table class="container-table"><thead><tr><th>Container / IP</th><th>Client</th><th>Salad</th><th>MB/min</th><th>Recorded MB</th><th>Recorded time</th><th>Last sample</th><th>Error / note</th></tr></thead><tbody id="workerRows"></tbody></table></div><p id="creditNote" class="source-note"></p>';
  const chart=window.createMinuteChart({canvas:el('trafficChart'),scroll:el('chartScroll'),popup:el('minutePopup'),active:()=>true,readMinute:async minute=>{
    if(active.id==='ps')return read('/api/ps1/minutes?minute='+minute);
    return model?.minutes.find(m=>m.minute_ms===minute)||{minute_ms:minute,mb:null,count:0,nodes:[]};
  }});
  async function read(url){const response=await fetch(url,{cache:'no-store',signal:AbortSignal.timeout(10000)});if(!response.ok){const error=await response.json().catch(()=>({}));throw new Error(typeof error.error==='string'?error.error:'HTTP '+response.status);}return response.json();}
  function render(){
    if(!model)return;
    const bars=periodMinutes(model.minutes,hours),measured=bars.filter(b=>valid(b.mb)),estimated=measured.some(b=>b.estimated);
    let amount=measured.length?measured.reduce((sum,b)=>sum+b.mb,0):null;
    const totals=el('totals');totals.replaceChildren();
    for(const [label,value] of [['Clients confirmed',shown(model.working,0)+'/'+model.desired+' · '+shown(model.running,0)+' containers running'],[active.id==='tm'?'Network RX + TX':'Total recorded',mb(model.total)],['Last '+hours+(hours===1?' hour':' hours'),(estimated?'≈ ':'')+mb(amount)],['Provider credited / earned',model.credited===model.earned?model.earned:model.credited+' · '+(model.earned==='Not reported'?'earnings not reported':model.earned)],['Elapsed',duration(diff(Date.now(),model.start))]]){const item=make('span',label+': ');item.append(make('strong',value));totals.append(item);}
    el('notice').textContent=model.notice;el('notice').classList.toggle('hidden',!model.notice);
    el('chartTitle').textContent=active.name+' · MB per minute';
    el('chartNote').textContent='Hover or click a bar for the top 20 IPs, countries and MB. '+(model.estimated?'≈ Minute estimates from saved counter intervals. ':'')+'Blank = no measurement; amber = partial coverage. Network traffic includes overhead.'+(active.id==='tm'?' TM row rates average the latest observed minute. Relay notes show client counter increases, not per-worker paid earnings.':'');
    const body=el('workerRows');body.replaceChildren();
    for(const n of model.nodes){const row=make('tr'),id=make('td',n.pending?'Unassigned':n.ip||n.id?.slice(0,12)||'IP unavailable');id.title=n.pending?'':n.id||'';row.dataset.instance=n.id;row.append(id,make('td',statusNames[n.status?.toLowerCase()]||n.status||'Awaiting client status',n.working?'ok':n.error?'bad':'stale'),make('td',(n.salad||'—')+(n.stale?' (last seen)':'')),make('td',shown(n.rate)),make('td',shown(n.total)),make('td',duration(n.duration)),make('td',age(valid(n.age)?n.age+Math.max(0,Date.now()-model.at):null)),make('td',n.error||''));body.append(row);}
    if(!model.nodes.length){const row=make('tr'),cell=make('td','Waiting for the recorder to publish its container inventory.');cell.colSpan=8;row.append(cell);body.append(row);}
    el('creditNote').textContent=model.creditNote;
    el('connection').textContent=active.name+' · status '+age(diff(Date.now(),model.source))+' old';
    el('connection').classList.toggle('bad',Boolean(model.notice));
    chart.update({time_ms:Date.now(),candles:bars});
  }
  async function refresh(){
    if(busy)return;busy=true;const ticket=generation,service=active;
    try{const result=await read(service.url);if(ticket!==generation)return;data=result;model=normalize(service.id,data,Date.now(),billing);render();}
    catch(e){if(ticket===generation){if(model){if(service.id==='rp'&&data)model=normalize('rp',data,Date.now(),billing);model.notice='Cannot refresh '+service.name+'. Last saved values are shown.';model.working=null;model.running=null;model.nodes=model.nodes.map(n=>({...n,working:false,status:'Unverified',stale:true,rate:null}));render();}else{model=normalize(service.id,{});model.nodes=[];model.working=null;model.running=null;model.notice='Waiting for '+service.name+' recorder: '+e.message;render();}}}
    finally{if(ticket===generation)busy=false;}
    if(service.id==='ps'&&!billingPending&&Date.now()-billingChecked>60000){billingPending=true;billingChecked=Date.now();read('/api/ps1/view').then(value=>{billing=value;if(active.id==='ps'&&data){const credit=normalize('ps',data,Date.now(),billing);if(model){model.credited=credit.credited;model.earned=credit.earned;model.creditNote=credit.creditNote;render();}}}).catch(()=>{}).finally(()=>{billingPending=false;});}
  }
  function select(service,changeHash=true){
    active=service;generation++;busy=false;data=null;model=null;chart.hide();chart.update({time_ms:Date.now(),candles:periodMinutes([],hours)});
    for(const item of SERVICES){const yes=item.id===service.id;buttons.get(item.id).setAttribute('aria-selected',String(yes));buttons.get(item.id).tabIndex=yes?0:-1;}
    panel.setAttribute('aria-labelledby','tab-'+service.id);if(changeHash)history.replaceState(null,'','/'+service.hash);document.title=service.name+' · Bandwidth test';
    el('connection').textContent=service.name+' · loading';el('totals').textContent='Loading '+service.name+' readings…';el('workerRows').replaceChildren();el('creditNote').textContent='';el('notice').classList.add('hidden');el('chartTitle').textContent=service.name+' · MB per minute';el('chartNote').textContent='Hover or click a minute for its contributors.';refresh();
  }
  el('hours').onchange=()=>{hours=Number(el('hours').value);chart.hide();if(model)render();else chart.update({time_ms:Date.now(),candles:periodMinutes([],hours)});};
  el('services').addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const index=SERVICES.indexOf(active),next=event.key==='Home'?0:event.key==='End'?SERVICES.length-1:(index+(event.key==='ArrowLeft'?-1:1)+SERVICES.length)%SERVICES.length;select(SERVICES[next]);buttons.get(active.id).focus();});
  window.addEventListener('hashchange',()=>select(SERVICES.find(s=>s.hash===location.hash)||SERVICES[1],false));
  select(active);setInterval(refresh,5000);
})();

`````

### `dashboard/static/index.html`

<!-- RP_FILE: dashboard/static/index.html SHA256: ee39d93054a6f9d5088780ee5edd41617998189df4870f6bbd9e895853decb3a -->
`````html
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bandwidth test</title><link rel="stylesheet" href="/styles.css"></head>
<body>
<header><h1>Bandwidth test</h1><span id="connection" role="status">Loading…</span></header>
<main><nav id="services" role="tablist" aria-label="Services"></nav><section id="bandwidthPanel" role="tabpanel"></section></main>
<script src="/ps1.js" defer></script><script src="/fleet-test.js" defer></script>
</body></html>

`````

### `dashboard/static/ps1.js`

<!-- RP_FILE: dashboard/static/ps1.js SHA256: a386aacc6db63b407dfa846d328b2860f98e6af6dfaabde98dc4382f57356558 -->
`````javascript
(() => {
  "use strict";
  const finite = value => typeof value === "number" && Number.isFinite(value);
  const number = (value, digits = 3) => finite(value) ? value.toLocaleString(undefined, {maximumFractionDigits: digits}) : "—";
  const clock = value => value == null ? "—" : new Date(value).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", hour12: false});
  const countries = new Intl.DisplayNames(undefined, {type:"region"});
  const make = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const countryCache = new Map();
  let countryLookup = null;
  async function lookupCountries(nodes) {
    if (nodes.every(n=>!n.ip || n.country || countryCache.has(n.ip))) return;
    if (countryLookup) await countryLookup;
    const ips=[...new Set(nodes.filter(n=>n.ip && !n.country && !countryCache.has(n.ip)).map(n=>n.ip))];
    if (!ips.length) return;
    countryLookup=(async()=>{
      try {
        const response=await fetch("https://api.country.is/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(ips),signal:AbortSignal.timeout(5000)});
        if (!response.ok) return;
        for (const row of await response.json()) if(ips.includes(row.ip) && /^[A-Z]{2}$/.test(row.country)) countryCache.set(row.ip,row.country);
      } catch (_) {}
    })();
    await countryLookup; countryLookup=null;
  }
  window.createMinuteChart = ({canvas, scroll, popup, active, readMinute}) => {
    let data=null, geometry=null, hover=null, pinned=false, detailTimer=null, detailRequest=0, detailPending=false;
  function draw() {
    if (!data || !active()) return;
    const bars = data.candles, width = scroll.clientWidth, height = 230;
    const dpr = Math.min(devicePixelRatio || 1, 2), left = 60, right = width - 10, top = 20, bottom = height - 30;
    canvas.style.width = width + "px"; canvas.width = Math.round(width * dpr); canvas.height = height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, width, height);
    ctx.font = "12px system-ui";
    if (!bars.length) {geometry=null;ctx.fillStyle="#555";ctx.fillText("Waiting for saved measurements…",12,110);return;}
    const maximum = Math.max(0.001, ...bars.map(b => b.mb || 0)), step = (right - left) / bars.length;
    for (let i = 0; i <= 3; i++) {
      const y = bottom - (bottom - top) * i / 3;
      ctx.strokeStyle = "#e3e3e3"; ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke();
      ctx.textAlign = "right"; ctx.fillStyle = "#555"; ctx.fillText(number(maximum * i / 3, 2), left - 7, y + 4);
    }
    bars.forEach((bar, i) => {
      const x = left + (i + .5) * step;
      if (bar.minute_ms === hover) {ctx.fillStyle = "#b8d7ed"; ctx.fillRect(x - 2, top, 4, bottom - top);}
      if (finite(bar.mb)) {
        const h = Math.max(1, bar.mb / maximum * (bottom - top));
        ctx.fillStyle = bar.partial ? "#a76508" : "#1769aa";
        ctx.fillRect(x - step * .35, bottom - h, step * .7, h);
      }
      if (i % Math.max(15, Math.round(bars.length/360)*60) === 0) {ctx.textAlign = "left"; ctx.fillStyle = "#555"; ctx.fillText(clock(bar.minute_ms), x, height - 9);}
    });
    ctx.textAlign = "right"; ctx.fillStyle = "#555"; ctx.fillText(clock(data.time_ms), right, height - 9);
    geometry = {left, right, step};
    const hours = Math.round(bars.length/60);
    canvas.setAttribute("aria-label", "Past " + hours + (hours === 1 ? " hour" : " hours") + ", one-minute traffic bars. Hover or click for the top 20 IPs, countries and megabytes. Arrow keys select a minute; Escape closes the popup.");
  }
  function hidePopup() {
    hover = null; pinned = false; detailPending = false; detailRequest++; clearTimeout(detailTimer);
    popup.classList.add("hidden"); draw();
  }
  function showMinute(index, event, refreshDetail = false) {
    const minute = data.candles[index].minute_ms;
    const wrap = scroll.parentElement.getBoundingClientRect();
    if (!refreshDetail) popup.style.left = Math.max(4, Math.min((event ? event.clientX - wrap.left : wrap.width - 330) + 12, wrap.width - 324)) + "px";
    if (!refreshDetail) popup.style.top = (event ? Math.max(8, event.clientY - wrap.top + 12) : 35) + "px";
    popup.classList.remove("hidden");
    const changed = hover !== minute;
    if (!changed && (!refreshDetail || detailPending)) return;
    hover = minute; detailPending = true; const ticket = ++detailRequest; clearTimeout(detailTimer); draw();
    if (changed) popup.replaceChildren(make("strong", clock(minute) + "–" + clock(minute + 60000)), make("p", "Reading contributions…"));
    detailTimer = setTimeout(async () => {
      try {
        const detail = await readMinute(minute);
        await lookupCountries(detail.nodes || []);
        if (ticket !== detailRequest) return;
        popup.replaceChildren(make("strong", clock(minute) + "–" + clock(minute + 60000) + " · " + (detail.estimated ? "≈ " : "") + number(detail.mb) + " MB"));
        if (!detail.count) {popup.append(make("p", detail.note || (finite(detail.mb) ? "Per-node detail is not available for this minute." : "No measurement recorded for this minute."))); return;}
        popup.append(make("p", "Top " + detail.nodes.length + " of " + detail.count + " contributing nodes"));
        const table = make("table"), head = make("tr");
        head.append(make("th","IP"),make("th","Country"),make("th","MB")); table.append(head);
        for (const node of detail.nodes) {
          const row = make("tr"); row.title = node.instance;
          row.append(make("td",node.ip || "Unknown"),make("td",(node.country || countryCache.get(node.ip)) ? countries.of(node.country || countryCache.get(node.ip)) : "Unknown"),make("td",number(node.mb)));
          table.append(row);
        }
        popup.append(table);
      } catch (_) {if (ticket === detailRequest) popup.replaceChildren(make("p","Cannot read this minute. Hover again to retry."));}
      finally {if (ticket === detailRequest) detailPending = false;}
    }, 70);
  }
  function indexAt(event) {
    if (!geometry) return null;
    const x = event.clientX - canvas.getBoundingClientRect().left;
    return x < geometry.left || x >= geometry.right ? null : Math.floor((x - geometry.left) / geometry.step);
  }
  canvas.addEventListener("pointermove", event => {const i=indexAt(event); if(i!=null && (!pinned || hover!==data.candles[i].minute_ms)){pinned=false;showMinute(i,event);}else if(i==null && !pinned)hidePopup();});
  canvas.addEventListener("pointerleave", () => {if (!pinned) hidePopup();});
  canvas.addEventListener("click", event => {const i=indexAt(event); if(i==null)return; if(pinned && hover===data.candles[i].minute_ms)hidePopup();else{pinned=true;showMinute(i,event);}});
  canvas.addEventListener("keydown", event => {
    if (!geometry || !data || !["ArrowLeft","ArrowRight","Home","End","Escape"].includes(event.key)) return;
    event.preventDefault(); if(event.key==="Escape"){hidePopup();return;}
    const bars=data.candles, index=hover==null ? bars.length-1 : bars.findIndex(b=>b.minute_ms===hover);
    pinned=true; showMinute(event.key==="Home" ? 0 : event.key==="End" ? bars.length-1 : Math.max(0,Math.min(bars.length-1,index+(event.key==="ArrowLeft"?-1:1))));
  });
    window.addEventListener("servicechange",hidePopup);
    window.addEventListener("resize",draw);
    return {hide:hidePopup,update(next){
      data=next; draw();
      if (hover!=null) {const i=data.candles.findIndex(b=>b.minute_ms===hover);if(i<0)hidePopup();else showMinute(i,undefined,true);}
    }};
  };
})();

"use strict";
// Preserve the existing provider-tab bridge; it is separate from presentation.
(() => {
  const button = document.getElementById("psConnect"), message = document.getElementById("psFeedStatus") || {textContent:""};
  let providerWindow = null, state = null, pending = null;
  let channel = sessionStorage.getItem("ps-billing-channel") || "";
  function refresh() {
    if(pending) return pending;
    pending = (async () => {
      try {
        const response=await fetch("/api/ps1/view",{cache:"no-store",signal:AbortSignal.timeout(8000)});
        if(!response.ok)throw new Error();
        state=await response.json();
        message.textContent=state.feed_age_ms!=null&&state.feed_age_ms<150000?"Provider readings are connected.":"Provider readings are missing or stale. Keep the connected provider tab open.";
      } catch(_) {state=null;message.textContent="Provider connection status is unknown.";}
    })().finally(()=>{pending=null;});
    return pending;
  }
  button?.addEventListener("click",()=>{
    if(providerWindow&&!providerWindow.closed){providerWindow.focus();return;}
    if(!channel){channel=crypto.randomUUID();sessionStorage.setItem("ps-billing-channel",channel);}
    providerWindow=window.open(`https://app.packetstream.io/dashboard#ps-sync=${channel}`,"psBillingSync");
    message.textContent="Provider tab opened. Waiting for credited-traffic readings.";refresh();
  });
  window.addEventListener("message",async event=>{
    if(event.origin!=="https://app.packetstream.io"||!channel||event.data?.type!=="ps-credited"||event.data.channel!==channel)return;
    if(providerWindow&&event.source!==providerWindow)return;
    if(event.data.error){message.textContent="Provider reading could not be retrieved.";return;}
    await refresh();if(!state?.bridge_token||!Number.isFinite(event.data.gb))return;
    try{
      const save=()=>fetch("/api/ps1/credited",{method:"POST",headers:{"Content-Type":"application/json","X-PS-Token":state.bridge_token},body:JSON.stringify({gb:event.data.gb,bytes:event.data.bytes,time_ms:event.data.time_ms})});
      let response=await save();
      if(response.status===403){await refresh();if(!state?.bridge_token)throw new Error();response=await save();}
      if(!response.ok)throw new Error();message.textContent="Provider reading saved.";
    }
    catch(_){message.textContent="Provider reading could not be saved.";}
  });
  document.getElementById("history")?.addEventListener("toggle",event=>{if(event.currentTarget.open)refresh();});
})();

`````

### `dashboard/static/styles.css`

<!-- RP_FILE: dashboard/static/styles.css SHA256: b7c37ee6cd698d1b327a51a62849a51d817435d166170a70791ebb6e68d7c9eb -->
`````css
:root{font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#161616;background:#fff;color-scheme:light}
*{box-sizing:border-box}body{margin:0;padding:16px 22px}header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:12px}h1{font-size:20px;margin:0}h2{font-size:16px;margin:0}p{margin:7px 0}
button,select{font:inherit;border:1px solid #aaa;border-radius:2px;background:#fff;color:inherit;padding:5px 9px;cursor:pointer}button:focus-visible,select:focus-visible{outline:2px solid #1767b5;outline-offset:2px}
nav{display:flex;flex-wrap:wrap;gap:6px;border-bottom:1px solid #999;padding-bottom:7px;margin-bottom:12px}nav button[aria-selected=true]{font-weight:700;background:#ededed;border-color:#333}
#connection,.source-note,.summary-line{font-size:12px}.summary-line{display:flex;flex-wrap:wrap;gap:8px 24px;margin:7px 0}.summary-line strong{font-size:14px}.summary-line span{white-space:nowrap}.source-note{color:#555}
.notice{color:#8b3b00;background:#fff8ed;padding:6px 9px;font-size:12px}.chart-controls{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:8px 0}.chart-controls label{font-size:12px}.chart-controls select{margin-left:5px}
.table-scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;text-align:left;font-size:12px}th,td{padding:7px 9px;border:1px solid #ccc;vertical-align:top;font-variant-numeric:tabular-nums}th{background:#f2f2f2;font-weight:600}.container-table{min-width:800px}.container-table td:first-child{max-width:250px;overflow-wrap:anywhere}
.ok{color:#126428}.bad{color:#ad230d}.stale{color:#777}.hidden{display:none!important}
.ps-chart{position:relative}.ps-chart-scroll{width:100%;overflow-x:auto;border:1px solid #bbb;margin:8px 0}.ps-chart-scroll canvas{display:block;height:230px;cursor:crosshair}.ps-chart-scroll canvas:focus-visible{outline:2px solid #1769aa;outline-offset:-2px}
.ps-popup{position:absolute;z-index:5;background:white;border:1px solid #888;box-shadow:0 2px 8px #0002;padding:10px;width:320px;max-width:calc(100% - 8px);max-height:70vh;overflow:auto;font-size:12px}.ps-popup p{margin:5px 0}.ps-popup th,.ps-popup td{padding:4px 6px}.ps-popup th:last-child,.ps-popup td:last-child{text-align:right;white-space:nowrap}
@media(max-width:650px){body{padding:10px}header{align-items:start}#connection{max-width:150px;text-align:right}.summary-line{gap:6px 14px}.chart-controls{gap:8px}}

`````

### `dashboard/store.py`

<!-- RP_FILE: dashboard/store.py SHA256: 1217de0c6e729cb87df4eae1d8842ebd518ef83774d82e9048ccb8ea9f37f0da -->
`````python
"""SQLite persistence and aggregation for Salad bandwidth samples."""

from __future__ import annotations

import json
import re
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


APP_NAMES = ("packetstream", "proxyrack", "traffmonetizer", "earnfm", "repocket", "bitping", "honeygain")
MINUTE_MS = 60_000
LIVE_SAMPLE_GRACE_MS = 120_000
HONEYGAIN_EVENTS = {
    "start",
    "authenticated",
    "service_starting",
    "connected",
    "disconnected",
    "network_overused",
    "duplicate_device",
    "device_limit_exceeded",
    "unusable_network",
    "authentication_error",
    "api_ping_error",
    "exit",
    "stopping",
    "stopped",
}


def parse_time_ms(value: str) -> int:
    value = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], value, count=1)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(round(parsed.timestamp() * 1000))


class Store:
    def __init__(self, path: Path, raw_retention_days: int = 30):
        self.path = Path(path)
        self.raw_retention_days = raw_retention_days
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA journal_mode = WAL")
        self._db.execute("PRAGMA synchronous = NORMAL")
        self._create_schema()
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def _create_schema(self) -> None:
        with self._db:
            self._db.executescript(
                """
                CREATE TABLE IF NOT EXISTS samples (
                    instance_id TEXT NOT NULL,
                    sample_time_ms INTEGER NOT NULL,
                    sequence INTEGER NOT NULL,
                    receive_time_ms INTEGER NOT NULL,
                    machine_id TEXT NOT NULL,
                    public_ip TEXT NOT NULL DEFAULT '',
                    public_ip_status TEXT NOT NULL DEFAULT 'unknown',
                    interface TEXT NOT NULL,
                    counter_reset INTEGER NOT NULL,
                    eth_rx_total INTEGER NOT NULL,
                    eth_tx_total INTEGER NOT NULL,
                    eth_rx_bytes INTEGER NOT NULL,
                    eth_tx_bytes INTEGER NOT NULL,
                    eth_rx_rate INTEGER NOT NULL DEFAULT 0,
                    eth_tx_rate INTEGER NOT NULL DEFAULT 0,
                    captured_rx_bytes INTEGER NOT NULL,
                    captured_tx_bytes INTEGER NOT NULL,
                    unassigned_rx_bytes INTEGER NOT NULL,
                    unassigned_tx_bytes INTEGER NOT NULL,
                    coverage_percent REAL NOT NULL,
                    organization_name TEXT NOT NULL DEFAULT '',
                    project_name TEXT NOT NULL DEFAULT '',
                    container_group_name TEXT NOT NULL DEFAULT '',
                    container_group_version TEXT NOT NULL DEFAULT '',
                    capture_mode TEXT NOT NULL DEFAULT 'packet',
                    interval_milliseconds INTEGER NOT NULL DEFAULT 1000,
                    partial_interval INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (instance_id, sample_time_ms, sequence)
                );
                CREATE INDEX IF NOT EXISTS samples_time ON samples(sample_time_ms);
                CREATE INDEX IF NOT EXISTS samples_receive_time ON samples(receive_time_ms);

                CREATE TABLE IF NOT EXISTS app_samples (
                    instance_id TEXT NOT NULL,
                    sample_time_ms INTEGER NOT NULL,
                    sequence INTEGER NOT NULL,
                    app_name TEXT NOT NULL,
                    rx_bytes INTEGER NOT NULL,
                    tx_bytes INTEGER NOT NULL,
                    process_count INTEGER NOT NULL,
                    socket_count INTEGER NOT NULL,
                    tcp_socket_count INTEGER NOT NULL DEFAULT 0,
                    tcp_established_count INTEGER NOT NULL DEFAULT 0,
                    udp_socket_count INTEGER NOT NULL DEFAULT 0,
                    state TEXT NOT NULL,
                    PRIMARY KEY (instance_id, sample_time_ms, sequence, app_name),
                    FOREIGN KEY (instance_id, sample_time_ms, sequence)
                        REFERENCES samples(instance_id, sample_time_ms, sequence) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS app_samples_time ON app_samples(sample_time_ms);

                CREATE TABLE IF NOT EXISTS instance_segments (
                    instance_id TEXT PRIMARY KEY,
                    machine_id TEXT NOT NULL,
                    first_seen_ms INTEGER NOT NULL,
                    last_seen_ms INTEGER NOT NULL,
                    public_ip TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS minute_rollups (
                    minute_ms INTEGER NOT NULL,
                    instance_id TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    sample_count INTEGER NOT NULL,
                    eth_rx_bytes INTEGER NOT NULL,
                    eth_tx_bytes INTEGER NOT NULL,
                    captured_rx_bytes INTEGER NOT NULL,
                    captured_tx_bytes INTEGER NOT NULL,
                    unassigned_rx_bytes INTEGER NOT NULL,
                    unassigned_tx_bytes INTEGER NOT NULL,
                    reset_count INTEGER NOT NULL,
                    partial_interval_count INTEGER NOT NULL DEFAULT 0,
                    eth_rx_rate_sum INTEGER NOT NULL DEFAULT 0,
                    eth_tx_rate_sum INTEGER NOT NULL DEFAULT 0,
                    coverage_sum REAL NOT NULL DEFAULT 0,
                    first_sample_ms INTEGER NOT NULL DEFAULT 0,
                    last_sample_ms INTEGER NOT NULL DEFAULT 0,
                    peak_rate INTEGER NOT NULL DEFAULT 0,
                    peak_time_ms INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (minute_ms, instance_id)
                );
                CREATE INDEX IF NOT EXISTS minute_rollups_time ON minute_rollups(minute_ms);

                CREATE TABLE IF NOT EXISTS minute_app_rollups (
                    minute_ms INTEGER NOT NULL,
                    instance_id TEXT NOT NULL,
                    app_name TEXT NOT NULL,
                    rx_bytes INTEGER NOT NULL,
                    tx_bytes INTEGER NOT NULL,
                    PRIMARY KEY (minute_ms, instance_id, app_name),
                    FOREIGN KEY (minute_ms, instance_id)
                        REFERENCES minute_rollups(minute_ms, instance_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS ingest_state (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    watermark_ms INTEGER,
                    last_poll_ms INTEGER,
                    last_success_ms INTEGER,
                    last_new_samples INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT ''
                );
                INSERT OR IGNORE INTO ingest_state(singleton) VALUES (1);

                CREATE TABLE IF NOT EXISTS runtime_events (
                    instance_id TEXT NOT NULL,
                    event_time_ms INTEGER NOT NULL,
                    receive_time_ms INTEGER NOT NULL,
                    machine_id TEXT NOT NULL,
                    organization_name TEXT NOT NULL DEFAULT '',
                    project_name TEXT NOT NULL DEFAULT '',
                    container_group_name TEXT NOT NULL DEFAULT '',
                    container_group_version TEXT NOT NULL DEFAULT '',
                    kind TEXT NOT NULL,
                    event TEXT NOT NULL,
                    client_version TEXT NOT NULL DEFAULT '',
                    attempt INTEGER NOT NULL DEFAULT 0,
                    exit_code INTEGER NOT NULL DEFAULT 0,
                    severity TEXT NOT NULL DEFAULT 'default',
                    PRIMARY KEY (instance_id, event_time_ms, kind, event, attempt)
                );
                CREATE INDEX IF NOT EXISTS runtime_events_time ON runtime_events(event_time_ms);
                """
            )
        columns = {row[1] for row in self._db.execute("PRAGMA table_info(app_samples)").fetchall()}
        with self._db:
            for name in ("tcp_socket_count", "tcp_established_count", "udp_socket_count"):
                if name not in columns:
                    self._db.execute(f"ALTER TABLE app_samples ADD COLUMN {name} INTEGER NOT NULL DEFAULT 0")
        sample_columns = {row[1] for row in self._db.execute("PRAGMA table_info(samples)").fetchall()}
        sample_additions = {
            "organization_name": "TEXT NOT NULL DEFAULT ''",
            "project_name": "TEXT NOT NULL DEFAULT ''",
            "container_group_name": "TEXT NOT NULL DEFAULT ''",
            "container_group_version": "TEXT NOT NULL DEFAULT ''",
            "capture_mode": "TEXT NOT NULL DEFAULT 'packet'",
            "interval_milliseconds": "INTEGER NOT NULL DEFAULT 1000",
            "partial_interval": "INTEGER NOT NULL DEFAULT 0",
            "eth_rx_rate": "INTEGER NOT NULL DEFAULT 0",
            "eth_tx_rate": "INTEGER NOT NULL DEFAULT 0",
        }
        with self._db:
            for name, definition in sample_additions.items():
                if name not in sample_columns:
                    self._db.execute(f"ALTER TABLE samples ADD COLUMN {name} {definition}")
            if "eth_rx_rate" not in sample_columns:
                self._db.execute("UPDATE samples SET eth_rx_rate=eth_rx_bytes")
            if "eth_tx_rate" not in sample_columns:
                self._db.execute("UPDATE samples SET eth_tx_rate=eth_tx_bytes")
        minute_columns = {row[1] for row in self._db.execute("PRAGMA table_info(minute_rollups)").fetchall()}
        minute_additions = {
            "partial_interval_count": "INTEGER NOT NULL DEFAULT 0",
            "eth_rx_rate_sum": "INTEGER NOT NULL DEFAULT 0",
            "eth_tx_rate_sum": "INTEGER NOT NULL DEFAULT 0",
            "coverage_sum": "REAL NOT NULL DEFAULT 0",
            "first_sample_ms": "INTEGER NOT NULL DEFAULT 0",
            "last_sample_ms": "INTEGER NOT NULL DEFAULT 0",
            "peak_rate": "INTEGER NOT NULL DEFAULT 0",
            "peak_time_ms": "INTEGER NOT NULL DEFAULT 0",
        }
        with self._db:
            for name, definition in minute_additions.items():
                if name not in minute_columns:
                    self._db.execute(f"ALTER TABLE minute_rollups ADD COLUMN {name} {definition}")

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def ingest(self, log_entry: Dict[str, Any]) -> bool:
        payload = log_entry.get("json_log")
        # Older monitor images forward this native transition without emitting
        # a structured event. Preserve the actual event time and source labels.
        if log_entry.get("text_log") == "Honeygain service disconnected":
            return self._ingest_runtime_event(log_entry, {
                "kind": "honeygain_event", "schema_version": 1,
                "event": "disconnected", "time": log_entry.get("time"),
            })
        if not isinstance(payload, dict):
            return False
        kind = payload.get("kind")
        if kind in ("honeygain_event", "bandwidth_monitor_status"):
            return self._ingest_runtime_event(log_entry, payload)
        if kind != "bandwidth_sample":
            return False
        if payload.get("schema_version") != 1:
            return False
        labels = ((log_entry.get("resource") or {}).get("labels") or {})
        instance_id = str(labels.get("instance_id") or payload.get("instance_id") or "unknown")
        machine_id = str(labels.get("machine_id") or payload.get("machine_id") or "unknown")
        sample_time_ms = parse_time_ms(str(payload["sample_time"]))
        receive_time_ms = parse_time_ms(str(log_entry.get("receive_time") or log_entry.get("time") or payload["sample_time"]))
        sequence = int(payload.get("sequence", 0))
        eth0 = payload.get("eth0") or {}
        captured = payload.get("captured") or {}
        unassigned = payload.get("unassigned") or {}
        public_ip = str(payload.get("public_ip") or "")
        eth_rx_bytes = int(eth0.get("rx_bytes_delta", eth0.get("rx_bytes_per_second", 0)))
        eth_tx_bytes = int(eth0.get("tx_bytes_delta", eth0.get("tx_bytes_per_second", 0)))
        eth_rx_rate = int(eth0.get("rx_bytes_per_second", 0))
        eth_tx_rate = int(eth0.get("tx_bytes_per_second", 0))
        coverage_percent = float(payload.get("coverage_percent", 0.0))
        partial_interval = int(bool(payload.get("partial_interval")))
        row = (
            instance_id,
            sample_time_ms,
            sequence,
            receive_time_ms,
            machine_id,
            public_ip,
            str(payload.get("public_ip_status") or "unknown"),
            str(payload.get("interface") or "eth0"),
            int(bool(payload.get("counter_reset"))),
            int(eth0.get("rx_bytes_total", 0)),
            int(eth0.get("tx_bytes_total", 0)),
            eth_rx_bytes,
            eth_tx_bytes,
            eth_rx_rate,
            eth_tx_rate,
            int(captured.get("rx_bytes", 0)),
            int(captured.get("tx_bytes", 0)),
            int(unassigned.get("rx_bytes", 0)),
            int(unassigned.get("tx_bytes", 0)),
            coverage_percent,
            str(labels.get("organization_name") or ""),
            str(labels.get("project_name") or ""),
            str(labels.get("container_group_name") or ""),
            str(labels.get("container_group_version") or ""),
            str(payload.get("capture_mode") or "packet"),
            int(payload.get("interval_milliseconds") or 1000),
            partial_interval,
        )
        with self._lock, self._db:
            cursor = self._db.execute(
                """
                INSERT OR IGNORE INTO samples(
                    instance_id, sample_time_ms, sequence, receive_time_ms, machine_id,
                    public_ip, public_ip_status, interface, counter_reset, eth_rx_total,
                    eth_tx_total, eth_rx_bytes, eth_tx_bytes, eth_rx_rate, eth_tx_rate, captured_rx_bytes,
                    captured_tx_bytes, unassigned_rx_bytes, unassigned_tx_bytes,
                    coverage_percent, organization_name, project_name, container_group_name,
                    container_group_version, capture_mode, interval_milliseconds,
                    partial_interval
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                row,
            )
            if cursor.rowcount == 0:
                return False
            apps = payload.get("applications") or {}
            for app_name, app in apps.items():
                if app_name not in APP_NAMES or not isinstance(app, dict):
                    continue
                self._db.execute(
                    """
                    INSERT INTO app_samples(
                        instance_id, sample_time_ms, sequence, app_name, rx_bytes, tx_bytes,
                        process_count, socket_count, tcp_socket_count, tcp_established_count,
                        udp_socket_count, state
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        instance_id,
                        sample_time_ms,
                        sequence,
                        app_name,
                        int(app.get("attributed_packet_rx_bytes", 0)),
                        int(app.get("attributed_packet_tx_bytes", 0)),
                        int(app.get("process_count", 0)),
                        int(app.get("socket_count", 0)),
                        int(app.get("tcp_socket_count", 0)),
                        int(app.get("tcp_established_count", 0)),
                        int(app.get("udp_socket_count", 0)),
                        str(app.get("state") or "down"),
                    ),
                )
            self._db.execute(
                """
                INSERT INTO instance_segments(instance_id, machine_id, first_seen_ms, last_seen_ms, public_ip)
                VALUES (?,?,?,?,?)
                ON CONFLICT(instance_id) DO UPDATE SET
                    machine_id=excluded.machine_id,
                    first_seen_ms=min(first_seen_ms, excluded.first_seen_ms),
                    last_seen_ms=max(last_seen_ms, excluded.last_seen_ms),
                    public_ip=CASE WHEN excluded.public_ip <> '' THEN excluded.public_ip ELSE public_ip END
                """,
                (instance_id, machine_id, sample_time_ms, sample_time_ms, public_ip),
            )
            minute_ms = (sample_time_ms // MINUTE_MS) * MINUTE_MS
            peak_rate = eth_rx_rate + eth_tx_rate
            self._db.execute(
                """
                INSERT INTO minute_rollups(
                    minute_ms, instance_id, machine_id, sample_count, eth_rx_bytes, eth_tx_bytes,
                    captured_rx_bytes, captured_tx_bytes, unassigned_rx_bytes, unassigned_tx_bytes,
                    reset_count, partial_interval_count, eth_rx_rate_sum, eth_tx_rate_sum,
                    coverage_sum, first_sample_ms, last_sample_ms, peak_rate, peak_time_ms
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(minute_ms, instance_id) DO UPDATE SET
                    machine_id=excluded.machine_id,
                    sample_count=minute_rollups.sample_count + 1,
                    eth_rx_bytes=minute_rollups.eth_rx_bytes + excluded.eth_rx_bytes,
                    eth_tx_bytes=minute_rollups.eth_tx_bytes + excluded.eth_tx_bytes,
                    captured_rx_bytes=minute_rollups.captured_rx_bytes + excluded.captured_rx_bytes,
                    captured_tx_bytes=minute_rollups.captured_tx_bytes + excluded.captured_tx_bytes,
                    unassigned_rx_bytes=minute_rollups.unassigned_rx_bytes + excluded.unassigned_rx_bytes,
                    unassigned_tx_bytes=minute_rollups.unassigned_tx_bytes + excluded.unassigned_tx_bytes,
                    reset_count=minute_rollups.reset_count + excluded.reset_count,
                    partial_interval_count=minute_rollups.partial_interval_count + excluded.partial_interval_count,
                    eth_rx_rate_sum=minute_rollups.eth_rx_rate_sum + excluded.eth_rx_rate_sum,
                    eth_tx_rate_sum=minute_rollups.eth_tx_rate_sum + excluded.eth_tx_rate_sum,
                    coverage_sum=minute_rollups.coverage_sum + excluded.coverage_sum,
                    first_sample_ms=min(minute_rollups.first_sample_ms, excluded.first_sample_ms),
                    last_sample_ms=max(minute_rollups.last_sample_ms, excluded.last_sample_ms),
                    peak_time_ms=CASE
                        WHEN excluded.peak_rate > minute_rollups.peak_rate
                          OR (excluded.peak_rate = minute_rollups.peak_rate
                              AND excluded.peak_time_ms < minute_rollups.peak_time_ms)
                        THEN excluded.peak_time_ms ELSE minute_rollups.peak_time_ms END,
                    peak_rate=max(minute_rollups.peak_rate, excluded.peak_rate)
                WHERE minute_rollups.sample_count < (
                    SELECT count(*) FROM samples s
                    WHERE s.instance_id=excluded.instance_id
                      AND (s.sample_time_ms / 60000) * 60000=excluded.minute_ms
                )
                """,
                (
                    minute_ms,
                    instance_id,
                    machine_id,
                    1,
                    eth_rx_bytes,
                    eth_tx_bytes,
                    int(captured.get("rx_bytes", 0)),
                    int(captured.get("tx_bytes", 0)),
                    int(unassigned.get("rx_bytes", 0)),
                    int(unassigned.get("tx_bytes", 0)),
                    int(bool(payload.get("counter_reset"))),
                    partial_interval,
                    eth_rx_rate,
                    eth_tx_rate,
                    coverage_percent,
                    sample_time_ms,
                    sample_time_ms,
                    peak_rate,
                    sample_time_ms,
                ),
            )
            for app_name, app in apps.items():
                if app_name not in APP_NAMES or not isinstance(app, dict):
                    continue
                self._db.execute(
                    """
                    INSERT INTO minute_app_rollups(minute_ms, instance_id, app_name, rx_bytes, tx_bytes)
                    VALUES (?,?,?,?,?)
                    ON CONFLICT(minute_ms, instance_id, app_name) DO UPDATE SET
                        rx_bytes=minute_app_rollups.rx_bytes + excluded.rx_bytes,
                        tx_bytes=minute_app_rollups.tx_bytes + excluded.tx_bytes
                    WHERE (SELECT sample_count FROM minute_rollups m
                           WHERE m.minute_ms=excluded.minute_ms AND m.instance_id=excluded.instance_id) =
                          (SELECT count(*) FROM samples s
                           WHERE s.instance_id=excluded.instance_id
                             AND (s.sample_time_ms / 60000) * 60000=excluded.minute_ms)
                    """,
                    (
                        minute_ms,
                        instance_id,
                        app_name,
                        int(app.get("attributed_packet_rx_bytes", 0)),
                        int(app.get("attributed_packet_tx_bytes", 0)),
                    ),
                )
        return True

    def _ingest_runtime_event(self, log_entry: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        if payload.get("schema_version") != 1:
            return False
        kind = str(payload.get("kind") or "")
        event = str(payload.get("event") or "")
        if kind == "honeygain_event" and event not in HONEYGAIN_EVENTS:
            return False
        if kind == "bandwidth_monitor_status" and event not in ("start", "exit"):
            return False
        labels = ((log_entry.get("resource") or {}).get("labels") or {})
        event_time_ms = parse_time_ms(str(payload.get("time") or log_entry.get("time")))
        receive_time_ms = parse_time_ms(str(log_entry.get("receive_time") or log_entry.get("time") or payload.get("time")))
        row = (
            str(labels.get("instance_id") or "unknown"),
            event_time_ms,
            receive_time_ms,
            str(labels.get("machine_id") or "unknown"),
            str(labels.get("organization_name") or ""),
            str(labels.get("project_name") or ""),
            str(labels.get("container_group_name") or ""),
            str(labels.get("container_group_version") or ""),
            kind,
            event,
            str(payload.get("client_version") or ""),
            int(payload.get("attempt") or 0),
            int(payload.get("exit_code") or 0),
            str(payload.get("severity") or log_entry.get("severity") or "default"),
        )
        with self._lock, self._db:
            if kind == "honeygain_event" and event == "disconnected":
                # New monitors emit both the native line and a structured
                # transition. Prefer that transition over the legacy fallback.
                second_start = (event_time_ms // 1000) * 1000
                same_event = (row[0], second_start, second_start + 1000)
                if row[10]:
                    self._db.execute(
                        "DELETE FROM runtime_events WHERE instance_id=? AND event_time_ms>=? AND event_time_ms<? "
                        "AND kind='honeygain_event' AND event='disconnected' AND client_version=''",
                        same_event,
                    )
                elif self._db.execute(
                    "SELECT 1 FROM runtime_events WHERE instance_id=? AND event_time_ms>=? AND event_time_ms<? "
                    "AND kind='honeygain_event' AND event='disconnected' AND client_version!='' LIMIT 1",
                    same_event,
                ).fetchone():
                    return False
            cursor = self._db.execute(
                """
                INSERT OR IGNORE INTO runtime_events(
                    instance_id, event_time_ms, receive_time_ms, machine_id,
                    organization_name, project_name, container_group_name,
                    container_group_version, kind, event, client_version,
                    attempt, exit_code, severity
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                row,
            )
            return cursor.rowcount > 0

    def ingest_many(self, entries: Iterable[Dict[str, Any]]) -> int:
        return sum(1 for entry in entries if self.ingest(entry))

    def query_events(self, start_ms: int, end_ms: int, limit: int = 1000) -> Dict[str, Any]:
        if end_ms <= start_ms:
            raise ValueError("end must be after start")
        if limit < 1 or limit > 10_000:
            raise ValueError("limit must be between 1 and 10000")
        with self._lock:
            rows = self._db.execute(
                """
                SELECT instance_id, event_time_ms, receive_time_ms, machine_id,
                       organization_name, project_name, container_group_name,
                       container_group_version, kind, event, client_version,
                       attempt, exit_code, severity
                FROM runtime_events
                WHERE event_time_ms >= ? AND event_time_ms < ?
                ORDER BY event_time_ms DESC, instance_id DESC
                LIMIT ?
                """,
                (start_ms, end_ms, limit),
            ).fetchall()
        events = [dict(row) for row in rows]
        counts: Dict[str, int] = {}
        for event in events:
            counts[event["event"]] = counts.get(event["event"], 0) + 1
        return {
            "schema_version": 1,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "event_count": len(events),
            "counts": counts,
            "events": events,
        }

    def watermark_ms(self) -> Optional[int]:
        with self._lock:
            row = self._db.execute("SELECT watermark_ms FROM ingest_state WHERE singleton=1").fetchone()
        return row[0] if row and row[0] is not None else None

    def record_poll(self, watermark_ms: int, new_samples: int, error: str = "", now_ms: Optional[int] = None) -> None:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        success = None if error else now_ms
        safe_error = error[:500]
        with self._lock, self._db:
            self._db.execute(
                """
                UPDATE ingest_state SET watermark_ms=?, last_poll_ms=?,
                    last_success_ms=coalesce(?, last_success_ms), last_new_samples=?, last_error=?
                WHERE singleton=1
                """,
                (watermark_ms, now_ms, success, new_samples, safe_error),
            )

    def rollup(self, before_ms: Optional[int] = None) -> int:
        if before_ms is None:
            before_ms = (int(time.time() * 1000) // MINUTE_MS) * MINUTE_MS
        with self._lock, self._db:
            count = int(self._db.execute("SELECT count(*) FROM samples WHERE sample_time_ms < ?", (before_ms,)).fetchone()[0])
            self._db.execute(
                """
                INSERT INTO minute_rollups
                    (minute_ms, instance_id, machine_id, sample_count, eth_rx_bytes, eth_tx_bytes,
                     captured_rx_bytes, captured_tx_bytes, unassigned_rx_bytes, unassigned_tx_bytes,
                     reset_count, partial_interval_count, eth_rx_rate_sum, eth_tx_rate_sum,
                     coverage_sum, first_sample_ms, last_sample_ms, peak_rate, peak_time_ms)
                WITH ranked AS (
                    SELECT *, (sample_time_ms / 60000) * 60000 AS minute_ms,
                           row_number() OVER (
                               PARTITION BY (sample_time_ms / 60000), instance_id
                               ORDER BY (eth_rx_rate + eth_tx_rate) DESC,
                                        sample_time_ms ASC, sequence ASC
                           ) AS peak_rank
                    FROM samples WHERE sample_time_ms < ?
                )
                SELECT minute_ms, instance_id, max(machine_id), count(*),
                       sum(eth_rx_bytes), sum(eth_tx_bytes), sum(captured_rx_bytes), sum(captured_tx_bytes),
                       sum(unassigned_rx_bytes), sum(unassigned_tx_bytes), sum(counter_reset), sum(partial_interval),
                       sum(eth_rx_rate), sum(eth_tx_rate), sum(coverage_percent),
                       min(sample_time_ms), max(sample_time_ms),
                       max(CASE WHEN peak_rank = 1 THEN eth_rx_rate + eth_tx_rate END),
                       max(CASE WHEN peak_rank = 1 THEN sample_time_ms END)
                FROM ranked
                GROUP BY minute_ms, instance_id
                ON CONFLICT(minute_ms, instance_id) DO UPDATE SET
                    machine_id=excluded.machine_id, sample_count=excluded.sample_count,
                    eth_rx_bytes=excluded.eth_rx_bytes, eth_tx_bytes=excluded.eth_tx_bytes,
                    captured_rx_bytes=excluded.captured_rx_bytes, captured_tx_bytes=excluded.captured_tx_bytes,
                    unassigned_rx_bytes=excluded.unassigned_rx_bytes, unassigned_tx_bytes=excluded.unassigned_tx_bytes,
                    reset_count=excluded.reset_count, partial_interval_count=excluded.partial_interval_count,
                    eth_rx_rate_sum=excluded.eth_rx_rate_sum, eth_tx_rate_sum=excluded.eth_tx_rate_sum,
                    coverage_sum=excluded.coverage_sum, first_sample_ms=excluded.first_sample_ms,
                    last_sample_ms=excluded.last_sample_ms, peak_rate=excluded.peak_rate,
                    peak_time_ms=excluded.peak_time_ms
                WHERE excluded.sample_count >= minute_rollups.sample_count
                """,
                (before_ms,),
            )
            self._db.execute(
                """
                INSERT INTO minute_app_rollups(minute_ms, instance_id, app_name, rx_bytes, tx_bytes)
                SELECT (sample_time_ms / 60000) * 60000, instance_id, app_name, sum(rx_bytes), sum(tx_bytes)
                FROM app_samples WHERE sample_time_ms < ?
                GROUP BY (sample_time_ms / 60000), instance_id, app_name
                ON CONFLICT(minute_ms, instance_id, app_name) DO UPDATE SET
                    rx_bytes=excluded.rx_bytes, tx_bytes=excluded.tx_bytes
                WHERE (SELECT sample_count FROM minute_rollups m
                       WHERE m.minute_ms=excluded.minute_ms AND m.instance_id=excluded.instance_id) =
                      (SELECT count(*) FROM samples s
                       WHERE s.instance_id=excluded.instance_id
                         AND (s.sample_time_ms / 60000) * 60000=excluded.minute_ms)
                """,
                (before_ms,),
            )
        return count

    def prune(self, now_ms: Optional[int] = None) -> int:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        cutoff = now_ms - self.raw_retention_days * 86400 * 1000
        self.rollup(before_ms=cutoff)
        with self._lock, self._db:
            cursor = self._db.execute("DELETE FROM samples WHERE sample_time_ms < ?", (cutoff,))
            return max(0, cursor.rowcount)

    def _raw_rows(self, start_ms: int, end_ms: int) -> List[sqlite3.Row]:
        return self._db.execute(
            """
            SELECT * FROM samples WHERE sample_time_ms >= ? AND sample_time_ms < ?
            ORDER BY sample_time_ms, sequence
            """,
            (start_ms, end_ms),
        ).fetchall()

    def _box_stats(self, start_ms: int, end_ms: int, instance_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Aggregate exact per-instance metrics from minute summaries plus uncovered raw edges."""
        rollup_start = ((start_ms + MINUTE_MS - 1) // MINUTE_MS) * MINUTE_MS
        rollup_end = (end_ms // MINUTE_MS) * MINUTE_MS
        stats: Dict[str, Dict[str, Any]] = {}

        def add(
            name: str,
            sample_count: int,
            partial_count: int,
            rx_bytes: int,
            tx_bytes: int,
            rx_rate_sum: int,
            tx_rate_sum: int,
            coverage_sum: float,
            first_ms: int,
            last_ms: int,
            peak_rate: int,
            peak_time_ms: int,
        ) -> None:
            value = stats.setdefault(
                name,
                {
                    "sample_count": 0,
                    "partial_count": 0,
                    "rx_bytes": 0,
                    "tx_bytes": 0,
                    "rx_rate_sum": 0,
                    "tx_rate_sum": 0,
                    "coverage_sum": 0.0,
                    "first_ms": None,
                    "last_ms": None,
                    "peak_rate": 0,
                    "peak_time_ms": None,
                },
            )
            value["sample_count"] += int(sample_count)
            value["partial_count"] += int(partial_count)
            value["rx_bytes"] += int(rx_bytes)
            value["tx_bytes"] += int(tx_bytes)
            value["rx_rate_sum"] += int(rx_rate_sum)
            value["tx_rate_sum"] += int(tx_rate_sum)
            value["coverage_sum"] += float(coverage_sum)
            value["first_ms"] = first_ms if value["first_ms"] is None else min(value["first_ms"], first_ms)
            value["last_ms"] = last_ms if value["last_ms"] is None else max(value["last_ms"], last_ms)
            if peak_rate > value["peak_rate"] or (
                peak_rate == value["peak_rate"]
                and (value["peak_time_ms"] is None or peak_time_ms < value["peak_time_ms"])
            ):
                value["peak_rate"] = int(peak_rate)
                value["peak_time_ms"] = int(peak_time_ms)

        rollup_sql = """
            SELECT instance_id, sample_count, partial_interval_count, eth_rx_bytes, eth_tx_bytes,
                   eth_rx_rate_sum, eth_tx_rate_sum, coverage_sum, first_sample_ms, last_sample_ms,
                   peak_rate, peak_time_ms
            FROM minute_rollups
            WHERE minute_ms >= ? AND minute_ms < ?
        """
        rollup_params: List[Any] = [rollup_start, rollup_end]
        if instance_id is not None:
            rollup_sql += " AND instance_id=?"
            rollup_params.append(instance_id)
        for row in self._db.execute(rollup_sql, rollup_params).fetchall():
            add(
                row["instance_id"], row["sample_count"], row["partial_interval_count"],
                row["eth_rx_bytes"], row["eth_tx_bytes"], row["eth_rx_rate_sum"],
                row["eth_tx_rate_sum"], row["coverage_sum"], row["first_sample_ms"],
                row["last_sample_ms"], row["peak_rate"], row["peak_time_ms"],
            )

        raw_sql = """
            SELECT s.instance_id, s.sample_time_ms, s.sequence, s.partial_interval,
                   s.eth_rx_bytes, s.eth_tx_bytes, s.eth_rx_rate, s.eth_tx_rate,
                   s.coverage_percent
            FROM samples s
            WHERE s.sample_time_ms >= ? AND s.sample_time_ms < ?
              AND NOT EXISTS (
                  SELECT 1 FROM minute_rollups m
                  WHERE m.instance_id=s.instance_id
                    AND m.minute_ms=(s.sample_time_ms / 60000) * 60000
                    AND m.minute_ms >= ? AND m.minute_ms < ?
              )
        """
        raw_params: List[Any] = [start_ms, end_ms, rollup_start, rollup_end]
        if instance_id is not None:
            raw_sql += " AND s.instance_id=?"
            raw_params.append(instance_id)
        for row in self._db.execute(raw_sql, raw_params).fetchall():
            rate = int(row["eth_rx_rate"]) + int(row["eth_tx_rate"])
            add(
                row["instance_id"], 1, row["partial_interval"], row["eth_rx_bytes"],
                row["eth_tx_bytes"], row["eth_rx_rate"], row["eth_tx_rate"],
                row["coverage_percent"], row["sample_time_ms"], row["sample_time_ms"],
                rate, row["sample_time_ms"],
            )
        return stats

    def _box_app_totals(self, start_ms: int, end_ms: int) -> Dict[str, Tuple[int, int]]:
        rollup_start = ((start_ms + MINUTE_MS - 1) // MINUTE_MS) * MINUTE_MS
        rollup_end = (end_ms // MINUTE_MS) * MINUTE_MS
        totals: Dict[str, List[int]] = {}
        for row in self._db.execute(
            """
            SELECT instance_id, sum(rx_bytes) AS rx_bytes, sum(tx_bytes) AS tx_bytes
            FROM minute_app_rollups
            WHERE app_name='honeygain' AND minute_ms >= ? AND minute_ms < ?
            GROUP BY instance_id
            """,
            (rollup_start, rollup_end),
        ).fetchall():
            totals[row["instance_id"]] = [int(row["rx_bytes"] or 0), int(row["tx_bytes"] or 0)]
        for row in self._db.execute(
            """
            SELECT a.instance_id, sum(a.rx_bytes) AS rx_bytes, sum(a.tx_bytes) AS tx_bytes
            FROM app_samples a
            WHERE a.app_name='honeygain' AND a.sample_time_ms >= ? AND a.sample_time_ms < ?
              AND NOT EXISTS (
                  SELECT 1 FROM minute_rollups m
                  WHERE m.instance_id=a.instance_id
                    AND m.minute_ms=(a.sample_time_ms / 60000) * 60000
                    AND m.minute_ms >= ? AND m.minute_ms < ?
              )
            GROUP BY a.instance_id
            """,
            (start_ms, end_ms, rollup_start, rollup_end),
        ).fetchall():
            total = totals.setdefault(row["instance_id"], [0, 0])
            total[0] += int(row["rx_bytes"] or 0)
            total[1] += int(row["tx_bytes"] or 0)
        return {name: (value[0], value[1]) for name, value in totals.items()}

    def query_boxes(self, start_ms: int, end_ms: int, expected_reporters: int = 10) -> Dict[str, Any]:
        if end_ms <= start_ms:
            raise ValueError("end must be after start")
        with self._lock:
            # A snapshot older than the live threshold cannot contribute to
            # current fleet values, so keep this exact-second search bounded.
            snapshot_start_ms = max(start_ms, end_ms - 60_000)
            fleet = self._db.execute(
                """
                SELECT (sample_time_ms / 1000) * 1000 AS sample_time_ms,
                       count(DISTINCT instance_id) AS reporters
                FROM samples
                WHERE sample_time_ms >= ? AND sample_time_ms < ?
                GROUP BY (sample_time_ms / 1000)
                HAVING count(DISTINCT instance_id) >= ?
                ORDER BY sample_time_ms DESC LIMIT 1
                """,
                (snapshot_start_ms, end_ms, expected_reporters),
            ).fetchone()
            if fleet is None:
                fleet = self._db.execute(
                    """
                    SELECT (sample_time_ms / 1000) * 1000 AS sample_time_ms,
                           count(DISTINCT instance_id) AS reporters
                    FROM samples
                    WHERE (sample_time_ms / 1000) = (
                        SELECT max(sample_time_ms / 1000) FROM samples
                        WHERE sample_time_ms >= ? AND sample_time_ms < ?
                    )
                    GROUP BY (sample_time_ms / 1000)
                    """,
                    (snapshot_start_ms, end_ms),
                ).fetchone()
            fleet_snapshot_ms = fleet["sample_time_ms"] if fleet else None
            snapshot_rows: Dict[str, sqlite3.Row] = {}
            if fleet_snapshot_ms is not None:
                for snapshot in self._db.execute(
                    """
                    SELECT instance_id, eth_rx_rate AS eth_rx_bytes, eth_tx_rate AS eth_tx_bytes, sequence
                    FROM samples WHERE sample_time_ms>=? AND sample_time_ms<?
                    ORDER BY instance_id, sample_time_ms DESC, sequence DESC
                    """,
                    (fleet_snapshot_ms, fleet_snapshot_ms + 1000),
                ).fetchall():
                    snapshot_rows.setdefault(snapshot["instance_id"], snapshot)

            selected_stats = self._box_stats(start_ms, end_ms)
            app_totals = self._box_app_totals(start_ms, end_ms)
            boxes = []
            for instance_id, stats in sorted(
                selected_stats.items(), key=lambda item: (-int(item[1]["last_ms"]), item[0])
            ):
                latest = self._db.execute(
                    """
                    SELECT s.*, seg.first_seen_ms AS segment_first_seen_ms,
                           coalesce(nullif(s.public_ip, ''), seg.public_ip, '') AS effective_public_ip,
                           a.rx_bytes AS honeygain_rx_bytes, a.tx_bytes AS honeygain_tx_bytes,
                           a.process_count AS honeygain_process_count,
                           a.socket_count AS honeygain_socket_count,
                           a.tcp_socket_count AS honeygain_tcp_socket_count,
                           a.tcp_established_count AS honeygain_tcp_established_count,
                           a.udp_socket_count AS honeygain_udp_socket_count,
                           a.state AS honeygain_state
                    FROM samples s
                    LEFT JOIN instance_segments seg ON seg.instance_id=s.instance_id
                    LEFT JOIN app_samples a
                      ON a.instance_id=s.instance_id AND a.sample_time_ms=s.sample_time_ms
                     AND a.sequence=s.sequence AND a.app_name='honeygain'
                    WHERE s.instance_id=? AND s.sample_time_ms>=? AND s.sample_time_ms<?
                    ORDER BY s.sample_time_ms DESC, s.sequence DESC LIMIT 1
                    """,
                    (instance_id, start_ms, end_ms),
                ).fetchone()
                segment = self._db.execute(
                    "SELECT machine_id, first_seen_ms, public_ip FROM instance_segments WHERE instance_id=?",
                    (instance_id,),
                ).fetchone()
                first_seen_ms = int(segment["first_seen_ms"] if segment else stats["first_ms"])
                profile_end_ms = int(stats["last_ms"])
                first_profile = self._box_stats(first_seen_ms, first_seen_ms + 300_000, instance_id).get(instance_id)
                last_profile = self._box_stats(max(0, profile_end_ms - 300_000), profile_end_ms + 1, instance_id).get(instance_id)

                def average_rate(value: Optional[Dict[str, Any]]) -> float:
                    if not value or not value["sample_count"]:
                        return 0.0
                    return float(value["rx_rate_sum"] + value["tx_rate_sum"]) / value["sample_count"]

                first_average = average_rate(first_profile)
                last_average = average_rate(last_profile)
                sample_count = int(stats["sample_count"])
                average_rx = float(stats["rx_rate_sum"]) / sample_count
                average_tx = float(stats["tx_rate_sum"]) / sample_count
                latest_rx = int(latest["eth_rx_rate"] if latest else 0)
                latest_tx = int(latest["eth_tx_rate"] if latest else 0)
                app_rx, app_tx = app_totals.get(instance_id, (0, 0))
                snapshot = snapshot_rows.get(instance_id)
                snapshot_value = None
                if snapshot:
                    snapshot_rx = int(snapshot["eth_rx_bytes"] or 0)
                    snapshot_tx = int(snapshot["eth_tx_bytes"] or 0)
                    snapshot_value = {
                        "time_ms": fleet_snapshot_ms,
                        "rx_bytes_per_second": snapshot_rx,
                        "tx_bytes_per_second": snapshot_tx,
                        "bytes_per_second": snapshot_rx + snapshot_tx,
                    }
                expected = max(1, (int(stats["last_ms"]) - int(stats["first_ms"])) // 1000 + 1)
                box = {
                    "instance_id": instance_id,
                    "machine_id": latest["machine_id"] if latest else (segment["machine_id"] if segment else "unknown"),
                    "public_ip": latest["effective_public_ip"] if latest else (segment["public_ip"] if segment else ""),
                    "public_ip_status": latest["public_ip_status"] if latest else "unknown",
                    "capture_mode": latest["capture_mode"] if latest else "unknown",
                    "source": {
                        "organization": latest["organization_name"] if latest else "",
                        "project": latest["project_name"] if latest else "",
                        "container_group": latest["container_group_name"] if latest else "",
                        "version": latest["container_group_version"] if latest else "",
                    },
                    "first_seen_ms": first_seen_ms,
                    "first_sample_ms": int(stats["first_ms"]),
                    "last_sample_ms": int(stats["last_ms"]),
                    "sample_count": sample_count,
                    "partial_interval_count": int(stats["partial_count"]),
                    "expected_sample_count": expected,
                    "missing_sample_count": max(0, expected - sample_count),
                    "completeness_percent": min(100.0, 100.0 * sample_count / expected),
                    "is_live": snapshot_value is not None and end_ms - fleet_snapshot_ms <= LIVE_SAMPLE_GRACE_MS,
                    "snapshot": snapshot_value,
                    "totals": {"rx_bytes": int(stats["rx_bytes"]), "tx_bytes": int(stats["tx_bytes"])},
                    "observed_average": {
                        "rx_bytes_per_second": average_rx,
                        "tx_bytes_per_second": average_tx,
                        "bytes_per_second": average_rx + average_tx,
                    },
                    "peak": {"bytes_per_second": int(stats["peak_rate"]), "time_ms": stats["peak_time_ms"]},
                    "latest": {
                        "rx_bytes_per_second": latest_rx,
                        "tx_bytes_per_second": latest_tx,
                        "bytes_per_second": latest_rx + latest_tx,
                    },
                    "first_5m_average_bytes_per_second": first_average,
                    "last_5m_average_bytes_per_second": last_average,
                    "slowdown_ratio": (last_average / first_average) if first_average > 0 else None,
                    "average_coverage_percent": float(stats["coverage_sum"]) / sample_count,
                    "honeygain": {
                        "state": latest["honeygain_state"] if latest and latest["honeygain_state"] else "unknown",
                        "process_count": int(latest["honeygain_process_count"] or 0) if latest else 0,
                        "socket_count": int(latest["honeygain_socket_count"] or 0) if latest else 0,
                        "tcp_socket_count": int(latest["honeygain_tcp_socket_count"] or 0) if latest else 0,
                        "tcp_established_count": int(latest["honeygain_tcp_established_count"] or 0) if latest else 0,
                        "udp_socket_count": int(latest["honeygain_udp_socket_count"] or 0) if latest else 0,
                        "rx_bytes": app_rx,
                        "tx_bytes": app_tx,
                    },
                }
                box.update(
                    {
                        "last_ms": box["last_sample_ms"], "samples": box["sample_count"],
                        "rx_bytes": box["totals"]["rx_bytes"], "tx_bytes": box["totals"]["tx_bytes"],
                        "now_rx": box["latest"]["rx_bytes_per_second"],
                        "now_tx": box["latest"]["tx_bytes_per_second"],
                        "honeygain_rx": box["honeygain"]["rx_bytes"],
                        "honeygain_tx": box["honeygain"]["tx_bytes"],
                        "honeygain_sockets": box["honeygain"]["socket_count"],
                        "honeygain_state": box["honeygain"]["state"],
                    }
                )
                boxes.append(box)
        return {
            "schema_version": 2,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "expected_reporter_count": expected_reporters,
            "fleet_snapshot_ms": fleet_snapshot_ms,
            "snapshot_reporter_count": len(snapshot_rows),
            "reporter_count": len(snapshot_rows),
            "boxes": boxes,
        }

    def query_range(self, start_ms: int, end_ms: int, bucket_seconds: int) -> Dict[str, Any]:
        if end_ms <= start_ms:
            raise ValueError("end must be after start")
        if bucket_seconds < 1 or bucket_seconds > 86400:
            raise ValueError("bucket must be between 1 and 86400 seconds")
        bucket_ms = bucket_seconds * 1000
        with self._lock:
            use_rollups = bucket_seconds >= 60 and start_ms % MINUTE_MS == 0 and bucket_ms % MINUTE_MS == 0
            rollup_start = ((start_ms + MINUTE_MS - 1) // MINUTE_MS) * MINUTE_MS if use_rollups else end_ms + MINUTE_MS
            rollups = []
            if use_rollups:
                rollups = self._db.execute(
                    """
                    SELECT * FROM minute_rollups
                    WHERE minute_ms >= ? AND minute_ms + 60000 <= ? ORDER BY minute_ms
                    """,
                    (rollup_start, end_ms),
                ).fetchall()
            raw_rows = self._db.execute(
                """
                SELECT s.* FROM samples s
                WHERE s.sample_time_ms >= ? AND s.sample_time_ms < ?
                  AND NOT EXISTS (
                      SELECT 1 FROM minute_rollups m
                      WHERE m.instance_id=s.instance_id
                        AND m.minute_ms=(s.sample_time_ms / 60000) * 60000
                        AND m.minute_ms >= ? AND m.minute_ms + 60000 <= ?
                  )
                ORDER BY s.sample_time_ms, s.sequence
                """,
                (
                    start_ms,
                    end_ms,
                    rollup_start,
                    end_ms,
                ),
            ).fetchall()
            raw_apps = self._db.execute(
                """
                SELECT a.instance_id, a.sample_time_ms, a.sequence, a.app_name, a.rx_bytes, a.tx_bytes
                FROM app_samples a
                WHERE a.sample_time_ms >= ? AND a.sample_time_ms < ?
                  AND NOT EXISTS (
                      SELECT 1 FROM minute_rollups m
                      WHERE m.instance_id=a.instance_id
                        AND m.minute_ms=(a.sample_time_ms / 60000) * 60000
                        AND m.minute_ms >= ? AND m.minute_ms + 60000 <= ?
                  )
                """,
                (
                    start_ms,
                    end_ms,
                    rollup_start,
                    end_ms,
                ),
            ).fetchall()
            rollup_apps = []
            if rollups:
                rollup_apps = self._db.execute(
                    """
                    SELECT * FROM minute_app_rollups
                    WHERE minute_ms >= ? AND minute_ms + 60000 <= ?
                    """,
                    (rollup_start, end_ms),
                ).fetchall()
            segments = self._db.execute(
                """
                SELECT instance_id, machine_id, first_seen_ms, last_seen_ms, public_ip
                FROM instance_segments WHERE last_seen_ms >= ? AND first_seen_ms < ? ORDER BY first_seen_ms
                """,
                (start_ms, end_ms),
            ).fetchall()
            latest = self._db.execute(
                """
                SELECT instance_id, sample_time_ms, sequence FROM samples
                WHERE sample_time_ms >= ? AND sample_time_ms < ?
                ORDER BY sample_time_ms DESC, sequence DESC LIMIT 1
                """,
                (start_ms, end_ms),
            ).fetchone()
            latest_apps = []
            if latest:
                latest_apps = self._db.execute(
                    """
                    SELECT app_name, process_count, socket_count, state FROM app_samples
                    WHERE instance_id=? AND sample_time_ms=? AND sequence=? ORDER BY app_name
                    """,
                    (latest["instance_id"], latest["sample_time_ms"], latest["sequence"]),
                ).fetchall()

        raw_app_map: Dict[Tuple[str, int, int], Dict[str, Tuple[int, int]]] = {}
        for row in raw_apps:
            minute_key = ((row["sample_time_ms"] // MINUTE_MS) * MINUTE_MS, row["instance_id"])
            key = (row["instance_id"], row["sample_time_ms"], row["sequence"])
            raw_app_map.setdefault(key, {})[row["app_name"]] = (row["rx_bytes"], row["tx_bytes"])
        rollup_app_map: Dict[Tuple[int, str], Dict[str, Tuple[int, int]]] = {}
        for row in rollup_apps:
            rollup_app_map.setdefault((row["minute_ms"], row["instance_id"]), {})[row["app_name"]] = (
                row["rx_bytes"], row["tx_bytes"]
            )

        buckets: Dict[int, Dict[str, Any]] = {}

        def add_event(timestamp_ms: int, instance_id: str, values: Dict[str, int], apps: Dict[str, Tuple[int, int]]) -> None:
            bucket = start_ms + ((timestamp_ms - start_ms) // bucket_ms) * bucket_ms
            point = buckets.setdefault(
                bucket,
                {
                    "time_ms": bucket,
                    "sample_count": 0,
                    "eth_rx": 0,
                    "eth_tx": 0,
                    "captured_rx": 0,
                    "captured_tx": 0,
                    "unassigned_rx": 0,
                    "unassigned_tx": 0,
                    "reset_count": 0,
                    "partial_count": 0,
                    "instances": set(),
                    "apps": {name: [0, 0] for name in APP_NAMES},
                },
            )
            point["sample_count"] += values["sample_count"]
            for field in ("eth_rx", "eth_tx", "captured_rx", "captured_tx", "unassigned_rx", "unassigned_tx", "reset_count", "partial_count"):
                point[field] += values[field]
            point["instances"].add(instance_id)
            for name, (rx, tx) in apps.items():
                if name in point["apps"]:
                    point["apps"][name][0] += rx
                    point["apps"][name][1] += tx

        for row in rollups:
            add_event(
                row["minute_ms"],
                row["instance_id"],
                {
                    "sample_count": row["sample_count"],
                    "eth_rx": row["eth_rx_bytes"],
                    "eth_tx": row["eth_tx_bytes"],
                    "captured_rx": row["captured_rx_bytes"],
                    "captured_tx": row["captured_tx_bytes"],
                    "unassigned_rx": row["unassigned_rx_bytes"],
                    "unassigned_tx": row["unassigned_tx_bytes"],
                    "reset_count": row["reset_count"],
                    "partial_count": row["partial_interval_count"],
                },
                rollup_app_map.get((row["minute_ms"], row["instance_id"]), {}),
            )
        for row in raw_rows:
            add_event(
                row["sample_time_ms"],
                row["instance_id"],
                {
                    "sample_count": 1,
                    "eth_rx": row["eth_rx_bytes"],
                    "eth_tx": row["eth_tx_bytes"],
                    "captured_rx": row["captured_rx_bytes"],
                    "captured_tx": row["captured_tx_bytes"],
                    "unassigned_rx": row["unassigned_rx_bytes"],
                    "unassigned_tx": row["unassigned_tx_bytes"],
                    "reset_count": row["counter_reset"],
                    "partial_count": row["partial_interval"],
                },
                raw_app_map.get((row["instance_id"], row["sample_time_ms"], row["sequence"]), {}),
            )

        totals = {
            "eth0": {"rx_bytes": 0, "tx_bytes": 0},
            "captured": {"rx_bytes": 0, "tx_bytes": 0},
            "unassigned": {"rx_bytes": 0, "tx_bytes": 0},
            "applications": {name: {"rx_bytes": 0, "tx_bytes": 0} for name in APP_NAMES},
        }
        points = []
        for bucket in sorted(buckets):
            value = buckets[bucket]
            captured_total = value["captured_rx"] + value["captured_tx"]
            unassigned_total = value["unassigned_rx"] + value["unassigned_tx"]
            coverage = 0.0 if captured_total == 0 else max(0.0, 100.0 * (captured_total - min(captured_total, unassigned_total)) / captured_total)
            applications = {}
            for name in APP_NAMES:
                rx, tx = value["apps"][name]
                applications[name] = {
                    "rx_bytes": rx,
                    "tx_bytes": tx,
                    "rx_bytes_per_second": rx / bucket_seconds,
                    "tx_bytes_per_second": tx / bucket_seconds,
                }
                totals["applications"][name]["rx_bytes"] += rx
                totals["applications"][name]["tx_bytes"] += tx
            points.append(
                {
                    "time_ms": bucket,
                    "sample_count": value["sample_count"],
                    "instance_ids": sorted(value["instances"]),
                    "counter_resets": value["reset_count"],
                    "partial_intervals": value["partial_count"],
                    "coverage_percent": coverage,
                    "eth0": {
                        "rx_bytes": value["eth_rx"],
                        "tx_bytes": value["eth_tx"],
                        "rx_bytes_per_second": value["eth_rx"] / bucket_seconds,
                        "tx_bytes_per_second": value["eth_tx"] / bucket_seconds,
                    },
                    "captured": {
                        "rx_bytes": value["captured_rx"],
                        "tx_bytes": value["captured_tx"],
                        "rx_bytes_per_second": value["captured_rx"] / bucket_seconds,
                        "tx_bytes_per_second": value["captured_tx"] / bucket_seconds,
                    },
                    "unassigned": {
                        "rx_bytes": value["unassigned_rx"],
                        "tx_bytes": value["unassigned_tx"],
                        "rx_bytes_per_second": value["unassigned_rx"] / bucket_seconds,
                        "tx_bytes_per_second": value["unassigned_tx"] / bucket_seconds,
                    },
                    "applications": applications,
                }
            )
            totals["eth0"]["rx_bytes"] += value["eth_rx"]
            totals["eth0"]["tx_bytes"] += value["eth_tx"]
            totals["captured"]["rx_bytes"] += value["captured_rx"]
            totals["captured"]["tx_bytes"] += value["captured_tx"]
            totals["unassigned"]["rx_bytes"] += value["unassigned_rx"]
            totals["unassigned"]["tx_bytes"] += value["unassigned_tx"]

        return {
            "schema_version": 1,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "bucket_seconds": bucket_seconds,
            "points": points,
            "totals": totals,
            "latest_apps": {r["app_name"]: {"process_count": r["process_count"], "socket_count": r["socket_count"], "state": r["state"]} for r in latest_apps},
            "reallocations": [dict(row) for row in segments],
        }

    def status(self) -> Dict[str, Any]:
        with self._lock:
            aggregate = self._db.execute(
                "SELECT count(*) AS count, min(sample_time_ms) AS first_ms, max(sample_time_ms) AS last_ms FROM samples"
            ).fetchone()
            latest = self._db.execute(
                """
                SELECT instance_id, machine_id, sample_time_ms, receive_time_ms, coverage_percent,
                       eth_rx_rate, eth_tx_rate, public_ip_status, organization_name,
                       project_name, container_group_name, container_group_version,
                       capture_mode, interval_milliseconds, partial_interval
                FROM samples ORDER BY sample_time_ms DESC, sequence DESC LIMIT 1
                """
            ).fetchone()
            state = self._db.execute("SELECT * FROM ingest_state WHERE singleton=1").fetchone()
            segment_count = self._db.execute("SELECT count(*) FROM instance_segments").fetchone()[0]
        result: Dict[str, Any] = {
            "sample_count": int(aggregate["count"]),
            "first_sample_ms": aggregate["first_ms"],
            "last_sample_ms": aggregate["last_ms"],
            "segment_count": int(segment_count),
            "database_path": str(self.path),
            "database_size_bytes": self.path.stat().st_size if self.path.exists() else 0,
            "watermark_ms": state["watermark_ms"],
            "last_poll_ms": state["last_poll_ms"],
            "last_success_ms": state["last_success_ms"],
            "last_new_samples": state["last_new_samples"],
            "last_error": state["last_error"],
        }
        if latest:
            result.update(
                {
                    "latest_instance_id": latest["instance_id"],
                    "latest_machine_id": latest["machine_id"],
                    "latest_receive_time_ms": latest["receive_time_ms"],
                    "latest_coverage_percent": latest["coverage_percent"],
                    "latest_rx_bytes_per_second": latest["eth_rx_rate"],
                    "latest_tx_bytes_per_second": latest["eth_tx_rate"],
                    "public_ip_status": latest["public_ip_status"],
                    "capture_mode": latest["capture_mode"],
                    "latest_interval_milliseconds": latest["interval_milliseconds"],
                    "latest_partial_interval": bool(latest["partial_interval"]),
                    "source": {
                        "organization": latest["organization_name"],
                        "project": latest["project_name"],
                        "container_group": latest["container_group_name"],
                        "version": latest["container_group_version"],
                    },
                }
            )
        return result


def compact_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)

`````

### `repocket-monitor/observe.py`

<!-- RP_FILE: repocket-monitor/observe.py SHA256: 6c52ef8591ad9b02425517c4f82b4fd2972d044c1865e96c0598fe6239c1030c -->
`````python
"""Read Repocket worker records from SSH2 and keep the local traffic history."""
import argparse
from datetime import datetime, timezone
import fcntl
import getpass
import hashlib
import json
import os
import re
from pathlib import Path
import sqlite3
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / '.hg1/repocket'
GROUP = '/projects/default/containers/rp-test-us'

def stamp(ms):
    return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')

def api(path,body=None):
    if path not in (GROUP,GROUP+'/instances','/log-entries'):raise ValueError('Outside Repocket read scope')
    key=subprocess.check_output([str(ROOT/'.runtime/keychain-store'),'--read','--service','salad-bandwidth-api','--account',getpass.getuser()],text=True).strip()
    config='header = '+json.dumps('Salad-Api-Key: '+key)+'\nheader = "Content-Type: application/json"\n'
    if body is not None:config+='data-binary = '+json.dumps(json.dumps(body))+'\n'
    r=subprocess.run(['curl','-sS','--max-time','20','--config','-','--write-out','\n%{http_code}','https://api.salad.com/api/public/organizations/ssh2'+path],input=config,text=True,capture_output=True,timeout=25)
    raw,code=r.stdout.rsplit('\n',1)
    if r.returncode or code!='200':raise RuntimeError('Salad read returned HTTP '+code)
    return json.loads(raw)

def save(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,separators=(',',':')));os.replace(temporary,path)

def fetch(start,end,depth=0):
    if depth>20:raise RuntimeError('Log window could not be read completely')
    body={'query':'resource.type = "container" and resource.labels.container_group_name = "rp-test-us" and text_log startswith "RP_MON "','start_time':stamp(start),'end_time':stamp(end),'page_size':100,'sort_order':'asc'}
    rows=api('/log-entries',body).get('items',[])
    if len(rows)>=100:
        middle=(start+end)//2
        if middle<=start:raise RuntimeError('Too many worker records at one timestamp')
        return fetch(start,middle,depth+1)+fetch(middle,end,depth+1)
    return rows

def insert(db,rows):
    added=0;size=0
    for row in sorted(rows,key=lambda x:x.get('time','')):
        raw=row.get('text_log','')
        if not raw.startswith('RP_MON '):continue
        try:
            item=json.loads(raw[7:]);kind=item['kind'];at=int(item['time_ms'])
            if item.get('service')!='repocket' or kind not in ('start','tick','minute','recovery'):continue
            if not isinstance(item.get('run'),str) or not isinstance(item.get('machine'),str):continue
            if kind=='minute' and (item['end_ms']<=item['start_ms'] or item['rx_bytes']<0 or item['tx_bytes']<0 or item['elapsed_ms']!=item['end_ms']-item['start_ms']):continue
        except (ValueError,KeyError,TypeError):continue
        value=json.dumps(item,separators=(',',':'));identity=hashlib.sha256(value.encode()).hexdigest()
        cursor=db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?)',(identity,at,item['machine'],item['run'],kind,value))
        if cursor.rowcount:added+=1;size+=len(value.encode())
    db.commit()
    if added:db.execute('INSERT INTO writes VALUES(?,?,?)',(int(time.time()*1000),added,size));db.commit()
    return added

def snapshot(db,deployment,group,instances,now,backfill,read_error=None):
    events=[json.loads(r[0]) for r in db.execute("SELECT body FROM events WHERE kind IN ('start','minute') OR rowid IN (SELECT rowid FROM (SELECT rowid,row_number() OVER (PARTITION BY run ORDER BY time_ms DESC,rowid DESC) AS rank FROM events WHERE kind='tick') WHERE rank=1) ORDER BY time_ms,rowid")]
    latest={};by_run={};minutes={};unbucketed=0
    for item in events:
        run=item['run'];state=by_run.setdefault(run,{'run':run,'machine':item['machine'],'instance':item.get('instance'),'revision':item.get('revision',1),'started_ms':item.get('started_ms',item['time_ms']),'ip':'','rx_bytes':0,'tx_bytes':0,'minutes':0})
        if item.get('ip'):state['ip']=item['ip']
        if item['kind'] in ('start','tick'):
            state.update(phase=item.get('phase','starting'),reason=item.get('reason',''),source_ms=item['time_ms'],restart_count=item.get('restart_count',0),diagnostics=item.get('diagnostics'),device_id=item.get('device_id'),last_ping_ms=item.get('last_ping_ms'),log_counts=item.get('log_counts',{}),policy=item.get('policy'))
            identity=(item['machine'],item.get('instance'))
            if identity not in latest or item['started_ms']>=latest[identity]['started_ms']:latest[identity]=state
        if item['kind']=='minute':
            amount=item['rx_bytes']+item['tx_bytes'];state['rx_bytes']+=item['rx_bytes'];state['tx_bytes']+=item['tx_bytes'];state['minutes']+=1
            state.update(last_mb=amount/1e6,last_elapsed_seconds=item['elapsed_ms']/1000,last_end_ms=item['end_ms'],last_mb_per_minute=amount/1e6*60000/item['elapsed_ms'])
            bucket=item['start_ms']//60000*60000
            nearest=round(item['start_ms']/60000)*60000
            if 59000<=item['elapsed_ms']<=61000 and abs(item['start_ms']-nearest)<=1000:bucket=nearest
            if item['elapsed_ms']>61000 or item['end_ms']>bucket+61000:
                unbucketed+=1;continue
            minute=minutes.setdefault(bucket,{'time_ms':bucket,'mb':0,'partial':False,'contributions':{}})
            contribution=minute['contributions'].setdefault(run,{'run':run,'machine':item['machine'],'instance':item.get('instance'),'ip':item.get('ip',''),'mb':0,'elapsed_seconds':0})
            contribution['mb']+=amount/1e6;contribution['elapsed_seconds']+=item['elapsed_ms']/1000;minute['mb']+=amount/1e6;minute['partial']|=item.get('partial',False)
    workers=[]
    for instance in instances:
        worker=dict(latest.get((instance['machine_id'],instance['id']),{}))
        if not worker and instance.get('update_time'):
            text=re.sub(r'\.(\d+)(?=[+-])',lambda m:'.'+m.group(1)[:6].ljust(6,'0'),instance['update_time'].replace('Z','+00:00'))
            began=int(datetime.fromisoformat(text).timestamp()*1000)
            candidates=[w for w in latest.values() if w['machine']==instance['machine_id'] and w.get('started_ms',0)>=began-60000 and w.get('source_ms',0)>=began]
            worker=dict(max(candidates,key=lambda w:w['started_ms'],default={}))
        worker.update(machine=instance['machine_id'],salad_instance=instance['id'],salad_state=instance['state'],current=True)
        age=now-worker.get('source_ms',0);worker['source_age_ms']=age if worker.get('source_ms') else None
        worker['status']=worker.get('phase','starting') if age<60000 and age>=-10000 and instance['state']=='running' else ('stale' if worker.get('source_ms') else instance['state'])
        worker['total_mb']=(worker.get('rx_bytes',0)+worker.get('tx_bytes',0))/1e6 if worker.get('minutes') else None;workers.append(worker)
    history=[]
    for minute in sorted(minutes.values(),key=lambda x:x['time_ms']):
        minute['contributions']=list(minute['contributions'].values());history.append(minute)
    total_network_mb=sum((r['rx_bytes']+r['tx_bytes'])/1e6 for r in by_run.values())
    if history:
        indexed={m['time_ms']:m for m in history};last=max(history[-1]['time_ms'],now//60000*60000-60000)
        history=[indexed.get(at,{'time_ms':at,'mb':None,'partial':True,'contributions':[]}) for at in range(max(history[0]['time_ms'],last-119*60000),last+1,60000)]
    cost_rate=0.05
    return {'generated_ms':now,'source_ms':max((w.get('source_ms',0)for w in workers),default=0),'organization':'ssh2','group':'rp-test-us','group_id':deployment['id'],'group_state':group.get('current_state',{}).get('status'),'desired':deployment['replicas'],'running':sum(i['state']=='running'for i in instances),'connected':sum(w['status']=='connected'for w in workers),'workers':workers,'minutes':history[-120:],'total_network_mb':total_network_mb,'unbucketed_intervals':unbucketed,'record_count':db.execute('SELECT count(*) FROM events').fetchone()[0],'database_bytes':sum(p.stat().st_size for p in DATA.glob('traffic.sqlite3*')),'saved_bytes_last_minute':db.execute('SELECT coalesce(sum(bytes),0) FROM writes WHERE time_ms>=?',(now-60000,)).fetchone()[0],'backfill_through_ms':backfill,'error':read_error,'recent_recovery':[json.loads(row[0]) for row in db.execute("SELECT body FROM events WHERE kind='recovery' ORDER BY time_ms DESC LIMIT 5")],'measurement':'Container interface RX+TX bytes, including overhead; not provider-credited traffic.','provider_url':'https://repocket.com/dashboard/share-internet','salad_url':'https://portal.salad.com/organizations/ssh2/projects/default/containers/rp-test-us','budget_usd':5,'estimated_full_fleet_usd_per_hour':cost_rate,'cost_basis':'Estimate from the existing one-CPU, one-GB lowest-priority fleet; invoice not reconciled.'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
    os.umask(0o077);DATA.mkdir(parents=True,exist_ok=True)
    lock=(DATA/'observer.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    deployment=json.loads((DATA/'deployment.json').read_text())
    db=sqlite3.connect(DATA/'traffic.sqlite3');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,time_ms INTEGER,machine TEXT,run TEXT,kind TEXT,body TEXT)')
    db.execute('CREATE INDEX IF NOT EXISTS event_time ON events(time_ms)')
    db.execute('CREATE TABLE IF NOT EXISTS writes(time_ms INTEGER,records INTEGER,bytes INTEGER)')
    state_path=DATA/'cursor.json';state=json.loads(state_path.read_text()) if state_path.exists() else {}
    beginning=int(datetime.fromisoformat(deployment.get('start_requested_at',deployment['created_at'])).timestamp()*1000)
    cursor=state.get('through_ms',beginning);last_reconcile=state.get('last_reconcile_ms',int(time.time()*1000))
    reconcile_cursor=state.get('reconcile_cursor');reconcile_end=state.get('reconcile_end')
    while True:
        began=time.monotonic();now=int(time.time()*1000)
        try:
            group=api(GROUP)
            if group['id']!=deployment['id']:raise RuntimeError('Repocket deployment identity changed')
            instances=api(GROUP+'/instances')['instances']
            end=min(now,cursor+600000);start=max(beginning,cursor-300000)
            rows=fetch(start,end)
            if end<now:rows+=fetch(max(beginning,now-180000),now)
            if reconcile_cursor is None and now-last_reconcile>=300000:
                reconcile_cursor=max(beginning,now-3600000);reconcile_end=now
            if reconcile_cursor is not None:
                stop=min(reconcile_end,reconcile_cursor+60000);rows+=fetch(reconcile_cursor,stop);reconcile_cursor=stop
                if reconcile_cursor>=reconcile_end:reconcile_cursor=None;reconcile_end=None;last_reconcile=now
            if int(time.time()*1000)-now>15000:
                fresh=int(time.time()*1000);rows+=fetch(max(beginning,fresh-60000),fresh)
                group=api(GROUP);instances=api(GROUP+'/instances')['instances']
                if group['id']!=deployment['id']:raise RuntimeError('Repocket deployment identity changed')
            added=insert(db,rows);cursor=end;save(state_path,{'through_ms':cursor,'last_reconcile_ms':last_reconcile,'reconcile_cursor':reconcile_cursor,'reconcile_end':reconcile_end})
            value=snapshot(db,deployment,group,instances,int(time.time()*1000),cursor);save(DATA/'view.json',value)
            print(json.dumps({'checked_at':stamp(value['generated_ms']),'running':value['running'],'connected':value['connected'],'inserted':added,'network_mb':round(value['total_network_mb'],3)}),flush=True)
        except Exception as error:
            message=str(error) if isinstance(error,RuntimeError) else type(error).__name__
            path=DATA/'view.json';value=json.loads(path.read_text()) if path.exists() else {'workers':[],'minutes':[],'desired':10,'running':0,'connected':0}
            value.update(generated_ms=int(time.time()*1000),error=message);save(path,value);print('Repocket recorder:',message,flush=True)
            if args.once:raise SystemExit(1)
        if args.once:break
        time.sleep(max(1,(1 if cursor<now-60000 else 15)-(time.monotonic()-began)))

if __name__=='__main__':main()

`````

### `repocket-monitor/start.js`

<!-- RP_FILE: repocket-monitor/start.js SHA256: f162447e703f157ac682a8d99b5e893a6500dc8370288be6802ed435941f6928 -->
`````javascript
if (process.env.RP_DIAGNOSTICS === '1') {
  const net=require('net'), base='/app/node_modules/@geonode/repocket-peer-client/dist/src/';
  const stats={client_started_ms:Date.now(),attempts:0,connected:0,responses:0,failed:0,failed_without_response:0,closed_without_response:0,closed_failed_without_response:0,rx_bytes:0,tx_bytes:0,http:0,socks:0,errors:{},connect_forwarding:'transparent',errors_by_target:{},dns_fallback:{attempted:0,recovered:0,failed:0}};
  const active=new Set(), seen=new WeakSet();let context='';
  function sample(item){const rx=item.socket.bytesRead||0,tx=item.socket.bytesWritten||0;stats.rx_bytes+=Math.max(0,rx-item.rx);stats.tx_bytes+=Math.max(0,tx-item.tx);item.rx=rx;item.tx=tx;if(rx>0&&!item.responded){item.responded=true;stats.responses++;}}
  function failure(item,error){sample(item);if(!item.failed){item.failed=true;stats.failed++;if(!item.responded)stats.failed_without_response++;}const code=['ECONNRESET','ETIMEDOUT','ECONNREFUSED','EHOSTUNREACH','EPIPE','ENOTFOUND','EAI_AGAIN','ECONNABORTED','ENETUNREACH','EADDRNOTAVAIL','EMFILE','ENFILE'].includes(error?.code)?error.code:'OTHER';stats.errors[code]=(stats.errors[code]||0)+1;
    const family=net.isIP(error?.address||'');const group=code+'/'+item.kind+'/'+item.hostType+'/'+(family?'ipv'+family:'unresolved');stats.errors_by_target[group]=(stats.errors_by_target[group]||0)+1;
  }
  function finish(item){if(item.finished)return;item.finished=true;sample(item);if(!item.responded){stats.closed_without_response++;if(item.failed)stats.closed_failed_without_response++;}active.delete(item);}
  function track(socket,host){if(seen.has(socket))return;seen.add(socket);const ip=net.isIP(host||'');const item={socket,host,kind:context,hostType:ip?'ipv'+ip:typeof host!=='string'||/[\s/:\[\]]/.test(host)?'malformed':'domain',rx:0,tx:0,responded:false,failed:false};active.add(item);stats.attempts++;stats[context]++;
    socket.once('connect',()=>stats.connected++);socket.on('error',error=>failure(item,error));socket.on('timeout',()=>failure(item,{code:'ETIMEDOUT'}));
    socket.once('close',()=>finish(item));return item;}
  const dns=require('dns'),lookup=dns.lookup;
  dns.lookup=function(host,options,callback){
    if(!context||typeof callback!=='function'||options?.family===6||typeof host!=='string'||net.isIP(host)||/[\s/:\[\]]/.test(host))return lookup.apply(this,arguments);
    return lookup.call(this,host,options,(error,address,family)=>{if(error?.code!=='ENOTFOUND')return callback(error,address,family);stats.dns_fallback.attempted++;
      dns.resolve4(host,(failure,addresses)=>{if(!failure&&addresses?.length){stats.dns_fallback.recovered++;return options?.all?callback(null,addresses.map(address=>({address,family:4}))):callback(null,addresses[0],4);}stats.dns_fallback.failed++;callback(error,address,family);});});
  };
  const originalConnect=net.Socket.prototype.connect;
  net.Socket.prototype.connect=function(...args){const option=Array.isArray(args[0])?args[0][0]:args[0],host=option&&typeof option==='object'?option.host:args[1];const item=context?track(this,host):null;try{return originalConnect.apply(this,args);}catch(error){if(item){failure(item,error);finish(item);}throw error;}};
  for(const [file,name,method,kind] of [['P2P/target.socket.js','TargetSocket','connect','http'],['P2P/socks5/socks5.socket.js','Socket5Handler','createConnection','socks']]){
    const prototype=require(base+file)[name].prototype, original=prototype[method];prototype[method]=function(...args){const previous=context;context=kind;try{return original.apply(this,args);}finally{context=previous;}};
  }
  Object.defineProperty(require(base+'P2P/target.socket.js').TargetSocket.prototype,'shouldUseBufferProcessor',{configurable:true,get(){return this.useBufferProcessor&&this.isSMTP;}});
  function publish(){for(const item of active)sample(item);if(process.connected&&process.send)process.send({type:'rp_diagnostics',...stats,active:active.size,time_ms:Date.now()},()=>{});}
  publish();setInterval(publish,15000).unref();process.once('beforeExit',publish);
} else {
const fs = require('fs');
const http = require('http');
const https = require('https');
const {spawn} = require('child_process');
const started = Date.now();
const identity = {service:'repocket',revision:10,machine:process.env.SALAD_MACHINE_ID || 'local',instance:process.env.SALAD_INSTANCE_ID || 'local',run:`${process.env.SALAD_INSTANCE_ID || 'local'}:${started}`,started_ms:started};
let diagnostics=null,deviceId='',lastPing=0;const logCounts={};
const replacement={window_ms:600000,min_target_bytes:1000000};
let history=[],lastClientActivity=started,policy={...replacement,state:'observing',observed_ms:0};
let child, phase='starting', reason='', ip='', failedSince=started, stopping=false, fatal=false;
const counters = () => ({rx:Number(fs.readFileSync('/sys/class/net/eth0/statistics/rx_bytes','utf8')),tx:Number(fs.readFileSync('/sys/class/net/eth0/statistics/tx_bytes','utf8'))});
const emit = value => process.stdout.write('RP_MON '+JSON.stringify({...identity,...value})+'\n');
let previous={...counters(),time_ms:started};
function tick() { const time_ms=Date.now(); emit({kind:'tick',time_ms,...counters(),phase,reason,ip,diagnostics,device_id:deviceId,last_ping_ms:lastPing,log_counts:logCounts,policy}); }
function minute(final=false) {
  const next={...counters(),time_ms:Date.now()}, elapsed_ms=next.time_ms-previous.time_ms;
  if(elapsed_ms>0 && next.rx>=previous.rx && next.tx>=previous.tx) emit({kind:'minute',time_ms:next.time_ms,start_ms:previous.time_ms,end_ms:next.time_ms,rx_bytes:next.rx-previous.rx,tx_bytes:next.tx-previous.tx,elapsed_ms,partial:final||elapsed_ms<59000||elapsed_ms>61000,phase,reason,ip,diagnostics,device_id:deviceId,log_counts:logCounts,policy});
  previous=next;
}
function assessReplacement() {
  const d=diagnostics,now=d.time_ms;if(history.length&&history[0].client!==d.client_started_ms)history=[];
  const errors={...d.errors,...Object.fromEntries(Object.entries(logCounts).map(([name,n])=>['log '+name,n]))};
  const next={at:now,client:d.client_started_ms,bytes:d.rx_bytes+d.tx_bytes,replies:d.responses,failures:d.closed_failed_without_response,errors};
  history.push(next);while(history.length>1&&history[1].at<=now-replacement.window_ms)history.shift();
  const first=history[0],elapsed=now-first.at,bytes=next.bytes-first.bytes,replies=next.replies-first.replies,failures=next.failures-first.failures,outcomes=replies+failures;
  const recentErrors=Object.fromEntries(Object.entries(errors).map(([name,n])=>[name,n-(first.errors[name]||0)]).filter(([,n])=>n>0));
  policy={...replacement,state:elapsed<replacement.window_ms?'observing':'keeping',checked_ms:now,observed_ms:elapsed,target_bytes:bytes,replies,failures,outcomes,errors:recentErrors};
  if(elapsed<replacement.window_ms||stopping||fatal)return;
  if(bytes<replacement.min_target_bytes)reallocate('Only '+bytes+' target bytes in '+Math.round(elapsed/1000)+'s; minimum '+replacement.min_target_bytes);
}
function reallocate(why) {
  if(stopping) return; stopping=true; phase='reallocating'; reason=why;policy={...policy,state:'reallocating',reason:why}; minute(true); tick();
  if(child) child.kill('SIGTERM');
  const body=JSON.stringify({reason:'Repocket: '+why});
  const request=http.request({host:'169.254.169.254',path:'/v1/reallocate',method:'POST',headers:{Metadata:'true','Content-Type':'application/json','Content-Length':Buffer.byteLength(body)},timeout:10000},response=>{
    emit({kind:'recovery',time_ms:Date.now(),reason:why,http_status:response.statusCode,ip}); response.resume();
    response.on('end',()=>process.exit(75));
  });
  request.on('timeout',()=>request.destroy()); request.on('error',()=>{emit({kind:'recovery',time_ms:Date.now(),reason:why,http_status:null,ip});process.exit(75);}); request.end(body);
  setTimeout(()=>process.exit(75),12000);
}
function acceptLine(line, exited=false) {
  if(stopping||fatal)return;
  if(/^docker-[0-9a-f]{16}$/.test(line.trim()))deviceId=line.trim();
  if(line.includes('MainSocket -> PING'))lastPing=lastClientActivity=Date.now();
  for(const label of ['onError: error when connecting to socket-server','MainSocket -> error','Peer monitor error','_markPeerAsAlive -> Error happened','Failed to get settings','Failed to create connection','Buffer size exceeds maximum allowed size','Record length exceeds maximum allowed size','Connection retries exceeded','Socket timeout','proxy timeout','ENOTFOUND','EAI_AGAIN','Unsupported SOCKS version','Unsupported method','not support'])if(line.includes(label))logCounts[label]=(logCounts[label]||0)+1;
  if(/invalid.?api.?key|invalid.?credential|login failed/i.test(line)||(phase==='starting'&&/unauthori[sz]ed/i.test(line))){fatal=true;phase='authorization_error';reason='Repocket rejected the credentials';if(child)child.kill('SIGTERM');return;}
  if(exited)return;
  if(/\bpeer connected\b/i.test(line)){phase='connected';reason='';failedSince=0;lastClientActivity=Date.now();}
  else if(/peer disconnected|peer resetting|peer_server_error|refresh_token_required/i.test(line)){
    phase='reconnecting';reason=(line.match(/peer disconnected|peer resetting|peer_server_error|refresh_token_required/i)||['Peer connection error'])[0];if(!failedSince)failedSince=Date.now();
  }
  else if(phase!=='connected'&&/ECONN|ETIMEDOUT|ENOTFOUND/i.test(line))reason=(line.match(/ECONN\w+|ETIMEDOUT|ENOTFOUND/i)||['Connection error'])[0];
}
function launch() {
  if(stopping||fatal)return;
  phase='starting';reason='';failedSince=Date.now();diagnostics=null;deviceId='';lastPing=0;history=[];lastClientActivity=Date.now();policy={...replacement,state:'observing',observed_ms:0};
  let exited=false;const worker=spawn(process.execPath,['--require',__filename,'/app/dist/index.js'],{cwd:'/app',env:{...process.env,RP_DIAGNOSTICS:'1'},stdio:['ignore','pipe','pipe','ipc']});child=worker;
  worker.on('message',message=>{if(worker===child&&!exited&&!stopping&&!fatal&&message?.type==='rp_diagnostics'&&Number.isFinite(message.closed_failed_without_response)&&Date.now()-message.time_ms<45000){diagnostics=message;lastClientActivity=Date.now();assessReplacement();}});
  for(const stream of [worker.stdout,worker.stderr]) {let buffer='';stream.on('data',data=>{if(worker!==child)return;buffer+=data.toString();let at;while((at=buffer.indexOf('\n'))>=0){acceptLine(buffer.slice(0,at),exited);buffer=buffer.slice(at+1);}if(buffer.length>16384)buffer='';});}
  worker.on('error',()=>{if(worker===child&&!stopping&&!fatal)reallocate('Repocket process could not start');});
  worker.on('exit',()=>{exited=true;if(worker===child&&!stopping&&!fatal)reallocate('Repocket process exited');});
  worker.on('close',()=>{if(worker===child)child=null;});
}
function publicIP() {
  const req=https.get('https://api.ipify.org',{timeout:8000},response=>{let body='';response.on('data',data=>{if(body.length<64)body+=data;});response.on('end',()=>{if(/^\d{1,3}(\.\d{1,3}){3}$/.test(body.trim()))ip=body.trim();});});
  req.on('timeout',()=>req.destroy());req.on('error',()=>{});
}
function stop() {if(stopping)return;stopping=true;phase='stopped';minute(true);tick();if(child)child.kill('SIGTERM');setTimeout(()=>process.exit(0),1000);}
process.on('SIGTERM',stop);process.on('SIGINT',stop);
emit({kind:'start',time_ms:started,...counters(),phase,ip});launch();publicIP();
setInterval(()=>{if(!stopping)tick();},15000);
setInterval(()=>{if(!stopping&&!ip)publicIP();},30000);
function nextMinute(){setTimeout(()=>{if(!stopping){minute();nextMinute();}},60000-Date.now()%60000);}
nextMinute();
setInterval(()=>{
  if(stopping||fatal)return;
  if(phase==='connected'&&Date.now()-lastClientActivity>=60000){reallocate('Repocket client diagnostics and control activity stopped for 60 seconds');return;}
  if(failedSince&&Date.now()-failedSince>=60000)reallocate('Repocket control connection unavailable for 60 seconds');
},5000);

}

`````

### `restore-control.py`

<!-- RP_FILE: restore-control.py SHA256: 9e31fef72e842faac72803107cfa0f6edff8f99c7e30f540b31be2ac2d07d23b -->
`````python
"""Recreate or attach to the documented RP Salad group; no secrets saved locally."""
import argparse
import base64
from datetime import datetime, timezone
import getpass
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DATA = Path.home() / '.hg1/repocket'
ORG, PROJECT, GROUP = 'ssh2', 'default', 'rp-test-us'
IMAGE = 'docker.io/repocket/repocket@sha256:5888d756de7e0e74b95b5eb08bb93f4240a0ce840c910a7e528d1143ad0c502b'
SOURCE_SHA = 'f162447e703f157ac682a8d99b5e893a6500dc8370288be6802ed435941f6928'
BASE = f'https://api.salad.com/api/public/organizations/{ORG}/projects/{PROJECT}/containers'
KEY = None


def now():
    return datetime.now(timezone.utc).isoformat()


def worker():
    source = (ROOT / 'repocket-monitor/start.js').read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA:
        raise RuntimeError('Worker differs from this recovery edition; inspect before deploying')
    encoded = base64.b64encode(source).decode('ascii')
    command = ['/bin/sh', '-c', 'umask 077; printf "%s" "$@" | base64 -d > /tmp/repocket-start.js; exec /usr/local/bin/node /tmp/repocket-start.js', 'policy-start']
    command += [encoded[i:i + 900] for i in range(0, len(encoded), 900)]
    assert len(command) <= 100 and all(len(part) <= 1000 for part in command)
    return command


def payload(email, rp_key):
    return {'name': GROUP, 'display_name': 'RP', 'replicas': 10,
            'autostart_policy': False, 'restart_policy': 'always', 'country_codes': ['us'],
            'container': {'image': IMAGE, 'command': worker(), 'priority': 'batch',
                          'resources': {'cpu': 1, 'memory': 1024, 'gpu_classes': [], 'shm_size': 64},
                          'environment_variables': {'RP_EMAIL': email, 'RP_API_KEY': rp_key}}}


def api(method, suffix='', body=None):
    global KEY
    if KEY is None:
        helper = ROOT / '.runtime/keychain-store'
        if sys.platform == 'darwin' and helper.exists():
            result = subprocess.run([str(helper), '--read', '--service', 'salad-bandwidth-api',
                                     '--account', getpass.getuser()], capture_output=True, text=True)
            KEY = result.stdout.strip() if result.returncode == 0 else None
        if not KEY:
            KEY = getpass.getpass('Salad API key (hidden): ').strip()
        if not KEY:
            raise RuntimeError('Salad API key is required')
    config = 'header = ' + json.dumps('Salad-Api-Key: ' + KEY) + '\nheader = "Content-Type: application/json"\n'
    if body is not None:
        config += 'data-binary = ' + json.dumps(json.dumps(body)) + '\n'
    try:
        result = subprocess.run(['curl', '-sS', '--max-time', '30', '--config', '-',
                                 '--request', method, '--write-out', '\n%{http_code}', BASE + suffix],
                                input=config, text=True, capture_output=True, timeout=35)
    except subprocess.TimeoutExpired:
        raise RuntimeError('Salad request timed out; inspect before retrying a mutation') from None
    if result.returncode or '\n' not in result.stdout:
        raise RuntimeError('Salad transport failed; inspect before retrying a mutation')
    content, status = result.stdout.rsplit('\n', 1)
    # Do not print response bodies: a provider could echo credentials/configuration.
    status = int(status)
    return status, json.loads(content) if 200 <= status < 300 and content.strip() else {}


def get_group():
    status, group = api('GET', '/' + GROUP)
    if status != 200:
        raise RuntimeError('Group read returned HTTP ' + str(status))
    return group


def check_group(group):
    c = group.get('container', {})
    resources = c.get('resources', {})
    if not (group.get('name') == GROUP and group.get('display_name') == 'RP'
            and c.get('image') == IMAGE and c.get('command') == worker()
            and resources.get('cpu') == 1 and resources.get('memory') == 1024
            and resources.get('shm_size') == 64 and resources.get('gpu_classes') == []
            and group.get('autostart_policy') is False
            and set(c.get('environment_variables', {})) == {'RP_EMAIL', 'RP_API_KEY'}
            and all(c['environment_variables'].values())
            and group.get('replicas') == 10 and group.get('country_codes') == ['us']
            and group.get('restart_policy') == 'always'
            and (group.get('priority') or c.get('priority')) == 'batch'):
        raise RuntimeError('Existing group differs from this recovery edition; it was not modified')


def save(group, capture_from=None):
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = DATA / 'deployment.json'
    old = json.loads(path.read_text()) if path.exists() else {}
    if old and old.get('id') != group['id']:
        raise RuntimeError('Local RP data belongs to another group; move that directory to a backup first')
    record = {**old, 'organization': ORG, 'project': PROJECT, 'group': GROUP, 'id': group['id'],
              'replicas': 10, 'image': IMAGE, 'version': group['version'], 'source_revision': 10,
              'source_sha256': SOURCE_SHA, 'created_at': group.get('create_time', now()),
              'start_requested_at': capture_from or old.get('start_requested_at') or now(),
              'budget_usd': 5}
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, indent=2) + '\n')
    temporary.chmod(0o600)
    temporary.replace(path)


def summary(group):
    return {'id': group['id'], 'name': group['display_name'], 'version': group['version'],
            'replicas': group['replicas'], 'state': group.get('current_state', {}),
            'worker_sha256': SOURCE_SHA}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'inspect', 'create', 'attach', 'start', 'stop'])
    args = parser.parse_args()
    if args.action == 'plan':
        print(json.dumps(payload('ENTER_YOUR_RP_EMAIL', 'ENTER_YOUR_RP_DOCKER_KEY'), indent=2))
        return
    if args.action == 'create':
        if (DATA / 'deployment.json').exists():
            raise RuntimeError('Local deployment state already exists: use inspect/attach; do not create a duplicate')
        status, _ = api('GET', '/' + GROUP)
        if status != 404:
            raise RuntimeError('Create requires confirmed HTTP 404; read returned HTTP ' + str(status) + '. Use inspect/attach for an existing group')
        email = input('Repocket account email: ').strip()
        rp_key = getpass.getpass('Repocket Docker API key (hidden): ').strip()
        if not email or not rp_key:
            raise RuntimeError('Both Repocket values are required')
        status, group = api('POST', '', payload(email, rp_key))
        if status not in (200, 201, 202) or 'id' not in group:
            raise RuntimeError('Create returned HTTP ' + str(status) + '; inspect before retrying')
        save(group)
        print(json.dumps(summary(group), indent=2))
        print('Created. Run start explicitly when ready to consume prepaid credit.')
        return
    group = get_group()
    if args.action == 'inspect':
        check_group(group)
        print(json.dumps(summary(group), indent=2))
        return
    check_group(group)
    if args.action == 'attach':
        save(group)
        print('Attached local recorder state to ' + group['id'] + '; existing capture cursor/history preserved if present')
        return
    state_file = DATA / 'deployment.json'
    if not state_file.exists() or json.loads(state_file.read_text()).get('id') != group['id']:
        raise RuntimeError('Run attach before controlling this group')
    current = group.get('current_state', {}).get('status')
    if args.action == 'start' and current == 'running':
        print('Already running; no start request sent')
        return
    if args.action == 'stop' and current == 'stopped':
        print('Already stopped; no stop request sent')
        return
    status, _ = api('POST', '/' + GROUP + '/' + args.action)
    if status not in (200, 202, 204):
        raise RuntimeError(args.action + ' returned HTTP ' + str(status) + '; inspect current state')
    print(args.action + ' request accepted; run inspect to check completion')


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(str(error))

`````

### `restore-dashboard.py`

<!-- RP_FILE: restore-dashboard.py SHA256: e6a4631de974ed7172667a1aacece0aa3b021be95a841997421d770e49bcc1b2 -->
`````python
"""Serve the preserved dashboard's RP routes without starting other provider pollers."""
import argparse
from http.server import ThreadingHTTPServer
from pathlib import Path
from dashboard.server import make_handler
from dashboard.store import Store

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port', type=int, default=8787)
args = parser.parse_args()
root = Path(__file__).resolve().parent
store = Store(Path.home() / '.hg1/repocket/recovery-dashboard.sqlite3')
handler = make_handler(store, lambda: {'poll_state': 'disabled'}, root / 'dashboard/static')
server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
print(f'RP monitor: http://127.0.0.1:{args.port}/#rp', flush=True)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
    store.close()

`````

### `scripts/dashboard-configure-keychain.sh`

<!-- RP_FILE: scripts/dashboard-configure-keychain.sh SHA256: f964f87eb082fc1805aaf4ef34a43af6b7f16f61b8acfde9022f372535d5f40f -->
`````bash
#!/bin/bash
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
runtime_dir="$repo_dir/.runtime"
helper="$runtime_dir/keychain-store"
source_file="$repo_dir/scripts/keychain-store.swift"
account="$(id -un)"

mkdir -p "$runtime_dir"
chmod 700 "$runtime_dir"
if [ ! -x "$helper" ] || [ "$source_file" -nt "$helper" ]; then
  /usr/bin/xcrun swiftc "$source_file" -o "$helper.next"
  chmod 700 "$helper.next"
  mv -f "$helper.next" "$helper"
fi

printf 'Paste the Salad API key, then press Return (typing stays hidden): ' >&2
IFS= read -r -s salad_key
printf '\n' >&2
if [ -z "$salad_key" ]; then
  echo "No key entered." >&2
  exit 1
fi
printf '%s' "$salad_key" | "$helper" --service salad-bandwidth-api --account "$account"
unset salad_key
"$helper" --read --service salad-bandwidth-api --account "$account" >/dev/null
echo "Salad API key saved and verified in macOS Keychain."

`````

### `scripts/keychain-store.swift`

<!-- RP_FILE: scripts/keychain-store.swift SHA256: 490eadaf1afb87a0f64bf6248254ccc48ac1171af9e2fc4c796c74c12c5ca045 -->
`````swift
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

`````

