# Workbench documentation

Workbench is a project control and inspection application: operate independent
Hardcaml projects, observe execution, and inspect identified hardware evidence.
Project/provider commands remain useful without the application.

## Start here

| Document | What it answers |
| --- | --- |
| [Feature list](feature_list.md) | What users want to do, what exists, and what comes first |
| [Feature sets](feature_sets.md) | FS0 initial demos and later themed groups of work |
| [Demo construction plan](construction_phase_plan.md) | What to implement next and how to demonstrate it |
| [Decision log](decisions.md) | Accepted D1/D2/D3 FS0 defaults and later command/snapshot policy |
| [FS0 acceptance](fs0_acceptance.md) | Actual HTTP/PTY fixtures, real 673/685 synthesis and live cached UI reopening |
| [Installed checks](fs0_install_checks.md) | Passed native installed workflow, external fixture and legacy captures |
| [Provider integration](fs0_provider_integration.md) | Implemented public API, configuration, cache and supervision limits |
| [Terminal host](fs0_terminal.md) / [Execution module](fs0_execution_module.md) | Current UI controls and daemon-routed generic execution boundary |
| [Architecture](hardcaml_workbench_architecture.md) | Runtime, ownership, data and integration boundaries |
| [Rendering](rendering.md) | Presentation, input, layout and headless interaction requirements |
| [Appearance handoffs](design/README.md) | Imported older design doc, newer gallery and implementation qualifications |
| [Appearance presets](appearance_presets.md) | Try the implemented A–E skins and independent presentation controls |
| [Synthesis inspection](synthesis_inspection.md) | FS1/F06 cell table, filter/sort, row detail and evidence controls |
| [FS1 acceptance](fs1_acceptance.md) | Aggregate timing/resources/checks, declared-clock context, finalization import, real physical/acceptance/cancellation evidence and remaining scope |
| [Finalization and artifacts](fs1_lifecycle_and_artifacts.md) | Workbench-owned collect/accept, live phases, cancel/reconnect, bounded report paging and explicit external text export |
| [Formatting](formatting_guide.md) | Source conventions |
| [Backlog](backlog/README.md) | Deferred work and reactivation triggers |
| [Archive](archive/README.md) | Superseded plans and historical acceptance evidence |

The feature list is the concise product inventory; feature sets group delivery
themes (FS0 delivered; bounded FS1 and FS5 slices underway). Focused feature documents record
behavior and boundaries; the construction plan alone owns implementation order and
completion checklist. Focused acceptance records linked there own exact runtime
evidence. A feature request or a provider capability is not proof
of an implemented Workbench feature.

## Current orientation — 2026-10-15

- **FS0 Demos A–C delivered with bounded limitations:** typed execution boundary,
  tile host/palette, project-scoped tests/logs, named workspaces, linked/independent
  contexts, run pins, public ASIC synthesis and autosaved-session/L2 reopening.
  Existing Dune, RTL/artifact/provenance and hierarchy workflows remain exercised.
- Real serial balanced/synth_delay synthesis completed with **673/685 cells**,
  acceptance **`not_evaluated`**, early allocation and client-detach survival.
  Actual cached UI reopening shows **673→685** and **pinned 673 beside following
  685**. [The plan](construction_phase_plan.md#evidence-and-candidate-baseline)
  consolidates evidence roots and exact candidate executable/hash provenance.
- **D1 accepted:** windows are attached surfaces; Overview/Timing/Resources are
  workspaces. Their selectors control a shared Main run context by default, with
  explicit independence/relink and per-tile references. See [F10](features/run_contexts.md).
- [F09 simulation/tests](features/simulation_and_tests.md) now use the existing
  generic Dune supervisor through the Execution module and project-scoped tiles.
  Rich cases/seeds/traces remain later FS2 work.
- **D2/D3 FS0 defaults accepted:** captured/revalidated targets, no missing-flow
  fallback, ordinary launch does not select, guarded launch-and-view, follow/pin-run
  first. Immutable snapshots/archival retention and richer command policy are later.
- Tiles render asynchronously delivered module state. The daemon shares/caches
  provider queries; rendering does not spawn one provider process per tile.
- [F11 run-summary caching](features/run_summary_cache.md) is delivered in L1/L2;
  canonical evidence remains provider-owned. Fixture warm/restart report calls stay
  2→2; real restart preserves exact evidence identity with `Cached_unverified`.
- [F12 appearance](features/appearance.md) keeps themes/components/layouts separate,
  utility chrome mountable and headers configurable. FS5/V1's first A–E skins and
  independent color/icon/density controls are delivered; richer gallery fixtures,
  reusable tabs and final aesthetic review remain pending. No embedded editor is selected.
- Limits: shelf layout rather than freeform geometry; no template export/clone;
  local chrome/header preferences do not persist; clock-driven redraw and a basic
  endpoint/assignment form; rich timing paths and measured CTS remain unsupported. Remaining frontend race/reconnect/
  cancellation coverage and scaling measurements are explicit in M0–M3.
- FS1 now includes [synthesis metrics and aggregate physical evidence](fs1_acceptance.md),
  signed timing, check verdicts, verified declared clocks and exact finalization
  import. Real six-stage execution, external acceptance and owned-container
  cancellation have separate retained evidence. Full FS1 remains open for richer
  path/CTS/physical explorers. FS2 structured simulation remains unstarted.
- Workbench-owned finalization/acceptance and report/artifact text viewing are
  delivered, with real palette/transport detach, cancellation, idempotency and
  restart checks. External text opening uses a private terminal-host export,
  not the daemon's original path; binary viewers remain later work.
- Parent format/lint, full runtest/build, installed workflow, actual metrics/physical
  HTTP/PTY/L2 checks, original synthesis inspection and the five-mode interrupt
  matrix passed. Evidence and limitations are recorded in the active plan.

Build, launch and check commands are in the repository [README](../README.md).
