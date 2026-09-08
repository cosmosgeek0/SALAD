# EarnFM recovery

[Start here](../README.md) · [Setup](SETUP.md) · [Operations](OPERATIONS.md) · [Recovery](RECOVERY.md) · [Reference](REFERENCE.md)

Restore this **whole folder**, including its source, configuration and manifest. Use [Setup](SETUP.md) for a fresh Mac. No chat transcript, old Markdown file, or outside source repository is required.

Accounts, current credentials, account funding and the pinned vendor image remain external requirements. Historical measurements require a database backup. A rebuild cannot guarantee the same physical machines, IP addresses, traffic or earnings.

## Restore or archive existing state

If `target.json` is missing while a traffic database, SQLite sidecar, provider reading, or provider baseline survives, `deploy` refuses to create/adopt/update a group. Restore the matching `target.json` from a consistent backup, or **stop the existing recorder first** and archive the whole `~/.hg1/earnfm` directory before creating fresh state. The same archive procedure applies when local `target.json` belongs to a group that was deleted/recreated. This preserves its database, baseline and logs rather than mixing two deployments. Example for a discontinued deployment only:

```sh
launchctl bootout "gui/$(id -u)/com.cosmosgeek.earnfm-recorder"
python3 - <<'PY_ARCHIVE'
from pathlib import Path
from datetime import datetime, timezone
p = Path.home()/'.hg1/earnfm'
if p.exists():
    dest = p.with_name('earnfm-saved-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    p.rename(dest)
    print(dest)
PY_ARCHIVE
```

If `bootout` says the service does not exist, that is expected on a new machine. Do not archive current state merely to silence a mismatch; compare group IDs first.

If a recorder plist survived `bootout`, reload it with `launchctl bootstrap` as shown in [Setup](SETUP.md#dashboard-and-local-services); `kickstart` only applies to a loaded service.

## Backups

Run the backup commands from the EarnFM project folder. Working backup files go in this folder's `backups/` directory. Copy that backup and this whole project to independent storage afterward.

Keep this entire EarnFM folder, the pinned vendor image if long-term availability matters, the encrypted account-recovery material, and a consistent database backup. A reference to a lost path is not a backup.

Consistent local state backup while the recorder runs (SQLite's backup API includes committed WAL content):

```sh
python3 - <<'PY_BACKUP'
from pathlib import Path
from datetime import datetime, timezone
import sqlite3, shutil
src = Path.home()/'.hg1/earnfm'
dst = Path.cwd()/'backups'/('state-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
dst.mkdir(parents=True)
with sqlite3.connect('file:'+str(src/'traffic.sqlite3')+'?mode=ro', uri=True) as original:
    with sqlite3.connect(dst/'traffic.sqlite3') as backup:
        original.backup(backup)
for name in ('target.json', 'provider-baseline.json', 'provider.json'):
    p = src/name
    if p.exists(): shutil.copy2(p, dst/name)
print('Move this state backup and the EarnFM folder to independent storage:', dst)
PY_BACKUP
```

Restore that backup only while the recorder is stopped, into `~/.hg1/earnfm`, and only when its target group/account still matches. Do not restore a stale `.sqlite3-wal`, `.sqlite3-shm` or lock file with the backed-up database. If all historical data is lost, start a new measurement baseline; this project cannot reconstruct deleted per-second traffic without a backup.

Optional image preservation, with Docker installed:

```sh
mkdir -p backups
docker pull --platform linux/amd64 earnfm/earnfm-client@sha256:99a9feaa3dfab9e858012994fa1f922523f41b098e6b1cd9c9e9fca9286c3843
docker save --output "backups/earnfm-client-amd64.tar" earnfm/earnfm-client@sha256:99a9feaa3dfab9e858012994fa1f922523f41b098e6b1cd9c9e9fca9286c3843
```

`docker load --input <archive>` restores the local image. To use a private preserved registry image in Salad, an operator must publish it to an authorized registry and update image/registry access deliberately; a local tar file is not automatically available to Salad. Do not paste credentials into this markdown.
