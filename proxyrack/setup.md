# PR setup

[Start here](README.md) · Next: [Deployment](deployment.md)

## 1. Prerequisites and account access

Use an account authorized to manage the Salad organization `ssh1`, with a project named `default` and sufficient prepaid credit. If the organization or project was also deleted, recreate those exact slugs in the Salad portal first. The included program is scoped to them; using a different organization requires changing its API base and portal URLs together. The original experiment used **$5**, with no automatic recharge added by this work. Ten desired replicas must fit the organization's quota. The portal was observed counting **stopped replicas too**; if old test groups occupy the allowance, explicitly retire those known groups in the portal before a fresh deployment. The commands below never delete unrelated groups or add credit.

Required local tools: Python **3.9 or later** with its standard library, `curl`, and Apple's Swift compiler (`xcrun swiftc`) to rebuild the Keychain helper. If absent, install Apple's Command Line Tools first, then return after installation completes:

```bash
xcode-select --install
```

Check tools:

```bash
python3 --version
curl --version
xcrun --find swiftc
```

Credentials:

| Credential | Obtain from | Keychain service | Where used |
|---|---|---|---|
| Salad API key | Authorized Salad account/API-key settings | `salad-bandwidth-api` | Local deployment and log/inventory reader only |
| ProxyRack Peer API key | [Peer API page](https://peer.proxyrack.com/api-doc) in the owning account | `proxyrack-peer-api` | Local provider reader and Salad `PR_API_KEY` environment variable for replica self-registration |

Both Keychain items use the current macOS username as the account. Do not paste keys into source files, Markdown, command arguments, shell history, screenshots, or log output. A worker does **not** receive the Salad API key. It uses Salad's local metadata service to reallocate itself. The ProxyRack key reaches the worker for registration and provider checks. The supervisor removes it from the native child’s environment and sends it to the provider through curl stdin, not command arguments or logs. Authorized Salad administrators can still access the configured environment.

## 2. Install the included source files

Keep the whole folder at `~/Desktop/salad/proxyrack`. If stored elsewhere, change the `cd` path. This command checks every source checksum before copying into Application Support. It refuses to overwrite a different installed file; a surviving shared dashboard must be compared before replacing its files. For inspection only, set `root` to a staging directory inside this project folder instead of the live installation.

```bash
cd "$HOME/Desktop/salad/proxyrack"
python3 - <<'PY_INSTALL'
from pathlib import Path
import hashlib
import os

os.umask(0o077)
source = Path.cwd()
root = Path.home() / "Library/Application Support/Salad Bandwidth Dashboard"
expected = {
    "proxyrack.py", "pr-worker.js", "dashboard/__init__.py", "dashboard/native_network.py",
    "scripts/keychain-store.swift", "dashboard/pr_recovery_server.py",
    "dashboard/static/proxyrack.html", "dashboard/static/ps1.js",
}
entries = [line.split(None, 1) for line in (source / "SHA256SUMS").read_text().splitlines() if line.strip()]
if len(entries) != len(expected) or {name for _, name in entries} != expected:
    raise SystemExit("Missing, duplicate, or unexpected source files in SHA256SUMS")
ready = []
for checksum, name in entries:
    body = (source / name).read_bytes()
    if hashlib.sha256(body).hexdigest() != checksum:
        raise SystemExit("Source checksum mismatch: " + name)
    target = root / name
    if target.exists() and target.read_bytes() != body:
        raise SystemExit("Existing file differs; stage and compare before replacing: " + str(target))
    ready.append((target, body))
for target, body in ready:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
print("Installed", len(ready), "files into", root)
PY_INSTALL
```

Compile the included Keychain helper. Skip compilation if the existing helper works and you are recovering only the recorder. Rebuilding a helper can cause macOS Keychain to ask for permission again; allow the trusted local helper for these specific items when prompted.

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
mkdir -p .runtime
chmod 700 .runtime
xcrun swiftc scripts/keychain-store.swift -o .runtime/keychain-store
chmod 700 .runtime/keychain-store
```

## 3. Store the keys securely

The command uses hidden terminal input and passes each key to the helper through stdin. Existing usable Keychain items are retained; missing items are requested. It never prints the key.

```bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
python3 - <<'PY_KEYS'
from pathlib import Path
import getpass
import subprocess

helper = Path.cwd() / ".runtime/keychain-store"
account = getpass.getuser()
for service, label in (("salad-bandwidth-api", "Salad API key"),
                       ("proxyrack-peer-api", "ProxyRack Peer API key")):
    args = [str(helper), "--service", service, "--account", account]
    result = subprocess.run(args + ["--read"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode == 0:
        print(label + ": existing Keychain item available")
        continue
    key = getpass.getpass(label + " (hidden): ").strip()
    if not key:
        raise SystemExit("Empty key; nothing stored")
    subprocess.run(args, input=key.encode(), check=True)
    del key
    subprocess.run(args + ["--read"], stdout=subprocess.DEVNULL, check=True)
    print(label + ": saved and readable")
PY_KEYS
```

If an existing item contains an obsolete key, update that named item through Keychain Access or rerun the helper with hidden stdin for that service. Never use the helper's `--read` mode directly in a visible terminal without redirecting/capturing its stdout.

## Linux production

The existing Mumbai runtime uses `/opt/salad/.runtime/keychain-store`, with the same `--read --service NAME --account USER` interface. The recorder runs as `salad`; its default data path is `/home/salad/.hg1/proxyrack`. Linux secret storage, the service manager, AWS connection and public hostname are supplied by the shared [Website recovery kit](../Website/README.md), not by the macOS Swift helper.

`PR_KEYCHAIN_HELPER` selects an existing compatible helper and `PR_DATA_DIR` selects the recording directory. A normal installation locates the helper at `.runtime/keychain-store` beside `proxyrack.py`. Copy both `proxyrack.py` and `pr-worker.js` together. Do not replace a production Linux helper with the macOS binary or activate a second Mac recorder.

The isolated shared UI imports `proxyrack.public_snapshot()` for `/api/proxyrack`. Its Website service unit must include the read-only bind `/opt/salad/proxyrack.py:/run/salad-ui-code/proxyrack.py`. Existing `HOME=/home/salad`, the shared `dashboard.native_network` bind and read access to the published PR data supply the remaining read-only dependencies; the UI does not need the worker file or key helper.
