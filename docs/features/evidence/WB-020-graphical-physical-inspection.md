---
id: WB-020
title: Embedded physical/layout/heatmap inspection
category: evidence
feature_sets: [FS1, FS5]
status: needs-design
kind: epic
priority: P3
severity: n/a
requested_size: Large Feature
size: Mega
points: 55
confidence: low
estimate_scope: standalone-epic
origin: owner-intake
tags: [graphics, layout, heatmaps, crossprobe]
depends_on: []
related: []
---

# WB-020 — First graphical physical inspector

## Request
Original size: **Large Feature**. Inspect physical layout, heatmaps and timing-path
crossprobes graphically; choose the first surface and format explicitly.

## Current baseline
FS1 delivers typed physical/routing evidence and exact external binary handoff.
A retained GDS was loaded headlessly by KLayout; interactive GUI rendering and an
embedded viewer were not established. Native physical tables are not layout graphics.
Existing FS1 completion is independent of this new graphical delivery.

## Scope
- Select one host surface and one provider geometry/overlay format in an initial spike.
- Deliver a read-only viewport with bounded loading, pan/zoom and layer controls.
- Render one actual geometry dataset and one attributed heatmap overlay.
- Crossprobe one evidence-backed timing path/selection to provider-mapped geometry,
  with explicit unmapped portions and exact run/stage/source binding.
- Include spike, first rendering and integrated crossprobe phases within this epic.

## Out of scope
Layout editing, full commercial-viewer parity, every binary format, complete route
reconstruction and EDA execution. Source-to-OCaml mapping is separately scoped.

## Acceptance criteria
1. First host/format decisions and resource limits are recorded before implementation.
2. A real retained dataset renders with correct coordinate units, layers and provenance.
3. One heatmap states quantity, scale, producer and missing coverage explicitly.
4. Crossprobe uses supplied mapping identities and marks unmapped path segments honestly.
5. Changing run/stage cannot reuse an obsolete overlay; oversized inputs fail visibly.
6. Opening or navigating the viewer never starts a producer flow.

## Dependencies
Required: delivered artifact/evidence APIs; geometry mapping work is included here.
No additional ticket blocker. Related: none required; RTL/OCaml navigation is independent.

## Estimate rationale
55 points cover one coherent first viewer, overlay and bounded path crossprobe.
All internal phases are included; exclude separate ticket costs and future format expansion.

## Assumptions and decisions needed
TBD: native graphical, web or another embedded surface; first geometry/overlay format.
Default: read-only retained evidence and explicit mapping, no heuristic geometry matches.
Re-estimate after the spike if the selected producer cannot supply usable coordinates.

## References
- [Physical evidence and external-handoff limits](../../fs1_investigation.md)
- [Binary export foundation](../../../terminal/artifact_binary_export.ml)
- [Hardware inspection requirements](../hardware_inspection.md)
