# bandwidth reel — PR

ProxyRack’s official native client runs in **one Salad group with ten replicas**: `ssh1/default/pr`, display name `PR`, batch priority, one CPU and 1024 MiB per replica. The live group was configured for Germany (`de`) when checked on September 7, 2026; this repair preserves that placement. The original deployment and fresh-create default use the US. The worker, recorder and recovery page are ordinary source files in this folder.

- [Setup and credentials](setup.md)
- [Deployment and recovery of identity](deployment.md)
- [Recording, website and measurements](monitoring.md)
- [Failure recovery and troubleshooting](troubleshooting.md)
- [Container supervisor](pr-worker.js) and [deployment/recorder program](proxyrack.py)
- [Source checksums](SHA256SUMS)

The live shared page is [salad.cosmosgeek.org/#proxyrack](https://salad.cosmosgeek.org/#proxyrack). Its recording host is the separate AWS Mumbai instance. Production PR code is `/opt/salad/proxyrack.py` and `/opt/salad/pr-worker.js`; its service is `salad-proxyrack.service`, its data is `/home/salad/.hg1/proxyrack`. The Mac’s retired recorders stay disabled.

Routine recovery runs **inside the container** using Salad IMDS. It handles detected process exits, failed startup, connection timeouts, a stopped/blocked native process and repeated provider-offline observations. Account quota/authentication problems use cooldowns rather than machine churn. Healthy connected peers stay running when traffic is low, absent or unverified. No traffic-floor or earnings-stall replacement policy is enabled.

Network MB means measured RX + TX divided by 1,000,000, including relaying and overhead. Provider counters and account balance are separate. The Peer bandwidth API’s physical unit has not yet been independently verified, so the page shows its original counter without a GB-to-MB assumption. No group or per-node dollar profit is inferred.

The base image is pinned:

`docker.io/proxyrack/pop@sha256:7de6719f37b31d5dd354f8cdd3ae601b4ed401832d0935ff460f968e0b6731bc`

The official native download and version URLs remain mutable upstream dependencies. Version 60 was observed during this work. Rebuilding requires funded Salad access, the provider account/key and continued availability of the image/download. Source recreates the configuration and behavior; it cannot guarantee the same IPs, traffic, earnings or deleted history.

Keep this **whole folder** together. `README.md` alone is not a backup of the source. Keep a separate consistent copy of the SQLite ledger and cursor if historical measurements matter. Credentials belong in the appropriate secret store, not this folder.
