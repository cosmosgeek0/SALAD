# EarnApp

Start here. This folder holds the EarnApp setup, executable source, service configuration and saved measurements.

| File | Use it for |
|---|---|
| [SETUP.md](SETUP.md) | Create or restore the EarnApp client in Salad |
| [MONITORING.md](MONITORING.md) | Run the recorder, connect account readings and manage its service |
| [RECOVERY.md](RECOVERY.md) | Native recovery, provider policies and how outcomes are verified |
| [liveness.json](liveness.json) | Salad heartbeat probe configuration |
| [salad-earnapp.conf](salad-earnapp.conf) | Linux recorder service drop-in |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Understand errors, missing readings and the verification evidence |
| [startup.sh](startup.sh) | The complete command to paste into Salad |
| [earnapp-recorder.py](earnapp-recorder.py) | Inventory, traffic, provider readings and JSON publication |
| [com.cosmosgeek.earnapp-recorder.plist](com.cosmosgeek.earnapp-recorder.plist) | The Mac service configuration |
| `data/view.json` (separate data backup) | The last saved dashboard reading; live measurements are excluded from the source repository. |
| `data/traffic.sqlite3` | Original samples, checkpoints and provider history |

## Storage and existing integrations

The real files live in this folder. The previous collector paths in `salad-bandwidth-stack/scripts` and the installed dashboard's `scripts` folder are compatibility links to this source. `~/.hg1/earnapp` links to `data/`, and the Mac LaunchAgents entry links to this folder's service configuration.

Those links keep the existing dashboard lookup and old entry points usable. They do not hold duplicate source or measurement files. The old loose `earn app.md` and duplicate service templates have been replaced by this layout.

Credentials remain in the existing Keychain or the process environment. The shared Keychain helper belongs to the bandwidth dashboard installation; it is not an EarnApp source file.

## Moving or backing up

Keep the whole folder together. Stop the recorder before copying its history, include the complete `data/` directory, and update the links and service paths if the folder moves. Copying only the Markdown files will not include the executable source or saved history.

Production recording is on AWS Mumbai under `/opt/salad/EarnApp`, using `/home/salad/.hg1/earnapp` for its database. The local EarnApp recorder and shared dashboard remain disabled. This file move did not enable them or change the cloud deployment. A saved JSON file is a dated reading, not evidence that collection is currently running.
