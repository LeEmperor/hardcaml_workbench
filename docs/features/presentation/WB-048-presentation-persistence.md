---
id: WB-048
title: More persistent presentation overrides
category: presentation
feature_sets: [FS3, FS5]
status: closed
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

## Baseline before original delivery
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
- [x] Enumerate supported fields and round-trip each explicit value and inheritance.
- [x] Reset stays reset after polling, reconnect and process restart.
- [x] Moved/retyped/removed tiles and replacement sessions reject stale overrides.
- [x] Existing preference files remain readable under a declared migration policy.
- [x] Invalid files fail visibly and safely; changes do not trigger domain operations.

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

## Completion review — 2026-10-20

**Owner closure — 2026-10-21:** closed under the owner's authorization to close
the non-signoff-dependent tickets in this set. Automated restart/persistence evidence
remains the basis for those checks; no additional manual restart test is claimed.


**Delivered status confirmed.** Independent code review found no blocking defect in
the persistence whitelist, sparse inheritance/reset semantics, schema 1/2/3 migration,
session/tile/workspace/kind identity guards, or fresh-process coverage. The combined
tree's full `dune build -j20`, `dune runtest -j20` and `dune build -j20 @lint` passed.
This is implementation/automated-validation sign-off, not an interactive visual review.

## References
- [Subsequent Timing preference extension](../../timing_workspace_usability.md)
- [Persistent presentation baseline](../../fs3_adoption.md#persistent-presentation-preferences)
- [Preference schema](../../../terminal/presentation_preferences.ml)
- [Override fields](../../../terminal/tile_presentation.mli)

## Delivery notes
Delivered 2026-10-19.

**Subsequent extensions:** the Timing usability increment adds persistent per-tile
`decimal_places` (0–9, inherited default 3) and `string_compression` (inherited
default true). Schema 4 introduced those fields; schema 5 additionally
persists the project-level Timing background-index/explicit-only policy and reads
schemas 1–4. WB-073's completed scope adds global/workspace compression in **schema 6**,
which reads schemas 1–5 and retains scoped identity guards and reset-to-inherit.
See [compression controls and evidence](../../identifier_compression.md). CLI loading
policy overrides apply initially; later palette changes persist. Fresh-process and
legacy-schema tests passed. [Controls and evidence](../../timing_workspace_usability.md).
The original owner-accepted scope remains closed; this note does not claim new
owner acceptance for the later extensions or for WB-073's completed implementation.

The schema-v3 record below is historical evidence for the original delivery.

**Persisted per-tile fields** (explicit overrides only; absent = inherited):
header (unchanged, `tile_headers`), title, binding badge, hints, frame, padding and
run-selector row count (new `tile_appearance`). Hints and frame are purely presentational
explicit overrides, so they persist with the rest. **Not persisted:** run reference and
freshness (selection/data, not appearance) stay session-local; toggling them never
triggers a save. The split lives in `Tile_presentation.persisted`, which also drives the
`Workspace_host.set_presentation` save decision.

**Schema version 3** (`terminal/presentation_preferences.ml`):
- adds `tile_appearance` (sparse entries keyed by tile/workspace/kind, each field
  `[@sexp.option]`); required in v3, forbidden in v1/v2.
- v1/v2 files keep loading; every missing appearance field inherits (header kept).
- rejected: unknown versions, v3 without the list, v2 with it, appearance entries without
  a session, duplicate tiles, all-absent entries, negative padding, rows < 1, bad field
  values. Malformed/oversized files still fall back to defaults with a notice and are left
  untouched. `save` validates through the same decoder.
- same identity guards as headers (session/tile/workspace/kind); replacement sessions,
  retyped/moved/removed tiles inherit. One-shot restoration and last-writer-wins unchanged.

**Verification** (all via `./scripts/with-switch.sh`, serialized with flock):
- `dune build`, `dune runtest` (new inline test "every persisted tile appearance field
  round-trips, resets and is guarded", extended strict-schema and catalog tests),
  `dune build @lint` pass; `@fmt` clean for touched files.
- `python3 terminal/test_presentation_preferences_restart.py
  _build/default/terminal/presentation_preferences_probe.exe`: fresh-process round-trip of
  every field via the catalog, reset across restart, v2 and v1 legacy reads, v3 missing
  structure rejected.
- `scripts/test-fs3-adoption.py` (schema check updated to 3) and
  `scripts/test-default-layout-restore.py` pass.
