---
id: WB-069
title: Timing as a distinct stage on the stage checklist
category: evidence
feature_sets: [FS1, FS5]
status: closed
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: L
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [checklist, timing, signoff, stages]
depends_on: []
related: [WB-004, WB-009, WB-001, WB-006, WB-071, WB-073, WB-048]
---

# WB-069 — Timing as a distinct stage on the stage checklist

**Owner verification/closure:** the owner explicitly confirmed “consider 069 closed
and verified” after reviewing the executable Timing and usability/preloading
changes. WB-069 is closed. Separate remaining WB-009/WB-073 scope is not included
in that acceptance.

## Request
**Owner clarification: both surfaces are required in the Overview workspace.**

1. The **stage checklist tile** must show **Timing as its own stage-like row**, with
   its own execution/analysis status and duration, rather than hiding it inside Signoff.
2. The existing **Timing summary tile in Overview** must show the additional timing
   information for that same analysis: its status/duration, available timing metrics
   and verdicts, and the evidence source. It must remain useful when STA completed
   but later signoff checks failed.

This is not only a change to the separate Timing investigation workspace. That
workspace remains the drilldown destination; the requested at-a-glance information
belongs in **Overview itself**. Requested size: **Unspecified**.

Example intended checklist presentation (illustrative values):

```text
Routing        completed        42s
Timing         completed         1s
Signoff        failed       10m 07s
```

Here `completed` means the timing analysis ran and produced its output. It does not
automatically mean timing constraints passed or signoff was accepted.

