# Deployment

Complete [SETUP.md](SETUP.md) first. Run the commands below from `~/Library/Application Support/TraffMonetizer Recovery/`.

## Cloud identity and launch configuration

| Item | Verified configuration |
|---|---|
| Provider label | `TM` — TraffMonetizer |
| Salad organization / project | `ssh4` / `default` |
| Group resource name | `tm-test-us` |
| Group display name | `TM` |
| Existing group ID | `1a64168c-d295-4b6c-9d4c-928303dfebf2` |
| Replicas | `10` |
| Original deployment country filter | `us`; the concurrent country trial changed the surviving group to `gb` on 7 September 2026. Preserve/read its current filter during updates. |
| Resources per worker | 1 vCPU, 1024 MiB RAM, no GPU |
| Priority | `batch` (Lowest in the portal) |
| Restart policy | `always` |
| Reliability worker group version | `8`; verify all actual instance versions, not only this group number |
| Autostart flag at this snapshot | `false`; the group was explicitly started and was running |
| Custom startup/liveness/readiness probes | None configured |
| Worker secret environment variable | `TM_TOKEN` |
| Device name | `ssh4-tm-` plus the Salad machine ID |
| Public inbound server/gateway | Not required for TM |

Portal: <https://portal.salad.com/organizations/ssh4/projects/default/containers/tm-test-us>

Current wrapper image:

```text
docker.io/cosmosgeek0/salad-bandwidth-stack@sha256:d75e26d28fbb9352829eb41440a38b59d5f9d3ecb4967cc0414bb3bbc50f1c2c
```

Pinned, unchanged vendor client image:

```text
traffmonetizer/cli_v2@sha256:6dbf8e75cc93e25131e2e701b1d478b3ccbf89212636b08d629621c270f0c966
```

Pinned Python base:

```text
python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
```

**The current command override is essential.** The wrapper image contains an earlier worker. Current Salad configuration starts `/bin/sh -c`, decodes the worker source from command arguments into `/tmp/tm-worker.py`, and executes that file. Merely restoring the image with its default entrypoint restores an older recovery policy.

The current [worker source](source/traffmonetizer/worker.py) has this SHA-256. After an update, decode the actual command and compare it before declaring deployment complete:

```text
9abf2983254dc09ee2a8bc8c37c8e477b1482f47eac0fc27181661e428c541ef
```

The deployment command below reconstructs that override automatically. Each base64 argument is at most 900 characters, matching the existing command layout. Base64 here transports **public source code**, not a secret.

## Deploy or reconnect

First check the Salad portal. If `tm-test-us` survived, **reuse it**. Deleting local files does not stop cloud billing or delete containers. Do not create a second ten-worker group.

The script below is for loss of the local TM database/configuration. It refuses to run if a local deployment record or database already exists. It captures a **new** account measurement baseline; it cannot recover an old earnings baseline from memory. The existing cloud group is read and left unchanged. Only when absent does it create the documented group, initially stopped, record the baseline, and start it.

