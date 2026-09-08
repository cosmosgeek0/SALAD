# Mysterium verification record

[Guide index](README.md)

**Owner decision — 2026-09-07:** shelve Mysterium and retain its details; no further work or trials are requested. Measured Salad readback at **17:32:57 UTC** confirmed version 8, Stopped, no instances, and autostart disabled. The attempts, failures and limits of the earnings evidence remain recorded below.

This is historical evidence from **2026-09-07**, not a new live-status check. Use [operations](operations.md) to verify a current deployment.

## Reallocation repair — not complete

The earlier successful run did not remain a functioning provider across later replacements. These are **measured** observations from the repair on **2026-09-07**:

| Observation | Result / action |
| --- | --- |
| At 13:27 UTC, instance `315d800f-8ed7-4bc2-9444-18a4ac23622e` was Running/Ready on a different machine. | Native identity `0xc707b9ee77583e1ac42cf7b1d6e20275fa9dc579` was unregistered; logs explicitly delayed proposal publication. Location was Carthage, New York, US. Container-running status did not establish an operational provider. |
| Manual repair of that identity | Configured the existing MystNodes key, observed `eligible:true`, requested registration, and verified Registered without a top-up. A later monitoring session `c18d1747-1a8e-4b63-9f80-045b3bd849e9` recorded 84,394,988 bytes received and 4,066,948 bytes sent over 75 seconds. This was a manual repair, not automatic reallocation proof. |
| First automatic-startup candidate, deployment version 5 | Real instances exited with code 1 shortly after the API started. The launcher assumed an identity already existed. A delayed-identity fixture reproduced its missing-readiness failure; the source was corrected to wait for identity creation. |
| Corrected candidate, version 6 | The actual launcher hash matched `89a8ce2e30c5c37e9a4d97e056465a55f40f739d9827cba76a4484658b44b527`. Identity creation completed, but identity-specific eligibility remained false and the registration marker was absent. Startup timeouts caused further fresh identities. |
| Eligibility investigation | Native requests returned `eligible:false`. Direct upstream reads for failed identities returned HTTP 200 with an empty body; the pinned client treats EOF as no parse error, leaving the eligibility boolean false. This does not establish a specific policy rejection, quota, or recovery deadline. Repeating a claim manually for identity `0xde920c336f189f3a97d3d0bd198dbc6b363babd4` did not change the immediate false result. |
| Placement changed during the repair | A separate owner-authorized country trial changed the group to GB. The placement owner confirmed UK was intended and held further Mysterium changes. This repair preserved that live selection; earlier U.S. observations remain historical. |
| Account inspection | The available Chrome profile did not have the original MystNodes session. Google sign-in unexpectedly opened a new empty MystNodes account. No nodes or container credentials were moved to it. The original Chrome profile later became available and its account was verified by the original user-linked identity. The current replacement was present there, Offline. No account deletion or paid registration was performed. |
| Version 7 live test, started at 16:39:34 UTC | Instance `e5d401fe-76bb-4366-8de8-88f6abbfa975`, machine `4ffdc14d-9d94-3454-a17d-c8efaab1ef38`, identity `0xbdd5f49f4b12ee5e82ea78b9d9d1cfc8f2399895`. At 16:48:45 UTC the native API reported uptime `8m18.628283076s`; location was Lockerbie, Scotland, GB, Vodafone residential IP `90.251.179.105`. The deployed launcher hash matched `c079fbee71c293a9c544c7760a2a678883f259367f5ee83412d28fa7c368ec6c`. Identity remained Unregistered and the readiness marker was absent. The same instance remained running/unready at 16:53:49 UTC. |
| Upstream response on that actual host, 16:52:03 UTC | The identity-specific endpoint returned HTTP 200 with `Content-Length: 0`; the generic provider endpoint returned HTTP 200 with `{"eligible":false}`. Account linking was confirmed by the matching identity/IP in the original MystNodes account. No sponsorship reason or eventual recovery time was established. |
| End of the failed live test | Stop accepted at 16:54:04 UTC; the API confirmed Stopped with no instances at 16:54:52 UTC. The source correction also guards failed account-linking and registration commands, retaining the same identity and reconciling native status before a cooldown retry. |

