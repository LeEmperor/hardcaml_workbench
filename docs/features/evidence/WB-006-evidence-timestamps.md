---
id: WB-006
title: Stage/report timestamps and age
category: evidence
feature_sets: [FS1]
status: partial
kind: enhancement
priority: P2
severity: n/a
requested_size: Ticket
size: M
points: 8
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [timestamps, provenance, freshness]
depends_on: []
related: []
---

# WB-006 — Trustworthy evidence age

## Request
Original size: **Ticket**. Show when stages/reports were produced and how old they
are, without confusing production with Workbench refresh time.

## Current baseline
Inspection indexes retain run/stage, source digests, producer and cache freshness.
Jobs have lifecycle timing, but job timing is not automatically report production time.
FS1 preserves carried-forward and supplementary evidence attribution.
Refreshing old bytes cannot make them newly produced evidence.

## Scope
- Define typed timestamp meanings and provenance for stage/report presentation.
- Show producer-supplied production time when available, alongside separately labeled
  observed/imported/refreshed time where actually recorded.
- Render absolute time and useful age without implying an unsupported precision.
- Preserve unknown timestamps and clock-skew diagnostics.

## Out of scope
Rewriting provider timestamps, using mtime as authoritative production time,
or declaring stale evidence invalid solely because of its age.

## Acceptance criteria
1. Refreshing unchanged old evidence changes only the labeled observation/refresh time.
2. Missing production time stays unknown rather than borrowing a job completion time.
3. Carried-forward evidence retains its original producer/stage attribution and age.
4. Absolute timestamps identify timezone; future/skewed values do not show negative age.
5. Cached-unverified status remains visible independently of the displayed timestamp.

## Dependencies
Required: delivered evidence provenance and cache states; no additional ticket blocker.
Related: none; activity indication can ship independently of timestamp semantics.

## Estimate rationale
8 points cover a bounded timestamp contract extension and report/stage presentation.
Exclude universal historical reconstruction and changes to every provider's report format.

## Assumptions and decisions needed
Default: unknown production time is acceptable and explicit.
TBD: first authoritative producer fields and whether filesystem mtime is useful only
as a clearly labeled observation; it must never masquerade as production evidence.

## References
- [Inspection index](../../../protocol/asic_inspection.ml)
- [Existing evidence service](../../../backend/asic_inspection.ml)
- [Attribution/freshness contract](../../fs1_investigation.md)
