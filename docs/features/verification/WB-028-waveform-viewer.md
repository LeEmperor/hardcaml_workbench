---
id: WB-028
title: Embedded waveform viewer
category: verification
feature_sets: [FS2, FS5]
status: needs-design
kind: feature
priority: P2
severity: n/a
requested_size: Feature
size: L
points: 34
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [waveforms, investigation, viewer]
depends_on: []
related: [WB-025, WB-040]
---

# WB-028 — Embedded waveform viewer

## Request
View and investigate waveforms inside Workbench, beyond exporting a trace or
launching an external viewer.

## Current baseline
FS2 already exports byte-exact trace artifacts and supports external handoff.
Embedded navigation remains deferred under FS2-F09, not delivered by registration.

## Scope
- Choose one initial trace format and an embedded terminal-compatible viewing surface.
- Provide signal selection, time navigation, zoom and value inspection.
- Load bounded portions lazily and retain exact attempt/case/artifact provenance.
- Keep explicit external handoff available when a format cannot be embedded.

## Out of scope
- Universal waveform formats, circuit-graph editing and simulator implementation.
- Counting a rendered waveform as test acceptance or hardware signoff.

## Acceptance criteria
- Navigate a real declared-format waveform and inspect values at selected times.
- Signal and time controls remain usable at supported terminal sizes.
- Large/unsupported traces produce explicit limits or unsupported messages.
- Switching attempts cannot display an old trace beneath a new identity.
- Opening, hiding and reopening the view does not launch or cancel simulations.
- Record interaction latency and peak loading memory for a bounded fixture.

## Dependencies
No additional prerequisite tickets. [WB-040](../infrastructure/WB-040-trace-streaming.md)
is related transport work for larger artifacts; bounded viewing can start with current
limits. [WB-025](WB-025-formal-verification.md) may later supply counterexamples.

## Estimate rationale
34 points, L, low confidence: trace indexing, bounded loading and interactive rendering
need format/surface decisions. Estimate is incremental beyond delivered export/handoff.
It covers one coherent viewer slice, excluding separately ticketed streaming work.

## Assumptions and decisions needed
Confirm format, signal-count/time-range limits and whether an existing rendering library
fits the native host. Library availability is not assumed to establish integration.

## References
- [FS2-F09 embedded waveforms](../../backlog/fs2_followups.md#fs2-f09--embedded-waveforms).
- [F09 trace and viewer distinction](../simulation_and_tests.md).
- [Artifact and paging limits](../../../protocol/simulation.ml).
