---
id: WB-001
title: Checklist column alignment
category: presentation
feature_sets: [FS5]
status: needs-triage
kind: defect
priority: P2
severity: S3
requested_size: Ticket
size: S
points: 3
confidence: high
estimate_scope: incremental
origin: owner-intake
tags: [checklist, alignment, cell-width]
depends_on: []
related: [WB-002, WB-059]
---

# WB-001 — Checklist column alignment

## Request
Align checklist status keywords into a common column. Requested size: **Ticket**.
Treat the reported visual defect as unconfirmed until reproduced.

## Current baseline
Checklist stage rows already render typed statuses and compact semantic indicators.
Native Unicode/ASCII indicators and Off mode are delivered in the current tree.
Dense packing and lowercase, undecorated titles are the current owner baseline.

## Scope
- Compute a common label/status column within the visible checklist group.
- Budget variable label lengths, indicator cells and separators using display width.
- Define a narrow-width fallback without changing status meaning or row identity.

## Out of scope
New lifecycle states, checklist launch behavior, or a general table rewrite.
This ticket does not require further icon expansion.

## Acceptance criteria
- [ ] Reproduce and record the current misalignment with unequal-length stage labels.
- [ ] Status keywords start in the same column when the available width permits.
- [ ] Unicode, ASCII and Off modes align correctly without phantom icon padding.
- [ ] Narrow widths truncate or compact predictably, preserving useful status text.
- [ ] Selection, hit regions, full identities and existing semantic colors remain correct.

## Dependencies
Required: none; the checklist and indicator foundation is already delivered.
Related: [WB-002](WB-002-native-icons-animation.md) shares glyph budgeting;
[WB-059](WB-059-terminal-glyph-validation.md) supplies broader terminal validation.
Neither is needed to reproduce or fix this cosmetic defect.

## Estimate rationale
Three incremental points cover one shared row-layout correction and width/fallback
verification, rather than reimplementing checklist presentation.

## Assumptions and decisions needed
Confirm which checklist variants reproduce the issue and the minimum useful width.
Current density/title preferences guide the fix but are not immutable design rules.

## References
- [Checklist workflow](../../checklist_launch_workflow.md)
- [Delivered indicators](../../terminal_indicators_plan.md)
- [Host renderer](../../../terminal/host_view.ml)