## Baseline before implementation
The checklist uses the provider's canonical physical stages `synthesis, floorplan,
placement, cts, routing, signoff` (`backend/asic_public.ml`). Timing evidence (the
signoff timing index) is reached through the signoff stage and the Timing workspace.
Finalization is a separate lifecycle. There is no checklist row whose status means
"timing analysed" independently of signoff checks.

The observed failing runs completed post-PNR STA before timing out later in Magic
DRC. Their raw STA reports and runtime survive, but the current public inspection
path requires a published signoff checkpoint. Therefore this is not solely a
checklist-renderer change: trustworthy partial analysis evidence must also be exposed
by the provider if the enclosing signoff segment fails.

## Scope
- Expose an authoritative post-PNR STA analysis observation with its own completion
  status, measured execution duration and exact attempt/producer/source identity.
- Show **Timing** as its own row in the **Overview stage checklist tile**, after
  Routing and before the remaining Signoff outcome. Keep status and duration columns
  aligned with the surrounding rows. Evidence timestamps (WB-006) remain distinct
  from how long the analysis took.
- Populate the **Overview Timing tile** from the same exact analysis: status,
  duration, available setup/hold slack and violation/goal information, with explicit
  stage/corner provenance and honest unknown/unavailable fields. Respect its compact
  layout; expose full context through details rather than clipping away status/time.
- Preserve and expose completed timing evidence when later DRC/signoff work fails;
  keep it clearly attributed as analysis from a failed enclosing attempt.
- Link the checklist row and Timing tile to the matching Timing investigation view.
- Keep signoff checks and finalization rows separate from it.

## Out of scope
Automatic reruns, implicit restart of a selected historical execution, or the
separate Clocks workspace. The original supplementary increment excluded a runnable
Timing boundary; the owner subsequently authorized that boundary and it is now
implemented by the [executable Timing follow-on](../../executable_timing_stage.md).

## Acceptance criteria
- [x] Overview's stage checklist tile visibly includes Timing as its own row with
  independently sourced status and duration; signoff status does not imply timing status.
- [x] Overview's Timing tile shows the same analysis's status/duration and available
  metrics/verdicts with source context; it is not left as a generic signoff-only summary.
- [x] Completed STA followed by failed/timed-out DRC shows Timing completed and Signoff
  failed, while retaining access to the exact completed timing evidence in both surfaces.
- [x] Analysis completion, timing-constraint verdict and signoff acceptance remain
  separate facts; neither index presence nor successful execution alone means passed.
- [x] Missing timing evidence shows as unavailable or not requested, never as passed.
- [x] The row's goal status comes from reported timing evidence and names its stage/corner source.
- [x] Enter/inspect from the checklist row or Overview Timing tile opens the matching
  Timing view without silently retargeting to another run, stage or report.
- [x] Run selection/pins and refresh update both Overview surfaces coherently; stale
  or missing analysis evidence cannot borrow another attempt's status, duration or metrics.
- [x] Alignment (WB-001) and launch/checklist consistency checks still pass.

## Delivery — 2026-10-21

**Follow-on delivered:** Timing is now a real seventh provider stage/checkpoint,
ending at `OpenROAD.STAPostPNR`, with Signoff continuing immediately afterward.
`r` prepares a new Timing run through the current catalog and requires explicit
Launch, including when historical six-stage evidence is selected. Historical
execution facts remain unchanged; incompatible old checkpoints fail continuation
explicitly. The Overview tile distinguishes stage duration from native STA runtime.

[Executable Timing controls and acceptance](../../executable_timing_stage.md) record
provider recipe-4/analysis-2 compatibility, full build/lint/tests, continuation and
11-check native HTTP/PTY evidence. The configured real-example provider/project and
retained Workbench binaries were refreshed without starting a physical flow or
restarting live user processes.

### Subsequent Timing usability and preloading delivery

The owner-authorized [usability/preload increment](../../timing_workspace_usability.md)
is implemented and automatically verified:

- [x] Three-decimal truncation by default, configurable per tile from 0–9; raw sort,
  comparison and constraint values retain full precision.
- [x] Persistent default-on compact identifiers/source paths with full-string toggle,
  semantic Session/provenance colors and a wider paths column.
- [x] Ordinary inspection uses built-in Timing; separate investigations are explicit
  and have a discoverable guarded close command. WB-071 records ordering/membership.
- [x] Default background index loading for completed selected/followed analyses,
  including hidden Timing; persistent explicit-only mode and initial CLI override.
- [x] One speculative request at a time, exact-source/selection fences, interactive
  coalescing, finite failure attempts and no hidden detail fan-out or off-screen drawing.
- [x] Actual a023 retained data: 1,021 index rows, one provider index read, zero hidden
  detail reads, unchanged focus/pins and no further read on switching to Timing.

Full build/lint/tests passed serially at `-j 1` after crash recovery. Native warm-up
acceptance passed 20 assertions; changed-file formatting passed. The saved built-in
order and retained daemon/client/exporter were updated; receipts and remaining
verification limitations are in the delivery guide. The owner subsequently verified
and closed WB-069. Broader WB-071/WB-073 scope is not implied.

### Original supplementary increment

Implemented and automatically verified across `hardcaml_asic` and Workbench. The
provider publishes an immutable supplementary observation after the enclosing segment
ends, including failure/timeout/cancellation. Both Overview surfaces consume the same
typed observation and retain exact-source inspection, pins and restart fencing.
Timing `r` in the checklist cannot prepare a run; the six physical stages are unchanged.

[Controls and acceptance evidence](../../timing_checklist_overview.md) record the full
build/lint/tests, provider failure fixtures and final 20-check native HTTP/PTY result.
No new physical flow was run. Live STA updates, historical backfill, installation
refresh and owner visual acceptance are not claimed by these automated checks.

## Dependencies
None required. WB-004 adds preparation rows (elaboration/bundle) to the same
checklist; agree a shared row order. WB-009 may change what timing evidence is trustworthy.

## Estimate rationale
Re-estimated from 8 low-confidence points to 13 medium-confidence points before
implementation: the clarified scope includes provider-supported partial STA evidence,
wire/cache compatibility, exact-source navigation and two Overview surfaces.

## Decisions
- Owner-facing intent is settled: a separate Timing row in Overview's checklist and
  richer information in Overview's Timing tile are both required.
- Retain a provider-backed **post-PNR STA observation**, separate from physical
  segment completion. Do not infer it from directory existence or inherited metrics.
- The executable follow-on publishes immutable timing evidence at Timing completion,
  before Signoff begins. Historical supplementary analyses keep their original
  signoff attribution; the earlier end-of-Signoff limitation is superseded for new runs.
- Start with one Timing row for post-PNR STA; additional per-stage timing analyses and
  independent stop/resume semantics require an explicit scope decision.

## References
- [Current Timing controls, close command, preloading and acceptance](../../timing_workspace_usability.md)
- [Usability/preload agent plan](../../timing_usability_preload_plan.md)
- [Executable Timing stage and refreshed deployment](../../executable_timing_stage.md)
- [Executable-stage implementation plan](../../executable_timing_stage_plan.md)
- [Implementation plan](../../timing_checklist_overview_plan.md)
- [Checklist projection](../../../terminal/overview_tiles.ml)
- [Canonical stages](../../../backend/asic_public.ml)
- [Launch/checklist consistency](../../launch_stage_consistency.md)
