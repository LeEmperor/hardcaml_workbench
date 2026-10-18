---
id: WB-053
title: Reusable tile-local tabs
category: presentation
feature_sets: [FS5]
status: needs-design
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [tabs, components, tile-local]
depends_on: []
related: [WB-013, WB-054, WB-060]
---

# WB-053 — Reusable tile-local tabs

## Request
Provide real reusable tabs inside tiles, inspired by the Studio treatment.
Requested size: **Unspecified**. These are tile-local view tabs, not workspace tabs.

## Current baseline
A–E skins, workspace switching and configurable tile headers already exist.
Filled title badges are presentation, not functional local tab groups.
The appearance contract explicitly separates workspace, tile-tab and run selection.

## Scope
- Define a reusable local tab model/component independent of a specific skin.
- Integrate a bounded representative tile with keyboard navigation and overflow.
- Preserve local view state and typed action/context meaning across tab switches.

## Out of scope
Replacing workspace navigation, changing selected runs, arbitrary docking or editing.
Mouse selection is optional followup rather than a prerequisite.

## Acceptance criteria
- [ ] A real tile switches between distinct local views with clear active state.
- [ ] Tabs work across A–E, including minimal/header-constrained presentation.
- [ ] Keyboard selection, focus and narrow-width overflow are recoverable.
- [ ] Tab changes preserve appropriate per-view state and do not change workspace IDs.
- [ ] Shared rendering contains no provider-specific I/O or fake domain results.

## Dependencies
Required: none; shared components and host-local state already exist.
Related: [WB-013](../workspaces/WB-013-mouse-support.md) can add pointer parity;
[WB-054](WB-054-contextual-controls.md) can expose local tab actions;
[WB-060](WB-060-comparison-gallery.md) can demonstrate the component across skins.

## Estimate rationale
Thirteen incremental points cover the component contract, representative integration,
local-state behavior and width/input verification beyond the existing skin system.

## Assumptions and decisions needed
Select the first tile/views and decide whether hidden headers retain a compact tab row.
Tab ordering and restoration policy need review; no new workspace engine is assumed.

## References
- [F12 tab distinction](../appearance.md#tile-first-chrome-and-headers)
- [Current candidate controls](../../appearance_presets.md)
- [Frontend composition](../../frontend_composition.md)
