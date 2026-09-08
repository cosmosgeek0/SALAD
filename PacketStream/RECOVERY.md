# PacketStream recovery

## Exact recovery and measurement behavior

The included packetstream-monitor/start-with-recovery.sh is the complete cloud wrapper. It starts the stock launcher, reads native log lines and measures eth0 counters.

| Event | Current action |
|---|---|
| Duplicate public IP or rejected non-residential IP | Stop client and request reallocation immediately |
| Native generic client error | Request reallocation immediately |
| Client process exits | Request reallocation immediately |
| Communication error persists | Replace after 30 seconds; a native running status clears that timer |
| No initial connection | Replace after 60 seconds |
| Operator stop | Stop the child and emit a final interval; do not classify as a new healthy client |

Each reallocation uses the instance metadata endpoint POST http://169.254.169.254/v1/reallocate, Metadata: true, Content-Type: application/json and a reason. HTTP 200/204 is success; the wrapper then exits 75. The native logs distinguish PS_SELF_REALLOCATE, PS_SELF_IMDS_RESPONSE, PS_SELF_IMDS_ACCEPTED and failure. [IMDS reference](https://docs.salad.com/reference/imds/reallocate).

A 7 September live incident confirmed this path: after a 30-second communication failure the wrapper logged a replacement request and HTTP 200, then the fleet recovered. An accepted request is still distinct from the next instance becoming connected.

## Command transport: do not lose this detail

The source is UTF-8, base64 encoded, and split into strings no longer than 900 characters. The launch command joins those base64 strings with printf "%s" "$@", decodes them to /tmp/ps-self-recovery.sh and execs Bash.

An earlier deployment split raw source into strings. Salad trimmed boundary whitespace, removing newlines and producing invalid programs. Base64 transports the exact bytes. The rebuild helper checks the tested command envelope: at most 100 arguments, at most 1,000 characters each. These are the bounds used by this recipe, not a promise about future provider limits.

Do not paste a password-bearing shell string, substitute a custom binary, reintroduce a gateway, or attach one public IP to several PacketStream clients.

## Verification and known failure remedies

Measured recheck on 7 September 2026: the printed extractor restored all twelve files from the preceding self-contained snapshot and validated every manifest hash. Isolated creation/start/rebind checks produced one ten-replica group, reused no historical UUID and added no duplicates. Wrong CID, missing CID and changed memory fixtures were rejected before any start request. Read-only Salad comparison matched the real ps-test-us configuration and command digest; the registry returned the exact Linux amd64 manifest. No new paid containers were launched by this check.

| Check/failure | Required result or remedy |
|---|---|
| Only “Salad running” is visible | Require fresh native running state before counting a confirmed client |
| Old ps1 group is queried | Fix observer-target.json and PS_GROUP=ps-test-us; do not launch the retired gateway collector |
| Ten-minute query returns a full capped page | Split windows; do not assume ordering or silently skip the rest |
| New container starts with a large lifetime counter | Establish its baseline; do not add that lifetime total as new traffic |
| Replacement disappears from the current table | Keep unassigned slots visible; do not invent IPs or metrics |
| Final reallocation minute rejected | Parser must allow reallocating and final=1 |
| Platform log ID differs after an update | Use the included PS_NATIVE/runtime identity |
| Need an API reallocation | Read exact current group and instance IDs, POST .../instances/ID/reallocate; verify the replacement |
| Need the prior chart history | Restore minutes.sqlite3 from a consistent backup; do not reuse an old collector cursor without its rows |
| Provider feed is stale | Re-establish the signed-in bridge or leave Not reported; network recording can continue |

No new schema, gateway, UI button collection, local Docker control loop, or benchmark-generated traffic is required for this deployment.

For a vendor-image backup:

~~~~bash
docker pull --platform linux/amd64 docker.io/packetstream/psclient@sha256:6e6a2cefe9f49c33f6c9d4bd41d21daf20c4767f2c66e82f57a5960ec9923987
docker save -o packetstream-amd64.tar docker.io/packetstream/psclient@sha256:6e6a2cefe9f49c33f6c9d4bd41d21daf20c4767f2c66e82f57a5960ec9923987
~~~~

[Salad create-group API](https://docs.salad.com/reference/saladcloud-api/container-groups/create-container-group).
