---
id: WB-054
title: Contextual actions, breadcrumbs and help
category: presentation
feature_sets: [FS5, FS1, FS2]
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
tags: [actions, breadcrumbs, help, inspector]
depends_on: []
related: [WB-019, WB-024, WB-053, WB-063]
---

# WB-054 — Contextual actions, breadcrumbs and help

## Request
Add richer contextual actions, breadcrumbs and help, including an explicit action
to close an inspector. Requested size: **Unspecified**.

## Current baseline
The command palette, focused-tile actions, hint controls and Timing investigation
views already exist. Run/context and evidence identities are typed facts.
This request extends discoverability and context rather than creating command routing.

## Scope
- Expose useful actions and availability reasons for the focused view/selection.
- Add concise breadcrumbs showing actual workspace/view/evidence context.
- Make inspector close explicit and document predictable return-focus behavior.

## Out of scope
New evidence backends, a universal navigation framework or replacing the palette.
Contextual commands must reuse existing action identities where available.

## Acceptance criteria
- [ ] Representative Timing and Testing views expose selection-appropriate actions.
- [ ] Breadcrumbs retain exact provenance or accessible full identities when shortened.
- [ ] Inspector close is visible in contextual help and keyboard-reachable.
- [ ] Closing returns focus predictably without changing selection or run binding.
- [ ] Unavailable actions explain why; hidden hints still have reachable help.

## Dependencies
Required: none; command, host and investigation foundations are delivered.
Related: [WB-019](WB-019-hideable-controls.md) coordinates hint recovery;
[WB-024](WB-024-context-link-label.md) aligns context wording;
[WB-053](WB-053-tile-local-tabs.md) adds optional local actions;
[WB-063](WB-063-testing-workspace.md) can adopt these controls independently.

## Estimate rationale
Eight incremental points cover a bounded set of contextual surfaces and focus/help
integration, excluding separately scoped tab or workspace redesign work.

## Assumptions and decisions needed
Choose representative actions and a compact breadcrumb vocabulary with owner review.
Dense packing remains the baseline; always-visible extra chrome is not assumed.

## References
- [Frontend composition](../../frontend_composition.md)
- [Investigation contract](../../fs1_investigation.md)
- [Simulation contract](../../fs2_simulation_contract.md)
