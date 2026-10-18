---
id: WB-048
title: More persistent presentation overrides
category: presentation
feature_sets: [FS3, FS5]
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
tags: [persistence, overrides, inheritance]
depends_on: []
related: [WB-019, WB-015, WB-057]
---

# WB-048 — More persistent presentation overrides

## Request
Make more per-tile presentation settings persistent. Both identical presentation
persistence bullets in the owner intake are consolidated here as one ticket.
Requested size: **Unspecified** for both occurrences; scope and points count once.

## Current baseline
Global appearance, layout mode and chrome already persist; explicit tile-header
overrides persist with session/tile/workspace/kind identity guards and reset support.
Other override fields remain transient, including title, badge, padding and row count.
The existing override type also includes run reference, freshness, hints and frame.

## Scope
- Persist the agreed remaining explicit appearance overrides in the existing store.
- Preserve absent/inherited values and reset-to-inherit across restart.
- Extend versioning, validation, identity guards and one-shot restoration coherently.

## Out of scope
Persisting run selections, pins, focus, scroll or provider data as presentation.
Portable templates remain distinct from identity-scoped local preferences.

## Acceptance criteria
- [ ] Enumerate supported fields and round-trip each explicit value and inheritance.
- [ ] Reset stays reset after polling, reconnect and process restart.
- [ ] Moved/retyped/removed tiles and replacement sessions reject stale overrides.
- [ ] Existing preference files remain readable under a declared migration policy.
- [ ] Invalid files fail visibly and safely; changes do not trigger domain operations.

## Dependencies
Required: none; persistence and override resolution foundations are delivered.
Related: [WB-019](WB-019-hideable-controls.md) may add independent hint choices;
[WB-015](../workspaces/WB-015-layout-file-usability.md) must distinguish template data;
[WB-057](WB-057-utility-placement.md) may introduce later placement preferences.

## Estimate rationale
Eight incremental points cover schema evolution and multi-field restoration/reset
semantics, not a new persistence engine or two separately estimated requests.

## Assumptions and decisions needed
Agree which remaining fields persist and their project/session scope before coding.
Keep existing last-writer-wins behavior unless a separately scoped decision changes it.

## References
- [Persistent presentation baseline](../../fs3_adoption.md#persistent-presentation-preferences)
- [Preference schema](../../../terminal/presentation_preferences.ml)
- [Override fields](../../../terminal/tile_presentation.mli)
