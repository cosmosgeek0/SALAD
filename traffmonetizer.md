# bandwidth reel — TraffMonetizer (TM) recovery guide

This file is a self-contained source backup and operating guide for **ten TraffMonetizer workers in Salad organization `ssh4`**. Keep a second copy outside this Mac. If the local project is deleted, the source appendix can recreate the TM worker, deployment helper, recorder, Keychain helper, and a TM-only monitoring page.

**Reproduction means restoring the same source, launch configuration, measurement formulas, and stated recovery behavior. It does not guarantee the same assigned machines, traffic volume, earnings, or recovery of deleted historical data.**

**Snapshot checked on 7 September 2026.** The live Salad API reported group version **6**, ten running instances, and the exact command override described below. This is a dated configuration record, not a promise that ten devices remain healthy forever.

## 1. What must survive outside this file

This document deliberately contains **no passwords, application token, API key, dashboard session, or payment information**. A new operator needs access to:

- The existing Salad account, organization `ssh4`, project `default`, sufficient credits, and a Salad API key authorized for that organization.
- The existing TraffMonetizer account and its **application token** from the dashboard. This is the token workers use.
- A signed-in TraffMonetizer **dashboard session** for the optional account earnings collector. It is different from the application token. The account APIs returned HTTP 401 when called with the application token.
- macOS with Python 3, `curl`, Xcode Command Line Tools/Swift, and Docker Desktop for the documented complete recovery path. The cloud worker itself is Linux/amd64. The recorder uses only Python's standard library; the credential helper uses macOS Keychain.
- Internet access to Salad, TraffMonetizer and the referenced container registries. If an upstream service or vendor binary disappears, this text cannot recreate that proprietary service or binary.

Losing the database loses local historical measurements. Losing account credentials requires recovering them through their respective services. The program source in this file survives independently of the original repository.

## 2. Exact cloud identity and runtime

| Item | Verified configuration |
|---|---|
| Provider label | `TM` — TraffMonetizer |
| Salad organization / project | `ssh4` / `default` |
| Group resource name | `tm-test-us` |
| Group display name | `TM` |
| Existing group ID | `1a64168c-d295-4b6c-9d4c-928303dfebf2` |
| Replicas | `10` |
| Country filter | `us` |
| Resources per worker | 1 vCPU, 1024 MiB RAM, no GPU |
| Priority | `batch` (Lowest in the portal) |
| Restart policy | `always` |
| Current group version at this snapshot | `6` |
| Autostart flag at this snapshot | `false`; the group was explicitly started and was running |
| Custom startup/liveness/readiness probes | None configured |
| Worker secret environment variable | `TM_TOKEN` |
| Device name | `ssh4-tm-` plus the Salad machine ID |
| Public inbound server/gateway | Not required for TM |

Portal: <https://portal.salad.com/organizations/ssh4/projects/default/containers/tm-test-us>

Current wrapper image:

```text
docker.io/cosmosgeek0/salad-bandwidth-stack@sha256:d75e26d28fbb9352829eb41440a38b59d5f9d3ecb4967cc0414bb3bbc50f1c2c
```

Pinned, unchanged vendor client image:

```text
traffmonetizer/cli_v2@sha256:6dbf8e75cc93e25131e2e701b1d478b3ccbf89212636b08d629621c270f0c966
```

Pinned Python base:

```text
python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
```

**The current command override is essential.** The wrapper image contains an earlier worker. Current Salad configuration starts `/bin/sh -c`, decodes the worker source from command arguments into `/tmp/tm-worker.py`, and executes that file. Merely restoring the image with its default entrypoint restores an older recovery policy.

The decoded live command was compared byte for byte with the source embedded below. Its SHA-256 is:

```text
b83b9c1b3e8709f8dac923696920fcbbe8230658699e5c7e87a8142cd03085f7
```

The deployment command in section 6 reconstructs that override automatically. Each base64 argument is at most 900 characters, matching the existing command layout. Base64 here transports **public source code**, not a secret.

## 3. What runs where, and what recovery actually does

Each Salad replica runs one official TM client and the Python worker. The worker reads the client, samples `eth0` RX/TX once per second, and sends ten-sample batches to stdout with the `TM_V1 ` prefix. It asks the client for `status` and `statistics` every ten seconds and also reads asynchronous connection events.

**The current version-6 worker in this file behaves as follows:**

1. A client process exit requests replacement immediately.
2. A confirmed unavailable connection lasting approximately 30 seconds requests replacement. A healthy connected-and-accepting state resets this timer.
3. No reply to either `status` or `statistics` for 60 seconds requests replacement.
4. Replacement is a POST from inside that replica to `http://169.254.169.254/v1/reallocate`, with `Metadata: true` and a reason. It then exits with code 75. A failed IMDS request is logged; the nonzero exit is a fallback, not proof a new machine was assigned.
5. There is **no local client restart before replacement in this current source**. Earlier chat descriptions of a 120-second accumulated budget and one local retry refer to the older image policy, not this verified command override.
6. Low traffic by itself does **not** request replacement. Brief healthy intervals reset the 30-second unavailable timer; repeated shorter disconnects can therefore avoid that threshold. Do not describe this policy as a guarantee of profitability or recovery from every failure.

The Mac reads cloud logs and account metrics; it does **not** have to be online for the worker to request IMDS reallocation. If the whole Salad host is offline, the worker cannot run: Salad's platform must detect and replace that host. This was observed to take several minutes. No extra cloud controller or custom liveness probe is configured in this snapshot.

## 4. Restore the source from this Markdown file

Use this section on a clean recovery machine. On the original Mac, preserve the current deployment and services; do not start duplicate observers or another server on port 8787.

The following command extracts only the marked source blocks, checks each SHA-256, and refuses to overwrite an existing recovery directory. It does not contact cloud accounts or start containers. Change only `document` if this Markdown file was copied elsewhere.

```bash
python3 - <<'PY_RESTORE'
from pathlib import Path
import hashlib,re

document=Path.home()/"Desktop/salad/traffmonetizer.md"
destination=Path.home()/"Library/Application Support/TraffMonetizer Recovery"
blocks=re.findall(r'<!-- TM_FILE: ([^\n]+) SHA256: ([0-9a-f]{64}) -->\n```[^\n]*\n(.*?)\n```',document.read_text(),re.S)
assert blocks, "No embedded TM source found"
assert not destination.exists(), "Use a new empty directory; existing files were not overwritten"
verified=[]
for relative,digest,body in blocks:
    path=Path(relative)
    assert not path.is_absolute() and ".." not in path.parts
    raw=(body+"\n").encode()
    assert hashlib.sha256(raw).hexdigest()==digest, "Source checksum mismatch: "+relative
    verified.append((path,raw))
assert len({str(p) for p,_ in verified})==len(verified), "Duplicate file paths"
for path,raw in verified:
    target=destination/path
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(raw)
print("Restored",len(verified),"source files to",destination)
PY_RESTORE
cd "$HOME/Library/Application Support/TraffMonetizer Recovery"
```

All later commands run in that recovery directory unless stated otherwise. Keep this directory out of Desktop/Documents for macOS background-service access; an earlier launchd deployment under Desktop failed with `Operation not permitted`.

## 5. Restore credentials safely

Install Xcode Command Line Tools if `xcrun --find swiftc` is unavailable, then compile the included helper:

