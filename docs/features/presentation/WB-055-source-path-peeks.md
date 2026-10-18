---
id: WB-055
title: Lightweight source/path peek overlays
category: presentation
feature_sets: [FS5, FS1]
status: needs-design
kind: enhancement
priority: P3
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [peek, source, path, overlay]
depends_on: []
related: [WB-021, WB-054, WB-056]
---

# WB-055 — Lightweight source/path peek overlays

## Request
Offer lightweight source and timing-path peeks without leaving the investigation.
Requested size: **Unspecified**.

## Current baseline
Timing investigation and a bounded transient palette lifecycle already exist.
The appearance contract calls for explicit overlay input capture and return focus.
Source mappings are not guaranteed; existing path evidence can be inspected without them.

## Scope
- Add a bounded read-only path peek from available exact path evidence.
- Add a source peek only where an explicit source mapping/reference is available.
- Define dismissal, scrolling, provenance display and return-focus semantics.

## Out of scope
Editing, source-map inference, full source navigation, or general stacked floats.
A path peek must not require source mappings or the whole WB-021 capability.

## Acceptance criteria
- [ ] A selected path opens a useful peek with no source mapping present.
- [ ] Mapped source opens at the declared location with exact reference context.
- [ ] Missing/stale mappings produce an honest unavailable state, never guessed source.
- [ ] Keyboard dismiss/scroll and narrow-size recovery preserve prior selection/focus.
- [ ] Peek capture behavior is explicit and does not accidentally swallow global input.

## Dependencies
Required: none; current overlay and path-evidence seams support a bounded delivery.
Related: [WB-021](../evidence/WB-021-source-navigation.md) may later supply more mappings;
[WB-054](WB-054-contextual-controls.md) improves entry actions;
[WB-056](WB-056-floating-panes.md) is broader optional float management.

## Estimate rationale
Thirteen incremental points cover two bounded read-only peek paths, mapping-aware
fallbacks and input/geometry integration, excluding a source-navigation engine.

## Assumptions and decisions needed
Choose the first supported source-reference format and peek size/lifecycle policy.
Source peeks require actual mapping data; path peeks require only path evidence.

## References
- [Floating surface contract](../appearance.md#floating-surfaces-and-reusable-primitives)
- [Hardware inspection](../hardware_inspection.md)
- [Timing workspace](../../../terminal/timing_workspace.ml)
