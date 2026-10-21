---
id: WB-069
title: Timing as a distinct stage on the stage checklist
category: evidence
feature_sets: [FS1, FS5]
status: needs-design
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 8
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [checklist, timing, signoff, stages]
depends_on: []
related: [WB-004, WB-009, WB-001, WB-006]
---

# WB-069 — Timing as a distinct stage on the stage checklist

## Request
Owner note, 2026-10-20: timing is a tile in the Overview. Perhaps timing should not
be grouped with signoff on the stage checklist. Timing should appear as a discrete
step, distinct from the checks and finalization. Requested size: **Unspecified**.

## Current baseline
The checklist uses the provider's canonical physical stages `synthesis, floorplan,
placement, cts, routing, signoff` (`backend/asic_public.ml`). Timing evidence (the
signoff timing index) is reached through the signoff stage and the Timing workspace.
Finalization is a separate lifecycle. There is no checklist row whose status means
"timing analysed" independently of signoff checks.

## Scope
- Decide what a timing row means: a provider-reported STA step, or a projection of
  existing timing evidence (index present, goal met or violated).
- Show it as its own checklist row with its own status, timestamp (WB-006) and
  Timing-workspace link, ordered after the stage that produced the analysed checkpoint.
- Keep signoff checks and finalization rows separate from it.

## Out of scope
Running STA, changing provider stage names, and diagnosing the WB-009 empty-paths report.

## Acceptance criteria
- [ ] Timing has its own row; a signoff status never implies a timing status, or the reverse.
- [ ] Missing timing evidence shows as unavailable or not requested, never as passed.
- [ ] The row's goal status comes from reported timing evidence and names its stage/corner source.
- [ ] Enter/inspect from the row opens the matching Timing view.
- [ ] Alignment (WB-001) and launch/checklist consistency checks still pass.

## Dependencies
None required. WB-004 adds preparation rows (elaboration/bundle) to the same
checklist; agree a shared row order. WB-009 may change what timing evidence is trustworthy.

## Estimate rationale
8 points, low confidence: cheap if it projects existing evidence, larger if the
provider must report a distinct timing step.

## Assumptions and decisions needed
- Projection of existing evidence (proposed first) vs a provider-reported step?
- One timing row, or one per analysed stage (post-route, signoff)?

## References
- [Checklist projection](../../../terminal/overview_tiles.ml)
- [Canonical stages](../../../backend/asic_public.ml)
- [Launch/checklist consistency](../../launch_stage_consistency.md)
