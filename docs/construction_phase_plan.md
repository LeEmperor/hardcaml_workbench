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

### ASIC provider handoff within Workbench P1

**Proposal after source review, 2026-10-12; not yet adopted into ASIC's own plan.**
This section records upstream deliverables needed by Workbench P1, not a second
ASIC phase-numbering scheme. Prefix existing task IDs with `ASIC` or `Workbench`.
The ASIC owner should incorporate the agreed sequence into its authoritative
architecture/phase plan before implementation. No ASIC files were changed by this
review. Source baseline: clean `hardcaml_asic` at `f6e8fd7`.

#### Existing work and dependency triage

| Foundation / track | Finding and integration consequence |
| --- | --- |
| ASIC P0–P5 / M3 | Completed project/build/bundle and execution/result foundation; reuse it |
| ASIC P6.1–P6.3, P6.4a/b | Reporting/archive policies, dispatcher, installed package and per-operation tests are recorded delivered; do not repackage or duplicate them |
| ASIC P6.5a | Source-artifact identity is still explicitly unknown in `identity.py`; finish this existing next slice for reliable generator/executor provenance |
| ASIC P6.5b/c and P6.6 | Dependency/waiver/provisioning and independent-installation gates remain; carry them toward a dependable pinned release, while observation prototypes proceed |
| ASIC P7 | Old protemu/scaf consumer migration; it is not a dependency of a new test-asic consumer or Workbench observation |
| ASIC S-series / T-series | SRAM and specific external-tool fixes remain independent unless the chosen specimen actually needs them |

Some README/status headers describe an earlier state than the detailed P6.4b
evidence. `p6-status.md` also records an old dirty HEAD, not the current clean
checkout. Reconcile those descriptions during the next ASIC planning update;
do not rerun completed packaging work based only on a stale header. Its old
handoff's mandatory scaf lookup is not applicable to the absent worktree.

#### Ordered upstream slices

1. **Run-domain contract and a narrow adapter feasibility probe.** Define build,
   run, outer operation, implementation step occurrence, attempt, result snapshot
   and artifact identities. Preserve existing `run`/`execute` semantics and final
   JSON stdout. Write two-run recorded examples with skipped/failed/interrupted
   steps and late result publication. Inspect the pinned LibreLane entry path and
   demonstrate how actual step boundaries can be observed; select a supported hook,
   structured-state observer with known limits, or bounded upstream change. Do not
   assume overriding `Flow.start_step` observes the sequential flow, which calls
   `step.start` directly. **Exit:** a tested observation seam and concrete contract
   examples without Workbench or a general orchestration rewrite.

2. **Durable catalog and outer-operation observation.** Expose explicit run-store
   listing/inspection, early run allocation with request correlation, and recorded
   updates plus a recoverable current snapshot. Instrument the existing runner and
   dispatcher once. Define writer serialization, cursor/snapshot consistency,
   partial writes, retention, stale observation and interrupted-writer behavior.
   Keep legacy records readable. **Exit:** a standalone CLI observer attaches late,
   disconnects/reconnects and inspects two runs; allocation is visible while the
   process is still running. This enables Workbench's run selector, but is not yet
   fine-grained physical progress.

3. **Actual implementation-step lifecycle.** Use the proven seam inside the
   LibreLane adapter to expose the actual step plan and started/completed/failed/
   skipped states, including repeated step identities and deferred errors. Keep
   raw logs as diagnostics. Cover the real Dockerized path and cancellation of its
   descendants; avoid inferring success from directory existence or silence.
   **Exit:** a bounded flow shows earlier steps completed while a later step is
   still executing; its status is available without Workbench.

4. **Incremental result publication and evidence preservation.** Refactor collection
   into reusable step-aware extraction plus final aggregation, keeping current
   reporter acceptance. Start with synthesis resources and one intermediate timing
   snapshot, then physical checks. Publish complete versioned snapshots before
   events reference them; retain producer provenance for cumulative/inherited
   metrics. Replace fragile fixed step-directory assumptions behind the adapter,
   not inside Workbench. Preserve snapshots, event history and referenced evidence
   through archive/restoration; decide a separate explicit policy for failed-run
   diagnostic exports. **Exit:** inspect earlier measurements during a later step,
   after a later failure, and from preserved evidence after scratch cleanup.

5. **Installed standalone acceptance and test-asic handoff.** Extend the existing
   installed-prefix tests for all public observation operations and compatible
   legacy behavior. Demonstrate cancellation, duplicate/partial updates, independent
   readers, later standalone postcheck/collect revisions and no-UI operation. Use
   one small real test-asic flow to validate internal-step/result evidence; fixtures
   cover the broader failure matrix. Finish applicable P6 identity/installation
   gates and record the exact candidate revision for deliberate adoption.
   **Exit:** a usable provider release and replay fixtures, with no Workbench
   import, source-checkout requirement or background UI service.

#### Files and tests to build on

- `lib/build.mli`, `lib/bundle.ml`: immutable intent/input identity. Export declared
  clock/constraint facts as needed rather than duplicating editable configuration
  in Workbench. Generated-clock/CTS analytics are later capability slices; the
  current clock/timing declaration API is narrower.
- `flow/hardcaml_asic_flow/cli.py`: installed operation dispatch and fixed sequence.
- `phase4.py`: allocation, atomic JSON replacement, execution, postchecks and
  collection. Existing collection uses fixed synthesis paths and final metrics;
  adapt it for step snapshots rather than create a competing report parser.
- `report.py`: operation-aware acceptance. New progress must not weaken its policy.
- `archive.py`: explicit artifact selection and integrity-preserving publication.
  Its current keep-list does not preserve every intermediate result automatically.
- `test/test_phase4.py`, `test/test_flow_cli.py`, `test/test_report.py`,
  `test/test_archive.py`: existing injected-process/fixture regression seams.
- `test/test_packaging.py`, `test/test_installed_prefix.py`: install boundary.
  The latter builds/installs with Dune and is intentionally run separately from
  `dune runtest`, not nested inside it.

#### What Workbench can do before upstream completion

| Available upstream slice | Workbench work unlocked |
| --- | --- |
| Contract examples / archived records | Feature reducers, adapter decoders, P3 headless window/tile tests |
| Catalog + outer observation | P2 catalog/cache, run selector, early run display, coarse progress |
| Internal step lifecycle | Live per-step execution tiles |
| Incremental results | Timing/PD/check tiles updating before run completion |
| Installed real-flow acceptance | P4 live integration and provider pin for release |

No ASIC work is needed for moving a tile, selecting a window's run, pinning a
reference tile or composing two typed feature views. Those remain Workbench UI
state. ASIC supports multiple independent readers of run evidence; it never stores
their window selections. The sibling test-asic owns declaration, source pins,
testbench/regression semantics and ordinary command entry points.

**Recommended immediate order:** complete the already-scoped ASIC P6.5a identity
slice, settle the run-domain examples and adapter probe, then implement catalog/
outer observation. P6.5b/c/P6.6 can progress alongside the new observation work;
do not require all ASIC roadmap items or old consumer migration before starting
Workbench's fixture-backed UI work. No EDA execution or new test pass is claimed
by this source/planning review.

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
