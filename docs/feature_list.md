# Feature inventory

Updated 2026-10-15 from the owner's feature discussion. **Requested** means desired
support, not delivered behavior. Demo scope is deliberately smaller than the full
inventory. Dependencies below are semantic dependencies, not a demand to finish an
entire feature before using its first slice.

[Feature sets](feature_sets.md) group these specs into delivery themes: **FS0** is
the initial demos, FS1 ASIC inspection, FS2 simulation helpers, FS3 workspace/setup
adoption, and FS4 external integrations. A set can deliver only a slice of a feature.
FS5 is the independent appearance/gallery track; F12's minimum structural seams
land in FS0 without requiring all visual variants before functional demos.

| ID / specification | User-facing purpose | Current state | First useful scope |
| --- | --- | --- | --- |
| [F01 Integration](features/integration.md) | Open generic or hardware-aware projects with only the capabilities they supply | Dune, manifest and RTL/hierarchy driver implemented; ASIC adapter pending | Adopt configured public ASIC/specimen interfaces |
| [F02 Modules and tiles](features/modules_and_tiles.md) | Change presentation without rebuilding domain logic; share data across views | Existing services/reducers; new boundaries and tile host pending | Execution/log and synthesis views |
| [F03 Commands and flows](features/commands_and_flows.md) | Palette/buttons/keys select and launch project-owned flows | Build/test/generation controls implemented; palette and named flows pending | Discover, preview, run through synthesis |
| [F04 Workspaces and layouts](features/workspaces_and_layouts.md) | Switch Overview/Timing/Resources arrangements; save and restore them | Fixed TUI; requested workspace host pending | Two named arrangements and basic tile operations |
| [F05 Runs and evidence](features/runs_and_evidence.md) | Switch run context, pin references, reopen results and compare evidence | Build/run references and imported artifacts exist; catalog/bindings pending | Two identified runs and one reference tile |
| [F06 Hardware inspection](features/hardware_inspection.md) | Inspect synthesis, hierarchy, timing, physical evidence and checks | RTL/hierarchy implemented; ASIC-specific projections pending | Synthesis resource evidence plus preserved hierarchy workflow |
| [F07 Project setup](features/project_setup.md) | Initialize existing repositories and offer approachable starter layouts | Root manifest exists; initialization/templates pending | Configure existing specimen; creation later |
| [F08 External clients](features/external_clients.md) | Ches summaries/source jumps, automation, MCP and eventual embedded editing | Application RPC exists; integrations pending | Keep contracts usable outside the TUI; clients later |
| [F09 Simulation and tests](features/simulation_and_tests.md) | Run tests/simulations, inspect attempts/logs/failures, later explore structured cases/traces | Generic Dune test supervision implemented; module/tile pending | Generic test runner over existing supervisor |
| [F10 Run contexts](features/run_contexts.md) | Link selectors across workspaces, detach for investigation and relink | D1 accepted; implementation pending | Main context, multiple selectors, independent/relink actions |
| [F11 Run-summary cache](features/run_summary_cache.md) | Switch runs quickly without repeatedly parsing reports; reuse summaries after restart | Tiered design specified; implementation pending | L1 memory in FS0a, provider invalidation in FS0b, L2 persistence in FS0c |
| [F12 Appearance and gallery](features/appearance.md) | Mix skins/tabs/color/icons/density over composable tiles; compare A–E before selecting defaults | Owner MDs imported; gallery/host changes pending | FS0 tokens/headers/utility tiles; FS5 comparative terminal gallery |

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

[D1](decisions.md) is accepted and captured in F04/F10. D2 command policy and D3
exact-snapshot scope retain open questions before those contracts harden.
The [construction plan](construction_phase_plan.md) defines the
first demos. Later feature scope remains recorded here without becoming a release
prerequisite. [Backlog](backlog/README.md) retains unrelated deferred ideas.
