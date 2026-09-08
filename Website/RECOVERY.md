# Recover the hosted website

Use this with [CONNECTIONS.md](CONNECTIONS.md), [SETUP.md](SETUP.md), the application source and the Linux configuration files. These are recovery instructions, not permission to delete a working host or start duplicate recorders.

## Choose the loss case

| What was lost | Recovery |
|---|---|
| Mac/workspace only | Restore the private repository or source backup; reconnect to surviving AWS through SSM. Do not start Mac recorders. |
| Application files only | Restore the verified source and Linux units on the existing host; preserve data, Secrets Manager and Cloudflare objects. |
| AWS host/disk | Launch from a verified AMI/data backup, or build a fresh host below; reconnect the surviving tunnel. |
| Cloudflare objects | Restore the Access policy/MFA and tunnel mapping below; update newly assigned IDs. |
| History and client deployments too | Recreate clients using their protocol guides, bind new IDs, and begin new recording. Deleted history needs its separate backup. |

Required external access: the private source repository/backup, AWS owner/admin account, Cloudflare and domain-registrar access, the owner's security key/recovery method, and provider account access. Runtime data and secret values are not in this repository.

## Recreate AWS when needed

Use the owner/admin AWS console in Mumbai. The scoped routine CLI can manage the existing host but is not a provisioning administrator.

1. Reuse the VPC/subnet in CONNECTIONS if they survive. For a replacement network, create a VPC with a public subnet in Mumbai, an Internet Gateway, and a default route to that gateway. Give EC2 outbound Internet access/public IPv4; a NAT Gateway is unnecessary for this layout.
2. Create a security group with **no inbound rules** and the documented outbound access. Do not add port 22, 80 or 8787.
3. Reuse the Secrets Manager secret in CONNECTIONS. If it was deleted, create **Other type of secret**, plaintext JSON `{}`, named `salad/mumbai/recorder-credentials`; record its new ARN. Values are populated through the hidden prompts in SETUP.
4. Recreate the EC2 role/profile `salad-dashboard-mumbai` with [instance-role-trust.json](linux/instance-role-trust.json), the inline [Session Manager policy](linux/instance-role-policy.json), and [recorder-secrets-policy.json](linux/recorder-secrets-policy.json). If the secret was recreated, replace that policy's Resource and the helper's `secret_id` with the new ARN. Grant only GetSecretValue/PutSecretValue for that secret.
5. Launch Ubuntu Server **24.04 ARM64**, `t4g.small`, **Unlimited** credits, IMDSv2 required/hop limit 1, IPv6 metadata disabled, and the role/profile above. Use an encrypted **50 GiB gp3** root volume. The captured host settings and IDs are in CONNECTIONS.
6. Verify SSM Agent is online. Open **EC2 → instance → Connect → Session Manager**, then install the operator's SSH public key for `ubuntu` if needed. Update the SSH configuration's HostName for the new instance and the operator's IAM session target permission.

The captured AMI was `ami-0b2c6d4daacfcfeb4`. If unavailable, select Canonical's current Ubuntu 24.04 ARM64 image; its published SSM lookup is `/aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id`. [Canonical image discovery](https://ubuntu.com/aws/docs/aws-how-to/instances/find-ubuntu-images/). SSM requires its agent, instance permissions and outbound service connectivity. [AWS prerequisites](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html).

## Stage the source from a Mac

From the restored repository root, use a new temporary directory. The application restore copies only manifest-listed source.

```sh
set -eu
SALAD_STAGE=$(mktemp -d)
python3 restore.py Website --to "$SALAD_STAGE/runtime"
(cd Website/linux && shasum -a 256 -c SHA256SUMS)
cp -RL Website/linux "$SALAD_STAGE/linux"
ssh -F Website/linux/ssh_config salad-mumbai 'mkdir -m 700 /tmp/salad-recovery'
scp -r -F Website/linux/ssh_config "$SALAD_STAGE/runtime" "$SALAD_STAGE/linux" salad-mumbai:/tmp/salad-recovery/
rm -rf "$SALAD_STAGE"
ssh -F Website/linux/ssh_config salad-mumbai
```

If the remote staging directory already exists, inspect it rather than replacing unknown work. Run the remaining privileged host commands through the AWS Run Command root path in CONNECTIONS, not the unprivileged SSH session.

## Install a fresh Linux host

