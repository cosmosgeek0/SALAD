# Pawns troubleshooting

[Start here](README.md) · [Check the current instance](setup.md#verify-the-current-deployment)

Always match logs to the current instance and its start time. Old instances can leave error messages in the group history.

## Recovery inside the workload

These are configured rules, not promises of placement time or earnings:

| Condition | Action |
|---|---|
| `ip_used` or `non_residential_ip` | Stop the SDK and request a new Salad machine immediately. |
| SDK process exits, closes its output, or is suspended | Stop any remaining child process and request replacement. |
| SDK has not reached Running after launch | Replace after the configured 120-second startup deadline. |
| SDK reports a persistent `not_running` error | Allow recovery until the fixed 120-second deadline. Repeated errors do not extend it; a Running event clears it. |
| Fresh provider checks repeatedly report the current IP offline | Replace after the configured 120-second observation span. An IP/account change, a positive observation or an unavailable check clears the window. |
| SDK or account API reports an expired session | Exit so Salad restarts the container and obtains a fresh login. |
| Supervisor stops updating its heartbeat | The configured Salad liveness probe restarts the container. See [Setup](setup.md#configure-the-supervisor-health-check). |
| Provider or collector data is unavailable | Show unavailable/stale evidence. Missing credits or telemetry alone does not trigger replacement of a healthy client. |
| Fresh provider sold traffic remains unchanged while this is the sole active IP | Record an idle observation after the configured 30-minute window. Keep the healthy connected machine running. Low traffic or earnings do not trigger replacement. |
| Initial login fails | Transient failures get at most three attempts with Retry-After/backoff. HTTP 401/403/422 ends this login cycle after the first failure and backoff. Invalid credentials require correction; changing machines does not repair them. |
| SDK reports `unsupported_version` | Report Update required and exit after a pause. Rebuild with a verified supported SDK; cycling IPs does not update software. |

IMDS replacement uses up to three attempts, with a configured request timeout of ten seconds and fifteen seconds between failed attempts. HTTP 200/204 means the request was accepted. Exhausted attempts end the container so Salad's restart policy can take over. Shutdown interrupts further retries; an already accepted request remains recorded as accepted.

`PAWNS_RECOVERY` records distinguish requested, accepted, failed, interrupted and container-exit phases. The collector records a result only after a later run has fresh native and provider confirmation. On this single-replica deployment, a different observed machine is a replacement; a new run on the same known machine is a restart. Missing machine identity is recorded as a healthy run with placement unknown. A result closes that request and is not counted again after an unrelated later restart.

## Login and sharing errors

| What you see | What to check or do |
|---|---|
| `authenticate user failed (please use SDK)` | This was the tested CLI's failure. Use the image from [Rebuild](rebuild.md), empty Command, and environment keys `PAWNS_EMAIL` and `PAWNS_PASSWORD`. |
| `Pawns login HTTP ...` | Read the status and check the credentials in Salad. A saved browser login does not verify the entered password. Stop a repeatedly failing group before correcting it; keep credentials out of chat and logs. |
| SDK `not_running` with `"error":"ip_used"` | Pawns rejected the assigned IP as already sharing. The launcher requests replacement through Salad IMDS and records `PAWNS_RECOVERY` phases. An accepted request is not proof the replacement finished; verify the new instance. If no replacement follows, use **Instances → Reallocate** for the failed instance. |

Measured automatic recovery on September 7, 2026, using the exact image in [Rebuild](rebuild.md): the SDK process on instance `c63e383b-e7cb-470d-ade2-ce1e9907764e` was deliberately suspended at **17:09:21.127 UTC**. The supervisor recorded `client_suspended` and requested replacement at **17:09:21.539 UTC**; Salad IMDS accepted it with HTTP 200 at **17:09:26.556 UTC**. No external recorder requested that replacement.

The collector confirmed the replacement at **17:16:05.212 UTC**, after fresh native Running and provider Active evidence for GB IP `95.144.198.53`. The machine changed from `1040aa2e-24d8-d558-a148-8f2e0896a5eb` to `cc8582ee-fc0a-7f5d-835c-14b232ddfa51`, with new instance `a4a41fd7-43d0-4587-9564-882f15e6f8e2`. These are one test's measured identities and times, not promises of future placement time.

Measured liveness recovery on September 7, 2026: the heartbeat was deliberately held stale from **17:30:11.238 UTC**, and the health command changed from exit 0 to exit 1. Salad recorded **“Instance Interrupted (Liveness Probe Failure)” at 17:30:33 UTC** and restarted the container. This exercised the stale-heartbeat path; the supervisor process itself was not frozen.

New instance `74fd53f8-fe2a-4d3b-b322-3336e75f75a2` started a new recorded run at **17:31:21.783 UTC** on the same machine and GB IP. Native Running was saved at **17:32:04.710 UTC**, the provider confirmed the IP active at **17:32:26.338 UTC**, and the collector recorded the healthy restart at **17:32:39.565 UTC**. The live health command returned exit 0 again after restart. All 3,453 pretest rows were unchanged, and the page's new-run values matched the saved intervals. The temporary fault ended with the old container; no ongoing test process or configuration change remains.

Both the automatic machine-replacement and liveness-restart paths therefore passed live checks with this image. Other error branches passed local simulations and are not all claimed as induced live faults.

## Wine startup messages

The previous image had `XDG_RUNTIME_DIR` unset. The updated launcher creates a private runtime directory and sets that variable before launching Wine. The `syswow64/rundll32.exe` failure is consistent with the absent Wine compatibility components in that image. The precise loader cause was not isolated.

In the earlier image's logs inspected on September 7, 2026, these messages were followed by the SDK's `running` event. A provider refresh also showed the matching device Active. Those facts establish that startup continued; they do not establish the warnings' effect on paid sharing. Read later SDK events and repeat the [provider check](setup.md#verify-the-current-deployment).

## Deployment and build problems

| What you see | What to check or do |
|---|---|
| Long **Allocating** state | Preserve the group's selected trial countries and inspect System Events. A stop/start retry was used during the measured deployment; finding a machine still depended on Salad availability. |
| **Downloading / Creating** | Inspect System Events and wait for the image/process preparation to finish. These are not Pawns login results. |
| Local Mac runtime exits with `rosetta error: invalid gdt selector index 5` | This was observed while running the Windows SDK under AMD64 emulation on Apple silicon. Building succeeded there; the SDK ran on Salad's AMD64 machine. Follow the build-on-computer, run-on-Salad flow. |
| Checksum mismatch during build | The vendor download differs from the pinned artifact. Verify the official package, library and interface before changing the source or hashes. Removing the checksum does not verify the new package. |
| Push denied | Sign into the Docker Hub account that owns the username in `PAWNS_IMAGE`, check the repository is Public, then repeat the push. |
| Current runtime produces no stdout/stderr in Salad logs | During integration, a node's sampler, clock and counters were checked but even diagnostic output never arrived. A manual reallocation during the earlier US deployment restored delivery. Check log delivery before treating absent records as a client rejection. |

## Little or unreported earnings

The workload polls Pawns' authenticated account and device endpoints with its existing token. The collector saves provider sold GB, the reported sharing amount and account balance with their own observation times. **Not reported** still means unavailable data, and stale observations remain marked stale. A Running callback is not a credit measurement.

The provider's balance does not attribute earnings to the current instance or observation period. Inspect the account's dated sold-traffic and sharing readings before claiming progress. Low earnings alone do not identify an SDK, network or machine failure.

Provider totals describe the account, not the current worker or chart window. A recorded sold-traffic change requires a baseline and a later provider reading. The idle observation uses unchanged provider sold traffic while the current IP is the account's sole active IP and readings remain fresh. It does not trigger replacement or infer failure from missing data. Multiplying raw container bytes by a payout rate would produce an unsupported earnings estimate.
