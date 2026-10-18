---
id: WB-045
title: TUI template browser/picker
category: workspaces
feature_sets: [FS3]
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
tags: [templates, picker, tui]
depends_on: []
related: [WB-015, WB-016, WB-049]
---

# WB-045 — TUI template browser/picker

## Request
Browse and choose workspace templates from the terminal UI.
Requested size: **Unspecified**.

## Current baseline
CLI starter export/import/clone and atomic registry mutations are delivered.
Imported workspaces appear in the existing workspace-switch palette after refresh.
FS3 deliberately did not introduce automatic discovery or a TUI file picker.

## Scope
- Present a bounded list of built-in and explicitly configured template sources.
- Show useful name/preset/view summaries and validation errors before import.
- Create a fresh workspace through the delivered import path with explicit naming.

## Out of scope
A new template engine, arbitrary filesystem explorer, or configuration migration.
Templates must not capture source investigation pins or selected run identities.

## Acceptance criteria
- [ ] Keyboard users can find, inspect, select and import a built-in template.
- [ ] A documented user-template source can be browsed without executing file content.
- [ ] Invalid/oversized/unknown-version templates give useful errors without mutation.
- [ ] Import creates fresh identities with documented context defaults atomically.
- [ ] Dismissal returns focus; failed or conflicting imports do not duplicate workspaces.

## Dependencies
Required: none; the template codec, registry import and palette foundations exist.
Related: [WB-015](WB-015-layout-file-usability.md) can improve editable examples;
[WB-016](WB-016-window-configuration.md) composes templates at another level;
[WB-049](../project/WB-049-config-migration.md) may later change search locations.
Initial explicit source selection avoids blocking on discovery/location policy.

## Estimate rationale
Eight incremental points cover browser/picker UX, summaries and error handling on
the existing import path, excluding template protocol or layout-engine reinvention.

## Assumptions and decisions needed
Choose first supported source locations, name-conflict behavior and preview detail.
Do not imply automatic whole-filesystem or upward discovery in the first delivery.

## References
- [Delivered template operations](../../fs3_adoption.md#workspace-templates)
- [Template codec](../../../protocol/workspace_template.ml)
- [Workspace service](../../../backend/workspace_service.ml)
