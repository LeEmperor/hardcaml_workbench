# Hardcaml Workbench — Demo construction plan

Updated 2026-10-15. This is the active implementation queue, replacing October 12
P0–P7 (preserved in the [archive](archive/construction_phase_plan_2026_10_12.md)).
The [feature inventory](feature_list.md) owns product scope; the [decision log](decisions.md)
records accepted D1 run contexts and remaining D2/D3 questions. Phase IDs use **M0–M5** to avoid
confusion with ASIC's phases and the archived Workbench plan.

**Active product target: [FS0 — initial functional demos](feature_sets.md).** FS0
groups M0–M3; FS1/FS2 split M4 into ASIC inspection and simulation themes, and FS3
groups workspace/setup adoption. Feature sets are product groupings; phases below
remain the single ordered implementation/evidence checklist.

F12's minimal appearance seams belong to FS0/M2. **FS5/V1** below is an independent
comparative-gallery track, not a gate on the functional demos. The imported visual
handoff's gallery phases apply to that track; they do not reorder the main plan.

**Status: planning only. No new Workbench implementation or test pass is claimed.**
Delivered foundations remain native daemon/client, generic Dune operations,
supervision/logs/cancellation, integration discovery, RTL/artifacts/provenance and
elaborated hierarchy. Preserve their existing behavior through extraction.

## What changed since the previous plan

The sibling `hardcaml_asic_example` now supplies a controlled FIFO specimen and
public named-flow discovery/description/preview/launch. Newer ASIC development
provides native execution, durable observation/watch and report references. The
standalone headless client demonstrates the candidate boundary. These findings
replace the old assumption that the entire observation interface is still missing.

The October 15 source review included uncommitted provider development. Latest
named-flow integration evidence uses installed native orchestration with a fixture
external backend; earlier real physical evidence is separate. Neither is proof of
Workbench integration or of real acceptance for the newest named-flow path.

Useful sibling references (checkout locations, not installed runtime dependencies):

- `../hardcaml_asic_example/docs/headless_flow.md`
- `../hardcaml_asic/docs/development/project-flow-catalog-progress.md`
- `../hardcaml_asic/docs/development/flow-infrastructure-progress.md`

Review current public contracts and pin a candidate. Do not implement the obsolete
Python-specific upstream handoff verbatim or assume every catalog/artifact/fine-step
capability is now present.

## M0 — Decisions, provider baseline and demo fixtures

Features: F01–F06, F09–F11. Status: in progress (documentation decision only);
provider baseline and implementation fixtures remain pending.

- [x] Record accepted D1: project session → windows → workspaces → tiles; default
  shared Main run context, multiple selector instances, independent/relink and
  per-tile pinned references. Architecture/rendering/specs synchronized 2026-10-15.
- [x] Import both aesthetic handoffs and reconcile their precedence/scope in
  `docs/design/README.md` (2026-10-15). Gallery v0.5 is newer; registry and general
  float-manager claims are qualified against current code. No visual implementation.
- [ ] Settle remaining D2 command capture/default-selection policy and D3 exact
  snapshot demo/retention scope before those specific contracts harden.
- [ ] Record configured specimen path, provider revision or immutable installation
  identity, project executable, environment and supported protocol versions.
- [ ] Verify the public discover/describe/plan/run/observe/report sequence, using
  explicit paths. Record gaps in run-store listing, snapshot identity/retention,
  detailed timing data, artifact access and cancellation separately.
- [ ] Retain two distinguishable run fixtures with original context, plus pending,
  preallocation failure, failed execution, late response and missing-evidence cases.
  Label synthetic/replayed/real evidence. Keep the existing counter fixture.
- [ ] Choose a bounded synthesis demo and inventory available cell/resource and
  diagnostic fields; unavailable metrics remain explicit.
- [ ] Specify F11 cache source identity/freshness examples, including later result
  revision, missing source and adapter/schema changes. Identify provider revision
  validation separately from potentially expensive report materialization.
- [ ] Identify the existing generic Dune test command and deterministic success,
  failure/cancellation fixtures for F09; this path requires no ASIC provider.

**Exit:** remaining command/binding scope settled and versioned examples available.
Accepted D1 plus generic test fixtures already define an independent first slice;
host/context reducers and generic runner extraction need not wait for ASIC or
exact-snapshot work. Real EDA is not required for fixture-backed implementation.

## M1 — Module/command contracts and headless ASIC path

Features: F01, F02, F03, F05, F09/F11, first F06 slice. Depends on relevant M0 examples.

- [ ] Extract execution/log access into a typed module over existing supervision.
  Specify scope, revisions, bounded updates, queries, commands and evidence refs.
