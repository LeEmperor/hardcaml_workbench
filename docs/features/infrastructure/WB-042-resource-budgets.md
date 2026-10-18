---
id: WB-042
title: Output/storage and aggregate execution budgets
category: infrastructure
feature_sets: [FS0, FS2, FS3]
status: needs-design
kind: enhancement
priority: P1
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [budgets, storage, processes, builds]
depends_on: []
related: [WB-030, WB-031, WB-033, WB-041, WB-044]
---

# WB-042 — Output/storage and aggregate execution budgets

## Request
Strengthen producer output and storage budgets. Provisionally broaden this to
aggregate process/build budgets needed for bounded sweeps; that expansion is an assumption.

## Current baseline
FS2 has fixed event/artifact/history limits; the supervisor owns root queueing and
process lifecycle. FS3 records an owner-directed aggregate 20-job build pool.

## Scope
- Define per-job and aggregate stdout/stderr, temporary-output and retained-byte limits.
- Reserve/release capacity across concurrent producers, cancellation and failures.
- Provisionally include process/build reservations and nested-helper accounting.
- Preserve the owner’s 20-job pool as a configurable operational current default,
  not a machine-core-derived automatic allocation or proof of general runtime enforcement.
- Expose queue/rejection, truncation and eviction reasons with effective configuration.

## Out of scope
- A second scheduler, machine-wide resource control or distributed-worker dispatch.
- Unlimited retention or silently substituting detected core count for owner policy.

## Acceptance criteria
- Concurrent noisy jobs remain within declared per-job and aggregate byte bounds.
- Nested builds/helpers cannot each claim the whole configured process/build pool.
- Queue, cancel, launch failure and completion release reservations exactly once.
- Restart and cleanup reconcile retained usage without corrupting normalized history.
- Effective limits and exhaustion behavior are inspectable and configurable.
- A configuration override changes the 20-job default explicitly; core detection does not.

## Dependencies
No additional prerequisite tickets. [WB-030](../verification/WB-030-seed-parameter-sweeps.md),
[WB-031](../exploration/WB-031-design-space-sweeper.md) and
[WB-033](../exploration/WB-033-quick-harn-playground.md) consume aggregate limits.
[WB-041](WB-041-durable-logs.md) consumes storage policy and
[WB-044](WB-044-load-acceptance.md) validates scale; these consumers are not prerequisites.

## Estimate rationale
13 points, M, medium confidence: existing limits/supervision provide seams for a bounded
policy layer. Incremental estimate assumes reuse, not a scheduler rewrite; re-estimate
if the provisional aggregate execution expansion requires a materially broader contract.

## Assumptions and decisions needed
Owner confirmation is required for the broadened aggregate process/build scope and
exhaustion policy. Distinguish build jobs, process slots and tool-internal thread limits.

## References
- [FS2-F05 output budgets](../../backlog/fs2_followups.md#fs2-f05--durable-logs-and-output-budgets).
- [FS3 operational build pool](../../fs3_integration_plan.md).
- [Current limits](../../../protocol/simulation.ml) and [supervisor](../../../backend/service.ml).
