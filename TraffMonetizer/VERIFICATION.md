# Verification and reproduction limits

The current worker is version **8**, documented under Healthy-idle correction below. The earlier sections record the version-6 rebuild and version-7 reliability rollout; their hashes, timings and replacement countdowns are historical evidence, not the current idle policy.

## Sources

- [Official TM image and interactive commands](https://hub.docker.com/r/traffmonetizer/cli_v2).
- [Salad container creation API](https://docs.salad.com/reference/saladcloud-api/container-groups/create-container-group).
- [Salad IMDS self-reallocation](https://docs.salad.com/container-engine/how-to-guides/imds/imds-reallocate).
- [Salad log schema and node/receipt timestamps](https://docs.salad.com/container-engine/reference/log-queries).
- [Salad deployment edits and restarts](https://docs.salad.com/container-engine/how-to-guides/managing-deployments).
- [TM account dashboard](https://app.traffmonetizer.com/dashboard).

The account collector endpoints were observed in TM's signed-in frontend, not a guaranteed public API contract: `https://data.traffmonetizer.com/api/app_user/get_balance` and `https://data.traffmonetizer.com/api/dashboard/get_graph_stat?period=month`. If that contract changes, restore the official account dashboard first and inspect the actual authenticated requests. Monthly graph retention also limits how far the included account calculation can look back.

The previous single-file guide was checked by extracting its source into an empty temporary directory, validating checksums and Python syntax, rebuilding the Keychain helper, and testing the TM-only server and observer against isolated fixtures. Those documentation checks did **not** create or stop cloud groups, change credentials, or replace the live runtime. The cloud configuration/source match was read-only. A new-account deployment and real billing were not repeated solely to test documentation.

### Reproduction audit — 7 September 2026

The follow-up audit started from the previous single-file Markdown guide alone in an empty temporary directory. Two independent readers checked the complete guide and ran separate extraction, deployment-recipe, observer and server tests. The source hashes were also compared again with the current project and the live Salad command override; all matched.

| Check | Measured result |
|---|---|
| Source extraction | All eight source hashes matched; repeat extraction refused to overwrite |
| Actual pinned image startup | The exact 18-argument shell/base64 command reconstructed the worker byte for byte; missing `TM_TOKEN` produced the expected configuration error and exit 64 |
| Image rebuild | BuildKit built a Linux/amd64 image using only the extracted Dockerfile and source |
| Healthy idle client | Zero payload; stayed running through 47.01 seconds of measurements; no replacement request; clean exit on operator stop |
| Confirmed unavailable client | One replacement request after 30.112 seconds from client start; no local restart |
| No status/statistics replies | One replacement request after 60.051 seconds from client start |
| Client process exit | Replacement requested after 0.101 seconds from client start |
| New/reused deployment recipes | Isolated API fixtures verified fresh baselines, ten-worker creation, reuse without cloud mutation, uncertain-create readback, and no start after failed baseline capture |
| Recorder and recovery page | Independent fixtures verified duplicate suppression, exact byte/rate arithmetic, separate provider credits/earnings, stale-status handling and page/API responses |

The worker timing tests ran in actual containers with real wall-clock time. **The vendor client was replaced by a controlled local test client** to make failures repeatable, and the Docker network had no external access. The IMDS endpoint was deliberately unavailable there: the tests verified the outgoing recovery attempt and fallback exit 75, **not** a new machine allocation by Salad. Account API fixtures were simulated; a fresh billable deployment and future paid traffic were not reproduced during that documentation audit.

These results support rebuilding and exercising the documented software. They do not prove every external account, registry, API or machine will remain available, that every relay request succeeds, or that earnings will repeat. Use fresh provider readings and native client counters to measure a restored deployment's actual results.

## Verify this folder

Use the manifest check in [README.md](README.md), then follow [SETUP.md](SETUP.md). The folder copy recipe replaces the old Markdown extraction recipe. Source hashes, local documentation links, shell/Python recipes and imports were checked after the split. The running cloud deployment, Mac runtime and stored measurements were left unchanged.

## Historical version-7 schema-2 reliability checks

The staged migration preserved all original values across 594,407 retained samples. Replaying actual cloud logs enriched receipt metadata, recovered ten delayed samples totaling 2,682 bytes, and was idempotent on a second pass. No experiment baseline was reset.

Controlled worker tests exercised positive payload, zero payload, repeated short outages, complete silence, missing statistics with status still responding, process exit, failed IMDS requests and operator stop. They execute the actual loop with a controlled client and accelerated monotonic clock; they do not manufacture paid traffic or prove a Salad replacement was allocated. Log tests covered reverse/capped pages, resumable failures, conflicting duplicates, old receipts with apparently fresh source times, and stale API reads.

A retained-history check kept the exact 5,599,254,243 postbaseline bytes equal to the chart total. Local measurements were 1.113 seconds for a chart rebuild and 0.089 seconds with the chart reused; these are Mac staging timings, not production CPU claims. Production timings and public-page checks must be recorded after deployment on the configured AWS CPU setting.


## Historical version-7 live reliability rollout — 7 September 2026

The schema-2 recorder was installed on AWS with root-owned application files. A consistent SQLite/cursor backup and matching deployment record were preserved at `/home/salad/.hg1/traffmonetizer/backups/reliability-20260907` before migration. All **633,797** pre-migration rows and every original column were compared after migration: zero missing rows, zero changed original values, and the monetary/traffic baseline remained unchanged. New samples continued arriving with real Salad receipt timestamps.

The live group command was updated at approximately **15:21 UTC** to worker version **7**, ten replicas. The actual command decoded to the documented worker hash. The concurrent country trial had already moved placement to `gb`; the update preserved that filter. Historical US and new country-trial traffic remain in the original ledger and must not be compared as one country-specific experiment.

The first historical catch-up cycle took 59.084 seconds. Following collection cycles returned to 7.7–17.3 seconds; one measured post-rollout cycle took 8.165 seconds. These measurements used the existing `t4g.small` with Unlimited CPU credits, verified by the EC2 API; no temporary CPU-mode change was made. A later periodic reconciliation reproduced the same publication delay. The final scheduling correction separates history/provider work onto a maintenance thread, prioritizes the newest current-log windows, adapts dense windows and resumes saved historical progress. Independent tests verified foreground publication while history stayed blocked, the dense 240-event case retaining all ten newest clients, and consistent totals/chart values during concurrent writes. The page/API continues to show unknown health whenever evidence is actually stale; widening the freshness limit was not used to hide this failure.

A controlled live client-exit test on instance `3d6e520e-5ca8-4937-a12f-2b951e872465` produced a schema-2 automatic `reallocate` event at **15:24:14.347 UTC**, reason `Traffic Monetizer client exited`. The container itself received IMDS **HTTP 200** on its first attempt at 15:24:14.350 UTC. At the next recorded check the old instance had left inventory and the recorder correctly showed `replacement_pending`, with nine healthy clients. This was an actual workload request, not a dashboard reallocate click. The replacement instance `8d5f4369-785f-4352-8de6-30b1a3f1283b`, machine `29c822e2-128a-045d-8ae9-ca6187ed2b09`, subsequently published fresh connected telemetry. The full ten-client fleet was confirmed at **15:29:55.662 UTC**, **341.315 seconds** after the request. That platform allocation delay is distinct from the immediate in-container decision. The recorder stored `fleet_restored` with that confirmation time.

Independent review found and verified corrections to two additional issues: the standalone fallback now marks stale receipt evidence Unverified, and `control.py create` refuses surviving identity/history before any account calls. The exact SETUP copy recipe restored all eight final source files into a clean staging home and rejected a repeat overwrite. The optional Opus UI review could not run because its existing OAuth session had expired; no review success is claimed for it.


Final production scheduling verification: **2026-09-07T15:57:35.901000+00:00 → 2026-09-07T15:58:19.740000+00:00**. Four consecutive publications reported ten running and ten confirmed clients with no recorder/history/provider errors. Collection durations were **4.869, 6.665, 3.573, 3.695 seconds**, while sample count advanced from 655,807 to 656,277. All ten current clients had positive native payload growth in their observed windows. The provider separately reported **2,234,080,811 credited bytes / $0.2081 gross earnings** at its recorded account observation. These are measured readings, not a promise of future revenue.

Source installed on AWS during that version-7 rollout: observer `608ee278f583304b9025d09e748c4642f083201fd3435c756cf051cf23120f9a`, control `b695012ec129e252a25a6bebf52bc65a739d336e120ae2429b22386e536c3337`, worker `1bdff48628a80f70ec129a43d4ca72b3a34490eb893176b6f61b72e96d238130`. The Mac observer remained disabled. The optional Opus review stayed unavailable; the final timeout/deadline, concurrent history, recording and recovery changes received independent review and their regression checks passed.


Public integration is complete: frontend `b2352e939ce769b4a2608d0e4a2d2dea24f60bfc5a6dc9d5030acf9c92a2340d`, API `43db2364fe858f0e61842873801a5fc09f8111e22ece22982f8eedc8df8fd397`. The shared owner restarted only the dashboard and preserved the Unix-socket/security configuration. Website/source contains the matching final protocol dependencies, including worker.py. Its 50-file restore and focused integration checks passed.

The signed-in public page was checked after deployment: all four time ranges changed correctly, selecting a minute showed measured IP/country/MB contributions, native payload and replacement countdowns appeared in current rows, and recovery request/outcome details appeared below them. Honeygain and PacketStream still loaded through their existing tabs; the browser reported no console warnings/errors.

The concurrent country trial subsequently moved TM to Germany. The above ten-client proof is dated **before that country transition**. During Germany allocation, fewer than ten clients were confirmed; one new instance `6b23defd-adea-4979-95c0-cc3fadc8002d` had a source clock about70 seconds behind receipt and delayed available logs, so the page correctly remained Unverified for it. That concrete node finding was handed to the active country-trial owner for inspection/replacement. It must not be silently counted as healthy or mixed with the earlier stable validation window.

## Healthy-idle correction — 2026-09-07

Version 8 removes the 15-minute payload-idle replacement rule. Worker hash: `9abf2983254dc09ee2a8bc8c37c8e477b1482f47eac0fc27181661e428c541ef`. Run the included checks from the protocol folder, not its `source/` or installed runtime directory:

```bash
cd "$HOME/Desktop/salad/TraffMonetizer"
python3 -B -m unittest discover -s tests -v
```

The two tests exercise the full worker loop with controlled clock, native replies, counters and IMDS: 40 simulated idle minutes, traffic arriving after 30 minutes without a restart, recorded zeros, and continued replacement for process exit, disconnection and unresponsive native status. These fixtures do not generate live customer traffic. Command readback matched at 16:50 UTC; the earlier live failure test remains historical evidence for the retained failure path.

At 16:53 UTC the read-only runtime check found 10 current machines emitting the new disabled-idle policy, with cloud state counts {"running": 10}. 10 of those emitted connected native state. This is a rollout observation, not evidence of paid traffic; recent source/receipt freshness is checked separately.


## Final failure-only verification — 7 September 2026

All ten actual instances were checked on version 8 with worker hash `9abf2983254dc09ee2a8bc8c37c8e477b1482f47eac0fc27181661e428c541ef`, and all ten emitted `reallocate_on_idle:false`. The saved deployment hash was corrected after command verification without changing the monetary or traffic baseline.

The remaining timing discrepancy was measured directly in the running container: host epoch 1788800618.009528, HTTPS Date `Mon, 07 Sep 2026 17:04:41 GMT`, cache Age 0, round trip 0.163 seconds. The host was 62.990 seconds behind that independent HTTPS clock. That faulty host (`8cab1991-2675-8d5b-983c-e8eee7e4afcd`) was reallocated after this diagnosis; this was a clock-fault repair, not a low-traffic replacement.

At 2026-09-07T17:12:31.343000+00:00 the recorder confirmed **10/10 running and 10/10 with fresh native status and statistics**, no recorder/provider/history errors, and a 3.864-second collection cycle. The faulty host was absent from current inventory. Original source timestamps and stored history were preserved.

A parallel API audit additionally corrected statistics expiration: confirmation now requires both native reply ages within 60 seconds, and stale/missing statistics cannot display old relay values. Ten focused fixtures covered healthy zeros, missing/expired replies, clock skew, stale receipts and historical recovery confirmation. Final observer hash: `6b8f41aafcd8ebbecf650adabf9f7eaa16add6c44a288547b1b68291d63ff56b`; API hash: `e130a3eba8d601b22b9eb45d70323d4d7473f297f116e8061dc005d6e011bcde`.

Final closeout at 2026-09-07T17:21:01.953000+00:00: all ten running, all ten confirmed with fresh statistics, all ten failure-only policies, errors {}. Served frontend hash `0b286b99c6b43743dcd2ebc5a68d68ea13a1c7c2050b211b0c358a04330d81e4` matched the source bundle. The final frontend regression keeps missing credited bytes as Not reported and preserves a real zero as 0 MB. Both the eight-file TM manifest and 51-file shared manifest passed.