```bash
mkdir -p .runtime
xcrun swiftc scripts/keychain-store.swift -o .runtime/keychain-store
```

The original Keychain service names are:

| Service | Value |
|---|---|
| `salad-bandwidth-api` | Salad API key |
| `salad-traffmonetizer-token` | TM application token, used by workers |
| `salad-traffmonetizer-session` | TM dashboard Bearer session token, without the `Bearer ` prefix |

The Keychain account is the current macOS username, obtained by `getpass.getuser()`. Existing entries may still work if only project files were lost. Recompiling the helper may cause macOS to request access to existing Keychain entries.

To save/re-enter the credentials, use hidden input; values go to the helper through stdin, not command arguments or source files:

```bash
python3 - <<'PY_KEYS'
import getpass,subprocess
from pathlib import Path
helper=Path.cwd()/".runtime/keychain-store"
for service,label in [
    ("salad-bandwidth-api","Salad API key"),
    ("salad-traffmonetizer-token","TM application token"),
    ("salad-traffmonetizer-session","TM dashboard session, without Bearer prefix"),
]:
    secret=getpass.getpass(label+": ").strip()
    if not secret:
        raise SystemExit("Empty input; this credential was not changed")
    subprocess.run([str(helper),"--service",service,"--account",getpass.getuser()],
                   input=secret,text=True,check=True,capture_output=True)
    print("Saved",service)
    secret=""
PY_KEYS
```

Obtain the application token from <https://app.traffmonetizer.com/dashboard>. For the account-session collector, sign into that same account, open browser Developer Tools → Network, reload the dashboard, select its `get_balance` request and inspect the **request Authorization header**. Copy only the value after `Bearer ` into the hidden prompt. Do not share it or save a browser HAR containing it. The site has also used local storage key `token`, but inspect the actual request if its frontend changes.

The collector uses two read-only account endpoints and refreshes the saved session when the response provides an Authorization header. Sessions can still expire. A provider 401/403 means reauthenticate and replace the **session** entry; it does not by itself mean the cloud workers' application token failed.

## 6. Start a replacement deployment, or reconnect to the surviving one

First check the Salad portal. If `tm-test-us` survived, **reuse it**. Deleting local files does not stop cloud billing or delete containers. Do not create a second ten-worker group.

The script below is for loss of the local TM database/configuration. It refuses to run if a local deployment record or database already exists. It captures a **new** account measurement baseline; it cannot recover an old earnings baseline from memory. The existing cloud group is read and left unchanged. Only when absent does it create the documented group, initially stopped, record the baseline, and start it.

It needs all three credentials from section 5 for complete monitoring. The initial baseline is captured from account APIs, not from an assumed `$0.0268`, `$0`, or a dashboard balance rounded by hand. Do not use the embedded legacy `control.py create` shortcut: its historical hardcoded baseline and image-only launch are not this recovery recipe.

```bash
python3 - <<'PY_DEPLOY'
from pathlib import Path
from datetime import datetime,timezone
import base64,json,os,sys
sys.path.insert(0,"traffmonetizer")
from control import api,keychain,DATA,GROUP_PATH,IMAGE
from observer import provider_request

record=DATA/"deployment.json"
assert not record.exists() and not (DATA/"traffic.sqlite3").exists(), "Existing history: use section 7, do not reset it"
DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
os.umask(0o077)
worker=Path("traffmonetizer/worker.py").read_bytes()
encoded=base64.b64encode(worker).decode()
command=["/bin/sh","-c",'umask 077; printf "%s" "$@" | base64 -d > /tmp/tm-worker.py; exec python3 -u /tmp/tm-worker.py',"policy-start"]
command.extend(encoded[i:i+900] for i in range(0,len(encoded),900))
image=os.environ.get("TM_IMAGE",IMAGE)
items=api("/projects/default/containers").get("items",[])
exists=any(g["name"]=="tm-test-us" for g in items)
group=api(GROUP_PATH) if exists else None
if exists:
    print("Reusing existing group:",group["id"],"version",group["version"],"replicas",group["replicas"])
    if group["replicas"]!=10:
        raise SystemExit("Existing replica count differs. Inspect it in Salad before making an intentional scale change.")
else:
    payload={"name":"tm-test-us","display_name":"TM","replicas":10,
        "autostart_policy":False,"restart_policy":"always","country_codes":["us"],
        "container":{"image":image,"command":command,"priority":"batch",
            "resources":{"cpu":1,"memory":1024},
            "environment_variables":{"TM_TOKEN":keychain("salad-traffmonetizer-token")}}}
    try:
        group=api("/projects/default/containers","POST",payload)
    except RuntimeError:
        group=api(GROUP_PATH)
        c=group.get("container",{})
        assert group.get("replicas")==10 and c.get("image")==image and c.get("command")==command
        assert c.get("environment_variables",{}).get("TM_TOKEN")==payload["container"]["environment_variables"]["TM_TOKEN"]
        print("Create response was uncertain; matching group found, no duplicate created")

# Account snapshots and wall-clock boundary are only seconds apart; for an
# already-running group, the baseline is a new observation, not old history.
began=datetime.now(timezone.utc)
balance=provider_request("/api/app_user/get_balance")["data"]
days=provider_request("/api/dashboard/get_graph_stat?period=month")
finished=datetime.now(timezone.utc)
assert began.date()==finished.date(), "UTC date changed; rerun baseline capture after inspecting the stopped group"
selected=[d for d in days if d["date"]>=began.date().isoformat()]
saved={"organization":"ssh4","project":"default","group":"tm-test-us",
    "group_id":group["id"],"image":group["container"]["image"],
    "display_name":"TM","desired_replicas":10,"started_at":began.isoformat(),
    "measurement_started_ms":int(finished.timestamp()*1000),
    "provider_baseline_usd":balance["balance"],
    "provider_baseline_bytes":sum(d["traffic"] for d in selected),
    "provider_baseline_earned_usd":sum(d["earning"] for d in selected),
    "provider_baseline_source":"Fresh account API readings during recovery; earlier history unavailable"}
with record.open("x") as f:
    json.dump(saved,f,indent=2)
record.chmod(0o600)
if not exists:
    api(GROUP_PATH+"/start","POST")
    print("Start requested for ten TM replicas")
else:
    print("Cloud state left unchanged. If the surviving group is stopped, start it explicitly in Salad.")
print("New observation baseline saved; run the observer next")
PY_DEPLOY
```

If an API call times out, read back the group before retrying a creation. If a stopped group was created but baseline authentication failed, fix the credentials, rerun the baseline step against that existing group, then start it in the portal. The script deliberately leaves surviving groups' runtime/image/command unchanged.

**If the custom registry image is unavailable:** rebuild from the complete Dockerfile and worker source below, using a registry you control. The original vendor binary must still be available.

```bash
# Replace the example registry username before executing.
export TM_IMAGE='YOUR_DOCKERHUB_USERNAME/tm-recovery:20260907'
docker login
docker buildx version
docker buildx build --load --platform linux/amd64 -t "$TM_IMAGE" -f traffmonetizer/Dockerfile traffmonetizer
docker push "$TM_IMAGE"
# Set TM_IMAGE to the repository@sha256:digest printed by the successful push
# before running PY_DEPLOY. Keep the command override; it is safe with either image.
```

