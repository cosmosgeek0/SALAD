# PacketStream

One `hyperlane/default/ps-test-us` group with ten stock PacketStream clients. The page is `/packetstream`; legacy `#ps1` links remain compatible. The cloud group is `ps-test-us`.

- [Setup and deployment](SETUP.md)
- [Native measurements and operations](MONITORING.md)
- [Automatic provider balance and dated traffic readings](PROVIDER.md)
- [Recovery and known mistakes](RECOVERY.md)
- [Actual source files](source/) and [checksums](source/SHA256SUMS)
- Shared page: [salad.cosmosgeek.org/#ps1](https://salad.cosmosgeek.org/#ps1)

The `source/` directory contains ordinary source files, and `source/SHA256SUMS` records their exact bytes. The repository-root `restore.py` installs them into a fresh runtime without relying on a Markdown extractor. From `Desktop/salad`, run `python3 restore.py PacketStream --to /path/to/empty/runtime` for an isolated rehearsal. Keep the package and `restore.py` together when copying this rebuild kit.

Credentials and old measurements are separate inputs. Source/configuration can be rebuilt; identical IPs, demand or earnings are not guaranteed. Existing live data and disabled local services are not changed by reorganizing these files.
