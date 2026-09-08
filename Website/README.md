# Start here: the Salad website

The website is [salad.cosmosgeek.org](https://salad.cosmosgeek.org/). AWS Mumbai runs the website and recorders continuously. The Mac edits files and connects through AWS Session Manager. Salad runs the bandwidth clients on separate provider machines. Cloudflare supplies the hostname, tunnel and security-key login.

You do not need an old chat to find or manage these pieces.

| What you need to do | Read |
|---|---|
| Implement the current UI, historical-IP and speed requirements | [REQUIREMENTS.md](REQUIREMENTS.md) |
| Find AWS, Cloudflare, Salad groups and the exact connection command | [CONNECTIONS.md](CONNECTIONS.md) |
| Rebuild after losing the Mac, AWS host or Cloudflare configuration | [RECOVERY.md](RECOVERY.md) |
| Restore credentials and connect recorders to surviving/new Salad groups | [SETUP.md](SETUP.md) |
| Inspect the site, change a file or diagnose a broken page | [OPERATIONS.md](OPERATIONS.md) |
| Understand API routes, measurements, databases and history | [DATA.md](DATA.md) |
| See what was actually tested and the remaining limits | [VERIFICATION.md](VERIFICATION.md) |
| Read application and collector code | [source/](source/) and [checksums](source/SHA256SUMS) |
| Recreate Linux services, credential storage, IAM role and SSH access | [linux/](linux/) and [checksums](linux/SHA256SUMS) |

## First actions for a new task

1. Read the repository's [AGENTS.md](../AGENTS.md), this page, then the guide for the requested operation.
2. Open the public site with the owner's existing Cloudflare login and security key.
3. From the repository root, connect with `ssh -F Website/linux/ssh_config salad-mumbai`. [CONNECTIONS.md](CONNECTIONS.md#connect-from-a-mac) explains prerequisites and replacement-machine access.
4. Identify the affected service in [OPERATIONS.md](OPERATIONS.md#services). Read its source and data contract before changing it. Its protocol README owns cloud-client deployment and recovery behavior.

Proxyrack's program, worker and service definition are owned by [the Proxyrack folder](../proxyrack/README.md); the matching Website paths are links. Keep that folder with this repository checkout. The source restore below materializes regular files, and the Linux staging command in RECOVERY.md resolves the service link before transfer.

For an offline source restore, run from the repository root:

```sh
python3 restore.py Website --to /path/to/empty/runtime
```

This validates and copies application source. It does not install Linux services, authenticate accounts, restore history or launch cloud clients. Complete those steps through [RECOVERY.md](RECOVERY.md).

## What must survive separately

Keep the repository/its backup, owner access to AWS/Cloudflare/domain/provider accounts, security-key recovery access, and an encrypted backup of runtime data and credentials. Credentials are absent from Git. A source rebuild can start new recording; it cannot reconstruct deleted historical samples or private keys without their backup.

[VERIFICATION.md](VERIFICATION.md) records the configuration capture and validation. When a deployment changes a path, unit, origin or authentication boundary, update the matching source/configuration and these guides together. An existing installation may contain a newer release; compare it before replacing files.

## Use the dashboard

Choose a service from the sidebar (the horizontal service list on a phone). The shared minute chart defaults to 24 hours and offers 1, 6, 12 and 24 hours; changing services keeps the chosen period. Its bars preserve measured zero, missing samples, partial coverage and estimated minute allocations. Select a minute with the pointer or keyboard arrows to inspect its Network and Credited amounts. The compact popup follows the owner’s approved presentation. IP breakdown and IP history retain the recorded IP contributions and detail access.

**Current nodes** shows the latest inventory, client state, measured rate, recorded traffic, duration, source age and client/recovery notes. Cloud-running counts, confirmed clients and provider credits remain separate. A cached or failed refresh keeps saved contributions while marking current state unverified. The Details section discloses account/device scope, dated observations, unavailable values, and estimated Salad cost from recorded running-state time. Historical cost catch-up remains partial until its source coverage is complete.

**IP history** reads the bounded `/api/history` contract. Use the chart period or all recorded history, choose the current or a labeled archived test, search IP/country/instance/run, and sort by last observation or contribution. Each row has a detail view with the original group, instance, machine and run identity. Traffic and recorded duration follow the selected period; first/last observation timestamps remain the original record bounds. Coverage notes and missing values remain visible. Provider account credits are never allocated to an IP by this interface.

The separate `/ef` EarnFM detail page uses the same visual theme and defaults to 24 hours. Its existing provider observations, recovery records, contributor popup and data download remain available; **Overview & IP history** returns to the shared page.
