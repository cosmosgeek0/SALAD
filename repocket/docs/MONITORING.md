# RP monitoring and local processes

Production is on the separate AWS Mumbai host: source `/opt/salad/repocket-monitor/observe.py`, data `/home/salad/.hg1/repocket`, service `salad-repocket.service`, page https://salad.cosmosgeek.org/#rp. Keep the retired Mac jobs disabled. The local commands below are recovery instructions only; do not run a second recorder beside production.

The RP worker emits `RP_MON ` JSON logs to Salad. `observe.py` reads them and persists them in SQLite. It makes no reallocation requests. The local page reads those saved measurements; it is not the fleet manager.

First, run the recorder in one terminal from the package root:

```bash
python3 -B repocket-monitor/observe.py
```

In another terminal, start the preserved page with the recovery launcher:

```bash
cd "$HOME/Desktop/salad/repocket"
python3 -B restore-dashboard.py --port 8787
```

Open [http://127.0.0.1:8787/#rp](http://127.0.0.1:8787/#rp). If another dashboard already owns port 8787, use `--port 8788` and open `http://127.0.0.1:8788/#rp` for this separate restored copy. Do not kill an unrelated service to free a port.

`restore-dashboard.py` uses the original `dashboard.server.make_handler` and original UI assets. It deliberately does not start the original server's Honeygain/PacketStream background pollers. The preserved common page still has other provider tabs; restoring their deployments/data is outside this RP backup. Use the **RP** tab. The `dashboard/*.py` dependencies are included because the original common server imports them, even though only the RP recorder is started by these instructions.

The current data directory is fixed in `observe.py` at `~/.hg1/repocket`. Organization/group constants and the log query are also fixed to `ssh2/default/rp-test-us`. To recreate under another organization/project/group, change **all** of the control helper's constants, the observer's API organization path, `GROUP`, log query, metadata and displayed portal links together. The recipe above needs no such changes.

### Start the two local processes automatically at login (macOS)

Do this only for a fresh recovery installation. Do not run a second recorder beside an existing one: its file lock intentionally refuses that. Existing original service labels are `com.cosmosgeek.repocket-recorder` and `com.cosmosgeek.salad-bandwidth-dashboard`; the recovery labels below are distinct. If the original service is already healthy, use it rather than installing duplicates.

Stop both foreground test processes with Ctrl+C first. The source package now lives under Desktop/salad/repocket. macOS privacy permissions can prevent a login agent from reading Desktop; verify the foreground commands first and grant the required access to your chosen Python interpreter if macOS requests it. The retired Mac install uses Application Support; production uses the AWS paths above. Use the same port you verified in the foreground: change `8787` to `8788` below if you selected that alternate port. From the package root:

```bash
python3 - 8787 <<'PY_AGENTS'
from pathlib import Path
import plistlib,sys
port=str(int(sys.argv[1]));root=Path.cwd().resolve();agents=Path.home()/'Library/LaunchAgents';agents.mkdir(parents=True,exist_ok=True)
data=Path.home()/'.hg1/repocket';data.mkdir(parents=True,exist_ok=True)
for label,script,extra in [
    ('com.cosmosgeek.rp-recovered-recorder','repocket-monitor/observe.py',[]),
    ('com.cosmosgeek.rp-recovered-dashboard','restore-dashboard.py',['--port',port])]:
    value={'Label':label,'ProgramArguments':[sys.executable,'-B',str(root/script),*extra],
           'WorkingDirectory':str(root),'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':15,
           'StandardOutPath':str(data/(label+'.out.log')),'StandardErrorPath':str(data/(label+'.err.log'))}
    (agents/(label+'.plist')).write_bytes(plistlib.dumps(value))
print('Wrote two login-agent definitions; use launchctl below to load them')
PY_AGENTS
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.cosmosgeek.rp-recovered-recorder.plist"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.cosmosgeek.rp-recovered-dashboard.plist"
```

Keep the package directory in place because these definitions point to it. LaunchAgents run while that user is logged in, and collection pauses when the Mac sleeps. Cloud recovery continues. To unload either recovery process, use `launchctl bootout "gui/$(id -u)/LABEL"` with its exact label above. That only stops the local process, not the Salad group. Delete its plist manually if you do not want it loaded next login.

## Existing operational locations

The editable recovery package is `~/Desktop/salad/repocket`.

| Purpose | Production location |
|---|---|
| Recorder source | AWS `/opt/salad/repocket-monitor/observe.py` |
| History, cursor, metadata and published view | AWS `/home/salad/.hg1/repocket` |
| Recorder service and logs | `salad-repocket.service`; `journalctl -u salad-repocket.service` |
| Shared website | AWS `/opt/salad/dashboard`; [public RP page](https://salad.cosmosgeek.org/#rp) |

The old Mac Application Support source, `~/.hg1/repocket` history and `com.cosmosgeek.repocket-recorder` job are retired operational copies, not temporary files. Their values are not current production evidence. Keep the Mac jobs disabled. AWS hosting, secret-adapter installation and service units are documented in the sibling [Website package](../../Website/README.md); preserve that package as well to reproduce the hosted site. This folder alone supplies the RP cloud workload and the local recovery viewer.

## Reading the results

- **Interface/network RX+TX:** real Linux `eth0` receive plus send byte deltas. A proxied payload commonly crosses the interface twice, once on each leg. This includes transport/control overhead and is not unique delivered content or earnings.
- **Target socket bytes:** bytes read/written on observed HTTP/HTTPS and SOCKS target connections. These avoid adding the relay's second leg, but still include target protocol overhead; they are not provider-credited bytes.
- **Reply outcome:** any target response bytes, including protocol/TLS bytes. It is not an HTTP 200 or proof of payment. Terminal failed-before-reply outcomes are counted once per observed connection; raw timeout logs can repeat.
- **Provider credited / earned:** a timestamped **account lifetime own-bandwidth** reading from Repocket. The separate `salad-repocket-provider.service` collects it automatically after account access is connected; follow [Provider earnings](PROVIDER.md). The page marks a snapshot stale after three minutes. Do not fabricate fresh zero values when it is unavailable. Actual payable rewards remain governed by [Repocket's payment policy](https://repocket.com/payment-and-rewards-policy).
- **Profit:** requires corresponding provider earning and Salad spend readings over the same interval. The current recorder does not publish an estimated profit. The deployment metadata's historical `budget_usd` field is informational and is not a spend limiter.

The provider service owns production `/home/salad/.hg1/repocket/provider.json` and preserves successful observations in `provider.sqlite3`. Do not manually overwrite its readings or restamp an older snapshot. Credentials belong in the private secret store, never in `provider.json`. Account totals may include earlier devices and other locations, so they are not earnings attributable only to this fleet. Until account access is connected, current earnings remain unverified.

## Recording contract

The existing `traffic.sqlite3` history is migrated additively. Raw `events.body` records remain intact. New columns retain group/runtime/sequence identity, measured interval boundaries, validity, Salad `indexed_ms` from receive_time and collector `received_ms`. Original source time remains `time_ms`. Legacy receipt timestamps remain NULL rather than being invented.

`record_key` binds format-2 records to group/run/sequence. Repeated identical records are ignored; conflicting payloads are retained and invalidated. Wrong-group records are rejected. The saved cursor advances only after a complete log fetch and committed inserts. Normal collection overlaps the last minute; a rolling hour sweep and a final persisted recheck after the full one-hour lateness allowance catch delayed logs. Each final slice is bounded to two minutes including overlap, and failed reads retain its cursor. Logs delayed beyond that allowance are not guaranteed to be recovered. Native evidence, latest traffic interval, inventory and diagnostics use separate freshness flags.

The collector publishes `chart_minutes` for 24 hours once per collection cycle. The website reads that prepared chart instead of querying all retained JSON bodies at every browser refresh. Totals include retired runs; row recorded time is the sum of captured intervals, not assumed uptime across gaps. Missing measurements remain blank. A newest invalid interval clears the rate rather than reusing a previous valid value. Final/partial intervals keep their partial status. An inventory update does not discard an exact matching runtime; a timestamp boundary applies to fallback matching only. The browser independently expires inventory at 90 seconds.

Recovery output records request IDs, attempts and acceptance. Fresh inventory establishes when the old machine is gone; `members` records newly seen and native-connected instances. The collector does not invent a one-to-one pairing between group-wide replacement requests and new hosts.

Provider observations are a separate timestamped journal (`provider_readings`). They are not computed from network bytes. A stale/missing/unverified provider feed is shown as Not reported; its last observed account value and time remain available. Account sign-in is needed to restore that feed; running containers alone do not provide dashboard earnings authorization.
