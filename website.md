# Local bandwidth website — complete rebuild guide

**Reproducibility:** the embedded source and deployment settings are reproducible. New IPs, placement time, traffic demand, provider acceptance and earnings are not fixed outputs of this software. Identical MB or credits are not promised. This verification used isolated reconstruction tests and read-only live comparisons; it did not delete and recreate the paid fleet.

Verified against the served files on **7 September 2026, UTC**. This is a source-bearing recovery document for the website at http://127.0.0.1:8787/. It includes the actual HTML, CSS, JavaScript, Python server, parsers, SQLite stores, six protocols' local collectors and fresh-install helpers. No Git checkout, old task, npm build or proprietary design tool is needed to reconstruct this website.

The Honeygain and PacketStream cloud deployments are independently documented in honeygain.md and packetstream.md. This file restores the local site and connects its collectors to existing protocol deployments. It does not silently deploy the other four cloud workloads.

## Exact product to reproduce

- One loopback-only page, six tabs in this order: **Honeygain, PacketStream, Proxyrack, Repocket, RFM, Traffic Monetizer**.
- One common bar chart above a simple table. One bar per minute. Select **1, 6, 12 or 24 hours**; default is 12. Do not display a time window beyond 24 hours.
- Hover/click a minute to see a popup containing the top 20 contributors by MB: IP, country and that minute's MB. Keyboard arrows/Home/End select minutes; Escape closes it.
- One row per current server, with explicit unassigned slots while a fresh inventory is short of the desired count. Do not append a separate persistent contributor list.
- Header values: confirmed clients versus desired count, cloud-running count, recorded network MB, selected-period MB, provider credits/earnings where actually reported, and elapsed time.
- Row values: IP/identifier, client state, Salad state, MB/min, recorded MB, recording duration, sample age, error/note.
- Downloading/creating/stopping/stopped are real cloud states. An unverified or stale monitor is not proof a client failed. Missing numbers are dashes/Not reported, not invented zeros.
- Same-page hash tabs: #hg1, #ps1, #proxyrack, #rp, #earnfm, #tm. Existing pretty service URLs map to the same page.

No account/Salad credentials appear in the browser data. The root is bound to 127.0.0.1, not publicly exposed. There is no revenue promise: RX+TX traffic includes overhead and both directions of a relay.

## Architecture and current locations

~~~~text
Salad native clients → stdout measurements/state → Salad Log API
                                                    ↓
                            independent local Python recorders
                                                    ↓
                       ~/.hg1/ JSONL + SQLite + current snapshots
                                                    ↓
                Python ThreadingHTTPServer on 127.0.0.1:8787
                                                    ↓
                 index.html → ps1.js chart → fleet-test.js UI

Provider account APIs / explicit browser feed → separate credited-traffic data
Cloud recovery: inside each workload via IMDS; does not depend on this Mac
~~~~

| Location | Meaning |
|---|---|
| ~/Desktop/salad-bandwidth-stack | Editable website and most observer sources |
| ~/Desktop/salad/proxyrack.py | Proxyrack source owned by its protocol implementation |
| ~/Desktop/salad/*.md | Recovery documents; these three are source-bearing |
| ~/Library/Application Support/Salad Bandwidth Dashboard | Installed source executed by LaunchAgents |
| ~/.hg1 | Local measurements, current snapshots and metadata |
| ~/Library/LaunchAgents | Local service definitions |

Editing Desktop source alone does not update the running site. Install only the changed file(s) into Application Support. Static JavaScript changes need a browser reload; Python modules need the relevant process restarted.

## Complete rebuild sequence

**External inputs:** macOS login/account access, Python 3.9+, curl, Xcode Command Line Tools for the Keychain helper, a modern browser, the Salad API key, and whichever provider account credentials/sessions are available. Python uses the standard library, including SQLite JSON/window support. Node is optional for JavaScript tests, not the production server.

If all local files were lost, the embedded appendix restores all required application source. If cloud groups were also deleted, first recreate them from their protocol documents; new UUIDs must be rebound. Deleted historical measurements are not contained in this source document.

1. Extract to the canonical installed root. The command validates hashes and refuses different existing files. To inspect or rehearse first, substitute a new empty directory for the destination.

~~~~bash
python3 - "$HOME/Desktop/salad/website.md" "$HOME/Library/Application Support/Salad Bandwidth Dashboard" <<'PY'
import hashlib, re, sys
from pathlib import Path
document=Path(sys.argv[1]);root=Path(sys.argv[2]).expanduser().resolve()
text=document.read_text()
pattern=r'^<!-- rebuild-file: ([^\n]+) sha256=([0-9a-f]{64}) -->\n~~~~~~[^\n]*\n(.*?)^~~~~~~\n'
files=re.findall(pattern,text,re.M|re.S)
if not files:raise SystemExit('No embedded source files found')
checked=[]
for name,digest,body in files:
    relative=Path(name)
    if relative.is_absolute() or '..' in relative.parts:raise SystemExit('Unsafe embedded path')
    target=root/relative;raw=body.encode()
    if hashlib.sha256(raw).hexdigest()!=digest:raise SystemExit('Damaged source block: '+name)
    if target.exists() and target.read_bytes()!=raw:raise SystemExit('Existing different file preserved: '+str(target))
    checked.append((target,raw))
for target,raw in checked:
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(raw)
print('Restored',len(checked),'verified files to',root)
PY
~~~~

2. Compile the helper and securely store the Salad key.

~~~~bash
cd "$HOME/Library/Application Support/Salad Bandwidth Dashboard"
mkdir -p .runtime
chmod 700 .runtime
xcrun swiftc scripts/keychain-store.swift -o .runtime/keychain-store
chmod 700 .runtime/keychain-store
python3 scripts/save-secret.py salad-bandwidth-api
~~~~

Use the existing Salad API key for the account that can access the named organizations. The prompt is hidden; the key goes to macOS Keychain service **salad-bandwidth-api**, account **your macOS login name**. Never put the key in this Markdown, a command argument, or a copied cloud JSON response. A freshly compiled helper may trigger the normal macOS Keychain access prompt. Do not start multiple copies of an observer: each uses a lock.


3. Restore Honeygain/PacketStream cloud bindings and get the first HG baseline. If the cloud does not exist, follow each app document's create step before this step. If you have already completed both app guides, their binding files, baseline and observers already exist: skip this step and continue at step 4. Do not run --once observers alongside their running services; their locks deliberately reject a second copy.

~~~~bash
HG_FLEET_DIR="$HOME/.hg1/hg-fleet" python3 scripts/rebuild-cloud.py honeygain bind &&
python3 scripts/rebuild-cloud.py packetstream bind &&
HG_FLEET_DIR="$HOME/.hg1/hg-fleet" python3 scripts/hg-provider-observer.py --once &&
HG_FLEET_DIR="$HOME/.hg1/hg-fleet" python3 scripts/hg-fleet-observer.py --once &&
python3 scripts/initialize-recording.py
~~~~

The provider baseline must be an actual new account reading. Never carry the September 2026 baseline numbers into a new experiment. The included initializer fixes the old start-new default that named the retired ps1 group and refuses to overwrite an existing experiment.

4. Bind the other existing cloud groups, if those protocols are running. These commands only read Salad and write fresh local metadata.

~~~~bash
python3 scripts/bind-website.py pr rp rfm
~~~~

The exact current targets are:

| UI | Organization / project / group | Current historical group ID |
|---|---|---|
| Honeygain | deathadder/default/hg1 and hg-solo-02…10 | Ten groups; discover their IDs during binding |
| PacketStream | hyperlane/default/ps-test-us | a36f8bba-0b01-4e86-9948-0cedb2fac3de |
| Proxyrack | ssh1/default/pr | ab9fd890-55b8-42ab-86ac-957fe8ce3d87 |
| Repocket | ssh2/default/rp-test-us | a3a77aae-085e-4c0c-a969-34d50b091a46 |
| RFM | ssh3/default/earnfm-us | 90078bc1-4410-46cd-8411-6ebb8968eec2 |
| Traffic Monetizer | ssh4/default/tm-test-us | 1a64168c-d295-4b6c-9d4c-928303dfebf2 |

Current placement/instance IDs change continuously. Fresh binding uses API responses, not this table.

When binding to an already-running RFM workload, its total_mb and row totals retain the wrapper-run cumulative counters. Its minute chart starts at the new local measurement boundary. Those totals can therefore include traffic from before this Mac was restored; they are not recovered historical minute records. This is the preserved source behavior, and must not be described as a new-run total.

5. Restore provider read access. Never paste secrets into Markdown.

| Keychain service | Exact value/input and source |
|---|---|
| salad-bandwidth-api | Salad account API key for the named organizations |
| proxyrack-peer-api | Proxyrack account API key from its provider portal |
| earnfm-read-session | One-line JSON with access_token and expires_at; expires_at is Unix seconds from the actual login/token lifetime |
| salad-traffmonetizer-session | Current provider bearer token, without the “Bearer ” prefix |

For each service, run the hidden prompt:

~~~~bash
python3 scripts/save-secret.py proxyrack-peer-api
python3 scripts/save-secret.py earnfm-read-session
python3 scripts/save-secret.py salad-traffmonetizer-session
~~~~

Obtain RFM/TM tokens from your own signed-in provider session: in the browser Network panel, inspect the authenticated provider request and its login response, not another user's data. RFM requests use X-API-Key to https://api.earn.fm/v2/harvester/view_balance and devices_online. TM requests use Authorization: Bearer to https://data.traffmonetizer.com/api/app_user/get_balance and /api/dashboard/get_graph_stat?period=month. RFM expires_at must reflect the real expiry; do not invent a permanent token. TM rotates a returned Authorization header back into Keychain.

After TM access is restored, initialize its baseline from an actual API reading:

~~~~bash
python3 scripts/bind-website.py tm
~~~~

This stops on missing/expired provider access instead of manufacturing a zero baseline. If a protocol is unavailable, defer its collector and show missing data; do not fabricate a provider JSON file to make the tab green.

Repocket's current provider-day account snapshot is separate from its automatic network recorder. To record figures you have just read in its logged-in dashboard:

~~~~bash
python3 scripts/publish-repocket-reading.py
~~~~

Enter the actual observed values at the prompts; placeholders are rejected and the observation timestamp is now. Do not schedule repeated re-stamping of an old reading. The UI labels it stale after three minutes.

PacketStream's optional signed-in provider bridge is included as dashboard/ps-paid-feed.js. Without a real feed, network recording continues but provider earnings remain Not reported. To restore it using only this document: in the local page's console run sessionStorage.setItem('ps-billing-channel', crypto.randomUUID()); location.reload();. After reload, run window.open('https://app.packetstream.io/dashboard#ps-sync='+encodeURIComponent(sessionStorage.getItem('ps-billing-channel')), 'psBillingSync'); from that same page. In the new child window, sign in to your own account and run the embedded dashboard/ps-paid-feed.js source. Its old public account guard psr=8ExP must match the provider's referral link; change that guard to your real account identifier if needed. Keep both windows open. It sends only measured credited bytes and time, never cookies or account credentials. At least two fresh provider observations are needed; do not invent a paid delta.

6. Start only the collectors whose required sources/bindings exist, then the server:

~~~~bash
python3 scripts/install-services.py hg-provider hg-fleet fleet ps
python3 scripts/install-services.py pr rp rfm tm
python3 scripts/install-services.py dashboard
~~~~

The second line assumes those four protocol bindings and required access were completed. Install the subset that exists if reconstructing in stages.

The rebuild service installer runs the current server with --no-poll. This disables only the retired single-Honeygain compatibility poller: the six independent observers and PacketStream metadata worker remain active. The original machine's dashboard plist still contained SALAD_CONTAINER_GROUP=hg-live-c438, SALAD_EXPECTED_REPORTERS=1 and no --no-poll; those fields do not define the root Honeygain fleet. Do not rebuild a dependence on that obsolete group. The root website source and its six displayed services are unchanged.

7. Open http://127.0.0.1:8787/ and check each tab. Wait for actual first samples; downloading or unassigned replacements are normal transitions, not measured zero-traffic clients.

## Services and startup dependencies

| Service label | Program under installed root |
|---|---|
| com.cosmosgeek.salad-bandwidth-dashboard | python3 -m dashboard.server --port 8787 --data-dir ~/.hg1 --no-poll |
| com.cosmosgeek.salad-hg-provider-observer | scripts/hg-provider-observer.py --interval 60 |
| com.cosmosgeek.salad-hg-fleet-observer | scripts/hg-fleet-observer.py --interval 60 |
| com.cosmosgeek.salad-fleet-test-recorder | fleet-test-recorder.py run |
| com.cosmosgeek.ps1-recorder | ps1-native-recorder.py → native-census.py |
| com.cosmosgeek.proxyrack-recorder | proxyrack.py observe |
| com.cosmosgeek.repocket-recorder | repocket-monitor/observe.py |
| com.cosmosgeek.earnfm-recorder | scripts/earnfm-recorder.py |
| com.cosmosgeek.tm-observer | traffmonetizer/observer.py |

All are user LaunchAgents with KeepAlive and a common installed working directory/PYTHONPATH. They run while that user's launchd session is available. If the Mac sleeps or shuts down, local recording pauses; the cloud clients and their IMDS recovery still run. Backfill is limited by retained upstream logs and implemented lookback/cursor behavior. Do not promise lossless recording through unlimited downtime.

The helper's install-services.py --write-only option writes inspectable plists without loading them. To inspect/restart an installed service:

~~~~bash
launchctl print "gui/$(id -u)/com.cosmosgeek.salad-bandwidth-dashboard"
launchctl kickstart -k "gui/$(id -u)/com.cosmosgeek.salad-bandwidth-dashboard"
~~~~

Use the relevant label for an observer. Do not restart or reset the whole fleet to change a website file.

## Data sources and route contract

| Tab / route | Local source and important semantics |
|---|---|
| HG /api/fleet-test?service=hg | fleet-tests observations/current/network-state plus hg-fleet original timestamps and provider readings; estimated minute allocation |
| PS /api/ps1/minutes | packetstream/minutes.sqlite3 and native-census.json; exact V2 minutes, estimated legacy intervals |
| PS minute ?minute=UTC_MS | Same ledger, top contributor detail for the selected UTC minute |
| PS /api/ps1/view | Provider readings and deployment metadata; private bridge token is local-only |
| PR /api/proxyrack | proxyrack/view.json plus traffic.sqlite3 filtered by current group_id |
| RP /api/repocket?chart=1 | repocket/view.json, optional provider.json, all retained minute events in traffic.sqlite3 |
| RFM /api/earnfm | installed dashboard/static/earnfm.json written by its recorder |
| TM /api/traffmonetizer?chart=1 | traffmonetizer/latest.json and traffic.sqlite3 with recorded-test boundary |

Public data contains status, IDs, timestamps and measured values. Secret credentials stay in Keychain/process memory. Legacy /api/series, /api/boxes and export routes remain in the preserved server, but are not the root six-tab data sources.

| Storage | Retain/restore |
|---|---|
| ~/.hg1/hg-fleet | Original timestamps/instances, counters, provider-readings JSONL and current safe snapshots |
| ~/.hg1/fleet-tests | current.json, observations.jsonl, network-state.json, latest.json, events.jsonl, archives |
| ~/.hg1/packetstream | observer-target.json, minutes.sqlite3, native-census.json, provider-observations.jsonl, period files |
| ~/.hg1/proxyrack | deployment.json, traffic.sqlite3, provider.json, view.json |
| ~/.hg1/repocket | deployment.json, traffic.sqlite3, cursor.json, provider.json, view.json |
| ~/.hg1/earnfm | target.json, traffic.sqlite3, provider.json, provider-baseline.json |
| ~/.hg1/traffmonetizer | deployment.json, traffic.sqlite3, latest.json; provider/error/cursor data is also in the DB |
| Installed dashboard/static/earnfm.json | RFM's published output, regenerated from its ledger |

SQLite tables are defined in the embedded source. Use SQLite's backup API or stop the associated writer before copying a database; copying only a live .sqlite3 file can omit committed WAL pages. Restore a recorder cursor only together with the matching ledger, or it may skip missing history. Do not store provider sessions or cloud environment dumps with a public source backup.

## Measurement and status rules that must not be lost

1. **Units:** decimal MB; bytes / 1,000,000. MB/min comes from the measured interval duration. KB/s × 0.06 = decimal MB/min.
2. **One source per number:** platform-running count, native acceptance, raw network traffic and provider credit use different evidence. They are not interchangeable.
3. **Time:** store original source timestamps and run IDs. Preserve timezone offsets; normalize non-six-digit fractions for Python 3.9. Render the viewer's local clock, but bucket by Unix UTC minutes.
4. **Counter resets:** never difference counters across instances, boots, runs or an IP handover. Keep missing/excluded samples as boundaries.
5. **Partial data:** the chart distinguishes gaps, partial/estimated bars and genuine observed zero. No smoothing into fabricated traffic.
6. **Current slots:** a fresh short inventory gets explicit Unassigned/Awaiting inventory rows. These have no IP/metrics. A stale inventory's counts remain unknown; it is not a fresh allocation fact.
7. **Transitions:** actual allocating/downloading/creating/stopping/stopped state overrides a stale positive client flag and suppresses current rate/confirmed status.
8. **Honeygain spike exclusion:** 96.246.178.36 is excluded from HG chart/display totals; its observations remain interval boundaries. Historical raw JSONL is not rewritten. If the ledger is truncated, the adjusted lifetime total becomes unknown rather than reintroducing removed traffic.
9. **HG performance:** the HG-only reader deduplicates identical source snapshots and caches output for five seconds; original source timestamps/run identities are reconciled using matching original observations. Do not rebuild the entire per-worker history on every UI paint.
10. **Provider data:** PacketStream requires actual baseline/follow-up samples; RP provider-day totals are not per-node earnings; RFM reports baseline balance change; TM reports provider baseline-adjusted traffic/earnings. Missing/stale sources must remain labelled.

## What happened, and how to avoid repeating it

| Observed problem | Resolution preserved in the code |
|---|---|
| Many separate pages/graphs/new windows | Shared root HTML, one reusable chart factory, same-page service adapters |
| Short timeline and thick bars | 1/6/12/24h windows with one-minute narrow bars |
| Selecting a candle created a permanent extra list | Temporary hover/click popup with top-20 IP/country/MB |
| Live rows vanished during replacement | Explicit unassigned slots; no fake IDs shown as IPs |
| “Unverified” masked a known download/stopping state | Use known platform transition and do not count it as a working client |
| Healthy customer traffic caused automatic rotation | Do not treat one failed customer destination or missing diagnostic stream alone as a failed control connection |
| Recovered TM client was immediately replaced | Positive current health resets outage timing; continuing stats protect against status-only delay |
| RFM showed a single-second zero/huge extrapolation | Use the recorded 60-second window and actual interval duration |
| RFM showed “provider offline” while telemetry was simply delayed | Separate provider membership, provider freshness, telemetry freshness and container state |
| Proxyrack included about 179 MB from a deleted deployment | Scope source history/totals by the current group ID |
| Proxyrack running count was actually a client label | Publish raw Salad state separately |
| API ID changed while RP logs still used the old runtime ID | Match current machine and boot/sample boundary; retain both IDs |
| TM stale status was ingested as a confirmed disconnect | Preserve the wrapper's explicit uncertainty state |
| UI displayed raw RX+TX as paid traffic | Keep provider credits/earnings separate |
| Raw shell/Python chunks lost whitespace on deployment | Base64 source transport plus source/hash readback |
| Old scripts silently targeted retired ps1/hg-live-c438 | Explicit current target files and independent recorder setup |

The cloud policies remain the protocol implementations' responsibility. Honeygain rejects unusable/overused networks and handles exits/connection deadlines. PacketStream handles explicit IP/client failures and communication deadlines. Proxyrack distinguishes its home connection from SOCKS destinations and paces provider API registration. Repocket uses control health and its documented low-traffic observation window. RFM honors actual provider cooldowns. TM separates positive health, confirmed failure and no command replies. The website displays those facts; it is not an always-on cloud controller.

## Rebuild validation

Measured recheck on 7 September 2026: the printed extractor restored all 43 source files from this document alone. The restored suite passed 57 Python tests and 22 JavaScript tests. A fresh isolated installation produced nine valid LaunchAgent plists without loading them; an actual local HTTP server returned 200 on eleven tested routes. The Keychain helper compiled from embedded Swift. Fresh binding and baseline preservation were exercised with simulated external responses, including duplicate-observer rejection. Runtime source matched the current editable/installed source; included test files and the Swift helper source were compared with the editable originals.

After extraction, these checks require no cloud mutations:

~~~~bash
python3 -m unittest dashboard.tests.test_native_network dashboard.tests.test_server dashboard.tests.test_fleet_test
node --test dashboard/tests/test_view_model.cjs dashboard/tests/test_provider_bridge.cjs
~~~~

Node 18+ is adequate for these tests. Check the source files themselves if a future Node version changes its test runner.

The source snapshot's quick dashboard suite passed 57 Python tests and 22 JavaScript tests during the original run. The latest status correction was additionally tested against transition, missing-slot, stale-feed and stopped-client cases and reviewed with Astra. Historical legacy HG observer tests that expect an absent native-state file are not the reconstruction acceptance suite.

Live checks:

- HTTP 200 for / and all currently configured service routes.
- Six exact tab names; switching tabs does not open windows.
- 1/6/12/24 selector; one chart; popup contributor sum and units agree with that candle.
- Known stopped/downloading rows cannot count as working or show a live rate.
- No invented IP/bytes/earnings on pending rows; stale sources retain honest unknowns.
- Compare at least one native sample's byte delta and duration directly to its row/bar.
- Verify actual provider credit timestamps separately.
- Verify a recovery with both an accepted native IMDS request and fresh evidence on the replacement.

Do not restart the experimental baseline to make a test pass or make a graph look smooth.

## Data-loss scenarios

**Source lost, data/cloud survives:** extract the source, restore Keychain, retain existing ~/.hg1 metadata/databases/cursors, and install the named jobs. Do not run fresh initializers over preserved data.

**Mac data lost, cloud survives:** extract, restore credentials, bind current groups, take fresh provider baselines and start new recording. The parsers retain whatever upstream log history they can still fetch; do not claim that recreates all prior observations.

**Cloud and local data lost:** rebuild each protocol using its document, then bind newly returned IDs and begin new baselines. Use the source appendices here for the local website/collectors. Vendor accounts, registries or separately archived images still must exist.

**A single recorder breaks:** inspect its log and target ID, repair only its source/credentials/cursor issue, preserve the ledger, restart only that LaunchAgent. Missing telemetry is not permission to discard a healthy workload.

## Complete source appendix

This appendix contains the site's full active source plus local collectors and rebuild-only helpers. It intentionally does not contain passwords, session tokens, old traffic databases, compiled binaries, or unrelated experimental projects.

| Restored file | SHA-256 |
|---|---|
| dashboard/__init__.py | 9e72baa6472e739d23291c979acefeba840fee3e9075376a188bf94f66f8f106 |
| dashboard/fleet_test.py | 135ddc358e127a15904b1e34d4ada9b65cb13fc54e3bc4f01369d747828844f1 |
| dashboard/native_network.py | 7aebbb480bab2244e47d768994e8530bec1c529bc819e7878875c6b99e2f8a7d |
| dashboard/packetstream.py | 739b686480b8839fa9c1bb95abddc2cf74db1bea66b76a549a96b82653916848 |
| dashboard/ps-paid-feed.js | a0809b7941d4cb91621cd499a383161e7a0005644ba3f24f3dc0747b0dad6acc |
| dashboard/salad_api.py | fdfad086f5d12cfcc69dd0f3012ffc7502a84b14ffdf172bd7009159ccde5f86 |
| dashboard/server.py | 436a98372e33f7d261707c670b3afee82270b3f379455b0fd07732a07768f808 |
| dashboard/static/app.js | 38c6274f51db69144d5dff2d322c57ce24c6666d2ff535839e50af2f0587778d |
| dashboard/static/earnfm.html | 9768ffd672bff19c43cbd96effca4f0b4617f775a28e1b5241c92efb39c4a458 |
| dashboard/static/fleet-test.js | 249c8547b6ae702c92cc954f8b0453ec280f9e08366c604df7dddb521dd2fe89 |
| dashboard/static/index.html | ee39d93054a6f9d5088780ee5edd41617998189df4870f6bbd9e895853decb3a |
| dashboard/static/ps1.js | a386aacc6db63b407dfa846d328b2860f98e6af6dfaabde98dc4382f57356558 |
| dashboard/static/styles.css | b7c37ee6cd698d1b327a51a62849a51d817435d166170a70791ebb6e68d7c9eb |
| dashboard/store.py | 1217de0c6e729cb87df4eae1d8842ebd518ef83774d82e9048ccb8ea9f37f0da |
| dashboard/tests/__init__.py | 01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b |
| dashboard/tests/test_fleet_test.py | 908709935eb4ee437689fe31061564636a0acb90f5662185bf236f5dc92afbc6 |
| dashboard/tests/test_native_network.py | 801c579a921e1f437825b0e1244905044047af685b0e6823e67c5037a1fabab5 |
| dashboard/tests/test_provider_bridge.cjs | dd36f307903409f578c0cfd02dd5f24a7fd4c79dc1229f1748f305c2f23a4f9c |
| dashboard/tests/test_server.py | 98bbfd4e883371e12a6c6da825445c610085e9d5ea399789adf7369049fe8e17 |
| dashboard/tests/test_store.py | d1bed50aaf2381bdedc65c60ceb06287671d9f3cf6060d45bf0e5bfb8eb61bc5 |
| dashboard/tests/test_view_model.cjs | fa0b6ae89dbdfb420156cf5daf8239e529e715d067e25ee84526758cdc10c601 |
| dashboard/traffmonetizer.py | 7ec44b146c1b3e3ea5466f336488489744a2b92bdab300808e5da31a7ef31396 |
| fleet-test-recorder.py | a82594851df4c0ea52daadb1d751ebcd13ac47954e6fa0913933a0174a43bd24 |
| packetstream-monitor/audit-client-status.py | dedb9113f45026be32a9a8e80d74da971e31ef3b462a3e6d55766ac8abab46b4 |
| packetstream-monitor/native-census.py | 400b1d22f26fab942eaf503940b94f4fdac1bf8c3b75a3d5ead12302ca5e16f8 |
| packetstream-monitor/native-network.py | 6c656033e0ca0121885da58a740f3df5fe614e5ed5af776037d6bd6e046e9f7c |
| packetstream-monitor/start-with-recovery.sh | a1352f21f52114bfdb716894303b29dc2d7cff1f9893950904716c1dd5ee2dbf |
| proxyrack.py | c349057ac0510e0ce70ff039277604409f44163ebf8e486bb0f52c60dbd88965 |
| ps1-native-recorder.py | a950adc2e25afad35a0085c1830ad681e5a4351f31fc46ef3f55134f00c63138 |
| repocket-monitor/observe.py | 6c52ef8591ad9b02425517c4f82b4fd2972d044c1865e96c0598fe6239c1030c |
| scripts/bind-website.py | f5945882e7e73e52b137d75e87489393d8aa982da89876d9a9c05b397aacb7d0 |
| scripts/earnfm-recorder.py | c75d268026c83b041c5d9634a7a6bfd4e170f32c8fc0db886968889a610fa75d |
| scripts/hg-fleet-control.py | 636784169bc0a3fd77eecba964f5c474b697bb4ac9f767d9db5fa510b820bcf0 |
| scripts/hg-fleet-observer.py | 419bc42de81169a8f1893411c600f3097ac24498f77083abb7033ab4ecbb2c01 |
| scripts/hg-provider-observer.py | df6011522bffec291015a596646590f2866a2955cdd49488ad9337e8ba6e863e |
| scripts/initialize-recording.py | 4ac3beac391fd2f7e3f52896b62ab2a201a40268161f10e004886832ac984f74 |
| scripts/install-services.py | 3c75ac6e7c82f8b1e06104d59b02c13b073685e0c5f19a4a25a3e7534a7ee4e9 |
| scripts/keychain-store.swift | 490eadaf1afb87a0f64bf6248254ccc48ac1171af9e2fc4c796c74c12c5ca045 |
| scripts/publish-repocket-reading.py | bb310b4accf6292b40fd6accc5139173cdbdc4cc3230203919be9d1cb9970053 |
| scripts/rebuild-cloud.py | 4fde37bb6ea6402a3ab1ce7fe46d935503ee7b6038af0f3c2ec48c0c401c08b9 |
| scripts/save-secret.py | 98e37bb083dd0c10773d1dfdc187780af29f7a62beb361cfc99ec0fc92822e9e |
| traffmonetizer/control.py | e3c8774bf4e75e9b25133152f8d42d24f7410358944d07245fa409506e82799e |
| traffmonetizer/observer.py | 44cf8579c09486a448497c87191b81cba74e39bfd230a84681ed8a7dd9ad6bca |

### dashboard/__init__.py

<!-- rebuild-file: dashboard/__init__.py sha256=9e72baa6472e739d23291c979acefeba840fee3e9075376a188bf94f66f8f106 -->
~~~~~~python
"""Local Salad bandwidth dashboard."""
~~~~~~

### dashboard/fleet_test.py

<!-- rebuild-file: dashboard/fleet_test.py sha256=135ddc358e127a15904b1e34d4ada9b65cb13fc54e3bc4f01369d747828844f1 -->
~~~~~~python
"""Read-only, bounded independent-fleet experiment reporting.

Network counters and provider account credits have separate units and clocks.
Never infer paid traffic from interfaces, or client acceptance from Salad state.
"""

from __future__ import annotations

import csv
from bisect import bisect_left, bisect_right
from copy import deepcopy
from datetime import datetime
import io
import json
import math
import re
import threading
import time
from pathlib import Path

from dashboard.native_network import instance_run


BUCKET_MS = 600_000
GAP_MS = 180_000
MAX_BYTES = 128 * 1024 * 1024
MAX_ROWS = 20_000
MAX_BUCKETS = 2016  # Two weeks; older observations remain on disk.
MAX_TIMELINE_INTERVALS = 2000
HG_ERROR_CODES = frozenset({"device_limit", "device_already_active", "network_overused", "network_unusable", "authorization_error", "disconnected"})
HG_EXCLUDED_IPS = frozenset({"96.246.178.36"})


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def pick(source, strings=(), numbers=()):
    source = source if isinstance(source, dict) else {}
    result = {key: str(source[key])[:200] if source.get(key) is not None else None for key in strings}
    result.update({key: number(source.get(key)) for key in numbers})
    return result


def clean_hg_error(value):
    # Observer exception messages may contain private URLs or credentials.
    if isinstance(value, str) and value in HG_ERROR_CODES:
        return value
    return "observer_error" if value else None


def clean_ps_error(value):
    if isinstance(value, str) and "PacketStream allows packeting from 1 client per IP address." in value:
        return "duplicate_ip"
    return "client_error" if value else None


def timestamp_ms(value):
    if not isinstance(value, str) or len(value) > 100:
        return None
    try:
        # Salad emits seven fractional digits; older Python accepts six.
        value = re.sub(r"\.(\d+)(?=[+-])", lambda m: "." + m.group(1)[:6].ljust(6, "0"), value.replace("Z", "+00:00"))
        stamp = datetime.fromisoformat(value)
        return int(stamp.timestamp() * 1000) if stamp.tzinfo else None
    except (ValueError, OverflowError, OSError):
        return None


def clean_experiment(raw):
    result = pick(raw, ("id", "started_at", "status", "phase"), ("started_ms",))
    result["ps"] = pick(raw.get("ps"), ("organization", "group"), ("desired", "baseline_provider_bytes"))
    result["hg"] = pick(raw.get("hg"), ("organization", "phase"),
                        ("desired", "baseline_provider_gathering_credits", "baseline_provider_observed_ms", "baseline_started_ms"))
    result["archive_name"] = Path(str(raw.get("archive_path", ""))).name or None
    # Action descriptions are deliberately omitted: raw operational logs may
    # carry credential-bearing URLs. Only the intervention's time/type is public.
    result["interventions"] = [pick(row, ("service", "action", "recorded_at"), ("time_ms",))
                               for row in raw.get("interventions", [])[-100:] if isinstance(row, dict)]
    return result


def clean_observation(raw):
    result = pick(raw, ("recorded_at", "experiment_id", "phase"), ("time_ms",))
    ps = raw.get("ps") or {}
    hg = raw.get("hg") or {}
    result["ps"] = pick(ps, (), ("running", "reporting", "accepted", "monitor_connections", "provider_bytes", "provider_observed_ms",
                                 "network_rx_bytes", "network_tx_bytes", "network_total_bytes", "network_observed_ms", "status_observed_ms"))
    result["ps"]["network_complete"] = ps.get("network_complete") is True
    result["ps"]["workers"] = [{**pick(w, ("machine", "run", "ip", "state", "client_status", "sample_source"),
                                      ("network_bytes", "received_age_ms", "client_status_age_ms", "source_age_ms", "source_granularity_seconds", "last_interval_seconds")),
                                "native_status_only": w.get("native_status_only") is True or w.get("sample_source") in {"native_status_only", "sysfs_via_salad_logs_1s", "native_sysfs_1s"},
                                "error_code": clean_ps_error(w.get("error"))}
                                 for w in ps.get("workers", [])[:50] if isinstance(w, dict)]
    result["ps"]["native_status_only"] = ps.get("native_status_only") is True or any(w["native_status_only"] for w in result["ps"]["workers"])
    result["hg"] = pick(hg, (), ("running", "connected", "desired", "provider_gathering_credits", "provider_observed_ms",
                                 "network_rx_bytes", "network_tx_bytes", "network_total_bytes", "network_observed_ms", "status_observed_ms"))
    result["hg"]["network_complete"] = hg.get("network_complete") is True
    result["hg"]["workers"] = [{**pick(w, ("group", "device", "machine", "run", "ip", "state", "client_status"),
                                      ("credits", "credit_observed_ms", "network_bytes", "received_age_ms", "sample_ms")),
                                "error_code": clean_hg_error(w.get("error"))}
                                 for w in hg.get("workers", [])[:50] if isinstance(w, dict)]
    result["collection_error"] = bool(raw.get("errors") or raw.get("error"))
    return result


def distinct_points(points):
    unique = {}
    for at, value, complete in points:
        previous = unique.get(at)
        if previous:
            # Conflicting counters at one source time cannot support a rate.
            value = value if value == previous[1] else None
            complete = complete and previous[2]
        unique[at] = (at, value, complete)
    return sorted(unique.values())


def window_counter(rows, counter, timestamp, start_ms, end_ms):
    points = distinct_points((source[timestamp], number(source.get(counter)), source.get("network_complete") is True)
                             for row in rows for source in (row["ps"],)
                             if number(source.get(timestamp)) is not None and start_ms <= source[timestamp] <= end_ms)
    values = [p[1] for p in points]
    delta = values[-1] - values[0] if len(values) >= 2 and all(v is not None for v in values) and all(b >= a for a, b in zip(values, values[1:])) else None
    return points, delta


def measured_interval(previous=None, current=None, gap_ms=GAP_MS):
    result = {"start_ms": previous[0] if previous else None, "end_ms": current[0] if current else None,
              "delta": None, "per_second": None, "complete": False, "status": "missing"}
    if not previous or not current or previous[1] is None or current[1] is None:
        return result
    elapsed = current[0] - previous[0]
    if elapsed <= 0:
        return result
    if current[1] < previous[1]:
        result["status"] = "counter_reset"
        return result
    result["delta"] = current[1] - previous[1]
    if elapsed > gap_ms:
        result["status"] = "gap"
        return result
    result["complete"] = previous[2] and current[2]
    result["status"] = "complete" if result["complete"] else "incomplete"
    # A partial sum is useful activity evidence, but never full-fleet coverage.
    result["per_second"] = result["delta"] * 1000 / elapsed
    return result


def rate_timeline(rows, started_ms, end_ms, hg_started_ms=None, ps_started_ms=None):
    timeline = {service: {metric: [] for metric in ("network", "provider")} for service in ("ps", "hg")}
    truncated = False
    for service, metric, counter, timestamp in (
        ("ps", "network", "network_total_bytes", "network_observed_ms"),
        ("ps", "provider", "provider_bytes", "provider_observed_ms"),
        ("hg", "network", "network_total_bytes", "network_observed_ms"),
        ("hg", "provider", "provider_gathering_credits", "provider_observed_ms"),
    ):
        start = max(started_ms, hg_started_ms or started_ms) if service == "hg" and metric == "provider" else started_ms
        if service == "ps":
            start = max(start, ps_started_ms or start)
        points = []
        for row in rows:
            source = row.get(service) or {}
            at = number(source.get(timestamp))
            # Missing source timestamps never become recorder-time observations.
            if at is not None and start <= at <= end_ms:
                points.append((at, number(source.get(counter)), metric != "network" or source.get("network_complete") is True))
        points = distinct_points(points)
        truncated = truncated or len(points) - 1 > MAX_TIMELINE_INTERVALS
        points = points[-MAX_TIMELINE_INTERVALS - 1:]
        gap = 420_000 if service == "hg" and metric == "provider" else GAP_MS
        timeline[service][metric] = [measured_interval(a, b, gap) for a, b in zip(points, points[1:])]
    return timeline, truncated


def worker_identity(worker):
    identity = tuple(worker.get(field) for field in ("group", "device", "machine", "run"))
    return identity if any(identity) else None


def worker_sample_time(service, source, worker, row_ms):
    if service == "hg" and number(worker.get("sample_ms")) is not None:
        return worker["sample_ms"]
    if service == "ps":
        sample_age = number(worker.get("source_age_ms"))
        if sample_age is None:
            sample_age = number(worker.get("received_age_ms"))
        base = row_ms
    else:
        sample_age = number(worker.get("received_age_ms"))
        base = number(source.get("status_observed_ms"))
    if sample_age is not None and base is not None:
        return base - sample_age
    return number(source.get("network_observed_ms"))


def worker_intervals(rows, latest, started_ms, now_ms, ps_started_ms=None):
    for service in ("ps", "hg"):
        start = max(started_ms, ps_started_ms or started_ms) if service == "ps" else started_ms
        series = {}
        for row in rows:
            source = row.get(service) or {}
            for worker in source.get("workers", []):
                identity = worker_identity(worker)
                at = worker_sample_time(service, source, worker, row["time_ms"])
                if identity is not None and at is not None and start <= at <= now_ms:
                    series.setdefault(identity, []).append((at, number(worker.get("network_bytes")), True))
        for worker in latest[service]["workers"]:
            points = distinct_points(series.get(worker_identity(worker), []))
            current = points[-1] if points else None
            value = measured_interval(points[-2] if len(points) >= 2 else None, current)
            if worker.get("network_bytes") is None:
                value = measured_interval()
            elif current and now_ms - current[0] > (60_000 if service == "ps" else 120_000):
                value.update(per_second=None, complete=False, status="stale")
            worker["network_interval"] = value
            worker["network_first_ms"] = points[0][0] if points else None
            worker["network_last_ms"] = current[0] if current else None


def honeygain_minutes(rows, started_ms, end_ms):
    end = int(end_ms)//60000*60000
    start = end-1439*60000
    series = {}
    for row in rows:
        source = row.get("hg") or {}
        for worker in source.get("workers", []):
            at = worker_sample_time("hg", source, worker, row["time_ms"])
            value = number(worker.get("network_bytes"))
            identity = worker_identity(worker)
            if identity is not None and at is not None and max(started_ms,start-GAP_MS) <= at <= end_ms:
                series.setdefault(identity, []).append((at,value,worker.get("ip")))
    buckets = {}
    for identity, values in series.items():
        unique = {}
        for at,value,ip in values:
            point=(value,ip)
            unique[at]=point if at not in unique or unique[at]==point else (None,None)
        points=[(at,*point) for at,point in sorted(unique.items())]
        for previous, current in zip(points,points[1:]):
            if previous[2] != current[2]:
                continue
            interval = measured_interval((*previous[:2],True),(*current[:2],True))
            if interval["per_second"] is None:
                continue
            first,last = interval["start_ms"],interval["end_ms"]
            for minute in range(max(start,int(first)//60000*60000),min(end,int(last-1)//60000*60000)+1,60000):
                overlap = min(last,minute+60000)-max(first,minute)
                if overlap <= 0:
                    continue
                contribution = buckets.setdefault(minute,{}).setdefault(identity+(current[2],),{"instance":"/".join(x or "" for x in identity),"ip":current[2],"mb":0})
                contribution["mb"] += interval["delta"]*overlap/(last-first)/1e6
    result=[]
    for minute in range(start,end+1,60000):
        nodes=sorted(buckets.get(minute,{}).values(),key=lambda n:(-n["mb"],n["instance"]))
        result.append({"minute_ms":minute,"mb":sum(n["mb"] for n in nodes) if nodes else None,
                       "partial":True,"estimated":True,"count":len(nodes),"nodes":nodes[:20]})
    return result


def measured_delta(points, start, end, *, final=False, gap_ms=GAP_MS):
    selected = points[bisect_left(points, (start,)):bisect_right(points, (end, float("inf"), True))]
    result = {"delta": None, "per_10_min": None, "coverage_seconds": 0, "status": "missing", "change_percent": None}
    if len(selected) < 2:
        return result
    elapsed = selected[-1][0] - selected[0][0]
    result["coverage_seconds"] = elapsed / 1000
    if any(b[1] < a[1] for a, b in zip(selected, selected[1:])):
        result["status"] = "counter_reset"
        return result
    result["delta"] = selected[-1][1] - selected[0][1]
    if any(b[0] - a[0] > gap_ms for a, b in zip(selected, selected[1:])):
        result["status"] = "gap"
    elif any(not point[2] for point in selected):
        result["status"] = "incomplete"
    elif elapsed < BUCKET_MS * .9 or selected[0][0] - start >= 60_000 or end - selected[-1][0] >= 60_000 or final:
        result["status"] = "partial"
    else:
        result["status"] = "complete"
        result["per_10_min"] = result["delta"] * BUCKET_MS / elapsed
    return result


def rate_buckets(rows, started_ms, end_ms):
    sources = {"ps_credited": [], "ps_network": [], "hg_credits": [], "hg_network": []}
    for row in rows:
        for metric, service, counter, timestamp, divisor in (
            ("ps_credited", "ps", "provider_bytes", "provider_observed_ms", 1_000_000),
            ("ps_network", "ps", "network_total_bytes", "network_observed_ms", 1_000_000),
            ("hg_credits", "hg", "provider_gathering_credits", "provider_observed_ms", 1),
            ("hg_network", "hg", "network_total_bytes", "network_observed_ms", 1_000_000),
        ):
            source = row.get(service) or {}
            value = number(source.get(counter))
            at = number(source.get(timestamp))
            if metric.endswith("_network") and at is None:
                at = number(row.get("time_ms"))
            if value is not None and at is not None and started_ms <= at <= end_ms:
                sources[metric].append((at, value / divisor, not metric.endswith("_network") or source.get("network_complete") is True))
    for key, points in sources.items():
        # Repeated stale provider readings are one observation, not zero-growth
        # samples. Keep an incomplete flag if any same-time sample is incomplete.
        unique = {}
        for point in points:
            previous = unique.get(point[0])
            unique[point[0]] = (point[0], point[1], point[2] and (previous[2] if previous else True))
        sources[key] = sorted(unique.values())
    count = min(MAX_BUCKETS, max(1, math.ceil((end_ms - started_ms) / BUCKET_MS)))
    first_index = max(0, math.ceil((end_ms - started_ms) / BUCKET_MS) - count)
    buckets = []
    for index in range(first_index, first_index + count):
        start = started_ms + index * BUCKET_MS
        end = min(end_ms, start + BUCKET_MS)
        bucket = {"start_ms": start, "end_ms": end, "open": end - start < BUCKET_MS}
        for metric, points in sources.items():
            bucket[metric] = measured_delta(points, start, end, final=bucket["open"], gap_ms=420_000 if metric == "hg_credits" else GAP_MS)
            current = bucket[metric]
            previous = buckets[-1][metric] if buckets else None
            if previous and current["per_10_min"] is not None and previous["per_10_min"]:
                current["change_percent"] = 100 * (current["per_10_min"] / previous["per_10_min"] - 1)
        buckets.append(bucket)
    return buckets


class FleetTestView:
    def __init__(self, root):
        self.root = Path(root)
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._hg_sources = (None, {})

    @staticmethod
    def read_json(path):
        with path.open("rb") as handle:
            data = handle.read(128 * 1024 + 1)
        if len(data) > 128 * 1024:
            raise ValueError("Experiment metadata is too large")
        raw = json.loads(data)
        if not isinstance(raw, dict):
            raise ValueError("Experiment metadata is invalid")
        return raw

    def service_windows(self, experiment, now_ms, archived=False):
        start = experiment["started_ms"] or now_ms
        windows = {service: {"start_ms": start, "basis": "test", "observed_ms": None,
                             "stale": False if archived or service == "hg" else True,
                             "state": "archived" if archived else "unknown"} for service in ("ps", "hg")}
        if archived:
            return windows, None
        try:
            census = self.read_json(self.root.parent / "packetstream" / "native-census.json")
            target = experiment["ps"]
            if not target.get("organization") or not target.get("group") or census.get("group") != f'{target["organization"]}/default/{target["group"]}':
                return windows, None
            group_state = census.get("group_state") or {}
            restarted = timestamp_ms(group_state.get("start_time"))
            observed = timestamp_ms(census.get("last_success_at") or census.get("checked_at"))
            if restarted is None or restarted > now_ms or observed is None or restarted > observed:
                return windows, None
            state = group_state.get("status")
            if state not in {"running", "stopped", "stopping", "pending", "starting", "allocating", "creating", "deploying", "failed", "succeeded"}:
                state = "unknown"
            windows["ps"].update(start_ms=max(start, restarted), basis="native_restart" if restarted > start else "test",
                                 observed_ms=observed, stale=not 0 <= now_ms - observed <= 90_000, state=state)
            nodes = census.get("nodes")
            if not isinstance(nodes, list):
                return windows, None
            runs = set()
            for node in nodes[:50]:
                if not isinstance(node, dict):
                    continue
                machine, instance = node.get("machine"), node.get("instance_id")
                if all(isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value) for value in (machine, instance)):
                    runs.add(machine + "/" + instance)
            return windows, {"observed_ms": observed, "runs": runs}
        except (OSError, ValueError, TypeError, AttributeError):
            return windows, None

    def archives(self):
        result = []
        archive_root = self.root / "archives"
        if not archive_root.is_dir():
            return result
        for child in sorted(archive_root.iterdir(), reverse=True)[:100]:
            if child.is_symlink() or not child.is_dir() or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", child.name):
                continue
            try:
                metadata = clean_experiment(self.read_json(child / "current.json"))
                result.append({"id": child.name, "started_ms": metadata["started_ms"], "status": metadata["status"]})
            except (OSError, ValueError):
                continue
        return result

    def snapshot(self, now_ms=None, archive=None, include_observations=False, honeygain_only=False):
        if now_ms is not None or archive or include_observations:
            return self._snapshot(now_ms, archive, include_observations, honeygain_only)
        with self._cache_lock:
            cached = self._cache.get(honeygain_only)
            if cached is None or time.monotonic() - cached[0] >= 5:
                cached = (time.monotonic(), self._snapshot(honeygain_only=honeygain_only))
                self._cache[honeygain_only] = cached
            return cached[1]

    def _snapshot(self, now_ms=None, archive=None, include_observations=False, honeygain_only=False):
        now_ms = int(time.time() * 1000) if now_ms is None else now_ms
        directory = self.root
        if archive is not None:
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", archive):
                raise ValueError("Invalid archive identifier")
            directory = self.root / "archives" / archive
            if directory.is_symlink() or directory.resolve().parent != (self.root / "archives").resolve():
                raise ValueError("Invalid archive identifier")
        try:
            experiment = clean_experiment(self.read_json(directory / "current.json"))
        except FileNotFoundError:
            return {"experiment": None, "warnings": ["Independent test recorder has not started."], "archives": self.archives()}
        rows, invalid, truncated = [], 0, False
        previous_hg = None
        source_path = self.root.parent / "hg-fleet" / "observations.jsonl"
        if source_path.exists() and self._hg_sources[0] != source_path.stat().st_mtime_ns:
            sources = {}
            source_stamp = source_path.stat().st_mtime_ns
            for line in source_path.open():
                try:
                    source = json.loads(line)
                    sources[source["time_ms"]] = {w["group"]: w for w in source.get("workers", [])}
                except (ValueError, KeyError):
                    continue
            self._hg_sources = (source_stamp, sources)
        path = directory / "observations.jsonl"
        if path.exists():
            with path.open("rb") as handle:
                size = path.stat().st_size
                if size > MAX_BYTES:
                    handle.seek(size - MAX_BYTES)
                    handle.readline()
                    truncated = True
                lines = handle.read(MAX_BYTES).splitlines()
            truncated = truncated or len(lines) > MAX_ROWS
            for line in lines[-MAX_ROWS:]:
                try:
                    raw = json.loads(line)
                    if not isinstance(raw, dict):
                        raise ValueError("Invalid observation")
                    if raw.get("experiment_id") == experiment["id"]:
                        hg = raw.get("hg") or {}
                        source_workers = self._hg_sources[1].get(hg.get("status_observed_ms"), {})
                        for worker in hg.get("workers", []):
                            original = source_workers.get(worker.get("group"), {})
                            sample = original.get("sample") or {}
                            if original.get("machine") == worker.get("machine") and number(sample.get("rx_total")) is not None and number(sample.get("tx_total")) is not None and sample["rx_total"] + sample["tx_total"] == worker.get("network_bytes"):
                                worker.update(sample_ms=timestamp_ms(sample.get("time")), run=original.get("instance"))
                        if honeygain_only:
                            key = hg
                            if rows and key == previous_hg:
                                rows[-1]["time_ms"] = raw["time_ms"]
                                rows[-1]["recorded_at"] = raw.get("recorded_at")
                                continue
                            previous_hg = key
                            raw["ps"] = {}
                        row = clean_observation(raw)
                        if row["time_ms"] is not None and row["time_ms"] >= (experiment["started_ms"] or 0):
                            rows.append(row)
                except (ValueError, TypeError, AttributeError):
                    invalid += 1
        rows.sort(key=lambda row: row["time_ms"])
        excluded_last, excluded_bytes = {}, 0
        for row in rows:
            hg = row["hg"]
            for worker in hg["workers"]:
                if worker.get("ip") not in HG_EXCLUDED_IPS:
                    continue
                identity, value = worker_identity(worker), worker.get("network_bytes")
                if identity is not None and value is not None:
                    previous = excluded_last.get(identity, value)
                    excluded_bytes += max(0, value - previous)
                    excluded_last[identity] = value
                worker["network_bytes"] = None
            if excluded_bytes and hg["network_total_bytes"] is not None:
                hg["network_total_bytes"] = max(0, hg["network_total_bytes"] - excluded_bytes)
                hg["network_rx_bytes"] = hg["network_tx_bytes"] = None
                hg["network_complete"] = False
            if truncated:
                hg["network_total_bytes"] = None
                hg["network_complete"] = False
        # Keep ledger source ages unchanged while advancing the live view clock.
        latest = deepcopy(rows[-1]) if rows else None
        if latest:
            latest["hg"]["workers"] = [w for w in latest["hg"]["workers"] if w.get("ip") not in HG_EXCLUDED_IPS]
        age = max(0, now_ms - latest["time_ms"]) if latest else None
        stale = age is None or age > GAP_MS
        start = experiment["started_ms"] or now_ms
        end = latest["time_ms"] if archive and latest else now_ms
        windows, census = self.service_windows(experiment, now_ms, archived=bool(archive))
        ps_start = windows["ps"]["start_ms"]
        warnings = []
        if not archive and windows["ps"]["stale"]:
            warnings.append("PacketStream restart census is stale, missing, or does not match this test target. The current run boundary is not freshly verified.")
        if stale and not archive:
            warnings.append("Recorder is stale or has no observations. Last values are historical, not live.")
        if invalid:
            warnings.append("An incomplete or invalid ledger line was skipped; the next refresh will retry.")
        if truncated:
            warnings.append("Showing the bounded ledger tail. Older records remain in the saved ledger.")
        if latest and latest["collection_error"]:
            warnings.append("A collector reported an error. Inspect its local recorder log.")
        timeline, timeline_truncated = rate_timeline(rows, start, max(start, end), experiment["hg"].get("baseline_provider_observed_ms"), ps_start)
        if timeline_truncated:
            warnings.append("The activity graph shows the latest 2,000 measured intervals per source. Older observations remain in history.")
        summary = {"ps_credited_mb": None, "ps_network_mb": None, "hg_gathering_credits": None, "hg_network_mb": None}
        if latest:
            ps, hg = latest["ps"], latest["hg"]
            ps["inventory_status"] = "ledger"
            if census and (census["observed_ms"] >= (ps["status_observed_ms"] or 0) or latest["time_ms"] < ps_start):
                current_workers = [w for w in ps["workers"] if instance_run(w.get("run")) in census["runs"] and latest["time_ms"] >= ps_start]
                if len(current_workers) != len(ps["workers"]):
                    ps["workers"] = current_workers
                    ps["inventory_status"] = "awaiting_current_run"
                    for field in ("running", "accepted", "reporting", "monitor_connections", "network_rx_bytes", "network_tx_bytes", "network_total_bytes", "network_observed_ms"):
                        ps[field] = None
                    ps["network_complete"] = False
                    warnings.append("PacketStream restarted or changed instances. Older container rows are hidden while the recorder catches up with the current census.")
                else:
                    ps["inventory_status"] = "matched"
            if ps_start > start:
                for worker in ps["workers"]:
                    client_age = worker.get("client_status_age_ms")
                    if client_age is not None and latest["time_ms"] - client_age < ps_start:
                        worker.update(client_status="unknown", client_status_age_ms=None, error_code=None)
            worker_intervals(rows, latest, start, end, ps_start)
            ps["status_age_ms"] = max(0, now_ms - ps["status_observed_ms"]) if ps["status_observed_ms"] is not None else None
            ps["status_stale"] = ps["status_age_ms"] is None or ps["status_age_ms"] > 90_000
            if ps["status_stale"] and not archive:
                warnings.append("PacketStream worker census is stale or missing. Running and accepted counts are last recorded states.")
            hg["status_age_ms"] = max(0, now_ms - hg["status_observed_ms"]) if hg["status_observed_ms"] is not None else None
            hg["status_stale"] = hg["status_age_ms"] is None or hg["status_age_ms"] > 120_000
            if hg["status_stale"] and not archive:
                warnings.append("Honeygain worker observer is stale or missing. Running and connected counts are last recorded states.")
            # Source ages were captured at different times. Advance them to the
            # current snapshot clock; a healthy fleet recorder cannot freshen an
            # old Honeygain observer or an old PacketStream client sample.
            for service, elapsed in ((ps, age), (hg, hg["status_age_ms"])):
                for worker in service["workers"]:
                    worker_elapsed = elapsed
                    for field in ("received_age_ms", "client_status_age_ms", "source_age_ms"):
                        # PS event ages are already measured against the fleet
                        # recorder clock, including native census events.
                        field_elapsed = age if service is ps and field == "client_status_age_ms" else worker_elapsed
                        if worker.get(field) is not None and field_elapsed is not None:
                            worker[field] += field_elapsed
                    if service is ps:
                        client_age = worker.get("client_status_age_ms")
                        worker["client_status_stale"] = stale or ps["status_stale"] or client_age is None or client_age > (240_000 if worker.get("native_status_only") else 120_000)
            for service, timestamp in ((ps, "provider_observed_ms"), (hg, "provider_observed_ms")):
                service["provider_age_ms"] = max(0, now_ms - service[timestamp]) if service[timestamp] is not None else None
            baseline, current = experiment["ps"].get("baseline_provider_bytes"), ps["provider_bytes"]
            paid_values = [r["ps"]["provider_bytes"] for r in rows if r["ps"]["provider_bytes"] is not None
                           and (r["ps"]["provider_observed_ms"] or 0) >= ps_start]
            paid_reset = any(b < a for a, b in zip(paid_values, paid_values[1:]))
            if baseline is not None and current is not None and current >= baseline and not paid_reset and (ps["provider_observed_ms"] or 0) >= start:
                summary["ps_credited_mb"] = (current - baseline) / 1_000_000
            if paid_reset:
                warnings.append("PacketStream's account counter decreased during this window. Its total delta is unknown.")
            summary["ps_network_mb"] = ps["network_total_bytes"] / 1_000_000 if ps["network_total_bytes"] is not None else None
            if ps_start > start:
                paid_points, paid_delta = window_counter(rows, "provider_bytes", "provider_observed_ms", ps_start, end)
                network_points, network_delta = window_counter(rows, "network_total_bytes", "network_observed_ms", ps_start, end)
                windows["ps"].update(provider_baseline_ms=paid_points[0][0] if paid_points else None,
                                     provider_baseline_bytes=paid_points[0][1] if paid_points else None,
                                     network_baseline_ms=network_points[0][0] if network_points else None)
                paid_fresh = paid_points and 0 <= now_ms - paid_points[-1][0] <= GAP_MS and not windows["ps"]["stale"]
                summary["ps_credited_mb"] = paid_delta / 1_000_000 if paid_delta is not None and paid_fresh else None
                summary["ps_network_mb"] = network_delta / 1_000_000 if network_delta is not None else None
                ps["network_complete"] = ps["network_complete"] and network_delta is not None and all(p[2] for p in network_points)
            summary["hg_network_mb"] = hg["network_total_bytes"] / 1_000_000 if hg["network_total_bytes"] is not None else None
            hg_baseline = experiment["hg"].get("baseline_provider_gathering_credits")
            hg_baseline_at = experiment["hg"].get("baseline_provider_observed_ms")
            explicit_hg_baseline = hg_baseline is not None and hg_baseline_at is not None
            hg_readings = sorted({r["hg"]["provider_observed_ms"]: r["hg"]["provider_gathering_credits"] for r in rows
                                 if r["hg"]["provider_gathering_credits"] is not None
                                 and (r["hg"]["provider_observed_ms"] or 0) >= (hg_baseline_at if explicit_hg_baseline else start)}.items())
            if explicit_hg_baseline:
                # The explicit reading is the independent Honeygain baseline;
                # never fall back to startup credits if later readings are absent.
                valid_hg = [hg_baseline] + [value for at, value in hg_readings if at > hg_baseline_at]
            else:
                valid_hg = [value for at, value in hg_readings]
            if len(valid_hg) >= 2 and all(b >= a for a, b in zip(valid_hg, valid_hg[1:])):
                summary["hg_gathering_credits"] = valid_hg[-1] - valid_hg[0]
            # Pad missing inventory without manufacturing running clients.
            for service in ("ps", "hg"):
                wanted = min(50, int(experiment[service].get("desired") or 10))
                while len(latest[service]["workers"]) < wanted:
                    latest[service]["workers"].append({"state": "unknown", "client_status": "unknown"})
        result = {"experiment": experiment, "latest": latest, "summary": summary, "observation_count": len(rows),
                  "recorder_age_ms": age, "recorder_stale": stale, "invalid_lines": invalid, "truncated": truncated,
                  "warnings": warnings, "archives": self.archives(), "archived": bool(archive),
                  "service_windows": windows,
                  "timeline": timeline, "timeline_truncated": timeline_truncated,
                  "hg_minutes": honeygain_minutes(rows, start, end),
                  "buckets": rate_buckets(rows, start, max(start, end)), "generated_ms": now_ms}
        if include_observations:
            result["observations"] = rows
        return result


def fleet_csv(snapshot):
    output = io.StringIO(newline="")
    fields = ["start_ms", "end_ms", "ps_network_mb", "ps_network_status", "ps_credited_mb", "ps_credited_mb_per_10_min",
              "ps_credited_change_percent", "ps_credited_coverage_seconds", "ps_credited_status", "hg_network_mb", "hg_network_status", "hg_gathering_credits", "hg_status"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for bucket in snapshot.get("buckets", []):
        writer.writerow({"start_ms": bucket["start_ms"], "end_ms": bucket["end_ms"],
                         "ps_network_mb": bucket["ps_network"]["delta"], "ps_network_status": bucket["ps_network"]["status"],
                         "ps_credited_mb": bucket["ps_credited"]["delta"], "ps_credited_mb_per_10_min": bucket["ps_credited"]["per_10_min"],
                         "ps_credited_change_percent": bucket["ps_credited"]["change_percent"],
                         "ps_credited_coverage_seconds": bucket["ps_credited"]["coverage_seconds"],
                         "ps_credited_status": bucket["ps_credited"]["status"],
                         "hg_network_mb": bucket["hg_network"]["delta"], "hg_network_status": bucket["hg_network"]["status"],
                         "hg_gathering_credits": bucket["hg_credits"]["delta"], "hg_status": bucket["hg_credits"]["status"]})
    return output.getvalue().encode("utf-8")
~~~~~~

### dashboard/native_network.py

<!-- rebuild-file: dashboard/native_network.py sha256=7aebbb480bab2244e47d768994e8530bec1c529bc819e7878875c6b99e2f8a7d -->
~~~~~~python
from contextlib import closing
"""Exact per-container minute records, durable storage, and dashboard summaries."""
from datetime import datetime
import ipaddress
from pathlib import Path
import re
import sqlite3
import threading
import time

UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z")
FIELDS = ("group_id", "instance", "machine", "observer", "seq", "start_ms", "end_ms",
          "rx", "tx", "total_rx", "total_tx", "ip", "state", "error", "final", "valid",
          "received_ms", "record_bytes", "bucket_ms")
ERRORS = {"communication_error": "Cannot communicate with PacketStream",
          "duplicate_ip": "PacketStream permits one client per public IP",
          "non_residential": "PacketStream rejected this IP as non-residential",
          "client_exited": "PacketStream client exited", "client_error": "PacketStream client reported an error; replacing this machine",
          "connection_timeout": "PacketStream did not connect within 60 seconds"}


def instance_run(value):
    parts = value.split("/") if isinstance(value, str) else []
    return "/".join(parts[:2]) if len(parts) >= 2 and all(UUID.fullmatch(p) for p in parts[:2]) else None


def stamp(value):
    if not value:
        return None
    value = re.sub(r"\.(\d+)(?=[+-])", lambda m: "." + m.group(1)[:6].ljust(6, "0"), value.replace("Z", "+00:00"))
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def parse_minute(item, group_id, received_ms=None):
    line = item.get("text_log", "")
    if not line.startswith(("PS_MINUTE_V1 ", "PS_MINUTE_V2 ")):
        return None
    try:
        values = dict(part.split("=", 1) for part in line.split()[1:])
        if not all(UUID.fullmatch(values[k]) for k in ("instance", "machine")):
            return None
        numbers = {key: int(values[key]) for key in
                   ("observer", "seq", "start_ms", "end_ms", "rx", "tx", "total_rx", "total_tx", "final")}
        if any(abs(v) > 2**53 - 1 for v in numbers.values()):
            return None
        if not (0 < numbers["observer"] <= numbers["start_ms"] <= numbers["end_ms"]
                and numbers["seq"] >= 0 and numbers["final"] in (0, 1)):
            return None
        if values["state"] not in ("starting", "running", "error", "exited", "reallocating"):
            return None
        ip = str(ipaddress.ip_address(values["ip"])) if values["ip"] != "-" else None
        result = dict(numbers, group_id=group_id, instance=values["instance"], machine=values["machine"],
                      ip=ip, state=values["state"], error=values.get("error", "none"),
                      valid=int(all(numbers[k] >= 0 for k in ("rx", "tx", "total_rx", "total_tx"))),
                      received_ms=received_ms or int(time.time() * 1000),
                      record_bytes=len(line.encode("utf-8")) + 1,
                      bucket_ms=int(values["bucket_ms"]) if "bucket_ms" in values else None)
        if result["bucket_ms"] is not None and (result["bucket_ms"] % 60000 or result["bucket_ms"] < 0):
            return None
        bucket = result["bucket_ms"]
        if bucket is not None and not bucket <= numbers["start_ms"] <= numbers["end_ms"] <= bucket + 60000:
            result["bucket_ms"] = None
        return result
    except (ValueError, KeyError, TypeError):
        return None


class NetworkMinutes:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS minutes (
                group_id TEXT, instance TEXT, machine TEXT, observer INTEGER, seq INTEGER,
                start_ms INTEGER, end_ms INTEGER, rx INTEGER, tx INTEGER,
                total_rx INTEGER, total_tx INTEGER, ip TEXT, state TEXT, error TEXT,
                final INTEGER, valid INTEGER, received_ms INTEGER, record_bytes INTEGER, bucket_ms INTEGER,
                PRIMARY KEY(group_id, instance, observer, seq));
            CREATE INDEX IF NOT EXISTS minutes_received ON minutes(group_id, received_ms);
            CREATE TABLE IF NOT EXISTS countries (ip TEXT PRIMARY KEY, country TEXT);
            CREATE TABLE IF NOT EXISTS collector (group_id TEXT PRIMARY KEY, time_ms INTEGER,
                cursor TEXT, error TEXT, inserted INTEGER);
        """)
        if "bucket_ms" not in {row[1] for row in self.db.execute("PRAGMA table_info(minutes)")}:
            self.db.execute("ALTER TABLE minutes ADD COLUMN bucket_ms INTEGER")
        self.db.commit()

    def ingest(self, records):
        inserted = 0
        with self.lock, self.db:
            for row in records:
                values = tuple(row.get(k) for k in FIELDS)
                result = self.db.execute("INSERT OR IGNORE INTO minutes VALUES (" + ",".join("?" * len(FIELDS)) + ")", values)
                inserted += result.rowcount
                if not result.rowcount:
                    old = self.db.execute(
                        "SELECT * FROM minutes WHERE group_id=? AND instance=? AND observer=? AND seq=?",
                        (row["group_id"], row["instance"], row["observer"], row["seq"])).fetchone()
                    core = [k for k in FIELDS if k not in ("received_ms", "record_bytes")]
                    if any(old[k] != row.get(k) for k in core if k != "valid"):
                        self.db.execute("UPDATE minutes SET valid=0 WHERE group_id=? AND instance=? AND observer=? AND seq=?",
                                        (row["group_id"], row["instance"], row["observer"], row["seq"]))
        return inserted

    def collector_status(self, group_id, cursor=None, error=None, inserted=0):
        with self.lock:
            if cursor is None:
                row = self.db.execute("SELECT * FROM collector WHERE group_id=?", (group_id,)).fetchone()
                return dict(row) if row else {}
            with self.db:
                self.db.execute("INSERT OR REPLACE INTO collector VALUES (?,?,?,?,?)",
                                (group_id, int(time.time() * 1000), cursor, error, inserted))

    def latest(self, group_id):
        with self.lock:
            rows = self.db.execute("""
                SELECT m.* FROM minutes m JOIN (
                    SELECT instance, MAX(observer) observer FROM minutes WHERE group_id=? GROUP BY instance
                ) r ON m.instance=r.instance AND m.observer=r.observer
                WHERE m.group_id=? AND m.seq=(SELECT MAX(seq) FROM minutes
                    WHERE group_id=m.group_id AND instance=m.instance AND observer=m.observer)
            """, (group_id, group_id)).fetchall()
            return {row["instance"]: dict(row) for row in rows}

    def minute(self, group_id, minute_ms):
        with self.lock:
            rows=self.db.execute("""SELECT m.*, c.country FROM minutes m LEFT JOIN countries c ON m.ip=c.ip
                WHERE m.group_id=? AND m.seq>0 AND m.valid=1 AND m.end_ms>=? AND m.start_ms<?""",
                (group_id,minute_ms,minute_ms+60000)).fetchall()
        points=bucket_minutes(rows,minute_ms,minute_ms)
        return points[0] if points else {"minute_ms":minute_ms,"mb":None,"count":0,"nodes":[]}

    def snapshot(self, census, now_ms=None):
        now = now_ms or int(time.time() * 1000)
        group_id = census.get("group_id", "")
        census_at = stamp(census.get("last_success_at") or census.get("checked_at"))
        census_fresh = census_at is not None and 0 <= now - census_at < 120_000 and not census.get("poll_error")
        current = {row["instance_id"]: row for row in census.get("nodes", [])}
        desired = int(census.get("desired_replicas") or len(current))
        end = now // 60000 * 60000
        start = end - 1439 * 60000
        nodes = []
        with self.lock, self.db:
            self.db.execute("BEGIN")
            latest = self.latest(group_id)
            rows=self.db.execute("SELECT * FROM minutes WHERE group_id=? AND valid=1 AND seq>0 AND end_ms>=? AND start_ms<?",(group_id,start,end+60000)).fetchall()
            points={p["minute_ms"]:p for p in bucket_minutes(rows,start,end)}
            candles=[]
            for minute in range(start,end+1,60000):
                point=points.get(minute)
                candles.append({"minute_ms":minute,"mb":point["mb"] if point else None,
                                "estimated":bool(point and point["estimated"]),
                                "partial":bool(not point or point["partial"] or point["count"]<desired or minute+60000>now)})
            for instance, member in current.items():
                last = latest.get(instance)
                observer = last["observer"] if last else None
                client = (member or {}).get("client_status") or {}
                client_at = stamp(client.get("source_time"))
                client_fresh = census_fresh and client_at is not None and -10_000 <= now - client_at <= 240_000
                state = client.get("state") if client_fresh else None
                error = client.get("message") if state == "error" else None
                if last and (not client_at or last["end_ms"] >= client_at) and -10_000 <= now - last["end_ms"] <= 150_000:
                    state = "stopped" if last["final"] and last["state"] == "running" else last["state"]
                    error = ERRORS.get(last["error"], last["error"]) if last["error"] != "none" else None
                salad_state = member.get("salad_state") if member else "previous"
                if not census_fresh:
                    label = "Status feed stale"
                elif state == "running":
                    label = "Running"
                elif state == "stopped":
                    label = "Stopped"
                elif state == "reallocating":
                    label = "Reallocating"
                elif state in ("error", "exited"):
                    label = "Error"
                elif salad_state != "running":
                    label = (salad_state or "starting").capitalize()
                else:
                    label = "Checking client"
                total, captured, latest_rate, first_at, last_at = None, 0, None, None, None
                gaps = False
                if last:
                    stats = self.db.execute("""
                        SELECT SUM(CASE WHEN valid=1 THEN rx+tx ELSE 0 END) recorded,
                               MIN(valid) valid, COUNT(CASE WHEN seq>0 THEN 1 END) count,
                               MIN(start_ms) first, MAX(end_ms) last, MAX(seq) seq
                        FROM minutes WHERE group_id=? AND instance=? AND observer=?
                    """, (group_id, instance, observer)).fetchone()
                    first_at, last_at = stats["first"], stats["last"]
                    gaps = stats["count"] < stats["seq"] or not stats["valid"]
                    total = (last["total_rx"] + last["total_tx"]) / 1e6 if stats["valid"] else stats["recorded"] / 1e6
                    captured = stats["count"]
                    seconds = (last["end_ms"] - last["start_ms"]) / 1000
                    if last["seq"] > 0 and last["valid"] and seconds > 0:
                        latest_rate = (last["rx"] + last["tx"]) / 1e6 * 60 / seconds
                metrics_fresh = last is not None and -10_000 <= now - last["end_ms"] <= 150_000 and not last["final"]
                nodes.append({"id": instance + "/" + str(observer or "pending"), "instance": instance,
                              "machine": member["machine"],
                              "current": True, "ip": last["ip"] if last else None,
                              "status": label, "salad_state": salad_state, "client_state": state, "error": error,
                              "start_ms": observer, "end_ms": last_at,
                              "elapsed_seconds": (last_at - first_at) / 1000 if first_at is not None else None,
                              "total_mb": total, "latest_mb_per_minute": latest_rate,
                              "minutes_recorded": captured, "metrics_fresh": bool(metrics_fresh),
                              "has_gaps": gaps, "sample_age_ms": now - last["end_ms"] if last else None})
            disk_minute = end - 60000
            saved = self.db.execute("""
                SELECT COUNT(*) records, COALESCE(SUM(record_bytes),0) bytes FROM minutes
                WHERE group_id=? AND received_ms>=? AND received_ms<?
            """, (group_id, disk_minute, disk_minute + 60000)).fetchone()
            totals = self.db.execute("SELECT COUNT(*) records, COALESCE(SUM(record_bytes),0) bytes, SUM(CASE WHEN valid=1 THEN rx+tx ELSE 0 END) network_bytes, MIN(start_ms) started_ms FROM minutes WHERE group_id=?", (group_id,)).fetchone()
        file_size = sum(path.stat().st_size for path in (self.path, Path(str(self.path) + "-wal")) if path.exists())
        return {"time_ms": now, "group": census.get("group"), "desired": desired, "assigned": len(current),
                "allocating": max(0, desired - len(current)), "inventory_fresh": census_fresh,
                "inventory_age_ms": now - census_at if census_at else None,
                "running": sum(n["status"] == "Running" for n in nodes),
                "errors": sum(n["status"] == "Error" for n in nodes),
                "nodes": nodes, "candles": candles, "collector": self.collector_status(group_id),
                "total_mb": totals["network_bytes"]/1e6 if totals["records"] else None, "started_ms": totals["started_ms"],
                "disk": {"minute_ms": disk_minute, "minute_bytes": saved["bytes"], "minute_records": saved["records"],
                         "total_record_bytes": totals["bytes"], "total_records": totals["records"],
                         "database_bytes": file_size,
                         "basis": "Telemetry payload bytes saved; excludes database/index overhead."}}


def saved_minutes(path, now_ms=None, group_id=None):
    """Read minute records from a provider's existing database without changing it."""
    now_ms = now_ms or int(time.time()*1000)
    first = now_ms//60000*60000 - 1439*60000
    if not Path(path).exists():
        return []
    with closing(sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)) as db:
        db.row_factory=sqlite3.Row
        query="SELECT * FROM minutes WHERE valid=1 AND seq>0 AND end_ms>=?"
        params=[first]
        if group_id is not None:
            query+=" AND group_id=?"
            params.append(group_id)
        rows=db.execute(query+" ORDER BY end_ms",params).fetchall()
    return bucket_minutes(rows,first,now_ms//60000*60000)


def bucket_minutes(rows, first, last):
    buckets={}
    for row in rows:
        start,end=row["start_ms"],row["end_ms"]
        amount=(row["rx"]+row["tx"])/1e6
        if end<start:
            continue
        exact=row["bucket_ms"]
        splits=[(exact,amount,False)] if exact is not None else []
        if exact is None and end==start:
            splits=[(end//60000*60000,amount,True)]
        elif exact is None:
            for minute in range(max(first,start//60000*60000),min(last,max(start,end-1)//60000*60000)+1,60000):
                overlap=min(end,minute+60000)-max(start,minute)
                if overlap>0:splits.append((minute,amount*overlap/(end-start),True))
        for minute,mb,estimated in splits:
            if not first<=minute<=last:
                continue
            bucket=buckets.setdefault(minute,{"minute_ms":minute,"mb":0,"estimated":False,"partial":False,"nodes":{}})
            bucket["mb"]+=mb;bucket["estimated"]|=estimated
            bucket["partial"]|=estimated or start!=minute or end!=minute+60000
            key=(row["instance"],row["machine"],row["ip"])
            node=bucket["nodes"].setdefault(key,{"instance":row["instance"],"machine":row["machine"],"ip":row["ip"],"country":row["country"] if "country" in row.keys() else None,"mb":0})
            node["mb"]+=mb
    result=[]
    for minute,bucket in sorted(buckets.items()):
        nodes=sorted(bucket["nodes"].values(),key=lambda n:(-n["mb"],n["instance"]))
        result.append(dict(bucket,count=len(nodes),nodes=nodes[:20]))
    return result
~~~~~~

### dashboard/packetstream.py

<!-- rebuild-file: dashboard/packetstream.py sha256=739b686480b8839fa9c1bb95abddc2cf74db1bea66b76a549a96b82653916848 -->
~~~~~~python
"""Paid-traffic readings and deployment membership for the PS dashboard.

Billing values come only from the authenticated provider page. Interface counters
are used for node identity, never converted into credited traffic.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import threading
import time
from urllib.parse import quote


def millis(value):
    if not value:
        return 0
    normalized = re.sub(r"(\.\d{6})\d+", r"\1", value.replace("Z", "+00:00"))
    return int(datetime.fromisoformat(normalized).timestamp() * 1000)


def paid_window(readings, start, end):
    selected = [r for r in readings if start <= r["time_ms"] <= end]
    # Rounded historical display readings must not be mixed with exact provider
    # byte records. Use the newest available measurement basis within the window.
    if selected:
        basis = selected[-1].get("basis", "display_gb")
        selected = [r for r in selected if r.get("basis", "display_gb") == basis]
    result = {"readings": selected, "mb": None, "mb_per_minute": None,
              "first_ms": None, "last_ms": None, "error": None}
    if len(selected) < 2:
        result["error"] = "Two provider readings are needed in this period."
        return result
    first, last = selected[0], selected[-1]
    result.update(first_ms=first["time_ms"], last_ms=last["time_ms"])
    if any(b["gb"] < a["gb"] for a, b in zip(selected, selected[1:])):
        result["error"] = "The provider's rolling counter decreased; this period cannot be measured reliably."
        return result
    amount = round((last["gb"] - first["gb"]) * 1000, 6)
    elapsed = last["time_ms"] - first["time_ms"]
    if elapsed <= 0:
        result["error"] = "The provider readings have no elapsed time."
        return result
    result.update(mb=amount, mb_per_minute=amount * 60000 / elapsed)
    return result


def ordered_nodes(raw_nodes, members, restart_ms, countries):
    newest = {}
    for n in raw_nodes:
        if n["start"] > newest.get(n["machine"], {}).get("start", -1):
            newest[n["machine"]] = n
    rows = []
    for n in raw_nodes:
        current = (n["machine"] in members and newest[n["machine"]]["run"] == n["run"]
                   and n["start"] * 1000 >= restart_ms - 2000)
        receipt_age, source_age = n.get("sample_age_ms"), n.get("source_sample_age_ms")
        sample_source = n.get("sample_source")
        receipt_limit = 25000 if sample_source == "salad_logs_10s" else 15000
        fresh = (n.get("samples", 0) > 0 and isinstance(receipt_age, (int, float)) and 0 <= receipt_age <= receipt_limit
                 and isinstance(source_age, (int, float)) and -15000 <= source_age <= 60000)
        rows.append({"run": n["run"], "machine": n["machine"], "ip": n["ip"],
                     "start_ms": n["start"] * 1000, "current": current,
                     "state": members[n["machine"]] if current else "previous",
                     "observed_network_mb": n.get("mb") if n.get("samples", 0) > 0 else None,
                     "network_sample_age_ms": receipt_age if receipt_age is not None else -1,
                     "network_source_age_ms": source_age,
                     "network_sample_fresh": bool(fresh), "sample_source": sample_source,
                     "source_granularity_seconds": n.get("source_granularity_seconds"),
                     "country": "United States" if countries == ["us"] else " / ".join(countries),
                     "country_source": "Salad deployment placement"})
    for machine, state in members.items():
        if not any(r["machine"] == machine and r["current"] for r in rows):
            rows.append({"run": machine + "/pending", "machine": machine, "ip": "",
                         "start_ms": 0, "current": True, "state": state,
                         "observed_network_mb": None, "network_sample_age_ms": -1,
                         "network_source_age_ms": None, "network_sample_fresh": False,
                         "sample_source": None, "source_granularity_seconds": None,
                         "country": "United States" if countries == ["us"] else " / ".join(countries),
                         "country_source": "Salad deployment placement"})
    return sorted(rows, key=lambda n: (not n["current"], -n["start_ms"], n["machine"]))


class PacketStreamView:
    def __init__(self, runtime: Path, key_provider):
        self.runtime = Path(runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.key_provider = key_provider
        self.target = {name: os.environ.get(env, "").strip() or fallback for name, env, fallback in (
            ("organization", "PS_ORGANIZATION", "hyperlane"),
            ("project", "PS_PROJECT", "default"), ("group", "PS_GROUP", "ps1"))}
        target_key = "/".join(self.target.values())
        # Retain the original group's history without mixing it into replacement
        # deployments, whose current test must begin at their own start time.
        period_name = ("dashboard-periods.json" if target_key == "hyperlane/default/ps1"
                       else "dashboard-periods-" + quote(target_key, safe="") + ".json")
        self.periods_path = self.runtime / period_name
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.metadata = {}
        self.members = {}
        self.metadata_at = 0
        self.error = "Checking Salad deployment…"
        self.periods = {}
        self.last_bridge_ms = 0
        self.stop_event = threading.Event()
        try:
            self.periods = {p["id"]: p for p in json.loads(self.periods_path.read_text())}
        except (ValueError, OSError, KeyError):
            pass
        # These saved snapshots preserve starts/stops already observed before this UI.
        for path in sorted(self.runtime.glob("status-*.json")):
            try:
                value = json.loads(path.read_text())
                if value.get("name") == self.target["group"]:
                    self.remember_period(value)
            except (ValueError, OSError):
                pass

    def remember_period(self, group):
        state = group.get("current_state", {})
        start = millis(state.get("start_time"))
        if not start:
            return
        if state.get("status") == "stopped" and millis(state.get("finish_time")) <= start:
            self.periods.pop(str(start), None)
            return
        item = self.periods.setdefault(str(start), {"id": str(start), "start_ms": start, "end_ms": None})
        if state.get("status") == "stopped":
            finish = millis(state.get("finish_time"))
            if finish > start:
                item["end_ms"] = finish
        for other in self.periods.values():
            if other["start_ms"] < start and other["end_ms"] is None:
                other["end_ms"] = start

    def fetch_metadata(self):
        base = ("https://api.salad.com/api/public/organizations/" + quote(self.target["organization"], safe="")
                + "/projects/" + quote(self.target["project"], safe="")
                + "/containers/" + quote(self.target["group"], safe=""))
        key = self.key_provider()
        def get(path):
            config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\n"
            response = subprocess.run(["/usr/bin/curl", "-sS", "--max-time", "10", "--config", "-",
                                       "--write-out", "\n%{http_code}", path],
                                      input=config, capture_output=True, text=True, timeout=12)
            raw, code = response.stdout.rsplit("\n", 1)
            if response.returncode or code != "200":
                raise ValueError("Salad request failed")
            return json.loads(raw)
        try:
            group, instances = get(base), get(base + "/instances")
            with self.lock:
                self.metadata = {k: group.get(k) for k in ("name", "display_name", "current_state", "country_codes", "version")}
                self.members = {n["machine_id"]: n["state"] for n in instances["instances"]}
                self.metadata_at = int(time.time() * 1000)
                self.error = None
                self.remember_period(group)
                self.periods_path.write_text(json.dumps(list(self.periods.values())))
        except Exception:
            with self.lock:
                self.error = "Salad membership could not be refreshed."

    def run(self):
        while not self.stop_event.is_set():
            self.fetch_metadata()
            self.stop_event.wait(15)

    def readings(self):
        values = {}
        path = self.runtime / "provider-observations.jsonl"
        if not path.exists():
            return []
        for line in path.read_text().splitlines():
            try:
                value = json.loads(line)
                stamp = millis(value.get("recorded_at") or value.get("observed_at"))
                gb = float(value["traffic_sold_gb"])
                if stamp and math.isfinite(gb) and gb >= 0:
                    values[stamp] = {"time_ms": stamp, "gb": gb,
                                     "basis": "provider_bytes" if "provider_bytes" in value else "display_gb"}
            except (KeyError, ValueError, TypeError):
                pass
        return sorted(values.values(), key=lambda r: r["time_ms"])

    def ingest(self, body):
        now = int(time.time() * 1000)
        gb, stamp = float(body["gb"]), int(body["time_ms"])
        provider_bytes = body.get("bytes")
        if provider_bytes is not None:
            if not isinstance(provider_bytes, int) or not 0 <= provider_bytes <= 10**18:
                raise ValueError("Invalid provider bytes")
            gb = provider_bytes / 1e9
        if not math.isfinite(gb) or not 0 <= gb <= 1e9 or abs(now - stamp) > 120000:
            raise ValueError("Invalid provider reading")
        with self.lock:
            self.last_bridge_ms = now
            previous = self.readings()
            if previous and stamp - previous[-1]["time_ms"] < 10000:
                return
            record = {"observed_at": datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat(),
                      "traffic_sold_gb": gb, "source": "Authenticated PacketStream browser feed"}
            if provider_bytes is not None:
                record["provider_bytes"] = provider_bytes
            with (self.runtime / "provider-observations.jsonl").open("a") as out:
                out.write(json.dumps(record) + "\n")

    def snapshot(self, raw, start=None, end=None):
        now = int(time.time() * 1000)
        with self.lock:
            state = self.metadata.get("current_state", {})
            restart = millis(state.get("start_time"))
            start = restart if start is None else start
            end = now if end is None else end
            readings = self.readings()
            countries = self.metadata.get("country_codes") or ["us"]
            return {"time_ms": now, "target": dict(self.target), "restart_ms": restart, "status": state.get("status", "unknown"),
                    "running_nodes": sum(s == "running" for s in self.members.values()),
                    "membership_age_ms": now - self.metadata_at, "membership_error": self.error,
                    "nodes": ordered_nodes(raw.get("nodes", []), self.members, restart, countries),
                    "periods": sorted(self.periods.values(), key=lambda r: -r["start_ms"]),
                    "billing": paid_window(readings, start, end), "window": {"start_ms": start, "end_ms": end},
                    "recent_billing": paid_window(readings, max(restart, readings[-1]["time_ms"] - 301000), readings[-1]["time_ms"]) if readings else None,
                    "latest_reading": readings[-1] if readings else None,
                    "feed_age_ms": now - self.last_bridge_ms if self.last_bridge_ms else None,
                    "bridge_token": self.token}
~~~~~~

### dashboard/ps-paid-feed.js

<!-- rebuild-file: dashboard/ps-paid-feed.js sha256=a0809b7941d4cb91621cd499a383161e7a0005644ba3f24f3dc0747b0dad6acc -->
~~~~~~javascript
// Run in the PacketStream tab opened by the local PS dashboard. No credentials
// are exported: only the provider's credited-byte total and observation time.
(async () => {
  const channel = new URLSearchParams(location.hash.slice(1)).get('ps-sync');
  if (!channel || !window.opener) throw new Error('Open from the local PS dashboard first.');
  if (window.__psPaidFeed) clearInterval(window.__psPaidFeed);
  let badge = document.getElementById('ps-local-feed');
  if (!badge) {
    badge = document.createElement('div'); badge.id = 'ps-local-feed';
    badge.style.cssText = 'position:fixed;bottom:16px;right:16px;z-index:99999;padding:12px 16px;border-radius:8px;background:#163d30;color:white;font:13px system-ui;box-shadow:0 3px 16px #0003';
    document.body.append(badge);
  }
  const send = data => window.opener.postMessage({type:'ps-credited',channel,...data}, 'http://127.0.0.1:8787');
  async function poll() {
    try {
      const response = await fetch('/dashboard', {credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(8000)});
      if (!response.ok) throw new Error('PacketStream could not be refreshed.');
      const doc = new DOMParser().parseFromString(await response.text(),'text/html');
      if (!(doc.querySelector('#referral-link')?.value || '').includes('psr=8ExP')) throw new Error('Sign in to the expected PacketStream account.');
      const source = [...doc.scripts].find(s => !s.src && s.textContent.includes('window.reportData'))?.textContent || '';
      const match = source.match(/const rd\s*=\s*("(?:\\.|[^"\\])*")\s*;/);
      if (!match) throw new Error('Provider report format changed.');
      const report = JSON.parse(JSON.parse(match[1]));
      if (!Array.isArray(report.exitnode)) throw new Error('Credited-byte records unavailable.');
      const bytes = report.exitnode.reduce((sum, row) => sum + Number(row.bandwidth.up) + Number(row.bandwidth.down), 0);
      if (!Number.isSafeInteger(bytes) || bytes < 0) throw new Error('Invalid credited-byte records.');
      send({gb:bytes/1e9,bytes,time_ms:Date.now()});
      // Refresh the existing provider UI using its own rendering function.
      window.reportData = report;
      if (typeof renderTrafficHistory === 'function') {
        document.getElementById('traffic-history-body')?.replaceChildren();
        renderTrafficHistory();
      }
      badge.textContent = 'PS dashboard connected · '+(bytes/1e6).toFixed(3)+' MB credited total · updates automatically';
      return bytes;
    } catch (error) { badge.textContent='PS feed: '+error.message; send({error:error.message}); }
  }
  await poll(); window.__psPaidFeed = setInterval(poll, 60000);
})();
~~~~~~

### dashboard/salad_api.py

<!-- rebuild-file: dashboard/salad_api.py sha256=fdfad086f5d12cfcc69dd0f3012ffc7502a84b14ffdf172bd7009159ccde5f86 -->
~~~~~~python
"""Small standard-library client for Salad's structured Log Entries API."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List


class SaladAPIError(RuntimeError):
    pass


class AuthenticationError(SaladAPIError):
    pass


class RetryableAPIError(SaladAPIError):
    pass


def _parse_iso(value: str) -> datetime:
    value = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], value, count=1)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class SaladLogClient:
    def __init__(
        self,
        organization: str,
        project: str,
        container_group: str,
        key_provider: Callable[[], str],
        base_url: str = "https://api.salad.com/api/public",
        timeout: float = 30.0,
    ):
        self.organization = organization
        self.project = project
        self.container_group = container_group
        self.key_provider = key_provider
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def query(self) -> str:
        return (
            'resource.type = "container" and '
            f'resource.labels.project_name = "{self.project}" and '
            f'resource.labels.container_group_name = "{self.container_group}" and '
            '(json_log.kind = "bandwidth_sample" or '
            'json_log.kind = "honeygain_event" or '
            'json_log.kind = "bandwidth_monitor_status" or '
            'text_log = "Honeygain service disconnected")'
        )

    def fetch(self, start_time: str, end_time: str, page_size: int = 100) -> List[Dict[str, Any]]:
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")
        key = self.key_provider().strip()
        if not key:
            raise AuthenticationError("Salad API key is not configured")
        url = f"{self.base_url}/organizations/{urllib.parse.quote(self.organization, safe='')}/log-entries"
        cursor = _parse_iso(start_time)
        end = _parse_iso(end_time)
        if cursor >= end:
            return []
        request_count = 0

        def fetch_window(window_start: datetime, window_end: datetime, depth: int = 0) -> List[Dict[str, Any]]:
            nonlocal request_count
            request_count += 1
            if request_count > 4096 or depth > 64:
                raise RetryableAPIError("Salad API pagination limit reached")
            body = {
                "query": self.query,
                "start_time": _iso(window_start),
                "end_time": _iso(window_end),
                "page_size": page_size,
                "sort_order": "asc",
            }
            request = urllib.request.Request(
                url,
                json.dumps(body, separators=(",", ":")).encode("utf-8"),
                {
                    "Content-Type": "application/json",
                    "Salad-Api-Key": key,
                    "User-Agent": "salad-bandwidth-dashboard/1",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    page = json.load(response)
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403):
                    raise AuthenticationError(f"Salad API authentication failed ({exc.code})") from None
                if exc.code == 429 or exc.code >= 500:
                    raise RetryableAPIError(f"Salad API temporarily unavailable ({exc.code})") from None
                raise SaladAPIError(f"Salad API request failed ({exc.code})") from None
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                raise RetryableAPIError(f"Salad API request could not complete: {type(exc).__name__}") from None

            page_items = page.get("items")
            if not isinstance(page_items, list):
                raise RetryableAPIError("Salad API returned an invalid log page")
            if len(page_items) < page_size:
                return [item for item in page_items if isinstance(item, dict)]

            span = window_end - window_start
            midpoint = window_start + span / 2
            if midpoint <= window_start or midpoint >= window_end or span <= timedelta(milliseconds=1):
                raise RetryableAPIError("too many Salad logs share one pagination timestamp")
            return fetch_window(window_start, midpoint, depth + 1) + fetch_window(midpoint, window_end, depth + 1)

        items = fetch_window(cursor, end)
        unique: Dict[str, Dict[str, Any]] = {}
        for item in items:
            identity = json.dumps(item, sort_keys=True, separators=(",", ":"))
            unique[identity] = item
        return sorted(
            unique.values(),
            key=lambda item: (
                str(item.get("time") or ""),
                str(item.get("receive_time") or ""),
                str(((item.get("resource") or {}).get("labels") or {}).get("instance_id") or ""),
                int((item.get("json_log") or {}).get("sequence") or 0),
            ),
        )
~~~~~~

### dashboard/server.py

<!-- rebuild-file: dashboard/server.py sha256=436a98372e33f7d261707c670b3afee82270b3f379455b0fd07732a07768f808 -->
~~~~~~python
#!/usr/bin/env python3
"""Loopback-only API, poller, and static server for the bandwidth dashboard."""

from __future__ import annotations

import argparse
import csv
from http.client import HTTPConnection, HTTPException
import getpass
import io
import json
import sqlite3
from contextlib import closing
import math
import mimetypes
import os
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import parse_qs, urlparse

from dashboard.salad_api import SaladLogClient
from dashboard.store import APP_NAMES, Store, parse_time_ms
from dashboard.packetstream import PacketStreamView
from dashboard.fleet_test import FleetTestView, fleet_csv
from dashboard.native_network import NetworkMinutes, saved_minutes, bucket_minutes


HOST = "127.0.0.1"
DEFAULT_PORT = 8787
MAX_POINTS = 2000


def iso_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def query_window(query: Dict[str, list]) -> tuple:
    try:
        start = int(query.get("start", [""])[0])
        end = int(query.get("end", [""])[0])
        requested_bucket = int(query.get("bucket", ["1"])[0])
    except (TypeError, ValueError):
        raise ValueError("start, end, and bucket must be integers") from None
    if end <= start:
        raise ValueError("end must be after start")
    if requested_bucket < 1 or requested_bucket > 86400:
        raise ValueError("bucket must be between 1 and 86400 seconds")
    minimum_bucket = max(1, math.ceil((end - start) / 1000 / MAX_POINTS))
    return start, end, max(requested_bucket, minimum_bucket)


def csv_export(series: Dict[str, Any]) -> bytes:
    output = io.StringIO(newline="")
    fields = [
        "time_utc",
        "sample_count",
        "instance_ids",
        "coverage_percent",
        "eth0_rx_bytes_per_second",
        "eth0_tx_bytes_per_second",
        "captured_rx_bytes_per_second",
        "captured_tx_bytes_per_second",
        "unassigned_rx_bytes_per_second",
        "unassigned_tx_bytes_per_second",
    ]
    for app in APP_NAMES:
        fields.extend((f"{app}_rx_bytes_per_second", f"{app}_tx_bytes_per_second"))
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for point in series["points"]:
        row = {
            "time_utc": iso_ms(point["time_ms"]),
            "sample_count": point["sample_count"],
            "instance_ids": ";".join(point["instance_ids"]),
            "coverage_percent": point["coverage_percent"],
            "eth0_rx_bytes_per_second": point["eth0"]["rx_bytes_per_second"],
            "eth0_tx_bytes_per_second": point["eth0"]["tx_bytes_per_second"],
            "captured_rx_bytes_per_second": point["captured"]["rx_bytes_per_second"],
            "captured_tx_bytes_per_second": point["captured"]["tx_bytes_per_second"],
            "unassigned_rx_bytes_per_second": point["unassigned"]["rx_bytes_per_second"],
            "unassigned_tx_bytes_per_second": point["unassigned"]["tx_bytes_per_second"],
        }
        for app in APP_NAMES:
            row[f"{app}_rx_bytes_per_second"] = point["applications"][app]["rx_bytes_per_second"]
            row[f"{app}_tx_bytes_per_second"] = point["applications"][app]["tx_bytes_per_second"]
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def make_handler(store: Store, status_provider: Callable[[], Dict[str, Any]], static_dir: Path, ps_view=None, expected_reporters: int = 10, fleet_view=None, minute_view=None):
    static_dir = Path(static_dir)
    fleet_view = fleet_view or FleetTestView(Path(os.environ.get("FLEET_TEST_DIR", str(Path.home() / ".hg1" / "fleet-tests"))))

    class Handler(BaseHTTPRequestHandler):
        server_version = "SaladBandwidthDashboard/1"

        def log_message(self, *_args):
            return

        def headers_common(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")

        def send_bytes(self, status: int, body: bytes, content_type: str, disposition: str = "") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if disposition:
                self.send_header("Content-Disposition", disposition)
            self.headers_common()
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status: int, value: Any, disposition: str = "") -> None:
            body = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
            self.send_bytes(status, body, "application/json; charset=utf-8", disposition)

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/proxyrack":
                    result = json.loads((Path.home() / ".hg1/proxyrack/view.json").read_text())
                    path=Path.home()/".hg1/proxyrack/traffic.sqlite3"
                    result["minutes"] = saved_minutes(path, group_id=result["group_id"])
                    if path.exists():
                        with closing(sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)) as db:
                            amount=db.execute("SELECT SUM(rx+tx) FROM minutes WHERE valid=1 AND seq>0 AND group_id=?",(result["group_id"],)).fetchone()[0]
                        result["total_recorded_mb"]=amount/1e6 if amount is not None else None
                    self.send_json(200, result)
                    return
                if parsed.path == "/api/traffmonetizer":
                    from dashboard.traffmonetizer import snapshot
                    result = snapshot()
                    path = Path.home()/".hg1/traffmonetizer/traffic.sqlite3"
                    if path.exists() and parse_qs(parsed.query).get("chart")==["1"]:
                        now=int(time.time()*1000); first=now//60000*60000-1439*60000
                        test_start=result.get("deployment",{}).get("measurement_started_ms",0)
                        points={}
                        with closing(sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)) as db:
                            db.row_factory=sqlite3.Row; db.execute("BEGIN")
                            rows=db.execute("""SELECT CAST(time_ms/60000 AS INTEGER)*60000 minute,run,instance,machine,ip,
                                SUM(rx+tx)/1e6 mb,
                                SUM(time_ms-MAX(start_ms,CAST(time_ms/60000 AS INTEGER)*60000)) coverage_ms,
                                SUM(MAX(0,CAST(time_ms/60000 AS INTEGER)*60000-start_ms)) previous_coverage_ms
                                FROM samples WHERE time_ms>=? AND start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL
                                GROUP BY minute,run,instance,machine,ip ORDER BY minute""",(first,test_start)).fetchall()
                            total=db.execute("SELECT SUM(rx) rx,SUM(tx) tx,COUNT(*) samples,MIN(time_ms) first_ms,MAX(time_ms) last_ms FROM samples WHERE start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL",(test_start,)).fetchone()
                            result["recorded"]=dict(total)
                        for row in rows:
                            point=points.setdefault(row["minute"],{"minute_ms":row["minute"],"mb":0,"nodes":[],"duration_ms":0})
                            point["mb"]+=row["mb"];point["duration_ms"]+=row["coverage_ms"]
                            previous=points.get(row["minute"]-60000)
                            if previous is not None: previous["duration_ms"]+=row["previous_coverage_ms"]
                            point["nodes"].append({"instance":row["instance"],"ip":row["ip"],"mb":row["mb"]})
                        for point in points.values():
                            point["count"]=len(point["nodes"])
                            point["nodes"]=sorted(point["nodes"],key=lambda n:-n["mb"])[:20]
                            point["partial"]=point.pop("duration_ms")<result.get("deployment",{}).get("desired_replicas",10)*60000
                        result["chart_minutes"]=list(points.values())
                    self.send_json(200,result)
                    return
                if parsed.path == "/api/earnfm":
                    path = static_dir/"earnfm.json"
                    result=json.loads(path.read_text()) if path.exists() else {"error":"EarnFM recorder has not published data yet", "desired":10,"workers":[],"points":[]}
                    self.send_json(200,result)
                    return
                if parsed.path == "/api/repocket":
                    data_dir = Path.home() / ".hg1" / "repocket"
                    result = json.loads((data_dir / "view.json").read_text())
                    if (data_dir / "provider.json").exists():
                        result["provider"] = json.loads((data_dir / "provider.json").read_text())
                    if parse_qs(parsed.query).get("chart")==["1"] and (data_dir/"traffic.sqlite3").exists():
                        now=int(time.time()*1000); first=now//60000*60000-1439*60000
                        with closing(sqlite3.connect("file:"+str(data_dir/"traffic.sqlite3")+"?mode=ro",uri=True)) as db:
                            db.execute("BEGIN")
                            raw=[json.loads(row[0]) for row in db.execute("SELECT body FROM events WHERE kind='minute' AND time_ms>=?",(first,))]
                            total=db.execute("SELECT SUM(json_extract(body,'$.rx_bytes')+json_extract(body,'$.tx_bytes')),MIN(json_extract(body,'$.start_ms')) FROM events WHERE kind='minute' AND json_extract(body,'$.rx_bytes')>=0 AND json_extract(body,'$.tx_bytes')>=0").fetchone()
                        records=[]
                        for row in raw:
                            if row.get("rx_bytes") is None or row.get("tx_bytes") is None or row["rx_bytes"]<0 or row["tx_bytes"]<0:continue
                            record={"start_ms":row["start_ms"],"end_ms":row["end_ms"],"rx":row["rx_bytes"],"tx":row["tx_bytes"],"bucket_ms":None,"instance":row["instance"],"machine":row["machine"],"ip":row.get("ip")}
                            bucket=round(row["start_ms"]/60000)*60000
                            if not row.get("partial") and 59000<=row["end_ms"]-row["start_ms"]<=61000 and abs(row["start_ms"]-bucket)<=1000:
                                record.update(start_ms=bucket,end_ms=bucket+60000,bucket_ms=bucket)
                            records.append(record)
                        result["chart_minutes"]=bucket_minutes(records,first,now//60000*60000)
                        for point in result["chart_minutes"]:point["partial"]|=point["count"]<result["desired"]
                        result["total_network_mb"]=total[0]/1e6 if total[0] is not None else None
                        result["test_started_ms"]=total[1]
                    self.send_json(200, result)
                    return
                if parsed.path == "/api/ps1/minutes" and minute_view is not None:
                    query = parse_qs(parsed.query)
                    census = json.loads((minute_view.path.parent / "native-census.json").read_text())
                    selected = int(query["minute"][0]) if "minute" in query else None
                    if selected is not None and (selected < 0 or selected % 60000):
                        raise ValueError("Invalid selected minute")
                    self.send_json(200, minute_view.minute(census.get("group_id", ""), selected) if selected is not None else minute_view.snapshot(census))
                    return
                if parsed.path in ("/api/fleet-test", "/api/fleet-test/export.json", "/api/fleet-test/export.csv"):
                    archive = parse_qs(parsed.query).get("archive", [None])[0]
                    result = fleet_view.snapshot(archive=archive, include_observations=parsed.path.endswith(".json"), honeygain_only=parse_qs(parsed.query).get("service") == ["hg"])
                    if parsed.path.endswith(".csv"):
                        self.send_bytes(200, fleet_csv(result), "text/csv; charset=utf-8", 'attachment; filename="independent-fleet-test.csv"')
                    else:
                        self.send_json(200, result, 'attachment; filename="independent-fleet-test.json"' if parsed.path.endswith(".json") else "")
                    return
                if parsed.path == "/api/ps1/view" and ps_view is not None:
                    query = parse_qs(parsed.query)
                    start = int(query["start"][0]) if "start" in query else None
                    end = int(query["end"][0]) if "end" in query else None
                    if start is not None and (start < 0 or (end is not None and end <= start)):
                        raise ValueError("Invalid period")
                    raw = {}
                    connection = HTTPConnection("127.0.0.1", 8789, timeout=4)
                    try:
                        connection.request("GET", "/api/ps1/status")
                        response = connection.getresponse()
                        if response.status == 200:
                            raw = json.loads(response.read())
                    except (OSError, HTTPException, ValueError):
                        pass
                    finally:
                        connection.close()
                    self.send_json(200, ps_view.snapshot(raw, start, end))
                    return
                if parsed.path in ("/api/ps1/status", "/api/ps1/history"):
                    # Fixed loopback target; browser input cannot select an upstream.
                    target = parsed.path
                    if parsed.path.endswith("/history"):
                        after = int(parse_qs(parsed.query).get("after", ["0"])[0])
                        if after < 0:
                            raise ValueError("after must be a non-negative integer")
                        target += f"?after={after}"
                    connection = HTTPConnection("127.0.0.1", 8789, timeout=4)
                    try:
                        connection.request("GET", target, headers={"Accept": "application/json"})
                        upstream = connection.getresponse()
                        body = upstream.read()
                        if upstream.status != 200:
                            self.send_json(503, {"error": f"PS1 recorder returned HTTP {upstream.status}"})
                        else:
                            self.send_bytes(200, body, "application/json; charset=utf-8")
                    except (OSError, HTTPException):
                        self.send_json(503, {"error": "PS1 recorder is unavailable"})
                    finally:
                        connection.close()
                    return
                if parsed.path == "/api/status":
                    result = store.status()
                    result.update(status_provider())
                    last_sample_ms = result.get("last_sample_ms")
                    result["source_lag_ms"] = (
                        max(0, int(time.time() * 1000) - int(last_sample_ms))
                        if last_sample_ms is not None
                        else None
                    )
                    self.send_json(200, result)
                    return
                if parsed.path == "/api/boxes":
                    start, end, _bucket = query_window(parse_qs(parsed.query))
                    self.send_json(200, store.query_boxes(start, end, expected_reporters=expected_reporters))
                    return
                if parsed.path == "/api/events":
                    start, end, _bucket = query_window(parse_qs(parsed.query))
                    self.send_json(200, store.query_events(start, end))
                    return
                if parsed.path in ("/api/series", "/api/export.csv", "/api/export.json"):
                    start, end, bucket = query_window(parse_qs(parsed.query))
                    result = store.query_range(start, end, bucket)
                    if parsed.path == "/api/export.csv":
                        self.send_bytes(200, csv_export(result), "text/csv; charset=utf-8", 'attachment; filename="salad-bandwidth.csv"')
                    elif parsed.path == "/api/export.json":
                        self.send_json(200, result, 'attachment; filename="salad-bandwidth.json"')
                    else:
                        self.send_json(200, result)
                    return
                files = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/ps1.js": "ps1.js", "/fleet-test.js": "fleet-test.js", "/styles.css": "styles.css"}
                files.update({"/rp": "repocket.html", "/repocket": "repocket.html", "/repocket.html": "repocket.html"})
                files.update({"/proxyrack": "proxyrack.html", "/proxyrack.html": "proxyrack.html"})
                files.update({"/ef": "earnfm.html", "/earnfm": "earnfm.html", "/earnfm.html": "earnfm.html", "/ef.json": "earnfm.json", "/earnfm.json": "earnfm.json"})
                files.update({alias:"index.html" for path in ("/proxyrack","/rp","/repocket","/earnfm","/traffmonetizer","/tm") for alias in (path,path+".html")})
                filename = files.get(parsed.path)
                if filename is None:
                    self.send_json(404, {"error": "not found"})
                    return
                body = (static_dir / filename).read_bytes()
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                self.send_bytes(200, body, content_type + ("; charset=utf-8" if content_type.startswith("text/") or content_type.endswith("javascript") else ""))
            except ValueError as exc:
                self.send_json(400, {"error": str(exc)})
            except FileNotFoundError:
                self.send_json(404, {"error": "dashboard asset not found"})
            except Exception:
                self.send_json(500, {"error": "internal dashboard error"})

        def do_POST(self):  # noqa: N802
            if self.path != "/api/ps1/credited" or ps_view is None:
                self.send_json(404, {"error": "not found"})
                return
            if self.headers.get("X-PS-Token") != ps_view.token or self.headers.get("Origin", "http://127.0.0.1:8787") != "http://127.0.0.1:8787":
                self.send_json(403, {"error": "Local dashboard authentication required"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 2048:
                    raise ValueError("Invalid reading size")
                ps_view.ingest(json.loads(self.rfile.read(size)))
                self.send_json(200, {"ok": True})
            except (ValueError, TypeError, KeyError):
                self.send_json(400, {"error": "Invalid provider reading"})

    return Handler


class Poller:
    def __init__(
        self,
        store: Store,
        client: SaladLogClient,
        interval_seconds: int = 1,
        overlap_seconds: int = 2,
        settlement_seconds: int = 10,
        initial_lookback_seconds: int = 60,
        reconcile_horizon_seconds: int = 3600,
        reconcile_chunk_seconds: int = 60,
        reconcile_interval_seconds: int = 10,
    ):
        self.store = store
        self.client = client
        self.interval_seconds = interval_seconds
        self.overlap_ms = overlap_seconds * 1000
        self.settlement_ms = settlement_seconds * 1000
        self.initial_lookback_ms = initial_lookback_seconds * 1000
        self.reconcile_horizon_ms = reconcile_horizon_seconds * 1000
        self.reconcile_chunk_ms = reconcile_chunk_seconds * 1000
        self.reconcile_interval_ms = reconcile_interval_seconds * 1000
        self._reconcile_cursor_ms: Optional[int] = None
        self._next_reconcile_ms: Optional[int] = None
        self._last_reconcile_start_ms: Optional[int] = None
        self._last_reconcile_end_ms: Optional[int] = None
        self._last_reconcile_final_start_ms: Optional[int] = None
        self._last_reconcile_final_end_ms: Optional[int] = None
        self.stop_event = threading.Event()
        self._lock = threading.Lock()
        self._status: Dict[str, Any] = {"poll_state": "starting"}
        self._maintenance_at = 0.0

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._status)

    def run_once(self, now_ms: Optional[int] = None) -> int:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        settled_end_ms = max(0, now_ms - self.settlement_ms)
        watermark = self.store.watermark_ms()
        start_ms = max(
            0,
            (watermark - self.overlap_ms)
            if watermark is not None
            else settled_end_ms - self.initial_lookback_ms,
        )
        try:
            entries = self.client.fetch(iso_ms(start_ms), iso_ms(settled_end_ms), page_size=100)
            reconcile_due = self._next_reconcile_ms is None or now_ms >= self._next_reconcile_ms
            if (
                reconcile_due
                and self.reconcile_horizon_ms > 0
                and self.reconcile_chunk_ms > 0
                and self.reconcile_interval_ms > 0
            ):
                self._next_reconcile_ms = now_ms + self.reconcile_interval_ms
                reconcile_floor = max(0, settled_end_ms - self.reconcile_horizon_ms)
                reconcile_limit = max(reconcile_floor, settled_end_ms - self.overlap_ms)
                reconcile_slice_ms = max(1000, self.reconcile_chunk_ms // 2)
                if self._reconcile_cursor_ms is None:
                    self._reconcile_cursor_ms = reconcile_floor
                if self._reconcile_cursor_ms < reconcile_floor or self._reconcile_cursor_ms >= reconcile_limit:
                    self._reconcile_cursor_ms = reconcile_floor
                reconcile_start_ms = self._reconcile_cursor_ms
                reconcile_end_ms = min(reconcile_start_ms + reconcile_slice_ms, reconcile_limit)
                if reconcile_end_ms > reconcile_start_ms:
                    entries.extend(
                        self.client.fetch(iso_ms(reconcile_start_ms), iso_ms(reconcile_end_ms), page_size=100)
                    )
                    self._reconcile_cursor_ms = (
                        reconcile_floor if reconcile_end_ms >= reconcile_limit else reconcile_end_ms
                    )
                    self._last_reconcile_start_ms = reconcile_start_ms
                    self._last_reconcile_end_ms = reconcile_end_ms

                # Every event-time slice receives a final check as it reaches the
                # configured lateness horizon. This prevents a log that arrived
                # just after the rolling sweep from aging out unseen.
                final_start_ms = reconcile_floor
                final_end_ms = min(final_start_ms + reconcile_slice_ms, reconcile_limit)
                if final_end_ms > final_start_ms and (final_start_ms, final_end_ms) != (
                    reconcile_start_ms,
                    reconcile_end_ms,
                ):
                    entries.extend(self.client.fetch(iso_ms(final_start_ms), iso_ms(final_end_ms), page_size=100))
                if final_end_ms > final_start_ms:
                    self._last_reconcile_final_start_ms = final_start_ms
                    self._last_reconcile_final_end_ms = final_end_ms
            inserted = self.store.ingest_many(entries)
            next_watermark = settled_end_ms if entries else (watermark if watermark is not None else start_ms)
            self.store.record_poll(next_watermark, inserted, now_ms=now_ms)
            if time.monotonic() >= self._maintenance_at:
                self.store.rollup()
                self.store.prune(now_ms=now_ms)
                self._maintenance_at = time.monotonic() + 3600
            with self._lock:
                self._status = {
                    "poll_state": "ok",
                    "last_fetch_count": len(entries),
                    "last_insert_count": inserted,
                    "settled_through_ms": settled_end_ms,
                    "reconcile_start_ms": self._last_reconcile_start_ms,
                    "reconcile_end_ms": self._last_reconcile_end_ms,
                    "reconcile_final_start_ms": self._last_reconcile_final_start_ms,
                    "reconcile_final_end_ms": self._last_reconcile_final_end_ms,
                    "tail_fetch_interval_seconds": self.interval_seconds,
                    "tail_overlap_seconds": self.overlap_ms // 1000,
                    "settlement_seconds": self.settlement_ms // 1000,
                    "reconcile_interval_seconds": self.reconcile_interval_ms // 1000,
                }
            return inserted
        except Exception as exc:
            safe_error = f"{type(exc).__name__}: {exc}"
            self.store.record_poll(watermark or start_ms, 0, error=safe_error, now_ms=now_ms)
            with self._lock:
                self._status = {"poll_state": "error", "poll_error": safe_error[:500]}
            return 0

    def run(self) -> None:
        while not self.stop_event.is_set():
            self.run_once()
            self.stop_event.wait(self.interval_seconds)

    def stop(self) -> None:
        self.stop_event.set()


def key_provider(helper: Path) -> str:
    environment_key = os.environ.get("SALAD_API_KEY", "").strip()
    if environment_key:
        return environment_key
    result = subprocess.run(
        [str(helper), "--read", "--service", "salad-bandwidth-api", "--account", getpass.getuser()],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".salad-bandwidth-monitor")
    parser.add_argument("--no-poll", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    helper = repo_root / ".runtime" / "keychain-store"
    store = Store(args.data_dir / "bandwidth.sqlite3")
    poller: Optional[Poller] = None
    if not args.no_poll:
        client = SaladLogClient(
            os.environ.get("SALAD_ORGANIZATION", "cosmosgeeketh"),
            os.environ.get("SALAD_PROJECT", "default"),
            os.environ.get("SALAD_CONTAINER_GROUP", "honeygain-canary"),
            lambda: key_provider(helper),
        )
        poller = Poller(store, client)
        threading.Thread(target=poller.run, name="salad-log-poller", daemon=True).start()

    status = poller.status if poller else (lambda: {"poll_state": "disabled"})
    ps_runtime = Path(os.environ.get("PS_MONITOR_DIR", str(args.data_dir / "packetstream")))
    ps_view = PacketStreamView(ps_runtime, lambda: key_provider(helper))
    minute_view = NetworkMinutes(ps_runtime / "minutes.sqlite3")
    threading.Thread(target=ps_view.run, name="ps-deployment-metadata", daemon=True).start()
    expected_reporters = max(1, int(os.environ.get("SALAD_EXPECTED_REPORTERS", "10")))
    server = ThreadingHTTPServer((HOST, args.port), make_handler(store, status, Path(__file__).parent / "static", ps_view, expected_reporters, minute_view=minute_view))

    def stop_server(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop_server)
    signal.signal(signal.SIGINT, stop_server)
    print(f"dashboard: http://{HOST}:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        ps_view.stop_event.set()
        if poller:
            poller.stop()
        server.server_close()
        minute_view.db.close()
        store.close()


if __name__ == "__main__":
    main()
~~~~~~

### dashboard/static/app.js

<!-- rebuild-file: dashboard/static/app.js sha256=38c6274f51db69144d5dff2d322c57ce24c6666d2ff535839e50af2f0587778d -->
~~~~~~javascript
"use strict";

let rangeSeconds = 900;
let lastStatus = {};
let lastSeries = {points: []};
let lastBoxes = {boxes: []};
let lastEvents = {events: [], counts: {}};
let refreshInFlight = false;

const $ = id => document.getElementById(id);
function formatBytes(value) {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let amount = Math.max(0, Number(value) || 0), unit = 0;
  while (amount >= 1000 && unit < units.length - 1) { amount /= 1000; unit += 1; }
  const decimals = amount >= 100 || unit === 0 ? 0 : amount >= 10 ? 1 : 2;
  return `${amount.toFixed(decimals)} ${units[unit]}`;
}
const formatRate = value => `${formatBytes(value)}/s`;
const utc = ms => new Date(ms).toISOString().replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
function age(ms) {
  if (!ms) return "—";
  const seconds = Math.max(0, Math.round((Date.now() - ms) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}
function duration(ms) {
  if (ms == null) return "waiting";
  const seconds = Math.max(0, Number(ms) / 1000);
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`;
  return `${(seconds / 60).toFixed(1)}m`;
}
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setupCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const width = Math.max(320, canvas.clientWidth);
  const height = parseFloat(getComputedStyle(canvas).height) || 280;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return {ctx, width, height};
}
function drawTraffic() {
  const canvas = $("trafficChart"), {ctx, width, height} = setupCanvas(canvas);
  const points = lastSeries.points || [];
  ctx.clearRect(0, 0, width, height);
  if (points.length < 2) {
    ctx.fillStyle = "#667085";
    ctx.font = "13px -apple-system, sans-serif";
    ctx.fillText("Waiting for one-second samples…", 40, 42);
    return;
  }
  const box = {left: 82, right: 18, top: 14, bottom: 30};
  const values = points.map(point => point.eth0.rx_bytes_per_second + point.eth0.tx_bytes_per_second);
  const maximum = Math.max(1, ...values);
  const first = points[0].time_ms, last = points[points.length - 1].time_ms;
  const span = Math.max(1, last - first);
  const x = time => box.left + ((time - first) / span) * (width - box.left - box.right);
  const y = value => box.top + (height - box.top - box.bottom) * (1 - value / maximum);
  ctx.font = "11px ui-monospace, monospace";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let step = 0; step <= 4; step += 1) {
    const value = maximum * step / 4, yPos = y(value);
    ctx.strokeStyle = "#e5e9ef"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(box.left, yPos); ctx.lineTo(width - box.right, yPos); ctx.stroke();
    ctx.fillStyle = "#667085"; ctx.fillText(formatRate(value), box.left - 8, yPos);
  }
  const expectedReporters = Number(lastBoxes.expected_reporter_count || 10);
  const expectedStep = Number(lastSeries.bucket_seconds || 1) * 1000;
  ctx.strokeStyle = "#2463eb"; ctx.lineWidth = 1.8; ctx.beginPath();
  let drawing = false;
  let previousTime = null;
  points.forEach((point, index) => {
    const complete = (point.instance_ids || []).length === expectedReporters
      && Number(point.sample_count || 0) === expectedReporters * Number(lastSeries.bucket_seconds || 1)
      && Number(point.partial_intervals || 0) === 0;
    const contiguous = previousTime == null || point.time_ms - previousTime <= expectedStep * 1.5;
    if (!complete || !contiguous) {
      if (drawing) ctx.stroke();
      drawing = false;
      ctx.fillStyle = "#e66a2c";
      ctx.fillRect(x(point.time_ms) - 1.5, y(values[index]) - 1.5, 3, 3);
      ctx.beginPath();
      previousTime = point.time_ms;
      return;
    }
    if (!drawing) { ctx.moveTo(x(point.time_ms), y(values[index])); drawing = true; }
    else ctx.lineTo(x(point.time_ms), y(values[index]));
    previousTime = point.time_ms;
  });
  if (drawing) ctx.stroke();
  ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillStyle = "#667085";
  for (let step = 0; step <= 5; step += 1) {
    const time = first + span * step / 5;
    ctx.fillText(new Date(time).toISOString().slice(11, 19), x(time), height - box.bottom + 8);
  }
}

function renderBoxes() {
  const table = $("boxTable"); table.replaceChildren();
  const boxes = [...(lastBoxes.boxes || [])].sort((a, b) => Number(b.is_live) - Number(a.is_live) || b.last_sample_ms - a.last_sample_ms);
  if (!boxes.length) {
    const row = document.createElement("tr");
    const cell = element("td", "", "No recorder samples yet."); cell.colSpan = 16; row.append(cell); table.append(row);
  }
  for (const box of boxes) {
    const latest = box.snapshot || {rx_bytes_per_second: 0, tx_bytes_per_second: 0, bytes_per_second: 0};
    const average = box.observed_average || {bytes_per_second: 0};
    const peak = box.peak || {bytes_per_second: 0, time_ms: null};
    const honeygain = box.honeygain || {};
    const state = box.is_live ? (honeygain.state || "unknown") : "stale";
    const stateCell = document.createElement("td"); stateCell.append(element("span", `state ${state}`, state.toUpperCase()));
    const connections = `TCP ${honeygain.tcp_established_count || 0}/${honeygain.tcp_socket_count || 0} established · UDP ${honeygain.udp_socket_count || 0}`;
    const comparison = box.slowdown_ratio == null ? "—" : `${(box.slowdown_ratio * 100).toFixed(0)}%`;
    const completeness = `${Number(box.completeness_percent || 0).toFixed(1)}% (${box.sample_count || 0}/${box.expected_sample_count || 0}; ${box.partial_interval_count || 0} partial)`;
    const totalMoved = (box.totals?.rx_bytes || 0) + (box.totals?.tx_bytes || 0);
    const row = document.createElement("tr");
    for (const cell of [
      element("td", "", (box.machine_id || box.instance_id).slice(0, 8)),
      element("td", "", utc(box.first_seen_ms || box.first_sample_ms)),
      stateCell, element("td", "", connections),
      element("td", "", box.is_live ? formatRate(latest.rx_bytes_per_second) : "—"),
      element("td", "", box.is_live ? formatRate(latest.tx_bytes_per_second) : "—"),
      element("td", "", box.is_live ? formatRate(latest.bytes_per_second) : "—"),
      element("td", "", formatRate(average.bytes_per_second)), element("td", "", formatRate(peak.bytes_per_second)),
      element("td", "", peak.time_ms ? utc(peak.time_ms) : "—"),
      element("td", "", formatRate(box.first_5m_average_bytes_per_second || 0)),
      element("td", "", formatRate(box.last_5m_average_bytes_per_second || 0)), element("td", "", comparison),
      element("td", "", completeness), element("td", "", formatBytes(totalMoved)), element("td", "", age(box.last_sample_ms)),
    ]) row.append(cell);
    table.append(row);
  }
  const live = boxes.filter(box => box.is_live && box.snapshot);
  const rx = live.reduce((sum, box) => sum + box.snapshot.rx_bytes_per_second, 0);
  const tx = live.reduce((sum, box) => sum + box.snapshot.tx_bytes_per_second, 0);
  $("currentRate").textContent = formatRate(rx + tx);
  $("currentSplit").textContent = `RX ${formatRate(rx)} · TX ${formatRate(tx)}`;
  $("reportingBoxes").textContent = `${lastBoxes.snapshot_reporter_count || 0} / ${lastBoxes.expected_reporter_count || 10}`;
  $("activeApps").textContent = `${live.filter(box => box.honeygain?.state === "up").length} / ${lastBoxes.expected_reporter_count || 10}`;
}

function renderEvents() {
  const labels = {start:"START", authenticated:"AUTHENTICATED", service_starting:"SERVICE STARTING", connected:"CONNECTED", disconnected:"DISCONNECTED", network_overused:"NETWORK OVERUSED", duplicate_device:"DUPLICATE DEVICE", device_limit_exceeded:"DEVICE LIMIT", unusable_network:"UNUSABLE NETWORK", authentication_error:"AUTH ERROR", api_ping_error:"API PING ERROR", exit:"EXIT", stopping:"STOPPING", stopped:"STOPPED"};
  const table = $("eventTable"); table.replaceChildren();
  for (const event of (lastEvents.events || []).slice(0, 250)) {
    const row = document.createElement("tr");
    for (const cell of [element("td", "", utc(event.event_time_ms)), element("td", "", event.machine_id.slice(0, 8)), element("td", "", event.client_version || "monitor"), element("td", "", labels[event.event] || event.event), element("td", "", String(event.attempt || "—")), element("td", "", event.event === "exit" ? String(event.exit_code) : "—")]) row.append(cell);
    table.append(row);
  }
  const summary = Object.entries(lastEvents.counts || {}).map(([event, count]) => `${labels[event] || event}: ${count}`).join(" · ");
  $("eventSummary").textContent = summary || "No Honeygain status events in this window yet.";
}

function renderSource() {
  const list = $("sourceStatus"); list.replaceChildren();
  const add = (term, value) => list.append(element("dt", "", term), element("dd", "", value));
  add("Poller", lastStatus.poll_state || "unknown");
  const source = lastStatus.source || {};
  add("Source", source.organization ? `${source.organization} / ${source.project} / ${source.container_group}` : "waiting");
  add("Deployment version", source.version || "waiting");
  add("Capture", lastStatus.capture_mode || "waiting");
  add("Stored samples", Number(lastStatus.sample_count || 0).toLocaleString());
  add("Source lag", duration(lastStatus.source_lag_ms));
  add("Tail fetch", lastStatus.tail_fetch_interval_seconds ? `${lastStatus.tail_fetch_interval_seconds}s cadence` : "waiting");
  add("Last API success", lastStatus.last_success_ms ? utc(lastStatus.last_success_ms) : "waiting");
  add("Settled through", lastStatus.settled_through_ms ? utc(lastStatus.settled_through_ms) : "waiting");
  add("Database", formatBytes(lastStatus.database_size_bytes || 0));
}

function requestWindow() {
  const liveEnd = Date.now() + 1000, liveStart = liveEnd - rangeSeconds * 1000;
  const bucket = rangeSeconds <= 900 ? 1 : rangeSeconds <= 3600 ? 2 : rangeSeconds <= 21600 ? 15 : 60;
  const seriesEnd = bucket >= 60 ? Math.floor(liveEnd / 60000) * 60000 : liveEnd;
  const seriesStart = seriesEnd - rangeSeconds * 1000;
  const liveQuery = `start=${Math.floor(liveStart)}&end=${Math.floor(liveEnd)}&bucket=1`;
  const seriesQuery = `start=${Math.floor(seriesStart)}&end=${Math.floor(seriesEnd)}&bucket=${bucket}`;
  $("csvExport").href = `/api/export.csv?${seriesQuery}`;
  $("jsonExport").href = `/api/export.json?${seriesQuery}`;
  $("utcWindow").textContent = `${new Date(liveStart).toISOString().slice(11, 19)} → now UTC`;
  return {liveQuery, seriesQuery};
}
async function refresh() {
  if (refreshInFlight || document.getElementById("hg1Panel").classList.contains("hidden")) return;
  refreshInFlight = true;
  try {
    const {liveQuery, seriesQuery} = requestWindow();
    const responses = await Promise.all(["/api/status", `/api/series?${seriesQuery}`, `/api/boxes?${liveQuery}`, `/api/events?${liveQuery}`].map(url => fetch(url, {cache:"no-store"})));
    if (responses.some(response => !response.ok)) throw new Error("Local API unavailable");
    [lastStatus, lastSeries, lastBoxes, lastEvents] = await Promise.all(responses.map(response => response.json()));
    if ($("hg1Panel").classList.contains("hidden")) return;
    renderBoxes(); drawTraffic(); renderEvents(); renderSource();
    $("sampleAge").textContent = age(lastStatus.last_sample_ms);
    $("sampleTime").textContent = lastStatus.last_sample_ms ? utc(lastStatus.last_sample_ms) : "waiting for data";
    const liveCount = (lastBoxes.boxes || []).filter(box => box.is_live).length;
    const warnings = [];
    if (lastStatus.poll_state === "error") warnings.push(lastStatus.poll_error || lastStatus.last_error || "Ingestion failed.");
    const expectedCount = lastBoxes.expected_reporter_count || 10;
    if (liveCount !== expectedCount) warnings.push(`${liveCount} of ${expectedCount} boxes have a fresh recorder sample.`);
    $("notice").textContent = warnings.join(" ");
    $("notice").classList.toggle("hidden", warnings.length === 0);
    $("connection").className = `connection ${warnings.length ? "error" : "ok"}`;
    $("connectionText").textContent = warnings.length ? "Incomplete" : `${liveCount} / ${expectedCount} live`;
  } catch (error) {
    if ($("hg1Panel").classList.contains("hidden")) return;
    $("connection").className = "connection error";
    $("connectionText").textContent = "Dashboard unavailable";
    $("notice").textContent = String(error.message || error);
    $("notice").classList.remove("hidden");
  } finally {
    refreshInFlight = false;
  }
}

document.querySelectorAll("[data-range]").forEach(button => button.addEventListener("click", () => {
  document.querySelectorAll("[data-range]").forEach(other => other.classList.toggle("active", other === button));
  rangeSeconds = Number(button.dataset.range); refresh();
}));
window.addEventListener("resize", () => { if (!$("hg1Panel").classList.contains("hidden")) drawTraffic(); });
window.addEventListener("dashboardchange", event => { if (event.detail === "HG1") refresh(); });
refresh();
setInterval(refresh, 1000);
~~~~~~

### dashboard/static/earnfm.html

<!-- rebuild-file: dashboard/static/earnfm.html sha256=9768ffd672bff19c43cbd96effca4f0b4617f775a28e1b5241c92efb39c4a458 -->
~~~~~~html
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EF · EarnFM traffic</title><link rel="stylesheet" href="/styles.css">
<style>nav a{padding:5px 9px;color:#155e9e;text-decoration:none;border:1px solid #aaa;border-radius:2px}nav a[aria-current]{background:#ededed;color:#161616;font-weight:700}.ef-chart{width:100%;height:270px;display:block;border:1px solid #bbb}.ef-bar{fill:#1266ad;cursor:pointer}.ef-bar.partial{fill:#9abbd6}.ef-bar.selected{fill:#173f68;stroke:#000;stroke-width:2}.ef-table{min-width:860px}.ef-provider{padding:9px 0;border-block:1px solid #ddd;margin:10px 0}.ef-controls{display:flex;gap:18px;align-items:center;flex-wrap:wrap}.ef-controls label{font-size:12px}.ef-controls select{margin-left:6px}#efSummary{font-size:15px;font-weight:600}#efSelected{min-height:20px;font-size:12px}.ef-small{font-size:12px;color:#555}</style>
</head><body>
<header><h1>EF · EarnFM</h1><span id="efStatus" role="status">Loading recorded data…</span></header>
<nav aria-label="Services"><a href="/#hg1">Honeygain</a><a href="/#ps1">PacketStream</a><a href="/ef" aria-current="page">EF</a></nav>
<main><p id="efNotice" class="notice hidden" role="status"></p><p id="efSummary"></p><p id="efTime" class="ef-small"></p>
<div class="ef-provider"><span id="efEarnings">Fetching EarnFM’s credited reading…</span><p id="efProviderTime" class="ef-small"></p></div>
<div class="ef-controls"><h2>Network MB by minute</h2><label>Show<select id="efRange"><option value="60">Last hour</option><option value="180">Last 3 hours</option><option value="1440">Last 24 hours</option></select></label><a href="/earnfm.json" download="ef-recording.json">Download data</a></div>
<p class="ef-small">Actual interface RX + TX, including client control traffic. This graph is not paid bandwidth. Pale bars have partial recording coverage. Click a bar to see each server’s contribution.</p>
<svg id="efChart" class="ef-chart" role="img" aria-label="EarnFM network traffic by minute"></svg><p id="efSelected" aria-live="polite"></p>
<div class="table-scroll"><table class="ef-table"><thead><tr><th>Server / observed instance</th><th>EarnFM</th><th>Process / Salad</th><th>Recorded MB</th><th>KB/s</th><th>MB in selected minute</th><th>Last sample</th></tr></thead><tbody id="efWorkers"></tbody><tfoot id="efPrevious"></tfoot></table></div>
<p class="ef-small">Retries and reallocation run inside each container. This local page and its recorder only observe. Provider figures are account-wide gross credits; Salad costs have not been subtracted.</p>
</main>
<script>
'use strict';
const $=id=>document.getElementById(id),finite=n=>typeof n==='number'&&Number.isFinite(n);
const number=(n,d=3)=>finite(n)?n.toLocaleString(undefined,{maximumFractionDigits:d}):'—';
const when=n=>finite(n)?new Date(n).toLocaleString([],{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}):'—';
const age=n=>finite(n)?`${Math.max(0,Math.round((Date.now()-n)/1000))}s ago`:'Awaiting first sample';
let data=null,selected=null,pending=false,failed=false;
function element(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e}
function svg(tag,attrs,text){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e}
function draw(){
 if(!data)return;
 const chart=$('efChart'),width=Math.max(300,chart.clientWidth),height=270,left=58,right=12,top=18,bottom=42;
 chart.setAttribute('viewBox',`0 0 ${width} ${height}`);chart.replaceChildren();
 const end=Math.floor(Date.now()/60000)*60000,range=Number($('efRange').value),start=end-(range-1)*60000;
 const points=data.points.filter(p=>p.time_ms>=start&&p.time_ms<=end),maximum=Math.max(.001,...points.map(p=>p.mb));
 const w=width-left-right,h=height-top-bottom;
 for(let i=0;i<=4;i++){const y=top+h-i*h/4;chart.append(svg('line',{x1:left,y1:y,x2:width-right,y2:y,stroke:'#ddd'}),svg('text',{x:left-7,y:y+4,'text-anchor':'end','font-size':11,fill:'#555'},number(maximum*i/4)))}
 for(let i=0;i<=4;i++){const t=start+(end-start)*i/4,x=left+w*i/4;chart.append(svg('text',{x,y:height-13,'text-anchor':i===0?'start':i===4?'end':'middle','font-size':11,fill:'#555'},new Date(t).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',hour12:false})))}
 if(!points.length)chart.append(svg('text',{x:width/2,y:height/2,'text-anchor':'middle','font-size':14,fill:'#666'},'Waiting for recorded traffic samples'));
 for(const p of points){const x=left+(p.time_ms-start)/60000*w/range,bh=p.mb/maximum*h;
  const bar=svg('rect',{x,y:top+h-Math.max(1,bh),width:Math.max(1,w/range-1),height:Math.max(1,bh),class:`ef-bar ${p.partial?'partial':''} ${selected===p.time_ms?'selected':''}`,tabindex:0,role:'button','aria-label':`${when(p.time_ms)}: ${number(p.mb)} MB${p.partial?', partial coverage':''}`});
  bar.append(svg('title',{},`${when(p.time_ms)} · ${number(p.mb,6)} MB${p.partial?' · partial recording':''}`));
  const choose=()=>{selected=p.time_ms;draw();rows()};bar.addEventListener('click',choose);bar.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose()}});chart.append(bar)
 }
}
function freshWorker(w){return !failed&&finite(w.sample_ms)&&Date.now()-w.sample_ms<90000&&!w.final}
function rows(){
 if(!data)return;
 const body=$('efWorkers');body.replaceChildren();const point=data.points.find(p=>p.time_ms===selected);
 const providerFresh=!failed&&finite(data.provider?.observed_ms)&&Date.now()-data.provider.observed_ms<180000&&!data.provider.error;
 $('efSelected').textContent=point?`${when(point.time_ms)} · ${number(point.mb,6)} MB recorded${point.partial?' · partial coverage':''}`:'Select a minute in the graph.';
 let shown=0;
 data.workers.forEach((w,i)=>{const row=element('tr'),name=element('td',`${i+1}. ${w.machine.slice(0,12)}`);name.append(element('small',w.runtime_instance||w.instance));
  if(w.runtime_instance&&w.runtime_instance!==w.instance)name.append(element('small',`Salad inventory ID: ${w.instance}`));
  if(w.ip)name.append(element('small',w.ip+(w.country?' · '+w.country:' · country unverified')));
  const fresh=freshWorker(w);
  const state=({starting:'Starting',running:'Process up',retrying:'Retrying',connection_error:'Connection errors · recovery active',rate_limited:'Rate limited · 24h pause',stopping:'Stopping',reallocating:'Replacing',awaiting_sample:'Awaiting current-instance sample'})[w.client_state]||w.client_state;
  const share=point?.by_instance[w.runtime_instance||w.instance]||0;shown+=share;
  row.append(name,element('td',providerFresh&&fresh?(w.provider_online?'Online':'Not confirmed'):'Reading pending',providerFresh&&fresh&&w.provider_online?'ok':'stale'),element('td',`${state} / ${w.salad_state}`,fresh&&w.client_state==='running'?'ok':'stale'),element('td',number(w.total_mb)),element('td',fresh?number(w.kb_per_second):'—'),element('td',point?number(share,6):'—'),element('td',age(w.sample_ms)));
  body.append(row)
 });
 for(let i=data.workers.length;i<data.desired;i++){const row=element('tr');row.append(element('td',`${i+1}. Allocating`));for(let j=0;j<6;j++)row.append(element('td','—'));body.append(row)}
 $('efPrevious').replaceChildren();
 if(point&&point.mb-shown>.000001){const row=element('tr'),label=element('td','Previously allocated servers');label.colSpan=5;row.append(label,element('td',number(point.mb-shown,6)),element('td','Historical contribution'));$('efPrevious').append(row)}
}
function render(){
 if(!data)return;
 const now=Date.now(),fresh=!failed&&now-data.generated_ms<60000&&finite(data.inventory_ms)&&now-data.inventory_ms<90000;
 const p=data.provider||{},providerFresh=!failed&&finite(p.observed_ms)&&now-p.observed_ms<180000&&!p.error;
 $('efStatus').textContent=failed?'Cannot refresh EF · last observations shown':fresh?`Recorder updated ${age(data.generated_ms)}`:`Recording stale · ${age(data.generated_ms)}`;
 const warnings=[data.error,p.error].filter(Boolean);$('efNotice').textContent=warnings.join(' · ');$('efNotice').classList.toggle('hidden',!warnings.length);
 const online=providerFresh?data.workers.filter(w=>w.provider_online&&freshWorker(w)).length:null;
 $('efSummary').textContent=`${data.workers.filter(w=>w.salad_state==='running').length}/${data.desired} containers running${online!==null?` · ${online} confirmed online by EarnFM`:''} · ${number(data.total_mb,6)} MB recorded`;
 $('efTime').textContent=`SSH3 · Test started ${when(data.test_started_ms)} · ${number(data.sample_count,0)} source samples saved`;
 $('efEarnings').textContent=finite(p.balance)?`EarnFM balance $${number(p.balance,6)} · credited total ${number(p.gb,6)} GB · change $${number(p.earned,6)} / ${number(p.credited_mb,6)} MB since the recorded provider baseline`:'Awaiting the provider’s credited reading';
 $('efProviderTime').textContent=finite(p.observed_ms)?`Provider reading ${when(p.observed_ms)}${providerFresh?'':' · last recorded'}; baseline ${when(p.baseline_ms)}. Gross account figures, not net profit.`:'';
 if(selected===null&&data.points.length)selected=data.points.at(-1).time_ms;
 draw();rows();
}
async function refresh(){if(pending)return;pending=true;try{const response=await fetch('/ef.json',{cache:'no-store'});if(!response.ok)throw Error();data=await response.json();failed=false;render()}catch{failed=true;$('efStatus').textContent='Cannot read the EF recorder';if(data)render()}finally{pending=false}}
$('efRange').addEventListener('change',draw);window.addEventListener('resize',draw);refresh();setInterval(refresh,2000);
</script></body></html>
~~~~~~

### dashboard/static/fleet-test.js

<!-- rebuild-file: dashboard/static/fleet-test.js sha256=249c8547b6ae702c92cc954f8b0453ec280f9e08366c604df7dddb521dd2fe89 -->
~~~~~~javascript
"use strict";
(() => {
  const valid = value => typeof value === "number" && Number.isFinite(value);
  const num = (value, digits = 3) => valid(value) ? value.toLocaleString(undefined, {maximumFractionDigits: digits}) : "Unknown";
  const fresh = (age, limit) => valid(age) && age >= 0 && age <= limit;
  const CLIENTS = {running: "Accepted", error: "Client error", accepted: "Accepted", connected: "Connected", exited: "Client exited", device_limit: "Device limit", device_already_active: "Device already active", network_overused: "Network overused", network_unusable: "Network unusable", authorization_error: "Authorization failed", connected_last_observed_telemetry_stale: "Connection unverified", connected_last_observed_telemetry_unverified: "Connection unverified", starting: "Starting", waiting: "Waiting", rejected: "Rejected", unknown: "Unknown", unverified: "Unverified", disconnected: "Disconnected", reallocating: "Reallocating"};
  const ERRORS = {device_limit: "Provider device limit reached.", device_already_active: "Provider reports this device is already active.", network_overused: "Provider reports this network is overused.", network_unusable: "Provider cannot use this network.", authorization_error: "Provider authorization failed.", observer_error: "Observer could not verify this container.", disconnected: "Client disconnected; automatic reallocation after 2 minutes without recovery."};
  function workerState(service, worker, data) {
    const source = data.latest?.[service] || {};
    const native = service === "ps" && (worker.native_status_only === true || ["native_status_only", "native_sysfs_1s", "sysfs_via_salad_logs_1s"].includes(worker.sample_source));
    const observerFresh = !data.recorder_stale && (service !== "hg" || !source.status_stale) && (!native || fresh(source.status_age_ms, 90000));
    const clientFresh = observerFresh && fresh(service === "hg" ? worker.received_age_ms : worker.client_status_age_ms, native ? 240000 : 120000);
    const knownState = ["running", "stopped", "stopping", "pending", "starting", "allocating", "creating", "deploying", "failed", "succeeded"].includes(worker.state);
    const client = CLIENTS[worker.client_status] || "Unknown";
    const accepted = service === "hg" ? worker.client_status === "connected" : ["accepted", "running"].includes(worker.client_status);
    const bad = ["error", "exited", "device_limit", "device_already_active", "network_overused", "network_unusable", "authorization_error", "rejected"].includes(worker.client_status);
    const working = clientFresh && worker.state === "running" && accepted && !worker.error_code;
    const knownFailure = observerFresh && ((knownState && worker.state !== "running") || (clientFresh && (bad || Boolean(worker.error_code) && worker.error_code !== "observer_error")));
    const networkFresh = observerFresh && (service === "hg" ? fresh(worker.received_age_ms, 120000) : fresh(worker.received_age_ms, ["native_sysfs_1s", "sysfs_via_salad_logs_1s"].includes(worker.sample_source) ? 45000 : worker.sample_source === "salad_logs_10s" ? 25000 : 15000) && valid(worker.source_age_ms) && worker.source_age_ms >= -15000 && worker.source_age_ms <= 60000);
    return {working, unknown: !working && !knownFailure, client, networkFresh, observerFresh, clientFresh,
      label: working ? "Working" : knownFailure ? "Needs attention" : "Unknown",
      tone: working ? "ok" : knownFailure ? "bad" : "warn"};
  }
  function serviceModel(service, data) {
    const source = data.latest?.[service] || {};
    const desired = Math.min(50, data.experiment?.[service]?.desired || 10);
    const workers = [...(source.workers || [])];
    while (workers.length < desired) workers.push({state: "unknown", client_status: "unknown"});
    const states = workers.map(worker => workerState(service, worker, data));
    const providerFresh = !data.recorder_stale && fresh(source.provider_age_ms, service === "hg" ? 360000 : 180000);
    const earnings = data.summary?.[service === "hg" ? "hg_gathering_credits" : "ps_credited_mb"];
    const network = data.summary?.[`${service}_network_mb`];
    const networkKnown = !data.recorder_stale && (service !== "hg" || !source.status_stale) && source.network_complete === true && states.length >= desired && states.every(s => s.networkFresh) && valid(network);
    return {source, desired, workers, states, working: states.filter(s => s.working).length, unknown: states.filter(s => s.unknown).length,
      providerFresh, earnings, earningsKnown: providerFresh && valid(earnings), network, networkKnown};
  }
  function chartValue(metric) {
    if (!metric || !valid(metric.delta) || ["counter_reset", "gap"].includes(metric.status) || (metric.status === "incomplete" && metric.delta === 0)) return null;
    return metric.delta;
  }
  function windowStart(service, data) {
    const value = data.service_windows?.[service]?.start_ms;
    return valid(value) ? value : data.experiment?.started_ms;
  }
  function displayedIntervals(service, kind, data) {
    const start = windowStart(service, data);
    return (data.timeline?.[service]?.[kind] || []).filter(p => !valid(start) || p.start_ms >= start);
  }
  const SERVICES=[
    {id:'hg',hash:'#hg1',name:'Honeygain',url:'/api/fleet-test?service=hg'},
    {id:'ps',hash:'#ps1',name:'PacketStream',url:'/api/ps1/minutes'},
    {id:'proxyrack',hash:'#proxyrack',name:'Proxyrack',url:'/api/proxyrack'},
    {id:'rp',hash:'#rp',name:'Repocket',url:'/api/repocket?chart=1'},
    {id:'earnfm',hash:'#earnfm',name:'RFM',url:'/api/earnfm'},
    {id:'tm',hash:'#tm',name:'Traffic Monetizer',url:'/api/traffmonetizer?chart=1'}
  ];
  const shown=(value,digits=3)=>valid(value)?num(value,digits):'—';
  const mb=value=>valid(value)?shown(value)+' MB':'Not reported';
  const usd=value=>valid(value)?'$'+shown(value,6):'Not reported';
  const diff=(end,start)=>valid(end)&&valid(start)&&end>=start?end-start:null;
  const normalizeMinute=(time,amount,nodes=[],partial=false,estimated=false)=>({minute_ms:time,mb:valid(amount)?amount:null,partial,estimated,count:nodes.length,nodes:[...nodes].sort((a,b)=>b.mb-a.mb).slice(0,20)});
  function normalize(service,d,now=Date.now(),billing=null){
    const result={at:now,statusFresh:true,name:SERVICES.find(s=>s.id===service)?.name,desired:10,running:null,working:0,total:null,start:null,source:d.generated_ms,credited:'Not reported',earned:'Not reported',creditNote:'',notice:'',nodes:[],minutes:[],estimated:false};
    const delay=valid(d.generated_ms)?now-d.generated_ms:Infinity,recordingFresh=delay>=-10000&&delay<=90000;
    if(service==='hg'){
      const m=serviceModel('hg',d),s=m.source;
      result.desired=m.desired;result.running=s.running;result.working=m.working;result.total=valid(s.network_total_bytes)?s.network_total_bytes/1e6:m.network;result.start=windowStart('hg',d);result.source=s.status_observed_ms;result.minutes=d.hg_minutes||[];result.estimated=true;result.statusFresh=Boolean(d.latest?.hg)&&!d.recorder_stale&&!s.status_stale;
      const intervals=displayedIntervals('hg','provider',d).filter(p=>valid(p.per_second)&&chartValue(p)!==null),credits=intervals.length?intervals.reduce((sum,p)=>sum+p.delta,0):null;
      result.credited=valid(credits)?shown(credits)+' credits':'Not reported';result.earned=valid(credits)?shown(credits)+' credits':'Not reported';
      result.creditNote='Honeygain gathering credits from recorded intervals'+(m.providerFresh?'':'; provider reading is stale');
      if(d.recorder_stale||s.status_stale)result.notice='Honeygain recorder or client status is stale.';
      result.nodes=m.workers.map((w,i)=>({id:w.machine||w.group||String(i),ip:w.ip,status:m.states[i].clientFresh?m.states[i].client:'Unverified',salad:w.state,working:m.states[i].working,
        rate:m.states[i].networkFresh&&valid(w.network_interval?.per_second)?w.network_interval.per_second*60/1e6:null,total:valid(w.network_bytes)?w.network_bytes/1e6:null,
        duration:diff(w.network_last_ms,w.network_first_ms),age:w.received_age_ms,error:ERRORS[w.error_code]||''}));
    }else if(service==='ps'){
      result.desired=d.desired||10;result.running=(d.nodes||[]).filter(n=>n.salad_state==='running').length;result.working=d.running;result.total=d.total_mb;result.start=d.started_ms;result.source=valid(d.inventory_age_ms)?d.time_ms-d.inventory_age_ms:null;result.minutes=d.candles||[];result.estimated=result.minutes.some(m=>m.estimated);result.statusFresh=d.inventory_fresh;
      result.notice=d.collector?.error||(!d.inventory_fresh?'PacketStream inventory is stale.':'');
      result.nodes=(d.nodes||[]).map(n=>({id:n.instance,ip:n.ip,status:n.status,salad:n.salad_state,working:n.status==='Running',rate:n.metrics_fresh?n.latest_mb_per_minute:null,total:n.total_mb,duration:valid(n.elapsed_seconds)?n.elapsed_seconds*1000:null,age:n.sample_age_ms,error:n.error||''}));
      const readings=(billing?.billing?.readings||[]).filter(r=>valid(r.time_ms)&&valid(d.started_ms)&&r.time_ms>=d.started_ms&&valid(r.gb));
      if(readings.length>=2&&readings.every((r,i)=>!i||r.gb>=readings[i-1].gb))result.credited=mb((readings.at(-1).gb-readings[0].gb)*1000);
      result.creditNote=readings.length<2?'PacketStream has no provider baseline and follow-up for this recording. Earnings are not reported.':'Provider credited traffic comes from account readings; earnings are not reported.';
      if(!valid(billing?.feed_age_ms)||billing.feed_age_ms>180000)result.creditNote+=' Provider feed is stale.';
    }else if(service==='proxyrack'){
      result.desired=d.requested||10;result.running=recordingFresh&&!d.cloud_error?(d.workers||[]).filter(w=>w.salad_state?.toLowerCase()==='running').length:null;result.total=valid(d.total_recorded_mb)?d.total_recorded_mb:d.network_mb;result.start=Date.parse(d.started_at);result.minutes=(d.minutes||[]).map(m=>({...m,partial:m.partial||m.count<(d.requested||10)}));result.estimated=result.minutes.some(m=>m.estimated);result.statusFresh=recordingFresh&&!d.cloud_error;
      result.credited=mb(d.credited_mb);result.creditNote='Cached PR credited bandwidth includes replaced replicas. Readings available for '+(d.credited_devices||0)+'/'+result.desired+' current devices. Network RX + TX counts both sides of relayed traffic and includes overhead.'+(d.balance?' Account balance '+d.balance+' covers the whole account.':'')+' Earnings for this group are not reported. Connection status comes from registered client logs; provider API checks are paced below its five requests/minute limit.';
      result.notice=d.cloud_error||(!recordingFresh?'Proxyrack recorder is stale.':'');
      result.nodes=(d.workers||[]).map(w=>{
        const networkFresh=recordingFresh&&!d.cloud_error&&valid(w.sample_age_ms)&&fresh(w.sample_age_ms+delay,150000),ip=w.provider_status?.match(/(?:Online|Offline):\s*(\S+)/i)?.[1];
        const connected=networkFresh&&w.fresh&&!w.client_error&&w.client_state==='running'&&w.salad_state?.toLowerCase()==='running';
        return {id:w.name,ip,status:connected?'Connected':w.client_error==='registration_pending'?'Registration pending':w.status||'Unverified',salad:w.salad_state,working:connected,rate:networkFresh&&w.fresh?w.mb_per_minute:null,total:w.network_mb,duration:null,age:valid(w.sample_age_ms)?w.sample_age_ms+delay:null,error:w.client_error||w.provider_error||''};
      });result.working=result.nodes.filter(n=>n.working).length;
    }else if(service==='rp'){
      result.desired=d.desired||10;result.running=recordingFresh?d.running:null;result.total=d.total_network_mb;result.start=d.test_started_ms||Math.min(...(d.workers||[]).map(w=>w.started_ms).filter(valid));result.source=d.generated_ms;result.statusFresh=recordingFresh&&!d.error;
      result.notice=d.error||(!recordingFresh?'Repocket recorder is stale.':'');
      result.nodes=(d.workers||[]).filter(w=>w.current!==false).map(w=>{const recent=recordingFresh&&!d.error&&fresh(now-w.source_ms,60000),diag=w.diagnostics,notes=[];
        if(w.reason)notes.push(w.reason);const policy=w.policy;
        if(policy&&recent){notes.push(policy.state==='observing'?'Auto replacement: observing '+shown(policy.observed_ms/60000,1)+'/'+shown(policy.window_ms/60000,0)+' min':policy.state==='reallocating'?'Auto replacement: reallocating':policy.state==='keeping'?'Auto replacement: keeping this node':'Auto replacement: '+policy.state.replaceAll('_',' '));if(valid(policy.target_bytes)&&fresh(now-policy.checked_ms,60000))notes.push('Recent window: '+shown(policy.target_bytes/1e6)+' MB target traffic; '+policy.failures+'/'+policy.outcomes+' failed-before-reply outcomes');const errors=Object.entries(fresh(now-policy.checked_ms,60000)?policy.errors||{}:{}).sort((a,b)=>b[1]-a[1]).slice(0,3);if(errors.length)notes.push('Recent errors: '+errors.map(([name,n])=>name+': '+n).join('; '));}else notes.push('Replacement status not yet reported');
        if(!diag||!recent||!fresh(now-diag.time_ms,60000))notes.push('Target diagnostics unavailable');
        return {id:w.instance||w.run,ip:w.ip,status:recent?(w.status==='connected'?'Connected (control)':w.status):'Unverified',salad:w.salad_state,working:recent&&w.phase==='connected'&&w.salad_state==='running',rate:recent?w.last_mb_per_minute:null,total:w.total_mb,duration:diff(w.last_end_ms,w.started_ms),age:diff(now,w.source_ms),error:notes.join(' · ')};});
      result.working=result.nodes.filter(n=>n.working).length;
      result.minutes=d.chart_minutes||(d.minutes||[]).map(m=>normalizeMinute(m.time_ms,m.mb,(m.contributions||[]).map(n=>({instance:n.instance||n.run,ip:n.ip,mb:n.mb})),m.partial));
      result.earned=d.provider?.today_earned_text||d.provider?.earned_text||'Not reported';result.credited=d.provider?.today_traffic_text||d.provider?.traffic_text||'Not reported';
      const providerStale=d.provider&&!fresh(now-d.provider.observed_ms,180000);
      if(providerStale){if(result.earned!=='Not reported')result.earned+=' (stale)';if(result.credited!=='Not reported')result.credited+=' (stale)';}
      result.creditNote='Connected confirms the control link. Replacement decisions use recent HTTP/HTTPS and SOCKS target traffic and connection outcomes, not paid earnings or HTTP success. RP network totals are received + sent bytes, including both directions of relayed traffic; they are not provider-credited bandwidth. Provider-day account snapshot'+(valid(d.provider?.observed_ms)?' · '+new Date(d.provider.observed_ms).toLocaleString():' not published')+(providerStale?' · stale':'')+'.';
      const rule=(d.workers||[]).find(w=>w.policy)?.policy;if(rule)result.creditNote+=' Automatic replacement after '+shown(rule.window_ms/60000,0)+' min: below '+shown(rule.min_target_bytes/1e6)+' MB target traffic. Control connection failures are replaced after 60 seconds; client exits are replaced immediately. Destination errors are reported separately.';
      const action=d.recent_recovery?.[0];if(action)result.creditNote+=' Last automatic replacement request: '+(action.ip||action.machine?.slice(0,8)||'worker')+' · '+new Date(action.time_ms).toLocaleString()+' · '+(action.http_status>=200&&action.http_status<300?'accepted by Salad':action.http_status?'HTTP '+action.http_status:'request failed; container restart fallback')+' · '+action.reason+'.';
    }else if(service==='tm'){
      result.desired=d.deployment?.desired_replicas||10;result.running=recordingFresh&&!d.stale?d.running:null;result.working=recordingFresh&&!d.stale?d.working||0:0;result.total=valid(d.recorded?.rx)&&valid(d.recorded?.tx)?(d.recorded.rx+d.recorded.tx)/1e6:null;result.start=d.deployment?.measurement_started_ms||Date.parse(d.deployment?.started_at);result.source=d.generated_ms;result.statusFresh=recordingFresh&&!d.stale&&!d.errors?.recorder;
      result.credited=mb(d.credited?.credited_bytes/1e6);result.earned=usd(d.credited?.credited_usd);result.creditNote=(d.credited?.scope||'TM provider account figures')+(d.credited?.fresh?'':'; provider reading is stale');
      result.notice=Object.values(d.errors||{}).join(' · ')||(!recordingFresh||d.stale?'Traffic Monetizer recorder is stale.':'');
      result.nodes=(d.workers||[]).map(w=>{const recent=recordingFresh&&!d.stale&&fresh(now-w.time_ms,45000);return {id:w.instance,ip:w.ip,status:recent?w.state:'Unverified',salad:w.salad_state,working:recent&&w.working,rate:recent?w.raw_mb_per_minute:null,total:valid(w.test_rx)&&valid(w.test_tx)?(w.test_rx+w.test_tx)/1e6:null,duration:w.test_duration_ms,age:diff(now,w.time_ms),error:[w.error,valid(w.native_recent_bytes)?'Relay observed: '+mb(w.native_recent_bytes/1e6)+' / '+shown(w.native_recent_requests,0)+' requests over '+shown(w.native_recent_ms/60000,1)+' min':'Relay window not yet measured'].filter(Boolean).join('; ')};});
      result.working=result.nodes.filter(n=>n.working).length;
      result.minutes=d.chart_minutes||(d.minutes||[]).map(m=>normalizeMinute(m.time_ms,(m.rx_bytes+m.tx_bytes)/1e6,(m.workers||[]).map(w=>({instance:w.instance,ip:w.ip||(d.workers||[]).find(n=>n.run===w.run)?.ip,mb:(w.rx+w.tx)/1e6})),m.samples<result.desired*60));
    }else if(service==='earnfm'){
      result.desired=d.desired||10;result.running=recordingFresh?(d.workers||[]).filter(w=>w.salad_state==='running').length:null;result.total=d.total_mb;result.start=d.test_started_ms;result.source=d.inventory_ms||d.generated_ms;result.statusFresh=recordingFresh&&!d.error;result.notice=d.error||(!recordingFresh?'RFM recorder is stale.':'');
      result.nodes=(d.workers||[]).map(w=>{
        const recent=recordingFresh&&!d.error&&fresh(now-w.sample_ms,90000),providerFresh=fresh(now-d.provider?.observed_ms,180000)&&!d.provider?.error;
        const runtime=w.runtime_instance||w.instance,present=Array.isArray(d.provider?.devices)?d.provider.devices.some(device=>device.instance===runtime):w.provider_online===true?true:null;
        const working=recent&&!w.final&&w.client_state==='running'&&w.salad_state==='running'&&providerFresh&&present===true;
        let status=w.client_state;
        if(w.salad_state&&w.salad_state!=='running')status=w.salad_state;
        else if(!recent)status='Unverified';
        else if(w.client_state==='reallocating')status='Reallocating';
        else if(w.final)status='Stopped';
        else if(w.client_state==='running')status=!providerFresh?'Provider status unavailable':present===false?'Provider offline':working?'Connected':'Awaiting provider confirmation';
        return {id:runtime,ip:w.ip,status,salad:w.salad_state,working,rate:recent&&!w.final&&valid(w.kb_per_second)?w.kb_per_second*.06:null,total:w.total_mb,duration:null,age:diff(now,w.sample_ms),error:w.error||(w.client_state==='rate_limited'?'Provider cooldown':!providerFresh&&d.provider?.error?d.provider.error:'')};
      });result.working=result.nodes.filter(n=>n.working).length;
      result.minutes=(d.points||[]).map(m=>normalizeMinute(m.time_ms,m.mb,Object.entries(m.by_instance||{}).map(([id,amount])=>({instance:id,ip:(d.workers||[]).find(w=>(w.runtime_instance||w.instance)===id)?.ip,country:(d.workers||[]).find(w=>(w.runtime_instance||w.instance)===id)?.country,mb:amount})),m.partial));
      result.earned=usd(d.provider?.earned);result.credited=mb(d.provider?.credited_mb);result.creditNote='EarnFM gross account balance change and credited traffic since its recorded baseline'+(valid(d.provider?.baseline_ms)?' · '+new Date(d.provider.baseline_ms).toLocaleString():'')+(!fresh(now-d.provider?.observed_ms,180000)||d.provider?.error?' · provider reading is stale':'')+'.';
    }
    result.estimated=result.estimated||result.minutes.some(m=>m.estimated);
    if(result.statusFresh){
      for(const node of result.nodes){
        const state=node.salad?.toLowerCase();
        if(['allocating','downloading','creating','stopping','stopped'].includes(state)){
          node.status=state[0].toUpperCase()+state.slice(1);node.working=false;node.rate=null;
          if(['allocating','downloading','creating'].includes(state))node.error='Waiting for the client to start on this machine.';
        }
      }
      result.working=result.nodes.filter(node=>node.working).length;
      while(result.nodes.length<result.desired)result.nodes.push({id:service+'-pending-'+result.nodes.length,pending:true,status:'Awaiting inventory',working:false,error:'No machine listed in the latest inventory.'});
    }
    if(!result.statusFresh){result.working=null;result.running=null;result.nodes=result.nodes.map(n=>({...n,working:false,status:"Unverified",stale:true,rate:null}));}
    return result;
  }
  function periodMinutes(minutes,hours,now=Date.now()){
    const end=Math.floor(now/60000)*60000,start=end-(hours*60-1)*60000,byTime=new Map(minutes.map(m=>[m.minute_ms,m]));
    return Array.from({length:hours*60},(_,i)=>byTime.get(start+i*60000)||{minute_ms:start+i*60000,mb:null,partial:true,count:0,nodes:[]});
  }
  if(typeof module!=='undefined'&&module.exports){module.exports={workerState,serviceModel,chartValue,windowStart,displayedIntervals,normalize,periodMinutes,SERVICES};return;}
  const el=id=>document.getElementById(id),make=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;};
  const duration=ms=>!valid(ms)?'—':Math.floor(ms/3600000)+'h '+Math.floor(ms%3600000/60000)+'m';
  const age=ms=>!valid(ms)?'—':ms<60000?shown(ms/1000,0)+'s':shown(ms/60000,1)+'m';
  const statusNames={unverified:'Status not received',unknown:'Awaiting client status','checking client':'Awaiting client status',stale:'Monitor delayed','status feed stale':'Monitor delayed',rate_limited:'Provider cooldown',connection_error:'Connection failed',reallocating:'Reallocating',awaiting_sample:'Awaiting first sample','online / running':'Connected'};
  const aliases={'/proxyrack':'proxyrack','/rp':'rp','/repocket':'rp','/earnfm':'earnfm','/traffmonetizer':'tm','/tm':'tm'};
  let active=SERVICES.find(s=>s.hash===location.hash)||SERVICES.find(s=>s.id===aliases[location.pathname.replace(/\.html$/,'')])||SERVICES[1],hours=12,data=null,model=null,busy=false,generation=0,billing=null,billingPending=false,billingChecked=0;
  const buttons=new Map();el('services').replaceChildren();
  for(const service of SERVICES){const button=make('button',service.name);button.id='tab-'+service.id;button.setAttribute('role','tab');button.setAttribute('aria-controls','bandwidthPanel');button.onclick=()=>select(service);buttons.set(service.id,button);el('services').append(button);}
  const panel=el('bandwidthPanel');
  panel.innerHTML='<div id="totals" class="summary-line"></div><p id="notice" class="notice hidden" role="status"></p>'+ 
    '<div class="chart-controls"><h2 id="chartTitle">Network traffic</h2><label>Show <select id="hours" aria-label="Time range"><option value="1">1 hour</option><option value="6">6 hours</option><option value="12" selected>12 hours</option><option value="24">24 hours</option></select></label></div>'+ 
    '<div class="ps-chart"><div id="chartScroll" class="ps-chart-scroll"><canvas id="trafficChart" tabindex="0" role="img"></canvas></div><div id="minutePopup" class="ps-popup hidden" role="tooltip"></div></div>'+ 
    '<p id="chartNote" class="source-note"></p><div class="table-scroll"><table class="container-table"><thead><tr><th>Container / IP</th><th>Client</th><th>Salad</th><th>MB/min</th><th>Recorded MB</th><th>Recorded time</th><th>Last sample</th><th>Error / note</th></tr></thead><tbody id="workerRows"></tbody></table></div><p id="creditNote" class="source-note"></p>';
  const chart=window.createMinuteChart({canvas:el('trafficChart'),scroll:el('chartScroll'),popup:el('minutePopup'),active:()=>true,readMinute:async minute=>{
    if(active.id==='ps')return read('/api/ps1/minutes?minute='+minute);
    return model?.minutes.find(m=>m.minute_ms===minute)||{minute_ms:minute,mb:null,count:0,nodes:[]};
  }});
  async function read(url){const response=await fetch(url,{cache:'no-store',signal:AbortSignal.timeout(10000)});if(!response.ok){const error=await response.json().catch(()=>({}));throw new Error(typeof error.error==='string'?error.error:'HTTP '+response.status);}return response.json();}
  function render(){
    if(!model)return;
    const bars=periodMinutes(model.minutes,hours),measured=bars.filter(b=>valid(b.mb)),estimated=measured.some(b=>b.estimated);
    let amount=measured.length?measured.reduce((sum,b)=>sum+b.mb,0):null;
    const totals=el('totals');totals.replaceChildren();
    for(const [label,value] of [['Clients confirmed',shown(model.working,0)+'/'+model.desired+' · '+shown(model.running,0)+' containers running'],[active.id==='tm'?'Network RX + TX':'Total recorded',mb(model.total)],['Last '+hours+(hours===1?' hour':' hours'),(estimated?'≈ ':'')+mb(amount)],['Provider credited / earned',model.credited===model.earned?model.earned:model.credited+' · '+(model.earned==='Not reported'?'earnings not reported':model.earned)],['Elapsed',duration(diff(Date.now(),model.start))]]){const item=make('span',label+': ');item.append(make('strong',value));totals.append(item);}
    el('notice').textContent=model.notice;el('notice').classList.toggle('hidden',!model.notice);
    el('chartTitle').textContent=active.name+' · MB per minute';
    el('chartNote').textContent='Hover or click a bar for the top 20 IPs, countries and MB. '+(model.estimated?'≈ Minute estimates from saved counter intervals. ':'')+'Blank = no measurement; amber = partial coverage. Network traffic includes overhead.'+(active.id==='tm'?' TM row rates average the latest observed minute. Relay notes show client counter increases, not per-worker paid earnings.':'');
    const body=el('workerRows');body.replaceChildren();
    for(const n of model.nodes){const row=make('tr'),id=make('td',n.pending?'Unassigned':n.ip||n.id?.slice(0,12)||'IP unavailable');id.title=n.pending?'':n.id||'';row.dataset.instance=n.id;row.append(id,make('td',statusNames[n.status?.toLowerCase()]||n.status||'Awaiting client status',n.working?'ok':n.error?'bad':'stale'),make('td',(n.salad||'—')+(n.stale?' (last seen)':'')),make('td',shown(n.rate)),make('td',shown(n.total)),make('td',duration(n.duration)),make('td',age(valid(n.age)?n.age+Math.max(0,Date.now()-model.at):null)),make('td',n.error||''));body.append(row);}
    if(!model.nodes.length){const row=make('tr'),cell=make('td','Waiting for the recorder to publish its container inventory.');cell.colSpan=8;row.append(cell);body.append(row);}
    el('creditNote').textContent=model.creditNote;
    el('connection').textContent=active.name+' · status '+age(diff(Date.now(),model.source))+' old';
    el('connection').classList.toggle('bad',Boolean(model.notice));
    chart.update({time_ms:Date.now(),candles:bars});
  }
  async function refresh(){
    if(busy)return;busy=true;const ticket=generation,service=active;
    try{const result=await read(service.url);if(ticket!==generation)return;data=result;model=normalize(service.id,data,Date.now(),billing);render();}
    catch(e){if(ticket===generation){if(model){if(service.id==='rp'&&data)model=normalize('rp',data,Date.now(),billing);model.notice='Cannot refresh '+service.name+'. Last saved values are shown.';model.working=null;model.running=null;model.nodes=model.nodes.map(n=>({...n,working:false,status:'Unverified',stale:true,rate:null}));render();}else{model=normalize(service.id,{});model.nodes=[];model.working=null;model.running=null;model.notice='Waiting for '+service.name+' recorder: '+e.message;render();}}}
    finally{if(ticket===generation)busy=false;}
    if(service.id==='ps'&&!billingPending&&Date.now()-billingChecked>60000){billingPending=true;billingChecked=Date.now();read('/api/ps1/view').then(value=>{billing=value;if(active.id==='ps'&&data){const credit=normalize('ps',data,Date.now(),billing);if(model){model.credited=credit.credited;model.earned=credit.earned;model.creditNote=credit.creditNote;render();}}}).catch(()=>{}).finally(()=>{billingPending=false;});}
  }
  function select(service,changeHash=true){
    active=service;generation++;busy=false;data=null;model=null;chart.hide();chart.update({time_ms:Date.now(),candles:periodMinutes([],hours)});
    for(const item of SERVICES){const yes=item.id===service.id;buttons.get(item.id).setAttribute('aria-selected',String(yes));buttons.get(item.id).tabIndex=yes?0:-1;}
    panel.setAttribute('aria-labelledby','tab-'+service.id);if(changeHash)history.replaceState(null,'','/'+service.hash);document.title=service.name+' · Bandwidth test';
    el('connection').textContent=service.name+' · loading';el('totals').textContent='Loading '+service.name+' readings…';el('workerRows').replaceChildren();el('creditNote').textContent='';el('notice').classList.add('hidden');el('chartTitle').textContent=service.name+' · MB per minute';el('chartNote').textContent='Hover or click a minute for its contributors.';refresh();
  }
  el('hours').onchange=()=>{hours=Number(el('hours').value);chart.hide();if(model)render();else chart.update({time_ms:Date.now(),candles:periodMinutes([],hours)});};
  el('services').addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const index=SERVICES.indexOf(active),next=event.key==='Home'?0:event.key==='End'?SERVICES.length-1:(index+(event.key==='ArrowLeft'?-1:1)+SERVICES.length)%SERVICES.length;select(SERVICES[next]);buttons.get(active.id).focus();});
  window.addEventListener('hashchange',()=>select(SERVICES.find(s=>s.hash===location.hash)||SERVICES[1],false));
  select(active);setInterval(refresh,5000);
})();
~~~~~~

### dashboard/static/index.html

<!-- rebuild-file: dashboard/static/index.html sha256=ee39d93054a6f9d5088780ee5edd41617998189df4870f6bbd9e895853decb3a -->
~~~~~~html
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bandwidth test</title><link rel="stylesheet" href="/styles.css"></head>
<body>
<header><h1>Bandwidth test</h1><span id="connection" role="status">Loading…</span></header>
<main><nav id="services" role="tablist" aria-label="Services"></nav><section id="bandwidthPanel" role="tabpanel"></section></main>
<script src="/ps1.js" defer></script><script src="/fleet-test.js" defer></script>
</body></html>
~~~~~~

### dashboard/static/ps1.js

<!-- rebuild-file: dashboard/static/ps1.js sha256=a386aacc6db63b407dfa846d328b2860f98e6af6dfaabde98dc4382f57356558 -->
~~~~~~javascript
(() => {
  "use strict";
  const finite = value => typeof value === "number" && Number.isFinite(value);
  const number = (value, digits = 3) => finite(value) ? value.toLocaleString(undefined, {maximumFractionDigits: digits}) : "—";
  const clock = value => value == null ? "—" : new Date(value).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", hour12: false});
  const countries = new Intl.DisplayNames(undefined, {type:"region"});
  const make = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const countryCache = new Map();
  let countryLookup = null;
  async function lookupCountries(nodes) {
    if (nodes.every(n=>!n.ip || n.country || countryCache.has(n.ip))) return;
    if (countryLookup) await countryLookup;
    const ips=[...new Set(nodes.filter(n=>n.ip && !n.country && !countryCache.has(n.ip)).map(n=>n.ip))];
    if (!ips.length) return;
    countryLookup=(async()=>{
      try {
        const response=await fetch("https://api.country.is/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(ips),signal:AbortSignal.timeout(5000)});
        if (!response.ok) return;
        for (const row of await response.json()) if(ips.includes(row.ip) && /^[A-Z]{2}$/.test(row.country)) countryCache.set(row.ip,row.country);
      } catch (_) {}
    })();
    await countryLookup; countryLookup=null;
  }
  window.createMinuteChart = ({canvas, scroll, popup, active, readMinute}) => {
    let data=null, geometry=null, hover=null, pinned=false, detailTimer=null, detailRequest=0, detailPending=false;
  function draw() {
    if (!data || !active()) return;
    const bars = data.candles, width = scroll.clientWidth, height = 230;
    const dpr = Math.min(devicePixelRatio || 1, 2), left = 60, right = width - 10, top = 20, bottom = height - 30;
    canvas.style.width = width + "px"; canvas.width = Math.round(width * dpr); canvas.height = height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, width, height);
    ctx.font = "12px system-ui";
    if (!bars.length) {geometry=null;ctx.fillStyle="#555";ctx.fillText("Waiting for saved measurements…",12,110);return;}
    const maximum = Math.max(0.001, ...bars.map(b => b.mb || 0)), step = (right - left) / bars.length;
    for (let i = 0; i <= 3; i++) {
      const y = bottom - (bottom - top) * i / 3;
      ctx.strokeStyle = "#e3e3e3"; ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke();
      ctx.textAlign = "right"; ctx.fillStyle = "#555"; ctx.fillText(number(maximum * i / 3, 2), left - 7, y + 4);
    }
    bars.forEach((bar, i) => {
      const x = left + (i + .5) * step;
      if (bar.minute_ms === hover) {ctx.fillStyle = "#b8d7ed"; ctx.fillRect(x - 2, top, 4, bottom - top);}
      if (finite(bar.mb)) {
        const h = Math.max(1, bar.mb / maximum * (bottom - top));
        ctx.fillStyle = bar.partial ? "#a76508" : "#1769aa";
        ctx.fillRect(x - step * .35, bottom - h, step * .7, h);
      }
      if (i % Math.max(15, Math.round(bars.length/360)*60) === 0) {ctx.textAlign = "left"; ctx.fillStyle = "#555"; ctx.fillText(clock(bar.minute_ms), x, height - 9);}
    });
    ctx.textAlign = "right"; ctx.fillStyle = "#555"; ctx.fillText(clock(data.time_ms), right, height - 9);
    geometry = {left, right, step};
    const hours = Math.round(bars.length/60);
    canvas.setAttribute("aria-label", "Past " + hours + (hours === 1 ? " hour" : " hours") + ", one-minute traffic bars. Hover or click for the top 20 IPs, countries and megabytes. Arrow keys select a minute; Escape closes the popup.");
  }
  function hidePopup() {
    hover = null; pinned = false; detailPending = false; detailRequest++; clearTimeout(detailTimer);
    popup.classList.add("hidden"); draw();
  }
  function showMinute(index, event, refreshDetail = false) {
    const minute = data.candles[index].minute_ms;
    const wrap = scroll.parentElement.getBoundingClientRect();
    if (!refreshDetail) popup.style.left = Math.max(4, Math.min((event ? event.clientX - wrap.left : wrap.width - 330) + 12, wrap.width - 324)) + "px";
    if (!refreshDetail) popup.style.top = (event ? Math.max(8, event.clientY - wrap.top + 12) : 35) + "px";
    popup.classList.remove("hidden");
    const changed = hover !== minute;
    if (!changed && (!refreshDetail || detailPending)) return;
    hover = minute; detailPending = true; const ticket = ++detailRequest; clearTimeout(detailTimer); draw();
    if (changed) popup.replaceChildren(make("strong", clock(minute) + "–" + clock(minute + 60000)), make("p", "Reading contributions…"));
    detailTimer = setTimeout(async () => {
      try {
        const detail = await readMinute(minute);
        await lookupCountries(detail.nodes || []);
        if (ticket !== detailRequest) return;
        popup.replaceChildren(make("strong", clock(minute) + "–" + clock(minute + 60000) + " · " + (detail.estimated ? "≈ " : "") + number(detail.mb) + " MB"));
        if (!detail.count) {popup.append(make("p", detail.note || (finite(detail.mb) ? "Per-node detail is not available for this minute." : "No measurement recorded for this minute."))); return;}
        popup.append(make("p", "Top " + detail.nodes.length + " of " + detail.count + " contributing nodes"));
        const table = make("table"), head = make("tr");
        head.append(make("th","IP"),make("th","Country"),make("th","MB")); table.append(head);
        for (const node of detail.nodes) {
          const row = make("tr"); row.title = node.instance;
          row.append(make("td",node.ip || "Unknown"),make("td",(node.country || countryCache.get(node.ip)) ? countries.of(node.country || countryCache.get(node.ip)) : "Unknown"),make("td",number(node.mb)));
          table.append(row);
        }
        popup.append(table);
      } catch (_) {if (ticket === detailRequest) popup.replaceChildren(make("p","Cannot read this minute. Hover again to retry."));}
      finally {if (ticket === detailRequest) detailPending = false;}
    }, 70);
  }
  function indexAt(event) {
    if (!geometry) return null;
    const x = event.clientX - canvas.getBoundingClientRect().left;
    return x < geometry.left || x >= geometry.right ? null : Math.floor((x - geometry.left) / geometry.step);
  }
  canvas.addEventListener("pointermove", event => {const i=indexAt(event); if(i!=null && (!pinned || hover!==data.candles[i].minute_ms)){pinned=false;showMinute(i,event);}else if(i==null && !pinned)hidePopup();});
  canvas.addEventListener("pointerleave", () => {if (!pinned) hidePopup();});
  canvas.addEventListener("click", event => {const i=indexAt(event); if(i==null)return; if(pinned && hover===data.candles[i].minute_ms)hidePopup();else{pinned=true;showMinute(i,event);}});
  canvas.addEventListener("keydown", event => {
    if (!geometry || !data || !["ArrowLeft","ArrowRight","Home","End","Escape"].includes(event.key)) return;
    event.preventDefault(); if(event.key==="Escape"){hidePopup();return;}
    const bars=data.candles, index=hover==null ? bars.length-1 : bars.findIndex(b=>b.minute_ms===hover);
    pinned=true; showMinute(event.key==="Home" ? 0 : event.key==="End" ? bars.length-1 : Math.max(0,Math.min(bars.length-1,index+(event.key==="ArrowLeft"?-1:1))));
  });
    window.addEventListener("servicechange",hidePopup);
    window.addEventListener("resize",draw);
    return {hide:hidePopup,update(next){
      data=next; draw();
      if (hover!=null) {const i=data.candles.findIndex(b=>b.minute_ms===hover);if(i<0)hidePopup();else showMinute(i,undefined,true);}
    }};
  };
})();

"use strict";
// Preserve the existing provider-tab bridge; it is separate from presentation.
(() => {
  const button = document.getElementById("psConnect"), message = document.getElementById("psFeedStatus") || {textContent:""};
  let providerWindow = null, state = null, pending = null;
  let channel = sessionStorage.getItem("ps-billing-channel") || "";
  function refresh() {
    if(pending) return pending;
    pending = (async () => {
      try {
        const response=await fetch("/api/ps1/view",{cache:"no-store",signal:AbortSignal.timeout(8000)});
        if(!response.ok)throw new Error();
        state=await response.json();
        message.textContent=state.feed_age_ms!=null&&state.feed_age_ms<150000?"Provider readings are connected.":"Provider readings are missing or stale. Keep the connected provider tab open.";
      } catch(_) {state=null;message.textContent="Provider connection status is unknown.";}
    })().finally(()=>{pending=null;});
    return pending;
  }
  button?.addEventListener("click",()=>{
    if(providerWindow&&!providerWindow.closed){providerWindow.focus();return;}
    if(!channel){channel=crypto.randomUUID();sessionStorage.setItem("ps-billing-channel",channel);}
    providerWindow=window.open(`https://app.packetstream.io/dashboard#ps-sync=${channel}`,"psBillingSync");
    message.textContent="Provider tab opened. Waiting for credited-traffic readings.";refresh();
  });
  window.addEventListener("message",async event=>{
    if(event.origin!=="https://app.packetstream.io"||!channel||event.data?.type!=="ps-credited"||event.data.channel!==channel)return;
    if(providerWindow&&event.source!==providerWindow)return;
    if(event.data.error){message.textContent="Provider reading could not be retrieved.";return;}
    await refresh();if(!state?.bridge_token||!Number.isFinite(event.data.gb))return;
    try{
      const save=()=>fetch("/api/ps1/credited",{method:"POST",headers:{"Content-Type":"application/json","X-PS-Token":state.bridge_token},body:JSON.stringify({gb:event.data.gb,bytes:event.data.bytes,time_ms:event.data.time_ms})});
      let response=await save();
      if(response.status===403){await refresh();if(!state?.bridge_token)throw new Error();response=await save();}
      if(!response.ok)throw new Error();message.textContent="Provider reading saved.";
    }
    catch(_){message.textContent="Provider reading could not be saved.";}
  });
  document.getElementById("history")?.addEventListener("toggle",event=>{if(event.currentTarget.open)refresh();});
})();
~~~~~~

### dashboard/static/styles.css

<!-- rebuild-file: dashboard/static/styles.css sha256=b7c37ee6cd698d1b327a51a62849a51d817435d166170a70791ebb6e68d7c9eb -->
~~~~~~css
:root{font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#161616;background:#fff;color-scheme:light}
*{box-sizing:border-box}body{margin:0;padding:16px 22px}header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:12px}h1{font-size:20px;margin:0}h2{font-size:16px;margin:0}p{margin:7px 0}
button,select{font:inherit;border:1px solid #aaa;border-radius:2px;background:#fff;color:inherit;padding:5px 9px;cursor:pointer}button:focus-visible,select:focus-visible{outline:2px solid #1767b5;outline-offset:2px}
nav{display:flex;flex-wrap:wrap;gap:6px;border-bottom:1px solid #999;padding-bottom:7px;margin-bottom:12px}nav button[aria-selected=true]{font-weight:700;background:#ededed;border-color:#333}
#connection,.source-note,.summary-line{font-size:12px}.summary-line{display:flex;flex-wrap:wrap;gap:8px 24px;margin:7px 0}.summary-line strong{font-size:14px}.summary-line span{white-space:nowrap}.source-note{color:#555}
.notice{color:#8b3b00;background:#fff8ed;padding:6px 9px;font-size:12px}.chart-controls{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:8px 0}.chart-controls label{font-size:12px}.chart-controls select{margin-left:5px}
.table-scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;text-align:left;font-size:12px}th,td{padding:7px 9px;border:1px solid #ccc;vertical-align:top;font-variant-numeric:tabular-nums}th{background:#f2f2f2;font-weight:600}.container-table{min-width:800px}.container-table td:first-child{max-width:250px;overflow-wrap:anywhere}
.ok{color:#126428}.bad{color:#ad230d}.stale{color:#777}.hidden{display:none!important}
.ps-chart{position:relative}.ps-chart-scroll{width:100%;overflow-x:auto;border:1px solid #bbb;margin:8px 0}.ps-chart-scroll canvas{display:block;height:230px;cursor:crosshair}.ps-chart-scroll canvas:focus-visible{outline:2px solid #1769aa;outline-offset:-2px}
.ps-popup{position:absolute;z-index:5;background:white;border:1px solid #888;box-shadow:0 2px 8px #0002;padding:10px;width:320px;max-width:calc(100% - 8px);max-height:70vh;overflow:auto;font-size:12px}.ps-popup p{margin:5px 0}.ps-popup th,.ps-popup td{padding:4px 6px}.ps-popup th:last-child,.ps-popup td:last-child{text-align:right;white-space:nowrap}
@media(max-width:650px){body{padding:10px}header{align-items:start}#connection{max-width:150px;text-align:right}.summary-line{gap:6px 14px}.chart-controls{gap:8px}}
~~~~~~

### dashboard/store.py

<!-- rebuild-file: dashboard/store.py sha256=1217de0c6e729cb87df4eae1d8842ebd518ef83774d82e9048ccb8ea9f37f0da -->
~~~~~~python
"""SQLite persistence and aggregation for Salad bandwidth samples."""

from __future__ import annotations

import json
import re
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


APP_NAMES = ("packetstream", "proxyrack", "traffmonetizer", "earnfm", "repocket", "bitping", "honeygain")
MINUTE_MS = 60_000
LIVE_SAMPLE_GRACE_MS = 120_000
HONEYGAIN_EVENTS = {
    "start",
    "authenticated",
    "service_starting",
    "connected",
    "disconnected",
    "network_overused",
    "duplicate_device",
    "device_limit_exceeded",
    "unusable_network",
    "authentication_error",
    "api_ping_error",
    "exit",
    "stopping",
    "stopped",
}


def parse_time_ms(value: str) -> int:
    value = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], value, count=1)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(round(parsed.timestamp() * 1000))


class Store:
    def __init__(self, path: Path, raw_retention_days: int = 30):
        self.path = Path(path)
        self.raw_retention_days = raw_retention_days
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA journal_mode = WAL")
        self._db.execute("PRAGMA synchronous = NORMAL")
        self._create_schema()
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def _create_schema(self) -> None:
        with self._db:
            self._db.executescript(
                """
                CREATE TABLE IF NOT EXISTS samples (
                    instance_id TEXT NOT NULL,
                    sample_time_ms INTEGER NOT NULL,
                    sequence INTEGER NOT NULL,
                    receive_time_ms INTEGER NOT NULL,
                    machine_id TEXT NOT NULL,
                    public_ip TEXT NOT NULL DEFAULT '',
                    public_ip_status TEXT NOT NULL DEFAULT 'unknown',
                    interface TEXT NOT NULL,
                    counter_reset INTEGER NOT NULL,
                    eth_rx_total INTEGER NOT NULL,
                    eth_tx_total INTEGER NOT NULL,
                    eth_rx_bytes INTEGER NOT NULL,
                    eth_tx_bytes INTEGER NOT NULL,
                    eth_rx_rate INTEGER NOT NULL DEFAULT 0,
                    eth_tx_rate INTEGER NOT NULL DEFAULT 0,
                    captured_rx_bytes INTEGER NOT NULL,
                    captured_tx_bytes INTEGER NOT NULL,
                    unassigned_rx_bytes INTEGER NOT NULL,
                    unassigned_tx_bytes INTEGER NOT NULL,
                    coverage_percent REAL NOT NULL,
                    organization_name TEXT NOT NULL DEFAULT '',
                    project_name TEXT NOT NULL DEFAULT '',
                    container_group_name TEXT NOT NULL DEFAULT '',
                    container_group_version TEXT NOT NULL DEFAULT '',
                    capture_mode TEXT NOT NULL DEFAULT 'packet',
                    interval_milliseconds INTEGER NOT NULL DEFAULT 1000,
                    partial_interval INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (instance_id, sample_time_ms, sequence)
                );
                CREATE INDEX IF NOT EXISTS samples_time ON samples(sample_time_ms);
                CREATE INDEX IF NOT EXISTS samples_receive_time ON samples(receive_time_ms);

                CREATE TABLE IF NOT EXISTS app_samples (
                    instance_id TEXT NOT NULL,
                    sample_time_ms INTEGER NOT NULL,
                    sequence INTEGER NOT NULL,
                    app_name TEXT NOT NULL,
                    rx_bytes INTEGER NOT NULL,
                    tx_bytes INTEGER NOT NULL,
                    process_count INTEGER NOT NULL,
                    socket_count INTEGER NOT NULL,
                    tcp_socket_count INTEGER NOT NULL DEFAULT 0,
                    tcp_established_count INTEGER NOT NULL DEFAULT 0,
                    udp_socket_count INTEGER NOT NULL DEFAULT 0,
                    state TEXT NOT NULL,
                    PRIMARY KEY (instance_id, sample_time_ms, sequence, app_name),
                    FOREIGN KEY (instance_id, sample_time_ms, sequence)
                        REFERENCES samples(instance_id, sample_time_ms, sequence) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS app_samples_time ON app_samples(sample_time_ms);

                CREATE TABLE IF NOT EXISTS instance_segments (
                    instance_id TEXT PRIMARY KEY,
                    machine_id TEXT NOT NULL,
                    first_seen_ms INTEGER NOT NULL,
                    last_seen_ms INTEGER NOT NULL,
                    public_ip TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS minute_rollups (
                    minute_ms INTEGER NOT NULL,
                    instance_id TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    sample_count INTEGER NOT NULL,
                    eth_rx_bytes INTEGER NOT NULL,
                    eth_tx_bytes INTEGER NOT NULL,
                    captured_rx_bytes INTEGER NOT NULL,
                    captured_tx_bytes INTEGER NOT NULL,
                    unassigned_rx_bytes INTEGER NOT NULL,
                    unassigned_tx_bytes INTEGER NOT NULL,
                    reset_count INTEGER NOT NULL,
                    partial_interval_count INTEGER NOT NULL DEFAULT 0,
                    eth_rx_rate_sum INTEGER NOT NULL DEFAULT 0,
                    eth_tx_rate_sum INTEGER NOT NULL DEFAULT 0,
                    coverage_sum REAL NOT NULL DEFAULT 0,
                    first_sample_ms INTEGER NOT NULL DEFAULT 0,
                    last_sample_ms INTEGER NOT NULL DEFAULT 0,
                    peak_rate INTEGER NOT NULL DEFAULT 0,
                    peak_time_ms INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (minute_ms, instance_id)
                );
                CREATE INDEX IF NOT EXISTS minute_rollups_time ON minute_rollups(minute_ms);

                CREATE TABLE IF NOT EXISTS minute_app_rollups (
                    minute_ms INTEGER NOT NULL,
                    instance_id TEXT NOT NULL,
                    app_name TEXT NOT NULL,
                    rx_bytes INTEGER NOT NULL,
                    tx_bytes INTEGER NOT NULL,
                    PRIMARY KEY (minute_ms, instance_id, app_name),
                    FOREIGN KEY (minute_ms, instance_id)
                        REFERENCES minute_rollups(minute_ms, instance_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS ingest_state (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    watermark_ms INTEGER,
                    last_poll_ms INTEGER,
                    last_success_ms INTEGER,
                    last_new_samples INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT ''
                );
                INSERT OR IGNORE INTO ingest_state(singleton) VALUES (1);

                CREATE TABLE IF NOT EXISTS runtime_events (
                    instance_id TEXT NOT NULL,
                    event_time_ms INTEGER NOT NULL,
                    receive_time_ms INTEGER NOT NULL,
                    machine_id TEXT NOT NULL,
                    organization_name TEXT NOT NULL DEFAULT '',
                    project_name TEXT NOT NULL DEFAULT '',
                    container_group_name TEXT NOT NULL DEFAULT '',
                    container_group_version TEXT NOT NULL DEFAULT '',
                    kind TEXT NOT NULL,
                    event TEXT NOT NULL,
                    client_version TEXT NOT NULL DEFAULT '',
                    attempt INTEGER NOT NULL DEFAULT 0,
                    exit_code INTEGER NOT NULL DEFAULT 0,
                    severity TEXT NOT NULL DEFAULT 'default',
                    PRIMARY KEY (instance_id, event_time_ms, kind, event, attempt)
                );
                CREATE INDEX IF NOT EXISTS runtime_events_time ON runtime_events(event_time_ms);
                """
            )
        columns = {row[1] for row in self._db.execute("PRAGMA table_info(app_samples)").fetchall()}
        with self._db:
            for name in ("tcp_socket_count", "tcp_established_count", "udp_socket_count"):
                if name not in columns:
                    self._db.execute(f"ALTER TABLE app_samples ADD COLUMN {name} INTEGER NOT NULL DEFAULT 0")
        sample_columns = {row[1] for row in self._db.execute("PRAGMA table_info(samples)").fetchall()}
        sample_additions = {
            "organization_name": "TEXT NOT NULL DEFAULT ''",
            "project_name": "TEXT NOT NULL DEFAULT ''",
            "container_group_name": "TEXT NOT NULL DEFAULT ''",
            "container_group_version": "TEXT NOT NULL DEFAULT ''",
            "capture_mode": "TEXT NOT NULL DEFAULT 'packet'",
            "interval_milliseconds": "INTEGER NOT NULL DEFAULT 1000",
            "partial_interval": "INTEGER NOT NULL DEFAULT 0",
            "eth_rx_rate": "INTEGER NOT NULL DEFAULT 0",
            "eth_tx_rate": "INTEGER NOT NULL DEFAULT 0",
        }
        with self._db:
            for name, definition in sample_additions.items():
                if name not in sample_columns:
                    self._db.execute(f"ALTER TABLE samples ADD COLUMN {name} {definition}")
            if "eth_rx_rate" not in sample_columns:
                self._db.execute("UPDATE samples SET eth_rx_rate=eth_rx_bytes")
            if "eth_tx_rate" not in sample_columns:
                self._db.execute("UPDATE samples SET eth_tx_rate=eth_tx_bytes")
        minute_columns = {row[1] for row in self._db.execute("PRAGMA table_info(minute_rollups)").fetchall()}
        minute_additions = {
            "partial_interval_count": "INTEGER NOT NULL DEFAULT 0",
            "eth_rx_rate_sum": "INTEGER NOT NULL DEFAULT 0",
            "eth_tx_rate_sum": "INTEGER NOT NULL DEFAULT 0",
            "coverage_sum": "REAL NOT NULL DEFAULT 0",
            "first_sample_ms": "INTEGER NOT NULL DEFAULT 0",
            "last_sample_ms": "INTEGER NOT NULL DEFAULT 0",
            "peak_rate": "INTEGER NOT NULL DEFAULT 0",
            "peak_time_ms": "INTEGER NOT NULL DEFAULT 0",
        }
        with self._db:
            for name, definition in minute_additions.items():
                if name not in minute_columns:
                    self._db.execute(f"ALTER TABLE minute_rollups ADD COLUMN {name} {definition}")

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def ingest(self, log_entry: Dict[str, Any]) -> bool:
        payload = log_entry.get("json_log")
        # Older monitor images forward this native transition without emitting
        # a structured event. Preserve the actual event time and source labels.
        if log_entry.get("text_log") == "Honeygain service disconnected":
            return self._ingest_runtime_event(log_entry, {
                "kind": "honeygain_event", "schema_version": 1,
                "event": "disconnected", "time": log_entry.get("time"),
            })
        if not isinstance(payload, dict):
            return False
        kind = payload.get("kind")
        if kind in ("honeygain_event", "bandwidth_monitor_status"):
            return self._ingest_runtime_event(log_entry, payload)
        if kind != "bandwidth_sample":
            return False
        if payload.get("schema_version") != 1:
            return False
        labels = ((log_entry.get("resource") or {}).get("labels") or {})
        instance_id = str(labels.get("instance_id") or payload.get("instance_id") or "unknown")
        machine_id = str(labels.get("machine_id") or payload.get("machine_id") or "unknown")
        sample_time_ms = parse_time_ms(str(payload["sample_time"]))
        receive_time_ms = parse_time_ms(str(log_entry.get("receive_time") or log_entry.get("time") or payload["sample_time"]))
        sequence = int(payload.get("sequence", 0))
        eth0 = payload.get("eth0") or {}
        captured = payload.get("captured") or {}
        unassigned = payload.get("unassigned") or {}
        public_ip = str(payload.get("public_ip") or "")
        eth_rx_bytes = int(eth0.get("rx_bytes_delta", eth0.get("rx_bytes_per_second", 0)))
        eth_tx_bytes = int(eth0.get("tx_bytes_delta", eth0.get("tx_bytes_per_second", 0)))
        eth_rx_rate = int(eth0.get("rx_bytes_per_second", 0))
        eth_tx_rate = int(eth0.get("tx_bytes_per_second", 0))
        coverage_percent = float(payload.get("coverage_percent", 0.0))
        partial_interval = int(bool(payload.get("partial_interval")))
        row = (
            instance_id,
            sample_time_ms,
            sequence,
            receive_time_ms,
            machine_id,
            public_ip,
            str(payload.get("public_ip_status") or "unknown"),
            str(payload.get("interface") or "eth0"),
            int(bool(payload.get("counter_reset"))),
            int(eth0.get("rx_bytes_total", 0)),
            int(eth0.get("tx_bytes_total", 0)),
            eth_rx_bytes,
            eth_tx_bytes,
            eth_rx_rate,
            eth_tx_rate,
            int(captured.get("rx_bytes", 0)),
            int(captured.get("tx_bytes", 0)),
            int(unassigned.get("rx_bytes", 0)),
            int(unassigned.get("tx_bytes", 0)),
            coverage_percent,
            str(labels.get("organization_name") or ""),
            str(labels.get("project_name") or ""),
            str(labels.get("container_group_name") or ""),
            str(labels.get("container_group_version") or ""),
            str(payload.get("capture_mode") or "packet"),
            int(payload.get("interval_milliseconds") or 1000),
            partial_interval,
        )
        with self._lock, self._db:
            cursor = self._db.execute(
                """
                INSERT OR IGNORE INTO samples(
                    instance_id, sample_time_ms, sequence, receive_time_ms, machine_id,
                    public_ip, public_ip_status, interface, counter_reset, eth_rx_total,
                    eth_tx_total, eth_rx_bytes, eth_tx_bytes, eth_rx_rate, eth_tx_rate, captured_rx_bytes,
                    captured_tx_bytes, unassigned_rx_bytes, unassigned_tx_bytes,
                    coverage_percent, organization_name, project_name, container_group_name,
                    container_group_version, capture_mode, interval_milliseconds,
                    partial_interval
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                row,
            )
            if cursor.rowcount == 0:
                return False
            apps = payload.get("applications") or {}
            for app_name, app in apps.items():
                if app_name not in APP_NAMES or not isinstance(app, dict):
                    continue
                self._db.execute(
                    """
                    INSERT INTO app_samples(
                        instance_id, sample_time_ms, sequence, app_name, rx_bytes, tx_bytes,
                        process_count, socket_count, tcp_socket_count, tcp_established_count,
                        udp_socket_count, state
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        instance_id,
                        sample_time_ms,
                        sequence,
                        app_name,
                        int(app.get("attributed_packet_rx_bytes", 0)),
                        int(app.get("attributed_packet_tx_bytes", 0)),
                        int(app.get("process_count", 0)),
                        int(app.get("socket_count", 0)),
                        int(app.get("tcp_socket_count", 0)),
                        int(app.get("tcp_established_count", 0)),
                        int(app.get("udp_socket_count", 0)),
                        str(app.get("state") or "down"),
                    ),
                )
            self._db.execute(
                """
                INSERT INTO instance_segments(instance_id, machine_id, first_seen_ms, last_seen_ms, public_ip)
                VALUES (?,?,?,?,?)
                ON CONFLICT(instance_id) DO UPDATE SET
                    machine_id=excluded.machine_id,
                    first_seen_ms=min(first_seen_ms, excluded.first_seen_ms),
                    last_seen_ms=max(last_seen_ms, excluded.last_seen_ms),
                    public_ip=CASE WHEN excluded.public_ip <> '' THEN excluded.public_ip ELSE public_ip END
                """,
                (instance_id, machine_id, sample_time_ms, sample_time_ms, public_ip),
            )
            minute_ms = (sample_time_ms // MINUTE_MS) * MINUTE_MS
            peak_rate = eth_rx_rate + eth_tx_rate
            self._db.execute(
                """
                INSERT INTO minute_rollups(
                    minute_ms, instance_id, machine_id, sample_count, eth_rx_bytes, eth_tx_bytes,
                    captured_rx_bytes, captured_tx_bytes, unassigned_rx_bytes, unassigned_tx_bytes,
                    reset_count, partial_interval_count, eth_rx_rate_sum, eth_tx_rate_sum,
                    coverage_sum, first_sample_ms, last_sample_ms, peak_rate, peak_time_ms
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(minute_ms, instance_id) DO UPDATE SET
                    machine_id=excluded.machine_id,
                    sample_count=minute_rollups.sample_count + 1,
                    eth_rx_bytes=minute_rollups.eth_rx_bytes + excluded.eth_rx_bytes,
                    eth_tx_bytes=minute_rollups.eth_tx_bytes + excluded.eth_tx_bytes,
                    captured_rx_bytes=minute_rollups.captured_rx_bytes + excluded.captured_rx_bytes,
                    captured_tx_bytes=minute_rollups.captured_tx_bytes + excluded.captured_tx_bytes,
                    unassigned_rx_bytes=minute_rollups.unassigned_rx_bytes + excluded.unassigned_rx_bytes,
                    unassigned_tx_bytes=minute_rollups.unassigned_tx_bytes + excluded.unassigned_tx_bytes,
                    reset_count=minute_rollups.reset_count + excluded.reset_count,
                    partial_interval_count=minute_rollups.partial_interval_count + excluded.partial_interval_count,
                    eth_rx_rate_sum=minute_rollups.eth_rx_rate_sum + excluded.eth_rx_rate_sum,
                    eth_tx_rate_sum=minute_rollups.eth_tx_rate_sum + excluded.eth_tx_rate_sum,
                    coverage_sum=minute_rollups.coverage_sum + excluded.coverage_sum,
                    first_sample_ms=min(minute_rollups.first_sample_ms, excluded.first_sample_ms),
                    last_sample_ms=max(minute_rollups.last_sample_ms, excluded.last_sample_ms),
                    peak_time_ms=CASE
                        WHEN excluded.peak_rate > minute_rollups.peak_rate
                          OR (excluded.peak_rate = minute_rollups.peak_rate
                              AND excluded.peak_time_ms < minute_rollups.peak_time_ms)
                        THEN excluded.peak_time_ms ELSE minute_rollups.peak_time_ms END,
                    peak_rate=max(minute_rollups.peak_rate, excluded.peak_rate)
                WHERE minute_rollups.sample_count < (
                    SELECT count(*) FROM samples s
                    WHERE s.instance_id=excluded.instance_id
                      AND (s.sample_time_ms / 60000) * 60000=excluded.minute_ms
                )
                """,
                (
                    minute_ms,
                    instance_id,
                    machine_id,
                    1,
                    eth_rx_bytes,
                    eth_tx_bytes,
                    int(captured.get("rx_bytes", 0)),
                    int(captured.get("tx_bytes", 0)),
                    int(unassigned.get("rx_bytes", 0)),
                    int(unassigned.get("tx_bytes", 0)),
                    int(bool(payload.get("counter_reset"))),
                    partial_interval,
                    eth_rx_rate,
                    eth_tx_rate,
                    coverage_percent,
                    sample_time_ms,
                    sample_time_ms,
                    peak_rate,
                    sample_time_ms,
                ),
            )
            for app_name, app in apps.items():
                if app_name not in APP_NAMES or not isinstance(app, dict):
                    continue
                self._db.execute(
                    """
                    INSERT INTO minute_app_rollups(minute_ms, instance_id, app_name, rx_bytes, tx_bytes)
                    VALUES (?,?,?,?,?)
                    ON CONFLICT(minute_ms, instance_id, app_name) DO UPDATE SET
                        rx_bytes=minute_app_rollups.rx_bytes + excluded.rx_bytes,
                        tx_bytes=minute_app_rollups.tx_bytes + excluded.tx_bytes
                    WHERE (SELECT sample_count FROM minute_rollups m
                           WHERE m.minute_ms=excluded.minute_ms AND m.instance_id=excluded.instance_id) =
                          (SELECT count(*) FROM samples s
                           WHERE s.instance_id=excluded.instance_id
                             AND (s.sample_time_ms / 60000) * 60000=excluded.minute_ms)
                    """,
                    (
                        minute_ms,
                        instance_id,
                        app_name,
                        int(app.get("attributed_packet_rx_bytes", 0)),
                        int(app.get("attributed_packet_tx_bytes", 0)),
                    ),
                )
        return True

    def _ingest_runtime_event(self, log_entry: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        if payload.get("schema_version") != 1:
            return False
        kind = str(payload.get("kind") or "")
        event = str(payload.get("event") or "")
        if kind == "honeygain_event" and event not in HONEYGAIN_EVENTS:
            return False
        if kind == "bandwidth_monitor_status" and event not in ("start", "exit"):
            return False
        labels = ((log_entry.get("resource") or {}).get("labels") or {})
        event_time_ms = parse_time_ms(str(payload.get("time") or log_entry.get("time")))
        receive_time_ms = parse_time_ms(str(log_entry.get("receive_time") or log_entry.get("time") or payload.get("time")))
        row = (
            str(labels.get("instance_id") or "unknown"),
            event_time_ms,
            receive_time_ms,
            str(labels.get("machine_id") or "unknown"),
            str(labels.get("organization_name") or ""),
            str(labels.get("project_name") or ""),
            str(labels.get("container_group_name") or ""),
            str(labels.get("container_group_version") or ""),
            kind,
            event,
            str(payload.get("client_version") or ""),
            int(payload.get("attempt") or 0),
            int(payload.get("exit_code") or 0),
            str(payload.get("severity") or log_entry.get("severity") or "default"),
        )
        with self._lock, self._db:
            if kind == "honeygain_event" and event == "disconnected":
                # New monitors emit both the native line and a structured
                # transition. Prefer that transition over the legacy fallback.
                second_start = (event_time_ms // 1000) * 1000
                same_event = (row[0], second_start, second_start + 1000)
                if row[10]:
                    self._db.execute(
                        "DELETE FROM runtime_events WHERE instance_id=? AND event_time_ms>=? AND event_time_ms<? "
                        "AND kind='honeygain_event' AND event='disconnected' AND client_version=''",
                        same_event,
                    )
                elif self._db.execute(
                    "SELECT 1 FROM runtime_events WHERE instance_id=? AND event_time_ms>=? AND event_time_ms<? "
                    "AND kind='honeygain_event' AND event='disconnected' AND client_version!='' LIMIT 1",
                    same_event,
                ).fetchone():
                    return False
            cursor = self._db.execute(
                """
                INSERT OR IGNORE INTO runtime_events(
                    instance_id, event_time_ms, receive_time_ms, machine_id,
                    organization_name, project_name, container_group_name,
                    container_group_version, kind, event, client_version,
                    attempt, exit_code, severity
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                row,
            )
            return cursor.rowcount > 0

    def ingest_many(self, entries: Iterable[Dict[str, Any]]) -> int:
        return sum(1 for entry in entries if self.ingest(entry))

    def query_events(self, start_ms: int, end_ms: int, limit: int = 1000) -> Dict[str, Any]:
        if end_ms <= start_ms:
            raise ValueError("end must be after start")
        if limit < 1 or limit > 10_000:
            raise ValueError("limit must be between 1 and 10000")
        with self._lock:
            rows = self._db.execute(
                """
                SELECT instance_id, event_time_ms, receive_time_ms, machine_id,
                       organization_name, project_name, container_group_name,
                       container_group_version, kind, event, client_version,
                       attempt, exit_code, severity
                FROM runtime_events
                WHERE event_time_ms >= ? AND event_time_ms < ?
                ORDER BY event_time_ms DESC, instance_id DESC
                LIMIT ?
                """,
                (start_ms, end_ms, limit),
            ).fetchall()
        events = [dict(row) for row in rows]
        counts: Dict[str, int] = {}
        for event in events:
            counts[event["event"]] = counts.get(event["event"], 0) + 1
        return {
            "schema_version": 1,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "event_count": len(events),
            "counts": counts,
            "events": events,
        }

    def watermark_ms(self) -> Optional[int]:
        with self._lock:
            row = self._db.execute("SELECT watermark_ms FROM ingest_state WHERE singleton=1").fetchone()
        return row[0] if row and row[0] is not None else None

    def record_poll(self, watermark_ms: int, new_samples: int, error: str = "", now_ms: Optional[int] = None) -> None:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        success = None if error else now_ms
        safe_error = error[:500]
        with self._lock, self._db:
            self._db.execute(
                """
                UPDATE ingest_state SET watermark_ms=?, last_poll_ms=?,
                    last_success_ms=coalesce(?, last_success_ms), last_new_samples=?, last_error=?
                WHERE singleton=1
                """,
                (watermark_ms, now_ms, success, new_samples, safe_error),
            )

    def rollup(self, before_ms: Optional[int] = None) -> int:
        if before_ms is None:
            before_ms = (int(time.time() * 1000) // MINUTE_MS) * MINUTE_MS
        with self._lock, self._db:
            count = int(self._db.execute("SELECT count(*) FROM samples WHERE sample_time_ms < ?", (before_ms,)).fetchone()[0])
            self._db.execute(
                """
                INSERT INTO minute_rollups
                    (minute_ms, instance_id, machine_id, sample_count, eth_rx_bytes, eth_tx_bytes,
                     captured_rx_bytes, captured_tx_bytes, unassigned_rx_bytes, unassigned_tx_bytes,
                     reset_count, partial_interval_count, eth_rx_rate_sum, eth_tx_rate_sum,
                     coverage_sum, first_sample_ms, last_sample_ms, peak_rate, peak_time_ms)
                WITH ranked AS (
                    SELECT *, (sample_time_ms / 60000) * 60000 AS minute_ms,
                           row_number() OVER (
                               PARTITION BY (sample_time_ms / 60000), instance_id
                               ORDER BY (eth_rx_rate + eth_tx_rate) DESC,
                                        sample_time_ms ASC, sequence ASC
                           ) AS peak_rank
                    FROM samples WHERE sample_time_ms < ?
                )
                SELECT minute_ms, instance_id, max(machine_id), count(*),
                       sum(eth_rx_bytes), sum(eth_tx_bytes), sum(captured_rx_bytes), sum(captured_tx_bytes),
                       sum(unassigned_rx_bytes), sum(unassigned_tx_bytes), sum(counter_reset), sum(partial_interval),
                       sum(eth_rx_rate), sum(eth_tx_rate), sum(coverage_percent),
                       min(sample_time_ms), max(sample_time_ms),
                       max(CASE WHEN peak_rank = 1 THEN eth_rx_rate + eth_tx_rate END),
                       max(CASE WHEN peak_rank = 1 THEN sample_time_ms END)
                FROM ranked
                GROUP BY minute_ms, instance_id
                ON CONFLICT(minute_ms, instance_id) DO UPDATE SET
                    machine_id=excluded.machine_id, sample_count=excluded.sample_count,
                    eth_rx_bytes=excluded.eth_rx_bytes, eth_tx_bytes=excluded.eth_tx_bytes,
                    captured_rx_bytes=excluded.captured_rx_bytes, captured_tx_bytes=excluded.captured_tx_bytes,
                    unassigned_rx_bytes=excluded.unassigned_rx_bytes, unassigned_tx_bytes=excluded.unassigned_tx_bytes,
                    reset_count=excluded.reset_count, partial_interval_count=excluded.partial_interval_count,
                    eth_rx_rate_sum=excluded.eth_rx_rate_sum, eth_tx_rate_sum=excluded.eth_tx_rate_sum,
                    coverage_sum=excluded.coverage_sum, first_sample_ms=excluded.first_sample_ms,
                    last_sample_ms=excluded.last_sample_ms, peak_rate=excluded.peak_rate,
                    peak_time_ms=excluded.peak_time_ms
                WHERE excluded.sample_count >= minute_rollups.sample_count
                """,
                (before_ms,),
            )
            self._db.execute(
                """
                INSERT INTO minute_app_rollups(minute_ms, instance_id, app_name, rx_bytes, tx_bytes)
                SELECT (sample_time_ms / 60000) * 60000, instance_id, app_name, sum(rx_bytes), sum(tx_bytes)
                FROM app_samples WHERE sample_time_ms < ?
                GROUP BY (sample_time_ms / 60000), instance_id, app_name
                ON CONFLICT(minute_ms, instance_id, app_name) DO UPDATE SET
                    rx_bytes=excluded.rx_bytes, tx_bytes=excluded.tx_bytes
                WHERE (SELECT sample_count FROM minute_rollups m
                       WHERE m.minute_ms=excluded.minute_ms AND m.instance_id=excluded.instance_id) =
                      (SELECT count(*) FROM samples s
                       WHERE s.instance_id=excluded.instance_id
                         AND (s.sample_time_ms / 60000) * 60000=excluded.minute_ms)
                """,
                (before_ms,),
            )
        return count

    def prune(self, now_ms: Optional[int] = None) -> int:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        cutoff = now_ms - self.raw_retention_days * 86400 * 1000
        self.rollup(before_ms=cutoff)
        with self._lock, self._db:
            cursor = self._db.execute("DELETE FROM samples WHERE sample_time_ms < ?", (cutoff,))
            return max(0, cursor.rowcount)

    def _raw_rows(self, start_ms: int, end_ms: int) -> List[sqlite3.Row]:
        return self._db.execute(
            """
            SELECT * FROM samples WHERE sample_time_ms >= ? AND sample_time_ms < ?
            ORDER BY sample_time_ms, sequence
            """,
            (start_ms, end_ms),
        ).fetchall()

    def _box_stats(self, start_ms: int, end_ms: int, instance_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Aggregate exact per-instance metrics from minute summaries plus uncovered raw edges."""
        rollup_start = ((start_ms + MINUTE_MS - 1) // MINUTE_MS) * MINUTE_MS
        rollup_end = (end_ms // MINUTE_MS) * MINUTE_MS
        stats: Dict[str, Dict[str, Any]] = {}

        def add(
            name: str,
            sample_count: int,
            partial_count: int,
            rx_bytes: int,
            tx_bytes: int,
            rx_rate_sum: int,
            tx_rate_sum: int,
            coverage_sum: float,
            first_ms: int,
            last_ms: int,
            peak_rate: int,
            peak_time_ms: int,
        ) -> None:
            value = stats.setdefault(
                name,
                {
                    "sample_count": 0,
                    "partial_count": 0,
                    "rx_bytes": 0,
                    "tx_bytes": 0,
                    "rx_rate_sum": 0,
                    "tx_rate_sum": 0,
                    "coverage_sum": 0.0,
                    "first_ms": None,
                    "last_ms": None,
                    "peak_rate": 0,
                    "peak_time_ms": None,
                },
            )
            value["sample_count"] += int(sample_count)
            value["partial_count"] += int(partial_count)
            value["rx_bytes"] += int(rx_bytes)
            value["tx_bytes"] += int(tx_bytes)
            value["rx_rate_sum"] += int(rx_rate_sum)
            value["tx_rate_sum"] += int(tx_rate_sum)
            value["coverage_sum"] += float(coverage_sum)
            value["first_ms"] = first_ms if value["first_ms"] is None else min(value["first_ms"], first_ms)
            value["last_ms"] = last_ms if value["last_ms"] is None else max(value["last_ms"], last_ms)
            if peak_rate > value["peak_rate"] or (
                peak_rate == value["peak_rate"]
                and (value["peak_time_ms"] is None or peak_time_ms < value["peak_time_ms"])
            ):
                value["peak_rate"] = int(peak_rate)
                value["peak_time_ms"] = int(peak_time_ms)

        rollup_sql = """
            SELECT instance_id, sample_count, partial_interval_count, eth_rx_bytes, eth_tx_bytes,
                   eth_rx_rate_sum, eth_tx_rate_sum, coverage_sum, first_sample_ms, last_sample_ms,
                   peak_rate, peak_time_ms
            FROM minute_rollups
            WHERE minute_ms >= ? AND minute_ms < ?
        """
        rollup_params: List[Any] = [rollup_start, rollup_end]
        if instance_id is not None:
            rollup_sql += " AND instance_id=?"
            rollup_params.append(instance_id)
        for row in self._db.execute(rollup_sql, rollup_params).fetchall():
            add(
                row["instance_id"], row["sample_count"], row["partial_interval_count"],
                row["eth_rx_bytes"], row["eth_tx_bytes"], row["eth_rx_rate_sum"],
                row["eth_tx_rate_sum"], row["coverage_sum"], row["first_sample_ms"],
                row["last_sample_ms"], row["peak_rate"], row["peak_time_ms"],
            )

        raw_sql = """
            SELECT s.instance_id, s.sample_time_ms, s.sequence, s.partial_interval,
                   s.eth_rx_bytes, s.eth_tx_bytes, s.eth_rx_rate, s.eth_tx_rate,
                   s.coverage_percent
            FROM samples s
            WHERE s.sample_time_ms >= ? AND s.sample_time_ms < ?
              AND NOT EXISTS (
                  SELECT 1 FROM minute_rollups m
                  WHERE m.instance_id=s.instance_id
                    AND m.minute_ms=(s.sample_time_ms / 60000) * 60000
                    AND m.minute_ms >= ? AND m.minute_ms < ?
              )
        """
        raw_params: List[Any] = [start_ms, end_ms, rollup_start, rollup_end]
        if instance_id is not None:
            raw_sql += " AND s.instance_id=?"
            raw_params.append(instance_id)
        for row in self._db.execute(raw_sql, raw_params).fetchall():
            rate = int(row["eth_rx_rate"]) + int(row["eth_tx_rate"])
            add(
                row["instance_id"], 1, row["partial_interval"], row["eth_rx_bytes"],
                row["eth_tx_bytes"], row["eth_rx_rate"], row["eth_tx_rate"],
                row["coverage_percent"], row["sample_time_ms"], row["sample_time_ms"],
                rate, row["sample_time_ms"],
            )
        return stats

    def _box_app_totals(self, start_ms: int, end_ms: int) -> Dict[str, Tuple[int, int]]:
        rollup_start = ((start_ms + MINUTE_MS - 1) // MINUTE_MS) * MINUTE_MS
        rollup_end = (end_ms // MINUTE_MS) * MINUTE_MS
        totals: Dict[str, List[int]] = {}
        for row in self._db.execute(
            """
            SELECT instance_id, sum(rx_bytes) AS rx_bytes, sum(tx_bytes) AS tx_bytes
            FROM minute_app_rollups
            WHERE app_name='honeygain' AND minute_ms >= ? AND minute_ms < ?
            GROUP BY instance_id
            """,
            (rollup_start, rollup_end),
        ).fetchall():
            totals[row["instance_id"]] = [int(row["rx_bytes"] or 0), int(row["tx_bytes"] or 0)]
        for row in self._db.execute(
            """
            SELECT a.instance_id, sum(a.rx_bytes) AS rx_bytes, sum(a.tx_bytes) AS tx_bytes
            FROM app_samples a
            WHERE a.app_name='honeygain' AND a.sample_time_ms >= ? AND a.sample_time_ms < ?
              AND NOT EXISTS (
                  SELECT 1 FROM minute_rollups m
                  WHERE m.instance_id=a.instance_id
                    AND m.minute_ms=(a.sample_time_ms / 60000) * 60000
                    AND m.minute_ms >= ? AND m.minute_ms < ?
              )
            GROUP BY a.instance_id
            """,
            (start_ms, end_ms, rollup_start, rollup_end),
        ).fetchall():
            total = totals.setdefault(row["instance_id"], [0, 0])
            total[0] += int(row["rx_bytes"] or 0)
            total[1] += int(row["tx_bytes"] or 0)
        return {name: (value[0], value[1]) for name, value in totals.items()}

    def query_boxes(self, start_ms: int, end_ms: int, expected_reporters: int = 10) -> Dict[str, Any]:
        if end_ms <= start_ms:
            raise ValueError("end must be after start")
        with self._lock:
            # A snapshot older than the live threshold cannot contribute to
            # current fleet values, so keep this exact-second search bounded.
            snapshot_start_ms = max(start_ms, end_ms - 60_000)
            fleet = self._db.execute(
                """
                SELECT (sample_time_ms / 1000) * 1000 AS sample_time_ms,
                       count(DISTINCT instance_id) AS reporters
                FROM samples
                WHERE sample_time_ms >= ? AND sample_time_ms < ?
                GROUP BY (sample_time_ms / 1000)
                HAVING count(DISTINCT instance_id) >= ?
                ORDER BY sample_time_ms DESC LIMIT 1
                """,
                (snapshot_start_ms, end_ms, expected_reporters),
            ).fetchone()
            if fleet is None:
                fleet = self._db.execute(
                    """
                    SELECT (sample_time_ms / 1000) * 1000 AS sample_time_ms,
                           count(DISTINCT instance_id) AS reporters
                    FROM samples
                    WHERE (sample_time_ms / 1000) = (
                        SELECT max(sample_time_ms / 1000) FROM samples
                        WHERE sample_time_ms >= ? AND sample_time_ms < ?
                    )
                    GROUP BY (sample_time_ms / 1000)
                    """,
                    (snapshot_start_ms, end_ms),
                ).fetchone()
            fleet_snapshot_ms = fleet["sample_time_ms"] if fleet else None
            snapshot_rows: Dict[str, sqlite3.Row] = {}
            if fleet_snapshot_ms is not None:
                for snapshot in self._db.execute(
                    """
                    SELECT instance_id, eth_rx_rate AS eth_rx_bytes, eth_tx_rate AS eth_tx_bytes, sequence
                    FROM samples WHERE sample_time_ms>=? AND sample_time_ms<?
                    ORDER BY instance_id, sample_time_ms DESC, sequence DESC
                    """,
                    (fleet_snapshot_ms, fleet_snapshot_ms + 1000),
                ).fetchall():
                    snapshot_rows.setdefault(snapshot["instance_id"], snapshot)

            selected_stats = self._box_stats(start_ms, end_ms)
            app_totals = self._box_app_totals(start_ms, end_ms)
            boxes = []
            for instance_id, stats in sorted(
                selected_stats.items(), key=lambda item: (-int(item[1]["last_ms"]), item[0])
            ):
                latest = self._db.execute(
                    """
                    SELECT s.*, seg.first_seen_ms AS segment_first_seen_ms,
                           coalesce(nullif(s.public_ip, ''), seg.public_ip, '') AS effective_public_ip,
                           a.rx_bytes AS honeygain_rx_bytes, a.tx_bytes AS honeygain_tx_bytes,
                           a.process_count AS honeygain_process_count,
                           a.socket_count AS honeygain_socket_count,
                           a.tcp_socket_count AS honeygain_tcp_socket_count,
                           a.tcp_established_count AS honeygain_tcp_established_count,
                           a.udp_socket_count AS honeygain_udp_socket_count,
                           a.state AS honeygain_state
                    FROM samples s
                    LEFT JOIN instance_segments seg ON seg.instance_id=s.instance_id
                    LEFT JOIN app_samples a
                      ON a.instance_id=s.instance_id AND a.sample_time_ms=s.sample_time_ms
                     AND a.sequence=s.sequence AND a.app_name='honeygain'
                    WHERE s.instance_id=? AND s.sample_time_ms>=? AND s.sample_time_ms<?
                    ORDER BY s.sample_time_ms DESC, s.sequence DESC LIMIT 1
                    """,
                    (instance_id, start_ms, end_ms),
                ).fetchone()
                segment = self._db.execute(
                    "SELECT machine_id, first_seen_ms, public_ip FROM instance_segments WHERE instance_id=?",
                    (instance_id,),
                ).fetchone()
                first_seen_ms = int(segment["first_seen_ms"] if segment else stats["first_ms"])
                profile_end_ms = int(stats["last_ms"])
                first_profile = self._box_stats(first_seen_ms, first_seen_ms + 300_000, instance_id).get(instance_id)
                last_profile = self._box_stats(max(0, profile_end_ms - 300_000), profile_end_ms + 1, instance_id).get(instance_id)

                def average_rate(value: Optional[Dict[str, Any]]) -> float:
                    if not value or not value["sample_count"]:
                        return 0.0
                    return float(value["rx_rate_sum"] + value["tx_rate_sum"]) / value["sample_count"]

                first_average = average_rate(first_profile)
                last_average = average_rate(last_profile)
                sample_count = int(stats["sample_count"])
                average_rx = float(stats["rx_rate_sum"]) / sample_count
                average_tx = float(stats["tx_rate_sum"]) / sample_count
                latest_rx = int(latest["eth_rx_rate"] if latest else 0)
                latest_tx = int(latest["eth_tx_rate"] if latest else 0)
                app_rx, app_tx = app_totals.get(instance_id, (0, 0))
                snapshot = snapshot_rows.get(instance_id)
                snapshot_value = None
                if snapshot:
                    snapshot_rx = int(snapshot["eth_rx_bytes"] or 0)
                    snapshot_tx = int(snapshot["eth_tx_bytes"] or 0)
                    snapshot_value = {
                        "time_ms": fleet_snapshot_ms,
                        "rx_bytes_per_second": snapshot_rx,
                        "tx_bytes_per_second": snapshot_tx,
                        "bytes_per_second": snapshot_rx + snapshot_tx,
                    }
                expected = max(1, (int(stats["last_ms"]) - int(stats["first_ms"])) // 1000 + 1)
                box = {
                    "instance_id": instance_id,
                    "machine_id": latest["machine_id"] if latest else (segment["machine_id"] if segment else "unknown"),
                    "public_ip": latest["effective_public_ip"] if latest else (segment["public_ip"] if segment else ""),
                    "public_ip_status": latest["public_ip_status"] if latest else "unknown",
                    "capture_mode": latest["capture_mode"] if latest else "unknown",
                    "source": {
                        "organization": latest["organization_name"] if latest else "",
                        "project": latest["project_name"] if latest else "",
                        "container_group": latest["container_group_name"] if latest else "",
                        "version": latest["container_group_version"] if latest else "",
                    },
                    "first_seen_ms": first_seen_ms,
                    "first_sample_ms": int(stats["first_ms"]),
                    "last_sample_ms": int(stats["last_ms"]),
                    "sample_count": sample_count,
                    "partial_interval_count": int(stats["partial_count"]),
                    "expected_sample_count": expected,
                    "missing_sample_count": max(0, expected - sample_count),
                    "completeness_percent": min(100.0, 100.0 * sample_count / expected),
                    "is_live": snapshot_value is not None and end_ms - fleet_snapshot_ms <= LIVE_SAMPLE_GRACE_MS,
                    "snapshot": snapshot_value,
                    "totals": {"rx_bytes": int(stats["rx_bytes"]), "tx_bytes": int(stats["tx_bytes"])},
                    "observed_average": {
                        "rx_bytes_per_second": average_rx,
                        "tx_bytes_per_second": average_tx,
                        "bytes_per_second": average_rx + average_tx,
                    },
                    "peak": {"bytes_per_second": int(stats["peak_rate"]), "time_ms": stats["peak_time_ms"]},
                    "latest": {
                        "rx_bytes_per_second": latest_rx,
                        "tx_bytes_per_second": latest_tx,
                        "bytes_per_second": latest_rx + latest_tx,
                    },
                    "first_5m_average_bytes_per_second": first_average,
                    "last_5m_average_bytes_per_second": last_average,
                    "slowdown_ratio": (last_average / first_average) if first_average > 0 else None,
                    "average_coverage_percent": float(stats["coverage_sum"]) / sample_count,
                    "honeygain": {
                        "state": latest["honeygain_state"] if latest and latest["honeygain_state"] else "unknown",
                        "process_count": int(latest["honeygain_process_count"] or 0) if latest else 0,
                        "socket_count": int(latest["honeygain_socket_count"] or 0) if latest else 0,
                        "tcp_socket_count": int(latest["honeygain_tcp_socket_count"] or 0) if latest else 0,
                        "tcp_established_count": int(latest["honeygain_tcp_established_count"] or 0) if latest else 0,
                        "udp_socket_count": int(latest["honeygain_udp_socket_count"] or 0) if latest else 0,
                        "rx_bytes": app_rx,
                        "tx_bytes": app_tx,
                    },
                }
                box.update(
                    {
                        "last_ms": box["last_sample_ms"], "samples": box["sample_count"],
                        "rx_bytes": box["totals"]["rx_bytes"], "tx_bytes": box["totals"]["tx_bytes"],
                        "now_rx": box["latest"]["rx_bytes_per_second"],
                        "now_tx": box["latest"]["tx_bytes_per_second"],
                        "honeygain_rx": box["honeygain"]["rx_bytes"],
                        "honeygain_tx": box["honeygain"]["tx_bytes"],
                        "honeygain_sockets": box["honeygain"]["socket_count"],
                        "honeygain_state": box["honeygain"]["state"],
                    }
                )
                boxes.append(box)
        return {
            "schema_version": 2,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "expected_reporter_count": expected_reporters,
            "fleet_snapshot_ms": fleet_snapshot_ms,
            "snapshot_reporter_count": len(snapshot_rows),
            "reporter_count": len(snapshot_rows),
            "boxes": boxes,
        }

    def query_range(self, start_ms: int, end_ms: int, bucket_seconds: int) -> Dict[str, Any]:
        if end_ms <= start_ms:
            raise ValueError("end must be after start")
        if bucket_seconds < 1 or bucket_seconds > 86400:
            raise ValueError("bucket must be between 1 and 86400 seconds")
        bucket_ms = bucket_seconds * 1000
        with self._lock:
            use_rollups = bucket_seconds >= 60 and start_ms % MINUTE_MS == 0 and bucket_ms % MINUTE_MS == 0
            rollup_start = ((start_ms + MINUTE_MS - 1) // MINUTE_MS) * MINUTE_MS if use_rollups else end_ms + MINUTE_MS
            rollups = []
            if use_rollups:
                rollups = self._db.execute(
                    """
                    SELECT * FROM minute_rollups
                    WHERE minute_ms >= ? AND minute_ms + 60000 <= ? ORDER BY minute_ms
                    """,
                    (rollup_start, end_ms),
                ).fetchall()
            raw_rows = self._db.execute(
                """
                SELECT s.* FROM samples s
                WHERE s.sample_time_ms >= ? AND s.sample_time_ms < ?
                  AND NOT EXISTS (
                      SELECT 1 FROM minute_rollups m
                      WHERE m.instance_id=s.instance_id
                        AND m.minute_ms=(s.sample_time_ms / 60000) * 60000
                        AND m.minute_ms >= ? AND m.minute_ms + 60000 <= ?
                  )
                ORDER BY s.sample_time_ms, s.sequence
                """,
                (
                    start_ms,
                    end_ms,
                    rollup_start,
                    end_ms,
                ),
            ).fetchall()
            raw_apps = self._db.execute(
                """
                SELECT a.instance_id, a.sample_time_ms, a.sequence, a.app_name, a.rx_bytes, a.tx_bytes
                FROM app_samples a
                WHERE a.sample_time_ms >= ? AND a.sample_time_ms < ?
                  AND NOT EXISTS (
                      SELECT 1 FROM minute_rollups m
                      WHERE m.instance_id=a.instance_id
                        AND m.minute_ms=(a.sample_time_ms / 60000) * 60000
                        AND m.minute_ms >= ? AND m.minute_ms + 60000 <= ?
                  )
                """,
                (
                    start_ms,
                    end_ms,
                    rollup_start,
                    end_ms,
                ),
            ).fetchall()
            rollup_apps = []
            if rollups:
                rollup_apps = self._db.execute(
                    """
                    SELECT * FROM minute_app_rollups
                    WHERE minute_ms >= ? AND minute_ms + 60000 <= ?
                    """,
                    (rollup_start, end_ms),
                ).fetchall()
            segments = self._db.execute(
                """
                SELECT instance_id, machine_id, first_seen_ms, last_seen_ms, public_ip
                FROM instance_segments WHERE last_seen_ms >= ? AND first_seen_ms < ? ORDER BY first_seen_ms
                """,
                (start_ms, end_ms),
            ).fetchall()
            latest = self._db.execute(
                """
                SELECT instance_id, sample_time_ms, sequence FROM samples
                WHERE sample_time_ms >= ? AND sample_time_ms < ?
                ORDER BY sample_time_ms DESC, sequence DESC LIMIT 1
                """,
                (start_ms, end_ms),
            ).fetchone()
            latest_apps = []
            if latest:
                latest_apps = self._db.execute(
                    """
                    SELECT app_name, process_count, socket_count, state FROM app_samples
                    WHERE instance_id=? AND sample_time_ms=? AND sequence=? ORDER BY app_name
                    """,
                    (latest["instance_id"], latest["sample_time_ms"], latest["sequence"]),
                ).fetchall()

        raw_app_map: Dict[Tuple[str, int, int], Dict[str, Tuple[int, int]]] = {}
        for row in raw_apps:
            minute_key = ((row["sample_time_ms"] // MINUTE_MS) * MINUTE_MS, row["instance_id"])
            key = (row["instance_id"], row["sample_time_ms"], row["sequence"])
            raw_app_map.setdefault(key, {})[row["app_name"]] = (row["rx_bytes"], row["tx_bytes"])
        rollup_app_map: Dict[Tuple[int, str], Dict[str, Tuple[int, int]]] = {}
        for row in rollup_apps:
            rollup_app_map.setdefault((row["minute_ms"], row["instance_id"]), {})[row["app_name"]] = (
                row["rx_bytes"], row["tx_bytes"]
            )

        buckets: Dict[int, Dict[str, Any]] = {}

        def add_event(timestamp_ms: int, instance_id: str, values: Dict[str, int], apps: Dict[str, Tuple[int, int]]) -> None:
            bucket = start_ms + ((timestamp_ms - start_ms) // bucket_ms) * bucket_ms
            point = buckets.setdefault(
                bucket,
                {
                    "time_ms": bucket,
                    "sample_count": 0,
                    "eth_rx": 0,
                    "eth_tx": 0,
                    "captured_rx": 0,
                    "captured_tx": 0,
                    "unassigned_rx": 0,
                    "unassigned_tx": 0,
                    "reset_count": 0,
                    "partial_count": 0,
                    "instances": set(),
                    "apps": {name: [0, 0] for name in APP_NAMES},
                },
            )
            point["sample_count"] += values["sample_count"]
            for field in ("eth_rx", "eth_tx", "captured_rx", "captured_tx", "unassigned_rx", "unassigned_tx", "reset_count", "partial_count"):
                point[field] += values[field]
            point["instances"].add(instance_id)
            for name, (rx, tx) in apps.items():
                if name in point["apps"]:
                    point["apps"][name][0] += rx
                    point["apps"][name][1] += tx

        for row in rollups:
            add_event(
                row["minute_ms"],
                row["instance_id"],
                {
                    "sample_count": row["sample_count"],
                    "eth_rx": row["eth_rx_bytes"],
                    "eth_tx": row["eth_tx_bytes"],
                    "captured_rx": row["captured_rx_bytes"],
                    "captured_tx": row["captured_tx_bytes"],
                    "unassigned_rx": row["unassigned_rx_bytes"],
                    "unassigned_tx": row["unassigned_tx_bytes"],
                    "reset_count": row["reset_count"],
                    "partial_count": row["partial_interval_count"],
                },
                rollup_app_map.get((row["minute_ms"], row["instance_id"]), {}),
            )
        for row in raw_rows:
            add_event(
                row["sample_time_ms"],
                row["instance_id"],
                {
                    "sample_count": 1,
                    "eth_rx": row["eth_rx_bytes"],
                    "eth_tx": row["eth_tx_bytes"],
                    "captured_rx": row["captured_rx_bytes"],
                    "captured_tx": row["captured_tx_bytes"],
                    "unassigned_rx": row["unassigned_rx_bytes"],
                    "unassigned_tx": row["unassigned_tx_bytes"],
                    "reset_count": row["counter_reset"],
                    "partial_count": row["partial_interval"],
                },
                raw_app_map.get((row["instance_id"], row["sample_time_ms"], row["sequence"]), {}),
            )

        totals = {
            "eth0": {"rx_bytes": 0, "tx_bytes": 0},
            "captured": {"rx_bytes": 0, "tx_bytes": 0},
            "unassigned": {"rx_bytes": 0, "tx_bytes": 0},
            "applications": {name: {"rx_bytes": 0, "tx_bytes": 0} for name in APP_NAMES},
        }
        points = []
        for bucket in sorted(buckets):
            value = buckets[bucket]
            captured_total = value["captured_rx"] + value["captured_tx"]
            unassigned_total = value["unassigned_rx"] + value["unassigned_tx"]
            coverage = 0.0 if captured_total == 0 else max(0.0, 100.0 * (captured_total - min(captured_total, unassigned_total)) / captured_total)
            applications = {}
            for name in APP_NAMES:
                rx, tx = value["apps"][name]
                applications[name] = {
                    "rx_bytes": rx,
                    "tx_bytes": tx,
                    "rx_bytes_per_second": rx / bucket_seconds,
                    "tx_bytes_per_second": tx / bucket_seconds,
                }
                totals["applications"][name]["rx_bytes"] += rx
                totals["applications"][name]["tx_bytes"] += tx
            points.append(
                {
                    "time_ms": bucket,
                    "sample_count": value["sample_count"],
                    "instance_ids": sorted(value["instances"]),
                    "counter_resets": value["reset_count"],
                    "partial_intervals": value["partial_count"],
                    "coverage_percent": coverage,
                    "eth0": {
                        "rx_bytes": value["eth_rx"],
                        "tx_bytes": value["eth_tx"],
                        "rx_bytes_per_second": value["eth_rx"] / bucket_seconds,
                        "tx_bytes_per_second": value["eth_tx"] / bucket_seconds,
                    },
                    "captured": {
                        "rx_bytes": value["captured_rx"],
                        "tx_bytes": value["captured_tx"],
                        "rx_bytes_per_second": value["captured_rx"] / bucket_seconds,
                        "tx_bytes_per_second": value["captured_tx"] / bucket_seconds,
                    },
                    "unassigned": {
                        "rx_bytes": value["unassigned_rx"],
                        "tx_bytes": value["unassigned_tx"],
                        "rx_bytes_per_second": value["unassigned_rx"] / bucket_seconds,
                        "tx_bytes_per_second": value["unassigned_tx"] / bucket_seconds,
                    },
                    "applications": applications,
                }
            )
            totals["eth0"]["rx_bytes"] += value["eth_rx"]
            totals["eth0"]["tx_bytes"] += value["eth_tx"]
            totals["captured"]["rx_bytes"] += value["captured_rx"]
            totals["captured"]["tx_bytes"] += value["captured_tx"]
            totals["unassigned"]["rx_bytes"] += value["unassigned_rx"]
            totals["unassigned"]["tx_bytes"] += value["unassigned_tx"]

        return {
            "schema_version": 1,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "bucket_seconds": bucket_seconds,
            "points": points,
            "totals": totals,
            "latest_apps": {r["app_name"]: {"process_count": r["process_count"], "socket_count": r["socket_count"], "state": r["state"]} for r in latest_apps},
            "reallocations": [dict(row) for row in segments],
        }

    def status(self) -> Dict[str, Any]:
        with self._lock:
            aggregate = self._db.execute(
                "SELECT count(*) AS count, min(sample_time_ms) AS first_ms, max(sample_time_ms) AS last_ms FROM samples"
            ).fetchone()
            latest = self._db.execute(
                """
                SELECT instance_id, machine_id, sample_time_ms, receive_time_ms, coverage_percent,
                       eth_rx_rate, eth_tx_rate, public_ip_status, organization_name,
                       project_name, container_group_name, container_group_version,
                       capture_mode, interval_milliseconds, partial_interval
                FROM samples ORDER BY sample_time_ms DESC, sequence DESC LIMIT 1
                """
            ).fetchone()
            state = self._db.execute("SELECT * FROM ingest_state WHERE singleton=1").fetchone()
            segment_count = self._db.execute("SELECT count(*) FROM instance_segments").fetchone()[0]
        result: Dict[str, Any] = {
            "sample_count": int(aggregate["count"]),
            "first_sample_ms": aggregate["first_ms"],
            "last_sample_ms": aggregate["last_ms"],
            "segment_count": int(segment_count),
            "database_path": str(self.path),
            "database_size_bytes": self.path.stat().st_size if self.path.exists() else 0,
            "watermark_ms": state["watermark_ms"],
            "last_poll_ms": state["last_poll_ms"],
            "last_success_ms": state["last_success_ms"],
            "last_new_samples": state["last_new_samples"],
            "last_error": state["last_error"],
        }
        if latest:
            result.update(
                {
                    "latest_instance_id": latest["instance_id"],
                    "latest_machine_id": latest["machine_id"],
                    "latest_receive_time_ms": latest["receive_time_ms"],
                    "latest_coverage_percent": latest["coverage_percent"],
                    "latest_rx_bytes_per_second": latest["eth_rx_rate"],
                    "latest_tx_bytes_per_second": latest["eth_tx_rate"],
                    "public_ip_status": latest["public_ip_status"],
                    "capture_mode": latest["capture_mode"],
                    "latest_interval_milliseconds": latest["interval_milliseconds"],
                    "latest_partial_interval": bool(latest["partial_interval"]),
                    "source": {
                        "organization": latest["organization_name"],
                        "project": latest["project_name"],
                        "container_group": latest["container_group_name"],
                        "version": latest["container_group_version"],
                    },
                }
            )
        return result


def compact_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)
~~~~~~

### dashboard/tests/__init__.py

<!-- rebuild-file: dashboard/tests/__init__.py sha256=01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b -->
~~~~~~python

~~~~~~

### dashboard/tests/test_fleet_test.py

<!-- rebuild-file: dashboard/tests/test_fleet_test.py sha256=908709935eb4ee437689fe31061564636a0acb90f5662185bf236f5dc92afbc6 -->
~~~~~~python
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from dashboard.fleet_test import FleetTestView, rate_buckets, rate_timeline, timestamp_ms, honeygain_minutes


START = 1_800_000_000_000
MACHINE = "11111111-1111-1111-1111-111111111111"
INSTANCE = "22222222-2222-2222-2222-222222222222"
REPLACEMENT = "33333333-3333-3333-3333-333333333333"


def observation(seconds, paid_mb, network_mb=None, *, experiment="test-one", complete=True):
    return {
        "experiment_id": experiment, "time_ms": START + seconds * 1000,
        "ps": {"provider_bytes": paid_mb * 1_000_000,
               "provider_observed_ms": START + seconds * 1000,
               "network_total_bytes": (network_mb if network_mb is not None else paid_mb * 2) * 1_000_000,
               "network_observed_ms": START + seconds * 1000,
               "network_complete": complete, "running": 10, "reporting": 10,
               "workers": [{"machine": "ps-worker", "client_status": "unknown", "state": "running"}]},
        "hg": {"provider_gathering_credits": seconds / 60,
               "provider_observed_ms": START + seconds * 1000,
               "workers": [{"device": "hg-01", "state": "running", "client_status": "unknown"}]},
    }


class FleetTestRates(unittest.TestCase):
    def test_honeygain_minute_estimates_preserve_interval_bytes_and_identity(self):
        rows=[]
        for seconds,total in [(20,100_000_000),(140,220_000_000)]:
            rows.append({"time_ms":START+seconds*1000,"hg":{"status_observed_ms":START+seconds*1000,
                "workers":[{"group":"hg1","machine":MACHINE,"ip":"192.0.2.1","network_bytes":total,"received_age_ms":0}]}})
        bars=honeygain_minutes(rows,START,START+180000)
        measured=[b for b in bars if b["mb"] is not None]
        self.assertEqual(len(bars),1440)
        self.assertEqual([b["mb"] for b in measured],[40,60,20])
        self.assertEqual(sum(b["mb"] for b in measured),120)
        self.assertTrue(all(b["estimated"] for b in measured))
        self.assertTrue(all(b["nodes"][0]["ip"]=="192.0.2.1" for b in measured))
        rows[-1]["hg"]["workers"][0]["ip"]="192.0.2.2"
        self.assertTrue(all(b["mb"] is None for b in honeygain_minutes(rows,START,START+180000)))

    def test_honeygain_does_not_bridge_an_ip_that_returns_later(self):
        rows=[{"time_ms":START+t*1000,"hg":{"status_observed_ms":START+t*1000,"workers":[{"machine":MACHINE,"ip":ip,"network_bytes":t*1_000_000,"received_age_ms":0}]}} for t,ip in [(0,"192.0.2.1"),(80,"192.0.2.2"),(160,"192.0.2.1")]]
        self.assertTrue(all(b["mb"] is None for b in honeygain_minutes(rows,START,START+180000)))

    def test_honeygain_missing_gap_and_counter_reset_are_not_estimated_traffic(self):
        for second,value in [(240,2_000_000),(60,500_000),(60,None)]:
            rows=[{"time_ms":START+t*1000,"hg":{"status_observed_ms":START+t*1000,
                "workers":[{"machine":MACHINE,"network_bytes":n,"received_age_ms":0}]}} for t,n in [(0,1_000_000),(second,value)]]
            self.assertTrue(all(b["mb"] is None for b in honeygain_minutes(rows,START,START+300000)))

    def test_honeygain_popup_returns_twenty_largest_contributors(self):
        rows=[]
        for second in (0,60):
            rows.append({"time_ms":START+second*1000,"hg":{"status_observed_ms":START+second*1000,
                "workers":[{"machine":str(i),"ip":"192.0.2."+str(i),"network_bytes":i*1_000_000*second/60,"received_age_ms":0} for i in range(1,31)]}})
        bar=next(b for b in honeygain_minutes(rows,START,START+60000) if b["mb"] is not None)
        self.assertEqual(bar["count"],30)
        self.assertEqual(bar["mb"],465)
        self.assertEqual(len(bar["nodes"]),20)
        self.assertEqual(bar["nodes"][0]["mb"],30)

    def test_salad_restart_timestamp_accepts_seven_fractional_digits(self):
        self.assertEqual(timestamp_ms("2026-09-06T15:57:21.5157715+00:00"), 1788710241515)

    def test_timeline_uses_distinct_source_times_and_actual_elapsed_seconds(self):
        rows = [observation(0, 1, 2), observation(20, 3, 8), observation(50, 3, 20)]
        rows[-1]["ps"]["provider_observed_ms"] = START + 20_000
        timeline, truncated = rate_timeline(rows, START, START + 50_000)
        self.assertFalse(truncated)
        self.assertEqual(len(timeline["ps"]["provider"]), 1)
        self.assertEqual(timeline["ps"]["provider"][0]["per_second"], 100_000)
        self.assertEqual([p["per_second"] for p in timeline["ps"]["network"]], [300_000, 400_000])
        self.assertEqual(timeline["ps"]["network"][-1]["end_ms"], START + 50_000)

    def test_timeline_preserves_gaps_resets_and_partial_network_activity(self):
        rows = [observation(s, paid, s, complete=s != 360) for s, paid in ((0, 100), (60, 101), (300, 104), (360, 2))]
        timeline, _ = rate_timeline(rows, START, START + 360_000)
        paid = timeline["ps"]["provider"]
        self.assertEqual([p["status"] for p in paid], ["complete", "gap", "counter_reset"])
        self.assertIsNone(paid[1]["per_second"])
        self.assertEqual(paid[1]["delta"], 3_000_000)
        self.assertIsNone(paid[2]["per_second"])
        self.assertIsNone(paid[2]["delta"])
        partial = timeline["ps"]["network"][-1]
        self.assertEqual(partial["status"], "incomplete")
        self.assertFalse(partial["complete"])
        self.assertEqual(partial["per_second"], 1_000_000)
        self.assertTrue(all(p["complete"] for p in timeline["hg"]["provider"]))

    def test_timeline_has_no_fabricated_timestamps_or_prebaseline_hg_earnings(self):
        rows = [observation(s, s) for s in (0, 60, 120)]
        for row in rows:
            row["ps"]["network_observed_ms"] = None
            row["ps"]["provider_observed_ms"] = START - 1000
        timeline, _ = rate_timeline(rows, START, START + 120_000, START + 60_000)
        self.assertEqual(timeline["ps"]["network"], [])
        self.assertEqual(timeline["ps"]["provider"], [])
        self.assertEqual(len(timeline["hg"]["provider"]), 1)
        self.assertEqual(timeline["hg"]["provider"][0]["start_ms"], START + 60_000)

    def test_records_rate_fall_without_calling_network_earnings(self):
        rows = [observation(s, s / 10 if s <= 600 else 60 + (s - 600) / 20) for s in range(0, 1201, 60)]
        buckets = rate_buckets(rows, START, START + 1200_000)
        self.assertEqual(len(buckets), 2)
        self.assertAlmostEqual(buckets[0]["ps_credited"]["delta"], 60)
        self.assertAlmostEqual(buckets[1]["ps_credited"]["delta"], 30)
        self.assertEqual(buckets[0]["ps_network"]["delta"], 120)
        self.assertEqual(buckets[1]["ps_credited"]["change_percent"], -50)
        self.assertEqual(buckets[0]["hg_credits"]["delta"], 10)
        self.assertEqual(buckets[0]["ps_credited"]["status"], "complete")

    def test_counter_reset_is_unknown_not_negative_earning(self):
        rows = [observation(s, s if s < 300 else s - 300) for s in range(0, 601, 60)]
        value = rate_buckets(rows, START, START + 600_000)[0]["ps_credited"]
        self.assertEqual(value["status"], "counter_reset")
        self.assertIsNone(value["delta"])
        self.assertIsNone(value["per_10_min"])

    def test_gap_has_no_claimed_ten_minute_rate(self):
        rows = [observation(s, s / 10) for s in [0, 60, 540, 600]]
        value = rate_buckets(rows, START, START + 600_000)[0]["ps_credited"]
        self.assertEqual(value["delta"], 60)
        self.assertEqual(value["status"], "gap")
        self.assertIsNone(value["per_10_min"])

    def test_missing_network_workers_do_not_become_full_fleet_zero(self):
        rows = [observation(s, 0, complete=s != 300) for s in range(0, 601, 60)]
        value = rate_buckets(rows, START, START + 600_000)[0]["ps_network"]
        self.assertEqual(value["status"], "incomplete")
        self.assertIsNone(value["per_10_min"])
        self.assertEqual(value["delta"], 0)

    def test_stale_provider_observation_is_not_a_new_zero_earning_sample(self):
        rows = [observation(s, 42) for s in range(0, 601, 60)]
        for row in rows:
            row["ps"]["provider_observed_ms"] = START - 60_000
        value = rate_buckets(rows, START, START + 600_000)[0]["ps_credited"]
        self.assertEqual(value["status"], "missing")
        self.assertIsNone(value["delta"])

    def test_honeygain_network_remains_separate_from_credits(self):
        rows = [observation(s, s / 10) for s in range(0, 601, 60)]
        for row in rows:
            row["hg"].update(network_total_bytes=(row["time_ms"] - START) * 200,
                             network_observed_ms=row["time_ms"], network_complete=True)
        bucket = rate_buckets(rows, START, START + 600_000)[0]
        self.assertEqual(bucket["hg_network"]["delta"], 120)
        self.assertEqual(bucket["hg_credits"]["delta"], 10)

    def test_five_minute_hg_readings_are_expected_but_ps_readings_are_gapped(self):
        bucket = rate_buckets([observation(s, s / 10) for s in [0, 300, 600]], START, START + 600_000)[0]
        self.assertEqual(bucket["hg_credits"]["status"], "complete")
        self.assertEqual(bucket["ps_credited"]["status"], "gap")

    def test_missing_first_or_last_minute_stays_partial(self):
        for times in (range(60, 601, 60), range(0, 541, 60)):
            value = rate_buckets([observation(s, s / 10) for s in times], START, START + 600_000)[0]["ps_credited"]
            self.assertEqual(value["status"], "partial")
            self.assertIsNone(value["per_10_min"])


class FleetTestFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "fleet-tests"
        self.root.mkdir()
        self.current = {"id": "test-one", "started_ms": START, "status": "measuring",
                        "phase": "baseline", "ps": {"desired": 10, "baseline_provider_bytes": 100_000_000,
                                                     "organization": "test-org", "group": "ps-current"},
                        "hg": {"desired": 10}, "api_key": "secret-not-for-browser"}
        (self.root / "current.json").write_text(json.dumps(self.current))

    def tearDown(self):
        self.tmp.cleanup()

    def write_rows(self, rows):
        (self.root / "observations.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def write_census(self, restarted, observed, instance=INSTANCE, group="test-org/default/ps-current"):
        def stamp(seconds):
            return datetime.fromtimestamp(START / 1000 + seconds, timezone.utc).isoformat()
        directory = self.root.parent / "packetstream"
        directory.mkdir(exist_ok=True)
        census = {"group": group, "checked_at": stamp(observed), "last_success_at": stamp(observed),
                  "group_state": {"status": "running", "start_time": stamp(restarted)},
                  "nodes": [{"machine": MACHINE, "instance_id": instance,
                             "client_status": {"state": "running", "message": "private-census-message"}}]}
        (directory / "native-census.json").write_text(json.dumps(census))

    def ps_row(self, seconds, paid, network=0, instance=INSTANCE):
        row = observation(seconds, paid, network)
        row["ps"]["status_observed_ms"] = row["time_ms"]
        row["ps"]["workers"][0].update(machine=MACHINE, run=MACHINE + "/" + instance,
            client_status="running", client_status_age_ms=0, sample_source="native_status_only",
            network_bytes=network * 1_000_000, source_age_ms=0)
        return row

    def test_native_minute_observer_suffix_matches_current_census(self):
        row = self.ps_row(610, 110, 999)
        row["ps"]["workers"][0]["run"] += "/1800000600000"
        row["ps"]["workers"][0]["sample_source"] = "native_minutes"
        self.write_rows([row])
        self.write_census(600, 610)
        result = FleetTestView(self.root).snapshot(now_ms=START + 611_000)
        self.assertEqual(result["latest"]["ps"]["inventory_status"], "matched")
        self.assertEqual(result["latest"]["ps"]["workers"][0]["sample_source"], "native_minutes")

    def test_restart_window_rebases_account_and_network_without_crossing_restart(self):
        rows = [self.ps_row(s, paid, network) for s, paid, network in ((0, 100, 200), (590, 110, 220), (610, 111, 230), (670, 113, 234))]
        self.write_rows(rows)
        self.write_census(600, 670)
        result = FleetTestView(self.root).snapshot(now_ms=START + 671_000)
        window = result["service_windows"]["ps"]
        self.assertEqual(window["start_ms"], START + 600_000)
        self.assertEqual(window["basis"], "native_restart")
        self.assertFalse(window["stale"])
        self.assertEqual(window["provider_baseline_ms"], START + 610_000)
        self.assertEqual(result["summary"]["ps_credited_mb"], 2)
        self.assertEqual(result["summary"]["ps_network_mb"], 4)
        for metric in ("provider", "network"):
            self.assertEqual(len(result["timeline"]["ps"][metric]), 1)
            self.assertEqual(result["timeline"]["ps"][metric][0]["start_ms"], START + 610_000)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["network_interval"]["start_ms"], START + 610_000)
        self.assertEqual(result["service_windows"]["hg"]["start_ms"], START)
        self.assertNotIn("private-census-message", json.dumps(result))

    def test_new_run_earnings_require_two_distinct_fresh_reset_free_readings(self):
        for scenario in ("pre_restart", "one_reading", "reset", "stale_provider", "stale_census"):
            with self.subTest(scenario=scenario):
                rows = [self.ps_row(590, 110), self.ps_row(610, 111), self.ps_row(670, 113)]
                now = 671
                if scenario == "pre_restart":
                    for row in rows[1:]:
                        row["ps"].update(provider_observed_ms=START + 590_000, provider_bytes=110_000_000)
                elif scenario == "one_reading":
                    rows[-1]["ps"].update(provider_observed_ms=START + 610_000, provider_bytes=111_000_000)
                elif scenario == "reset":
                    rows[-1]["ps"]["provider_bytes"] = 1_000_000
                elif scenario == "stale_provider":
                    now = 900
                elif scenario == "stale_census":
                    now = 770
                self.write_rows(rows)
                self.write_census(600, 670 if scenario == "stale_census" else now)
                result = FleetTestView(self.root).snapshot(now_ms=START + now * 1000)
                self.assertIsNone(result["summary"]["ps_credited_mb"])

    def test_newer_census_hides_replaced_instances_until_the_ledger_catches_up(self):
        self.write_rows([self.ps_row(610, 111, 1)])
        self.write_census(600, 615, instance=REPLACEMENT)
        result = FleetTestView(self.root).snapshot(now_ms=START + 616_000)
        ps = result["latest"]["ps"]
        self.assertEqual(ps["inventory_status"], "awaiting_current_run")
        self.assertEqual(len(ps["workers"]), 10)
        self.assertTrue(all(w["state"] == "unknown" and not w.get("run") for w in ps["workers"]))
        self.assertIsNone(ps["running"])
        self.assertFalse(ps["network_complete"])
        self.assertTrue(any("Older container rows are hidden" in w for w in result["warnings"]))

    def test_restart_does_not_reuse_an_earlier_event_or_worker_counter(self):
        rows = [self.ps_row(590, 110, 100), self.ps_row(610, 111, 200)]
        rows[-1]["ps"]["workers"][0]["client_status_age_ms"] = 20_000
        self.write_rows(rows)
        self.write_census(600, 610)
        result = FleetTestView(self.root).snapshot(now_ms=START + 611_000)
        worker = result["latest"]["ps"]["workers"][0]
        self.assertEqual(worker["client_status"], "unknown")
        self.assertTrue(worker["client_status_stale"])
        self.assertIsNone(worker["network_interval"]["per_second"])

    def test_wrong_target_census_and_older_membership_do_not_replace_newer_ledger(self):
        self.write_rows([self.ps_row(620, 111, instance=REPLACEMENT)])
        self.write_census(600, 615, group="other-org/default/ps-current")
        result = FleetTestView(self.root).snapshot(now_ms=START + 621_000)
        self.assertEqual(result["service_windows"]["ps"]["start_ms"], START)
        self.assertTrue(result["service_windows"]["ps"]["stale"])
        self.assertEqual(result["latest"]["ps"]["workers"][0]["run"], MACHINE + "/" + REPLACEMENT)
        self.write_census(600, 615)
        result = FleetTestView(self.root).snapshot(now_ms=START + 621_000)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["run"], MACHINE + "/" + REPLACEMENT)

    def test_archives_keep_test_window_and_original_baseline_after_a_live_restart(self):
        archive = self.root / "archives" / "test-one"
        archive.mkdir(parents=True)
        (archive / "current.json").write_text(json.dumps(self.current))
        rows = [self.ps_row(s, paid) for s, paid in ((0, 100), (590, 110), (610, 111), (670, 113))]
        (archive / "observations.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        self.write_census(600, 670, instance=REPLACEMENT)
        result = FleetTestView(self.root).snapshot(now_ms=START + 671_000, archive="test-one")
        self.assertEqual(result["service_windows"]["ps"]["start_ms"], START)
        self.assertEqual(result["service_windows"]["ps"]["basis"], "test")
        self.assertEqual(result["summary"]["ps_credited_mb"], 13)
        self.assertEqual(len(result["timeline"]["ps"]["provider"]), 3)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["run"], MACHINE + "/" + INSTANCE)

    def test_current_snapshot_ignores_prior_run_and_allowlists_secrets(self):
        prior = observation(0, 999, experiment="old-test")
        good = observation(60, 102)
        good["ps"]["password"] = "secret-password"
        good["ps"]["workers"][0]["token"] = "secret-token"
        good["errors"] = ["failure contains secret-password"]
        self.write_rows([prior, observation(0, 100), good])
        result = FleetTestView(self.root).snapshot(now_ms=START + 70_000)
        self.assertEqual(result["observation_count"], 2)
        self.assertEqual(result["summary"]["ps_credited_mb"], 2)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["client_status"], "unknown")
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(len(result["latest"]["ps"]["workers"]), 10)

    def test_bad_tail_and_stopped_recorder_are_visible(self):
        self.write_rows([observation(0, 100)])
        with (self.root / "observations.jsonl").open("a") as handle:
            handle.write('{"partial":')
        result = FleetTestView(self.root).snapshot(now_ms=START + 300_000)
        self.assertTrue(result["recorder_stale"])
        self.assertEqual(result["invalid_lines"], 1)
        self.assertTrue(result["warnings"])

    def test_hg_worker_error_codes_are_allowlisted(self):
        cases = [(code, code) for code in (
            "device_limit", "device_already_active", "network_overused", "network_unusable", "authorization_error")]
        cases += [(None, None), ("", None),
                  ("RuntimeError: https://example.invalid/?token=private-value-not-for-browser", "observer_error"),
                  ("device_limit: private-value-not-for-browser", "observer_error"),
                  ({"message": "private-value-not-for-browser"}, "observer_error")]
        for raw_error, expected in cases:
            with self.subTest(raw_error=raw_error):
                row = observation(0, 100)
                row["hg"]["workers"][0]["error"] = raw_error
                self.write_rows([row])
                result = FleetTestView(self.root).snapshot(now_ms=START + 10_000, include_observations=True)
                for source in (result["latest"], result["observations"][0]):
                    worker = source["hg"]["workers"][0]
                    self.assertEqual(worker["error_code"], expected)
                    self.assertNotIn("error", worker)
                self.assertNotIn("private-value-not-for-browser", json.dumps(result))

    def test_ps_errors_and_native_census_age_are_sanitized_independently(self):
        cases = [(None, None), ("", None),
                 ("PacketStream allows packeting from 1 client per IP address. private-value-not-for-browser", "duplicate_ip"),
                 ("one client per IP private-value-not-for-browser", "client_error"),
                 ({"message": "private-value-not-for-browser"}, "client_error")]
        for raw_error, expected in cases:
            with self.subTest(raw_error=raw_error):
                row = observation(90, 100)
                row["ps"]["status_observed_ms"] = START
                row["ps"]["workers"][0].update(run="instance-a", sample_source="native_status_only",
                    client_status="running", client_status_age_ms=30_000, error=raw_error)
                self.write_rows([row])
                result = FleetTestView(self.root).snapshot(now_ms=START + 100_000, include_observations=True)
                ps = result["latest"]["ps"]
                worker = ps["workers"][0]
                self.assertFalse(result["recorder_stale"])
                self.assertEqual(ps["status_age_ms"], 100_000)
                self.assertTrue(ps["status_stale"])
                self.assertTrue(ps["native_status_only"])
                self.assertEqual(worker["client_status"], "running")
                self.assertEqual(worker["client_status_age_ms"], 40_000)
                self.assertTrue(worker["client_status_stale"])
                self.assertEqual(worker["run"], "instance-a")
                self.assertEqual(worker["error_code"], expected)
                self.assertNotIn("error", worker)
                self.assertEqual(result["observations"][0]["ps"]["workers"][0]["client_status_age_ms"], 30_000)
                self.assertNotIn("private-value-not-for-browser", json.dumps(result))

    def test_native_event_age_does_not_add_the_census_age_again(self):
        row = observation(300, 100)
        row["ps"]["status_observed_ms"] = START + 280_000
        row["ps"]["workers"][0].update(sample_source="native_status_only", client_status_age_ms=180_000)
        self.write_rows([row])
        for recorder_age in (0, 2000):
            with self.subTest(recorder_age=recorder_age):
                result = FleetTestView(self.root).snapshot(now_ms=START + 300_000 + recorder_age)
                ps = result["latest"]["ps"]
                self.assertEqual(ps["status_age_ms"], 20_000 + recorder_age)
                self.assertEqual(ps["workers"][0]["client_status_age_ms"], 180_000 + recorder_age)
                self.assertFalse(ps["status_stale"])
                self.assertFalse(ps["workers"][0]["client_status_stale"])

    def test_native_client_event_has_its_own_four_minute_cutoff(self):
        for event_age, expected_stale in ((230_000, False), (231_000, True)):
            with self.subTest(event_age=event_age):
                row = observation(300, 100)
                row["ps"]["status_observed_ms"] = START + 300_000
                row["ps"]["workers"][0].update(sample_source="native_status_only", client_status_age_ms=event_age)
                self.write_rows([row])
                result = FleetTestView(self.root).snapshot(now_ms=START + 310_000)
                self.assertFalse(result["latest"]["ps"]["status_stale"])
                self.assertEqual(result["latest"]["ps"]["workers"][0]["client_status_stale"], expected_stale)

    def test_worker_rates_use_sample_times_without_mutating_ledger_ages(self):
        rows = [observation(s, 100) for s in (0, 30, 60)]
        for row, ps_bytes, hg_bytes in zip(rows, (100, 160, 220), (500, 800, 1100)):
            row["ps"]["status_observed_ms"] = row["time_ms"]
            row["ps"]["workers"][0].update(run="instance-a", network_bytes=ps_bytes, source_age_ms=1000, received_age_ms=500)
            row["hg"]["status_observed_ms"] = row["time_ms"]
            row["hg"]["workers"][0].update(network_bytes=hg_bytes, received_age_ms=5000)
        self.write_rows(rows)
        result = FleetTestView(self.root).snapshot(now_ms=START + 61_000, include_observations=True)
        ps = result["latest"]["ps"]["workers"][0]
        hg = result["latest"]["hg"]["workers"][0]
        self.assertEqual(ps["network_interval"]["per_second"], 2)
        self.assertEqual(ps["network_interval"]["end_ms"], START + 59_000)
        self.assertEqual(hg["network_interval"]["per_second"], 10)
        self.assertEqual(hg["network_interval"]["end_ms"], START + 55_000)
        self.assertEqual(ps["source_age_ms"], 2000)
        self.assertEqual(result["observations"][-1]["ps"]["workers"][0]["source_age_ms"], 1000)

    def test_worker_restart_gap_reset_and_stale_samples_have_unknown_rates(self):
        for run, seconds, current_bytes, now_seconds, expected in (
            ("new-instance", 60, 200, 61, "missing"),
            ("same-instance", 60, 50, 61, "counter_reset"),
            ("same-instance", 240, 200, 241, "gap"),
            ("same-instance", 60, 200, 121, "stale"),
            ("same-instance", 60, None, 61, "missing"),
        ):
            with self.subTest(expected=expected):
                rows = [observation(0, 100), observation(seconds, 100)]
                rows[0]["ps"]["workers"][0].update(run="same-instance", network_bytes=100, source_age_ms=0)
                rows[1]["ps"]["workers"][0].update(run=run, network_bytes=current_bytes, source_age_ms=0)
                self.write_rows(rows)
                result = FleetTestView(self.root).snapshot(now_ms=START + now_seconds * 1000)
                interval = result["latest"]["ps"]["workers"][0]["network_interval"]
                self.assertEqual(interval["status"], expected)
                self.assertIsNone(interval["per_second"])
                self.assertFalse(interval["complete"])

    def test_fresh_recorder_does_not_hide_a_stale_honeygain_observer(self):
        row = observation(300, 100)
        row["hg"]["status_observed_ms"] = START
        row["hg"]["workers"][0]["received_age_ms"] = 2000
        row["ps"]["workers"][0]["network_bytes"] = 9_000_000
        row["ps"]["workers"][0]["received_age_ms"] = 1000
        self.write_rows([row])
        result = FleetTestView(self.root).snapshot(now_ms=START + 310_000)
        self.assertFalse(result["recorder_stale"])
        self.assertTrue(result["latest"]["hg"]["status_stale"])
        self.assertEqual(result["latest"]["hg"]["status_age_ms"], 310_000)
        self.assertEqual(result["latest"]["hg"]["workers"][0]["received_age_ms"], 312_000)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["received_age_ms"], 11_000)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["network_bytes"], 9_000_000)
        self.assertTrue(any("observer" in warning for warning in result["warnings"]))

    def test_hg_explicit_baseline_excludes_startup_credits(self):
        self.current["hg"].update(baseline_provider_gathering_credits=181.73,
                                  baseline_provider_observed_ms=START + 300_000,
                                  baseline_started_ms=START + 300_000)
        (self.root / "current.json").write_text(json.dumps(self.current))
        rows = [observation(s, 100) for s in (0, 300, 600)]
        for row, credits in zip(rows, (169.74, 181.73, 187.33)):
            row["hg"]["provider_gathering_credits"] = credits
        rows[-1]["ps"]["accepted"] = 7
        rows[-1]["ps"]["workers"][0].update(sample_source="salad_logs_10s", source_granularity_seconds=10, last_interval_seconds=10)
        self.write_rows(rows)
        result = FleetTestView(self.root).snapshot(now_ms=START + 610_000)
        self.assertAlmostEqual(result["summary"]["hg_gathering_credits"], 5.6)
        self.assertEqual(result["latest"]["ps"]["accepted"], 7)
        self.assertEqual(result["latest"]["ps"]["workers"][0]["sample_source"], "salad_logs_10s")
        self.write_rows(rows[:2])
        result = FleetTestView(self.root).snapshot(now_ms=START + 310_000)
        self.assertIsNone(result["summary"]["hg_gathering_credits"])
        rows[-1]["hg"]["provider_gathering_credits"] = 20
        self.write_rows(rows)
        self.assertIsNone(FleetTestView(self.root).snapshot(now_ms=START + 610_000)["summary"]["hg_gathering_credits"])

    def test_archive_selection_cannot_escape_archive_directory(self):
        view = FleetTestView(self.root)
        for name in ["../current.json", "/tmp", "a/b", ".."]:
            with self.assertRaises(ValueError):
                view.snapshot(archive=name)

    def test_saved_experiment_archive_is_readable(self):
        archive = self.root / "archives" / "test-one"
        archive.mkdir(parents=True)
        (archive / "current.json").write_text(json.dumps(self.current))
        (archive / "observations.jsonl").write_text(json.dumps(observation(0, 100)) + "\n")
        result = FleetTestView(self.root).snapshot(now_ms=START + 60_000, archive="test-one")
        self.assertEqual(result["experiment"]["id"], "test-one")
        self.assertTrue(result["archived"])
        self.assertEqual(result["archives"][0]["id"], "test-one")


if __name__ == "__main__":
    unittest.main()
~~~~~~

### dashboard/tests/test_native_network.py

<!-- rebuild-file: dashboard/tests/test_native_network.py sha256=801c579a921e1f437825b0e1244905044047af685b0e6823e67c5037a1fabab5 -->
~~~~~~python
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from dashboard.native_network import NetworkMinutes, parse_minute

START = 1_800_000_000_000
MACHINE = '11111111-1111-1111-1111-111111111111'
INSTANCE = '22222222-2222-2222-2222-222222222222'
OTHER = '44444444-4444-4444-4444-444444444444'
GROUP = 'test-group'


def sample(seq, amount, instance=INSTANCE, **changes):
    values = dict(instance=instance, machine=MACHINE, observer=START, seq=seq,
                  start_ms=START + max(0, seq-1)*60000, end_ms=START+seq*60000,
                  rx=amount, tx=0, total_rx=amount, total_tx=0, ip='192.0.2.1',
                  state='running', error='none', final=0, bucket_ms=START+max(0, seq-1)*60000)
    values.update(changes)
    return {'text_log': 'PS_MINUTE_V2 ' + ' '.join(f'{k}={v}' for k,v in values.items())}


class NativeNetworkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = NetworkMinutes(Path(self.tmp.name)/'minutes.sqlite3')
        self.now = START+130000
        self.census = {'group_id': GROUP, 'desired_replicas': 2,
                       'checked_at': datetime.fromtimestamp(self.now/1000,timezone.utc).isoformat(),
                       'nodes': [{'machine': MACHINE, 'instance_id': i, 'salad_state': 'running'} for i in (INSTANCE,OTHER)]}

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def ingest(self,*items):
        return self.store.ingest([parse_minute(i,GROUP,self.now) for i in items])

    def view(self, **kwargs):
        return self.store.snapshot(self.census, now_ms=self.now, **kwargs)

    def test_common_minutes_contributions_totals_and_replay(self):
        items = [sample(0,0),sample(1,60000000),sample(2,1500000,total_rx=61500000),sample(2,2500000,OTHER)]
        self.assertEqual(self.ingest(*items),4)
        self.assertEqual(self.ingest(*items),0)
        result=self.view()
        self.assertEqual([b['mb'] for b in result['candles'] if b['mb'] is not None], [60,4])
        detail=self.store.minute(GROUP,START+60000)
        self.assertEqual(detail['mb'],4)
        self.assertEqual(sum(n['mb'] for n in detail['nodes']),4)
        self.assertEqual(result['nodes'][0]['total_mb'],61.5)
        self.assertEqual(result['nodes'][0]['latest_mb_per_minute'],1.5)
        self.assertEqual(result['nodes'][0]['status'],'Running')
        self.assertEqual(result['disk']['total_records'],4)
        self.assertEqual(result['disk']['total_record_bytes'],sum(len(i['text_log'].encode())+1 for i in items))
        first=self.store.minute(GROUP,START)
        self.assertEqual(first['nodes'][0]['mb'],60)
        self.assertEqual(len(first['nodes']),1)

    def test_missing_and_conflicting_records_are_not_zero(self):
        self.ingest(sample(1,1000000),sample(1,2000000),sample(3,0))
        result=self.view()
        self.assertEqual([b['mb'] for b in result['candles'][-3:]], [None,None,0])
        self.assertIsNone(self.store.minute(GROUP,START+60000)['mb'])
        self.assertTrue(result['nodes'][0]['has_gaps'])

    def test_selected_minute_includes_reallocated_contributor(self):
        self.ingest(sample(1,4000000,final=1),sample(1,7000000,OTHER))
        self.census['nodes']=self.census['nodes'][1:]
        result=self.view()
        detail=self.store.minute(GROUP,START)
        self.assertEqual(detail['mb'],11)
        self.assertEqual(sum(n['mb'] for n in detail['nodes']),11)
        self.assertEqual(len(result['nodes']),1)
        self.assertEqual(result['nodes'][0]['instance'],OTHER)

    def test_bad_component_does_not_break_candle_contribution_sum(self):
        self.ingest(sample(1,1000000,end_ms=START+30000),sample(2,2000000,start_ms=START+30000,end_ms=START+60000,bucket_ms=START))
        self.ingest(sample(2,9000000,start_ms=START+30000,end_ms=START+60000,bucket_ms=START))
        result=self.view()
        detail=self.store.minute(GROUP,START)
        self.assertEqual(detail['mb'],1)
        self.assertEqual(detail['nodes'][0]['mb'],1)
        self.assertTrue(next(b for b in result['candles'] if b['minute_ms']==START)['partial'])

    def test_unaligned_legacy_and_delayed_intervals_are_marked_estimated(self):
        delayed=sample(1,1000000,end_ms=START+61000)
        legacy=sample(2,2000000);legacy['text_log']=legacy['text_log'].replace('PS_MINUTE_V2','PS_MINUTE_V1').split(' bucket_ms=')[0]
        self.ingest(delayed,legacy)
        measured=[b for b in self.view()['candles'] if b['mb'] is not None]
        self.assertTrue(measured)
        self.assertTrue(all(b['estimated'] for b in measured))
        self.assertAlmostEqual(sum(b['mb'] for b in measured),3)
        self.assertEqual(self.view()['nodes'][0]['total_mb'],2)

    def test_large_history_gap_is_bounded_and_stale_status_is_explicit(self):
        self.ingest(sample(1,1000000),sample(10000,1000000))
        result=self.view()
        self.assertEqual(len(result['candles']),1440)
        self.now += 300000
        result=self.view()
        self.assertFalse(result['inventory_fresh'])
        self.assertEqual(result['nodes'][0]['status'],'Status feed stale')

    def test_baseline_has_no_bar_and_zero_interval_is_measured(self):
        self.ingest(sample(0,0))
        self.assertTrue(all(b['mb'] is None for b in self.view()['candles']))
        self.ingest(sample(1,0))
        self.assertEqual(self.store.minute(GROUP,START)['mb'],0)


    def test_full_day_top_twenty_countries_and_stopped_client(self):
        self.ingest(sample(1,1000000,final=1))
        result=self.view()
        self.assertEqual(result['nodes'][0]['status'],'Stopped')
        self.assertEqual(result['running'],0)
        self.assertEqual(len(result['candles']),1440)
        self.assertEqual(result['candles'][-1]['minute_ms']-result['candles'][0]['minute_ms'],1439*60000)
        for i in range(30):
            self.ingest(sample(1,(i+1)*1000000,instance=f'{i:08x}-aaaa-aaaa-aaaa-aaaaaaaaaaaa',ip=f'192.0.2.{i+1}'))
        with self.store.db:self.store.db.execute("INSERT INTO countries VALUES ('192.0.2.30','US')")
        detail=self.store.minute(GROUP,START)
        self.assertEqual(len(detail['nodes']),20)
        self.assertEqual(detail['nodes'][0]['mb'],30)
        self.assertEqual(detail['nodes'][0]['country'],'US')
        self.assertEqual(detail['count'],31)
        self.assertEqual(detail['mb'],466)

    def test_snapshot_read_transaction_keeps_concurrent_collector_consistent(self):
        self.ingest(sample(1,1000000))
        writer=NetworkMinutes(self.store.path)
        original=self.store.latest
        def interleave(group):
            rows=original(group)
            writer.ingest([parse_minute(sample(2,5000000,total_rx=6000000),GROUP,self.now)])
            return rows
        self.store.latest=interleave
        result=self.view()
        self.assertEqual(result['nodes'][0]['total_mb'],1)
        self.assertIsNone(result['candles'][-2]['mb'])
        self.store.latest=original
        self.assertEqual(self.view()['nodes'][0]['total_mb'],6)
        writer.db.close()

if __name__ == '__main__': unittest.main()
~~~~~~

### dashboard/tests/test_provider_bridge.cjs

<!-- rebuild-file: dashboard/tests/test_provider_bridge.cjs sha256=dd36f307903409f578c0cfd02dd5f24a7fd4c79dc1229f1748f305c2f23a4f9c -->
~~~~~~text
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../static/ps1.js'), 'utf8');
const channel = 'simulated-provider-channel';
const reading = {type: 'ps-credited', channel, gb: 1.25, bytes: 1250000000, time_ms: 1788666387000};
const response = (status, body = {}) => ({status, ok: status >= 200 && status < 300, json: async () => body});

function bridge(fetchReply, hash = '#ps1') {
  const listeners = new Map();
  const calls = [];
  const element = () => ({textContent: '', addEventListener() {}});
  const elements = {psConnect: element(), psFeedStatus: element(), history: element()};
  const location = {hash};
  const context = {
    location,
    window: {location, addEventListener: (name, handler) => listeners.set(name, handler)},
    document: {getElementById: id => elements[id]},
    sessionStorage: {getItem: key => key === 'ps-billing-channel' ? channel : null},
    AbortSignal: {timeout: () => undefined},
    fetch: async (url, options) => {
      calls.push({url, options});
      return fetchReply(url, options, calls);
    },
  };
  vm.runInNewContext(source, context, {filename: 'ps1.js'});
  return {
    calls,
    message: elements.psFeedStatus,
    location,
    emit: overrides => listeners.get('message')({
      origin: 'https://app.packetstream.io', data: {...reading}, ...overrides,
    }),
  };
}

test('untrusted origins and channels cannot fetch or save provider readings', async () => {
  const app = bridge(() => {throw new Error('Rejected messages must not fetch');});
  for (const overrides of [
    {origin: 'https://unrelated.example'},
    {origin: 'https://app.packetstream.io.unrelated.example'},
    {data: {...reading, channel: 'wrong-channel'}},
    {data: {...reading, channel: ''}},
    {data: {...reading, type: 'unrelated-message'}},
  ]) await app.emit(overrides);
  assert.equal(app.calls.length, 0);
  assert.equal(app.message.textContent, '');
});

test('provider messages are saved while either service tab is selected', async () => {
  for (const hash of ['#hg1', '#ps1']) {
    const app = bridge(url => url === '/api/ps1/view'
      ? response(200, {bridge_token: 'simulated-token', feed_age_ms: 1000})
      : response(200), hash);
    await app.emit();
    assert.deepEqual(app.calls.map(call => call.url), ['/api/ps1/view', '/api/ps1/credited']);
    const saved = app.calls[1].options;
    assert.equal(saved.method, 'POST');
    assert.equal(saved.headers['X-PS-Token'], 'simulated-token');
    assert.deepEqual(JSON.parse(saved.body), {gb: reading.gb, bytes: reading.bytes, time_ms: reading.time_ms});
    assert.equal(app.message.textContent, 'Provider reading saved.');
    assert.equal(app.location.hash, hash);
  }
});

test('a later push obtains the new token after a dashboard restart', async () => {
  let token = 'before-restart';
  const app = bridge((url, options) => {
    if (url === '/api/ps1/view') return response(200, {bridge_token: token});
    return response(options.headers['X-PS-Token'] === token ? 200 : 403);
  });
  await app.emit();
  token = 'after-restart';
  await app.emit();
  assert.deepEqual(app.calls.map(call => call.url), [
    '/api/ps1/view', '/api/ps1/credited', '/api/ps1/view', '/api/ps1/credited',
  ]);
  assert.deepEqual(app.calls.filter(call => call.url === '/api/ps1/credited')
    .map(call => call.options.headers['X-PS-Token']), ['before-restart', 'after-restart']);
  assert.equal(app.message.textContent, 'Provider reading saved.');
});

test('a 403 between reading the token and saving refreshes and retries once', async () => {
  let reads = 0;
  const app = bridge((url, options) => {
    if (url === '/api/ps1/view') return response(200, {bridge_token: ++reads === 1 ? 'expired-token' : 'fresh-token'});
    return response(options.headers['X-PS-Token'] === 'fresh-token' ? 200 : 403);
  });
  await app.emit();
  assert.deepEqual(app.calls.map(call => call.url), [
    '/api/ps1/view', '/api/ps1/credited', '/api/ps1/view', '/api/ps1/credited',
  ]);
  const saves = app.calls.filter(call => call.url === '/api/ps1/credited');
  assert.deepEqual(saves.map(call => call.options.headers['X-PS-Token']), ['expired-token', 'fresh-token']);
  assert.equal(saves[0].options.body, saves[1].options.body);
  assert.equal(app.message.textContent, 'Provider reading saved.');
});

test('a second 403 stops retrying and leaves an explicit failure', async () => {
  const app = bridge(url => url === '/api/ps1/view'
    ? response(200, {bridge_token: 'still-rejected-token'})
    : response(403));
  await app.emit();
  assert.equal(app.calls.filter(call => call.url === '/api/ps1/view').length, 2);
  assert.equal(app.calls.filter(call => call.url === '/api/ps1/credited').length, 2);
  assert.equal(app.message.textContent, 'Provider reading could not be saved.');
});
~~~~~~

### dashboard/tests/test_server.py

<!-- rebuild-file: dashboard/tests/test_server.py sha256=98bbfd4e883371e12a6c6da825445c610085e9d5ea399789adf7369049fe8e17 -->
~~~~~~python
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch
from http.server import ThreadingHTTPServer
from pathlib import Path

from dashboard.server import Poller, make_handler
from dashboard.fleet_test import FleetTestView
from dashboard.salad_api import _parse_iso
from dashboard.store import Store
from dashboard.tests.test_store import honeygain_event, log_entry


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "db.sqlite3")
        self.start = 1_700_000_000
        self.store.ingest(log_entry(self.start, 1))
        static_dir = Path(__file__).resolve().parents[1] / "static"
        self.fleet_dir = Path(self.tmp.name) / "fleet-tests"
        handler = make_handler(self.store, lambda: {"poll_state": "ok"}, static_dir, fleet_view=FleetTestView(self.fleet_dir))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        self.tmp.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as response:
            return response.status, response.headers, response.read()

    def test_status_series_and_exports(self):
        self.store.ingest(honeygain_event(self.start + 1, "connected"))
        status, headers, body = self.get("/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        status_body = json.loads(body)
        self.assertEqual(status_body["sample_count"], 1)
        self.assertGreaterEqual(status_body["source_lag_ms"], 0)

        end = (self.start + 2) * 1000
        status, _, body = self.get(f"/api/series?start={self.start * 1000}&end={end}&bucket=1")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["totals"]["eth0"]["rx_bytes"], 100)

        status, headers, body = self.get(f"/api/export.csv?start={self.start * 1000}&end={end}&bucket=1")
        self.assertEqual(status, 200)
        self.assertIn("text/csv", headers["Content-Type"])
        self.assertIn(b"eth0_rx_bytes_per_second", body)

        status, headers, body = self.get(f"/api/export.json?start={self.start * 1000}&end={end}&bucket=1")
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertEqual(json.loads(body)["schema_version"], 1)

        status, _, body = self.get(f"/api/events?start={self.start * 1000}&end={end}&bucket=1")
        self.assertEqual(status, 200)
        events = json.loads(body)
        self.assertEqual(events["event_count"], 1)
        self.assertEqual(events["counts"], {"connected": 1})

    def test_invalid_range_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.get("/api/series?start=2000&end=1000&bucket=1")
        self.assertEqual(raised.exception.code, 400)

    def test_dashboard_uses_one_panel_and_shared_service_tabs(self):
        status,_,body=self.get("/")
        self.assertEqual(status,200)
        page=body.decode()
        self.assertIn('id="services" role="tablist"',page)
        self.assertIn('id="bandwidthPanel" role="tabpanel"',page)
        self.assertNotIn('target="_blank"',page)
        self.assertLess(page.index('/ps1.js'),page.index('/fleet-test.js'))
        _,_,script=self.get('/fleet-test.js')
        for name in [b'Honeygain',b'PacketStream',b'Proxyrack',b'Repocket',b'RFM',b'Traffic Monetizer']:
            self.assertIn(name,script)
        self.assertIn(b'6 hours',script)
        self.assertIn(b'12 hours',script)
        self.assertIn(b'24 hours',script)

    def test_ps1_proxy_preserves_raw_history_and_cursor(self):
        payload = b'{"cursor":241,"points":[{"seq":240,"seconds":1,"bytes":750000},{"seq":241,"seconds":4,"bytes":2000000}]}'
        connection = MagicMock()
        connection.getresponse.return_value.status = 200
        connection.getresponse.return_value.read.return_value = payload
        with patch("dashboard.server.HTTPConnection", return_value=connection) as connect:
            status, headers, body = self.get("/api/ps1/history?after=239")
        self.assertEqual(status, 200)
        self.assertEqual(body, payload)
        self.assertEqual(headers["Cache-Control"], "no-store")
        connect.assert_called_once_with("127.0.0.1", 8789, timeout=4)
        connection.request.assert_called_once_with("GET", "/api/ps1/history?after=239", headers={"Accept": "application/json"})
        connection.close.assert_called_once()

    def test_fleet_endpoint_exports_only_sanitized_current_experiment(self):
        self.fleet_dir.mkdir()
        start = 1_800_000_000_000
        metadata = {"id": "current-run", "started_ms": start, "ps": {"baseline_provider_bytes": 0}, "hg": {}, "token": "do-not-expose"}
        (self.fleet_dir / "current.json").write_text(json.dumps(metadata))
        row = {"experiment_id": "current-run", "time_ms": start, "ps": {"api_key": "do-not-expose"}, "hg": {}}
        (self.fleet_dir / "observations.jsonl").write_text(json.dumps(row) + "\n")
        for path in ("/api/fleet-test", "/api/fleet-test/export.json", "/api/fleet-test/export.csv"):
            status, headers, body = self.get(path)
            self.assertEqual(status, 200)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertNotIn(b"do-not-expose", body)
            if "export" in path:
                self.assertIn("attachment", headers["Content-Disposition"])
        _, _, body = self.get("/api/fleet-test/export.json")
        self.assertEqual(json.loads(body)["observations"][0]["experiment_id"], "current-run")
        _, _, script = self.get("/fleet-test.js")
        self.assertIn(b"/api/fleet-test", script)
        self.assertIn(b"setInterval(refresh,5000)", script)

    def test_fleet_endpoint_rejects_archive_path_traversal(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.get("/api/fleet-test?archive=..%2F..%2Fsecrets")
        self.assertEqual(raised.exception.code, 400)

    def test_ps1_proxy_reports_offline_without_faking_zero_traffic(self):
        connection = MagicMock()
        connection.request.side_effect = ConnectionRefusedError("private upstream detail")
        with patch("dashboard.server.HTTPConnection", return_value=connection):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                self.get("/api/ps1/status")
        self.assertEqual(raised.exception.code, 503)
        self.assertEqual(json.loads(raised.exception.read()), {"error": "PS1 recorder is unavailable"})
        connection.close.assert_called_once()

    def test_ps1_proxy_rejects_invalid_history_cursor(self):
        for value in ("-1", "nope", "http://example.com"):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                self.get(f"/api/ps1/history?after={value}")
            self.assertEqual(raised.exception.code, 400)

    def test_poller_recovers_a_log_that_arrives_after_the_first_poll(self):
        late_entry = log_entry(30, 1)

        class LateClient:
            calls = 0

            def fetch(self, start, end, page_size=100):
                self.calls += 1
                if self.calls == 1:
                    return []
                sample_time = _parse_iso(late_entry["json_log"]["sample_time"])
                if _parse_iso(start) <= sample_time < _parse_iso(end):
                    return [late_entry]
                return []

        poller = Poller(self.store, LateClient())
        poller.run_once(now_ms=110_000)
        poller.run_once(now_ms=120_000)

        self.assertEqual(self.store.status()["sample_count"], 2)

    def test_new_database_limits_initial_backfill_to_one_minute(self):
        class CaptureClient:
            window = None

            def fetch(self, start, end, page_size=100):
                self.window = (_parse_iso(start), _parse_iso(end))
                return []

        client = CaptureClient()
        poller = Poller(self.store, client, reconcile_horizon_seconds=0)
        poller.run_once(now_ms=2_000_000)

        start, end = client.window
        self.assertEqual((end - start).total_seconds(), 60)

    def test_poller_reconciles_a_late_log_during_continuous_traffic(self):
        normal = [log_entry(second, second, instance=f"normal-{second}") for second in range(650, 731, 10)]
        late = log_entry(610, 610, instance="late-instance")

        class ReconcileClient:
            late_available = False

            def fetch(self, start, end, page_size=100):
                start_time, end_time = _parse_iso(start), _parse_iso(end)
                rows = normal + ([late] if self.late_available else [])
                return [
                    row
                    for row in rows
                    if start_time <= _parse_iso(row["json_log"]["sample_time"]) < end_time
                ]

        client = ReconcileClient()
        poller = Poller(
            self.store,
            client,
            overlap_seconds=30,
            reconcile_horizon_seconds=120,
            reconcile_chunk_seconds=30,
        )
        poller.run_once(now_ms=700_000)
        poller.run_once(now_ms=710_000)
        client.late_available = True
        poller.run_once(now_ms=720_000)

        recovered = self.store.query_range(610_000, 611_000, 1)
        self.assertEqual(recovered["totals"]["eth0"]["rx_bytes"], 100)

    def test_reconciliation_final_check_catches_log_arriving_after_sweep(self):
        normal = [log_entry(second, second, instance=f"normal-{second}") for second in (185, 195, 205, 215)]
        late = log_entry(100, 999, instance="late-after-sweep")

        class ReconcileClient:
            late_available = False

            def fetch(self, start, end, page_size=100):
                start_time, end_time = _parse_iso(start), _parse_iso(end)
                rows = normal + ([late] if self.late_available else [])
                return [
                    row
                    for row in rows
                    if start_time <= _parse_iso(row["json_log"]["sample_time"]) < end_time
                ]

        client = ReconcileClient()
        poller = Poller(
            self.store,
            client,
            interval_seconds=10,
            overlap_seconds=30,
            reconcile_horizon_seconds=120,
            reconcile_chunk_seconds=30,
            reconcile_interval_seconds=10,
        )
        for now_ms in (200_000, 210_000, 220_000):
            poller.run_once(now_ms=now_ms)
        client.late_available = True
        poller.run_once(now_ms=230_000)

        recovered = self.store.query_range(100_000, 101_000, 1)
        self.assertEqual(recovered["totals"]["eth0"]["rx_bytes"], 100)

    def test_one_second_tail_fetch_keeps_reconciliation_on_slower_cadence(self):
        class CaptureClient:
            def __init__(self):
                self.windows = []

            def fetch(self, start, end, page_size=100):
                self.windows.append((_parse_iso(start), _parse_iso(end)))
                return []

        client = CaptureClient()
        poller = Poller(
            self.store,
            client,
            reconcile_horizon_seconds=120,
            reconcile_chunk_seconds=30,
            reconcile_interval_seconds=10,
        )
        for now_ms in range(200_000, 205_000, 1_000):
            poller.run_once(now_ms=now_ms)

        self.assertEqual(poller.interval_seconds, 1)
        self.assertLessEqual(len(client.windows), 7)
        self.assertEqual(poller.status()["tail_fetch_interval_seconds"], 1)
        self.assertEqual(poller.status()["reconcile_interval_seconds"], 10)


if __name__ == "__main__":
    unittest.main()
~~~~~~

### dashboard/tests/test_store.py

<!-- rebuild-file: dashboard/tests/test_store.py sha256=d1bed50aaf2381bdedc65c60ceb06287671d9f3cf6060d45bf0e5bfb8eb61bc5 -->
~~~~~~python
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from dashboard.store import Store


APPS = ("packetstream", "proxyrack", "traffmonetizer", "earnfm", "repocket", "bitping", "honeygain")


def iso(epoch_seconds):
    return datetime.fromtimestamp(epoch_seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def log_entry(epoch_seconds, sequence, instance="instance-a", machine="machine-a", rx=100, tx=50):
    applications = {
        name: {
            "attributed_packet_rx_bytes": rx if name == "packetstream" else 0,
            "attributed_packet_tx_bytes": tx if name == "packetstream" else 0,
            "process_count": 1,
            "socket_count": 2,
            "tcp_socket_count": 1,
            "tcp_established_count": 1,
            "udp_socket_count": 1,
            "state": "up",
        }
        for name in APPS
    }
    return {
        "time": iso(epoch_seconds + 0.2),
        "receive_time": iso(epoch_seconds + 0.3),
        "resource": {
            "type": "container",
            "labels": {
                "organization_name": "org",
                "project_name": "default",
                "container_group_name": "honeygain-us-1",
                "container_group_version": "1",
                "instance_id": instance,
                "machine_id": machine,
            },
        },
        "json_log": {
            "kind": "bandwidth_sample",
            "schema_version": 1,
            "sequence": sequence,
            "sample_time": iso(epoch_seconds),
            "instance_id": "payload-instance-must-not-win",
            "machine_id": "payload-machine-must-not-win",
            "interface": "eth0",
            "capture_mode": "total_only",
            "interval_milliseconds": 1000,
            "partial_interval": False,
            "counter_reset": False,
            "eth0": {
                "rx_bytes_total": 100000 + sequence * rx,
                "tx_bytes_total": 50000 + sequence * tx,
                "rx_bytes_delta": rx,
                "tx_bytes_delta": tx,
                "rx_bytes_per_second": rx,
                "tx_bytes_per_second": tx,
            },
            "applications": applications,
            "captured": {"rx_bytes": rx, "tx_bytes": tx},
            "unassigned": {"rx_bytes": 0, "tx_bytes": 0},
            "coverage_percent": 100.0,
        },
    }


def honeygain_event(epoch_seconds, event, instance="instance-a", machine="machine-a", attempt=1, exit_code=0):
    return {
        "time": iso(epoch_seconds),
        "receive_time": iso(epoch_seconds + 0.2),
        "resource": {
            "type": "container",
            "labels": {
                "organization_name": "org",
                "project_name": "default",
                "container_group_name": "honeygain-us-1",
                "container_group_version": "1",
                "instance_id": instance,
                "machine_id": machine,
            },
        },
        "json_log": {
            "kind": "honeygain_event",
            "schema_version": 1,
            "time": iso(epoch_seconds),
            "event": event,
            "client_version": "0.9.0",
            "attempt": attempt,
            "exit_code": exit_code,
        },
    }
class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "bandwidth.sqlite3")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_ingest_is_idempotent_and_resource_identity_is_authoritative(self):
        entry = log_entry(1_700_000_000, 1)
        self.assertTrue(self.store.ingest(entry))
        self.assertFalse(self.store.ingest(entry))

        status = self.store.status()
        self.assertEqual(status["sample_count"], 1)
        self.assertEqual(status["latest_instance_id"], "instance-a")
        self.assertNotIn("payload-instance", str(status))
        self.assertEqual(status["source"]["container_group"], "honeygain-us-1")
        self.assertEqual(status["source"]["version"], "1")

    def test_query_reconciles_totals_and_marks_reallocation(self):
        start = 1_700_000_000
        self.store.ingest(log_entry(start, 1, instance="instance-a", rx=100, tx=50))
        self.store.ingest(log_entry(start + 1, 2, instance="instance-a", rx=200, tx=70))
        self.store.ingest(log_entry(start + 2, 1, instance="instance-b", machine="machine-b", rx=300, tx=90))

        result = self.store.query_range(start * 1000, (start + 3) * 1000, 1)
        self.assertEqual(result["totals"]["eth0"], {"rx_bytes": 600, "tx_bytes": 210})
        self.assertEqual(result["totals"]["applications"]["packetstream"], {"rx_bytes": 600, "tx_bytes": 210})
        self.assertEqual(len(result["points"]), 3)
        self.assertEqual([m["instance_id"] for m in result["reallocations"]], ["instance-a", "instance-b"])

    def test_minute_rollup_survives_raw_retention_prune(self):
        old = 1_600_000_020
        self.store.ingest(log_entry(old, 1, rx=120, tx=60))
        self.store.ingest(log_entry(old + 1, 2, rx=180, tx=90))
        self.assertEqual(self.store.rollup(before_ms=(old + 60) * 1000), 2)
        self.assertEqual(self.store.prune(now_ms=(old + 31 * 86400) * 1000), 2)

        result = self.store.query_range(old * 1000, (old + 60) * 1000, 60)
        self.assertEqual(result["totals"]["eth0"], {"rx_bytes": 300, "tx_bytes": 150})
        self.assertEqual(result["points"][0]["sample_count"], 2)

    def test_range_edges_do_not_include_whole_overlapping_rollup_minutes(self):
        for second in range(90):
            self.store.ingest(log_entry(second, second + 1, rx=100, tx=0))
        self.store.rollup(before_ms=90_000)

        result = self.store.query_range(30_000, 90_000, 60)

        self.assertEqual(result["totals"]["eth0"], {"rx_bytes": 6000, "tx_bytes": 0})
        self.assertEqual([point["time_ms"] for point in result["points"]], [30_000])

    def test_unaligned_buckets_do_not_mix_whole_minute_rollups_with_partial_edges(self):
        for second in range(150):
            self.store.ingest(log_entry(second, second + 1, rx=100, tx=0))
        self.store.rollup(before_ms=150_000)

        result = self.store.query_range(30_000, 150_000, 60)

        self.assertEqual([point["time_ms"] for point in result["points"]], [30_000, 90_000])
        self.assertEqual([point["eth0"]["rx_bytes_per_second"] for point in result["points"]], [100, 100])

    def test_partial_late_minute_cannot_overwrite_complete_rollup(self):
        for second in range(60):
            self.store.ingest(log_entry(second, second + 1, rx=100, tx=0))
        self.store.rollup(before_ms=60_000)
        self.store.prune(now_ms=31 * 86400 * 1000)

        self.store.ingest(log_entry(30, 999, rx=999, tx=0))
        self.store.rollup(before_ms=60_000)
        result = self.store.query_range(0, 60_000, 60)

        self.assertEqual(result["totals"]["eth0"], {"rx_bytes": 6000, "tx_bytes": 0})

    def test_query_instances_reports_peak_slowdown_and_missing_samples_per_box(self):
        start = 100
        self.store.ingest(log_entry(start, 1, instance="instance-a", rx=100, tx=50))
        self.store.ingest(log_entry(start + 1, 2, instance="instance-a", rx=200, tx=50))
        self.store.ingest(log_entry(start + 2, 3, instance="instance-a", rx=50, tx=25))
        self.store.ingest(log_entry(start, 1, instance="instance-b", machine="machine-b", rx=10, tx=5))
        self.store.ingest(log_entry(start + 2, 3, instance="instance-b", machine="machine-b", rx=30, tx=15))

        result = self.store.query_boxes(start * 1000, (start + 3) * 1000)
        boxes = {box["instance_id"]: box for box in result["boxes"]}

        self.assertEqual(result["reporter_count"], 2)
        self.assertEqual(boxes["instance-a"]["sample_count"], 3)
        self.assertEqual(boxes["instance-a"]["expected_sample_count"], 3)
        self.assertEqual(boxes["instance-a"]["peak"]["bytes_per_second"], 250)
        self.assertEqual(boxes["instance-a"]["peak"]["time_ms"], (start + 1) * 1000)
        self.assertEqual(boxes["instance-a"]["latest"]["bytes_per_second"], 75)
        self.assertAlmostEqual(boxes["instance-a"]["observed_average"]["bytes_per_second"], 475 / 3)
        self.assertEqual(boxes["instance-a"]["slowdown_ratio"], 1.0)
        self.assertEqual(boxes["instance-a"]["honeygain"]["tcp_socket_count"], 1)
        self.assertEqual(boxes["instance-a"]["honeygain"]["tcp_established_count"], 1)
        self.assertEqual(boxes["instance-a"]["honeygain"]["udp_socket_count"], 1)
        self.assertEqual(
            boxes["instance-a"]["source"],
            {"organization": "org", "project": "default", "container_group": "honeygain-us-1", "version": "1"},
        )
        self.assertEqual(boxes["instance-b"]["expected_sample_count"], 3)
        self.assertEqual(boxes["instance-b"]["missing_sample_count"], 1)
        self.assertAlmostEqual(boxes["instance-b"]["completeness_percent"], 200 / 3)

    def test_native_disconnect_is_recorded_without_claiming_a_version(self):
        connected = honeygain_event(200, "connected")
        raw = {"time": iso(201), "resource": connected["resource"],
               "text_log": "Honeygain service disconnected"}
        self.assertTrue(self.store.ingest(connected))
        self.assertTrue(self.store.ingest(raw))
        self.assertFalse(self.store.ingest(raw))
        self.assertFalse(self.store.ingest(dict(raw, text_log="not Honeygain service disconnected")))
        result = self.store.query_events(199_000, 202_000)
        self.assertEqual([e["event"] for e in result["events"]], ["disconnected", "connected"])
        self.assertEqual(result["events"][0]["client_version"], "")
        self.assertEqual(result["events"][0]["instance_id"], "instance-a")

    def test_structured_disconnect_replaces_legacy_fallback_in_either_arrival_order(self):
        for index, raw_first in enumerate((True, False)):
            structured = honeygain_event(201, "disconnected", instance=f"instance-{index}")
            raw = {"time": iso(201.179), "resource": structured["resource"],
                   "text_log": "Honeygain service disconnected"}
            for entry in ([raw, structured] if raw_first else [structured, raw]):
                self.store.ingest(entry)
        result = self.store.query_events(200_000, 202_000)
        self.assertEqual(result["event_count"], 2)
        self.assertTrue(all(e["client_version"] == "0.9.0" for e in result["events"]))

    def test_honeygain_events_are_sanitized_deduplicated_and_queryable(self):
        connected = honeygain_event(200, "connected")
        overused = honeygain_event(201, "network_overused", instance="instance-b", machine="machine-b")
        device_limit = honeygain_event(201.5, "device_limit_exceeded", instance="instance-c", machine="machine-c")

        self.assertTrue(self.store.ingest(connected))
        self.assertFalse(self.store.ingest(connected))
        self.assertTrue(self.store.ingest(overused))
        self.assertTrue(self.store.ingest(device_limit))

        result = self.store.query_events(199_000, 202_000)
        self.assertEqual(result["event_count"], 3)
        self.assertEqual(result["counts"], {"connected": 1, "device_limit_exceeded": 1, "network_overused": 1})
        self.assertEqual(
            [event["event"] for event in result["events"]],
            ["device_limit_exceeded", "network_overused", "connected"],
        )
        self.assertEqual(result["events"][0]["client_version"], "0.9.0")
        self.assertNotIn("text_log", str(result))

    def test_sparse_application_payload_does_not_expand_unused_apps(self):
        entry = log_entry(250, 1)
        entry["json_log"]["applications"] = {"honeygain": entry["json_log"]["applications"]["honeygain"]}
        self.store.ingest(entry)

        result = self.store.query_range(250_000, 251_000, 1)
        self.assertEqual(set(result["latest_apps"]), {"honeygain"})

    def test_authorization_and_service_start_are_preserved_without_claiming_connection(self):
        self.assertTrue(self.store.ingest(honeygain_event(260, "authenticated")))
        self.assertTrue(self.store.ingest(honeygain_event(261, "service_starting")))
        result = self.store.query_events(259_000, 262_000)
        self.assertEqual(result["counts"], {"authenticated": 1, "service_starting": 1})
        self.assertNotIn("connected", result["counts"])

    def test_query_boxes_uses_one_complete_shared_fleet_second(self):
        self.store.ingest(log_entry(300.1, 1, instance="instance-a", rx=100, tx=50))
        self.store.ingest(log_entry(300.8, 1, instance="instance-b", machine="machine-b", rx=10, tx=5))
        self.store.ingest(log_entry(301, 2, instance="instance-a", rx=200, tx=50))

        result = self.store.query_boxes(300_000, 302_000, expected_reporters=2)
        boxes = {box["instance_id"]: box for box in result["boxes"]}

        self.assertEqual(result["fleet_snapshot_ms"], 300_000)
        self.assertEqual(result["snapshot_reporter_count"], 2)
        self.assertEqual(boxes["instance-a"]["snapshot"]["bytes_per_second"], 150)
        self.assertEqual(boxes["instance-b"]["snapshot"]["bytes_per_second"], 15)

    def test_query_boxes_tolerates_salad_log_delivery_lag_without_hiding_live_boxes(self):
        self.store.ingest(log_entry(100, 1, instance="instance-a", rx=100, tx=50))

        delayed_but_live = self.store.query_boxes(0, 145_000, expected_reporters=1)
        self.assertTrue(delayed_but_live["boxes"][0]["is_live"])

        genuinely_stale = self.store.query_boxes(0, 221_000, expected_reporters=1)
        self.assertFalse(genuinely_stale["boxes"][0]["is_live"])

    def test_query_boxes_start_profile_does_not_change_with_selected_window(self):
        self.store.ingest(log_entry(1, 1, rx=1000, tx=0))
        self.store.ingest(log_entry(601, 2, rx=100, tx=0))
        self.store.ingest(log_entry(602, 3, rx=100, tx=0))

        result = self.store.query_boxes(601_000, 603_000, expected_reporters=1)
        box = result["boxes"][0]

        self.assertEqual(box["first_seen_ms"], 1000)
        self.assertEqual(box["first_5m_average_bytes_per_second"], 1000)
        self.assertEqual(box["last_5m_average_bytes_per_second"], 100)
        self.assertEqual(box["slowdown_ratio"], 0.1)

    def test_exact_interval_bytes_are_separate_from_normalized_rate(self):
        entry = log_entry(700, 1, rx=100, tx=50)
        entry["json_log"]["interval_milliseconds"] = 2000
        entry["json_log"]["partial_interval"] = True
        entry["json_log"]["eth0"]["rx_bytes_delta"] = 200
        entry["json_log"]["eth0"]["tx_bytes_delta"] = 100
        self.store.ingest(entry)

        box = self.store.query_boxes(700_000, 701_000, expected_reporters=1)["boxes"][0]
        self.assertEqual(box["totals"], {"rx_bytes": 200, "tx_bytes": 100})
        self.assertEqual(box["snapshot"]["bytes_per_second"], 150)
        self.assertEqual(box["partial_interval_count"], 1)

    def test_query_boxes_combines_minute_summaries_with_raw_edges(self):
        for second in range(120):
            rate = 1000 if second == 10 else 100
            self.store.ingest(log_entry(second, second + 1, rx=rate, tx=0))
        self.store.raw_retention_days = 0
        self.store.prune(now_ms=60_000)

        box = self.store.query_boxes(0, 120_000, expected_reporters=1)["boxes"][0]

        self.assertEqual(box["sample_count"], 120)
        self.assertEqual(box["totals"], {"rx_bytes": 12_900, "tx_bytes": 0})
        self.assertAlmostEqual(box["observed_average"]["bytes_per_second"], 107.5)
        self.assertEqual(box["peak"], {"bytes_per_second": 1000, "time_ms": 10_000})
        self.assertEqual(box["first_5m_average_bytes_per_second"], 107.5)
        self.assertEqual(box["completeness_percent"], 100.0)


if __name__ == "__main__":
    unittest.main()
~~~~~~

### dashboard/tests/test_view_model.cjs

<!-- rebuild-file: dashboard/tests/test_view_model.cjs sha256=fa0b6ae89dbdfb420156cf5daf8239e529e715d067e25ee84526758cdc10c601 -->
~~~~~~text
const test = require('node:test');
const assert = require('node:assert/strict');
const {workerState,serviceModel,chartValue} = require('../static/fleet-test.js');
const worker = () => ({state:'running',client_status:'connected',network_bytes:1000000,received_age_ms:1000});
function snapshot() {return {experiment:{hg:{desired:10},ps:{desired:10}},recorder_stale:false,summary:{hg_network_mb:10,hg_gathering_credits:3,ps_network_mb:0,ps_credited_mb:0.005326},latest:{hg:{workers:Array.from({length:10},worker),status_stale:false,network_complete:true,provider_age_ms:1000},ps:{workers:[],network_complete:false,provider_age_ms:1000}}};}
test('ten fresh connected HG clients count as working independently of earnings',()=>{const s=snapshot();const m=serviceModel('hg',s);assert.equal(m.working,10);assert.equal(m.unknown,0);assert.equal(m.networkKnown,true);});
test('Salad running does not confirm a client',()=>{const s=snapshot();s.latest.hg.workers[0].client_status='exited';const m=serviceModel('hg',s);assert.equal(m.working,9);assert.equal(m.unknown,0);assert.equal(m.states[0].label,'Needs attention');});
test('stale or unverified clients are unknown, not working',()=>{for(const field of ['client','receipt','observer','recorder']){const s=snapshot();if(field==='client')s.latest.hg.workers[0].client_status='connected_last_observed_telemetry_unverified';if(field==='receipt')s.latest.hg.workers[0].received_age_ms=120001;if(field==='observer')s.latest.hg.status_stale=true;if(field==='recorder')s.recorder_stale=true;const m=serviceModel('hg',s);assert.ok(m.working<10);assert.ok(m.unknown>0);}});
test('missing inventory and incomplete zero traffic remain unknown',()=>{const m=serviceModel('ps',snapshot());assert.equal(m.workers.length,10);assert.equal(m.working,0);assert.equal(m.unknown,10);assert.equal(m.networkKnown,false);});
test('stale provider values are retained only as historical values',()=>{const s=snapshot();s.latest.ps.provider_age_ms=180001;const m=serviceModel('ps',s);assert.equal(m.earningsKnown,false);assert.equal(m.earnings,0.005326);});
test('a measured fresh zero is valid but absent readings are not zero',()=>{const s=snapshot();s.summary.hg_gathering_credits=0;assert.equal(serviceModel('hg',s).earningsKnown,true);s.summary.hg_gathering_credits=null;assert.equal(serviceModel('hg',s).earningsKnown,false);});
test('PacketStream acceptance and network sample freshness use separate clocks',()=>{const s=snapshot();const w={state:'running',client_status:'accepted',client_status_age_ms:1000,received_age_ms:20000,source_age_ms:1000,sample_source:'salad_logs_10s'};assert.equal(workerState('ps',w,s).working,true);assert.equal(workerState('ps',w,s).networkFresh,true);w.sample_source='gateway_1s';assert.equal(workerState('ps',w,s).networkFresh,false);w.client_status_age_ms=120001;assert.equal(workerState('ps',w,s).working,false);w.source_age_ms=65000;assert.equal(workerState('ps',w,s).networkFresh,false);});
test('an observer error cannot leave a client healthy',()=>{const s=snapshot();s.latest.hg.workers[0].error_code='observer_error';assert.equal(serviceModel('hg',s).working,9);});
test('chart does not turn missing/reset/incomplete zero into measured zero',()=>{assert.equal(chartValue({status:'missing',delta:null}),null);assert.equal(chartValue({status:'counter_reset',delta:4}),null);assert.equal(chartValue({status:'gap',delta:0}),null);assert.equal(chartValue({status:'gap',delta:4}),null);assert.equal(chartValue({status:'incomplete',delta:0}),null);assert.equal(chartValue({status:'complete',delta:0}),0);assert.equal(chartValue({status:'partial',delta:2}),2);});
test('native PacketStream heartbeat uses current census and the native event interval',()=>{const s=snapshot();s.latest.ps.status_age_ms=10000;const w={state:'running',client_status:'running',sample_source:'native_status_only',client_status_age_ms:180000};assert.equal(workerState('ps',w,s).working,true);s.latest.ps.status_age_ms=91000;assert.equal(workerState('ps',w,s).working,false);s.latest.ps.status_age_ms=10000;w.client_status_age_ms=240001;assert.equal(workerState('ps',w,s).working,false);});
test('restart boundary excludes old and straddling intervals in the display',()=>{const {windowStart,displayedIntervals}=require('../static/fleet-test.js');const s={experiment:{started_ms:1000},service_windows:{ps:{start_ms:10000,basis:'deployment_restart'}},timeline:{ps:{provider:[{start_ms:1000,end_ms:9000},{start_ms:9000,end_ms:11000},{start_ms:11000,end_ms:12000}]}}};assert.equal(windowStart('ps',s),10000);assert.deepEqual(displayedIntervals('ps','provider',s),[{start_ms:11000,end_ms:12000}]);});
test('a stale native error is unverified rather than a current failure',()=>{const s=snapshot();s.latest.ps.status_age_ms=10000;const w={state:'running',client_status:'error',error_code:'client_error',sample_source:'native_status_only',client_status_age_ms:300000};const v=workerState('ps',w,s);assert.equal(v.working,false);assert.equal(v.unknown,true);});
test('sysfs sampling keeps the independent native-client heartbeat window',()=>{const s=snapshot();s.latest.ps.status_age_ms=10000;const w={state:'running',client_status:'running',sample_source:'native_sysfs_1s',native_status_only:true,client_status_age_ms:180000,received_age_ms:30000,source_age_ms:40000};const v=workerState('ps',w,s);assert.equal(v.working,true);assert.equal(v.networkFresh,true);w.source_age_ms=61000;assert.equal(workerState('ps',w,s).networkFresh,false);});

const unified = require('../static/fleet-test.js');
test('unified services use hashes and provide six, twelve and twenty-four hour windows', () => {
  assert.equal(unified.SERVICES.length, 6);
  assert.ok(unified.SERVICES.every(s=>s.hash.startsWith('#')));
  for(const hours of [6,12,24]){
    const bars=unified.periodMinutes([{minute_ms:1800000000000,mb:0}],hours,1800000000010);
    assert.equal(bars.length,hours*60);
    assert.equal(bars.at(-1).mb,0);
    assert.equal(bars[0].mb,null);
  }
});
test('network bytes do not become invented earnings', () => {
  const model=unified.normalize('rp',{generated_ms:1000,desired:10,workers:[],minutes:[],total_network_mb:500},1000);
  assert.equal(model.total,500);
  assert.equal(model.earned,'Not reported');
});
test('ProxyRack parser failure makes working clients unverified', () => {
  const model=unified.normalize('proxyrack',{generated_ms:1000,requested:10,cloud_error:'timestamp parse failed',workers:[{name:'one',provider_online:true,provider_status:'Online: 192.0.2.1',provider_age_ms:0,sample_age_ms:0,mb_per_minute:3}],minutes:[]},1000);
  assert.equal(model.working,null);
  assert.equal(model.nodes[0].status,'Unverified');
  assert.equal(model.nodes[0].rate,null);
});
test('TM provider credits remain separate from network totals', () => {
  const model=unified.normalize('tm',{generated_ms:1000,recorded:{rx:60000000,tx:40000000},deployment:{desired_replicas:10},workers:[],minutes:[],credited:{credited_bytes:25000000,credited_usd:0.0025,fresh:true},errors:{}},1000);
  assert.equal(model.total,100);
  assert.equal(model.credited,'25 MB');
  assert.equal(model.earned,'$0.0025');
});
~~~~~~

### dashboard/traffmonetizer.py

<!-- rebuild-file: dashboard/traffmonetizer.py sha256=7ec44b146c1b3e3ea5466f336488489744a2b92bdab300808e5da31a7ef31396 -->
~~~~~~python
"""Read the TraffMonetizer observer snapshot for the shared dashboard."""
import json
from pathlib import Path
import time


def snapshot():
    path = Path.home() / ".hg1/traffmonetizer/latest.json"
    if not path.exists():
        return {"provider": "traffmonetizer", "workers": [], "minutes": [], "errors": {"recorder": "Recorder has not published a reading yet"}}
    data = json.loads(path.read_text())
    now = int(time.time() * 1000)
    age = now - data["generated_ms"]
    data["snapshot_age_ms"] = age
    data["stale"] = age > 45000
    for worker in data.get("workers", []):
        sample_age = now - worker["time_ms"] if worker.get("time_ms") is not None else None
        worker["sample_age_ms"] = sample_age
        worker["fresh"] = not data["stale"] and sample_age is not None and -5000 <= sample_age <= 45000
        worker["working"] = bool(worker["fresh"] and worker.get("state") == "connected" and worker.get("salad_state") == "running" and not data.get("errors", {}).get("recorder"))
    data["working"] = None if data["stale"] else sum(worker["working"] for worker in data.get("workers", []))
    return data
~~~~~~

### fleet-test-recorder.py

<!-- rebuild-file: fleet-test-recorder.py sha256=a82594851df4c0ea52daadb1d751ebcd13ac47954e6fa0913933a0174a43bd24 -->
~~~~~~python
#!/usr/bin/env python3
"""Record independent Salad tests; provider credits never derive from network bytes."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import math
import os
import re
from pathlib import Path
import shutil
import signal
import time
import urllib.request

DATA = Path(os.environ.get('FLEET_TEST_DIR', str(Path.home() / '.hg1/fleet-tests')))
HG_DATA = Path(os.environ.get('HG_FLEET_DIR', str(Path.home() / '.hg1/hg-fleet')))
PS_DATA = Path.home() / '.hg1/packetstream'


def stamp(ms=None):
    return datetime.fromtimestamp((ms or time.time()*1000)/1000, timezone.utc).isoformat()


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default if default is not None else {}


def atomic(path, value):
    temp = Path(str(path) + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def last_provider():
    try:
        rows = (PS_DATA / 'provider-observations.jsonl').read_text().splitlines()
    except OSError:
        return None
    for line in reversed(rows):
        try:
            r = json.loads(line)
            if not isinstance(r.get('provider_bytes'), int):
                continue
            dt = datetime.fromisoformat((r.get('observed_at') or r['recorded_at']).replace('Z', '+00:00'))
            return {'bytes': r['provider_bytes'], 'time_ms': int(dt.timestamp()*1000)}
        except (KeyError, ValueError, TypeError):
            continue
    return None


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            return json.load(response)
    except Exception:
        return {}


def moved(n):
    if isinstance(n.get('rx_moved_bytes'), int) and isinstance(n.get('tx_moved_bytes'), int):
        return n['rx_moved_bytes'], n['tx_moved_bytes']
    # No conversion from a rounded MB display: wait for the repaired collector.
    return None


def exact_counter(value):
    # Salad serializes structured log numbers as doubles, including integer counters.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value) if math.isfinite(value) and 0 <= value <= 2**53 and int(value) == value else None


def accumulate(network, nodes):
    """Sum observed per-run increments, never add a replacement's lifetime baseline."""
    resets = []
    for n in nodes:
        counters = moved(n)
        if counters is None:
            continue
        key = n['run']
        old = network['last'].get(key)
        if old is not None:
            if counters[0] >= old[0] and counters[1] >= old[1]:
                network['rx'] += counters[0]-old[0]
                network['tx'] += counters[1]-old[1]
            else:
                resets.append(key)
        network['last'][key] = list(counters)
    return resets


def inventory_changes(state, result):
    events=[]
    previous=state.get('inventory')
    current={}
    for service in ['ps','hg']:
        for worker in result[service]['workers']:
            identity=worker.get('group') if service=='hg' else worker.get('machine')
            if not identity:continue
            key=service+'/'+identity
            current[key]={k:worker.get(k) for k in ['machine','ip','client_status']}
            old=previous.get(key) if previous is not None else None
            if old:
                for field in ['machine','ip','client_status']:
                    if old.get(field) is not None and current[key].get(field) is not None and old[field]!=current[key][field]:
                        events.append({'time_ms':result['time_ms'],'service':service,'worker':identity,
                                       'action':field+'_changed','previous':old[field],'value':current[key][field]})
            elif previous is not None:
                events.append({'time_ms':result['time_ms'],'service':service,'worker':identity,'action':'worker_appeared'})
    if previous is not None:
        for key in previous.keys()-current.keys():
            service,identity=key.split('/',1)
            events.append({'time_ms':result['time_ms'],'service':service,'worker':identity,'action':'worker_not_observed'})
    state['inventory']=current
    return events


def observation(current, network):
    raw = get('http://127.0.0.1:8789/api/ps1/status')
    view = get('http://127.0.0.1:8787/api/ps1/view')
    now = int(time.time()*1000)
    target=current.get('ps',{})
    target_path='/'.join([target.get('organization','hyperlane'),target.get('project','default'),target.get('group','ps1')])
    census=read(PS_DATA/'native-census.json')
    plain=False
    try:
        census_ms=int(datetime.fromisoformat((census.get('last_success_at') or census.get('checked_at','')).replace('Z','+00:00')).timestamp()*1000)
        plain=census.get('group')==target_path and 0<=now-census_ms<180000
    except (ValueError,TypeError):
        census_ms=0
    if plain:
        entries=[]
        for row in census.get('nodes',[]):
            client=row.get('client_status') or {}
            net=row.get('network') or {}
            try:status_age=now-int(datetime.fromisoformat(client.get('source_time','').replace('Z','+00:00')).timestamp()*1000)
            except (ValueError,TypeError):status_age=None
            entry={'machine':row['machine'],'run':row['machine']+'/'+row['instance_id']+'/'+str(net.get('observer','status')),
                'deployment_current':True,'salad_state':row.get('salad_state'),'client_status':client,
                'client_status_age_ms':status_age,'ip':row.get('ip'),'sample_source':'native_status_only'}
            if net.get('available') and isinstance(net.get('observed_rx_bytes'),int) and isinstance(net.get('observed_tx_bytes'),int):
                entry.update(rx_moved_bytes=net['observed_rx_bytes'],tx_moved_bytes=net['observed_tx_bytes'],
                    sample_age_ms=now-net['received_ms'],source_sample_age_ms=now-net['time_ms'],
                    sample_source='native_minutes',source_granularity_seconds=60,
                    last_interval_seconds=net.get('last_interval_seconds'))
            entries.append(entry)
        raw={'nodes':entries,'accepted_nodes':sum((r.get('client_status')or{}).get('state')=='running' and
                r.get('client_status_age_ms') is not None and -15000<=r['client_status_age_ms']<=600000 for r in entries),
             'connected_machines':[],'deployment_membership_age_ms':now-census_ms}
        view['running_nodes']=sum(r.get('salad_state')=='running' for r in entries)
    membership = {n['machine']: n for n in view.get('nodes', []) if n.get('current')}
    if any('deployment_current' in n for n in raw.get('nodes', [])):
        nodes = [n for n in raw['nodes'] if n.get('deployment_current')]
    else:
        nodes = [n for n in raw.get('nodes', []) if n.get('current') and n.get('machine') in membership]
    workers = []
    for n in nodes:
        client = n.get('client_status') or {}
        if not isinstance(client, dict):
            client = {'state': str(client)}
        counters = moved(n)
        workers.append({'machine': n['machine'], 'run': n['run'], 'ip': n.get('ip'),
                        'state': n.get('salad_state') or membership.get(n['machine'], {}).get('state'),
                        'client_status': client.get('state', 'unknown'),
                        'client_status_age_ms': n.get('client_status_age_ms'),
                        'error': client.get('message') if client.get('state') == 'error' else None,
                        'network_bytes': sum(counters) if counters else None,
                        'received_age_ms': n.get('sample_age_ms'),
                        'source_age_ms': n.get('source_sample_age_ms'),
                        'sample_source':n.get('sample_source'),
                        'source_granularity_seconds':n.get('source_granularity_seconds'),
                        'last_interval_seconds':n.get('last_interval_seconds')})
    resets = accumulate(network, nodes)
    provider = last_provider()
    fresh = [n for n in workers if isinstance(n.get('received_age_ms'), (int,float)) and
             0 <= n['received_age_ms'] <= (150000 if n.get('sample_source')=='native_minutes' else 45000 if n.get('sample_source')=='sysfs_via_salad_logs_1s' else
                                         25000 if n.get('sample_source')=='salad_logs_10s' else 15000)]
    membership_age = raw.get('deployment_membership_age_ms', view.get('membership_age_ms'))
    complete = len(fresh) == 10 and len(workers) == 10 and all(n['network_bytes'] is not None for n in workers)
    complete = complete and membership_age is not None and membership_age < 45000 and not resets
    complete = complete and all(isinstance(n['source_age_ms'],(int,float)) and -15000<=n['source_age_ms']<=60000 for n in workers)
    hg = read(HG_DATA / 'status.json')
    hg_workers = []
    hg_samples = []
    for w in hg.get('workers', []):
        safe = {k:w.get(k) for k in ['group','device','machine','ip','state','client_status','credits','credit_observed_ms','error']}
        sample=w.get('sample') or {}
        safe['run']=w.get('instance')
        sample_time=re.sub(r'\.(\d+)(?=[+-])', lambda m: '.'+m.group(1)[:6].ljust(6,'0'), sample.get('time','').replace('Z','+00:00'))
        safe['sample_ms']=int(datetime.fromisoformat(sample_time).timestamp()*1000) if sample_time else None
        rx,tx=exact_counter(sample.get('rx_total')),exact_counter(sample.get('tx_total'))
        safe['network_bytes']=rx+tx if isinstance(rx,int) and isinstance(tx,int) else None
        safe['received_age_ms']=hg['time_ms']-safe['sample_ms'] if safe['sample_ms'] is not None else None
        hg_workers.append(safe)
        if safe['network_bytes'] is not None and w.get('instance'):
            hg_samples.append({'run':w['group']+'/'+w['instance'],'rx_moved_bytes':rx,'tx_moved_bytes':tx})
    hg_network=network.setdefault('hg',{'rx':0,'tx':0,'last':{}})
    hg_resets=accumulate(hg_network,hg_samples)
    hg_complete=len(hg_workers)==10 and len(hg_samples)==10 and not hg_resets
    hg_complete=hg_complete and all(isinstance(w['received_age_ms'],(int,float)) and 0<=w['received_age_ms']<=120000 for w in hg_workers)
    hg_complete=hg_complete and isinstance(hg.get('time_ms'),(int,float)) and now-hg['time_ms']<120000
    result = {'recorded_at': stamp(now), 'time_ms': now, 'experiment_id': current['id'], 'phase': current.get('phase'),
              'ps': {'running': view.get('running_nodes'), 'reporting': len(fresh),
                     'desired': 10, 'accepted': raw.get('accepted_nodes'),
                     'monitor_connections': len(raw.get('connected_machines', [])),
                     'provider_bytes': provider['bytes'] if provider else None,
                     'provider_observed_ms': provider['time_ms'] if provider else None,
                     'network_rx_bytes': network['rx'] if network['last'] else None,
                     'network_tx_bytes': network['tx'] if network['last'] else None,
                     'network_total_bytes': network['rx']+network['tx'] if network['last'] else None, 'network_complete': bool(complete),
                     'network_observed_ms': census_ms if plain and network['last'] else now if raw and not plain else None, 'counter_resets': resets,
                     'status_observed_ms':census_ms if plain else now if raw else None,
                     'group_started_at':census.get('group_state',{}).get('start_time') if plain else None,
                     'workers': workers},
              'hg': {'running': hg.get('running'), 'connected': hg.get('connected'), 'desired': 10,
                     'provider_gathering_credits': hg.get('provider_gathering_credits'),
                     'provider_observed_ms': hg.get('provider_observed_ms'),
                     'status_observed_ms': hg.get('time_ms'),
                     'network_rx_bytes':hg_network['rx'],'network_tx_bytes':hg_network['tx'],
                     'network_total_bytes':hg_network['rx']+hg_network['tx'],
                     'network_complete':bool(hg_complete),'network_observed_ms':hg.get('time_ms'),
                     'workers': hg_workers}}
    result['events']=inventory_changes(network,result)
    return result


def start_new(phase):
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    old = read(DATA/'current.json')
    now = int(time.time()*1000)
    ident = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    archive = DATA/'archives'/(old.get('id') or 'pre-fleet-'+ident)
    archive.mkdir(parents=True, exist_ok=True, mode=0o700)
    if old:
        for filename in ['current.json','observations.jsonl','network-state.json','latest.json','events.jsonl']:
            source=DATA/filename
            if source.exists():
                shutil.copy2(source, archive/filename)
    else:
        # Preserve the exact earlier credited ledger. Existing raw network log remains append-only.
        if (PS_DATA/'provider-observations.jsonl').exists():
            shutil.copy2(PS_DATA/'provider-observations.jsonl', archive/'provider-observations.jsonl')
        atomic(archive/'legacy-sources.json', {'archived_at':stamp(now), 'network_log':str(PS_DATA/'network/samples.jsonl'),
               'network_size_bytes':(PS_DATA/'network/samples.jsonl').stat().st_size if (PS_DATA/'network/samples.jsonl').exists() else None})
    provider = last_provider()
    hg_provider = read(HG_DATA/'provider-latest.json')
    value = {'id':ident, 'started_at':stamp(now), 'started_ms':now, 'status':'preparing' if phase=='repair' else 'measuring',
             'phase':phase, 'ps':{'organization':'hyperlane','group':'ps1','desired':10,
               'baseline_provider_bytes':provider['bytes'] if provider else None,
               'baseline_provider_observed_ms':provider['time_ms'] if provider else None,
               'estimated_fleet_cost_usd_per_hour':0.05,'cost_basis':'Previously quoted estimate; invoice unverified'},
             'hg':{'organization':'deathadder','desired':10,'version':'0.6.6',
                   'baseline_provider_gathering_credits':hg_provider.get('gathering_credits'),
                   'baseline_provider_observed_ms':hg_provider.get('observed_ms'),
                   'baseline_started_ms':hg_provider.get('observed_ms'),
                   'phase':phase},
             'interventions':[], 'archive_path':str(archive),
             'measurement_note':'Network totals are observed per-run increments. Provider totals are account-level. Missing samples are not zero traffic.'}
    (DATA/'observations.jsonl').write_text('')
    (DATA/'events.jsonl').write_text('')
    atomic(DATA/'network-state.json', {'experiment_id':ident,'rx':0,'tx':0,'last':{}})
    atomic(DATA/'current.json', value)
    return value


def run(once=False):
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock=(DATA/'recorder.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    stopping = False
    def stop(_sig,_frame):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    while not stopping:
        current=read(DATA/'current.json')
        if not current:
            raise RuntimeError('Start a test before starting recorder')
        network=read(DATA/'network-state.json')
        if network.get('experiment_id')!=current['id']:
            network={'experiment_id':current['id'],'rx':0,'tx':0,'last':{}}
        record=observation(current,network)
        atomic(DATA/'network-state.json',network)
        with (DATA/'observations.jsonl').open('a') as out:
            out.write(json.dumps(record,separators=(',',':'))+'\n');out.flush()
        if record.get('events'):
            with (DATA/'events.jsonl').open('a') as out:
                for event in record['events']:out.write(json.dumps(event)+'\n')
        atomic(DATA/'latest.json',record)
        if once:
            print(json.dumps({'at':record['recorded_at'],'ps_running':record['ps']['running'],'ps_reporting':record['ps']['reporting'],
                              'hg_running':record['hg']['running'],'hg_connected':record['hg']['connected']}));return
        for _ in range(10):
            if stopping:break
            time.sleep(1)


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start-new','run','once','mark'])
    parser.add_argument('--phase',default='repair')
    parser.add_argument('--reason',default='')
    args=parser.parse_args()
    if args.action=='start-new':
        # Prevent archive/reset racing an active writer. Stop the launchd job first.
        DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
        lock=(DATA/'recorder.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        print(json.dumps(start_new(args.phase),indent=2))
    elif args.action=='mark':
        current=read(DATA/'current.json');current['phase']=args.phase
        current['interventions'].append({'time_ms':int(time.time()*1000),'reason':args.reason,'phase':args.phase,
                                         'service':'fleet','action':args.phase})
        atomic(DATA/'current.json',current)
    else:run(args.action=='once')


if __name__=='__main__':
    main()
~~~~~~

### packetstream-monitor/audit-client-status.py

<!-- rebuild-file: packetstream-monitor/audit-client-status.py sha256=dedb9113f45026be32a9a8e80d74da971e31ef3b462a3e6d55766ac8abab46b4 -->
~~~~~~python
#!/usr/bin/env python3
"""Read-only native-status census for PS1; never treat absent logs as failure."""
import concurrent.futures
from datetime import datetime, timedelta, timezone
import getpass
import json
import os
from pathlib import Path
import re
import subprocess


def collect():
    root = Path(__file__).resolve().parents[1]
    key = subprocess.check_output([str(root / ".runtime/keychain-store"), "--read", "--service",
                                   "salad-bandwidth-api", "--account", getpass.getuser()], text=True).strip()
    base = "https://api.salad.com/api/public/organizations/hyperlane"
    group = os.environ.get("PS_GROUP", "ps1")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,61}[a-z0-9]", group):
        raise ValueError("Invalid PacketStream group name")
    now = datetime.now(timezone.utc)

    def api(path, body=None):
        cfg = "header = " + json.dumps("Salad-Api-Key: " + key) + '\nheader = "Content-Type: application/json"\n'
        if body is not None:
            cfg += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
        result = subprocess.run(["curl", "-sS", "--max-time", "20", "--config", "-", "--write-out",
                                 "\n%{http_code}", base + path], input=cfg, text=True, capture_output=True, timeout=25)
        raw, code = result.stdout.rsplit("\n", 1)
        if result.returncode or code != "200":
            raise RuntimeError("Salad read failed HTTP " + code)
        return json.loads(raw)

    deployment = api("/projects/default/containers/" + group)
    expected_id = os.environ.get("PS_EXPECTED_GROUP_ID")
    if expected_id and deployment["id"] != expected_id:
        raise RuntimeError("PacketStream deployment identity changed")
    instances = api("/projects/default/containers/" + group + "/instances")["instances"]

    def one(instance):
        query = ('resource.type = "container" and resource.labels.container_group_name = "' + group + '" and '
                 'resource.labels.machine_id = "' + instance["machine_id"] + '" and text_log contains "Status:"')
        body = {"query": query, "start_time": (now-timedelta(minutes=10)).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "end_time": now.isoformat(timespec="milliseconds").replace("+00:00", "Z"), "page_size": 100, "sort_order": "desc"}
        row = {"machine": instance["machine_id"], "instance_id": instance["id"], "salad_state": instance["state"],
               "salad_ready": instance.get("ready"), "version": instance["version"], "client_status": None}
        try:
            result = api("/log-entries", body)
            statuses = []
            for item in result.get("items", []):
                text = item.get("text_log", "")
                embedded = re.match(r'PS_NATIVE instance=([^ ]+) ', text)
                recorded_instance = embedded.group(1) if embedded else item.get("resource", {}).get("labels", {}).get("instance_id")
                if recorded_instance != instance["id"]:
                    continue
                match = re.search(r'time="([^" ]+)".*msg="(Status: [^"]+)"', text)
                if match:
                    statuses.append((match.group(1), item.get("time", ""), match.group(2)))
            if statuses:
                at, indexed_at, message = max(statuses)
                state = "running" if message == "Status: PacketStream is running" else "error" if "error" in message.lower() else "unknown"
                row["client_status"] = {"state": state, "message": message, "source_time": at, "indexed_at": indexed_at,
                                         "source": "Salad native client logs; exact current instance"}
            row["returned_log_records"] = len(result.get("items", []))
        except (RuntimeError, subprocess.TimeoutExpired, ValueError):
            row["query_failed"] = True
        return row

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(one, instances))
    for row in rows:
        status = row.get("client_status")
        row["client_status_age_seconds"] = None
        if status:
            row["client_status_age_seconds"] = (now-datetime.fromisoformat(status["source_time"].replace("Z", "+00:00"))).total_seconds()
    result = {"schema_version": 1, "checked_at": now.isoformat(), "group": "hyperlane/default/" + group,
              "group_id": deployment["id"], "group_state": deployment["current_state"], "desired_replicas": deployment["replicas"], "nodes": rows,
              "running_instances": sum(row["salad_state"] == "running" for row in rows),
              "ready_instances": sum(bool(row["salad_ready"]) for row in rows),
              "accepted_clients": sum(row.get("client_status", {}).get("state") == "running" and row["client_status_age_seconds"] is not None and -10 <= row["client_status_age_seconds"] < 600 for row in rows if row.get("client_status")),
              "network_available": False, "network_note": "Plain official client has no network-counter exporter; missing network values are not zero traffic.",
              "limitations": "Up to 100 latest indexed logs per current instance over ten minutes. Missing status is unknown, not zero traffic or rejected."}
    return result


def main():
    root = Path(__file__).resolve().parents[1]
    result = collect()
    path = root / ".runtime/ps1-monitor/independent-test/client-census-latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
~~~~~~

### packetstream-monitor/native-census.py

<!-- rebuild-file: packetstream-monitor/native-census.py sha256=400b1d22f26fab942eaf503940b94f4fdac1bf8c3b75a3d5ead12302ca5e16f8 -->
~~~~~~python
#!/usr/bin/env python3
"""Continuously record native PS client acceptance without changing cloud clients."""
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import time


def main():
    source = Path(__file__).with_name("audit-client-status.py")
    spec = importlib.util.spec_from_file_location("ps_native_audit", source)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    network_spec = importlib.util.spec_from_file_location("ps_native_network", Path(__file__).with_name("native-network.py"))
    network_module = importlib.util.module_from_spec(network_spec)
    network_spec.loader.exec_module(network_module)
    network = network_module.NetworkObserver(Path(__file__).resolve().parents[1], os.environ["PS_GROUP"], os.environ["PS_EXPECTED_GROUP_ID"])
    target = Path.home()/".hg1/packetstream/native-census.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    last = {}
    while True:
        started = time.monotonic()
        try:
            result = audit.collect()
            network.update_members(result["nodes"])
            measurements = network.snapshots()
            for node in result["nodes"]:
                node["network"] = measurements.get(node["instance_id"], {"available": False, "reason": "Waiting for the first minute record"})
                node["ip"] = node["network"].get("ip")
            result["network_available"] = any(node["network"]["available"] for node in result["nodes"])
            result["network_note"] = "Minute records from each container are saved in minutes.sqlite3. Missing records are not zero traffic."
            result["last_success_at"] = result["checked_at"]
            result["poll_interval_seconds"] = 30
            last = result
        except Exception as error:
            result = dict(last, poll_error=type(error).__name__,
                          poll_failed_at=datetime.now(timezone.utc).isoformat(),
                          network_available=False)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, indent=2))
        os.replace(temporary, target)
        time.sleep(max(1, 30-(time.monotonic()-started)))


if __name__ == "__main__":
    main()
~~~~~~

### packetstream-monitor/native-network.py

<!-- rebuild-file: packetstream-monitor/native-network.py sha256=6c656033e0ca0121885da58a740f3df5fe614e5ed5af776037d6bd6e046e9f7c -->
~~~~~~python
"""Collect complete minute records from Salad logs, including replaced instances."""
from datetime import datetime, timedelta, timezone
import getpass
import json
from pathlib import Path
import re
import subprocess
import threading
import time

from dashboard.native_network import NetworkMinutes, parse_minute


def provider_datetime(value):
    value = re.sub(r"\.(\d+)(?=Z$|[+-]\d\d:\d\d$)", lambda m: "." + (m[1] + "000000")[:6], value)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class NetworkObserver:
    def __init__(self, app_root, group, group_id, data_dir=None):
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,61}[a-z0-9]", group):
            raise ValueError("Invalid PacketStream group")
        self.group, self.group_id = group, group_id
        self.key = subprocess.check_output(
            [str(app_root / ".runtime/keychain-store"), "--read", "--service",
             "salad-bandwidth-api", "--account", getpass.getuser()], text=True).strip()
        self.store = NetworkMinutes((data_dir or Path.home() / ".hg1/packetstream") / "minutes.sqlite3")
        self.members = []
        self.lock = threading.Lock()
        threading.Thread(target=self.run, daemon=True).start()

    def request(self, path, body=None):
        config = "header = " + json.dumps("Salad-Api-Key: " + self.key) + '\nheader = "Content-Type: application/json"\n'
        if body is not None:
            config += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
        response = subprocess.run(
            ["curl", "-sS", "--max-time", "20", "--config", "-", "--write-out", "\n%{http_code}",
             "https://api.salad.com/api/public/organizations/hyperlane" + path],
            input=config, text=True, capture_output=True, timeout=25)
        raw, code = response.stdout.rsplit("\n", 1)
        if response.returncode or code != "200":
            raise RuntimeError("Salad log request HTTP " + code)
        return json.loads(raw)

    def update_members(self, nodes):
        with self.lock:
            self.members = [node["instance_id"] for node in nodes]

    def snapshots(self):
        now = int(time.time() * 1000)
        latest = self.store.latest(self.group_id)
        with self.lock:
            members = list(self.members)
        result = {}
        for instance in members:
            row = latest.get(instance)
            if not row or not row["valid"]:
                continue
            seconds = (row["end_ms"] - row["start_ms"]) / 1000
            result[instance] = {
                "available": True, "source": "sysfs-minute-via-salad-logs",
                "observer": row["observer"], "time_ms": row["end_ms"], "received_ms": row["received_ms"],
                "ip": row["ip"], "observed_rx_bytes": row["total_rx"], "observed_tx_bytes": row["total_tx"],
                "observed_total_bytes": row["total_rx"] + row["total_tx"],
                "source_age_seconds": (now - row["end_ms"]) / 1000,
                "receipt_age_seconds": (now - row["received_ms"]) / 1000,
                "last_interval_seconds": seconds, "last_delta_bytes": row["rx"] + row["tx"],
                "bytes_per_second": (row["rx"] + row["tx"]) / seconds if seconds > 0 else None,
                "nominal_interval_ms": 60000, "samples": row["seq"] + 1}
        return result

    def poll(self):
        group = self.request("/projects/default/containers/" + self.group)
        if group.get("id") != self.group_id:
            raise RuntimeError("PacketStream deployment identity changed")
        now = datetime.now(timezone.utc)
        saved = self.store.collector_status(self.group_id)
        cursor = provider_datetime(saved["cursor"]) if saved.get("cursor") else now
        start = min(cursor, now) - timedelta(minutes=10)
        calls = 0

        def fetch(begin, end):
            nonlocal calls
            calls += 1
            if calls > 512:
                raise RuntimeError("Minute log catch-up has too many pages")
            body = {
                "query": 'resource.type = "container" and resource.labels.project_name = "default" and '
                         'resource.labels.container_group_name = "' + self.group + '" and text_log startswith "PS_MINUTE_V"',
                "start_time": begin.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "end_time": end.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "page_size": 100, "sort_order": "asc"}
            items = self.request("/log-entries", body).get("items")
            if not isinstance(items, list):
                raise RuntimeError("Invalid Salad log response")
            if len(items) < 100:
                return items
            if end - begin <= timedelta(milliseconds=1):
                raise RuntimeError("Too many minute records share a pagination timestamp")
            middle = begin + (end - begin) / 2
            return fetch(begin, middle) + fetch(middle, end)

        items = fetch(start, now)
        records = [parse_minute(item, self.group_id) for item in items]
        invalid = sum(row is None for row in records)
        inserted = self.store.ingest([row for row in records if row is not None])
        self.store.collector_status(self.group_id, now.isoformat(),
                                    "Invalid minute records: " + str(invalid) if invalid else None, inserted)

    def lookup_countries(self):
        with self.store.lock:
            ips = [r[0] for r in self.store.db.execute(
                "SELECT DISTINCT ip FROM minutes WHERE ip IS NOT NULL AND ip NOT IN (SELECT ip FROM countries) LIMIT 100")]
        if not ips:
            return
        response = subprocess.run(["curl", "-fsS", "--max-time", "8", "-H", "Content-Type: application/json",
                                   "--data-binary", "@-", "https://api.country.is/"],
                                  input=json.dumps(ips), text=True, capture_output=True, timeout=10)
        if response.returncode:
            return
        countries = json.loads(response.stdout)
        with self.store.lock, self.store.db:
            for row in countries:
                country = row.get("country")
                if row.get("ip") in ips and (country is None or re.fullmatch(r"[A-Z]{2}", country)):
                    self.store.db.execute("INSERT OR REPLACE INTO countries VALUES (?,?)", (row["ip"], country))

    def run(self):
        while True:
            began = time.monotonic()
            try:
                self.poll()
                self.lookup_countries()
            except Exception as error:
                saved = self.store.collector_status(self.group_id)
                cursor = saved.get("cursor") or datetime.now(timezone.utc).isoformat()
                message = str(error) if isinstance(error, RuntimeError) else type(error).__name__
                self.store.collector_status(self.group_id, cursor, message)
                print("PS minute recording failed:", message, flush=True)
            time.sleep(max(1, 15 - (time.monotonic() - began)))
~~~~~~

### packetstream-monitor/start-with-recovery.sh

<!-- rebuild-file: packetstream-monitor/start-with-recovery.sh sha256=a1352f21f52114bfdb716894303b29dc2d7cff1f9893950904716c1dd5ee2dbf -->
~~~~~~bash
#!/bin/bash
set -u
ps_client_pid=""
ps_final=0
ps_state=starting
ps_error=none
record_minute() {
  [[ -n "${ps_started_ms:-}" && -n "${ps_sequence+x}" ]] || return
  local ps_now_ms ps_rx ps_tx
  ps_now_ms="$(date +%s)000"
  read -r ps_rx </sys/class/net/eth0/statistics/rx_bytes || return
  read -r ps_tx </sys/class/net/eth0/statistics/tx_bytes || return
  printf 'PS_MINUTE_V2 instance=%s machine=%s observer=%s seq=%s start_ms=%s end_ms=%s rx=%s tx=%s total_rx=%s total_tx=%s ip=%s state=%s error=%s final=%s bucket_ms=%s\n' \
    "${SALAD_INSTANCE_ID:-local}" "${SALAD_MACHINE_ID:-local}" "$ps_started_ms" "$ps_sequence" "$ps_previous_ms" "$ps_now_ms" \
    "$((ps_rx-ps_previous_rx))" "$((ps_tx-ps_previous_tx))" "$((ps_rx-ps_base_rx))" "$((ps_tx-ps_base_tx))" "$ps_ip" "$ps_state" "$ps_error" "$1" "$ps_bucket_ms"
  ps_previous_rx=$ps_rx; ps_previous_tx=$ps_tx; ps_previous_ms=$ps_now_ms
  ps_sequence=$((ps_sequence+1))
  ps_bucket_ms=$((ps_now_ms / 60000 * 60000))
}
stop_client() {
  (( ps_final == 0 )) || return
  ps_final=1
  if [[ -n "$ps_client_pid" ]]; then
    kill "$ps_client_pid" 2>/dev/null || true
    sleep 1
    kill -KILL "$ps_client_pid" 2>/dev/null || true
    wait "$ps_client_pid" 2>/dev/null || true
  fi
  record_minute 1
}
trap 'stop_client; exit 0' TERM INT
ps_ip=$(/usr/bin/timeout 6 /usr/bin/perl -MIO::Socket::INET -e '
  alarm 5; my $s=IO::Socket::INET->new(PeerAddr=>"api.ipify.org",PeerPort=>80,Proto=>"tcp",Timeout=>3) or exit;
  print $s "GET / HTTP/1.0\r\nHost: api.ipify.org\r\nConnection: close\r\n\r\n";
  local $/; my $r=<$s>; $r=~s/^.*?\r\n\r\n//s; $r=~s/\s+//g;
  print $r if $r=~/^\d{1,3}(?:\.\d{1,3}){3}$/;
' 2>/dev/null) || ps_ip=''
[[ -n "$ps_ip" ]] || ps_ip='-'
ps_started_ms="$(date +%s)000"
read -r ps_base_rx </sys/class/net/eth0/statistics/rx_bytes
read -r ps_base_tx </sys/class/net/eth0/statistics/tx_bytes
ps_previous_rx=$ps_base_rx; ps_previous_tx=$ps_base_tx; ps_previous_ms=$ps_started_ms
ps_sequence=0
ps_bucket_ms=$((ps_started_ms / 60000 * 60000))
record_minute 0
exec 3< <(exec /usr/local/bin/pslauncher 2>&1)
ps_client_pid=$!
ps_error_since=-1
ps_connect_deadline=$((SECONDS+60))
ps_reason=""
printf 'PS_SELF_START instance=%s machine=%s controller=imds\n' "${SALAD_INSTANCE_ID:-local}" "${SALAD_MACHINE_ID:-local}"
while :; do
  if IFS= read -r -t 0.2 ps_line <&3; then
    if [[ "$ps_line" == *'msg="Status:'* ]]; then
      printf 'PS_NATIVE instance=%s %s\n' "${SALAD_INSTANCE_ID:-local}" "$ps_line"
    else
      printf '%s\n' "$ps_line"
    fi
    case "${ps_line,,}" in
      *'msg="status: packetstream is running"'*) ps_error_since=-1; ps_state=running; ps_error=none ;;
      *'error communicating with packetstream server'*)
        ps_state=error; ps_error=communication_error
        if (( ps_error_since < 0 )); then ps_error_since=$SECONDS; fi ;;
      *'1 client per ip address'*) ps_state=error; ps_error=duplicate_ip; ps_reason='PacketStream rejected duplicate public IP'; break ;;
      *'non-residential'*|*'non residential'*) ps_state=error; ps_error=non_residential; ps_reason='PacketStream rejected non-residential IP'; break ;;
      *'msg="status: error'*) ps_state=error; ps_error=client_error; ps_reason='PacketStream reported a client error'; break ;;
    esac
  elif ! kill -0 "$ps_client_pid" 2>/dev/null; then
    ps_state=exited; ps_error=client_exited; ps_reason='PacketStream client exited'; break
  fi
  if (( EPOCHSECONDS * 1000 >= ps_bucket_ms + 60000 )); then record_minute 0; fi
  if [[ "$ps_state" == starting ]] && (( SECONDS >= ps_connect_deadline )); then ps_error=connection_timeout; ps_reason='PacketStream did not connect within 60 seconds'; break; fi
  if (( ps_error_since >= 0 && SECONDS - ps_error_since >= 30 )); then
    ps_reason='PacketStream server communication error persisted for 30 seconds'; break
  fi
done
ps_state=reallocating
stop_client
printf 'PS_SELF_REALLOCATE instance=%s machine=%s reason=%s\n' "${SALAD_INSTANCE_ID:-local}" "${SALAD_MACHINE_ID:-local}" "$ps_reason"
if /usr/bin/timeout 10 /bin/bash -c '
  ps_body="{\"reason\":\"$1\"}"
  exec 4<>/dev/tcp/169.254.169.254/80 || exit 1
  printf "POST /v1/reallocate HTTP/1.1\r\nHost: 169.254.169.254\r\nMetadata: true\r\nContent-Type: application/json\r\nContent-Length: %s\r\nConnection: close\r\n\r\n" "${#ps_body}" >&4
  printf "%s" "$ps_body" >&4
  IFS= read -r ps_response <&4 || exit 1
  printf "PS_SELF_IMDS_RESPONSE %s\n" "$ps_response"
  [[ "$ps_response" =~ ^HTTP/1\.[01][[:space:]]+(200|204)[[:space:]] ]]
' ps-imds "$ps_reason"; then
  printf 'PS_SELF_IMDS_ACCEPTED instance=%s\n' "${SALAD_INSTANCE_ID:-local}"
else
  printf 'PS_SELF_IMDS_FAILED instance=%s fallback=nonzero_exit\n' "${SALAD_INSTANCE_ID:-local}"
fi
# Salad also reallocates failed containers; never leave a failed client burning credits.
exit 75
~~~~~~

### proxyrack.py

<!-- rebuild-file: proxyrack.py sha256=c349057ac0510e0ce70ff039277604409f44163ebf8e486bb0f52c60dbd88965 -->
~~~~~~python
#!/usr/bin/env python3
"""Deploy and observe PR: one Salad group with ten replicas in SSH1."""
import argparse
import base64
from datetime import datetime, timedelta, timezone
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent
DATA = Path.home() / ".hg1/proxyrack"
HELPER = Path.home() / "Library/Application Support/Salad Bandwidth Dashboard/.runtime/keychain-store"
BASE = "https://api.salad.com/api/public/organizations/ssh1"
GROUPS = "/projects/default/containers"
IMAGE = "docker.io/proxyrack/pop@sha256:7de6719f37b31d5dd354f8cdd3ae601b4ed401832d0935ff460f968e0b6731bc"
sys.path.insert(0, str(ROOT.parent / "salad-bandwidth-stack"))
from dashboard.native_network import NetworkMinutes, parse_minute

STARTUP = r'''#!/bin/bash
set -u
umask 077
: "${PR_NAMESPACE:?}" "${PR_API_KEY:?}" "${SALAD_INSTANCE_ID:?}" "${SALAD_MACHINE_ID:?}"
pr_key=$PR_API_KEY; unset PR_API_KEY
[[ "$pr_key" =~ ^[A-Za-z0-9]+$ ]] || exit 1
UUID=$(printf '%s:%s' "$PR_NAMESPACE" "$SALAD_INSTANCE_ID" | sha256sum | cut -c1-64 | tr a-f A-F)
PR_WORKER="PR-${SALAD_INSTANCE_ID:0:8}"
pr_pid=""; pr_state=starting; pr_error=none; pr_registered=0
record_minute() {
  [[ -n "${pr_started:-}" ]] || return
  local now rx tx state=$pr_state error=$pr_error
  if [[ "$state" == running && "$pr_registered" == 0 ]]; then
    state=starting; error=registration_pending
  fi
  now="$(date +%s)000"
  read -r rx </sys/class/net/eth0/statistics/rx_bytes || return
  read -r tx </sys/class/net/eth0/statistics/tx_bytes || return
  printf 'PR_MINUTE_V1 worker=%s device=%s instance=%s machine=%s observer=%s seq=%s start_ms=%s end_ms=%s rx=%s tx=%s total_rx=%s total_tx=%s state=%s error=%s final=%s registered=%s\n' \
    "$PR_WORKER" "$UUID" "$SALAD_INSTANCE_ID" "$SALAD_MACHINE_ID" "$pr_started" "$pr_seq" "$pr_previous_ms" "$now" \
    "$((rx-pr_previous_rx))" "$((tx-pr_previous_tx))" "$((rx-pr_base_rx))" "$((tx-pr_base_tx))" "$state" "$error" "$1" "$pr_registered"
  pr_previous_rx=$rx; pr_previous_tx=$tx; pr_previous_ms=$now
  pr_seq=$((pr_seq+1)); pr_recorded=$SECONDS
}
stop_client() {
  exec 4>&-
  if [[ -n "$pr_pid" ]]; then
    kill "$pr_pid" 2>/dev/null || true
    sleep 1
    kill -KILL "$pr_pid" 2>/dev/null || true
    wait "$pr_pid" 2>/dev/null || true
  fi
  pr_pid=""
  exec 3<&-
}
reallocate() {
  stop_client
  pr_state=reallocating
  record_minute 1
  printf 'PR_SELF_REALLOCATE worker=%s instance=%s machine=%s reason=%s\n' "$PR_WORKER" "$SALAD_INSTANCE_ID" "$SALAD_MACHINE_ID" "$1"
  for attempt in 1 2 3; do
    code=$(curl --noproxy '*' -sS --connect-timeout 3 --max-time 10 -o /dev/null -w '%{http_code}' -X POST http://169.254.169.254/v1/reallocate -H 'Metadata: true' -H 'Content-Type: application/json' --data "{\"reason\":\"$1\"}") || code=000
    printf 'PR_SELF_IMDS_RESPONSE worker=%s instance=%s http=%s\n' "$PR_WORKER" "$SALAD_INSTANCE_ID" "$code"
    [[ "$code" == 200 || "$code" == 204 ]] && break
    sleep 5
  done
  exit 75
}
register_device() {
  local endpoint body code resolver
  local -a dns_args
  for endpoint in device/add device/status; do
    body="{\"device_id\":\"$UUID\",\"device_name\":\"$PR_WORKER\"}"
    for resolver in default doh; do
      dns_args=()
      [[ "$resolver" == doh ]] && dns_args=(--doh-url https://1.1.1.1/dns-query)
      code=$(printf 'header = "Api-Key: %s"\nheader = "Content-Type: application/json"\nheader = "Accept: application/json"\n' "$pr_key" | curl -sS --config - "${dns_args[@]}" --connect-timeout 5 --max-time 15 -X POST "https://peer.proxyrack.com/api/$endpoint" --data "$body" -o /tmp/pr-registration.json -w '%{http_code}' 2>/tmp/pr-registration.err) || code=000
      if [[ "$resolver" == default && "$code" == 000 ]] && grep -qiE 'Could not resolve host|Resolving timed out' /tmp/pr-registration.err; then
        printf 'PR_DNS_FALLBACK worker=%s instance=%s resolver=https\n' "$PR_WORKER" "$SALAD_INSTANCE_ID"
        continue
      fi
      cat /tmp/pr-registration.err >&2
      break
    done
    if [[ "$code" == 200 ]] && node -e 'const r=require("/tmp/pr-registration.json");process.exit(r.status==="success"&&r.data&&r.data.device_id===process.argv[1]?0:1)' "$UUID" 2>/dev/null; then
      pr_registered=1
      printf 'PR_REGISTERED worker=%s device=%s instance=%s\n' "$PR_WORKER" "$UUID" "$SALAD_INSTANCE_ID"
      rm -f /tmp/pr-registration.json /tmp/pr-registration.err
      pr_key=""
      return
    fi
    printf 'PR_REGISTRATION_RETRY worker=%s endpoint=%s http=%s\n' "$PR_WORKER" "$endpoint" "$code"
    [[ "$endpoint" == device/add && "$code" == 400 ]] && node -e 'const r=require("/tmp/pr-registration.json");process.exit(JSON.stringify(r).includes("already been taken")?0:1)' 2>/dev/null || break
  done
  rm -f /tmp/pr-registration.json /tmp/pr-registration.err
}
trap 'pr_state=exited; pr_error=operator_stop; stop_client; record_minute 1; exit 0' TERM INT
if ! curl -fsS --retry 2 --retry-delay 3 --connect-timeout 8 --max-time 45 https://app-updates.sock.sh/peerclient/go/client -o /app/pr-client; then
  pr_error=download_failed; reallocate 'PR native client download failed after retries'
fi
version=$(curl -fsS --retry 2 --retry-delay 3 --connect-timeout 8 --max-time 20 https://app-updates.sock.sh/peerclient/go/version.txt) || reallocate 'PR version download failed after retries'
[[ "$version" =~ ^[0-9]+$ ]] || reallocate 'PR returned an invalid client version'
chmod 700 /app/pr-client
pr_started="$(date +%s)000"
read -r pr_base_rx </sys/class/net/eth0/statistics/rx_bytes
read -r pr_base_tx </sys/class/net/eth0/statistics/tx_bytes
pr_previous_rx=$pr_base_rx; pr_previous_tx=$pr_base_tx; pr_previous_ms=$pr_started; pr_seq=0; pr_recorded=$SECONDS
record_minute 0
start_client() {
  rm -f /tmp/pr-input; mkfifo /tmp/pr-input
  exec 3< <(exec /app/pr-client --homeIp point-of-presence.sock.sh --homePort 443 --id "$UUID" --version "$version" --clientKey proxyrack-pop-client --clientType PoP --ppid $$ --osType Linux --osRelease "$(uname -r)" --osArch x64 </tmp/pr-input 2>&1)
  pr_pid=$!; exec 4>/tmp/pr-input
  pr_state=starting; pr_connect_since=$SECONDS
  printf 'PR_SELF_START worker=%s device=%s instance=%s machine=%s client_version=%s native=1\n' "$PR_WORKER" "$UUID" "$SALAD_INSTANCE_ID" "$SALAD_MACHINE_ID" "$version"
}
pr_register_delay=60; pr_register_at=$((SECONDS+60+RANDOM%120))
start_client
while :; do
  if IFS= read -r -t 1 line <&3; then
    printf 'PR_LOG worker=%s instance=%s %s\n' "$PR_WORKER" "$SALAD_INSTANCE_ID" "$line"
    case "$line" in
      *'connected to home:'*) pr_state=running; pr_error=none; pr_connect_since=-1 ;;
      *'connecting to home:'*)
        pr_state=starting; pr_error=connecting
        if (( pr_connect_since < 0 )); then pr_connect_since=$SECONDS; fi ;;
    esac
  elif ! kill -0 "$pr_pid" 2>/dev/null; then
    pr_state=exited; pr_error=client_exited
    reallocate 'Proxyrack native client exited'
  fi
  if (( pr_registered == 0 && SECONDS >= pr_register_at )); then
    register_device
    pr_register_at=$((SECONDS+pr_register_delay+RANDOM%90))
    (( pr_register_delay < 600 )) && pr_register_delay=$((pr_register_delay*2))
    (( pr_register_delay > 600 )) && pr_register_delay=600
  fi
  if (( SECONDS-pr_recorded >= 60 )); then record_minute 0; fi
  if (( pr_connect_since >= 0 && SECONDS-pr_connect_since >= 60 )); then
    pr_state=error; pr_error=connection_timeout; reallocate 'Proxyrack home connection unavailable for 60 seconds'
  fi
done
'''


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2))
    os.replace(temp, path)


def salad_api():
    key = subprocess.check_output([str(HELPER), "--read", "--service", "salad-bandwidth-api",
                                   "--account", getpass.getuser()], text=True).strip()

    def request(path, method="GET", body=None):
        if not (path == GROUPS or path.startswith(GROUPS + "/") or path == "/log-entries"):
            raise ValueError("Outside the requested SSH1 deployment")
        media = "application/merge-patch+json" if method == "PATCH" else "application/json"
        config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\nheader = " + json.dumps("Content-Type: " + media) + "\n"
        if body is not None:
            config += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
        result = subprocess.run(["curl", "-sS", "--max-time", "25", "--config", "-", "--request", method,
                                 "--write-out", "\n%{http_code}", BASE + path], input=config, text=True,
                                capture_output=True, timeout=30)
        raw, code = result.stdout.rsplit("\n", 1)
        if result.returncode or not 200 <= int(code) < 300:
            raise RuntimeError("Salad " + method + " " + path + " returned HTTP " + code)
        return json.loads(raw) if raw.strip() else {}
    return request


def peer_api():
    key = subprocess.check_output([str(HELPER), "--read", "--service", "proxyrack-peer-api",
                                   "--account", getpass.getuser()], text=True, stderr=subprocess.DEVNULL).strip()

    def request(method, payload=None):
        if method not in ("balance", "bandwidth", "device/status"):
            raise ValueError("Unsupported ProxyRack operation")
        config = "header = " + json.dumps("Api-Key: " + key) + '\nheader = "Content-Type: application/json"\nheader = "Accept: application/json"\n'
        config += "data-binary = " + json.dumps(json.dumps(payload or {})) + "\n"
        result = subprocess.run(["curl", "-sS", "--max-time", "20", "--config", "-", "--request", "POST",
                                 "--write-out", "\n%{http_code}", "https://peer.proxyrack.com/api/" + method],
                                input=config, text=True, capture_output=True, timeout=25)
        raw, code = result.stdout.rsplit("\n", 1)
        if result.returncode or code not in ("200", "400"):
            try:
                detail = str(json.loads(raw).get("error", "")).replace(key, "[redacted]")[:160]
            except (ValueError, AttributeError):
                detail = ""
            raise RuntimeError("ProxyRack " + method + " returned HTTP " + code + (": " + detail if detail else ""))
        try:
            return json.loads(raw)
        except ValueError:
            raise RuntimeError("ProxyRack returned a non-JSON response") from None
    return request


def configuration():
    return json.loads((DATA / "deployment.json").read_text())


def command():
    encoded = base64.b64encode(STARTUP.encode()).decode()
    args = ["/bin/bash", "-c", 'umask 077; printf "%s" "$@" | base64 -d > /tmp/pr-start.sh; exec /bin/bash /tmp/pr-start.sh',
            "pr-start", *[encoded[i:i+900] for i in range(0, len(encoded), 900)]]
    if len(args) > 100 or any(not value or len(value) > 1000 for value in args):
        raise ValueError("Startup command exceeds Salad command limits")
    return args


def deploy():
    api = salad_api()
    config = configuration()
    if "workers" in config:
        old = config
        for worker in old["workers"]:
            group = api(GROUPS + "/" + worker["name"])
            if group["id"] != worker["group_id"] or group["current_state"]["status"] != "stopped":
                raise RuntimeError("Stop the previous deployment before replacing it")
        config = {"organization": "ssh1", "project": "default", "name": "pr", "replicas": 10,
                  "created_at": datetime.now(timezone.utc).isoformat(), "namespace": secrets.token_hex(16),
                  "image": IMAGE, "replaced_groups": old["workers"]}
        save(DATA / "deployment.json", config)
    key = subprocess.check_output([str(HELPER), "--read", "--service", "proxyrack-peer-api",
                                   "--account", getpass.getuser()], text=True).strip()
    existing = {g["name"]: g for g in api(GROUPS).get("items", [])}
    if "pr" in existing:
        group = api(GROUPS + "/pr")
        if group["container"]["environment_variables"].get("PR_NAMESPACE") != config["namespace"]:
            raise RuntimeError("Existing PR group has a different deployment identity")
        if group["container"]["command"] != command():
            raise RuntimeError("Use update to change an existing PR deployment")
    else:
        payload = {"name": "pr", "display_name": "PR", "replicas": 10,
                   "autostart_policy": True, "restart_policy": "always", "country_codes": ["us"],
                   "container": {"image": IMAGE, "priority": "batch", "resources": {"cpu": 1, "memory": 1024},
                                 "command": command(), "environment_variables": {
                                     "PR_NAMESPACE": config["namespace"], "PR_API_KEY": key}}}
        group = api(GROUPS, "POST", payload)
    config["group_id"] = group["id"]
    save(DATA / "deployment.json", config)
    for _ in range(30):
        group = api(GROUPS + "/pr")
        if group["current_state"]["status"] != "preparing":
            break
        time.sleep(2)
    if group["current_state"]["status"] == "stopped":
        api(GROUPS + "/pr/start", "POST")
    elif group["current_state"]["status"] not in ("deploying", "running"):
        raise RuntimeError("PR is not ready to start: " + group["current_state"]["status"])
    print("PR requested: one group, ten replicas, US, 1 CPU / 1 GB each", flush=True)


def inspect():
    api = salad_api()
    config = configuration()
    group = api(GROUPS + "/pr")
    if group["id"] != config["group_id"]:
        raise RuntimeError("Deployment identity changed")
    instances = api(GROUPS + "/pr/instances").get("instances", [])
    print("PR", group["current_state"], [{k:i.get(k) for k in ("id", "machine_id", "state", "ready")} for i in instances])


def update_startup():
    api = salad_api()
    config = configuration()
    group = api(GROUPS + "/pr")
    if group["id"] != config["group_id"]:
        raise RuntimeError("Deployment identity changed")
    if group["container"]["command"] != command():
        api(GROUPS + "/pr", "PATCH", {"container": {"command": command()}})
    after = api(GROUPS + "/pr")
    if after["container"]["command"] != command():
        raise RuntimeError("Startup command was not applied")
    print("PR startup verified", flush=True)


def device_id(config, instance):
    return hashlib.sha256((config["namespace"] + ":" + instance).encode()).hexdigest().upper()


def parsed_time(value):
    value = re.sub(r"\.(\d+)(?=Z$|[+-]\d\d:\d\d$)",
                   lambda m: "." + (m[1] + "000000")[:6], value)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def provider_loop(config, members, meter, stopped):
    path = DATA / "provider.json"
    state = json.loads(path.read_text()) if path.exists() else {}
    if state.get("group_id") != config["group_id"]:
        state = {"group_id": config["group_id"], "workers": {}}
    api = peer_api()
    while not stopped.is_set():
        current = {w["device_id"]: w for w in members.get("workers", [])}
        for instance in meter.latest(config["group_id"]):
            state["workers"].setdefault(device_id(config, instance), {})
        now, jobs = int(time.time() * 1000), []
        for device, row in state["workers"].items():
            live = current.get(device, {})
            connected = live.get("fresh") and live.get("client_state") == "running"
            if connected:
                due = row.get("status_attempted_ms", 0) + (120_000 if row.get("error") else 1_800_000)
                if due <= now:
                    jobs.append((due, "device/status", device))
            interval = 300_000 if device in current else 3_600_000
            due = row.get("bandwidth_attempted_ms", 0) + interval
            if due <= now:
                jobs.append((due, "bandwidth", device))
        due = state.get("balance_attempted_ms", 0) + (120_000 if state.get("balance_error") else 600_000)
        if due <= now:
            jobs.append((due, "balance", ""))
        if not jobs:
            stopped.wait(5)
            continue
        _, method, device = min(jobs)
        row = state if method == "balance" else state["workers"][device]
        kind = "status" if method == "device/status" else method
        row[kind + "_attempted_ms"] = now
        payload = {"device_id": device} if device else {}
        if method == "bandwidth":
            payload.update(date_start=(parsed_time(config["created_at"]).date() - timedelta(days=1)).isoformat(),
                           date_end=datetime.now(timezone.utc).date().isoformat())
        try:
            result = api(method, payload)
            if result.get("status") != "success":
                raise RuntimeError(result.get("error", "PR has not returned this reading"))
            data, checked = result["data"], int(time.time() * 1000)
            if method == "device/status":
                row.update(status=data.get("status", "Not reported"), checked_ms=checked, error=None)
            elif method == "bandwidth":
                days = data.get("bandwidth", {})
                if not isinstance(days, dict) or not all(isinstance(v, (int, float)) and v >= 0 for v in days.values()):
                    raise ValueError("PR returned invalid bandwidth values")
                row.update(credited_mb=sum(days.values()) * 1000, bandwidth_state=data.get("state"),
                           bandwidth_checked_ms=checked, bandwidth_error=None)
            else:
                row.update(balance=data.get("balance"), balance_checked_ms=checked, balance_error=None)
        except Exception as error:
            row["error" if method == "device/status" else kind + "_error"] = str(error)[:200]
        save(path, state)
        # The measured account limit is five requests/minute; leave capacity for replica registration.
        stopped.wait(20)


def make_view(meter, config, inventory, cloud_error=None):
    now = int(time.time() * 1000)
    provider_path = DATA / "provider.json"
    provider = json.loads(provider_path.read_text()) if provider_path.exists() else {}
    if provider.get("group_id") != config["group_id"]:
        provider = {}
    with meter.lock:
        rows = [dict(row) for row in meter.db.execute(
            "SELECT * FROM minutes WHERE group_id=? ORDER BY end_ms,observer,seq", (config["group_id"],))]
    totals, timeline, total = {}, [], 0
    for row in rows:
        if not row["valid"]:
            continue
        run = (row["instance"], row["observer"])
        amount = row["total_rx"] + row["total_tx"]
        previous = totals.get(run, 0)
        if amount < previous:
            continue
        total += amount - previous
        totals[run] = amount
        if timeline and timeline[-1]["time_ms"] == row["end_ms"]:
            timeline[-1]["mb"] = total / 1e6
        else:
            timeline.append({"time_ms": row["end_ms"], "mb": total / 1e6})
    workers = []
    for member in inventory.get("instances", []):
        machine_rows = [r for r in rows if r["machine"] == member["machine_id"] and r["instance"] == member["id"]]
        last = max(machine_rows, key=lambda r:(r["observer"], r["seq"]), default=None)
        instance = member["id"]
        device = device_id(config, instance)
        age = now - last["end_ms"] if last else None
        fresh = bool(not cloud_error and last and last["valid"] and -10_000 <= age <= 150_000 and not last["final"])
        status_fresh = bool(not cloud_error and last and -10_000 <= age <= 150_000)
        seconds = (last["end_ms"] - last["start_ms"]) / 1000 if last else None
        amount = (last["rx"] + last["tx"]) / 1e6 if last and last["valid"] and last["seq"] > 0 else None
        prov = provider.get("workers", {}).get(device, {})
        p_age = now - prov["checked_ms"] if prov.get("checked_ms") else None
        raw_status = prov.get("status", "Waiting for registration")
        online = p_age is not None and p_age < 240_000 and raw_status.startswith("Online") and not prov.get("error")
        if cloud_error:
            state = "Status unavailable"
        elif inventory.get("status") == "stopped":
            state = "Stopped"
        elif member["state"] != "running":
            state = member["state"].capitalize()
        elif status_fresh and last["state"] == "reallocating":
            state = "Reallocating"
        elif fresh:
            state = "Running" if last["state"] == "running" else "Recovering" if last["state"] in ("error", "exited") else "Starting client"
        else:
            state = "Checking client"
        workers.append({"name": "PR-" + instance[:8], "instance": instance, "device_id": device,
            "salad_instance": member["id"], "machine": member["machine_id"], "salad_state": member["state"], "status": state,
            "client_state": last["state"] if status_fresh else None,
            "provider_status": raw_status, "provider_online": bool(online), "provider_age_ms": p_age,
            "provider_error": prov.get("error"), "credited_mb": prov.get("credited_mb"),
            "bandwidth_state": prov.get("bandwidth_error") or prov.get("bandwidth_state"),
            "bandwidth_checked_ms": prov.get("bandwidth_checked_ms"),
            "network_mb": sum(v for k,v in totals.items() if k[0] == instance) / 1e6 if last else None,
            "interval_mb": amount, "interval_seconds": seconds,
            "mb_per_minute": amount * 60 / seconds if amount is not None and seconds else None,
            "sample_age_ms": age, "fresh": fresh, "last_sample_ms": last["end_ms"] if last else None,
            "client_error": last["error"] if last and last["error"] != "none" else None,
            "samples": sum(r["seq"] > 0 for r in machine_rows),
            "group_url": "https://portal.salad.com/organizations/ssh1/projects/default/containers/pr/instances/" + member["id"]})
    credited = [p["credited_mb"] for p in provider.get("workers", {}).values() if p.get("credited_mb") is not None]
    return {"generated_ms": now, "organization": "SSH1", "group": "PR", "requested": config["replicas"],
            "group_id": config["group_id"], "workers": workers,
            "reporting": sum(w["fresh"] for w in workers), "online": sum(w["provider_online"] for w in workers),
            "network_mb": total / 1e6, "credited_mb": sum(credited) if credited else None,
            "credited_devices": sum(w["credited_mb"] is not None for w in workers),
            "balance": provider.get("balance"), "balance_checked_ms": provider.get("balance_checked_ms"),
            "timeline": timeline, "cloud_error": cloud_error, "started_at": config["created_at"]}


def observe():
    config = configuration()
    lock = (DATA / "observer.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    meter = NetworkMinutes(DATA / "traffic.sqlite3")
    api = salad_api()
    stopped, members = threading.Event(), {}
    threading.Thread(target=provider_loop, args=(config, members, meter, stopped), daemon=True).start()
    cursor = parsed_time(config["created_at"])
    state_path = DATA / "cursor.json"
    if state_path.exists():
        saved = json.loads(state_path.read_text())
        if saved.get("group_id") == config["group_id"]:
            cursor = parsed_time(saved["cursor"])
    inventory = {}
    try:
        while True:
            began = time.monotonic()
            error = None
            try:
                group = api(GROUPS + "/pr")
                if group["id"] != config["group_id"]:
                    raise RuntimeError("Deployment identity changed")
                inventory = {"status": group["current_state"]["status"],
                             "instances": api(GROUPS + "/pr/instances").get("instances", [])}
                end, start = datetime.now(timezone.utc), cursor - timedelta(minutes=10)
                for page in range(30):
                    entries = api("/log-entries", "POST", {
                        "query": 'resource.type = "container" and resource.labels.container_group_name = "pr" and text_log startswith "PR_MINUTE_V1"',
                        "start_time": start.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                        "end_time": end.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                        "page_size": 100, "sort_order": "asc"}).get("items", [])
                    records = []
                    for item in entries:
                        line = item.get("text_log", "")
                        try:
                            values = dict(part.split("=", 1) for part in line.split()[1:])
                            if values["device"] != device_id(config, values["instance"]):
                                continue
                            converted = dict(item, text_log=line.replace("PR_MINUTE_V1 ", "PS_MINUTE_V1 ", 1) + " ip=-")
                            record = parse_minute(converted, config["group_id"])
                            if record and record["end_ms"] <= int(time.time() * 1000) + 30_000:
                                record["record_bytes"] = len(line.encode()) + 1
                                records.append(record)
                        except (ValueError, KeyError, TypeError):
                            continue
                    meter.ingest(records)
                    times = [parsed_time(i["time"]) for i in entries if i.get("time")]
                    if times:
                        following = max(times)
                        cursor = max(cursor, following)
                    if len(entries) < 100 or not times:
                        break
                    following = following.replace(microsecond=following.microsecond//1000*1000)
                    if following <= start:
                        raise RuntimeError("PR log pagination made no progress")
                    start = following
                else:
                    raise RuntimeError("PR log backlog is still being collected")
                save(state_path, {"group_id": config["group_id"], "cursor": cursor.isoformat()})
            except Exception as caught:
                error = str(caught)[:200]
            view = make_view(meter, config, inventory, error)
            members["workers"] = view["workers"]
            save(DATA / "view.json", view)
            time.sleep(max(1, 15 - (time.monotonic() - began)))
    finally:
        stopped.set()


def main():
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["deploy", "status", "observe", "update"])
    args = parser.parse_args()
    if args.action == "deploy":
        deploy()
    elif args.action == "status":
        inspect()
    elif args.action == "update":
        update_startup()
    else:
        observe()


if __name__ == "__main__":
    main()
~~~~~~

### ps1-native-recorder.py

<!-- rebuild-file: ps1-native-recorder.py sha256=a950adc2e25afad35a0085c1830ad681e5a4351f31fc46ef3f55134f00c63138 -->
~~~~~~python
#!/usr/bin/env python3
"""Start only the PS1 recorder on macOS, without starting Docker or other apps."""
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
import runpy


def main():
    root = Path.home() / "Library/Application Support/Salad Bandwidth Dashboard"
    target_file = Path.home()/".hg1/packetstream/observer-target.json"
    if target_file.exists():
        target = json.loads(target_file.read_text())
        if target.get("mode") == "native-census":
            os.environ["PS_GROUP"] = target["group"]
            os.environ["PS_EXPECTED_GROUP_ID"] = target["group_id"]
            runpy.run_path(str(root/"packetstream-monitor/native-census.py"), run_name="__main__")
            return
    helper = root / ".runtime/keychain-store"
    key = subprocess.check_output([str(helper), "--read", "--service", "salad-bandwidth-api",
                                   "--account", getpass.getuser()], text=True).strip()
    if not key:
        raise RuntimeError("Salad credential is unavailable")
    config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\n"
    result = subprocess.run(["/usr/bin/curl", "-sS", "--max-time", "20", "--config", "-",
                             "--write-out", "\n%{http_code}",
                             "https://api.salad.com/api/public/organizations/hyperlane/projects/default/containers/ps1"],
                            input=config, text=True, capture_output=True, timeout=25)
    raw, code = result.stdout.rsplit("\n", 1)
    if result.returncode or code != "200":
        raise RuntimeError("PS1 configuration could not be read")
    group = json.loads(raw)
    if group.get("id") != "1c7c9cbd-0cc2-4f10-a1ad-76f56d7492ba":
        raise RuntimeError("PS1 deployment identity changed")
    env = group["container"]["environment_variables"]
    if env.get("CID") != "8ExP" or len(env.get("PS_STREAM_TOKEN", "")) < 32:
        raise RuntimeError("PS1 recorder configuration changed")
    data = Path.home() / ".hg1/packetstream/network"
    data.mkdir(parents=True, exist_ok=True)
    child_env = os.environ.copy()
    child_env.update(SALAD_API_KEY=key, PS_STREAM_TOKEN=env["PS_STREAM_TOKEN"],
                     PS_ORGANIZATION="hyperlane", PS_GROUP="ps1")
    executable = str(root / "ps1-collector")
    print("Starting native PS1 device recorder on 127.0.0.1:8789", flush=True)
    os.execve(executable, [executable, "-data", str(data), "-listen", "127.0.0.1:8789"], child_env)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never emit the provider response or credentials into service logs.
        print("PS1 native recorder could not start:", type(exc).__name__, file=sys.stderr)
        sys.exit(1)
~~~~~~

### repocket-monitor/observe.py

<!-- rebuild-file: repocket-monitor/observe.py sha256=6c52ef8591ad9b02425517c4f82b4fd2972d044c1865e96c0598fe6239c1030c -->
~~~~~~python
"""Read Repocket worker records from SSH2 and keep the local traffic history."""
import argparse
from datetime import datetime, timezone
import fcntl
import getpass
import hashlib
import json
import os
import re
from pathlib import Path
import sqlite3
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / '.hg1/repocket'
GROUP = '/projects/default/containers/rp-test-us'

def stamp(ms):
    return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')

def api(path,body=None):
    if path not in (GROUP,GROUP+'/instances','/log-entries'):raise ValueError('Outside Repocket read scope')
    key=subprocess.check_output([str(ROOT/'.runtime/keychain-store'),'--read','--service','salad-bandwidth-api','--account',getpass.getuser()],text=True).strip()
    config='header = '+json.dumps('Salad-Api-Key: '+key)+'\nheader = "Content-Type: application/json"\n'
    if body is not None:config+='data-binary = '+json.dumps(json.dumps(body))+'\n'
    r=subprocess.run(['curl','-sS','--max-time','20','--config','-','--write-out','\n%{http_code}','https://api.salad.com/api/public/organizations/ssh2'+path],input=config,text=True,capture_output=True,timeout=25)
    raw,code=r.stdout.rsplit('\n',1)
    if r.returncode or code!='200':raise RuntimeError('Salad read returned HTTP '+code)
    return json.loads(raw)

def save(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,separators=(',',':')));os.replace(temporary,path)

def fetch(start,end,depth=0):
    if depth>20:raise RuntimeError('Log window could not be read completely')
    body={'query':'resource.type = "container" and resource.labels.container_group_name = "rp-test-us" and text_log startswith "RP_MON "','start_time':stamp(start),'end_time':stamp(end),'page_size':100,'sort_order':'asc'}
    rows=api('/log-entries',body).get('items',[])
    if len(rows)>=100:
        middle=(start+end)//2
        if middle<=start:raise RuntimeError('Too many worker records at one timestamp')
        return fetch(start,middle,depth+1)+fetch(middle,end,depth+1)
    return rows

def insert(db,rows):
    added=0;size=0
    for row in sorted(rows,key=lambda x:x.get('time','')):
        raw=row.get('text_log','')
        if not raw.startswith('RP_MON '):continue
        try:
            item=json.loads(raw[7:]);kind=item['kind'];at=int(item['time_ms'])
            if item.get('service')!='repocket' or kind not in ('start','tick','minute','recovery'):continue
            if not isinstance(item.get('run'),str) or not isinstance(item.get('machine'),str):continue
            if kind=='minute' and (item['end_ms']<=item['start_ms'] or item['rx_bytes']<0 or item['tx_bytes']<0 or item['elapsed_ms']!=item['end_ms']-item['start_ms']):continue
        except (ValueError,KeyError,TypeError):continue
        value=json.dumps(item,separators=(',',':'));identity=hashlib.sha256(value.encode()).hexdigest()
        cursor=db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?)',(identity,at,item['machine'],item['run'],kind,value))
        if cursor.rowcount:added+=1;size+=len(value.encode())
    db.commit()
    if added:db.execute('INSERT INTO writes VALUES(?,?,?)',(int(time.time()*1000),added,size));db.commit()
    return added

def snapshot(db,deployment,group,instances,now,backfill,read_error=None):
    events=[json.loads(r[0]) for r in db.execute("SELECT body FROM events WHERE kind IN ('start','minute') OR rowid IN (SELECT rowid FROM (SELECT rowid,row_number() OVER (PARTITION BY run ORDER BY time_ms DESC,rowid DESC) AS rank FROM events WHERE kind='tick') WHERE rank=1) ORDER BY time_ms,rowid")]
    latest={};by_run={};minutes={};unbucketed=0
    for item in events:
        run=item['run'];state=by_run.setdefault(run,{'run':run,'machine':item['machine'],'instance':item.get('instance'),'revision':item.get('revision',1),'started_ms':item.get('started_ms',item['time_ms']),'ip':'','rx_bytes':0,'tx_bytes':0,'minutes':0})
        if item.get('ip'):state['ip']=item['ip']
        if item['kind'] in ('start','tick'):
            state.update(phase=item.get('phase','starting'),reason=item.get('reason',''),source_ms=item['time_ms'],restart_count=item.get('restart_count',0),diagnostics=item.get('diagnostics'),device_id=item.get('device_id'),last_ping_ms=item.get('last_ping_ms'),log_counts=item.get('log_counts',{}),policy=item.get('policy'))
            identity=(item['machine'],item.get('instance'))
            if identity not in latest or item['started_ms']>=latest[identity]['started_ms']:latest[identity]=state
        if item['kind']=='minute':
            amount=item['rx_bytes']+item['tx_bytes'];state['rx_bytes']+=item['rx_bytes'];state['tx_bytes']+=item['tx_bytes'];state['minutes']+=1
            state.update(last_mb=amount/1e6,last_elapsed_seconds=item['elapsed_ms']/1000,last_end_ms=item['end_ms'],last_mb_per_minute=amount/1e6*60000/item['elapsed_ms'])
            bucket=item['start_ms']//60000*60000
            nearest=round(item['start_ms']/60000)*60000
            if 59000<=item['elapsed_ms']<=61000 and abs(item['start_ms']-nearest)<=1000:bucket=nearest
            if item['elapsed_ms']>61000 or item['end_ms']>bucket+61000:
                unbucketed+=1;continue
            minute=minutes.setdefault(bucket,{'time_ms':bucket,'mb':0,'partial':False,'contributions':{}})
            contribution=minute['contributions'].setdefault(run,{'run':run,'machine':item['machine'],'instance':item.get('instance'),'ip':item.get('ip',''),'mb':0,'elapsed_seconds':0})
            contribution['mb']+=amount/1e6;contribution['elapsed_seconds']+=item['elapsed_ms']/1000;minute['mb']+=amount/1e6;minute['partial']|=item.get('partial',False)
    workers=[]
    for instance in instances:
        worker=dict(latest.get((instance['machine_id'],instance['id']),{}))
        if not worker and instance.get('update_time'):
            text=re.sub(r'\.(\d+)(?=[+-])',lambda m:'.'+m.group(1)[:6].ljust(6,'0'),instance['update_time'].replace('Z','+00:00'))
            began=int(datetime.fromisoformat(text).timestamp()*1000)
            candidates=[w for w in latest.values() if w['machine']==instance['machine_id'] and w.get('started_ms',0)>=began-60000 and w.get('source_ms',0)>=began]
            worker=dict(max(candidates,key=lambda w:w['started_ms'],default={}))
        worker.update(machine=instance['machine_id'],salad_instance=instance['id'],salad_state=instance['state'],current=True)
        age=now-worker.get('source_ms',0);worker['source_age_ms']=age if worker.get('source_ms') else None
        worker['status']=worker.get('phase','starting') if age<60000 and age>=-10000 and instance['state']=='running' else ('stale' if worker.get('source_ms') else instance['state'])
        worker['total_mb']=(worker.get('rx_bytes',0)+worker.get('tx_bytes',0))/1e6 if worker.get('minutes') else None;workers.append(worker)
    history=[]
    for minute in sorted(minutes.values(),key=lambda x:x['time_ms']):
        minute['contributions']=list(minute['contributions'].values());history.append(minute)
    total_network_mb=sum((r['rx_bytes']+r['tx_bytes'])/1e6 for r in by_run.values())
    if history:
        indexed={m['time_ms']:m for m in history};last=max(history[-1]['time_ms'],now//60000*60000-60000)
        history=[indexed.get(at,{'time_ms':at,'mb':None,'partial':True,'contributions':[]}) for at in range(max(history[0]['time_ms'],last-119*60000),last+1,60000)]
    cost_rate=0.05
    return {'generated_ms':now,'source_ms':max((w.get('source_ms',0)for w in workers),default=0),'organization':'ssh2','group':'rp-test-us','group_id':deployment['id'],'group_state':group.get('current_state',{}).get('status'),'desired':deployment['replicas'],'running':sum(i['state']=='running'for i in instances),'connected':sum(w['status']=='connected'for w in workers),'workers':workers,'minutes':history[-120:],'total_network_mb':total_network_mb,'unbucketed_intervals':unbucketed,'record_count':db.execute('SELECT count(*) FROM events').fetchone()[0],'database_bytes':sum(p.stat().st_size for p in DATA.glob('traffic.sqlite3*')),'saved_bytes_last_minute':db.execute('SELECT coalesce(sum(bytes),0) FROM writes WHERE time_ms>=?',(now-60000,)).fetchone()[0],'backfill_through_ms':backfill,'error':read_error,'recent_recovery':[json.loads(row[0]) for row in db.execute("SELECT body FROM events WHERE kind='recovery' ORDER BY time_ms DESC LIMIT 5")],'measurement':'Container interface RX+TX bytes, including overhead; not provider-credited traffic.','provider_url':'https://repocket.com/dashboard/share-internet','salad_url':'https://portal.salad.com/organizations/ssh2/projects/default/containers/rp-test-us','budget_usd':5,'estimated_full_fleet_usd_per_hour':cost_rate,'cost_basis':'Estimate from the existing one-CPU, one-GB lowest-priority fleet; invoice not reconciled.'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
    os.umask(0o077);DATA.mkdir(parents=True,exist_ok=True)
    lock=(DATA/'observer.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    deployment=json.loads((DATA/'deployment.json').read_text())
    db=sqlite3.connect(DATA/'traffic.sqlite3');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,time_ms INTEGER,machine TEXT,run TEXT,kind TEXT,body TEXT)')
    db.execute('CREATE INDEX IF NOT EXISTS event_time ON events(time_ms)')
    db.execute('CREATE TABLE IF NOT EXISTS writes(time_ms INTEGER,records INTEGER,bytes INTEGER)')
    state_path=DATA/'cursor.json';state=json.loads(state_path.read_text()) if state_path.exists() else {}
    beginning=int(datetime.fromisoformat(deployment.get('start_requested_at',deployment['created_at'])).timestamp()*1000)
    cursor=state.get('through_ms',beginning);last_reconcile=state.get('last_reconcile_ms',int(time.time()*1000))
    reconcile_cursor=state.get('reconcile_cursor');reconcile_end=state.get('reconcile_end')
    while True:
        began=time.monotonic();now=int(time.time()*1000)
        try:
            group=api(GROUP)
            if group['id']!=deployment['id']:raise RuntimeError('Repocket deployment identity changed')
            instances=api(GROUP+'/instances')['instances']
            end=min(now,cursor+600000);start=max(beginning,cursor-300000)
            rows=fetch(start,end)
            if end<now:rows+=fetch(max(beginning,now-180000),now)
            if reconcile_cursor is None and now-last_reconcile>=300000:
                reconcile_cursor=max(beginning,now-3600000);reconcile_end=now
            if reconcile_cursor is not None:
                stop=min(reconcile_end,reconcile_cursor+60000);rows+=fetch(reconcile_cursor,stop);reconcile_cursor=stop
                if reconcile_cursor>=reconcile_end:reconcile_cursor=None;reconcile_end=None;last_reconcile=now
            if int(time.time()*1000)-now>15000:
                fresh=int(time.time()*1000);rows+=fetch(max(beginning,fresh-60000),fresh)
                group=api(GROUP);instances=api(GROUP+'/instances')['instances']
                if group['id']!=deployment['id']:raise RuntimeError('Repocket deployment identity changed')
            added=insert(db,rows);cursor=end;save(state_path,{'through_ms':cursor,'last_reconcile_ms':last_reconcile,'reconcile_cursor':reconcile_cursor,'reconcile_end':reconcile_end})
            value=snapshot(db,deployment,group,instances,int(time.time()*1000),cursor);save(DATA/'view.json',value)
            print(json.dumps({'checked_at':stamp(value['generated_ms']),'running':value['running'],'connected':value['connected'],'inserted':added,'network_mb':round(value['total_network_mb'],3)}),flush=True)
        except Exception as error:
            message=str(error) if isinstance(error,RuntimeError) else type(error).__name__
            path=DATA/'view.json';value=json.loads(path.read_text()) if path.exists() else {'workers':[],'minutes':[],'desired':10,'running':0,'connected':0}
            value.update(generated_ms=int(time.time()*1000),error=message);save(path,value);print('Repocket recorder:',message,flush=True)
            if args.once:raise SystemExit(1)
        if args.once:break
        time.sleep(max(1,(1 if cursor<now-60000 else 15)-(time.monotonic()-began)))

if __name__=='__main__':main()
~~~~~~

### scripts/bind-website.py

<!-- rebuild-file: scripts/bind-website.py sha256=f5945882e7e73e52b137d75e87489393d8aa982da89876d9a9c05b397aacb7d0 -->
~~~~~~python
#!/usr/bin/env python3
"""Bind fresh local ledgers to existing Salad groups; do not deploy containers."""
import argparse
from datetime import datetime, timezone
import getpass
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rebuild_cloud',ROOT/'scripts/rebuild-cloud.py')
cloud=importlib.util.module_from_spec(spec);spec.loader.exec_module(cloud)
targets={'ps':('hyperlane','ps-test-us'),'pr':('ssh1','pr'),'rp':('ssh2','rp-test-us'),'rfm':('ssh3','earnfm-us'),'tm':('ssh4','tm-test-us')}
p=argparse.ArgumentParser(description=__doc__);p.add_argument('services',nargs='+',choices=targets);args=p.parse_args()
key=subprocess.check_output([str(ROOT/'.runtime/keychain-store'),'--read','--service','salad-bandwidth-api','--account',getpass.getuser()],text=True).strip()
os.umask(0o077);data=Path.home()/'.hg1'
for name in args.services:
 org,group=targets[name];g=cloud.api(key,org,'/projects/default/containers/'+group)
 now=int(time.time()*1000);started=datetime.fromtimestamp(now/1000,timezone.utc).isoformat()
 common=dict(organization=org,project='default',group=group,image=g['container']['image'])
 if name=='ps':
  path=data/'packetstream/observer-target.json';value=dict(mode='native-census',group_id=g['id'],**common)
 elif name=='pr':
  path=data/'proxyrack/deployment.json';value=dict(name=group,replicas=g['replicas'],group_id=g['id'],created_at=started,namespace=g['container']['environment_variables']['PR_NAMESPACE'],**common)
 elif name=='rp':
  path=data/'repocket/deployment.json';value=dict(id=g['id'],replicas=g['replicas'],version=g['version'],created_at=started,start_requested_at=started,**common)
 elif name=='rfm':
  path=data/'earnfm/target.json';value=dict(id=g['id'],desired=g['replicas'],version=g['version'],created_at=started,measurement_started_ms=now,**common)
 else:
  path=data/'traffmonetizer/deployment.json'
  if path.exists():raise SystemExit('Existing metadata preserved: '+str(path))
  sys.path.insert(0,str(ROOT/'traffmonetizer'))
  from observer import provider_reading
  baseline=provider_reading(dict(started_at=started,provider_baseline_usd=0,provider_baseline_bytes=0,provider_baseline_earned_usd=0))
  value=dict(group_id=g['id'],desired_replicas=g['replicas'],started_at=started,measurement_started_ms=now,
      provider_baseline_usd=baseline['balance_usd'],provider_baseline_bytes=baseline['credited_bytes'],
      provider_baseline_earned_usd=baseline['credited_usd'],**common)
 if path.exists():raise SystemExit('Existing metadata preserved: '+str(path))
 cloud.write(path,value);print(name+' bound to '+g['id']+'; new measurement baseline, not restored history.')
~~~~~~

### scripts/earnfm-recorder.py

<!-- rebuild-file: scripts/earnfm-recorder.py sha256=c75d268026c83b041c5d9634a7a6bfd4e170f32c8fc0db886968889a610fa75d -->
~~~~~~python
#!/usr/bin/env python3
"""Read SSH3 telemetry into a durable ledger and publish the EarnFM monitoring page data."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import getpass
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / '.hg1/earnfm'
OUTPUT = ROOT / 'dashboard/static/earnfm.json'
FIELDS = ('run', 'seq', 'instance', 'machine', 'start_ms', 'end_ms', 'rx', 'tx',
          'total_rx', 'total_tx', 'state', 'valid', 'final', 'ip', 'country')


def millis(value):
    value = re.sub(r'\.(\d+)(?=[+-]\d\d:\d\d$)', lambda m: '.'+m.group(1)[:6].ljust(6, '0'), value.replace('Z', '+00:00'))
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def iso(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def request(path, body=None):
    key = subprocess.check_output([str(ROOT / '.runtime/keychain-store'), '--read', '--service',
                                   'salad-bandwidth-api', '--account', getpass.getuser()], text=True).strip()
    config = 'header = ' + json.dumps('Salad-Api-Key: ' + key) + '\nheader = "Content-Type: application/json"\n'
    if body is not None:
        config += 'data-binary = ' + json.dumps(json.dumps(body)) + '\n'
    response = subprocess.run(['curl', '-sS', '--max-time', '20', '--config', '-', '--write-out', '\n%{http_code}',
                               'https://api.salad.com/api/public/organizations/ssh3' + path],
                              input=config, text=True, capture_output=True, timeout=25)
    raw, status = response.stdout.rsplit('\n', 1)
    if response.returncode or status != '200':
        raise RuntimeError('Salad reading failed (HTTP ' + status + ')')
    return json.loads(raw)


def provider_reading():
    path = DATA / 'provider.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    now = int(time.time()*1000)
    if now - previous.get('checked_ms', 0) < 60000:
        return previous
    result = dict(previous, checked_ms=now)
    try:
        value = subprocess.check_output([str(ROOT/'.runtime/keychain-store'), '--read', '--service',
                                         'earnfm-read-session', '--account', getpass.getuser()], text=True)
        session = json.loads(value)
        if session['expires_at'] <= time.time():
            raise RuntimeError('EarnFM account login expired; traffic recording continues')
        config = 'header = '+json.dumps('X-API-Key: '+session['access_token'])+'\n'
        responses = {}
        for name in ('view_balance', 'devices_online'):
            reply = subprocess.run(['curl', '-sS', '--max-time', '15', '--config', '-', '--write-out', '\n%{http_code}',
                                    'https://api.earn.fm/v2/harvester/'+name], input=config, text=True, capture_output=True, timeout=20)
            raw, code = reply.stdout.rsplit('\n', 1)
            if reply.returncode or code != '200':
                raise RuntimeError('EarnFM account reading failed (HTTP '+code+')')
            responses[name] = json.loads(raw)
        balance = responses['view_balance']['data']
        paid = float(Decimal(str(balance['bandwidthBalance']))+Decimal(str(balance['bandwidthDCBalance'])))
        shared = float(Decimal(str(balance['totalBandwidthShared']))+Decimal(str(balance['totalDCBandwidthShared'])))
        baseline_path = DATA/'provider-baseline.json'
        baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {'time_ms': now, 'balance': paid, 'gb': shared}
        if not baseline_path.exists():
            baseline_path.write_text(json.dumps(baseline))
        devices = []
        for item in responses['devices_online']['data']['devices']:
            match = re.search(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', item.get('deviceName', ''))
            devices.append({'instance': match.group() if match else None, 'name': item.get('deviceName'),
                            'ip': item.get('IP'), 'hosting': item.get('isHosting')})
        result = {'checked_ms': now, 'observed_ms': responses['view_balance']['timestamp'], 'balance': paid, 'gb': shared,
                  'earned': float(Decimal(str(paid))-Decimal(str(baseline['balance']))),
                  'credited_mb': float((Decimal(str(shared))-Decimal(str(baseline['gb'])))*1000),
                  'baseline_ms': baseline['time_ms'], 'devices': devices, 'error': None}
    except Exception as exc:
        result['error'] = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
    temporary = path.with_suffix('.tmp'); temporary.write_text(json.dumps(result)); os.replace(temporary, path)
    return result


def parse_sample(item, machine):
    row = item.get('json_log')
    if not isinstance(row, dict):
        try:
            row = json.loads(item.get('text_log', ''))
        except (ValueError, TypeError):
            return None
    if row.get('kind') != 'earnfm_sample' or row.get('revision') != 1 or row.get('machine') != machine:
        return None
    try:
        result = {key: row.get(key, '') if key in ('ip', 'country') else row[key] for key in FIELDS}
        for key in ('seq', 'start_ms', 'end_ms', 'rx', 'tx', 'total_rx', 'total_tx', 'valid', 'final'):
            value = result[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value) or not 0 <= value < 2**53:
                return None
            result[key] = int(value)
        if (not 0 < result['start_ms'] <= result['end_ms'] <= int(time.time()*1000)+60000 or result['valid'] not in (0, 1) or result['final'] not in (0, 1)
                or result['state'] not in ('starting', 'running', 'retrying', 'rate_limited', 'connection_error', 'stopping', 'reallocating')
                or not isinstance(result['run'], str) or len(result['run']) > 120
                or not isinstance(result['instance'], str) or len(result['instance']) != 36):
            return None
        if result['ip']:
            result['ip'] = str(ipaddress.ip_address(result['ip']))
        if result['country'] and not re.fullmatch('[A-Z]{2}', result['country']):
            return None
        return result
    except (KeyError, TypeError, ValueError):
        return None


def database(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS samples (
        run TEXT, seq INTEGER, instance TEXT, machine TEXT, start_ms INTEGER, end_ms INTEGER,
        rx INTEGER, tx INTEGER, total_rx INTEGER, total_tx INTEGER, state TEXT, valid INTEGER, final INTEGER, ip TEXT, country TEXT,
        PRIMARY KEY(run,seq));
      CREATE INDEX IF NOT EXISTS samples_time ON samples(end_ms);
      CREATE TABLE IF NOT EXISTS cursors(machine TEXT PRIMARY KEY,time_ms INTEGER);
      CREATE TABLE IF NOT EXISTS runs (
        run TEXT PRIMARY KEY, seq INTEGER, instance TEXT, machine TEXT, start_ms INTEGER, end_ms INTEGER,
        rx INTEGER, tx INTEGER, total_rx INTEGER, total_tx INTEGER, state TEXT, valid INTEGER, final INTEGER, ip TEXT, country TEXT);
    ''')
    for table in ('samples', 'runs'):
        columns = {r[1] for r in db.execute('PRAGMA table_info('+table+')')}
        for column in ('ip', 'country'):
            if column not in columns:
                db.execute('ALTER TABLE '+table+' ADD COLUMN '+column+' TEXT')
    return db


def fetch_worker(machine, cursor, now):
    records = []
    start = max(0, cursor - 60000)
    latest = cursor
    query = ('resource.type = "container" and resource.labels.container_group_name = "earnfm-us" '
             'and resource.labels.machine_id = "' + machine + '" and json_log.kind = "earnfm_sample"')
    # Small windows avoid Salad's capped pages and preserve delayed records.
    for _ in range(8):
        if start >= now:
            break
        end = min(now, start + 60000)
        items = request('/log-entries', {'query': query, 'start_time': iso(start), 'end_time': iso(end),
                                        'page_size': 100, 'sort_order': 'asc'}).get('items', [])
        if len(items) >= 100:
            raise RuntimeError('A telemetry window exceeded the log page limit')
        for item in items:
            parsed = parse_sample(item, machine)
            if parsed is not None:
                records.append(parsed)
                latest = max(latest, millis(item['time']))
        latest = max(latest, end)
        start = end
    return records, latest


def snapshot(db, target, inventory, observed_ms, error=None, provider=None):
    now = int(time.time() * 1000)
    latest_rows = db.execute('SELECT * FROM runs').fetchall()
    total = sum(row['total_rx'] + row['total_tx'] for row in latest_rows)
    latest = {}
    for row in latest_rows:
        if row['machine'] not in latest or row['end_ms'] > latest[row['machine']]['end_ms']:
            latest[row['machine']] = row
    workers = []
    provider = provider or {}
    online = {d['instance']: d for d in provider.get('devices', []) if d.get('instance')}
    for node in inventory:
        sample = latest.get(node['machine_id'])
        runtime_instance = sample['instance'] if sample else node['id']
        provider_ip = online.get(runtime_instance, {}).get('ip')
        public_ip = provider_ip or (sample['ip'] if sample else None)
        country = sample['country'] if sample and provider_ip and provider_ip == sample['ip'] else None
        window = db.execute('SELECT SUM((rx+tx)*1.0*(end_ms-MAX(start_ms,?))/(end_ms-start_ms)),SUM(end_ms-MAX(start_ms,?)) FROM samples WHERE run=? AND seq>0 AND valid=1 AND end_ms>start_ms AND end_ms>?', (sample['end_ms']-60000,sample['end_ms']-60000,sample['run'],sample['end_ms']-60000)).fetchone() if sample else (None,None)
        rate = window[0]/window[1] if window[1] else None
        workers.append({'instance': node['id'], 'machine': node['machine_id'], 'runtime_instance': runtime_instance, 'salad_state': node['state'],
                        'client_state': sample['state'] if sample else 'awaiting_sample',
                        'provider_online': runtime_instance in online and sample is not None and now-sample['end_ms'] < 90000 and not sample['final'] and sample['state'] == 'running',
                        'ip': public_ip, 'country': country,
                        'error': ('Connection failed: replacing after exhausted connection attempts or 30 seconds of repeated errors' if sample and sample['state'] == 'connection_error' else 'Provider cooldown: retries automatically after the required 24-hour wait' if sample and sample['state'] == 'rate_limited' else ''),
                        'sample_ms': sample['end_ms'] if sample else None,
                        'total_mb': (sample['total_rx'] + sample['total_tx']) / 1e6 if sample else None,
                        'kb_per_second': rate,
                        'final': bool(sample['final']) if sample else False})
    start = max(target.get('measurement_started_ms', now), now - 24 * 3600000)
    minutes = db.execute('''SELECT (end_ms-CASE WHEN end_ms>start_ms THEN 1 ELSE 0 END)/60000*60000 minute_ms, instance, machine,
      SUM(CASE WHEN valid=1 THEN rx+tx ELSE 0 END) bytes,
      SUM(CASE WHEN valid=1 THEN end_ms-start_ms ELSE 0 END) duration_ms FROM samples WHERE seq>0 AND end_ms>=?
      GROUP BY minute_ms,instance,machine ORDER BY minute_ms''', (start,)).fetchall()
    points = {}
    for row in minutes:
        point = points.setdefault(row['minute_ms'], {'time_ms': row['minute_ms'], 'mb': 0, 'duration_ms': 0, 'by_instance': {}})
        point['mb'] += row['bytes'] / 1e6
        point['duration_ms'] += row['duration_ms']
        point['by_instance'][row['instance']] = row['bytes'] / 1e6
    for point in points.values():
        point['partial'] = point['duration_ms'] < 60000 * target['desired']
    return {'generated_ms': now, 'inventory_ms': observed_ms, 'error': error,
            'test_started_ms': target.get('measurement_started_ms'), 'desired': target['desired'],
            'group': 'ssh3/default/earnfm-us', 'workers': workers, 'points': list(points.values()),
            'total_mb': total / 1e6, 'sample_count': db.execute('SELECT COUNT(*) FROM samples').fetchone()[0],
            'database_bytes': sum(p.stat().st_size for p in (DATA/'traffic.sqlite3', DATA/'traffic.sqlite3-wal') if p.exists()),
            'provider': provider,
            'basis': 'Measured eth0 RX + TX; includes client control traffic. Not provider-paid bandwidth.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True)
    lock = (DATA / 'recorder.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    db = database(DATA / 'traffic.sqlite3')
    inventory, observed = [], None
    departed = {}
    while True:
        began = time.monotonic()
        target = json.loads((DATA / 'target.json').read_text())
        error = None
        try:
            group = request('/projects/default/containers/earnfm-us')
            if group['id'] != target['id'] or group['container']['image'] != target['image']:
                raise RuntimeError('EarnFM deployment identity changed')
            inventory = request('/projects/default/containers/earnfm-us/instances').get('instances', [])
            observed = int(time.time() * 1000)
            cursors = dict(db.execute('SELECT machine,time_ms FROM cursors').fetchall())
            active = {n['machine_id'] for n in inventory}
            for node in inventory:
                cursors.setdefault(node['machine_id'], max(target.get('measurement_started_ms', observed), millis(node['update_time'])-60000))
            for machine in cursors:
                if machine in active:
                    departed.pop(machine, None)
                else:
                    departed.setdefault(machine, observed)
            with ThreadPoolExecutor(max_workers=3) as pool:
                jobs = {pool.submit(fetch_worker, machine, cursor, observed): machine for machine, cursor in cursors.items()}
                for job, machine in jobs.items():
                    try:
                        records, cursor = job.result()
                        with db:
                            for row in records:
                                db.execute('INSERT OR IGNORE INTO samples VALUES (' + ','.join('?' for _ in FIELDS) + ')', tuple(row[k] for k in FIELDS))
                                db.execute('INSERT INTO runs VALUES (' + ','.join('?' for _ in FIELDS) + ') ON CONFLICT(run) DO UPDATE SET ' + ','.join(k+'=excluded.'+k for k in FIELDS if k!='run') + ' WHERE excluded.seq>runs.seq', tuple(row[k] for k in FIELDS))
                            if machine in departed and observed-departed[machine] >= 60000 and cursor >= observed:
                                db.execute('DELETE FROM cursors WHERE machine=?', (machine,))
                                departed.pop(machine)
                            else:
                                db.execute('INSERT OR REPLACE INTO cursors VALUES (?,?)', (machine, cursor))
                    except Exception as exc:
                        error = type(exc).__name__ + ': ' + str(exc)
        except Exception as exc:
            error = type(exc).__name__ + ': ' + str(exc)
        output = snapshot(db, target, inventory, observed, error, provider_reading())
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        temporary = OUTPUT.with_suffix('.tmp')
        temporary.write_text(json.dumps(output, separators=(',', ':')))
        os.replace(temporary, OUTPUT)
        if args.once:
            print(json.dumps({'workers': len(output['workers']), 'samples': output['sample_count'], 'total_mb': output['total_mb'], 'error': error}))
            break
        time.sleep(max(1, 15 - (time.monotonic() - began)))
    db.close()


if __name__ == '__main__':
    main()
~~~~~~

### scripts/hg-fleet-control.py

<!-- rebuild-file: scripts/hg-fleet-control.py sha256=636784169bc0a3fd77eecba964f5c474b697bb4ac9f767d9db5fa510b820bcf0 -->
~~~~~~python
#!/usr/bin/env python3
"""Operate a bounded ten-worker Honeygain control using existing registrations."""
import argparse
import fcntl
from datetime import datetime, timedelta, timezone
import getpass
import ipaddress
import json
import os
import re
import math
import sys
import time
from pathlib import Path
import subprocess
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get('HG_FLEET_DIR', str(ROOT / '.runtime/hg-fleet')))
IMAGE = 'docker.io/honeygain/honeygain@sha256:5cd8c361517d0cbae4aa2c75e13239e45f9193ab8e205d57fa29f2e695ea3ec1'
ORGS = ('deathadder', 'cosmosgeeketh', 'hyperlane')
DEVICES = (
    'salad-us-1', 'worker-us-1',
    'salad-c4385ee4-0693-505d-8bd4-76f0e37054a9',
    'salad-5cd61ffc-5e1a-7f55-86a6-ebf67cf06478',
    'salad-b8ababd8-ac4b-d45c-b6a0-b499236dee05',
    'salad-45ef0f8f-0a89-6a5d-9f16-9b606250128e',
    'salad-eeec7129-d81e-d851-8a2e-2a94747b15d2',
    'salad-62d87783-409d-825e-9125-d5166b9038e0',
    'salad-d645de46-f7cc-1859-98a4-cfe7f88bc346',
    'salad-a1d8dea8-73bc-5356-8980-b652388c1659',
)
GROUPS = ('hg1',) + tuple('hg-solo-%02d' % n for n in range(2, 11))


def recovery_command():
    script = r'''set -u
child=""; state=starting; error=none; reason=""; deadline=120; next_sample=0
stop_client() { if [ -n "$child" ]; then kill "$child" 2>/dev/null || true; sleep 1; kill -KILL "$child" 2>/dev/null || true; wait "$child" 2>/dev/null || true; child=""; fi; }
trap 'stop_client; exit 0' TERM INT
start_client() {
  exec 3< <(exec /app/honeygain -tou-accept -email "$HONEYGAIN_EMAIL" -pass "$HONEYGAIN_PASSWORD" -device "$HONEYGAIN_DEVICE_NAME" 2>&1)
  child=$!
}
printf 'HG_SELF_START controller=imds time=%s\n' "$(date -u +%FT%TZ)"
start_client
while :; do
  if IFS= read -r -t 1 line <&3; then
    printf '%s\n' "$line"
    case "${line,,}" in
      *overused*) state=network_overused; error=network_overused; reason=network_overused; break ;;
      *unusable*) state=network_unusable; error=network_unusable; reason=network_unusable; break ;;
      *'connected and running'*) state=connected; error=none ;;
      *disconnected*) if [ "$state" != disconnected ]; then deadline=$((SECONDS+120)); fi; state=disconnected; error=disconnected ;;
      *'already active'*) state=waiting; error=device_already_active ;;
      *'error processing'*) state=authorization_error; error=authorization_error ;;
    esac
  elif ! kill -0 "$child" 2>/dev/null; then
    wait "$child"; code=$?; child=""
    printf 'HG_STOCK_EXIT status=%s time=%s\n' "$code" "$(date -u +%FT%TZ)"
    if [ "$error" = device_already_active ] && (( SECONDS < deadline )); then sleep 15; start_client; else reason=client_exited; break; fi
  fi
  if [ "$state" != connected ] && (( SECONDS >= deadline )); then reason=connection_timeout; break; fi
  if (( SECONDS >= next_sample )); then
    while read -r iface rx rp re rd rf rfr rc rm tx rest; do
      if [ "$iface" = 'eth0:' ]; then printf '{"kind":"hg_native_sample","time":"%s","version":"0.6.6","rx_total":%s,"tx_total":%s,"state":"%s","error":"%s"}\n' "$(date -u +%FT%TZ)" "$rx" "$tx" "$state" "$error"; fi
    done </proc/net/dev
    next_sample=$((SECONDS+10))
  fi
done
stop_client
printf 'HG_SELF_REALLOCATE reason=%s time=%s\n' "$reason" "$(date -u +%FT%TZ)"
for attempt in 1 2 3; do
  if timeout 10 /bin/bash -c '
    body="{\"reason\":\"Honeygain $1\"}"
    exec 4<>/dev/tcp/169.254.169.254/80 || exit 1
    printf "POST /v1/reallocate HTTP/1.1\r\nHost: 169.254.169.254\r\nMetadata: true\r\nContent-Type: application/json\r\nContent-Length: %s\r\nConnection: close\r\n\r\n%s" "${#body}" "$body" >&4
    IFS= read -r response <&4 || exit 1
    printf "HG_SELF_IMDS_RESPONSE %s\n" "$response"
    [[ "$response" =~ ^HTTP/1\.[01][[:space:]]+(200|204)[[:space:]] ]]
  ' hg-imds "$reason"; then
    printf 'HG_SELF_IMDS_ACCEPTED time=%s\n' "$(date -u +%FT%TZ)"
    exit 75
  fi
  printf 'HG_SELF_IMDS_FAILED attempt=%s time=%s\n' "$attempt" "$(date -u +%FT%TZ)"
  sleep 15
done
exit 75'''
    return ['/bin/bash', '-c', 'printf "%s\\n" "$@" > /tmp/hg-stock-run.sh; exec /bin/bash /tmp/hg-stock-run.sh', 'hg-stock', *script.splitlines()]


def now():
    return datetime.now(timezone.utc).isoformat()


class Fleet:
    def __init__(self):
        RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
        helper = os.environ.get('HG_KEYCHAIN_HELPER', str(ROOT / '.runtime/keychain-store'))
        self.key = subprocess.check_output([helper, '--read',
            '--service', 'salad-bandwidth-api', '--account', getpass.getuser()], text=True).strip()

    def api(self, org, path='', method='GET', body=None):
        url = 'https://api.salad.com/api/public/organizations/' + org + path
        media = 'application/merge-patch+json' if method == 'PATCH' else 'application/json'
        config = 'header = ' + json.dumps('Salad-Api-Key: ' + self.key) + '\n'
        config += 'header = ' + json.dumps('Content-Type: ' + media) + '\n'
        if body is not None:
            config += 'data-binary = ' + json.dumps(json.dumps(body)) + '\n'
        response = subprocess.run(['curl', '--silent', '--show-error', '--max-time', '35',
            '--config', '-', '--request', method, '--write-out', '\n%{http_code}', url],
            input=config, capture_output=True, text=True, timeout=40)
        if response.returncode:
            raise RuntimeError('Salad transport request failed')
        raw, code = response.stdout.rsplit('\n', 1)
        if not 200 <= int(code) < 300:
            raise RuntimeError('%s %s%s returned HTTP %s' % (method, org, path, code))
        return json.loads(raw) if raw.strip() else {}

    def groups(self, org):
        return self.api(org, '/projects/default/containers').get('items', [])

    @staticmethod
    def device(g):
        c = g.get('container', {})
        device = c.get('environment_variables', {}).get('HONEYGAIN_DEVICE_NAME')
        if device:
            return device
        command = c.get('command') or []
        if '-device' in command and command.index('-device') + 1 < len(command):
            return command[command.index('-device') + 1]
        matches = re.findall(r'-device[ =]+[\"\x27]?([A-Za-z0-9-]+)', ' '.join(command))
        if len(matches) == 1:
            return matches[0]
        return None

    @staticmethod
    def safe(g):
        return {'group': g['name'], 'id': g['id'], 'replicas': g.get('replicas'),
                'image': g.get('container', {}).get('image'), 'device': Fleet.device(g),
                'state': g.get('current_state', {}), 'version': g.get('version')}

    def inventory(self):
        result = []
        for org in ORGS:
            try:
                for g in self.groups(org):
                    result.append({'organization': org, **self.safe(g)})
            except RuntimeError as e:
                result.append({'organization': org, 'error': str(e)})
        return result

    @staticmethod
    def write(name, record):
        path = RUNTIME / name
        temp = path.with_suffix(path.suffix + '.%s.tmp' % os.getpid())
        temp.write_text(json.dumps(record, indent=2) + '\n')
        temp.chmod(0o600)
        temp.replace(path)

    def stop_redundant(self):
        result = []
        for org in ORGS:
            for g in self.groups(org):
                if not self.device(g):
                    continue
                if org == 'deathadder' and g['name'] in GROUPS:
                    continue
                if g.get('current_state', {}).get('status') != 'stopped':
                    self.api(org, '/projects/default/containers/' + g['name'] + '/stop', 'POST')
                    result.append({'organization': org, 'group': g['name'], 'device': self.device(g),
                                   'stop_requested_at': now()})
        self.write('redundant-stops.json', result)
        return result

    def deploy(self):
        # Read every org first; never add workers while another HG group is active.
        for org in ORGS:
            for g in self.groups(org):
                if not self.device(g):
                    continue
                intended = org == 'deathadder' and g['name'] in GROUPS
                if not intended:
                    instances = self.api(org, '/projects/default/containers/' + g['name'] + '/instances')
                    if instances.get('instances'):
                        raise RuntimeError('Redundant HG instances must finish stopping: ' + org + '/' + g['name'])
        original = self.api('deathadder', '/projects/default/containers/hg1')
        if original['container']['image'] != IMAGE or self.device(original) != DEVICES[0] or original['replicas'] != 1:
            raise RuntimeError('Existing solo control changed; inspect before deployment')
        env = original['container']['environment_variables']
        current = {g['name']: g for g in self.groups('deathadder')}
        assert len(DEVICES) == len(set(DEVICES)) == len(GROUPS) == 10
        receipt = []
        for index, (group, device) in enumerate(zip(GROUPS, DEVICES), 1):
            if group in current:
                g = current[group]
                if self.device(g) != device or g['container']['image'] != IMAGE or g['replicas'] != 1:
                    raise RuntimeError('Existing group does not match approved control: ' + group)
            else:
                payload = {'name': group, 'display_name': 'HG Solo %02d' % index, 'replicas': 1,
                    'autostart_policy': True, 'restart_policy': 'always', 'country_codes': ['us'],
                    'container': {'image': IMAGE, 'resources': {'cpu': 1, 'memory': 1024},
                        'priority': 'low', 'command': original['container']['command'],
                        'environment_variables': {'HONEYGAIN_EMAIL': env['HONEYGAIN_EMAIL'],
                            'HONEYGAIN_PASSWORD': env['HONEYGAIN_PASSWORD'], 'HONEYGAIN_DEVICE_NAME': device}}}
                g = self.api('deathadder', '/projects/default/containers', 'POST', payload)
            receipt.append({'worker': index, 'organization': 'deathadder', **self.safe(g), 'checked_at': now()})
            self.write('deployment.json', receipt)
            print(json.dumps({'worker': index, 'group': group, 'device': device,
                              'state': g.get('current_state', {}).get('status')}), flush=True)
        return receipt

    def start_ready(self):
        result = []
        for group in GROUPS:
            g = self.api('deathadder', '/projects/default/containers/' + group)
            if g.get('current_state', {}).get('status') == 'stopped':
                try:
                    self.api('deathadder', '/projects/default/containers/' + group + '/start', 'POST')
                    result.append({'group': group, 'start_requested_at': now()})
                except RuntimeError as e:
                    result.append({'group': group, 'error': str(e)})
        return result

    def enable_recovery(self, groups=GROUPS):
        command = recovery_command()
        result = []
        for group in groups:
            if group not in GROUPS:
                raise ValueError('Unknown Honeygain group')
            path = '/projects/default/containers/' + group
            current = self.api('deathadder', path)
            if current['container']['image'] != IMAGE or current['replicas'] != 1 or self.device(current) != DEVICES[GROUPS.index(group)]:
                raise RuntimeError('Honeygain registration or deployment changed: ' + group)
            if current['container']['command'] != command:
                current = self.api('deathadder', path, 'PATCH', {'container': {'command': command}})
            result.append({'group': group, 'version': current.get('version'), 'recovery': 'IMDS inside container'})
        return result


def record_provider(record):
    """Persist an actual fresh visible-UI reading; never read authentication state."""
    observed_ms = record.get('observed_ms')
    if not isinstance(observed_ms, int) or not -60000 <= int(time.time()*1000) - observed_ms <= 300000:
        raise ValueError('Provider reading needs its actual observation time within five minutes')
    source = record.get('source', 'Fresh Honeygain dashboard visible UI')
    if source not in ('Fresh Honeygain dashboard visible UI', 'Honeygain official dashboard API'):
        raise ValueError('Unrecognized provider reading source')
    def amount(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('Credits must be finite nonnegative provider observations')
        return value
    devices = record.get('devices', [])
    if len(devices) != 10 or {x.get('device') for x in devices} != set(DEVICES):
        raise ValueError('Reading must contain exactly the ten existing fleet registrations once each')
    clean_devices = []
    for device in DEVICES:
        item = next(x for x in devices if x['device'] == device)
        if not isinstance(item.get('provider_active'), bool):
            raise ValueError('Provider active status must be observed, not inferred from historical device count')
        ip = item.get('ip')
        if ip:
            parsed = ipaddress.ip_address(ip)
            ip = str(parsed.ipv4_mapped or parsed) if isinstance(parsed, ipaddress.IPv6Address) else str(parsed)
        clean_devices.append({'device': device, 'credits': amount(item.get('credits')),
                              'provider_active': item['provider_active'], 'ip': ip})
    clean = {'checked_at': now(), 'observed_ms': observed_ms,
             'gathering_credits': amount(record.get('gathering_credits')),
             'account_balance_credits': amount(record.get('account_balance_credits')),
             'source': source, 'devices': clean_devices}
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (RUNTIME / 'provider-writer.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        latest = RUNTIME / 'provider-latest.json'
        if latest.exists() and json.loads(latest.read_text()).get('observed_ms', 0) >= observed_ms:
            raise ValueError('Reading does not advance the actual provider observation timestamp')
        Fleet.write('provider-latest.json', clean)
        with (RUNTIME / 'provider-readings.jsonl').open('a') as output:
            output.write(json.dumps(clean) + '\n')
    return {'observed_ms': observed_ms, 'gathering_credits': clean['gathering_credits'],
            'device_count': len(clean_devices), 'provider_active': sum(x['provider_active'] for x in clean_devices)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['inventory', 'stop-redundant', 'deploy', 'start-ready', 'record-provider', 'enable-recovery'])
    args = p.parse_args()
    if args.action == 'record-provider':
        print(json.dumps(record_provider(json.load(sys.stdin))))
        return
    fleet = Fleet()
    action = getattr(fleet, args.action.replace('-', '_'))
    result = action()
    if args.action != 'deploy':
        print(json.dumps(result, indent=2))
    fleet.write(args.action + '-latest.json', {'checked_at': now(), 'result': result})


if __name__ == '__main__':
    main()
~~~~~~

### scripts/hg-fleet-observer.py

<!-- rebuild-file: scripts/hg-fleet-observer.py sha256=419bc42de81169a8f1893411c600f3097ac24498f77083abb7033ab4ecbb2c01 -->
~~~~~~python
#!/usr/bin/env python3
"""Read Salad native lifecycle and network counters into a per-worker ledger."""
import argparse
import fcntl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import re
from pathlib import Path
import time

spec = importlib.util.spec_from_file_location('hg_fleet_control', Path(__file__).with_name('hg-fleet-control.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


def milliseconds(value):
    value = value.replace('Z', '+00:00')
    value = re.sub(r'\.(\d+)(?=[+-])', lambda m: '.' + m.group(1)[:6].ljust(6, '0'), value)
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def classify(text):
    low = text.lower()
    if 'hg_self_reallocate' in low or 'hg_self_imds_accepted' in low:
        return 'reallocating'
    if 'user_device_limit_exceeded' in low or 'device limit' in low:
        return 'device_limit'
    if 'already active' in low:
        return 'device_already_active'
    if 'overused' in low:
        return 'network_overused'
    if 'unusable' in low:
        return 'network_unusable'
    if 'connected and running' in low:
        return 'connected'
    if 'disconnected' in low:
        return 'disconnected'
    if 'authorisation successful' in low:
        return 'authenticated'
    if 'service is starting' in low:
        return 'starting'
    if 'error processing' in low:
        return 'authorization_error'
    if 'hg_stock_exit' in low:
        return 'exited'
    return None


def read_provider():
    path = control.RUNTIME / 'provider-latest.json'
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def observe_worker(fleet, index, group, device, provider):
    worker = {'worker': index, 'organization': 'deathadder', 'group': group, 'device': device,
              'machine': None, 'ip': None, 'state': 'unverified', 'client_status': 'unverified',
              'credits': None, 'credit_observed_ms': None, 'error': None}
    device_reading = next((x for x in provider.get('devices', []) if x.get('device') == device), {})
    worker.update(credits=device_reading.get('credits'), ip=device_reading.get('ip'),
                  credit_observed_ms=provider.get('observed_ms'),
                  provider_active=device_reading.get('provider_active'))
    try:
        path = '/projects/default/containers/' + group
        g = fleet.api('deathadder', path)
        if fleet.device(g) != device or g.get('replicas') != 1 or g['container']['image'] != control.IMAGE:
            raise RuntimeError('Configuration differs from the approved independent stock control')
        instances = fleet.api('deathadder', path + '/instances').get('instances', [])
        worker.update(state=g.get('current_state', {}).get('status'), image=g['container']['image'],
                      replica_count=len(instances), running_instances=sum(x.get('state') == 'running' for x in instances))
        if len(instances) > 1:
            raise RuntimeError('Multiple instances share one registration during rollout')
        if not instances:
            worker['client_status'] = 'not_started'
            return worker
        instance = instances[0]
        worker.update(instance=instance['id'], machine=instance.get('machine_id'),
                      instance_state=instance.get('state'), ready=instance.get('ready'))
        end = datetime.now(timezone.utc)
        native_recovery = any('HG_SELF_START' in part for part in g['container'].get('command', []))
        identity = 'machine_id' if native_recovery else 'instance_id'
        base = ('resource.type = "container" and resource.labels.project_name = "default" and '
                'resource.labels.container_group_name = "' + group + '" and '
                'resource.labels.' + identity + ' = "' + instance.get(identity, instance['id']) + '"')
        lifecycle_query = base + ' and (text_log contains "Honeygain" or text_log contains "Authorisation" or text_log contains "HG_STOCK" or text_log contains "HG_SELF" or text_log contains "device" or text_log contains "overused" or text_log contains "Error")'
        def logs(query, minutes, size):
            calls = 0
            def fetch_window(start, stop):
                nonlocal calls
                calls += 1
                if calls > 63:
                    raise RuntimeError('Salad log window exceeds bounded pagination budget')
                items = fleet.api('deathadder', '/log-entries', 'POST', {'query': query,
                    'start_time': start.isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
                    'end_time': stop.isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
                    'page_size': size, 'sort_order': 'asc'}).get('items', [])
                if len(items) < size:
                    return items
                # A full response can contain an older capped page, regardless of
                # requested sort order. Split time until every window is complete.
                if (stop-start) <= timedelta(milliseconds=1):
                    raise RuntimeError('Too many Salad logs share one timestamp')
                midpoint = start + (stop-start)/2
                return fetch_window(start, midpoint) + fetch_window(midpoint, stop)
            start = end-timedelta(minutes=minutes)
            if native_recovery and instance.get('update_time'):
                start = max(start, datetime.fromtimestamp(milliseconds(instance['update_time'])/1000, timezone.utc))
            items = fetch_window(start, end) if start < end else []
            unique = {json.dumps(item, sort_keys=True): item for item in items}
            return list(unique.values())
        events = logs(lifecycle_query, 3 if native_recovery else 120, 100)
        safe_events = []
        for entry in events:
            text = entry.get('text_log', '')
            status = classify(text)
            if status:
                safe_events.append({'time': entry.get('time'), 'status': status})
        safe_events.sort(key=lambda x: x['time'] or '', reverse=True)
        if safe_events:
            worker.update(client_status=safe_events[0]['status'], last_event_at=safe_events[0]['time'])
            if safe_events[0]['status'] in ('device_limit', 'device_already_active', 'network_overused', 'network_unusable', 'authorization_error'):
                worker['error'] = safe_events[0]['status']
        worker['lifecycle'] = safe_events[:20]
        samples = logs(base + ' and json_log.kind = "hg_native_sample"', 3, 30)
        readings = [{'time': x.get('time'), **{k: x.get('json_log', {}).get(k) for k in ('rx_total', 'tx_total', 'state', 'error')}} for x in samples]
        readings.sort(key=lambda x: x['time'] or '')
        if readings:
            worker['sample'] = readings[-1]
            worker['sample_age_seconds'] = (int(time.time()*1000) - milliseconds(readings[-1]['time'])) / 1000
            if len(readings) >= 2:
                seconds = (milliseconds(readings[-1]['time']) - milliseconds(readings[0]['time'])) / 1000
                worker['network_window_seconds'] = seconds
                worker['rx_bytes_window'] = max(0, readings[-1]['rx_total'] - readings[0]['rx_total'])
                worker['tx_bytes_window'] = max(0, readings[-1]['tx_total'] - readings[0]['tx_total'])
        worker['connection_evidence_fresh'] = worker.get('sample_age_seconds', 9999) < 120 and instance.get('state') == 'running'
        if worker['client_status'] == 'connected' and not worker['connection_evidence_fresh']:
            worker['client_status'] = 'connected_last_observed_telemetry_stale'
        if readings and worker['connection_evidence_fresh'] and readings[-1].get('state') in ('connected', 'starting', 'waiting', 'disconnected', 'authorization_error'):
            if not safe_events or milliseconds(readings[-1]['time']) >= milliseconds(safe_events[0]['time']):
                worker['client_status'] = readings[-1]['state']
                worker['error'] = readings[-1].get('error') if readings[-1].get('error') not in (None, 'none') else None
        if not safe_events and worker['client_status'] == 'unverified':
            previous = control.RUNTIME / ('worker-%02d.json' % index)
            if previous.exists():
                old = json.loads(previous.read_text())
                previous_age = int(time.time()*1000) - milliseconds(old.get('checked_at', '1970-01-01T00:00:00Z'))
                if old.get('instance') == instance['id'] and worker.get('connection_evidence_fresh') and previous_age < 600000:
                    worker['client_status'] = old.get('client_status', 'unverified')
                    worker['last_event_at'] = old.get('last_event_at')
    except Exception as error:
        worker['error'] = type(error).__name__ + ': ' + str(error)
        if worker['client_status'] == 'connected':
            worker['client_status'] = 'connected_last_observed_telemetry_unverified'
    return worker


def observe(fleet):
    provider = read_provider()
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(observe_worker, fleet, index, group, device, provider)
                   for index, (group, device) in enumerate(zip(control.GROUPS, control.DEVICES), 1)]
        workers = [x.result() for x in futures]
    stamp = control.now()
    record = {'checked_at': stamp, 'time_ms': int(time.time()*1000), 'desired': 10,
              'running': sum(x.get('running_instances', 0) for x in workers),
              'connected': sum(x['client_status'] == 'connected' for x in workers),
              'provider_gathering_credits': provider.get('gathering_credits'),
              'provider_observed_ms': provider.get('observed_ms'), 'workers': workers,
              'connection_definition': 'Current native connected lifecycle without later exit/disconnect, live Salad instance and telemetry sample under 120s old. Provider credits remain separate.',
              'network_definition': 'Container interface bytes include protocol overhead and are not provider billed traffic.'}
    for worker in workers:
        worker['checked_at'] = stamp
        fleet.write('worker-%02d.json' % worker['worker'], worker)
    fleet.write('status.json', record)
    with (control.RUNTIME / 'observations.jsonl').open('a') as output:
        output.write(json.dumps(record) + '\n')
    print(json.dumps({k: record[k] for k in ('checked_at', 'desired', 'running', 'connected')}), flush=True)
    print(json.dumps([{'group': x['group'], 'state': x['state'], 'client_status': x['client_status'], 'error': x['error']} for x in workers]), flush=True)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--once', action='store_true')
    p.add_argument('--interval', type=int, default=60)
    args = p.parse_args()
    fleet = control.Fleet()
    lock = (control.RUNTIME / 'observer.lock').open('a')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('A Honeygain fleet observer is already running')
    while True:
        observe(fleet)
        if args.once:
            return
        time.sleep(max(30, args.interval))


if __name__ == '__main__':
    main()
~~~~~~

### scripts/hg-provider-observer.py

<!-- rebuild-file: scripts/hg-provider-observer.py sha256=df6011522bffec291015a596646590f2866a2955cdd49488ad9337e8ba6e863e -->
~~~~~~python
#!/usr/bin/env python3
"""Record Honeygain provider credits through its official dashboard API."""
import argparse
from decimal import Decimal
import fcntl
import importlib.util
import json
from pathlib import Path
import subprocess
import time

spec = importlib.util.spec_from_file_location('hg_fleet_control', Path(__file__).with_name('hg-fleet-control.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class HoneygainProvider:
    def __init__(self):
        fleet = control.Fleet()
        source = fleet.api('deathadder', '/projects/default/containers/hg1')['container']['environment_variables']
        self.credentials = {'email': source['HONEYGAIN_EMAIL'], 'password': source['HONEYGAIN_PASSWORD']}
        self.token = None

    def request(self, path, method='GET', payload=None, authenticate=True):
        if path not in ('/api/v1/users/tokens', '/api/v2/devices', '/api/v1/earnings/stats', '/api/v1/users/balances'):
            raise RuntimeError('Unrecognized Honeygain endpoint')
        config = 'header = ' + json.dumps('Content-Type: application/json') + '\n'
        config += 'header = ' + json.dumps('Accept: application/json') + '\n'
        if authenticate:
            if not self.token:
                self.login()
            config += 'header = ' + json.dumps('Authorization: Bearer ' + self.token) + '\n'
        if payload is not None:
            config += 'data-binary = ' + json.dumps(json.dumps(payload)) + '\n'
        result = subprocess.run(['curl', '--silent', '--show-error', '--max-time', '20', '--config', '-',
            '--request', method, '--write-out', '\n%{http_code}', 'https://dashboard.honeygain.com' + path],
            input=config, capture_output=True, text=True, timeout=25)
        if result.returncode:
            raise RuntimeError('Honeygain request transport failed')
        raw, status = result.stdout.rsplit('\n', 1)
        if int(status) == 401 and authenticate:
            self.token = None
        if not 200 <= int(status) < 300:
            raise RuntimeError('Honeygain ' + path + ' returned HTTP ' + status)
        return json.loads(raw)

    def login(self):
        data = self.request('/api/v1/users/tokens', 'POST', self.credentials, authenticate=False)
        token = data.get('data', {}).get('access_token')
        if not isinstance(token, str) or not token:
            raise RuntimeError('Honeygain login returned no usable session')
        self.token = token

    def fetch(self):
        return (self.request('/api/v2/devices'), self.request('/api/v1/earnings/stats'),
                self.request('/api/v1/users/balances'))


def build_reading(devices, stats, balances, observed_ms):
    rows = devices['data']
    by_name = {row.get('model'): row for row in rows if row.get('model') in control.DEVICES}
    if len(by_name) != 10 or sum(row.get('model') in control.DEVICES for row in rows) != 10:
        raise RuntimeError('Provider did not return exactly the ten registered fleet devices')
    gathering = sum((Decimal(str(day['gathering']['credits'])) for day in stats.values()), Decimal(0))
    return {'observed_ms': observed_ms, 'gathering_credits': float(gathering),
            'account_balance_credits': balances['data']['payout']['credits'],
            'source': 'Honeygain official dashboard API',
            'devices': [{'device': name, 'credits': by_name[name]['stats']['total_credits'],
                         'ip': by_name[name].get('ip'), 'provider_active': by_name[name]['status'] == 'active'}
                        for name in control.DEVICES]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect-schema', action='store_true')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval', type=int, default=60)
    args = parser.parse_args()
    if args.inspect_schema:
        devices, stats, balances = HoneygainProvider().fetch()
        rows = devices.get('data', [])
        day = stats[sorted(stats)[-1]]
        print(json.dumps({'device_count': len(rows), 'device_title': rows[0].get('title') if rows else None,
            'device_identity_fields': [{k: row.get(k) for k in ('manufacturer', 'model', 'title')} for row in rows],
            'device_status': rows[0].get('status') if rows else None,
            'device_stats': rows[0].get('stats') if rows else None,
            'day_stats': day, 'balances': balances.get('data')}, indent=2))
        return
    control.RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = (control.RUNTIME / 'provider-observer.lock').open('a')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('A Honeygain provider observer is already running')
    provider = None
    failures = 0
    while True:
        started = time.monotonic()
        try:
            if provider is None:
                provider = HoneygainProvider()
            devices, stats, balances = provider.fetch()
            observed_ms = int(time.time()*1000)
            result = control.record_provider(build_reading(devices, stats, balances, observed_ms))
            # Retain only the provider's traffic/credit measurements, never auth responses.
            control.Fleet.write('provider-api-traffic-latest.json', {
                'observed_ms': observed_ms, 'source': 'Honeygain official dashboard API',
                'days': {date: {'gathering_credits': day['gathering']['credits'],
                                'gathering_traffic_bytes': day['gathering']['traffic']}
                         for date, day in stats.items()},
                'devices': [{'device': row['model'], 'total_traffic_bytes': row['stats']['total_traffic'],
                             'total_credits': row['stats']['total_credits']}
                            for row in devices['data'] if row.get('model') in control.DEVICES]})
            control.Fleet.write('provider-feed-status.json', {'checked_at': control.now(),
                'observed_ms': observed_ms, 'state': 'ok', 'interval_seconds': max(60, args.interval),
                'authentication_storage': 'process memory only'})
            print(json.dumps(result), flush=True)
            failures = 0
        except Exception as error:
            failures += 1
            message = str(error) if isinstance(error, RuntimeError) else type(error).__name__
            control.Fleet.write('provider-feed-status.json', {'checked_at': control.now(),
                'state': 'error', 'error': message, 'consecutive_failures': failures})
            print(json.dumps({'state': 'error', 'error': message}), flush=True)
            if args.once:
                raise SystemExit(1)
        if args.once:
            return
        interval = min(1800, max(60, args.interval) * (2 ** min(failures, 5)))
        time.sleep(max(1, interval - (time.monotonic()-started)))


if __name__ == '__main__':
    main()
~~~~~~

### scripts/initialize-recording.py

<!-- rebuild-file: scripts/initialize-recording.py sha256=4ac3beac391fd2f7e3f52896b62ab2a201a40268161f10e004886832ac984f74 -->
~~~~~~python
#!/usr/bin/env python3
"""Initialize a fresh shared ledger without resetting any existing experiment."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
os.umask(0o077)
data=Path.home()/'.hg1';root=data/'fleet-tests';root.mkdir(parents=True,exist_ok=True)
current=root/'current.json'
if current.exists():raise SystemExit('Existing experiment preserved. Do not reset it to repair a display.')
provider=data/'hg-fleet/provider-latest.json'
hg=json.loads(provider.read_text()) if provider.exists() else {}
now=int(time.time()*1000);started=datetime.fromtimestamp(now/1000,timezone.utc).isoformat();ident=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
record=dict(id=ident,started_at=started,started_ms=now,status='measuring',phase='bandwidth-test',
    ps=dict(organization='hyperlane',project='default',group='ps-test-us',desired=10,baseline_provider_bytes=None),
    hg=dict(organization='deathadder',desired=10,version='0.6.6',baseline_provider_gathering_credits=hg.get('gathering_credits'),
        baseline_provider_observed_ms=hg.get('observed_ms'),baseline_started_ms=hg.get('observed_ms')),interventions=[])
current.write_text(json.dumps(record,indent=2)+'\n')
(root/'network-state.json').write_text(json.dumps(dict(experiment_id=ident,rx=0,tx=0,last={})))
print('Started new recording metadata '+ident+'; historical values were not invented.')
~~~~~~

### scripts/install-services.py

<!-- rebuild-file: scripts/install-services.py sha256=3c75ac6e7c82f8b1e06104d59b02c13b073685e0c5f19a4a25a3e7534a7ee4e9 -->
~~~~~~python
#!/usr/bin/env python3
"""Install only explicitly named local observers; never alter Salad workloads."""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess
root=Path(__file__).resolve().parents[1];data=Path.home()/'.hg1';agents=Path.home()/'Library/LaunchAgents'
jobs={
 'dashboard':('com.cosmosgeek.salad-bandwidth-dashboard',['-m','dashboard.server','--port','8787','--data-dir',str(data),'--no-poll'],'dashboard'),
 'hg-provider':('com.cosmosgeek.salad-hg-provider-observer',[str(root/'scripts/hg-provider-observer.py'),'--interval','60'],'hg-fleet/provider-observer'),
 'hg-fleet':('com.cosmosgeek.salad-hg-fleet-observer',[str(root/'scripts/hg-fleet-observer.py'),'--interval','60'],'hg-fleet/observer'),
 'fleet':('com.cosmosgeek.salad-fleet-test-recorder',[str(root/'fleet-test-recorder.py'),'run'],'fleet-tests/recorder'),
 'ps':('com.cosmosgeek.ps1-recorder',['-B',str(root/'ps1-native-recorder.py')],'packetstream/native-recorder'),
 'pr':('com.cosmosgeek.proxyrack-recorder',['-B',str(root/'proxyrack.py'),'observe'],'proxyrack/observer'),
 'rp':('com.cosmosgeek.repocket-recorder',['-B',str(root/'repocket-monitor/observe.py')],'repocket/observer'),
 'rfm':('com.cosmosgeek.earnfm-recorder',['-B',str(root/'scripts/earnfm-recorder.py')],'earnfm/recorder'),
 'tm':('com.cosmosgeek.tm-observer',['-B',str(root/'traffmonetizer/observer.py')],'traffmonetizer/observer')}
p=argparse.ArgumentParser(description=__doc__);p.add_argument('services',nargs='+',choices=jobs);p.add_argument('--write-only',action='store_true');args=p.parse_args()
env=dict(PYTHONPATH=str(root),PYTHONDONTWRITEBYTECODE='1',HG_FLEET_DIR=str(data/'hg-fleet'),HG_KEYCHAIN_HELPER=str(root/'.runtime/keychain-store'),PS_ORGANIZATION='hyperlane',PS_PROJECT='default',PS_GROUP='ps-test-us')
os.umask(0o077);agents.mkdir(parents=True,exist_ok=True)
for name in args.services:
 label,arguments,logs=jobs[name]
 for value in arguments:
  if value.endswith('.py') and not Path(value).exists():raise SystemExit('Missing embedded source: '+value)
 (data/logs).parent.mkdir(parents=True,exist_ok=True)
 document=dict(Label=label,ProgramArguments=['/usr/bin/python3',*arguments],WorkingDirectory=str(root),EnvironmentVariables=env,
     KeepAlive=True,RunAtLoad=True,ThrottleInterval=15,StandardOutPath=str(data/(logs+'.out.log')),StandardErrorPath=str(data/(logs+'.err.log')))
 path=agents/(label+'.plist');path.write_bytes(plistlib.dumps(document));path.chmod(0o600)
 if not args.write_only:
  domain='gui/'+str(os.getuid())
  subprocess.run(['launchctl','bootout',domain+'/'+label],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  subprocess.run(['launchctl','bootstrap',domain,str(path)],check=True)
 print(('Wrote ' if args.write_only else 'Started ')+label)
~~~~~~

### scripts/keychain-store.swift

<!-- rebuild-file: scripts/keychain-store.swift sha256=490eadaf1afb87a0f64bf6248254ccc48ac1171af9e2fc4c796c74c12c5ca045 -->
~~~~~~swift
import Foundation
import Security

func fail(_ message: String, code: Int32 = 2) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(code)
}

func option(_ name: String) -> String? {
    let arguments = CommandLine.arguments
    guard let index = arguments.firstIndex(of: name), index + 1 < arguments.count else {
        return nil
    }
    return arguments[index + 1]
}

guard let service = option("--service"), !service.isEmpty else {
    fail("missing --service")
}
guard let account = option("--account"), !account.isEmpty else {
    fail("missing --account")
}

let query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrService as String: service,
    kSecAttrAccount as String: account,
]

let wantsRead = CommandLine.arguments.contains("--read")
let wantsDelete = CommandLine.arguments.contains("--delete")
guard !(wantsRead && wantsDelete) else {
    fail("choose only one operation")
}

if wantsRead {
    var readQuery = query
    readQuery[kSecReturnData as String] = true
    readQuery[kSecMatchLimit as String] = kSecMatchLimitOne
    var result: CFTypeRef?
    let status = SecItemCopyMatching(readQuery as CFDictionary, &result)
    guard status == errSecSuccess, let password = result as? Data else {
        let explanation = SecCopyErrorMessageString(status, nil) as String? ?? "unknown error"
        fail("keychain error \(status): \(explanation)", code: 1)
    }
    FileHandle.standardOutput.write(password)
    exit(0)
}

if wantsDelete {
    let status = SecItemDelete(query as CFDictionary)
    guard status == errSecSuccess || status == errSecItemNotFound else {
        let explanation = SecCopyErrorMessageString(status, nil) as String? ?? "unknown error"
        fail("keychain error \(status): \(explanation)", code: 1)
    }
    exit(0)
}

var password = FileHandle.standardInput.readDataToEndOfFile()
while password.last == 10 || password.last == 13 {
    password.removeLast()
}
guard !password.isEmpty else {
    fail("empty password data")
}

let update: [String: Any] = [
    kSecValueData as String: password,
]

var status = SecItemUpdate(query as CFDictionary, update as CFDictionary)
if status == errSecItemNotFound {
    var item = query
    item[kSecValueData as String] = password
    status = SecItemAdd(item as CFDictionary, nil)
}

guard status == errSecSuccess else {
    let explanation = SecCopyErrorMessageString(status, nil) as String? ?? "unknown error"
    fail("keychain error \(status): \(explanation)", code: 1)
}
~~~~~~

### scripts/publish-repocket-reading.py

<!-- rebuild-file: scripts/publish-repocket-reading.py sha256=bb310b4accf6292b40fd6accc5139173cdbdc4cc3230203919be9d1cb9970053 -->
~~~~~~python
#!/usr/bin/env python3
"""Save numbers the operator has just read on the signed-in Repocket dashboard."""
import argparse
import json
import os
from pathlib import Path
import re
import time
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--traffic',help='Exact displayed provider-day traffic including unit')
p.add_argument('--earned',help='Exact displayed provider-day earned amount including currency')
args=p.parse_args();os.umask(0o077)
traffic=args.traffic or input('Provider-day traffic exactly as displayed, with unit: ').strip()
earned=args.earned or input('Provider-day earnings exactly as displayed, with currency: ').strip()
if not all(re.search(r'\d',x) for x in (traffic,earned)):raise SystemExit('Read the real numeric values first; placeholders were not saved.')
root=Path.home()/'.hg1/repocket';root.mkdir(parents=True,exist_ok=True)
value=dict(observed_ms=int(time.time()*1000),today_traffic_text=traffic,today_earned_text=earned,source='Fresh operator reading of the Repocket provider-day account dashboard')
temporary=root/'provider.tmp';temporary.write_text(json.dumps(value));temporary.replace(root/'provider.json')
print('Saved actual provider reading; it will become stale normally until refreshed.')
~~~~~~

### scripts/rebuild-cloud.py

<!-- rebuild-file: scripts/rebuild-cloud.py sha256=4fde37bb6ea6402a3ab1ce7fe46d935503ee7b6038af0f3c2ec48c0c401c08b9 -->
~~~~~~python
#!/usr/bin/env python3
"""Recreate only the documented Honeygain or PacketStream deployment."""
import argparse
import base64
import getpass
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / '.hg1'
PS_IMAGE = 'docker.io/packetstream/psclient@sha256:6e6a2cefe9f49c33f6c9d4bd41d21daf20c4767f2c66e82f57a5960ec9923987'

def api(key, org, path, method='GET', body=None):
    config = 'header = '+json.dumps('Salad-Api-Key: '+key)+'\nheader = "Content-Type: application/json"\n'
    if body is not None:
        config += 'data-binary = '+json.dumps(json.dumps(body))+'\n'
    result = subprocess.run(['curl','-sS','--max-time','30','--config','-','--request',method,'--write-out','\n%{http_code}',
        'https://api.salad.com/api/public/organizations/'+org+path],input=config,text=True,capture_output=True,timeout=35)
    if result.returncode:
        raise RuntimeError('Salad transport failed')
    raw, code = result.stdout.rsplit('\n',1)
    if not 200 <= int(code) < 300:
        raise RuntimeError(f'Salad {method} {org}{path}: HTTP {code}')
    return json.loads(raw) if raw.strip() else {}

def specifications(protocol, secrets):
    if protocol == 'honeygain':
        spec=importlib.util.spec_from_file_location('hg_control',ROOT/'scripts/hg-fleet-control.py')
        hg=importlib.util.module_from_spec(spec);spec.loader.exec_module(hg)
        return 'deathadder', [dict(name=group,display_name='HG1 Native 0.6.6' if i==0 else 'HG Solo %02d'%(i+1),replicas=1,
            country_codes=['us'],restart_policy='always',autostart_policy=False,
            container=dict(image=hg.IMAGE,command=hg.recovery_command(),image_caching=True,priority='batch' if i==0 else 'low',
                resources=dict(cpu=1,memory=1024,shm_size=64,gpu_classes=[]),
                environment_variables=dict(HONEYGAIN_EMAIL=secrets['email'],HONEYGAIN_PASSWORD=secrets['password'],HONEYGAIN_DEVICE_NAME=hg.DEVICES[i])))
            for i,group in enumerate(hg.GROUPS)]
    code=(ROOT/'packetstream-monitor/start-with-recovery.sh').read_bytes()
    encoded=base64.b64encode(code).decode()
    command=['/bin/bash','-c','umask 077; printf "%s" "$@" | base64 -d > /tmp/ps-self-recovery.sh; exec /bin/bash /tmp/ps-self-recovery.sh',
             'policy-start',*[encoded[i:i+900] for i in range(0,len(encoded),900)]]
    assert len(command)<=100 and max(map(len,command))<=1000
    return 'hyperlane', [dict(name='ps-test-us',display_name='PS Test US',replicas=10,country_codes=['us'],
        restart_policy='always',autostart_policy=False,container=dict(image=PS_IMAGE,command=command,image_caching=True,priority='batch',
            resources=dict(cpu=1,memory=1024,shm_size=64,gpu_classes=[]),environment_variables=dict(CID=secrets['cid'])))]

def verify(actual, desired, compare_account):
    container=actual.get('container',{});expected=desired['container']
    different=[k for k in ('name','display_name','replicas','country_codes','restart_policy','autostart_policy') if actual.get(k)!=desired[k]]
    different += ['container.'+k for k in ('image','command','image_caching') if container.get(k)!=expected[k]]
    different += ['resources.'+k for k,v in expected['resources'].items() if container.get('resources',{}).get(k)!=v]
    if actual.get('priority')!=expected['priority']:different.append('priority')
    different += [k for k in ('networking','readiness_probe','liveness_probe','startup_probe') if actual.get(k) or container.get(k)]
    environment=container.get('environment_variables',{});wanted=expected['environment_variables']
    if set(environment)!=set(wanted) or not all(isinstance(v,str) and v for v in environment.values()):
        different.append('required account environment')
    elif compare_account and environment!=wanted:
        different.append('account environment')
    elif 'HONEYGAIN_DEVICE_NAME' in wanted and environment['HONEYGAIN_DEVICE_NAME']!=wanted['HONEYGAIN_DEVICE_NAME']:
        different.append('Honeygain registration')
    if different:
        raise RuntimeError('Deployment differs in '+', '.join(different)+': '+desired['name']+'; inspect it instead of overwriting it')

def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.chmod(0o600);temporary.replace(path)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('protocol',choices=['honeygain','packetstream'])
    p.add_argument('action',choices=['plan','create','bind'])
    args=p.parse_args();os.umask(0o077)
    values=dict(email='<HONEYGAIN_EMAIL>',password='<HONEYGAIN_PASSWORD>',cid='<PACKETSTREAM_CID>')
    if args.action=='create':
        if args.protocol=='honeygain':
            values.update(email=input('Honeygain account email: ').strip(),password=getpass.getpass('Honeygain password: '))
        else:
            values['cid']=getpass.getpass('PacketStream CID from your account: ').strip()
        if any(not value for value in values.values()):raise ValueError('An account value is empty')
    org, specs=specifications(args.protocol,values)
    if args.action=='plan':
        for item in specs:
            print(json.dumps({k:item[k] for k in ('name','replicas','country_codes','restart_policy','autostart_policy')},sort_keys=True))
        print('Offline plan only; no account access, files, or cloud changes.')
        return
    helper=ROOT/'.runtime/keychain-store'
    key=subprocess.check_output([str(helper),'--read','--service','salad-bandwidth-api','--account',getpass.getuser()],text=True).strip()
    existing={g['name']:g for g in api(key,org,'/projects/default/containers').get('items',[])}
    if args.protocol=='honeygain' and args.action=='create':
        registrations={g['container']['environment_variables']['HONEYGAIN_DEVICE_NAME'] for g in specs}
        intended={g['name'] for g in specs}
        for other_org in ('deathadder','cosmosgeeketh','hyperlane'):
            for group in api(key,other_org,'/projects/default/containers').get('items',[]):
                device=group.get('container',{}).get('environment_variables',{}).get('HONEYGAIN_DEVICE_NAME')
                if device in registrations and not (other_org==org and group['name'] in intended):
                    if api(key,other_org,'/projects/default/containers/'+group['name']+'/instances').get('instances'):
                        raise RuntimeError('A Honeygain registration is already running in '+other_org+'/'+group['name'])
    receipts=[]
    for desired in specs:
        name=desired['name'];path='/projects/default/containers/'+name
        if name in existing:
            actual=api(key,org,path)
        elif args.action=='bind':
            raise RuntimeError('Cannot bind a missing group: '+name)
        else:
            try:
                actual=api(key,org,'/projects/default/containers','POST',desired)
            except RuntimeError:
                # A rejected response can follow an applied creation. Read back once; never duplicate.
                actual=api(key,org,path)
        verify(actual,desired,args.action=='create')
        if args.action=='create':
            for _ in range(60):
                actual=api(key,org,path);state=actual.get('current_state',{}).get('status')
                if state=='stopped':
                    api(key,org,path+'/start','POST');break
                if state in ('running','deploying','starting'):break
                time.sleep(5)
            else:raise RuntimeError('Group did not become startable within five minutes: '+name)
        receipts.append(dict(organization=org,group=name,id=actual['id'],replicas=desired['replicas'],image=actual['container']['image'],version=actual['version']))
    if args.protocol=='packetstream':
        receipt=receipts[0]
        write(DATA/'packetstream/observer-target.json',dict(mode='native-census',organization=org,project='default',group=receipt['group'],group_id=receipt['id']))
    else:
        write(DATA/'hg-fleet/deployment.json',receipts)
    print(json.dumps(receipts,indent=2))
    print('Binding saved. Verify native logs/client acceptance before claiming the fleet is working.')

if __name__=='__main__':main()
~~~~~~

### scripts/save-secret.py

<!-- rebuild-file: scripts/save-secret.py sha256=98e37bb083dd0c10773d1dfdc187780af29f7a62beb361cfc99ec0fc92822e9e -->
~~~~~~python
#!/usr/bin/env python3
"""Save an operator-supplied value to the existing macOS Keychain helper."""
import argparse
import getpass
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__);p.add_argument('service');args=p.parse_args()
helper=Path(__file__).resolve().parents[1]/'.runtime/keychain-store'
secret=getpass.getpass('Value for '+args.service+' (hidden): ')
if not secret:raise SystemExit('Empty secret not saved')
subprocess.run([str(helper),'--service',args.service,'--account',getpass.getuser()],input=secret,text=True,check=True)
print('Saved '+args.service+'; value not printed.')
~~~~~~

### traffmonetizer/control.py

<!-- rebuild-file: traffmonetizer/control.py sha256=e3c8774bf4e75e9b25133152f8d42d24f7410358944d07245fa409506e82799e -->
~~~~~~python
"""Operate only the SSH4 TraffMonetizer deployment; never print credentials."""
import argparse
from datetime import datetime, timezone
import getpass
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / ".hg1/traffmonetizer"
ORGANIZATION = "ssh4"
GROUP = "tm-test-us"
GROUP_PATH = "/projects/default/containers/" + GROUP
IMAGE = "docker.io/cosmosgeek0/salad-bandwidth-stack@sha256:d75e26d28fbb9352829eb41440a38b59d5f9d3ecb4967cc0414bb3bbc50f1c2c"


def keychain(service):
    return subprocess.check_output([str(ROOT / ".runtime/keychain-store"), "--read", "--service",
                                    service, "--account", getpass.getuser()], text=True).strip()


def api(path, method="GET", body=None):
    if not (path == "/projects/default/containers" or path == GROUP_PATH or path.startswith(GROUP_PATH + "/") or path == "/log-entries"):
        raise ValueError("Outside the SSH4 TraffMonetizer scope")
    key = keychain("salad-bandwidth-api")
    media = "application/merge-patch+json" if method == "PATCH" else "application/json"
    config = "header = " + json.dumps("Salad-Api-Key: " + key) + "\nheader = " + json.dumps("Content-Type: " + media) + "\n"
    if body is not None:
        config += "data-binary = " + json.dumps(json.dumps(body)) + "\n"
    result = subprocess.run(["curl", "-sS", "--max-time", "25", "--config", "-", "--request", method,
        "--write-out", "\n%{http_code}", "https://api.salad.com/api/public/organizations/ssh4" + path],
        input=config, capture_output=True, text=True, timeout=30)
    raw, status = result.stdout.rsplit("\n", 1)
    if result.returncode or not 200 <= int(status) < 300:
        raise RuntimeError("Salad " + method + " " + path + " returned HTTP " + status)
    return json.loads(raw) if raw.strip() else {}


def safe_group(group):
    return {key: group.get(key) for key in ("id", "name", "version", "replicas", "country_codes", "current_state")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "scale", "update", "status"))
    parser.add_argument("--replicas", type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.replicas <= 10:
        parser.error("This task is authorized for one through ten workers")
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    record = DATA / "deployment.json"
    if args.action == "create":
        if any(group["name"] == GROUP for group in api("/projects/default/containers").get("items", [])):
            raise RuntimeError("TraffMonetizer group already exists; inspect it instead")
        payload = {"name": GROUP, "display_name": "TM", "replicas": args.replicas,
            "autostart_policy": True, "restart_policy": "always", "country_codes": ["us"],
            "container": {"image": IMAGE, "priority": "batch", "resources": {"cpu": 1, "memory": 1024},
                          "environment_variables": {"TM_TOKEN": keychain("salad-traffmonetizer-token")}}}
        try:
            group = api("/projects/default/containers", "POST", payload)
        except RuntimeError:
            group = api(GROUP_PATH)
            if (group.get("container", {}).get("image") != IMAGE or group.get("country_codes") != ["us"]
                    or group.get("container", {}).get("environment_variables", {}).get("TM_TOKEN") != payload["container"]["environment_variables"]["TM_TOKEN"]):
                raise RuntimeError("Uncertain create response did not match this deployment") from None
        saved = {"organization": ORGANIZATION, "project": "default", "group": GROUP, "group_id": group["id"],
                 "image": IMAGE, "started_at": datetime.now(timezone.utc).isoformat(),
                 "desired_replicas": 10, "provider_baseline_usd": 0.0268,
                 "provider_baseline_source": "Observed signed-in dashboard before this deployment"}
        record.write_text(json.dumps(saved, indent=2))
        record.chmod(0o600)
    else:
        group = api(GROUP_PATH)
        if not record.exists() or json.loads(record.read_text())["group_id"] != group["id"]:
            raise RuntimeError("Deployment identity does not match this task")
        if args.action == "scale":
            if group["container"]["image"] != IMAGE or group.get("pending_change"):
                raise RuntimeError("The runtime image update is still applying; do not expand the old runtime")
            api(GROUP_PATH, "PATCH", {"replicas": args.replicas})
            group = api(GROUP_PATH)
            if group["replicas"] != args.replicas:
                raise RuntimeError("Replica change was not confirmed")
        if args.action == "update":
            api(GROUP_PATH, "PATCH", {"container": {"image": IMAGE}})
            group = api(GROUP_PATH)
            if group["container"]["image"] != IMAGE:
                if group.get("pending_change"):
                    print("Image update accepted and still preparing; verify the applied runtime before scaling.")
                    print(json.dumps(safe_group(group), indent=2))
                    return
                raise RuntimeError("Image update was not confirmed")
            saved = json.loads(record.read_text())
            saved["image"] = IMAGE
            record.write_text(json.dumps(saved, indent=2))
    print(json.dumps(safe_group(group), indent=2))
    print("instances", json.dumps([{key: value.get(key) for key in ("id", "machine_id", "state", "version", "ready")}
                                   for value in api(GROUP_PATH + "/instances").get("instances", [])]))


if __name__ == "__main__":
    main()
~~~~~~

### traffmonetizer/observer.py

<!-- rebuild-file: traffmonetizer/observer.py sha256=44cf8579c09486a448497c87191b81cba74e39bfd230a84681ed8a7dd9ad6bca -->
~~~~~~python
"""Read SSH4 logs and provider metrics; publish a credential-free dashboard snapshot."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import urllib.request

from control import DATA, GROUP_PATH, api, keychain


def millis(value):
    value = re.sub(r"\.(\d+)", lambda m: "." + (m[1] + "000000")[:6], value, count=1)
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def iso(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def database(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS samples (
          run TEXT, seq INTEGER, instance TEXT, machine TEXT, device TEXT, ip TEXT,
          time_ms INTEGER, start_ms INTEGER, interval_ms REAL, rx INTEGER, tx INTEGER,
          total_rx INTEGER, total_tx INTEGER, state TEXT, status_ms INTEGER,
          client_run INTEGER, native_in TEXT, native_out TEXT, requests INTEGER, error TEXT,
          PRIMARY KEY(run,seq));
        CREATE INDEX IF NOT EXISTS sample_time ON samples(time_ms);
        CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY,time_ms INTEGER,payload TEXT);
        CREATE TABLE IF NOT EXISTS provider (time_ms INTEGER PRIMARY KEY,payload TEXT);
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT);
    """)
    return db


def fetch_logs(start, end):
    cursor = start
    for _ in range(500):
        response = api("/log-entries", "POST", {"query": 'resource.type = "container" and resource.labels.project_name = "default" and resource.labels.container_group_name = "tm-test-us" and text_log startswith "TM_V1 "',
            "start_time": iso(cursor), "end_time": iso(end), "page_size": 100, "sort_order": "asc"})
        page = response.get("items")
        if not isinstance(page, list):
            raise RuntimeError("Salad returned an invalid log page")
        yield page
        if len(page) < 100:
            return
        following = max(millis(item["time"]) for item in page)
        if following <= cursor:
            raise RuntimeError("A full log page cannot advance; measurements were not skipped")
        cursor = following
    raise RuntimeError("Log backlog exceeded the bounded fetch window")


def ingest(db, items):
    for item in items:
        text = item.get("text_log", "")
        if not text.startswith("TM_V1 "):
            continue
        try:
            record = json.loads(text[6:])
            kind = record["kind"]
            instance, machine = record["instance"], record["machine"]
            run = instance + "/" + str(record["observer_start_ms"])
            if kind == "batch":
                rows = record["samples"]
            elif kind == "sample":  # Preserve measurements made by the initial canary.
                rows = [[record["seq"], record["time_ms"], record["start_ms"], record["interval_ms"],
                    record["rx_bytes"], record["tx_bytes"], record["total_rx_bytes"], record["total_tx_bytes"],
                    record["state"], record["status_ms"], record["client_run"], record["connected"], record["accepting"]]]
            else:
                encoded = json.dumps(record, sort_keys=True)
                db.execute("INSERT OR IGNORE INTO events VALUES (?,?,?)",
                           (hashlib.sha256(encoded.encode()).hexdigest(), record["time_ms"], encoded))
                continue
            for row in rows:
                if len(row) != 13 or not math.isfinite(row[3]) or row[3] <= 0:
                    raise ValueError("Invalid measurement interval")
                if any(value is not None and (not isinstance(value, (int, float)) or value < 0) for value in row[4:8]):
                    raise ValueError("Invalid traffic counter")
                state = row[8]
                if state not in ("starting", "connected", "disconnected") or state == "connected" and not (row[11] and row[12]):
                    raise ValueError("Invalid client state")
                db.execute("INSERT OR IGNORE INTO samples VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (run, row[0], instance, machine, record.get("device"), record.get("ip"), row[1], row[2], row[3],
                     row[4], row[5], row[6], row[7], state, row[9], row[10], record.get("native_inbound"),
                     record.get("native_outgoing"), record.get("native_requests"), record.get("error")))
        except (KeyError, ValueError, TypeError) as error:
            raise RuntimeError("A TraffMonetizer record was invalid: " + type(error).__name__) from None
    db.commit()


def provider_request(path):
    if path not in ("/api/app_user/get_balance", "/api/dashboard/get_graph_stat?period=month"):
        raise ValueError("Provider request is outside the read-only metrics scope")
    request = urllib.request.Request("https://data.traffmonetizer.com" + path,
        headers={"Authorization": "Bearer " + keychain("salad-traffmonetizer-session"), "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.load(response)
        refreshed = response.headers.get("Authorization", "")
    if refreshed.startswith("Bearer "):
        from control import ROOT
        import getpass
        subprocess.run([str(ROOT / ".runtime/keychain-store"), "--service", "salad-traffmonetizer-session",
            "--account", getpass.getuser()], input=refreshed[7:], text=True, capture_output=True, check=True)
    return result


def provider_reading(deployment):
    balance = provider_request("/api/app_user/get_balance")["data"]
    days = provider_request("/api/dashboard/get_graph_stat?period=month")
    start_day = deployment["started_at"][:10]
    selected = [day for day in days if day["date"] >= start_day]
    return {"observed_ms": int(time.time() * 1000), "balance_usd": balance["balance"],
            "balance_change_usd": balance["balance"] - deployment["provider_baseline_usd"],
            "credited_bytes": sum(day["traffic"] for day in selected) - deployment.get("provider_baseline_bytes", 0),
            "credited_usd": sum(day["earning"] for day in selected) - deployment.get("provider_baseline_earned_usd", 0),
            "requests": sum(day["requestsCount"] for day in selected), "days": selected,
            "source": "TraffMonetizer authenticated dashboard API", "scope": "Provider account totals less the saved ten-worker test baseline. Account balance is separate."}


def snapshot(db, deployment, members, errors):
    now = int(time.time() * 1000)
    test_start = deployment.get("measurement_started_ms", millis(deployment["started_at"]))
    current = []
    for member in members:
        row = db.execute("SELECT * FROM samples WHERE instance=? ORDER BY time_ms DESC,seq DESC LIMIT 1", (member["id"],)).fetchone()
        value = dict(row) if row else {"instance": member["id"], "machine": member["machine_id"], "state": "awaiting_sample"}
        age = now - value["time_ms"] if row else None
        value.update(salad_state=member["state"], sample_age_ms=age,
                     fresh=age is not None and -5000 <= age <= 45000)
        measured = db.execute("SELECT SUM(rx) rx,SUM(tx) tx,SUM(interval_ms) duration FROM samples WHERE instance=? AND start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL", (member["id"], test_start)).fetchone()
        value.update(test_rx=measured["rx"], test_tx=measured["tx"], test_duration_ms=measured["duration"],
                     raw_mb_per_minute=None, native_recent_bytes=None, native_recent_requests=None, native_recent_ms=None)
        if row:
            end = value["time_ms"]
            recent = db.execute("SELECT SUM(rx+tx) bytes,SUM(interval_ms) duration FROM samples WHERE run=? AND time_ms>? AND time_ms<=? AND start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL",
                                (value["run"], end - 60000, end, test_start)).fetchone()
            if recent["duration"]:
                value["raw_mb_per_minute"] = recent["bytes"] / 1e6 * 60000 / recent["duration"]
            base = db.execute("SELECT time_ms,native_in,native_out,requests FROM samples WHERE run=? AND client_run=? AND time_ms>=? AND time_ms<=? AND native_in IS NOT NULL AND native_out IS NOT NULL AND requests IS NOT NULL ORDER BY seq LIMIT 1",
                              (value["run"], value["client_run"], max(test_start, end - 900000), end)).fetchone()
            if base and end > base["time_ms"]:
                before = [base[key] for key in ("native_in", "native_out", "requests")]
                after = [value[key] for key in ("native_in", "native_out", "requests")]
                if all(str(number).isdigit() for number in before + after):
                    deltas = [int(last) - int(first) for first, last in zip(before, after)]
                    if min(deltas) >= 0:
                        value.update(native_recent_bytes=deltas[0] + deltas[1], native_recent_requests=deltas[2],
                                     native_recent_ms=end - base["time_ms"])
        value["working"] = bool(not errors.get("recorder") and value["fresh"] and value["state"] == "connected" and member["state"] == "running")
        current.append(value)
    totals = db.execute("SELECT COALESCE(SUM(rx),0) rx,COALESCE(SUM(tx),0) tx,COUNT(*) samples,MIN(time_ms) first_ms,MAX(time_ms) last_ms FROM samples WHERE start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL", (test_start,)).fetchone()
    minutes = {}
    for row in db.execute("SELECT CAST(time_ms/60000 AS INTEGER)*60000 minute,run,machine,instance,MAX(device) device,SUM(rx) rx,SUM(tx) tx,SUM(interval_ms) duration_ms,COUNT(*) samples FROM samples WHERE time_ms>=? AND start_ms>=? AND rx IS NOT NULL AND tx IS NOT NULL GROUP BY minute,run,machine,instance ORDER BY minute", (now - 3600000, test_start)):
        minute = minutes.setdefault(row["minute"], {"time_ms": row["minute"], "rx_bytes": 0, "tx_bytes": 0, "samples": 0, "workers": []})
        minute["rx_bytes"] += row["rx"]
        minute["tx_bytes"] += row["tx"]
        minute["samples"] += row["samples"]
        minute["workers"].append(dict(row))
    provider_row = db.execute("SELECT payload FROM provider ORDER BY time_ms DESC LIMIT 1").fetchone()
    provider = json.loads(provider_row[0]) if provider_row else None
    if provider:
        provider["age_ms"] = now - provider["observed_ms"]
        provider["fresh"] = provider["age_ms"] <= 180000 and not errors.get("provider")
    events = [json.loads(row[0]) for row in db.execute("SELECT payload FROM events WHERE json_extract(payload,'$.kind') NOT IN ('client_log') ORDER BY time_ms DESC LIMIT 20")]
    return {"schema_version": 1, "provider": "traffmonetizer", "title": "TM", "generated_ms": now,
            "deployment": deployment, "recorded": dict(totals), "workers": current,
            "running": sum(row["salad_state"] == "running" for row in current),
            "working": sum(row["working"] for row in current), "minutes": list(minutes.values()),
            "credited": provider, "events": events, "errors": errors,
            "measurement": "Raw interface RX and TX measured every second inside each container. Transported in ten-sample batches. Credited traffic comes separately from the provider account API."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True)
    lock = (DATA / "observer.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    deployment = json.loads((DATA / "deployment.json").read_text())
    db = database(DATA / "traffic.sqlite3")
    cursor_row = db.execute("SELECT value FROM meta WHERE key='cursor'").fetchone()
    cursor = int(cursor_row[0]) if cursor_row else millis(deployment["started_at"])
    members = []
    provider_at = 0
    reconcile_at = 0
    while True:
        began = time.monotonic()
        now = int(time.time() * 1000)
        errors = {}
        try:
            current_deployment = json.loads((DATA / "deployment.json").read_text())
            if current_deployment["group_id"] != deployment["group_id"]:
                raise RuntimeError("Saved deployment identity changed")
            deployment = current_deployment
            group = api(GROUP_PATH)
            if group["id"] != deployment["group_id"]:
                raise RuntimeError("Deployment identity changed")
            members = api(GROUP_PATH + "/instances")["instances"]
            start = max(millis(deployment["started_at"]), cursor - 120000)
            if time.monotonic() >= reconcile_at:
                start = min(start, max(millis(deployment["started_at"]), now - 600000))
                reconcile_at = time.monotonic() + 300
            for page in fetch_logs(start, now):
                ingest(db, page)
            cursor = now
            db.execute("INSERT OR REPLACE INTO meta VALUES ('cursor',?)", (str(cursor),))
            db.commit()
        except Exception as error:
            errors["recorder"] = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        if time.monotonic() >= provider_at:
            try:
                reading = provider_reading(deployment)
                db.execute("INSERT OR REPLACE INTO provider VALUES (?,?)", (reading["observed_ms"], json.dumps(reading)))
                db.commit()
                db.execute("DELETE FROM meta WHERE key='provider_error'")
            except Exception as error:
                db.execute("INSERT OR REPLACE INTO meta VALUES ('provider_error',?)", (type(error).__name__,))
            db.commit()
            provider_at = time.monotonic() + 60
        provider_error = db.execute("SELECT value FROM meta WHERE key='provider_error'").fetchone()
        if provider_error:
            errors["provider"] = provider_error[0]
        result = snapshot(db, deployment, members, errors)
        temporary = DATA / "latest.tmp"
        temporary.write_text(json.dumps(result, separators=(",", ":")))
        os.replace(temporary, DATA / "latest.json")
        print(json.dumps({"time_ms": result["generated_ms"], "running": result["running"], "working": result["working"], "samples": result["recorded"]["samples"], "errors": errors}), flush=True)
        if args.once:
            break
        time.sleep(max(1, 15 - (time.monotonic() - began)))


if __name__ == "__main__":
    main()
~~~~~~