- [ ] Establish daemon-owned asynchronous query coordination: shared cache and
  equivalent in-flight fetches, bounded provider reads and one-reader fan-out.
  Separate safe read scheduling from long-lived execution queues; keep provider
  locking rules. No tile-owned processes or query-triggered EDA execution.
- [ ] Implement F11 L1 typed summary caching, versioned keys/current-observation
  index and bounded active/recent retention. Share data across contexts/tiles;
  separate large detail. Map provider invalidation so late fetches cannot regress
  newer summaries and completed runs can acquire later revisions.
- [ ] Define command IDs/arguments/availability/context once; adapt existing
  build/test/cancel/RTL actions without losing submission deduplication.
- [ ] Expose the generic simulation/test module over existing Dune test supervision:
  typed attempts/status/log access and cancellation, no invented case counts or ASIC
  run association. Verify fixtures and one real PDK-free project test invocation.
- [ ] Implement the configured ASIC adapter: discovery, flow/profile selection,
  preview identity, launch and early allocation. No fabricated run IDs.
- [ ] Consume durable observation with stream/cursor reconnect; drain launcher
  output without confusing query success with execution or acceptance success.
- [ ] Use returned exact report/artifact references and validate context. Project
  commands retain tool/flow semantics; Workbench does not become a scheduler inside
  the provider. Validate descendant cancellation for the adopted execution path.
- [ ] Project synthesis resources and available diagnostics into shared module
  data. Preserve original reports and source/stage identity.

**Demo A:** plain/headless Workbench discovers the specimen, previews and launches
synthesis, observes allocation/progress, reconnects and reads a contextual report.
Run fixture acceptance first; record actual synthesis acceptance separately when
the chosen provider/tool environment is ready. Client detach leaves work running.
**Independent early check:** generic tests work through the new module API before
the ASIC adapter, retaining explicit project scope and submission identity.

## M2 — Tile host, named arrangements and palette

Features: F02–F05, F09–F11. Depends on accepted D1 and relevant M1 contract shapes; fixtures allow
parallel progress before the live adapter is finished.
Also includes F12's minimal host/component seams, not full gallery acceptance.

- [ ] Separate transport/server data from host context, tile-local state and render.
  Preserve existing event sequencing and stale-response rejection.
- [ ] Implement stable workspace/tile/context identities and at least two named
  workspaces linked to Main. Add differently sized run selectors with shared selected
  run but local focus/filter/scroll; Overview has no privileged ownership.
- [ ] Establish one daemon-owned semantic session/window/workspace/tile registry and
  client projections. Keep local dimensions/focus/scroll/overlays/effective geometry
  separate; do not implement a competing registry for a skin or gallery.
- [ ] Implement make-independent initialized from the current run, link-to-context,
  and revisioned invalidation across selection/rebinding. Moving a workspace retains
  its binding; moving a following tile adopts its destination workspace's context.
- [ ] Implement shared shell/focus/input capture and move/reorder, resize,
  hide/restore and zoom. No backend lifecycle side effects from tile manipulation.
- [ ] F12 minimum: semantic tokens, replaceable skin, configurable mostly-on headers,
  reusable tabs and explicit layout geometry. Navigation/status/help-legend tiles
  are mountable; essential commands/recovery work when all such chrome is hidden.
- [ ] Inspect installed Bonsai Term APIs and Ches float placement/capture/release
  implementation; select a thin adapter or bounded shared extraction for the
  single-transient palette. Record reuse limits instead of adding a general float
  manager or mandatory editor dependency. Preserve return focus/paste ownership.
- [ ] Add palette (`Space c c` intended), command availability and effective target
  labels; derive help/shortcut hints from the command registry.
- [ ] Add run selector, execution/log/synthesis tiles, following and reference
  bindings accepted in D1/D3. Preserve useful RTL/hierarchy/artifact inspection while
  migrating it into tile-compatible boundaries.
- [ ] Add a project-scoped simulation/test tile over F09: run, list/select attempts,
  inspect logs/status and cancel. It works without a selected ASIC run and never
  relabels generic test evidence after a context switch.
- [ ] Test actual frontend events with controlled transport/time/dimensions:
  execute once, switch A→B with A responses pending, pin A, move/hide, change
  arrangement, modal capture and compact-size recovery. Select from either linked
  selector, hide the other, detach/relink Timing and verify local navigation/pins.
- [ ] Exercise many tiles over a few shared queries: measure provider-call counts,
  bounded concurrency and warm-cache switching; accept results independently while
  input stays responsive. Test obsolete reads and shared/pinned consumers surviving
  context changes without cancellation of their jobs or required readers.
- [ ] F11 warm-switch acceptance: load R1/R2 with different cell counts, then select
  R1→R2→R1 while unchanged/resident and assert correct values with zero additional
  summary/report materialization queries. Account separately for freshness checks;
  exercise source revision updates, stale responses and bounded-memory eviction.
