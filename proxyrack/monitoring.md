# PR recording and monitoring

[Start here](README.md) · [Deployment](deployment.md) · [Recovery](troubleshooting.md)

## Active production

Production recording is owned by `salad-proxyrack.service` on the AWS Mumbai host, with code under `/opt/salad` and data under `/home/salad/.hg1/proxyrack`. The Mac is a workspace/viewer and its recorders remain disabled. The shared website owner integrates the PR branch in `dashboard/static/fleet-test.js`; the server owner integrates `/api/proxyrack` through `proxyrack.public_snapshot()`.

The page has one minute bar chart, 1/6/12/24-hour choices, a 24-hour default, persistent selection across tabs and a contributor popup. Current rows show country/IP, native and Salad state, rate, recorded bytes, recorded duration, source age and precise notes. A control connection is not proof of successful customer forwarding or earnings.

## Record and inspect

For an intentional standalone recovery on the machine that now owns recording:

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 -B proxyrack.py observe
```

Do not run this alongside the active production reader. An `fcntl` lock prevents duplicate writers to the same directory. To inspect one cycle without starting an additional provider-account reader:

```bash
python3 -B proxyrack.py observe --once
```

For the included standalone page, in another terminal:

```bash
python3 -B -m dashboard.pr_recovery_server --port 8787
```

Use a different port if an existing service occupies it. The page is read-only and makes no provider or Salad calls. It reads the same precomputed view and uses the same freshness/status formatter as the public API.

On the existing Linux host, inspect the assigned PR service:

```bash
sudo systemctl status salad-proxyrack.service
sudo journalctl -u salad-proxyrack.service --since '15 minutes ago' --no-pager
```

Restart only that service after installing a finished recorder change. A recorder restart does not restart Salad workers. Cloud recovery does not depend on the recorder, dashboard or Mac.

## Durable records

`traffic.sqlite3` is the main ledger. Preserve it and the matching cursor together.

| Data | Meaning |
|---|---|
| `minutes` | Original interval start/end, source run, sequence, instance/machine, RX/TX, IP, validity and receipt time |
| `pr_events` | Original worker/provider/recovery events, source time and independent receipt time |
| `pr_provider` | Latest per-device and account observations, errors and check times; derived from recorded events |
| `pr_recovery` | Reallocation request, HTTP response, old-instance departure and later whole-fleet connection confirmation |
| `collector` and `cursor.json` | Completed log collection boundary; overlap and deduplication make replay safe |
| `deployment.json` | Current group identity and namespace; retain it with the ledger |
| `provider.json` | Pre-repair cache retained as an import source; new provider history lives in SQLite |
| `view.json` | Regenerated, precomputed page/API snapshot; not a replacement for the ledger |

The recorder queries group-wide logs, including replaced instances. It splits any capped page by time until complete; it does not trust requested sort order to provide every row. Catch-up is bounded and errors remain visible. Late data beyond the lookback/upstream retention cannot be guaranteed recoverable.

Repeated source records are deduplicated. Conflicting duplicates are invalid. Row totals and durations use the current instance, machine and run; overall totals retain valid earlier runs in this group. A counter reset never becomes a new traffic spike. An IP change keeps measured bytes but leaves the ambiguous interval’s IP unknown. Old V1 records without dated IP evidence remain unattributed.

## Measurements and freshness

- **Network MB:** decimal RX + TX / 1,000,000. The client download is outside the initial baseline. Both relay directions, registration and health-check overhead may be included.
- **Recorded duration:** sum of valid measured interval durations, not guessed uptime or time since group creation. Missing intervals are not filled in.
- **Provider counter:** original `bandwidth` API value, with its check time and reported source age. The physical unit is unverified; no MB or dollar conversion is presented. Old converted cache entries are inverted back to their original scalar solely because the earlier conversion is known.
- **Account balance:** the provider’s account-scoped string and check time. It includes earlier devices/runs and is not this group’s profit.
- **Current status:** requires recent inventory/recorder evidence and recent source samples. A successful HTTP fetch cannot refresh an old source timestamp. API reads expire live flags/rates while retaining history.
- **Provider coverage:** current-device coverage becomes unknown when inventory is stale, even if individual old-device readings were recent.

Minute bins retain exact aligned boundaries where available. Unaligned legacy intervals are proportionally allocated and marked estimated. Missing minutes remain blank; incomplete coverage remains partial. IP/country contributor details describe recorded intervals, not guessed current ownership.

## Verify the deployed flow

Use `python3 -B proxyrack.py status` to inspect the exact group and instance versions. In Salad logs, compare every current instance and machine against its new `PR_MINUTE_V2` and `PR_EVENT_V1` records. Require fresh source records rather than Salad’s `running` label alone.

New worker events include `started`, `registered`, `registration_retry`, `provider`, `native_error`, `counter_reset`, `ip_changed`, `reallocate_requested`, `reallocate_response` and `operator_stop`. An accepted request is only one phase. The ledger separately records the old instance leaving and the fleet later reaching its desired confirmed connections; it does not invent a specific old-to-new node mapping that Salad has not provided.

## September 7, 2026 repair verification

The recorder and supervisor were installed on AWS at approximately 17:19 UTC, and the existing `pr` group accepted worker version **7**. Group ID, namespace, ten replicas, pinned image, resources and the current Germany placement were retained. The recorder SHA256 is `561aef133cbbeddd88cd5fcdf2bda7bfe5598b52a18ebd940c871e7aefe1dac3`; the worker SHA256 is `c41f124a87de40c2abbdabb8de0c631c0d689e63d3f2df0ac36211d4eeb16e98`.

Before installation, a fresh production-data copy completed one collection cycle in 9.89 seconds with no collection error or backfill pending. It retained 417.425095 measured MB, 1,167 minute bins and ten current rows. Five serialized API snapshot reads took 43–46 ms each on the actual AWS host with its existing Unlimited CPU credit mode. This was a staging replay, not evidence that each new cloud worker had connected.

The exact supervisor passed 22 Linux failure cases in the pinned image with simulated native/provider/metadata services and external networking disabled. Checks covered process/connection failure, bounded IMDS retries, non-JSON and JSON quota/auth cooldowns, idle/no-growth/missing-counter preservation, counter resets and IP changes. Recorder checks covered capped log collection, delayed and malformed records, duplicate/run identity, recovery chronology, source expiry and original provider precision. All 43 accumulated worker fixtures parsed as 798 samples and 1,065 events with no rejected valid records. These checks passed with both the earlier shared dependency and the production dependency included in this folder.

The recovery-page candidates passed 12 Node model/DOM groups and 19 HTTP checks, including missing/stale data, range changes, tiny nonzero values and a full-day fixture. A clean reconstruction verified all eight manifest files and the documented Python snippets. Simulated checks do not establish provider earnings or customer demand.

A consistent pre-install database, cursor, metadata and previous recorder source were retained on AWS under `/home/salad/.hg1/proxyrack/backups/20260907T171854Z-pr-repair`. This is a real measurement backup; it is separate from the source folder and is not in Git.

Live rollout verification at 17:28:54 UTC found all ten current instances on version 7. Nine had fresh running/registered V2 records that matched their saved minute fields and machine identities. One instance, `c412c0b4-4b99-4413-8044-ac0213dbef60` on machine `774ac27a-a354-4750-ac49-13e30162dfb9`, continued advancing registered/running records with a source clock about five minutes slow. Its first V7 source timestamp was 17:15:13, before the actual cloud update at 17:19:39 and instance update at 17:20:00; delivery delay alone cannot explain this ordering. A separate provider check at 17:33:41 returned Online for the exact device at `92.209.187.123`. Source freshness remains Unverified; source timestamps were not rewritten. Its source-minute placement must not be treated as accurately synchronized UTC.

Actual automatic recovery was also observed: instance `a56e1152` recorded `startup_failed`, Salad IMDS accepted HTTP 200 at 17:22:20, and the old instance departed at 17:22:38. Replacement `4a0879b6` subsequently connected and registered. The ledger records these phases separately; whole-fleet fresh confirmation remains pending because of the clock issue. A single Salad log HTTP 408 at 17:22:05 recovered in later collection cycles without a recorder restart or discarded cursor.

The authenticated public PR page was checked after the API installation: ten rows, actual recorded durations, independent native/receipt ages and the original provider counter were visible. The PR API module is a single read-only bind in the existing UI service. The UI remains `salad-ui`, Unix-socket only, with IPv4/IPv6 denied and its existing inaccessible paths. An unsigned socket request still returned HTTP 403. No new credential access was granted.

The final public page uses the name **PR**, one chart and a 24-hour default. Switching between PR, Honeygain and PacketStream retained a selected six-hour period; all three pages loaded their real current rows. The PR worker, recorder, shared dependency, merged API and shared renderer were compared byte-for-byte with their Website recovery copies. These checks concern this repair; later independent website changes require their own verification.

### Follow-up: September 8, 2026, 00:09 IST

A read-only check at September 7, 18:39:50 UTC found all ten current replicas on version 7 and **10/10 confirmed**. Recording was 12.5 seconds old, with no collection error or pending backfill, and the AWS recorder service was active. Installed recorder and worker hashes still matched the verified source above. The former clock-skew instance was no longer in current inventory; this check does not establish why it left. The recovery ledger now also contains a whole-fleet connected timestamp for the previously observed startup-failure recovery.

At this snapshot, retained network RX + TX was 446.888362 MB and the separately reported whole-account balance was $0.10. Those values do not establish this group's sold traffic or earnings. No deployment, restart or reallocation was performed during this follow-up.
