---
id: WB-011
title: FPGA/Vivado integration
category: integrations
feature_sets: [FS4, FS1]
status: needs-design
kind: feature
priority: P3
severity: n/a
requested_size: Ticket
size: L
points: 34
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [fpga, vivado, providers]
depends_on: []
related: []
---

# WB-011 — First Vivado project provider

## Request
Original size: **Ticket**. Support FPGA projects through a Vivado project provider
that participates in Workbench's execution and evidence model.

## Current baseline
The repository has Dune, project-driver, ASIC and simulation adapter seams.
The architecture anticipates Vivado as a future provider; the current ASIC adapter
is not proof of live Vivado support. Existing supervisor/log/artifact services can
be reused without importing tool logic into terminal widgets.

## Scope
- Adopt one existing Vivado project mode and explicit tool/configuration identity.
- Discover declared targets and expose one bounded synthesis workflow.
- Capture logs, completion state, utilization and timing summaries with provenance.
- Preserve FPGA device, top, constraints and tool-version context in results.

## Out of scope
Full implementation/bitstream/programming support, every Vivado project style,
embedded vendor GUI, persistent Tcl workers and automatic tool installation.

## Acceptance criteria
1. Missing tool/configuration disables the provider with an actionable reason.
2. A selected project preview identifies device, top, constraints and executable.
3. Explicit launch runs under the existing supervisor with logs and cancellation.
4. Retained timing/utilization evidence identifies tool, run, units and inputs.
5. Fixture parsing is labeled separately from one actual supported Vivado handoff.
6. Viewing/discovering retained results does not implicitly launch synthesis.

## Dependencies
Required: delivered supervisor, provider seam and artifact/provenance model.
No additional ticket blocker; the bounded Vivado provider is included here.
Related: none; general extra ASIC report adoption is not required.

## Estimate rationale
34 points cover one project mode, synthesis lifecycle and first retained summaries.
Exclude vendor provisioning, full FPGA lifecycle and separately ticketed inspection tools.

## Assumptions and decisions needed
TBD: first Vivado version, project mode, specimen and available licensed environment.
Default: existing provider-owned project/constraints, with explicit batch synthesis.
Real tool acceptance must be identified separately from recorded-data validation.

## References
- [Provider architecture](../../hardcaml_workbench_architecture.md)
- [Existing project adapter](../../../adapters/project_driver_adapter.ml)
- [Supervisor boundary](../../../backend/execution_module.ml)
