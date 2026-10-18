---
id: WB-059
title: Terminal/font/SSH/tmux glyph validation
category: presentation
feature_sets: [FS5, FS3]
status: partial
kind: validation
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 8
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [terminal, font, ssh, tmux]
depends_on: []
related: [WB-002, WB-052, WB-058, WB-060]
---

# WB-059 — Terminal/font/SSH/tmux glyph validation

## Request
Validate real terminal/font rendering, including remote SSH and tmux use.
Requested size: **Unspecified**.

## Current baseline
Renderer-cell checks, native indicator PTY checks and wide/narrow captures exist.
Unicode/ASCII/Off and deterministic fallbacks are delivered; ordinary fonts suffice.
Those checks are not a complete visual terminal/font/remote compatibility matrix.

## Scope
- Select a bounded terminal/font matrix covering local, SSH, tmux and SSH+tmux.
- Check glyph width, borders, animation, contrast, focus and fallback recovery.
- Record environment/version details and actionable compatibility limitations.

## Out of scope
Exhaustive terminal certification, font installation, or unrelated adoption redesign.
Optional Nerd Font validation applies only if that mode is available in the sample.

## Acceptance criteria
- [ ] Publish the selected terminal/font/locale/transport combinations and rationale.
- [ ] Compare actual rendered geometry with expected cell grids at wide/narrow sizes.
- [ ] Unicode/ASCII/Off preserve alignment, selection, readable text and recovery.
- [ ] SSH/tmux runs cover input, resize and activity rendering, not screenshots alone.
- [ ] Failures have repro details, fallback guidance and clearly scoped followups.

## Dependencies
Required: none; delivered modes can be validated immediately.
Related: [WB-002](WB-002-native-icons-animation.md) expands glyph usage;
[WB-052](../project/WB-052-adoption-polish.md) uses remote-workflow findings;
[WB-058](WB-058-nerd-font-mode.md) adds an optional font-specific mode;
[WB-060](WB-060-comparison-gallery.md) can reuse representative evidence.

## Estimate rationale
Eight incremental points cover one bounded compatibility campaign and documented
findings, building on existing PTY/renderer evidence rather than starting a harness.

## Assumptions and decisions needed
Owner selects representative workstation and small-laptop remote environments.
Separate renderer-measured width from actual font appearance in all conclusions.

## References
- [Current native indicator evidence](../../terminal_indicators_plan.md)
- [Gallery terminal requirements](../appearance.md#candidates-and-gallery-fs5)
- [FS3 adoption](../../fs3_adoption.md)
