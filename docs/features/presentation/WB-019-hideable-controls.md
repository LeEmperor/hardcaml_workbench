---
id: WB-019
title: Independently hideable window/palette controls
category: presentation
feature_sets: [FS5]
status: closed
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
- [x] All four visible/hidden combinations work independently.
- [x] Both controls can be restored by keyboard with every hint area hidden.
- [x] Palette search, selection, dismissal and return focus remain usable.
- [x] Narrow layouts gain the freed rows without clipping content or focus markers.
- [x] Persistence behavior is explicit and does not alter the existing global toggle.

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

## Delivery notes

**Owner acceptance — 2026-10-21:** owner confirmed the hints work correctly and
authorized closure of the non-signoff-dependent tickets. WB-019 is closed/accepted.

- **Default:** both hint areas visible (unchanged behavior for new and existing users).
- **Persistence:** stored with the other global presentation choices in the existing
  per-project/environment `presentation-<digest>.sexp`. The schema moves to version 2
  with explicit `main_hints`/`palette_hints` fields; version 1 files still load (both
  hint areas visible), version-2 files missing either field and version-1 files
  carrying them are rejected, as are unknown versions. The global chrome toggle is
  unchanged: with chrome off the footer stays suppressed regardless of hint choices,
  and hint toggles never write `chrome`.
- **Commands/keys:** palette commands `host.hints.main` ("Hide/Show main window
  control hints (Space c h)") and `host.hints.palette` ("Hide/Show command palette
  control hints (Space c p)"), plus the chords **Space c h** and **Space c p**, which
  work with every hint area hidden (the palette itself still opens with Space c c).
  Toggling posts a transient notice naming the restore chord.
- **Geometry:** a hidden main hint row is returned to the tile area (including compact
  narrow layouts); a notice or filter/paste status still claims the row. A hidden
  palette hint row returns both the hint row and its separator to the result list;
  notices (e.g. an unavailable reason) still show there. Selection scrolling uses the
  same row budget, so the selected row stays visible.
- **Verification:**
  - `dune runtest terminal`: new `host_view.ml` tests (all four combinations at
    120×40, 80×24, 44×14, 30×9 incl. reclaimed rows, tile bounds, palette panel
    independence, last-selection visibility, notices, chrome independence; keyboard
    restore with all hidden, palette search/Enter/Escape and return focus) and
    `presentation_preferences.ml` tests (all chrome×main×palette round-trips, schema 1
    compatibility, strict validation) pass.
  - `terminal/test_presentation_preferences_restart.py` (fresh-process round-trip of
    all four combinations and a schema 1 file) passes.
  - `scripts/test-fs3-adoption.py` extended with a real HTTP/PTY segment: Space c h /
    Space c p in every combination, palette footer presence, saved file contents, a
    fresh client restoring both hidden and keyboard-restoring each area: PASSED.

## References
- [Appearance contract](../appearance.md)
- [Composition controls](../../frontend_composition.md)
- [Existing persistence](../../fs3_adoption.md#persistent-presentation-preferences)
