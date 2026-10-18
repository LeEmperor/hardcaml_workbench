---
id: WB-043
title: Slow-storage responsiveness
category: infrastructure
feature_sets: [FS0, FS2]
status: proposed
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [storage, async, responsiveness]
depends_on: []
related: [WB-027, WB-041, WB-042]
---

# WB-043 — Slow-storage responsiveness

## Request
Keep input, queries and cancellation responsive when artifact capture, history,
fsync or pruning encounter slow storage.

## Current baseline
FS2-F03 identifies remaining synchronous persistence/loading work as followup.
Simulation file helpers perform atomic writes, fsync and bounded reads.

## Scope
- Identify blocking capture, metadata loading/persistence and pruning paths.
- Move remaining blocking work off the Async event loop using bounded workers.
- Preserve serialized reservations, record ordering and atomic publication.
- Measure responsiveness under injected slow I/O with realistic retained records.

## Out of scope
- Replacing the storage backend or weakening durable/atomic semantics for speed.
- Unlimited worker fan-out or automatic broad cache redesign.

## Acceptance criteria
- Injected slow reads/writes/fsync do not monopolize query/cancel/input processing.
- Record measured latency and worker/queue bounds for the declared workload.
- Durable submission identity and idempotency survive delayed publication.
- Partial cancellation results remain attributable and reservations remain consistent.
- Corrupt/missing records and retention failures retain explicit behavior.
- Atomic record visibility is preserved under concurrent work and shutdown.

## Dependencies
No additional prerequisite tickets; use scoped injected-I/O measurements for this change.
[WB-027](WB-027-performance-measurement.md) supplies broader baseline methods,
[WB-041](WB-041-durable-logs.md) adds persistence consumers and
[WB-042](WB-042-resource-budgets.md) can unify budget policy. These are related enablers.

## Estimate rationale
13 points, M, medium confidence: specific synchronous helpers are known, but moving
work safely requires lifecycle/order integration. Incremental estimate covers a bounded
responsiveness slice, excluding storage replacement and broad measurement infrastructure.

## Assumptions and decisions needed
Choose representative delay/failure injection points and acceptable query/cancel bounds.
Confirm worker ownership and shutdown draining without weakening persistence guarantees.

## References
- [FS2-F03 slow storage](../../backlog/fs2_followups.md#fs2-f03--slow-storage-responsiveness).
- [Atomic persistence/read helpers](../../../backend/simulation_files.ml).
- [Supervisor lifecycle](../../../backend/service.ml).
