---
id: WB-028
title: Embedded waveform viewer
category: verification
feature_sets: [FS2, FS5]
status: partial
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
related: [WB-025, WB-040, WB-067, WB-068]
---

# WB-028 — Embedded waveform viewer

## Bounded embedded delivery — 2026-10-18

Implemented and automatically verified in the `sim-artifacts` checkout. Select a
VCD in Testing's Artifacts pane and press **w**, or use **Simulation: Open embedded
waveform …**. A full-area Hardcaml Waveterm view opens with exact retained identity;
Esc/q returns to the unchanged Testing context. No external viewer is required.
See [controls and evidence](../../testing_workspace.md#embedded-waveform-viewer).

Follow-up implemented: **W** opens/reuses a dedicated Waveforms workspace with
independent Session, Signals, Waves, VCD picker and matching-attempt Logs tiles. Disabled
signal names remain visible; Enter toggles while Space c c opens the global palette.
Pinned identity survives workspace/client restoration with reverified data and honest
missing/log-unavailable states. Inline/stacked values, quiet hints and filter word
deletion are implemented. Compact Session-over-Signals layout and content-sized
value columns are verified. Both viewing surfaces now show a glyph-preserving cursor
column and adaptive absolute-time ruler with exact compressed/expanded mapping and
off-screen indicators. 1,773 acceptance checks passed; see
[workspace controls](../../testing_workspace.md#dedicated-waveforms-workspace).

The first slice verifies and parses a complete VCD of at most 8 MiB, with bounded
sparse conversion/rendering windows. Lazy file indexing remains outstanding, so the
ticket is partial against its original broader scope. X/Z/uninitialized values are
preserved and inspectable as text; graphical windows containing them report an
explicit limitation of the installed two-state renderer. Surver remains proposed.

## Request
View and investigate waveforms inside Workbench, beyond exporting a trace or
launching an external viewer.

## Current baseline
FS2 exports byte-exact trace artifacts and supports external handoff. The bounded
embedded slice above now implements navigation beyond that original baseline.

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

## Design discussion — 2026-10-18

Historical proposal, preceding the bounded embedded delivery above. The owner
prefers exploring native Surfer remote viewing alongside Hardcaml terminal waveform
embedding. The existing 34-point estimate covers the embedded slice, not the new
remote-session work described here; split/estimate that work before implementation.

### Two complementary viewing paths

1. **Open with Surfer on the workstation.** Run Surver beside the retained waveform
   on the server; connect a native workstation Surfer through an SSH tunnel. Surfer's
   documented remote mode transfers requested waveform information rather than
   requiring a complete file download. This is the preferred remote GUI experiment.
2. **Open in Workbench.** Evaluate `hardcaml_waveterm` for an SSH-friendly terminal
   investigation surface. This is useful without a desktop viewer or tunnel setup.
   VCD import, rendering integration and resource behavior still need a spike.

Keep verified file export and GTKWave handoff as useful fallback actions. GTKWave
over X11 requires GTKWave on the server and forwards display traffic; Surfer remote
mode renders on the workstation and requests waveform data from the server. Neither
remote mode nor embedded rendering implies live simulation streaming: start with
closed, retained artifacts from completed cases.

### Placement: open from Testing into a dedicated waveform view

The Testing workspace is the entry point: select attempt, case and VCD, then choose
the viewing action. Avoid adding a permanent waveform tile to its already crowded
default layout. Proposed initial embedded surface is a full-area investigation view
with an explicit return action that restores the Testing pane focus and selections.
It can evolve into a dedicated Waveforms workspace if multiple traces need persistent
investigation; a small optional preview is a later layout choice.

Suggested layout:

```text
Waveform · case / artifact                  Back to Testing | Open with Surfer
Attempt / seed / time units / availability
+-----------------------+---------------------------------------------------+
| Signal tree + filter  | Time ruler / cursor / selected signal values      |
|                       | Waveform lanes                                    |
|                       |                                                   |
+-----------------------+---------------------------------------------------+
Load status / time range / navigation help
```

Opening captures project, attempt, optional case, artifact ID and digest. The view
stays pinned to that artifact when Testing selection changes; opening another trace
is explicit. Preserve signal selection, radix, cursor and zoom by artifact identity.
Closing or hiding a viewer must not rerun or cancel a simulation.

### Remote-session consequences

- **Different host roles:** daemon host owns retained artifacts; terminal-client
  host owns the TUI; workstation owns the native GUI. These may be three machines.
  An executable path passed to the TUI cannot launch an application on a different
  workstation. Name the destination in actions and status messages.
- **New session lifecycle:** propose a daemon-managed Surver session referencing one
  verified retained artifact, with start/status/stop operations and bounded idle
  expiry. Keep the artifact available while served, with an explicit lease/storage
  budget. Handle artifact eviction, server failure and daemon restart visibly.
- **Connectivity:** bind Surver to loopback and provide SSH tunnel/connection
  instructions, following upstream's recommended transport. First delivery can show
  a copyable connection command; automatic workstation launch needs an additional
  workstation-side integration and is not supplied by the existing viewer flag.
- **Identity:** serve an immutable verified snapshot of the selected artifact, not
  an arbitrary producer path. The Workbench session records its digest and ownership;
  do not assume Surfer's remote protocol itself supplies Workbench's hash guarantees.
- **Cost:** selective transfer avoids mandatory whole-file download, but does not
  establish bounded server parsing/indexing memory or instant startup. Measure server
  CPU/memory, initial readiness, transferred bytes and interactive latency separately.
- **Disconnect:** losing the GUI/tunnel should leave the simulation result intact.
  Reconnection should target the same session/artifact or report expiry explicitly.
- **UI feedback:** viewer actions need concise pending/ready/error status scoped to
  the artifact/session. Avoid repeating long action IDs and notices across Attempts
  and Artifacts headings, as observed with the current missing-viewer message.

Surver remote access is distinct from WB-040's verified raw-byte export streaming.
It does not automatically lift Workbench's current 64 MiB artifact retention limit.
Revisit storage limits separately when larger retained traces are required.

### Hardcaml embedding spike

Use an actual retained FIFO VCD, including a failed case, and determine:

- Whether `hardcaml_waveterm` can import that VCD or needs an adapter from parsed
  events; whether an additional producer-native artifact would be needed instead.
- Preservation of hierarchy, bus widths, timestamps/time units and X/Z values;
  expose unsupported semantics rather than silently converting them.
- Whether rendering and key handling can be hosted within Workbench without a
  competing terminal event loop; include resize and return-to-Testing behavior.
- Whether signal/time selection can avoid loading the entire trace, and what explicit
  limits are necessary if the library requires full materialization.
- Responsiveness and peak memory for representative traces and terminal dimensions.

The spike should end with a working vertical demonstration or a concrete integration
gap, not a commitment based only on the library rendering waveforms in isolation.

### Proposed sequence and acceptance

1. Demonstrate workstation Surfer reading a real retained FIFO VCD through Surver
   and SSH; record versions, connection steps and measured resource/latency results.
2. Demonstrate the same artifact in a full-area Hardcaml-based Workbench prototype.
3. Review both experiences, then ticket the remote-session integration separately
   and finalize WB-028's initial embedded scope and layout.

For the remote slice, verify exact artifact selection, reconnect/expiry, concurrent
sessions, cleanup and retention leases. For the embedded slice, verify meaningful
signal/time navigation, resize, restoration of Testing context and pinned identity.
Missing dependencies or unsupported formats should leave export available and give
an actionable message. Decide later whether cursor/signal synchronization with
Surfer is worth adding; its Waveform Control Protocol is separate from remote data
access and is not required for the first handoff.

### Upstream references checked

- [Surfer documentation](https://docs.surfer-project.org/book/): native viewer and
  standalone `surver` installation.
- [Remote file access](https://docs.surfer-project.org/book/print.html#remote-file-access):
  selective information transfer, `surver <FILENAME>`, connection URL and SSH tunnel.
- [Waveform Control Protocol](https://docs.surfer-project.org/book/print.html#waveform-control-protocol-wcp):
  separate viewer-control interface, for possible later integration.
