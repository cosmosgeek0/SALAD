# Website data

## Honeygain recovery evidence

The released Honeygain observer preserves a reduced current-machine lifecycle view, with event times and generic status. A complete group recovery ledger and public `recovery_note` are not part of deployed release `1c70638`. An unpublished local extension is deliberately excluded from this backup. Retain original native logs when available; reduced lifecycle rows alone cannot recover discarded reasons or establish which replacement request produced a later healthy instance.

## Data sources and route contract

The paths below refer to AWS: `~/.hg1` means `/home/salad/.hg1`. The website reads them as the isolated `salad-ui` user; recorders write as `salad`. See [RECOVERY.md](RECOVERY.md) for schemas, ACLs and the single billing-file write exception.

| Tab / route | Local source and important semantics |
|---|---|
| HG /api/fleet-test?service=hg | fleet-tests observations/current/network-state plus hg-fleet original timestamps and provider readings; estimated minute allocation |
| PS /api/ps1/minutes | packetstream/minutes.sqlite3 and native-census.json; exact V2 minutes, estimated legacy intervals |
| PS minute ?minute=UTC_MS | Same ledger, top contributor detail for the selected UTC minute |
| PS /api/ps1/view | Provider readings and deployment metadata; ephemeral same-origin bridge token, not an upstream account credential |
| PR /api/proxyrack | proxyrack.public_snapshot reads the published view, recalculates native/provider freshness, and uses group-filtered minutes for legacy views |
| RP /api/repocket?chart=1 | repocket/view.json, optional provider.json, all retained minute events in traffic.sqlite3 |
| EarnFM /api/earnfm | earnfm/view.json written by its recorder |
| TM /api/traffmonetizer?chart=1 | traffmonetizer/latest.json; its recorder publishes the chart and recorded-test totals |
| Pawns.app /api/pawns | pawns/view.json from native intervals, SDK state and fresh provider/IP confirmation; dated account sold-traffic and sharing balance remain separate |
| EarnApp /api/earnapp | earnapp/view.json supplied by its collector; missing values remain null |
| Grass /api/grass | grass/view.json supplied by its collector; missing values remain null |

The new feeds share a restricted JSON contract. Core top-level fields include `generated_ms`, `inventory_ms`, `desired`, `running`, `working`, `started_ms`, `total_mb`, `credited_text`, `earned_text`, `credit_note`, `error`, `workers` and `minutes`. Core worker fields include `id`, `ip`, `country`, `client_status`, `salad_state`, `working`, `mb_per_minute`, `total_mb`, `recorded_ms`, `sample_ms` and `error`. `sample_ms` is the original observation time; `recorded_ms` is its local receipt time. Minute fields are `minute_ms`, `mb`, `partial`, `estimated`, `count`, optional `coverage_complete` and contributor `nodes` with `instance`, `ip`, `country` and `mb`. Unknown values are null. The server exposes only these fields and expires stale working flags and live rates on API reads. The page applies the same freshness checks. Historical traffic is retained.

Pawns recording requires the telemetry-emitting cloud image in the [Pawns folder and guides](../pawns/README.md); the older SDK-only image has no periodic byte records. The collector reads `cosmosgeeketh/default/pawns` by default and supports explicit organization/project/group arguments. It preserves stored history and requires each incoming sample to carry the current cloud group ID. Retained logs from a deleted group with the same name cannot enter the replacement group's ledger. The completed EarnApp and Grass collector sources are in source/. Their tabs wait for real views when no measurement exists. Grass installs its native worker and automatic login restoration through the repair step in [Grass monitoring](../grass/monitoring.md); replacement instances use the saved startup automatically. Confirmation requires a fresh provider response matching the current device/IP, not cached CONNECTED text. The recorder saves account-wide finalized Network Points and recovery outcomes separately from measured traffic; cash earnings remain unreported. A running/enabled process alone is not provider registration, and raw network counters do not establish paid credits.

Public data contains status, IDs, timestamps and measured values. Recorder credentials live in Secrets Manager with a private tmpfs cache, not in the website or source bundle. The isolated server does not call cloud APIs. Legacy /api/series, /api/boxes and exports read the preserved compatibility database; /api/ps1/status and /api/ps1/history are retired compatibility endpoints returning unavailable. Use /api/ps1/minutes for the active PacketStream page.

