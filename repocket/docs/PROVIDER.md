# Repocket earnings collection

`repocket-monitor/provider.py` collects Repocket-reported **account lifetime own-bandwidth** traffic and earnings. It runs on AWS independently of the Salad workload and network recorder. It does not infer earnings from network bytes, allocate account earnings to individual IPs, or replace idle workers.

Verified on 2026-09-07: the existing authenticated BTC Chrome session was stored privately in AWS Secrets Manager. The AWS reader renewed that access, matched the account to the deployment and read actual bandwidth earnings successfully. No account password was required during this connection. The first verified reader observation was $0.755531002022 from 8,112,452,362 provider bytes; the page displays a rounded amount while the exact decimal cents remain saved.

Verify this provider addition from the RP folder with `shasum -a 256 -c PROVIDER-SHA256SUMS`. The provider manifest verifies this addition independently; the main package manifest also includes it.

## Connect the account once

Use the Repocket account configured in the running Salad group `ssh2/default/rp-test-us`. The collector checks that account against the group's `RP_EMAIL` and the saved group UUID before accepting a session.

Open a real interactive terminal on the Mac and run:

```bash
cd "$HOME/Desktop/salad/repocket"
bash scripts/connect-provider.sh
```

The command uses the sibling Website package's SSH configuration to reach AWS, stops only `salad-repocket-provider.service`, runs the hidden-input setup as Linux user `salad`, and restarts the service when setup exits. AWS CLI, Session Manager and SSH access must already work; see [Website connections](../../Website/CONNECTIONS.md).

The hardened host grants only these fixed renewal commands through `Website/linux/sudoers/salad-credential-renewal`. It does not restore blanket sudo or an interactive `salad` shell. The optional RP/PS local session bridge runs its orchestration as `ubuntu`, using exact sudo grants for the writer and affected reader start/stop; credentials travel only over SSH stdin. Other privileged inspection/rebuild commands in this guide use the AWS Run Command root maintenance path, not general sudo from routine SSH.

The connection command goes directly to hidden Repocket email and password prompts; there is no sign-in-method menu. Use the Repocket account's own password.

Token-based recovery remains available through `save-provider-access.py --mode refresh_token` in an interactive AWS terminal, with the provider service stopped during entry and restarted afterward. Supply only an already-authorized Repocket Firebase refresh token; never a Google account password. This helper does not perform Google sign-in or obtain a token for you.

The Repocket Docker API key authenticates the bandwidth client, not this earnings reader. It cannot substitute for these credentials. Do not put credentials in chat, shell arguments, environment variables, project files or commands that echo them. The setup script refuses piped input and requires hidden terminal entry.

`scripts/save-provider-access.py` writes through `/opt/salad/.runtime/keychain-store`, using service `repocket-provider-session` and account `salad`. The Linux helper stores this record inside the private AWS Secrets Manager recorder-credentials secret and its protected runtime cache. After a verified login, the collector replaces the supplied email/password record with renewable session access; the password is removed from the current record. Earlier Secrets Manager versions follow the secret's retention policy.

To inspect only stored mode and field presence, from an interactive AWS terminal:

```bash
sudo -u salad /usr/bin/python3 -B /opt/salad/scripts/save-provider-access.py --check
```

This check does not authenticate or prove that earnings can be read. Never run the credential helper's `--read` directly in a visible terminal; it prints the secret.

## What is read and when

Authentication uses Firebase `accounts:signInWithPassword`, `accounts:lookup` and the Secure Token refresh endpoint. The public Firebase project API key in the source identifies Repocket's application; it is not account authorization. A verified refresh token renews the ID token before expiry. [Firebase REST authentication](https://firebase.google.com/docs/reference/rest/auth).

The earnings request is `GET https://api.repocket.com/api/reports/total` with these headers:

```text
auth-token: <Firebase ID token>
x-app-version: web
device-os: web
```

There is no `Bearer` prefix. The collector uses `bandwidth.own.bytes` and `bandwidth.own.cents`, preserving both raw amounts. The live HTTP body is the report object itself (the web app’s Axios `.data` unwraps its transport response). The collector uses curl for the report and Salad account check; plain Python urllib requests to those APIs returned HTTP 403 while curl returned HTTP 200. It divides cents by **100** for USD and bytes by **1,048,576** for MiB. These are account lifetime totals, potentially including earlier devices and locations. `centsCredited` is a separate account balance that can include other activities; it is not substituted for bandwidth earnings. The response's account ID and authenticated Firebase user ID are recorded separately.

