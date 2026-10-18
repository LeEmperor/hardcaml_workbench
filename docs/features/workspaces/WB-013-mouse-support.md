---
id: WB-013
title: Mouse focus, scrolling and actions
category: workspaces
feature_sets: [FS3, FS5]
status: proposed
kind: enhancement
priority: P2
severity: n/a
requested_size: Ticket
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [mouse, focus, scrolling, selection]
depends_on: []
related: [WB-014, WB-046, WB-053, WB-056]
---

# WB-013 — Mouse focus, scrolling and actions

## Request
Support mouse interaction, first for focus, scrolling and selection/actions with
keyboard parity. Requested size: **Ticket**. Drag layout editing comes later.

## Current baseline
The native terminal currently requests `No_mouse_events`. Keyboard focus, selection,
scrolling, palette capture and cell-aware layout already exist in the host.
Pointer support should reuse these actions and effective rendered geometry.

## Scope
- Enable supported native mouse events and map cell coordinates to visible targets.
- Add click-to-focus/select, wheel scrolling and bounded existing action activation.
- Route overlay/modal input before underlying tiles, with full keyboard equivalents.

## Out of scope
Drag move/resize, desktop window management, or mandatory mouse-only controls.
Interactive layout editing is separately scoped in WB-046.

## Acceptance criteria
- [ ] Clicking visible tiles/rows focuses/selects the intended target at current geometry.
- [ ] Wheel input scrolls the intended view with sensible clamping and focus policy.
- [ ] Supported pointer actions invoke the same typed intents as keyboard actions.
- [ ] Palette/modal capture prevents click-through and returns focus predictably.
- [ ] Resize, narrow layouts and terminal mouse disablement preserve keyboard usability.

## Dependencies
Required: none; action routing, geometry and keyboard behavior are delivered.
Related: [WB-014](WB-014-hotkey-configuration.md) configures keyboard equivalents;
[WB-046](WB-046-interactive-layout-editing.md) owns later drag editing;
[WB-053](../presentation/WB-053-tile-local-tabs.md) adds optional tab targets;
[WB-056](../presentation/WB-056-floating-panes.md) adds optional floating surfaces.

## Estimate rationale
Thirteen incremental points cover native event integration, hit testing and focus/
scroll/action parity checks. Drag editing and floating-window policy are excluded.

## Assumptions and decisions needed
Confirm click activation versus selection conventions and wheel focus behavior.
Document terminal/tmux event limitations and preserve ordinary text-copy recovery.

## References
- [Native event setup](../../../terminal/main.ml)
- [Workspace host](../../../terminal/workspace_host.ml)
- [Input ownership contract](../workspaces_and_layouts.md)
