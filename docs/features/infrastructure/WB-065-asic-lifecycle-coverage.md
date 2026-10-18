---
id: WB-065
title: Broader ASIC lifecycle/cancellation race coverage
category: infrastructure
feature_sets: [FS1]
status: proposed
kind: validation
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: existing-backlog
tags: [asic, lifecycle, cancellation, races]
depends_on: []
related: [WB-044, WB-062]
---

# WB-065 — Broader ASIC lifecycle/cancellation race coverage

## Request
Carry forward construction-plan lifecycle/cancellation coverage gaps across late
responses, allocation and reconnect. These are existing followups, not new owner requests.

## Current baseline
FS1 records real owned backend/container and postcheck cancellation, plus focused
fixture coverage. Those records explicitly do not establish every race permutation.

## Scope
- Define a bounded lifecycle matrix across allocation, launcher, reader and postcheck.
- Add deterministic late-response/reconnect/cancel and concurrent-client specimens.
- Verify exact owned-process targeting and separation of reader/producer lifecycle.
- Retain actual frontend/transport evidence for selected interaction boundaries.

## Out of scope
- A second ASIC engine, fresh broad physical acceptance or claims of exhaustive races.
- Treating client detach or reader shutdown as permission to terminate historical producers.

## Acceptance criteria
- The matrix maps prior evidence, new coverage and remaining explicit gaps.
- Cancel before/after allocation and during postcheck preserves exact operation identity.
- Late responses cannot retarget newer selections or resurrect cancelled work.
- Client detach preserves work; shutdown/cancellation signals only owned processes.
- Concurrent readers/clients do not duplicate launch or falsely report producer termination.
- Fixtures distinguish execution completion, cancellation and acceptance verdicts.

## Dependencies
No additional prerequisite tickets; existing services and fixtures provide the seams.
[WB-044](WB-044-load-acceptance.md) supplies related load coverage and
[WB-062](../verification/WB-062-submission-recovery.md) addresses simulation receipt recovery,
not prerequisites for targeted ASIC lifecycle coverage.

## Estimate rationale
13 points, M, medium confidence: known lifecycle boundaries need a coherent matrix
and deterministic race fixtures. Incremental estimate covers bounded validation,
excluding unrelated runtime redesign and new physical-flow execution campaigns.

## Assumptions and decisions needed
Select the highest-value uncovered permutations from construction records first.
Use fixture evidence where it proves ownership/order, retaining limits on real-tool claims.

## References
- [Construction lifecycle coverage gaps](../../construction_phase_plan.md).
- [FS1 lifecycle/cancellation evidence](../../fs1_lifecycle_and_artifacts.md).
- [ASIC service ownership/shutdown contract](../../../backend/asic_service.mli).
- [Backlog coverage followups](../../backlog/README.md).
