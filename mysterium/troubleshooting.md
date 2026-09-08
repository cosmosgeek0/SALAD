# Troubleshoot Mysterium

[Guide index](README.md)

## Account registration limit

**Measured on 2026-09-07:** the original account's signed onboarding request returned `isEligibleForFreeRegistration:false`. Its page said the account “has reached the limit of free node registrations” and directed it to standard onboarding. The page did not state a numeric allowance or reset time. Repeating account claiming or allocating a fresh machine had not completed registration.

This account needs a provider-supported registration route, or an existing registered identity's private data that the owner can actually restore. The current package contains no identity backup and implements no automatic private-data restore. To make repeated reallocation independent of fresh sponsorship, a registered identity must be preserved outside the disposable instance and restored before startup; that capability remains unfinished. Registration does not guarantee monitoring success on a new IP.

To reproduce the account diagnostic on a running node, use the native `GET /mmn/onboarding?redirect_uri=http%3A%2F%2F127.0.0.1%3A4449` endpoint in its Salad terminal. Generate the link only once and open it privately in the original signed-in MystNodes account. Inspect the browser's Network response for `/api/v2/clickboarding/identify`. With an explicit false eligibility result, **Confirm** displayed the limit explanation in this trial. Stop there; **Proceed** and the callback were not used. The local callback address is not a remotely exposed NodeUI.

