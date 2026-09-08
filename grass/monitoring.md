# Monitor Grass

The active recorder is `salad-grass.service` on AWS. The retired Mac recorder stays disabled. Native recording and recovery are installed by `deploy.py repair`; there is no per-instance cron attachment step.

## Production setup and checks

For a lost or new AWS host, follow [Website recovery](../Website/RECOVERY.md) and [credential setup](../Website/SETUP.md). The shared bundle includes the Grass recorder and its systemd unit. Compare it with this folder's verified `recorder.py` before installing a different release.

The production executable is `/opt/salad/scripts/grass-recorder.py`, run as `salad`. Its state is `/home/salad/.hg1/grass/traffic.sqlite3` and `view.json`. The existing credential helper supplies `salad-bandwidth-api` privately; retain its systemd credential configuration. The standalone recorder also accepts `SALAD_API_KEY` from a privately supplied process environment and `GRASS_DATA_DIR` for its state path. Do not put a key in command arguments or source files.

For a different organization, project or group, the values set in your Mac Terminal do not configure AWS. Run `sudo systemctl edit salad-grass.service` on AWS and add the matching nonsecret settings, replacing the example names:

```ini
[Service]
Environment=GRASS_ORGANIZATION=your-organization
Environment=GRASS_PROJECT=your-project
Environment=GRASS_GROUP=grass
```

Apply these settings before the first collection on the rebuilt host, then run `sudo systemctl daemon-reload` and restart only `salad-grass.service`. Do not reuse a different group's measurement database as this group's history; retain the previous database in its separate backup.

Connect using [Website connections](../Website/CONNECTIONS.md), then inspect:

```sh
sudo systemctl status salad-grass.service --no-pager
sudo journalctl -u salad-grass.service -n 10 --no-pager
sudo -u salad python3 -m json.tool /home/salad/.hg1/grass/view.json
```

Restarting this recorder reloads its saved SQLite cursor and retains history:

```sh
sudo systemctl restart salad-grass.service
```

A measurement backup must preserve the database and cursor together. Use SQLite's backup API or stop the writer before copying the database; copying only its main file while WAL writes are active is not a consistent backup.

## What the page measures

| Reading | Meaning |
|---|---|
| Salad state / running count | The most recent cloud inventory. |
| Connected / confirmed count | A running native Grass process plus a fresh successful Grass `/activeDevices` response containing its device ID, current public IP, and positive network quality. |
| Status unavailable / sign-in required | Provider telemetry failed, or Grass rejected/lost account login. These are different from a bad IP. |
| MB/min and recorded MB | Measured container `eth0` receive + send bytes, including Grass control, setup, monitoring and viewer traffic. They are not sold bandwidth or earnings. Decimal MB uses 1,000,000 bytes by definition. |
| Duration | Sum of valid recorded intervals, excluding missing baselines, resets, IP changes and clock conflicts. It is not a provider earnings duration. |
| Network Points | Grass `proxyPoints`: account-wide finalized epoch Network Points. The note also gives total points, epoch, provider modification date and observation time. |
| Cash earnings | Not reported. Points and network bytes are not converted into money. |
| Details / recovery | Quality, next status attempt, last restart/reallocation reason and its recorded outcome. |

The points note reports the change since this recorder's first observation in the same account/epoch scope. It does not assign account earnings to this IP. Grass's published guidance says Network Points are credited through a daily calculation and depend on bandwidth demand; unchanged points alone do not warrant a restart. [Grass point reporting](https://www.grass.io/learn/grass-points-stopped-increasing-a-troubleshooting-checklist/)

## Recording boundaries

The configured native sample cadence is ten seconds; device checks are thirty seconds and point checks are sixty seconds when provider access succeeds. The AWS loop aims for fifteen seconds, subject to API latency. These are code settings, not promises of Salad log delivery time. Failed requests remain visible and are retried; no missing sample is replaced with zero.

Each native record carries group, instance, machine, container/worker run, sequence, source timestamp and monotonic counter time. SQLite retains the first collector receipt time. Repeated logs are deduplicated; conflicting duplicates invalidate the affected intervals. Late logs repair their neighboring intervals without double counting.

The first sample establishes a counter baseline. Deltas never cross a run, reset, IP change or invalid clock boundary. Intervals up to the configured ninety-second chart cutoff are proportionally split into minute bars with contributors and coverage. Longer valid gaps retain the measured endpoint total without invented minute bars. Replaced-node history remains in SQLite.

The configured freshness windows are ninety seconds for native measurements and three minutes for provider points. The shared page also checks recorder and inventory freshness. Cached native `CONNECTED` text and `lastConnectedAt` are not connection heartbeats. The recorder publishes the actual provider/API failure instead of claiming a process is earning.
