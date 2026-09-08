# Recorder setup on AWS

This configures the website's data sources after the Linux files in [RECOVERY.md](RECOVERY.md) are installed. It does not recreate deleted historical data. For cloud clients that are missing, use the corresponding [protocol README](CONNECTIONS.md#salad-groups-and-protocol-source) before binding recorders.

**If a consistent runtime-data backup was restored, preserve it and skip fresh binding/baseline initialization.** Start its matching recorders and inspect identity/freshness checks. Never run a fresh initializer over an existing experiment.

## Credentials

The Linux helper is installed at `/opt/salad/.runtime/keychain-store`; its source is [linux/keychain-store](linux/keychain-store). It reads the Secrets Manager secret named in [CONNECTIONS.md](CONNECTIONS.md), using the EC2 role and boto3. Private `/run/salad-credentials/values.json` caches reads; writes also update Secrets Manager. The macOS Swift helper and LaunchAgents are not used on AWS.

Non-secret binding/initialization commands later in this guide run as `salad` through the AWS Run Command root maintenance path in [CONNECTIONS.md](CONNECTIONS.md). These are not instructions to open a privileged shell through routine SSH. The initialization block below includes the required environment:

Use hidden prompts; no value belongs in a command argument, Git file or task transcript.

| Secret JSON key / helper service | Required string value and origin |
|---|---|
| `salad-bandwidth-api` | Existing Salad account API key with access to the named organizations |
| `proxyrack-peer-api` | ProxyRack account API key from the owner's provider portal |
| `earnfm-read-session` | JSON with actual `access_token` and `expires_at` (Unix seconds) from the authenticated EarnFM session |
| `salad-traffmonetizer-session` | Current TM bearer token, without the Bearer prefix; refreshed tokens are saved by the recorder |
| `earnapp-read-session` | JSON with the authenticated EarnApp request's `cookie` and `xsrf_token` fields |
| `repocket-provider-session` | JSON account-access record saved by [Repocket's private connection command](../repocket/docs/PROVIDER.md#connect-the-account-once) |

For private credential entry, use a real interactive Mac terminal and the fixed SSH prompt command below. Replace the final service name with the required table entry from the first five rows. A provider-session value must be the stated JSON string. Input is hidden and travels inside SSH, not through Run Command arguments or logs:

```sh
ssh -F Website/linux/ssh_config -tt salad-mumbai \
  'sudo -n -u salad /usr/bin/python3 -B /opt/salad/scripts/save-secret.py salad-bandwidth-api'
```

The exact-command sudo rule permits those named prompts only; it does not grant a shell, `python -c`, or direct secret reads. Piped/non-terminal input is refused. For Repocket email/password renewal, use `bash repocket/scripts/connect-provider.sh`. For existing RP/PS sessions, use the private forms from `python3 repocket/scripts/session-to-aws.py`; the local form validates the session and sends it over SSH stdin. These workflows stop/restart only the affected provider reader to avoid overwriting a concurrently refreshed session.

The secret is one JSON object whose values are strings; a provider-session JSON value is stored as a string, not a nested object. On an entirely new AWS setup, first create this secret with plaintext JSON `{}` in the owner console, set its actual ARN in the helper and role policy, and create the private runtime cache directory as described in RECOVERY. Then the hidden prompts above can populate it. Supply only services in use. Obtain tokens/cookies from the owner's existing authenticated provider session. EarnFM expiry must be real, not an invented permanent timestamp. EarnApp's saved device identity must match its cloud deployment; follow [EarnApp setup](../EarnApp/README.md).

If credentials are changed directly in the Secrets Manager console, invalidate the host's old cache before the next check. The helper's lock makes this cache-only removal safe; the authoritative secret remains in AWS:

```sh
sudo -u salad flock /run/salad-credentials/lock rm -f /run/salad-credentials/values.json
```

Run that cache-only operation through AWS Run Command as root, then verify the affected recorder refreshes. Do not print the cache. The helper's own hidden-prompt writes already update both Secrets Manager and cache.

Honeygain's observer reads the account configuration from the existing Salad deployment; recreation of those groups requires the owner's Honeygain account credentials. PacketStream's cloud client CID is separate from the optional provider-credit browser feed. Grass's initial login, saved-login restoration and native recovery setup are described in [Grass](../grass/README.md); replacement instances use that configured startup automatically.

## Fresh data, existing cloud clients

Run this section only when recording state was lost or this is an intentionally new recording. First save the Salad API key. Keep the corresponding services stopped while their one-shot initialization runs.

```sh
sudo -u salad -H /bin/bash <<'SALAD_SETUP'
set -eu
cd /opt/salad
export PYTHONPATH=/opt/salad
export HG_FLEET_DIR=/home/salad/.hg1/hg-fleet
python3 scripts/rebuild-cloud.py honeygain bind
python3 scripts/rebuild-cloud.py packetstream bind
python3 scripts/hg-provider-observer.py --once
python3 scripts/hg-fleet-observer.py --once
python3 scripts/initialize-recording.py
python3 scripts/bind-website.py pr rp rfm
SALAD_SETUP
```

The HG provider baseline comes from an actual account reading. The initializer creates a new experiment and refuses an existing current.json. Bindings use returned group IDs and images; do not paste historical UUIDs or baseline amounts into a replacement experiment. The bind helpers verify expected cloud configuration and stop on a mismatch instead of changing the cloud deployment.

After restoring the TM provider session, create its actual baseline:

```sh
sudo -u salad -H /bin/bash -c 'cd /opt/salad && PYTHONPATH=/opt/salad python3 scripts/bind-website.py tm'
```

The TM binding refuses missing provider access or an existing deployment file. Its baseline-adjusted provider totals remain separate from raw network bytes.

Pawns, EarnApp and Grass have their own collector initialization and workload requirements; follow their protocol guides. Their services can only produce measurements if the deployed client emits the expected records. Missing input remains unknown.

## If cloud clients are also gone

Use the create/recovery steps in each [protocol guide](CONNECTIONS.md#salad-groups-and-protocol-source), including its pinned image, account inputs and recovery policy. This incurs the provider's normal workload costs. Then use the fresh-binding sequence above with the newly returned IDs. Do not assume that recreating a group restores its former IPs or recordings.

The website bundle includes the Honeygain and PacketStream rebuild helpers, but does not replace the other protocol guides. The offline command `python3 scripts/rebuild-cloud.py honeygain plan` shows its proposed groups without authenticating or creating them.

## Additional provider connections

- **Repocket:** the separate `salad-repocket-provider.service` collects account lifetime own-bandwidth totals after [connecting the deployed account](../repocket/docs/PROVIDER.md). On a fresh host, after installing the credential helper, prompt and renewal sudo rule, use `ssh -F Website/linux/ssh_config -tt salad-mumbai 'sudo -n -u salad /usr/bin/python3 -B /opt/salad/scripts/save-provider-access.py --mode email_password'`; this direct prompt does not require the provider service to exist. The Mac wrapper is for an already installed provider service. The client Docker key does not authorize provider earnings; missing account access leaves earnings unavailable. Preserve `provider.sqlite3` and the original successful reading timestamps.
- **PacketStream:** the provider-credit bridge source is `dashboard/ps-paid-feed.js`; follow the exact connection steps below. Network recording continues without it; paid traffic needs actual baseline and follow-up readings.
- **Pawns:** its native worker supplies dated account-wide sold-traffic and sharing-balance readings alongside current-IP confirmation; follow [Pawns data](../pawns/website.md). These account totals are separate from per-node measured traffic.
- **Grass:** the native worker supplies fresh device/IP acceptance and account-wide Network Points to its recorder. Follow [Grass monitoring](../grass/monitoring.md); points are not cash earnings, and stale or rejected provider access remains visible.

When every selected recorder has its real inputs, return to [RECOVERY: Initialize database access](RECOVERY.md#initialize-database-access). Complete those database/ACL steps through the root maintenance path and the following Cloudflare/token setup before starting services. Disabled Mac recorders stay disabled.

## Connect PacketStream provider readings

This optional connection is made after the public website has been started and owner login works.

1. In the owner's signed-in public Salad website tab, open the browser console and run:

```javascript
sessionStorage.setItem('ps-billing-channel', crypto.randomUUID());
location.reload();
```

2. After the page reloads, open its connected provider child window from that same console:

```javascript
window.open('https://app.packetstream.io/dashboard#ps-sync=' +
  encodeURIComponent(sessionStorage.getItem('ps-billing-channel')), 'psBillingSync');
```

3. Sign in to the owner's PacketStream account in that child window. Run the complete, inspected [provider bridge source](source/dashboard/ps-paid-feed.js) in the child window's console. The account guard currently checks referral identifier `psr=8ExP`; a different account requires its own verified identifier.
4. Keep both windows open. The provider window sends only credited bytes and observation time to the public Salad origin; the parent submits them using its authenticated application session and ephemeral bridge token. No provider cookies are exported.
5. Verify the provider-connected message and actual fresh baseline/follow-up observations. Reconnect after closing the child/provider session or changing the channel. Missing or stale data stays Not reported.
