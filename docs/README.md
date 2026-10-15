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
| [Decision log](decisions.md) | Accepted run contexts and remaining command/snapshot choices |
| [Architecture](hardcaml_workbench_architecture.md) | Runtime, ownership, data and integration boundaries |
| [Rendering](rendering.md) | Presentation, input, layout and headless interaction requirements |
| [Appearance handoffs](design/README.md) | Imported older design doc, newer gallery and implementation qualifications |
| [Formatting](formatting_guide.md) | Source conventions |
| [Backlog](backlog/README.md) | Deferred work and reactivation triggers |
| [Archive](archive/README.md) | Superseded plans and historical acceptance evidence |

The feature list is the concise product inventory; feature sets group delivery
themes (current target: FS0). Focused feature documents record
behavior and boundaries; the construction plan alone owns implementation order and
new completion evidence. A feature request or a provider capability is not proof
of an implemented Workbench feature.

## Current orientation — 2026-10-15

- Delivered Workbench foundation: native daemon/client, Dune jobs, logs,
  cancellation, manifest/driver discovery, RTL/artifacts/provenance and hierarchy.
- Next demos: typed modules/tiles, generic simulation/test runner, palette-driven
  ASIC synthesis, linked/independent run inspection and historical reopening.
- The sibling ASIC provider and FIFO specimen have advanced beyond the October 12
  review. Adopt an explicitly verified version; do not repeat obsolete upstream
  tasks from the archived handoff.
- **D1 accepted:** windows are attached surfaces; Overview/Timing/Resources are
  workspaces. Their selectors control a shared Main run context by default, with
  explicit independence/relink and per-tile references. See [F10](features/run_contexts.md).
- **New F09:** [simulation/tests](features/simulation_and_tests.md) start with the
  existing generic Dune test supervisor. Rich case/trace adapters follow later.
- D2 command policy and D3 exact-snapshot scope retain open questions. They do not
  block pure run-context state or generic execution/test module extraction.
- Tiles render asynchronously delivered module state. The daemon shares/caches
  provider queries; rendering does not spawn one provider process per tile.
- [F11 run-summary caching](features/run_summary_cache.md) is FS0 scope: hot decoded
  summaries in L1, persistent derived summaries in L2, canonical evidence owned by
  the provider. Warm switching and restart reuse have explicit acceptance checks.
- [F12 appearance](features/appearance.md) keeps themes/components/layouts separate,
  utility chrome mountable and headers configurable. FS0 includes minimal seams;
  FS5/V1 compares five candidates on mock Overview/Timing fixtures. No final default,
  embedded editor or implemented workspace registry is implied by the imported gallery.

Build, launch and check commands are in the repository [README](../README.md).
