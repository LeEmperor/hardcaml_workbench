---
id: WB-024
title: Context-link wording and semantic emphasis
category: presentation
feature_sets: [FS5]
status: needs-triage
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
- [ ] Record the surface currently showing `context: linked: main`.
- [ ] Revised wording avoids nested colon labels and highlights the linked state.
- [ ] Main and independent context names remain distinguishable at narrow widths.
- [ ] Restrained/ASCII/Off modes retain readable state without relying on color.
- [ ] The change never mutates context bindings or evidence selection.

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
