# Recovery verification

## Recorder process restrictions — 8 September 2026 UTC

The 13 recorder units were checked against their live fragments, then given no-new-privileges, empty capabilities, private devices/tmp, restricted kernel/namespace/realtime/SUID operations, native syscall architecture and limited address families. Their filesystem namespaces are read-only except for the named data/cache paths. After one TM canary and the remaining recorder restarts, all 13 actual processes showed NoNewPrivs=1, Seccomp=2 and an empty CapBnd, with no automatic restarts. No application, provider recovery policy, account credential, UI, SSH, tunnel or Tokyo change was made by this recorder hardening step.

A canary filesystem probe could create/remove its own temporary file in the TM data directory but was denied writing the RP directory. TM continued publishing fresh samples. Verification then caught the shared fleet recorder's background cost thread failing with `sqlite3.OperationalError: attempt to write a readonly database`: its existing cost database lives directly under `.hg1`, not `fleet-tests`. The fleet unit's write exception was corrected for the parent required by SQLite/WAL, with every other protocol directory and the compatibility database mounted read-only. Only that recorder was restarted for this correction. Existing database/history files were not moved or reset.

AWS role reads confirmed EC2-only trust and GetSecretValue/PutSecretValue limited to the one Salad recorder secret, with no attached managed role policies. Persistent host journaling and automatic-update services were enabled. This does not verify administrator MFA, the complete operator policy set, off-host CloudTrail/security alerts, snapshot backups or restoration: those read APIs were denied to the routine CLI, and the owner console session had expired. They remain unverified pending owner sign-in, not silently marked passed. Recorders still share one Linux identity and credential cache; this change does not establish per-provider credential isolation.

## Mumbai admin and connector hardening — 8 September 2026 IST

Measured on the active Mumbai instance after the authorized change: the routine `ubuntu` SSH account has no general sudo grant and no `sudo` or `lxd` membership. A fresh Session Manager SSH login and SCP transfer passed; `sudo -n true` was denied. An independent AWS Run Command still returned UID 0 for authorized maintenance. Root/password SSH logins are disabled, the live SSH socket binds only to `127.0.0.1:22`, and EC2 security-group ingress remains empty.

The running Cloudflare connector has empty effective and bounding capabilities, NoNewPrivs=1 and Seccomp=2. Its kernel/control-group, namespace, address-family, realtime and SUID/SGID restrictions are active; the IMDS deny rule remains. Only SSH and the connector restarted. Every dashboard/recorder PID and start timestamp matched the pre-change capture, and saved source files continued publishing. The signed-in public TM page rendered current rows, chart and provider measurements after the connector restart. An unsigned origin request returned 403; `salad-ui`, `cloudflared-salad` and `ubuntu` could not read the recorder credential cache.

Syntax checks (`sshd -t`, `visudo -c`, systemd unit verification) and deployed/source hashes passed. Tokyo, provider configurations, recording data and the application authentication implementation were not changed. Trader's separate per-device logout registry is not implemented by this infrastructure change.

The initial sudo removal broke credential-renewal entry points that assumed arbitrary root Python over SSH. The corrected policy permits only fixed root-owned renewal prompts/session writers as `salad`, the masked RP check, and start/stop of the RP/PS provider readers. The RP/PS bridge now runs its orchestration as the unprivileged SSH user. General root Python/shells, a `salad` shell, direct helper `--read`, and a different account argument were denied in live tests. Both session-write permissions, all five generic hidden prompts, both RP modes and the two service-control permissions passed their checks. Idempotent starts preserved provider-reader PIDs; no collector was stopped. A real SSH hidden prompt opened and was cancelled before entry, reporting nothing saved. No real credential was renewed or replaced in this verification. Local bridge and connection-wrapper suites passed 18 and 7 tests respectively, including redacted transport, invalid inputs and restart-on-failure behavior. The source-only RP prompt was also synchronized with the already-deployed `--mode` implementation.

The Linux manifest and both RP manifests pass after this correction. The two changed Website prompt entries match their manifest. The complete Website source check still rejects four independently edited files (`dashboard/fleet_test.py`, `dashboard/server.py`, `scripts/hg-fleet-control.py`, `scripts/hg-provider-observer.py`); they were not modified or rehashed by the hardening task. The shared integration owner must reconcile them before claiming a complete source-bundle verification.

## Release backup scope

The deployed application source is the verified `1c70638` release. The integration owner published it after 45 API-response checks, preserving explicit Proxyrack provider limitations and historical gaps. This backup adds the protocol folders, readable rebuild guides, reconstruction helpers and Linux configuration. It does not redeploy the site or alter retained measurements.

The local experimental Honeygain recovery-ledger extension remains outside this commit. Its isolated test results are not evidence that it was deployed. The preserved production observer has the reduced lifecycle semantics described in DATA.md. Historical tests and earlier validation counts below apply to their dated releases, not automatically to every current source file.

