---
id: WB-032
title: Project test catalog and discovery UI
category: verification
feature_sets: [FS2]
status: delivered
kind: feature
priority: P1
severity: n/a
requested_size: Feature
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [catalog, discovery, tests]
depends_on: []
related: [WB-030, WB-034, WB-063]
---

# WB-032 — Project test catalog and discovery UI

## Delivery — 2026-10-17

Implemented and automatically verified; [controls/evidence](../../testing_workspace.md).
The new catalog pane exposes declared suites/cases/defaults, filtering, explicit
subsets and discovery/launch reasons. Palette and keyboard actions capture the
exact suite/subset/digest and reject changed choices before opening a form.
Failed/stale discovery retains browsing but does not enable a launch.

Native cooperative proof: `/tmp/opencode/testing-workspace-w56bs6_c/verified.json`;
genuine FIFO subset/form proof: `/tmp/opencode/fifo-testing-wx4xhzjp/`.
Original points record the implementation estimate, not remaining work.

## Request
Discover and show the project's available tests so users can understand and select
what to run without reconstructing a catalog from logs.

## Current baseline
FS2 already has versioned suite/case discovery and declared parameter/default-seed
metadata. This ticket improves catalog presentation and navigation, not initial discovery.

## Scope
- Present provider-declared suites/cases with stable IDs, labels and parameters.
- Show provider availability, discovery errors and bounded refresh state.
- Select a declared subset and preview exact submission inputs.
- Distinguish a generic project test command from a structured test catalog.
- Preserve a useful no-provider and empty-catalog experience.

## Out of scope
- Inferring case counts or passes from generic Dune success or arbitrary text logs.
- Seed-matrix orchestration, implementing project tests or redesigning all Testing tiles.

## Acceptance criteria
- A real structured provider's declared catalog is discoverable in the native UI.
- Suite/case selection submits exactly the declared IDs and captured parameters.
- Refresh handles changed/removed cases without silently retargeting selection.
- Empty, unavailable, incompatible and discovery-failed states are distinct.
- A generic successful Dune job shows command success and unavailable case detail;
  it does not manufacture passed-case counts or prove that cached tests reran.
- Catalog browsing launches no tests and does not alter investigation selection.

## Dependencies
No additional prerequisite tickets: FS2 discovery is delivered.
[WB-030](WB-030-seed-parameter-sweeps.md) can use the catalog for matrix setup;
[WB-034](WB-034-fifo-adapter.md) adds another real provider and
[WB-063](../presentation/WB-063-testing-workspace.md) improves broader investigation UX.

## Estimate rationale
13 points, M, medium confidence: known typed discovery needs a clear catalog surface,
selection rules and refresh integration. Incremental estimate excludes new test adapters.

## Assumptions and decisions needed
Confirm search/filter and default selection behavior. Keep provider-declared catalogs
authoritative; generic commands need an explicit unavailable-details presentation.

## References
- [F09 generic versus structured tests](../simulation_and_tests.md).
- [Suite/case discovery types](../../../protocol/simulation.ml).
- [FS2 acceptance](../../fs2_acceptance.md).
