# bandwidth reel — ProxyRack (PR) rebuild guide

Snapshot: **7 September 2026**. This document contains the source and commands needed to recreate the PR deployment and a standalone PR monitoring page without this conversation or any other local project file. The reproducible result is the configuration, recovery behaviour and measurement pipeline. The same future IPs, traffic, credited bandwidth or earnings are not guaranteed.

The cloud worker and recorder below use the installed version 6 source snapshot, with one verified recovery-only correction: `record_minute()` uses Bash's built-in clock instead of launching `date` inside the shutdown trap. The live deployment was not changed during this guide verification. The small PR-only HTTP server and page adapt the existing monitoring page so rebuilding PR does not require the other five providers' dashboards. This is not a reconstruction of those other providers.

## What this rebuild creates

| Item | Exact setting in this snapshot |
|---|---|
| Salad organization / project | `ssh1` / `default` |
| Container group slug / display name | `pr` / `PR` |
| Desired replicas | **10 in one group**, not ten separate groups |
| Placement | `country_codes: ["us"]` |
| Per replica resources | **1 vCPU, 1024 MiB RAM**, no GPU |
| Priority / restart policy | `batch` / `always` |
| Container image | `docker.io/proxyrack/pop@sha256:7de6719f37b31d5dd354f8cdd3ae601b4ed401832d0935ff460f968e0b6731bc` |
| Native client | Official Go client downloaded from `https://app-updates.sock.sh/peerclient/go/client` |
| Native version source | `https://app-updates.sock.sh/peerclient/go/version.txt` — version **60 was observed** during implementation |
| Peer home connection | `point-of-presence.sock.sh:443` |
| Monitoring | `http://127.0.0.1:8787/` and `/proxyrack`; JSON `/api/proxyrack` |
| Installed files on macOS | `~/Library/Application Support/Salad Bandwidth Dashboard/` |
| Local state and history | `~/.hg1/proxyrack/` |

Settings are the implemented configuration, not claims about provider limits or profitability. The base image is pinned by digest; the native download URL is mutable and may serve a newer version at a future rebuild. A successful rebuild still depends on Salad and ProxyRack operating, this image/download being available, funded account access, and working credentials. Keep a copy of this Markdown outside the machine; it cannot recover itself if its only copy is deleted.

No API keys are included. If all credentials and account access are lost, recover those accounts first. Deleted local traffic history cannot be reconstructed from this document; retained Salad logs and provider records may recover only part of it.

## Recovery paths

- **Local files lost, cloud group still exists:** extract files, restore credentials, then run the initialization step. It adopts the existing `pr` group's namespace and ID without restarting or changing it. Start the local recorder and page.
- **Cloud group and local files both lost:** extract files, restore credentials, initialize a fresh manifest, then deploy the single group. Its new replicas register themselves.
- **Only this Markdown remains:** follow every step in order. The appendix contains every local source dependency for this PR-only path. There is no required clone, npm package, pip package, chat message, private gist, or pre-existing binary helper.

This guide documents macOS because that is the original control/recording machine. The paid peer clients run on Salad's Linux nodes; Docker Desktop is not required on the Mac. A Linux control machine would need a different credential-store adapter and service manager, which this exact macOS recovery path does not provide.

## 1. Prerequisites and account access

Use an account authorized to manage the Salad organization `ssh1`, with a project named `default` and sufficient prepaid credit. If the organization or project was also deleted, recreate those exact slugs in the Salad portal first. The embedded program is scoped to them; using a different organization requires changing its API base and portal URLs together. The original experiment used **$5**, with no automatic recharge added by this work. Ten desired replicas must fit the organization's quota. The portal was observed counting **stopped replicas too**; if old test groups occupy the allowance, explicitly retire those known groups in the portal before a fresh deployment. The commands below never delete unrelated groups or add credit.

Required local tools: Python **3.9 or later** with its standard library, `curl`, and Apple's Swift compiler (`xcrun swiftc`) to rebuild the Keychain helper. If absent, install Apple's Command Line Tools first, then return after installation completes:

```bash
xcode-select --install
```

Check tools:

```bash
python3 --version
curl --version
xcrun --find swiftc
```

Credentials:

