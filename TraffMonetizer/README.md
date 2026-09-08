# bandwidth reel — TraffMonetizer (TM)

This folder is the complete, editable recovery package for the ten-worker TM deployment in Salad organization **ssh4**. It replaces the former single-file `traffmonetizer.md`. Keep a copy of the **whole folder** on separate storage.

The verified program source is in ordinary files under [source/](source/). No code has to be extracted from Markdown, and no file from the old `salad-bandwidth-stack/traffmonetizer` directory is needed by this recovery package.

## Start here

1. [SETUP.md](SETUP.md) — prerequisites, copy the source to the runtime location, and restore credentials.
2. [DEPLOYMENT.md](DEPLOYMENT.md) — exact cloud configuration, reuse a surviving group or create ten workers, and rebuild the image if needed.
3. [MONITORING.md](MONITORING.md) — start the recorder and page, install background services, and interpret traffic versus earnings.
4. [RECOVERY.md](RECOVERY.md) — replacement policy, error diagnosis, stopping cloud charges, and database backups.
5. [VERIFICATION.md](VERIFICATION.md) — independent checks, measured recovery timings, sources, and what reproduction can and cannot promise.

The current worker and recorder use telemetry schema **2**. The group’s command override supplies the worker; the pinned image entrypoint contains an older policy. Follow [DEPLOYMENT.md](DEPLOYMENT.md) to preserve the override, and verify the actual instance versions after each update.

Version **8** replaces clients for process exits, accumulated connection failures or missing native replies. Healthy connected clients keep running with zero payload; idle time and earnings are observations, not replacement triggers. See [RECOVERY.md](RECOVERY.md) for the exact thresholds.

**This reproduces the source, launch configuration, measurement formulas and declared recovery behavior. It does not guarantee identical future traffic, earnings, machine assignments, or deleted historical data.** The package contains no real API keys, application tokens, sessions or passwords; account access is restored separately.

## Folder contents

```text
TraffMonetizer/
  README.md
  SETUP.md
  DEPLOYMENT.md
  MONITORING.md
  RECOVERY.md
  VERIFICATION.md
  tests/
    test_worker.py
  source/
    SHA256SUMS
    recovery-server.py
    traffmonetizer/
      Dockerfile
      worker.py
      control.py
      observer.py
    dashboard/
      traffmonetizer.py
      static/traffmonetizer.html
    scripts/
      keychain-store.swift
```

Verify the source before using it:

```bash
cd "$HOME/Desktop/salad/TraffMonetizer/source"
shasum -a 256 -c SHA256SUMS
```

The included worker regression checks run from the protocol folder, as shown in [VERIFICATION.md](VERIFICATION.md#healthy-idle-correction--2026-09-07). They simulate client failures and idle periods without cloud access.

All editable TM files belong here. Production recording runs on AWS Mumbai: `/opt/salad/traffmonetizer`, data `/home/salad/.hg1/traffmonetizer`, and `salad-traffmonetizer.service`. The retired Mac runtime and Keychain instructions remain for recovery; keep disabled Mac jobs disabled while AWS owns recording. Shared website changes stay with its current owner.

The included standalone recovery page covers **TM only**. Recreating the other providers and the shared nine-tab interface is outside this package. The cloud worker’s self-reallocation does not require the Mac to stay on; monitoring requires an online recorder host, currently AWS.
