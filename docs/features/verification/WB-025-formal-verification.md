---
id: WB-025
title: Formal verification support
category: verification
feature_sets: [FS2, FS4]
status: needs-design
kind: epic
priority: P3
severity: n/a
requested_size: Mega Feature
size: Mega
points: 89
confidence: low
estimate_scope: standalone-epic
origin: owner-intake
tags: [formal, properties, proof, counterexamples]
depends_on: []
related: [WB-028, WB-042]
---

# WB-025 — Formal verification support

## Request
Provide formal verification with explicit properties, proof outcomes and inspectable
counterexamples, rather than treating simulation success as a proof.

## Current baseline
FS2 supplies structured simulation and generic supervised execution, not a formal
property/proof contract. Its accepted milestone remains closed.

## Scope
- Define project-owned property discovery, assumptions, clocks and reset context.
- Capture source, tool, recipe and property identities for each proof attempt.
- Support one selected backend through project-owned recipes and the generic supervisor.
- Represent bounded checking and unbounded proof separately, including bound/depth.
- Retain counterexample artifacts and enough context for an exact investigation.
- Include contract/backend spike, one adapter and native result investigation in this epic.

## Out of scope
- A second ASIC engine, universal solver support or automatic property generation.
- Treating bounded success as unbounded proof or a proof result as physical signoff.

## Acceptance criteria
- A real project exposes named properties and reproducible captured proof inputs.
- Proved, bounded-no-counterexample, failed, unknown and timeout remain distinguishable.
- A failing property retains a counterexample and its assumptions/tool provenance.
- Cancellation and launch/backend failures preserve honest incomplete outcomes.
- Native inspection shows the property, bound/mode and exact artifact association.
- At least one bounded and one unbounded-capable recipe demonstrates honest semantics;
  unsupported modes are explicit rather than silently downgraded.

## Dependencies
No additional prerequisite tickets. [WB-028](WB-028-waveform-viewer.md) can improve
counterexample viewing; [WB-042](../infrastructure/WB-042-resource-budgets.md) can
strengthen limits. Neither is required for a bounded first adapter.

## Estimate rationale
89 points, Mega, low confidence: property semantics, solver integration and result
interpretation are unresolved. This standalone epic covers its first coherent delivery;
separately ticketed enablers are excluded and internal phases are included, not additive.

## Assumptions and decisions needed
Select the first backend, property language and supported proof modes before implementation.
Decide how assumptions and vacuity warnings are exposed; never hide an inconclusive proof.

## References
- [F09 simulation foundations](../simulation_and_tests.md).
- [Supervisor ownership](../../../backend/simulation_task.ml).
- [Current simulation protocol](../../../protocol/simulation.ml), not a proof schema.