Use Docker Desktop’s BuildKit/buildx builder. If `docker buildx version` fails, restore the Docker Desktop CLI plugins before building. In the isolated audit, hiding those plugins selected the legacy builder, which failed with `failed to export image: NotFound: content digest ... not found`; the explicit BuildKit build succeeded. If using a temporary `DOCKER_CONFIG`, it must retain access to the installed CLI plugins.

A Docker Desktop credential-helper hang was resolved by using the existing `docker-credential-osxkeychain` helper in a temporary Docker config, not by putting a registry password in the project. Rebuilt image digests need not equal the historical image digest.

## 7. Start the recorder and the TM-only page

If a backup of `deployment.json` **and** `traffic.sqlite3` survived, restore them together under `~/.hg1/traffmonetizer/` and skip fresh-baseline creation. Preserve the matching group identity and baseline. If only one survives, use a separate archived copy and start a clearly new observation window rather than silently combining unrelated histories.

Run one collector cycle first:

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

Open <http://127.0.0.1:8787/>. The included page is a **TM-only recovery view**, with the last hour of minute bars, current workers, raw RX/TX totals, provider credits/earnings, and recovery events. It does not recreate the other five providers or their shared 6/12/24-hour UI. The full second-level TM history remains in SQLite for later integration.

The recovery server reads local snapshots and binds only to `127.0.0.1`; it never receives account credentials. The cloud workers keep running if this page or the Mac stops. The recorder needs an online, awake host to collect new observations and refresh account metrics.

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

## 8. Verify the deployment and understand the numbers

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

Recorded minute bars assign each measured interval's bytes to its ending minute. The observer keeps a last-hour JSON view but retains second-level rows in SQLite. Native contribution windows use same-client counter differences across up to fifteen minutes. The corrected minute rate is a measured approximately 60-second average, not a single second multiplied by sixty.

Provider account readings cover all traffic on that account. Use a dedicated account or account for other devices before attributing the whole account's earnings to this fleet. Preserve measurement baselines across ordinary restarts and image updates.

## 9. Logs, manual recovery, and known limitations

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
| Connected but native bytes zero | Connection alone does not prove paid contribution; observe a meaningful counter window |
| Increasing RX/TX but flat credits | Check native counters and delayed provider updates; raw overhead is not paid payload |

One recorded node clock was about **220 seconds ahead** of log receipt time. The current recorder still uses source timestamps for pagination/freshness and does **not** normalize node clocks. Compare Salad log `time` with `receive_time` when health or chart timing looks wrong. Do not silently rewrite timestamps or claim this limitation has been fixed.

The wrapper records recognized connection/statistics output and selected error/log keywords. It does not retain every possible vendor line or expose per-request destination errors. No `client_error` event is not proof every forwarded request succeeded.

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

## 10. Original paths and data worth backing up

| Component | Original location |
|---|---|
| Project source | `/Users/cosmosgeek/Desktop/salad-bandwidth-stack/traffmonetizer/` |
| Deployed Mac recorder | `/Users/cosmosgeek/Library/Application Support/Salad Bandwidth Dashboard/traffmonetizer/` |
| Keychain helper source | `salad-bandwidth-stack/scripts/keychain-store.swift` |
| Worker/deployment/account history | `~/.hg1/traffmonetizer/traffic.sqlite3` |
| Identity and monetary baseline | `~/.hg1/traffmonetizer/deployment.json` |
| Current derived view | `~/.hg1/traffmonetizer/latest.json` |
| Recorder logs and lock | `~/.hg1/traffmonetizer/observer.*` |
| Original observer LaunchAgent | `~/Library/LaunchAgents/com.cosmosgeek.tm-observer.plist` |
| Shared six-provider dashboard | `http://127.0.0.1:8787/#tm` (larger project, not needed for TM-only recovery) |

Back up SQLite with its backup API or while the observer is stopped; copying only a live `.sqlite3` file can omit its WAL data. A consistent backup command, when the original database still exists:

```bash
python3 - <<'PY_BACKUP'
from pathlib import Path
import sqlite3,shutil
source=Path.home()/".hg1/traffmonetizer"
target=Path.home()/"Desktop/tm-data-backup"
target.mkdir(exist_ok=False)
with sqlite3.connect("file:"+str(source/"traffic.sqlite3")+"?mode=ro",uri=True) as src:
    with sqlite3.connect(target/"traffic.sqlite3") as dst:
        src.backup(dst)
shutil.copy2(source/"deployment.json",target/"deployment.json")
print("Copy this folder to separate storage:",target)
PY_BACKUP
```

The historical ten-worker baseline on the original Mac was 7 September 2026 02:50:03 IST (`1788729603014` milliseconds), balance `$0.0269`, traffic `129348` bytes, and reported earning `$0`. These values are historical facts only: **do not paste them into a new deployment baseline.**

## 11. Sources and verification scope

