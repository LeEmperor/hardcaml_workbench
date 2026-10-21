---
id: WB-073
title: Identifier compression with global, workspace and tile toggles
category: presentation
feature_sets: [FS5, FS2]
status: proposed
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 8
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [identifiers, compression, presentation, persistence]
depends_on: []
related: [WB-048, WB-063, WB-057]
---

# WB-073 — Identifier compression with global, workspace and tile toggles

## Request
Owner note, 2026-10-20: in the simulation-detail tile, use compressed strings for
long strings such as attempt, job and discovery IDs. Add a command palette item that
toggles string compression globally, per workspace, and per selected/focused tile.

## Current baseline
`Overview_tiles.short_id` shortens long ASCII opaque IDs to `prefix6...suffix6`,
and Testing attempt labels use it (commit 866c70b). `waveform_view.ml` has a separate
`abbreviate_attempt`. simulation-detail still prints full attempt, job and discovery
IDs. Compression cannot be switched off, and per-tile presentation overrides now
persist (WB-048).

## Scope
- Apply compression to simulation-detail's attempt, job and discovery IDs, and
  replace the duplicate helper with one shared function.
- A compression setting with three levels: global default, workspace override,
  tile override. Absent means inherited, as in WB-048.
- Palette commands to toggle at each level, plus reset-to-inherit, saved in the existing preferences store.
- Full IDs stay available in inspection/detail views.

## Out of scope
Human/provider labels (never compressed), and copy-to-clipboard.

## Acceptance criteria
- [ ] simulation-detail shows compressed attempt/job/discovery IDs by default.
- [ ] Global, workspace and tile toggles each work; the most specific setting wins.
- [ ] Settings and resets survive restart through the preferences file.
- [ ] Compressed IDs stay unique within a visible list; collisions fall back to longer forms.
- [ ] Non-ASCII and short IDs are unchanged.

## Dependencies
None required. Reuses WB-048's persistence and inheritance rules.

## Estimate rationale
8 points, medium confidence: the helper exists; three-level inheritance and
persistence carry most of the work.

## Assumptions and decisions needed
- Default on (proposed) or off?
- Should the collision rule apply per tile or per workspace?

## References
- [short_id](../../../terminal/overview_tiles.ml)
- [Testing workspace](../../testing_workspace.md)
- [WB-048 persistence](WB-048-presentation-persistence.md)
