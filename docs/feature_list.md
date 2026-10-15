# Feature inventory

Updated 2026-10-15 against current source and FS0 acceptance. **FS0 Demos A–C are
delivered with bounded limitations.** **Requested** means desired support, not
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
| [F01 Integration](features/integration.md) | Open generic or hardware-aware projects with only the capabilities they supply | Dune/driver plus configured public ASIC adapter delivered; real synthesis passed | Exact installed candidate, discover/describe/plan/run/observe/report |
| [F02 Modules and tiles](features/modules_and_tiles.md) | Change presentation without rebuilding domain logic; share data across views | Execution boundary, daemon ASIC service and tile host delivered | Shared execution/log/test/synthesis views; reactive publication refinement remains |
| [F03 Commands and flows](features/commands_and_flows.md) | Palette/buttons/keys select and launch project-owned flows | Palette, captured/revalidated commands, remembered Plan inputs and named synthesis delivered | Exact-preview launch and guarded launch-and-view; basic endpoint form |
| [F04 Workspaces and layouts](features/workspaces_and_layouts.md) | Switch Overview/Timing/Resources arrangements; save and restore them | Named autosaved workspaces and tile operations delivered; shelf geometry | Main-linked Overview/Timing, independent/relink; template export/clone absent |
| [F05 Runs and evidence](features/runs_and_evidence.md) | Switch run context, pin references, reopen results and compare evidence | Registered exact references, follow/pin-run, L2 reopening delivered | Real 673/685 switch and pinned/following comparison; broad store discovery absent |
| [F06 Hardware inspection](features/hardware_inspection.md) | Inspect synthesis, hierarchy, timing, physical evidence and checks | RTL/hierarchy plus FS1 synthesis table/filter/sort/cell detail/evidence inspector delivered | Cached inspection; timing/check/physical slices remain |
| [F07 Project setup](features/project_setup.md) | Initialize existing repositories and offer approachable starter layouts | Root manifest exists; initialization/templates pending | Configure existing specimen; creation later |
| [F08 External clients](features/external_clients.md) | Ches summaries/source jumps, automation, MCP and eventual embedded editing | Application RPC exists; integrations pending | Keep contracts usable outside the TUI; clients later |
| [F09 Simulation and tests](features/simulation_and_tests.md) | Run tests/simulations, inspect attempts/logs/failures, later explore structured cases/traces | Project-scoped module/tile, attempts/logs/cancel delivered over existing supervisor | Real PDK-free tests passed; no structured cases/seeds/traces (FS2) |
| [F10 Run contexts](features/run_contexts.md) | Link selectors across workspaces, detach for investigation and relink | Daemon-owned revisioned Main/independent contexts and pins delivered/persisted | Linked selectors, independent/relink, move semantics; multi-monitor acceptance later |
| [F11 Run-summary cache](features/run_summary_cache.md) | Switch runs quickly without repeatedly parsing reports; reuse summaries after restart | Bounded L1/L2, coalescing, observation invalidation and explicit Refresh delivered | Fixture 2→2 report calls; real exact restart identity with Cached_unverified; no cheap revision query |
| [F12 Appearance and gallery](features/appearance.md) | Mix skins/tabs/color/icons/density over composable tiles; compare A–E before selecting defaults | First A–E skins and independent presentation controls delivered; richer gallery/review pending | Actual host palette controls and shared synthetic captures |

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
and [installed checks](fs0_install_checks.md) record runtime results. FS1 synthesis
inspection and FS5's first appearance slice are delivered; FS2 remains unstarted.
The next proposed execution-inspection slice is scoped in M4, not yet implemented.
Later feature scope remains recorded here without becoming a release
prerequisite. [Backlog](backlog/README.md) retains unrelated deferred ideas.
