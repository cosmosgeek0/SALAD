# Honeygain setup

Production recording runs on the separate AWS Mumbai host. This guide preserves the Mac rebuild recipe, including macOS Keychain and LaunchAgents; it does not rebuild the AWS services. Keep the retired Mac jobs disabled while AWS owns recording. See [website operations](../Website/OPERATIONS.md) for the current hosting layout.

## External prerequisites

You need access to the Honeygain account, a Salad API key, funded deathadder/default access plus read access to cosmosgeeketh/default and hyperlane/default for the duplicate-registration check, macOS with Python 3.9+ and Xcode Command Line Tools, and the pinned vendor image below. Credentials are deliberately not embedded. Docker is only needed if you want to save/test the image locally; the running Salad clients do not depend on Docker Desktop or this Mac.

This rebuild starts new measurements. Deleted JSONL/SQLite history cannot be calculated back from today's counters. If you need the old chart too, preserve the [recording data directories](MONITORING.md#locations-and-service-operations) separately. A source bundle cannot reproduce a closed-source vendor image if both the registry copy and your image archive are gone.

## Captured deployment configuration

These settings were checked on 7 September 2026. Group revisions and instance IDs are observations from that check; read the current group before changing it.

| Setting | Verified value |
|---|---|
| Organization / project | deathadder / default |
| Layout | Ten independent groups; one replica in each |
| Groups | hg1, hg-solo-02 through hg-solo-10 |
| Runtime | Official Honeygain 0.6.6, Linux amd64, one stock client per container |
| Image | docker.io/honeygain/honeygain@sha256:5cd8c361517d0cbae4aa2c75e13239e45f9193ab8e205d57fa29f2e695ea3ec1 |
| CPU / memory / shared memory | 1 CPU / 1,024 MiB / 64 MiB per container; no GPU |
| Placement | US |
| Priority | hg1: batch; the other nine: low |
| Restart policy | always |
| Auto-start flag in captured API readback | false; the groups were explicitly started |
| Public networking / probes | None configured |
| Captured group revisions | hg1: 8; other nine: 2 |
| Cloud display names / image caching | HG1 Native 0.6.6; HG Solo 02…10 / enabled |
| Wrapper command SHA-256 | d253f4f5dad66c00222f843bd9b0e33d16d7c9a0ed7f64da2742b5a057bcae8d |
| Environment names | HONEYGAIN_EMAIL, HONEYGAIN_PASSWORD, HONEYGAIN_DEVICE_NAME |

The API returns priority at the **group** level, although creation specifies it in container.priority. Do not mistake a missing container.priority in a GET response for the actual scheduling priority.

| Group | Honeygain registration/device name |
|---|---|
| hg1 | salad-us-1 |
| hg-solo-02 | worker-us-1 |
| hg-solo-03 | salad-c4385ee4-0693-505d-8bd4-76f0e37054a9 |
| hg-solo-04 | salad-5cd61ffc-5e1a-7f55-86a6-ebf67cf06478 |
| hg-solo-05 | salad-b8ababd8-ac4b-d45c-b6a0-b499236dee05 |
| hg-solo-06 | salad-45ef0f8f-0a89-6a5d-9f16-9b606250128e |
| hg-solo-07 | salad-eeec7129-d81e-d851-8a2e-2a94747b15d2 |
| hg-solo-08 | salad-62d87783-409d-825e-9125-d5166b9038e0 |
| hg-solo-09 | salad-d645de46-f7cc-1859-98a4-cfe7f88bc346 |
| hg-solo-10 | salad-a1d8dea8-73bc-5356-8980-b652388c1659 |

These registration names are intentional. Reuse them after the previous clients have stopped; do not generate a new name on every retry. Never run two live clients with one registration. If an old deployment still exists in deathadder, cosmosgeeketh, or hyperlane, inspect it before creating replacements. New Salad group/instance/machine UUIDs must come from API responses; the old UUIDs are historical identifiers, not reusable creation parameters.

## Rebuild from this folder

1. Run the shared restore command. It checks this package's source manifest and refuses to overwrite different existing files. For an intact existing installation, use an empty staging directory instead of copying over live files.

```bash
cd "$HOME/Desktop/salad"
python3 restore.py Honeygain
```

2. Compile the credential helper and save the Salad key.

~~~~bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
mkdir -p .runtime
chmod 700 .runtime
xcrun swiftc scripts/keychain-store.swift -o .runtime/keychain-store
chmod 700 .runtime/keychain-store
python3 scripts/save-secret.py salad-bandwidth-api
~~~~

Use the existing Salad API key for the account that can access the named organizations. The prompt is hidden; the key goes to macOS Keychain service **salad-bandwidth-api**, account **your macOS login name**. Never put the key in these guides, a command argument, or a copied cloud JSON response. A freshly compiled helper may trigger the normal macOS Keychain access prompt. Do not start multiple copies of an observer: each uses a lock.


3. Inspect the offline cloud plan. It performs no login, cloud change, or data write.

~~~~bash
python3 -B scripts/rebuild-cloud.py honeygain plan
~~~~

4. For a fresh deployment, run the command below. It prompts for the Honeygain email/password, creates only missing named groups, and explicitly starts them. It keeps those credentials in process memory and sends them directly to Salad's container environment. This step starts billable cloud workloads.

~~~~bash
HG_FLEET_DIR="$HOME/.hg1/hg-fleet" python3 scripts/rebuild-cloud.py honeygain create
~~~~

If the cloud groups already survive and only the Mac was lost, use **bind** instead of create:

~~~~bash
HG_FLEET_DIR="$HOME/.hg1/hg-fleet" python3 scripts/rebuild-cloud.py honeygain bind
~~~~

The helper checks the full documented configuration, required credential fields and each registration. In create mode, surviving groups must also match the email/password just entered. A mismatch stops the rebuild before starting that group; secret values are never printed. In bind mode, verify the surviving provider account through the next actual provider reading.

The receipt is saved to ~/.hg1/hg-fleet/deployment.json. This bootstrap does not use the old Fleet.deploy() path that assumes hg1 already exists. That old helper remains in the preserved operational source, but is not the fresh-install recipe.

5. Get a real provider baseline, then a native client/network reading.

~~~~bash
HG_FLEET_DIR="$HOME/.hg1/hg-fleet" python3 scripts/hg-provider-observer.py --once &&
HG_FLEET_DIR="$HOME/.hg1/hg-fleet" python3 scripts/hg-fleet-observer.py --once &&
python3 scripts/initialize-recording.py
~~~~

If Honeygain has not registered all ten devices yet, the provider observer fails explicitly. Wait for registration/recovery and rerun; never fill missing registrations or credits with invented zeros. The baseline initializer refuses to reset an existing test.

6. Start the local recorders. These jobs collect evidence; recovery itself runs in the Salad containers.

~~~~bash
python3 scripts/install-services.py hg-provider hg-fleet fleet
~~~~

For the hosted shared page, follow [Website setup](../Website/SETUP.md) and restore its bundle into a separate fresh directory. Its production Linux recorder modules can differ from this Mac diagnostic package; do not combine both bundles over the same destination. Honeygain's native logs and JSONL observers work independently of that page; the standalone fleet recorder can show missing PacketStream inputs until that service is restored.
