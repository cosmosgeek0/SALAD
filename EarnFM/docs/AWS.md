# EarnFM on AWS

Production uses the shared Mumbai host documented in [Website operations](../../Website/OPERATIONS.md). The Mac is an optional recovery workstation; routine client recovery and recording do not require it. Keep the retired Mac LaunchAgents disabled while AWS owns collection.

| Component | Production location |
|---|---|
| Recorder source | `/opt/salad/scripts/earnfm-recorder.py` |
| Service / user | `salad-earnfm.service` / `salad` |
| Database, cursors, target, provider baseline | `/home/salad/.hg1/earnfm/` |
| Published snapshot | `/home/salad/.hg1/earnfm/view.json` |
| Credential adapter | `/opt/salad/.runtime/keychain-store` |
| Public API / page | `https://salad.cosmosgeek.org/api/earnfm` / `#earnfm` |

The existing credential adapter reads the authorized Secrets Manager entries through the host role and a private RAM cache. Keep that adapter and the existing systemd security settings. The Salad management key never enters the client container or browser. The client container receives only its EarnFM Docker credential and policy settings; its reallocation request uses Salad's instance metadata service.

## Reconstruct the production integration

1. Restore the shared AWS host, service account, Secrets Manager adapter, access controls, shared server and domain using the Website package. This protocol package does not replace those host-wide components.
2. Restore this complete EarnFM folder to `/opt/salad/EarnFM`, with code owned by root and not writable by the recorder. Supply the Salad API and EarnFM reader services listed in [Setup](SETUP.md) through the host's adapter. Updating an existing group preserves its current Docker credential if the optional `earnfm-api-key` entry is unavailable; creating a fresh group requires that client credential too. Do not install the macOS Swift helper on Linux.
3. Restore a consistent matching EarnFM data backup, including `target.json` and `provider-baseline.json`, to `/home/salad/.hg1/earnfm`. Keep the directory owned by `salad` and preserve the Website owner's read ACL for `view.json`. Do not reset an active experiment merely to install new code.
4. Install the verified `EarnFM/scripts/earnfm-recorder.py` to `/opt/salad/scripts/earnfm-recorder.py` as root:root mode 0644. The existing unit runs it as `salad`; restart only `salad-earnfm.service`. Its schema migration preserves original `samples`, `runs`, and legacy cursors and adds the cache, receipt details, provider history, recovery ledger and rejected-record ledger.
5. The shared server reads `view.json` for `/api/earnfm`. Use the updated EarnFM normalization branch in the Website source bundle. It reads `recorded_duration_ms`, historical `history_nodes` / `points[].contributions`, provider observation times and `recent_recovery`. The recorder also preserves `points[].by_instance` for older page versions during rollout.

For an intentional cloud update from that restored host, run the protocol CLI as `salad` with the existing credential adapter. Read configuration before changing it:

```sh
sudo -u salad env EARNFM_KEY_HELPER=/opt/salad/.runtime/keychain-store python3 -B /opt/salad/EarnFM/earnfm.py inspect
sudo -u salad env EARNFM_KEY_HELPER=/opt/salad/.runtime/keychain-store python3 -B /opt/salad/EarnFM/earnfm.py deploy --update
```

The update retains current country placement, `EARNFM_COUNTRY`, unrelated environment variables, unexpired cooldowns, group identity, measurement start and baseline. It still enforces the intended ten replicas, pinned image and documented resource allocation. It stops if the group version changes during preparation. A single-country placement and matching uppercase `EARNFM_COUNTRY` are required; coordinate any active country trial before changing them.

The group name `earnfm-us` is an existing identifier, not proof of its current country. The country trial may change placement while preserving that name. Read live `country_codes`, current native samples and provider IPs.

## Check and roll back

```sh
sudo systemctl status salad-earnfm.service --no-pager
sudo journalctl -u salad-earnfm.service -n 40 --no-pager
sudo -u salad python3 - <<'PY'
import json, time
from pathlib import Path
p=Path('/home/salad/.hg1/earnfm/view.json')
v=json.loads(p.read_text())
print({k:v.get(k) for k in ('generated_ms','inventory_ms','sample_count','collection','error','provider_history','telemetry_rejections')})
print('Snapshot age seconds:',round(time.time()-v['generated_ms']/1000))
PY
```

Before installing, save the prior recorder and a consistent database backup with the target and provider baseline. Roll back code if the service cannot publish. The added tables do not alter the original fifteen sample columns, so the previous recorder can continue with the preserved database; investigate any migration error before retrying. Roll back a cloud command only after checking the live version, country trial and unexpired cooldowns. A saved source file cannot undo an already requested machine replacement.
