---
id: WB-063
title: Testing-workspace investigation redesign
category: presentation
feature_sets: [FS2, FS5]
status: delivered
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: L
points: 21
confidence: medium
estimate_scope: incremental
origin: existing-backlog
tags: [testing, investigation, usability]
depends_on: []
related: [WB-028, WB-032, WB-041, WB-054, WB-062, WB-064]
---

# WB-063 — Testing-workspace investigation redesign

## Implementation delivery — 2026-10-17

Code and automated acceptance are complete; the owner visual/workflow review was
accepted after the reconnect and Attempts-pane follow-ups. Catalog, Attempts, Cases, Detail,
Artifacts and Logs share client/workspace-local investigation, with independent
tile scroll/focus and one polling stream. Generic process tests and legacy
standalone simulation remain distinct. See [controls and evidence](../../testing_workspace.md).

Actual FIFO proof: `/tmp/opencode/fifo-testing-wx4xhzjp/`; synthetic/cooperative
proof: `/tmp/opencode/testing-workspace-w56bs6_c/verified.json`. Actual painted
120x40/180x55 geometry, case-selection stability, exact artifact bytes, rerun lineage,
independent workspaces and preserved saved extras/pins were verified. Original
points record the implementation estimate; this is not another 21 points of
unfinished implementation. Owner acceptance is recorded separately below.

## Owner acceptance — 2026-10-21

The owner confirmed Testing behavior and subsequently approved the final Attempts-pane
tab-switch correction. WB-063 is now **delivered and closed/accepted**, including
retained-catalog reuse, initial attempt/artifact selection, persisted investigation
navigation and stable rows during background refresh. The earlier explicit manual
workflow gate is satisfied by this approval, not inferred from automated tests.

Follow-up implementation and evidence:
[client reconnect/hydration](../../client_reconnect_hydration_plan.md). A two-client
PTY acceptance verified exact selection restoration without second-client input or
additional provider jobs; held-response tests cover the row-shift/busy/paging races.
This closure does not cover unrelated large-regression load tests, durable logging,
the dedicated Clocks workspace or signoff-dependent report inspection.

## Request
Carry forward Testing-workspace usability work as a coherent investigation surface
for cases, attempts, results, logs and artifacts. Requested size: **Unspecified**.
This is existing backlog, not another owner-intake item or a reopened FS2 gate.

## Current baseline
The accepted FS2 milestone is closed: structured simulation, attempts/cases, results,
reruns, retained artifacts and viewer handoff already exist. Testing includes a
simulation panel plus separate project-test, execution and log panels; this request
goes beyond the existing simulation panel to coordinate case/attempt investigation.

## Scope
- Compose a coordinated case/attempt navigator, result detail and log/artifact views.
- Preserve exact attempt/case/input provenance and intentional investigation selection.
- Improve failure navigation, scrolling, empty states and explicit close/reopen behavior.

## Out of scope
All FS2 backend/viewer extensions, embedded waveforms, new adapters or durable logs.
The workspace must work with currently available data and honest missing states.

## Acceptance criteria
- [x] Native input follows a failed case through result, log and artifact.
- [x] Attempt/case/request/lifetime fences prevent stale detail or artifact retargeting.
- [x] Workspace navigation, polling and local reconnect model preserve coherent state;
  native historical reopen remains tool-free with explicit unavailable logs.
- [x] Existing pending/cancelled/missing/truncated/unavailable states remain explicit.
- [x] Keyboard navigation and bounded narrow/normal layouts have automated coverage.
- [x] Owner reviews the actual composition/workflow; further visual preferences are
  followup refinements rather than assumed acceptance.

## Dependencies
Required: none; FS2 data/actions, workspace composition and registry are delivered.
Related: [WB-028](../verification/WB-028-waveform-viewer.md) adds optional embedded waves;
[WB-032](../verification/WB-032-test-catalog.md) enriches discovery;
[WB-041](../infrastructure/WB-041-durable-logs.md) extends retention;
[WB-054](WB-054-contextual-controls.md) improves controls;
[WB-062](../verification/WB-062-submission-recovery.md) improves uncertain submissions;
[WB-064](../infrastructure/WB-064-generic-job-detail.md) shares generic log patterns.

## Estimate rationale
Twenty-one incremental points cover one coherent multi-view Testing investigation
delivery and workflow acceptance, excluding the separately ticketed capabilities.

## Assumptions and decisions needed
Choose the first case/attempt workflow and layout with the owner before redesign.
Preserve FS2 milestone closure; no requirement to finish every simulation followup.

## References
- [Existing usability backlog](../../backlog/fs2_followups.md#fs2-f06--multi-clientload-acceptance-and-usability)
- [Closed FS2 acceptance](../../fs2_acceptance.md)
- [Testing template baseline](../../fs3_adoption.md#workspace-templates)
