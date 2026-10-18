---
id: WB-047
title: Full window/monitor attachment
category: workspaces
feature_sets: [FS3]
status: needs-design
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: L
points: 21
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [windows, monitors, attachment, multi-client]
depends_on: []
related: [WB-016, WB-044, WB-046, WB-056]
---

# WB-047 — Full window/monitor attachment

## Request
Make multiple terminal/window surfaces usable across monitors with explicit
attachment and workspace movement. Requested size: **Unspecified**.

## Current baseline
The daemon already owns session/window/workspace/tile registry identities and run
contexts. Clients own dimensions, navigation, focus and scroll. FS3 reconnect and
restoration exist; full multi-monitor adoption UX/acceptance remains later work.

## Scope
- Expose explicit attachment/detachment to named registry windows on live clients.
- Define workspace movement between surfaces while preserving bindings and identity.
- Verify independent local browsing with shared authoritative context/data updates.

## Out of scope
OS monitor detection/control, declarative window files or a second registry.
Floating panes and mouse dragging are optional separate presentation capabilities.

## Acceptance criteria
- [ ] Two terminal surfaces attach predictably to chosen windows in one project session.
- [ ] Local focus, scrolling, active views and dimensions do not overwrite each other.
- [ ] Linked context changes propagate; independent contexts remain independent.
- [ ] Moving a workspace preserves IDs, bindings and documented local-state behavior.
- [ ] Disconnect/reconnect, stale clients and detach recovery avoid duplicates or lost work.

## Dependencies
Required: none; registry, context and reconnect foundations are delivered.
Related: [WB-016](WB-016-window-configuration.md) supplies optional declarative setup;
[WB-044](../infrastructure/WB-044-load-acceptance.md) broadens multi-client load evidence;
[WB-046](WB-046-interactive-layout-editing.md) adds optional editing gestures;
[WB-056](../presentation/WB-056-floating-panes.md) manages panes within a surface.

## Estimate rationale
Twenty-one incremental points cover live attachment UX, movement and bounded
multi-surface recovery acceptance, excluding delivered registry and optional config.

## Assumptions and decisions needed
Decide whether multiple clients may attach to the same window and how conflicts show.
Define detach/empty-window lifecycle and the first two-surface owner-review scenario.

## References
- [Window and context ownership](../workspaces_and_layouts.md)
- [FS3 reconnect baseline](../../fs3_adoption.md)
- [Workspace registry](../../../protocol/workspace.ml)
