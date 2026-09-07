# Run EarnApp on Salad from scratch

Deployment instructions audited on **September 7, 2026**. The startup and identity handling have execution evidence; reproducing the same earnings remains unproven. See the verification record at the end.

This guide lets you recreate the deployment using a browser, even if the local project files and the old Salad deployment are gone. You still need working Salad and EarnApp accounts, Salad credit and available capacity, and access to the public image and download below. There are no passwords or API keys in this file.

The setup is **Salad → Ubuntu container → official EarnApp Linux client**. The measured running container reported **Ubuntu 20.04.4 LTS** and client **1.665.73**. You do not need Docker Desktop, Python, this chat, or any other project file on your own computer.

EarnApp's [published policy](https://help.earnapp.com/hc/en-us/articles/10199416541969--Can-I-install-EarnApp-on-Hosting-Services-Virtual-Machines-or-Dockers) prohibits Docker and hosting and warns of account termination and canceled payments. This is a technical reproduction guide, not a way to hide Docker or a guarantee of earnings.

## 1. Open the accounts

1. Sign in to [SaladCloud](https://portal.salad.com/organizations).
2. For this project, select the **cosmosgeeketh** organization and **Default** project. Another reader should select their own organization and project.
3. Make sure the organization has credit in **Billing & Usage** and room for a container in **Quotas**.
4. In another tab, sign in to the [EarnApp dashboard](https://earnapp.com/dashboard/me/passive-income) that should receive the earnings. Create an account there if necessary.
5. If EarnApp is already running in your Salad organization, use that deployment. Do not launch another copy with the same device ID.

## 2. Choose whether you are restoring or starting fresh

An **EarnApp device ID**, also called a UUID, identifies the client in your EarnApp account. It is different from a Salad group name, instance ID, or machine ID.

**Restoring this project's existing EarnApp device:** use the following environment variable in step 4, only after the previous copy is no longer running:

| Key | Value |
|---|---|
| `EARNAPP_UUID` | `sdk-node-f529f336e6a94edaa4c7c4d23fa0d355` |

This device is already linked to the Cosmosgeek EarnApp account. Its dashboard name ends in `3fa0d355`. Keep the complete value above for a rebuild.

**Starting with a different account or no existing device:** leave `EARNAPP_UUID` unset. The startup command below will initialize a new device. You will link it and save its generated ID in step 6. Do not use the Cosmosgeek device ID for a different account.

## 3. Create the Salad container

Open **Container Groups → Deploy a Container Group**. On the starting-point page, choose **Custom Container Group → Get Started**.

Choose **SaladCloud Community – CPU only**, then **Next Step**. The wizard can initially select a GPU and larger CPU/RAM values; select the values below yourself.

These are the measured settings of the working deployment, not claimed minimum requirements:

| Setting | Value to select |
|---|---|
| vCPUs | **1 vCPU** |
| Memory | **1 GB** |
| Shared memory | **64 MB** |
| GPU | **None** / CPU only |
| Additional disk space | **None Selected** |
| Allowed Countries | **All** |
| Priority | **Lowest**; the API calls this `batch` |

Click **Next Step** to reach **Container Configuration**.

## 4. Set the image, name, and device ID

Use a container group name such as `earnapp-live`. If Salad says **name conflict**, use a new unused name such as `earnapp-rebuild`. A deleted name was rejected during our measured restore; deleting something else will not fix that.

In **Image Source → Edit**, choose **Public Registry** and paste this complete image name, then click **Configure**:

```text
docker.io/fazalfarhan01/earnapp@sha256:5506e2992d8154292dca81054b56c4d1ae1f8b038b3248b871a600df6f2d12d8
```

The long `sha256` ending pins the exact image we used. This unofficial Ubuntu-based image contains an old EarnApp binary. Our command downloads the tested official binary instead of running that old copy. Do not substitute the image's default startup or its `latest` instructions.

Set **Replicas = 1**. Leave **Scheduled Scaling** unconfigured. If a restart-policy option is offered, select **Always**, matching the working deployment.

If restoring an existing device, open **Environment Variables → Edit**, enter the key and complete value from step 2, and click **Configure**. For a fresh device, leave the environment-variable list empty for now.

## 5. Paste the startup command and deploy

Open **Command → Edit**. Use **Manual Edit**, not **Bulk Edit**: Bulk Edit treats each line as a separate argument.

Fill the command fields as follows. Do not type extra quotes around these fields:

| Field | What to paste |
|---|---|
| Command | `/bin/bash` |
| First argument, using **Add Argument** | `-c` |
| Second argument, using **Add Argument** again | The entire multiline block below, in this single field |

```bash
set -eu
umask 077
mkdir -p /etc/earnapp
wget -q --timeout=30 --tries=1 https://cdn-earnapp.b-cdn.net/static/earnapp-x64-1.665.73 -O /tmp/earnapp
chmod 755 /tmp/earnapp
/tmp/earnapp --version
if [ -n "${EARNAPP_UUID:-}" ]; then
  mv /tmp/earnapp /usr/bin/earnapp
  printf '%s' "$EARNAPP_UUID" > /etc/earnapp/uuid
  /usr/bin/earnapp start
else
  /tmp/earnapp install --auto
fi
/usr/bin/earnapp showid
exec /usr/bin/earnapp run --verbose
```

The command stops on a failed shell step, creates the required directory, downloads and identifies the tested client, and either restores your saved device ID or initializes a fresh device. It prints the ID and runs EarnApp as the container's main process. The first-time `--auto` installer accepts the provider's terms; use it only for an account and installation you are authorized to operate.

Click **Configure**. Continue through **Networking** and **Health Probes & Logging** with the container gateway, probes, and external logging disabled. This client makes outbound connections; it does not need a public web server.

Review the selected organization, image, command, CPU, memory, and replica count before clicking the final **Deploy** button. If the deployment finishes preparing but shows **Stopped**, click **Start** on its group page. Creating a group and starting it are distinct steps.

Check the price shown in the wizard. Published prices for this allocation were **$0.005 per running hour** when verified. The [announced September 12, 2026 change](https://blog.salad.com/saladcloud-price-changes-september-2026/) makes it **$0.006 per running hour** because the CPU price increases while RAM pricing stays unchanged. Use the current portal quote when following this guide later.

## 6. Link the device and save its ID

Wait for a worker to appear under **Instances**, then open **Container Logs**. Allocation and image download can take time; an empty instance list is not evidence that EarnApp has started.

Look for the client version, registration result, and device ID. A fresh installation prints a link beginning `https://earnapp.com/r/` followed by its generated `sdk-node-...` ID.

If the logs say **Failed registration**, do not treat `enabled` or a running process as a successful provider connection. In the isolated verification, the real client returned `enabled` even with networking disabled and registration failing. Resolve the reported connection error and check registration and the provider account separately.

1. Open that exact link in the browser where you signed into the intended EarnApp account.
2. Confirm the page says **Device successfully linked**.
3. Open the [EarnApp device list](https://earnapp.com/dashboard/me/passive-income) and match the ID. The list may display only its ending; click the device for the full ID.
4. For a fresh device, immediately save its full ID outside the container. Also set **Salad group → Edit → Environment Variables → EARNAPP_UUID** to that ID and save. This can restart the worker; afterward, run `earnapp showid` in its Terminal and check that it exactly matches the saved ID.
5. Keep a copy of that ID with this guide. Salad replacement machines do not preserve the previous container's files. The saved environment variable makes future starts use the same identity.

For an already-linked restored device, confirm it appears in the correct account. If needed, open `https://earnapp.com/r/` followed by the complete saved device ID. Do not create or invent a new ID to recover an existing one.

## 7. Check whether it actually works

In Salad, open **Instances**, click the running machine, and open **Terminal**. This is a shell inside the cloud container; type the following there, not in your Mac's Terminal:

```bash
cat /etc/os-release
earnapp --version
sha256sum /usr/bin/earnapp
earnapp showid
earnapp status
ps -p 1 -o pid,etime,rss,comm
```

The verified deployment returned Ubuntu, the pinned client version, its saved device ID, **Current status: enabled**, and an `earnapp` process. These establish installation, identity, and a running process. They do not prove paid activity.

Measured SHA-256 of both the newly downloaded official binary and the running cloud binary:

```text
a5080f9eff9df9f59a2192ccafc344f06259bfffe2a0aee619d44c8cafbd8def
```

The checksum printed by `sha256sum` should match this value to reproduce the tested binary. A different checksum means the bytes differ; it does not establish why. Verify the source and version before describing it as the same tested client.

The authoritative money reading is the device's **Amount / Total earned** on EarnApp. Record that amount and the dashboard's update countdown, then compare a later refreshed report. EarnApp's [published hourly calculation](https://help.earnapp.com/hc/en-us/articles/38191916327441--What-are-the-EarnApp-rates-How-are-they-calculated) credits qualifying active usage, not all process uptime.

Measured during the earlier US run: an early report showed zero, and a later report credited **$0.006 with 27 minutes 18 seconds of usage**. This credit must not be attributed to the restored worker at a different address. At the **September 7, 2026, 05:12 UTC** check, the dashboard still showed that earlier amount and address despite the restored worker's network activity. Additional credited earnings for the restored worker were unconfirmed.

That delay and attribution gap are why an unchanged timer or an early zero must not automatically stop or delete the deployment. The displayed monthly **Rate** is not money already earned. Network bytes also are not credited dollars. This guide reproduces the client setup; it does not establish repeatable revenue.

Leave the client running while measuring. The owner must explicitly request a shutdown or deletion; this guide does not define a zero-earnings cutoff.

## 8. Fix the failures encountered in this setup

| What you see | What to do |
|---|---|
| `/etc/earnapp/uuid: No such file or directory` | Restore the complete command from step 5, including `mkdir -p /etc/earnapp`. This fixed a measured startup crash. |
| `systemctl: not found` during first initialization | The first-time installer tries to configure system services. In this image, the foreground `earnapp run` command supplies the running process. Check the later registration result, current process, and provider report. A saved `EARNAPP_UUID` skips that service installer on later starts. |
| `earnapp showid` prints `undefined` | The device was not initialized and no saved ID was supplied. Follow the fresh-device path in steps 2–6. Measured offline: `showid` alone did not generate an ID. |
| `Failed registration` / `EAI_AGAIN` while status says `enabled` | Keep the exact error visible and investigate the reported network/DNS failure. A successful shell exit, `enabled`, or an existing UUID is not proof that registration succeeded. This combination was reproduced with networking deliberately disabled. |
| `name_conflict` / name already used | Choose an unused Salad group name. Keep the EarnApp device ID unchanged when restoring. |
| **Allocating** with no worker | Read **System Events** and the selected resources/countries. Keep the same deployment while investigating. If allocation is demonstrably stalled, restarting allocation means **Stop**, wait for **Stopped**, then **Start** on that same group; this is not deletion. |
| SSH says `Permission denied (publickey)` | Use Salad's connected browser **Terminal** as in step 7. This guide does not require SSH-key setup. |
| Dashboard time or money does not change yet | Refresh after its advertised reporting time and compare the device ID and IP. Keep readings marked pending when the provider has not reported. Do not infer failure from the absence of new stdout logs; the client's SDK log is binary. |
| An old error remains in Container Logs | Check its timestamp and machine. Historical errors can remain visible after a corrected worker starts. Verify the current instance rather than treating every old log as a current failure. |

If the pinned image or binary download is unavailable in the future, the file cannot replace that external service. Read the [official Linux installation instructions](https://help.earnapp.com/hc/en-us/articles/10261224561553-Installation-instructions-and-hardware-software-requirements), inspect the then-current official installer, and verify its client before updating the pinned command. Do not silently substitute an unknown image.

## Reference for restoring this project

| Item | Saved value |
|---|---|
| Salad organization | `cosmosgeeketh` |
| Salad project | `default` (shown as **Default**) |
| Current group | `earnapp-live`, displayed as **EarnApp** |
| Current group page | [Open EarnApp in Salad](https://portal.salad.com/organizations/cosmosgeeketh/projects/default/containers/earnapp-live) |
| EarnApp device ID | Use the complete saved ID in step 2 |

If that group is deleted, repeat this guide with an unused group name and the saved EarnApp device ID. The new Salad group and machine will have new IDs; the EarnApp identity can remain the same.

## Verification record

- **Live configuration check:** the image digest, client version, resources, saved device ID, and foreground startup were compared with the running Salad group. The guide's restore branch downloads to a temporary path and moves the binary into place; the deployed command downloads directly to that same final path. This difference is explicit, not a claim of byte-identical scripts.
- **Binary check:** a real download from the documented official URL matched the running cloud client's SHA-256 shown above. Its measured size was **49,072,804 bytes**.
- **Clean execution checks:** the complete command from this file was executed in the pinned image with `/etc/earnapp` initially absent, once without a saved ID and once with the saved ID. Networking was disabled. Only `wget` was replaced by a test fixture that copied the real downloaded binary to the requested path. The fresh branch generated an ID; the restore branch retained the supplied ID. Both created the required directory and executable and reached `earnapp` as the main process.
- **Limits of those checks:** registration failed as expected with networking disabled. Those executions prove the local initialization and launch flow, not a fresh successful online registration or earnings. The fresh installer and saved-ID start flows have separate earlier live Salad evidence; the combined guide command has not been deployed as another online Salad test.
- **Documentation check:** all shell blocks passed `bash -n`, and the browser command-field instructions were checked against the actual Salad wizard. The live deployment was left unchanged during this audit.

Portal references: [command fields](https://docs.salad.com/container-engine/how-to-guides/specifying-a-command), [browser terminal](https://docs.salad.com/container-engine/explanation/container-groups/ssh-and-terminal), [managing deployments](https://docs.salad.com/container-engine/how-to-guides/managing-deployments), [EarnApp CLI commands](https://help.earnapp.com/hc/en-us/articles/11987016499089-EarnApp-commands-for-Linux), [image source](https://github.com/fazalfarhan01/EarnApp-Docker).