| Storage | Retain/restore |
|---|---|
| ~/.hg1/hg-fleet | Original timestamps/instances, counters, provider-readings JSONL and current safe snapshots |
| ~/.hg1/fleet-tests | current.json, observations.jsonl, network-state.json, latest.json, events.jsonl, archives |
| ~/.hg1/packetstream | observer-target.json, minutes.sqlite3, native-census.json, provider-observations.jsonl, period files |
| ~/.hg1/proxyrack | deployment.json, traffic.sqlite3, provider.json, view.json |
| ~/.hg1/repocket | deployment.json, traffic.sqlite3, cursor.json, provider.sqlite3, provider.json, provider-status.json, view.json |
| ~/.hg1/earnfm | target.json, traffic.sqlite3, provider.json, provider-baseline.json |
| ~/.hg1/traffmonetizer | deployment.json, traffic.sqlite3, latest.json; provider/error/cursor data is also in the DB |
| ~/.hg1/earnfm/view.json | EarnFM's published output, regenerated from its ledger |
| ~/.hg1/pawns | traffic.sqlite3 with native samples, log cursor and pawns_events provider/recovery records; view.json current safe snapshot |
| ~/.hg1/earnapp and ~/.hg1/grass | Preserve the respective collectors' measurements and view.json |

The retired Mac Pawns data has been consolidated into `~/Desktop/salad/pawns/data`; see [Pawns website and data](../pawns/website.md). The `~/.hg1/pawns` path above remains the default for a fresh installation of the included collector. Its old Mac LaunchAgent and duplicate installed source were removed; production continues on Mumbai.

SQLite tables are defined in the included source. Use SQLite's backup API or stop the associated writer before copying a database; copying only a live .sqlite3 file can omit committed WAL pages. Restore a recorder cursor only together with the matching ledger, or it may skip missing history. Do not store provider sessions or cloud environment dumps with a public source backup.

## Measurement and status rules that must not be lost

1. **Network units:** decimal MB; bytes / 1,000,000. RP provider traffic is separately labelled MiB (bytes / 1,048,576). MB/min comes from the measured interval duration. KB/s × 0.06 = decimal MB/min.
2. **One source per number:** platform-running count, native acceptance, raw network traffic and provider credit use different evidence. They are not interchangeable.
3. **Time:** store original source timestamps and run IDs. Preserve timezone offsets; normalize non-six-digit fractions for Python 3.9. Render the viewer's local clock, but bucket by Unix UTC minutes.
4. **Counter resets:** never difference counters across instances, boots, runs or an IP handover. Keep missing/excluded samples as boundaries.
5. **Partial data:** the chart distinguishes gaps, partial/estimated bars and genuine observed zero. No smoothing into fabricated traffic.
6. **Current slots:** a fresh short inventory gets explicit Unassigned/Awaiting inventory rows. These have no IP/metrics. A stale inventory's counts remain unknown; it is not a fresh allocation fact.
7. **Transitions:** actual allocating/downloading/creating/stopping/stopped state overrides a stale positive client flag and suppresses current rate/confirmed status.
8. **Honeygain spike exclusion:** 96.246.178.36 is excluded from HG chart/display totals; its observations remain interval boundaries. Historical raw JSONL is not rewritten. If the ledger is truncated, the adjusted lifetime total becomes unknown rather than reintroducing removed traffic.
9. **HG performance:** the HG-only reader reuses history while its source signature is unchanged, with a bounded refresh; ages still advance and new observations invalidate the cache. Original timestamps/run identities remain intact. TM also publishes its minute chart in the recorder. Do not rebuild entire histories on every UI paint.
10. **Provider data:** PacketStream requires actual baseline/follow-up samples; PR bandwidth counters retain their unverified original unit and dated account balance; Pawns sold traffic/sharing balance and RP lifetime own-bandwidth totals are account-scoped, not per-node earnings; EarnFM reports baseline balance change; TM reports provider baseline-adjusted traffic/earnings. Missing/stale sources must remain labelled.

## Data-loss scenarios

**Source lost, data/cloud survives:** restore the source bundle and Linux configuration, retain Secrets Manager and the matching ~/.hg1 metadata/databases/cursors, and install the named units. Do not run fresh initializers over preserved data.

