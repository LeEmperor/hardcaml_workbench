# Feature sets

Updated 2026-10-17. **FS numbers group product work**, F numbers identify architectural
area specs, WB numbers identify individual tickets, and M numbers order implementation/acceptance in the construction
plan. One feature can contribute slices to several sets; completing a set does not
mean every linked feature is finished. Later set scope is provisional and can be
refined when activated.

The [categorized WB catalog](features/README.md) contains the current owner intake,
one file per feature, with provisional estimates and dependency contracts. See its
[intake crosswalk](features/intake.md) and [dependency map](features/dependencies.md).
Cross-set labels are intentional: a Testing redesign can be FS2+FS5, while shared
layout persistence is FS3+FS5. These classifications do not reopen closed milestones.

## At a glance

| Set | Theme | Demonstrable outcome | Main features | Delivery mapping |
| --- | --- | --- | --- | --- |
| **FS0** | Initial functional demos | Modular shell, generic tests, linked contexts, fast synthesis/reference switching and saved reopening | F01–F05, bounded F06/F09, F10/F11, F12 seams | M0–M3; Demos A–C |
| **FS1** | ASIC evidence investigation | Useful timing/check/physical/clock drilldowns backed by actual evidence | F05/F06, F01/F02 extensions | M4 ASIC slices |
| **FS2** | Simulation helpers and test views | Structured suites/cases/seeds, regression failure investigation and trace artifacts | F09, F03/F05/F06 | M4 simulation/regression slices; later dedicated tasks |
| **FS3** | Workspace adoption and setup | Multiple monitor surfaces, comfortable presets and existing-project initialization | F04/F07/F10 | M5 host/setup slices |
| **FS4** | External clients and advanced extensions | Ches summaries/source navigation and automation; additional extensions when justified | F08 plus provider-specific additions | Future scoped phases |
| **FS5** | Appearance experiments and candidate gallery | Comparable A–E terminal variants with independent styling axes and composable chrome | F12, F03/F04 adapters, mocked F06/F08 data | V1 independent gallery track |

Sets express themes, not a compulsory serial queue: FS1 and FS2 can progress
independently once FS0 contracts exist. Some FS3 polish can happen alongside them.
M5 release/adoption checks run against whichever feature scope is being adopted;
they do not require every future set to finish.
FS5 can run alongside FS0 after common host/component seams; its number does not
place it after FS4. A complete gallery is not an FS0 exit criterion.

## FS0 — Initial functional demos (delivered with bounded followups)

**Current status:** Demos A–C delivered. The lists below describe the intended
slices, not unchecked implementation tasks. The [active plan](construction_phase_plan.md)
splits completed conditions from remaining gaps and consolidates exact candidate
paths/hashes and [acceptance](fs0_acceptance.md) / [installed-check](fs0_install_checks.md)
evidence. FS0 does not complete the full normative specs.

### FS0a: provider-independent shell

- Extract existing execution/test supervision into module contracts.
- Build Main/independent contexts, linked selectors and per-tile run references.
- Add workspace/tile host, command palette and generic test/log views.
- Exercise asynchronous shared queries, bounded fan-out and stale-response handling
  using fixtures. Keep RTL/hierarchy access available through migration.
- F11: define normalized summary identities and a bounded L1 memory cache with
  shared cold fetches. Prove unchanged resident R1→R2→R1 uses no new report queries.
- F12 minimum: semantic tokens/replaceable skin, configurable tile headers and
  mountable navigation/status tiles over one host. Keep commands usable without
  mounted chrome, use safe palette capture and test a narrow cell-grid fallback.
  Inspect/adapt Ches primitives before writing new overlay machinery. A provisional
  skin is sufficient; no final aesthetic selection or five-candidate gallery gate.

**Delivered:** daemon-routed Execution module over the existing supervisor,
project-scoped test/log tiles, palette, Main/independent contexts and shelf tile
host. Generic HTTP and installed tests pass; RTL/hierarchy and legacy captures
remain covered. D2/D3 FS0 defaults were explicitly approved. Domain delivery remains
polled; local input and deferred completion invalidate the view immediately.
Fully subscription-driven publication and high-tile-count measurements remain followups.

### FS0b: bounded ASIC synthesis integration

- Configure/pin project executable and installed provider contracts.
- Discover/select/preview/launch, consume early allocation and observe/reconnect.
- Project available synthesis resources/reports into the same module/tile model.
- Select two runs and keep one labeled reference while inspecting the other.
- F11: map provider result identities/revisions, invalidate live/later results
  correctly and measure warm switching with real summaries. Record the adapter's
  freshness strategy and distinguish lightweight validation from materialization.

