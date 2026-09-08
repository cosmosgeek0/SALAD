# PacketStream recording and operations

Production recording is on AWS Mumbai. The paths and launchctl commands below describe the preserved Mac/local-rebuild layout. Keep the retired Mac jobs disabled while AWS owns recording; see [website operations](../Website/OPERATIONS.md).

## Minute-record contract

The cloud wrapper emits PS_MINUTE_V2 text lines. An example shape, with illustrative values only:

~~~~text
PS_MINUTE_V2 instance=UUID machine=UUID observer=START_MS seq=N start_ms=A end_ms=B rx=RX_DELTA tx=TX_DELTA total_rx=RUN_RX total_tx=RUN_TX ip=PUBLIC_IP state=running error=none final=0 bucket_ms=UTC_MINUTE_START
~~~~

- Values are integer bytes and Unix milliseconds. Network MB = (rx+tx)/1,000,000; this includes overhead and both directions of relayed traffic.
- observer identifies the wrapper run; seq is monotonic within it. Never join counters from different runs.
- The first record establishes the baseline. Normal records cover UTC-aligned minutes; shutdown records can be partial.
- A final replacement record has state=reallocating and final=1. Its parser must accept that state.
- Counter resets/gaps/invalid records remain explicit. Missing data is not zero.
- Exact V2 minute buckets remain exact. Old V1/unaligned intervals are proportionally split and labelled estimated rather than erased.
- The group-wide log collector retains departed instances' measurements; it does not restrict history to current members.
- Full Salad result pages are recursively split into time windows; records are deduplicated in SQLite. Do not advance over unexamined capped pages.
- Country lookup uses api.country.is and is informational; geolocation is not proof the provider accepted a residential IP.

SQLite schema and calculations are defined in source/dashboard/native_network.py. Its tables include minutes, countries and collector status; runtime code creates/migrates them. Preserve the whole database, not just the latest JSON census.

## Native client status and current inventory

packetstream-monitor/audit-client-status.py reads Salad instances and native Status lines. The PS_NATIVE prefix includes the actual runtime instance ID, because Salad log resource IDs can lag a rollout. The included ID must match the current API instance before claiming native acceptance.

The website checks source freshness separately from provider credit freshness. A node may be cloud-running but still starting, downloading, reallocating, or awaiting a client sample. A stale local feed must not become a new machine-failure signal.

## Locations and operations

| Location | Purpose |
|---|---|
| ~/Desktop/salad/PacketStream/source/packetstream-monitor/start-with-recovery.sh | Editable cloud wrapper |
| ~/Library/Application Support/Salad Bandwidth Dashboard/ps1-native-recorder.py | LaunchAgent entry point |
| Same root / packetstream-monitor/native-census.py | Orchestrates status and minute collection |
| Same root / packetstream-monitor/audit-client-status.py | Current native acceptance |
| Same root / packetstream-monitor/native-network.py | Complete minute log collection |
| ~/.hg1/packetstream/observer-target.json | Current group binding; prevents retired-mode fallback |
| ~/.hg1/packetstream/native-census.json | Latest safe inventory and native state |
| ~/.hg1/packetstream/minutes.sqlite3 | Durable recorded minute history |
| ~/.hg1/packetstream/provider-observations.jsonl | Actual provider byte observations |
| ~/.hg1/packetstream/dashboard-periods-*.json | Observed group starts/stops, scoped to the group |
| ~/Library/LaunchAgents/com.cosmosgeek.ps1-recorder.plist | Local observer |

~~~~bash
launchctl print "gui/$(id -u)/com.cosmosgeek.ps1-recorder"
launchctl kickstart -k "gui/$(id -u)/com.cosmosgeek.ps1-recorder"
curl -fsS http://127.0.0.1:8787/api/ps1/minutes
~~~~

Check the actual plist's stdout/stderr filenames. The reconstruction installer uses native-recorder.out.log and native-recorder.err.log in ~/.hg1/packetstream.
