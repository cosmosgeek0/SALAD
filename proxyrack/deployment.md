# PR deployment

[Start here](README.md) · Previous: [Setup](setup.md) · Next: [Monitoring](monitoring.md)

## 1. Initialize local deployment identity

The original program expects `deployment.json` to exist, so **do not skip this step**. It creates the directory, generates a fresh namespace for a new deployment, or recovers identity from an existing `pr` group. It only reads Salad and writes local metadata; it does not create, update, restart, or delete containers.

For this snapshot the historical group ID was `ab9fd890-55b8-42ab-86ac-957fe8ce3d87`, and its namespace was `bdf752e1281d57a77633eeeb4044b210`. These are identity values, not credentials. Do not force them onto a new group; adopt the values actually returned by Salad.

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 -B - <<'PY_INIT'
from datetime import datetime, timezone
import json
import os
import secrets
import proxyrack as pr

os.umask(0o077)
pr.DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
path = pr.DATA / "deployment.json"
api = pr.salad_api()
items = api(pr.GROUPS).get("items", [])
existing = next((g for g in items if g["name"] == "pr"), None)
if path.exists():
    config = json.loads(path.read_text())
    if config.get("name") != "pr" or config.get("replicas") != 10:
        raise SystemExit("Existing local manifest is not this PR deployment; inspect it before changing it")
    if existing is None and config.get("group_id"):
        raise SystemExit("Manifest belongs to a deleted group. Preserve its data, move ~/.hg1/proxyrack aside, then initialize a new run")
    if existing and config.get("group_id") != existing["id"]:
        raise SystemExit("Local and cloud group IDs disagree; inspect before proceeding")
    print("Existing local manifest retained")
else:
    config = {
        "organization": "ssh1", "project": "default", "name": "pr", "replicas": 10,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "namespace": secrets.token_hex(16), "image": pr.IMAGE,
    }
    if existing:
        group = api(pr.GROUPS + "/pr")
        namespace = group["container"].get("environment_variables", {}).get("PR_NAMESPACE")
        if not namespace or group["container"]["image"] != pr.IMAGE or group["replicas"] != 10:
            raise SystemExit("Existing PR has a different configuration; inspect it, do not overwrite it")
        config.update(group_id=group["id"], namespace=namespace, created_at=group["create_time"])
        print("Adopting existing PR; its running configuration is unchanged")
    else:
        print("Initialized a new PR manifest; cloud deployment has not started")
    pr.save(path, config)
print("Manifest:", path)
PY_INIT
```

A replica's provider ID is `SHA256(PR_NAMESPACE + ":" + SALAD_INSTANCE_ID).hexdigest().upper()`. This gives each instance a separate 64-character provider ID without maintaining ten group configurations. Replacements get new IDs; preserve earlier provider devices for accounting. Separate Salad nodes can still share a public IP: compare provider-reported IPs before assuming ten distinct exits.

### Surviving cloud group with a replaced ProxyRack key

If the original Peer API key was lost/revoked and you obtained a replacement, saving it in Keychain fixes local reads only. Neither `deploy` nor `update` replaces an existing group's `PR_API_KEY`. After adopting the surviving group in step 1, use this explicit synchronization command. It compares the keys without printing them and updates only that environment value if different. This is an intentional cloud change and can roll replicas. Skip it when no group exists; fresh `deploy` already supplies the current key.

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 -B - <<'PY_KEY_SYNC'
import getpass
import subprocess
import proxyrack as pr

api = pr.salad_api()
config = pr.configuration()
group = api(pr.GROUPS + "/pr")
environment = dict(group["container"].get("environment_variables", {}))
if group["id"] != config.get("group_id") or environment.get("PR_NAMESPACE") != config["namespace"]:
    raise SystemExit("Cloud identity differs; no key update requested")
key = subprocess.check_output([
    str(pr.HELPER), "--read", "--service", "proxyrack-peer-api", "--account", getpass.getuser()
], text=True).strip()
if not key:
    raise SystemExit("Empty Keychain credential; no key update requested")
if environment.get("PR_API_KEY") == key:
    print("Cloud registration key already matches; no update needed")
else:
    environment["PR_API_KEY"] = key
    api(pr.GROUPS + "/pr", "PATCH", {"container": {"environment_variables": environment}})
    after = api(pr.GROUPS + "/pr")
    if after["container"]["environment_variables"].get("PR_API_KEY") != key:
        raise SystemExit("Cloud key update is not confirmed; inspect the group before proceeding")
    print("Cloud registration key updated; wait for the rollout and verify registration")
del key
PY_KEY_SYNC
```

## 2. Deploy one group with ten replicas

**Fresh deployment only:** this command starts paid Salad workloads using existing credit. It creates `pr`, waits for the initial preparing state, starts a stopped group, and saves its ID locally. No top-up or payment configuration is performed.

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 -B proxyrack.py deploy
python3 -B proxyrack.py status
```

For **local-only recovery of a surviving cloud group**, skip `deploy`; use `status` and start the recorder using [monitoring.md](monitoring.md). To intentionally apply the current worker to an existing matching group:

```bash
python3 -B proxyrack.py update
```

`update` changes the group's startup command and may roll its instances. It is not required merely to restore local monitoring. The pre-repair group was version **6**. Read the API result and current instance versions after each actual rollout; do not assume a version number from this document.

### Placement when rebuilding the current experiment

The September 7 live preflight returned `country_codes: ["de"]`; `update` preserves it. Fresh `deploy` retains the original US default. To reproduce the subsequently selected Germany placement on a newly created group, apply this explicit scoped change, then verify the actual assigned nodes. It can trigger another rollout; it is unnecessary when recovering an existing Germany group.

```bash
python3 -B - <<'PY_COUNTRY'
import proxyrack as pr
api = pr.salad_api()
group = api(pr.GROUPS + '/pr')
if group['id'] != pr.configuration()['group_id']:
    raise SystemExit('Group identity changed; no placement update requested')
if group.get('country_codes') != ['de']:
    api(pr.GROUPS + '/pr', 'PATCH', {'country_codes': ['de']})
after = api(pr.GROUPS + '/pr')
if after.get('country_codes') != ['de']:
    raise SystemExit('Germany placement was not confirmed')
print('PR country configuration verified: Germany')
PY_COUNTRY
```

Implementation details are in `pr-worker.js` and `command()`:

- `command()` transports the exact worker bytes as base64 chunks of at most 900 characters, within the verified 100-argument/1000-character envelope. The bootstrap writes `/tmp/pr-worker.js` and execs Node.
- The pinned vendor image supplies Node, curl and the tools needed by the official native client. The supervisor keeps the native child’s stdin pipe open.
- `update` preserves the group ID, namespace, key, resource settings and replica count. It adds the provider query start date and changes only the worker command/environment. Salad may roll the instances to apply it.
- Each worker emits its native version, run identity, minute samples, provider observations and recovery events. Verify the running instance version and fresh records after an update.

If creation returns HTTP 400, check the real portal error and replica allowance before retrying. If a create request times out, inspect the group list before repeating it. The initializer/deployer verifies identity rather than blindly creating another group. Legacy singleton manifests must be inspected and migrated separately; this program creates only the single `pr` group.
