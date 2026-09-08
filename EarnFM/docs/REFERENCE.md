# EarnFM reference

[Start here](../README.md) · [AWS](AWS.md) · [Operations](OPERATIONS.md) · [Recovery](RECOVERY.md)

## Deployment identity

The existing deployment is **SSH3 / default / earnfm-us**, group ID `90078bc1-4410-46cd-8411-6ebb8968eec2`, display **EF**, with **ten replicas**. Each uses 1 CPU, 1024 MiB memory, 64 MiB shared memory, no GPU, batch priority, image caching, and restart policy `always`. Autostart is false for a new group; creation and start are separate operations.

The image is pinned to `docker.io/earnfm/earnfm-client@sha256:99a9feaa3dfab9e858012994fa1f922523f41b098e6b1cd9c9e9fca9286c3843`; its AMD64 manifest is `sha256:743a3118986ec1a794af8fc3c3bbcb5562797b269c1745345f326972d8792b56`. The unmodified vendor process is `/app/main` (SDK 2.3.5 / app 1.0.0 observed in native logs). No debug payload logging is enabled.

`config.json` records a US default for a fresh deployment. An existing deployment's current country is retained during recovery updates; a country trial moved this group to GB on September 7. The name `earnfm-us` does not determine placement. `EARNFM_COUNTRY` and live `country_codes` must agree. Read the current cloud command and source hash; the historical version-6 local metadata and version-8 archive are diagnostic references, not the deployment authority.

The latest recorded release is **version 12**, verified on all ten current instances at 17:02 UTC on September 7, 2026. `config.json` retains a legacy `activity_min_bytes` environment value for compatibility with the existing deployment; v12 ignores it and reports zero. Its recorded cooldowns keep their original capture timestamp and are filtered by their deadlines when preparing an update. Live state must still be read before any cloud change.

The shell program is base64 encoded into arguments of at most 900 characters, decoded to `/tmp/earnfm-start.sh`, and executed by `/bin/sh`. The vendor credential is supplied through `EARNFM_TOKEN`; policy settings are `EARNFM_COUNTRY` and `EARNFM_COOLDOWNS`. `EARNFM_ACTIVITY_SECONDS` sets an observation window only; legacy `EARNFM_MIN_BYTES` values are ignored.

## Embedded recovery

| Evidence | Action |
|---|---|
| Child process exits | Request own-instance reallocation immediately. |
| No established child-owned control socket | Observe for 120 monotonic seconds, then reallocate if the absence persists. |
| Native DNS/dial/backend errors while control is absent | Reallocate after matching errors span 30 seconds; gaps over 60 seconds or a recovered control socket reset the window. Backend exhaustion alone does not preempt a working fallback. |
| Healthy control connection with zero or low RX + TX | Keep the same client running. The observation window records activity only; it never restarts or reallocates the client. The legacy `activity_min_bytes` telemetry field is zero. |
| HTTP 401 handshake rejection | Report account-key rejection; retry after 15, then 30, then at most 60 minutes. Replacing machines cannot repair the credential. |
| HTTP 403 handshake rejection | Report provider rejection with the same bounded backoff; no IP rotation to evade it. |
| HTTP 429 | Stop the client and wait 86,400 seconds before retry. |
| Native IP-change/different-location notice | Preserve the vendor's 129,600-second (36-hour) cooldown. |
| Preserved machine cooldown | Wait until its absolute deadline before geo requests or client launch. |
| Both geo providers agree on another country for the same IP | Reallocate before launching the client. |
| Geo result missing or contradictory | Continue with country unknown. |
| Counter/control observation unavailable | Preserve the observation error and leave the measurement unknown; missing data cannot trigger a low-activity replacement. |
| Explicit stop signal | Stop the child and emit a final sample when counters are readable. |

A control socket means an established TCP connection owned by the vendor process to its observed control port 8443. It is transport evidence, not proof of application acceptance, paid payload, or earnings. The page also requires a fresh EarnFM online-device observation before confirming a device.

Activity uses raw interface bytes because no verified per-device paid-byte endpoint is available. It is never a health or replacement threshold. A healthy client can receive no customer work; control traffic and paid traffic remain separate. Do not manufacture traffic to make the graph rise.

Each launch has a separate log pipe, so an old buffered error cannot reject the next process. Timing windows use `/proc/uptime`; measurement timestamps retain the source wall clock and its one-second resolution.

