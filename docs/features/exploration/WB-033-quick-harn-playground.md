---
id: WB-033
title: Quick-Harn comparative editing playground
category: exploration
feature_sets: [FS4, FS2, FS5]
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
tags: [quick-harn, playground, editors, comparison]
depends_on: [WB-012, WB-042]
related: [WB-031, WB-028]
---

# WB-033 — Quick-Harn comparative editing playground

## Request
Provide a Quick-Harn exploratory comparative playground with two editable code
variants/editor tiles and a way to run and compare their results.

## Current baseline
Workbench has project execution, tile hosting and evidence inspection. The precise
Quick-Harn concept is unknown; no existing library or integrated playground is asserted.

## Scope
- Assumed first outcome: a bounded scratch side-by-side playground with two editors.
- Capture immutable revisions of each variant when explicitly running a comparison.
- Use project-owned compile/test/measurement recipes through generic supervision.
- Compare attributable outputs/results and expose failure logs for each side.
- Own the scratch-variant and compile/test-output adapters around WB-012's pairing/
  compatibility rules; its bounded ASIC summary view is not a generic test comparator.
- Isolate scratch outputs from the working project and keep edits distinct from executed bytes.
- Include concept/recipe spike, bounded editor integration and an end-to-end A/B result view.

## Out of scope
- Inventing an existing Quick-Harn API, a general IDE or a second ASIC engine.
- Automatic source-tree replacement, unrestricted evaluation or autonomous design search.

## Acceptance criteria
- Two editor tiles retain independent editable variants in a declared scratch session.
- A run captures exact A/B source revisions, recipe/tool identities and parameters.
- Editing after launch cannot relabel old results as belonging to the new bytes.
- Each side can fail/cancel independently with honest partial comparative results.
- Comparisons align provenance and measurement context; absent output is not a pass.
- Execution/nested helpers and scratch output remain within shared budgets.
- Build/test success is not presented as proof, ASIC acceptance or physical signoff.

## Dependencies
[WB-012](../evidence/WB-012-run-comparison.md) is required for attributable A/B
results; [WB-042](../infrastructure/WB-042-resource-budgets.md) is required for
bounded scratch execution/storage. [WB-031](WB-031-design-space-sweeper.md) may
later expand variants, and [WB-028](../verification/WB-028-waveform-viewer.md) may
visualize traces; neither is a prerequisite to this two-variant playground.

## Estimate rationale
89 points, Mega, low confidence: unknown concept, editing/isolation and comparative
execution require design. Standalone epic covers a first coherent delivery with its
internal phases included, excluding WB-012/WB-042 and later sweep/viewer costs.

## Assumptions and decisions needed
Owner must clarify Quick-Harn's exact intended workflow. The bounded scratch A/B
interpretation is provisional; confirm language, editor depth, recipes and persistence.

## References
- [Module/tile foundations](../modules_and_tiles.md).
- [Execution module](../../fs0_execution_module.md).
- [Generic supervisor ownership](../../../backend/simulation_task.ml).
- [External integration architecture](../integration.md).
