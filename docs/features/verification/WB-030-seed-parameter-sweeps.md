---
id: WB-030
title: Seed sweeps and test-parameter matrices
category: verification
feature_sets: [FS2]
status: proposed
kind: feature
priority: P2
severity: n/a
requested_size: Feature
size: L
points: 21
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [regressions, seeds, matrices]
depends_on: [WB-042]
related: [WB-031, WB-032, WB-012]
---

# WB-030 — Seed sweeps and test-parameter matrices

## Request
Run explicit test-seed sweeps and test-parameter combinations with useful aggregate
results and targeted reruns.

## Current baseline
FS2 v1 discovers suites/cases and captures one seed plus parameters per submission.
FS2-F10 preserves richer regression expansion beyond that accepted contract.

## Scope
- Preview a finite matrix with deterministic expansion and stable child identities.
- Capture each child's suite/cases, seed, parameters and parent sweep identity.
- Schedule through the existing supervisor under shared reservations and limits.
- Summarize completed, failed, cancelled, missing and pending children honestly.
- Support failed-child investigation and exact-input reruns without replacing history.

## Out of scope
- Building design variants or comparing physical PPA; that is WB-031.
- Unbounded search, automatic seed mining or inferred generic Dune case outcomes.

## Acceptance criteria
- Previewed cardinality and inputs match the submitted finite child set.
- Duplicate submission/reconnect cannot double-launch a child.
- A failing seed can be inspected and rerun with its original parameters.
- Cancellation stops queued expansion and targets only owned active children.
- Noisy children and nested helpers respect shared execution/storage budgets.
- Aggregate results distinguish absent results from passes and preserve partial history.

## Dependencies
[WB-042](../infrastructure/WB-042-resource-budgets.md) is required for aggregate
execution/output reservations before multiplying jobs. [WB-032](WB-032-test-catalog.md)
and [WB-012](../evidence/WB-012-run-comparison.md) are useful UI/comparison enablers,
not prerequisites; existing discovery suffices. [WB-031](../exploration/WB-031-design-space-sweeper.md)
is a related but distinct design-build workflow.

## Estimate rationale
21 points, L, medium confidence: known single-attempt seams need matrix identity,
bounded orchestration and partial-result UI. Incremental scope excludes WB-042 costs.

## Assumptions and decisions needed
Choose matrix syntax, maximum expansion and resume policy. Retain project-owned test
semantics; decide whether dynamic generated cases require a versioned provider extension.

## References
- [FS2-F10 catalogs and comparisons](../../backlog/fs2_followups.md#fs2-f10--richer-regression-catalogs-and-comparisons).
- [Captured selections](../../../protocol/simulation.ml).
- [Supervisor callbacks](../../../backend/simulation_task.ml).
