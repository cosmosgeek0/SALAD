# Record EarnApp measurements


## Active Linux service

Production uses `/opt/salad/EarnApp/earnapp-recorder.py` and the unchanged history directory `/home/salad/.hg1/earnapp`. `salad-earnapp.conf` is installed as `/etc/systemd/system/salad-earnapp.service.d/earnapp.conf`. It preserves the existing service's user/security/restart settings and selects the canonical source and existing credential helper. The earlier `/opt/salad/scripts/earnapp-recorder.py` path is a compatibility link.

This drop-in assumes the shared website's existing `salad-earnapp.service`, `salad` user and configured helper. For a deleted/rebuilt host, first follow [Website setup](../Website/SETUP.md), then copy this whole EarnApp folder to `/opt/salad/EarnApp` and install the drop-in. Preserve or consistently restore the complete SQLite database and its cursor; missing history cannot be reconstructed from source files.

On the recorder host:

```bash
sudo mkdir -p /etc/systemd/system/salad-earnapp.service.d
sudo cp /opt/salad/EarnApp/salad-earnapp.conf /etc/systemd/system/salad-earnapp.service.d/earnapp.conf
sudo systemctl daemon-reload
sudo systemctl restart salad-earnapp.service
sudo systemctl status salad-earnapp.service
```

The workload emits original counters/native state about every ten seconds. The recorder polls about every fifteen seconds, retains complete source intervals and recovery events, and reads provider credits/status separately. The public graph includes every valid recorded interval across retained runs, with each original country preserved. `total_mb` and its compatibility alias `all_recorded_mb` cover the full saved history; `received_mb` and `sent_mb` split its measured incoming and outgoing bytes. Current deployment remains US-only.

`--once` collects and publishes without issuing provider-based recovery requests. The normal service applies the policies described in [RECOVERY.md](RECOVERY.md). `samples` stores traffic, `events` stores original native/controller actions, `provider` stores account observations, and `meta` holds cursors, policy baselines and verified replacement outcomes. Request acceptance and replacement verification are separate fields.

The sections below retain the optional Mac/local-rebuild workflow. Do not enable a Mac writer alongside the active AWS writer.

The [collector](earnapp-recorder.py) reads Salad inventory and logs, saves original source times and run identities, reads EarnApp credit/status, and atomically publishes `data/view.json`. The shared website consumes that reading through `/api/earnapp`.

Traffic and provider credit are separate measurements. A browser does not need to remain open while the saved account session is valid.

The dashboard emphasizes measured incoming/outgoing network MB and actual provider earnings. EarnApp does not publish credited network MB or a per-GB conversion rate in the current feed, so credited traffic remains Not reported. Provider usage time stays in the original saved observations and is never converted into bytes. The graph uses decimal MB and defaults to a labeled logarithmic scale; Linear is also available. Gray baseline marks are measured zero, while gaps have no samples. Totals include historical countries; new deployment remains US-only. Counters cover the saved intervals after the sampler baseline, not unobserved transfer before it.

## Files and access

Run commands below from this folder:

```bash
cd "$HOME/Desktop/salad/EarnApp"
```

| Setting | Default or purpose |
|---|---|
| `EARNAPP_DATA_DIR` | This folder's `data/` directory |
| `EARNAPP_ORGANIZATION` / `EARNAPP_PROJECT` / `EARNAPP_GROUP` | `cosmosgeeketh` / `default` / `earnapp-live` |
| `EARNAPP_UUID` | The saved device in [SETUP.md](SETUP.md) |
| `SALAD_API_KEY` | Salad access supplied through the process environment |
| `EARNAPP_COOKIE` / `EARNAPP_XSRF_TOKEN` | EarnApp account access supplied through the process environment |
| `SALAD_KEY_HELPER` | Optional existing credential helper; the current Mac defaults to the shared dashboard's `.runtime/keychain-store` |

The current Mac helper uses Keychain entries `salad-bandwidth-api` and `earnapp-read-session`. On a clean Mac, the [shared website setup](../Website/SETUP.md) restores the source bundle, builds that helper and configures Salad access. Another host can supply the environment variables directly.

