---
id: WB-031
title: Performance-engineering design/build sweeper
category: exploration
feature_sets: [FS2, FS1, FS4]
status: needs-design
kind: epic
priority: P3
severity: n/a
requested_size: Mega Feature
size: Mega
points: 55
confidence: low
estimate_scope: standalone-epic
origin: owner-intake
tags: [design-space, variants, ppa, sweeps]
depends_on: [WB-012, WB-042]
related: [WB-030, WB-026, WB-033]
---

# WB-031 — Performance-engineering design/build sweeper

## Request
Sweep design parameters by building distinct variants and comparing their performance,
power and area evidence. This is different from sweeping simulation seeds/test parameters.

## Current baseline
Workbench has project operations, supervised execution and provenance-bearing ASIC
evidence. It does not yet provide a bounded design-variant exploration coordinator.

## Scope
- Define a finite variant space using project-owned generation/build/measurement recipes.
- Preview exact design parameters, recipe identities and expected resource reservations.
- Isolate variant outputs and preserve source/configuration/tool/run provenance.
- Reuse generic supervision and existing ASIC provider operations, not a second engine.
- Compare available PPA with aligned stage, corner, units and constraint context.
- Adapt captured variant/PPA results to WB-012's reusable comparison rules; that
  consumer-specific mapping belongs to this estimate, not WB-012's summary UI.
- Include recipe spike, bounded orchestration and one comparative native result surface.

## Out of scope
- Test-seed sweeps, autonomous optimization and universal design generation.
- Fabricating power when unavailable or treating completed builds/tests as signoff.

## Acceptance criteria
- One real project builds a finite set of distinct parameterized variants.
- Previewed inputs match consumed variant inputs and retained output identities.
- Partial failure/cancellation preserves completed evidence and honest missing cells.
- Comparison rejects or labels incompatible corners/stages/units/constraints.
- Power is activity/model/corner-qualified where supplied, otherwise unavailable.
- Concurrent variants/nested helpers obey aggregate execution and output/storage limits.
- Inspection does not launch flows; explicit launches use project-owned recipes.

## Dependencies
[WB-012](../evidence/WB-012-run-comparison.md) is required for provenance-aware
comparison; [WB-042](../infrastructure/WB-042-resource-budgets.md) is required for
aggregate reservations. [WB-030](../verification/WB-030-seed-parameter-sweeps.md)
is a distinct test-input workflow; [WB-026](../evidence/WB-026-power-analysis.md) and
[WB-033](WB-033-quick-harn-playground.md) are optional evidence/playground enablers.

## Estimate rationale
55 points, Mega, low confidence: variant isolation, recipe contracts and comparative
exploration remain substantial work, but this first finite-grid implementation reuses
project recipes, the supervisor and separately estimated comparison/budget features.
The standalone epic excludes WB-012/WB-042 costs and includes its internal phases.
Re-estimate upward if adaptive search, arbitrary distributed workers or automatic
recipe generation is added; none is included in these 55 points.

## Assumptions and decisions needed
Select initial design parameters, recipe and measurement endpoints. Decide acceptable
missing PPA dimensions and resume policy; test parameters that rebuild hardware belong here.

## References
- [Execution foundations](../../fs0_execution_module.md).
- [ASIC operation boundary](../../../backend/asic_service.mli).
- [Existing supervisor](../../../backend/service.ml).
- [Hardware evidence architecture](../hardware_inspection.md).
