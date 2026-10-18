---
id: WB-060
title: Richer A–E comparison gallery
category: presentation
feature_sets: [FS5]
status: partial
kind: enhancement
priority: P3
severity: n/a
requested_size: Unspecified
size: M
points: 8
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [gallery, fixtures, comparison]
depends_on: []
related: [WB-053, WB-055, WB-059, WB-061]
---

# WB-060 — Richer A–E comparison gallery

## Request
Expand the comparison gallery with richer, representative investigation content.
Requested size: **Unspecified**; retain comparison across all five candidates.

## Current baseline
A–E skins and deterministic terminal captures already exist, including Overview
and Timing examples. Shared rendering, compositional definitions and independent
color/icon/density controls are delivered. This is not a gallery from scratch.

## Scope
- Enrich a bounded set of shared fixtures with tables, diagnostics and inspectors.
- Capture identical labeled data and useful interaction states across A–E.
- Include wide and modest/narrow terminal grids and clearly marked mock content.

## Out of scope
Five separate domain implementations, a new registry, or selecting a final default.
Unimplemented tabs/peeks may be explicitly mocked rather than becoming blockers.

## Acceptance criteria
- [ ] All A–E candidates compare the same fixture identities and domain facts.
- [ ] Captures include focus/selection, overflow and independent appearance axes.
- [ ] Existing captures remain identifiable and the richer additions are documented.
- [ ] Mock source/test data is labeled and cannot be mistaken for real evidence.
- [ ] The gallery is reproducible without launching real physical flows.

## Dependencies
Required: none; capture/rendering and A–E foundations already exist.
Related: [WB-053](WB-053-tile-local-tabs.md) and [WB-055](WB-055-source-path-peeks.md)
can supply real components later; [WB-059](WB-059-terminal-glyph-validation.md)
adds compatibility evidence; [WB-061](WB-061-aesthetic-refinement.md) uses comparisons.

## Estimate rationale
Eight incremental points cover richer shared fixtures, interaction snapshots and
comparison documentation, excluding independent tab/peek implementation.

## Assumptions and decisions needed
Agree the most useful extra fixture and capture matrix before expanding content.
Current owner preferences guide review; all candidates remain available for comparison.

## References
- [Existing captures](../../appearance_presets.md#captures)
- [Gallery contract](../appearance.md#candidates-and-gallery-fs5)
- [Design interpretation](../../design/README.md)
