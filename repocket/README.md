# RP — bandwidth reel

Source and recovery package for the Repocket containers and monitoring page. Keep this whole folder together, and keep a complete backup copy outside this computer.

The recorder/provider-reader source in this backup is synchronized with the deployed `1c70638` website release, including its database indexes. Use `SHA256SUMS` for current package integrity; dated checks in the guides describe the exact revisions tested at those times.

## Start here

1. Read [Deployment](docs/DEPLOYMENT.md) to recreate the ten-container group or reconnect to one that still exists.
2. Read [Monitoring](docs/MONITORING.md) to run the recorder and page, then [Provider earnings](docs/PROVIDER.md) to connect the account privately.
3. Read [Worker behavior](docs/WORKER.md) for the exact captured configuration, fixes and automatic replacement rules.
4. Read [Backups and troubleshooting](docs/RECOVERY.md) for preserving the image, credentials and history.
5. Read [Verification](docs/VERIFICATION.md) for measured checks and how to verify the package.

## Files

| Path | Purpose |
|---|---|
| `repocket-monitor/start.js` | Exact captured cloud worker: client fixes, measurements and self-reallocation |
| `repocket-monitor/observe.py` | Read-only Salad log recorder, deployed on AWS |
| `repocket-monitor/provider.py` | Automatic account earnings reader with renewable access |
| `scripts/connect-provider.sh` | Hidden credential entry into AWS Secrets Manager |
| `systemd/` | The separate provider earnings service |
| `restore-control.py` | Create, attach, inspect, start and stop the documented group |
| `restore-dashboard.py` | Start the preserved RP monitoring page without other provider pollers |
| `dashboard/` | Existing shared page assets and its required Python modules |
| `scripts/` | macOS Keychain helper source and setup command |
| `docs/` | Short guides separated by task |
| `tests/` | Offline recording, freshness and worker-recovery regressions |
| `SHA256SUMS` | Integrity checks for the package files |

Start from this folder:

```bash
cd "$HOME/Desktop/salad/repocket"
shasum -a 256 -c SHA256SUMS
```

No source extraction, Codex session or private repository is required. The cloud setup uses the pinned official image and your own Salad/Repocket account access. Real credentials and historical data are not included.

This is the **2026-09-07 recovery snapshot** of worker telemetry label 12, deployed in Salad configuration version 16. The create recipe retains its original US placement; the separate live country trial can change placement without changing the worker. Inspect current settings before restoring over an experiment. It recreates the captured code, configuration, monitoring and replacement policy. Hosts, IPs, traffic, earnings and provider availability are variable and cannot be guaranteed to repeat. The worker's SHA-256 is `937d35e7c59fdd9c2afac80ffb3f45fbf2fbc8f06e21d43c3f66fe6a03a7ae8b`.

Edit source in its actual files and instructions in `docs/`; keep code separate from the guides. Temporary work for RP belongs inside this folder and should be removed when finished. Existing live runtime locations are listed in [Monitoring](docs/MONITORING.md#existing-operational-locations); they remain separate from this editable package.

Production recording runs on AWS Mumbai (`salad-repocket.service`), not on the Mac. The current recorder preserves original/receipt clocks and sequence conflicts, publishes the chart once per collection, and separates native, network and recovery freshness. See [Monitoring](docs/MONITORING.md).

The provider service is installed and verified with the owner’s existing authenticated session. Its 60-second polling interval is our checking schedule, not a claimed Repocket settlement interval. See [Provider earnings](docs/PROVIDER.md).
