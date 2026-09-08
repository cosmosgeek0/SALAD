# Website operations

Start at [CONNECTIONS.md](CONNECTIONS.md) for the instance, domain and SSM/SSH command. The routine SSH account has only the documented fixed credential-renewal exceptions, not general sudo. Execute other privileged examples below through the IAM-authorized AWS Run Command root path documented there; do not restore blanket sudo. Production runs on AWS; the disabled Mac recorders should stay disabled.

## Services

Every unit below is provided in [linux/systemd/](linux/systemd/). Application paths are relative to `/opt/salad`; state paths are below `/home/salad/.hg1`.

| Unit | Executable / purpose | State |
|---|---|---|
| `salad-dashboard.service` | `python3 -m dashboard.server`; HTTP API and shared static UI | Reads all published views and ledgers |
| `salad-hg-provider.service` | `scripts/hg-provider-observer.py --interval 60` | `hg-fleet` provider readings |
| `salad-hg-fleet.service` | `scripts/hg-fleet-observer.py --interval 60` | `hg-fleet` native observations |
| `salad-fleet.service` | `fleet-test-recorder.py run` | `fleet-tests` ledger and counters |
| `salad-packetstream.service` | `ps1-native-recorder.py` | `packetstream` census and minute database |
| `salad-proxyrack.service` | `proxyrack.py observe` | `proxyrack` |
| `salad-repocket.service` | `repocket-monitor/observe.py` | `repocket` |
| `salad-repocket-provider.service` | `repocket-monitor/provider.py`; authenticated account earnings | `repocket/provider.sqlite3`, `provider.json`, `provider-status.json` |
| `salad-earnfm.service` | `scripts/earnfm-recorder.py` | `earnfm`; see published-output path in DATA |
| `salad-traffmonetizer.service` | `traffmonetizer/observer.py` | `traffmonetizer` |
| `salad-pawns.service` | `pawns/observe.py` | `pawns` |
| `salad-earnapp.service` | `EarnApp/earnapp-recorder.py`, selected by its supplied service drop-in | `earnapp` |
| `salad-grass.service` | `scripts/grass-recorder.py` | `grass` |
| `cloudflared-salad.service` | `/usr/local/bin/cloudflared`; outbound tunnel | Private token in `/etc/cloudflared-salad` |

Bindings, provider access and initial baselines must exist before starting their corresponding recorders. Missing protocol inputs do not justify manufacturing a JSON reading. [SETUP.md](SETUP.md) gives the initialization order.

Recorder units now deny privilege escalation, capabilities, device access and kernel/namespace changes. System files and home directories are read-only inside each recorder's service namespace; only its protocol data directory and `/run/salad-credentials` are writable. The shared fleet recorder also writes the existing top-level `costs.sqlite3` and its WAL files, so its data-root write exception is paired with read-only mounts over all other protocol directories and the compatibility database. Preserve these exceptions during recovery; do not remove a guard merely because a new producer writes to an undocumented path.

These are process and filesystem restrictions, not separate provider identities: the recorders still use the existing `salad` account and shared credential cache. Full credential separation is not established by these unit settings. Restart only the affected recorder after a unit change, then verify its background workers and actual output timestamps; an active main process can conceal a failed cost/metadata thread.

## Read the current system

```sh
sudo systemctl --no-pager --type=service --all 'salad-*.service' cloudflared-salad.service
sudo systemctl show salad-dashboard.service -p User -p Group -p ExecStart -p ActiveEnterTimestamp
sudo ss -lntp
sudo ss -lxnp
df -h / /home/salad
```

For one affected recorder, replace the unit name in this example:

```sh
sudo systemctl status salad-traffmonetizer.service --no-pager
sudo journalctl -u salad-traffmonetizer.service --since '15 minutes ago' --no-pager
```

Do not print credential files or unfiltered Salad group/environment responses into a task. The service code, safe status JSON and named logs normally identify the failed step.

## Install a finished change

Read the complete affected source and coordinate one editor for shared files. Compare the running file with the intended version, stage the finished file through SCP, then install only that file.

Example for a finished static JavaScript change, after staging it as shown in CONNECTIONS:

```sh
sudo install -o root -g root -m 0644 /tmp/fleet-test.js /opt/salad/dashboard/static/fleet-test.js
sha256sum /opt/salad/dashboard/static/fleet-test.js
rm /tmp/fleet-test.js
```

Static changes require a browser reload, not a shared service restart. A Python module change requires restarting only its owning unit after syntax/review checks; the UI's individual module bind mounts are refreshed by its restart. A unit change additionally requires `sudo systemctl daemon-reload`. Preserve root ownership, named read ACLs and the captured isolation settings.

After the live flow passes, synchronize the verified file into its protocol source and `Website/source`, update the relevant SHA256SUMS entries, and update connection/unit documentation when those contracts changed. Keep pending edits out of a release backup. The [recovery rehearsal](RECOVERY.md#verify-the-restored-site) is the final check for a restorable snapshot.

## Diagnose the layer that failed

| Symptom | Check |
|---|---|
| Cloudflare sign-in or security-key screen | Expected Access boundary; use the owner identity and enrolled key |
| Cloudflare error / tunnel unhealthy | `cloudflared-salad` log, token-file readability, outbound connectivity and hostname route |
| Tunnel healthy but origin error | Website unit, its listening endpoint and the route's service URL must agree |
| All pages hang | Check actual CPU credit mode, process load and slow history scans; do not reapply a CPU cap merely to reduce a percentage |
| One page has old data | Its recorder log, actual source timestamps and target binding |
| A running container is unverified | Native status is missing/old or a provider has not confirmed it; inspect the protocol's own evidence |
| Traffic updates but credits do not | Provider account session/feed is separate; preserve the dated reading or Not reported |
| New group has old totals or no measurements | Check group/run IDs and the ledger boundary; do not reset data to hide a mismatch |
| SSM cannot connect | IAM session permission, instance role, SSM Agent, outbound HTTPS, local Session Manager plugin; use owner console access if the routine CLI is insufficient |

The domain's HTTPS certificate is served by Cloudflare. The origin is `/run/salad-ui/ui.sock`; there is no public or loopback HTTP listener for the website. A bare socket request without an Access assertion returns 403, including from the connector user. Verify real data through the owner's signed-in public browser; do not copy session tokens into commands. Changing EC2's public IP does not require pointing DNS at that IP.

Public acceptance means every configured tab loads, shows its chart/table, and advances with actual recorder observations. A worker/provider warning can be real even when the page works; HTTP 200 alone is not evidence of fresh measurements.

## Browser refresh and backend cache behavior

The server adds each current file's SHA-256 version to the shared HTML's CSS and script URLs. Matching versioned static assets use `Cache-Control: private, max-age=31536000, immutable`; HTML and unversioned assets use private revalidation. A static deployment changes the generated URLs automatically, so it requires no manual cache purge or filename copy. Measurement APIs remain `no-store`, and every network request still passes the existing Access/Unix-UID validation. Cached code contains no measurements or credentials.

The server reuses parsed view files only while their inode/size/mtime signature matches. Minute summaries invalidate on ledger changes or minute rollover. HG verifies the retained prefix before treating file growth as an append, keeps its byte/row bounds before decoding, retries partial lines, and retains the full original source lookup needed by archives. These are process caches: restarting the dashboard rebuilds them from preserved data; it does not reset recording.

`dashboard.traffmonetizer.snapshot(source=None)` accepts the server's cached published view and copies mutable worker/provider fields before recalculating freshness. Preserve this optional argument when integrating protocol freshness changes. Replacing it with a zero-argument function breaks the shared API caller.
