---
id: WB-073
title: Identifier compression with global, workspace and tile toggles
category: presentation
feature_sets: [FS5, FS2]
status: partial
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
related: [WB-048, WB-063, WB-057, WB-069]
---

# WB-073 — Identifier compression with global, workspace and tile toggles

## Request
Owner note, 2026-10-20: in the simulation-detail tile, use compressed strings for
long strings such as attempt, job and discovery IDs. Add a command palette item that
toggles string compression globally, per workspace, and per selected/focused tile.

## Current baseline
The Timing follow-on added reusable `Presentation.identifier/source_path` display
helpers and a default-on `string_compression` per-tile trait. Timing, Session and
run-selector identities use first-four/last-four compression; source paths retain
recognizable filenames. Focused-tile compact/full/reset palette controls persist,
and portable workspace configuration can provide inherited defaults. Original
Testing helper consolidation and global/workspace-wide runtime toggles remain open.

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
- [x] Delivered per-tile compression settings and resets survive restart through the preferences file.
- [ ] Future global/workspace runtime overrides persist with the required precedence.
- [ ] Compressed IDs stay unique within a visible list; collisions fall back to longer forms.
- [ ] Non-ASCII and short IDs are unchanged.

## Partial delivery — Timing presentation

- Focused-tile commands: **Strings: Compress identifiers and source paths**,
  **Strings: Show full identifiers and source paths**, and reset-to-inherit.
- `string_compression : bool option` in workspace configuration and tile overrides;
  absent inherits, effective default is on. Preferences schema 4 added this and
  decimal precision; current schema 5 retains both and reads schemas 1–4.
- Full identifiers/report paths remain available by toggling compression off.
  Raw evidence, RPC identities and technical report bodies are not rewritten.
- Tests cover UTF-8-safe display, short strings, compact/full source metadata,
  sparse preference migration and fresh-process persistence. Actual a023 screenshots
  show `a023…4e4a` in Session and Runs.

**Remaining:** global and workspace-level runtime controls/precedence, original
simulation-detail attempt/job/discovery coverage and helper consolidation, and
visible-list collision expansion. The new helper safely compresses long Unicode
identifiers; the original criterion requiring all non-ASCII IDs unchanged has not
been claimed satisfied and needs reconciliation before closure. First-four/last-four
display is not a uniqueness guarantee; full exact IDs remain the selectors.

See [controls and acceptance](../../timing_workspace_usability.md). The whole ticket
is partial, not delivered/closed.

## Dependencies
None required. Reuses WB-048's persistence and inheritance rules.

## Estimate rationale
8 points, medium confidence: the helper exists; three-level inheritance and
persistence carry most of the work.

## Assumptions and decisions needed
- Default on is implemented for the delivered Timing/Session per-tile trait.
- Should the collision rule apply per tile or per workspace?

## References
- [Timing compression, precision and preference controls](../../timing_workspace_usability.md)
- [Shared display helpers](../../../terminal/presentation.ml)
- [short_id](../../../terminal/overview_tiles.ml)
- [Testing workspace](../../testing_workspace.md)
- [WB-048 persistence](WB-048-presentation-persistence.md)
