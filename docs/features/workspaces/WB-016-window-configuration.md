---
id: WB-016
title: Full window configuration files
category: workspaces
feature_sets: [FS3]
status: needs-design
kind: enhancement
priority: P2
severity: n/a
requested_size: 'Med Feaure'
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [windows, configuration, composition, restore]
depends_on: []
related: [WB-015, WB-045, WB-047, WB-049]
---

# WB-016 — Full window configuration files

## Request
Support full compositional window configuration: windows, their workspaces and
session restoration. Original requested size: **“Med Feaure”** (owner typo retained).

## Current baseline
The daemon owns session/window/workspace/tile identities and autosaved restoration.
Portable templates and CLI import/clone exist, but contain layout data rather than
live IDs, run selections or pins. Multi-monitor adoption remains additional scope.

## Scope
- Define a versioned configuration composing named windows and workspace templates.
- Specify initial composition versus restoring existing live session state.
- Validate and apply through the existing registry, preserving ownership boundaries.

## Out of scope
Live terminal attachment, cross-window movement or OS monitor orchestration.
WB-047 owns attachment; this ticket must not require it to validate configuration.

## Acceptance criteria
- [ ] A file describes multiple named window/workspace compositions without live IDs.
- [ ] First creation and restart/restore have explicit, nonduplicating precedence rules.
- [ ] Existing session modifications are not silently replaced by startup defaults.
- [ ] Invalid references/configuration fail clearly without partial composition.
- [ ] Context/binding defaults and local presentation versus registry state are documented.

## Dependencies
Required: none; registry, templates and session restoration already exist.
Related: [WB-015](WB-015-layout-file-usability.md) improves component layout editing;
[WB-045](WB-045-template-picker.md) adds optional browsing;
[WB-047](WB-047-window-attachment.md) consumes window composition for live surfaces;
[WB-049](../project/WB-049-config-migration.md) may later unify configuration locations.

## Estimate rationale
Thirteen incremental points cover composition schema, validation and restoration
policy integration, excluding separate live attachment and layout-engine work.

## Assumptions and decisions needed
Agree file precedence, named-window matching and explicit reapply/reset semantics.
Configuration is declarative composition, not a second authoritative live registry.

## References
- [Window vocabulary and ownership](../workspaces_and_layouts.md)
- [Existing template exclusions](../../fs3_adoption.md#workspace-templates)
- [Protocol registry](../../../protocol/workspace.ml)
