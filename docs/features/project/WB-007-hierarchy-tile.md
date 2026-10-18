---
id: WB-007
title: Hierarchy tile and selected top visibility
category: project
feature_sets: [FS1, FS2]
status: partial
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
related: []
---

# WB-007 — Visible hierarchy and top

## Request
Original size: **Ticket**. Make the hardware hierarchy and selected/tested top
visible in a tile. The owner is unsure whether Overview is its best home.

## Current baseline
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
Related: none; alternate-top execution can consume this view independently later.

## Estimate rationale
13 points cover mounting the existing data as a tile, provenance labels and state handling.
Exclude provider DUT mapping generation and out-of-context execution costs.

## Assumptions and decisions needed
Default: opt-in tile, leaving current preset composition intact initially.
TBD: Overview placement and compact depth; confirm the meaning of “tested top”
for each provider rather than treating an instance tree as test evidence.

## References
- [Hierarchy contract](../../../protocol/hierarchy.ml)
- [Existing inspector](../../../terminal/main.ml)
- [Current-generation checks](../../../terminal/state.ml)