For a restored full-machine AMI, its users and software already exist: verify them rather than recreating them. On a fresh Ubuntu host:

```sh
sudo apt-get update
sudo apt-get install -y python3 python3-boto3 curl ca-certificates acl iptables
sudo useradd --create-home --user-group --shell /usr/sbin/nologin salad
sudo useradd --system --no-create-home --user-group --home-dir /nonexistent --shell /usr/sbin/nologin salad-ui
sudo useradd --system --no-create-home --user-group --home-dir /nonexistent --shell /usr/sbin/nologin cloudflared-salad
sudo usermod -a -G salad-ui cloudflared-salad
sudo install -d -o root -g root -m 0755 /opt/salad /opt/salad/.runtime
sudo cp -a /tmp/salad-recovery/runtime/. /opt/salad/
sudo chown -R root:root /opt/salad
sudo chmod -R a+rX,go-w /opt/salad
sudo install -o root -g root -m 0755 /tmp/salad-recovery/linux/keychain-store /opt/salad/.runtime/keychain-store
sudo install -d -o salad -g salad -m 0700 /home/salad/.hg1 /run/salad-credentials
sudo /usr/sbin/visudo -cf /tmp/salad-recovery/linux/sudoers/salad-credential-renewal
sudo install -o root -g root -m 0440 /tmp/salad-recovery/linux/sudoers/salad-credential-renewal /etc/sudoers.d/salad-credential-renewal
```

The active helper uses the EC2 role and boto3. The measured host has Python 3.12.3 and distro boto3 1.34.46. There is no Node/npm/Swift application server dependency.

Install the captured cloudflared version from the vendor, checking its published hash before execution:

```sh
curl -fL https://github.com/cloudflare/cloudflared/releases/download/2026.8.3/cloudflared-linux-arm64 -o /tmp/cloudflared-linux-arm64
printf '%s  %s\n' 4bcfd35521a7cbc545ebfd5d57334a71ee180e2a64874981f374c81472118391 /tmp/cloudflared-linux-arm64 | sha256sum -c -
sudo install -o root -g root -m 0755 /tmp/cloudflared-linux-arm64 /usr/local/bin/cloudflared
rm /tmp/cloudflared-linux-arm64
```

