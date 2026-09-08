# RP worker and deployment snapshot

The corrected worker command was read back from Salad configuration version 16 on 2026-09-07 at 16:50 UTC. The original create recipe retains US placement; the live group currently has no country restriction, which this policy update preserved. Its deployment settings are:

| Setting | Value |
|---|---|
| Organization | `ssh2` |
| Project | `default` |
| Group slug / visible name | `rp-test-us` / `RP` |
| Existing group UUID, for identifying this deployment only | `a3a77aae-085e-4c0c-a969-34d50b091a46` |
| Desired replicas | 10 |
| Country restriction in create recipe | United States: `["us"]`; the later live country trial changed this to GB |
| CPU / RAM / shared memory per replica | 1 vCPU / 1024 MiB / 64 MiB |
| GPU | None |
| Priority / restart policy | `batch` / `always` |
| Autostart policy | `false`; explicitly start after creating |
| Live Salad configuration version at capture | 16 |
| Worker telemetry `revision` field | 12 (a separate source label, not Salad's configuration version) |
| Incoming gateway / ports / queue / custom probes | Not used for this workload |
| Environment variables | `RP_EMAIL`, `RP_API_KEY` |

Pinned image:

```text
docker.io/repocket/repocket@sha256:5888d756de7e0e74b95b5eb08bb93f4240a0ce840c910a7e528d1143ad0c502b
```

The image contains Docker package 1.1.46 and its bundled peer client. Do not substitute `latest` when reproducing this edition: the custom worker hooks known module paths inside that exact image. A future vendor image needs a separate compatibility check. [Official image](https://hub.docker.com/r/repocket/repocket).

The decoded command deployed in Salad was byte-for-byte identical to [`repocket-monitor/start.js`](../repocket-monitor/start.js):

```text
SHA-256 937d35e7c59fdd9c2afac80ffb3f45fbf2fbc8f06e21d43c3f66fe6a03a7ae8b
```

The original version-15 capture showed 10 running replicas. Version-16 command readback alone does not verify that all updated clients are online; see the dated runtime checks in Verification.

**Behavior of this snapshot.** The captured worker does not use the former 50% failure rule or the former restart-once/three-minute delay. Its policy is:

- A new client gets a complete 600-second observation window. Thereafter the rolling window covers about the latest ten minutes, evaluated on diagnostic snapshots about every 15 seconds.
- The traffic window is observational only. A connected client remains on its machine at zero target bytes. `min_target_bytes:0`, `traffic_reallocation:false` and `relay_idle_reallocation:false` explicitly disable the old low-traffic and quiet-relay triggers.
- Reallocate if the vendor child fails to start or closes after an unexpected exit. Buffered credential errors are processed before the exit is treated as a host failure.
- Reallocate after 60 seconds of a known unavailable control connection (including an unfinished handshake), or 60 seconds without client diagnostics. Quiet relay traffic alone never triggers replacement. The vendor handshake and relay error/close callbacks provide native state; old relay objects cannot override a newer connection. These checks run every five seconds.
- Explicit credential rejection stops the child and reports `authorization_error`; it does not deliberately rotate nodes for a rejected account key. Operator credential repair is necessary. The exact string recognition is in `acceptLine`; unknown vendor errors still need diagnosis.
- Reallocation is a POST **from the container itself** to `http://169.254.169.254/v1/reallocate`, with `Metadata: true` and a reason. No Salad API key or Mac is required for this call. Requested/accepted/failed attempts share a request ID. It makes at most three ten-second attempts with two/four-second retry delays, accepts HTTP 200/204, and flushes its outcome record before exiting. The wrapper exits with code 75 afterward; Salad's `always` policy is the restart fallback if the request cannot complete. HTTP 200 means the request was accepted, not that the replacement is already online. [Salad IMDS reference](https://docs.salad.com/container-engine/how-to-guides/imds/imds-reallocate).

Connection outcome and traffic counters are diagnostic evidence. Only the explicit client/control failure conditions above trigger replacement.

Salad maintains the requested replica count and replaces lost hosts. Allocation/download time can temporarily leave fewer than ten running. The former ten-minute floor was removed because it repeatedly interrupted healthy idle clients. The current implementation has no profitability optimizer.

## Client changes

There is no custom image registry or build pipeline required. The container command reconstructs the packaged worker at startup and uses the pinned official image's dependencies.

1. The parent worker starts `/app/dist/index.js` with this same file as a Node preload and an IPC channel. The child-only `RP_DIAGNOSTICS=1` flag prevents recursively starting supervisors. Do not set that flag on the top-level Salad container.
2. The preload observes the vendor's HTTP/HTTPS and SOCKS target socket creation; it samples byte counters and records sanitized error categories. It does not log target hostnames or payload contents.
3. CONNECT tunnels use the vendor's direct byte-forwarding branch, preserving its SMTP branch. This corrected observed non-TLS data being discarded by a TLS record parser. CONNECT is an opaque tunnel, as described in [RFC 9110 §9.3.6](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.6).
4. Failed target-domain `dns.lookup` calls with `ENOTFOUND` may retry with `dns.resolve4` against the same configured resolver. Successful lookups, literal IPs, IPv6-only requests and non-target lookups keep their original path. The original error is preserved if fallback fails.
5. The parent consumes only safe log categories, prints `RP_MON` records, records activity separately from health, and requests reallocation only for the documented failures.
6. `observe.py` reads Salad logs, deduplicates records, reconciles late arrivals, matches current runs to inventory and publishes `view.json`. A guarded fallback handles Salad instance-label lag on the same machine; inspect `snapshot` for the exact condition.

Current telemetry format 2 carries `group_id`, `run`, `seq`, original `time_ms`, and explicit valid/invalid minute intervals. The API configuration version and source revision are separate identifiers; compare the checksum when restoring. Invalid intervals and conflicting sequences remain in the raw log history but are excluded from totals. Older records are retained with unknown receipt times.
