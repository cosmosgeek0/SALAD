# Honeygain recording and operations

Production recording is on AWS Mumbai. The paths and launchctl commands below describe the preserved Mac/local-rebuild layout; they are not instructions to re-enable the retired Mac jobs alongside AWS. See [website operations](../Website/OPERATIONS.md) for hosting.

## Recording and credit sources

| Component | What it records |
|---|---|
| Container wrapper | Native client state and eth0 cumulative counters |
| scripts/hg-fleet-observer.py | Salad group/instance inventory, bounded native log queries, per-worker state/sample and a separate recovery-event ledger |
| scripts/hg-provider-observer.py | Authenticated Honeygain dashboard credits and provider device/IP evidence |
| fleet-test-recorder.py | Shared append-only experiment observations and per-run counter increments |

Provider requests use https://dashboard.honeygain.com with POST /api/v1/users/tokens, then /api/v2/devices, /api/v1/earnings/stats and /api/v1/users/balances. The provider observer reads the account credentials from the surviving hg1 container configuration, keeps its token only in memory, and backs off on failures. Do not export a login token into the dashboard's public JSON.

Network MB is decimal bytes / 1,000,000 and sums receive plus send; relayed data can appear in both directions. Credits are provider observations with a separate clock. The website uses measured counter intervals to estimate minute contributions; it does not invent exact one-second Honeygain measurements.

Source sample.time and runtime instance identity must survive recording. Salad sometimes emits 5–7 fractional timestamp digits; pad/truncate to six before Python 3.9 parsing. After rollout, log resource labels have been observed to retain an old instance ID. The current Honeygain observer matches the current machine and time boundary for the self-recovery wrapper, and uses its fresh state-bearing samples.

The released observer records bounded current-machine lifecycle events and counters. Its lifecycle projection keeps the event time and status; it does not retain a complete recovery-event ledger. Requested and accepted replacement markers share the displayed `reallocating` state. Original departure reasons or outcomes cannot be reconstructed from that reduced history alone. Check retained native logs and the subsequent instance's health before claiming a recovery succeeded.

## Locations and service operations

| Path | Purpose |
|---|---|
| ~/Desktop/salad/Honeygain/source/scripts/hg-fleet-control.py | Editable deployment/recovery source |
| ~/Library/Application Support/Salad Bandwidth Dashboard/ | Installed runtime; jobs execute here |
| ~/.hg1/hg-fleet/status.json | Latest safe aggregate inventory/status |
| ~/.hg1/hg-fleet/worker-NN.json | Latest worker snapshots |
| ~/.hg1/hg-fleet/observations.jsonl | Original source timestamps, counters, instances, credits |
| ~/.hg1/hg-fleet/provider-latest.json | Last provider baseline/current observation |
| ~/.hg1/hg-fleet/provider-readings.jsonl | Append-only provider observations |
| ~/.hg1/hg-fleet/provider-feed-status.json | Provider freshness/error |
| ~/.hg1/hg-fleet/provider-api-traffic-latest.json | Provider traffic detail where published |
| ~/.hg1/fleet-tests/ | Shared experiment metadata, network accumulator, observations and events |
| ~/Library/LaunchAgents/com.cosmosgeek.salad-hg-*.plist | The two Honeygain observer jobs |
| ~/Library/LaunchAgents/com.cosmosgeek.salad-fleet-test-recorder.plist | Shared ten-second recorder |

The source/scripts/install-services.py helper uses .out.log/.err.log under these directories. The original running installation used observer.stdout.log/observer.stderr.log and provider-observer.stdout.log/provider-observer.stderr.log for the Honeygain jobs; inspect the actual plist to find the live log names.

~~~~bash
launchctl print "gui/$(id -u)/com.cosmosgeek.salad-hg-fleet-observer"
launchctl kickstart -k "gui/$(id -u)/com.cosmosgeek.salad-hg-fleet-observer"
launchctl kickstart -k "gui/$(id -u)/com.cosmosgeek.salad-hg-provider-observer"
~~~~

Restarting an observer does not reallocate a cloud client. For an individual failed instance, use the exact current instance ID from GET /organizations/deathadder/projects/default/containers/GROUP/instances with POST .../instances/INSTANCE/reallocate. Do not rotate the whole fleet to repair a stale local display.

## Verification before declaring success

The original packaging recheck on 7 September 2026 restored all nine files from the preceding self-contained snapshot, validated every manifest hash and rejected both damaged content and conflicting existing files. The isolated creation/start/rebind rehearsal produced the documented ten one-replica groups using simulated Salad responses. Read-only Salad comparisons matched all ten real group configurations and the pinned command digest. The registry still returned the exact Linux amd64 image manifest. No new paid containers were launched by this check.

This Git package preserves the released observer and the independently verified standalone Mac recording recipe. An unpublished experimental recovery-ledger extension is excluded from the release backup. For the current AWS fleet/cost recorder, restore the separate Website bundle; do not mix its newer Linux dependencies into this standalone package.

Read ~/.hg1/hg-fleet/status.json: every claimed connected worker needs a current running instance, a fresh sample and a positive client state without a later error. Confirm the JSONL file advances, and independently confirm the provider-feed status and credit timestamps. On http://127.0.0.1:8787/#hg1, the known running count and confirmed-client count must remain distinct.

For recovery, inspect native logs for HG_SELF_IMDS_ACCEPTED and then compare instance/machine IDs. A test that merely prints a reallocation request is insufficient.
