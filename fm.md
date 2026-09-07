# bandwidth reel — EarnFM (EF) complete rebuild

This file is the recovery package for the EarnFM service, not a reference to an agent's memory. Save a copy of **this file itself outside this Desktop**. It embeds the cloud startup program, recorder, page, stylesheet, Keychain helper source, configuration, checksums, and recovery commands. None of the original project files or chats is needed to extract them.

**Scope:** recreate the EarnFM portion: ten Salad replicas in SSH3, the deployed recovery policy, byte recording, EarnFM credit readings, and an EF page at `http://127.0.0.1:8787/` and `/ef`. The existing multi-protocol dashboard can consume the same `/api/earnfm` data. Honeygain, PacketStream, RP, PR, and TM are different services and are not recreated by this EarnFM-only package. The fallback HTTP server below restores the original EF page without requiring those projects.

**What cannot be manufactured from documentation:** owned Salad/EarnFM accounts, their current credentials and credit balance, the vendor's container image if its registry disappears, and historical traffic whose database/backups have been destroyed. The file includes the steps to obtain credentials again and pins the image exactly. It recreates the software and settings; it cannot promise the same physical IPs, customer traffic, income, or an identical old provider account. Secret values are deliberately not embedded. The image-backup and database-backup steps below cover those remaining recovery inputs.

## 1. Authoritative version and configuration

Captured on **2026-09-07**, by reading the Salad API and the installed local files. **Cloud version 8 is authoritative.** The old local `target.json` still said version 6 and had an outdated script hash; its contents are preserved only under `historical-record.json` for diagnosis. Do not deploy from that old version number. The embedded cloud program was decoded from the actual base64 command and matched the current source file byte for byte.

| Setting | Captured value |
|---|---|
| Service / display name | EarnFM / **EF** |
| Salad organization slug | `ssh3` (portal display SSH3) |
| Salad project slug | `default` |
| Container group slug | `earnfm-us` |
| Existing group ID | `90078bc1-4410-46cd-8411-6ebb8968eec2` — a recreated group gets a new ID |
| Desired replicas | **10**, not one |
| CPU / memory per replica | 1 CPU / 1024 MiB, 64 MiB shared memory; no GPU |
| Priority | `batch`, shown as Lowest |
| Requested country | `us` |
| Restart policy | `always` |
| Autostart policy | `false`; create first, then call the explicit start endpoint |
| Image cache | enabled |
| Image index digest | `docker.io/earnfm/earnfm-client@sha256:99a9feaa3dfab9e858012994fa1f922523f41b098e6b1cd9c9e9fca9286c3843` |
| Resolved AMD64 digest | `sha256:743a3118986ec1a794af8fc3c3bbcb5562797b269c1745345f326972d8792b56` |
| Entrypoint inside image | `/app/main`; SDK 2.3.5 / app 1.0.0 observed in native logs |
| Cloud environment | `EARNFM_TOKEN`, `EARNFM_COOLDOWNS` |
| Cloud command | `/bin/sh -c` decodes embedded base64 chunks into `/tmp/earnfm-start.sh`, then executes it |
| Gateway, SSH, health probes, autoscaling, external log sink | not configured for this service |
| Funding | user supplied $5; this is historical funding, not a current balance guarantee |

