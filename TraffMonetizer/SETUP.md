# Setup and credentials

Start with this guide on a clean recovery Mac. Keep the entire TraffMonetizer folder together.

## Prerequisites

This recovery package deliberately contains **no passwords, application token, API key, dashboard session, or payment information**. A new operator needs access to:

- The existing Salad account, organization `ssh4`, project `default`, sufficient credits, and a Salad API key authorized for that organization.
- The existing TraffMonetizer account and its **application token** from the dashboard. This is the token workers use.
- A signed-in TraffMonetizer **dashboard session** for the optional account earnings collector. It is different from the application token. The account APIs returned HTTP 401 when called with the application token.
- macOS with Python 3, `curl`, Xcode Command Line Tools/Swift, and Docker Desktop for the documented complete recovery path. The cloud worker itself is Linux/amd64. The recorder uses only Python's standard library; the credential helper uses macOS Keychain.
- Internet access to Salad, TraffMonetizer and the referenced container registries. If an upstream service or vendor binary disappears, this package cannot recreate that proprietary service or binary.

Losing the database loses local historical measurements. Losing account credentials requires recovering them through their respective services. The program source in [source/](source/) survives independently of the original repository.

## Copy the program into its runtime location

On the original Mac, preserve the existing services; do not start duplicate observers or a second server on port 8787. For a clean recovery, this command verifies the manifest, copies the eight source files, and refuses to overwrite an existing runtime directory. It does not contact cloud accounts or start containers. Change `source` only if this recovery folder was copied elsewhere.

```bash
python3 - <<'PY_COPY'
from pathlib import Path
import hashlib
source=Path.home()/"Desktop/salad/TraffMonetizer/source"
destination=Path.home()/"Library/Application Support/TraffMonetizer Recovery"
assert not destination.exists(), "Existing runtime: inspect it instead of overwriting"
entries=[]
for line in (source/"SHA256SUMS").read_text().splitlines():
    digest,relative=line.split("  ",1)
    path=Path(relative)
    assert not path.is_absolute() and ".." not in path.parts
    raw=(source/path).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==digest, "Checksum mismatch: "+relative
    entries.append((path,raw))
assert len(entries)==8 and len({str(p) for p,_ in entries})==8, "Incomplete source manifest"
for path,raw in entries:
    target=destination/path
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(raw)
(destination/"SHA256SUMS").write_bytes((source/"SHA256SUMS").read_bytes())
print("Copied",len(entries),"source files to",destination)
PY_COPY
cd "$HOME/Library/Application Support/TraffMonetizer Recovery"
```

Run subsequent setup, deployment and monitoring commands from that runtime directory. The editable master copy remains inside this Salad/TraffMonetizer folder. macOS launchd previously failed with `Operation not permitted` when the runtime lived under Desktop, so background services use Application Support.

## Credentials

Install Xcode Command Line Tools if `xcrun --find swiftc` is unavailable, then compile the included [Keychain helper source](source/scripts/keychain-store.swift):

```bash
mkdir -p .runtime
xcrun swiftc scripts/keychain-store.swift -o .runtime/keychain-store
```

The original Keychain service names are:

| Service | Value |
|---|---|
| `salad-bandwidth-api` | Salad API key |
| `salad-traffmonetizer-token` | TM application token, used by workers |
| `salad-traffmonetizer-session` | TM dashboard Bearer session token, without the `Bearer ` prefix |

The Keychain account is the current macOS username, obtained by `getpass.getuser()`. Existing entries may still work if only project files were lost. Recompiling the helper may cause macOS to request access to existing Keychain entries.

To save/re-enter the credentials, use hidden input; values go to the helper through stdin, not command arguments or source files:

```bash
python3 - <<'PY_KEYS'
import getpass,subprocess
from pathlib import Path
helper=Path.cwd()/".runtime/keychain-store"
for service,label in [
    ("salad-bandwidth-api","Salad API key"),
    ("salad-traffmonetizer-token","TM application token"),
    ("salad-traffmonetizer-session","TM dashboard session, without Bearer prefix"),
]:
    secret=getpass.getpass(label+": ").strip()
    if not secret:
        raise SystemExit("Empty input; this credential was not changed")
    subprocess.run([str(helper),"--service",service,"--account",getpass.getuser()],
                   input=secret,text=True,check=True,capture_output=True)
    print("Saved",service)
    secret=""
PY_KEYS
```

Obtain the application token from <https://app.traffmonetizer.com/dashboard>. For the account-session collector, sign into that same account, open browser Developer Tools → Network, reload the dashboard, select its `get_balance` request and inspect the **request Authorization header**. Copy only the value after `Bearer ` into the hidden prompt. Do not share it or save a browser HAR containing it. The site has also used local storage key `token`, but inspect the actual request if its frontend changes.

The collector uses two read-only account endpoints and refreshes the saved session when the response provides an Authorization header. Sessions can still expire. A provider 401/403 means reauthenticate and replace the **session** entry; it does not by itself mean the cloud workers' application token failed.

Continue with [DEPLOYMENT.md](DEPLOYMENT.md).