**AWS data lost, cloud survives:** restore the source/configuration, restore credential access, bind current groups, take fresh provider baselines and start new recording. The parsers retain whatever upstream log history they can still fetch; do not claim that recreates all prior observations. Losing only the Mac does not erase the AWS recordings.

**Cloud and recorded data lost:** rebuild each protocol using its document, then bind newly returned IDs and begin new baselines. Use the source and Linux configuration here for the hosted website/collectors. Vendor accounts, registries or separately archived images still must exist.

**A single recorder breaks:** inspect its log and target ID, repair only its source/credentials/cursor issue, preserve the ledger, restart only that Linux unit. Missing telemetry is not permission to discard a healthy workload.

## Historical IP and run API

`GET /api/history?service=hg&hours=24&test=current&sort=last_seen&offset=0&limit=50` reads retained measurements. Service IDs are `hg`, `ps`, `proxyrack`, `rp`, `earnfm`, `tm`, `pawns`, `earnapp`, and `grass`. Hours are `1`, `6`, `12`, `24`, or `all`; `q` searches identity/IP/country/lifecycle text; sort is `last_seen` or `total_mb`, descending. Pages contain at most 100 rows.

The response includes `test`, `tests`, `start_ms`, `end_ms`, `source_ms`, `inventory_ms`, `coverage_note`, `total`, `has_more`, and `rows`. Test choices have `id`, `label`, and `archived`; pass the returned ID back as `test`. Archived periods end at the archive's last observation, rather than today's clock.

Rows retain `id`, `group_id`, `instance`, `machine`, `run`, `ip`, `country`, `total_mb`, `first_seen_ms`, `last_seen_ms`, `duration_ms`, `samples`, `current`, `lifecycle`, `partial`, and `estimated`. Observation times come from recorded source intervals; they are not replaced by query time. Duration and traffic cover the selected period; a boundary interval can begin outside it. Unknown traffic/duration remain null. An unverified inventory or missing run identity makes lifecycle unverified. Provider figures remain available through their original feeds; history `provider` is null because account/device credits cannot be reassigned to IPs.

Native minute, Repocket and EarnApp queries aggregate only the selected group and period. Honeygain uses its retained test/archive observations and original source lookup, preserving missing/reset/IP-change boundaries and spike exclusion. TM and EarnFM reuse in-memory minute/run/IP aggregates and ingest only new immutable sample row IDs; changing period does not rescan all samples. Clipped aggregate boundaries are explicitly estimated. EarnFM also returns separate source receipt and local recorded timestamps when stored. TM receipt-only backfills remain unavailable until that in-memory cache is rebuilt. No ledger, recorder cursor or provider baseline is changed by these readers. Other history aggregates can be reused for up to 30 seconds, retaining their original window/source clocks; live membership is checked separately.

Coverage limits are explicit: Grass does not record historical group UUIDs, TM does not retain archived group UUIDs, and legacy Repocket attribution/receipt coverage can be partial. Unknown countries and IPs stay unknown. EarnApp history includes recorded non-US rows, while its current summary separately labels US traffic.

## Compact chart delivery

The existing service APIs accept `compact=1&hours=1|6|12|24`. The overview also accepts `hours=720` for retained provider postings. Native chart readers still supply their available last 24 hours, so longer overview selections retain explicit partial coverage; older native records remain accessible through IP history. They keep status, totals, timestamps and coverage flags. Repeated contributor identities move into `chart_nodes`; each minute uses `contributions: [[identity_index, mb], ...]`. Decode each entry as `{...chart_nodes[index], mb}`. EarnFM retains its existing `history_nodes` representation. Compact HG omits unused ten-minute buckets and network timelines but retains the provider timeline; compact PR omits its unused duplicate timeline. Full routes/exports remain available. All measurement responses remain `Cache-Control: no-store`.

## Shared overview values

Every current service feed includes `traffic_summary` and `provider_metrics`, including compact responses. The billing-only `/api/ps1/view` supplies `provider_metrics`; its traffic overview comes from `/api/ps1/minutes`. The overview uses the same plain names across services: Containers running/total, Confirmed clients, Current MB/min, Average MB/min, Measured MB · 24h, Measured MB · selected period, Credited MB, Credit / measured %, Earned USD, Effective USD/GB, and Peak MB/min. Prefer the last day over lifetime network traffic. Container totals must use the reported configuration without a fixed ten-container default or display cap. Current rate is the sum of fresh, known native rates from the service's normalized nodes; missing contributors make that aggregate partial or unavailable.

