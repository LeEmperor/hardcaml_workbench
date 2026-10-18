---
id: WB-044
title: Large-regression and multi-client load acceptance
category: infrastructure
feature_sets: [FS2, FS3]
status: proposed
kind: validation
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [load, concurrency, acceptance]
depends_on: [WB-027, WB-042]
related: [WB-030, WB-043, WB-062]
---

# WB-044 — Large-regression and multi-client load acceptance

## Request
Validate larger regressions and simultaneous clients with measured responsiveness,
bounded resources and independent investigation state.

## Current baseline
FS2 has scoped native HTTP/PTY acceptance. FS2-F06 and construction records defer
broader high-event-volume, reconnect and concurrent-client matrices.

## Scope
- Define finite regression/event-volume and simultaneous-client workloads.
- Use agreed latency/memory/loading measurements and effective shared budgets.
- Exercise reconnect, hide/reopen, cancellation and independent client selection.
- Retain reproducible fixture/transport evidence and scoped usability observations.

## Out of scope
- Reopening FS2 milestone acceptance or claiming unlimited scaling.
- Distributed workers, mandatory real physical flows or a speculative workspace redesign.

## Acceptance criteria
- Recorded workload/results include latency distributions, peak memory and disk usage.
- Multiple clients share execution without duplicate launches or selection leakage.
- Hide/reopen does not cancel work; reconnect preserves exact attempt identity.
- Noisy/high-event-volume jobs obey aggregate execution and output/storage policy.
- Cancellation and query latency stay within reviewed thresholds under declared load.
- Usability changes receive scoped review; fixture evidence is labelled separately from real use.

## Dependencies
[WB-027](WB-027-performance-measurement.md) is required for measurement methodology;
[WB-042](WB-042-resource-budgets.md) is required for enforceable reviewed limits.
[WB-030](../verification/WB-030-seed-parameter-sweeps.md),
[WB-043](WB-043-slow-storage.md) and [WB-062](../verification/WB-062-submission-recovery.md)
are related workload/recovery improvements, not additional prerequisites.

## Estimate rationale
13 points, M, medium confidence: extends known acceptance seams with bounded workloads
and concurrency evidence. Incremental estimate excludes measurement/budget prerequisites
and subsequent fixes whose scope emerges from the load results.

## Assumptions and decisions needed
Agree client counts, regression volume and thresholds before judging success. A fixture
can exercise large event volumes without requiring the separate sweep feature first.

## References
- [FS2-F06 load acceptance](../../backlog/fs2_followups.md#fs2-f06--multi-clientload-acceptance-and-usability).
- [Construction coverage followups](../../construction_phase_plan.md).
- [Current FS2 acceptance](../../fs2_acceptance.md).
