---
id: WB-016
title: Full window configuration files
category: workspaces
feature_sets: [FS3]
status: delivered
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
Delivered 2026-10-21: versioned multi-window configuration, atomic fresh initialization
and additive application, stable authoring keys and persisted resolved definitions.
Stock window/workspace layouts use the same specification. See the
[authoring guide and native evidence](../../workspace_configuration.md).

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
- [x] A file describes multiple named window/workspace compositions without live IDs.
- [x] First creation and restart/restore have explicit, nonduplicating precedence rules.
- [x] Existing session modifications are not silently replaced by startup defaults.
- [x] Invalid references/configuration fail clearly without partial composition.
- [x] Context/binding defaults and local presentation versus registry state are documented.

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
Saved state wins; explicit client-read paths initialize fresh sessions only. Reapply
adds missing keys and preserves edits/policy. Reset-to-config remains a follow-on.
Configuration is declarative composition, not a second authoritative live registry.

## References
- [User-composable windows/workspaces: implementation plan](../../workspace_configuration_plan.md)
- [Window vocabulary and ownership](../workspaces_and_layouts.md)
- [Existing template exclusions](../../fs3_adoption.md#workspace-templates)
- [Protocol registry](../../../protocol/workspace.ml)
