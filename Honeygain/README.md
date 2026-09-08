# Honeygain

Ten independent Honeygain groups in `deathadder/default`, one stock client in each. The native wrapper handles failed clients and network rejection inside Salad.

- [Setup and deployment](SETUP.md)
- [Recording, credits and operations](MONITORING.md)
- [Recovery, known mistakes and image backup](RECOVERY.md)
- [Actual source files](source/) and [checksums](source/SHA256SUMS)
- Shared page: [salad.cosmosgeek.org/#hg1](https://salad.cosmosgeek.org/#hg1)

The `source/` directory contains ordinary source files, and `source/SHA256SUMS` records their exact bytes. The repository-root `restore.py` installs them into a fresh runtime without relying on a Markdown extractor. From `Desktop/salad`, run `python3 restore.py Honeygain --to /path/to/empty/runtime` for an isolated rehearsal. Keep the package and `restore.py` together when copying this rebuild kit.

Credentials and old measurements are separate inputs. Source/configuration can be rebuilt; identical IPs, demand or earnings are not guaranteed. Existing live data and disabled local services are not changed by reorganizing these files.