Review identified the repeated-replacement behavior as a defect. The subsequent source correction keeps the same identity unready while polling eligibility and propagates a daemon failure during registration. It also aligns current setup guidance with the authorized GB placement. Local tests cover retained identity under unavailable eligibility and daemon exit after identity discovery; this correction has not established a successful live registration.

The final candidate image in [setup](setup.md#create-the-deployment) includes the guarded-command correction. It was built and published after the live test above. Salad readback at 16:58:03 UTC confirmed version 8, the exact final image digest, country GB, Stopped, and no pending update. That final correction passed isolated failure tests and was then started for the account diagnostic below; it has not produced a successful live sponsored registration.

The current source is a recovery candidate, not a claim that fresh allocations are operational. No successful automatic sponsored registration or fully working post-reallocation provider was demonstrated with this candidate.

Local checks did establish the launcher behavior for delayed identity creation, an already registered identity, unavailable eligibility, daemon exit, an identity that never appears, account-claim failure followed by recovery, registration-command failure followed by recovery, and an uncertain registration response followed by InProgress and Registered without a duplicate request. These used dummy keys, isolated containers with networking disabled, and a controlled clock for timeout cases. They are not live sponsorship tests. Shell/guide syntax and local links also passed. The independent GPT-6 Astra review ran at max reasoning (session `01a07ccc-f2e8-7cc0-9579-1f62b2047e76`) and found no concrete code or report defect; it explicitly left live recovery unverified.

### Account-specific blocker confirmed

After the owner requested parallel agents, independent source investigations compared native CLI/NodeUI registration and the current MystNodes quick-onboarding flow. The latter supplied the missing account-specific evidence. On **2026-09-07 at 17:14:42 UTC**, `/api/v2/clickboarding/identify` returned HTTP 200 and `isEligibleForFreeRegistration:false` for fresh identity `0x48129754095d6d3d5d566271362c6d26445d57bd` in the original account. Confirm displayed that account's free-registration-limit explanation. No numeric quota or reset time was established. No SSO login request or callback was observed; Proceed was not clicked, and no password, beneficiary or funding operation followed.

The signed link was obtained through the unmodified native onboarding endpoint. One research conclusion that the existing account key necessarily blocks that endpoint was refuted by this actual successful read; the pinned helper performs a nested configuration lookup. The link's decoded fields were exactly `codeChallenge`, `identity` and `redirectUrl`. Neither the link nor its signature is saved here.

The final version 8 image was started at **17:07:32 UTC**. At **17:17:05 UTC**, instance `d4cab330-e25c-42bf-bdb5-b93902a53739` on machine `df3af9d4-6e5f-f757-b1bd-d7e9c30b9066` reported native uptime `8m46.631888085s`, version `1.39.5`, process 8, and launcher SHA-256 `3df1691bf1c8e4632a913d54b5cbf7d713706687f9558eea627fa5308ac9cafa`. Location was Brighton, England, GB; British Telecommunications Limited, residential IP `86.139.215.15`. Identity remained Unregistered, native balance was zero MYST, and the registration marker was absent. This verifies the actual final launcher on a fresh filesystem, not a functioning or earning provider.

Stop was accepted at **17:18:21 UTC** after the account restriction was confirmed. API readback at **17:20:21 UTC** confirmed version 8, country GB, Stopped, and no instances. The remaining requirement is [a supported registration path plus identity persistence](troubleshooting.md#account-registration-limit); restarting or replacing a container does not itself grant registration eligibility. None of the historical public identities in this record can be operated from this source package without their separately retained private data.

A read-only local backup check found no Mysterium installation in the documented default data paths, no Mysterium Docker container or named/labeled volume, and no keystore in this source folder. The four detached anonymous Docker volumes each contained only a regular file named `uuid`; their contents were not read. Temporary helpers used read-only mounts and no network, and were removed. This establishes no usable backup on those checked local surfaces, not that the owner has no backup on another device.

## Recorded deployment

The image update was accepted at **2026-09-07 08:35 UTC**. The fresh instance became Running/Ready at **08:39:35 UTC**, and registration completed by **08:43 UTC**. The monitoring-pending endpoint included its identity during onboarding and no longer listed it at the measured **08:51:26 UTC** read, after completed sessions appeared. These identifiers describe this snapshot; always discover the new identity after rebuilding.

| Field | Measured value |
| --- | --- |
| Organization / project / group | `cosmosgeeketh` / `default` / `mysterium` |
| Instance | `9e03148a-4cd9-45d1-852f-3b2ece8965b8` |
| Machine | `85436a6f-593f-a55c-90d0-869a2f074a88` |
| Mysterium identity | `0x825390ae8af6af54c55a4cb0378c38a1d1bbdd30` |
| Location | Plano, Texas, US; AT&T Enterprises LLC; classified residential |
| Public IP | `12.131.55.162` |
| Salad / native identity | Running, Ready, Started / Registered; MystNodes also showed this identity Online, United States |
| Discovery | Normal query returned this identity at **09:09:56 UTC**, without `include_monitoring_failed=true`; its proposal had quality `0.8` and no monitoring-failure flag. |
| Test outcome | Completed monitoring sessions below; native/public monitoring `success`; absent from pending list; normal discovery eligible; customer delivery not asserted |
| Native resolver / MTU | Started from the saved command with `nameserver 1.0.0.1` and MTU `1100` |

At the measured **08:57:54 UTC** read, the upstream detailed quality feed contained this identity’s `.data_transfer`, `.dvpn`, `.monitoring`, `.scraping`, and `.wireguard` entries with quality `0.8`, latency `25.47`, bandwidth `0`, uptime `0.17`, and packet loss `0`, with no monitoring-failure flag. Normal discovery still returned `null` at **09:00:29 UTC**, then returned the identity at **09:09:56 UTC**. The exact documented public-check block also returned monitoring `success`, no pending entry, and the normal proposal. The published discovery source uses that detailed feed and substitutes zero fields plus a failure flag when its cached entry is missing; this is not proof of a new failed probe. Its deployed cache duration was not established. [Pinned discovery source](https://github.com/mysteriumnetwork/discovery/blob/2aef83e640819e4df1dcf49d90cc27280fba97b4/proposal/metrics/enhancer.go).

The fresh image recorded these **measured** native sessions, all `direction: Provided`, `service_type: monitoring`, `status: Completed`, and `provider_country: US`:

| Session ID | Created at (UTC) | Duration (seconds) | `bytes_received` | `bytes_sent` |
| --- | --- | --- | --- | --- |
| `adf2caa2-c34b-468b-a87c-2914f06e1a74` | 2026-09-07 08:47:12 | 38 | 6511064 | 1001508 |
| `ed615b58-8996-4167-8013-f8371d95fa39` | 2026-09-07 08:49:34 | 92 | 132773052 | 4880004 |
| `91bebc8c-75fa-463b-b551-5fd6bb00a88a` | 2026-09-07 08:52:00 | 63 | 130985464 | 6205012 |

Their exact measured receive-counter total was **270,269,580 bytes**; the send-counter total was **12,086,524 bytes**. These totals are arithmetic over monitoring records, not a customer-traffic or earnings claim.

A later scraping record was `New` with zero stored byte counters; it is not counted above as a completed customer transfer.

The earlier Texas identity `0xdab9936d468965cc1d8282c29808481f8d481cb4` belonged to instance `64b5bb24-ef09-4207-bd20-6becd94d0e10`. The version 4 image update replaced that filesystem and created the fresh identity above, while retaining the same measured host/IP. This is why an image update also requires rediscovering and registering the identity.

The original user-linked identity `0x056f1396e48ec3d0808b87e671ea44ad4c8011be` was an existing offline India node. It was not moved or reused. Fresh Salad filesystems created new identities linked to the same MystNodes account. Old account rows can remain after their Salad instances are gone; they are not a list of currently running Salad replicas.

For the current owner account, [open the Salad group](https://portal.salad.com/organizations/cosmosgeeketh/projects/default/containers/mysterium) and [open MystNodes](https://my.mystnodes.com/nodes). A direct node-statistics URL may redirect to the node list while MystNodes has not populated that identity's dashboard state.

## Reproduction audit

The following first audit covered the original stock setup, before the later MTU correction. Its failed results are historical, not the final monitoring status:

| Test actually performed | Result and limit |
| --- | --- |
| Fresh local pull of the pinned image for `linux/amd64` | Digest resolved; the binary reported version `1.39.5`, commit `c45527af`. The documented entrypoint and `myst`, `wget`, `timeout`, `nslookup`, `awk`, and `sh` were present. |
| Documented launch command with `--help` appended, in a fresh local container with networking disabled | Entrypoint setup and launch-flag parsing succeeded. The node service was not started and no account key was supplied. |
| Entire embedded Python body with real hidden terminal prompts, dummy keys, and intercepted HTTP transport | Both simulated creation success and HTTP-error paths passed. The request contained the intended U.S.-only settings; dummy keys were not echoed. This did not test live Salad creation acceptance. |
| Request configuration compared with a fresh authenticated GET of the existing Salad group | Image, command, resources, country restriction, replica count, priority, and restart/autostart settings matched. Request/response priority placement and omitted GPU selection were accounted for. |
| Documented native read-only checks replayed individually on the existing Salad instance | Health responded; location remained Plano, Texas, US; the identity was Registered and native services were Running. Monitoring remained `failed`. |
| Documented public-API block executed with only the identity placeholder substituted | Returned that identity's monitoring failure and its published U.S. residential monitoring proposal. |

A fresh **measured read at 2026-09-07 06:12:28 UTC** of the earlier node's `/sessions` returned the following records for `0xdab9936d468965cc1d8282c29808481f8d481cb4`. All were `direction: Provided`, `service_type: monitoring`, `status: Completed`, and `provider_country: US`:

| Session ID | Created at (UTC) | `bytes_received` | `bytes_sent` |
| --- | --- | --- | --- |
| `e647bd33-5b72-4fbf-ab7d-93e2449348aa` | 2026-09-07 05:24:04 | 31484 | 6684 |
| `09e5ab75-70c1-463a-a28b-e9cbdabf7f2d` | 2026-09-07 05:25:32 | 27756 | 6492 |
| `0e4555ae-243c-4269-bf49-3b8f44c1a689` | 2026-09-07 05:27:14 | 35004 | 6396 |

These are measured history fields and byte counters, not proof of successful customer payload delivery or a passing monitoring verdict. The earlier empty `/sessions` responses preceded these records.

Shell/Python syntax checks and an actual-credential scan also passed. No live key is stored in this file.

**Not re-executed in the first audit:** cloud creation, Start/Stop, account claiming, registration, DNS changes, Restart, Recreate, or Reallocate. Those operational steps are documented from the earlier live trial. A fresh host, its IP/ISP, sponsorship eligibility, and monitoring outcome depend on the services' current state; the file cannot guarantee the same identity, host, or result after deletion. Recovering the exact old identity requires its separately saved private data.

The resumed audit built the corrected image from a fresh pinned source archive, inspected its applied source change and binary version/hash, and ran the exact saved command with `--help` in a fresh local container. The image push and anonymous digest read passed. Salad’s saved version 4 and the fresh runtime binary hash, U.S. location, MTU, resolver, sponsorship eligibility, and Registered identity were verified. No compiler, status helper, packet capture, or capture package was put in this final image.

## Trial cleanup

The fresh runtime was checked for cleanup: `/tmp/myst-status-probe`, `/tmp/myst-live-headers.log`, and the temporary `.myst-capture` package were absent. The local trial image, its exact build-cache records, and build-history records were removed; the published deployment image remains available. Cleanup tooling was corrected for a nullable cache-parent list and for Docker history requiring the short build ID rather than its full displayed reference. No unrelated local images or project files were deleted.

The reallocation-repair cleanup removed its temporary test/review files, task build history, local image and scoped build cache. The published image and source/guides remain. An accidental empty MystNodes account from the earlier wrong-profile sign-in remains unused; its tab was closed, and the node key continued to target the original account.

The final guide check found an actual HTTP-client difference: an authenticated group GET through Python's default `urllib` header returned `403`, while the same request with `User-Agent: mysterium-setup` returned `200` and the expected group. That header is now explicit in the creation recipe. No duplicate creation request was submitted; syntax and saved request settings were checked separately.
