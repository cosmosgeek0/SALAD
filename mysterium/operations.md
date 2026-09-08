# Operate and verify Mysterium

[Guide index](README.md)

**Shelved at the owner's request — 2026-09-07.** Leave the group stopped; use the procedures below only if the owner explicitly resumes Mysterium. The last trial remained blocked by the original account's free-registration limit. The [registration requirement](troubleshooting.md#account-registration-limit) is retained as an unresolved historical result.

For a fresh deployment, complete [setup](setup.md) first. Public checks below need `curl` and `python3` on your laptop; the native commands run in the Salad terminal.

## Stop, start, restart, or rebuild

| Operation | How to do it | What to check afterward |
| --- | --- | --- |
| Stop for now | Open the Salad group and click **Stop**. | Wait for the deployment/instances to stop. This preserves the saved group configuration, not a promise of retaining the old container filesystem. |
| Start an existing stopped group | Open that same group and click **Start**. | Follow [host and identity setup](setup.md#start-and-verify-the-host), then [node verification](operations.md#verify-the-running-node) again. The image claims a fresh identity and requests sponsored registration when eligible; verify the actual result. |
| Restart a running instance | Open its instance page and click **Restart**. | In the same-instance trials, identity/data, the DNS edit, and the installed binary survived this operation. Verify them again after reconnecting. |
| Reallocate a failed host | Open its instance page and click **Reallocate**. | A different host/IP/filesystem and new identity were measured. Verify country, automatic registration, DNS, and monitoring on the replacement. The corrected image and launch settings come from the saved group. |
| Recreate | Use the instance's **Recreate** action only when intentionally resetting its container. | Treat this as a fresh filesystem and repeat onboarding. |
| Group was deleted | Repeat [deployment setup](setup.md#create-the-deployment) with the account keys. | Start it and follow [host and identity setup](setup.md#start-and-verify-the-host), then [node verification](operations.md#verify-the-running-node). Historical instance IDs are not reusable configuration. |

Salad's [published lifecycle](https://docs.salad.com/container-engine/explanation/container-groups/container-groups) states that Start after Stop creates new instances. Its [deployment-management guide](https://docs.salad.com/container-engine/how-to-guides/managing-deployments) distinguishes Restart, Recreate, and Reallocate. The image now includes [startup registration](start.sh). The current source preserves the identity and stays unready while registration eligibility is unresolved. It does not turn that condition into a replacement loop or claim success.

**If you need to preserve the exact old Mysterium identity**, its private node data must be backed up separately before deletion. The measured data directory is `/var/lib/mysterium-node`. It contains sensitive material; do not put it in this Markdown or Git. Follow Mysterium's [migration instructions](https://help.mystnodes.com/en/articles/8005511-how-to-migrate-your-node). This trial did not implement persistent storage or export an identity backup. If the data is gone, follow this guide to create a fresh identity; the public `0x...` address cannot recover its private key.

## Verify the running node

In the **Salad terminal**:

```sh
myst cli service list
myst cli nat
wget -qO - http://127.0.0.1:4050/sessions
wget -qO - http://127.0.0.1:4050/sessions-connectivity-status
wget -qO - http://127.0.0.1:4050/node/monitoring-agent-statuses
```

The measured running service types were `data_transfer`, `dvpn`, `scraping`, `monitoring`, and `quic_scraping`. They appeared without manually enabling the public `wireguard` service. MystNodes' service-toggle count does not count native services in the same way.

| Check | What it establishes |
| --- | --- |
| Salad instance Running/Ready and native health response | The container/process is operating. |
| Native identity Registered | Registration completed. |
| Discovery returns this identity's proposals | The provider is published. |
| `myst cli nat` monitoring result | Mysterium's reported monitoring status, separate from the NAT type. |
| `/sessions` | Local recorded sessions; inspect service type, status, timestamps, and byte counts. |
| Completed monitoring sessions | Recorded session status and byte counters. A Completed history status does not establish passing monitoring or successful customer payload delivery. |

`myst cli service sessions` labels its result “Current sessions” but reads session history. Do not report it as a live connection count. `/node/provider/sessions?range=1d` instead reads remote quality data with a published-in-source cache of ten minutes; use `/sessions` for local history. Empty agent statuses do not establish that there are no faults. `/sessions-connectivity-status` is an in-memory consumer connectivity cache, not a provider monitoring history; a restart clears it. [Measured-version source](https://github.com/mysteriumnetwork/node/blob/c45527af1ea80300ae3d9c92bd37255335b6140d/core/quality/mysterium_morqa.go).

### Request an official monitoring check

Open [My Nodes](https://my.mystnodes.com/nodes), find the **current identity** in either the Online or Offline list, open its row's action menu, and choose **Test node → Check Connection**. The profile can initially show Offline or Unknown even while the process responds; inspect the current identity rather than an old row.

Published on 2023-06-13: Mysterium allows one manual check per ten minutes and says this check does not perform a large data-transfer test. [Node service monitoring](https://help.mystnodes.com/en/articles/8005478-node-service-monitoring). Respect the current UI's rate limit; do not repeatedly submit checks.

Measured during the trial: some submissions returned HTTP `500` with `Internal Server Error`; a later current-node submission returned HTTP `200`. A closing dialog or HTTP `200` establishes neither a completed test nor passing monitoring. If needed, inspect the browser's developer tools **Network** panel and filter for `/check` to see the submission status. Use the native monitoring result and session records for the outcome.

### Verify through the public APIs

Run this optional block on **your laptop** with `curl`, replacing the identity. These endpoints require no account key. This `myst_id` is a new local shell variable, separate from the Salad terminal's variable.

```sh
myst_id='PASTE_YOUR_NEW_0x_IDENTITY_HERE'
curl -sS --max-time 20 \
  -H 'Content-Type: application/json' \
  --data "{\"providers\":[\"$myst_id\"]}" \
  https://quality.mysterium.network/api/v3/providers/monitoring-status

curl -sS --fail --max-time 20 \
  https://quality.mysterium.network/api/v3/providers/monitoring-pending | \
  python3 -c 'import json,sys; data=json.load(sys.stdin); print("PENDING" if sys.argv[1].lower() in json.dumps(data).lower() else "Not listed as pending")' "$myst_id"

curl -sS --max-time 20 --get \
  --data-urlencode "provider_id=$myst_id" \
  --data-urlencode 'service_type=monitoring' \
  --data-urlencode 'access_policy=mysterium' \
  --data-urlencode 'access_policy_source=https://trust.mysterium.network/api/v1/access-policies/mysterium' \
  https://discovery.mysterium.network/api/v4/proposals
```

If the pending check prints `PENDING`, do not treat an initial public `success` as a finished monitor test. A new identity in this trial simultaneously returned public `success`, appeared in the pending list, and had `monitoring_failed:true` in discovery. Absence from the pending list is not by itself proof of passing either. The discovery command above checks normal eligibility. For diagnosing a failed provider, add `--data-urlencode 'include_monitoring_failed=true'`; a result obtained with that option does not prove monitoring success. The policy fields above were read from the trial's native `/services` response. Queries omitting them returned `null` even though the correctly filtered query returned published proposals. For the other services, replace `service_type=monitoring` with a service type listed earlier. If using a different configuration, read its actual policies instead of assuming these values. [Exact query-field implementation](https://github.com/mysteriumnetwork/node/blob/c45527af1ea80300ae3d9c92bd37255335b6140d/market/mysterium/dto.go).

## Record a later run

After every fresh deployment, record the actual image digest, selected-country location, registered identity, monitoring result, and session evidence. A saved image is not a promise that every host, resolver, sponsorship request, or monitor will behave identically. Keep monitoring records separate from customer transfers and avoid calling a `New` session with zero recorded bytes a completed transfer.

This folder contains the bootstrap instructions, exact source build, and observed failure history. It contains no account credentials or private identity backup. Startup claiming and sponsored registration are automated. Ongoing monitoring failures or absent earnings do not trigger an added watchdog; readiness confirms registration only.