| Credential | Obtain from | Keychain service | Where used |
|---|---|---|---|
| Salad API key | Authorized Salad account/API-key settings | `salad-bandwidth-api` | Local deployment and log/inventory reader only |
| ProxyRack Peer API key | [Peer API page](https://peer.proxyrack.com/api-doc) in the owning account | `proxyrack-peer-api` | Local provider reader and Salad `PR_API_KEY` environment variable for replica self-registration |

Both Keychain items use the current macOS username as the account. Do not paste keys into source files, Markdown, command arguments, shell history, screenshots, or log output. A worker does **not** receive the Salad API key. It uses Salad's local metadata service to reallocate itself. The ProxyRack key must reach the workers for autonomous registration; the shell unsets it before launching the native child and clears its private copy after registration. Authorized Salad administrators can still access the configured environment.

## 2. Extract the embedded source files

Save this Markdown as `~/Desktop/salad/proxyrack.md`. If stored elsewhere, change only `document` in this command. It extracts into the installation directory and verifies the appendix hashes. It refuses to overwrite different files so an existing shared dashboard is not silently replaced. This is intended for disaster recovery; if a working installation already exists, first compare files and use a separate staging directory for inspection.

```bash
python3 - <<'PY_EXTRACT'
from pathlib import Path
import hashlib
import os
import re

os.umask(0o077)
document = Path.home() / "Desktop/salad/proxyrack.md"
root = Path.home() / "Library/Application Support/Salad Bandwidth Dashboard"
expected = {
    "proxyrack.py", "dashboard/__init__.py", "dashboard/native_network.py",
    "scripts/keychain-store.swift", "dashboard/pr_recovery_server.py",
    "dashboard/static/proxyrack.html",
}
pattern = r"<!-- recovery-file: ([^\n]+) sha256: ([0-9a-f]{64}) -->\n```[^\n]*\n(.*?)\n```\n<!-- end-recovery-file -->"
blocks = re.findall(pattern, document.read_text(), flags=re.S)
if len(blocks) != len(expected) or {path for path, _, _ in blocks} != expected:
    raise SystemExit("Missing, duplicate, or unexpected recovery source blocks")
ready = []
for name, checksum, text in blocks:
    body = (text + "\n").encode()
    if hashlib.sha256(body).hexdigest() != checksum:
        raise SystemExit("Source checksum mismatch: " + name)
    target = root / name
    if target.exists() and target.read_bytes() != body:
        raise SystemExit("Existing file differs; stage and compare before replacing: " + str(target))
    ready.append((target, body))
for target, body in ready:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
print("Extracted", len(ready), "files into", root)
PY_EXTRACT
```

Compile the embedded Keychain helper. Skip compilation if the existing helper works and you are recovering only the recorder. Rebuilding a helper can cause macOS Keychain to ask for permission again; allow the trusted local helper for these specific items when prompted.

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
mkdir -p .runtime
chmod 700 .runtime
xcrun swiftc scripts/keychain-store.swift -o .runtime/keychain-store
chmod 700 .runtime/keychain-store
```

## 3. Store the keys securely

The command uses hidden terminal input and passes each key to the helper through stdin. Existing usable Keychain items are retained; missing items are requested. It never prints the key.

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 - <<'PY_KEYS'
from pathlib import Path
import getpass
import subprocess

helper = Path.cwd() / ".runtime/keychain-store"
account = getpass.getuser()
for service, label in (("salad-bandwidth-api", "Salad API key"),
                       ("proxyrack-peer-api", "ProxyRack Peer API key")):
    args = [str(helper), "--service", service, "--account", account]
    result = subprocess.run(args + ["--read"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode == 0:
        print(label + ": existing Keychain item available")
        continue
    key = getpass.getpass(label + " (hidden): ").strip()
    if not key:
        raise SystemExit("Empty key; nothing stored")
    subprocess.run(args, input=key.encode(), check=True)
    del key
    subprocess.run(args + ["--read"], stdout=subprocess.DEVNULL, check=True)
    print(label + ": saved and readable")
PY_KEYS
```

If an existing item contains an obsolete key, update that named item through Keychain Access or rerun the helper with hidden stdin for that service. Never use the helper's `--read` mode directly in a visible terminal without redirecting/capturing its stdout.

## 4. Initialize local deployment identity

The original program expects `deployment.json` to exist, so **do not skip this step**. It creates the directory, generates a fresh namespace for a new deployment, or recovers identity from an existing `pr` group. It only reads Salad and writes local metadata; it does not create, update, restart, or delete containers.

For this snapshot the historical group ID was `ab9fd890-55b8-42ab-86ac-957fe8ce3d87`, and its namespace was `bdf752e1281d57a77633eeeb4044b210`. These are identity values, not credentials. Do not force them onto a new group; adopt the values actually returned by Salad.

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 -B - <<'PY_INIT'
from datetime import datetime, timezone
import json
import os
import secrets
import proxyrack as pr

os.umask(0o077)
pr.DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
path = pr.DATA / "deployment.json"
api = pr.salad_api()
items = api(pr.GROUPS).get("items", [])
existing = next((g for g in items if g["name"] == "pr"), None)
if path.exists():
    config = json.loads(path.read_text())
    if config.get("name") != "pr" or config.get("replicas") != 10:
        raise SystemExit("Existing local manifest is not this PR deployment; inspect it before changing it")
    if existing is None and config.get("group_id"):
        raise SystemExit("Manifest belongs to a deleted group. Preserve its data, move ~/.hg1/proxyrack aside, then initialize a new run")
    if existing and config.get("group_id") != existing["id"]:
        raise SystemExit("Local and cloud group IDs disagree; inspect before proceeding")
    print("Existing local manifest retained")
else:
    config = {
        "organization": "ssh1", "project": "default", "name": "pr", "replicas": 10,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "namespace": secrets.token_hex(16), "image": pr.IMAGE,
    }
    if existing:
        group = api(pr.GROUPS + "/pr")
        namespace = group["container"].get("environment_variables", {}).get("PR_NAMESPACE")
        if not namespace or group["container"]["image"] != pr.IMAGE or group["replicas"] != 10:
            raise SystemExit("Existing PR has a different configuration; inspect it, do not overwrite it")
        config.update(group_id=group["id"], namespace=namespace, created_at=group["create_time"])
        print("Adopting existing PR; its running configuration is unchanged")
    else:
        print("Initialized a new PR manifest; cloud deployment has not started")
    pr.save(path, config)
print("Manifest:", path)
PY_INIT
```

A replica's provider ID is `SHA256(PR_NAMESPACE + ":" + SALAD_INSTANCE_ID).hexdigest().upper()`. This gives each instance a separate 64-character provider ID without maintaining ten group configurations. Replacements get new IDs; preserve earlier provider devices for accounting. Separate Salad nodes can still share a public IP: compare provider-reported IPs before assuming ten distinct exits.

### Surviving cloud group with a replaced ProxyRack key

If the original Peer API key was lost/revoked and you obtained a replacement, saving it in Keychain fixes local reads only. Neither `deploy` nor `update` replaces an existing group's `PR_API_KEY`. After adopting the surviving group in step 4, use this explicit synchronization command. It compares the keys without printing them and updates only that environment value if different. This is an intentional cloud change and can roll replicas. Skip it when no group exists; fresh `deploy` already supplies the current key.

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 -B - <<'PY_KEY_SYNC'
import getpass
import subprocess
import proxyrack as pr

api = pr.salad_api()
config = pr.configuration()
group = api(pr.GROUPS + "/pr")
environment = dict(group["container"].get("environment_variables", {}))
if group["id"] != config.get("group_id") or environment.get("PR_NAMESPACE") != config["namespace"]:
    raise SystemExit("Cloud identity differs; no key update requested")
key = subprocess.check_output([
    str(pr.HELPER), "--read", "--service", "proxyrack-peer-api", "--account", getpass.getuser()
], text=True).strip()
if not key:
    raise SystemExit("Empty Keychain credential; no key update requested")
if environment.get("PR_API_KEY") == key:
    print("Cloud registration key already matches; no update needed")
else:
    environment["PR_API_KEY"] = key
    api(pr.GROUPS + "/pr", "PATCH", {"container": {"environment_variables": environment}})
    after = api(pr.GROUPS + "/pr")
    if after["container"]["environment_variables"].get("PR_API_KEY") != key:
        raise SystemExit("Cloud key update is not confirmed; inspect the group before proceeding")
    print("Cloud registration key updated; wait for the rollout and verify registration")
del key
PY_KEY_SYNC
```

## 5. Deploy one group with ten replicas

**Fresh deployment only:** this command starts paid Salad workloads using existing credit. It creates `pr`, waits for the initial preparing state, starts a stopped group, and saves its ID locally. No top-up or payment configuration is performed.

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 -B proxyrack.py deploy
python3 -B proxyrack.py status
```

For **local-only recovery of a surviving cloud group**, skip `deploy`; use `status` and start the recorder in the next step. To intentionally apply the embedded startup to an existing matching group:

```bash
python3 -B proxyrack.py update
```

`update` changes the group's startup command and may roll its instances. It is not required merely to restore local monitoring. The historical group's last verified version was **6**; a new deployment's version number will differ.

Important implementation details are embedded in `STARTUP` and `command()`:

- The command writes the Bash startup from base64 chunks into `/tmp/pr-start.sh`. Each chunk is at most 900 characters; the implementation checks at most 100 argv entries and at most 1000 characters per entry. Multiline argv strings were rejected with HTTP 400 in the original live run; the base64 command was accepted.
- The official image supplies Bash, Node, curl, and GNU tools. Node is used only to validate registration JSON; the native Go program does the peer work.
- The native child must keep stdin open. The FIFO/FD arrangement is required; launching it with closed stdin makes it exit.
- There is no custom registry, custom built image, external control server, or Salad key inside a worker.

If creation returns HTTP 400, check the real portal error and replica allowance before retrying. If a create request times out, inspect the group list before repeating it. The initializer/deployer verifies identity rather than blindly creating another group. Do not run the old singleton migration branch unless deliberately migrating a known legacy manifest.

## 6. Run the recorder and monitoring page

First run the recorder in the foreground so Keychain prompts and errors are visible:

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 -B proxyrack.py observe
```

Leave it running until `~/.hg1/proxyrack/view.json` begins updating. In another terminal:

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 -B -m dashboard.pr_recovery_server --port 8787
```

Open `http://127.0.0.1:8787/`. `/#proxyrack` also opens this standalone page; URL fragments are browser-side. It serves only PR. If port 8787 is already occupied by the surviving shared dashboard, use its PR tab instead, or use `--port 8788` for this recovery page. Do not kill an unrelated server to free the port.

The page reads files; it makes **no provider or Salad API calls**. Closing the Mac stops local recording and viewing, not the cloud peers or their self-reallocation. The recorder can backfill retained Salad logs when restarted, but logs outside retention and unsaved final records cannot be guaranteed recoverable.

For login-time local recording and viewing, stop the two foreground processes with Ctrl-C, then create the macOS LaunchAgents below. These are just the local recorder and read-only page, not a recovery dependency for the cloud workers.

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 - <<'PY_SERVICES'
from pathlib import Path
import os
import plistlib
import shutil

os.umask(0o077)
root = Path.cwd()
python = shutil.which("python3")
if not python:
    raise SystemExit("python3 is not installed")
logs = Path.home() / ".hg1/proxyrack"
logs.mkdir(parents=True, exist_ok=True, mode=0o700)
agents = Path.home() / "Library/LaunchAgents"
agents.mkdir(parents=True, exist_ok=True)
items = [
    ("com.cosmosgeek.proxyrack-recorder", [python, "-B", str(root / "proxyrack.py"), "observe"], "observer"),
    ("com.cosmosgeek.proxyrack-page", [python, "-B", "-m", "dashboard.pr_recovery_server", "--port", "8787"], "page"),
]
for label, args, stem in items:
    spec = {
        "Label": label, "ProgramArguments": args, "WorkingDirectory": str(root),
        "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 30,
        "StandardOutPath": str(logs / (stem + ".out.log")),
        "StandardErrorPath": str(logs / (stem + ".err.log")),
    }
    path = agents / (label + ".plist")
    if path.exists() and plistlib.loads(path.read_bytes()) != spec:
        raise SystemExit("Existing service differs; inspect its settings before replacing: " + str(path))
    path.write_bytes(plistlib.dumps(spec))
    print(path)
PY_SERVICES
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.cosmosgeek.proxyrack-recorder.plist"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.cosmosgeek.proxyrack-page.plist"
```

Do not bootstrap a second copy if the label is already loaded. Inspect with `launchctl print`, and use `launchctl kickstart -k` for an intentional restart after an update. If the existing shared dashboard occupies port 8787, omit the page agent or change its port before loading it.

```bash
launchctl print "gui/$(id -u)/com.cosmosgeek.proxyrack-recorder"
launchctl print "gui/$(id -u)/com.cosmosgeek.proxyrack-page"
```

Installing under Application Support is intentional: background Python launched from Desktop previously failed with macOS `Operation not permitted`. Keep a single recorder per data directory; its `fcntl` lock rejects a duplicate writer.

## 7. Verify actual operation

Do not equate a successful deploy request or Salad's `running` state with a registered, connected, productive peer.

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 -B - <<'PY_VERIFY'
import json
import time
import proxyrack as pr

api = pr.salad_api()
config = pr.configuration()
group = api(pr.GROUPS + "/pr")
assert group["id"] == config["group_id"]
assert group["replicas"] == 10
assert group["container"]["environment_variables"]["PR_NAMESPACE"] == config["namespace"]
assert "Salad-Api-Key" not in group["container"]["environment_variables"]
print("Group:", group["name"], "replicas:", group["replicas"], "version:", group["version"])
print("Salad counts:", group["current_state"]["instance_status_counts"])
view = json.loads((pr.DATA / "view.json").read_text())
assert view["group_id"] == config["group_id"], "Recorder view belongs to a different group"
now = int(time.time() * 1000)
feed_fresh = -10_000 <= now - view["generated_ms"] <= 90_000 and not view["cloud_error"]
connected = sum(bool(feed_fresh and w["fresh"] and w.get("client_state") == "running"
                     and not w.get("client_error") and w["salad_state"] == "running"
                     and -10_000 <= now - w["last_sample_ms"] <= 150_000)
                for w in view["workers"])
print("Fresh registered/connected clients:", connected, "/", view["requested"])
print("Recorder error:", view["cloud_error"], "feed age seconds:", round((now-view["generated_ms"])/1000))
print("Raw network MB:", view["network_mb"], "cached credited MB:", view["credited_mb"],
      "account balance:", view["balance"])
for w in view["workers"]:
    print(w["name"], w["salad_state"], w.get("client_state"), w.get("client_error"),
          w["provider_status"], "latest MB/min:", w["mb_per_minute"])
PY_VERIFY
```

In Salad's log viewer, filter project `default` and group `pr`. Useful prefixes:

| Log prefix | Meaning |
|---|---|
| `PR_SELF_START` | Instance/device/machine identity and downloaded native version |
| `PR_LOG ... connected to home:` | Native control connection established |
| `PR_REGISTERED` | Provider confirmed that exact device ID belongs to the account |
| `PR_MINUTE_V1` | Source timestamp, sequence, counters, registration flag and client state |
| `PR_DNS_FALLBACK` | Registration switched to HTTPS DNS after a resolver failure |
| `PR_REGISTRATION_RETRY` | Registration still pending or rate-limited; not successful earning |
| `PR_SELF_REALLOCATE` | Worker itself requested replacement |
| `PR_SELF_IMDS_RESPONSE` | Actual metadata response: both HTTP 200 and 204 are accepted |

For a scoped read-only log query, without printing keys or container environment:

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 -B - <<'PY_LOGS'
from datetime import datetime, timedelta, timezone
import proxyrack as pr

end = datetime.now(timezone.utc)
result = pr.salad_api()("/log-entries", "POST", {
    "query": 'resource.type = "container" and resource.labels.project_name = "default" and resource.labels.container_group_name = "pr"',
    "start_time": (end - timedelta(minutes=10)).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    "end_time": end.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    "page_size": 100, "sort_order": "desc",
})
for item in reversed(result.get("items", [])):
    print(item["time"], item.get("text_log", ""))
print("This is at most 100 recent rows, not a full-fleet proof if truncated.")
PY_LOGS
```

Check each current instance, not just the newest log line. Good operational evidence is a fresh minute with `registered=1 state=running error=none final=0`, matching both the current instance ID and machine ID. Low traffic alone is not proof of a broken connection; connected alone is not proof of earnings. Recheck after replacements and provider delays.

## Recovery behaviour in the embedded worker

This is the **version 6 policy with the verified shutdown-clock correction**, replacing the earlier two-restart/180-second experiment:

1. Download failures after the built-in curl retries request self-reallocation.
2. Native process exit immediately requests self-reallocation.
3. A continuous home-connection attempt lasting **60 seconds** triggers self-reallocation. Registration calls can delay the supervisor loop by their bounded timeout, so this is a configured threshold rather than a hard real-time deadline.
4. The worker POSTs to `http://169.254.169.254/v1/reallocate` with `Metadata: true` and a JSON reason. It retries a failed metadata request up to three times, accepts 200/204, and exits 75 as the fallback for Salad's restart policy.
5. An operator TERM/INT exits cleanly with final telemetry and **does not** ask for another machine.
6. Registration initially waits 60–179 seconds, then backs off from 60 seconds toward a 600-second cap, plus up to 89 seconds of jitter. DNS resolver errors use curl's `--doh-url https://1.1.1.1/dns-query`; TLS verification stays enabled. An already-owned ID is verified with `device/status`.
7. An unregistered control-connected client emits `state=starting error=registration_pending`, not `running`. The normal native process retains its own connection/retry behavior.

**Limits of this policy:** registration failure/rate limits retry without reallocating; the metadata controller cannot run while the container is still downloading or not executing; it cannot recover a frozen host from within that frozen host. No automatic low-earner sorting, duplicate-IP detector, or profitability-based replacement loop was implemented. Low-contributor and duplicate-IP reallocations were operator trials, not a proven optimization policy.

Native SOCKS target connection errors are not automatically treated as failed home connections. In the investigation, every new worker received requests to `144.202.45.251:443` that timed out. Binary inspection and live sockets identified these as requested destination connections, separate from the home/backconnect host. Whether that target was a scoring probe or a customer's destination was not established. Reallocating every node on those individual target failures would recreate the same failures on each new node.

## What the measurements mean

- **Network MB** is decimal `(RX + TX) / 1,000,000` from `eth0` counters after the client-download baseline. It includes control/registration traffic and both network legs when forwarding a byte. It is not unique customer payload or paid bandwidth.
- **Credited MB** is ProxyRack's reported gigabytes multiplied by 1000. The aggregate includes all recorded current and replaced devices for this group. Values are cached, delayed, and can be incomplete; inspect their `bandwidth_checked_ms` and errors. It is not dollars.
- **Balance** is the provider account balance, including earlier devices/runs. The code does not retain a starting account balance and interval balance history, so it cannot report exact earnings or profit attributable to this group.
- **Connected clients** require fresh registered native-client evidence. Provider status/IP is sampled slowly; a stale provider API read does not automatically mean the client is offline.
- Counters are deduplicated by `(group_id, instance, observer, seq)`. Conflicting duplicates are invalidated. Both instance and machine identity must match when displaying a current worker. All queries for this test must filter the current `group_id`.
- Source records are per observed interval; fixed clock-minute bars produced by `bucket_minutes()` split unaligned intervals proportionally and label them estimated. Do not invent traffic in missing intervals.

A real root-dashboard bug included **179.264546 MB from deleted singleton groups** in the new PR test. The correct group had **81.921907 MB** at that audit snapshot. The recovery server and embedded `saved_minutes(..., group_id=...)` preserve the fix. Never sum every row in a reused SQLite database without the group filter.

A separate measured API response was `Requests limit exceeded (5 per minute).` The recorder therefore serializes requests with a 20-second wait after each request, leaving some capacity for cloud registration. That is per recorder, not a cross-machine distributed lock: multiple recorders or external manual calls share the account limit. Startup bursts can still return 403; replicas back off. Current bandwidth is due every five minutes, old-device bandwidth hourly, provider status every 30 minutes (errors due again after two minutes), and balance every ten minutes (errors due after two minutes). These are earliest-due intervals; backlog and the global pacing can make actual reads later. Only one local provider reader should be active.

The implementation does not prove PR is profitable. The historical audit found roughly **81% of observed worker-minute intervals at or below 5 KB**, despite active control connections. Trials replacing poor contributors and duplicate IPs did not establish a sustained paid-throughput gain. Reproducing the deployment must not be described as reproducing a successful earner.

## Troubleshooting and operation

| Symptom | Check and correction |
|---|---|
| Periodic Node `ECONNREFUSED ...:80` / `go1.monetizemyapp.net` | The original vendor Node wrapper's log uploader caused this. Use the embedded direct native startup, not `/app/run.sh` or the Node script. Do not hide true native errors. |
| Intentional stop unexpectedly requests reallocation | Use the corrected `record_minute()` clock line embedded below. In the pinned Bash image, spawning `date` while handling TERM during a timed read reproduced the failure; the built-in clock passed repeated stop tests. |
| Native immediately exits with stdin closed | Restore the FIFO and open descriptor arrangement in `start_client()`; do not background it with closed stdin. |
| `PR_REGISTRATION_RETRY http=000`, resolver timeout | Check `PR_DNS_FALLBACK`; live DNS-over-HTTPS fixed API-name resolution on affected nodes. This fallback covers registration curl requests, not the native Go resolver for every customer hostname. General DNS failure needs its own node investigation. |
| `403 Requests limit exceeded` | Count all callers for the account, keep one paced recorder, retain replica backoff. More polling lowers data quality by blocking registration. |
| Instance remains unregistered | Inspect exact `device/add` response without leaking the key, check device ID, DNS, rate limit and owning account. Do not mark it earning because Salad is running. |
| `Invalid isoformat string` | Keep `parsed_time()` normalization to six fractional digits; Salad timestamps were observed with varying fractional precision. |
| Recorder `Operation not permitted` on Desktop | Run the installed program from Application Support; foreground it once to resolve Keychain access. |
| Port 8787 occupied | Use the existing server or a different loopback port; do not start two servers on the same port. |
| Source/Salad state disagrees | Preserve raw Salad state and separately display fresh client state; API labels can lag. Never attribute a previous instance's log to a replacement on the same machine. |
| Duplicate public IPs | Confirm both device IDs with provider responses. One node per replica does not guarantee unique public IP. A single scoped reallocation may improve diversity; it does not guarantee throughput and should not delete provider history. |
| Low credits but large network totals | Compare the same time window, source overhead, relayed RX+TX, delayed provider reads and old IDs. Do not call raw bytes earnings or assume geography proves demand. |

Manage the cloud group through [Salad PR](https://portal.salad.com/organizations/ssh1/projects/default/containers/pr). Local `observe`/HTTP processes stopping does not stop paid cloud instances. To stop the paid experiment deliberately, use the portal's **Stop** for `pr`, or the scoped API command below:

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 -B - <<'PY_STOP'
import proxyrack as pr
api = pr.salad_api()
group = api(pr.GROUPS + "/pr")
if group["id"] != pr.configuration()["group_id"]:
    raise SystemExit("Group identity changed; no stop requested")
api(pr.GROUPS + "/pr/stop", "POST")
print("PR stop requested; confirm stopped in Salad")
PY_STOP
```

After an intentional stop, rerunning `deploy` starts the same matching group. Do not detach/delete old devices merely to tidy the provider page: provider documentation says their associated earnings can disappear until reattached.

## Preserve data separately

At minimum back up this Markdown, account recovery access and the API credentials in an appropriate secret store, plus `~/.hg1/proxyrack/deployment.json`, `provider.json`, `cursor.json`, and `traffic.sqlite3` if history matters. `view.json` is derived. Use SQLite's online backup API for a consistent database copy while the recorder is running; do not copy only the main database file and ignore an active WAL.

```bash
python3 - <<'PY_BACKUP'
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sqlite3

os.umask(0o077)
source = Path.home() / ".hg1/proxyrack"
backup = Path.home() / "Desktop" / ("pr-backup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
backup.mkdir(mode=0o700)
with sqlite3.connect("file:" + str(source / "traffic.sqlite3") + "?mode=ro", uri=True) as src:
    with sqlite3.connect(backup / "traffic.sqlite3") as dst:
        src.backup(dst)
for name in ("deployment.json", "provider.json", "cursor.json"):
    path = source / name
    if path.exists():
        text = path.read_text()
        json.loads(text)
        (backup / name).write_text(text)
print("History backup:", backup, "— copy it to an independent backup location")
PY_BACKUP
```

To restore history, stop the local recorder, restore a consistent backup set to `~/.hg1/proxyrack/`, confirm its group ID and namespace match the surviving cloud group, then restart the recorder. If creating a completely new group, retain the old backup separately and initialize fresh state instead of relabeling old history with the new group ID.

## Sources and verification boundary

Primary references: [ProxyRack Docker image](https://hub.docker.com/r/proxyrack/pop), [official Docker installation guide](https://help.proxyrack.com/en/articles/8397256-how-do-i-install-the-peer-program-in-docker), [Peer API](https://peer.proxyrack.com/api-doc), [payout rate](https://help.proxyrack.com/en/articles/9722403-what-is-the-payout-rate-for-the-peer-program), [device removal and earnings](https://help.proxyrack.com/en/articles/6532814-my-earnings-were-removed), [Salad group creation](https://docs.salad.com/reference/saladcloud-api/container-groups/create-container-group), [Salad IMDS reallocation](https://docs.salad.com/container-engine/how-to-guides/imds/imds-reallocate), and [curl DNS-over-HTTPS](https://curl.se/libcurl/c/CURLOPT_DOH_URL.html).

Verification repeated on **7 September 2026**, using only the renamed `proxyrack.md` as the recovery input:

| Check | Measured result and scope |
|---|---|
| Exact extraction into an empty macOS-style directory | Six files extracted and hash-verified; Python ran in isolated mode without the existing project on its import path. The stale `proxyrack.proxyrack.md` filename was corrected. |
| Deployment and adoption flow | The extracted code used real curl against a local HTTP API fixture. It created exactly one `pr` group with ten replicas, preserved identity on re-run/adoption, and correctly sent merge PATCH updates and replacement-key synchronization. This fixture does not establish that a future account has sufficient credit/quota. |
| Recorder and accounting | A full observer cycle consumed fixture logs through HTTP, wrote SQLite, and served the recovery page. A 2 MB RX+TX reading, 1 MB credited value and $0.03 account balance remained distinct. An obsolete group's 18 MB was excluded. |
| Browser | The extracted page rendered the fixture data. With the fixture made stale it displayed zero live clients and a stale-feed notice. |
| Native process exit | In the pinned Linux image with network disabled and an intentionally failing fixture child, the supervisor requested fixture IMDS reallocation and exited 75. |
| Home connection timeout | The unchanged 60-second threshold fired in approximately 62 seconds including cleanup in the Linux fixture. |
| Intentional stop | The old external-clock line reproduced an incorrect reallocation during TERM. Using the Bash built-in clock fixed it: three consecutive initial reproductions then exited 0 with `operator_stop final=1`, without a reallocation request; the complete failure matrix was rerun afterward. |
| Registration resolver failure | The extracted function switched from a failed default-DNS fixture to a successful DoH fixture and accepted the matching device ID. TLS verification flags were unchanged. |
| Real Salad configuration, read only | The deployed group was `ssh1/default/pr`, display `PR`, version 6, ten replicas, US, batch, one CPU, 1024 MiB, restart always. The original embedded startup exactly matched it before the one-line shutdown correction. That correction is now the only worker difference. |
| External prerequisites, read only | The pinned image was present as Linux/amd64; the official native download URL returned HTTP 200 and the version endpoint returned 60. Availability and version can change later. The embedded Swift helper compiled successfully. |

The Linux tests exercised the real embedded Bash supervisor in the pinned image; the peer process and metadata/API responses were controlled fixtures, and loopback counters substituted for the absent `eth0` under `--network none`. They did not generate credited provider traffic. No new paid cloud group, credential mutation, or LaunchAgent installation was performed for these verification checks. A fresh cloud rebuild using the shutdown correction has **not** been performed as part of this document check; run step 7 after an actual rebuild. Identical future throughput or profit is not established by these tests.

## Embedded recovery source

The source below is intentionally complete. `native_network.py` is preserved as the actual storage file, including shared helper functions that PR does not call. `proxyrack.py` preserves the deployment/recorder source except for the one-line shutdown-clock correction described above. The only new recovery component is the read-only PR-only HTTP server; its page is adapted from the existing PR page. No production file is modified by creating this Markdown.

### `proxyrack.py`

<!-- recovery-file: proxyrack.py sha256: 4c7cc56c9c7593088ae639407bd000751342c02a796e541e8e8495f55bf54522 -->
```python
#!/usr/bin/env python3
"""Deploy and observe PR: one Salad group with ten replicas in SSH1."""
import argparse
import base64
from datetime import datetime, timedelta, timezone
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent
DATA = Path.home() / ".hg1/proxyrack"
HELPER = Path.home() / "Library/Application Support/Salad Bandwidth Dashboard/.runtime/keychain-store"
BASE = "https://api.salad.com/api/public/organizations/ssh1"
GROUPS = "/projects/default/containers"
IMAGE = "docker.io/proxyrack/pop@sha256:7de6719f37b31d5dd354f8cdd3ae601b4ed401832d0935ff460f968e0b6731bc"
sys.path.insert(0, str(ROOT.parent / "salad-bandwidth-stack"))
from dashboard.native_network import NetworkMinutes, parse_minute

STARTUP = r'''#!/bin/bash
set -u
umask 077
: "${PR_NAMESPACE:?}" "${PR_API_KEY:?}" "${SALAD_INSTANCE_ID:?}" "${SALAD_MACHINE_ID:?}"
pr_key=$PR_API_KEY; unset PR_API_KEY
[[ "$pr_key" =~ ^[A-Za-z0-9]+$ ]] || exit 1
UUID=$(printf '%s:%s' "$PR_NAMESPACE" "$SALAD_INSTANCE_ID" | sha256sum | cut -c1-64 | tr a-f A-F)
PR_WORKER="PR-${SALAD_INSTANCE_ID:0:8}"
pr_pid=""; pr_state=starting; pr_error=none; pr_registered=0
record_minute() {
  [[ -n "${pr_started:-}" ]] || return
  local now rx tx state=$pr_state error=$pr_error
  if [[ "$state" == running && "$pr_registered" == 0 ]]; then
    state=starting; error=registration_pending
  fi
  printf -v now '%(%s)T' -1; now="${now}000"
  read -r rx </sys/class/net/eth0/statistics/rx_bytes || return
  read -r tx </sys/class/net/eth0/statistics/tx_bytes || return
  printf 'PR_MINUTE_V1 worker=%s device=%s instance=%s machine=%s observer=%s seq=%s start_ms=%s end_ms=%s rx=%s tx=%s total_rx=%s total_tx=%s state=%s error=%s final=%s registered=%s\n' \
    "$PR_WORKER" "$UUID" "$SALAD_INSTANCE_ID" "$SALAD_MACHINE_ID" "$pr_started" "$pr_seq" "$pr_previous_ms" "$now" \
    "$((rx-pr_previous_rx))" "$((tx-pr_previous_tx))" "$((rx-pr_base_rx))" "$((tx-pr_base_tx))" "$state" "$error" "$1" "$pr_registered"
  pr_previous_rx=$rx; pr_previous_tx=$tx; pr_previous_ms=$now
  pr_seq=$((pr_seq+1)); pr_recorded=$SECONDS
}
stop_client() {
  exec 4>&-
  if [[ -n "$pr_pid" ]]; then
    kill "$pr_pid" 2>/dev/null || true
    sleep 1
    kill -KILL "$pr_pid" 2>/dev/null || true
    wait "$pr_pid" 2>/dev/null || true
  fi
  pr_pid=""
  exec 3<&-
}
reallocate() {
  stop_client
  pr_state=reallocating
  record_minute 1
  printf 'PR_SELF_REALLOCATE worker=%s instance=%s machine=%s reason=%s\n' "$PR_WORKER" "$SALAD_INSTANCE_ID" "$SALAD_MACHINE_ID" "$1"
  for attempt in 1 2 3; do
    code=$(curl --noproxy '*' -sS --connect-timeout 3 --max-time 10 -o /dev/null -w '%{http_code}' -X POST http://169.254.169.254/v1/reallocate -H 'Metadata: true' -H 'Content-Type: application/json' --data "{\"reason\":\"$1\"}") || code=000
    printf 'PR_SELF_IMDS_RESPONSE worker=%s instance=%s http=%s\n' "$PR_WORKER" "$SALAD_INSTANCE_ID" "$code"
    [[ "$code" == 200 || "$code" == 204 ]] && break
    sleep 5
  done
  exit 75
}
register_device() {
  local endpoint body code resolver
  local -a dns_args
  for endpoint in device/add device/status; do
    body="{\"device_id\":\"$UUID\",\"device_name\":\"$PR_WORKER\"}"
    for resolver in default doh; do
      dns_args=()
      [[ "$resolver" == doh ]] && dns_args=(--doh-url https://1.1.1.1/dns-query)
      code=$(printf 'header = "Api-Key: %s"\nheader = "Content-Type: application/json"\nheader = "Accept: application/json"\n' "$pr_key" | curl -sS --config - "${dns_args[@]}" --connect-timeout 5 --max-time 15 -X POST "https://peer.proxyrack.com/api/$endpoint" --data "$body" -o /tmp/pr-registration.json -w '%{http_code}' 2>/tmp/pr-registration.err) || code=000
      if [[ "$resolver" == default && "$code" == 000 ]] && grep -qiE 'Could not resolve host|Resolving timed out' /tmp/pr-registration.err; then
        printf 'PR_DNS_FALLBACK worker=%s instance=%s resolver=https\n' "$PR_WORKER" "$SALAD_INSTANCE_ID"
        continue
      fi
      cat /tmp/pr-registration.err >&2
      break
    done
    if [[ "$code" == 200 ]] && node -e 'const r=require("/tmp/pr-registration.json");process.exit(r.status==="success"&&r.data&&r.data.device_id===process.argv[1]?0:1)' "$UUID" 2>/dev/null; then
      pr_registered=1
      printf 'PR_REGISTERED worker=%s device=%s instance=%s\n' "$PR_WORKER" "$UUID" "$SALAD_INSTANCE_ID"
      rm -f /tmp/pr-registration.json /tmp/pr-registration.err
      pr_key=""
      return
    fi
    printf 'PR_REGISTRATION_RETRY worker=%s endpoint=%s http=%s\n' "$PR_WORKER" "$endpoint" "$code"
    [[ "$endpoint" == device/add && "$code" == 400 ]] && node -e 'const r=require("/tmp/pr-registration.json");process.exit(JSON.stringify(r).includes("already been taken")?0:1)' 2>/dev/null || break
  done
  rm -f /tmp/pr-registration.json /tmp/pr-registration.err
}
trap 'pr_state=exited; pr_error=operator_stop; stop_client; record_minute 1; exit 0' TERM INT
if ! curl -fsS --retry 2 --retry-delay 3 --connect-timeout 8 --max-time 45 https://app-updates.sock.sh/peerclient/go/client -o /app/pr-client; then
  pr_error=download_failed; reallocate 'PR native client download failed after retries'
fi
version=$(curl -fsS --retry 2 --retry-delay 3 --connect-timeout 8 --max-time 20 https://app-updates.sock.sh/peerclient/go/version.txt) || reallocate 'PR version download failed after retries'
[[ "$version" =~ ^[0-9]+$ ]] || reallocate 'PR returned an invalid client version'
chmod 700 /app/pr-client
pr_started="$(date +%s)000"
read -r pr_base_rx </sys/class/net/eth0/statistics/rx_bytes
read -r pr_base_tx </sys/class/net/eth0/statistics/tx_bytes
pr_previous_rx=$pr_base_rx; pr_previous_tx=$pr_base_tx; pr_previous_ms=$pr_started; pr_seq=0; pr_recorded=$SECONDS
record_minute 0
start_client() {
  rm -f /tmp/pr-input; mkfifo /tmp/pr-input
  exec 3< <(exec /app/pr-client --homeIp point-of-presence.sock.sh --homePort 443 --id "$UUID" --version "$version" --clientKey proxyrack-pop-client --clientType PoP --ppid $$ --osType Linux --osRelease "$(uname -r)" --osArch x64 </tmp/pr-input 2>&1)
  pr_pid=$!; exec 4>/tmp/pr-input
  pr_state=starting; pr_connect_since=$SECONDS
  printf 'PR_SELF_START worker=%s device=%s instance=%s machine=%s client_version=%s native=1\n' "$PR_WORKER" "$UUID" "$SALAD_INSTANCE_ID" "$SALAD_MACHINE_ID" "$version"
}
pr_register_delay=60; pr_register_at=$((SECONDS+60+RANDOM%120))
start_client
while :; do
  if IFS= read -r -t 1 line <&3; then
    printf 'PR_LOG worker=%s instance=%s %s\n' "$PR_WORKER" "$SALAD_INSTANCE_ID" "$line"
    case "$line" in
      *'connected to home:'*) pr_state=running; pr_error=none; pr_connect_since=-1 ;;
      *'connecting to home:'*)
        pr_state=starting; pr_error=connecting
        if (( pr_connect_since < 0 )); then pr_connect_since=$SECONDS; fi ;;
    esac
  elif ! kill -0 "$pr_pid" 2>/dev/null; then
    pr_state=exited; pr_error=client_exited
    reallocate 'Proxyrack native client exited'
  fi
  if (( pr_registered == 0 && SECONDS >= pr_register_at )); then
    register_device
    pr_register_at=$((SECONDS+pr_register_delay+RANDOM%90))
    (( pr_register_delay < 600 )) && pr_register_delay=$((pr_register_delay*2))
    (( pr_register_delay > 600 )) && pr_register_delay=600
  fi
  if (( SECONDS-pr_recorded >= 60 )); then record_minute 0; fi
  if (( pr_connect_since >= 0 && SECONDS-pr_connect_since >= 60 )); then
    pr_state=error; pr_error=connection_timeout; reallocate 'Proxyrack home connection unavailable for 60 seconds'
  fi
done
'''


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2))
    os.replace(temp, path)


def salad_api():
    key = subprocess.check_output([str(HELPER), "--read", "--service", "salad-bandwidth-api",
                                   "--account", getpass.getuser()], text=True).strip()

    def request(path, method="GET", body=None):
        if not (path == GROUPS or path.startswith(GROUPS + "/") or path == "/log-entries"):
            raise ValueError("Outside the requested SSH1 deployment")
        media = "application/merge-patch+json" if method == "PATCH" else "application/json"
        config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\nheader = " + json.dumps("Content-Type: " + media) + "\n"
        if body is not None:
            config += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
        result = subprocess.run(["curl", "-sS", "--max-time", "25", "--config", "-", "--request", method,
                                 "--write-out", "\n%{http_code}", BASE + path], input=config, text=True,
                                capture_output=True, timeout=30)
        raw, code = result.stdout.rsplit("\n", 1)
        if result.returncode or not 200 <= int(code) < 300:
            raise RuntimeError("Salad " + method + " " + path + " returned HTTP " + code)
        return json.loads(raw) if raw.strip() else {}
    return request


def peer_api():
    key = subprocess.check_output([str(HELPER), "--read", "--service", "proxyrack-peer-api",
                                   "--account", getpass.getuser()], text=True, stderr=subprocess.DEVNULL).strip()

    def request(method, payload=None):
        if method not in ("balance", "bandwidth", "device/status"):
            raise ValueError("Unsupported ProxyRack operation")
        config = "header = " + json.dumps("Api-Key: " + key) + '\nheader = "Content-Type: application/json"\nheader = "Accept: application/json"\n'
        config += "data-binary = " + json.dumps(json.dumps(payload or {})) + "\n"
        result = subprocess.run(["curl", "-sS", "--max-time", "20", "--config", "-", "--request", "POST",
                                 "--write-out", "\n%{http_code}", "https://peer.proxyrack.com/api/" + method],
                                input=config, text=True, capture_output=True, timeout=25)
        raw, code = result.stdout.rsplit("\n", 1)
        if result.returncode or code not in ("200", "400"):
            try:
                detail = str(json.loads(raw).get("error", "")).replace(key, "[redacted]")[:160]
            except (ValueError, AttributeError):
                detail = ""
            raise RuntimeError("ProxyRack " + method + " returned HTTP " + code + (": " + detail if detail else ""))
        try:
            return json.loads(raw)
        except ValueError:
            raise RuntimeError("ProxyRack returned a non-JSON response") from None
    return request


def configuration():
    return json.loads((DATA / "deployment.json").read_text())


def command():
    encoded = base64.b64encode(STARTUP.encode()).decode()
    args = ["/bin/bash", "-c", 'umask 077; printf "%s" "$@" | base64 -d > /tmp/pr-start.sh; exec /bin/bash /tmp/pr-start.sh',
            "pr-start", *[encoded[i:i+900] for i in range(0, len(encoded), 900)]]
    if len(args) > 100 or any(not value or len(value) > 1000 for value in args):
        raise ValueError("Startup command exceeds Salad command limits")
    return args


def deploy():
    api = salad_api()
    config = configuration()
    if "workers" in config:
        old = config
        for worker in old["workers"]:
            group = api(GROUPS + "/" + worker["name"])
            if group["id"] != worker["group_id"] or group["current_state"]["status"] != "stopped":
                raise RuntimeError("Stop the previous deployment before replacing it")
        config = {"organization": "ssh1", "project": "default", "name": "pr", "replicas": 10,
                  "created_at": datetime.now(timezone.utc).isoformat(), "namespace": secrets.token_hex(16),
                  "image": IMAGE, "replaced_groups": old["workers"]}
        save(DATA / "deployment.json", config)
    key = subprocess.check_output([str(HELPER), "--read", "--service", "proxyrack-peer-api",
                                   "--account", getpass.getuser()], text=True).strip()
    existing = {g["name"]: g for g in api(GROUPS).get("items", [])}
    if "pr" in existing:
        group = api(GROUPS + "/pr")
        if group["container"]["environment_variables"].get("PR_NAMESPACE") != config["namespace"]:
            raise RuntimeError("Existing PR group has a different deployment identity")
        if group["container"]["command"] != command():
            raise RuntimeError("Use update to change an existing PR deployment")
    else:
        payload = {"name": "pr", "display_name": "PR", "replicas": 10,
                   "autostart_policy": True, "restart_policy": "always", "country_codes": ["us"],
                   "container": {"image": IMAGE, "priority": "batch", "resources": {"cpu": 1, "memory": 1024},
                                 "command": command(), "environment_variables": {
                                     "PR_NAMESPACE": config["namespace"], "PR_API_KEY": key}}}
        group = api(GROUPS, "POST", payload)
    config["group_id"] = group["id"]
    save(DATA / "deployment.json", config)
    for _ in range(30):
        group = api(GROUPS + "/pr")
        if group["current_state"]["status"] != "preparing":
            break
        time.sleep(2)
    if group["current_state"]["status"] == "stopped":
        api(GROUPS + "/pr/start", "POST")
    elif group["current_state"]["status"] not in ("deploying", "running"):
        raise RuntimeError("PR is not ready to start: " + group["current_state"]["status"])
    print("PR requested: one group, ten replicas, US, 1 CPU / 1 GB each", flush=True)


def inspect():
    api = salad_api()
    config = configuration()
    group = api(GROUPS + "/pr")
    if group["id"] != config["group_id"]:
        raise RuntimeError("Deployment identity changed")
    instances = api(GROUPS + "/pr/instances").get("instances", [])
    print("PR", group["current_state"], [{k:i.get(k) for k in ("id", "machine_id", "state", "ready")} for i in instances])


def update_startup():
    api = salad_api()
    config = configuration()
    group = api(GROUPS + "/pr")
    if group["id"] != config["group_id"]:
        raise RuntimeError("Deployment identity changed")
    if group["container"]["command"] != command():
        api(GROUPS + "/pr", "PATCH", {"container": {"command": command()}})
    after = api(GROUPS + "/pr")
    if after["container"]["command"] != command():
        raise RuntimeError("Startup command was not applied")
    print("PR startup verified", flush=True)


def device_id(config, instance):
    return hashlib.sha256((config["namespace"] + ":" + instance).encode()).hexdigest().upper()


def parsed_time(value):
    value = re.sub(r"\.(\d+)(?=Z$|[+-]\d\d:\d\d$)",
                   lambda m: "." + (m[1] + "000000")[:6], value)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def provider_loop(config, members, meter, stopped):
    path = DATA / "provider.json"
    state = json.loads(path.read_text()) if path.exists() else {}
    if state.get("group_id") != config["group_id"]:
        state = {"group_id": config["group_id"], "workers": {}}
    api = peer_api()
    while not stopped.is_set():
        current = {w["device_id"]: w for w in members.get("workers", [])}
        for instance in meter.latest(config["group_id"]):
            state["workers"].setdefault(device_id(config, instance), {})
        now, jobs = int(time.time() * 1000), []
        for device, row in state["workers"].items():
            live = current.get(device, {})
            connected = live.get("fresh") and live.get("client_state") == "running"
            if connected:
                due = row.get("status_attempted_ms", 0) + (120_000 if row.get("error") else 1_800_000)
                if due <= now:
                    jobs.append((due, "device/status", device))
            interval = 300_000 if device in current else 3_600_000
            due = row.get("bandwidth_attempted_ms", 0) + interval
            if due <= now:
                jobs.append((due, "bandwidth", device))
        due = state.get("balance_attempted_ms", 0) + (120_000 if state.get("balance_error") else 600_000)
        if due <= now:
            jobs.append((due, "balance", ""))
        if not jobs:
            stopped.wait(5)
            continue
        _, method, device = min(jobs)
        row = state if method == "balance" else state["workers"][device]
        kind = "status" if method == "device/status" else method
        row[kind + "_attempted_ms"] = now
        payload = {"device_id": device} if device else {}
        if method == "bandwidth":
            payload.update(date_start=(parsed_time(config["created_at"]).date() - timedelta(days=1)).isoformat(),
                           date_end=datetime.now(timezone.utc).date().isoformat())
        try:
            result = api(method, payload)
            if result.get("status") != "success":
                raise RuntimeError(result.get("error", "PR has not returned this reading"))
            data, checked = result["data"], int(time.time() * 1000)
            if method == "device/status":
                row.update(status=data.get("status", "Not reported"), checked_ms=checked, error=None)
            elif method == "bandwidth":
                days = data.get("bandwidth", {})
                if not isinstance(days, dict) or not all(isinstance(v, (int, float)) and v >= 0 for v in days.values()):
                    raise ValueError("PR returned invalid bandwidth values")
                row.update(credited_mb=sum(days.values()) * 1000, bandwidth_state=data.get("state"),
                           bandwidth_checked_ms=checked, bandwidth_error=None)
            else:
                row.update(balance=data.get("balance"), balance_checked_ms=checked, balance_error=None)
        except Exception as error:
            row["error" if method == "device/status" else kind + "_error"] = str(error)[:200]
        save(path, state)
        # The measured account limit is five requests/minute; leave capacity for replica registration.
        stopped.wait(20)


def make_view(meter, config, inventory, cloud_error=None):
    now = int(time.time() * 1000)
    provider_path = DATA / "provider.json"
    provider = json.loads(provider_path.read_text()) if provider_path.exists() else {}
    if provider.get("group_id") != config["group_id"]:
        provider = {}
    with meter.lock:
        rows = [dict(row) for row in meter.db.execute(
            "SELECT * FROM minutes WHERE group_id=? ORDER BY end_ms,observer,seq", (config["group_id"],))]
    totals, timeline, total = {}, [], 0
    for row in rows:
        if not row["valid"]:
            continue
        run = (row["instance"], row["observer"])
        amount = row["total_rx"] + row["total_tx"]
        previous = totals.get(run, 0)
        if amount < previous:
            continue
        total += amount - previous
        totals[run] = amount
        if timeline and timeline[-1]["time_ms"] == row["end_ms"]:
            timeline[-1]["mb"] = total / 1e6
        else:
            timeline.append({"time_ms": row["end_ms"], "mb": total / 1e6})
    workers = []
    for member in inventory.get("instances", []):
        machine_rows = [r for r in rows if r["machine"] == member["machine_id"] and r["instance"] == member["id"]]
        last = max(machine_rows, key=lambda r:(r["observer"], r["seq"]), default=None)
        instance = member["id"]
        device = device_id(config, instance)
        age = now - last["end_ms"] if last else None
        fresh = bool(not cloud_error and last and last["valid"] and -10_000 <= age <= 150_000 and not last["final"])
        status_fresh = bool(not cloud_error and last and -10_000 <= age <= 150_000)
        seconds = (last["end_ms"] - last["start_ms"]) / 1000 if last else None
        amount = (last["rx"] + last["tx"]) / 1e6 if last and last["valid"] and last["seq"] > 0 else None
        prov = provider.get("workers", {}).get(device, {})
        p_age = now - prov["checked_ms"] if prov.get("checked_ms") else None
        raw_status = prov.get("status", "Waiting for registration")
        online = p_age is not None and p_age < 240_000 and raw_status.startswith("Online") and not prov.get("error")
        if cloud_error:
            state = "Status unavailable"
        elif inventory.get("status") == "stopped":
            state = "Stopped"
        elif member["state"] != "running":
            state = member["state"].capitalize()
        elif status_fresh and last["state"] == "reallocating":
            state = "Reallocating"
        elif fresh:
            state = "Running" if last["state"] == "running" else "Recovering" if last["state"] in ("error", "exited") else "Starting client"
        else:
            state = "Checking client"
        workers.append({"name": "PR-" + instance[:8], "instance": instance, "device_id": device,
            "salad_instance": member["id"], "machine": member["machine_id"], "salad_state": member["state"], "status": state,
            "client_state": last["state"] if status_fresh else None,
            "provider_status": raw_status, "provider_online": bool(online), "provider_age_ms": p_age,
            "provider_error": prov.get("error"), "credited_mb": prov.get("credited_mb"),
            "bandwidth_state": prov.get("bandwidth_error") or prov.get("bandwidth_state"),
            "bandwidth_checked_ms": prov.get("bandwidth_checked_ms"),
            "network_mb": sum(v for k,v in totals.items() if k[0] == instance) / 1e6 if last else None,
            "interval_mb": amount, "interval_seconds": seconds,
            "mb_per_minute": amount * 60 / seconds if amount is not None and seconds else None,
            "sample_age_ms": age, "fresh": fresh, "last_sample_ms": last["end_ms"] if last else None,
            "client_error": last["error"] if last and last["error"] != "none" else None,
            "samples": sum(r["seq"] > 0 for r in machine_rows),
            "group_url": "https://portal.salad.com/organizations/ssh1/projects/default/containers/pr/instances/" + member["id"]})
    credited = [p["credited_mb"] for p in provider.get("workers", {}).values() if p.get("credited_mb") is not None]
    return {"generated_ms": now, "organization": "SSH1", "group": "PR", "requested": config["replicas"],
            "group_id": config["group_id"], "workers": workers,
            "reporting": sum(w["fresh"] for w in workers), "online": sum(w["provider_online"] for w in workers),
            "network_mb": total / 1e6, "credited_mb": sum(credited) if credited else None,
            "credited_devices": sum(w["credited_mb"] is not None for w in workers),
            "balance": provider.get("balance"), "balance_checked_ms": provider.get("balance_checked_ms"),
            "timeline": timeline, "cloud_error": cloud_error, "started_at": config["created_at"]}


def observe():
    config = configuration()
    lock = (DATA / "observer.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    meter = NetworkMinutes(DATA / "traffic.sqlite3")
    api = salad_api()
    stopped, members = threading.Event(), {}
    threading.Thread(target=provider_loop, args=(config, members, meter, stopped), daemon=True).start()
    cursor = parsed_time(config["created_at"])
    state_path = DATA / "cursor.json"
    if state_path.exists():
        saved = json.loads(state_path.read_text())
        if saved.get("group_id") == config["group_id"]:
            cursor = parsed_time(saved["cursor"])
    inventory = {}
    try:
        while True:
            began = time.monotonic()
            error = None
            try:
                group = api(GROUPS + "/pr")
                if group["id"] != config["group_id"]:
                    raise RuntimeError("Deployment identity changed")
                inventory = {"status": group["current_state"]["status"],
                             "instances": api(GROUPS + "/pr/instances").get("instances", [])}
                end, start = datetime.now(timezone.utc), cursor - timedelta(minutes=10)
                for page in range(30):
                    entries = api("/log-entries", "POST", {
                        "query": 'resource.type = "container" and resource.labels.container_group_name = "pr" and text_log startswith "PR_MINUTE_V1"',
                        "start_time": start.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                        "end_time": end.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                        "page_size": 100, "sort_order": "asc"}).get("items", [])
                    records = []
                    for item in entries:
                        line = item.get("text_log", "")
                        try:
                            values = dict(part.split("=", 1) for part in line.split()[1:])
                            if values["device"] != device_id(config, values["instance"]):
                                continue
                            converted = dict(item, text_log=line.replace("PR_MINUTE_V1 ", "PS_MINUTE_V1 ", 1) + " ip=-")
                            record = parse_minute(converted, config["group_id"])
                            if record and record["end_ms"] <= int(time.time() * 1000) + 30_000:
                                record["record_bytes"] = len(line.encode()) + 1
                                records.append(record)
                        except (ValueError, KeyError, TypeError):
                            continue
                    meter.ingest(records)
                    times = [parsed_time(i["time"]) for i in entries if i.get("time")]
                    if times:
                        following = max(times)
                        cursor = max(cursor, following)
                    if len(entries) < 100 or not times:
                        break
                    following = following.replace(microsecond=following.microsecond//1000*1000)
                    if following <= start:
                        raise RuntimeError("PR log pagination made no progress")
                    start = following
                else:
                    raise RuntimeError("PR log backlog is still being collected")
                save(state_path, {"group_id": config["group_id"], "cursor": cursor.isoformat()})
            except Exception as caught:
                error = str(caught)[:200]
            view = make_view(meter, config, inventory, error)
            members["workers"] = view["workers"]
            save(DATA / "view.json", view)
            time.sleep(max(1, 15 - (time.monotonic() - began)))
    finally:
        stopped.set()


def main():
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["deploy", "status", "observe", "update"])
    args = parser.parse_args()
    if args.action == "deploy":
        deploy()
    elif args.action == "status":
        inspect()
    elif args.action == "update":
        update_startup()
    else:
        observe()


if __name__ == "__main__":
    main()
```
<!-- end-recovery-file -->

### `dashboard/__init__.py`

<!-- recovery-file: dashboard/__init__.py sha256: 0a50e596009c0f7980394b4195bc27e01d71052ba4cfd89c3d8a2edae158e40a -->
```python
"""Local PR recovery support."""
```
<!-- end-recovery-file -->

### `dashboard/native_network.py`

<!-- recovery-file: dashboard/native_network.py sha256: 7aebbb480bab2244e47d768994e8530bec1c529bc819e7878875c6b99e2f8a7d -->
```python
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
```
<!-- end-recovery-file -->

### `scripts/keychain-store.swift`

<!-- recovery-file: scripts/keychain-store.swift sha256: 490eadaf1afb87a0f64bf6248254ccc48ac1171af9e2fc4c796c74c12c5ca045 -->
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
<!-- end-recovery-file -->

### `dashboard/pr_recovery_server.py`

<!-- recovery-file: dashboard/pr_recovery_server.py sha256: 71c0cbcaf8b8a04c889294e3c78724cea86c7a0535eea10de00b969bbe3acd1d -->
```python
#!/usr/bin/env python3
"""PR-only recovery page; reads local files and never calls account APIs."""
import argparse
import json
from pathlib import Path
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from dashboard.native_network import saved_minutes

DATA = Path.home() / ".hg1/proxyrack"
PAGE = Path(__file__).parent / "static/proxyrack.html"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urlsplit(self.path).path
        try:
            if route in ("/", "/proxyrack", "/proxyrack.html"):
                body, media, status = PAGE.read_bytes(), "text/html; charset=utf-8", 200
            elif route == "/api/proxyrack":
                result = json.loads((DATA / "view.json").read_text())
                database = DATA / "traffic.sqlite3"
                group_id = result["group_id"]
                result["minutes"] = saved_minutes(database, group_id=group_id)
                if database.exists():
                    with closing(sqlite3.connect("file:" + str(database) + "?mode=ro", uri=True)) as db:
                        amount = db.execute(
                            "SELECT SUM(rx+tx) FROM minutes WHERE group_id=? AND valid=1 AND seq>0",
                            (group_id,)).fetchone()[0]
                    result["total_recorded_mb"] = amount / 1e6 if amount is not None else None
                body, media, status = json.dumps(result).encode(), "application/json", 200
            else:
                body, media, status = b"Not found", "text/plain", 404
        except (OSError, ValueError, KeyError, sqlite3.Error):
            body, media, status = b'{"error":"PR recorder data is not available yet"}', "application/json", 503
        self.send_response(status)
        self.send_header("Content-Type", media)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
```
<!-- end-recovery-file -->

### `dashboard/static/proxyrack.html`

<!-- recovery-file: dashboard/static/proxyrack.html sha256: a4ced44026b19ef8f72bc9348258f38550c3a30e7828dc2beaafbd56927aa1b2 -->
```html
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PR — SSH1</title><style>
body{font:15px system-ui,sans-serif;color:#17212a;background:#fff;margin:0;padding:24px}main{max-width:1450px;margin:auto}h1{font-size:24px;margin:0 0 8px}nav{display:flex;gap:22px;margin:20px 0}a{color:#165b9a}p{line-height:1.5}.muted{color:#5e6a75;font-size:13px}.error{color:#a22121}.summary{font-size:17px;font-variant-numeric:tabular-nums}.chart{border:1px solid #ddd;padding:12px;margin:20px 0}canvas{width:100%;height:280px;display:block}select{font:inherit;padding:5px}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{border-bottom:1px solid #e2e6ea;padding:12px 8px;text-align:right;white-space:nowrap}th{font-size:12px;color:#596774}th:first-child,td:first-child,th:nth-child(2),td:nth-child(2),th:nth-child(3),td:nth-child(3){text-align:left}.scroll{overflow-x:auto}.stale{color:#936000}.details{font-size:12px;color:#687580;max-width:260px;white-space:normal}footer{margin-top:22px;font-size:13px;color:#596774}@media(max-width:650px){body{padding:14px}h1{font-size:21px}.summary{font-size:15px}canvas{height:230px}}
</style></head><body><main>
<h1>PR — SSH1</h1><div class="muted" id="connection">Loading recorder…</div>
<nav aria-label="PR"><strong>PR</strong><a href="https://portal.salad.com/organizations/ssh1/projects/default/containers/pr">Salad group</a><a href="https://peer.proxyrack.com/devices">Provider devices</a></nav>
<p class="summary" id="summary">Waiting for the first recorded reading.</p><p id="notice" class="error"></p>
<div class="chart"><label>Recorded network traffic <select id="range"><option value="hour">Last hour</option><option value="all">Since test started</option></select></label><canvas id="chart" role="img" aria-label="Cumulative recorded ProxyRack network traffic in megabytes"></canvas><div class="muted">Cumulative RX + TX reported by the containers. Measured after the client download; includes connection and registration traffic. Credited bandwidth is separate.</div></div>
<div class="scroll"><table><thead><tr><th>Worker</th><th>Client / Salad</th><th>PR / IP</th><th>Network MB</th><th>Last interval MB</th><th>Seconds</th><th>MB/min</th><th>Credited MB</th><th>Last sample</th></tr></thead><tbody id="workers"></tbody></table></div>
<p class="muted" id="providerNote"></p><footer>Each container requests Salad reallocation after client failure or a sustained home connection timeout. This Mac only records and displays readings. Minute records survive replacement; gaps are not filled with invented traffic.</footer>
</main><script>
const $=id=>document.getElementById(id);let data=null,busy=false,failed=false;
const number=(v,d=3)=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString(undefined,{maximumFractionDigits:d}):'—';
const age=v=>typeof v==='number'&&v>=0?(v<60000?Math.floor(v/1000)+'s':Math.floor(v/60000)+'m'):'—';
const time=v=>new Date(v).toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit'});
function plot(){
 const canvas=$('chart'),ratio=window.devicePixelRatio||1,w=canvas.clientWidth,h=canvas.clientHeight;
 canvas.width=w*ratio;canvas.height=h*ratio;const c=canvas.getContext('2d');c.scale(ratio,ratio);c.clearRect(0,0,w,h);
 const end=Date.now(),all=data?.timeline||[],start=$('range').value==='hour'?end-3600000:(all[0]?.time_ms||end-60000);
 let points=all.filter(p=>p.time_ms>=start);const before=all.filter(p=>p.time_ms<start).at(-1);if(before)points.unshift({...before,time_ms:start});
 const stride=Math.max(1,Math.ceil(points.length/1500));points=points.filter((p,i)=>i%stride===0||i===points.length-1);
 const left=65,right=w-15,top=20,bottom=h-36,min=points.length?Math.min(...points.map(p=>p.mb)):0,max=points.length?Math.max(...points.map(p=>p.mb)):0,span=Math.max(max-min,0.001);
 c.font='12px system-ui';c.textAlign='right';for(let i=0;i<=4;i++){const y=bottom-(bottom-top)*i/4;c.strokeStyle='#e4e8eb';c.beginPath();c.moveTo(left,y);c.lineTo(right,y);c.stroke();c.fillStyle='#586570';c.fillText(number(min+span*i/4,3),left-8,y+4);}
 c.textAlign='left';c.fillText('MB',12,14);c.fillText(time(start),left,h-9);c.textAlign='right';c.fillText(time(end),right,h-9);
 if(!points.length){c.textAlign='center';c.fillText('First minute has not been recorded yet.',w/2,h/2);return;}
 const x=p=>left+(p.time_ms-start)/Math.max(1,end-start)*(right-left),y=p=>bottom-(p.mb-min)/span*(bottom-top);
 c.strokeStyle='#176b9c';c.lineWidth=2;c.beginPath();points.forEach((p,i)=>{if(i){c.lineTo(x(p),y(points[i-1]));c.lineTo(x(p),y(p));}else c.moveTo(x(p),y(p));});c.stroke();
}
function render(){if(!data)return;const delay=Math.max(0,Date.now()-data.generated_ms),live=!failed&&delay<60000&&!data.cloud_error;
 const reporting=data.workers.filter(w=>w.fresh&&w.last_sample_ms&&Date.now()-w.last_sample_ms<150000&&live).length;
 const connected=data.workers.filter(w=>live&&w.fresh&&w.client_state==='running'&&!w.client_error&&w.salad_state==='running'&&Date.now()-w.last_sample_ms<150000).length;
 $('connection').textContent=(live?'Recorder updating':'Recorder stale')+' · last update '+age(delay)+' ago';$('connection').className=live?'muted':'error';
 $('summary').textContent=connected+'/'+data.requested+' registered and connected · '+reporting+'/'+data.requested+' reporting traffic · Network '+number(data.network_mb)+' MB · Cached credited '+number(data.credited_mb)+' MB · Account balance '+(data.balance||'—');
 $('notice').textContent=data.cloud_error||(!live?'The recorder has stopped updating. Values below are the last observations.':'');
 $('workers').replaceChildren();for(const w of data.workers){const tr=document.createElement('tr'),td=document.createElement('td'),a=document.createElement('a');a.textContent=w.name.replace('proxyrack-','PR ');a.href=w.group_url;a.target='_blank';a.rel='noopener noreferrer';td.append(a);tr.append(td);
  const pFresh=w.provider_age_ms!==null&&w.provider_age_ms+delay<240000,rawFresh=w.fresh&&w.last_sample_ms&&Date.now()-w.last_sample_ms<150000&&live;
  const values=[(live?'':'Last: ')+(w.status||w.client_state||'Unknown')+' / '+w.salad_state,(pFresh?'':'Last: ')+w.provider_status,number(w.network_mb),number(w.interval_mb),number(w.interval_seconds,1),number(w.mb_per_minute),number(w.credited_mb),age(w.sample_age_ms===null?null:w.sample_age_ms+delay)];
  values.forEach((v,i)=>{const cell=document.createElement('td');cell.textContent=v;if((i>=2&&i<=5)&&!rawFresh)cell.className='stale';if(i===1&&(w.client_error||w.provider_error||!pFresh)){const note=document.createElement('div');note.className='details';note.textContent=w.client_error||w.provider_error||'Provider status is stale';cell.append(note);}if(i===6){const note=document.createElement('div');note.className='details';note.textContent=w.bandwidth_state||'Provider reading pending';cell.append(note);}tr.append(cell);});$('workers').append(tr);}
 $('providerNote').textContent='Cached credited bandwidth includes replaced replicas; readings are available for '+data.credited_devices+'/'+data.requested+' current devices. RX + TX counts both legs of relayed traffic and includes overhead. It is not credited bandwidth or earnings. Account balance covers the whole account. Provider status is polled slowly to respect its API limit; registered client logs determine connection status.';plot();
}
async function refresh(){if(busy)return;busy=true;try{const r=await fetch('/api/proxyrack',{cache:'no-store'});if(!r.ok)throw Error();data=await r.json();failed=false;render();}catch(e){failed=true;$('connection').textContent='Cannot reach the ProxyRack recorder';$('connection').className='error';if(data)render();}finally{busy=false;}}
$('range').addEventListener('change',plot);window.addEventListener('resize',plot);setInterval(refresh,3000);refresh();
</script></body></html>
```
<!-- end-recovery-file -->

