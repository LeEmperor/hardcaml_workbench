# Hardcaml Workbench — Construction Plan

Plan reset and consolidated 2026-10-12. The [architecture](hardcaml_workbench_architecture.md)
defines ownership and contracts; [rendering](rendering.md) defines presentation.
This is the only active phase plan. P0–P7 below replace all archived 1A–4D, D1–D4,
W0–W6 and prettification phases. Deferred work lives in [backlog](backlog/README.md).

**Current status: planning only; every phase below is not started.** Existing
daemon/client, Dune jobs, RTL/artifacts and hierarchy remain delivered foundations.
Their earlier validation is preserved in [archive](archive/README.md); it is not
evidence that the newly planned features exist.

## P0 — Establish the sibling test ASIC and evidence fixtures

**Goal:** a stable development specimen independent of the production ASIC.

- [ ] Use the owner's dedicated sibling test-asic repository. Choose a small
  understandable design and record its source revision, pinned `hardcaml_asic`,
  tool/PDK versions, constraints and ordinary build/test/flow commands. Its root is
  configured, not a mandatory hardcoded sibling path in the installed application.
- [ ] Obtain one real physical run and archive original records/reports with
  provenance. Record which Magic/KLayout operations the chosen flow supports.
- [ ] Keep small deterministic report/event fixtures in Workbench, including
  pending, failure, missing/unconstrained timing, partial results, disconnects and
  two distinguishable runs. Synthetic evidence is explicitly labeled.
- [ ] Specify operation and evidence examples jointly with the ASIC provider:
  build/unit test, bounded regression, generation, physical run, collect/inspect.
  Preserve the existing counter fixture for generic Dune/RTL/hierarchy tests.

**Exit:** standalone CLI reproduction and one real archived result; fast tests
need no PDK/vendor tools. Exact specimen/technology and usable provider revision
remain to be selected. Contract prototyping can proceed while live setup is pending.

## P1 — Define and supply the ASIC provider boundary

**Depends on:** P0 examples; distinguish provider work from Workbench adaptation.

- [ ] Specify a versioned public contract for capability/operation discovery, run
  listing/lookup, early run allocation, request correlation, stage/substep updates,
  result revisions and artifact lookup. Decide event or bounded status transport,
  update atomicity and reconnect behavior with concrete examples.
- [ ] Implement missing flow-side capabilities in `hardcaml_asic` through its own
  development process and pin the resulting revision in test-asic. The APIs must
  work without Workbench and not import Workbench UI/application libraries.
- [ ] Define supported stage continuation/retry semantics and cancellation
  ownership. Preserve separate attempts and earlier evidence. Do not promise a
  generic resume facility the provider does not implement.
- [ ] Implement the Workbench ASIC adapter to consume these contracts and reuse
  its supervisor. Keep project Dune/tests/regressions on their own declared paths
  where appropriate; associate them with runs only when meaningful.
- [ ] Adapt existing execution state into a feature contract and implement timing
  import/projection from provider data. Setup/hold, corners, units, constraints,
  stage and original reports remain attached to observations.

**Exit:** a plain client can launch/observe a bounded operation and inspect one
archived run; the provider exposes the same data without Workbench. Two timing
consumers share data without repeating parsing/extraction. Early run identity is
observable before the physical process finishes, not only in its final stdout.

## P2 — Persistent run catalog and bounded summary cache

**Depends on:** P1 identities/revisions; archived fixtures allow early work.

- [ ] Index configured provider run stores, including CLI-created runs, using
  explicit identities. List queued submissions separately until a provider run is
  allocated; correlate it without substituting a Workbench ID.
- [ ] Define persistent index/config storage and schema compatibility. Canonical
  run records/reports remain provider-owned; Workbench data is a rebuildable index
  plus saved UI configuration. Test missing/moved stores and schema failures.
- [ ] Cache normalized summaries keyed by project/provider, run, record revision
  or digest and adapter version. Invalidate when later postchecks/collection change
  evidence; bound retention and paginate catalogs/logs/report detail.
- [ ] Extend artifact access to registered provider-backed evidence with explicit
  missing/cached states. Do not copy an entire physical output tree to view a summary.
- [ ] Reopen named results after daemon restart without flow execution. Saved IDs
  that no longer resolve remain unavailable instead of selecting another run.

**Exit:** alternate between two stored runs without launching tools or reparsing
unchanged large reports; new observations invalidate the right cache entries.
Rebuild the index from canonical records and demonstrate cache eviction does not
delete provider evidence. Document measured switch behavior before setting a budget.

## P3 — Window context, tiles and headless interaction

**Depends on:** P1 feature contracts; P2 supplies live catalog/storage. Host and
selection tests can start against deterministic data before those are complete.

- [ ] Separate terminal startup/transport, server-derived data, window UI state and
  rendering. Preserve production event reduction and stale-response checks.
- [ ] Implement workspace, window and tile-instance identities. A workspace
  associates with one project/catalog; each window has an independent selected
  run. Establish an API/configuration seam for multiple window attachments.
- [ ] Implement the run-selector tile, default follow-window bindings and explicit
  pinned-reference bindings. Run changes invalidate old queries as one context
  transition; late responses never populate another run's tiles.
