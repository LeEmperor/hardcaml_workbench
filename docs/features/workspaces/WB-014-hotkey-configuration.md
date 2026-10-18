---
id: WB-014
title: Hotkey configuration file
category: workspaces
feature_sets: [FS3, FS5]
status: proposed
kind: enhancement
priority: P2
severity: n/a
requested_size: Ticket
size: M
points: 8
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [hotkeys, sexp, configuration]
depends_on: []
related: [WB-013, WB-049, WB-054]
---

# WB-014 — Hotkey configuration file

## Request
Make hotkeys configurable through an editable sexp file mapping keys to actions.
Requested size: **Ticket**.

## Current baseline
Keyboard commands, palette action identities and modal/focused-tile routing exist.
Current bindings provide the working default; configurable mapping is additional UX.
Modal input must continue to capture keys before tile/global bindings.

## Scope
- Define a versioned sexp mapping for a bounded documented configurable action set.
- Validate key syntax, unknown actions and conflicts within effective input scopes.
- Expose effective bindings in help while retaining safe defaults and recovery.

## Out of scope
An executable macro language, command implementation changes, or configuration
location migration. Mouse support is not needed to configure keyboard input.

## Acceptance criteria
- [ ] A documented file remaps representative global and focused-view actions.
- [ ] Conflicting, malformed and unsupported mappings produce actionable diagnostics.
- [ ] Modal capture, focus precedence and multi-key sequences remain deterministic.
- [ ] Palette/help show effective bindings and essential recovery stays reachable.
- [ ] Missing/bad configuration has a defined fallback with no silent action substitution.

## Dependencies
Required: none; existing action and input routing foundations are sufficient.
Related: [WB-013](WB-013-mouse-support.md) shares action parity;
[WB-049](../project/WB-049-config-migration.md) may later unify locations/precedence;
[WB-054](../presentation/WB-054-contextual-controls.md) can display effective bindings.
No optional configuration migration is a blocker.

## Estimate rationale
Eight incremental points cover sexp parsing, action mapping, conflict diagnostics and
modal/focus integration, excluding new command capabilities or a macro interpreter.

## Assumptions and decisions needed
Choose first-load versus explicit reload behavior and initial file location.
Agree reserved recovery keys and whether context-scoped duplicate bindings are legal.

## References
- [Command architecture](../commands_and_flows.md)
- [Input precedence](../workspaces_and_layouts.md)
- [Native input handling](../../../terminal/main.ml)
