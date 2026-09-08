# EarnFM

Complete source and recovery project for **EarnFM bandwidth sharing on Salad**: ten replicas in **SSH3**, recovery inside each container, persistent traffic and provider recordings, and a shared monitoring page.

## Start here

| Guide | What it contains |
|---|---|
| [Setup](docs/SETUP.md) | Prerequisites, credentials, deployment, dashboard and services |
| [Operations](docs/OPERATIONS.md) | Health checks, logs, troubleshooting and stopping the group |
| [Recovery](docs/RECOVERY.md) | Lost-file recovery, existing-state handling and backups |
| [Reference](docs/REFERENCE.md) | Captured deployment, recovery policy and byte/earnings definitions |
| [Validation](docs/VALIDATION.md) | Checks performed and the limits of reproducibility |

## Project files

```text
EarnFM/
  earnfm.py                    recovery and deployment commands
  config.json                  pinned deployment settings
  manifest.json                source checksums
  container/start.sh           cloud client and recovery policy
  scripts/earnfm-recorder.py    traffic ledger and provider reader
  scripts/keychain-store.swift local credential helper source
  dashboard/static/            standalone recovery page and stylesheet
  tests/                       offline accounting and recovery checks
  reference/historical-record.json  captured metadata; not live state
  docs/                        focused guides
```

All source needed for an EarnFM rebuild is here. **Copy/back up the entire EarnFM folder.** Credentials and historical traffic are not included; [Recovery](docs/RECOVERY.md) explains how to preserve or restore them.

On a new machine, follow [Setup](docs/SETUP.md). For a harmless configuration preview:

```sh
cd "$HOME/Desktop/salad/EarnFM"
python3 earnfm.py plan
```

**EarnFM** is the protocol name. The existing cloud display code `EF`, environment names and `/ef` URL remain compatible with the captured deployment. The original multi-protocol dashboard and other protocols are separate projects.

Production recording runs on the Mumbai AWS host, independently of the Mac. Its code is `/opt/salad/scripts/earnfm-recorder.py`, its state is `/home/salad/.hg1/earnfm`, and its service is `salad-earnfm.service`. The public page is [EarnFM](https://salad.cosmosgeek.org/#earnfm). Keep the retired Mac recorders disabled. [AWS setup](docs/AWS.md) documents the production boundary; the standalone Mac setup remains an optional disaster-recovery path.