- [ ] Verify styling/density/icon changes preserve IDs, bindings and local state,
  cause no provider fetches for existing data and retain meaning without color or
  special fonts. Capture one provisional skin at wide/narrow terminal cell grids;
  sensible scroll/hide/tab fallback is enough, no pixel-responsive layout gate.

**Demo B:** from the palette launch synthesis; select A/B and see following tiles
change; keep a labeled A synthesis reference beside B; switch arrangements and
return without losing context or stopping execution. Linked selectors agree; an
independent workspace retains its run until relinked. Run/inspect a generic test
through the simulation tile. Multiple views share module data, not local scroll.

## M3 — Historical reopening and saved layouts

Features: F04/F05/F10/F11. Depends on M1 identities and M2 host model. Storage prototyping
may proceed alongside M2 once identities are stable.

- [ ] Persist a rebuildable provider-result index and bounded revision-keyed cache.
  Start with explicit known references if provider store discovery is unavailable;
  record that limitation rather than guessing the newest directory.
- [ ] Implement F11 L2 normalized summary storage outside canonical run results.
  Choose location/format/budgets and writer ownership; publish complete entries
  atomically, reject incompatible/corrupt entries and rebuild without provider edits.
- [ ] Reopen historical results after daemon restart without tool execution.
  Distinguish missing canonical evidence from labeled cached evidence.
- [ ] Verify L2 reopening avoids re-materializing unchanged large reports after
  restart. Show cached/unverified while validation is pending and source-unavailable
  on missing records; test refresh failure and schema/adapter changes. Measure cold,
  L1 and L2 latency/query counts and memory/disk sizes before setting speed targets.
- [ ] Persist named layouts/templates and session references with schema versions;
  keep project-shared templates separate from personal/machine session state.
- [ ] Keep functional workspace definitions, appearance choices and requested
  geometry distinct in saved config. Restyling does not recreate tile IDs or runs;
  changing suggested layout is explicit and clamping stays local to each surface.
- [ ] Preserve context identities and workspace linkage on restoration: Main-linked
  workspaces must not restore as independent copies of the selected run. Preserve
  independent contexts and pinned references separately from geometry.
- [ ] Refresh later result revisions correctly. Implement immutable snapshot pinning
  only to the extent selected in D3 and supported by provider guarantees.
- [ ] Restore the existing hierarchy/evidence context accurately; a stale result
  must not become an apparent view of a newly selected build/run.

**Demo C:** save a layout/reference, restart the daemon/client, reopen the same
identified results and restore the arrangement. Missing references remain explicit;
unchanged summaries do not trigger tool execution or repeated large-report parsing.

## M4 — Rich evidence and live acceptance

Features: F06/F09 plus execution/regression extensions. Depends on M1–M3 and actual
provider data availability; deliver individual useful slices rather than all at once.

- [ ] Add one timing/check drilldown with setup/hold and measurement context;
  paginate paths/details if supplied. Explain unavailable detailed-path data.
- [ ] Add bounded placement/resource/clock views using actual provider fields.
- [ ] Extend F09 with project-declared simulation/regression cases, seeds and failure
  artifacts where supported. Trace artifacts do not require an embedded waveform UI.
- [ ] Add explicit external artifact/source viewer actions with host/path handling.
- [ ] Demonstrate a real supported physical run, failure/cancellation cases and
  observation freshness. Preserve earlier measurements after later-stage failure.

**Exit:** trace a real issue from a summary to its supporting report. Fixture and
real-tool acceptance are recorded separately. Full timing exploration can continue
after the first useful drilldown.

## M5 — Multi-window polish and adoption

Features: F04/F07/F08/F10 selective slices. Depends on working demos above.

- [ ] Attach two monitor surfaces with shared Main selectors plus independent-context
  support and local focus/scroll. Verify context changes converge across surfaces
  and implement documented cross-window workspace/tile movement semantics.
- [ ] Provide useful starter templates and initialization of an existing project;
  decide configuration-directory naming and root-manifest migration explicitly.
- [ ] Measure responsiveness under bounded high-volume logs/events; review visual
  comfort and help/palette discoverability.
- [ ] Adopt reviewed F12 presets where available without requiring FS5's entire
  experiment matrix for functional adoption. Validate SSH/tmux controls and glyph
  fallbacks on a modest grid; do not assume monitor pixels determine cell sizes.
- [ ] Validate format/lint/unit/build plus affected fixture/install/PTY checks;
  adopt a verified provider version deliberately before production use.

Later independent features: full project creation, Ches summary integration,
MCP/automation adapters, embedded editor, dedicated comparator, rich graphical
views and live third-party/FPGA integrations. Their requirements are retained in
feature specs/backlog, not prerequisites for Demos A–C.

