# Deploy or reconnect to RP

For the preserved local recorder and page, use macOS with Python 3.9 or newer, `curl`, and Apple Command Line Tools (`xcrun swiftc`). Node is needed only for the optional local syntax check; the cloud image already has Node. Docker is optional for saving/testing the image locally. The cloud control helper itself uses Python's standard library plus `curl` and can prompt for its Salad key on non-macOS systems, while the local recovery setup uses the included macOS Keychain helper. Production Linux uses the compatible credential adapter and systemd units in the sibling Website package.

Start in this package's root directory and verify all included files:

```bash
cd "$HOME/Desktop/salad/repocket"
shasum -a 256 -c SHA256SUMS
```

The create recipe below is the captured US setup. A separate country experiment changed the live group to GB on 2026-09-07; later placements can differ. `inspect` intentionally refuses a configuration that differs from the captured recipe. Read back the current group and preserve the experiment; do not recreate it merely to make this check pass.

If you copied the package elsewhere, use that location. The source is already in real files; there is no Markdown extractor to run.

1. Save the **Salad API key** in Keychain for the recorder. The included script compiles the included Swift helper and reads the key with hidden input:

```bash
bash scripts/dashboard-configure-keychain.sh
```

Use a Salad account key that can access `ssh2/default`, read logs/inventory and manage this group. Obtain/recover it through the Salad account's API-key controls. Existing local storage uses Keychain service `salad-bandwidth-api`, account equal to the operating-system username. Run setup in the foreground with the login Keychain unlocked. When reusing an old entry, macOS may ask you to authorize the newly compiled helper; resolve that prompt before starting a background recorder. A successful compile alone does not establish permission to read an existing entry. The disposable new-entry test passed, but a fresh helper's read of the old live entry timed out during verification; the live recovery check used the existing authorized build of the same helper source. Do not run the helper's `--read` command directly into a visible terminal: it emits the key. Repocket's **Docker key is a different credential**, obtained from the logged-in [Repocket bandwidth page](https://repocket.com/dashboard/share-internet). The page labels it “Use this API key with Docker.” Use the Repocket account email, not an assumed Salad email.

2. Inspect the non-secret create plan:

```bash
python3 -B restore-control.py plan > deployment-plan.json
```

The plan contains placeholder Repocket values and the encoded worker, never real credentials. The helper constructs this exact command array: `/bin/sh`, `-c`, the base64-decoding shell command, `policy-start`, then 900-character pieces of the base64 source. The decoded file is `/tmp/repocket-start.js`; it runs `/usr/local/bin/node`. Do not paste each JavaScript line into Salad's command editor or change quoting. The helper validates command sizes and the worker checksum.

3. Choose the case that matches the cloud state.

**If this RP group still exists:**

```bash
python3 -B restore-control.py inspect
python3 -B restore-control.py attach
```

`inspect` compares the remote image, command and core configuration to this edition without printing credentials. `attach` records the current group UUID locally; it does not redeploy or restart it. A new local recorder begins capture at attachment time. An existing capture cursor/history is preserved. If configuration differs, stop and inspect that difference; do not overwrite a newer working deployment from an old guide.

**If the group was deleted:**

Make sure `ssh2` and project `default` exist, the organization has enough prepaid credit and quota for ten CPU replicas, and you can access the Repocket account. This guide assumes those account resources already exist. Then:

```bash
python3 -B restore-control.py create
python3 -B restore-control.py start
python3 -B restore-control.py inspect
```

`create` requires a confirmed HTTP 404 for `rp-test-us`, prompts for the Repocket email and Docker key, and sends them directly to Salad over HTTPS. It does not save those credentials to a local file. `start` is explicit because creation alone does not establish that containers are running. A newly created group gets a **new UUID and version**, not the historical UUID/version in [Worker behavior](WORKER.md). The helper records the returned values. [Create API](https://docs.salad.com/reference/saladcloud-api/container-groups/create-container-group), [start API](https://docs.salad.com/reference/saladcloud-api/container-groups/start-container-group).

If a create/start request times out, run `inspect` before retrying: the provider may have accepted it. If local `~/.hg1/repocket/deployment.json` belongs to a deleted group, move that entire local RP directory to a backup before creating another group; do not mix two groups' measurements. The helper refuses to overwrite an existing local deployment record during creation.

**Stop cloud spending when required:**

```bash
python3 -B restore-control.py stop
python3 -B restore-control.py inspect
```

Wait for Salad to report the group stopped; an accepted stop is not immediate completion. The [Salad group page](https://portal.salad.com/organizations/ssh2/projects/default/containers/rp-test-us) also provides Stop. Closing the monitoring page or shutting down the Mac does **not** stop cloud containers. The original organization was funded with $5 and auto-recharge was off; this guide does not add funds, enable recharge, or guarantee that credit remains.