**Delivered:** exact installed candidate and public interfaces verified; actual
HTTP/PTY fixtures and strictly serial real balanced/synth_delay synthesis passed,
**673/685 cells**, completion `completed`, acceptance `not_evaluated`. Early
allocation and submission-client detach are proven. Live cached real UI shows
673→685 and pinned 673 beside following 685. Timing is unsupported (`[]`).
Ordinary switching reuses summaries; explicit Refresh is needed for current
validation because the provider has no cheap revision query. Broader interactive
launch-and-view/reconnect/cancellation coverage remains a followup.

### FS0c: reusable session

- Save layouts, shared context linkage and pinned references.
- Index explicit provider result references and reopen after daemon restart.
- Restore missing references honestly; bounded caches do not become provider truth.
- F11: persist versioned normalized summaries in L2, load them after restart without
  re-materializing unchanged large reports, and expose pending/unavailable source
  validation. Exercise corruption/schema rebuild and eviction without provider edits.

**Delivered:** named workspace/context/pin/geometry state autosaves and restores;
bounded L2 summaries reopen after restart as `Cached_unverified`, preserving exact
real report identity and original observation time. Fixture report calls stay 2→2
through warm switching and restart. FS3 subsequently adds preset-preserving template
export/import/clone and selected persistent presentation preferences; shelf geometry
is not freeform placement.
Cold/L1/L2 performance/size measurements remain open.

**Exit scope:** Demos A–C in the active plan, including a real bounded synthesis path and
real PDK-free tests, with fixture-backed failure/race coverage. Generic test-history
restart persistence is not implied by provider-result reopening. Exact immutable
snapshot support is governed by D3 and must not be claimed from run pinning.
F11 is part of FS0, not deferred performance polish. Concrete memory/disk budgets
and storage location are implementation choices; predictive prefetch and elaborate
large-detail indexes can follow measured need in later feature-set slices.

## FS1 — ASIC evidence investigation

**Delivered for the adopted evidence interfaces, with explicit limits:** first F06 slice is the [cached synthesis inspector](synthesis_inspection.md):
cell table sorting/filtering, row detail and evidence drilldown. It consumes FS0
summaries without invoking tools. Subsequent [FS1 delivery](fs1_acceptance.md) adds
synthesis area/diagnostic metrics, explicit finalization import, aggregate signed
timing, physical resources, reported DRC/LVS/antenna verdicts, declared-clock
configuration and full evidence inspection. Real physical completion, separate
external acceptance pass/fail import and owned-container cancellation are exercised.
Workbench-owned collect/accept lifecycle, cancellation/reconnect and bounded text
report/artifact viewing with explicit terminal-host export are also delivered;
see [lifecycle evidence](fs1_lifecycle_and_artifacts.md). The final
[investigation slice](fs1_investigation.md) delivers retained setup/hold paths,
corner/group/producer/stage navigation, measured clock latency/skew and supplied
relationships, stage-specific placement/routing/congestion tables, and byte-exact
external GDS handoff verified by headless KLayout loading. Provider-owned parsing,
bounded L1/L2 indexes and on-demand detail preserve original measurement context.

This completes the useful FS1 investigation/operation scope against this adopted
provider, not every future F06 capability. Missing generated-clock/source-mapping
evidence remains unavailable rather than inferred; embedded graphical editors,
spatial heatmaps, arbitrary-tool adoption and exhaustive lifecycle-race coverage
remain later extensions. No new physical execution or signoff verdict was produced
by the final read-only inspection acceptance.