## Dependency and acceptance summary

### V1 — Independent appearance gallery track (FS5)

Status: not started. Feature: F12. Depends on enough M2 host/component contracts
to reuse them, with injected mock state allowed. This is a visual-workstream task
ID, unrelated to application wire protocol V1. It does not block Demos A–C.

- [ ] Confirm reusable installed rendering APIs and Ches float seams; keep generic
  theme/component/layout code free of ASIC I/O and editor-primary assumptions.
- [ ] Add only components needed for the comparison: configurable tile header,
  panel/tabs, metrics, tree/table, inspector, utility status/navigation and overlays.
- [ ] Render A Instrument, B Structured, C Minimal, D Studio and E Structured Studio
  using identical labeled synthetic Overview and Timing data. Retain C; E must be
  a real B+D composition. Neither fixture chooses a mandatory workspace style.
- [ ] Expose independent vivid/selective/restrained color, none/ascii/unicode/
  nerd-font icon modes with fallbacks, and compact/comfortable density. Reuse tabs
  across skins; preserve semantic selection and local state across changes.
- [ ] Showcase movable/hidden utility chrome, configurable/headerless tiles and
  palette/help/mock source-peek surfaces. Use real adapted lifecycle where available
  or label the mock; do not claim stacked/nonmodal or Ches editor integration.
- [ ] Capture actual terminal-cell wide and modest/narrow frames and test geometry,
  glyph widths, focus versus selection, tab semantics, input recovery and no domain
  effects on restyling. Review variants with the owner before choosing defaults.

**Exit:** comparative terminal gallery and bounded component/input evidence; source
panes and engineering fixtures remain explicitly synthetic. Record visual feedback
in the current gallery handoff, not a new sequence of exported versions. Later
defaults, richer floating behaviors and cross-project UI packaging need their own
reviewed scope.

### Functional dependency graph

```text
M0 decisions/examples ──→ M1 headless adapter ──→ Demo A
         └──────────────→ M2 host/palette ──────→ Demo B (with M1)
                  M1 identities + M2 host ─────→ M3 → Demo C
                  M1–M3 + real evidence ────────→ M4 → M5
```

| Phase | Status | Completion evidence |
| --- | --- | --- |
| M0 | In progress (docs) | D1 accepted and synchronized 2026-10-15; D2/D3 and baseline pending |
| M1 | Not started | Existing supervisor/driver foundation; ASIC adapter absent |
| M2 | Not started | Existing fixed renderer; new host/palette absent |
| M3 | Not started | Provider reference foundations; Workbench catalog/layout storage absent |
| M4 | Not started | Existing RTL/hierarchy; richer ASIC views pending |
| M5 | Not started | Depends on demos |
| V1 (FS5) | Not started | Imported visual handoffs and API inspection only |

Record new acceptance here: exact revisions/environment, command/test, outcome,
evidence path, fixture versus real-tool scope, and remaining limitations. Existing
historical acceptance stays archived. Run Dune checks serially per the repository
README. Documentation updates alone do not complete implementation checkboxes.

## Decision/feature update — 2026-10-15

Owner accepted shared Main run contexts, multiple selector instances, workspace
independence/relink and per-tile references (D1/F10). Added F09 simulation/tests
with a generic supervised test runner first. Specs, architecture, rendering and
demo tasks are updated; no new application implementation or runtime acceptance.

**Immediate implementation entry:** F10 pure context state/reducers and F02/F09
execution/test module extraction over existing supervision, using deterministic
fixtures. Settle D2 before palette dispatch semantics and D3 before exact-snapshot
support; establish M0's provider baseline for the separate ASIC adapter track.

Feature-set organization and asynchronous access clarification (2026-10-15): FS0
is the current target; F02 specifies daemon-coordinated reads/subscriptions and
reactive tile rendering. This documents intended behavior, not a new implementation
or concurrency benchmark.

Tiered run caching update (2026-10-15): F11 belongs to FS0a–c, delivering L1 memory,
provider revision/invalidation and L2 persistence respectively. Fast switching uses
normalized summaries, not reparsing full result entries or caching rendered tiles.
The source of truth remains provider-owned; exact snapshot retention stays D3 scope.

Appearance intake (2026-10-15): copied the two owner exports under `docs/design/`;
gallery v0.5 takes precedence. F12 records composable utility tiles, configurable
headers, independent axes and A–E candidates. Minimal structural requirements are
in M2/FS0; the comparative gallery is V1/FS5. Source review confirmed Ches single-
float placement/lifecycle seams and that Workbench's semantic workspace registry is
still planned. No UI implementation, browser/gallery execution or EDA acceptance.
