# PacketStream setup

Production recording runs on the separate AWS Mumbai host. This guide preserves the Mac rebuild recipe, including macOS Keychain and LaunchAgents; it does not rebuild the AWS services. Keep the retired Mac jobs disabled while AWS owns recording. See [website operations](../Website/OPERATIONS.md) for the current hosting layout.

## Required external inputs

You need the Salad account/API key, the PacketStream account's **CID**, funded hyperlane/default access, the pinned official image, and macOS with Python 3.9+, curl and Xcode Command Line Tools. The CID is entered at rebuild time; do not copy somebody else's account identifier. No passwords, API keys, live browser sessions or traffic-history database are embedded.

This package recreates the software and a new run. Original sold-traffic/provider history and local minute history require their own surviving backup or still-retained provider logs. The closed-source vendor image requires the registry or an independently saved image archive.

## Captured deployment configuration

These settings were checked on 7 September 2026. Group revisions and instance IDs are observations from that check; read the current group before changing it.

| Setting | Verified value |
|---|---|
| Organization / project / group | hyperlane / default / ps-test-us |
| Historical group ID | a36f8bba-0b01-4e86-9948-0cedb2fac3de |
| Layout | One group, ten replicas, one official PacketStream client per replica |
| Image | docker.io/packetstream/psclient@sha256:6e6a2cefe9f49c33f6c9d4bd41d21daf20c4767f2c66e82f57a5960ec9923987 |
| Runtime architecture | Linux amd64; official /usr/local/bin/pslauncher |
| CPU / memory / shared memory | 1 CPU / 1,024 MiB / 64 MiB per replica; no GPU |
| Placement / priority | US / batch |
| Restart policy / captured auto-start flag | always / false; explicitly started |
| Public networking / probes | None configured |
| Captured group revision | 7 |
| Cloud display name / image caching | PS Test US / enabled |
| Complete command SHA-256 | e55cd5a1c6e8ea102600732b775ba71bb7c42cf0ac51f8763b8f7202d2d0b948 |
| Environment | CID only; no Salad account API key inside the workload |
| Local rebuild dashboard | http://127.0.0.1:8787/#ps1 |

**The URL fragment #ps1 is a UI name. The live Salad group is ps-test-us.** The old group ps1 and its custom port-8789 collector are retired paths. Do not bootstrap from scripts/ps1-control.py or allow the native recorder to fall back to its old ps1 branch. The binding file below is mandatory.

## Restore and start

1. Restore this folder's verified source using the shared repository helper. It refuses to overwrite different files.

```bash
cd "$HOME/Desktop/salad"
python3 restore.py PacketStream
```

2. Build the Keychain helper and enter the Salad API key.

~~~~bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
mkdir -p .runtime
chmod 700 .runtime
xcrun swiftc scripts/keychain-store.swift -o .runtime/keychain-store
chmod 700 .runtime/keychain-store
python3 scripts/save-secret.py salad-bandwidth-api
~~~~

Use the existing Salad API key for the account that can access the named organizations. The prompt is hidden; the key goes to macOS Keychain service **salad-bandwidth-api**, account **your macOS login name**. Never put the key in these guides, a command argument, or a copied cloud JSON response. A freshly compiled helper may trigger the normal macOS Keychain access prompt. Keep only one PacketStream observer process running; the preserved native recorder does not enforce a singleton lock.


3. Validate the payload without external actions.

~~~~bash
python3 -B scripts/rebuild-cloud.py packetstream plan
~~~~

4. Create/start the ten-replica deployment, entering your CID at the hidden prompt. This starts billable cloud workloads.

~~~~bash
python3 scripts/rebuild-cloud.py packetstream create
~~~~

If the cloud group already survives, use:

~~~~bash
python3 scripts/rebuild-cloud.py packetstream bind
~~~~

The script verifies the full documented configuration and a nonempty CID. In create mode, an existing group must also match the CID just entered; a mismatch stops before starting it. In bind mode, confirm that the surviving group belongs to your PacketStream account. Secret values are never printed. It saves the current, newly returned group ID to ~/.hg1/packetstream/observer-target.json:

~~~~json
{"mode":"native-census","organization":"hyperlane","project":"default","group":"ps-test-us","group_id":"ACTUAL_ID_FROM_SALAD"}
~~~~

Do not reuse the historical group ID after deleting/recreating the group.

5. Start the local observer:

~~~~bash
python3 scripts/install-services.py ps
~~~~

The installed ps1-native-recorder.py sees mode=native-census, sets PS_GROUP and PS_EXPECTED_GROUP_ID, then runs packetstream-monitor/native-census.py. It never starts Docker Desktop. Native census runs about every 30 seconds; minute collection runs independently about every 15 seconds.

Follow [Website setup](../Website/SETUP.md) to serve the graph. The minute recorder itself is usable without the website.
