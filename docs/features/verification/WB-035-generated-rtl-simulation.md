---
id: WB-035
title: Generated-RTL simulation adapters
category: verification
feature_sets: [FS2]
status: needs-design
kind: feature
priority: P2
severity: n/a
requested_size: Unspecified
size: L
points: 21
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [rtl, simulator, staging]
depends_on: []
related: [WB-036, WB-037]
---

# WB-035 — Generated-RTL simulation adapters

## Request
Simulate named generated RTL through a concrete project adapter with explicit
input selection, staging and attributable results.

## Current baseline
FS2 has structured results and explicit ASIC-input provenance fields. Those fields
alone do not demonstrate a simulator consuming the claimed generated output.

## Scope
- Select one real simulator and project-owned compile/run recipe.
- Resolve exact generated RTL/build references and required testbench collateral.
- Provide reusable simulator input selection/staging for later gate-level adapters.
- Record consumed input digests, tool/recipe identity and report/trace association.
- Reuse the generic supervisor for execution, cancellation and bounded output.

## Out of scope
- Gate-level timing/library integration, archived replay and a second ASIC engine.
- Inferring input association from the currently viewed physical run.

## Acceptance criteria
- A real simulator consumes the exact selected generated RTL and testbench inputs.
- Captured digests/references prove linkage to the claimed generated output.
- Missing, changed or stale inputs fail explicitly before a misleading result appears.
- Pass/fail, launch failure, cancellation and trace inspection retain exact identity.
- A rerun records its actual consumed inputs rather than assuming original linkage.
- Successful RTL simulation remains distinct from ASIC acceptance or signoff.

## Dependencies
No additional prerequisite tickets; existing structured execution supports an initial adapter.
[WB-036](WB-036-gate-level-simulation.md) will reuse this staging scaffold;
[WB-037](WB-037-archived-replay.md) adds a different retained-input replay guarantee.
Neither is required for current-project generated-RTL simulation.

## Estimate rationale
21 points, L, low confidence: simulator selection, build collateral and exact-input
staging remain project-specific. Incremental estimate includes the reusable scaffold,
but excludes subsequent gate-level integration and archive retention.

## Assumptions and decisions needed
Choose simulator, supported RTL dialect and testbench recipe. Decide immutable staging
versus verified copy semantics; input identities must describe bytes actually consumed.

## References
- [FS2-F07 adapters](../../backlog/fs2_followups.md#fs2-f07--generated-rtl-and-gate-level-adapters).
- [Explicit ASIC input type](../../../protocol/simulation.ml).
- [Supervisor integration](../../../backend/simulation_task.ml).
