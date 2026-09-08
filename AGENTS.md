# bandwidth reel

## Messages between chats, and side chats

A message to another chat is an interrupt, not a conversation. Before sending one, read that chat's recent turns and see what it is doing. While it is mid-task, send nothing unless the message is critical: money at risk, a shared host or file about to collide, or an owner order it must have this minute. One thing per message, a few lines; never findings, plans, tables, or code. A message never changes the receiving chat's task; only the owner gives tasks. A claim relayed by another chat is unverified until the receiving chat has checked it itself.

When a chat's task holds more than one piece of grinding work, or a piece that would pull it away from its own task, it spins up a side chat for that piece instead of doing it in the middle of its own work: a new chat handed this file, the exact task, the files and the live facts that task needs, and nothing else. It grinds on its own and reports its result once, when done. The main chat keeps its own task. A chat starts a side chat through the spawn-task chip, which the owner starts with one click. Sub-agents are the last resort, for one small narrow lookup that returns a fact; never for building, measuring, running, or reviewing. No more chats than the work has pieces.

Mistake on record: 2026-09-06, three chats sent each other dozens of long messages during each other's runs; a record run was restarted, a pipe test was stopped and restarted twice, and code was changed on relayed claims that were withdrawn an hour later; and the main chat ran every record, rerun, and critic round itself while its own task waited.

## Project and starting points

This project runs bandwidth-sharing clients on Salad, records what each instance does, manages client recovery and presents the measurements on one shared website.

- Work in this repository: `~/Desktop/salad`, remote `cosmosgeek0/SALAD`. The [root README](README.md) lists every protocol folder and its entry guide.
- Read the relevant protocol's setup, source and recovery guide before changing it. Keep protocol-specific settings and implementation in that folder.
- Shared page source and collector dependencies are in [Website/source](Website/source/); website setup, data definitions and hosting notes start at [Website/README.md](Website/README.md). Keep bundled copies consistent with their verified protocol source.
- The public dashboard is `https://salad.cosmosgeek.org/`. Read [Website/OPERATIONS.md](Website/OPERATIONS.md) for deployment and data locations, and confirm the active runtime before changing it. Editing the local bundle does not deploy it.
- Start at [Website/README.md](Website/README.md) for Linux production recovery, its connection map and required host configuration. Keep disabled Mac recorders disabled while production recording is owned elsewhere.

## Fix the complete flow

- Use Honeygain and PacketStream as references for native health, recovery, recording boundaries and honest accounting. Read the actual implementation and adapt it to the target client; do not blindly copy its error strings, thresholds or provider assumptions.
- Trace a reported problem through the native client, Salad state/log delivery, recorder, saved data, API and page. Find which layer failed; a different label or graph does not repair a failed client or missing recording.
- Use the protocol's configured organization, group, image, country restrictions, resources and replica count. Read back the current configuration before a cloud change. Do not copy another protocol's identifiers or assume historical IPs are still assigned.
- Implement recovery in the workload where supported, so routine client recovery does not require the Mac or a person clicking the dashboard.
- Each protocol needs explicit handling for its actual failure states: rejected/overused IPs, failed startup, process exits, stalled connections and unavailable telemetry. Set thresholds from the client behavior and documented policy; record the reason for each decision.
- Distinguish a bad node/IP from invalid account credentials, provider restrictions, a collector failure or low customer demand. Reallocation must address the observed cause. Use bounded retries and cooldowns to prevent repeated replacements that only spend credits.
- Keep a native-healthy connected node running even with little or no traffic. Do not restart or reallocate it for a byte floor, an empty payload window, comparison with other nodes, or missing/unverified earnings. Record idle performance as an observation. Any earnings-based replacement policy needs separate explicit user direction and fresh, attributable provider evidence; a traffic counter is not that evidence.
- Record a recovery attempt, whether Salad accepted it, and evidence of the replacement's identity and health. An accepted request alone is not a successful recovery.
- Preserve active experiments, histories and baselines while fixing problems. Changes to deployment size, recording ownership or combined-container experiments belong to the user's requested scope.