The onboarding message contains the identity, redirect URL and a public code challenge; it contains no account API key. Keep the complete signed URL and any later authorization grant out of files, logs and shared messages. Do not use `/mmn/claim-link` for this diagnostic: that older link embeds the account API key. The [pinned onboarding implementation](https://github.com/mysteriumnetwork/node/blob/c45527af1ea80300ae3d9c92bd37255335b6140d/tequilapi/endpoints/mmn.go#L227) succeeded in this trial despite the existing account key; no guard or credential was changed. If it returns an authorization error on another version, treat that as an error, not permission to bypass it.

No account password, withdrawal address, paid registration, identity export or private-data persistence was changed in this diagnostic.

## DNS: apply a correction only after measuring this host

The measured Texas container initially had these resolver entries:

```text
nameserver 1.1.1.1
nameserver 1.0.0.1
```

In the **Salad terminal**, inspect and test the actual configuration:

```sh
cat /etc/resolv.conf
timeout 4 nslookup quality.mysterium.network
timeout 4 nslookup quality.mysterium.network 1.1.1.1
timeout 4 nslookup quality.mysterium.network 1.0.0.1
```

Measured result: the default and `1.1.1.1` tests reached the four-second diagnostic deadline; `1.0.0.1` answered. These are bounded observations, not a universal claim that a resolver is unreachable.

For that same observed failure, the applied correction was:

```sh
printf 'nameserver 1.0.0.1\n' > /etc/resolv.conf
cat /etc/resolv.conf
timeout 8 nslookup quality.mysterium.network
```

The default lookup then answered. The provider DNS proxy reads the resolver file at bootstrap, so the final command sets it before starting Mysterium; it does not use a hardcoded provider DoH server. [Pinned resolver implementation](https://github.com/mysteriumnetwork/node/blob/c45527af1ea80300ae3d9c92bd37255335b6140d/dns/handler_system.go). Click **Restart** on the same instance, reconnect, and repeat `cat /etc/resolv.conf`, the lookup, health, identity, and monitoring checks. The change survived the measured same-instance restart. **The final launch command now includes this resolver**, so the setting is reapplied on a new allocation. Test that resolver on the actual new host. DNS alone left monitoring failed; public success was observed later after the MTU correction. Different before/after deadlines also do not establish a speed improvement.

## Remaining diagnostics

To read the current native log without printing lines containing the account-linking key, run inside the container:

```sh
tail -n 80 /root/.mysterium/logs/mysterium-node* | awk 'index($0,ENVIRON["MYSTNODES_API_KEY"])==0'
```

Do not dump environment variables, full configuration, or process command lines into shared logs: these can contain the key. The exact-key filter above is not a general sanitizer for arbitrary sensitive data.

| Observed failure / misleading signal | Action taken and actual result |
| --- | --- |
| Portal Docker wizard did not create a group; API lookup found none. | Created the stopped group through the authenticated Salad API, then started it in the authorized trial. The guide uses API creation directly. |
| Wizard initially selected GPU resources. | Corrected to CPU-only settings; the [saved deployment configuration](setup.md#create-the-deployment) has no GPU request. |
| Generic `Free registration is not eligible` warning; a replacement remained unregistered while Salad showed Running/Ready. | The old flag checks generic eligibility once. The [startup candidate](start.sh) adds those steps, but live fresh-identity registration remains unresolved; see the [repair record](verification.md#reallocation-repair--not-complete). |
| Initial allocation was Mexico. | Saved `country_codes:["us"]` and explicitly reallocated the Mexico instance. Subsequent observed assignments were U.S. |
| First U.S. process responded while Salad showed Creating. | Read System Events; Salad recorded `Instance Reallocated by Platform`. Followed the replacement; no cause beyond that event was established. |
| North Carolina host was Running/Ready and published but monitoring-failed. | Reallocated within the existing U.S. restriction. The next measured host was residential AT&T in Texas. |
| `Failed to sign metrics event ... authentication needed: password or unlock`. | Read source and tried native identity unlock earlier. Unlock was not proved to cure it; the error alone did not establish that the provider identity was locked or explain failed monitoring. |
| Stopping monitoring first used a mistyped service UUID, then the correct UUID returned `monitoring service cannot be stopped`. | Read the real service ID; used an instance Restart instead. Do not try to stop/restart monitoring independently as the recovery recipe. |
| SSH returned `Permission denied (publickey)`. | Used the owner's signed-in Salad web terminal; no new SSH key was needed for the tested path. |
| Web terminal disconnected. | Refreshed the instance page and clicked its Terminal input before issuing more commands. Checked the current instance ID when a host had been replaced. |
| Authenticated MystNodes manual-check endpoint returned HTTP `500` with `{"message":"Internal Server Error","errorCode":"internalServerError"}`. | Read the response through browser network events. The fresh identity later recorded monitoring sessions despite that submission error. No permanent website API fix was established. |
| Direct HTTPS to `1.1.1.1/cdn-cgi/trace` hit the eight-second diagnostic deadline (exit 143); `1.0.0.1/cdn-cgi/trace` completed (exit 0, `loc=US`). | Recorded the host-specific failure; did not rewrite the monitor’s requested destination or fake a successful response. |
| Public discovery returned `null`. | Read the native access policies and queried using the correct policy/source and service type; proposals were returned. |
| Salad log API gave old output after an instance restart. | Checked current native health and the in-container log instead of treating absent fresh cloud logs as a healthy result. |
| Log API rejected a large page request or unsupported timestamp format with HTTP `400`. | Used the measured accepted page size of 100 and UTC timestamps with milliseconds ending in `Z`; advanced the time window instead of treating the first page as all logs. |
| Python's default HTTP client header returned `403` on an authenticated Salad request. | The same live group GET returned `200` with `User-Agent: mysterium-setup`. The creation recipe now supplies that explicit client name; no duplicate group was created to test it. |

## Provider MTU correction

The pinned official source passes `device.DefaultMTU` directly to `CreateNetTUNWithStack`; it ignores `cfg.MTU` in full userspace provider mode. The **measured** Texas container interface MTU was `1280`; the **published-in-source** provider default was `1420`. The corrected `ConfigureDevice` uses the requested MTU, retaining the original fallback when it is unset:

```go
mtu := cfg.MTU
if mtu == 0 {
    mtu = device.DefaultMTU
}
tunnel, _, _, err := CreateNetTUNWithStack([]netip.Addr{netip.MustParseAddr(cfg.Subnet.IP.String())}, cfg.DNSPort, mtu)
```

This is the entire functional source change: **measured 105 → 109 lines** in `services/wireguard/endpoint/netstack-provider/client.go`. The runtime choice `1100` was tested; it is not a claimed optimum or universal requirement. [Pinned original implementation](https://github.com/mysteriumnetwork/node/blob/c45527af1ea80300ae3d9c92bd37255335b6140d/services/wireguard/endpoint/netstack-provider/client.go).

The earlier Mexico experiment with MTU `1200` still failed and was discarded. It did not establish that every MTU or U.S. host would fail. On Texas, the later MTU `1100` run recorded a monitoring session lasting **203 seconds**, with native counters **3,562,368 bytes received** and **433,484 bytes sent**, compared with the prior measured **18-second**, **31,564 / 6,492-byte** stock run. Temporary relay logging also observed an HTTPS response of **194,933 bytes**. These are measured session/relay counters, not customer earnings.

The public monitoring result changed from `failed` at **08:07:29 UTC** to `success` at **08:22:04 UTC**. A clean build containing only the source change above, with all added packet logging removed, reported native monitoring `success` after the **08:26 UTC** restart. Source review found no concrete defect in the scoped correction.

The raw signed monitoring counts still contained historical `internet_fail` entries. Static inspection of the official quality-oracle image published **2026-04-27** found historical aggregation and separate cached failure-set/public-status paths; the public endpoint defaults to success when an identity is absent from its failed set. Its exact deployed version and individual probe verdict were not verified. Do not treat historical counts as the latest verdict, promise a fixed recovery delay, or claim that this sequence alone proves MTU caused the status change.

Temporary build failures were corrected before deployment: unqualified Go linker metadata names produced `source.dev-build`, fixed by using the full module paths in [image build instructions](build.md); an overescaped `sed` insertion produced `illegal character U+005C`, fixed by the tested insertion in the [image build instructions](build.md). A clean Docker build and exact launch-command help check then passed.

The final image contains no diagnostic packet logging, signed-status helper, captures, compiler, or Go build cache. Its modified source is included at `/usr/share/mysterium/source` for reproduction and source distribution. No unrelated UDP, DNS-over-TCP, or ICMP implementation changes were made.
