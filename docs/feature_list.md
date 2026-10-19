# Feature inventory

## Actionable ticket catalog

The owner's current requests now have **one Markdown file per feature**, grouped
in [the WB ticket catalog](features/README.md). It contains **66 tickets**: 61 distinct
features from 62 intake entries (one duplicate merged), four explicitly sourced
existing followups, and the later WB-066 native-provider request. Each has tags,
status, priority, defect severity where relevant,
original size label, estimated size/points/confidence, acceptance criteria,
dependencies and open decisions.

Start with the [categorized index and estimate conventions](features/README.md),
[complete intake crosswalk](features/intake.md), and
[dependency/interface map](features/dependencies.md). Numerical estimates are
provisional relative effort, not days. Existing delivery is excluded from incremental
estimates; epic estimates exclude separately ticketed prerequisites.

| Category | Tickets | Main concerns |
| --- | ---: | --- |
| [Presentation](features/README.md#presentation-and-interaction) |15 | Alignment, controls, icons, tabs, overlays, glyphs and Testing composition |
| [Workspaces](features/README.md#workspaces-input-and-configuration) |7 | Mouse/hotkeys, layout/window files, editing, template picker and attachment |
| [Project adoption](features/README.md#project-adoption-and-design-scope) |10 | Build/bundle state, hierarchy/IP scope, files, setup and discovery |
| [Evidence](features/README.md#evidence-and-hardware-investigation) |9 | Refresh/timestamps, Timing triage, comparisons, graphics, mappings and power |
| [Verification](features/README.md#verification-and-simulation) |11 | Formal, waveforms, catalogs, sweeps, adapters, native provider helpers, replay and acceptance |
| [Infrastructure](features/README.md#execution-storage-and-observability) |9 | Process view, metrics, logs, streaming, budgets, responsiveness and coverage |
| [Integrations](features/README.md#external-providers-and-clients) |3 | Vivado, Ches and Git/Mercurial |
| [Exploration](features/README.md#design-space-exploration) |2 | Design/build sweeping and Quick-Harn comparative editing |

**WB-009 is a newly reported, unconfirmed Timing-coherency defect.** Earlier accepted
FS1 evidence remains valid; it does not diagnose the owner's new execution. WB-002
is further icon expansion over the native indicators already delivered in the
current tree, not a request to implement those foundations again.

## Architectural areas and delivered baseline

**Native-provider closeout, 2026-10-19:** WB-066 is complete and owner-accepted.
The separately packaged OCaml helper library and project-owned native adapters
preserve independent test executables and the FS2v1 contract.
[Implementation and evidence](native_provider_plan.md).

Updated 2026-10-17 against current source and FS0/FS1/FS2/FS3 evidence. **FS0 Demos A–C
and FS1's adopted-evidence functional scope are delivered with explicit limits;
the substantial project-scoped FS2 milestone is accepted and closed.**
**Requested** means desired support, not
delivered behavior. Demo scope is deliberately smaller than the full
inventory. Dependencies below are semantic dependencies, not a demand to finish an
entire feature before using its first slice.

[Feature sets](feature_sets.md) group these specs into delivery themes: **FS0** is
the initial demos, FS1 ASIC inspection, FS2 simulation helpers, FS3 workspace/setup
adoption, and FS4 external integrations. A set can deliver only a slice of a feature.
FS5 is the independent appearance/gallery track; F12's minimum structural seams
land in FS0 without requiring all visual variants before functional demos.

| ID / specification | User-facing purpose | Current state | First useful scope |
| --- | --- | --- | --- |
| [F01 Integration](features/integration.md) | Open generic or hardware-aware projects with only the capabilities they supply | Dune/driver plus configured public ASIC adapter delivered; physical, finalization and inspection interfaces exercised | Exact installed generation and public contracts; missing capabilities remain explicit |
| [F02 Modules and tiles](features/modules_and_tiles.md) | Change presentation without rebuilding domain logic; share data across views | Execution boundary, daemon ASIC service and tile host delivered | Shared execution/log/test/synthesis views; reactive publication refinement remains |
| [F03 Commands and flows](features/commands_and_flows.md) | Palette/buttons/keys select and launch project-owned flows | Palette, captured/revalidated commands, remembered Plan inputs, named flow launch and finalization/acceptance lifecycle delivered | Exact-preview launch and guarded launch-and-view; explicit finalization collateral, durable keys, phase/reconnect/cancel; basic endpoint form |
| [F04 Workspaces and layouts](features/workspaces_and_layouts.md) | Switch Overview/Timing/Resources arrangements; save and restore them | Named autosaved workspaces, atomic bootstrap and preset-preserving CLI templates delivered; Fit/shelf geometry | Main-linked Overview/Timing, independent/relink; shared Overview/Timing/Testing starters and generic/ASIC templates |
| [F05 Runs and evidence](features/runs_and_evidence.md) | Switch run context, pin references, reopen results and compare evidence | Registered exact references, follow/pin-run, L2 reopening delivered | Real 673/685 switch and pinned/following comparison; broad store discovery absent |
| [F06 Hardware inspection](features/hardware_inspection.md) | Inspect synthesis, hierarchy, timing, physical evidence and checks | RTL/hierarchy, synthesis, timing paths, measured clocks, stage-specific physical/routing/congestion, checks, report paging and text/binary handoff delivered | FS1 complete for adopted evidence; embedded graphics, unsupported mappings and later provider extensions remain |
| [F07 Project setup](features/project_setup.md) | Initialize existing repositories and offer approachable starter layouts | Existing-project initializer, manifest-only reload, CLI starter templates and selected presentation persistence delivered | Current manifest format and installed handoff verified; config-location migration and new-project creation later |
| [F08 External clients](features/external_clients.md) | Ches summaries/source jumps, automation, MCP and eventual embedded editing | Application RPC exists; integrations pending | Keep contracts usable outside the TUI; clients later |
| [F09 Simulation and tests](features/simulation_and_tests.md) | Run tests/simulations, inspect cases/seeds/failures and traces | Generic tests, structured suites/catalog, cooperative investigation, reruns, durable history and exact trace export over existing supervisor | Real counter and FIFO/native HTTP/PTY passed; Testing composition owner review pending; gate-level, archived replay and embedded waves remain later |
| [F10 Run contexts](features/run_contexts.md) | Link selectors across workspaces, detach for investigation and relink | Daemon-owned revisioned Main/independent contexts and pins delivered/persisted | Linked selectors, independent/relink, move semantics; multi-monitor acceptance later |
| [F11 Run-summary cache](features/run_summary_cache.md) | Switch runs quickly without repeatedly parsing reports; reuse summaries after restart | Bounded L1/L2, coalescing, observation invalidation and explicit Refresh delivered | Fixture 2→2 report calls; real exact restart identity with Cached_unverified; no cheap revision query |
| [F12 Appearance and gallery](features/appearance.md) | Mix skins/tabs/color/icons/density over composable tiles; compare A–E before selecting defaults | A–E skins, schemes, native activity/status indicators and selected persistent preferences delivered; further composition/gallery work pending | Actual host palette controls and shared native/synthetic captures |

## Dependency map

```text
F01 configured provider ──→ F03 flow operations ──→ F05 observed run/evidence
          │                         │                       │
          └──→ F02 module contracts ┴──→ F06 domain views ←─┘
                         │                       │
                         └──→ F04 workspace/tiles┘
                                      │
                            F05 follow/reference bindings

F10 shared run contexts joins F04 workspaces to F05 evidence selection.
F11 caches F02 domain summaries using F01 identities for fast F05/F10 switching.
F09 tests reuse F01/F02/F03 and feed F04 tiles; ASIC integration is optional.
F07 setup/templates composes F01 + F04; does not define ASIC recipes.
F08 clients consume F02/F03 APIs; source navigation also needs F06 source evidence.
F12 presents F02/F03/F04 contracts independently of backend data and F11 caches.
```

F02/F04/F05 can start against deterministic fixtures while F01/F03 integrate the
provider. Rich timing inspection need not block a synthesis demo. Multiple OS
windows need not block named workspace switching within one terminal surface.

## Product principles

- Capabilities, not mandatory adoption tiers: a driver does not imply an ASIC flow.
- Providers own tools and authoritative evidence; modules own semantic projections;
  tiles own presentation/local interaction; the host owns geometry/focus/context.
- Reading/subscribing/switching views never implicitly executes expensive work.
- Tiles query daemon-hosted modules. Shared cached/in-flight reads and bounded
  asynchronous provider access feed reactive views; no process is owned by a tile.
- Completion, goal attainment and verification acceptance are separate facts.
- Evidence keeps run, producing stage, revision, units and measurement context.
- Flow/profile selection for a future launch differs from run selection for viewing.
- Overview/Timing/Resources are workspaces; windows are attached surfaces. Shared
  Main run context is the default; workspace detach/relink and per-tile pins are
  separate from layout persistence. Multiple selectors share selection, not scroll.
- Simulation/test attempts may be project-scoped without an ASIC run association.
- Cache normalized domain summaries in daemon memory and a separate persistent
  Workbench store; canonical provider records remain authoritative. Budget retention
  and distinguish cached/unverified evidence from validated current observations.
- Preserve useful existing RTL and hierarchy workflows while extracting boundaries.
- Appearance is orthogonal to workspace/run identity. Prefer mountable navigation/
  status tiles and configurable headers; keep input/recovery infrastructure thin.
  A provisional demo skin does not choose the final A–E default.

## Decisions and delivery

[D1 and D2/D3 FS0 defaults](decisions.md) are accepted, including guarded
launch-and-view and follow/pin-run first; immutable snapshots are deferred.
The [construction plan](construction_phase_plan.md) records delivered conditions,
true leftovers and consolidated candidate/evidence links. [Acceptance](fs0_acceptance.md)
and [installed checks](fs0_install_checks.md) record runtime results. FS1's
adopted-evidence scope and FS5's first appearance slice are delivered.
[FS1 investigation](fs1_investigation.md) records current completion, real evidence,
provider adoption and limits. The owner confirmed the Escape-responsiveness fix;
inspector presentation polish and broader race/scaling coverage are followups,
not FS1 feature blockers. [Substantial FS2 delivery](fs2_acceptance.md) includes
structured project-scoped simulation and real Cyclesim acceptance. The agreed FS2
milestone is accepted and closed; [followups](backlog/fs2_followups.md) preserve later
scope independently of closure.
The F01–F12 specifications remain architectural areas; WB tickets are separately
estimated proposals under those contracts. Proposed catalog scope does not become a
release prerequisite until deliberately activated in the construction plan.
[Backlog](backlog/README.md) retains unrelated deferred ideas and compatibility links.
