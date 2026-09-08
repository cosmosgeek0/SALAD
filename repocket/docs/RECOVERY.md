# Backups and troubleshooting

Back up the **whole `repocket` folder**, including its code, guides and `SHA256SUMS`. Keep a complete copy of this folder outside the computer; losing the computer and its only local copy loses the recovery package too. A single guide file is no longer a complete backup. Credentials, historical databases and the vendor image require the separate backups described below.

| Symptom | Check / action |
|---|---|
| No workers after create | Run explicit `start`, inspect group state, credit and replica quota. |
| `authorization_error` | Verify the Repocket email/Docker key in the account; node replacement does not repair account authorization. |
| `Salad read returned HTTP 401/403` | Repair Salad API access in Keychain; this is the recorder credential, not the RP Docker key. |
| HTTP 408/429/timeouts | Let the recorder's next loop retry, check API access and source age; old values must remain labeled stale. |
| `BlockingIOError` from recorder | Another recorder holds `observer.lock`; run exactly one. Do not delete the lock file to bypass the process lock. |
| Port 8787 occupied | Use the healthy existing dashboard or select another port for the recovery viewer. |
| `ENETUNREACH` with IPv6 | The requested destination may be unreachable from that node; changing inbound listening addresses does not establish outbound reachability. Do not relabel the error as a DNS failure. |
| Many errors but useful traffic | Read recent target traffic and policy state; raw error counts are not earnings and no longer directly trigger the current replacement policy. |
| Replacement accepted but fewer than ten running | Wait for Salad allocation/download/startup and inspect those states. The worker cannot force provider capacity to exist. |
| Local history disappeared | Restore the SQLite backup; code alone cannot recreate already-expired provider logs. |
| Image digest unavailable | Load an earlier saved official image archive or obtain that exact image from a trusted source. The custom source cannot reconstruct the proprietary vendor image. |

For image preservation on a machine with Docker, before an outage:

```bash
cd "$HOME/Desktop/salad/repocket"
mkdir -p backups
docker pull --platform linux/amd64 docker.io/repocket/repocket@sha256:5888d756de7e0e74b95b5eb08bb93f4240a0ce840c910a7e528d1143ad0c502b
docker image save --platform linux/amd64 docker.io/repocket/repocket@sha256:5888d756de7e0e74b95b5eb08bb93f4240a0ce840c910a7e528d1143ad0c502b -o backups/repocket-official-amd64.tar
```

Use Docker whose `docker image save --help` and `docker image load --help` list `--platform`. The unqualified save command failed on the measured multi-platform image; explicitly selecting `linux/amd64` succeeded. To load the saved platform on a Docker machine:

```bash
docker image load --platform linux/amd64 -i backups/repocket-official-amd64.tar
```

Loading this untagged archive reports an image ID and need not recreate the original Docker Hub manifest-list name. Record the printed ID, inspect its platform with `docker image inspect IMAGE_ID`, and tag/publish it if a new registry is needed.

The commands create the tar in `backups/` inside this package. Store a backup copy outside this computer. A local archive is not automatically a Salad-accessible registry; if Docker Hub disappears, publish it to a registry you control and update the image reference only after verifying image contents/platform. Running the worker on an ordinary local Docker host does not reproduce Salad IMDS self-reallocation.

For **production history backup**, use SQLite's online backup API on AWS and preserve the matching metadata/cursor, or stop `salad-repocket.service` and `salad-repocket-provider.service` while copying `/home/salad/.hg1/repocket`, then restart both. Include SQLite/WAL/SHM, `deployment.json`, `cursor.json`, `view.json` and any `provider.json`. The retired Mac `~/.hg1/repocket` history is not a current AWS backup. Preserve the group UUID and cursor with that history; never attach a different group's data under the same state. Secure account recovery and credentials separately in a password manager. This package restores program/configuration, not historical payments, balances, accounts or deleted logs.
