---
id: WB-012
title: Provenance-aware run comparison
category: evidence
feature_sets: [FS1, FS2]
status: partial
kind: enhancement
priority: P2
severity: n/a
requested_size: Ticket
size: L
points: 21
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [comparison, runs, provenance]
depends_on: []
related: [WB-031, WB-033]
---

# WB-012 — Compare retained runs

## Request
Original size: **Ticket**. Compare runs and make meaningful differences in results
visible without losing measurement context.

## Current baseline
Run contexts support following Main, independent selection and pinned references.
FS1 already demonstrates switching retained runs and pinned/following views.
Typed inspection rows preserve stage, producer, corner and unit evidence.
Those foundations do not yet define a general paired-delta comparison contract.

## Scope
- Select baseline/candidate explicitly and retain both exact identities.
- Compare one agreed summary set: synthesis resources and compatible timing quantities.
- Show configuration/source differences and comparable, incompatible or missing values.
- Link each side to original evidence and preserve direction of numeric deltas.
- Expose reusable paired identity, quantity-compatibility and missing-result rules;
  the initial UI still covers the bounded synthesis/timing summaries above.

## Out of scope
Launching experiments, archived-build replay, automatic timing-path equivalence,
normalizing unrelated tools/corners into misleading numeric differences, and
suite/case/seed-aligned simulation regression comparison. Consumer-specific scratch
variant, compile/test and non-summary adapters are not included in this ticket.

## Acceptance criteria
1. Baseline/candidate remain explicit when Main changes or either side is pinned.
2. Deltas require compatible units, stage, corner and measurement semantics.
3. Missing/incompatible evidence shows reasons rather than zero or an invented delta.
4. Both sides expose exact source provenance and cache-verification state.
5. Swapping sides reverses compatible deltas and retains evidence identities.

## Dependencies
Required: delivered run contexts, retained summaries and inspection evidence.
No additional ticket blocker.
Related: [WB-031](../exploration/WB-031-design-space-sweeper.md) and
[WB-033](../exploration/WB-033-quick-harn-playground.md) reuse pairing/compatibility
rules, but own mapping their variant/results into that model within their estimates.

## Estimate rationale
21 points cover pair selection, compatibility rules, summary deltas and investigation UI.
Exclude experiment execution, arbitrary report matching and source replay infrastructure.

## Assumptions and decisions needed
Default: one comparison view over already registered runs, no automatic best-run verdict.
TBD: first metric list and rules for configuration changes that should warn versus
prevent comparison; incompatible quantities remain inspectable side by side.

## References
- [Run-context requirements](../run_contexts.md)
- [Retained runs](../runs_and_evidence.md)
- [Typed inspection rows](../../../protocol/asic_inspection.ml)
- [Existing evidence behavior](../../fs1_investigation.md)