It needs all three credentials from [SETUP.md](SETUP.md#credentials) for complete monitoring. The initial baseline is captured from account APIs, not from an assumed `$0.0268`, `$0`, or a dashboard balance rounded by hand. The current `control.py create` command also captures a fresh provider baseline, installs the actual worker command, creates the group stopped, and starts only after recording that baseline. It refuses an existing group.

```bash
python3 - <<'PY_DEPLOY'
from pathlib import Path
from datetime import datetime,timezone
import base64,json,os,sys
sys.path.insert(0,"traffmonetizer")
from control import api,keychain,DATA,GROUP_PATH,IMAGE
from observer import provider_request

record=DATA/"deployment.json"
assert not record.exists() and not (DATA/"traffic.sqlite3").exists(), "Existing history: use MONITORING.md, do not reset it"
DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
os.umask(0o077)
worker=Path("traffmonetizer/worker.py").read_bytes()
encoded=base64.b64encode(worker).decode()
command=["/bin/sh","-c",'umask 077; printf "%s" "$@" | base64 -d > /tmp/tm-worker.py; exec python3 -u /tmp/tm-worker.py',"policy-start"]
command.extend(encoded[i:i+900] for i in range(0,len(encoded),900))
image=os.environ.get("TM_IMAGE",IMAGE)
items=api("/projects/default/containers").get("items",[])
exists=any(g["name"]=="tm-test-us" for g in items)
group=api(GROUP_PATH) if exists else None
if exists:
    print("Reusing existing group:",group["id"],"version",group["version"],"replicas",group["replicas"])
    if group["replicas"]!=10:
        raise SystemExit("Existing replica count differs. Inspect it in Salad before making an intentional scale change.")
else:
    payload={"name":"tm-test-us","display_name":"TM","replicas":10,
        "autostart_policy":False,"restart_policy":"always","country_codes":["us"],
        "container":{"image":image,"command":command,"priority":"batch",
            "resources":{"cpu":1,"memory":1024},
            "environment_variables":{"TM_TOKEN":keychain("salad-traffmonetizer-token")}}}
    try:
        group=api("/projects/default/containers","POST",payload)
    except RuntimeError:
        group=api(GROUP_PATH)
        c=group.get("container",{})
        assert group.get("replicas")==10 and c.get("image")==image and c.get("command")==command
        assert c.get("environment_variables",{}).get("TM_TOKEN")==payload["container"]["environment_variables"]["TM_TOKEN"]
        print("Create response was uncertain; matching group found, no duplicate created")

# Account snapshots and wall-clock boundary are only seconds apart; for an
# already-running group, the baseline is a new observation, not old history.
began=datetime.now(timezone.utc)
balance=provider_request("/api/app_user/get_balance")["data"]
days=provider_request("/api/dashboard/get_graph_stat?period=month")
finished=datetime.now(timezone.utc)
assert began.date()==finished.date(), "UTC date changed; rerun baseline capture after inspecting the stopped group"
selected=[d for d in days if d["date"]>=began.date().isoformat()]
saved={"organization":"ssh4","project":"default","group":"tm-test-us",
    "group_id":group["id"],"image":group["container"]["image"],
    "display_name":"TM","desired_replicas":10,"started_at":began.isoformat(),
    "measurement_started_ms":int(finished.timestamp()*1000),
    "provider_baseline_usd":balance["balance"],
    "provider_baseline_bytes":sum(d["traffic"] for d in selected),
    "provider_baseline_earned_usd":sum(d["earning"] for d in selected),
    "provider_baseline_source":"Fresh account API readings during recovery; earlier history unavailable"}
with record.open("x") as f:
    json.dump(saved,f,indent=2)
record.chmod(0o600)
if not exists:
    api(GROUP_PATH+"/start","POST")
    print("Start requested for ten TM replicas")
else:
    print("Cloud state left unchanged. If the surviving group is stopped, start it explicitly in Salad.")
print("New observation baseline saved; run the observer next")
PY_DEPLOY
```

If an API call times out, read back the group before retrying a creation. If a stopped group was created but baseline authentication failed, fix the credentials, rerun the baseline step against that existing group, then start it in the portal. The script deliberately leaves surviving groups' runtime/image/command unchanged.

**If the custom registry image is unavailable:** rebuild from the [Dockerfile](source/traffmonetizer/Dockerfile) and [worker source](source/traffmonetizer/worker.py), using a registry you control. The original vendor binary must still be available.

```bash
# Replace the example registry username before executing.
export TM_IMAGE='YOUR_DOCKERHUB_USERNAME/tm-recovery:20260907'
docker login
docker buildx version
docker buildx build --load --platform linux/amd64 -t "$TM_IMAGE" -f traffmonetizer/Dockerfile traffmonetizer
docker push "$TM_IMAGE"
# Set TM_IMAGE to the repository@sha256:digest printed by the successful push
# before running PY_DEPLOY. Keep the command override; it is safe with either image.
```

Use Docker Desktop’s BuildKit/buildx builder. If `docker buildx version` fails, restore the Docker Desktop CLI plugins before building. In the isolated audit, hiding those plugins selected the legacy builder, which failed with `failed to export image: NotFound: content digest ... not found`; the explicit BuildKit build succeeded. If using a temporary `DOCKER_CONFIG`, it must retain access to the installed CLI plugins.

A Docker Desktop credential-helper hang was resolved by using the existing `docker-credential-osxkeychain` helper in a temporary Docker config, not by putting a registry password in the recovery folder. Rebuilt image digests need not equal the historical image digest.

Continue with [MONITORING.md](MONITORING.md).

## Updating the existing worker

After restoring source and credentials on the designated recorder host, `python3 -B traffmonetizer/control.py update` applies the source command to the existing bound group. It preserves the experiment baseline and writes the worker hash into deployment metadata. Install the updated recorder before publishing schema-2 workers so both old and new sample formats are understood during rollout.

A command update restarts the replicas. Check actual per-instance versions and fresh native replies afterward; a changed group version alone is not completion. The schema-2 batch contains 15 values per sample, including monotonic status/statistics ages, plus policy metadata. The recorder still accepts the historical 13-value format. Keep exactly ten desired replicas for this test.
