---
id: WB-036
title: Gate-level simulation adapters
category: verification
feature_sets: [FS2, FS1]
status: needs-design
kind: feature
priority: P2
severity: n/a
requested_size: Unspecified
size: L
points: 34
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [gate-level, netlists, collateral]
depends_on: [WB-035]
related: [WB-038, WB-037]
---

# WB-036 — Gate-level simulation adapters

## Request
Run gate-level simulation against explicitly named physical/build outputs with
the required models and collateral, retaining exact consumption provenance.

## Current baseline
FS2 accepts explicit input references but has no accepted real gate-level adapter.
The FS2-F07 backlog requires actual consumption, not merely valid RPC provenance.

## Scope
- Extend generated-RTL simulator staging for one gate-level project recipe.
- Select exact netlist/output, cell models and required timing/reset collateral.
- Declare whether the initial recipe is functional or timing-annotated simulation.
- Preserve source/run/output, tool and collateral identities with test artifacts.
- Keep simulation execution separate from the physical provider's lifecycle engine.

## Out of scope
- Universal PDK/model support, a new ASIC engine or automatic signoff approval.
- Treating a viewed run selection as proof of consumed netlist association.

## Acceptance criteria
- A real gate-level simulation consumes a named netlist and required models.
- Evidence identifies actual consumed bytes and the claimed physical/build output.
- Stale/missing netlists or collateral are rejected rather than silently substituted.
- Result and trace investigation retain exact attempt and input provenance.
- Rerun and cancellation work without mutating or cancelling unrelated ASIC work.
- Gate-level test pass remains distinct from policy acceptance and physical signoff.

## Dependencies
[WB-035](WB-035-generated-rtl-simulation.md) is required for its reusable simulator
input-selection/staging scaffold. [WB-038](WB-038-acceptance-bridge.md) can later
consume verified results under explicit acceptance policy;
[WB-037](WB-037-archived-replay.md) adds retained historical inputs, not this adapter.

## Estimate rationale
34 points, L, low confidence: model/collateral compatibility, annotation semantics
and real-output linkage add significant uncertainty. Incremental estimate excludes
the WB-035 scaffold cost and any separate acceptance-policy bridge.

## Assumptions and decisions needed
Select simulator/PDK recipe and functional versus timing-annotated first scope.
Document unsupported annotation or model modes explicitly; do not overstate coverage.

## References
- [FS2-F07 adapters](../../backlog/fs2_followups.md#fs2-f07--generated-rtl-and-gate-level-adapters).
- [FS1 lifecycle and artifacts](../../fs1_lifecycle_and_artifacts.md).
- [Input provenance contract](../../../protocol/simulation.ml).
