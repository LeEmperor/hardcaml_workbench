---
id: WB-024
title: Context-link wording and semantic emphasis
category: presentation
feature_sets: [FS5]
status: delivered
kind: defect
priority: P2
severity: S3
requested_size: Quick Fix
size: XS
points: 2
confidence: high
estimate_scope: incremental
origin: owner-intake
tags: [context, wording, emphasis]
depends_on: []
related: [WB-054]
---

# WB-024 — Context-link wording and semantic emphasis

## Request
Improve the text `context: linked: main`: highlight **linked** and avoid nested
colons. Requested size: **Quick Fix**. This is a reported cosmetic S3 defect.

## Current baseline
Main/independent context linking is already implemented and authoritative in the
session registry. Presentation uses typed binding facts and semantic emphasis.
The wording complaint does not demonstrate a context-binding correctness failure.

## Scope
- Reproduce the affected label and choose a clear single-label formulation.
- Emphasize the linked state semantically, with a readable non-color fallback.
- Keep the actual context name visible and independent states unambiguous.

## Out of scope
Changing linking semantics, context ownership, or run selection behavior.
No context migration or new binding mechanism is required.

## Acceptance criteria
- [x] Record the surface currently showing `context: linked: main`.
- [x] Revised wording avoids nested colon labels and highlights the linked state.
- [x] Main and independent context names remain distinguishable at narrow widths.
- [x] Restrained/ASCII/Off modes retain readable state without relying on color.
- [x] The change never mutates context bindings or evidence selection.

## Dependencies
Required: none; context binding and semantic styling already exist.
Related: [WB-054](WB-054-contextual-controls.md) may reuse the revised vocabulary in
breadcrumbs/help. Broader contextual controls are not required for this fix.

## Estimate rationale
Two incremental points cover reproduction, one label/styling adjustment and focused
rendering checks. No backend or interaction redesign is included.

## Assumptions and decisions needed
Confirm final wording, for example `context: linked to main`, with the owner.
The defect remains unconfirmed until its current rendering is reproduced.
Preserve current compact presentation rather than adding a decorative badge row.

## References
- [Run contexts](../run_contexts.md)
- [Appearance semantic roles](../appearance.md)
- [Host renderer](../../../terminal/host_view.ml)

## Delivery notes

**Owner closure — 2026-10-21:** closed under the owner's authorization to close
the non-signoff-dependent tickets in this set. The subsequent `linked` styling uses
the semantic Linked role mapped to theme success green plus bold. Custom theme-file
support remains separate work; current custom colors are configured in OCaml.

**Reproduced surface.** The Overview `live-status` (Session) tile's linkage row,
built by `Overview_tiles.status_rows` and drawn by `Overview_tiles.render`. Captured
before the change (any icon mode, 40 and 24 cells):

```
Context: Linked: Main
Context: Independent: Overview independe     (40 cells)
Context: Independent: Ov                     (24 cells)
```

**Wording (owner decision).** `Context: linked to <name>` for a shared context (Main,
or any context shared by more than one workspace) and `Context: own <name>` for an
independent one, e.g. `Context: linked to Main` and `Context: own Overview independent`.
That leaves one label colon. The state keyword comes first in lowercase, so right-clipping
removes the name before the state. At 24 cells the rows read `Context: linked to Main`
and `Context: own Overview in`.

**Emphasis.** The row has a new `emphasis` prefix (bytes of `value`). Only the `linked`
keyword gets the new `Overview_tiles.Role.Emphasis`, which the host maps to `Focus`
(bold accent). Restrained colour keeps the bold weight. ASCII and Off icon modes change
nothing, because the state is spelled out in the text. The full value and details stay
unchanged for inspection.

**Not changed.** The global header (`<workspace> | run … | Linked: Main | …`) has no
nested colon, and several PTY scripts and `docs/fs0_install_checks.md` pin it. If the
vocabulary should match there too, that's a follow-up for WB-054 or the owner. Bindings,
the registry and run selection are untouched. The edit is presentation-only, in the
`status_rows` value construction.

**Verification.** The expect test `context linkage avoids nested colons and keeps names
visible` in `terminal/overview_tiles.ml` renders linked and independent rows in all
three icon modes at 40 and 24 cells. It also asserts one label colon and that only
`linked` carries `Emphasis`. Commands:
`./scripts/with-switch.sh dune build -j20`, `./scripts/with-switch.sh dune runtest -j20`
(all pass).
The same PTY acceptance run as WB-001 (`test-overview-sidebar.py`,
`test-checklist-launch-workflow.py`, `test-launch-stage-consistency.py`) passed with the
new wording.
