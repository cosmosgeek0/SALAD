# Pawns on Salad

Start here. This folder contains the Pawns source, instructions and saved local traffic history.

The computer builds an image; Salad runs it in the countries selected on its container group. The launcher uses the SDK from the official Pawns Windows application through Wine. The cloud client keeps running when the computer is off.

## Choose the instructions you need

1. **Run the saved image:** copy the immutable image reference in [Rebuild](rebuild.md#use-the-published-image), then follow [Setup](setup.md). No local build is needed for this route.
2. **Build from source:** follow [Rebuild](rebuild.md#before-opening-terminal), using the source files in this folder.
3. **Understand an error:** use [Troubleshooting](troubleshooting.md).
4. **Understand the chart and saved history:** read [Website and data](website.md).

## What belongs here

| File or folder | Purpose |
|---|---|
| [Dockerfile](Dockerfile) | Downloads and verifies the official SDK, compiles the bridge and packages the Linux image. |
| [runner.c](runner.c) | Loads the Windows SDK, starts it and prints its callbacks. |
| [run.py](run.py) | Supervises the SDK, checks the provider, records traffic and recovery events, and replaces failed clients. |
| [observe.py](observe.py) | Records native samples, provider snapshots and verified recovery results in the shared website ledger. |
| [.dockerignore](.dockerignore) | Keeps documentation, collector data and temporary work out of the image build context. |
| `data/` (separate data backup) | Preserved history from the retired Mac collector, including its SQLite files and last snapshot; excluded from the source repository. |

The Markdown files explain the work; the source files beside them are the actual program. Keep the **whole folder** when making a recovery copy. A Markdown file alone no longer contains an embedded copy of the program.

The live configuration was measured on September 8, 2026 UTC: one replica, one vCPU, 1024 MiB memory and the United States country filter (`us`). Preserve the group's current country filter when updating it. New machines, IPs, traffic and earnings will vary. A running SDK and raw network traffic do not establish provider credits or profit. Healthy connected machines stay running when traffic or earnings are low.

Put Pawns work and temporary files inside this folder. Remove temporary work when finished. Passwords stay in the provider's runtime configuration and configured credential store, outside the source and documentation.

Recovery rules and their verification are described in [Troubleshooting](troubleshooting.md). The health-check command is embedded in the image; Salad's liveness probe must be configured as shown in [Setup](setup.md).
