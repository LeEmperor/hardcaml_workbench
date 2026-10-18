---
id: WB-003
title: Evidence refresh activity and current-operation status
category: evidence
feature_sets: [FS1, FS5]
status: partial
kind: enhancement
priority: P1
severity: n/a
requested_size: Ticket
size: S
points: 5
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [refresh, activity, session]
depends_on: []
related: []
---

# WB-003 — Visible evidence refresh activity

## Request
Original size: **Ticket**. Show “Updating Evidence” while evidence is being read;
a Session current-operation line may be the right compact surface.

## Current baseline
ASIC inspection already has explicit refresh, shared in-flight reads and bounded caches.
The terminal has session status, utility projections and native indicator primitives.
Existing icon/spinner delivery is a foundation; this ticket concerns semantic wiring,
not a new animation system or reopening FS1 acceptance.

## Scope
- Project active evidence reads/refreshes into a visible scoped activity state.
- Identify the operation and selected run/domain/stage where space permits.
- Retain old evidence with its honest freshness label while replacement is pending.
- Clear activity on success, error, cancellation or invalidated selection.

## Out of scope
Launching physical flows, treating repaint/polling as refresh, or adding a scheduler.
No invented percentage when the provider supplies no progress total.

## Acceptance criteria
1. A deliberately delayed explicit refresh shows activity until its terminal result.
2. A cache-only reopen does not display a fictitious provider operation.
3. Failure clears activity and preserves a useful error plus prior freshness status.
4. A late response cannot restore activity or evidence for an obsolete selection.
5. Overlapping reads are summarized without falsely reporting the session idle.

## Dependencies
Required: delivered inspection lifecycle and indicator primitives; no new blocker.
Related: none; artifact production timestamps are independent evidence semantics.

## Estimate rationale
5 points cover activity projection, compact presentation and lifecycle edge cases.
Exclude animation-library work, transport redesign and performance instrumentation.

## Assumptions and decisions needed
Default: indeterminate activity with explicit operation text and accessible static label.
TBD: Session line versus tile-local indicator, and compact wording for concurrent reads.
The indicator must distinguish evidence reading from actual producer execution.

## References
- [Inspection lifecycle](../../../backend/asic_inspection.ml)
- [Utility projections](../../../terminal/overview_tiles.ml)
- [Indicator primitives](../../../terminal/indicator.ml)
- [Inspection cache behavior](../../fs1_investigation.md)
