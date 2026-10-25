---
id: WB-007
title: Hierarchy tile and selected top visibility
category: project
feature_sets: [FS1, FS2]
status: delivered
kind: enhancement
priority: P2
severity: n/a
requested_size: Ticket
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [hierarchy, top, tiles]
depends_on: []
related: [WB-002]
---

# WB-007 — Visible hierarchy and top

## Request
Original size: **Ticket**. Make the hardware hierarchy and selected/tested top
visible in a tile. The owner is unsure whether Overview is its best home.

## Current baseline
Implemented and automatically verified 2026-10-21. See
[controls and acceptance](../../hierarchy_tile.md). Owner visual review is separate.

The driver exports bounded structural hierarchy artifacts with ports and provenance.
The terminal already offers “Inspect hardware hierarchy” and current/historical
generation checks. This is not a request to rebuild that inspector.
Structural hierarchy is not a signal/operator graph or proof of a test's DUT.

## Scope
- Expose a reusable compact hierarchy tile with expandable instance structure.
- Display the selected elaboration top and exact generating target/configuration.
- Distinguish a simulation's declared DUT/top from the selected elaboration top;
  show the tested top only when provider evidence supplies that association.
- Preserve local expansion/selection and offer the existing inspector for detail.

## Out of scope
New elaboration engines, inferred DUT mappings and alternate-top execution.
Do not turn a hierarchy-node selection into a new build or simulation request.

## Acceptance criteria
1. The tile identifies its hierarchy artifact, generating job and top.
2. Historical hierarchy cannot appear current after a target/configuration change.
3. A missing tested-top association is labeled unknown rather than copied from selection.
4. Two tile instances can browse independently without regenerating hierarchy.
5. Unsupported or pending hierarchy has an actionable, nonempty state.

## Dependencies
Required: delivered hierarchy reader and tile host; no additional ticket prerequisite.
Related: [WB-002](../presentation/WB-002-native-icons-animation.md) delivered the
shared hierarchy markers; its remaining hierarchy-specific visual review is tracked
here. Alternate-top execution can consume this view independently later.

## Estimate rationale
13 points cover mounting the existing data as a tile, provenance labels and state handling.
Exclude provider DUT mapping generation and out-of-context execution costs.

## Assumptions and decisions needed
Delivered default: opt-in tile, leaving current preset composition intact. Root
initially expanded; independent local navigation; explicit load-current action.
Loaded artifacts remain browsable with recomputed current/historical labels.
Current provider contracts supply no tested-DUT association, so it is unknown.

## Delivery evidence

- Shared immutable hierarchy model, bounded/deduplicated reads, tile-local navigation
  and exact artifact/node handoff to the existing inspector are implemented.
- Normal build, full tests, lint and changed-file formatting passed. Native HTTP/PTY
  acceptance passed at `/tmp/opencode/hierarchy-tile-w1de3jp1/`.
- The [acceptance record](../../hierarchy_tile.md#verification-limits) records
  pre-existing global format failures and native lifecycle/real-provider coverage limits.

## Deferred real-example acceptance — 2026-10-25

The owner authorized closing WB-002 independently and tracking remaining hierarchy
icon acceptance here. Expanded/collapsed, leaf and childless-root markers are already
implemented with Unicode/ASCII/Off support and automated coverage.

- [ ] Supply or arrange the real FIFO example's generic Workbench hardware-driver
  integration and structured hierarchy evidence so the tile can be exercised there.
  Its current ASIC and simulation providers alone do not publish this evidence.
- [ ] Owner-review hierarchy markers, expansion/selection and top visibility with
  that evidence in Unicode, ASCII and Off modes.

The missing-driver guidance is now explicit. These follow-ups do not reopen WB-002
or the already closed WB-001. WB-007 remains delivered pending owner acceptance;
the example integration gap is not a claim that the tested tile renderer is absent.

## References
- [Implementation plan and agent work packages](../../hierarchy_tile_plan.md)
- [Hierarchy contract](../../../protocol/hierarchy.ml)
- [Existing inspector](../../../terminal/main.ml)
- [Current-generation checks](../../../terminal/state.ml)