The final source-only backup restored Honeygain (9 files), PacketStream (13 files) and Website (58 files) independently into empty directories. The preserved HG/PS offline deployment plans succeeded. Repocket's recording, idle-worker and frontend regressions passed after synchronizing its shared traffic parser with the deployed recorder; 13 Repocket and 18 PacketStream provider tests passed. Fresh database schemas reopened read-only after the documented journal initialization. The backup includes the live SSH metadata-guard unit required by its socket configuration. No cloud client, credential, service or measurement was changed by these backup checks.

## Captured configuration

This recovery kit was assembled from the live Mumbai host, its IAM policies, and the owner's signed-in Cloudflare configuration on 7 September 2026. It includes the verified security cutover: root-owned code, the salad-ui Unix-socket service, named read ACLs, the billing-file write exception, Secrets Manager, the private runtime cache and the tunnel's IMDS denial.

Cloudflare DNS, Access identity/policy/MFA/session settings and the tunnel were read from the console. The initial route was HTTP; the security cutover changed it to the Unix socket in CONNECTIONS. The instance, disk, security group and inline role policies were read through AWS. The scoped routine identity denied AMI/route-table/secret-metadata enumeration; no permissions were broadened for this documentation task.

The application bundle is a production snapshot plus the existing reconstruction helpers. Running-source files are copied from the host, rather than reconstructed from chat recollection. Linux unit/helper/policy bytes have their own manifest. The shared frontend is synchronized only by its single integration owner.

## Measured recovery defect and correction

A fresh-schema test on the actual Ubuntu host created empty databases using Store and NetworkMinutes, closed the writers, then tried read-only access as salad-ui without directory write permission. Both WAL databases failed with `OperationalError: attempt to write a readonly database`.

RECOVERY therefore initializes fresh schemas and switches their journal mode to DELETE while no writer is running. The inactive compatibility database stays in DELETE mode; the active PacketStream recorder establishes its own WAL/SHM files before the UI starts. This is a real empty-host dependency, not a fabricated traffic fixture.

The permission procedure reapplies named ACLs after initialization/restoration because schema creation and copied mode bits can otherwise remove the UI's effective read access. No real data or credentials were used in the empty-schema test.

## Rehearse the bundle

Run from the repository root; this creates only a temporary source restore:

```sh
SALAD_CHECK=$(mktemp -d)
python3 restore.py Website --to "$SALAD_CHECK/runtime"
python3 -B - "$SALAD_CHECK/runtime" <<'PY'
import ast
from pathlib import Path
import sys
for path in Path(sys.argv[1]).rglob("*.py"):
    ast.parse(path.read_text(), filename=str(path))
print("Python source syntax passed")
PY
node --check "$SALAD_CHECK/runtime/dashboard/static/fleet-test.js"
node --check "$SALAD_CHECK/runtime/dashboard/static/ps1.js"
rm -rf "$SALAD_CHECK"
```

Validate `Website/linux/SHA256SUMS` before copying Linux configuration. On the Linux host, `systemd-analyze verify` checks the supplied units without starting them. Verify secret ARN references agree between the helper and IAM policy; never print secret values during a check.

After an intentional, reviewed edit to a recreated object's ARN or SSH target, regenerate the Linux manifest from the changed configuration before staging:

```sh
python3 -B - <<'PY'
from pathlib import Path
import hashlib
root = Path("Website/linux")
files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
(root / "SHA256SUMS").write_text("".join(
    hashlib.sha256(p.read_bytes()).hexdigest() + "  " + str(p.relative_to(root)) + "\n"
    for p in files))
PY
```

Do not regenerate a manifest merely to silence an unexplained mismatch; compare it with the known source first.

Historical test files in source were written for earlier localhost interfaces. Their old full-suite counts are not acceptance evidence for the isolated Unix-socket release. Use the actual restore, source/hash, permission and public-page checks documented here and in RECOVERY; do not weaken production authentication to satisfy an obsolete localhost fixture.

## Public acceptance and retained behavior

The earlier performance repair was measured on the retained-history AWS host. Standard CPU credits reproduced timeouts; Unlimited is the current setting. An independent browser pass confirmed that every tab loaded its chart/table and that all recorded totals advanced on a second observation. This is evidence of that measured run, not a guarantee of every provider's connection or earnings.

After recovery, repeat the public checks against the restored host: owner security-key login, each configured route, actual source timestamps, advancing traffic, correct group/run identity and honest unavailable provider fields. Test a bare unauthenticated socket request as a denied request; do not fabricate Access headers.

The kit does not claim that a fresh EC2 instance was provisioned or production deleted during this documentation task. Infrastructure creation is documented from the captured settings and vendor procedures; source restoration and cold database reopening are checked in isolation.

