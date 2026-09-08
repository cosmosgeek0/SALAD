# PacketStream provider readings

The AWS service `salad-packetstream-provider.service` reads the account’s own authenticated dashboard every 60 seconds. It is separate from the ten bandwidth clients and their network recorder. Closing the Mac does not stop this reader while its saved session remains valid.

## What is recorded

- **Account balance:** the amount explicitly labelled Balance / Available Funds, in USD. It can include earlier activity and is not earnings attributable to this deployment or minute.
- **Traffic sold:** the provider’s rolling 14-day account report. Each UTC day’s upload/download bytes is retained separately. A change in the whole rolling total is not an interval earning: old days can leave that window.
- **Times:** original provider day, successful observation time, latest check and last observed change. Provider posting/settlement time is unknown. Our 60-second checking schedule is not a promise that PacketStream updates every minute.

The parser reads `GET https://app.packetstream.io/dashboard`, verifies referral/account identifier `8ExP`, reads the `metric-card-balance` card, and parses the page’s double-encoded JSON `const rd` into dated `exitnode[].bandwidth.up/down` records. It never estimates USD from network bytes or computes earnings from balance changes.

## Account access

The BTC Chrome profile held the correct signed-in account during setup. PacketStream login uses username/password and a browser security challenge, so the AWS reader reuses that already-authorized session. It does not automate a CAPTCHA or attempt a password-only login.

The `auth` session cookie and its real expiry are stored under helper service `packetstream-provider-session` in the existing private AWS Secrets Manager secret. The value is a JSON string with `mode: browser_cookie`, `auth_cookie` and `expires_at` (Unix seconds). No cookie value belongs in this repository, a shell argument or visible output. The Website helper must allow that service; its current Linux source does.

For an existing signed-in account, [the RP package’s short-lived session transfer](../repocket/scripts/session-to-aws.py) provides a local, nonce-protected password form and sends the authorized session to the existing AWS secret store over SSH stdin. It is an operator setup utility, not a continuously running browser dependency. Supply actual account-session data through private entry only. The cookie is sent only to the exact PacketStream HTTPS dashboard URL; redirects are refused.

A renewed cookie from the provider is saved before parsing the report. Throttles/transient errors back off. Expired or rejected sessions stop provider requests until the stored access changes; the rejection fingerprint survives a service restart. Sign in normally again and replace the session when required. Missing/changed report markup does not invent a zero or invalidate an otherwise usable renewed cookie.

## Files and recovery

| Item | Location on AWS |
|---|---|
| Reader | `/opt/salad/packetstream-monitor/provider.py` |
| Unit | `/etc/systemd/system/salad-packetstream-provider.service` |
| Successful observations and checks | `/home/salad/.hg1/packetstream/provider.sqlite3` |
| Last reading and current safe error | `/home/salad/.hg1/packetstream/provider.json` |
| Check/retry status | `/home/salad/.hg1/packetstream/provider-status.json` |
| Single-writer lock | `/home/salad/.hg1/packetstream/provider.lock` |

Rebuild the AWS host and private helper from [Website recovery](../Website/RECOVERY.md). Install `source/packetstream-monitor/provider.py` at the reader path and `systemd/salad-packetstream-provider.service` at the unit path, owned by root. Run `sudo systemctl daemon-reload` and `sudo systemctl enable --now salad-packetstream-provider.service`. The unit runs as `salad`; Python standard library plus the Website credential helper dependencies are required. Preserve SQLite history and use its online backup API or stop this provider writer while making a consistent copy.

Verify with `sudo -u salad cat /home/salad/.hg1/packetstream/provider-status.json` and `sudo journalctl -u salad-packetstream-provider.service -n 10 --no-pager`. A fresh `state: ok` and repeated saved provider observations prove successful reads. The page must retain the account/14-day labels and show stale/unavailable values after access fails.

The older browser bridge and `provider-observations.jsonl` are preserved historical inputs. They contain rolling traffic totals, not verified interval earnings. Do not start that old bridge beside the new reader or use total differences as exact paid traffic.

## Verified implementation

The existing authorized session was stored privately and the AWS reader returned actual account balance and dated traffic successfully on 2026-09-07. Its initial observed balance was $1.20; the traffic counter advances with later provider observations. The live PS tab was verified showing the account balance and provider 14-day traffic under those explicit labels. These are dated observations, not a guaranteed earning rate. Eighteen offline tests cover parser validity, zero versus missing values, account checks, renewal, throttles, persistent rejection and preserved history. See `tests/test_provider.py`.
