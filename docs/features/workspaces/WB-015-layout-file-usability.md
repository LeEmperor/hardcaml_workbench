---
id: WB-015
title: Human-friendly workspace layout files
category: workspaces
feature_sets: [FS3, FS5]
status: partial
kind: enhancement
priority: P1
severity: n/a
requested_size: Ticket
size: M
points: 8
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [layout, files, templates, source-of-truth]
depends_on: []
related: [WB-016, WB-045, WB-046, WB-049]
---

# WB-015 — Human-friendly workspace layout files

## Request
Make workspace layouts easy to edit in files, with a clear source of truth.
Requested size: **Ticket**. Build on current preset/template formats and definitions.

## Current baseline
Central OCaml workspace definitions feed client/demo and starter exports. Versioned
sexp templates already support export/import/clone, preset identity, ordered views,
hidden state and geometry. Live identities/bindings stay in the daemon registry.
One-step [built-in default restoration](../../default_layout_restore.md) is also
delivered; the editable-file workflow/diagnostics in this ticket remain additional
scope, not work implicitly completed by that recovery command.

## Scope
- Improve readable layout examples, validation diagnostics and edit/apply workflow.
- State how editable files, registered presets and live saved layouts relate.
- Reuse or compatibly extend the existing format rather than add another layout engine.

## Out of scope
Arbitrary free placement, hotkey configuration, or moving live session identities
into portable templates. Appearance changes must not silently reapply geometry.

## Acceptance criteria
- [ ] A user exports, edits and imports a named arrangement using documented files.
- [ ] Explain exactly when file edits take effect and what remains live session state.
- [ ] Preset identity, view order, visibility and requested geometry round-trip honestly.
- [ ] Invalid/unsupported files fail clearly without partial registry changes.
- [ ] No duplicate source of truth or hidden preset refill overwrites user arrangements.

## Dependencies
Required: none; definitions, template codec and atomic registry mutations are delivered.
Related: [WB-016](WB-016-window-configuration.md) composes layouts into window config;
[WB-045](WB-045-template-picker.md) adds an optional TUI entry point;
[WB-046](WB-046-interactive-layout-editing.md) adds live editing;
[WB-049](../project/WB-049-config-migration.md) may change locations later.

## Estimate rationale
Eight incremental points cover a human-editable workflow, diagnostics and source-of-
truth clarification on delivered formats, excluding a new layout renderer or engine.

## Assumptions and decisions needed
Decide whether first delivery is explicit import/apply or includes reload-in-place.
Keep requested layout data separate from effective terminal-size clamping.

## References
- [Delivered template format/workflow](../../fs3_adoption.md#workspace-templates)
- [Template codec](../../../protocol/workspace_template.ml)
- [Workspace contract](../workspaces_and_layouts.md)
