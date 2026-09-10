# bandwidth reel

EarnApp was permanently retired on 10 September 2026 after account suspension. Do not install, deploy, record, or restore it. Historical instructions mentioning it are superseded.


Source, focused rebuild guides and safe configuration for the Salad bandwidth project.

The deployed website source was verified and published in [release 1c70638](https://github.com/cosmosgeek0/SALAD/commit/1c70638e8efbe337e27ba1c0c78212f3df365f82). This backup adds the protocol packages and reconstruction guides around that release. Unpublished Honeygain recovery-ledger changes and separate preview worktrees are excluded; they are not presented as deployed behavior.

The live dashboard is [salad.cosmosgeek.org](https://salad.cosmosgeek.org/). **For the website, AWS, Cloudflare, access or disaster recovery, start at [Website/README.md](Website/README.md).** It maps the live system, source, connections and rebuild steps. The Mac is the workspace; opening or restoring this repository does not start production services.

| Package | Entry point |
|---|---|
| Honeygain | [Honeygain/README.md](Honeygain/README.md) |
| PacketStream | [PacketStream/README.md](PacketStream/README.md) |
| Proxyrack | [proxyrack/README.md](proxyrack/README.md) |
| Repocket | [repocket/README.md](repocket/README.md) |
| EarnFM | [EarnFM/README.md](EarnFM/README.md) |
| Traffic Monetizer | [TraffMonetizer/README.md](TraffMonetizer/README.md) |
| Pawns.app | [pawns/README.md](pawns/README.md) |
| Grass | [grass/README.md](grass/README.md) |
| Mysterium | [mysterium/README.md](mysterium/README.md) |
| Shared website | [Website/README.md](Website/README.md) |

For the hosted website and all its recorder dependencies, restore the Website package from this repository root:

```sh
python3 restore.py Website --to /path/to/empty/runtime
```

The helper checks SHA-256 manifests before copying and refuses an existing different installation. Do not combine the production Website bundle with older protocol diagnostic bundles: some overlapping modules now differ because the website uses Linux isolation. Follow the other protocol folders' own cloud-client restore/setup guides, then bind the website recorders as documented in Website/SETUP.md.

Git backs up source, guides and safe configuration. Live `data/`, logs, runtime caches and credentials are excluded and remain where their owners put them. Preserve measurement databases separately using their documented backup procedure; a source checkout cannot recreate deleted history or guarantee the same traffic/earnings.

Read [AGENTS.md](AGENTS.md) before working. Combined-container experiments are a separate future task, not part of this reorganization.
