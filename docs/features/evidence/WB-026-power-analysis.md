---
id: WB-026
title: Activity/corner-qualified power analysis
category: evidence
feature_sets: [FS1]
status: needs-design
kind: feature
priority: P3
severity: n/a
requested_size: Feature
size: L
points: 34
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [power, activity, model, corner]
depends_on: []
related: []
---

# WB-026 — Qualified power measurements

## Request
Original size: **Feature**. Inspect power measurements with the activity assumptions,
model and corner necessary to interpret them honestly.

## Current baseline
FS1's adopted typed domains cover timing, clocks, physical and routing evidence.
Their producer/unit/corner provenance patterns are reusable, but do not establish
a delivered power-analysis contract or measured power for existing runs.
Simulation artifacts alone are not proof of representative switching activity.

## Scope
- Adopt one provider power report and its retained model/activity references.
- Represent reported components such as leakage/internal/switching only where supplied.
- Show voltage, temperature, process/corner, analysis stage and measurement units.
- Distinguish vector-based, vectorless and unknown activity, including time window,
  coverage and clock assumptions when available.

## Out of scope
A universal power engine, automatic activity generation or EDA runs, power optimization,
and assuming sums or cross-corner comparisons are valid without producer semantics.

## Acceptance criteria
1. One retained report exposes measured values with exact source/producer identity.
2. Activity source, model/library and corner are visible or explicitly unknown.
3. Vectorless estimates cannot be presented as measured workload switching behavior.
4. Missing components/coverage retain unknown state rather than zero or a fabricated total.
5. Stale/mismatched activity or design identity is diagnosed before trusted attribution.
6. Detail retains raw evidence, units and the provider's aggregation semantics.

## Dependencies
Required: delivered typed evidence infrastructure and one selected power producer.
No additional ticket blocker; adopting the first power contract is included here.
Related: none; additional general report adoption is independently scoped.

## Estimate rationale
34 points cover one power family, qualification model and bounded inspection workflow.
Exclude simulation-adapter creation, activity-capture engines and other evidence tickets.

## Assumptions and decisions needed
TBD: first producer/report format and minimum acceptable activity/model metadata.
Default: inspect retained evidence only and label insufficient qualification explicitly.
No accuracy claim follows merely from successful parsing or numeric availability.

## References
- [Current adopted domains](../../fs1_investigation.md)
- [Inspection evidence model](../../../protocol/asic_inspection.ml)
- [Hardware inspection requirements](../hardware_inspection.md)
