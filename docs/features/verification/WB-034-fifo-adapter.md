---
id: WB-034
title: Real FIFO structured-test adapter
category: verification
feature_sets: [FS2]
status: delivered
kind: feature
priority: P1
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [fifo, cyclesim, adoption]
depends_on: []
related: [WB-032, WB-039]
---

# WB-034 — Real FIFO structured-test adapter

## Delivery — 2026-10-17

Implemented and automatically verified; [controls/evidence](../../testing_workspace.md).
The real example has a standalone `controlled-fifo` provider with directed/seeded
cases, canonical uint64 inputs, native VCD/reports and an explicit checker-only
mismatch mode. The persistent generation and root companion configuration are
installed. Ordinary project CLI/Dune tests retain their prior behavior.

Final proof: `/tmp/opencode/fifo-testing-wx4xhzjp/` (standalone, actual public HTTP,
new catalog/cooperative PTY, exact artifact export, targeted rerun and legacy view).
No physical flow or synthetic FIFO evidence was used. Original points record the
implementation estimate, not remaining work.

## Request
Expose real directed and seeded FIFO tests from hardcaml_asic_example through
the structured simulation contract, with meaningful failures and traces.

## Current baseline
The accepted FS2 real counter provider demonstrates the independent contract.
FS2-F01 recommends FIFO adoption; the counter demonstration is not FIFO coverage.

## Scope
- Add a small project-owned adapter for actual FIFO Cyclesim tests.
- Declare suites/cases, seeds and parameters through existing discovery.
- Emit project-owned failure reports and inspectable traces.
- Preserve ordinary project CLI/Dune use and targeted rerun parent identity.

## Out of scope
- Replacing the independent counter contract fixture or changing FIFO design semantics.
- Physical ASIC flows, signoff claims or generalized regression sweeps.

## Acceptance criteria
- Actual FIFO directed and seeded tests succeed through the structured path.
- A deterministic FIFO failure has an inspectable case report and trace.
- Targeted rerun preserves exact seed, parameters and parent attempt identity.
- Native HTTP and actual terminal input exercise discovery, launch and investigation.
- Ordinary CLI/Dune operation still works without Workbench-specific invocation.
- Evidence distinguishes real FIFO coverage from fixture and generic command success.

## Dependencies
No additional prerequisite tickets; use the delivered FS2 provider contract.
[WB-032](WB-032-test-catalog.md) improves browsing, while
[WB-039](../project/WB-039-simulation-setup.md) can simplify configuration.
Neither is necessary to demonstrate the adapter through current controls.

## Estimate rationale
13 points, M, medium confidence: the adapter seam exists, but real project failure
and trace integration require adoption work. Estimate is incremental and excludes
unrelated FIFO implementation changes or setup/catalog enhancements.

## Assumptions and decisions needed
Confirm the first directed/seeded cases and deterministic fault mechanism with the
project owner. Preserve failure evidence without introducing a permanent design defect.

## References
- [FS2-F01 FIFO adoption](../../backlog/fs2_followups.md#fs2-f01--fifo-project-adoption).
- [Provider contract](../../fs2_simulation_contract.md).
- [F09 accepted foundation](../simulation_and_tests.md).
