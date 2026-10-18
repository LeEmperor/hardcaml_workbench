---
id: WB-064
title: Generic selected-job detail and log investigation
category: infrastructure
feature_sets: [FS0, FS2]
status: proposed
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 8
confidence: medium
estimate_scope: incremental
origin: existing-backlog
tags: [jobs, logs, investigation]
depends_on: []
related: [WB-041, WB-005, WB-063]
---

# WB-064 — Generic selected-job detail and log investigation

## Request
Carry forward generic selected-job detail and log-investigation work from existing
construction records. This is not a newly submitted owner feature request.

## Current baseline
FS0 exposes generic project Build/Test attempts, statuses, logs and cancellation.
Structured FS2 case detail does not automatically enrich generic job outcomes/history.

## Scope
- Improve selected-job command, scope, timestamps and lifecycle/exit explanation.
- Make bounded stdout/stderr paging and failure navigation useful in Testing/execution.
- Keep exact selected-job identity and local scroll/filter state during refresh.
- Explain unavailable case details and non-durable/missing generic history honestly.

## Out of scope
- Manufacturing structured cases from logs or claiming generic success proves a case count.
- Implementing durable full-log retention or a complete Testing-workspace redesign.

## Acceptance criteria
- A user can select a generic failed job and inspect its actual command/exit/log detail.
- Stdout/stderr scope, offsets and truncation are visible where applicable.
- Refresh, new job arrival and workspace switching cannot silently retarget selection.
- Launch failure, nonzero exit and cancellation are distinguishable.
- No structured-case provider means case detail is explicitly unavailable.
- Opening/closing detail does not launch, rerun or cancel jobs implicitly.

## Dependencies
No additional prerequisite tickets; current bounded logs support the first detail slice.
[WB-041](WB-041-durable-logs.md) extends historical availability,
[WB-005](WB-005-process-monitor.md) adds resource visibility and
[WB-063](../presentation/WB-063-testing-workspace.md) addresses broader investigation layout.

## Estimate rationale
8 points, M, medium confidence: existing attempt/log seams limit backend novelty,
with most effort in coherent native selection/detail behavior. Incremental scope
excludes durable retention, process sampling and broad workspace redesign.

## Assumptions and decisions needed
Confirm the initial detail surface and log-navigation controls. Preserve project scope
and avoid associating generic tests with a viewed ASIC run without actual provenance.

## References
- [Construction plan](../../construction_phase_plan.md).
- [Execution module baseline](../../fs0_execution_module.md).
- [Generic runner semantics](../simulation_and_tests.md).
- [Supervisor job/log state](../../../backend/service.ml).