Normal polling is **every 60 seconds**. Repocket's earnings posting cadence has not been established; checking every minute does not imply settlement every minute. `observed_ms` is our successful read time, `last_changed_ms` tracks observed changes, and `provider_updated_ms` preserves the report’s `updatedAt`. That report timestamp is not a documented settlement interval. `periodStart` is also retained, and pending bandwidth/cents remain separate from credited own-bandwidth amounts. An unchanged total is not evidence that a healthy worker failed.

Temporary request failures back off from 60 seconds up to 15 minutes; a provider `Retry-After` can extend the delay to 30 minutes. On report HTTP 401/403, the client renews once and retries once. Known revoked, invalid or disabled-account responses set `requires_login`; the running collector suppresses further authentication attempts with the same rejected credential record until access changes. Re-run the connection command with renewed access. Ordinary missing credentials or a credential-store outage remain separate errors.

## Saved data and verification

Production data is `/home/salad/.hg1/repocket`:

| File | Meaning |
|---|---|
| `provider.sqlite3` | Append-only successful observations in `readings`, including repeated unchanged totals |
| `provider.json` | Last successful reading, atomically published for the network recorder |
| `provider-status.json` | Latest check, error, retry delay and any `requires_login` state |
| `provider.lock` | Prevents two provider collectors from running together |
| `traffic.sqlite3` | Network recorder history; its separate `provider_readings` journal imports provider snapshots |

A failed check preserves the previous successful reading and its original observation time. The dashboard must show unavailable/stale earnings honestly; a new error check does not refresh old earnings. Preserve databases with a consistent SQLite backup, including their required state, rather than copying an active database file alone.

Connect to AWS using [Website connections](../../Website/CONNECTIONS.md), then inspect:

```bash
sudo systemctl status salad-repocket-provider.service --no-pager
sudo journalctl -u salad-repocket-provider.service -n 20 --no-pager
sudo -u salad cat /home/salad/.hg1/repocket/provider-status.json
```

Completion requires fresh `state: "ok"`, matching timestamped provider readings, and the account-scoped value appearing on the [RP page](https://salad.cosmosgeek.org/#rp). A running service alone is insufficient. If access is missing, provide it through the connection command above; do not overwrite the old reading with a guessed zero.

## Rebuild the AWS service

First restore the [Website host, credentials and IAM configuration](../../Website/RECOVERY.md). This RP folder alone cannot rebuild the AWS host. The sibling `Website/linux/keychain-store` must allow `repocket-provider-session`; install that compatible helper at `/opt/salad/.runtime/keychain-store`. Its IAM role needs access to read and update the existing private credential secret for session renewal. Preserve the other credential services and their values.

On the recovered host, set `rp_package` to the restored RP package's absolute path, then install the tracked files:

```bash
rp_package=/absolute/path/to/restored/repocket
sudo install -d /opt/salad/repocket-monitor /opt/salad/scripts
sudo install -m 0755 "$rp_package/repocket-monitor/provider.py" /opt/salad/repocket-monitor/provider.py
sudo install -m 0755 "$rp_package/scripts/save-provider-access.py" /opt/salad/scripts/save-provider-access.py
sudo install -m 0644 "$rp_package/systemd/salad-repocket-provider.service" /etc/systemd/system/salad-repocket-provider.service
sudo systemctl daemon-reload
sudo systemctl enable --now salad-repocket-provider.service
```

Restore or attach the correct `deployment.json` and ensure the existing `salad-bandwidth-api` credential can read that group. Restore the private provider credential through the approved secret recovery process, or run the hidden-input connection command. The unit runs Python as `salad`, uses `/opt/salad`, creates a private runtime credential directory, and restarts on process failure. Python's standard library is sufficient for the collector; the Linux credential helper additionally needs Website's AWS dependencies.

For an existing host, compare source before replacing a newer installation. Keep the retired Mac recorders disabled. This service does not change Salad replicas, country policy or workload recovery behavior; those remain in the worker and its separate deployment guide.
