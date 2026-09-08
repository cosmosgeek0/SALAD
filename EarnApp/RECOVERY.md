# EarnApp recovery and recording

The supervisor in [startup.sh](startup.sh) runs inside each Salad container. The AWS recorder in [earnapp-recorder.py](earnapp-recorder.py) records its evidence and applies policies that require authenticated provider readings. The original device UUID is preserved across replacements. All placement requests remain US-only.

## Chosen policies

These are operator recovery settings, not vendor guarantees about response times or earnings.

| Condition | Action |
|---|---|
| Public IP is reported outside the US | Request replacement before starting EarnApp |
| Country cannot be verified | Retry the lookup with bounded timeouts; after the configured attempts request replacement |
| Client download/setup fails | Record the exact failure category and request replacement |
| Native registration fails | Stop the client and request replacement |
| Client process exits | Record its exit code, finish the traffic interval and request replacement |
| Registration never succeeds or DNS failure persists | The native supervisor uses a 120-second deadline |
| Supervisor stops advancing its heartbeat | The [Salad liveness probe](liveness.json) detects the stale heartbeat and requests platform recovery |
| Provider repeatedly reports this current registered client offline | The AWS recorder requests replacement after 120 seconds of fresh offline observations |
| Traffic is low, or neither provider earnings nor qualifying usage advances | Keep the healthy client on its current machine; display the dated provider reading and elapsed time without replacement |
| Provider/recorder evidence is missing, stale or erroneous | Pause the affected provider policy and show the error; do not manufacture a failure or zero credit |
| Operator stops the container | Stop the child process group and save a final interval; do not initiate a new native replacement request |

Provider device totals and qualifying usage are recorded separately from raw bytes and the displayed monthly rate. A provider counter change resets the displayed time since progress. Flat credits never trigger replacement; no earnings-stall replacement window is configured.

The supervisor samples interface counters about every ten seconds. Its first counter record is a baseline after the binary download. Later records retain the actual interval boundaries, bytes, process/native state, registration time, run identity and final flag. Native registered state and a live process are separate from provider-online confirmation and credited earnings.

## Requests and verified outcomes

Native recovery uses `POST http://169.254.169.254/v1/reallocate` with `Metadata: true`; no account key is installed in the workload. Native HTTP 200/204 is accepted. Failed requests have bounded retries, then the supervisor exits with a nonzero status so the configured platform restart policy can take over.

Provider-based recovery uses the existing Salad key on the recorder host and targets the exact current instance. HTTP 202 records acceptance. A request is recorded before it is sent, and repeated requests for an already accepted action are suppressed. After bounded failures the request error remains visible.

The SQLite `events` table stores the original native and recorder events. Recovery metadata separately stores the old instance/machine, request/result, observed replacement identity and the time that fresh native plus provider-online evidence verified that replacement. If the observed replacement leaves before verification, that outcome remains explicit. Acceptance alone is not recorded as a healthy replacement.

The graph includes every valid traffic interval across retained runs and countries. Historical non-US and unknown-country records remain visible with their original country; new placement stays US-only. Missing minutes remain missing, zero-byte observations remain real zeros, and partial/estimated intervals remain marked. Network RX + TX includes overhead and is not a measurement of paid bandwidth.

## Inspect a running deployment

Use the Salad Terminal to inspect the supervisor and its child:

```bash
ps -eo pid,ppid,pgid,etime,rss,comm
cat /tmp/earnapp-heartbeat
earnapp showid
```

Use the container logs for `EARNAPP_SAMPLE` and `EARNAPP_EVENT`. A successful native recovery includes `requested`, `accepted`, and later a different instance's `starting`/`registered` records. Check the recorder's recovery outcome and the live page to verify the replacement. A controlled process-exit test is different from proof that every future provider/network fault will recover within a fixed wall-clock time.

For service paths, credentials and retained history, see [MONITORING.md](MONITORING.md). For a complete cloud rebuild, see [SETUP.md](SETUP.md).
