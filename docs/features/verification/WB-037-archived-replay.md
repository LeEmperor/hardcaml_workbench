---
id: WB-037
title: Archived source/build/tool replay
category: verification
feature_sets: [FS2, FS1]
status: needs-design
kind: feature
priority: P3
severity: n/a
requested_size: Unspecified
size: L
points: 34
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [replay, archives, provenance]
depends_on: []
related: [WB-035, WB-036, WB-042]
---

# WB-037 — Archived source/build/tool replay

## Request
Replay a historical attempt using retained original source, build, tool and
environment inputs instead of implicitly using today's working project.

## Current baseline
FS2 targeted reruns preserve seed/parameters and parent identity. That is not an
archived-build replay guarantee; FS2-F08 explicitly preserves this additional scope.

## Scope
- Define an archive manifest for required source/build/tool/environment identities.
- Capture or reference retained immutable inputs under an explicit retention policy.
- Offer replay as a distinct operation with visible archive availability.
- Reuse project recipes and supervised execution to consume retained inputs.
- State remaining external dependencies and reproducibility limitations honestly.

## Out of scope
- Promising bitwise determinism for arbitrary tools or preserving every host forever.
- Falling back silently to current inputs when an archive component is missing.

## Acceptance criteria
- After the working project changes, replay consumes the retained original identities.
- Evidence distinguishes current-project rerun from archived replay and links parents.
- Missing, corrupt or evicted inputs cause explicit unavailability/failure.
- Tool/environment identity and consumed archive digests are inspectable.
- Retention and cleanup preserve referenced records or report their eviction honestly.
- Replay does not overwrite the current working project or original attempt artifacts.

## Dependencies
No additional prerequisite tickets: begin with one existing structured project recipe.
[WB-035](WB-035-generated-rtl-simulation.md) and [WB-036](WB-036-gate-level-simulation.md)
are additional adapter consumers. [WB-042](../infrastructure/WB-042-resource-budgets.md)
can extend shared storage policy; the first archive slice must still declare local bounds.

## Estimate rationale
34 points, L, low confidence: archive completeness, tool availability and lifecycle
policy need design. Incremental scope covers one declared replay recipe, excluding
separate simulator adapters and broad environment-distribution infrastructure.

## Assumptions and decisions needed
Choose the first replayable recipe and retention/copy strategy. Decide what can be
captured versus externally pinned and expose any resulting reproducibility limits.

## References
- [FS2-F08 archived replay](../../backlog/fs2_followups.md#fs2-f08--archived-build-replay).
- [F09 rerun foundations](../simulation_and_tests.md).
- [FS2 provider contract](../../fs2_simulation_contract.md).