The owner subsequently confirmed that Escape responsiveness works well in the
manual timing-inspection workflow. There are no remaining FS1 feature blockers
for this adoption. [Inspector presentation polish](backlog/README.md#inspector-usability-polish)
and additional lifecycle/performance coverage can proceed alongside later sets;
they do not turn FS1 into an open-ended implementation gate for FS2.

Timing summaries/path detail, checks, clocks and physical/resource slices with
original evidence and context. Full physical operation/cancellation acceptance
belongs here. Adopt fields actually provided; put missing extraction semantics in
the provider rather than reverse-engineering tool reports in tiles. Detailed paths,
intermediate snapshots and fine-grained progress may depend on further ASIC work.

## FS2 — Simulation helpers and test views

Status: **milestone closed — structured project-scoped simulation delivered and
accepted**, 2026-10-16; see
[controls and acceptance](fs2_acceptance.md) and the
[versioned provider/RPC contract](fs2_simulation_contract.md). Structured suites,
cases, seeds/parameters, live progress/outcomes, targeted reruns, durable history,
failure reports and byte-exact trace export are implemented over the existing
supervisor. Actual Cyclesim, native HTTP and terminal PTY acceptance passed.
The owner confirmed the basic demo works and authorized closure. Manual acceptance
is scoped to that workflow; broader checks retain their automated evidence.

**Subsequent extension delivered, 2026-10-17:** actual FIFO project adoption and a
test catalog (WB-034/WB-032), plus the implemented cooperative Testing investigation
(WB-063; owner visual review pending). See [current controls/evidence](testing_workspace.md).
This reuses simulation v1 and preserves the independent counter acceptance fixture.

**Native-provider extension accepted, 2026-10-19:** WB-066 delivers a separately
packaged OCaml protocol-helper library and project-owned `test_provider.exe`
adapters for real FIFO and counter examples. Tests remain independent executables;
FS2v1 is unchanged. Automated checks and owner workflow acceptance are complete.
[Implementation and evidence](native_provider_plan.md).

Extend FS0's generic test runner with project-declared suites, cases, seeds,
structured progress/outcomes, targeted reruns and failure/trace artifacts. Rich
adapters can proceed without ASIC for Cyclesim or ordinary RTL tests. Gate-level
association depends on real build/output provenance. Embedded waveform exploration
is a separately activated extension, not an automatic FS2 prerequisite.

FS0 supplies execution/host contracts; completed FS1 supplies artifact patterns and
optional ASIC evidence. FS2 owns simulation semantics and supplies configuration/view
identifiers for later FS3 setup/templates. No unfinished FS1 or FS3 gate remains.
Gate-level adapters, exact archived-build replay and ASIC acceptance contribution
remain explicit later integrations, not claims of this project-scoped delivery.
They and adoption/performance improvements are tracked in
[named followups](backlog/fs2_followups.md), not as blockers to the closed milestone.

## FS3 — Workspace adoption and project setup

**First adoption slice delivered:** existing-project initializer using the current
manifest, portable CLI workspace templates (export/import/clone and starters), and
persistent local presentation choices. The 2026-10-17 integration preserves preset
identity in templates, initializes defaults atomically, restores sparse preferences
without poll replay, and supports successful driverless manifest reload. See
[guide and verification](fs3_adoption.md).
Multi-monitor acceptance and configuration-location migration remain later work.

Multiple attached windows, shared/independent contexts across them, preset/layout
comfort, responsiveness and existing-project initialization. Full project creation
is a later F07 slice after configuration/templates are proven. Saved single-window
layouts already belong to FS0; FS3 expands their use rather than delaying them.
Adopt reviewed F12 appearance/layout presets here as available, preserving the
separation of functional workspace definitions, geometry and styling choices.

## FS4 — External clients and extensions

Start with a Ches summary subscription or source-open action over public contracts,
then automation/MCP when needed. Embedded editing, graph/layout views and new tool
providers require their own concrete acceptance scope. Mixed-tool flow validation
remains provider-owned. This set is a grouping of future work, not a commitment to
ship every extension together.

## FS5 — Appearance experiments and candidate gallery

Status: **first appearance slice delivered**. All five thin skins, independent
color/off-ASCII-Unicode/density controls and synthetic frame captures are available
in the real host. See [preset guide/evidence](appearance_presets.md). Rich Timing
fixtures, reusable tab groups, source/help overlay showcases and owner default review
remain; this is not completion of every gallery requirement below.

Implement F12's theme/components/layout boundaries over the same host contracts;
use injected synthetic Overview and Timing fixtures to compare A Instrument,
B Structured, C Minimal, D Studio and E Structured Studio. Keep every candidate,
independent vivid/selective/restrained color, optional width-safe icons and compact/
comfortable density. D-style tabs can appear in any candidate. Navigation/status/
legend chrome is mountable; headers are configurable, including headerless widgets.

V1 in the construction plan owns the gallery tasks/evidence. Use actual Bonsai Term
cell grids at wide and laptop/tmux-like sizes, mock source panes honestly and inspect
Ches float reuse before overlay showcases. No provider, full multi-client system,
embedded editor or web renderer is needed for the gallery. Default selection waits
for owner review of rendered variants; extra polish need not block functional demos.

Source priority and implementation corrections are recorded in [design/README](design/README.md).

## Tracking rules

- Use “working on FS0 / M2 / F10” for set, phase and feature respectively.
- The [feature inventory](feature_list.md) remains the full scope/status index.
- The [construction plan](construction_phase_plan.md) owns checkboxes and evidence.
- The [decision log](decisions.md) owns accepted policy and unresolved questions.
- Do not create competing implementation checklists in each set description.

## Proposed ticket reading routes

These are thematic entry points, not new mandatory milestone checklists. The
catalog tables contain all tickets and cross-set tags; the links below identify
coherent slices to discuss together.

| Set | Candidate slices and explicit boundaries |
| --- | --- |
| FS0 shared foundation | [WB-004](features/project/WB-004-build-bundle-status.md) build/bundle state; [WB-005](features/infrastructure/WB-005-process-monitor.md) owned processes; [WB-010](features/project/WB-010-progressive-adoption.md) progressive adoption; [WB-027](features/infrastructure/WB-027-performance-measurement.md) measurement; [WB-041](features/infrastructure/WB-041-durable-logs.md)/[042](features/infrastructure/WB-042-resource-budgets.md)/[043](features/infrastructure/WB-043-slow-storage.md) storage; [WB-064](features/infrastructure/WB-064-generic-job-detail.md) generic detail |
| FS1 evidence | [WB-003](features/evidence/WB-003-evidence-refresh-activity.md)/[006](features/evidence/WB-006-evidence-timestamps.md)/[009](features/evidence/WB-009-timing-coherency.md) visibility/coherency; [WB-007](features/project/WB-007-hierarchy-tile.md)/[008](features/project/WB-008-leaf-out-of-context.md) hierarchy/IP scope; [WB-012](features/evidence/WB-012-run-comparison.md) comparison; [WB-020](features/evidence/WB-020-graphical-physical-inspection.md)/[021](features/evidence/WB-021-source-navigation.md)/[022](features/evidence/WB-022-signal-name-annotations.md)/[023](features/evidence/WB-023-provider-evidence.md)/[026](features/evidence/WB-026-power-analysis.md) new evidence/inspection; [WB-065](features/infrastructure/WB-065-asic-lifecycle-coverage.md) coverage |
| FS2 verification | [WB-032](features/verification/WB-032-test-catalog.md)/[034](features/verification/WB-034-fifo-adapter.md)/[063](features/presentation/WB-063-testing-workspace.md) real adoption/investigation; [WB-028](features/verification/WB-028-waveform-viewer.md)/[030](features/verification/WB-030-seed-parameter-sweeps.md) waveform/sweeps; [WB-035](features/verification/WB-035-generated-rtl-simulation.md)/[036](features/verification/WB-036-gate-level-simulation.md)/[037](features/verification/WB-037-archived-replay.md)/[038](features/verification/WB-038-acceptance-bridge.md) adapters/replay/bridge; [WB-039](features/project/WB-039-simulation-setup.md)/[040](features/infrastructure/WB-040-trace-streaming.md)/[044](features/infrastructure/WB-044-load-acceptance.md)/[062](features/verification/WB-062-submission-recovery.md) adoption/robustness. Formal WB-025 is a new proof domain, not a missing original FS2 gate. |
| FS3 adoption | [Workspace/input category](features/README.md#workspaces-input-and-configuration), [WB-048](features/presentation/WB-048-presentation-persistence.md) remaining override persistence and [WB-049](features/project/WB-049-config-migration.md)/[050](features/project/WB-050-upward-discovery.md)/[051](features/project/WB-051-new-project-creation.md)/[052](features/project/WB-052-adoption-polish.md) setup. Templates/window config are distinct from live surface attachment. |
| FS4 extensions | [WB-011](features/integrations/WB-011-vivado.md) Vivado; [WB-018](features/integrations/WB-018-ches-tiles.md) Ches; [WB-029](features/integrations/WB-029-version-control.md) VCS; [WB-017](features/project/WB-017-project-files.md) files; [WB-025](features/verification/WB-025-formal-verification.md), [WB-031](features/exploration/WB-031-design-space-sweeper.md), [WB-033](features/exploration/WB-033-quick-harn-playground.md) proof/design exploration. Each needs its own bounded activation. |
| FS5 presentation | [Presentation category](features/README.md#presentation-and-interaction): small alignment/wording/control work through tabs, peeks, floats and a richer gallery. Native spinners, existing schemes and persisted global appearance are already delivered. |

The newer WB-009 report requires exact-run triage; earlier adopted-evidence FS1
acceptance remains recorded and must not be used to dismiss or pre-diagnose it.
