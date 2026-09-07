# Mysterium on Salad — rebuild and operating guide

Written from the live trial on **2026-09-07**. This file is intended to be usable without the previous chat, this repository's other files, a local credential helper, or an existing container.

**What was achieved:** a U.S.-only Salad deployment running the official Mysterium image, a registered identity linked to MystNodes, and externally published service proposals. **What was not achieved:** passing Mysterium monitoring or verified customer bandwidth service. The last completed monitoring checks still reported `failed`. This guide records the tested configuration and manual rebuild procedure. A clean cloud rebuild from this file alone has not been performed; it is not a proven earning recipe.

In this guide, **measured** means observed on the actual trial, **published** means documented by the linked provider, and command values are the tested configuration or explicit diagnostic deadlines—not claims about minimum resources, maximum performance, or guaranteed startup time.

## 1. What you need

- A [SaladCloud account](https://portal.salad.com/organizations), an organization/project you can manage, available container quota, and billing access. Check the portal's current price before starting a container.
- A [MystNodes account](https://my.mystnodes.com/) to own the new node.
- A macOS or Linux terminal with `python3` for the creation block below and `curl` for the optional public checks. Check Python with `python3 --version`; obtain it from [python.org](https://www.python.org/downloads/) if missing. Docker does not need to run on your laptop: Salad runs the image.
- Your **Salad API key**: in Salad's account menu, open **API Access** and copy the existing key. This key authorizes cloud operations. [Published instructions](https://docs.salad.com/reference/api-usage).
- Your **MystNodes API key**: open your MystNodes profile/settings, available through [My Profile](https://my.mystnodes.com/me), and find the API key for linking a node. This is a different key from Salad's. [Published account-linking instructions](https://help.mystnodes.com/en/articles/8006168-how-to-install-and-run-a-node-on-avado-box).

Keep keys in your password manager/account settings. Do not paste them into this Markdown, source control, screenshots, or logs. The creation block prompts without echoing keys and sends the MystNodes key directly into the container's environment.

The launch command accepts Mysterium's provider and consumer terms through `--agreed-terms-and-conditions`. Starting the deployment runs that command. Review the [Mysterium terms](https://www.mystnodes.com/legal/terms-and-conditions) when operating your own account.

### Names you will encounter

| Name | Meaning |
| --- | --- |
| Container group | Saved Salad configuration. This guide names it `mysterium`, displayed as **Mysterium**. |
| Instance ID | Salad's UUID for a particular container. Use it for restart/reallocation operations. |
| Machine ID | Salad's UUID for the host assigned to the container. |
| Mysterium identity | The node's `0x...` address. Use it with `myst cli identities` and Mysterium discovery. It is not an API key. |

## 2. Choose the correct starting point

- **Everything was deleted / no group exists:** follow section 3.
- **The group still exists but is stopped:** use the Stop/Start instructions in section 7; do not create a duplicate.
- **An instance is already running:** open its Terminal and begin section 4.

The owner's tested Salad location is organization `cosmosgeeketh`, project `default`:

[Open the container groups](https://portal.salad.com/organizations/cosmosgeeketh/projects/default/containers)

For another account, first create/select an organization and project in Salad. Their slugs appear in the portal URL as `/organizations/ORG/projects/PROJECT/containers`. Substitute those values in the creation block. No old instance ID or old Mysterium identity is required for a fresh deployment.

## 3. Create the saved U.S.-only deployment

These are the **measured configuration choices**, not minimum requirements: one CPU, 1024 MiB RAM, no GPU, 64 MiB shared memory, one replica, `batch` priority, and `restart_policy: always`. The official image is pinned to the digest used in the trial, reporting Mysterium `1.39.5`.

Run the following whole block in **your laptop's terminal**, not inside Salad. Change `ORG` and `PROJECT` if needed. Paste each API key only when its hidden prompt appears, then press Enter. The block creates a **stopped** group; section 4 starts it.

```bash
python3 - <<'PY'
import getpass
import json
import urllib.error
import urllib.request

ORG = "cosmosgeeketh"
PROJECT = "default"
GROUP = "mysterium"
IMAGE = "docker.io/mysteriumnetwork/myst@sha256:4a7f312c8b8bec4fa249d6e916a9e2b0c4987f50a5e4d9f72b71efd10bbcd1cf"

salad_key = getpass.getpass("Salad API key: ").strip()
myst_key = getpass.getpass("MystNodes API key: ").strip()
if not salad_key or not myst_key:
    raise SystemExit("Both account keys are required.")

command = (
    'exec /usr/local/bin/docker-entrypoint.sh '
    '--userspace --transactor.provider.try-free-registration '
    '--log-level=info --mmn.api-key="$MYSTNODES_API_KEY" '
    'service --agreed-terms-and-conditions'
)
payload = {
    "name": GROUP,
    "display_name": "Mysterium",
    "autostart_policy": False,
    "replicas": 1,
    "restart_policy": "always",
    "country_codes": ["us"],
    "container": {
        "image": IMAGE,
        "image_caching": True,
        "priority": "batch",
        "resources": {"cpu": 1, "memory": 1024, "shm_size": 64},
        "command": ["/bin/sh", "-c", command],
        "environment_variables": {"MYSTNODES_API_KEY": myst_key},
    },
}
url = (
    "https://api.salad.com/api/public/organizations/"
    f"{ORG}/projects/{PROJECT}/containers"
)
request = urllib.request.Request(
    url,
    data=json.dumps(payload).encode(),
    headers={"Salad-Api-Key": salad_key, "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
        print("Create response:", response.status, "group:", result["name"])
except urllib.error.HTTPError as error:
    raise SystemExit(f"Create failed: HTTP {error.code}. Check the group/account in Salad.")

print("Open this group, wait for preparation, then click Start:")
print(f"https://portal.salad.com/organizations/{ORG}/projects/{PROJECT}/containers/{GROUP}")
PY
```

The API's **published and previously measured** creation success response is HTTP `201`. A name-conflict error means you should inspect the existing group and use section 7, rather than deleting it reflexively. If a request times out, check whether the group exists before rerunning it.

The creation request puts `priority` inside `container`; Salad's GET response reports priority at the group level. The payload follows the [published creation schema](https://docs.salad.com/reference/saladcloud-api/container-groups/create-container-group).

The original trial used authenticated API calls after the portal's Docker wizard did not actually create a group. The Python block above is a self-contained replacement for that local API invocation; it needs no SDK or project helper. Its configuration matches the live setup. The reproduction audit executed its Python body with dummy keys and an intercepted HTTP transport, including hidden terminal prompts and success/error paths. It did not submit a real creation request. Section 11 records the verification scope.

### Why this launch command matters

- `--userspace` selects Mysterium's full userspace network stack. This is the path exercised on Salad; the trial did not add a TUN device or `NET_ADMIN`. It is distinct from merely choosing a userspace WireGuard binary. [Pinned implementation](https://github.com/mysteriumnetwork/node/blob/c45527af1ea80300ae3d9c92bd37255335b6140d/services/wireguard/endpoint/netstack-provider/client.go).
- The shell expands `$MYSTNODES_API_KEY` from Salad's environment. Keep the literal variable reference in the saved command; do not replace it with the secret.
- The free-registration flag only attempts the generic provider sponsorship path. It did **not** finish registration in the trial. Section 5 is still required for a new identity.
- No Container Gateway, public administrative port, GPU, autoscaler, or custom health probe was configured. The native API was reachable from inside the container at `127.0.0.1:4050`.
- `restart_policy: always` is a container restart policy. It is not a Mysterium monitoring-failure reallocation or new-identity registration policy.

## 4. Start it and verify the actual U.S. host

1. Open the group link printed by the creation block. Wait for image preparation to finish, then click **Start**.
2. Look at the **Instances** table. Wait for the actual instance to show **RUNNING / READY**. The group heading can say Running while its instance is still allocating or creating.
3. Click that instance and open **Terminal**. Click inside the terminal before typing. If it says Connection Closed, refresh the instance page and reconnect.
4. Run these commands in the **Salad container's shell**, entering **one complete command at a time and pressing Enter after each**. Browser-automated multiline entry joined commands together during the audit; individual command entry worked. This is not your laptop's terminal and not the interactive prompt entered by running bare `myst cli`.

```sh
wget -qO - http://127.0.0.1:4050/healthcheck
wget -qO - http://127.0.0.1:4050/location
myst cli identities list
```

Check that location reports `"country":"US"`. Record the actual ISP/IP type rather than assuming that U.S. placement guarantees a residential connection. The trial received cellular, education, and residential U.S. networks on different assignments.

If location is not US, inspect the group's country restriction and reallocate the instance after correcting it. The intended saved value is exactly `country_codes: ["us"]`. Do not remove the restriction to obtain a faster allocation.

If allocation stalls, use the group's **System Events** tab to distinguish platform reallocation, host interruption, or a container exit. In the trial, an instance's process answered requests while Salad still called it Creating; Salad later reallocated it. Do not equate a responding process with provider traffic working.

## 5. Claim and register the new identity

Copy the identity printed by `myst cli identities list`. In the same **Salad terminal**, set the variable below to that exact address. Do not use the historical address in section 9 for a fresh container.

```sh
myst_id='PASTE_YOUR_NEW_0x_IDENTITY_HERE'
myst cli mmn "$MYSTNODES_API_KEY"
myst cli identities get "$myst_id"
```

Expected account-linking output measured in the trial: `[SUCCESS] MMN API key configured.` If the identity already says `Registered`, skip the registration command below and continue to section 6.

For an unregistered identity, check its **identity-specific** sponsorship eligibility:

```sh
wget -qO - "http://127.0.0.1:4050/identities/$myst_id/eligibility"
```

The measured successful free path returned `{"eligible":true}`. Only after that result, run:

```sh
myst cli identities register "$myst_id"
```

The CLI printed `Registration started. Top up the identities channel to finish it.` even when the sponsored registration subsequently succeeded. That sentence alone did not mean a deposit was needed. Check actual status again:

```sh
myst cli identities get "$myst_id"
```

Wait for `Registration Status: Registered`; `InProgress` is not finished. The trial registered without a wallet top-up. Sponsorship is an external account/network decision: if eligibility is false or the request fails, use the current MystNodes onboarding instructions to determine the required registration path rather than assuming registration is free.

The launch command automatically unlocks the selected identity. Manually unlocking it did not establish a cure for the later metrics-signing error.

**After a terminal refresh/reconnect**, run `myst cli identities list` and set `myst_id` again before using commands that reference it. Shell variables do not survive a new terminal session.

## 6. Verify each layer separately

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
| Completed monitoring sessions | Monitoring connected and recorded traffic; this does not itself establish passing monitoring or customer traffic. |

`myst cli service sessions` labels its result “Current sessions” but reads session history. Do not report it as a live connection count. `/node/provider/sessions?range=1d` instead reads remote quality data with a published-in-source cache of ten minutes; use `/sessions` for local history. Empty agent statuses do not establish that there are no faults. [Measured-version source](https://github.com/mysteriumnetwork/node/blob/c45527af1ea80300ae3d9c92bd37255335b6140d/core/quality/mysterium_morqa.go).

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

curl -sS --max-time 20 --get \
  --data-urlencode "provider_id=$myst_id" \
  --data-urlencode 'service_type=monitoring' \
  --data-urlencode 'include_monitoring_failed=true' \
  --data-urlencode 'access_policy=mysterium' \
  --data-urlencode 'access_policy_source=https://trust.mysterium.network/api/v1/access-policies/mysterium' \
  https://discovery.mysterium.network/api/v4/proposals
```

The policy fields above were read from the trial's native `/services` response. Queries omitting them returned `null` even though the correctly filtered query returned published proposals. For the other services, replace `service_type=monitoring` with a service type listed earlier. If using a different configuration, read its actual policies instead of assuming these values. [Exact query-field implementation](https://github.com/mysteriumnetwork/node/blob/c45527af1ea80300ae3d9c92bd37255335b6140d/market/mysterium/dto.go).

## 7. Turn it off, turn it back on, or rebuild it

| Operation | How to do it | What to check afterward |
| --- | --- | --- |
| Stop for now | Open the Salad group and click **Stop**. | Wait for the deployment/instances to stop. This preserves the saved group configuration, not a promise of retaining the old container filesystem. |
| Start an existing stopped group | Open that same group and click **Start**. | Follow sections 4–6 again. Discover the actual identity and register it if new. |
| Restart a running instance | Open its instance page and click **Restart**. | In the trial, identity/data and the DNS edit survived this operation. Verify them again after reconnecting. |
| Reallocate a failed host | Open its instance page and click **Reallocate**. | A different host/IP/filesystem and new identity were measured. Repeat country, claim, registration, DNS, and monitoring checks. |
| Recreate | Use the instance's **Recreate** action only when intentionally resetting its container. | Treat this as a fresh filesystem and repeat onboarding. |
| Group was deleted | Repeat section 3 with the account keys. | Start it and follow sections 4–6. Historical instance IDs are not reusable configuration. |

Salad's [published lifecycle](https://docs.salad.com/container-engine/explanation/container-groups/container-groups) states that Start after Stop creates new instances. Its [deployment-management guide](https://docs.salad.com/container-engine/how-to-guides/managing-deployments) distinguishes Restart, Recreate, and Reallocate. A generic restart policy does not automate Mysterium sponsorship/registration on the new identity.

**If you need to preserve the exact old Mysterium identity**, its private node data must be backed up separately before deletion. The measured data directory is `/var/lib/mysterium-node`. It contains sensitive material; do not put it in this Markdown or Git. Follow Mysterium's [migration instructions](https://help.mystnodes.com/en/articles/8005511-how-to-migrate-your-node). This trial did not implement persistent storage or export an identity backup. If the data is gone, follow this guide to create a fresh identity; the public `0x...` address cannot recover its private key.

## 8. Observed failures and their handling

### DNS: apply a correction only after measuring this host

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

The default lookup then answered. Click **Restart** on the same instance, reconnect, and repeat `cat /etc/resolv.conf`, the lookup, health, identity, and monitoring checks. The change survived the measured same-instance restart. **It was not put into the saved launch command**, so a new allocation must be tested again. This DNS change did not establish that Mysterium monitoring was fixed; monitoring remained failed. Different before/after deadlines also do not establish a speed improvement.

### Remaining diagnostics

To read the current native log without printing lines containing the account-linking key, run inside the container:

```sh
tail -n 80 /root/.mysterium/logs/mysterium-node* | awk 'index($0,ENVIRON["MYSTNODES_API_KEY"])==0'
```

Do not dump environment variables, full configuration, or process command lines into shared logs: these can contain the key. The exact-key filter above is not a general sanitizer for arbitrary sensitive data.

| Observed failure / misleading signal | Action taken and actual result |
| --- | --- |
| Portal Docker wizard did not create a group; API lookup found none. | Created the stopped group through the authenticated Salad API, then started it in the authorized trial. The guide uses API creation directly. |
| Wizard initially selected GPU resources. | Corrected to CPU-only settings; the saved configuration above has no GPU request. |
| Generic `Free registration is not eligible` warning. | Claimed the node with the MystNodes key, checked identity-specific eligibility, then registered through the CLI. Native status became Registered without a top-up. |
| Initial allocation was Mexico. | Saved `country_codes:["us"]` and explicitly reallocated the Mexico instance. Subsequent observed assignments were U.S. |
| First U.S. process responded while Salad showed Creating. | Read System Events; Salad recorded `Instance Reallocated by Platform`. Followed the replacement; no cause beyond that event was established. |
| North Carolina host was Running/Ready and published but monitoring-failed. | Reallocated within the existing U.S. restriction. The next measured host was residential AT&T in Texas. |
| `Failed to sign metrics event ... authentication needed: password or unlock`. | Read source and tried native identity unlock earlier. Unlock was not proved to cure it; the error alone did not establish that the provider identity was locked or explain failed monitoring. |
| Stopping monitoring first used a mistyped service UUID, then the correct UUID returned `monitoring service cannot be stopped`. | Read the real service ID; used an instance Restart instead. Do not try to stop/restart monitoring independently as the recovery recipe. |
| SSH returned `Permission denied (publickey)`. | Used the owner's signed-in Salad web terminal; no new SSH key was needed for the tested path. |
| Web terminal disconnected. | Refreshed the instance page and clicked its Terminal input before issuing more commands. Checked the current instance ID when a host had been replaced. |
| Authenticated MystNodes manual-check endpoint returned HTTP `500`. | Read its actual response. Later accepted requests were HTTP `200`, but completed sessions still did not clear monitoring failure. No cause or permanent API fix was established. |
| Public discovery returned `null`. | Read the native access policies and queried using the correct policy/source and service type; proposals were returned. |
| Salad log API gave old output after an instance restart. | Checked current native health and the in-container log instead of treating absent fresh cloud logs as a healthy result. |
| Log API rejected a large page request or unsupported timestamp format with HTTP `400`. | Used the measured accepted page size of 100 and UTC timestamps with milliseconds ending in `Z`; advanced the time window instead of treating the first page as all logs. |

### Discarded experiment: MTU modification

On the earlier Mexico instance, a temporary binary was built from official node commit `c45527af1ea80300ae3d9c92bd37255335b6140d` using Go `1.26.8`. The provider netstack's `ConfigureDevice` was changed to honor `cfg.MTU`, falling back to the original default. The runtime `wireguard.mtu` was set to the experimental value `1200`, and the instance was restarted.

The actual monitoring check still failed. Header-only tcpdump captures did not establish MTU as the cause. The temporary binary, compiler/source directories, captures, and MTU setting were not carried to the U.S. deployment. **The rebuild recipe uses the stock official image, not that experiment.** No custom image was published. Independent Astra reviews found no concrete defect in the final launch/resolver change, while explicitly leaving successful bandwidth service unproved.

## 9. Last measured trial state — reference only

The live Salad configuration was read again at **2026-09-07 05:33 UTC**. The latest detailed monitoring/session observation before this guide was **05:27 UTC**. These identifiers describe that snapshot; always discover the new identity after rebuilding.

| Field | Measured value |
| --- | --- |
| Organization / project / group | `cosmosgeeketh` / `default` / `mysterium` |
| Instance | `64b5bb24-ef09-4207-bd20-6becd94d0e10` |
| Machine | `85436a6f-593f-a55c-90d0-869a2f074a88` |
| Mysterium identity | `0xdab9936d468965cc1d8282c29808481f8d481cb4` |
| Location | Plano, Texas, US; AT&T Enterprises LLC; classified residential |
| Public IP | `12.131.55.162` |
| Salad / native identity | Running, Ready, Started / Registered |
| Discovery | Native service proposals returned by correctly filtered public queries |
| Test outcome | Completed monitoring sessions exchanged data; monitoring still `failed`; customer traffic unverified |
| Native resolver | `/etc/resolv.conf` retained only `nameserver 1.0.0.1` after restart |

The original user-linked identity `0x056f1396e48ec3d0808b87e671ea44ad4c8011be` was an existing offline India node. It was not moved or reused. Fresh Salad filesystems created new identities linked to the same MystNodes account. Old account rows can remain after their Salad instances are gone; they are not a list of currently running Salad replicas.

For the current owner account, [open the Salad group](https://portal.salad.com/organizations/cosmosgeeketh/projects/default/containers/mysterium) and [open MystNodes](https://my.mystnodes.com/nodes). A direct node-statistics URL may redirect to the node list while MystNodes has not populated that identity's dashboard state.

## 10. How to record a later successful run

If a later attempt succeeds, update this file with the date, actual image/configuration changes, U.S. location, registered identity, monitoring result, and the relevant session evidence. Separate monitoring sessions from customer service types and recorded history from simultaneous connections. Record the exact fix that survived a fresh start before changing this guide's outcome to successful.

This file contains the complete bootstrap instructions and the observed failure history. It intentionally contains no credentials, private identity backup, hidden helper dependency, background watcher, or automatic re-registration/reallocation service.

## 11. Reproduction audit — 2026-09-07

These are measured verification results, not a claim that a new cloud rebuild or successful bandwidth service was demonstrated:

| Test actually performed | Result and limit |
| --- | --- |
| Fresh local pull of the pinned image for `linux/amd64` | Digest resolved; the binary reported version `1.39.5`, commit `c45527af`. The documented entrypoint and `myst`, `wget`, `timeout`, `nslookup`, `awk`, and `sh` were present. |
| Documented launch command with `--help` appended, in a fresh local container with networking disabled | Entrypoint setup and launch-flag parsing succeeded. The node service was not started and no account key was supplied. |
| Entire embedded Python body with real hidden terminal prompts, dummy keys, and intercepted HTTP transport | Both simulated creation success and HTTP-error paths passed. The request contained the intended U.S.-only settings; dummy keys were not echoed. This did not test live Salad creation acceptance. |
| Request configuration compared with a fresh authenticated GET of the existing Salad group | Image, command, resources, country restriction, replica count, priority, and restart/autostart settings matched. Request/response priority placement and omitted GPU selection were accounted for. |
| Documented native read-only checks replayed individually on the existing Salad instance | Health responded; location remained Plano, Texas, US; the identity was Registered and native services were Running. Monitoring remained `failed`. |
| Documented public-API block executed with only the identity placeholder substituted | Returned that identity's monitoring failure and its published U.S. residential monitoring proposal. |

Shell/Python syntax checks and an actual-credential scan also passed. No live key is stored in this file.

**Not re-executed in this audit:** cloud creation, Start/Stop, account claiming, registration, DNS changes, Restart, Recreate, or Reallocate. Those operational steps are documented from the earlier live trial. A fresh host, its IP/ISP, sponsorship eligibility, and monitoring outcome depend on the services' current state; the file cannot guarantee the same identity, host, or result after deletion. Recovering the exact old identity requires its separately saved private data.
