---
id: WB-018
title: Ches-hosted Workbench tile projections
category: integrations
feature_sets: [FS4]
status: needs-design
kind: feature
priority: P3
severity: n/a
requested_size: Medium Feature
size: L
points: 21
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [ches, companion, daemon]
depends_on: []
related: []
---

# WB-018 — Mirror Workbench status in Ches

## Request
Original size: **Medium Feature**. Mirror a stage-checklist-like Workbench tile in
Ches, attached to the existing daemon rather than creating a second execution engine.

## Current baseline
Workbench already owns semantic execution/ASIC services and reusable utility projections.
The external-client spec requests a Ches companion with explicit context binding.
Its ches-mini gallery surface is a labeled placeholder, not an integrated editor host.
Ches host/focus/geometry APIs still need inspection before choosing an embedding seam.

## Scope
- Inspect and select one supported Ches companion-tile mount boundary.
- Attach to an explicitly chosen existing daemon/project and expose connection state.
- Display a compact checklist/status projection with Main or named-run binding.
- Keep tile focus/scroll local and detach without affecting daemon work.

## Out of scope
A second scheduler, automatic daemon launch, full renderer extraction, embedded editing,
source mapping and lifecycle ownership transferred to Ches.

## Acceptance criteria
1. The companion visibly identifies daemon/project and its run-context binding.
2. Stage status preserves explicit observations, including unknown/not-requested states.
3. Workbench and Ches can view the same run without sharing local scroll/focus.
4. Disconnect/reconnect shows stale/unavailable state and fences obsolete responses.
5. Closing Ches or removing the tile neither cancels jobs nor starts another engine.

## Dependencies
Required: delivered daemon query contracts and a selected Ches host boundary.
No additional ticket prerequisite; bounded host-adapter investigation is included here.
Related: none; source navigation can be adopted separately after its mapping contract.

## Estimate rationale
21 points cover one companion projection, host adapter, binding and connection lifecycle.
Exclude editor embedding, universal shared widgets and other external-client programs.

## Assumptions and decisions needed
Default: read-only status/checklist first, attached to an existing daemon endpoint.
TBD: Ches extension API, refresh/subscription mechanism and authentication/endpoint reuse.
Sharing semantic data is required; sharing rendering packages is optional.

## References
- [External-client requirements and placeholder limits](../external_clients.md)
- [Current semantic projections](../../../terminal/overview_tiles.ml)
- [Execution module](../../../backend/execution_module.ml)