`traffic_summary` is calculated before compact chart filtering. It includes `containers_running`, `containers_total`, `inventory_ms`, `selected_mb`, `last_24h_mb`, observed-minute counts, `partial`, `last_24h_partial`, `estimated`, `average_mb_per_minute`, `average_minutes`, `peak_mb_per_minute`, and `peak_minute_ms`. Average and peak use completed observed minutes; `average_partial` marks incomplete coverage. Empty coverage is null; recorded zero is zero. Windows follow the chart's UTC minute boundaries and include the current partial minute. These totals cover recorded chart intervals, with coverage flags, rather than claiming unobserved traffic was zero.

`provider_metrics` contains numeric decimal `credited_mb`, `earned_usd`, `balance_usd`, `bandwidth_balance_usd`, `balance_change_usd`, `effective_usd_per_gb` and `withdrawn_usd`. Null means unavailable. `raw` preserves original amounts; `scope`, `window`, `source`, `observed_ms`, `provider_updated_ms`, `fresh`, `error`, and `missing` preserve their meaning. `usd_conversion` identifies a published conversion applied to provider-reported credits or sold traffic; it is not a payout transaction. A fresh observation is not a new provider posting. `accounting_interval_seconds` describes published accounting granularity; `posting_interval_seconds` remains unknown where settlement cadence is unverified. Native units belong in source details, not the main metric cells.

