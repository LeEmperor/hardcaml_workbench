---
id: WB-009
title: Timing workspace availability/coherency investigation
category: evidence
feature_sets: [FS1]
status: needs-triage
kind: defect
priority: P1
severity: S2
requested_size: Ticket
size: M
points: 8
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [timing, unconfirmed, triage]
depends_on: []
related: []
---

# WB-009 — Reported missing timing paths

## Request
Original size: **Ticket**. The owner reports no timing paths after a run reached
signoff, while signoff was not performed. Investigate that exact observation.
Severity **S2 is provisional**: the report is unconfirmed and unreproduced here.

## Current baseline
FS1 delivered retained timing inspection with explicit run/stage selection and
missing-evidence diagnostics. Its accepted specimen contains real signoff paths.
The investigation record also documents a prior provider-selection correction;
that history does not establish the cause of this owner's current report.

## Scope
- Capture the exact run/execution, provider configuration/capability, requested and
  observed stages, selected inspection stage, filters and cache state.
- Inspect retained artifacts/import registration with read-only queries.
- Separate stage reached, stage completed, report produced, report available/imported
  and inspection-stage selected; repair a reproduced coherency/message defect only.

## Out of scope
Automatic EDA, performing signoff to manufacture missing evidence, or assuming a root
cause from the report. Existing FS1 delivery and milestones remain closed.

## Acceptance criteria
1. Triage records exact identities and reproduction steps, or explicitly remains unconfirmed.
2. Completed stages and available/imported timing reports are reported as separate facts.
3. Missing report, failed import, wrong stage and zero filtered rows are distinguishable.
4. A reproduced defect receives a targeted fix and regression against retained/fixture data.
5. Diagnosis does not launch a physical flow or promote “reached signoff” to completion.

## Dependencies
Required: existing retained evidence, configuration and inspection APIs; no new blocker.
Related: none; refresh activity and timestamps may aid diagnosis but are not prerequisites.

## Estimate rationale
8 points cover bounded reproduction, evidence tracing and one localized correction.
Exclude new report providers, EDA reruns and speculative architectural replacement.

## Assumptions and decisions needed
Default: read-only triage first; no present conclusion about cause or correctness.
TBD: owner's exact execution reference, screenshot/state, provider generation and
whether any timing-producing stage actually completed for that run.

## References
- [Accepted timing behavior and deployment history](../../fs1_investigation.md)
- [Inspection service](../../../backend/asic_inspection.ml)
- [Stage/selection presentation](../../../terminal/inspection_view.ml)
