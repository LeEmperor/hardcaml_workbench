---
id: WB-056
title: General floating-pane management
category: presentation
feature_sets: [FS5, FS3]
status: needs-design
kind: enhancement
priority: P3
severity: n/a
requested_size: Unspecified
size: L
points: 34
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [floating, focus, geometry]
depends_on: []
related: [WB-013, WB-046, WB-047, WB-055]
---

# WB-056 — General floating-pane management

## Request
Explore full floating windows/panes with useful native capabilities where supported.
Requested size: **Unspecified**; this is optional extended presentation scope.

## Current baseline
The host has tiled workspaces and a supported single transient palette overlay.
General stacked floats, persistent floating panes and tiled/floating transitions
are not established by that palette. Native capability availability needs inspection.

## Scope
- Define a bounded first model for multiple managed floating panes on a surface.
- Inspect installed native placement/capture/focus capabilities before choosing adapters.
- Include keyboard move/resize, stacking, dismissal and off-screen recovery policy.

## Out of scope
An OS window manager, mandatory mouse dragging, or cross-monitor attachment.
Do not imply all editor/Ches floating APIs are installed Workbench dependencies.

## Acceptance criteria
- [ ] Document supported pane types, native capability limits and explicit fallbacks.
- [ ] Multiple floats have predictable stacking, focus and modal/nonmodal input rules.
- [ ] Keyboard placement/resize and tiled return preserve tile identity and context.
- [ ] Terminal resize cannot strand panes or make recovery commands unreachable.
- [ ] Closing a float restores focus and does not cancel unrelated domain execution.

## Dependencies
Required: none; existing host/registry/overlay foundations support independent design.
Related: [WB-013](../workspaces/WB-013-mouse-support.md) enables optional pointer controls;
[WB-046](../workspaces/WB-046-interactive-layout-editing.md) shares geometry concepts;
[WB-047](../workspaces/WB-047-window-attachment.md) manages separate attached surfaces;
[WB-055](WB-055-source-path-peeks.md) is a narrower overlay use case.

## Estimate rationale
Thirty-four incremental points cover one coherent managed-float delivery, including
capability investigation and recovery. They exclude separate mouse/window tickets.

## Assumptions and decisions needed
Owner review must select pane types, persistence expectations and native-only limits.
Scope remains optional; low confidence reflects unresolved interaction contracts.

## References
- [Floating-surface requirements](../appearance.md#floating-surfaces-and-reusable-primitives)
- [Window/workspace ownership](../workspaces_and_layouts.md)
- [Host state](../../../terminal/workspace_host.ml)
