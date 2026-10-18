---
id: WB-019
title: Independently hideable window/palette controls
category: presentation
feature_sets: [FS5]
status: partial
kind: enhancement
priority: P2
severity: n/a
requested_size: Quick-Ticket
size: S
points: 3
confidence: high
estimate_scope: incremental
origin: owner-intake
tags: [hints, palette, chrome]
depends_on: []
related: [WB-048, WB-054, WB-057]
---

# WB-019 — Independently hideable window/palette controls

## Request
Make bottom control hints independently hideable in the main window and command
palette. Requested size: **Quick-Ticket**.

## Current baseline
Global chrome and per-tile hint/header controls already exist; explicit global
chrome choices persist. The palette is a bounded fuzzy overlay with keyboard input.
Those controls do not by themselves establish independent main/palette bottom hints.

## Scope
- Add distinct visibility choices for main-window and palette bottom control hints.
- Preserve accessible help and a discoverable command to restore each hint area.
- Reclaim hidden rows while maintaining correct overlay geometry and selection.

## Out of scope
A replacement chrome system, movable utility tiles, or wholesale help redesign.
Hiding hints must not disable their underlying commands.

## Acceptance criteria
- [ ] All four visible/hidden combinations work independently.
- [ ] Both controls can be restored by keyboard with every hint area hidden.
- [ ] Palette search, selection, dismissal and return focus remain usable.
- [ ] Narrow layouts gain the freed rows without clipping content or focus markers.
- [ ] Persistence behavior is explicit and does not alter the existing global toggle.

## Dependencies
Required: none; existing chrome and palette seams are sufficient.
Related: [WB-048](WB-048-presentation-persistence.md) coordinates preference policy;
[WB-054](WB-054-contextual-controls.md) may improve the help content;
[WB-057](WB-057-utility-placement.md) concerns placement rather than visibility.
These are optional coordination points, not blockers.

## Estimate rationale
Three incremental points cover two visibility settings, recovery commands and
focused geometry/input checks on the existing host and palette.

## Assumptions and decisions needed
Confirm default visibility and whether each choice is project-local or global.
Current dense packing favors reclaiming space, without fixing all future defaults.

## References
- [Appearance contract](../appearance.md)
- [Composition controls](../../frontend_composition.md)
- [Existing persistence](../../fs3_adoption.md#persistent-presentation-preferences)
