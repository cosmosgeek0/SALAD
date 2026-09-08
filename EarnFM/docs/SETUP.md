# EarnFM setup

[Start here](../README.md) · [Setup](SETUP.md) · [Operations](OPERATIONS.md) · [Recovery](RECOVERY.md) · [Reference](REFERENCE.md)

**Production is on AWS.** Follow [AWS setup](AWS.md) for the active host and keep the retired Mac recorders disabled. The instructions below provide an optional standalone Mac recovery installation.

Run the commands in this guide from the **EarnFM project folder**. The source files are already present; no Markdown extraction is required.

```sh
cd "$HOME/Desktop/salad/EarnFM"
```

If this folder is stored elsewhere, use that directory instead. Check the prerequisites before preparing a new Mac.

## Prerequisites and credentials

Use a Mac with Python **3.9 or later**, `curl`, and Apple's Swift compiler. The recorder uses the standard library and macOS Keychain; no npm, pip, web framework, paid dashboard service, or local Docker daemon is required to operate it. Docker is useful only for optional image backup and offline checks.

Check tools in Terminal:

```sh
python3 --version
curl --version
xcrun --find swiftc
```

If `swiftc` or Python is unavailable, install Apple's Command Line Tools using `xcode-select --install`, complete Apple's installation, and repeat the checks. Install a supported Python from [python.org](https://www.python.org/downloads/macos/) if the OS does not provide one. The service installer records the interpreter you actually used.

Log into the existing [Salad portal](https://portal.salad.com/organizations) and [EarnFM account](https://app.earn.fm/). Confirm access to **SSH3 / default** and available credit. Do not create another earning account to get around a restriction. If SSH3 itself was deleted, its owner must recreate/restore it and funding through Salad; cloud organization access cannot be reconstructed from a UUID.

Three different credentials are used:

| Keychain service | Obtain it from | Used for |
|---|---|---|
| `salad-bandwidth-api` | Salad profile menu → **API Access** | Read/manage authorized Salad group and logs |
| `earnfm-api-key` | EarnFM account settings / Docker installation card | Docker `EARNFM_TOKEN` only |
| `earnfm-read-session` | Access JWT used by the signed-in EarnFM web app's `X-API-Key` request header | Account balance and online-device reads |

All Keychain items use the **current macOS username** as account. The compiled helper is `.runtime/keychain-store`. It accepts secret values on standard input; commands in this guide do not put them in command-line arguments, project files, screenshots, or shell history.

To obtain the **reader JWT** without any chat-specific login link:

1. Sign in normally at `https://app.earn.fm/`.
2. Open browser Developer Tools → **Network**, then reload the app.
3. Filter requests for `view_balance`; open the request to `https://api.earn.fm/v2/harvester/view_balance`.
4. Under Request Headers, copy the **value only** of `X-API-Key`. It is an access JWT, commonly beginning `eyJ`. It is not the short Docker API key and has no `Bearer ` prefix in the observed client.
5. Paste it only into the recovery CLI's hidden reader prompt. The CLI reads the JWT's expiry, verifies it against both provider endpoints, and stores `{access_token, expires_at}` securely. It never asks for or stores a refresh token.
6. If that request is absent, ensure the app has fully loaded and you are signed in. The app's Application → Local Storage entry `sb-sb-auth-token` also contained `access_token` and `expires_at` in the observed build; do not copy the whole session or its refresh token. Network headers are the preferred route because storage names can change.

The captured reader session had an expiry of September 11, 2026, around 20:55 IST. **That old token is not supplied here.** New sessions have their own expiry. Refresh the reader using the same steps and `keys --service reader --replace`. Its expiry does not stop the cloud EarnFM clients.

After the prerequisites and account steps, prepare the local helper, preview the configuration, and save missing credentials in an interactive Terminal:

```sh
python3 earnfm.py prepare
python3 earnfm.py plan
python3 earnfm.py keys
```

`prepare` verifies the source checksums and compiles the local helper. `plan` prints nonsecret settings without changing the cloud. Usable existing credential entries are retained. `--service reader --replace` renews only the account-reading token. A macOS Keychain prompt may require allowing the compiled local helper to read an existing item.

## Create or adopt the deployment

First inspect. Do not create duplicate groups if the original still exists.

```sh
python3 earnfm.py inspect
python3 earnfm.py deploy
```

`deploy` behaves as follows:

- If the group is absent, it creates **ten replicas** using the pinned image and full startup script, initially with autostart false.
- If the same group/configuration **and selected client token** survive, it adopts it and writes local `target.json` without restarting it. A missing/different cloud token requires the explicit update path; neither token is printed.
- If the group differs, it stops with an explanation. To deliberately replace its configuration with this version, use `python3 earnfm.py deploy --update`. **That updates a paid running group and may restart every replica.** It preserves the current single-country trial and its matching `EARNFM_COUNTRY`, carries forward unexpired environment and recorded-log cooldowns, explicitly clears GPU classes, and verifies CPU/memory/shared-memory settings and the selected client token after the update. When no cooldown remains, the environment uses the harmless nonempty marker `none`, which the startup loop ignores.
- If the local Docker-key entry is missing for an existing group, it retains that group's existing `EARNFM_TOKEN`. A new group still requires the client credential. It never prints the payload containing `EARNFM_TOKEN` or the Salad key. It verifies the decoded cloud script and image after a create/update, reads the actual new group ID/version, and writes them to `~/.hg1/earnfm/target.json`.
- After a mutation, it waits up to 30 seconds using read-only checks for the updated command to propagate. On a network error with uncertain mutation outcome, run `inspect` first. Do not keep firing create/update requests.

After successful deployment/adoption, start the group and take a single live observation before installing the recurring local services:

```sh
python3 earnfm.py start
python3 earnfm.py inspect
python3 earnfm.py observe
```

Allocation and image preparation are asynchronous. A successful start response is not a claim that ten clients are earning. Repeat `inspect` after the platform has made progress. `observe` creates a fresh database and a fresh provider baseline only when they are absent. It does not fabricate earlier history. A surviving matching database/baseline is retained.

If `observe` says the recorder lock is held, the existing recorder is already running; use its published JSON instead of starting another process. If the page says “awaiting sample,” inspect logs and let the nodes reach the client startup stage. Schema migrations preserve saved samples and add the minute cache, receipt details, provider history and recovery ledger.

If deployment reports old state without a matching target, follow [the recovery procedure](RECOVERY.md#restore-or-archive-existing-state) before continuing. Do not mix another deployment's ledger with new measurements.

## Dashboard and local services

For a clean machine with port 8787 free:

```sh
python3 earnfm.py install
```

This creates and starts these user LaunchAgents, both in `~/Library/LaunchAgents/`:

- `com.cosmosgeek.earnfm-recorder`: runs `scripts/earnfm-recorder.py`, writes the ledger and JSON.
- `com.cosmosgeek.earnfm-dashboard`: runs the small recovery server in `earnfm.py`, binds **127.0.0.1 only**, serves the original EF HTML/CSS/JSON.

Open [EF locally](http://127.0.0.1:8787/ef) or [the root page](http://127.0.0.1:8787/). This clean-room page is EF-only. Its inherited Honeygain/PacketStream links require those other projects; they do not install or control them.

For a foreground test without installing a service:

```sh
python3 earnfm.py serve --port 8787
```

Stop that foreground server with Ctrl-C before calling `install`. An occupied port is reported as an error; the installer does not kill an unrelated dashboard.

If the original shared dashboard survives, use its server and restore only the EarnFM files. **Do not run two servers on 8787.** `install --shared-dashboard` installs only the recorder, provided that recorder's LaunchAgent does not already exist. For a surviving service, retain its plist and verify its working directory and executable. If it is still loaded, use `launchctl kickstart -k "gui/$(id -u)/com.cosmosgeek.earnfm-recorder"`. **If the archive step unloaded it with `bootout`, reload it instead:**

```sh
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.cosmosgeek.earnfm-recorder.plist"
```

Do not call `install` for an existing retained plist. If you restored the project to a different directory, first edit that plist's `WorkingDirectory` and script path under `ProgramArguments` to the EarnFM project directory; keep the Python interpreter path valid. Use `plutil -lint` on the edited plist, then the bootstrap command above. A loaded service must be booted out before reloading an edited plist.

The shared server integration requires only these read-only routes, with JSON read from `~/.hg1/earnfm/view.json` and assets from the EarnFM static directory:

| Route | Contents / MIME |
|---|---|
| `/ef` | `dashboard/static/earnfm.html`, HTML |
| `/ef.json`, `/earnfm.json` | `~/.hg1/earnfm/view.json`, JSON |
| `/api/earnfm` | the same `view.json`, used by the shared dashboard's EarnFM tab |
| `/styles.css` | included stylesheet if no shared stylesheet already exists |

No management API key goes to browser JavaScript. The captured multi-protocol tab linked to `http://127.0.0.1:8787/#earnfm`; `earnfm.py` supplies `/api/earnfm` for integration, but does not recreate the other protocols' UI/backend. The standalone `/ef` gives the complete EarnFM monitoring function if that shared code has been lost.
