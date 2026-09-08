# Recover or stop Grass

## Automatic recovery inside the container

`bootstrap.sh` registers `worker.pl` with the image's existing supervisor. The supervisor restarts a failed worker, and the worker checks Grass independently of the Mac and AWS recorder.

The following are configured policy values in `worker.pl`, not Grass or Salad platform limits:

| Observed failure | Native action |
|---|---|
| Grass process absent | After a twenty-second grace period, request an app restart. |
| Process suspended/stalled | Request app recovery at the next sample check, subject to the current recovery cooldown. |
| Device/IP absent from a successful provider listing, or registration stuck | After two minutes, restart the app. |
| App recovery still fails | Allow at most two local restarts, each with a two-minute grace period; then request a new machine through Salad IMDS. |
| Provider reports zero network quality | Reallocate after two successive zero-quality readings, subject to the recovery cooldown. |
| Provider timeout, malformed response or rate limit | Show unknown/error and retry status with backoff. Respect `Retry-After`; do not replace a machine from missing telemetry. |
| Missing/rejected account login | Show **Sign-in required**. Reallocation does not repair invalid credentials. |
| Little traffic or unchanged points on a connected node | Keep it running. Demand and provider credit schedules are not client failures. |

Five minutes of continuously confirmed health reset the local restart budget. The worker records restart requests and verifies a changed process plus renewed provider acceptance. For reallocation it records IMDS responses and acceptance. The recorder separately records `replacement_connected` only after a fresh healthy instance appears on a different machine. Accepted is not the same as recovered.

An initial saved login is required for machine replacement. `deploy.py repair` supplies it. Newly created devices register their own identity; they share the account session, not a copied device ID. The current measured deployment and replacement correlation use one replica. Multi-replica earning attribution and replacement correlation are not established by this implementation.

## Repair an account login

Open the group's printed HTTPS desktop and sign in again if Grass requests it. If the saved deployment session was revoked, the old seed must be replaced as well:

1. In Salad's group settings, remove only `GRASS_STATE_B64` from the environment, leaving the desktop access settings and other configuration intact. Save, then wait for the new instance.
2. Sign in to Grass on that running instance using the desktop.
3. Run `python3 -B "$HOME/Desktop/salad/grass/deploy.py" repair` and complete its encrypted transfer again.
4. Verify fresh provider acceptance on the rolled-out instance.

The native app owns its authentication. No undocumented token-refresh request or password bypass is implemented.

## Rebuild after deletion

If the Salad group was deleted, follow [Setup](setup.md) from `create`, sign in, then run `repair`. If only the machine was replaced, the configured startup command automatically installs the worker and restores the saved session.

Restore this whole folder after source loss. Restore the repository's Website folder and follow its [recovery guide](../Website/RECOVERY.md) if AWS recording or the shared page was lost. Source alone cannot recreate deleted historical measurements, account credentials, or identical traffic/earnings.

## Diagnose an interruption

| Symptom | Check |
|---|---|
| `Setup failed` | Native `bootstrap_failed` event gives the failed stage and exit code. |
| `Awaiting native sample` | Current instance/version, `GRASS_BOOTSTRAP_READY`, and `worker_started` in Salad logs. |
| `Grass status unavailable` | The reported API/IP-check error and next retry time. A cached app status is not fresh provider proof. |
| `Restarting Grass` / `Reallocating` | Native request, response and subsequent recovery evidence; retain the failure until confirmation. |
| Old graph or collection error | `salad-grass.service` journal, current source times, and log retrieval. Restarting the client does not repair AWS recording. |
| Viewer reconnecting or clipboard error | Reload the HTTPS desktop and re-enter its desktop password. |

Measured fixes on September 7, 2026: the image lacked Perl TLS support and its `messagebus` group. Bootstrap restores that group before installing `libio-socket-ssl-perl`. Its init script ignored a symlinked startup hook; deployment now copies a regular executable hook. The `man-db` package trigger printed a missing-`man` warning, but installation completed successfully and verified TLS requests worked.

## Stop hosting charges

Open the [Grass group](https://portal.salad.com/organizations/cosmosgeeketh/projects/default/containers/grass), click **Stop**, and verify **Stopped** with no running instances. Closing the viewer or stopping the AWS recorder does not stop Salad charges. **Start** resumes the configured group with the native startup and saved login.
