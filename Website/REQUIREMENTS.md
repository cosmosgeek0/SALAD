# Current website requirements

Confirmed by the owner on 7 September 2026. Read this with README.md, DATA.md and OPERATIONS.md.

## UI redesign

Deliver and apply a polished, coherent website UI across Honeygain, PacketStream, Proxyrack, Repocket, EarnFM, Traffic Monetizer, Pawns.app, EarnApp and Grass. Improve layout, typography, spacing, visual hierarchy, charts, tables, navigation and responsive behavior. The result must be implemented and verified on the hosted site, not left as a mockup.

Keep measurements useful and honest: current cloud/native state, recorded traffic, period totals, duration, freshness, errors, recovery outcomes and available provider figures. Preserve the protocol teams' completed data and recovery changes. Honeygain and PacketStream are references for depth and evidence, not templates for copying another client's thresholds or identifiers.

## Historical IP records

Each service must provide a clearly discoverable view of its older/replaced IP and node records on the website. A current-server-only table or a minute popup is insufficient for this request.

Show the measured traffic contributed by each historical IP, its first/last observation and recording duration where supported, country when known, and the associated instance/run identity and lifecycle. Provide usable period selection, sorting/search and detail access without crowding the current-health view.

Respect selected test/group boundaries and counter resets. Label archived tests separately. Show provider credits per IP only where the provider actually supplies that attribution; account totals are not per-IP earnings. Mark missing or partial historical coverage explicitly.

This newer requirement takes precedence over older guidance that prevented a historical IP listing. It does not request duplicate permanent lists of the currently hovered minute's contributors.

## Latency and speed

Improve actual page opening, tab changes, history exploration and continuing refreshes across every service. Measure cold/warm end-to-end behavior and distinguish network/serialization/rendering delay from stale upstream observations.

Use efficient queries, bounded history responses, appropriate caching and incremental work where measured bottlenecks justify them. Preserve original timestamps, identities, raw records, baselines and truthful stale/missing states.

Responsiveness and correctness come first. Do not chase arbitrary CPU percentages or re-enable the Standard credit cap that reproduced hangs. Preserve the current AWS/Cloudflare security boundaries and existing hosting.

## Integration

UI work owns frontend assets. Latency/data-delivery work owns shared backend/history APIs. Protocol tasks continue to own their clients and recorders. Agree on a compact history-data contract and coordinate shared edits; do not overwrite another task's unfinished work.

Check documented protocol requests and completed deliveries before claiming feature parity. Record any concrete remaining data limitation rather than filling it with mock numbers. Keep this file and the recovery source/manifests current after verified changes.