## Record and display real measurements

- Keep Salad running state, native client acceptance, measured network traffic and provider-reported credits separate. RX + TX does not establish sold traffic or earnings.
- Preserve source timestamps, receipt times, group/instance/machine identity, run boundaries and counter units. Deduplicate repeated logs. Do not calculate deltas across a reset or replacement.
- Missing or stale data must remain visibly unknown. Keep a measured zero distinct from an absent sample. Report the actual error and which source is stale.
- Keep provider units, observation time and account/device scope with every earnings value. Do not allocate account earnings to individual IPs without evidence.
- Keep one shared minute bar chart above simple server rows. Offer 1, 6, 12 and 24 hours, defaulting to 24. The selected range applies across all protocol tabs and must not reset when switching services. Hover/click shows the contributing IPs, countries and MB for that minute; avoid extra charts and permanent contributor lists.
- Show running/confirmed counts, measured totals, selected-period traffic, available provider credits and elapsed time. Each row should show the country name before its IP, client/cloud state, MB/min, recorded MB, duration, freshness and errors. Label unavailable measurements honestly.
- Do not repeatedly scan full retained history on every browser refresh. Check chart/API performance with realistic history and the actual deployed CPU setting. A temporary CPU boost is not evidence that the normal setting can sustain the load.

## One integration path to Git

- Protocol tasks finish their client, recovery and recorder changes in their own folders. The website task owns the user's latest UI requirements and the shared website bundle. Respect the current deployment/security owner's files during integration.
- One coordinating task collects completed deliveries and handles shared integration, staging, commit and push. Do not edit the same shared files from several tasks or interrupt owners with repeated delivery requests.
- Before committing, verify the complete delivered flow: native state and recovery results, saved samples matching API/row/chart values, correctly scoped provider figures, all affected pages, performance and a reproducible source bundle. Record evidence for the actual final source; an earlier test pass does not verify later edits.
- Make the combined commit only after the protocol repairs, website UI and deployment changes required by that release are finished and verified. Keep missing evidence and known failures open until resolved. Include only completed source and guides; exclude secrets, live measurements and unfinished work.

## Rebuild, verify and save

- Keep ordinary source files and focused setup, monitoring and recovery guides. Include required tools, secret names and how to supply them, image references, deployment commands and observed failure remedies. Keep secret values out of guides, browser responses, logs and Git.
- Make a rebuild possible from the saved source plus the stated external accounts and dependencies. Distinguish local simulation, a successful build and a verified live deployment. Historical data and identical traffic/earnings cannot be recreated from source alone.
- For Honeygain, PacketStream and Website, [restore.py](restore.py) verifies source manifests and restores to an explicitly chosen directory. Use a fresh staging directory for reconstruction checks; preserve conflicting existing installations. Other protocol folders document their own setup.
- Check manifests and shared-file compatibility after completed source changes. A mismatch needs investigation; do not refresh a checksum merely to hide an unfinished or unexplained change.
- Choose checks that exercise the failure being fixed. Counter changes need known inputs and expected deltas; recovery changes need failure and replacement cases; shared website changes need the affected protocols checked. Use a focused independent review when the change warrants it. Documentation edits need accuracy, path and command checks.
- Verify live claims using actual client logs, source freshness, persisted records and provider evidence. State what was checked, when, and what remains unverified. Do not describe a running process or HTTP 200 as proof the whole system works.
- Preserve databases and collection cursors together. Use a consistent database backup, such as SQLite's backup API, before moving live measurements.
- Before the final commit/push, inspect the exact staged files and check that they are the versions verified together. A source backup and a measurement backup are separate.
- Remove only your own temporary files once they are no longer needed. Preserve other tasks' work and real measurements. Finish with the actual change, verification result and any remaining blocker.