The exact API schema and required create/start sequence are documented by [Salad's create API](https://docs.salad.com/reference/saladcloud-api/container-groups/create-container-group) and [API quickstart](https://docs.salad.com/container-engine/tutorials/quickstart-api). The client is the [official EarnFM Docker image](https://hub.docker.com/r/earnfm/earnfm-client). These are external service dependencies, not missing project source.

## 2. What runs where

```text
Salad, each of 10 machines
  pinned EarnFM image
    embedded start.sh
      account client process /app/main
      actual eth0 RX/TX samples -> Salad container logs
      process/error/country recovery -> own-node IMDS reallocation

Mac, logged-in user
  Keychain -> recorder's read credentials
  scripts/earnfm-recorder.py -> Salad logs + EarnFM account readings
    ~/.hg1/earnfm/traffic.sqlite3       durable network ledger
    ~/.hg1/earnfm/provider*.json        credited account observations
    dashboard/static/earnfm.json       current public-to-loopback snapshot
  HTTP server on 127.0.0.1:8787 -> dashboard/static/earnfm.html
```

Cloud recovery does not use the Mac's Salad API key or require the Mac to be awake. The **local dashboard, credit refresh, and durable local collection do require the Mac**. While it is off, cloud clients continue and emit logs; later backfill is limited by provider log retention and the recorder's query windows. A Mac outage is not guaranteed lossless historical recording.

Original paths on the source Mac:

- Source: `/Users/cosmosgeek/Desktop/salad-bandwidth-stack/`
- Installed app: `/Users/cosmosgeek/Library/Application Support/Salad Bandwidth Dashboard/`
- State: `/Users/cosmosgeek/.hg1/earnfm/`
- Recorder service: `~/Library/LaunchAgents/com.cosmosgeek.earnfm-recorder.plist`
- Existing shared dashboard service: `com.cosmosgeek.salad-bandwidth-dashboard`
- This file: `/Users/cosmosgeek/Desktop/salad/fm.md`

The clean rebuild uses your own home directory automatically. The extraction destination determines the app directory; the standard destination below recreates the original layout without hardcoding a username.

## 3. Actual recovery rules in version 8

This section describes the embedded code, not the earlier chat's five-minute policy.

| Observed condition | Exact current behavior |
|---|---|
| `WebSocket dial ... HTTP 429` | Stop the client, mark `rate_limited`, wait **86,400 seconds**, then try again. No reallocation for that error. |
| Unexpired `EARNFM_COOLDOWNS` entry for this machine | Wait until its absolute Unix deadline before client launch or geolocation requests. |
| `All ... IP(s) for ... exhausted` | Stop the client and request own-node replacement immediately. |
| Repeated matching WebSocket DNS/dial/control errors spanning **30 seconds** | Stop the client and request own-node replacement. A gap exceeding 60 seconds resets the error window. |
| Native client exits, including exit code 0 | Request replacement with reason `client_exited`. |
| IPinfo and DB-IP both give the same non-US country for the same IP | Request replacement with reason `foreign_egress` before launching EarnFM. |
| Geo requests fail, disagree, or lack a usable country | Continue; country is unknown. This is not a verified US exit. |
| Ordinary quiet period / no paid traffic | No earnings-based replacement; the code has no per-client paid traffic counter. |
| Explicit termination signal | Emit final telemetry when possible and stop normally. |

Reallocation uses `POST http://169.254.169.254/v1/reallocate` with `Metadata: true`, JSON reason, and bounded timeouts. After requesting it, the process exits 75; that is also a platform failure fallback. See [Salad IMDS](https://docs.salad.com/reference/imds/reallocate). `EF_REALLOCATION_ACCEPTED` means the request was accepted, not that the successor is already ready.

Important operating limits:

- **The last rule set is more aggressive than the earlier five-minute/restart-once version.** Exhausting one host's backend list can preempt the vendor's later fallback. Preserve this fact when deciding whether to change policy; this guide reproduces the observed deployment rather than silently redesigning it.
- A one-backend HTTP 429 triggers the full pause. The [provider's guidance](https://help.earn.fm/portal/en/kb/articles/why-am-i-rate-limited-or-user-is-limited) recommends a day for rate-limited connections, but does not establish the scope of every individual WebSocket 429. Do not change source IP or identity to evade a confirmed restriction.
- Cooldowns created during a run live in that run's memory; only entries already encoded in the cloud environment survive a full restart. **Before any manual update/restart, recover new `EF_BACKOFF` deadlines from logs and preserve them.** The supplied `deploy --update` does this. A platform restart outside that path can reset a newly observed cooldown; the current system is not a persistent global rate-limit controller.
- Country checking happens once at startup. IP changes later in a run are not rechecked by this shell program. The page only labels a country when EarnFM's observed IP matches the startup IP.
- Error recovery is driven by specific log messages and process exit. A silent live-but-disconnected process emitting none of those messages is not fully detected. Zero credited traffic also does not trigger replacement.
- A new host can again be unsuitable. No global replacement quota or spending controller is embedded. Keep the account's funded balance and auto-recharge settings under explicit control.

## 4. Rebuild prerequisites and accounts

Use a Mac with Python **3.9 or later**, `curl`, and Apple's Swift compiler. The recorder uses the standard library and macOS Keychain; no npm, pip, web framework, paid dashboard service, or local Docker daemon is required to operate it. Docker is useful only for optional image backup and offline checks.

Check tools in Terminal:

```sh
python3 --version
curl --version
xcrun --find swiftc
```

If `swiftc` or Python is unavailable, install Apple's Command Line Tools using `xcode-select --install`, complete Apple's installation, and repeat the checks. Install a supported Python from [python.org](https://www.python.org/downloads/macos/) if the OS does not provide one. The service installer records the interpreter you actually used.

Log into the existing [Salad portal](https://portal.salad.com/organizations) and [EarnFM account](https://app.earn.fm/). Confirm access to **SSH3 / default** and available credit. Do not create another earning account to get around a restriction. If SSH3 itself was deleted, its owner must recreate/restore it and funding through Salad; cloud organization access cannot be reconstructed from a UUID.

Three different credentials are used:

| Keychain service | Obtain it from | Used for |
|---|---|---|
| `salad-bandwidth-api` | Salad profile menu → **API Access** | Read/manage authorized Salad group and logs |
| `earnfm-api-key` | EarnFM account settings / Docker installation card | Docker `EARNFM_TOKEN` only |
| `earnfm-read-session` | Access JWT used by the signed-in EarnFM web app's `X-API-Key` request header | Account balance and online-device reads |

All Keychain items use the **current macOS username** as account. The compiled helper is `.runtime/keychain-store`. It accepts secret values on standard input; commands in this guide do not put them in command-line arguments, project files, screenshots, or shell history.

To obtain the **reader JWT** without any chat-specific login link:

1. Sign in normally at `https://app.earn.fm/`.
2. Open browser Developer Tools → **Network**, then reload the app.
3. Filter requests for `view_balance`; open the request to `https://api.earn.fm/v2/harvester/view_balance`.
4. Under Request Headers, copy the **value only** of `X-API-Key`. It is an access JWT, commonly beginning `eyJ`. It is not the short Docker API key and has no `Bearer ` prefix in the observed client.
5. Paste it only into the recovery CLI's hidden reader prompt. The CLI reads the JWT's expiry, verifies it against both provider endpoints, and stores `{access_token, expires_at}` securely. It never asks for or stores a refresh token.
6. If that request is absent, ensure the app has fully loaded and you are signed in. The app's Application → Local Storage entry `sb-sb-auth-token` also contained `access_token` and `expires_at` in the observed build; do not copy the whole session or its refresh token. Network headers are the preferred route because storage names can change.

The captured reader session expired on September 11, 2026, around 20:55 IST. **That old token is not supplied here.** New sessions have their own expiry. Refresh the reader using the same steps and `keys --service reader --replace`. Its expiry does not stop the cloud EarnFM clients.

## 5. Extract every embedded file

Save this document at `~/Desktop/salad/fm.md`. The following is a complete extractor. It checks the manifest before writing and refuses to overwrite a differing existing file. It does not change the live cloud or Keychain.

```sh
python3 - "$HOME/Desktop/salad/fm.md" "$HOME/Library/Application Support/Salad Bandwidth Dashboard" <<'PY_EXTRACT'
from pathlib import Path
import hashlib, json, re, sys
source = Path(sys.argv[1])
root = Path(sys.argv[2]).expanduser().resolve()
pattern = r'^<!-- FM_FILE ([A-Za-z0-9_./-]+) -->\n```[^\n]*\n(.*?)^```\n<!-- /FM_FILE -->'
items = re.findall(pattern, source.read_text(), re.M | re.S)
if not items or len(dict(items)) != len(items):
    raise SystemExit('Missing or duplicate embedded file blocks')
files = {name: text.encode() for name, text in items}
manifest = json.loads(files['manifest.json'])
if set(files) != set(manifest) | {'manifest.json'}:
    raise SystemExit('Manifest and embedded files differ')
for name, content in files.items():
    path = (root/name).resolve()
    if root not in path.parents:
        raise SystemExit('Unsafe embedded path: '+name)
    if name != 'manifest.json' and hashlib.sha256(content).hexdigest() != manifest[name]:
        raise SystemExit('Checksum failed: '+name)
    if path.exists() and path.read_bytes() != content:
        raise SystemExit('Existing file differs; choose an empty recovery directory: '+str(path))
for name, content in files.items():
    path = root/name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
print('Extracted', len(files), 'verified files into', root)
PY_EXTRACT
```

If surviving source files differ, use a new empty directory such as `~/Desktop/earnfm-rebuild` as the second argument. Investigate the differences before replacing a live app. All subsequent commands must run from the extraction directory you chose.

```sh
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 fm-rebuild.py prepare
python3 fm-rebuild.py plan
python3 fm-rebuild.py keys
```

`prepare` verifies all embedded file checksums and compiles the Keychain helper. `plan` prints only nonsecret configuration. `keys` retains usable existing entries and prompts for missing/expired ones in an interactive terminal. macOS may ask permission for the helper to access an existing Keychain item; allow only this local helper when restoring the service.

## 6. Restore the cloud and local recording

First inspect. Do not create duplicate groups if the original still exists.

```sh
python3 fm-rebuild.py inspect
python3 fm-rebuild.py deploy
```

`deploy` behaves as follows:

- If the group is absent, it creates **ten replicas** using the pinned image and full startup script, initially with autostart false.
- If the same group/configuration **and selected client token** survive, it adopts it and writes local `target.json` without restarting it. A missing/different cloud token requires the explicit update path; neither token is printed.
- If the group differs, it stops with an explanation. To deliberately replace its configuration with this version, use `python3 fm-rebuild.py deploy --update`. **That updates a paid running group and may restart every replica.** It carries forward unexpired environment and recorded-log cooldowns, explicitly clears GPU classes, and verifies CPU/memory/shared-memory settings and the selected client token after the update. When no cooldown remains, the environment uses the harmless nonempty marker `none`, which the startup loop ignores.
- It never prints the payload containing `EARNFM_TOKEN` or the Salad key. It verifies the decoded cloud script and image after a create/update, reads the actual new group ID/version, and writes them to `~/.hg1/earnfm/target.json`.
- On a network error with uncertain mutation outcome, run `inspect` first. Do not keep firing create/update requests.

If `target.json` is missing while a traffic database, SQLite sidecar, provider reading, or provider baseline survives, `deploy` refuses to create/adopt/update a group. Restore the matching `target.json` from a consistent backup, or **stop the existing recorder first** and archive the whole `~/.hg1/earnfm` directory before creating fresh state. The same archive procedure applies when local `target.json` belongs to a group that was deleted/recreated. This preserves its database, baseline and logs rather than mixing two deployments. Example for a discontinued deployment only:

```sh
launchctl bootout "gui/$(id -u)/com.cosmosgeek.earnfm-recorder"
python3 - <<'PY_ARCHIVE'
from pathlib import Path
from datetime import datetime, timezone
p = Path.home()/'.hg1/earnfm'
if p.exists():
    dest = p.with_name('earnfm-saved-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    p.rename(dest)
    print(dest)
PY_ARCHIVE
```

If `bootout` says the service does not exist, that is expected on a new machine. Do not archive current state merely to silence a mismatch; compare group IDs first.

After successful deployment/adoption, start the group and take a single live observation before installing the recurring local services:

```sh
python3 fm-rebuild.py start
python3 fm-rebuild.py inspect
python3 fm-rebuild.py observe
```

Allocation and image preparation are asynchronous. A successful start response is not a claim that ten clients are earning. Repeat `inspect` after the platform has made progress. `observe` creates a fresh database and a fresh provider baseline only when they are absent. It does not fabricate earlier history. A surviving matching database/baseline is retained.

If `observe` says the recorder lock is held, the existing recorder is already running; use its published JSON instead of starting another process. If the page says “awaiting sample,” inspect logs and let the nodes reach the client startup stage. Schema migrations add IP/country columns to old local databases without clearing saved bytes.

## 7. Restore the page and services

For a clean machine with port 8787 free:

```sh
python3 fm-rebuild.py install
```

This creates and starts these user LaunchAgents, both in `~/Library/LaunchAgents/`:

- `com.cosmosgeek.earnfm-recorder`: runs the embedded `scripts/earnfm-recorder.py`, writes the ledger and JSON.
- `com.cosmosgeek.earnfm-dashboard`: runs the small recovery server embedded in `fm-rebuild.py`, binds **127.0.0.1 only**, serves the original EF HTML/CSS/JSON.

Open [EF locally](http://127.0.0.1:8787/ef) or [the root page](http://127.0.0.1:8787/). This clean-room page is EF-only. Its inherited Honeygain/PacketStream links require those other projects; they do not install or control them.

For a foreground test without installing a service:

```sh
python3 fm-rebuild.py serve --port 8787
```

Stop that foreground server with Ctrl-C before calling `install`. An occupied port is reported as an error; the installer does not kill an unrelated dashboard.

If the original shared dashboard survives, use its server and restore only the EF files. **Do not run two servers on 8787.** `install --shared-dashboard` installs only the recorder, provided that recorder's LaunchAgent does not already exist. For a surviving service, retain its plist and verify its working directory and executable. If it is still loaded, use `launchctl kickstart -k "gui/$(id -u)/com.cosmosgeek.earnfm-recorder"`. **If the archive step unloaded it with `bootout`, reload it instead:**

```sh
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.cosmosgeek.earnfm-recorder.plist"
```

Do not call `install` for an existing retained plist. If you extracted to a different directory, first edit that plist's `WorkingDirectory` and script path under `ProgramArguments` to the extraction directory; keep the Python interpreter path valid. Use `plutil -lint` on the edited plist, then the bootstrap command above. A loaded service must be booted out before reloading an edited plist.

The shared server integration requires only these read-only routes, all sourced from the EF static directory:

| Route | Contents / MIME |
|---|---|
| `/ef` | `dashboard/static/earnfm.html`, HTML |
| `/ef.json`, `/earnfm.json` | `dashboard/static/earnfm.json`, JSON |
| `/api/earnfm` | the same JSON, used by the shared dashboard's EarnFM tab |
| `/styles.css` | embedded stylesheet if no shared stylesheet already exists |

No management API key goes to browser JavaScript. The captured multi-protocol tab linked to `http://127.0.0.1:8787/#earnfm`; `fm-rebuild.py` supplies `/api/earnfm` for integration, but does not recreate the other protocols' UI/backend. The included standalone `/ef` gives the complete EarnFM monitoring function if that shared code has been lost.

## 8. Verify that it actually works

Run these from the recovery directory:

```sh
python3 fm-rebuild.py inspect
python3 fm-rebuild.py logs --minutes 15
curl --fail --silent http://127.0.0.1:8787/ef.json
```

Expected evidence, not just “process running”:

1. Cloud desired replicas = 10; current instance states and versions are visible. A new group's version number need not be 8; **decoded script SHA256 must match this package**.
2. Logs show `EF_START`, `EF_LOCATION`, and JSON `earnfm_sample` with current machine/runtime IDs. `EF_REALLOCATE` and `EF_REALLOCATION_ACCEPTED` explain replacement requests. Match a successor's ID and later samples before calling replacement complete.
3. `earned` and `credited_mb` change only from authenticated EarnFM account reads. `provider.error` and overall `error` must be checked; stale values are not current earnings.
4. A client counts online only when EarnFM lists its observed runtime ID, its latest sample is recent and non-final, and its state is `running`. A Salad container can be running while the client is paused or failing.
5. `country = US` requires matching provider IP and the startup two-vendor country result. Blank country is unverified. Group placement `us` alone does not prove the exit IP is in the US.
6. Selecting a graph minute should show the recorded server contributions; a different time range must change the graph. Look at browser Console for errors. Do not count a successful HTTP response as a healthy application by itself.

Fresh configuration/checksum verification is available without printing secrets:

```sh
python3 fm-rebuild.py plan
python3 fm-rebuild.py inspect
```

Local service checks and logs:

```sh
launchctl print "gui/$(id -u)/com.cosmosgeek.earnfm-recorder"
launchctl print "gui/$(id -u)/com.cosmosgeek.earnfm-dashboard"
tail -n 40 "$HOME/.hg1/earnfm/recorder.err.log"
tail -n 40 "$HOME/.hg1/earnfm/standalone-dashboard.err.log"
```

The original shared server uses `com.cosmosgeek.salad-bandwidth-dashboard` instead of the standalone dashboard label. User LaunchAgents start with login; the Keychain must be available. No claim is made that this local observer runs before login.

## 9. Byte accounting and earnings

- `rx`, `tx`: measured interface deltas since the prior sample, in bytes. `total_rx`, `total_tx`: counters accumulated within one wrapper run. The first sample establishes a zero-delta baseline.
- One sample per second, explicitly **1000 ms clock resolution**. The image's BusyBox date did not provide nanosecond timestamps.
- Database primary key `(run, seq)` deduplicates queried samples; `run` is the runtime instance ID plus launch time. The latest cumulative row per run supports a lifetime raw total. Departed machines' cursors are drained briefly to collect tail logs.
- Graph bars sum recorded interval RX+TX by minute. Missing intervals and boundary-straddling samples can make graph sums differ slightly from cumulative totals or label a minute partial. This is not fabricated earning data.
- Current `kb_per_second` is the **latest 60 seconds of that run's measured bytes divided by covered milliseconds**; bytes/ms numerically equals decimal KB/s. A boundary interval is prorated uniformly. It is not instantaneous throughput or customer-only traffic. The shared tab multiplies by `0.06` for MB/min.
- Interface RX+TX includes request/response forwarding, control traffic, failed attempts and the startup geolocation lookups. A relayed payload may cross the interface more than once. EarnFM's exact billing byte convention is not established here; do not call the raw-minus-credited difference waste.
- Provider reads: `GET /v2/harvester/view_balance` and `GET /v2/harvester/devices_online` on `https://api.earn.fm`, using the **account access JWT** in `X-API-Key`. The Docker token does not authorize those account reads.
- Credited USD = `bandwidthBalance + bandwidthDCBalance`; credited GB = `totalBandwidthShared + totalDCBandwidthShared`; displayed changes subtract the saved baseline. These are gross, account-wide accrued credits, not payouts, per-machine earnings or net profit. Salad cost is not subtracted.
- The original baseline was `$0.041831 / 0.418308 GB` with saved time `1788730420050` (2026-09-07 03:03:40.050 IST). That timestamp was captured locally before the first API request, so the original provider observation time is approximate. Do not copy this baseline into a different account or a new experiment.
- The [published rates](https://sdk-docs.earn.fm/overview/) were $0.10/GB residential and $0.04/GB datacenter when checked. Actual observed credit changes, not inferred rates applied to raw bytes, determine reported earnings.

## 10. Troubleshooting and concrete failures already seen

| Symptom | What to do |
|---|---|
| One replica instead of ten | Check both `plan` and live `inspect`; this package sets 10 at creation, not a one-replica canary. |
| `EARNFM_TOKEN environment variable is not set` | Save the Docker key and ensure it is in the cloud environment. An account JWT is not a substitute. |
| Account endpoint HTTP 401 | Use the web app's current access JWT, not the Docker UUID. Renew reader credentials. |
| `EarnFM account login expired` | Sign in again, obtain the current request-header JWT, then run `keys --service reader --replace`. Cloud clients keep running. |
| Salad HTTP 400 on log timestamps | Use UTC ISO strings with millisecond precision from `iso()`; raw varying fractional timestamps caused real failures. |
| `A telemetry window exceeded the log page limit` | A full page is not a complete result. Use narrower query windows; never silently advance a cursor on truncated data. The recovery CLI splits full text-log windows. |
| Keychain entry unavailable or prompt loops | Use the same macOS username, unlocked login Keychain and the compiled helper; restore the missing service via `keys`. Do not put secrets into source. |
| Ledger/provider state survives without `target.json` | Restore the matching target from backup, or stop the recorder and archive the state as described in section 6. Do not create a new target over an unidentified old ledger. |
| `Resource temporarily unavailable` on `recorder.lock` | Another recorder holds the lock. Retain one process; inspect LaunchAgents before rerunning `observe`. |
| `Country unverified` / blank country | Check `EF_LOCATION`, both geo requests, and current provider IP. Unknown results do not establish US placement. |
| Container running, client not confirmed | Read native logs and sample state. Do not equate a live process with a useful relay or credited traffic. |
| HTTP 429 / `rate_limited` | Honor the cooldown, preserve its deadline across manual changes. A paused container still incurs Salad cost. Do not reallocate it to evade the restriction. |
| Persistent DNS / socket errors | This version requests replacement on exhaustion or 30 seconds of repeated matching errors. Read `EF_REALLOCATE` and inspect the successor. Quiet unverified clients remain a known limitation. |
| Salad version changes, runtime ID does not | This happened on a problematic node. Compare actual `EF_START`/sample runtime ID with inventory. A targeted operator reallocation may be needed after checking rate-limit history; version alone was misleading. |
| Geo says GB/GR despite requested US | This happened for two old nodes. The two-provider startup rule rejected them automatically; replacements must be checked anew. |
| Old raw headline differs from current row totals | Rows refer to the latest run; the headline includes previous runs. Do not delete old runs or multiply a current counter by replica count. |
| Few credits, high raw MB | Compare the same account/time window and connection quality. Neither absent demand nor profitability is established by a raw-byte graph. |
| Port 8787 occupied | Keep the existing shared dashboard, or explicitly stop a known duplicate server. Use `serve --port 8788` for a separate recovery test. |
| Group not found / permission denied | Verify `ssh3/default` and Salad account access. Don't silently deploy into another organization. |
| Registry image unavailable | Restore a saved image archive or resolve the official vendor image. Do not silently swap to an unknown/latest implementation. |

A whole-group shutdown, when intended, is explicit:

```sh
python3 fm-rebuild.py stop
python3 fm-rebuild.py inspect
```

Stopping the local recorder or web server **does not stop paid cloud containers**. Stopping the cloud group does not delete the local ledger. The original account's auto-recharge was inactive when checked; verify the current billing page before relying on a credit ceiling.

## 11. Back up the irreplaceable parts

Keep this file, the pinned vendor image if long-term availability matters, the encrypted account-recovery material, and a consistent database backup. A reference to a lost path is not a backup.

Consistent local state backup while the recorder runs (SQLite's backup API includes committed WAL content):

```sh
python3 - <<'PY_BACKUP'
from pathlib import Path
from datetime import datetime, timezone
import sqlite3, shutil
src = Path.home()/'.hg1/earnfm'
dst = Path.home()/('Desktop/earnfm-state-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
dst.mkdir()
with sqlite3.connect('file:'+str(src/'traffic.sqlite3')+'?mode=ro', uri=True) as original:
    with sqlite3.connect(dst/'traffic.sqlite3') as backup:
        original.backup(backup)
for name in ('target.json', 'provider-baseline.json', 'provider.json'):
    p = src/name
    if p.exists(): shutil.copy2(p, dst/name)
print('Move this state backup and fm.md to independent storage:', dst)
PY_BACKUP
```

Restore that backup only while the recorder is stopped, into `~/.hg1/earnfm`, and only when its target group/account still matches. Do not restore a stale `.sqlite3-wal`, `.sqlite3-shm` or lock file with the backed-up database. If all historical data is lost, start a new measurement baseline; this file does not invent old per-second traffic.

Optional image preservation, with Docker installed:

```sh
docker pull --platform linux/amd64 earnfm/earnfm-client@sha256:99a9feaa3dfab9e858012994fa1f922523f41b098e6b1cd9c9e9fca9286c3843
docker save --output "$HOME/Desktop/earnfm-client-amd64.tar" earnfm/earnfm-client@sha256:99a9feaa3dfab9e858012994fa1f922523f41b098e6b1cd9c9e9fca9286c3843
```

`docker load --input <archive>` restores the local image. To use a private preserved registry image in Salad, an operator must publish it to an authorized registry and update image/registry access deliberately; a local tar file is not automatically available to Salad. Do not paste credentials into this markdown.

## 12. Validation and source inventory

The embedded runtime files are frozen snapshots. The manifest hashes cover their exact bytes. `fm-rebuild.py` is a recovery-only helper added for this document; it is not a claim that the former shared dashboard server was this small file.

The following records validation performed while writing and auditing this document. No paid deployment, credential writes, current dashboard restart, or current ledger modification is needed to test extraction and the bootstrap code.

<!-- FM_VALIDATION -->
- Extracted all nine embedded files from this markdown into an empty temporary directory; every SHA256 matched.
- Verified the generated cloud command decodes to the exact version-8 startup source (SHA256 `ffe70604216fd91769da8cfee6ecf4699b4dd3890b42bd42318eb987376860aa`). Ran that command in the pinned AMD64 image with networking disabled and no token: it decoded correctly and stopped at the explicit missing-key check before launching the vendor client.
- Python syntax, shell syntax, inline browser JavaScript syntax and Swift compilation passed.
- Exercised create-ten, no-change adoption, explicit update, and refusal of a differing existing configuration against an isolated API fixture. No real create/update/start request was issued while authoring this file.
- Tested all standalone HTML/CSS/JSON aliases over loopback HTTP with temporary fixture data; HTTP 200 and expected content verified.
- Generated and inspected LaunchAgent definitions with `launchctl` stubbed. No real service was installed or restarted during these tests.
- Verified an extraction conflict leaves the operator's existing differing file untouched.
- One initial test assertion compared `/var/...` with macOS's equivalent `/private/var/...`; canonicalizing both test paths resolved it. No production-code change was needed for that fixture issue.
- Not re-executed here: interactive credential writes, a new paid Salad deployment, supplier traffic generation, or a fresh real provider account. These require the operator's account and authorization at rebuild time; the document gives the exact steps.
- Follow-up recovery checks passed for an unfamiliar old command, a missing cloud client token, a surviving unwanted GPU allocation, and post-update refusal when the API still reports wrong resources. Empty cooldown lists use the nonempty `none` marker accepted by the documented environment-value schema.
- Verified the optional `docker save` command writes an archive for the pinned cached image. The temporary archive was deleted after testing.
- Independent Astra review found no concrete defect in the corrected recovery paths or their regressions.

Additional verification on 2026-09-07 after the owner requested a second audit:

- Compared the decoded live cloud version-8 script with this file again: exact SHA256 match. The installed recorder, HTML and CSS also matched their embedded versions.
- Extracted the package again into an empty directory, compiled its Swift helper, and ran the embedded recorder's real main flow with temporary state/output paths. Existing authorized Keychain access supplied read credentials; no credential values were written into the package or temporary state.
- Real Salad and EarnFM API reads succeeded. The isolated recorder collected **1,217 source samples from 10 workers** and created a new provider baseline with **zero initial earned/credited change**, rather than claiming old account earnings as new income. The raw headline retained source-reported cumulative run bytes, as described in section 9; it is not a claim that those bytes flowed during the short audit window.
- Served that actual isolated observation with the embedded server, checked all HTML/CSS/JSON aliases, opened the rebuilt page, changed its time range, and selected a traffic bar. Browser warnings/errors were empty. The one-shot snapshot correctly became stale while the test was idle.
- Repeated the exact base64 startup command in the pinned AMD64 image with network disabled and no token. It decoded and stopped at the expected required-key check before vendor-client launch.
- Found and fixed a partial-loss defect: a missing `target.json` with an old ledger/provider baseline could previously mix old and new deployments. The helper now refuses before mutation for five surviving data-file types, with either an existing or absent cloud group, in normal and explicit-update modes. Clean creation and valid matching-state adoption still pass.
- These additional checks made **no cloud mutation, credential write, production ledger change, or live service restart**. A new paid deployment and new-account provisioning were not repeated. Reproducible code/configuration/data collection is verified; identical future traffic, placement and earnings are not guaranteed.
- Final independent Astra review of the corrected file found no concrete defect. The additional Claude UI reviewer could not run because its saved login had expired; the restored-page browser checks above were executed directly.
<!-- /FM_VALIDATION -->

## 13. Embedded recovery files

Do not edit the following blocks independently of the manifest. If maintaining this package later, recapture the actual deployed script, update descriptions of changed behavior, regenerate hashes and rerun extraction/verification. The extractor recognizes only `FM_FILE` blocks below.

### `rebuild-config.json`

<!-- FM_FILE rebuild-config.json -->
```json
{
  "organization": "ssh3",
  "project": "default",
  "name": "earnfm-us",
  "display_name": "EF",
  "replicas": 10,
  "image": "docker.io/earnfm/earnfm-client@sha256:99a9feaa3dfab9e858012994fa1f922523f41b098e6b1cd9c9e9fca9286c3843",
  "recorded_cloud_version": 8,
  "recorded_group_id": "90078bc1-4410-46cd-8411-6ebb8968eec2",
  "recorded_cooldowns": {
    "55da989f-fdeb-5a51-b95b-1627b227f1be": 1788821961,
    "640f0410-7d89-4c51-a507-17cdd7acbac1": 1788821197
  },
  "recorded_at_utc": "2026-09-07T04:59:23.007579+00:00"
}
```
<!-- /FM_FILE -->

### `fm-rebuild.py`

<!-- FM_FILE fm-rebuild.py -->
```python
#!/usr/bin/env python3
"""Recovery CLI shipped inside fm.md. No live actions happen on import."""
import argparse
import base64
from datetime import datetime, timezone
import getpass
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import plistlib
import re
import shutil
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA = Path.home() / '.hg1/earnfm'
CONFIG = json.loads((ROOT / 'rebuild-config.json').read_text())
BASE = 'https://api.salad.com/api/public/organizations/' + CONFIG['organization']
GROUP = '/projects/' + CONFIG['project'] + '/containers/' + CONFIG['name']
HELPER = ROOT / '.runtime/keychain-store'
SERVICES = {'salad': 'salad-bandwidth-api', 'client': 'earnfm-api-key', 'reader': 'earnfm-read-session'}


def key(service):
    p = subprocess.run([str(HELPER), '--read', '--service', service, '--account', getpass.getuser()],
                       capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError('Keychain entry unavailable: ' + service + '; run the keys command in Terminal')
    return p.stdout.strip()


def call(url, header, method='GET', body=None, missing=False):
    lines = ['header = ' + json.dumps(header)]
    if body is not None:
        kind = 'application/merge-patch+json' if method == 'PATCH' else 'application/json'
        lines += ['header = ' + json.dumps('Content-Type: ' + kind), 'data-binary = ' + json.dumps(json.dumps(body))]
    p = subprocess.run(['curl', '-sS', '--max-time', '30', '--config', '-', '-X', method,
                        '--write-out', '\n%{http_code}', url], input='\n'.join(lines)+'\n',
                       text=True, capture_output=True, timeout=35)
    raw, _, code = p.stdout.rpartition('\n')
    if missing and code == '404':
        return None
    if p.returncode or not code.isdigit() or not 200 <= int(code) < 300:
        raise RuntimeError(method + ' failed: HTTP ' + code + '; no automatic mutation retry was made')
    return json.loads(raw) if raw.strip() else {}


def api(path, method='GET', body=None, missing=False):
    return call(BASE + path, 'Salad-Api-Key: ' + key(SERVICES['salad']), method, body, missing)


def ms(value):
    value = re.sub(r'\.(\d+)(?=[+-]\d\d:\d\d$)', lambda m: '.'+m[1][:6].ljust(6, '0'), value.replace('Z', '+00:00'))
    return int(datetime.fromisoformat(value).timestamp()*1000)


def iso(value):
    return datetime.fromtimestamp(value/1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def source_bytes(command):
    if command[:2] != ['/bin/sh', '-c']:
        raise RuntimeError('Existing group has an unrecognized command; inspect it before updating')
    if 'base64 -d' in command[2]:
        return base64.b64decode(''.join(command[4:]), validate=True)
    if 'printf "%s\\n" "$@"' in command[2]:
        return ('\n'.join(command[4:])+'\n').encode()
    raise RuntimeError('Existing command encoding is unknown; no update performed')


def command():
    payload = base64.b64encode((ROOT/'earnfm-monitor/start.sh').read_bytes()).decode()
    args = ['/bin/sh', '-c', 'umask 077; printf "%s" "$@" | base64 -d > /tmp/earnfm-start.sh; exec /bin/sh /tmp/earnfm-start.sh', 'policy-start']
    args += [payload[i:i+900] for i in range(0, len(payload), 900)]
    if len(args) > 100 or max(map(len, args)) > 1000:
        raise RuntimeError('Command exceeds Salad argument limits')
    return args


def log_rows(start, end, query):
    rows = api('/log-entries', 'POST', {'query': query, 'start_time': iso(start), 'end_time': iso(end),
                                      'page_size': 100, 'sort_order': 'asc'}).get('items', [])
    if len(rows) < 100:
        return rows
    if end-start < 1000:
        raise RuntimeError('Log page still full at one second; result would be incomplete')
    middle = (start+end)//2
    return log_rows(start, middle, query) + log_rows(middle, end, query)


def cooldowns(group):
    holds = dict(CONFIG.get('recorded_cooldowns', {}))
    if group:
        env = group['container'].get('environment_variables', {})
        for item in env.get('EARNFM_COOLDOWNS', '').split():
            if item == 'none':
                continue
            machine, until = item.rsplit(':', 1)
            holds[machine] = max(holds.get(machine, 0), int(until))
        now = int(time.time()*1000)
        query = 'resource.type = "container" and resource.labels.container_group_name = '+json.dumps(CONFIG['name'])+' and text_log contains "EF_BACKOFF"'
        for row in log_rows(now-86400000, now, query):
            match = re.search(r'machine=([0-9a-f-]{36}) seconds=(\d+)', row.get('text_log', ''))
            if match:
                until = math.ceil(ms(row['time'])/1000)+int(match[2])
                holds[match[1]] = max(holds.get(match[1], 0), until)
    return {k: v for k, v in holds.items() if v > time.time()}


def prepare():
    for binary in ('curl', 'swiftc'):
        if not shutil.which(binary):
            raise RuntimeError(binary+' is missing; install Apple Command Line Tools first')
    manifest = json.loads((ROOT/'manifest.json').read_text())
    for name, digest in manifest.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Embedded source checksum mismatch: '+name)
    HELPER.parent.mkdir(exist_ok=True)
    if not HELPER.exists():
        subprocess.run(['swiftc', str(ROOT/'scripts/keychain-store.swift'), '-o', str(HELPER)], check=True)
        HELPER.chmod(0o700)
    DATA.mkdir(parents=True, exist_ok=True)
    print('Source checksums verified; Keychain helper ready. No cloud change made.')


def save_keys(which, replace):
    if not sys.stdin.isatty():
        raise RuntimeError('Run keys interactively in Terminal so secret entry is hidden')
    for name in (list(SERVICES) if which == 'all' else [which]):
        service = SERVICES[name]
        try:
            current = key(service)
            usable = name != 'reader' or json.loads(current)['expires_at'] > time.time()
            if usable and not replace:
                print(service+': existing entry retained')
                continue
        except (RuntimeError, ValueError, KeyError):
            pass
        prompt = {'salad': 'Salad API key: ', 'client': 'EarnFM Docker EARNFM_TOKEN: ',
                  'reader': 'EarnFM account X-API-Key access JWT (not the Docker key): '}[name]
        value = getpass.getpass(prompt).strip()
        if not value:
            raise RuntimeError('Empty credential; nothing saved')
        if name == 'reader':
            middle = value.split('.')[1]
            expiry = json.loads(base64.urlsafe_b64decode(middle+'='*((-len(middle))%4)))['exp']
            if expiry <= time.time():
                raise RuntimeError('Access JWT expired; sign in to EarnFM again')
            for endpoint in ('view_balance', 'devices_online'):
                result = call('https://api.earn.fm/v2/harvester/'+endpoint, 'X-API-Key: '+value)
                if result.get('status') != 200 or 'data' not in result:
                    raise RuntimeError('EarnFM account session verification failed')
            value = json.dumps({'access_token': value, 'expires_at': expiry})
        subprocess.run([str(HELPER), '--service', service, '--account', getpass.getuser()],
                       input=value, text=True, check=True, stdout=subprocess.DEVNULL)
        print(service+': saved securely')


def deploy(update):
    DATA.mkdir(parents=True, exist_ok=True)
    existing = api(GROUP, missing=True)
    desired = command()
    local = json.loads((DATA/'target.json').read_text()) if (DATA/'target.json').exists() else None
    old_state = ('traffic.sqlite3', 'traffic.sqlite3-wal', 'traffic.sqlite3-shm', 'provider-baseline.json', 'provider.json')
    if not local and any((DATA/name).exists() for name in old_state):
        raise RuntimeError('Ledger/provider state survives without target.json. Restore its matching target or archive the stopped recorder state as described in fm.md before deploying.')
    if local and (not existing or local['id'] != existing['id']):
        raise RuntimeError('Saved target belongs to another/deleted group. Follow the old-data archive step in fm.md first.')
    client_token = key(SERVICES['client'])
    same = bool(existing) and not update
    if same:
        try:
            same = source_bytes(existing['container']['command']) == (ROOT/'earnfm-monitor/start.sh').read_bytes()
        except RuntimeError:
            same = False
    if existing:
        same = same and existing['container']['image'] == CONFIG['image'] and existing['replicas'] == 10
        same = same and existing['country_codes'] == ['us'] and existing['container']['resources']['cpu'] == 1
        same = same and existing['container']['resources']['memory'] == 1024 and not existing['container']['resources'].get('gpu_classes')
        same = same and existing['restart_policy'] == 'always' and existing.get('priority') == 'batch'
        same = same and bool(client_token) and existing['container'].get('environment_variables', {}).get('EARNFM_TOKEN') == client_token
        same = same and existing['display_name'] == 'EF' and existing['autostart_policy'] is False
        same = same and existing['container']['image_caching'] is True and existing['container']['resources'].get('shm_size') == 64
        if not same and not update:
            raise RuntimeError('Existing group differs. Inspect it; --update explicitly replaces its configuration and restarts replicas.')
    holds = cooldowns(existing)
    changed = not same or update
    if changed:
        env = dict(existing['container'].get('environment_variables', {})) if existing else {}
        env.update(EARNFM_TOKEN=client_token, EARNFM_COOLDOWNS=' '.join(k+':'+str(v) for k, v in sorted(holds.items())) or 'none')
        container = {'image': CONFIG['image'], 'command': desired, 'resources': {'cpu': 1, 'memory': 1024, 'shm_size': 64, 'gpu_classes': []},
                     'priority': 'batch', 'image_caching': True, 'environment_variables': env}
        body = {'container': container, 'replicas': 10, 'display_name': 'EF', 'country_codes': ['us'],
                'restart_policy': 'always', 'autostart_policy': False}
        if existing:
            api(GROUP, 'PATCH', body)
        else:
            body['name'] = CONFIG['name']
            api('/projects/'+CONFIG['project']+'/containers', 'POST', body)
    actual = api(GROUP)
    if source_bytes(actual['container']['command']) != (ROOT/'earnfm-monitor/start.sh').read_bytes():
        raise RuntimeError('Cloud command verification failed; do not call start')
    resources = actual['container']['resources']
    if (actual['container']['image'] != CONFIG['image'] or actual['replicas'] != 10 or
            resources['cpu'] != 1 or resources['memory'] != 1024 or resources.get('shm_size') != 64 or
            resources.get('gpu_classes') or actual['container'].get('environment_variables', {}).get('EARNFM_TOKEN') != client_token):
        raise RuntimeError('Cloud image/resource/replica/credential verification failed; do not call start')
    now = int(time.time()*1000)
    target = dict(local or {}, id=actual['id'], organization=CONFIG['organization'], project=CONFIG['project'],
                  group=CONFIG['name'], desired=10, image=CONFIG['image'], display_name='EF', phase='measuring',
                  created_at=actual['create_time'], version=actual['version'], cooldowns=holds,
                  agent_sha256=hashlib.sha256((ROOT/'earnfm-monitor/start.sh').read_bytes()).hexdigest())
    target.setdefault('measurement_started_ms', now)
    (DATA/'target.json').write_text(json.dumps(target, indent=2))
    print(json.dumps({'id': actual['id'], 'version': actual['version'], 'replicas': actual['replicas'],
                      'cloud_changed': changed, 'state': actual['current_state']['status']}))


def inspect():
    group = api(GROUP, missing=True)
    if group is None:
        print('EF group does not exist; deploy can create it.')
        return
    print(json.dumps({k: group[k] for k in ('id', 'name', 'display_name', 'version', 'replicas', 'country_codes', 'current_state')}, indent=2))
    print('Cloud script SHA256:', hashlib.sha256(source_bytes(group['container']['command'])).hexdigest())
    nodes = api(GROUP+'/instances').get('instances', [])
    print(json.dumps([{k: n[k] for k in ('id', 'machine_id', 'state', 'version')} for n in nodes], indent=2))
    path = ROOT/'dashboard/static/earnfm.json'
    if path.exists():
        value = json.loads(path.read_text())
        print(json.dumps({'snapshot_age_s': round(time.time()-value['generated_ms']/1000), 'error': value['error'],
                          'provider': {k: v for k, v in value.get('provider', {}).items() if k != 'devices'},
                          'workers': value['workers']}, indent=2))


class Page(BaseHTTPRequestHandler):
    def do_GET(self):
        name = {'/': 'earnfm.html', '/ef': 'earnfm.html', '/earnfm': 'earnfm.html', '/earnfm.html': 'earnfm.html',
                '/styles.css': 'styles.css', '/ef.json': 'earnfm.json', '/earnfm.json': 'earnfm.json',
                '/api/earnfm': 'earnfm.json'}.get(urlparse(self.path).path)
        if not name:
            self.send_error(404)
            return
        path = ROOT/'dashboard/static'/name
        if not path.exists():
            self.send_error(503, 'Recorder has not published yet; run observe or inspect recorder.err.log')
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', {'html': 'text/html; charset=utf-8', 'css': 'text/css', 'json': 'application/json'}[name.rsplit('.', 1)[1]])
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def install(shared):
    labels = ['com.cosmosgeek.earnfm-recorder'] + ([] if shared else ['com.cosmosgeek.earnfm-dashboard'])
    directory = Path.home()/'Library/LaunchAgents'
    directory.mkdir(parents=True, exist_ok=True)
    for label in labels:
        if (directory/(label+'.plist')).exists():
            raise RuntimeError(label+' already exists. Inspect the existing service; do not install a second recorder.')
    if not shared:
        with socket.socket() as check:
            check.bind(('127.0.0.1', 8787))
    DATA.mkdir(parents=True, exist_ok=True)
    for label in labels:
        recorder = label.endswith('recorder')
        arguments = [sys.executable, '-B', str(ROOT/'scripts/earnfm-recorder.py')] if recorder else [sys.executable, '-B', str(ROOT/'fm-rebuild.py'), 'serve']
        log = 'recorder' if recorder else 'standalone-dashboard'
        value = {'Label': label, 'ProgramArguments': arguments, 'WorkingDirectory': str(ROOT), 'RunAtLoad': True,
                 'KeepAlive': True, 'ThrottleInterval': 10, 'StandardOutPath': str(DATA/(log+'.out.log')),
                 'StandardErrorPath': str(DATA/(log+'.err.log'))}
        path = directory/(label+'.plist')
        with path.open('wb') as file:
            plistlib.dump(value, file)
        subprocess.run(['launchctl', 'bootstrap', 'gui/'+str(os.getuid()), str(path)], check=True)
    print('Installed:', ', '.join(labels))


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('prepare')
    keys = sub.add_parser('keys'); keys.add_argument('--service', choices=['all']+list(SERVICES), default='all'); keys.add_argument('--replace', action='store_true')
    sub.add_parser('plan')
    deploy_parser = sub.add_parser('deploy'); deploy_parser.add_argument('--update', action='store_true')
    for name in ('inspect', 'start', 'stop', 'observe'):
        sub.add_parser(name)
    server = sub.add_parser('serve'); server.add_argument('--port', type=int, default=8787)
    service = sub.add_parser('install'); service.add_argument('--shared-dashboard', action='store_true')
    logs = sub.add_parser('logs'); logs.add_argument('--minutes', type=int, default=15); logs.add_argument('--machine')
    args = parser.parse_args()
    if args.action == 'prepare': prepare()
    elif args.action == 'keys': save_keys(args.service, args.replace)
    elif args.action == 'plan': print(json.dumps({'organization': CONFIG['organization'], 'project': CONFIG['project'], 'name': CONFIG['name'], 'replicas': 10, 'image': CONFIG['image'], 'cpu': 1, 'memory_mib': 1024, 'countries': ['us'], 'command_args': len(command()), 'script_sha256': hashlib.sha256((ROOT/'earnfm-monitor/start.sh').read_bytes()).hexdigest()}, indent=2))
    elif args.action == 'deploy': deploy(args.update)
    elif args.action == 'inspect': inspect()
    elif args.action in ('start', 'stop'):
        if args.action == 'start' and not (DATA/'target.json').exists():
            raise RuntimeError('Run deploy first to verify/adopt the group and create target.json')
        api(GROUP+'/'+args.action, 'POST'); print('Salad accepted '+args.action+'; inspect to verify completion.')
    elif args.action == 'observe': subprocess.run([sys.executable, '-B', str(ROOT/'scripts/earnfm-recorder.py'), '--once'], check=True)
    elif args.action == 'serve': ThreadingHTTPServer(('127.0.0.1', args.port), Page).serve_forever()
    elif args.action == 'install': install(args.shared_dashboard)
    elif args.action == 'logs':
        if not 1 <= args.minutes <= 1440: raise RuntimeError('Use a window from 1 to 1440 minutes')
        query = 'resource.type = "container" and resource.labels.container_group_name = '+json.dumps(CONFIG['name'])+' and text_log contains "EF_"'
        if args.machine:
            if not re.fullmatch('[0-9a-f-]{36}', args.machine): raise RuntimeError('Use the full machine UUID')
            query += ' and resource.labels.machine_id = '+json.dumps(args.machine)
        now = int(time.time()*1000)
        for row in log_rows(now-args.minutes*60000, now, query):
            text = re.sub(r'(?i)(apikey=)[^&\s]+', r'\1[redacted]', row.get('text_log', ''))
            print(row['time'], text)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, IndexError, KeyError, OSError, subprocess.SubprocessError) as exc:
        print('Recovery stopped: '+str(exc), file=sys.stderr)
        sys.exit(1)
```
<!-- /FM_FILE -->

### `earnfm-monitor/start.sh`

<!-- FM_FILE earnfm-monitor/start.sh -->
```sh
#!/bin/sh
set -u
: "${EARNFM_TOKEN:?EarnFM client key is required}"
umask 077
ef_dir=$(mktemp -d /tmp/earnfm.XXXXXX)
ef_instance=${SALAD_INSTANCE_ID:-local}
ef_machine=${SALAD_MACHINE_ID:-local}
ef_start=$(date +%s)
ef_run="$ef_instance/$ef_start"
ef_child=''
ef_seq=-1
ef_rx=0
ef_tx=0
ef_total_rx=0
ef_total_tx=0
ef_last=$ef_start
printf 'starting\n' > "$ef_dir/state"
printf '%s\n' '- -' > "$ef_dir/location"
mkfifo "$ef_dir/log"
exec 3<>"$ef_dir/log"
state() { printf '%s\n' "$1" > "$ef_dir/state.next"; mv "$ef_dir/state.next" "$ef_dir/state"; }
sample() {
  ef_now=$(date +%s)
  read -r ef_next_rx < /sys/class/net/eth0/statistics/rx_bytes || return
  read -r ef_next_tx < /sys/class/net/eth0/statistics/tx_bytes || return
  ef_seq=$((ef_seq+1))
  ef_dr=$((ef_next_rx-ef_rx)); ef_dt=$((ef_next_tx-ef_tx)); ef_valid=1
  if [ "$ef_seq" -eq 0 ]; then ef_dr=0; ef_dt=0; fi
  if [ "$ef_dr" -lt 0 ] || [ "$ef_dt" -lt 0 ]; then ef_valid=0; ef_dr=0; ef_dt=0; fi
  ef_total_rx=$((ef_total_rx+ef_dr)); ef_total_tx=$((ef_total_tx+ef_dt))
  read -r ef_state < "$ef_dir/state" || ef_state=starting
  read -r ef_ip ef_country < "$ef_dir/location"
  [ "$ef_ip" != '-' ] || ef_ip=''
  [ "$ef_country" != '-' ] || ef_country='' 
  printf '{"kind":"earnfm_sample","revision":1,"instance":"%s","machine":"%s","run":"%s","seq":%s,"start_ms":%s000,"end_ms":%s000,"rx":%s,"tx":%s,"total_rx":%s,"total_tx":%s,"state":"%s","valid":%s,"final":%s,"clock_resolution_ms":1000,"ip":"%s","country":"%s"}\n' "$ef_instance" "$ef_machine" "$ef_run" "$ef_seq" "$ef_last" "$ef_now" "$ef_dr" "$ef_dt" "$ef_total_rx" "$ef_total_tx" "$ef_state" "$ef_valid" "$1" "$ef_ip" "$ef_country"
  ef_rx=$ef_next_rx; ef_tx=$ef_next_tx; ef_last=$ef_now
}
shutdown() {
  trap '' TERM INT
  state "${1:-stopping}"
  ef_jobs=$(jobs -p)
  [ -z "$ef_jobs" ] || kill $ef_jobs 2>/dev/null || true
  sleep 2
  [ -z "$ef_jobs" ] || kill -KILL $ef_jobs 2>/dev/null || true
  wait 2>/dev/null || true
  rm -rf "$ef_dir"
}
trap 'shutdown; exit 0' TERM INT
sample 0
(ef_done=0; trap 'ef_done=1' TERM INT; while [ "$ef_done" -eq 0 ]; do sleep 1; [ "$ef_done" -eq 0 ] || break; sample 0; done; sample 1) &
reallocate() {
  state reallocating
  printf 'EF_REALLOCATE instance=%s machine=%s reason=%s\n' "$ef_instance" "$ef_machine" "$1"
  if timeout 15 wget -q -T 10 -O /dev/null --header 'Metadata: true' --header 'Content-Type: application/json' --post-data "{\"reason\":\"$1\"}" http://169.254.169.254/v1/reallocate; then
    printf 'EF_REALLOCATION_ACCEPTED instance=%s\n' "$ef_instance"
  else printf 'EF_REALLOCATION_FAILED instance=%s fallback=nonzero_exit\n' "$ef_instance"; fi
  shutdown reallocating
  exit 75
}
for ef_hold in ${EARNFM_COOLDOWNS:-}; do
  [ "${ef_hold%:*}" = "$ef_machine" ] || continue
  ef_until=${ef_hold##*:}
  case "$ef_until" in *[!0-9]*|'') continue ;; esac
  ef_remaining=$((ef_until-$(date +%s)))
  if [ "$ef_remaining" -gt 0 ]; then
    state rate_limited
    printf 'EF_BACKOFF instance=%s machine=%s seconds=%s reason=previous_rate_limit\n' "$ef_instance" "$ef_machine" "$ef_remaining"
    sleep "$ef_remaining" & wait $!
  fi
done
ef_info=$(timeout 15 wget -q -T 10 -O - https://ipinfo.io/json 2>/dev/null) || ef_info=''
ef_ip=$(printf '%s' "$ef_info" | sed -n 's/.*"ip"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
ef_country_a=$(printf '%s' "$ef_info" | sed -n 's/.*"country"[[:space:]]*:[[:space:]]*"\([A-Z][A-Z]\)".*/\1/p')
ef_country=''
case "$ef_ip" in *[!0-9a-fA-F:.]*|'') ef_ip='' ;; *)
  ef_info=$(timeout 15 wget -q -T 10 -O - "https://api.db-ip.com/v2/free/$ef_ip" 2>/dev/null) || ef_info=''
  ef_country_b=$(printf '%s' "$ef_info" | sed -n 's/.*"countryCode"[[:space:]]*:[[:space:]]*"\([A-Z][A-Z]\)".*/\1/p')
  if [ -n "$ef_country_a" ] && [ "$ef_country_a" = "$ef_country_b" ]; then ef_country=$ef_country_a; fi
;; esac
printf '%s %s\n' "${ef_ip:--}" "${ef_country:--}" > "$ef_dir/location.next"
mv "$ef_dir/location.next" "$ef_dir/location"
printf 'EF_LOCATION instance=%s machine=%s ip=%s country=%s\n' "$ef_instance" "$ef_machine" "${ef_ip:-unknown}" "${ef_country:-unknown}"
[ -z "$ef_country" ] || [ "$ef_country" = US ] || reallocate foreign_egress
printf 'EF_START instance=%s machine=%s run=%s recovery=container-local\n' "$ef_instance" "$ef_machine" "$ef_run"
while :; do
  ef_reason=''
  ef_failure_since=0; ef_failure_last=0
  state running
  /app/main > "$ef_dir/log" 2>&1 &
  ef_child=$!
  while :; do
    if IFS= read -r -t 1 ef_line <&3; then
      ef_clean=$(printf '%s\n' "$ef_line" | awk '{s=$0;k=ENVIRON["EARNFM_TOKEN"];while((p=index(s,k))>0){printf "%s[redacted]",substr(s,1,p-1);s=substr(s,p+length(k))}print s}')
      printf 'EF_LOG instance=%s machine=%s %s\n' "$ef_instance" "$ef_machine" "$ef_clean"
      case "$ef_line" in
        *'WebSocket dial '*'HTTP 429'*) ef_reason=rate_limited; state rate_limited; kill "$ef_child" 2>/dev/null || true; break ;;
        *'All '*'IP(s) for '*' exhausted'*) ef_reason=connection_error; state connection_error; kill "$ef_child" 2>/dev/null || true; break ;;
        *'WebSocket DNS lookup failed '*|*'WebSocket dial '*' failed:'*|*'Primary connection failed: WebSocket connection error:'*)
          ef_now=$(date +%s)
          if [ "$ef_failure_since" -eq 0 ] || [ $((ef_now-ef_failure_last)) -gt 60 ]; then ef_failure_since=$ef_now; fi
          ef_failure_last=$ef_now
          state connection_error ;;
      esac
    elif ! kill -0 "$ef_child" 2>/dev/null; then break; fi
    ef_now=$(date +%s)
    if [ "$ef_failure_since" -gt 0 ]; then
      if [ $((ef_now-ef_failure_last)) -gt 60 ]; then
        ef_failure_since=0; state running
      elif [ $((ef_failure_last-ef_failure_since)) -ge 30 ]; then
        ef_reason=connection_error; kill "$ef_child" 2>/dev/null || true; break
      fi
    fi
  done
  [ -z "$ef_reason" ] || { sleep 1; kill -KILL "$ef_child" 2>/dev/null || true; }
  wait "$ef_child"; ef_code=$?; ef_child=''
  if [ "$ef_reason" = rate_limited ]; then
    state rate_limited
    printf 'EF_BACKOFF instance=%s machine=%s seconds=%s reason=rate_limited\n' "$ef_instance" "$ef_machine" 86400
    sleep 86400 & wait $!
    continue
  fi
  if [ "$ef_reason" = connection_error ]; then
    reallocate connection_failure
  fi
  printf 'EF_EXIT instance=%s machine=%s code=%s\n' "$ef_instance" "$ef_machine" "$ef_code"
  reallocate client_exited
done
```
<!-- /FM_FILE -->

### `scripts/earnfm-recorder.py`

<!-- FM_FILE scripts/earnfm-recorder.py -->
```python
#!/usr/bin/env python3
"""Read SSH3 telemetry into a durable ledger and publish the EarnFM monitoring page data."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import getpass
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / '.hg1/earnfm'
OUTPUT = ROOT / 'dashboard/static/earnfm.json'
FIELDS = ('run', 'seq', 'instance', 'machine', 'start_ms', 'end_ms', 'rx', 'tx',
          'total_rx', 'total_tx', 'state', 'valid', 'final', 'ip', 'country')


def millis(value):
    value = re.sub(r'\.(\d+)(?=[+-]\d\d:\d\d$)', lambda m: '.'+m.group(1)[:6].ljust(6, '0'), value.replace('Z', '+00:00'))
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def iso(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def request(path, body=None):
    key = subprocess.check_output([str(ROOT / '.runtime/keychain-store'), '--read', '--service',
                                   'salad-bandwidth-api', '--account', getpass.getuser()], text=True).strip()
    config = 'header = ' + json.dumps('Salad-Api-Key: ' + key) + '\nheader = "Content-Type: application/json"\n'
    if body is not None:
        config += 'data-binary = ' + json.dumps(json.dumps(body)) + '\n'
    response = subprocess.run(['curl', '-sS', '--max-time', '20', '--config', '-', '--write-out', '\n%{http_code}',
                               'https://api.salad.com/api/public/organizations/ssh3' + path],
                              input=config, text=True, capture_output=True, timeout=25)
    raw, status = response.stdout.rsplit('\n', 1)
    if response.returncode or status != '200':
        raise RuntimeError('Salad reading failed (HTTP ' + status + ')')
    return json.loads(raw)


def provider_reading():
    path = DATA / 'provider.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    now = int(time.time()*1000)
    if now - previous.get('checked_ms', 0) < 60000:
        return previous
    result = dict(previous, checked_ms=now)
    try:
        value = subprocess.check_output([str(ROOT/'.runtime/keychain-store'), '--read', '--service',
                                         'earnfm-read-session', '--account', getpass.getuser()], text=True)
        session = json.loads(value)
        if session['expires_at'] <= time.time():
            raise RuntimeError('EarnFM account login expired; traffic recording continues')
        config = 'header = '+json.dumps('X-API-Key: '+session['access_token'])+'\n'
        responses = {}
        for name in ('view_balance', 'devices_online'):
            reply = subprocess.run(['curl', '-sS', '--max-time', '15', '--config', '-', '--write-out', '\n%{http_code}',
                                    'https://api.earn.fm/v2/harvester/'+name], input=config, text=True, capture_output=True, timeout=20)
            raw, code = reply.stdout.rsplit('\n', 1)
            if reply.returncode or code != '200':
                raise RuntimeError('EarnFM account reading failed (HTTP '+code+')')
            responses[name] = json.loads(raw)
        balance = responses['view_balance']['data']
        paid = float(Decimal(str(balance['bandwidthBalance']))+Decimal(str(balance['bandwidthDCBalance'])))
        shared = float(Decimal(str(balance['totalBandwidthShared']))+Decimal(str(balance['totalDCBandwidthShared'])))
        baseline_path = DATA/'provider-baseline.json'
        baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {'time_ms': now, 'balance': paid, 'gb': shared}
        if not baseline_path.exists():
            baseline_path.write_text(json.dumps(baseline))
        devices = []
        for item in responses['devices_online']['data']['devices']:
            match = re.search(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', item.get('deviceName', ''))
            devices.append({'instance': match.group() if match else None, 'name': item.get('deviceName'),
                            'ip': item.get('IP'), 'hosting': item.get('isHosting')})
        result = {'checked_ms': now, 'observed_ms': responses['view_balance']['timestamp'], 'balance': paid, 'gb': shared,
                  'earned': float(Decimal(str(paid))-Decimal(str(baseline['balance']))),
                  'credited_mb': float((Decimal(str(shared))-Decimal(str(baseline['gb'])))*1000),
                  'baseline_ms': baseline['time_ms'], 'devices': devices, 'error': None}
    except Exception as exc:
        result['error'] = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
    temporary = path.with_suffix('.tmp'); temporary.write_text(json.dumps(result)); os.replace(temporary, path)
    return result


def parse_sample(item, machine):
    row = item.get('json_log')
    if not isinstance(row, dict):
        try:
            row = json.loads(item.get('text_log', ''))
        except (ValueError, TypeError):
            return None
    if row.get('kind') != 'earnfm_sample' or row.get('revision') != 1 or row.get('machine') != machine:
        return None
    try:
        result = {key: row.get(key, '') if key in ('ip', 'country') else row[key] for key in FIELDS}
        for key in ('seq', 'start_ms', 'end_ms', 'rx', 'tx', 'total_rx', 'total_tx', 'valid', 'final'):
            value = result[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value) or not 0 <= value < 2**53:
                return None
            result[key] = int(value)
        if (not 0 < result['start_ms'] <= result['end_ms'] <= int(time.time()*1000)+60000 or result['valid'] not in (0, 1) or result['final'] not in (0, 1)
                or result['state'] not in ('starting', 'running', 'retrying', 'rate_limited', 'connection_error', 'stopping', 'reallocating')
                or not isinstance(result['run'], str) or len(result['run']) > 120
                or not isinstance(result['instance'], str) or len(result['instance']) != 36):
            return None
        if result['ip']:
            result['ip'] = str(ipaddress.ip_address(result['ip']))
        if result['country'] and not re.fullmatch('[A-Z]{2}', result['country']):
            return None
        return result
    except (KeyError, TypeError, ValueError):
        return None


def database(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS samples (
        run TEXT, seq INTEGER, instance TEXT, machine TEXT, start_ms INTEGER, end_ms INTEGER,
        rx INTEGER, tx INTEGER, total_rx INTEGER, total_tx INTEGER, state TEXT, valid INTEGER, final INTEGER, ip TEXT, country TEXT,
        PRIMARY KEY(run,seq));
      CREATE INDEX IF NOT EXISTS samples_time ON samples(end_ms);
      CREATE TABLE IF NOT EXISTS cursors(machine TEXT PRIMARY KEY,time_ms INTEGER);
      CREATE TABLE IF NOT EXISTS runs (
        run TEXT PRIMARY KEY, seq INTEGER, instance TEXT, machine TEXT, start_ms INTEGER, end_ms INTEGER,
        rx INTEGER, tx INTEGER, total_rx INTEGER, total_tx INTEGER, state TEXT, valid INTEGER, final INTEGER, ip TEXT, country TEXT);
    ''')
    for table in ('samples', 'runs'):
        columns = {r[1] for r in db.execute('PRAGMA table_info('+table+')')}
        for column in ('ip', 'country'):
            if column not in columns:
                db.execute('ALTER TABLE '+table+' ADD COLUMN '+column+' TEXT')
    return db


def fetch_worker(machine, cursor, now):
    records = []
    start = max(0, cursor - 60000)
    latest = cursor
    query = ('resource.type = "container" and resource.labels.container_group_name = "earnfm-us" '
             'and resource.labels.machine_id = "' + machine + '" and json_log.kind = "earnfm_sample"')
    # Small windows avoid Salad's capped pages and preserve delayed records.
    for _ in range(8):
        if start >= now:
            break
        end = min(now, start + 60000)
        items = request('/log-entries', {'query': query, 'start_time': iso(start), 'end_time': iso(end),
                                        'page_size': 100, 'sort_order': 'asc'}).get('items', [])
        if len(items) >= 100:
            raise RuntimeError('A telemetry window exceeded the log page limit')
        for item in items:
            parsed = parse_sample(item, machine)
            if parsed is not None:
                records.append(parsed)
                latest = max(latest, millis(item['time']))
        latest = max(latest, end)
        start = end
    return records, latest


def snapshot(db, target, inventory, observed_ms, error=None, provider=None):
    now = int(time.time() * 1000)
    latest_rows = db.execute('SELECT * FROM runs').fetchall()
    total = sum(row['total_rx'] + row['total_tx'] for row in latest_rows)
    latest = {}
    for row in latest_rows:
        if row['machine'] not in latest or row['end_ms'] > latest[row['machine']]['end_ms']:
            latest[row['machine']] = row
    workers = []
    provider = provider or {}
    online = {d['instance']: d for d in provider.get('devices', []) if d.get('instance')}
    for node in inventory:
        sample = latest.get(node['machine_id'])
        runtime_instance = sample['instance'] if sample else node['id']
        provider_ip = online.get(runtime_instance, {}).get('ip')
        public_ip = provider_ip or (sample['ip'] if sample else None)
        country = sample['country'] if sample and provider_ip and provider_ip == sample['ip'] else None
        window = db.execute('SELECT SUM((rx+tx)*1.0*(end_ms-MAX(start_ms,?))/(end_ms-start_ms)),SUM(end_ms-MAX(start_ms,?)) FROM samples WHERE run=? AND seq>0 AND valid=1 AND end_ms>start_ms AND end_ms>?', (sample['end_ms']-60000,sample['end_ms']-60000,sample['run'],sample['end_ms']-60000)).fetchone() if sample else (None,None)
        rate = window[0]/window[1] if window[1] else None
        workers.append({'instance': node['id'], 'machine': node['machine_id'], 'runtime_instance': runtime_instance, 'salad_state': node['state'],
                        'client_state': sample['state'] if sample else 'awaiting_sample',
                        'provider_online': runtime_instance in online and sample is not None and now-sample['end_ms'] < 90000 and not sample['final'] and sample['state'] == 'running',
                        'ip': public_ip, 'country': country,
                        'error': ('Connection failed: replacing after exhausted connection attempts or 30 seconds of repeated errors' if sample and sample['state'] == 'connection_error' else 'Provider cooldown: retries automatically after the required 24-hour wait' if sample and sample['state'] == 'rate_limited' else ''),
                        'sample_ms': sample['end_ms'] if sample else None,
                        'total_mb': (sample['total_rx'] + sample['total_tx']) / 1e6 if sample else None,
                        'kb_per_second': rate,
                        'final': bool(sample['final']) if sample else False})
    start = max(target.get('measurement_started_ms', now), now - 24 * 3600000)
    minutes = db.execute('''SELECT (end_ms-CASE WHEN end_ms>start_ms THEN 1 ELSE 0 END)/60000*60000 minute_ms, instance, machine,
      SUM(CASE WHEN valid=1 THEN rx+tx ELSE 0 END) bytes,
      SUM(CASE WHEN valid=1 THEN end_ms-start_ms ELSE 0 END) duration_ms FROM samples WHERE seq>0 AND end_ms>=?
      GROUP BY minute_ms,instance,machine ORDER BY minute_ms''', (start,)).fetchall()
    points = {}
    for row in minutes:
        point = points.setdefault(row['minute_ms'], {'time_ms': row['minute_ms'], 'mb': 0, 'duration_ms': 0, 'by_instance': {}})
        point['mb'] += row['bytes'] / 1e6
        point['duration_ms'] += row['duration_ms']
        point['by_instance'][row['instance']] = row['bytes'] / 1e6
    for point in points.values():
        point['partial'] = point['duration_ms'] < 60000 * target['desired']
    return {'generated_ms': now, 'inventory_ms': observed_ms, 'error': error,
            'test_started_ms': target.get('measurement_started_ms'), 'desired': target['desired'],
            'group': 'ssh3/default/earnfm-us', 'workers': workers, 'points': list(points.values()),
            'total_mb': total / 1e6, 'sample_count': db.execute('SELECT COUNT(*) FROM samples').fetchone()[0],
            'database_bytes': sum(p.stat().st_size for p in (DATA/'traffic.sqlite3', DATA/'traffic.sqlite3-wal') if p.exists()),
            'provider': provider,
            'basis': 'Measured eth0 RX + TX; includes client control traffic. Not provider-paid bandwidth.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True)
    lock = (DATA / 'recorder.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    db = database(DATA / 'traffic.sqlite3')
    inventory, observed = [], None
    departed = {}
    while True:
        began = time.monotonic()
        target = json.loads((DATA / 'target.json').read_text())
        error = None
        try:
            group = request('/projects/default/containers/earnfm-us')
            if group['id'] != target['id'] or group['container']['image'] != target['image']:
                raise RuntimeError('EarnFM deployment identity changed')
            inventory = request('/projects/default/containers/earnfm-us/instances').get('instances', [])
            observed = int(time.time() * 1000)
            cursors = dict(db.execute('SELECT machine,time_ms FROM cursors').fetchall())
            active = {n['machine_id'] for n in inventory}
            for node in inventory:
                cursors.setdefault(node['machine_id'], max(target.get('measurement_started_ms', observed), millis(node['update_time'])-60000))
            for machine in cursors:
                if machine in active:
                    departed.pop(machine, None)
                else:
                    departed.setdefault(machine, observed)
            with ThreadPoolExecutor(max_workers=3) as pool:
                jobs = {pool.submit(fetch_worker, machine, cursor, observed): machine for machine, cursor in cursors.items()}
                for job, machine in jobs.items():
                    try:
                        records, cursor = job.result()
                        with db:
                            for row in records:
                                db.execute('INSERT OR IGNORE INTO samples VALUES (' + ','.join('?' for _ in FIELDS) + ')', tuple(row[k] for k in FIELDS))
                                db.execute('INSERT INTO runs VALUES (' + ','.join('?' for _ in FIELDS) + ') ON CONFLICT(run) DO UPDATE SET ' + ','.join(k+'=excluded.'+k for k in FIELDS if k!='run') + ' WHERE excluded.seq>runs.seq', tuple(row[k] for k in FIELDS))
                            if machine in departed and observed-departed[machine] >= 60000 and cursor >= observed:
                                db.execute('DELETE FROM cursors WHERE machine=?', (machine,))
                                departed.pop(machine)
                            else:
                                db.execute('INSERT OR REPLACE INTO cursors VALUES (?,?)', (machine, cursor))
                    except Exception as exc:
                        error = type(exc).__name__ + ': ' + str(exc)
        except Exception as exc:
            error = type(exc).__name__ + ': ' + str(exc)
        output = snapshot(db, target, inventory, observed, error, provider_reading())
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        temporary = OUTPUT.with_suffix('.tmp')
        temporary.write_text(json.dumps(output, separators=(',', ':')))
        os.replace(temporary, OUTPUT)
        if args.once:
            print(json.dumps({'workers': len(output['workers']), 'samples': output['sample_count'], 'total_mb': output['total_mb'], 'error': error}))
            break
        time.sleep(max(1, 15 - (time.monotonic() - began)))
    db.close()


if __name__ == '__main__':
    main()
```
<!-- /FM_FILE -->

### `scripts/keychain-store.swift`

<!-- FM_FILE scripts/keychain-store.swift -->
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
<!-- /FM_FILE -->

### `dashboard/static/earnfm.html`

<!-- FM_FILE dashboard/static/earnfm.html -->
```html
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EF · EarnFM traffic</title><link rel="stylesheet" href="/styles.css">
<style>nav a{padding:5px 9px;color:#155e9e;text-decoration:none;border:1px solid #aaa;border-radius:2px}nav a[aria-current]{background:#ededed;color:#161616;font-weight:700}.ef-chart{width:100%;height:270px;display:block;border:1px solid #bbb}.ef-bar{fill:#1266ad;cursor:pointer}.ef-bar.partial{fill:#9abbd6}.ef-bar.selected{fill:#173f68;stroke:#000;stroke-width:2}.ef-table{min-width:860px}.ef-provider{padding:9px 0;border-block:1px solid #ddd;margin:10px 0}.ef-controls{display:flex;gap:18px;align-items:center;flex-wrap:wrap}.ef-controls label{font-size:12px}.ef-controls select{margin-left:6px}#efSummary{font-size:15px;font-weight:600}#efSelected{min-height:20px;font-size:12px}.ef-small{font-size:12px;color:#555}</style>
</head><body>
<header><h1>EF · EarnFM</h1><span id="efStatus" role="status">Loading recorded data…</span></header>
<nav aria-label="Services"><a href="/#hg1">Honeygain</a><a href="/#ps1">PacketStream</a><a href="/ef" aria-current="page">EF</a></nav>
<main><p id="efNotice" class="notice hidden" role="status"></p><p id="efSummary"></p><p id="efTime" class="ef-small"></p>
<div class="ef-provider"><span id="efEarnings">Fetching EarnFM’s credited reading…</span><p id="efProviderTime" class="ef-small"></p></div>
<div class="ef-controls"><h2>Network MB by minute</h2><label>Show<select id="efRange"><option value="60">Last hour</option><option value="180">Last 3 hours</option><option value="1440">Last 24 hours</option></select></label><a href="/earnfm.json" download="ef-recording.json">Download data</a></div>
<p class="ef-small">Actual interface RX + TX, including client control traffic. This graph is not paid bandwidth. Pale bars have partial recording coverage. Click a bar to see each server’s contribution.</p>
<svg id="efChart" class="ef-chart" role="img" aria-label="EarnFM network traffic by minute"></svg><p id="efSelected" aria-live="polite"></p>
<div class="table-scroll"><table class="ef-table"><thead><tr><th>Server / observed instance</th><th>EarnFM</th><th>Process / Salad</th><th>Recorded MB</th><th>KB/s</th><th>MB in selected minute</th><th>Last sample</th></tr></thead><tbody id="efWorkers"></tbody><tfoot id="efPrevious"></tfoot></table></div>
<p class="ef-small">Retries and reallocation run inside each container. This local page and its recorder only observe. Provider figures are account-wide gross credits; Salad costs have not been subtracted.</p>
</main>
<script>
'use strict';
const $=id=>document.getElementById(id),finite=n=>typeof n==='number'&&Number.isFinite(n);
const number=(n,d=3)=>finite(n)?n.toLocaleString(undefined,{maximumFractionDigits:d}):'—';
const when=n=>finite(n)?new Date(n).toLocaleString([],{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}):'—';
const age=n=>finite(n)?`${Math.max(0,Math.round((Date.now()-n)/1000))}s ago`:'Awaiting first sample';
let data=null,selected=null,pending=false,failed=false;
function element(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e}
function svg(tag,attrs,text){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e}
function draw(){
 if(!data)return;
 const chart=$('efChart'),width=Math.max(300,chart.clientWidth),height=270,left=58,right=12,top=18,bottom=42;
 chart.setAttribute('viewBox',`0 0 ${width} ${height}`);chart.replaceChildren();
 const end=Math.floor(Date.now()/60000)*60000,range=Number($('efRange').value),start=end-(range-1)*60000;
 const points=data.points.filter(p=>p.time_ms>=start&&p.time_ms<=end),maximum=Math.max(.001,...points.map(p=>p.mb));
 const w=width-left-right,h=height-top-bottom;
 for(let i=0;i<=4;i++){const y=top+h-i*h/4;chart.append(svg('line',{x1:left,y1:y,x2:width-right,y2:y,stroke:'#ddd'}),svg('text',{x:left-7,y:y+4,'text-anchor':'end','font-size':11,fill:'#555'},number(maximum*i/4)))}
 for(let i=0;i<=4;i++){const t=start+(end-start)*i/4,x=left+w*i/4;chart.append(svg('text',{x,y:height-13,'text-anchor':i===0?'start':i===4?'end':'middle','font-size':11,fill:'#555'},new Date(t).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',hour12:false})))}
 if(!points.length)chart.append(svg('text',{x:width/2,y:height/2,'text-anchor':'middle','font-size':14,fill:'#666'},'Waiting for recorded traffic samples'));
 for(const p of points){const x=left+(p.time_ms-start)/60000*w/range,bh=p.mb/maximum*h;
  const bar=svg('rect',{x,y:top+h-Math.max(1,bh),width:Math.max(1,w/range-1),height:Math.max(1,bh),class:`ef-bar ${p.partial?'partial':''} ${selected===p.time_ms?'selected':''}`,tabindex:0,role:'button','aria-label':`${when(p.time_ms)}: ${number(p.mb)} MB${p.partial?', partial coverage':''}`});
  bar.append(svg('title',{},`${when(p.time_ms)} · ${number(p.mb,6)} MB${p.partial?' · partial recording':''}`));
  const choose=()=>{selected=p.time_ms;draw();rows()};bar.addEventListener('click',choose);bar.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose()}});chart.append(bar)
 }
}
function freshWorker(w){return !failed&&finite(w.sample_ms)&&Date.now()-w.sample_ms<90000&&!w.final}
function rows(){
 if(!data)return;
 const body=$('efWorkers');body.replaceChildren();const point=data.points.find(p=>p.time_ms===selected);
 const providerFresh=!failed&&finite(data.provider?.observed_ms)&&Date.now()-data.provider.observed_ms<180000&&!data.provider.error;
 $('efSelected').textContent=point?`${when(point.time_ms)} · ${number(point.mb,6)} MB recorded${point.partial?' · partial coverage':''}`:'Select a minute in the graph.';
 let shown=0;
 data.workers.forEach((w,i)=>{const row=element('tr'),name=element('td',`${i+1}. ${w.machine.slice(0,12)}`);name.append(element('small',w.runtime_instance||w.instance));
  if(w.runtime_instance&&w.runtime_instance!==w.instance)name.append(element('small',`Salad inventory ID: ${w.instance}`));
  if(w.ip)name.append(element('small',w.ip+(w.country?' · '+w.country:' · country unverified')));
  const fresh=freshWorker(w);
  const state=({starting:'Starting',running:'Process up',retrying:'Retrying',connection_error:'Connection errors · recovery active',rate_limited:'Rate limited · 24h pause',stopping:'Stopping',reallocating:'Replacing',awaiting_sample:'Awaiting current-instance sample'})[w.client_state]||w.client_state;
  const share=point?.by_instance[w.runtime_instance||w.instance]||0;shown+=share;
  row.append(name,element('td',providerFresh&&fresh?(w.provider_online?'Online':'Not confirmed'):'Reading pending',providerFresh&&fresh&&w.provider_online?'ok':'stale'),element('td',`${state} / ${w.salad_state}`,fresh&&w.client_state==='running'?'ok':'stale'),element('td',number(w.total_mb)),element('td',fresh?number(w.kb_per_second):'—'),element('td',point?number(share,6):'—'),element('td',age(w.sample_ms)));
  body.append(row)
 });
 for(let i=data.workers.length;i<data.desired;i++){const row=element('tr');row.append(element('td',`${i+1}. Allocating`));for(let j=0;j<6;j++)row.append(element('td','—'));body.append(row)}
 $('efPrevious').replaceChildren();
 if(point&&point.mb-shown>.000001){const row=element('tr'),label=element('td','Previously allocated servers');label.colSpan=5;row.append(label,element('td',number(point.mb-shown,6)),element('td','Historical contribution'));$('efPrevious').append(row)}
}
function render(){
 if(!data)return;
 const now=Date.now(),fresh=!failed&&now-data.generated_ms<60000&&finite(data.inventory_ms)&&now-data.inventory_ms<90000;
 const p=data.provider||{},providerFresh=!failed&&finite(p.observed_ms)&&now-p.observed_ms<180000&&!p.error;
 $('efStatus').textContent=failed?'Cannot refresh EF · last observations shown':fresh?`Recorder updated ${age(data.generated_ms)}`:`Recording stale · ${age(data.generated_ms)}`;
 const warnings=[data.error,p.error].filter(Boolean);$('efNotice').textContent=warnings.join(' · ');$('efNotice').classList.toggle('hidden',!warnings.length);
 const online=providerFresh?data.workers.filter(w=>w.provider_online&&freshWorker(w)).length:null;
 $('efSummary').textContent=`${data.workers.filter(w=>w.salad_state==='running').length}/${data.desired} containers running${online!==null?` · ${online} confirmed online by EarnFM`:''} · ${number(data.total_mb,6)} MB recorded`;
 $('efTime').textContent=`SSH3 · Test started ${when(data.test_started_ms)} · ${number(data.sample_count,0)} source samples saved`;
 $('efEarnings').textContent=finite(p.balance)?`EarnFM balance $${number(p.balance,6)} · credited total ${number(p.gb,6)} GB · change $${number(p.earned,6)} / ${number(p.credited_mb,6)} MB since the recorded provider baseline`:'Awaiting the provider’s credited reading';
 $('efProviderTime').textContent=finite(p.observed_ms)?`Provider reading ${when(p.observed_ms)}${providerFresh?'':' · last recorded'}; baseline ${when(p.baseline_ms)}. Gross account figures, not net profit.`:'';
 if(selected===null&&data.points.length)selected=data.points.at(-1).time_ms;
 draw();rows();
}
async function refresh(){if(pending)return;pending=true;try{const response=await fetch('/ef.json',{cache:'no-store'});if(!response.ok)throw Error();data=await response.json();failed=false;render()}catch{failed=true;$('efStatus').textContent='Cannot read the EF recorder';if(data)render()}finally{pending=false}}
$('efRange').addEventListener('change',draw);window.addEventListener('resize',draw);refresh();setInterval(refresh,2000);
</script></body></html>
```
<!-- /FM_FILE -->

### `dashboard/static/styles.css`

<!-- FM_FILE dashboard/static/styles.css -->
```css
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
```
<!-- /FM_FILE -->

### `historical-record.json`

<!-- FM_FILE historical-record.json -->
```json
{
  "snapshot_time_ms": 1788756842730,
  "cloud_group_id": "90078bc1-4410-46cd-8411-6ebb8968eec2",
  "cloud_version": 8,
  "create_time": "2026-09-06T20:33:32.2242869+00:00",
  "cloud_update_time": "2026-09-07T02:29:15.9086685+00:00",
  "original_provider_baseline": {
    "time_ms": 1788730420050,
    "balance": 0.041831,
    "gb": 0.418308
  },
  "stale_target_file_reference": {
    "id": "90078bc1-4410-46cd-8411-6ebb8968eec2",
    "organization": "ssh3",
    "project": "default",
    "group": "earnfm-us",
    "desired": 10,
    "image": "docker.io/earnfm/earnfm-client@sha256:99a9feaa3dfab9e858012994fa1f922523f41b098e6b1cd9c9e9fca9286c3843",
    "created_at": "2026-09-06T20:33:33.192945+00:00",
    "phase": "measuring",
    "display_name": "EF",
    "measurement_started_ms": 1788729704607,
    "agent_sha256": "64ff95194f8ff6a2d3afdfbddc5b39ec2298d1b70f686e67f5c1ec399146bd86",
    "version": 6,
    "cooldowns": {
      "640f0410-7d89-4c51-a507-17cdd7acbac1": 1788821197,
      "55da989f-fdeb-5a51-b95b-1627b227f1be": 1788821961
    },
    "recovery_started_ms": 1788743729183,
    "recovery_baseline": {
      "observed_ms": 1788743674255,
      "balance": 0.051763,
      "gb": 0.517626
    }
  },
  "observation": {
    "running": 10,
    "provider_confirmed": 10,
    "paused": 0,
    "raw_total_mb": 1326.098141,
    "provider": {
      "checked_ms": 1788756824057,
      "observed_ms": 1788756824387,
      "balance": 0.090613,
      "gb": 0.906134,
      "earned": 0.048782,
      "credited_mb": 487.826,
      "baseline_ms": 1788730420050,
      "error": null
    }
  }
}
```
<!-- /FM_FILE -->

### `manifest.json`

<!-- FM_FILE manifest.json -->
```json
{
  "dashboard/static/earnfm.html": "9768ffd672bff19c43cbd96effca4f0b4617f775a28e1b5241c92efb39c4a458",
  "dashboard/static/styles.css": "b7c37ee6cd698d1b327a51a62849a51d817435d166170a70791ebb6e68d7c9eb",
  "earnfm-monitor/start.sh": "ffe70604216fd91769da8cfee6ecf4699b4dd3890b42bd42318eb987376860aa",
  "fm-rebuild.py": "93cd6432c5145b2b0b35a089ffbcb621178bad1a83b150a1959b6aa5e9680bf1",
  "historical-record.json": "f838ea2379b340917ab62699914b031d105dfb3fd419b4d73ff06b923c562dfb",
  "rebuild-config.json": "860a85d6eec74fbd2a94d08e953f152197f4a53e4c3165aebff10ba7fccb0667",
  "scripts/earnfm-recorder.py": "c75d268026c83b041c5d9634a7a6bfd4e170f32c8fc0db886968889a610fa75d",
  "scripts/keychain-store.swift": "490eadaf1afb87a0f64bf6248254ccc48ac1171af9e2fc4c796c74c12c5ca045"
}
```
<!-- /FM_FILE -->

