---
id: WB-057
title: Configurable status/help/navigation placement
category: presentation
feature_sets: [FS5, FS3]
status: partial
kind: enhancement
priority: P3
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [utility, chrome, placement]
depends_on: []
related: [WB-015, WB-019, WB-046, WB-048]
---

# WB-057 — Configurable status/help/navigation placement

## Request
Make utility chrome movable/configurable: status, help, navigation and related
project context should fit the chosen workspace arrangement. Size: **Unspecified**.

## Current baseline
Composable workspace definitions, utility presentation policies and hideable chrome
already exist. F12 favors ordinary mountable utility tiles with thin host recovery.
This is richer placement and composition, not the initial chrome implementation.

## Scope
- Define placement choices for a bounded set of utility views using existing layouts.
- Keep utility meaning and commands independent of top/bottom/side location.
- Preserve keyboard access when all visible navigation/help chrome is hidden.

## Out of scope
Arbitrary drag editing, full floating management, or a second layout registry.
No requirement to keep a mandatory global header/footer band.

## Acceptance criteria
- [ ] Status/help/navigation can occupy documented alternative locations.
- [ ] Moving/hiding utilities preserves workspace, run bindings and local investigation.
- [ ] All navigation and restore commands remain keyboard-reachable with utilities hidden.
- [ ] Narrow layouts expose overflow/hide recovery without duplicating controllers.
- [ ] Saved placement uses the appropriate existing layout/preference ownership seam.

## Dependencies
Required: none; compositional definitions and the authoritative registry are delivered.
Related: [WB-015](../workspaces/WB-015-layout-file-usability.md) can improve file editing;
[WB-019](WB-019-hideable-controls.md) provides independent hint visibility;
[WB-046](../workspaces/WB-046-interactive-layout-editing.md) adds optional live editing;
[WB-048](WB-048-presentation-persistence.md) coordinates local override persistence.

## Estimate rationale
Thirteen incremental points cover bounded utility composition, configuration and
recovery verification, excluding separate free-placement or persistence extensions.

## Assumptions and decisions needed
Choose which utilities are relocatable and which thin host affordances must remain.
Dense packing is a current preference, not a permanent ban on alternate arrangements.

## References
- [Tile-first chrome contract](../appearance.md#tile-first-chrome-and-headers)
- [Frontend composition](../../frontend_composition.md)
- [Workspace source definitions](../../../terminal/workspaces/common.ml)
