# Set up EarnApp in Salad

Use this for the cloud client. Use [MONITORING.md](MONITORING.md) afterward to record its traffic and account readings.

You need a browser, working Salad and EarnApp accounts, Salad credit and available capacity. The pinned public image and official download must still be available. The historical installation was measured as Ubuntu 20.04.4 LTS with EarnApp 1.665.73.

EarnApp's [published Docker/hosting policy](https://help.earnapp.com/hc/en-us/articles/10199416541969--Can-I-install-EarnApp-on-Hosting-Services-Virtual-Machines-or-Dockers) warns of account termination and canceled payments. This setup does not hide the container or guarantee earnings.

## Open the accounts

1. Sign into [SaladCloud](https://portal.salad.com/organizations). Select organization **cosmosgeeketh** and project **Default** for this installation.
2. Check **Billing & Usage** for credit and **Quotas** for room to run the allocation.
3. In the Chrome profile already signed into the intended account, open [EarnApp Passive Income](https://earnapp.com/dashboard/me/passive-income).
4. If this device is already running, use that deployment. Do not launch another copy of the same device ID.

## Restore this device or create a fresh one

Saved deployment details:

| Item | Value |
|---|---|
| Organization / project | `cosmosgeeketh` / `default` |
| Group | `earnapp-live`, displayed as **EarnApp** |
| Group page | [Open EarnApp in Salad](https://portal.salad.com/organizations/cosmosgeeketh/projects/default/containers/earnapp-live) |
| Saved device ID | `sdk-node-f529f336e6a94edaa4c7c4d23fa0d355` |
| Restore environment variable | `EARNAPP_UUID` = the complete saved device ID above |

Use that UUID only for this existing linked account and after its previous copy has stopped. A replacement Salad machine or group can have a different ID while this EarnApp device identity stays the same.

For a different account or a genuinely new device, leave `EARNAPP_UUID` unset. The startup script initializes a new ID; link and save it as described below. Do not use this account's saved ID for another account.

## Configure the container

Open **Container Groups → Deploy a Container Group → Custom Container Group → Get Started**. Choose **SaladCloud Community – CPU only**.

Use these deployment settings. United States only is required; resource settings come from the measured installation:

| Setting | Value |
|---|---|
| vCPUs | **1 vCPU** |
| Memory | **1 GB** |
| Shared memory | **64 MB** |
| GPU / additional disk | None |
| Allowed Countries | **United States only** (`["us"]` in the API; never All) |
| Priority | Lowest (`batch` in the API) |
| Replicas | 1 |
| Restart policy, if offered | Always |
| Scheduled scaling | Unconfigured |

Use `earnapp-live` as the group name when available. If Salad returns `name_conflict`, use an unused name such as `earnapp-rebuild`.

In **Image Source → Edit → Public Registry**, paste:

```text
docker.io/fazalfarhan01/earnapp@sha256:5506e2992d8154292dca81054b56c4d1ae1f8b038b3248b871a600df6f2d12d8
```

This pins the tested unofficial Ubuntu image. Its old bundled client is replaced by the official versioned download in `startup.sh`; do not select the image's default startup.

For a restore, add the saved `EARNAPP_UUID` under **Environment Variables**. For a fresh device, leave it unset.

## Install the supervised command

The supervisor is [startup.sh](startup.sh). It verifies US placement, installs the pinned client, records traffic and handles native failures. The [recovery guide](RECOVERY.md) explains every policy.

On your Mac, open Terminal and run:

```bash
cd ~/Desktop/salad
python3 EarnApp/earnapp-recorder.py --command
```

This prints the exact JSON command array used by the deployment. Its first item is the command, `/bin/bash`; each following item is a separate argument. In Salad's **Command → Edit → Manual Edit**, enter those items into the corresponding command/argument fields without JSON quotes. The long encoded arguments are generated from `startup.sh`; copy them exactly. Do not select the image's default command. `--startup` prints the readable script if you want to inspect it.

Configure the **Liveness Probe** as an Exec probe using [liveness.json](liveness.json): copy its command array and timing fields. This checks the supervisor heartbeat, not provider earnings. Keep the gateway and readiness/startup probes disabled for this setup.

For API deployment, set `container.command` to the array printed above, `liveness_probe` to the contents of `liveness.json`, and `country_codes` to `["us"]`. A command update creates a new version; reallocate the old instance if it has not moved to that version. Keep the saved `EARNAPP_UUID`, pinned image and resource settings.

Review the current price and select **Deploy**. If the group is **Stopped**, select **Start**. A running group can still be allocating or downloading a worker: verify the individual instance and its native samples.

Published prices when checked on September 7, 2026 were **$0.005 per running hour** for this allocation. The [announced September 12 change](https://blog.salad.com/saladcloud-price-changes-september-2026/) makes it **$0.006**. Use the current portal quote when deploying.

## Link and preserve a fresh ID

1. Open the running instance's **Container Logs**. Look for the version, registration result and `https://earnapp.com/r/sdk-node-...` link.
2. Open that exact link in the intended signed-in EarnApp account and confirm **Device successfully linked**.
3. Match the device in the provider's list. It may show only the ID's ending; open its details for the full ID.
4. Save the complete ID outside the container. Set the group's `EARNAPP_UUID` environment variable to it for subsequent starts.
5. After that update, use the cloud **Terminal** to run `earnapp showid` and confirm the saved ID survived.

For an already linked restore, confirm the device appears in the correct account. Reopen its `https://earnapp.com/r/` link if needed. Do not invent a replacement ID.

## Verify the client and money separately

Run these in the Salad instance's **Terminal**:

```bash
cat /etc/os-release
earnapp --version
sha256sum /usr/bin/earnapp
earnapp showid
earnapp status
ps -eo pid,ppid,pgid,etime,rss,comm
```

The measured SHA-256 of the tested official binary and earlier running cloud binary was:

```text
a5080f9eff9df9f59a2192ccafc344f06259bfffe2a0aee619d44c8cafbd8def
```

A different checksum means different bytes; verify the source and version before calling it the same tested client.

`enabled` or a live process does not establish registration or paid activity. Check the actual registration result and provider account. The authoritative earnings figure is the device's **Amount / Total earned**, not its displayed monthly Rate or network bytes.

Record the amount and compare a later provider refresh. EarnApp's [published calculation](https://help.earnapp.com/hc/en-us/articles/38191916327441--What-are-the-EarnApp-rates-How-are-they-calculated) uses qualifying active usage. Low traffic and unchanged credits never replace a healthy client. The native supervisor and verified provider-offline policy handle actual failures; see RECOVERY.md.

If the image or binary disappears, consult the [official Linux instructions](https://help.earnapp.com/hc/en-us/articles/10261224561553-Installation-instructions-and-hardware-software-requirements) before changing the pinned script.

References: [Salad command fields](https://docs.salad.com/container-engine/how-to-guides/specifying-a-command), [browser terminal](https://docs.salad.com/container-engine/explanation/container-groups/ssh-and-terminal), [EarnApp commands](https://help.earnapp.com/hc/en-us/articles/11987016499089-EarnApp-commands-for-Linux), [image source](https://github.com/fazalfarhan01/EarnApp-Docker).
