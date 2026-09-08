# EarnFM validation

[Start here](../README.md) · [AWS](AWS.md) · [Reference](REFERENCE.md)

## Current release — version 12

Version **12** is the current recorded deployment. At **17:02 UTC on September 7, 2026**, all ten current instances were running and emitted `activity_min_bytes:0` with native `state:running`. Healthy zero-traffic clients remain running; real connection failures retain the embedded recovery path. The startup source is `6654e0f11669b62689c9b2601c4614ca258f06e3dcbd6266ad652b5d1e8fdf36`. See [the healthy-idle correction](#healthy-idle-correction--2026-09-07) for rollout and verification details. Native running state is not proof of paid traffic.

## Historical v11 repair checks — September 7, 2026

The earlier repair was deployed to the existing ten-replica SSH3 group as cloud version **11**, preserving its active GB country trial, pinned vendor image, original measurement start and provider baseline. No new earning account or duplicate group was created. The old target file's version-6 metadata was corrected from the actual cloud readback.

The v11 decoded cloud startup source matched the then-current `container/start.sh`, SHA256 `99f620aea5605a3b11711acff6596d2eb55ff3cac09184697c69f34e72e3b017`. The AWS recorder matched `scripts/earnfm-recorder.py`, SHA256 `ace046752e63e2a9419ed6d0edfe05896e385862f7343bc80c552408f430b31c`.

### Offline failure and accounting checks

- **17 container cases passed** inside the pinned AMD64 image with external networking disabled: connected, silent connection, repeated native error, 429, preserved cooldown, low activity, foreign egress, process exit, three failed IMDS attempts, 401, 403, 36-hour IP-change pause, configured UK guard, unavailable counters, recovered connection flap, buffered authentication errors, and a large startup burst followed by silence.
- These fixtures replace the native process, geo responses and IMDS response at explicit boundaries, and accelerate the monotonic clock. Child-owned sockets and `/proc` inspection are real inside the image. They verify wrapper decisions and event/final-sample behavior, not an actual paid provider workload or a real IMDS replacement.
- The startup-burst case sends more than 4 MB across the isolated loopback fixture, then goes quiet. It still produces exactly one client restart followed by reallocation after a second full observed low window. Connection setup cannot keep resetting that retry count.
- **10 recorder tests passed**: source/receipt clocks, exact interval byte/duration conservation, old-schema cache migration, retired IP attribution, zero versus unavailable measurements, group identity rejection, capped-page/cursor handling, malformed/conflicting entries alongside valid records, persistent observation faults and replay handling, and bounded source timestamps with legitimate future retry deadlines, and last provider IP/time kept separate from current confirmation.
- **5 deployment guard tests passed**: preserving country/identity/baseline/unrelated environment, mismatched-country refusal, orphan-state refusal, concurrent-version refusal, and preserving the existing cloud client credential when a local entry is unavailable.
- Focused shared-frontend tests passed for fresh/stale provider and inventory data, connecting/final states, recorded duration and MB/min, historical IP attribution, old/new payloads and 1/6/12/24-hour ranges. Other protocol normalization results were unchanged by the EarnFM branch.
- An independent review found and corrected stale error windows, authentication-driven reallocation, malformed-record stalls, buffered errors across launches, missing observer errors, unbounded event times and replayed errors after successful measurements.

### Real history and production checks

- A consistent local copy containing **611,111 samples** preserved the exact **3,719,546,359 recorded bytes** when building minute history.
- The actual AWS host migrated a consistent **619,324-sample** copy without changing its recorded-byte sum. Initial cache construction took **8.9 seconds**; the final measured snapshot took **1.557 seconds wall time / 0.131 seconds CPU** with the existing two-CPU host settings and no temporary CPU boost. A loaded intermediate run took 1.493 seconds; the normal service interval is 60 seconds.
- The live pre-upgrade backup contained **633,040 samples**. A field-by-field SQLite join after deployment found **zero changed or missing original rows**. The provider-baseline file retained SHA256 `e3ed955d6535842877846902f2a306671fbfe34dfd294720e4736ecc7391ac4b`.
- The first live pass exposed sequential Salad paging taking roughly 160 seconds through dense old one-second logs. The final collector limits concurrent reads to four and retains the same splitting/deduplication/cursor guarantees. After catch-up, the observed collection needed three requests and about eight seconds; source and inventory freshness recovered.
- During the v11 verification, all ten then-current workloads emitted revision-2 telemetry with one child-owned control socket and the deployed 262,144-byte / 900-second policy. Ten `activity_observation_started` events confirmed the post-setup observation windows in the workload.
- Provider observations accumulated in the database; the API and page showed account credits separately from raw traffic. The current device listing can vary and has shown an unconfirmed device despite an established control socket. A read-only investigation found the exact same runtime/IP in five of fourteen provider observations, so this was not an ID mismatch. The workload itself restarted that client for low activity at 16:03:01 UTC; later confirmation remained intermittent. Its last provider-seen IP and timestamp are retained separately from its current confirmation. At 16:19:13 and 16:19:20 UTC, two low-activity workloads requested their own reallocation after the second full low window. Both old allocations were absent in the subsequent inventory; new instances appeared and began emitting telemetry. At 16:24:47 UTC, all ten current instances—including both replacements—were running and provider-confirmed with fresh control-socket telemetry and no current wrapper errors. The two new instances were `7d44803b-ca94-493d-a9b9-cabe6e07198f` / `94.198.82.99` and `bba1a3f4-da56-4c47-bd43-b864083aa797` / `90.205.146.194`; the two simultaneous replacements are not assigned a speculative one-to-one pairing. The page showed that device as unconfirmed whenever the current provider observation omitted it. This is not proof that all ten nodes earned money.
- The public EarnFM page was checked after reload: all four ranges changed their totals; its 24-hour selected sum matched the recorded total for this experiment; recorded durations appeared; and the 10:05–10:06 historical popup retained ten old US contributor identities/IPs after the live fleet had moved to GB. The observed minute totaled 296.977 MB, with 290.344 MB from its largest contributor.
- Honeygain and PacketStream still rendered their charts and ten rows. These checks do not claim that their current provider/cloud statuses were all healthy. No browser errors or warnings appeared in the EarnFM checks.
- A source-only reconstruction in a directory containing spaces verified all 13 manifest files, generated the ten-replica command, and served all eight standalone HTML/CSS/JSON aliases correctly. The retired Mac recorder remained unloaded and explicitly disabled; no test containers remained.
- The standalone recovery page passed isolated Chrome checks with the actual 1,042-minute retained-history payload, all ranges, freshness failures, error states, popup interactions, old history and missing measurements, including desktop/mobile layout.

## Repeat the offline checks

Run from this protocol folder with Python 3.9+:

```sh
python3 -B tests/test_recorder.py
python3 -B tests/test_deploy.py
```

The optional container suite also needs Docker, the pinned vendor image, and the official `golang:1.24-bookworm` build image for its tiny socket fixtures:

```sh
python3 -B tests/test_recovery.py
```

It uses `.work/` inside this folder for disposable test fixtures/results. A single case can be selected, for example `python3 -B tests/test_recovery.py startup_burst`. It never reads credentials or contacts the paid deployment. Test scratch is removed from the delivered package after the recorded checks; the fixture source is retained.

`manifest.json` checks source, configuration and fixture integrity. `python3 earnfm.py prepare` verifies it on a Mac and prepares the local credential helper. For production operation, use the existing Linux adapter as described in [AWS](AWS.md); do not install a Mac helper on Linux.

## Reproducibility boundary

The complete folder plus the documented external accounts, credentials, pinned images and shared AWS/Website dependencies can rebuild the software. A database backup is required to restore destroyed history. Machine selection, future traffic, provider acceptance and identical earnings cannot be reproduced from source alone. Recovery decisions are tested; a live IMDS acceptance is only a request outcome, and a particular healthy successor requires subsequent evidence.

## Healthy-idle correction — 2026-09-07

The v11 low-activity restart/reallocation observations above are historical and superseded. Version 12 removes that trigger and reports `activity_min_bytes:0`. Focused pinned-image tests passed: healthy idle, startup burst then silence, no control socket, native error, process exit, HTTP 429, rejected credentials and GB placement. The two idle cases kept a single client through multiple accelerated observation windows. Command readback matched source `6654e0f11669b62689c9b2601c4614ca258f06e3dcbd6266ad652b5d1e8fdf36` at 16:50 UTC. Native counters, provider cooldowns, recording and history were preserved.

At 16:53 UTC the read-only runtime check found 9 current machines emitting the new disabled-idle policy, with cloud state counts {"running": 9, "creating": 1}. 8 of those emitted connected native state. This is a rollout observation, not evidence of paid traffic; recent source/receipt freshness is checked separately.

One machine still emitted the old 262,144-byte rule despite inventory version 12. A single `recreate` request was accepted for instance `40aadd9d-7b9a-4f25-a955-0929dd60e3df` to apply the corrected command; it was not a low-traffic recovery decision. The request alone is not a successful runtime verification.

The isolated recreate succeeded on the same machine: at 17:00 UTC, replacement runtime `64d70eb1-b35f-45c0-afde-a1adadca83f3` reported `activity_min_bytes:0`, one control socket, `state:running`, no error, and fresh consecutive samples. The old 262,144-byte runtime is superseded. A separate instance with actual control-connection failure was being recreated by the retained native recovery path; healthy low traffic was not its trigger.

At 17:02 UTC all ten current instances were running and emitted `activity_min_bytes:0` with native `state:running`. The isolated stale-runtime correction and the separate genuine connection-failure replacement had both completed.

## Final page verification

The final shared refresh fix passed seven controlled slow-response/cancellation tests and was verified on the public site. Both the shared EarnFM page and `/ef` loaded current data with all ten containers running and provider-confirmed. The page default is 24 hours; healthy `none` error sentinels are suppressed while real errors remain visible. There were no browser console or CSP errors. Final standalone HTML SHA256: `5c6318efae8f2a5321fba1635db0996e7ede0f7b29bfc3a5741c72ad4de01546`. At the final page check, the provider reported 1,437.514 MB credited and $0.143672 gross account change; recorded interface traffic was 3,941.599753 MB. These remain separate measurements.

## September 8: visible dollars and receipt-clock correction

The live IP `108.88.197.68` had advancing source samples and fresh recorder arrivals while its Salad receipt clock preceded the source by 186–187 seconds. The old receipt-age gate incorrectly hid its online confirmation and MB/min. Source plus first-recorder-receipt freshness now retains this healthy device; original timestamps are unchanged and the clock discrepancy is visible. Stale/replayed data still becomes unknown.

Eleven recorder tests, the signed balance-change test and the frontend regression check pass. A read-only production check matched all valid sample bytes to the minute-cache total exactly (6,870,654,037 bytes at that check). An independent interval calculation for the affected IP returned 0.046963636 MB/min, matching the recorder; live table values now show numeric MB/min to at least three decimals rather than a blanket `<0.1`. All ten devices were provider-confirmed after deployment.

The public page showed the preserved account balance and selected-period signed balance change in USD. The 1/6/12/24-hour provider sums were checked against saved provider observations. No container configuration or earning-client restart was required. Only the recorder and shared dashboard services were restarted; the concurrent Overview CSP correction was preserved.
