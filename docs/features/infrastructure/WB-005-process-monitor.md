---
id: WB-005
title: BTOP-like owned-process view
category: infrastructure
feature_sets: [FS0, FS2]
status: proposed
kind: enhancement
priority: P2
severity: n/a
requested_size: Ticket
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [processes, resources, execution]
depends_on: []
related: [WB-027, WB-042, WB-064]
---

# WB-005 — BTOP-like owned-process view

## Request
Provide a btop-like execution tile showing Workbench-owned running processes
and their resource use, linked to the jobs they serve.

## Current baseline
The generic supervisor owns process creation, queueing, logs and cancellation.
Execution state exists, but it is not a sampled per-process resource monitor.

## Scope
- Show owned root processes and attributable descendants with job/attempt identity.
- Sample available CPU, memory and elapsed-time metrics with explicit units/age.
- Distinguish queued jobs, running processes and unavailable remote/container metrics.
- Provide bounded refresh and selected-job investigation using existing commands.

## Out of scope
- A machine-wide replacement for btop or controlling unrelated user processes.
- Inferring ownership from PID alone or automatically cancelling high-resource jobs.

## Acceptance criteria
- Concurrent owned jobs can be distinguished and opened by exact identity.
- Reported process/resource samples identify their scope, timestamp and units.
- PID reuse, process exit and unavailable metrics cannot misattribute another process.
- Sampling and rendering remain bounded under rapid descendant creation/exit.
- Hiding/reopening the tile has no execution lifecycle side effects.
- Container/remote limitations are explicit rather than fabricated host measurements.

## Dependencies
No additional prerequisite tickets. [WB-027](WB-027-performance-measurement.md) can
measure monitor overhead; [WB-042](WB-042-resource-budgets.md) defines enforcement,
distinct from visibility. [WB-064](WB-064-generic-job-detail.md) shares job navigation.

## Estimate rationale
13 points, M, medium confidence: supervisor identity is known, while safe descendant
sampling and native rendering need integration. The owner's Ticket label is preserved;
the estimate is incremental, not a claim that resource accounting already exists.

## Assumptions and decisions needed
Choose initial platform metrics and sampling interval. Decide whether CPU is per-process
or aggregated; label aggregation and missing descendants rather than implying completeness.

## References
- [Generic supervisor state](../../../backend/service.ml).
- [Supervisor ownership contract](../../../backend/simulation_task.ml).
- [Execution foundations](../../fs0_execution_module.md).
