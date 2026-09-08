# Mysterium on Salad

**Shelved at the owner's request — 2026-09-07.** Leave Mysterium stopped. No further deployment, reallocation, registration or earnings experiments are planned; resume only if the owner explicitly requests it. Measured Salad readback at **17:32:57 UTC** confirmed Stopped, no instances, and autostart disabled.

**Recovery status — 2026-09-07:** fresh registration is blocked on the tested MystNodes account: its official onboarding page reports that the free-registration limit has been reached. The startup fixes are saved and tested, but an operational provider after reallocation is not proven. The failed test was stopped. See the [exact evidence and remaining requirement](verification.md#reallocation-repair--not-complete).

These saved guides document the build, setup, operation and failed recovery trial. The deployment instructions below are retained for a future owner-requested resumption. Keep this folder together; the instructions do not depend on the previous chat or other Salad project files. Account keys and private node data must be kept separately.

## Choose your starting point

- **Everything was deleted / no group exists:** begin with [setup.md](setup.md).
- **The group still exists but is stopped:** follow [stop/start instructions](operations.md#stop-start-restart-or-rebuild); do not create a duplicate.
- **An instance is already running:** open its Terminal and begin [host startup checks](setup.md#start-and-verify-the-host).
- **The published image is unavailable:** follow [build.md](build.md), then return to [setup.md](setup.md).

## Files

| File | Use it for |
| --- | --- |
| [setup.md](setup.md) | Accounts, selected-country deployment, and startup registration. |
| [start.sh](start.sh) | The in-container startup and registration implementation. |
| [Dockerfile](Dockerfile) | The pinned image build. |
| [operations.md](operations.md) | Stop/start, restart/reallocation, and checking the actual node. |
| [build.md](build.md) | Rebuilding and publishing the corrected image from source. |
| [troubleshooting.md](troubleshooting.md) | DNS, the MTU correction, and observed errors with their handling. |
| [verification.md](verification.md) | The dated deployment, session evidence, and reproduction checks. |

## Reading the evidence

These instructions come from the recorded trial on **2026-09-07**. [Verification](verification.md) contains its results; use [operations](operations.md) to check a running node now.

In this guide, **measured** means observed on the actual trial, **published** means documented by the linked provider, and command values are the tested configuration or explicit diagnostic deadlines—not claims about minimum resources, maximum performance, or guaranteed startup time.