Final measured packaging check: 50 application/source files and 19 Linux configuration/source files matched their manifests. A fresh temporary restore, relative links, embedded Python, and source syntax passed. All active Linux units passed systemd verification. The documented database initialization reopened both empty fixture databases successfully as salad-ui. Independent Astra GPT-6 at max reasoning found one setup-handoff defect; the corrected sequence was reviewed again with no concrete defect found.

The full state must be backed up separately. A source manifest proves source bytes; it does not prove an AMI, credential or historical-data backup exists.

## Backend delivery and Mac refresh — 7 September 2026

Measured on the owner's signed-in MacBook through the public hostname. Two normal reloads before static caching painted after 3.320 and 2.972 seconds; after caching, 0.428 and 0.464 seconds. First compact PacketStream data completed after navigation at 6.432/4.832 seconds before and 1.722/0.963 seconds after. All three versioned assets used zero network bytes on the repeated reloads. Measurement responses remained uncached HTTP 200. HTML 304 behavior was not demonstrated through Cloudflare.

Measured on Mumbai against the same copied production inputs, compact payloads fell from 2,965,621 to 650,443 bytes for HG, 2,125,417 to 352,789 for PR, 1,882,183 to 412,156 for RP, 973,484 to 408,922 for EarnFM, and 1,107,452 to 293,966 for TM. Full JSON value equality and compact contributor round-trip checks passed across all nine services. Payloads are uncompressed counts from that captured dataset; newer recordings change them.

Measured history work on Mumbai: the initial general query took 6.898 seconds for EarnFM and 5.600 seconds for TM. Incremental readers took 4.175/2.273 seconds on initial loading, then 34–66/31–54 milliseconds for subsequent period changes, including metadata/lifecycle handling. Initial cache population is still slower than warm requests. Boundary-bin allocation is marked estimated.

Checks covered partial-line completion, append/rewrite/truncation/replacement, byte/row retention limits, warm/cold equality, and archived HG original source timestamps. A concurrent TM integration removed the optional snapshot argument; it was reconciled with the delivered statistics-freshness correction, then all nine compact routes passed again. Only the dashboard was restarted for backend installation. Unlimited credit mode, root code ownership, the isolated Unix origin, Access validation and recorder state were preserved.

Final permission check: TM history initially returned public HTTP 500 because `salad-ui` could not read its private `deployment.json`. The API now reads the matching deployment fields already published in `latest.json`; no ACL, authentication or isolation change was made. All nine history readers subsequently passed under the actual `salad-ui` account. Across three observations over 90 seconds, every service's native source time advanced; provider times remained independently reported (including the old Repocket reading and unavailable feeds).

Final PR integration preserves the delivered `proxyrack.public_snapshot()` API, its source bundle and existing read-only module bind. The superseded shared PR chart helper was removed. A concurrency check reproduced an archive/export cache-eviction race; all snapshot paths now use the existing fleet lock, and 24 concurrent local requests passed. Unsigned origin requests still returned 403; the active dashboard remained `salad-ui`, AF_UNIX only, with all IP networking denied and its original single billing-file write exception.

| Backend file | Before integration | Final |
|---|---:|---:|
| server.py | 369 | 793 |
| fleet_test.py | 669 | 726 |
| native_network.py | 280 | 285 |
| traffmonetizer.py | 46 | 49 |

`server.py` adds bounded history selection, shared incremental sample aggregation, parsed-view/compact-chart reuse and versioned static delivery; its handler routes the new history API and retains protocol-owned PR freshness. `FleetTestView.ledger` reuses validated appends; `snapshot` serializes all cache access; `_snapshot` reuses original HG source timestamps. `NetworkMinutes.snapshot` reuses unchanged PS minute bars. `traffmonetizer.snapshot` accepts a cached source while independently aging copied fields. No dependency, background runner, data rewrite, recorder policy change, auth bypass, commit or push was added.

Closure review: independent Astra GPT-6 at max reasoning returned “No concrete defect found” for the final fleet locking, published TM metadata and PR forwarding corrections. Public verification passed all nine compact APIs and PR/TM history after the final integration.

Restore check: the complete main-checkout restore correctly rejected unpublished frontend edits in `dashboard/static/ps1.js` and `dashboard/static/styles.css`. Those held edits were preserved. A temporary staging copy using the matching deployed assets passed the source restore; its files and target were then removed. Backend files and their manifests match production. The frontend holder/coordinator still needs to reconcile the pending frontend source before a combined release.

Additional command-only failures during inspection were corrected without application changes: systemctl wildcard inspection was rerun with `list-units`; privileged glob inspection was replaced with explicit Python reads; unavailable `getfacl` was replaced by a direct read under `salad-ui`.