Reallocation uses [Salad's in-container IMDS endpoint](https://docs.salad.com/container-engine/how-to-guides/imds/imds-reallocate), without the Salad management key. It makes at most three attempts with 12-second timeouts and five-second gaps, records request/HTTP acceptance or failure, then exits 75. Salad documents [nonzero-exit reallocation](https://docs.salad.com/container-engine/how-to-guides/managing-deployments) as a platform fallback. Acceptance is followed by inventory observations; old allocation removal and current provider-confirmed devices are shown separately. Concurrent replacements do not establish a unique old-to-new match.

Cooldowns are held in workload memory and preserved in environment settings by intentional CLI updates, which recover new deadlines from legacy and structured logs. An unplanned platform restart can lose a newly created in-memory deadline. A cooldown also still incurs Salad runtime cost. This is not a global account-spending controller.

## Recording and accounting

Production collection runs on AWS, using the [documented paths](AWS.md). Clients keep recovering if the recorder or Mac is offline. A recorder outage can only be backfilled while Salad still retains the logs; no unlimited history guarantee is implied.

- Revision-2 source samples arrive roughly every ten seconds, plus state-boundary/final samples. Revision-1 one-second samples remain readable. `(run, seq)` deduplicates observations; runs include runtime instance ID, start time and PID. Counter resets and invalid intervals never become traffic deltas across a replacement.
- Original `samples` and `runs` are preserved. `sample_details` stores source-log, Salad receipt and first recorder receipt timestamps. Freshness requires both a recent source sample and its first recorder receipt; Salad receipt-clock skew is retained and shown as a note rather than hiding fresh traffic. Duplicate reads do not refresh that first receipt. Invalid or conflicting records are retained in `rejected_records`; valid records and the collection cursor continue, and the original valid sample wins a conflicting duplicate.
- Group-wide log queries include departed machines. Full pages are split with at most four concurrent reads; the cursor is not advanced for an incomplete/failed query. A 120-second overlap handles ordinary log delay; arbitrary delays beyond that window are not guaranteed recoverable.
- `minute_cache` apportions crossing intervals by duration while conserving integer byte totals exactly. Such minutes are marked estimated. Coverage is the sum of valid recorded interval durations, not invented elapsed uptime. Unknown intervals remain absent; a measured zero remains zero.
- `total_mb` sums valid recorded RX + TX intervals over retained history. `counter_total_mb` separately preserves accumulated run counters. Current rows refer to their current recorded run, so row totals do not include all retired machines.
- `history_nodes` preserves each historical run/IP/country. Each minute's `contributions` contains `[identity index, MB, recorded milliseconds]`. The compatibility `by_instance` map supports an older shared page during rollout. Current worker IPs are not substituted for known historical IPs.
- `kb_per_second` is the latest 60 seconds of covered bytes divided by covered milliseconds. Decimal bytes/ms equals KB/s; multiply by 0.06 for MB/min. Boundary intervals are estimated uniformly.
- Raw RX + TX includes forwarding in both directions, overhead, failed attempts and control traffic. It is not sold bandwidth and must not be priced as though it were credited traffic.
- `provider_history` saves successful account observations with source and receipt timestamps. `events` records native/recovery and inventory observations. `observer_status` retains a counter fault until a newer successful observation; `observer_success` prevents replayed old errors from reappearing.
- The provider endpoints are `https://api.earn.fm/v2/harvester/view_balance` and `/devices_online`, authenticated with the account access JWT in `X-API-Key`. The Docker token cannot read them. Device-list freshness and balance freshness are tracked separately. `provider_devices` caches each runtime's last provider-seen IP and timestamp; the page labels a missing current IP as “last seen” rather than treating that older observation as current confirmation.
- Account bandwidth balance is `bandwidthBalance + bandwidthDCBalance`; account shared GB is `totalBandwidthShared + totalDCBandwidthShared`. The displayed changes subtract the saved baseline. They are account-wide gross balance/credited-traffic changes, not per-machine earnings, payouts or net profit.
- The preserved experiment baseline is `$0.041831 / 0.418308 GB` at saved time `1788730420050`. Its original timestamp was captured before the provider request and is approximate; it must not be silently replaced with a newer timestamp or reused for a different experiment.

The shared page uses one minute chart, 1/6/12/24-hour ranges, historical contributor popups, one row per current allocation, actual recorded duration, source freshness, provider observations and recovery notes. The standalone `/ef` page implements the same EarnFM data distinctions for recovery use.

The shared USD card displays **Balance change** from signed differences between saved bandwidth-balance observations in the selected period. **Account balance** displays the current provider bandwidth balance. A decrease is preserved, not clipped or relabeled as gross earnings. Gross earnings, withdrawals and per-device profit remain unverified; the recorded dollar observations are still displayed.