| Provider | Normalization and limits verified against current source and AWS records on 7 September 2026 UTC |
|---|---|
| Honeygain | `/api/v1/earnings/stats` gathering traffic bytes / 1,000,000; gathering credits / 1,000 USD. Provider calendar-day window is retained; other credits are excluded. [Published USD conversion](https://www.honeygain.com/jumptask-mode/). |
| PacketStream | Authenticated `/dashboard` dated rolling traffic bytes / 1,000,000. Provider traffic × the [published $0.10/GB Packeter rate](https://packetstream.io/terms-of-service/) supplies its USD equivalent. Account balance remains separate. `/api/ps1/view` also preserves the original safe provider reading. |
| Proxyrack | Original `/api/bandwidth` counter stays unconverted until its physical unit is verified. The dated dollar balance is an account balance. Published IP-dependent payout rates cannot identify the counter's unit. |
| Repocket | `/api/reports/total` own-bandwidth bytes / 1,000,000 and own-bandwidth cents / 100 USD, with the account lifetime scope. Formatted legacy snapshots are insufficient for this conversion. |
| EarnFM | `/v2/harvester/view_balance` shared GB delta × 1,000; bandwidth balance and baseline balance change remain separate from gross earnings. The original approximate baseline time is retained. |
| Traffic Monetizer | `/api/dashboard/get_graph_stat?period=month` baseline-adjusted traffic bytes / 1,000,000 and its bandwidth earnings in USD. Account balance and balance change stay separate. Original daily traffic and stream fields remain in `raw`. |
| Pawns.app | `/api/v1/users/me/balance` sold GB × 1,000; sold traffic × the [published $0.20/GB rate](https://business.pawns.app/sdk/) supplies its USD equivalent. Sharing and total balances stay separate. Original account amounts are retained without per-IP allocation. |
| EarnApp | `/dashboard/api/devices` `earned_total` in USD for the recorded device UUID. Provider credited MB is unavailable under its [hourly active-usage accounting](https://help.earnapp.com/hc/en-us/articles/38191916327441--What-are-the-EarnApp-rates-How-are-they-calculated). |
| Grass | `/epochEarnings` retains reported stage/epoch Network Points separately from total points. The [published Stage 2 allocation](https://www.grass.io/learn/how-your-stage-2-rewards-allocation-works/) does not price the recorded Stage 3 points. No MB/USD conversion is asserted. |

`provider_metrics.intervals` delivers the changes between successive saved provider readings as `{start_ms, end_ms, credited_mb, earned_usd}`. Use `observed_period` for the selected-period credited/earned overview values; `credited_window` and `earned_window` retain separate actual observation bounds, covered time and partial coverage. This prevents a short byte-history window from inheriting the longer USD-history window. The original `credited_mb`/`earned_usd` fields and `window` retain the provider account/device totals as source detail. An unchanged observed counter produces a real zero change. A missing baseline, decreasing counter, changed account/device/baseline or reporting-window boundary never produces invented credit. Cached interval derivation invalidates when the ledger/WAL changes. The reader bounds retained observations; returned observation bounds disclose its coverage.

These are **observed provider postings**, with their actual interval boundaries. Plot that evidence beside the measured traffic; keep longer posting intervals intact instead of distributing them into assumed minutes. The source does not assign an account posting to a country or prove it was earned by traffic in its observation minute. No credited amount is added to measured traffic. Honeygain now saves original gathering bytes and reporting dates in its existing provider observation ledger; older entries retain their missing-byte state.

Effective USD/GB divides actual bandwidth earnings by provider-credited GB only when both cover the same source window and category. `minute_attribution` and `country_attribution` remain false because these account/device reports do not establish that the credits belong to the displayed fleet's same minute or rolling day. Do not stack credited account volume on top of measured traffic, manufacture minute allocations, or divide a lifetime account total by a selected-period network total. Withdrawn USD needs an actual payout source; earned value and current balance are not withdrawal evidence.

`traffic_summary.provider_comparison` gives **Credit / measured %** from provider credit changes and recorded network traffic in the same available observation intervals. It includes both MB operands, actual bounds, covered time, source scopes, and estimated/partial flags. Only intervals with both numeric sources and verified full native minute coverage enter either operand; native boundary minutes are proportionally allocated and marked estimated. The clock passing a minute boundary does not establish coverage. Honeygain publishes `coverage_complete` from actual covered intervals for every contributing node; other feeds must supply a complete minute. Unfinished or incompletely recorded minutes wait for source coverage, preventing a partial total from being prorated twice. Missing provider intervals and gaps remain explicitly partial. Missing intervals are excluded from both sides. This is an account/fleet reporting comparison, not proof that a percentage of individual packets was paid. Reporting delays can produce a ratio above 100%; do not clamp it, assign it to countries, or add the two volumes together. Use the comparison's own operands and bounds together.

## Salad runtime and cost

The shared recorder retains Salad instance state observations and running/interruption events in `~/.hg1/costs.sqlite3`. Its cost worker runs inside the existing recorder service so slow cloud reads do not block traffic recording. It reads only the configured groups, using the existing Salad credential privately. The ledger retains group/instance/machine identity, source and receipt times, resource settings and collection cursors. Capped log responses are split by time; unfinished history remains partial.

Current service feeds include `costs`: `estimated_usd`, summed `running_minutes` (node-minutes), current `usd_per_hour`, `observed_ms`, `window`, `partial`, `errors`, and per-instance `nodes`. Workers and history rows also carry an optional `cost` object matched by actual instance ID. That value belongs to the Salad instance for the selected period; IP/run rows referencing the same instance share its cost. The app total deduplicates instances and must not be calculated by summing paginated IP rows. Unknown identity, runtime or pricing stays unavailable.

Cost uses Salad running-state time, independently of provider acceptance and network activity. Allocation and download time do not become charged runtime. Open runs extend only through their last confirmed running observation. Unresolved retirement and old versions whose resource profile was not captured remain partial; older unverified resource versions use the observed profile as an explicitly partial estimate. Calculated cost is not an invoice or proof of money withdrawn.

[Salad billing](https://docs.salad.com/container-engine/explanation/billing-pricing/billing) specifies per-second running usage. The current CPU-only rate is USD 0.004 per vCPU-hour plus USD 0.001 per allocated GiB-hour (API memory is MiB). The signed-in portal confirmed 1 vCPU + 1 GB = USD 0.005 per node-hour on 7 September 2026 UTC. [The announced change](https://blog.salad.com/saladcloud-price-changes-september-2026/) raises vCPU pricing to USD 0.005 at 12 September 2026 00:00 UTC; RAM is unchanged. Intervals crossing that boundary retain both rates. GPU configurations remain unpriced until their tariff is supplied; CPU/RAM fees must not be added to a GPU-inclusive rate.
