---
id: WB-058
title: Optional Nerd Font icons with fallbacks
category: presentation
feature_sets: [FS5]
status: proposed
kind: enhancement
priority: P3
severity: n/a
requested_size: Unspecified
size: S
points: 5
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [nerd-font, icons, fallback]
depends_on: []
related: [WB-002, WB-059]
---

# WB-058 — Optional Nerd Font icons with fallbacks

## Request
Offer an opt-in Nerd Font icon treatment while preserving ordinary terminal use.
Requested size: **Unspecified**.

## Current baseline
Unicode/ASCII/Off icons and native Dot/Line activity are delivered without special
font requirements. Shared semantic indicators preserve full labels and exact IDs.
The appearance architecture names Nerd Font as a future independent icon axis.

## Scope
- Add an explicitly selected Nerd Font glyph mode for a bounded semantic set.
- Provide documented Unicode/ASCII/Off recovery and conservative width budgeting.
- Keep semantic text usable when private-use glyphs are absent or rendered poorly.

## Out of scope
Installing fonts, requiring Nerd Fonts by default, or inferring font support reliably.
Do not replace delivered native spinner foundations or decorate all tile titles.

## Acceptance criteria
- [ ] Default startup remains usable with a normal terminal font.
- [ ] Explicit mode selection and reset/fallback are keyboard-reachable and documented.
- [ ] Glyphs retain the same semantic meanings and full text labels as other modes.
- [ ] Supported font/terminal combinations have measured cell-width evidence.
- [ ] Missing-glyph scenarios remain recoverable without altering domain data/actions.

## Dependencies
Required: none; the shared indicator and icon-mode seams are delivered.
Related: [WB-002](WB-002-native-icons-animation.md) can reuse chosen semantic roles;
[WB-059](WB-059-terminal-glyph-validation.md) supplies a wider compatibility matrix.
Broader validation is useful coordination, not an open prerequisite.

## Estimate rationale
Five incremental points cover a bounded glyph mapping, opt-in control/fallbacks and
representative width checks, excluding font installation and general icon expansion.

## Assumptions and decisions needed
Select supported Nerd Font family/version and fallback behavior explicitly.
Do not assume terminal glyph appearance can be detected from renderer width alone.

## References
- [Independent appearance axes](../appearance.md#independent-presentation-axes)
- [Existing indicator contract](../../terminal_indicators_plan.md)
- [Appearance implementation](../../../terminal/appearance.ml)
