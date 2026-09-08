# Grass on Salad

Start with [Setup](setup.md). Keep this entire folder together: the guides use the source files beside them. A source backup can rebuild the client; recovering old measurements also requires the SQLite database and its cursor.

| Guide | Purpose |
|---|---|
| [Setup](setup.md) | Create the container, sign in once, and install automatic login restoration and recovery. |
| [Monitoring](monitoring.md) | Understand native health, traffic, Network Points, and the AWS recorder. |
| [Recovery](recovery.md) | Read the recovery policy, repair sign-in, rebuild, or stop hosting. |

| Source | Active role |
|---|---|
| `deploy.py` | Creates/reads the pinned Grass group; `repair` packages the native files and saves the login privately in Salad. |
| `bootstrap.sh` | Installs TLS support, restores account login, and registers the native worker with the image's supervisor. |
| `worker.pl` | Checks the actual process and Grass device/IP acceptance, records counters and points, and restarts/reallocates failed clients. |
| `recorder.py` | Collects native Salad logs into SQLite and publishes the shared dashboard feed. |
| `data/` | Retained former Mac measurements. Production history is on AWS. |

The current shared page is [Grass](https://salad.cosmosgeek.org/#grass). AWS runs its recorder; the Mac recorder stays disabled. See [Website recovery](../Website/README.md) for the shared site and production host.

The native worker runs inside each Salad container. It continues when the Mac is asleep. Traffic, provider acceptance, and account points are separate measurements; no cash conversion or earnings estimate is invented.
