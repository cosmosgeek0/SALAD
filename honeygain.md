# Honeygain — complete rebuild guide

**Reproducibility:** the embedded source and deployment settings are reproducible. New IPs, placement time, traffic demand, provider acceptance and earnings are not fixed outputs of this software. Identical MB or credits are not promised. This verification used isolated reconstruction tests and read-only live comparisons; it did not delete and recreate the paid fleet.

Verified against the running deployment and matching installed source on **7 September 2026, UTC**. This file contains the cloud recipe, the actual container wrapper, local observers, secure credential helper, and service installer. Its source appendix is sufficient to recreate Honeygain's software without the old repository or chat.

## What must survive outside this file

You need access to the Honeygain account, a Salad API key, funded deathadder/default access plus read access to cosmosgeeketh/default and hyperlane/default for the duplicate-registration check, macOS with Python 3.9+ and Xcode Command Line Tools, and the pinned vendor image below. Credentials are deliberately not embedded. Docker is only needed if you want to save/test the image locally; the running Salad clients do not depend on Docker Desktop or this Mac.

This rebuild starts new measurements. Deleted JSONL/SQLite history cannot be calculated back from today's counters. If you need the old chart too, preserve the data directories listed below separately. A Markdown file cannot reproduce a closed-source vendor image if both the registry copy and your image archive are gone.

## Exact deployed configuration

| Setting | Verified value |
|---|---|
| Organization / project | deathadder / default |
| Layout | Ten independent groups; one replica in each |
| Groups | hg1, hg-solo-02 through hg-solo-10 |
| Runtime | Official Honeygain 0.6.6, Linux amd64, one stock client per container |
| Image | docker.io/honeygain/honeygain@sha256:5cd8c361517d0cbae4aa2c75e13239e45f9193ab8e205d57fa29f2e695ea3ec1 |
| CPU / memory / shared memory | 1 CPU / 1,024 MiB / 64 MiB per container; no GPU |
| Placement | US |
| Priority | hg1: batch; the other nine: low |
| Restart policy | always |
| Auto-start flag in current API readback | false; the groups were explicitly started |
| Public networking / probes | None configured |
| Current group revisions | hg1: 8; other nine: 2 |
| Cloud display names / image caching | HG1 Native 0.6.6; HG Solo 02…10 / enabled |
| Wrapper command SHA-256 | d253f4f5dad66c00222f843bd9b0e33d16d7c9a0ed7f64da2742b5a057bcae8d |
| Environment names | HONEYGAIN_EMAIL, HONEYGAIN_PASSWORD, HONEYGAIN_DEVICE_NAME |

The API returns priority at the **group** level, although creation specifies it in container.priority. Do not mistake a missing container.priority in a GET response for the actual scheduling priority.

| Group | Honeygain registration/device name |
|---|---|
| hg1 | salad-us-1 |
| hg-solo-02 | worker-us-1 |
| hg-solo-03 | salad-c4385ee4-0693-505d-8bd4-76f0e37054a9 |
| hg-solo-04 | salad-5cd61ffc-5e1a-7f55-86a6-ebf67cf06478 |
| hg-solo-05 | salad-b8ababd8-ac4b-d45c-b6a0-b499236dee05 |
| hg-solo-06 | salad-45ef0f8f-0a89-6a5d-9f16-9b606250128e |
| hg-solo-07 | salad-eeec7129-d81e-d851-8a2e-2a94747b15d2 |
| hg-solo-08 | salad-62d87783-409d-825e-9125-d5166b9038e0 |
| hg-solo-09 | salad-d645de46-f7cc-1859-98a4-cfe7f88bc346 |
| hg-solo-10 | salad-a1d8dea8-73bc-5356-8980-b652388c1659 |

These registration names are intentional. Reuse them after the previous clients have stopped; do not generate a new name on every retry. Never run two live clients with one registration. If an old deployment still exists in deathadder, cosmosgeeketh, or hyperlane, inspect it before creating replacements. New Salad group/instance/machine UUIDs must come from API responses; the old UUIDs are historical identifiers, not reusable creation parameters.

## Rebuild from only this file

1. Run the extraction command. It checks every embedded file's SHA-256 and refuses to overwrite different existing source. For an intact existing installation, use an empty staging directory instead of copying over live files.

~~~~bash
python3 - "$HOME/Desktop/salad/honeygain.md" "$HOME/Library/Application Support/Salad Bandwidth Dashboard" <<'PY'
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

2. Compile the credential helper and save the Salad key.

~~~~bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
mkdir -p .runtime
chmod 700 .runtime
xcrun swiftc scripts/keychain-store.swift -o .runtime/keychain-store
chmod 700 .runtime/keychain-store
python3 scripts/save-secret.py salad-bandwidth-api
~~~~

Use the existing Salad API key for the account that can access the named organizations. The prompt is hidden; the key goes to macOS Keychain service **salad-bandwidth-api**, account **your macOS login name**. Never put the key in this Markdown, a command argument, or a copied cloud JSON response. A freshly compiled helper may trigger the normal macOS Keychain access prompt. Do not start multiple copies of an observer: each uses a lock.


3. Inspect the offline cloud plan. It performs no login, cloud change, or data write.

~~~~bash
python3 scripts/rebuild-cloud.py honeygain plan
~~~~

4. For a fresh deployment, run the command below. It prompts for the Honeygain email/password, creates only missing named groups, and explicitly starts them. It keeps those credentials in process memory and sends them directly to Salad's container environment. This step starts billable cloud workloads.

~~~~bash
HG_FLEET_DIR="$HOME/.hg1/hg-fleet" python3 scripts/rebuild-cloud.py honeygain create
~~~~

If the cloud groups already survive and only the Mac was lost, use **bind** instead of create:

~~~~bash
HG_FLEET_DIR="$HOME/.hg1/hg-fleet" python3 scripts/rebuild-cloud.py honeygain bind
~~~~

The helper checks the full documented configuration, required credential fields and each registration. In create mode, surviving groups must also match the email/password just entered. A mismatch stops the rebuild before starting that group; secret values are never printed. In bind mode, verify the surviving provider account through the next actual provider reading.

The receipt is saved to ~/.hg1/hg-fleet/deployment.json. This bootstrap does not use the old Fleet.deploy() path that assumes hg1 already exists. That old helper remains in the preserved operational source, but is not the fresh-install recipe.

5. Get a real provider baseline, then a native client/network reading.

~~~~bash
HG_FLEET_DIR="$HOME/.hg1/hg-fleet" python3 scripts/hg-provider-observer.py --once &&
HG_FLEET_DIR="$HOME/.hg1/hg-fleet" python3 scripts/hg-fleet-observer.py --once &&
python3 scripts/initialize-recording.py
~~~~

If Honeygain has not registered all ten devices yet, the provider observer fails explicitly. Wait for registration/recovery and rerun; never fill missing registrations or credits with invented zeros. The baseline initializer refuses to reset an existing test.

6. Start the local recorders. These jobs collect evidence; recovery itself runs in the Salad containers.

~~~~bash
python3 scripts/install-services.py hg-provider hg-fleet fleet
~~~~

For the shared website and its graph, restore website.md as well. Honeygain's own native logs and JSONL observers work independently of that page; the shared fleet recorder can show missing PacketStream inputs until that service is restored.

## Container behavior, exactly

The complete wrapper is generated by recovery_command() in the embedded scripts/hg-fleet-control.py. It launches /app/honeygain with the three environment values and the stock client's terms-acceptance flag.

- It records eth0 RX/TX cumulative byte counters about every ten seconds. Each JSON record is kind=hg_native_sample, with source time, version, counters, current client state and error.
- A positive native “connected and running” line sets connected. Interface activity alone does not.
- “overused” or “unusable” immediately ends the client and requests a new machine.
- A client exit requests replacement. An “already active” registration error gets 15-second retries within the existing two-minute connection window, allowing the old provider session to expire.
- Startup or a persistent disconnection has a 120-second deadline.
- Reallocation calls POST http://169.254.169.254/v1/reallocate with Metadata: true and a JSON reason. It uses the instance's metadata service, not a Salad account key in the image.
- The wrapper logs HG_SELF_REALLOCATE, HG_SELF_IMDS_RESPONSE and HG_SELF_IMDS_ACCEPTED. HTTP 200 or 204 is accepted. Failed requests get three bounded attempts, then exit 75; the configured platform restart policy takes over.
- Request acceptance is not placement completion. Verify that a new instance/machine appears and then provides fresh connected evidence.

