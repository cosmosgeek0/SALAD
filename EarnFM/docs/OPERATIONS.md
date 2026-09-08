# EarnFM operations

[Start here](../README.md) · [Setup](SETUP.md) · [Operations](OPERATIONS.md) · [Recovery](RECOVERY.md) · [Reference](REFERENCE.md)

Production recording runs on AWS. Use [AWS operations](AWS.md#check-and-roll-back) for that host; keep the retired Mac services disabled. The commands below use the EarnFM project folder and the authorized credential adapter.

## Verify the running system

Run these from the EarnFM project directory:

```sh
python3 earnfm.py inspect
python3 earnfm.py logs --minutes 15
curl --fail --silent http://127.0.0.1:8787/ef.json
```

Expected evidence, not just “process running”:

1. Cloud desired replicas = 10; current instance states and versions are visible. A group's version number changes on rollout; **decoded script SHA256 must match this package**.
2. Logs show `EF_LOG` native messages, JSON `earnfm_sample` revision 2, and `earnfm_event` actions such as `client_started`, `location_checked`, `reallocate_requested`, `reallocate_accepted`, and `reallocate_failed`. Compare old allocation removal with fresh current native/provider evidence; an accepted request alone is not a healthy successor.
3. `earned` and `credited_mb` change only from authenticated EarnFM account reads. `provider.error` and overall `error` must be checked; stale values are not current earnings.
4. A client counts online only when EarnFM lists its observed runtime ID, its latest sample is recent and non-final, and its state is `running`. A Salad container can be running while the client is paused or failing.
5. A displayed country requires a matching provider IP and the startup two-vendor country result. Blank country is unverified. Read current placement and `EARNFM_COUNTRY`; the active trial may have moved this existing group away from the US.
6. Selecting a graph minute should show the recorded server contributions; a different time range must change the graph. Look at browser Console for errors. Do not count a successful HTTP response as a healthy application by itself.

Fresh configuration/checksum verification is available without printing secrets:

```sh
python3 earnfm.py plan
python3 earnfm.py inspect
```

Optional standalone Mac service checks (do not enable these while AWS owns collection):

```sh
launchctl print "gui/$(id -u)/com.cosmosgeek.earnfm-recorder"
launchctl print "gui/$(id -u)/com.cosmosgeek.earnfm-dashboard"
tail -n 40 "$HOME/.hg1/earnfm/recorder.err.log"
tail -n 40 "$HOME/.hg1/earnfm/standalone-dashboard.err.log"
```

The original shared server uses `com.cosmosgeek.salad-bandwidth-dashboard` instead of the standalone dashboard label. User LaunchAgents start with login; the Keychain must be available. No claim is made that this local observer runs before login.

## Troubleshooting

| Symptom | What to do |
|---|---|
| One replica instead of ten | Check both `plan` and live `inspect`; this package sets 10 at creation, not a one-replica canary. |
| `EARNFM_TOKEN environment variable is not set` | Save the Docker key and ensure it is in the cloud environment. An account JWT is not a substitute. |
| Account endpoint HTTP 401 | Use the web app's current access JWT, not the Docker UUID. Renew reader credentials. |
| `EarnFM account login expired` | Sign in again, obtain the current request-header JWT, then run `keys --service reader --replace`. Cloud clients keep running. |
| Salad HTTP 400 on log timestamps | Use UTC ISO strings with millisecond precision from `iso()`; raw varying fractional timestamps caused real failures. |
| `A telemetry window exceeded the log page limit` | A full page is not a complete result. Use narrower query windows; never silently advance a cursor on truncated data. The recovery CLI splits full text-log windows. |
| Keychain entry unavailable or prompt loops | Use the same macOS username, unlocked login Keychain and the compiled helper; restore the missing service via `keys`. Do not put secrets into source. |
| Ledger/provider state survives without `target.json` | Restore the matching target from backup, or stop the recorder and archive the state as described in [Recovery](RECOVERY.md#restore-or-archive-existing-state). Do not create a new target over an unidentified old ledger. |
| `Resource temporarily unavailable` on `recorder.lock` | Another recorder holds the lock. Retain one process; inspect LaunchAgents before rerunning `observe`. |
| `Country unverified` / blank country | Check `location_checked`, both geo requests, and current provider IP. Unknown results do not establish the requested country. |
| Container running, client not confirmed | Read native logs and sample state. Do not equate a live process with a useful relay or credited traffic. |
| HTTP 429 / `rate_limited` | Honor the cooldown, preserve its deadline across manual changes. A paused container still incurs Salad cost. Do not reallocate it to evade the restriction. |
| Persistent DNS / socket errors | Repeated matching errors with no control link trigger replacement after 30 seconds; silent absence has a 120-second deadline. Working control links clear old error windows. Check structured recovery events and current inventory. |
| Salad version changes, runtime ID does not | This happened on a problematic node. Compare actual `client_started`/sample runtime ID with inventory. A targeted operator reallocation may be needed after checking rate-limit history; version alone was misleading. |
| Geo says GB/GR despite requested US | This happened for two old nodes. The two-provider startup rule rejected them automatically; replacements must be checked anew. |
| Old raw headline differs from current row totals | Rows refer to the current recorded run; the headline includes all valid recorded historical intervals. `counter_total_mb` retains the separate cumulative-run basis. Do not delete old runs or multiply one counter by replica count. |
| Almost no traffic | Keep a healthy connected client running. Low traffic or missing earnings alone never triggers restart or replacement. Check native acceptance and source freshness separately. |
| Native HTTP 401/403 | The container reports account/provider rejection and uses 15/30/60-minute backoff, without repeated host replacement. Correct the account or Docker credential; a reader JWT is separate. |
| Counter observation unavailable | `worker.observation_error` preserves the error and its source/receipt times. Rates remain unknown until a newer successful sample. |
| Malformed/conflicting telemetry | Inspect `rejected_records` and the collection warning. Original valid samples are retained and other workers continue recording. |
| Few credits, high raw MB | Compare the same account/time window and connection quality. Neither absent demand nor profitability is established by a raw-byte graph. |
| Port 8787 occupied | Keep the existing shared dashboard, or explicitly stop a known duplicate server. Use `serve --port 8788` for a separate recovery test. |
| Group not found / permission denied | Verify `ssh3/default` and Salad account access. Don't silently deploy into another organization. |
| Registry image unavailable | Restore a saved image archive or resolve the official vendor image. Do not silently swap to an unknown/latest implementation. |

A whole-group shutdown, when intended, is explicit:

```sh
python3 earnfm.py stop
python3 earnfm.py inspect
```

Stopping the local recorder or web server **does not stop paid cloud containers**. Stopping the cloud group does not delete the local ledger. The original account's auto-recharge was inactive when checked; verify the current billing page before relying on a credit ceiling.
