# Troubleshooting and verification

Use [SETUP.md](SETUP.md) for the cloud client and [MONITORING.md](MONITORING.md) for the recorder.

## Known failures

| Symptom | Meaning and correction |
|---|---|
| `/etc/earnapp/uuid: No such file or directory` | The state directory was absent. The supplied startup script creates it before writing the saved ID. |
| `systemctl: not found` during first initialization | The old image has no systemd service manager. The supplied script runs EarnApp in the foreground afterward. Check the actual registration result and process. |
| `earnapp showid` returns `undefined` | No device was initialized and no saved ID was supplied. Use the fresh-device setup; `showid` alone did not generate an ID in the measured test. |
| `Failed registration` / `EAI_AGAIN` despite `enabled` | The client can report enabled while registration fails. Investigate the reported network/DNS error; do not count the status word as success. |
| `name_conflict` | Use an unused Salad group name while retaining the correct saved EarnApp UUID. |
| **Allocating** with no worker | Read System Events and resource/country settings. If demonstrably stalled, a Stop/Start cycle restarts allocation on the same group; deleting a group is unnecessary. |
| Telemetry instance ID disagrees with Salad log labels | Salad's log envelope kept the previous instance ID/version after the measured update. This recorder preserves that label and matches the actual runtime/machine instead. |
| `ValueError` parsing a log time | The actual Mac parser rejected a fractional second with five digits. The current collector normalizes fractional seconds and resumes from its saved cursor. |
| API `415 Unsupported Media Type` | Salad PATCH requires `application/merge-patch+json`. The portal supplies this automatically. |
| EarnApp `403 auth required` | The observed account API requires its session cookies and `xsrf-token` header. Renew the session using the monitoring instructions. |
| SSH `Permission denied (publickey)` | Use the connected Salad browser Terminal; this setup does not require SSH-key installation. |
| launchd error `113` or bootstrap error `5` | The measured Mac jobs were explicitly disabled/unloaded. Check `launchctl print-disabled "gui/$(id -u)"`; enable the EarnApp service only when choosing to resume it. |
| Collector reports a duplicate-writer lock | Use the existing running collector; do not launch another for the same data directory. |
| Dashboard amount or usage stays unchanged | Check the advertised refresh time and match the device ID/IPs. Monthly Rate and network bytes are not credited dollars. |
| Old errors remain in logs | Check source time and runtime. Historical log entries are not current failures. |

The cloud image also lacked `curl` and Perl's `Time::HiRes` module in the measured inspection. `startup.sh` uses its existing Bash, `wget`, `date`, `flock` and Linux counters.

## Reading the data honestly

- `sample_ms` is the original counter observation time; `recorded_ms` is its first saved local receipt; `inventory_ms` is the last successful inventory read.
- Counter traffic includes control traffic. The chart divides intervals crossing minute boundaries proportionally and marks those points `estimated`; incomplete points are `partial`.
- Errors keep their machine, source time and original log identity. Ambiguous runtime attribution remains explicit. Cached online status cannot erase a newer error.
- A confirmed supervised client requires fresh inventory and a native registered state from the current runtime, a live EarnApp process, and a fresh provider-online observation after registration. Provider online-since can predate the counter baseline or persist across reconnections; it is not a per-IP earnings timestamp. `enabled`, process presence, or network bytes alone are insufficient.
- A fresh empty inventory has known zero workers. Stale or unverified counts remain null.
- Earned amounts are reported device totals across the device's IPs. They are not assigned to a specific worker or treated as a payout.

## Historical evidence

The checks below were performed on September 7, 2026; moving this folder did not refresh them:

- The pinned official binary matched the earlier cloud binary's SHA-256 in SETUP.md; its measured size was **49,072,804 bytes**.
- Fresh-install and saved-ID branches ran in isolated containers, with network registration deliberately unavailable in that test.
- The cloud command update from measured version **3 to 4** retained the group, image, replica count and saved device ID.
- At **08:43 UTC**, the last measured on-demand pass had **82 contiguous source records**, **307,305,339 recorded bytes**, and **$0.051 device earnings**. The byte sum matched the raw counter difference and the chart sum.
- The local restart test preserved its prior sample bodies and provider history when launchd restarted the collector. That test preceded the later explicit disabling of the Mac jobs.
- Independent review corrected stale error attribution, cached-status precedence and empty-inventory counts, then returned **no concrete defect found**.

## Recovery boundaries

Keep `data/` intact when moving or upgrading. Its database holds the original records and checkpoints; a recreated folder cannot manufacture deleted history. Public image/download availability, cloud capacity, credentials and future paid demand remain external dependencies.

The historical reorganization validated paths, links, source equivalence and saved-data integrity. It did not deploy a new client, enable the Mac services or claim that the relocated background service had been live-tested.

Current recovery behavior is defined in [RECOVERY.md](RECOVERY.md). A current download/allocation has no measured traffic until its native sampler starts; its missing readings stay unknown while older recorded intervals remain visible.

## Current repair verification

Measured on September 7, 2026 at 16:55 UTC: the deployed command was version 6, with one US instance, the saved UUID and pinned image unchanged. The native client was registered, EarnApp reported it online, and the public page displayed the same current instance and provider device total as the recorder.

The live run's 13 source records were contiguous: interval bytes summed to 172,256 and the raw counter difference was also 172,256. The retained US chart and database total both measured 1.371594 MB at that observation. These are dated observations, not promised rebuild traffic or earnings.

A controlled live process exit produced exit code 143, a final interval, an accepted native replacement request, and a different instance. That successor remained provider-offline; the recorder requested its replacement, then verified the next US instance using fresh native and provider evidence. The version 6 update subsequently retained that machine and IP while starting a new measured run.

Isolated checks also covered registration failure, persistent DNS/startup failure, rejected non-US placement, failed replacement requests, stale heartbeat, final-interval accounting and clock rollback. A pause/resume/stop test exposed a signal-handler race; the handler now sets a flag, and the repeated test exited cleanly with its final sample and no replacement request. Simulated healthy idle operation with unchanged credits for 48 hours issued no request. These isolated checks do not establish paid traffic.