There is no provider-credit watchdog inside this wrapper. A connected low-volume client is not automatically removed merely because credits have not increased in a short window. Do not claim that network bytes are paid earnings.

[Salad IMDS reallocation reference](https://docs.salad.com/reference/imds/reallocate).

## Recording and credit sources

| Component | What it records |
|---|---|
| Container wrapper | Native client state and eth0 cumulative counters |
| scripts/hg-fleet-observer.py | Salad group/instance inventory, bounded native log queries, per-worker state/sample |
| scripts/hg-provider-observer.py | Authenticated Honeygain dashboard credits and provider device/IP evidence |
| fleet-test-recorder.py | Shared append-only experiment observations and per-run counter increments |

Provider requests use https://dashboard.honeygain.com with POST /api/v1/users/tokens, then /api/v2/devices, /api/v1/earnings/stats and /api/v1/users/balances. The provider observer reads the account credentials from the surviving hg1 container configuration, keeps its token only in memory, and backs off on failures. Do not export a login token into the dashboard's public JSON.

Network MB is decimal bytes / 1,000,000 and sums receive plus send; relayed data can appear in both directions. Credits are provider observations with a separate clock. The website uses measured counter intervals to estimate minute contributions; it does not invent exact one-second Honeygain measurements.

Source sample.time and runtime instance identity must survive recording. Salad sometimes emits 5–7 fractional timestamp digits; pad/truncate to six before Python 3.9 parsing. After rollout, log resource labels have been observed to retain an old instance ID. The current Honeygain observer matches the current machine and time boundary for the self-recovery wrapper, and uses its fresh state-bearing samples.

## Locations and service operations

| Path | Purpose |
|---|---|
| ~/Desktop/salad-bandwidth-stack/scripts/hg-fleet-control.py | Editable deployment/recovery source |
| ~/Library/Application Support/Salad Bandwidth Dashboard/ | Installed runtime; jobs execute here |
| ~/.hg1/hg-fleet/status.json | Latest safe aggregate inventory/status |
| ~/.hg1/hg-fleet/worker-NN.json | Latest worker snapshots |
| ~/.hg1/hg-fleet/observations.jsonl | Original source timestamps, counters, instances, credits |
| ~/.hg1/hg-fleet/provider-latest.json | Last provider baseline/current observation |
| ~/.hg1/hg-fleet/provider-readings.jsonl | Append-only provider observations |
| ~/.hg1/hg-fleet/provider-feed-status.json | Provider freshness/error |
| ~/.hg1/hg-fleet/provider-api-traffic-latest.json | Provider traffic detail where published |
| ~/.hg1/fleet-tests/ | Shared experiment metadata, network accumulator, observations and events |
| ~/Library/LaunchAgents/com.cosmosgeek.salad-hg-*.plist | The two Honeygain observer jobs |
| ~/Library/LaunchAgents/com.cosmosgeek.salad-fleet-test-recorder.plist | Shared ten-second recorder |

The service installer below uses .out.log/.err.log under these directories. The original running installation used observer.stdout.log/observer.stderr.log and provider-observer.stdout.log/provider-observer.stderr.log for the Honeygain jobs; inspect the actual plist to find the live log names.

~~~~bash
launchctl print "gui/$(id -u)/com.cosmosgeek.salad-hg-fleet-observer"
launchctl kickstart -k "gui/$(id -u)/com.cosmosgeek.salad-hg-fleet-observer"
launchctl kickstart -k "gui/$(id -u)/com.cosmosgeek.salad-hg-provider-observer"
~~~~

Restarting an observer does not reallocate a cloud client. For an individual failed instance, use the exact current instance ID from GET /organizations/deathadder/projects/default/containers/GROUP/instances with POST .../instances/INSTANCE/reallocate. Do not rotate the whole fleet to repair a stale local display.

## Verification before declaring success

Measured recheck on 7 September 2026: the printed extractor restored all nine files from this document alone, validated every manifest hash and rejected both damaged content and conflicting existing files. The isolated creation/start/rebind rehearsal produced the documented ten one-replica groups using simulated Salad responses. Read-only Salad comparisons matched all ten real group configurations and the pinned command digest. The registry still returned the exact Linux amd64 image manifest. No new paid containers were launched by this check.

Read ~/.hg1/hg-fleet/status.json: every claimed connected worker needs a current running instance, a fresh sample and a positive client state without a later error. Confirm the JSONL file advances, and independently confirm the provider-feed status and credit timestamps. On http://127.0.0.1:8787/#hg1, the known running count and confirmed-client count must remain distinct.

For recovery, inspect native logs for HG_SELF_IMDS_ACCEPTED and then compare instance/machine IDs. A test that merely prints a reallocation request is insufficient.

## Mistakes already encountered

| Failure | What the reconstruction must retain |
|---|---|
| Same-node restart loop left “network overused” burning credits | Use the embedded IMDS wrapper, not a plain infinite restart loop |
| Stock process existed but client was disconnected | Confirm native acceptance; do not equate Salad running with working |
| Observer lost the true sample clock | Preserve sample_ms and runtime instance; never reconstruct rates from the end of a fleet sweep |
| Old Salad log instance labels after update | Match actual runtime evidence to current machine/start boundary |
| Bounded log pages hid later recovery | Split full windows and preserve delayed observations; do not silently skip records |
| A 4,683 MB minute overwhelmed the graph | The rejected IP 96.246.178.36 is excluded in dashboard/fleet_test.py; keep exclusion boundaries and cumulative totals consistent |
| The spike ended in a killed Honeygain process | Kernel logs confirmed a memory-cgroup OOM at 23:18:48 UTC on 6 September; memory was 1,024 MiB |
| Interface traffic was mistaken for payment | The affected node showed about 8,971 MB RX+TX across the burst, while provider credits changed 26.13 → 26.15 in that window; cause of the traffic was not established |
| Removing a sample joined traffic across IP/run changes | Preserve missing/excluded intervals as boundaries; do not interpolate across replacements |
| Old start-new helper targeted ps1 | Use the included initializer, which uses ps-test-us and refuses an existing experiment |

The IP exclusion is a dashboard/data-display decision and an earlier one-time replacement, not a permanent cloud IP denylist. Do not claim the wrapper can force Salad never to offer that address again.

The pinned release is the tested runtime. Do not silently substitute latest or claim a new vendor release is equivalent. Honeygain's current documentation states Docker Content Delivery is unavailable; this deployment did not use it. [Official Docker guide](https://support.honeygain.com/hc/en-us/articles/360018979919-How-to-run-Honeygain-on-Docker-Linux).

To preserve the vendor image before a registry disappears:

~~~~bash
docker pull --platform linux/amd64 docker.io/honeygain/honeygain@sha256:5cd8c361517d0cbae4aa2c75e13239e45f9193ab8e205d57fa29f2e695ea3ec1
docker save -o honeygain-0.6.6-amd64.tar docker.io/honeygain/honeygain@sha256:5cd8c361517d0cbae4aa2c75e13239e45f9193ab8e205d57fa29f2e695ea3ec1
~~~~

Keep that archive and the JSONL history in a real backup. Re-import the archive with docker load and publish it to an accessible registry if the original registry is unavailable.

## Complete source appendix

The code below is part of this document, not a link to a missing repository. The manifest hashes the exact extracted text. Files created specifically to make this document usable from an empty directory are labelled rebuild helpers; the operational worker/observer source is preserved.

| Restored file | SHA-256 |
|---|---|
| fleet-test-recorder.py | a82594851df4c0ea52daadb1d751ebcd13ac47954e6fa0913933a0174a43bd24 |
| scripts/hg-fleet-control.py | 636784169bc0a3fd77eecba964f5c474b697bb4ac9f767d9db5fa510b820bcf0 |
| scripts/hg-fleet-observer.py | 419bc42de81169a8f1893411c600f3097ac24498f77083abb7033ab4ecbb2c01 |
| scripts/hg-provider-observer.py | df6011522bffec291015a596646590f2866a2955cdd49488ad9337e8ba6e863e |
| scripts/initialize-recording.py | 4ac3beac391fd2f7e3f52896b62ab2a201a40268161f10e004886832ac984f74 |
| scripts/install-services.py | 3c75ac6e7c82f8b1e06104d59b02c13b073685e0c5f19a4a25a3e7534a7ee4e9 |
| scripts/keychain-store.swift | 490eadaf1afb87a0f64bf6248254ccc48ac1171af9e2fc4c796c74c12c5ca045 |
| scripts/rebuild-cloud.py | 4fde37bb6ea6402a3ab1ce7fe46d935503ee7b6038af0f3c2ec48c0c401c08b9 |
| scripts/save-secret.py | 98e37bb083dd0c10773d1dfdc187780af29f7a62beb361cfc99ec0fc92822e9e |

### fleet-test-recorder.py

<!-- rebuild-file: fleet-test-recorder.py sha256=a82594851df4c0ea52daadb1d751ebcd13ac47954e6fa0913933a0174a43bd24 -->
~~~~~~python
#!/usr/bin/env python3
"""Record independent Salad tests; provider credits never derive from network bytes."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import math
import os
import re
from pathlib import Path
import shutil
import signal
import time
import urllib.request

DATA = Path(os.environ.get('FLEET_TEST_DIR', str(Path.home() / '.hg1/fleet-tests')))
HG_DATA = Path(os.environ.get('HG_FLEET_DIR', str(Path.home() / '.hg1/hg-fleet')))
PS_DATA = Path.home() / '.hg1/packetstream'


def stamp(ms=None):
    return datetime.fromtimestamp((ms or time.time()*1000)/1000, timezone.utc).isoformat()


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default if default is not None else {}


def atomic(path, value):
    temp = Path(str(path) + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def last_provider():
    try:
        rows = (PS_DATA / 'provider-observations.jsonl').read_text().splitlines()
    except OSError:
        return None
    for line in reversed(rows):
        try:
            r = json.loads(line)
            if not isinstance(r.get('provider_bytes'), int):
                continue
            dt = datetime.fromisoformat((r.get('observed_at') or r['recorded_at']).replace('Z', '+00:00'))
            return {'bytes': r['provider_bytes'], 'time_ms': int(dt.timestamp()*1000)}
        except (KeyError, ValueError, TypeError):
            continue
    return None


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            return json.load(response)
    except Exception:
        return {}


def moved(n):
    if isinstance(n.get('rx_moved_bytes'), int) and isinstance(n.get('tx_moved_bytes'), int):
        return n['rx_moved_bytes'], n['tx_moved_bytes']
    # No conversion from a rounded MB display: wait for the repaired collector.
    return None


def exact_counter(value):
    # Salad serializes structured log numbers as doubles, including integer counters.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value) if math.isfinite(value) and 0 <= value <= 2**53 and int(value) == value else None


def accumulate(network, nodes):
    """Sum observed per-run increments, never add a replacement's lifetime baseline."""
    resets = []
    for n in nodes:
        counters = moved(n)
        if counters is None:
            continue
        key = n['run']
        old = network['last'].get(key)
        if old is not None:
            if counters[0] >= old[0] and counters[1] >= old[1]:
                network['rx'] += counters[0]-old[0]
                network['tx'] += counters[1]-old[1]
            else:
                resets.append(key)
        network['last'][key] = list(counters)
    return resets


def inventory_changes(state, result):
    events=[]
    previous=state.get('inventory')
    current={}
    for service in ['ps','hg']:
        for worker in result[service]['workers']:
            identity=worker.get('group') if service=='hg' else worker.get('machine')
            if not identity:continue
            key=service+'/'+identity
            current[key]={k:worker.get(k) for k in ['machine','ip','client_status']}
            old=previous.get(key) if previous is not None else None
            if old:
                for field in ['machine','ip','client_status']:
                    if old.get(field) is not None and current[key].get(field) is not None and old[field]!=current[key][field]:
                        events.append({'time_ms':result['time_ms'],'service':service,'worker':identity,
                                       'action':field+'_changed','previous':old[field],'value':current[key][field]})
            elif previous is not None:
                events.append({'time_ms':result['time_ms'],'service':service,'worker':identity,'action':'worker_appeared'})
    if previous is not None:
        for key in previous.keys()-current.keys():
            service,identity=key.split('/',1)
            events.append({'time_ms':result['time_ms'],'service':service,'worker':identity,'action':'worker_not_observed'})
    state['inventory']=current
    return events


def observation(current, network):
    raw = get('http://127.0.0.1:8789/api/ps1/status')
    view = get('http://127.0.0.1:8787/api/ps1/view')
    now = int(time.time()*1000)
    target=current.get('ps',{})
    target_path='/'.join([target.get('organization','hyperlane'),target.get('project','default'),target.get('group','ps1')])
    census=read(PS_DATA/'native-census.json')
    plain=False
    try:
        census_ms=int(datetime.fromisoformat((census.get('last_success_at') or census.get('checked_at','')).replace('Z','+00:00')).timestamp()*1000)
        plain=census.get('group')==target_path and 0<=now-census_ms<180000
    except (ValueError,TypeError):
        census_ms=0
    if plain:
        entries=[]
        for row in census.get('nodes',[]):
            client=row.get('client_status') or {}
            net=row.get('network') or {}
            try:status_age=now-int(datetime.fromisoformat(client.get('source_time','').replace('Z','+00:00')).timestamp()*1000)
            except (ValueError,TypeError):status_age=None
            entry={'machine':row['machine'],'run':row['machine']+'/'+row['instance_id']+'/'+str(net.get('observer','status')),
                'deployment_current':True,'salad_state':row.get('salad_state'),'client_status':client,
                'client_status_age_ms':status_age,'ip':row.get('ip'),'sample_source':'native_status_only'}
            if net.get('available') and isinstance(net.get('observed_rx_bytes'),int) and isinstance(net.get('observed_tx_bytes'),int):
                entry.update(rx_moved_bytes=net['observed_rx_bytes'],tx_moved_bytes=net['observed_tx_bytes'],
                    sample_age_ms=now-net['received_ms'],source_sample_age_ms=now-net['time_ms'],
                    sample_source='native_minutes',source_granularity_seconds=60,
                    last_interval_seconds=net.get('last_interval_seconds'))
            entries.append(entry)
        raw={'nodes':entries,'accepted_nodes':sum((r.get('client_status')or{}).get('state')=='running' and
                r.get('client_status_age_ms') is not None and -15000<=r['client_status_age_ms']<=600000 for r in entries),
             'connected_machines':[],'deployment_membership_age_ms':now-census_ms}
        view['running_nodes']=sum(r.get('salad_state')=='running' for r in entries)
    membership = {n['machine']: n for n in view.get('nodes', []) if n.get('current')}
    if any('deployment_current' in n for n in raw.get('nodes', [])):
        nodes = [n for n in raw['nodes'] if n.get('deployment_current')]
    else:
        nodes = [n for n in raw.get('nodes', []) if n.get('current') and n.get('machine') in membership]
    workers = []
    for n in nodes:
        client = n.get('client_status') or {}
        if not isinstance(client, dict):
            client = {'state': str(client)}
        counters = moved(n)
        workers.append({'machine': n['machine'], 'run': n['run'], 'ip': n.get('ip'),
                        'state': n.get('salad_state') or membership.get(n['machine'], {}).get('state'),
                        'client_status': client.get('state', 'unknown'),
                        'client_status_age_ms': n.get('client_status_age_ms'),
                        'error': client.get('message') if client.get('state') == 'error' else None,
                        'network_bytes': sum(counters) if counters else None,
                        'received_age_ms': n.get('sample_age_ms'),
                        'source_age_ms': n.get('source_sample_age_ms'),
                        'sample_source':n.get('sample_source'),
                        'source_granularity_seconds':n.get('source_granularity_seconds'),
                        'last_interval_seconds':n.get('last_interval_seconds')})
    resets = accumulate(network, nodes)
    provider = last_provider()
    fresh = [n for n in workers if isinstance(n.get('received_age_ms'), (int,float)) and
             0 <= n['received_age_ms'] <= (150000 if n.get('sample_source')=='native_minutes' else 45000 if n.get('sample_source')=='sysfs_via_salad_logs_1s' else
                                         25000 if n.get('sample_source')=='salad_logs_10s' else 15000)]
    membership_age = raw.get('deployment_membership_age_ms', view.get('membership_age_ms'))
    complete = len(fresh) == 10 and len(workers) == 10 and all(n['network_bytes'] is not None for n in workers)
    complete = complete and membership_age is not None and membership_age < 45000 and not resets
    complete = complete and all(isinstance(n['source_age_ms'],(int,float)) and -15000<=n['source_age_ms']<=60000 for n in workers)
    hg = read(HG_DATA / 'status.json')
    hg_workers = []
    hg_samples = []
    for w in hg.get('workers', []):
        safe = {k:w.get(k) for k in ['group','device','machine','ip','state','client_status','credits','credit_observed_ms','error']}
        sample=w.get('sample') or {}
        safe['run']=w.get('instance')
        sample_time=re.sub(r'\.(\d+)(?=[+-])', lambda m: '.'+m.group(1)[:6].ljust(6,'0'), sample.get('time','').replace('Z','+00:00'))
        safe['sample_ms']=int(datetime.fromisoformat(sample_time).timestamp()*1000) if sample_time else None
        rx,tx=exact_counter(sample.get('rx_total')),exact_counter(sample.get('tx_total'))
        safe['network_bytes']=rx+tx if isinstance(rx,int) and isinstance(tx,int) else None
        safe['received_age_ms']=hg['time_ms']-safe['sample_ms'] if safe['sample_ms'] is not None else None
        hg_workers.append(safe)
        if safe['network_bytes'] is not None and w.get('instance'):
            hg_samples.append({'run':w['group']+'/'+w['instance'],'rx_moved_bytes':rx,'tx_moved_bytes':tx})
    hg_network=network.setdefault('hg',{'rx':0,'tx':0,'last':{}})
    hg_resets=accumulate(hg_network,hg_samples)
    hg_complete=len(hg_workers)==10 and len(hg_samples)==10 and not hg_resets
    hg_complete=hg_complete and all(isinstance(w['received_age_ms'],(int,float)) and 0<=w['received_age_ms']<=120000 for w in hg_workers)
    hg_complete=hg_complete and isinstance(hg.get('time_ms'),(int,float)) and now-hg['time_ms']<120000
    result = {'recorded_at': stamp(now), 'time_ms': now, 'experiment_id': current['id'], 'phase': current.get('phase'),
              'ps': {'running': view.get('running_nodes'), 'reporting': len(fresh),
                     'desired': 10, 'accepted': raw.get('accepted_nodes'),
                     'monitor_connections': len(raw.get('connected_machines', [])),
                     'provider_bytes': provider['bytes'] if provider else None,
                     'provider_observed_ms': provider['time_ms'] if provider else None,
                     'network_rx_bytes': network['rx'] if network['last'] else None,
                     'network_tx_bytes': network['tx'] if network['last'] else None,
                     'network_total_bytes': network['rx']+network['tx'] if network['last'] else None, 'network_complete': bool(complete),
                     'network_observed_ms': census_ms if plain and network['last'] else now if raw and not plain else None, 'counter_resets': resets,
                     'status_observed_ms':census_ms if plain else now if raw else None,
                     'group_started_at':census.get('group_state',{}).get('start_time') if plain else None,
                     'workers': workers},
              'hg': {'running': hg.get('running'), 'connected': hg.get('connected'), 'desired': 10,
                     'provider_gathering_credits': hg.get('provider_gathering_credits'),
                     'provider_observed_ms': hg.get('provider_observed_ms'),
                     'status_observed_ms': hg.get('time_ms'),
                     'network_rx_bytes':hg_network['rx'],'network_tx_bytes':hg_network['tx'],
                     'network_total_bytes':hg_network['rx']+hg_network['tx'],
                     'network_complete':bool(hg_complete),'network_observed_ms':hg.get('time_ms'),
                     'workers': hg_workers}}
    result['events']=inventory_changes(network,result)
    return result


def start_new(phase):
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    old = read(DATA/'current.json')
    now = int(time.time()*1000)
    ident = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    archive = DATA/'archives'/(old.get('id') or 'pre-fleet-'+ident)
    archive.mkdir(parents=True, exist_ok=True, mode=0o700)
    if old:
        for filename in ['current.json','observations.jsonl','network-state.json','latest.json','events.jsonl']:
            source=DATA/filename
            if source.exists():
                shutil.copy2(source, archive/filename)
    else:
        # Preserve the exact earlier credited ledger. Existing raw network log remains append-only.
        if (PS_DATA/'provider-observations.jsonl').exists():
            shutil.copy2(PS_DATA/'provider-observations.jsonl', archive/'provider-observations.jsonl')
        atomic(archive/'legacy-sources.json', {'archived_at':stamp(now), 'network_log':str(PS_DATA/'network/samples.jsonl'),
               'network_size_bytes':(PS_DATA/'network/samples.jsonl').stat().st_size if (PS_DATA/'network/samples.jsonl').exists() else None})
    provider = last_provider()
    hg_provider = read(HG_DATA/'provider-latest.json')
    value = {'id':ident, 'started_at':stamp(now), 'started_ms':now, 'status':'preparing' if phase=='repair' else 'measuring',
             'phase':phase, 'ps':{'organization':'hyperlane','group':'ps1','desired':10,
               'baseline_provider_bytes':provider['bytes'] if provider else None,
               'baseline_provider_observed_ms':provider['time_ms'] if provider else None,
               'estimated_fleet_cost_usd_per_hour':0.05,'cost_basis':'Previously quoted estimate; invoice unverified'},
             'hg':{'organization':'deathadder','desired':10,'version':'0.6.6',
                   'baseline_provider_gathering_credits':hg_provider.get('gathering_credits'),
                   'baseline_provider_observed_ms':hg_provider.get('observed_ms'),
                   'baseline_started_ms':hg_provider.get('observed_ms'),
                   'phase':phase},
             'interventions':[], 'archive_path':str(archive),
             'measurement_note':'Network totals are observed per-run increments. Provider totals are account-level. Missing samples are not zero traffic.'}
    (DATA/'observations.jsonl').write_text('')
    (DATA/'events.jsonl').write_text('')
    atomic(DATA/'network-state.json', {'experiment_id':ident,'rx':0,'tx':0,'last':{}})
    atomic(DATA/'current.json', value)
    return value


def run(once=False):
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock=(DATA/'recorder.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    stopping = False
    def stop(_sig,_frame):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    while not stopping:
        current=read(DATA/'current.json')
        if not current:
            raise RuntimeError('Start a test before starting recorder')
        network=read(DATA/'network-state.json')
        if network.get('experiment_id')!=current['id']:
            network={'experiment_id':current['id'],'rx':0,'tx':0,'last':{}}
        record=observation(current,network)
        atomic(DATA/'network-state.json',network)
        with (DATA/'observations.jsonl').open('a') as out:
            out.write(json.dumps(record,separators=(',',':'))+'\n');out.flush()
        if record.get('events'):
            with (DATA/'events.jsonl').open('a') as out:
                for event in record['events']:out.write(json.dumps(event)+'\n')
        atomic(DATA/'latest.json',record)
        if once:
            print(json.dumps({'at':record['recorded_at'],'ps_running':record['ps']['running'],'ps_reporting':record['ps']['reporting'],
                              'hg_running':record['hg']['running'],'hg_connected':record['hg']['connected']}));return
        for _ in range(10):
            if stopping:break
            time.sleep(1)


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start-new','run','once','mark'])
    parser.add_argument('--phase',default='repair')
    parser.add_argument('--reason',default='')
    args=parser.parse_args()
    if args.action=='start-new':
        # Prevent archive/reset racing an active writer. Stop the launchd job first.
        DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
        lock=(DATA/'recorder.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        print(json.dumps(start_new(args.phase),indent=2))
    elif args.action=='mark':
        current=read(DATA/'current.json');current['phase']=args.phase
        current['interventions'].append({'time_ms':int(time.time()*1000),'reason':args.reason,'phase':args.phase,
                                         'service':'fleet','action':args.phase})
        atomic(DATA/'current.json',current)
    else:run(args.action=='once')


if __name__=='__main__':
    main()
~~~~~~

### scripts/hg-fleet-control.py

<!-- rebuild-file: scripts/hg-fleet-control.py sha256=636784169bc0a3fd77eecba964f5c474b697bb4ac9f767d9db5fa510b820bcf0 -->
~~~~~~python
#!/usr/bin/env python3
"""Operate a bounded ten-worker Honeygain control using existing registrations."""
import argparse
import fcntl
from datetime import datetime, timedelta, timezone
import getpass
import ipaddress
import json
import os
import re
import math
import sys
import time
from pathlib import Path
import subprocess
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get('HG_FLEET_DIR', str(ROOT / '.runtime/hg-fleet')))
IMAGE = 'docker.io/honeygain/honeygain@sha256:5cd8c361517d0cbae4aa2c75e13239e45f9193ab8e205d57fa29f2e695ea3ec1'
ORGS = ('deathadder', 'cosmosgeeketh', 'hyperlane')
DEVICES = (
    'salad-us-1', 'worker-us-1',
    'salad-c4385ee4-0693-505d-8bd4-76f0e37054a9',
    'salad-5cd61ffc-5e1a-7f55-86a6-ebf67cf06478',
    'salad-b8ababd8-ac4b-d45c-b6a0-b499236dee05',
    'salad-45ef0f8f-0a89-6a5d-9f16-9b606250128e',
    'salad-eeec7129-d81e-d851-8a2e-2a94747b15d2',
    'salad-62d87783-409d-825e-9125-d5166b9038e0',
    'salad-d645de46-f7cc-1859-98a4-cfe7f88bc346',
    'salad-a1d8dea8-73bc-5356-8980-b652388c1659',
)
GROUPS = ('hg1',) + tuple('hg-solo-%02d' % n for n in range(2, 11))


def recovery_command():
    script = r'''set -u
child=""; state=starting; error=none; reason=""; deadline=120; next_sample=0
stop_client() { if [ -n "$child" ]; then kill "$child" 2>/dev/null || true; sleep 1; kill -KILL "$child" 2>/dev/null || true; wait "$child" 2>/dev/null || true; child=""; fi; }
trap 'stop_client; exit 0' TERM INT
start_client() {
  exec 3< <(exec /app/honeygain -tou-accept -email "$HONEYGAIN_EMAIL" -pass "$HONEYGAIN_PASSWORD" -device "$HONEYGAIN_DEVICE_NAME" 2>&1)
  child=$!
}
printf 'HG_SELF_START controller=imds time=%s\n' "$(date -u +%FT%TZ)"
start_client
while :; do
  if IFS= read -r -t 1 line <&3; then
    printf '%s\n' "$line"
    case "${line,,}" in
      *overused*) state=network_overused; error=network_overused; reason=network_overused; break ;;
      *unusable*) state=network_unusable; error=network_unusable; reason=network_unusable; break ;;
      *'connected and running'*) state=connected; error=none ;;
      *disconnected*) if [ "$state" != disconnected ]; then deadline=$((SECONDS+120)); fi; state=disconnected; error=disconnected ;;
      *'already active'*) state=waiting; error=device_already_active ;;
      *'error processing'*) state=authorization_error; error=authorization_error ;;
    esac
  elif ! kill -0 "$child" 2>/dev/null; then
    wait "$child"; code=$?; child=""
    printf 'HG_STOCK_EXIT status=%s time=%s\n' "$code" "$(date -u +%FT%TZ)"
    if [ "$error" = device_already_active ] && (( SECONDS < deadline )); then sleep 15; start_client; else reason=client_exited; break; fi
  fi
  if [ "$state" != connected ] && (( SECONDS >= deadline )); then reason=connection_timeout; break; fi
  if (( SECONDS >= next_sample )); then
    while read -r iface rx rp re rd rf rfr rc rm tx rest; do
      if [ "$iface" = 'eth0:' ]; then printf '{"kind":"hg_native_sample","time":"%s","version":"0.6.6","rx_total":%s,"tx_total":%s,"state":"%s","error":"%s"}\n' "$(date -u +%FT%TZ)" "$rx" "$tx" "$state" "$error"; fi
    done </proc/net/dev
    next_sample=$((SECONDS+10))
  fi
done
stop_client
printf 'HG_SELF_REALLOCATE reason=%s time=%s\n' "$reason" "$(date -u +%FT%TZ)"
for attempt in 1 2 3; do
  if timeout 10 /bin/bash -c '
    body="{\"reason\":\"Honeygain $1\"}"
    exec 4<>/dev/tcp/169.254.169.254/80 || exit 1
    printf "POST /v1/reallocate HTTP/1.1\r\nHost: 169.254.169.254\r\nMetadata: true\r\nContent-Type: application/json\r\nContent-Length: %s\r\nConnection: close\r\n\r\n%s" "${#body}" "$body" >&4
    IFS= read -r response <&4 || exit 1
    printf "HG_SELF_IMDS_RESPONSE %s\n" "$response"
    [[ "$response" =~ ^HTTP/1\.[01][[:space:]]+(200|204)[[:space:]] ]]
  ' hg-imds "$reason"; then
    printf 'HG_SELF_IMDS_ACCEPTED time=%s\n' "$(date -u +%FT%TZ)"
    exit 75
  fi
  printf 'HG_SELF_IMDS_FAILED attempt=%s time=%s\n' "$attempt" "$(date -u +%FT%TZ)"
  sleep 15
done
exit 75'''
    return ['/bin/bash', '-c', 'printf "%s\\n" "$@" > /tmp/hg-stock-run.sh; exec /bin/bash /tmp/hg-stock-run.sh', 'hg-stock', *script.splitlines()]


def now():
    return datetime.now(timezone.utc).isoformat()


class Fleet:
    def __init__(self):
        RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
        helper = os.environ.get('HG_KEYCHAIN_HELPER', str(ROOT / '.runtime/keychain-store'))
        self.key = subprocess.check_output([helper, '--read',
            '--service', 'salad-bandwidth-api', '--account', getpass.getuser()], text=True).strip()

    def api(self, org, path='', method='GET', body=None):
        url = 'https://api.salad.com/api/public/organizations/' + org + path
        media = 'application/merge-patch+json' if method == 'PATCH' else 'application/json'
        config = 'header = ' + json.dumps('Salad-Api-Key: ' + self.key) + '\n'
        config += 'header = ' + json.dumps('Content-Type: ' + media) + '\n'
        if body is not None:
            config += 'data-binary = ' + json.dumps(json.dumps(body)) + '\n'
        response = subprocess.run(['curl', '--silent', '--show-error', '--max-time', '35',
            '--config', '-', '--request', method, '--write-out', '\n%{http_code}', url],
            input=config, capture_output=True, text=True, timeout=40)
        if response.returncode:
            raise RuntimeError('Salad transport request failed')
        raw, code = response.stdout.rsplit('\n', 1)
        if not 200 <= int(code) < 300:
            raise RuntimeError('%s %s%s returned HTTP %s' % (method, org, path, code))
        return json.loads(raw) if raw.strip() else {}

    def groups(self, org):
        return self.api(org, '/projects/default/containers').get('items', [])

    @staticmethod
    def device(g):
        c = g.get('container', {})
        device = c.get('environment_variables', {}).get('HONEYGAIN_DEVICE_NAME')
        if device:
            return device
        command = c.get('command') or []
        if '-device' in command and command.index('-device') + 1 < len(command):
            return command[command.index('-device') + 1]
        matches = re.findall(r'-device[ =]+[\"\x27]?([A-Za-z0-9-]+)', ' '.join(command))
        if len(matches) == 1:
            return matches[0]
        return None

    @staticmethod
    def safe(g):
        return {'group': g['name'], 'id': g['id'], 'replicas': g.get('replicas'),
                'image': g.get('container', {}).get('image'), 'device': Fleet.device(g),
                'state': g.get('current_state', {}), 'version': g.get('version')}

    def inventory(self):
        result = []
        for org in ORGS:
            try:
                for g in self.groups(org):
                    result.append({'organization': org, **self.safe(g)})
            except RuntimeError as e:
                result.append({'organization': org, 'error': str(e)})
        return result

    @staticmethod
    def write(name, record):
        path = RUNTIME / name
        temp = path.with_suffix(path.suffix + '.%s.tmp' % os.getpid())
        temp.write_text(json.dumps(record, indent=2) + '\n')
        temp.chmod(0o600)
        temp.replace(path)

    def stop_redundant(self):
        result = []
        for org in ORGS:
            for g in self.groups(org):
                if not self.device(g):
                    continue
                if org == 'deathadder' and g['name'] in GROUPS:
                    continue
                if g.get('current_state', {}).get('status') != 'stopped':
                    self.api(org, '/projects/default/containers/' + g['name'] + '/stop', 'POST')
                    result.append({'organization': org, 'group': g['name'], 'device': self.device(g),
                                   'stop_requested_at': now()})
        self.write('redundant-stops.json', result)
        return result

    def deploy(self):
        # Read every org first; never add workers while another HG group is active.
        for org in ORGS:
            for g in self.groups(org):
                if not self.device(g):
                    continue
                intended = org == 'deathadder' and g['name'] in GROUPS
                if not intended:
                    instances = self.api(org, '/projects/default/containers/' + g['name'] + '/instances')
                    if instances.get('instances'):
                        raise RuntimeError('Redundant HG instances must finish stopping: ' + org + '/' + g['name'])
        original = self.api('deathadder', '/projects/default/containers/hg1')
        if original['container']['image'] != IMAGE or self.device(original) != DEVICES[0] or original['replicas'] != 1:
            raise RuntimeError('Existing solo control changed; inspect before deployment')
        env = original['container']['environment_variables']
        current = {g['name']: g for g in self.groups('deathadder')}
        assert len(DEVICES) == len(set(DEVICES)) == len(GROUPS) == 10
        receipt = []
        for index, (group, device) in enumerate(zip(GROUPS, DEVICES), 1):
            if group in current:
                g = current[group]
                if self.device(g) != device or g['container']['image'] != IMAGE or g['replicas'] != 1:
                    raise RuntimeError('Existing group does not match approved control: ' + group)
            else:
                payload = {'name': group, 'display_name': 'HG Solo %02d' % index, 'replicas': 1,
                    'autostart_policy': True, 'restart_policy': 'always', 'country_codes': ['us'],
                    'container': {'image': IMAGE, 'resources': {'cpu': 1, 'memory': 1024},
                        'priority': 'low', 'command': original['container']['command'],
                        'environment_variables': {'HONEYGAIN_EMAIL': env['HONEYGAIN_EMAIL'],
                            'HONEYGAIN_PASSWORD': env['HONEYGAIN_PASSWORD'], 'HONEYGAIN_DEVICE_NAME': device}}}
                g = self.api('deathadder', '/projects/default/containers', 'POST', payload)
            receipt.append({'worker': index, 'organization': 'deathadder', **self.safe(g), 'checked_at': now()})
            self.write('deployment.json', receipt)
            print(json.dumps({'worker': index, 'group': group, 'device': device,
                              'state': g.get('current_state', {}).get('status')}), flush=True)
        return receipt

    def start_ready(self):
        result = []
        for group in GROUPS:
            g = self.api('deathadder', '/projects/default/containers/' + group)
            if g.get('current_state', {}).get('status') == 'stopped':
                try:
                    self.api('deathadder', '/projects/default/containers/' + group + '/start', 'POST')
                    result.append({'group': group, 'start_requested_at': now()})
                except RuntimeError as e:
                    result.append({'group': group, 'error': str(e)})
        return result

    def enable_recovery(self, groups=GROUPS):
        command = recovery_command()
        result = []
        for group in groups:
            if group not in GROUPS:
                raise ValueError('Unknown Honeygain group')
            path = '/projects/default/containers/' + group
            current = self.api('deathadder', path)
            if current['container']['image'] != IMAGE or current['replicas'] != 1 or self.device(current) != DEVICES[GROUPS.index(group)]:
                raise RuntimeError('Honeygain registration or deployment changed: ' + group)
            if current['container']['command'] != command:
                current = self.api('deathadder', path, 'PATCH', {'container': {'command': command}})
            result.append({'group': group, 'version': current.get('version'), 'recovery': 'IMDS inside container'})
        return result


def record_provider(record):
    """Persist an actual fresh visible-UI reading; never read authentication state."""
    observed_ms = record.get('observed_ms')
    if not isinstance(observed_ms, int) or not -60000 <= int(time.time()*1000) - observed_ms <= 300000:
        raise ValueError('Provider reading needs its actual observation time within five minutes')
    source = record.get('source', 'Fresh Honeygain dashboard visible UI')
    if source not in ('Fresh Honeygain dashboard visible UI', 'Honeygain official dashboard API'):
        raise ValueError('Unrecognized provider reading source')
    def amount(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('Credits must be finite nonnegative provider observations')
        return value
    devices = record.get('devices', [])
    if len(devices) != 10 or {x.get('device') for x in devices} != set(DEVICES):
        raise ValueError('Reading must contain exactly the ten existing fleet registrations once each')
    clean_devices = []
    for device in DEVICES:
        item = next(x for x in devices if x['device'] == device)
        if not isinstance(item.get('provider_active'), bool):
            raise ValueError('Provider active status must be observed, not inferred from historical device count')
        ip = item.get('ip')
        if ip:
            parsed = ipaddress.ip_address(ip)
            ip = str(parsed.ipv4_mapped or parsed) if isinstance(parsed, ipaddress.IPv6Address) else str(parsed)
        clean_devices.append({'device': device, 'credits': amount(item.get('credits')),
                              'provider_active': item['provider_active'], 'ip': ip})
    clean = {'checked_at': now(), 'observed_ms': observed_ms,
             'gathering_credits': amount(record.get('gathering_credits')),
             'account_balance_credits': amount(record.get('account_balance_credits')),
             'source': source, 'devices': clean_devices}
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (RUNTIME / 'provider-writer.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        latest = RUNTIME / 'provider-latest.json'
        if latest.exists() and json.loads(latest.read_text()).get('observed_ms', 0) >= observed_ms:
            raise ValueError('Reading does not advance the actual provider observation timestamp')
        Fleet.write('provider-latest.json', clean)
        with (RUNTIME / 'provider-readings.jsonl').open('a') as output:
            output.write(json.dumps(clean) + '\n')
    return {'observed_ms': observed_ms, 'gathering_credits': clean['gathering_credits'],
            'device_count': len(clean_devices), 'provider_active': sum(x['provider_active'] for x in clean_devices)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['inventory', 'stop-redundant', 'deploy', 'start-ready', 'record-provider', 'enable-recovery'])
    args = p.parse_args()
    if args.action == 'record-provider':
        print(json.dumps(record_provider(json.load(sys.stdin))))
        return
    fleet = Fleet()
    action = getattr(fleet, args.action.replace('-', '_'))
    result = action()
    if args.action != 'deploy':
        print(json.dumps(result, indent=2))
    fleet.write(args.action + '-latest.json', {'checked_at': now(), 'result': result})


if __name__ == '__main__':
    main()
~~~~~~

### scripts/hg-fleet-observer.py

<!-- rebuild-file: scripts/hg-fleet-observer.py sha256=419bc42de81169a8f1893411c600f3097ac24498f77083abb7033ab4ecbb2c01 -->
~~~~~~python
#!/usr/bin/env python3
"""Read Salad native lifecycle and network counters into a per-worker ledger."""
import argparse
import fcntl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import re
from pathlib import Path
import time

spec = importlib.util.spec_from_file_location('hg_fleet_control', Path(__file__).with_name('hg-fleet-control.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


def milliseconds(value):
    value = value.replace('Z', '+00:00')
    value = re.sub(r'\.(\d+)(?=[+-])', lambda m: '.' + m.group(1)[:6].ljust(6, '0'), value)
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def classify(text):
    low = text.lower()
    if 'hg_self_reallocate' in low or 'hg_self_imds_accepted' in low:
        return 'reallocating'
    if 'user_device_limit_exceeded' in low or 'device limit' in low:
        return 'device_limit'
    if 'already active' in low:
        return 'device_already_active'
    if 'overused' in low:
        return 'network_overused'
    if 'unusable' in low:
        return 'network_unusable'
    if 'connected and running' in low:
        return 'connected'
    if 'disconnected' in low:
        return 'disconnected'
    if 'authorisation successful' in low:
        return 'authenticated'
    if 'service is starting' in low:
        return 'starting'
    if 'error processing' in low:
        return 'authorization_error'
    if 'hg_stock_exit' in low:
        return 'exited'
    return None


def read_provider():
    path = control.RUNTIME / 'provider-latest.json'
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def observe_worker(fleet, index, group, device, provider):
    worker = {'worker': index, 'organization': 'deathadder', 'group': group, 'device': device,
              'machine': None, 'ip': None, 'state': 'unverified', 'client_status': 'unverified',
              'credits': None, 'credit_observed_ms': None, 'error': None}
    device_reading = next((x for x in provider.get('devices', []) if x.get('device') == device), {})
    worker.update(credits=device_reading.get('credits'), ip=device_reading.get('ip'),
                  credit_observed_ms=provider.get('observed_ms'),
                  provider_active=device_reading.get('provider_active'))
    try:
        path = '/projects/default/containers/' + group
        g = fleet.api('deathadder', path)
        if fleet.device(g) != device or g.get('replicas') != 1 or g['container']['image'] != control.IMAGE:
            raise RuntimeError('Configuration differs from the approved independent stock control')
        instances = fleet.api('deathadder', path + '/instances').get('instances', [])
        worker.update(state=g.get('current_state', {}).get('status'), image=g['container']['image'],
                      replica_count=len(instances), running_instances=sum(x.get('state') == 'running' for x in instances))
        if len(instances) > 1:
            raise RuntimeError('Multiple instances share one registration during rollout')
        if not instances:
            worker['client_status'] = 'not_started'
            return worker
        instance = instances[0]
        worker.update(instance=instance['id'], machine=instance.get('machine_id'),
                      instance_state=instance.get('state'), ready=instance.get('ready'))
        end = datetime.now(timezone.utc)
        native_recovery = any('HG_SELF_START' in part for part in g['container'].get('command', []))
        identity = 'machine_id' if native_recovery else 'instance_id'
        base = ('resource.type = "container" and resource.labels.project_name = "default" and '
                'resource.labels.container_group_name = "' + group + '" and '
                'resource.labels.' + identity + ' = "' + instance.get(identity, instance['id']) + '"')
        lifecycle_query = base + ' and (text_log contains "Honeygain" or text_log contains "Authorisation" or text_log contains "HG_STOCK" or text_log contains "HG_SELF" or text_log contains "device" or text_log contains "overused" or text_log contains "Error")'
        def logs(query, minutes, size):
            calls = 0
            def fetch_window(start, stop):
                nonlocal calls
                calls += 1
                if calls > 63:
                    raise RuntimeError('Salad log window exceeds bounded pagination budget')
                items = fleet.api('deathadder', '/log-entries', 'POST', {'query': query,
                    'start_time': start.isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
                    'end_time': stop.isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
                    'page_size': size, 'sort_order': 'asc'}).get('items', [])
                if len(items) < size:
                    return items
                # A full response can contain an older capped page, regardless of
                # requested sort order. Split time until every window is complete.
                if (stop-start) <= timedelta(milliseconds=1):
                    raise RuntimeError('Too many Salad logs share one timestamp')
                midpoint = start + (stop-start)/2
                return fetch_window(start, midpoint) + fetch_window(midpoint, stop)
            start = end-timedelta(minutes=minutes)
            if native_recovery and instance.get('update_time'):
                start = max(start, datetime.fromtimestamp(milliseconds(instance['update_time'])/1000, timezone.utc))
            items = fetch_window(start, end) if start < end else []
            unique = {json.dumps(item, sort_keys=True): item for item in items}
            return list(unique.values())
        events = logs(lifecycle_query, 3 if native_recovery else 120, 100)
        safe_events = []
        for entry in events:
            text = entry.get('text_log', '')
            status = classify(text)
            if status:
                safe_events.append({'time': entry.get('time'), 'status': status})
        safe_events.sort(key=lambda x: x['time'] or '', reverse=True)
        if safe_events:
            worker.update(client_status=safe_events[0]['status'], last_event_at=safe_events[0]['time'])
            if safe_events[0]['status'] in ('device_limit', 'device_already_active', 'network_overused', 'network_unusable', 'authorization_error'):
                worker['error'] = safe_events[0]['status']
        worker['lifecycle'] = safe_events[:20]
        samples = logs(base + ' and json_log.kind = "hg_native_sample"', 3, 30)
        readings = [{'time': x.get('time'), **{k: x.get('json_log', {}).get(k) for k in ('rx_total', 'tx_total', 'state', 'error')}} for x in samples]
        readings.sort(key=lambda x: x['time'] or '')
        if readings:
            worker['sample'] = readings[-1]
            worker['sample_age_seconds'] = (int(time.time()*1000) - milliseconds(readings[-1]['time'])) / 1000
            if len(readings) >= 2:
                seconds = (milliseconds(readings[-1]['time']) - milliseconds(readings[0]['time'])) / 1000
                worker['network_window_seconds'] = seconds
                worker['rx_bytes_window'] = max(0, readings[-1]['rx_total'] - readings[0]['rx_total'])
                worker['tx_bytes_window'] = max(0, readings[-1]['tx_total'] - readings[0]['tx_total'])
        worker['connection_evidence_fresh'] = worker.get('sample_age_seconds', 9999) < 120 and instance.get('state') == 'running'
        if worker['client_status'] == 'connected' and not worker['connection_evidence_fresh']:
            worker['client_status'] = 'connected_last_observed_telemetry_stale'
        if readings and worker['connection_evidence_fresh'] and readings[-1].get('state') in ('connected', 'starting', 'waiting', 'disconnected', 'authorization_error'):
            if not safe_events or milliseconds(readings[-1]['time']) >= milliseconds(safe_events[0]['time']):
                worker['client_status'] = readings[-1]['state']
                worker['error'] = readings[-1].get('error') if readings[-1].get('error') not in (None, 'none') else None
        if not safe_events and worker['client_status'] == 'unverified':
            previous = control.RUNTIME / ('worker-%02d.json' % index)
            if previous.exists():
                old = json.loads(previous.read_text())
                previous_age = int(time.time()*1000) - milliseconds(old.get('checked_at', '1970-01-01T00:00:00Z'))
                if old.get('instance') == instance['id'] and worker.get('connection_evidence_fresh') and previous_age < 600000:
                    worker['client_status'] = old.get('client_status', 'unverified')
                    worker['last_event_at'] = old.get('last_event_at')
    except Exception as error:
        worker['error'] = type(error).__name__ + ': ' + str(error)
        if worker['client_status'] == 'connected':
            worker['client_status'] = 'connected_last_observed_telemetry_unverified'
    return worker


def observe(fleet):
    provider = read_provider()
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(observe_worker, fleet, index, group, device, provider)
                   for index, (group, device) in enumerate(zip(control.GROUPS, control.DEVICES), 1)]
        workers = [x.result() for x in futures]
    stamp = control.now()
    record = {'checked_at': stamp, 'time_ms': int(time.time()*1000), 'desired': 10,
              'running': sum(x.get('running_instances', 0) for x in workers),
              'connected': sum(x['client_status'] == 'connected' for x in workers),
              'provider_gathering_credits': provider.get('gathering_credits'),
              'provider_observed_ms': provider.get('observed_ms'), 'workers': workers,
              'connection_definition': 'Current native connected lifecycle without later exit/disconnect, live Salad instance and telemetry sample under 120s old. Provider credits remain separate.',
              'network_definition': 'Container interface bytes include protocol overhead and are not provider billed traffic.'}
    for worker in workers:
        worker['checked_at'] = stamp
        fleet.write('worker-%02d.json' % worker['worker'], worker)
    fleet.write('status.json', record)
    with (control.RUNTIME / 'observations.jsonl').open('a') as output:
        output.write(json.dumps(record) + '\n')
    print(json.dumps({k: record[k] for k in ('checked_at', 'desired', 'running', 'connected')}), flush=True)
    print(json.dumps([{'group': x['group'], 'state': x['state'], 'client_status': x['client_status'], 'error': x['error']} for x in workers]), flush=True)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--once', action='store_true')
    p.add_argument('--interval', type=int, default=60)
    args = p.parse_args()
    fleet = control.Fleet()
    lock = (control.RUNTIME / 'observer.lock').open('a')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('A Honeygain fleet observer is already running')
    while True:
        observe(fleet)
        if args.once:
            return
        time.sleep(max(30, args.interval))


if __name__ == '__main__':
    main()
~~~~~~

### scripts/hg-provider-observer.py

<!-- rebuild-file: scripts/hg-provider-observer.py sha256=df6011522bffec291015a596646590f2866a2955cdd49488ad9337e8ba6e863e -->
~~~~~~python
#!/usr/bin/env python3
"""Record Honeygain provider credits through its official dashboard API."""
import argparse
from decimal import Decimal
import fcntl
import importlib.util
import json
from pathlib import Path
import subprocess
import time

spec = importlib.util.spec_from_file_location('hg_fleet_control', Path(__file__).with_name('hg-fleet-control.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class HoneygainProvider:
    def __init__(self):
        fleet = control.Fleet()
        source = fleet.api('deathadder', '/projects/default/containers/hg1')['container']['environment_variables']
        self.credentials = {'email': source['HONEYGAIN_EMAIL'], 'password': source['HONEYGAIN_PASSWORD']}
        self.token = None

    def request(self, path, method='GET', payload=None, authenticate=True):
        if path not in ('/api/v1/users/tokens', '/api/v2/devices', '/api/v1/earnings/stats', '/api/v1/users/balances'):
            raise RuntimeError('Unrecognized Honeygain endpoint')
        config = 'header = ' + json.dumps('Content-Type: application/json') + '\n'
        config += 'header = ' + json.dumps('Accept: application/json') + '\n'
        if authenticate:
            if not self.token:
                self.login()
            config += 'header = ' + json.dumps('Authorization: Bearer ' + self.token) + '\n'
        if payload is not None:
            config += 'data-binary = ' + json.dumps(json.dumps(payload)) + '\n'
        result = subprocess.run(['curl', '--silent', '--show-error', '--max-time', '20', '--config', '-',
            '--request', method, '--write-out', '\n%{http_code}', 'https://dashboard.honeygain.com' + path],
            input=config, capture_output=True, text=True, timeout=25)
        if result.returncode:
            raise RuntimeError('Honeygain request transport failed')
        raw, status = result.stdout.rsplit('\n', 1)
        if int(status) == 401 and authenticate:
            self.token = None
        if not 200 <= int(status) < 300:
            raise RuntimeError('Honeygain ' + path + ' returned HTTP ' + status)
        return json.loads(raw)

    def login(self):
        data = self.request('/api/v1/users/tokens', 'POST', self.credentials, authenticate=False)
        token = data.get('data', {}).get('access_token')
        if not isinstance(token, str) or not token:
            raise RuntimeError('Honeygain login returned no usable session')
        self.token = token

    def fetch(self):
        return (self.request('/api/v2/devices'), self.request('/api/v1/earnings/stats'),
                self.request('/api/v1/users/balances'))


def build_reading(devices, stats, balances, observed_ms):
    rows = devices['data']
    by_name = {row.get('model'): row for row in rows if row.get('model') in control.DEVICES}
    if len(by_name) != 10 or sum(row.get('model') in control.DEVICES for row in rows) != 10:
        raise RuntimeError('Provider did not return exactly the ten registered fleet devices')
    gathering = sum((Decimal(str(day['gathering']['credits'])) for day in stats.values()), Decimal(0))
    return {'observed_ms': observed_ms, 'gathering_credits': float(gathering),
            'account_balance_credits': balances['data']['payout']['credits'],
            'source': 'Honeygain official dashboard API',
            'devices': [{'device': name, 'credits': by_name[name]['stats']['total_credits'],
                         'ip': by_name[name].get('ip'), 'provider_active': by_name[name]['status'] == 'active'}
                        for name in control.DEVICES]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect-schema', action='store_true')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval', type=int, default=60)
    args = parser.parse_args()
    if args.inspect_schema:
        devices, stats, balances = HoneygainProvider().fetch()
        rows = devices.get('data', [])
        day = stats[sorted(stats)[-1]]
        print(json.dumps({'device_count': len(rows), 'device_title': rows[0].get('title') if rows else None,
            'device_identity_fields': [{k: row.get(k) for k in ('manufacturer', 'model', 'title')} for row in rows],
            'device_status': rows[0].get('status') if rows else None,
            'device_stats': rows[0].get('stats') if rows else None,
            'day_stats': day, 'balances': balances.get('data')}, indent=2))
        return
    control.RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = (control.RUNTIME / 'provider-observer.lock').open('a')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('A Honeygain provider observer is already running')
    provider = None
    failures = 0
    while True:
        started = time.monotonic()
        try:
            if provider is None:
                provider = HoneygainProvider()
            devices, stats, balances = provider.fetch()
            observed_ms = int(time.time()*1000)
            result = control.record_provider(build_reading(devices, stats, balances, observed_ms))
            # Retain only the provider's traffic/credit measurements, never auth responses.
            control.Fleet.write('provider-api-traffic-latest.json', {
                'observed_ms': observed_ms, 'source': 'Honeygain official dashboard API',
                'days': {date: {'gathering_credits': day['gathering']['credits'],
                                'gathering_traffic_bytes': day['gathering']['traffic']}
                         for date, day in stats.items()},
                'devices': [{'device': row['model'], 'total_traffic_bytes': row['stats']['total_traffic'],
                             'total_credits': row['stats']['total_credits']}
                            for row in devices['data'] if row.get('model') in control.DEVICES]})
            control.Fleet.write('provider-feed-status.json', {'checked_at': control.now(),
                'observed_ms': observed_ms, 'state': 'ok', 'interval_seconds': max(60, args.interval),
                'authentication_storage': 'process memory only'})
            print(json.dumps(result), flush=True)
            failures = 0
        except Exception as error:
            failures += 1
            message = str(error) if isinstance(error, RuntimeError) else type(error).__name__
            control.Fleet.write('provider-feed-status.json', {'checked_at': control.now(),
                'state': 'error', 'error': message, 'consecutive_failures': failures})
            print(json.dumps({'state': 'error', 'error': message}), flush=True)
            if args.once:
                raise SystemExit(1)
        if args.once:
            return
        interval = min(1800, max(60, args.interval) * (2 ** min(failures, 5)))
        time.sleep(max(1, interval - (time.monotonic()-started)))


if __name__ == '__main__':
    main()
~~~~~~

### scripts/initialize-recording.py

<!-- rebuild-file: scripts/initialize-recording.py sha256=4ac3beac391fd2f7e3f52896b62ab2a201a40268161f10e004886832ac984f74 -->
~~~~~~python
#!/usr/bin/env python3
"""Initialize a fresh shared ledger without resetting any existing experiment."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
os.umask(0o077)
data=Path.home()/'.hg1';root=data/'fleet-tests';root.mkdir(parents=True,exist_ok=True)
current=root/'current.json'
if current.exists():raise SystemExit('Existing experiment preserved. Do not reset it to repair a display.')
provider=data/'hg-fleet/provider-latest.json'
hg=json.loads(provider.read_text()) if provider.exists() else {}
now=int(time.time()*1000);started=datetime.fromtimestamp(now/1000,timezone.utc).isoformat();ident=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
record=dict(id=ident,started_at=started,started_ms=now,status='measuring',phase='bandwidth-test',
    ps=dict(organization='hyperlane',project='default',group='ps-test-us',desired=10,baseline_provider_bytes=None),
    hg=dict(organization='deathadder',desired=10,version='0.6.6',baseline_provider_gathering_credits=hg.get('gathering_credits'),
        baseline_provider_observed_ms=hg.get('observed_ms'),baseline_started_ms=hg.get('observed_ms')),interventions=[])
current.write_text(json.dumps(record,indent=2)+'\n')
(root/'network-state.json').write_text(json.dumps(dict(experiment_id=ident,rx=0,tx=0,last={})))
print('Started new recording metadata '+ident+'; historical values were not invented.')
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
