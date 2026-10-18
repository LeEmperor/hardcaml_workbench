---
id: WB-046
title: Interactive layout editing
category: workspaces
feature_sets: [FS3, FS5]
status: needs-design
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: L
points: 34
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [layout, editing, move, resize]
depends_on: []
related: [WB-013, WB-015, WB-047, WB-056, WB-057]
---

# WB-046 — Interactive layout editing

## Request
Edit layouts interactively, including move/reorder/resize and later pointer dragging
where useful. Requested size: **Unspecified**.

## Current baseline
Stable registry identities, requested tile geometry, hide/restore, focus and zoom
already exist. The renderer uses Fit or requested shelf sizes, not arbitrary free
placement. Portable export/import can preserve requested layout data.

## Scope
- Design a bounded editing mode for move/reorder/resize with keyboard completion.
- Separate requested geometry edits from client-local effective/clamped geometry.
- Define apply/cancel/recovery and persistence; specify optional drag gestures.

## Out of scope
Requiring mouse support, cross-window attachment or full floating-pane management.
If pointer dragging is unavailable, the first coherent editing outcome remains usable.

## Acceptance criteria
- [ ] Users can enter edit mode, change order/size/placement and finish by keyboard.
- [ ] Apply/cancel behavior is explicit and cannot strand or silently delete a tile.
- [ ] Resize/clamping preserves requested intent and offers off-screen/overflow recovery.
- [ ] Edits retain stable IDs, bindings and investigation state with conflict handling.
- [ ] Saved/exported arrangements reflect supported edits without claiming unsupported geometry.

## Dependencies
Required: none; registry mutations and layout foundations are delivered.
Related: [WB-013](WB-013-mouse-support.md) can enable optional drag gestures;
[WB-015](WB-015-layout-file-usability.md) improves file interchange;
[WB-047](WB-047-window-attachment.md) covers cross-surface movement;
[WB-056](../presentation/WB-056-floating-panes.md) adds optional floating policy;
[WB-057](../presentation/WB-057-utility-placement.md) supplies movable utility use cases.

## Estimate rationale
Thirty-four incremental points cover one coherent editing model and geometry/input/
persistence integration. Separately ticketed mouse and attachment work is excluded.

## Assumptions and decisions needed
Choose shelf/split constraints versus bounded free placement before implementation.
Low confidence reflects that product decision; optional drag integration must be bounded.

## References
- [Requested/effective layout contract](../workspaces_and_layouts.md)
- [Existing modes and template limits](../../fs3_adoption.md#workspace-templates)
- [Workspace host](../../../terminal/workspace_host.ml)
