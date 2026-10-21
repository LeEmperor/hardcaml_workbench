---
id: WB-070
title: Ctrl-Backspace word deletion in the palette and text inputs
category: workspaces
feature_sets: [FS5]
status: proposed
kind: defect
priority: P2
severity: S3
requested_size: Unspecified
size: XS
points: 2
confidence: high
estimate_scope: incremental
origin: owner-intake
tags: [palette, input, keyboard]
depends_on: []
related: [WB-014, WB-067]
---

# WB-070 — Ctrl-Backspace word deletion in the palette and text inputs

## Request
Owner note, 2026-10-20: Ctrl+Backspace should work in the command palette.

## Current baseline
The Waveforms Signals filter already deletes a word on Ctrl-Backspace or Ctrl-W
(`Waveform_view.edit_key` / `delete_word`). It handles the encodings the native
decoder actually delivers (^H, ^W, Ctrl/Meta+Backspace). The command palette and the
other text inputs — Timing filter, inspector filter, simulation launch form,
synthesis filter — offer only Backspace and Ctrl-U.

## Scope
- Move the waveform word-deletion helper to a shared module and use it in the
  palette query and every other single-line text input.
- Mention `Ctrl-BS/Ctrl-W word` in each input's help line where it fits.

## Out of scope
Cursor movement inside inputs, Alt-word motions and configurable bindings (WB-014).

## Acceptance criteria
- [ ] Ctrl-Backspace and Ctrl-W delete the previous word in the palette and all listed inputs.
- [ ] Plain Backspace still deletes one code point; non-ASCII text is never split.
- [ ] Terminals that send plain DEL for Ctrl-Backspace still have Ctrl-W.
- [ ] Existing waveform filter tests keep passing against the shared helper.

## Dependencies
None.

## Estimate rationale
2 points, high confidence: the helper and its decoder tests already exist.

## Assumptions and decisions needed
None beyond confirming the input list.

## References
- [Word deletion helper](../../../terminal/waveform_view.ml)
- [Palette controls](../../frontend_composition.md)
