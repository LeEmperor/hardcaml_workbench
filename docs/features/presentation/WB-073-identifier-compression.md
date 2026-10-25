---
id: WB-073
title: Identifier compression with global, workspace and tile toggles
category: presentation
feature_sets: [FS5, FS2]
status: delivered
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
and portable workspace configuration can provide inherited defaults. Testing helper
consolidation and global/workspace runtime controls are now delivered; the completion
record below supersedes the initial partial-delivery notes.

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
- [x] simulation-detail shows compressed attempt/job/discovery IDs by default.
- [x] Global, workspace and tile toggles each work; the most specific setting wins.
- [x] Delivered per-tile compression settings and resets survive restart through the preferences file.
- [x] Global/workspace runtime overrides persist with the required precedence.
- [x] Compressed IDs stay distinct within the displayed population; collisions extend tokens and narrow selectors reserve distinguishing markers.
- [x] Non-ASCII and short IDs are unchanged by semantic compression.

## Completion delivery

All requested scopes now work and persist in schema-6 preferences, with migration
from schemas 1–5. Precedence is tile runtime → configured tile → workspace runtime
→ global project/client default → built-in on. Scoped reset affects compression
only. Global/workspace controls explain the focused tile's effective source.

The shared identifier helper preserves short/non-ASCII IDs and human/provider labels.
Collision resolution extends first-four/last-four tokens deterministically across
the loaded population; narrow lists reserve explicit `#n` markers rather than
clipping away distinguishing characters. Tokens are stable while scrolling the same
population; a different history page can change expansion or ordinal assignment.
Extremely narrow viewports remain a physical visibility limit, not a change to raw IDs.

Testing detail and attempt lists, Session/Runs, relevant catalog/log metadata and
Waveforms identity displays now use the effective policy and shared helpers. Full
mode exposes exact IDs; RPC identities, raw source bytes and selection remain exact.

Verification passed: 27 scope combinations in fresh processes; identity guards and
reset/migration tests; collision/Unicode/width-fitted renderer tests; native HTTP/PTY
Testing and Waveforms controls/restart/export checks; independent Timing-preload
regression; full Workbench build/lint/runtest at `-j 1`; changed-file formatting.
Receipts: `/tmp/opencode/identifier-compression-n537648w/` and
`/tmp/opencode/wb073-timing-preload/`.

[Controls, scope and verification limits](../../identifier_compression.md).
Status is **delivered**, awaiting owner acceptance; not closed.

### Overview regression follow-up

The owner's subsequent blank Placement/Routing report was reproduced against the
supplied state. Saved header-off preferences explained missing titles; compression
actions preserved them. An independent terminal-result detail fallback discarded
available stage evidence without finalization. That reader is fixed and actual-state
native tests verify global/workspace/tile compression isolation, restart and missing
states. [Diagnosis, recovery controls and evidence](../../overview_compression_regression_plan.md).
This does not assert when the original header overrides were created or imply owner
acceptance of WB-073.

## Original partial delivery — Timing presentation (superseded)

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

**Gaps at that earlier checkpoint, now addressed above:** global/workspace controls,
simulation-detail coverage, helper consolidation and collision expansion. The early
helper compressed long Unicode IDs; the completed shared formatter now preserves
them unchanged. Plain first-four/last-four display alone was not a uniqueness
guarantee; the completed list resolver expands collisions while retaining exact selectors.

See the [earlier Timing controls and acceptance](../../timing_workspace_usability.md).
That increment alone was partial; the completion delivery above supersedes it.

## Dependencies
None required. Reuses WB-048's persistence and inheritance rules.

## Estimate rationale
8 points, medium confidence: the helper exists; three-level inheritance and
persistence carry most of the work.

## Assumptions and decisions needed
- Default on is implemented for the delivered Timing/Session per-tile trait.
- Collision resolution applies per tile's loaded identifier population, before
  viewport slicing where practical; it is not a workspace-wide ID registry.

## References
- [Completed compression controls and acceptance](../../identifier_compression.md)
- [Completion agent plan](../../timing_triage_identifier_completion_plan.md)
- [Timing compression, precision and preference controls](../../timing_workspace_usability.md)
- [Shared display helpers](../../../terminal/presentation.ml)
- [short_id](../../../terminal/overview_tiles.ml)
- [Testing workspace](../../testing_workspace.md)
- [WB-048 persistence](WB-048-presentation-persistence.md)