The published [2026.8.3 release checksum](https://github.com/cloudflare/cloudflared/releases/tag/2026.8.3) matches the measured deployed binary. The service uses a private token file; this flag is supported by the pinned version. [Cloudflare run parameters](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/).

## Restore state, or initialize new recording

If a consistent data backup survives, restore the complete `/home/salad/.hg1` tree with its matching metadata, ledgers and cursors. Do not run fresh bindings or reset baselines. Use Secrets Manager as the credential source; `/run/salad-credentials` is an expendable cache.

If state was lost, follow [SETUP.md](SETUP.md) to save real credentials, bind surviving/new groups and create new baselines. Keep recorders stopped during their one-shot initialization.

## Initialize database access

Return here after SETUP. Complete the database and ACL steps below, then Cloudflare/token setup, before proceeding to service startup.

The read-only UI needs two database schemas even before traffic exists. For **fresh recording state only**, initialize them with the actual bundled classes, then use DELETE journal mode while no writer is running. This avoids the measured empty-WAL/read-only startup failure; it does not invent any readings:

```sh
sudo -u salad -H bash
cd /opt/salad
python3 -B - <<'PY'
from pathlib import Path
import sqlite3
from dashboard.store import Store
from dashboard.native_network import NetworkMinutes
data = Path.home() / ".hg1"
Store(data / "bandwidth.sqlite3").close()
NetworkMinutes(data / "packetstream/minutes.sqlite3").db.close()
for path in (data / "bandwidth.sqlite3", data / "packetstream/minutes.sqlite3"):
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA journal_mode=DELETE")
(data / "packetstream/provider-observations.jsonl").touch(exist_ok=True)
PY
exit
```

For restored state, the inactive compatibility `bandwidth.sqlite3` must also be checkpointed/converted to DELETE while its writers are stopped. Use this instead of fresh schema initialization; it refuses a missing restored database and preserves rows:

```sh
sudo -u salad -H python3 -B - <<'PY'
from pathlib import Path
import sqlite3
path = Path.home() / ".hg1/bandwidth.sqlite3"
assert path.is_file(), "Restored compatibility database is missing"
with sqlite3.connect(path) as db:
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db.execute("PRAGMA journal_mode=DELETE")
PY
```

The active PacketStream recorder opens its own database in WAL mode and creates its WAL/SHM files before the UI starts.

Apply permissions after restoring/initializing state. These commands target the dedicated Salad data tree on the replacement host, remove stale numeric ACL identities from backups, and grant the new named UI account read access:

```sh
sudo chown -R salad:salad /home/salad/.hg1
sudo setfacl -R -b /home/salad/.hg1
sudo find /home/salad/.hg1 -type d -exec setfacl -k {} +
sudo chmod -R go-rwx /home/salad/.hg1
sudo setfacl -m u:salad-ui:x /home/salad
sudo setfacl -R -m u:salad-ui:rX /home/salad/.hg1
sudo find /home/salad/.hg1 -type d -exec setfacl -m d:u::rwx,d:u:salad-ui:r-x,d:g::---,d:m::r-x,d:o::--- {} +
sudo -u salad touch /home/salad/.hg1/packetstream/provider-observations.jsonl
sudo setfacl -m u:salad-ui:rw /home/salad/.hg1/packetstream/provider-observations.jsonl
```

The last file is the UI's explicit provider-observation write exception. Keep code root-owned and the credential cache private. Systemd creates `/run/salad-ui-code` and `/run/salad-ui`; the supplied unit bind-mounts only the required UI code and denies IP networking.

## Restore Cloudflare

If the zone/account survives, reuse its app, policy and tunnel. If recreating them, use the configuration table in [CONNECTIONS.md](CONNECTIONS.md#cloudflare):

1. Recreate the zone and set the registrar to the nameservers assigned to that new zone.
2. Restore the Cloudflare identity provider restricted to account members; create the owner-email Allow policy and the self-hosted full-hostname application. Restore its security-key MFA, session and cookie settings.
3. Create the remotely managed tunnel and record its new ID. Publish `salad.cosmosgeek.org` with blank path, service **`unix:/run/salad-ui/ui.sock`**, and Protect with Access enabled.
4. Set the tunnel's team/AUD to the application. Set the matching `ACCESS_ISSUER` and `ACCESS_AUDIENCE` in `dashboard/server.py`. If changing the hostname, update the PacketStream POST origin and `dashboard/ps-paid-feed.js` target origin as well.
5. Create the proxied CNAME `salad` to `<new-tunnel-id>.cfargotunnel.com`, TTL Auto. Do not create an A record to the EC2 IP.

Restore the tunnel token through a hidden prompt on AWS; never paste it into a unit, command argument or repository:

```sh
sudo install -d -o root -g cloudflared-salad -m 0750 /etc/cloudflared-salad
sudo install -o root -g cloudflared-salad -m 0640 /dev/null /etc/cloudflared-salad/tunnel.token
sudo python3 -c 'import getpass; from pathlib import Path; value=getpass.getpass("Cloudflare tunnel token (hidden): "); assert value; Path("/etc/cloudflared-salad/tunnel.token").write_text(value.strip())'
```

Use the current token from the surviving tunnel or the new tunnel's connector setup. Restore/enroll the owner's physical security key through the normal owner login flow. Its private material is not recoverable from this repository.

## Start the services

Install the captured units and reload systemd:

```sh
sudo cp -a /tmp/salad-recovery/linux/systemd/. /etc/systemd/system/
sudo chown -R root:root /etc/systemd/system/salad-*.service /etc/systemd/system/salad-*.service.d /etc/systemd/system/cloudflared-salad.service
sudo systemctl daemon-reload
sudo systemd-analyze verify /etc/systemd/system/salad-*.service /etc/systemd/system/cloudflared-salad.service
```

Enable/start the configured recorders first, so their files and current observations exist:

```sh
sudo systemctl enable --now salad-hg-provider.service salad-hg-fleet.service salad-fleet.service salad-packetstream.service
sudo systemctl enable --now salad-proxyrack.service salad-repocket.service salad-repocket-provider.service salad-earnfm.service salad-traffmonetizer.service
sudo systemctl enable --now salad-pawns.service salad-earnapp.service salad-grass.service
sudo systemctl enable --now salad-dashboard.service
sudo systemctl enable --now cloudflared-salad.service
```

Run only the subset whose actual bindings/account inputs exist. Keep any surviving old recorders/tunnel connector stopped during replacement cutover; otherwise a tunnel can route to inconsistent hosts and duplicate observers can compete for state.

Copy the service drop-in directories as well as the main unit files. EarnApp's drop-in selects `/opt/salad/EarnApp/earnapp-recorder.py` and supplies its data/helper paths; copying only `*.service` would restore the wrong executable.

## Restrict routine administration

Before removing the initial Ubuntu administrator grant, verify both a fresh SSH/SCP connection and an AWS Run Command returning `uid=0`. Keep Run Command available while applying these settings; it is independent of the SSH listener. These commands run in that root maintenance context:

```sh
install -d -m 0755 /etc/ssh/sshd_config.d /etc/systemd/system/ssh.socket.d
install -o root -g root -m 0644 /tmp/salad-recovery/linux/sshd/10-salad.conf /etc/ssh/sshd_config.d/10-salad.conf
install -o root -g root -m 0644 /tmp/salad-recovery/linux/systemd/ssh.socket.d/listen.conf /etc/systemd/system/ssh.socket.d/listen.conf
/usr/sbin/sshd -t
systemctl daemon-reload
systemctl enable --now salad-imds-guard.service
systemctl stop ssh.service
systemctl restart ssh.socket
systemctl start ssh.service
```

Recheck SSH/SCP through Session Manager and `ss -ltn`: SSH must listen only on `127.0.0.1:22`. There must still be no AWS inbound rules. Inspect `/etc/sudoers.d/90-cloud-init-users` before replacing it: on the captured dedicated host its only active rule granted `ubuntu` unrestricted passwordless sudo. Preserve any unrelated rules if recovering a different host.

```sh
/usr/sbin/visudo -cf /tmp/salad-recovery/linux/sudoers/90-cloud-init-users
install -o root -g root -m 0440 /tmp/salad-recovery/linux/sudoers/90-cloud-init-users /etc/sudoers.d/90-cloud-init-users
for group in sudo lxd; do
    if id -nG ubuntu | tr ' ' '\n' | grep -qx "$group"; then
        gpasswd -d ubuntu "$group"
    fi
done
/usr/sbin/visudo -c
```

A **fresh** SSH login must report no `sudo`/`lxd` group and reject `sudo -n true`. The fixed renewal rule installed above permits only the named prompt/session writers, a masked RP check, and RP/PS reader start/stop; it does not allow a shell, arbitrary interpreter or direct secret read. Verify those command permissions without replacing real credentials. Verify AWS Run Command still runs as root. The connector unit carries its own capability, namespace, kernel, realtime and metadata restrictions. This does not add Trader's separate per-device login registry to Salad.

## Verify the restored site

- Verify manifests/source hashes, unit identities and socket permissions.
- The UI runs as salad-ui; recorders run as salad; only cloudflared-salad can supply trusted socket requests.
- A bare socket request without an Access assertion returns 403. Use the signed-in public site for data checks; never fabricate an assertion.
- Every configured tab must load its chart/table and update across successive real observations. Check provider timestamps separately.
- Confirm CPU mode is Unlimited and source data/cursors keep advancing. An enabled process or HTTP 200 alone is insufficient.
- Confirm code is root-owned, the UI cannot reach IP networking/credentials, and only the billing append file is writable to it.
- After a confirmed recovery, remove the temporary staging directory. Keep the source and encrypted state backups.

## Preserve a recovery backup

The source repository contains code/configuration, not the full machine. Preserve these separately: the complete data tree with consistent SQLite/WAL state and cursors; the Secrets Manager values/recovery access; Cloudflare token/account/MFA access; operator SSH access; and domain ownership.

An AWS EBS-backed AMI can preserve the configured host and encrypted data. Use EC2 → instance → Actions → Image and templates → Create image, with the normal consistency/reboot behavior during an authorized maintenance window, then verify the AMI is available. Retain its EBS snapshots and required KMS access. [AWS AMI backup procedure](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/creating-an-ami-ebs.html).

For logical data copies, stop the associated writers before copying the whole matching state, or use SQLite backup plus a coordinated metadata/cursor snapshot. A live database file copied without its WAL is not a verified backup. Do not place credentials or live databases in Git.

After each approved release, retain an off-Mac copy of the source/configuration and an encrypted state backup whose location/key the owner can recover. If every copy of historical data or private credentials is deleted, a new recording/login can be established; those lost values cannot be reconstructed from application source.
