---
id: WB-069
title: Timing as a distinct stage on the stage checklist
category: evidence
feature_sets: [FS1, FS5]
status: needs-design
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 8
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [checklist, timing, signoff, stages]
depends_on: []
related: [WB-004, WB-009, WB-001, WB-006]
---

# WB-069 — Timing as a distinct stage on the stage checklist

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

## Current baseline
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
Automatically rerunning STA, creating a separately runnable/restartable Timing
checkpoint, renaming canonical execution stages, or implementing the separate Clocks
workspace. Targeted provider plumbing to expose retained STA observations is **in
scope**. A seventh true execution boundary would require a separate design decision.

## Acceptance criteria
- [ ] Overview's stage checklist tile visibly includes Timing as its own row with
  independently sourced status and duration; signoff status does not imply timing status.
- [ ] Overview's Timing tile shows the same analysis's status/duration and available
  metrics/verdicts with source context; it is not left as a generic signoff-only summary.
- [ ] Completed STA followed by failed/timed-out DRC shows Timing completed and Signoff
  failed, while retaining access to the exact completed timing evidence in both surfaces.
- [ ] Analysis completion, timing-constraint verdict and signoff acceptance remain
  separate facts; neither index presence nor successful execution alone means passed.
- [ ] Missing timing evidence shows as unavailable or not requested, never as passed.
- [ ] The row's goal status comes from reported timing evidence and names its stage/corner source.
- [ ] Enter/inspect from the checklist row or Overview Timing tile opens the matching
  Timing view without silently retargeting to another run, stage or report.
- [ ] Run selection/pins and refresh update both Overview surfaces coherently; stale
  or missing analysis evidence cannot borrow another attempt's status, duration or metrics.
- [ ] Alignment (WB-001) and launch/checklist consistency checks still pass.

## Dependencies
None required. WB-004 adds preparation rows (elaboration/bundle) to the same
checklist; agree a shared row order. WB-009 may change what timing evidence is trustworthy.

## Estimate rationale
8 points is the original low-confidence estimate. Re-estimate before implementation:
the clarified scope includes provider-supported partial STA evidence and two Overview
surfaces, not merely inserting a label into the checklist.

## Assumptions and decisions needed
- Owner-facing intent is settled: a separate Timing row in Overview's checklist and
  richer information in Overview's Timing tile are both required.
- Recommended implementation: a provider-backed **supplementary post-PNR STA
  observation**, presented as a checklist stage-like item without advertising a new
  launch endpoint or checkpoint. Do not infer completion from directory existence or
  inherited metrics alone.
- Decide whether the first delivery publishes the observation only after the enclosing
  segment ends, or reports STA completion live while later signoff work is still running.
- Start with one Timing row for post-PNR STA; additional per-stage timing analyses and
  independent stop/resume semantics require an explicit scope decision.

## References
- [Checklist projection](../../../terminal/overview_tiles.ml)
- [Canonical stages](../../../backend/asic_public.ml)
- [Launch/checklist consistency](../../launch_stage_consistency.md)
