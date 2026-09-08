# Run Pawns on Salad in the selected countries

[Start here](README.md) · [Build the image](rebuild.md) · [Troubleshooting](troubleshooting.md)

## Accounts and image

Have the published image reference or your own uploaded image from [Rebuild](rebuild.md), a SaladCloud account with billing and project access, and your ordinary Pawns account email and password. The browser's saved login does not supply a password to a container.

The measured deployment used the consumer SDK without a separate partner/developer API key. The old `iproyal/pawns-cli` image rejected the tested login with `authenticate user failed (please use SDK)`.

Open [cosmosgeeketh → Default → Container Groups](https://portal.salad.com/organizations/cosmosgeeketh/projects/default/containers), or the organization and project you are authorized to use.

If **pawns** already exists, open it first and record its current image, countries, resources and replica count. Update only its image and the liveness probe described below; preserve the other settings and credentials. If the portal requires stopping before editing, stop, save the changes and start the same group. Read back the saved configuration before checking its new instance. Deleting local files does not delete the cloud group.

## Container settings

For a new group, choose **Deploy a Container Group → Custom Container Group → Get Started**. These settings reproduce the configuration measured on September 7, 2026:

| Setting | Value |
|---|---|
| Cloud | **SaladCloud Community — CPU only** |
| Container Group Name | `pawns` |
| Image Name | The entire published digest from Rebuild, or your successfully uploaded image reference |
| Registry | **Public Registry** |
| CPU / memory | **1 vCPU / 1024 MiB** |
| Replicas | `1` |
| Allowed Countries | The group's currently approved countries |
| GPU | None |
| Command | **Empty / None Configured**; remove old CLI overrides |
| Container Gateway | Disabled; no public HTTP port is required |
| Liveness probe | Exec command and timing below |
| Startup/readiness probes and external logging | Disabled |
| Shared memory / extra disk | Default shared memory; no extra disk reservation |

Under **Environment Variables**, add:

| Key | Value |
|---|---|
| `PAWNS_EMAIL` | Your Pawns account email, without quotes or an `-email=` prefix |
| `PAWNS_PASSWORD` | Your Pawns account password, unchanged and without surrounding quotes |

Click **Configure** inside each editor to save it. Enter passwords only in the runtime configuration, never in source files, Markdown, build commands or image tags.

In **Allowed Countries → Edit**, use the countries approved for this deployment. The current trial selected Great Britain (`country_codes: ["gb"]`). Preserve the live selection when updating the image. An empty list allows arbitrary countries. [Salad's country-setting reference](https://docs.salad.com/reference/saladcloud-api/container-groups/get-container-group).

The measured group used CPU batch priority and `restart_policy: "always"`. Retain that CPU-only/default restart configuration. Leaving Command empty runs the launcher in the image.

## Configure the supervisor health check

Under **Health Probes**, configure a **Liveness / Exec** probe. Its command arguments are `python3`, `/app/run.py`, and `--healthcheck`. This checks the supervisor's heartbeat file; the supervisor separately watches SDK state and provider evidence.

| Probe setting | Configured value |
|---|---|
| Initial delay | 30 seconds |
| Period | 10 seconds |
| Timeout | 3 seconds |
| Failure threshold | 3 |
| Success threshold | 1 |

The exact API configuration is:

```json
{"exec":{"command":["python3","/app/run.py","--healthcheck"]},"initial_delay_seconds":30,"period_seconds":10,"timeout_seconds":3,"failure_threshold":3,"success_threshold":1}
```

The Docker image also declares this health-check command. Docker health status alone does not restart a process; the configured Salad liveness probe performs that recovery. Keep `restart_policy: "always"` for process exits and session renewal.

Check the current cost estimate and country selection, enable autostart if offered, then click **Deploy**. Click **Start** if the prepared group is Stopped.

## Verify the current deployment

1. **Container:** in **pawns → Instances**, find the current instance marked **Running / Ready**. Preparation states do not prove the client has started.
2. **Client:** filter Container Logs using its current Machine ID, match the current instance ID where shown, and read entries after that instance started. Refresh the query. A successful startup produced:

```text
PAWNS_LOGIN {"...":"...","state":"authenticated"}
PAWNS_SDK {"happened_at":"...","name":"starting","parameters":{}}
PAWNS_SDK {"happened_at":"...","name":"running","parameters":{}}
```

Read later messages too: a later `not_running` changes the SDK state. Repeated `PAWNS_SAMPLE` records carry the last callback state; they are not new SDK confirmations of paid traffic.

3. **Country and IP:** open that instance's **Terminal**, wait for **Successfully Connected**, then run:

```sh
curl -fsS --max-time 15 https://ipinfo.io/json
```

Compare its `country` with the group's approved country list, and note its `ip`. This lookup runs inside the container; the Mac's IP and Salad's SSH relay address are not the worker's sharing IP.

4. **Provider:** open [Pawns → Internet Sharing](https://dashboard.pawns.app/internet-sharing), click **Refresh**, and find that same IP marked **Active**. Its device name is **windows**, reflecting the SDK used. Old devices may remain Inactive.

If the observed country is outside the approved list, investigate the placement and correct the group with its country-trial owner before declaring success. Never substitute an old IP, screenshot or successful log for the current instance.

5. **Recording:** on [the Pawns page](https://salad.cosmosgeek.org/#pawns), check that the current row's freshness advances, its country/IP matches this instance, and provider values carry an observation time. The collector requires fresh native running state and a fresh provider observation of the matching IP before marking the client Connected. Provider sold traffic and sharing amounts have account scope; they are not per-worker profit measurements. The row's recorded time sums saved valid intervals and excludes gaps.

## Stop or resume

Open **pawns → Stop** and wait for **Stopped** with no running instances. Closing the browser or Docker Desktop does not stop the cloud workload. Keep the stopped group to reuse its settings, and choose **Start** when needed.
