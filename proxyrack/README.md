# Proxyrack: the complete client and recorder folder

**This is the canonical Proxyrack source. Copy this whole folder.** It contains the Salad deployment program, exact installed container supervisor, recorder dependency, Linux credential reader and service definition. The Proxyrack entries under `Website/` are links to this source, not separate programs.

Docker containers run on Salad. The recorder runs on Linux; the Mac only edits files and connects to that host. No Docker build or local Docker daemon is required. The shared website is a separate application that reads this recorder's published data.

## Exact deployment

Measured against the existing Salad group on 8 September 2026:

| Setting | Value |
|---|---|
| Organization / project / group | `ssh1` / `default` / `pr` |
| Current group ID / version | `ab9fd890-55b8-42ab-86ac-957fe8ce3d87` / `7` |
| Replicas / placement | `10` / United States (`us`) |
| Per replica | `1` vCPU, `1024` MiB RAM, `64` MiB shared memory, no GPU |
| Priority / restart | `batch` / `always` |
| Image | `docker.io/proxyrack/pop@sha256:7de6719f37b31d5dd354f8cdd3ae601b4ed401832d0935ff460f968e0b6731bc` |
| Startup | `proxyrack.py` packages the exact `pr-worker.js` bytes into the Salad command override |

Fresh creation uses these settings. A surviving group keeps its identity and placement. Never paste the historical group ID into a replacement deployment: `init` discovers the surviving group or prepares a new namespace. Provider device IDs derive from that namespace and each Salad instance ID.

The supervisor downloads the official native program from `https://app-updates.sock.sh/peerclient/go/client` and its version from `https://app-updates.sock.sh/peerclient/go/version.txt`. These vendor downloads remain mutable; version 60 was observed in the verified deployment. The pinned image and saved supervisor do not pin that external binary.

## Files and prerequisites

| File | Role |
|---|---|
| `proxyrack.py` | Initialize identity, deploy/read/update the group, collect logs and publish readings |
| `pr-worker.js` | Native client supervision, network samples, registration and recovery inside Salad |
| `dashboard/` | Included Python dependency used by the recorder; no standalone website |
| `linux/keychain-store` | Existing Mumbai Secrets Manager credential interface |
| `linux/recorder-secrets-policy.json` | Existing secret's required IAM permissions |
| `linux/salad-proxyrack.service` | Linux recorder service |
| `linux/ssh_config` | Existing Mumbai SSH-over-Session-Manager connection |
| `SHA256SUMS` | Exact source checksums |

Required outside Git: funded Salad access for `ssh1/default`, a Proxyrack Peer account/key, a Linux host with Python 3.9+ and curl, and access to the pinned image and native download. The supplied Linux credential reader additionally needs boto3 and AWS permission to the secret named inside it. Credentials and retained measurements are not source files.

The secret's JSON must retain `salad-bandwidth-api` and `proxyrack-peer-api`. The bundled helper uses the existing Mumbai secret ARN and `/run/salad-credentials` cache. Restore secret values through the owner's private Secrets Manager access; do not put them in this folder or print the helper's `--read` output. A replacement AWS account/secret needs its real ARN and corresponding IAM permission, not a copied credential value in source.

## Install the recorder on Linux

On the Mac, the existing connection is:

```sh
cd "$HOME/Desktop/salad/proxyrack"
ssh -F linux/ssh_config salad-mumbai
```

This requires the owner's configured AWS CLI access, Session Manager plugin and existing SSH key. The routine `ubuntu` account cannot install system files with blanket sudo. Run installation commands through the existing IAM-authorized AWS Run Command root session, or as the administrator of a fresh Linux recorder host.

Copy this complete folder to the host and enter it. For a **fresh Ubuntu recorder installation**:

```sh
sha256sum -c SHA256SUMS
apt-get update
apt-get install -y python3 python3-boto3 curl
id salad >/dev/null 2>&1 || useradd --system --create-home --home-dir /home/salad --shell /usr/sbin/nologin salad
install -d -m 0755 /opt/salad/dashboard /opt/salad/.runtime
install -m 0644 proxyrack.py pr-worker.js /opt/salad/
install -m 0644 dashboard/__init__.py dashboard/native_network.py /opt/salad/dashboard/
install -m 0755 linux/keychain-store /opt/salad/.runtime/keychain-store
install -d -o salad -g salad -m 0700 /home/salad/.hg1/proxyrack /run/salad-credentials
install -m 0644 linux/salad-proxyrack.service /etc/systemd/system/
systemctl daemon-reload
```