- [Official TM image and interactive commands](https://hub.docker.com/r/traffmonetizer/cli_v2).
- [Salad container creation API](https://docs.salad.com/reference/saladcloud-api/container-groups/create-container-group).
- [Salad IMDS self-reallocation](https://docs.salad.com/container-engine/how-to-guides/imds/imds-reallocate).
- [Salad log schema and node/receipt timestamps](https://docs.salad.com/container-engine/reference/log-queries).
- [Salad deployment edits and restarts](https://docs.salad.com/container-engine/how-to-guides/managing-deployments).
- [TM account dashboard](https://app.traffmonetizer.com/dashboard).

The account collector endpoints were observed in TM's signed-in frontend, not a guaranteed public API contract: `https://data.traffmonetizer.com/api/app_user/get_balance` and `https://data.traffmonetizer.com/api/dashboard/get_graph_stat?period=month`. If that contract changes, restore the official account dashboard first and inspect the actual authenticated requests. Monthly graph retention also limits how far the included account calculation can look back.

This recovery guide was checked by extracting its source into an empty temporary directory, validating checksums and Python syntax, rebuilding the Keychain helper, and testing the TM-only server and observer against isolated fixtures. Writing this document did **not** create or stop cloud groups, change credentials, or replace the live runtime. The cloud configuration/source match was read-only. A new-account deployment and real billing were not repeated solely to test documentation.

### Reproduction audit — 7 September 2026

The follow-up audit started from this Markdown file alone in an empty temporary directory. Two independent readers checked the complete guide and ran separate extraction, deployment-recipe, observer and server tests. The source hashes were also compared again with the current project and the live Salad command override; all matched.

| Check | Measured result |
|---|---|
| Source extraction | All eight embedded file hashes matched; repeat extraction refused to overwrite |
| Actual pinned image startup | The exact 18-argument shell/base64 command reconstructed the worker byte for byte; missing `TM_TOKEN` produced the expected configuration error and exit 64 |
| Image rebuild | BuildKit built a Linux/amd64 image using only the extracted Dockerfile and source |
| Healthy idle client | Zero payload; stayed running through 47.01 seconds of measurements; no replacement request; clean exit on operator stop |
| Confirmed unavailable client | One replacement request after 30.112 seconds from client start; no local restart |
| No status/statistics replies | One replacement request after 60.051 seconds from client start |
| Client process exit | Replacement requested after 0.101 seconds from client start |
| New/reused deployment recipes | Isolated API fixtures verified fresh baselines, ten-worker creation, reuse without cloud mutation, uncertain-create readback, and no start after failed baseline capture |
| Recorder and recovery page | Independent fixtures verified duplicate suppression, exact byte/rate arithmetic, separate provider credits/earnings, stale-status handling and page/API responses |

The worker timing tests ran in actual containers with real wall-clock time. **The vendor client was replaced by a controlled local test client** to make failures repeatable, and the Docker network had no external access. The IMDS endpoint was deliberately unavailable there: the tests verified the outgoing recovery attempt and fallback exit 75, **not** a new machine allocation by Salad. Account API fixtures were simulated; a fresh billable deployment and future paid traffic were not reproduced during this documentation audit.

These results support rebuilding and exercising the documented software. They do not prove every external account, registry, API or machine will remain available, that every relay request succeeds, or that earnings will repeat. Use fresh provider readings and native client counters to measure a restored deployment's actual results.

## 12. Complete source appendix

The extraction markers and code blocks below are machine-readable. Preserve them exactly. These files are sufficient for the documented TM-only recovery path. The Dockerfile, worker, observer, legacy control helper, snapshot reader, page, and Swift helper are source copies from the current project; `recovery-server.py` is a small standalone adapter for serving the included TM page without the unrelated providers.

### traffmonetizer/Dockerfile

<!-- TM_FILE: traffmonetizer/Dockerfile SHA256: f375d5ff2f867e3ccd5243b6ca287c986b454241ca8917e2864235a79252d94d -->
```dockerfile
FROM traffmonetizer/cli_v2@sha256:6dbf8e75cc93e25131e2e701b1d478b3ccbf89212636b08d629621c270f0c966 AS vendor
FROM python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
COPY --from=vendor /usr/local/bin/cli /usr/local/bin/cli
COPY worker.py /usr/local/bin/tm-worker.py
WORKDIR /usr/local/bin
ENTRYPOINT ["python3", "-u", "/usr/local/bin/tm-worker.py"]
```

### traffmonetizer/worker.py

<!-- TM_FILE: traffmonetizer/worker.py SHA256: b83b9c1b3e8709f8dac923696920fcbbe8230658699e5c7e87a8142cd03085f7 -->
```python
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
    record = dict(kind=kind, time_ms=int(time.time() * 1000), instance=INSTANCE,
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
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            emit("reallocate_result", http_status=response.status, accepted=200 <= response.status < 300)
    except Exception as error:
        emit("reallocate_result", accepted=False, error=type(error).__name__, fallback="nonzero_exit")
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
    reply_at = time.monotonic()
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
        current_status = status_ms is not None and end_ms-status_ms <= 60000
        state = "connected" if current_status and connected and accepting and process is not None and process.poll() is None else "starting" if not current_status else "disconnected"
        batch.append([seq, end_ms, previous_ms, round(interval_ms, 3), delta_rx, delta_tx,
                      total_rx, total_tx, state, status_ms, 0, connected, accepting])
        previous_rx, previous_tx, previous_mono, previous_ms = rx, tx, now, end_ms
        seq += 1
        if len(batch) >= 10 or final:
            emit("batch", samples=batch, final=final, ip=ip, native_inbound=native_in,
                 native_outgoing=native_out, native_requests=native_requests, error=last_error,
                 unavailable_seconds=round(bad_seconds, 1))
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
            reply_at = now
            next_command = now + 3
            emit("client_start", client_run=0)
        for key, _ in selector.select(timeout=max(0, min(0.2, next_sample - now))):
            chunk = os.read(key.fd, 16384)
            if not chunk:
                selector.unregister(key.fileobj)
                continue
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
                    reply_at = time.monotonic()
                elif connection:
                    connected = connection[1].lower() == "connected"
                    if not connected:
                        accepting = False
                        status_ms = int(time.time() * 1000)
                        last_error = "Last connection event: " + connection[1].lower()
                    emit("client_log", message=line.replace(TOKEN, "[redacted]")[:500])
                elif stats:
                    native_in, native_out, requests = stats.groups()
                    native_requests = int(requests)
                    reply_at = time.monotonic()
                elif any(word in line.lower() for word in ("error", "failed", "invalid", "denied")):
                    clean = line.replace(TOKEN, "[redacted]")[:500]
                    if clean != last_error:
                        last_error = clean
                        emit("client_error", message=clean)
                elif line and any(word in line.lower() for word in ("connect", "accept", "starting", "version", "traffic")):
                    emit("client_log", message=line.replace(TOKEN, "[redacted]")[:500])
        now = time.monotonic()
        if process is not None and process.poll() is None and now >= next_command:
            try:
                process.stdin.write(b"status\nstatistics\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                last_error = "Client command input closed"
            next_command = now + 10
        stale = status_ms is not None and int(time.time() * 1000) - status_ms > 60000
        if stale:
            connected = accepting = False
            last_error = "Client status stopped responding"
        failed = process is not None and process.poll() is not None
        healthy = connected and accepting and process is not None and not failed and not stale
        if healthy:
            bad_seconds = 0
            last_error = None
        elif status_ms is not None and not stale:
            bad_seconds += max(0, now - health_checked_at)
        else:
            bad_seconds = 0
        health_checked_at = now
        unavailable = not healthy and bad_seconds >= 30
        unresponsive = now-reply_at >= 60
        if failed or unavailable or unresponsive:
            reason = "Traffic Monetizer client exited" if failed else "Traffic Monetizer stopped replying to status and statistics for 60 seconds" if unresponsive else "Traffic Monetizer unavailable for 30 seconds"
            stop_client()
            sample(final=True)
            reallocate(reason)
        if now >= next_sample:
            sample()
            next_sample = now + 1
    stop_client()
    sample(final=True)
    emit("stopped")


if __name__ == "__main__":
    main()
```

### traffmonetizer/control.py

<!-- TM_FILE: traffmonetizer/control.py SHA256: e3c8774bf4e75e9b25133152f8d42d24f7410358944d07245fa409506e82799e -->
```python
"""Operate only the SSH4 TraffMonetizer deployment; never print credentials."""
import argparse
from datetime import datetime, timezone
import getpass
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / ".hg1/traffmonetizer"
ORGANIZATION = "ssh4"
GROUP = "tm-test-us"
GROUP_PATH = "/projects/default/containers/" + GROUP
IMAGE = "docker.io/cosmosgeek0/salad-bandwidth-stack@sha256:d75e26d28fbb9352829eb41440a38b59d5f9d3ecb4967cc0414bb3bbc50f1c2c"


def keychain(service):
    return subprocess.check_output([str(ROOT / ".runtime/keychain-store"), "--read", "--service",
                                    service, "--account", getpass.getuser()], text=True).strip()


def api(path, method="GET", body=None):
    if not (path == "/projects/default/containers" or path == GROUP_PATH or path.startswith(GROUP_PATH + "/") or path == "/log-entries"):
        raise ValueError("Outside the SSH4 TraffMonetizer scope")
    key = keychain("salad-bandwidth-api")
    media = "application/merge-patch+json" if method == "PATCH" else "application/json"
    config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\nheader = " + json.dumps("Content-Type: " + media) + "\n"
    if body is not None:
        config += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
    result = subprocess.run(["curl", "-sS", "--max-time", "25", "--config", "-", "--request", method,
        "--write-out", "\n%{http_code}", "https://api.salad.com/api/public/organizations/ssh4" + path],
        input=config, capture_output=True, text=True, timeout=30)
    raw, status = result.stdout.rsplit("\n", 1)
    if result.returncode or not 200 <= int(status) < 300:
        raise RuntimeError("Salad " + method + " " + path + " returned HTTP " + status)
    return json.loads(raw) if raw.strip() else {}


def safe_group(group):
    return {key: group.get(key) for key in ("id", "name", "version", "replicas", "country_codes", "current_state")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "scale", "update", "status"))
    parser.add_argument("--replicas", type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.replicas <= 10:
        parser.error("This task is authorized for one through ten workers")
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    record = DATA / "deployment.json"
    if args.action == "create":
        if any(group["name"] == GROUP for group in api("/projects/default/containers").get("items", [])):
            raise RuntimeError("TraffMonetizer group already exists; inspect it instead")
        payload = {"name": GROUP, "display_name": "TM", "replicas": args.replicas,
            "autostart_policy": True, "restart_policy": "always", "country_codes": ["us"],
            "container": {"image": IMAGE, "priority": "batch", "resources": {"cpu": 1, "memory": 1024},
                          "environment_variables": {"TM_TOKEN": keychain("salad-traffmonetizer-token")}}}
        try:
            group = api("/projects/default/containers", "POST", payload)
        except RuntimeError:
            group = api(GROUP_PATH)
            if (group.get("container", {}).get("image") != IMAGE or group.get("country_codes") != ["us"]
                    or group.get("container", {}).get("environment_variables", {}).get("TM_TOKEN") != payload["container"]["environment_variables"]["TM_TOKEN"]):
                raise RuntimeError("Uncertain create response did not match this deployment") from None
        saved = {"organization": ORGANIZATION, "project": "default", "group": GROUP, "group_id": group["id"],
                 "image": IMAGE, "started_at": datetime.now(timezone.utc).isoformat(),
                 "desired_replicas": 10, "provider_baseline_usd": 0.0268,
                 "provider_baseline_source": "Observed signed-in dashboard before this deployment"}
        record.write_text(json.dumps(saved, indent=2))
        record.chmod(0o600)
    else:
        group = api(GROUP_PATH)
        if not record.exists() or json.loads(record.read_text())["group_id"] != group["id"]:
            raise RuntimeError("Deployment identity does not match this task")
        if args.action == "scale":
            if group["container"]["image"] != IMAGE or group.get("pending_change"):
                raise RuntimeError("The runtime image update is still applying; do not expand the old runtime")
            api(GROUP_PATH, "PATCH", {"replicas": args.replicas})
            group = api(GROUP_PATH)
            if group["replicas"] != args.replicas:
                raise RuntimeError("Replica change was not confirmed")
        if args.action == "update":
            api(GROUP_PATH, "PATCH", {"container": {"image": IMAGE}})
            group = api(GROUP_PATH)
            if group["container"]["image"] != IMAGE:
                if group.get("pending_change"):
                    print("Image update accepted and still preparing; verify the applied runtime before scaling.")
                    print(json.dumps(safe_group(group), indent=2))
                    return
                raise RuntimeError("Image update was not confirmed")
            saved = json.loads(record.read_text())
            saved["image"] = IMAGE
            record.write_text(json.dumps(saved, indent=2))
    print(json.dumps(safe_group(group), indent=2))
    print("instances", json.dumps([{key: value.get(key) for key in ("id", "machine_id", "state", "version", "ready")}
                                   for value in api(GROUP_PATH + "/instances").get("instances", [])]))


if __name__ == "__main__":
    main()
```

### traffmonetizer/observer.py

<!-- TM_FILE: traffmonetizer/observer.py SHA256: 44cf8579c09486a448497c87191b81cba74e39bfd230a84681ed8a7dd9ad6bca -->
```python
"""Read SSH4 logs and provider metrics; publish a credential-free dashboard snapshot."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import urllib.request

from control import DATA, GROUP_PATH, api, keychain


def millis(value):
    value = re.sub(r"\.(\d+)", lambda m: "." + (m[1] + "000000")[:6], value, count=1)
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def iso(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def database(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS samples (
          run TEXT, seq INTEGER, instance TEXT, machine TEXT, device TEXT, ip TEXT,
          time_ms INTEGER, start_ms INTEGER, interval_ms REAL, rx INTEGER, tx INTEGER,
          total_rx INTEGER, total_tx INTEGER, state TEXT, status_ms INTEGER,
          client_run INTEGER, native_in TEXT, native_out TEXT, requests INTEGER, error TEXT,
          PRIMARY KEY(run,seq));
        CREATE INDEX IF NOT EXISTS sample_time ON samples(time_ms);
        CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY,time_ms INTEGER,payload TEXT);
        CREATE TABLE IF NOT EXISTS provider (time_ms INTEGER PRIMARY KEY,payload TEXT);
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT);
    """)
    return db


def fetch_logs(start, end):
    cursor = start
    for _ in range(500):
        response = api("/log-entries", "POST", {"query": 'resource.type = "container" and resource.labels.project_name = "default" and resource.labels.container_group_name = "tm-test-us" and text_log startswith "TM_V1 "',
            "start_time": iso(cursor), "end_time": iso(end), "page_size": 100, "sort_order": "asc"})
        page = response.get("items")
        if not isinstance(page, list):
            raise RuntimeError("Salad returned an invalid log page")
        yield page
        if len(page) < 100:
            return
        following = max(millis(item["time"]) for item in page)
        if following <= cursor:
            raise RuntimeError("A full log page cannot advance; measurements were not skipped")
        cursor = following
    raise RuntimeError("Log backlog exceeded the bounded fetch window")


def ingest(db, items):
    for item in items:
        text = item.get("text_log", "")
        if not text.startswith("TM_V1 "):
            continue
        try:
            record = json.loads(text[6:])
            kind = record["kind"]
            instance, machine = record["instance"], record["machine"]
            run = instance + "/" + str(record["observer_start_ms"])
            if kind == "batch":
                rows = record["samples"]
            elif kind == "sample":  # Preserve measurements made by the initial canary.
                rows = [[record["seq"], record["time_ms"], record["start_ms"], record["interval_ms"],
                    record["rx_bytes"], record["tx_bytes"], record["total_rx_bytes"], record["total_tx_bytes"],
                    record["state"], record["status_ms"], record["client_run"], record["connected"], record["accepting"]]]
            else:
                encoded = json.dumps(record, sort_keys=True)
                db.execute("INSERT OR IGNORE INTO events VALUES (?,?,?)",
                           (hashlib.sha256(encoded.encode()).hexdigest(), record["time_ms"], encoded))
                continue
            for row in rows:
                if len(row) != 13 or not math.isfinite(row[3]) or row[3] <= 0:
                    raise ValueError("Invalid measurement interval")
                if any(value is not None and (not isinstance(value, (int, float)) or value < 0) for value in row[4:8]):
                    raise ValueError("Invalid traffic counter")
                state = row[8]
                if state not in ("starting", "connected", "disconnected") or state == "connected" and not (row[11] and row[12]):
                    raise ValueError("Invalid client state")
                db.execute("INSERT OR IGNORE INTO samples VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (run, row[0], instance, machine, record.get("device"), record.get("ip"), row[1], row[2], row[3],
                     row[4], row[5], row[6], row[7], state, row[9], row[10], record.get("native_inbound"),
                     record.get("native_outgoing"), record.get("native_requests"), record.get("error")))
        except (KeyError, ValueError, TypeError) as error:
            raise RuntimeError("A TraffMonetizer record was invalid: " + type(error).__name__) from None
    db.commit()


def provider_request(path):
    if path not in ("/api/app_user/get_balance", "/api/dashboard/get_graph_stat?period=month"):
        raise ValueError("Provider request is outside the read-only metrics scope")
    request = urllib.request.Request("https://data.traffmonetizer.com" + path,
        headers={"Authorization": "Bearer " + keychain("salad-traffmonetizer-session"), "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.load(response)
        refreshed = response.headers.get("Authorization", "")
    if refreshed.startswith("Bearer "):
        from control import ROOT
        import getpass
        subprocess.run([str(ROOT / ".runtime/keychain-store"), "--service", "salad-traffmonetizer-session",
            "--account", getpass.getuser()], input=refreshed[7:], text=True, capture_output=True, check=True)
    return result


def provider_reading(deployment):
    balance = provider_request("/api/app_user/get_balance")["data"]
    days = provider_request("/api/dashboard/get_graph_stat?period=month")
    start_day = deployment["started_at"][:10]
    selected = [day for day in days if day["date"] >= start_day]
    return {"observed_ms": int(time.time() * 1000), "balance_usd": balance["balance"],
            "balance_change_usd": balance["balance"] - deployment["provider_baseline_usd"],
            "credited_bytes": sum(day["traffic"] for day in selected) - deployment.get("provider_baseline_bytes", 0),
            "credited_usd": sum(day["earning"] for day in selected) - deployment.get("provider_baseline_earned_usd", 0),
            "requests": sum(day["requestsCount"] for day in selected), "days": selected,
            "source": "TraffMonetizer authenticated dashboard API", "scope": "Provider account totals less the saved ten-worker test baseline. Account balance is separate."}


def snapshot(db, deployment, members, errors):
    now = int(time.time() * 1000)
    test_start = deployment.get("measurement_started_ms", millis(deployment["started_at"]))
    current = []
    for member in members:
        row = db.execute("SELECT * FROM samples WHERE instance=? ORDER BY time_ms DESC,seq DESC LIMIT 1", (member["id"],)).fetchone()
        value = dict(row) if row else {"instance": member["id"], "machine": member["machine_id"], "state": "awaiting_sample"}
        age = now - value["time_ms"] if row else None
        value.update(salad_state=member["state"], sample_age_ms=age,
                     fresh=age is not None and -5000 <= age <= 45000)
        measured = db.execute("SELECT SUM(rx) rx,SUM(tx) tx,SUM(interval_ms) duration FROM samples WHERE instance=? AND start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL", (member["id"], test_start)).fetchone()
        value.update(test_rx=measured["rx"], test_tx=measured["tx"], test_duration_ms=measured["duration"],
                     raw_mb_per_minute=None, native_recent_bytes=None, native_recent_requests=None, native_recent_ms=None)
        if row:
            end = value["time_ms"]
            recent = db.execute("SELECT SUM(rx+tx) bytes,SUM(interval_ms) duration FROM samples WHERE run=? AND time_ms>? AND time_ms<=? AND start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL",
                                (value["run"], end - 60000, end, test_start)).fetchone()
            if recent["duration"]:
                value["raw_mb_per_minute"] = recent["bytes"] / 1e6 * 60000 / recent["duration"]
            base = db.execute("SELECT time_ms,native_in,native_out,requests FROM samples WHERE run=? AND client_run=? AND time_ms>=? AND time_ms<=? AND native_in IS NOT NULL AND native_out IS NOT NULL AND requests IS NOT NULL ORDER BY seq LIMIT 1",
                              (value["run"], value["client_run"], max(test_start, end - 900000), end)).fetchone()
            if base and end > base["time_ms"]:
                before = [base[key] for key in ("native_in", "native_out", "requests")]
                after = [value[key] for key in ("native_in", "native_out", "requests")]
                if all(str(number).isdigit() for number in before + after):
                    deltas = [int(last) - int(first) for first, last in zip(before, after)]
                    if min(deltas) >= 0:
                        value.update(native_recent_bytes=deltas[0] + deltas[1], native_recent_requests=deltas[2],
                                     native_recent_ms=end - base["time_ms"])
        value["working"] = bool(not errors.get("recorder") and value["fresh"] and value["state"] == "connected" and member["state"] == "running")
        current.append(value)
    totals = db.execute("SELECT COALESCE(SUM(rx),0) rx,COALESCE(SUM(tx),0) tx,COUNT(*) samples,MIN(time_ms) first_ms,MAX(time_ms) last_ms FROM samples WHERE start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL", (test_start,)).fetchone()
    minutes = {}
    for row in db.execute("SELECT CAST(time_ms/60000 AS INTEGER)*60000 minute,run,machine,instance,MAX(device) device,SUM(rx) rx,SUM(tx) tx,SUM(interval_ms) duration_ms,COUNT(*) samples FROM samples WHERE time_ms>=? AND start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL GROUP BY minute,run,machine,instance ORDER BY minute", (now - 3600000, test_start)):
        minute = minutes.setdefault(row["minute"], {"time_ms": row["minute"], "rx_bytes": 0, "tx_bytes": 0, "samples": 0, "workers": []})
        minute["rx_bytes"] += row["rx"]
        minute["tx_bytes"] += row["tx"]
        minute["samples"] += row["samples"]
        minute["workers"].append(dict(row))
    provider_row = db.execute("SELECT payload FROM provider ORDER BY time_ms DESC LIMIT 1").fetchone()
    provider = json.loads(provider_row[0]) if provider_row else None
    if provider:
        provider["age_ms"] = now - provider["observed_ms"]
        provider["fresh"] = provider["age_ms"] <= 180000 and not errors.get("provider")
    events = [json.loads(row[0]) for row in db.execute("SELECT payload FROM events WHERE json_extract(payload,'$.kind') NOT IN ('client_log') ORDER BY time_ms DESC LIMIT 20")]
    return {"schema_version": 1, "provider": "traffmonetizer", "title": "TM", "generated_ms": now,
            "deployment": deployment, "recorded": dict(totals), "workers": current,
            "running": sum(row["salad_state"] == "running" for row in current),
            "working": sum(row["working"] for row in current), "minutes": list(minutes.values()),
            "credited": provider, "events": events, "errors": errors,
            "measurement": "Raw interface RX and TX measured every second inside each container. Transported in ten-sample batches. Credited traffic comes separately from the provider account API."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True)
    lock = (DATA / "observer.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    deployment = json.loads((DATA / "deployment.json").read_text())
    db = database(DATA / "traffic.sqlite3")
    cursor_row = db.execute("SELECT value FROM meta WHERE key='cursor'").fetchone()
    cursor = int(cursor_row[0]) if cursor_row else millis(deployment["started_at"])
    members = []
    provider_at = 0
    reconcile_at = 0
    while True:
        began = time.monotonic()
        now = int(time.time() * 1000)
        errors = {}
        try:
            current_deployment = json.loads((DATA / "deployment.json").read_text())
            if current_deployment["group_id"] != deployment["group_id"]:
                raise RuntimeError("Saved deployment identity changed")
            deployment = current_deployment
            group = api(GROUP_PATH)
            if group["id"] != deployment["group_id"]:
                raise RuntimeError("Deployment identity changed")
            members = api(GROUP_PATH + "/instances")["instances"]
            start = max(millis(deployment["started_at"]), cursor - 120000)
            if time.monotonic() >= reconcile_at:
                start = min(start, max(millis(deployment["started_at"]), now - 600000))
                reconcile_at = time.monotonic() + 300
            for page in fetch_logs(start, now):
                ingest(db, page)
            cursor = now
            db.execute("INSERT OR REPLACE INTO meta VALUES ('cursor',?)", (str(cursor),))
            db.commit()
        except Exception as error:
            errors["recorder"] = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        if time.monotonic() >= provider_at:
            try:
                reading = provider_reading(deployment)
                db.execute("INSERT OR REPLACE INTO provider VALUES (?,?)", (reading["observed_ms"], json.dumps(reading)))
                db.commit()
                db.execute("DELETE FROM meta WHERE key='provider_error'")
            except Exception as error:
                db.execute("INSERT OR REPLACE INTO meta VALUES ('provider_error',?)", (type(error).__name__,))
            db.commit()
            provider_at = time.monotonic() + 60
        provider_error = db.execute("SELECT value FROM meta WHERE key='provider_error'").fetchone()
        if provider_error:
            errors["provider"] = provider_error[0]
        result = snapshot(db, deployment, members, errors)
        temporary = DATA / "latest.tmp"
        temporary.write_text(json.dumps(result, separators=(",", ":")))
        os.replace(temporary, DATA / "latest.json")
        print(json.dumps({"time_ms": result["generated_ms"], "running": result["running"], "working": result["working"], "samples": result["recorded"]["samples"], "errors": errors}), flush=True)
        if args.once:
            break
        time.sleep(max(1, 15 - (time.monotonic() - began)))


if __name__ == "__main__":
    main()
```

### dashboard/traffmonetizer.py

<!-- TM_FILE: dashboard/traffmonetizer.py SHA256: 7ec44b146c1b3e3ea5466f336488489744a2b92bdab300808e5da31a7ef31396 -->
```python
"""Read the TraffMonetizer observer snapshot for the shared dashboard."""
import json
from pathlib import Path
import time


def snapshot():
    path = Path.home() / ".hg1/traffmonetizer/latest.json"
    if not path.exists():
        return {"provider": "traffmonetizer", "workers": [], "minutes": [], "errors": {"recorder": "Recorder has not published a reading yet"}}
    data = json.loads(path.read_text())
    now = int(time.time() * 1000)
    age = now - data["generated_ms"]
    data["snapshot_age_ms"] = age
    data["stale"] = age > 45000
    for worker in data.get("workers", []):
        sample_age = now - worker["time_ms"] if worker.get("time_ms") is not None else None
        worker["sample_age_ms"] = sample_age
        worker["fresh"] = not data["stale"] and sample_age is not None and -5000 <= sample_age <= 45000
        worker["working"] = bool(worker["fresh"] and worker.get("state") == "connected" and worker.get("salad_state") == "running" and not data.get("errors", {}).get("recorder"))
    data["working"] = None if data["stale"] else sum(worker["working"] for worker in data.get("workers", []))
    return data
```

### dashboard/static/traffmonetizer.html

<!-- TM_FILE: dashboard/static/traffmonetizer.html SHA256: 588f0e315fe47d4d8394189c06d8a59bd1d7746a5c50745f968ed61f2289abec -->
```html
<!doctype html>
<html lang="en">
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TM · SSH4</title>
<style>
body{font:15px system-ui,sans-serif;color:#17212b;background:#fff;margin:24px;max-width:1400px}header{display:flex;align-items:baseline;gap:18px;flex-wrap:wrap}h1{font-size:24px;margin:0}a{color:#175ca5}nav{margin:14px 0 20px;display:flex;gap:18px;flex-wrap:wrap}.muted{color:#66717e}#summary{font-size:19px;font-weight:600;margin:16px 0 5px}#provider{margin:6px 0 20px}.notice{padding:9px 12px;background:#fff3cf;border:1px solid #dec985;white-space:pre-wrap}.chart{border:1px solid #d4dce5;padding:12px}svg{display:block;width:100%;height:230px}button{font:inherit;border:1px solid #bac6d2;border-radius:3px;background:#fff;padding:5px 10px;cursor:pointer}rect.bar{cursor:pointer}rect.bar:hover{fill:#163f70}.toolbar{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin:12px 0}.table{overflow:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{border-bottom:1px solid #dce2e8;padding:9px 10px;text-align:left;white-space:nowrap}th{font-size:12px;text-transform:uppercase;color:#586777;background:#f6f8fa}td:first-child{font-family:ui-monospace,monospace;font-size:12px}.good{color:#216b3b}.bad{color:#a43b2c}footer{font-size:12px;line-height:1.6;margin-top:18px}#events{white-space:pre-wrap;line-height:1.6}.hidden{display:none}@media(max-width:640px){body{margin:12px}#summary{font-size:16px}svg{height:190px}th,td{padding:7px}}
</style>
<header><h1>TM · SSH4</h1><span id="freshness" class="muted">Loading readings…</span></header>
<nav><a href="/">All services</a><a href="https://portal.salad.com/organizations/ssh4/projects/default/containers/tm-test-us" target="_blank" rel="noreferrer">Salad workers</a><a href="https://app.traffmonetizer.com/dashboard" target="_blank" rel="noreferrer">Provider account</a></nav>
<div id="error" class="notice hidden" role="status"></div>
<p id="summary">Waiting for the recorder.</p><p id="provider" class="muted"></p>
<section class="chart" aria-label="Recorded network traffic">
 <strong>Recorded network traffic per minute</strong><span class="muted"> · RX + TX · click a bar for server contributions</span>
 <svg id="chart" viewBox="0 0 1100 230" role="group" aria-label="Minute traffic graph"></svg>
 <div id="selection" class="muted">Only measured intervals are plotted. Missing readings are gaps.</div>
</section>
<div class="toolbar"><strong id="tableTitle">Current workers</strong><button id="current" type="button">Show current workers</button></div>
<div class="table"><table><thead><tr><th>Machine / instance</th><th>Status</th><th>Public IP</th><th>Received MB</th><th>Sent MB</th><th>Total MB</th><th>Last reading</th></tr></thead><tbody id="workers"></tbody></table></div>
<details style="margin-top:18px"><summary>Recent recovery and client events</summary><div id="events"></div></details>
<footer id="sources"></footer>
<script>
const $=id=>document.getElementById(id), ns='http://www.w3.org/2000/svg';let data=null, selected=null, busy=false, failed=false;
const number=(n,d=3)=>typeof n==='number'&&Number.isFinite(n)?n.toLocaleString('en-IN',{maximumFractionDigits:d}):'—';
const mb=n=>typeof n==='number'?number(n/1e6):'—';
const time=ms=>typeof ms==='number'?new Date(ms).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'—';
const age=ms=>typeof ms==='number'?Math.max(0,Math.round((Date.now()-ms)/1000))+'s ago':'No reading';
function svg(tag,attrs,text){const n=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;return n}
function cell(row,text,klass){const n=document.createElement('td');n.textContent=text;if(klass)n.className=klass;row.append(n);return n}
function render(){if(!data)return;const stale=failed||Date.now()-(data.generated_ms||0)>45000;const records=data.recorded||{};
 $('freshness').textContent=stale?'Recorder updates stopped · '+age(data.generated_ms):'Latest sample '+age(records.last_ms);
 const error=Object.values(data.errors||{});if(failed)error.unshift('The dashboard could not refresh. Last recorded data is shown.');$('error').textContent=error.join('\n');$('error').classList.toggle('hidden',!error.length);
 const working=stale?'—':(data.workers||[]).filter(w=>w.working&&Date.now()-(w.time_ms||0)<=45000).length, desired=data.deployment?.desired_replicas??10;
 $('summary').textContent=working+' / '+desired+' accepting traffic · '+(records.samples>0?mb((records.rx||0)+(records.tx||0)):'—')+' MB recorded';
 const paid=data.credited;
 $('provider').textContent=paid?'Provider credited: '+mb(paid.credited_bytes)+' MB · $'+number(paid.credited_usd,4)+' earned · account balance $'+number(paid.balance_usd,4)+' · '+age(paid.observed_ms)+(Date.now()-paid.observed_ms>180000||data.errors?.provider?' (stale)':''):'Provider credited traffic: waiting for an authenticated reading.';
 const minutes=data.minutes||[], chart=$('chart');chart.replaceChildren();const max=Math.max(0.001,...minutes.map(m=>(m.rx_bytes+m.tx_bytes)/1e6));const end=Math.floor(Date.now()/60000)*60000+60000,start=end-3600000;
 for(let n=0;n<=4;n++){const y=190-n*40;chart.append(svg('line',{x1:60,y1:y,x2:1080,y2:y,stroke:'#e3e8ed'}));chart.append(svg('text',{x:52,y:y+4,'text-anchor':'end',fill:'#62717e','font-size':11},number(max*n/4,3)))}
 for(let n=0;n<=6;n++){const at=start+n*600000;chart.append(svg('text',{x:60+n*170,y:216,'text-anchor':'middle',fill:'#62717e','font-size':11},new Date(at).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})))}
 for(const m of minutes){const value=(m.rx_bytes+m.tx_bytes)/1e6,x=60+(m.time_ms-start)/3600000*1020;if(x<60||x>1080)continue;const h=value?value/max*160:2;const r=svg('rect',{x,y:190-h,width:14,height:h,fill:selected===m.time_ms?'#163f70':value?'#347bbd':'#aebac5',class:'bar',tabindex:0,role:'button','aria-label':time(m.time_ms)+', '+number(value)+' MB'});r.append(svg('title',{},time(m.time_ms)+' · '+number(value)+' MB · '+m.samples+' measured intervals across workers'));const choose=()=>{selected=m.time_ms;render()};r.addEventListener('click',choose);r.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose()}});chart.append(r)}
 const minute=minutes.find(m=>m.time_ms===selected);$('selection').textContent=minute?time(minute.time_ms)+' · '+mb(minute.rx_bytes+minute.tx_bytes)+' MB · '+minute.samples+' measured intervals':'Only measured intervals are plotted. Missing readings are gaps.';
 $('tableTitle').textContent=minute?'Contributors to '+time(minute.time_ms)+' (including replaced workers)':'Current workers';
 const rows=minute?minute.workers:(data.workers||[]),body=$('workers');body.replaceChildren();
 for(const w of rows){const tr=document.createElement('tr');const id=cell(tr,(w.machine||'').slice(0,8)+' / '+(w.instance||'').slice(0,8));id.title=(w.machine||'')+' / '+(w.instance||'');const fresh=!stale&&Date.now()-(w.time_ms||0)<=45000;
 const status=minute?'Recorded':!w.time_ms?'Waiting for first reading':!fresh?'Last known: '+w.state:w.working?'Connected / accepting':w.state;
 cell(tr,status,minute?'muted':fresh&&w.working?'good':fresh&&w.state==='disconnected'?'bad':'muted');cell(tr,w.ip||'—');const rx=minute?w.rx:w.test_rx,tx=minute?w.tx:w.test_tx;cell(tr,mb(rx));cell(tr,mb(tx));cell(tr,typeof rx==='number'&&typeof tx==='number'?mb(rx+tx):'—');cell(tr,minute?number(w.duration_ms/1000,1)+'s recorded':age(w.time_ms));body.append(tr)}
 if(!rows.length){const tr=document.createElement('tr');const td=cell(tr,'Waiting for worker measurements.');td.colSpan=7;body.append(tr)}
 $('events').textContent=(data.events||[]).map(e=>time(e.time_ms)+' · '+(e.machine||'').slice(0,8)+' · '+e.kind+' · '+(e.reason||e.message||e.error||'')).join('\n')||'No recovery events recorded.';
 const since=data.deployment?.measurement_started_ms||Date.parse(data.deployment?.started_at||'');$('sources').textContent='Test started '+(Number.isFinite(since)?new Date(since).toLocaleString('en-IN'):'—')+'. MB means 1,000,000 bytes. Raw traffic is measured every second inside each worker and transported in batches. Provider credited bytes, earnings and balance are separately reported account metrics. Minute bars sum intervals ending in that minute; they are not forecasts.';
}
async function refresh(){if(busy)return;busy=true;const controller=new AbortController(),deadline=setTimeout(()=>controller.abort(),10000);
try{const r=await fetch('/api/traffmonetizer',{cache:'no-store',signal:controller.signal});if(!r.ok)throw Error('Recorder unavailable');data=await r.json();failed=false}
catch(e){failed=true;$('error').classList.remove('hidden');$('error').textContent='Cannot read the TraffMonetizer recorder.'}
finally{clearTimeout(deadline);busy=false;render()}}
$('current').addEventListener('click',()=>{selected=null;render()});refresh();setInterval(()=>{render();refresh()},2000);
</script>
</html>
```

### scripts/keychain-store.swift

<!-- TM_FILE: scripts/keychain-store.swift SHA256: 490eadaf1afb87a0f64bf6248254ccc48ac1171af9e2fc4c796c74c12c5ca045 -->
```swift
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
```

### recovery-server.py

<!-- TM_FILE: recovery-server.py SHA256: 9b32e66ca9ecfdb447d73543da72cfeef8e0171fff34b0b4619efff2c6bcaa72 -->
```python
"""TM-only loopback recovery server; no cloud writes or credential handling."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from dashboard.traffmonetizer import snapshot

ROOT = Path(__file__).resolve().parent


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/traffmonetizer":
                body = json.dumps(snapshot()).encode()
                content_type = "application/json; charset=utf-8"
            elif path in ("/", "/tm", "/traffmonetizer"):
                body = (ROOT / "dashboard/static/traffmonetizer.html").read_bytes()
                content_type = "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
        except (OSError, ValueError, KeyError) as error:
            self.send_error(503, "TM snapshot unavailable: " + type(error).__name__)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 8787), Handler) as server:
        print("TM recovery dashboard: http://127.0.0.1:8787/", flush=True)
        server.serve_forever()
```