Keep credential values in Keychain or the service manager's protected environment, outside this folder. The service configuration stored here contains paths and settings, not credentials.

## Read or run the collector

Read the saved result without starting anything:

```bash
cat data/view.json
```

To deliberately collect an on-demand reading:

```bash
python3 -B earnapp-recorder.py --once
```

To run continuously in the current terminal:

```bash
python3 -B earnapp-recorder.py
```

Run only one collector for this data directory. Its lock rejects duplicate writers. The `--startup` option only prints [startup.sh](startup.sh); it does not deploy or start a client.

The saved database and logs are in `data/`. A failed account refresh keeps the last verified credit and its timestamp while reporting the error. Missing traffic is not filled with zero.

## Mac service

[com.cosmosgeek.earnapp-recorder.plist](com.cosmosgeek.earnapp-recorder.plist) is the actual service configuration. The matching entry in `~/Library/LaunchAgents` is a link to it.

The service is currently disabled. When the owner chooses to activate it on this Mac:

```bash
launchctl enable "gui/$(id -u)/com.cosmosgeek.earnapp-recorder"
launchctl bootstrap "gui/$(id -u)" "$PWD/com.cosmosgeek.earnapp-recorder.plist"
```

If it is already loaded, reload its source with:

```bash
launchctl kickstart -k "gui/$(id -u)/com.cosmosgeek.earnapp-recorder"
```

Check its status with `launchctl print "gui/$(id -u)/com.cosmosgeek.earnapp-recorder"`. `RunAtLoad` and `KeepAlive` apply while the job is enabled; an explicit disabled setting prevents automatic recording.

After copying this folder to another Mac location, update the service paths before loading it:

```bash
python3 - <<'PY'
from pathlib import Path
import os, plistlib, sys
root = Path.cwd().resolve()
service = root / 'com.cosmosgeek.earnapp-recorder.plist'
config = plistlib.loads(service.read_bytes())
config['ProgramArguments'] = [sys.executable, str(root / 'earnapp-recorder.py')]
config['WorkingDirectory'] = str(root)
env = config['EnvironmentVariables']
env['EARNAPP_DATA_DIR'] = str(root / 'data')
env['SALAD_KEY_HELPER'] = os.environ.get('SALAD_KEY_HELPER', str(
    Path.home() / 'Library/Application Support/Salad Bandwidth Dashboard/.runtime/keychain-store'))
config['StandardOutPath'] = str(root / 'data/recorder.out.log')
config['StandardErrorPath'] = str(root / 'data/recorder.err.log')
(root / 'data').mkdir(exist_ok=True, mode=0o700)
service.write_bytes(plistlib.dumps(config, sort_keys=False))
service.chmod(0o600)
PY
```

For a new installation, create links at the locations the OS and shared dashboard expect:

```bash
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.hg1"
ln -s "$PWD/com.cosmosgeek.earnapp-recorder.plist" "$HOME/Library/LaunchAgents/com.cosmosgeek.earnapp-recorder.plist"
ln -s "$PWD/data" "$HOME/.hg1/earnapp"
```

These links already exist on the reorganized Mac. Do not overwrite an older real history directory; preserve it when relocating. On Linux, configure the recorder's environment and run it under that host's service manager.

## Connect or renew the EarnApp account

1. Open the correct signed-in Chrome profile's EarnApp **Passive Income** page.
2. Open **More Tools → Developer Tools → Network**, reload, and select the **devices** request at `/dashboard/api/devices`.
3. Find the **Cookie** and **xsrf-token** values under **Request Headers**.
4. With the existing Keychain helper available, run:

```bash
python3 -B earnapp-recorder.py --connect-provider
```

Paste only into its hidden prompts. The next account refresh reads the renewed Keychain session. For environment-based credentials, update `EARNAPP_COOKIE` and `EARNAPP_XSRF_TOKEN` in the service manager and restart that collector.

Verify a recent `provider_observed_ms`, a credit note without an authentication error, and the provider's reported device total. Online status is queried separately from credit; neither is a payout confirmation.
