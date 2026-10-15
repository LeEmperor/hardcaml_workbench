# F06 — Hardware and stage evidence inspection

Status (2026-10-15): RTL/artifact/provenance, elaborated hierarchy and **FS0 synthesis
cell count/breakdown with evidence context delivered**. [Acceptance](../fs0_acceptance.md)
records real 673/685 counts, completed execution and `not_evaluated` acceptance.
The original synthesis-only stage summary has no timing (`[]`), not zero slack.
Later FS1 terminal-result import supplies aggregate timing with full provenance;
requirements below remain normative where not covered by the delivered slices.

**FS1/F06 synthesis inspection slice delivered:** sortable/filterable cell table,
stable row selection, count/share detail and full evidence inspection over existing
cached summaries. Normal views use concise provenance; full producer records/paths
are inspectable. Actual PTY cached-run isolation and switching tests passed; see
[controls and acceptance](../synthesis_inspection.md).

**Subsequent FS1 slices delivered:** synthesis area/lint/latch/check counters,
explicit read-only finalization-reference import, signed aggregate setup/hold,
final area/utilization, reported DRC/LVS/antenna verdicts, verified declared-clock
configuration and full evidence drilldown. Real physical completion, separate
acceptance pass/fail imports, cache reopening and active-container cancellation
are verified in [FS1 acceptance](../fs1_acceptance.md). The followup
[finalization lifecycle and artifact browser](../fs1_lifecycle_and_artifacts.md)
adds daemon-owned collection/acceptance, bounded report paging and explicit
external text opening on the terminal host. Rich paths, measured CTS,
stage-specific placement/routing/congestion and binary/graphical viewers remain open.

## Feature slices

| View | Desired evidence and interactions |
| --- | --- |
| Synthesis | Cell/gate/resource breakdown, area where supplied, inferred-latch and synthesis diagnostics, report links |
| Hierarchy | Elaborated instance tree, ports/widths, metadata, target/configuration and generating-build identity |
| Timing | Setup/hold, corners/modes, constraints, warnings, failing/near-limit paths, filtering, hierarchy/group expansion, paginated path detail |
| Placement / physical design | Die/core context, utilization, cell/macro area, provider-defined density/congestion/placement quality evidence |
| Clocks / CTS | Declared/generated clocks and relationships, constraint coverage, measured skew/insertion where supplied |
| Routing | Provider-produced routing/congestion/antenna evidence and artifacts |
| Checks / signoff / finalization | Independent check outcomes, scope, report evidence and supported finalization operation outcomes |
| Simulation / tests / regressions | [F09](simulation_and_tests.md): generic runner/attempts first, structured cases/seeds and trace artifacts later |
| General summary | Compatible execution/resource/timing/check summaries composed from shared modules |

Metric names such as “placement pressure” are examples of desired insight, not a
new Workbench-defined metric. Provider semantics and units must accompany values.

## Hierarchy preservation and extension

Retain the existing hierarchy generation/validation/navigation workflow during the
tile migration. Keep elaborated hierarchy distinct from synthesized/netlist
hierarchy. Cross-links to resources, timing or diagnostics require explicit mapping
evidence; similar instance names are not sufficient proof of correspondence.

## Interaction and evidence

- Several views may consume the same timing/resource module without re-extraction.
- Keep immediately useful counts/slacks/check summaries in F11's shared normalized
  cache. Rich cell/path detail is separately bounded and fetched on demand; fast
  run switching must not require loading every report or waveform for that run.
- Rich explorers own their local filtering, expansion and selection independently.
- Initially inspect bounded text/reports and offer explicit external viewer actions.
  Declare viewer host/location; remote paths are not automatically local files.
- Preserve original reports and producer context. Carried-forward metrics must not
  be relabeled as newly measured at the current stage.
- Overview provenance uses short, meaningful producer/stage/source labels with
  explicit detail inspection for complete structured records and absolute paths.
  Do not dump serialized JSON into normal metric rows or discard original evidence
  to shorten a label. Owner review (2026-10-15) identified the current raw producer/
  source display as a presentation followup, not an FS0 functionality blocker.
- Source jumps use file/range and source identity where supplied. Generated RTL
  locations are useful even when no reliable OCaml source mapping exists.
- F12's Overview/Timing gallery uses synthetic metrics, paths, diagnostics and source
  panes. It does not deliver provider extraction, Fmax derivation, per-case counts
  or source mapping. Rich path→inspector/source coordination uses explicit typed
  investigation selection when implemented, separate from shared run context and
  each tile's local scroll. No implicit global selected-path state across clients.

## First demo / later

First: synthesis resource evidence plus existing RTL/hierarchy/artifact access.
The generic simulation/test module has its own early slice in F09, independent of
ASIC report availability. Next: one meaningful timing/check drilldown, then placement/clock slices. Full
timing explorers and embedded graphical/editor surfaces are later increments.

Dependencies: F01 provider evidence; F02 shared modules; F05 scoped results.
