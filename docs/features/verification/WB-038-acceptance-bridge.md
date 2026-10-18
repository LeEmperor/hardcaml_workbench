---
id: WB-038
title: Simulation-to-ASIC acceptance evidence bridge
category: verification
feature_sets: [FS2, FS1]
status: needs-design
kind: feature
priority: P3
severity: n/a
requested_size: Unspecified
size: L
points: 21
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [acceptance, evidence, policy]
depends_on: []
related: [WB-036, WB-025]
---

# WB-038 — Simulation-to-ASIC acceptance evidence bridge

## Request
Allow an explicitly defined ASIC acceptance policy to consume exact structured
simulation evidence while preserving separate execution and acceptance verdicts.

## Current baseline
FS2 simulation results and FS1 acceptance operations exist independently.
FS2-F11 defers their policy bridge; case success does not automatically mean signoff.

## Scope
- Define policy-owned required evidence, completeness and freshness rules.
- Import verified exact attempt/case/input identities into an explicit acceptance operation.
- Record the policy version and consumed evidence identities with its verdict.
- Explain missing, stale, incompatible or insufficient evidence in investigation views.
- Reuse the existing ASIC acceptance boundary rather than building another flow engine.

## Out of scope
- Automatically approving ASIC runs when any simulation passes.
- Defining universal signoff policy or implementing new simulation/formal backends.

## Acceptance criteria
- An explicit operation consumes verified simulation evidence under a named policy.
- Passing, failing, missing and stale required cases produce policy-correct outcomes.
- Unrelated run/input evidence cannot satisfy a requirement merely through UI selection.
- Original process completion, simulation outcome and ASIC acceptance remain distinct.
- Repeated inspection does not launch acceptance or mutate the consumed evidence.
- Unsupported policy/evidence combinations are explicit and never reported as accepted.

## Dependencies
No additional prerequisite tickets; use existing structured evidence for a first bridge.
[WB-036](WB-036-gate-level-simulation.md) may provide a policy-specific evidence source;
[WB-025](WB-025-formal-verification.md) is a possible later proof source, not a required
dependency or an assertion that formal evidence is already accepted by this policy.

## Estimate rationale
21 points, L, low confidence: policy ownership, exact linkage and completeness rules
are unresolved integration work. Incremental estimate excludes producer adapters and
formal verification; it covers one declared policy bridge, not universal signoff.

## Assumptions and decisions needed
Activate when the adopted ASIC policy actually requires FS2 evidence. Confirm who owns
the policy and which inputs/results satisfy it before choosing acceptance semantics.

## References
- [FS2-F11 acceptance bridge](../../backlog/fs2_followups.md#fs2-f11--asic-acceptance-evidence-bridge).
- [FS1 acceptance lifecycle](../../fs1_lifecycle_and_artifacts.md).
- [Explicit input associations](../../../protocol/simulation.ml).
