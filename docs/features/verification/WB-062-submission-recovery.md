---
id: WB-062
title: Uncertain simulation submission/history recovery
category: verification
feature_sets: [FS2]
status: proposed
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: existing-backlog
tags: [reconnect, submissions, history]
depends_on: []
related: [WB-063, WB-044]
---

# WB-062 — Uncertain simulation submission/history recovery

## Request
Carry forward FS2-F04: make accepted attempts recoverable after lost, delayed or
superseded submission responses. This is existing backlog, not a new owner request.

## Current baseline
FS2 has submission identity, deduplication and durable structured history.
The backlog identifies pending-submission visibility and history restoration as followups.

## Scope
- Show pending/uncertain submission identity and explicit reconciliation state.
- Locate the exact accepted attempt without creating another submission.
- Restore relevant history pages and preserve independent investigation selection.
- Explain restart boundaries where a pending client receipt cannot be safely replayed.

## Out of scope
- Automatic replacement launches or replaying old submissions after daemon restart.
- Reopening the accepted FS2 milestone or redesigning every Testing interaction.

## Acceptance criteria
- Delayed/lost receipts reconcile to the exact accepted attempt with no duplicate job.
- Reconnect and navigation races do not retarget an unrelated investigation tile.
- History-page restoration finds the accepted record or reports honest unavailability.
- A superseded response cannot overwrite a newer explicit user selection.
- Daemon restart does not replay uncertain submissions as fresh work.
- Native transport/input evidence covers recovery, not only pure reducer fixtures.

## Dependencies
No additional prerequisite tickets; build on delivered identity/history contracts.
[WB-063](../presentation/WB-063-testing-workspace.md) shares investigation UX and
[WB-044](../infrastructure/WB-044-load-acceptance.md) extends concurrent-load evidence.
These are related refinements rather than blockers for targeted recovery work.

## Estimate rationale
13 points, M, medium confidence: known identity seams need visible reconciliation
and transport/navigation race coverage. Incremental estimate covers one bounded
recovery slice, excluding broad workspace redesign and load acceptance.

## Assumptions and decisions needed
Choose pending-receipt persistence and lookup limits. Preserve explicit user selection
and fail honestly when an old daemon identity no longer permits safe reconciliation.

## References
- [FS2-F04 recovery](../../backlog/fs2_followups.md#fs2-f04--reconnect-and-uncertain-submission-recovery).
- [FS2 acceptance](../../fs2_acceptance.md).
- [Simulation selection/parent types](../../../protocol/simulation.ml).
