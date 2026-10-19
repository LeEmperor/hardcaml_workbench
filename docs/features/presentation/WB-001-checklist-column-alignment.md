---
id: WB-001
title: Checklist column alignment
category: presentation
feature_sets: [FS5]
status: delivered
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
- [x] Reproduce and record the current misalignment with unequal-length stage labels.
- [x] Status keywords start in the same column when the available width permits.
- [x] Unicode, ASCII and Off modes align correctly without phantom icon padding.
- [x] Narrow widths truncate or compact predictably, preserving useful status text.
- [x] Selection, hit regions, full identities and existing semantic colors remain correct.

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

## Delivery notes
**Reproduction (confirmed defect).** I rendered `Overview_tiles.render` (the vertical
checklist renderer for the Overview stage-checklist tile and other utility tiles) with
stage labels of different lengths and the second row selected. Before the change,
Unicode at 40 cells:

```
✓ Synthesis: completed
> ⣷ Placement: running
◷ CTS: pending
↷ 界é stage: skipped
· Global routing: not requested
```

Every keyword started right after its own label, and the `> ` selection marker
pushed the selected row two cells further. ASCII and Off modes behaved the same way.
At narrow widths the right edge clipped the status first (`Global routing: not re`,
`CTS: pendi`).

**Fix.** `Overview_tiles.status_column` computes one keyword column for the rows that
are actually visible and carry a `status` (the checklist group). It measures each row's
prefix (indent, selection marker, indicator glyph) by display cells, so Off mode adds no
phantom icon cells and the selected row's keyword lines up with the rest. `row_spans`
pads after `Label:` up to that column. Rows without a status (aggregate facts, `Run`)
keep their compact `Label: value` form. Row order, identity, `details`/inspection text,
roles/colours and the selection index are unchanged. The host has no mouse hit regions,
and row positions do not move. After the change, Unicode at 40 cells:

```
✓ Synthesis:      completed
> ⣷ Placement:    running
◷ CTS:            pending
↷ 界é stage:      skipped
· Global routing: not requested
```

**Narrow widths and minimum useful width.** When the natural column plus the longest
visible keyword does not fit, the column moves left and labels clip by display cells
with `…` (for example `· Glob…: not requested`), so every keyword stays whole. The label
never shrinks below 3 cells (2 plus the ellipsis). The **minimum useful width** is
therefore `widest prefix + 3 + 2 (": ") + longest visible keyword`. For a Unicode/ASCII
checklist with a selected row and `not requested` that is 4 + 3 + 2 + 13 = **22 cells**
(18 in Off mode with no selection). Below it the keywords stay aligned and are
clipped on the right, as before.

**Test oracles.** Because keywords are now padded, PTY oracles that matched `Label: status`
literally now collapse status padding before matching
(`status_text` in `scripts/test-frontend-composition.py`, used by the shared
`Terminal.capture` and by the stage-row checks in `test-overview-sidebar.py`,
`test-frontend-refinement.py` and `test-terminal-indicators.py`; a local equivalent
in `test-synthetic-flow.py`). Only runs of 2 or more spaces after a colon are collapsed.

**Verification.** The expect test `checklist status keywords share a display-width
column` in `terminal/overview_tiles.ml` captures Unicode, ASCII and Off at 40, 30, 22 and
12 cells (it includes a wide-glyph label and a selected Running row). It also asserts
that for every width from 22 to 61 all keywords start in the same cell and no row
exceeds the width. Commands: `./scripts/with-switch.sh dune build -j20`,
`./scripts/with-switch.sh dune runtest -j20` (all pass).
PTY acceptance against the prebuilt binaries
(`python3 -B scripts/<name>.py --daemon _build/default/daemon/main.exe --client
_build/default/terminal/main.exe --preset-export
_build/default/terminal/workspaces/export_presets.exe --timeout 900`):
`test-overview-sidebar.py`, `test-checklist-launch-workflow.py` and
`test-launch-stage-consistency.py` passed. In `test-terminal-indicators.py`, all 303
checks passed, including every Unicode, ASCII and Off stage-row and indicator-prefix
check, and the script then stopped at its later Testing-workspace step
(`cooperative-testing-default` expects `SIMULATION CATALOG` pane titles, but the panes
are titled by kind id, `simulation-catalog`). That step is outside the checklist renderer
and this ticket. Owner visual review of the padded column is still welcome.

