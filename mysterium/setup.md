# Set up Mysterium on Salad

[Guide index](README.md)

**Registration is blocked on the tested account.** MystNodes' official onboarding check returned `isEligibleForFreeRegistration:false` and displayed its account free-registration-limit explanation. This recipe rebuilds the startup software; it does not remove that restriction or prove unattended recovery. Resolve the [registration requirement](troubleshooting.md#account-registration-limit) before expecting this account's fresh node to become ready.

## What you need

- A [SaladCloud account](https://portal.salad.com/organizations), an organization/project you can manage, available container quota, and billing access. Check the portal's current price before starting a container.
- A [MystNodes account](https://my.mystnodes.com/) to own the new node.
- A macOS or Linux terminal with `python3` for the creation block below and `curl` for the optional public checks. Check Python with `python3 --version`; obtain it from [python.org](https://www.python.org/downloads/) if missing. Docker does not need to run on your laptop: Salad runs the image.
- Your **Salad API key**: in Salad's account menu, open **API Access** and copy the existing key. This key authorizes cloud operations. [Published instructions](https://docs.salad.com/reference/api-usage).
- Your **MystNodes API key**: open your MystNodes profile/settings, available through [My Profile](https://my.mystnodes.com/me), and find the API key for linking a node. This is a different key from Salad's. [Published account-linking instructions](https://help.mystnodes.com/en/articles/8006168-how-to-install-and-run-a-node-on-avado-box).

Keep keys in your password manager/account settings. Do not paste them into this Markdown, source control, screenshots, or logs. The creation block prompts without echoing keys and sends the MystNodes key directly into the container's environment.

The [startup script](start.sh) accepts Mysterium's provider and consumer terms through `--agreed-terms-and-conditions`. Starting the deployment runs that command. Review the [Mysterium terms](https://www.mystnodes.com/legal/terms-and-conditions) when operating your own account.

### Names you will encounter

| Name | Meaning |
| --- | --- |
| Container group | Saved Salad configuration. This guide names it `mysterium`, displayed as **Mysterium**. |
| Instance ID | Salad's UUID for a particular container. Use it for restart/reallocation operations. |
| Machine ID | Salad's UUID for the host assigned to the container. |
| Mysterium identity | The node's `0x...` address. Use it with `myst cli identities` and Mysterium discovery. It is not an API key. |

## Find your organization and project

The owner's tested Salad location is organization `cosmosgeeketh`, project `default`:

[Open the container groups](https://portal.salad.com/organizations/cosmosgeeketh/projects/default/containers)

For another account, first create/select an organization and project in Salad. Their slugs appear in the portal URL as `/organizations/ORG/projects/PROJECT/containers`. Substitute those values in the creation block. No old instance ID or old Mysterium identity is required for a fresh deployment.

## Create the deployment

These are the **measured configuration choices**, not minimum requirements: one CPU, 1024 MiB RAM, no GPU, 64 MiB shared memory, one replica, `batch` priority, and `restart_policy: always`. The image is a pinned build of Mysterium `1.39.5` with the provider MTU correction described in [troubleshooting](troubleshooting.md). It uses the official image as its base. The [image build instructions](build.md) contain the complete build recipe if the published image is ever unavailable.

Run the following whole block in **your laptop's terminal**, not inside Salad. Change `ORG` and `PROJECT` if needed. Paste each API key only when its hidden prompt appears, then press Enter. The block creates a **stopped** group. Its image includes automatic account claiming and sponsored identity registration. After creation, [start and verify the host](setup.md#start-and-verify-the-host).

```bash
python3 - <<'PY'
import getpass
import json
import urllib.error
import urllib.request

ORG = "cosmosgeeketh"
PROJECT = "default"
GROUP = "mysterium"
COUNTRY_CODES = ["gb"]  # Current owner-authorized UK trial.
IMAGE = "docker.io/cosmosgeek0/salad-bandwidth-stack@sha256:1ee2bb61878f03754b469e59f8a98020407d31aa67c284a181560124205c7fab"

salad_key = getpass.getpass("Salad API key: ").strip()
myst_key = getpass.getpass("MystNodes API key: ").strip()
if not salad_key or not myst_key:
    raise SystemExit("Both account keys are required.")

command = ["/usr/local/bin/mysterium-start.sh"]

payload = {
    "name": GROUP,
    "display_name": "Mysterium",
    "autostart_policy": False,
    "replicas": 1,
    "restart_policy": "always",
    "country_codes": COUNTRY_CODES,
    "readiness_probe": {
        "exec": {"command": ["/bin/sh", "-c", "test -f /var/run/mysterium-node/registered"]},
        "initial_delay_seconds": 0, "period_seconds": 5, "timeout_seconds": 2,
        "success_threshold": 1, "failure_threshold": 1,
    },
    "container": {
        "image": IMAGE,
        "image_caching": True,
        "priority": "batch",
        "resources": {"cpu": 1, "memory": 1024, "shm_size": 64},
        "command": command,
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
    headers={"Salad-Api-Key": salad_key, "Content-Type": "application/json", "User-Agent": "mysterium-setup"},
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

The API's **published and previously measured** creation success response is HTTP `201`. A name-conflict error means you should inspect the existing group and use [stop/start instructions](operations.md#stop-start-restart-or-rebuild), rather than deleting it reflexively. If a request times out, check whether the group exists before rerunning it.

The creation request puts `priority` inside `container`; Salad's GET response reports priority at the group level. The payload follows the [published creation schema](https://docs.salad.com/reference/saladcloud-api/container-groups/create-container-group).

The original trial used authenticated API calls after the portal's Docker wizard did not actually create a group. The Python block above is a self-contained replacement for that local API invocation; it needs no SDK or project helper. Its original stock configuration matched the first live setup; the block now specifies the corrected image, MTU, and resolver saved during the resumed trial. The reproduction audit executed its Python body with dummy keys and an intercepted HTTP transport, including hidden terminal prompts and success/error paths. It did not submit a real creation request. The [reproduction audit](verification.md#reproduction-audit) records the verification scope.

### What runs inside the container

[start.sh](start.sh) sets the tested resolver and MTU, starts Mysterium, waits for its local API, discovers the actual identity, and configures the MystNodes account key. If the identity is unregistered, it checks identity-specific sponsorship eligibility and requests registration only after `eligible:true`. It waits for the native status `Registered` before creating the readiness marker. In the live replacement tests, that condition was not reached.

The chosen local API/identity startup budget is **180 seconds**, checked between bounded calls. Registration then waits on the same identity and checks again at a configured **30-second interval** while remaining unready. It no longer restarts solely because eligibility has not arrived. A failed claim is retried after the same cooldown. A registration-command failure retains the identity and checks native status before retrying; an InProgress result is allowed to finish. A daemon failure still propagates to Salad. These are configuration choices, not provider timing guarantees. The script does not fund identities or bypass eligibility.

The readiness probe checks the registration marker. It distinguishes completed registration from a merely running process; it does not establish monitoring success or earnings. The marker is cleared at startup and on launcher exit.

- `MYSTNODES_API_KEY` remains a container environment secret; no Salad API key is installed inside the image.
- The full userspace stack still uses the tested MTU correction. See [troubleshooting](troubleshooting.md#provider-mtu-correction).
- A fresh filesystem receives a fresh identity. The startup script claims it automatically and requests registration only when sponsorship is available. Unavailable eligibility leaves it unregistered and unready.
- No public administration port, Container Gateway, GPU, or earnings-triggered restart policy is configured.

## Start and verify the host

1. Open the group link printed by the creation block. Wait for image preparation to finish, then click **Start**.
2. Look at the **Instances** table. Open the actual instance once its process is **RUNNING**, including when it is **NOT READY**, to diagnose pending registration. Completed registration should produce **READY**. The group heading can say Running while its instance is still allocating or creating.
3. Click that instance and open **Terminal**. Click inside the terminal before typing. If it says Connection Closed, refresh the instance page and reconnect.
4. Run these commands in the **Salad container's shell**, entering **one complete command at a time and pressing Enter after each**. Browser-automated multiline entry joined commands together during the audit; individual command entry worked. This is not your laptop's terminal and not the interactive prompt entered by running bare `myst cli`.

```sh
wget -qO - http://127.0.0.1:4050/healthcheck
wget -qO - http://127.0.0.1:4050/location
myst cli identities list
```

Check that health reports version `1.39.5`, branch `salad-mtu`, and commit `c45527af-mtu`. Check that location matches the selected country; this recipe uses `"country":"GB"` for the current UK trial. Record the actual ISP/IP type; a country restriction does not guarantee a residential connection. The earlier U.S. trial received cellular, education, and residential networks on different assignments.

The current owner-authorized trial uses `country_codes: ["gb"]`. Earlier U.S. results are historical. Preserve the owner’s current selection during restart/reallocation; change `COUNTRY_CODES` only when deliberately selecting a different trial country.

If allocation stalls, use the group's **System Events** tab to distinguish platform reallocation, host interruption, or a container exit. In the trial, an instance's process answered requests while Salad still called it Creating; Salad later reallocated it. Do not equate a responding process with provider traffic working.

## Verify automatic registration

The startup script performs claiming and sponsored registration. Read the actual identity from the command above, then verify it in the Salad terminal:

```sh
myst_id='PASTE_THE_ACTUAL_0x_IDENTITY_HERE'
myst cli identities get "$myst_id"
test -f /var/run/mysterium-node/registered && printf 'Registration readiness confirmed\n'
```

Expect `Registration Status: Registered` and the readiness marker. `InProgress`, an absent marker, or a running process alone is not completed onboarding. After reconnecting the terminal, set `myst_id` again before using it.

If startup does not finish, read its filtered logs using [troubleshooting](troubleshooting.md#remaining-diagnostics). The native generic free-registration flag used by the old image did not complete onboarding; the current script uses the account-linked, identity-specific path that was verified manually. Sponsorship can be declined by MystNodes; automatic registration is not a guarantee of free eligibility on every future assignment.

Continue with [node verification](operations.md#verify-the-running-node).
