---
id: WB-002
title: Further native icons and animation
category: presentation
feature_sets: [FS5]
status: partial
kind: enhancement
priority: P3
severity: n/a
requested_size: Ticket
size: S
points: 5
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [native, indicators, animation]
depends_on: []
related: [WB-001, WB-058, WB-059]
---

# WB-002 — Further native icons and animation

## Request
Add **more** useful icons and animation using native Bonsai Term capabilities.
Requested size: **Ticket**; this is incremental expansion of delivered indicators.

## Current baseline
The uncommitted working tree already delivers native Dot/Line spinners and semantic
icons for lifecycle, readiness, pins, artifacts, logs and simulation context.
Unicode/ASCII/Off controls, persistence and deterministic capture fallbacks exist.
The installed spinner API is known; a broad imported icon catalog is not assumed.

## Scope
- Review remaining high-value status/context locations and select a bounded set.
- Reuse the shared indicator policy and native components where appropriate.
- Keep text labels, semantic distinctions and width-tested ASCII/Off alternatives.

## Out of scope
Rebuilding native animation, introducing decorative title dots, or importing an
unverified general icon API. Nerd Font support is a separate optional feature.

## Acceptance criteria
- [ ] Agree and document the additional locations and intended semantic value.
- [ ] Existing and new indicators distinguish activity, completion and verdicts.
- [ ] Animation follows real typed activity and stops for terminal states.
- [ ] Unicode/ASCII/Off preserve labels, layout and keyboard actions.
- [ ] Presentation changes and animation cause no provider execution or extra polling.

## Dependencies
Required: none; native integration and shared semantic indicators are delivered.
Related: [WB-001](WB-001-checklist-column-alignment.md) shares cell budgeting;
[WB-058](WB-058-nerd-font-mode.md) is an optional alternate glyph mode;
[WB-059](WB-059-terminal-glyph-validation.md) broadens compatibility evidence.

## Estimate rationale
Five incremental points cover a bounded expansion and integration verification,
excluding the already delivered spinner and indicator foundations.

## Assumptions and decisions needed
Owner review selects useful additions. Dense packing, lowercase titles and no
decorative dots are current preferences, subject to later explicit review.

## References
- [Implemented native indicator plan](../../terminal_indicators_plan.md)
- [Appearance controls](../../appearance_presets.md)
- [Indicator implementation](../../../terminal/indicator.ml)