On the existing shared host, compare installed hashes first and install only the finished changed files. Preserve its credential helper, ownership/ACLs, databases and cursors. Do not run a second recorder on the Mac or another host against the same deployment.

## Bind, deploy, record

Run on the prepared Linux host:

```sh
cd /opt/salad
runuser -u salad -- python3 -B proxyrack.py init
```

`init` only reads Salad and writes local `deployment.json`. It adopts the existing group's namespace, image and original creation time, or creates fresh local metadata when no group exists. It preserves a matching existing manifest and refuses a conflicting identity. It never starts containers. If rebuilding a deleted group while keeping older recordings, select a separate `PR_DATA_DIR`; do not reset the old ledger.

**The next command creates or starts paid Salad containers. Run it only when you intend to start the deployment.**

```sh
runuser -u salad -- python3 -B proxyrack.py deploy
runuser -u salad -- python3 -B proxyrack.py status
systemctl enable --now salad-proxyrack.service
```

For recorder-only recovery of an existing group, omit `deploy`. Preserve or restore its data first, run `init`, then start the recorder service. If the cloud command differs and you deliberately intend a rollout, `python3 -B proxyrack.py update` applies the saved supervisor while preserving group identity and placement. Run it as the `salad` user on this host. A rotated Peer key must also be updated in the group's `PR_API_KEY` through the owner's Salad access; `deploy` and `update` do not replace an existing registration key.

Default state is `/home/salad/.hg1/proxyrack`. `PR_DATA_DIR` selects another state directory; set the same value for initialization, deployment and recording, and adjust the service's writable path accordingly. `PR_KEYCHAIN_HELPER` selects an existing compatible credential helper.

## Verify actual operation

```sh
systemctl status salad-proxyrack.service --no-pager
journalctl -u salad-proxyrack.service --since '10 minutes ago' --no-pager
cd /opt/salad
runuser -u salad -- python3 -B proxyrack.py status
```

Verify all of these against fresh source evidence:

- Salad has the intended group, image, command, resources, placement and replica count.
- Native `PR_MINUTE_V2` samples advance for the actual instance/machine, and registration/control state is confirmed. Salad's running state alone is insufficient.
- `traffic.sqlite3` and its `collector` cursor advance; `view.json` has fresh inventory, no collection error and `backfilling: false` after catch-up. The reader fetches only the minute/event tags it accepts, splits capped pages and counts actual insertions.
- Provider status and account readings succeed independently. Cached balances and counters retain their original timestamps. The shared [Proxyrack page](https://salad.cosmosgeek.org/proxyrack) reads `/api/proxyrack`; installing this recorder does not install the shared website or its authentication.

The worker handles native exits, failed startup, connection/process stalls and repeated provider-offline observations. Account/authentication errors use cooldowns. Healthy idle clients remain running; traffic or earnings floors do not trigger replacement. An accepted reallocation is not proof the replacement is healthy.

## Keep history separate from source

Retain `deployment.json`, `traffic.sqlite3`, `cursor.json` and the original provider cache together. SQLite also contains provider observations and recovery history. `view.json` is derived output. Preserve source timestamps, run/instance/machine identities and the original recording boundary.

Before moving live recordings, use SQLite's online backup API and copy the cursor before the database backup. Restore that consistent set with only the recorder stopped. A source installation cannot reconstruct deleted history or private credentials. Stopping the recorder does not stop paid containers; stop the group through the [Salad PR page](https://portal.salad.com/organizations/ssh1/projects/default/containers/pr) and read back its stopped state.

Network values are decimal RX + TX MB for the whole container interface, including overhead. They are not process-only traffic or sold bandwidth. The Peer bandwidth counter's physical unit remains unverified; do not convert it to MB or dollars or assign the account balance to IPs.

## Verification boundary — 8 September 2026

The image, supervisor command and recorder dependency matched the installed deployment. The folder passed isolated import/checksum checks, and `init` adopted the real stopped group then preserved its metadata on a second run. Website source restoration and Linux service-link materialization passed. The last direct Peer balance check returned HTTP 502. Successful provider registration/acceptance still needs a fresh check when the service is available. No paid deployment or claim of profitable demand is part of this source consolidation.
