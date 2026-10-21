---
id: WB-068
title: Waveform cursor repeat lag and step units
category: verification
feature_sets: [FS2, FS5]
status: needs-triage
kind: defect
priority: P2
severity: S3
requested_size: Unspecified
size: M
points: 8
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [waveforms, cursor, latency, zoom]
depends_on: []
related: [WB-028, WB-067, WB-027]
---

# WB-068 — Waveform cursor repeat lag and step units

## Request
Owner notes, 2026-10-20: repeated h and l in the waveform should just work, rather
than lagging on repeated presses as they do now. This relates to the cursor's tick
scaling: perhaps step by one character column versus one actual timestep should be
distinguished. Reported S3 usability defect; unconfirmed until reproduced.

## Current baseline
`waveform_view.ml` moves the cursor by exactly **one VCD tick** per h/l press
(`t.cursor - 1L` / `Int64.succ t.cursor`), whatever the zoom. When one screen column
covers many ticks (the ruler's compressed mapping), several presses can leave the
cursor in the same column, so it looks stuck or laggy. Each keypress also rebuilds
the view; per-key render cost has not been measured. `:` jumps to an absolute tick.

## Scope
- Reproduce and measure: per-key latency under held-key repeat at representative
  zooms and trace sizes, separating render cost from "no visible movement".
- Two explicit step units: **column** (move to the next/previous screen column's
  tick) and **tick** (one raw timestep). Pick the default and a key for the other.
- Optional: jump to the focused signal's next/previous value change.
- Keep keypresses from queueing up behind slow renders, e.g. by coalescing repeats.

## Out of scope
Count prefixes (`20 l`), which are WB-067. Lazy trace loading and four-state
graphics remain WB-028.

## Acceptance criteria
- [ ] Recorded before/after latency for held h/l on a bounded fixture.
- [ ] In column mode, every press moves the cursor at least one visible column.
- [ ] Tick mode moves exactly one timestep and shows that unit in the ruler or help.
- [ ] Holding h/l for 2 s stops within one frame of release, with no queued backlog.
- [ ] Cursor never leaves trace bounds; off-screen indicators stay correct.

## Dependencies
None required. WB-067's counts multiply whichever step unit this ticket defines.
WB-027 measurement tooling can be reused for the latency record.

## Estimate rationale
8 points, medium confidence: the step-unit change is narrow. Render coalescing may
need deeper view changes if profiling shows it is the main cost.

## Assumptions and decisions needed
- Default unit: column (proposed), with tick on a modifier or alternate key (e.g. H/L)?
- Should value-change jumps be in this ticket or deferred?

## References
- [Cursor handling](../../../terminal/waveform_view.ml)
- [Time mapping](../../../terminal/waveform_time.ml)
- [WB-028 embedded viewer](WB-028-waveform-viewer.md)
