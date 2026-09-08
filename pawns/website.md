# Website and saved Pawns data

[Start here](README.md) · [Check the cloud client](setup.md#verify-the-current-deployment)

## Current website

Open [Pawns on the bandwidth website](https://salad.cosmosgeek.org/pawns-app). Production was moved to Mumbai; the old Mac collectors were unloaded. The live server keeps its own installed collector and measurements. Local source organization does not redeploy or restart it.

The complete shared website source and Linux recovery instructions start at [Website](../Website/README.md). Its [Recovery](../Website/RECOVERY.md), [Setup](../Website/SETUP.md) and [Operations](../Website/OPERATIONS.md) guides restore the host, credential access and services. The Pawns service is `salad-pawns.service`, its source is `/opt/salad/pawns/observe.py`, and its state is `/home/salad/.hg1/pawns`. Keep the disabled Mac recorders disabled.

## What the collector records

`run.py` emits sanitized `PAWNS_SAMPLE` records with instance/group identity, native RX/TX deltas, original interval times and the last SDK callback state. Its configured interval is ten seconds. Samples close actual counter intervals, including the final interval on orderly shutdown/recovery. Counter decreases start a new baseline and invalidate the reset interval. Invalid or cross-IP boundaries stay excluded. The actual runtime instance and machine identity take precedence over stale Salad log labels.

`observe.py` uses the shared website's `dashboard.salad_api` and `dashboard.native_network` modules. It reads Salad logs using the configured `salad-bandwidth-api` secret through `/opt/salad/.runtime/keychain-store`; follow Website Setup's hidden credential prompt. It does not need a Pawns password on the recorder host. Its default cloud target is `cosmosgeeketh/default/pawns`; explicit `--organization`, `--project` and `--group` arguments select another authorized target.

The collector rejects missing/mismatched cloud group IDs and malformed records while continuing with valid records. It deduplicates by group, instance, run and sequence. Replayed legacy records are reconciled to their runtime identity without adding their bytes again or refreshing their first receipt time. Minute splits are estimates based on elapsed overlap. Freshness uses original sample and receipt times, so rereading an old record does not make it fresh. Salad's original `time` and `receive_time` strings are retained as `salad_time` and `salad_receive_time`: sample delivery metadata uses `SAMPLE_SOURCE` rows in `pawns_events`; provider and recovery rows retain the fields directly. Replaying retained logs fills each missing delivery timestamp independently and preserves any already recorded timestamp. It does not change recorded bytes, provider amounts or their first local receipt times.

The chart records raw network traffic. Each current row shows the current run's sum of valid recorded interval durations and bytes; group totals and the chart retain departed runs. **Connected** requires a running SDK, a running Salad instance, fresh measurements and a fresh provider observation of that IP as active. Unknown provider state remains unverified instead of becoming a failure or a fabricated zero.

`PAWNS_PROVIDER` records come from `/api/v1/users/me`, `/api/v1/users/me/balance` and the paginated `/api/v1/users/me/devices` endpoint. Provider checks are configured every sixty seconds after the preceding result, respecting a longer Retry-After. The consumer app labels `traffic_sold` in GB. The site shows that provider account total and the reported `money_details.shared` dollar amount, with the observation date and account scope. It never assigns these account totals to a worker or the chart window. A change since the provider baseline requires a later reading; a decrease starts a new baseline so no credited delta crosses a reset.

The existing `traffic.sqlite3` keeps its network ledger and cursor. The additional `pawns_events` table stores provider observations and recovery events, plus current per-run SDK/deadline details. Accepted requests and confirmed outcomes are separate. New healthy runtime generations without a matching request are recorded as observed restarts or machine changes; their cause is not guessed. Old network records are retained through this schema addition. Source, receipt and provider clocks remain separate; refreshing the site does not refresh old evidence. Provider records also retain the idle observation state. The configured 30-minute observation threshold never replaces a healthy connected node. Progress or unavailable/ambiguous evidence resets the observation window.

## Local history now lives here

The retired Mac collector's saved files are in `data/`, which is preserved separately and excluded from the source repository. This is historical local data, not a live mirror of Mumbai.

| File | Meaning |
|---|---|
| `data/traffic.sqlite3` | Saved sample ledger and collector cursor |
| `data/traffic.sqlite3-wal` and `data/traffic.sqlite3-shm`, when present | SQLite companion files; keep them with the database during a stopped-writer file copy |
| `data/view.json` | Last saved local snapshot, with its original timestamps |

The old `~/.hg1/pawns` directory was moved here after verifying that no process held its files and the observer lock was available. The unloaded Mac LaunchAgent, its duplicate installed `observe.py`, and empty observer logs/lock were removed. The canonical collector source remains [observe.py](observe.py).

The source retains its existing default `--data-dir` of `~/.hg1/pawns` for compatibility with the shared website installation. If deliberately running a local collector from this folder later, supply `--app-root` for the configured shared website and `--data-dir "$HOME/Desktop/salad/pawns/data"`; its shared modules must also be on `PYTHONPATH`. The current remote recorder uses its own paths. Do not start a second collector just to inspect this saved history.

Preserve the database and its cursor together. Deleted history cannot be reconstructed from source code alone. Keep this folder's data out of source-only image uploads; `.dockerignore` already excludes it from Docker builds.