- [ ] Add shared tile shell/geometry/focus, keyboard move/reorder, resize,
  hide/restore and zoom. Start with jobs/logs/timing tiles and a useful preset.
  Input routing and command definitions drive both dispatch and help.
- [ ] Test through the actual Bonsai frontend using injected transport, controlled
  time/dimensions and supported events. Verify commands submit once, arrival does
  not steal focus, switching replaces ordinary data, and pinned views stay pinned.
- [ ] Apply semantic theme roles, cell-aware measurement and explicit log follow
  state as tiles migrate. A few frame tests cover compact/wide geometry and focus.

**Exit:** select run A/B in one window, see all follow-window tiles change, and
retain A's timing as a labeled reference inside B. Moving/hiding a tile has no
backend side effect. Routine interaction acceptance requires no manual clicking.

## P4 — Live flow, regressions, checks and artifact inspection

**Depends on:** P0 real environment, P1 adapter, P2/P3 catalog and UI.

- [ ] Launch front-end builds/tests, a bounded long-running regression and a full
  physical flow through the specimen's declared commands. Preserve standalone CLI.
- [ ] Show early run allocation, requested extent, real stage/substep/tool progress,
  logs, elapsed time and observation freshness. Unknown substeps stay unknown.
- [ ] Populate timing/check/artifact tiles for that run. Expected future values are
  pending; unsupported, not requested, failed and not produced are distinct.
  Verify supported Magic/KLayout evidence against their actual reports.
- [ ] Add bounded text/report readers and an explicit external viewer action with
  host location, file-transfer requirements and unavailable-display behavior defined.
- [ ] Verify cancellation of the actual runner/tool descendants, including
  containers if used. Client detach and run-selection changes do not affect work.
- [ ] Confirm late postchecks/results update the same identified run with new
  revisions. Explicit new implementation attempts receive new provider run IDs.

**Exit:** one real physical run and bounded failure/cancellation cases are observed
end to end; replay and live acceptance are recorded separately. Run B's selected
tiles never contain unlabeled measurements from A while B is pending.

## P5 — Clock and physical-design slices

**Depends on:** P4 evidence. Keep these narrow enough to deliver useful views.

- [ ] Expose declared/generated clocks, periods, relationships and constraint
  coverage; add CTS observations where the provider produces them. Reuse timing
  references; a clock list does not imply CDC verification.
- [ ] Expose core/die context, cell/macro area and utilization plus known
  placement/routing/CTS/congestion evidence. Physical design is the meaning of PD;
  power-domain intent is a deferred separate feature.
- [ ] Add concise metric/check explanations and report drilldowns, including the
  producing stage/corner and declared goal. Provider policy owns verdicts.
- [ ] Compose an overview from multiple compatible feature contracts and a second
  view of one module without duplicating provider work.

**Exit:** the user can identify a concrete clock/physical issue and open its
supporting evidence rather than only see an unexplained number or status color.

## P6 — Multi-window monitor workspace and release acceptance

**Depends on:** P3 window foundation, P4/P5 usable views.

- [ ] Persist named workspace/window layouts, selected-run preferences and pinned
  references with explicit versions. Missing runs are visible after restoration.
- [ ] Attach two terminal surfaces to distinct windows of one workspace. Select A
  in one and B in the other; share backend observations without synchronizing their
  selections, focus or scroll. Move/restore tiles with documented binding semantics.
- [ ] Exercise wide dedicated-monitor layouts and compact/tiny recovery. Bound
  high-volume progress/log work and measure responsiveness during regression.
- [ ] Prove FPGA-only and ASIC-with-FPGA-emulation capability composition using
  fixtures. Do not claim live Vivado support from recorded data.
- [ ] Run format/lint/unit/build, affected installed/fixture and PTY checks. Keep a
  focused human review of appearance/comfort. Record results here with evidence
  paths, rather than creating another general development log.

**Release exit:** the sibling test ASIC is operated and inspected from independent
monitor windows with movable tiles, selectable durable runs, a pinned comparison
reference, traceable evidence and reliable detach/reconnect/restart reopening.

## P7 — Production adoption

**After the first release.** Integrate the current production ASIC project through
the proven provider contracts. Record gaps in their owning repository and extend
only for concrete workflows. Revisit [backlog](backlog/README.md) deliberately;
phase completion does not automatically activate deferred features.

## Tracking and immediate next step

| Phase | Status | Evidence |
| --- | --- | --- |
| P0 | Not started | Owner selected a sibling repository; specimen/pins pending |
| P1 | Not started | Existing ASIC dispatcher/records inspected; new contract pending |
| P2 | Not started | Storage ownership agreed; index/cache not implemented |
| P3 | Not started | Window/run semantics agreed; tile workspace not implemented |
| P4 | Not started | Live integration pending |
| P5 | Not started | Clock/PD slices pending |
| P6 | Not started | Multi-window implementation and acceptance pending |
| P7 | Deferred until release | Production adoption follows specimen validation |

Next: select the P0 design/provider revision and write P1's early-run/catalog/
observation examples. Implement missing provider features in `hardcaml_asic`
without requiring Workbench. P3's pure window-selection/headless seam can be
prototyped against the two-run fixture while that work proceeds.
