# WB-007 — Hierarchy module and tile implementation plan

Status: **implemented and automatically verified**, 2026-10-21 on `bpurtell/hier`.
The owner approved implementation after reviewing the durable plan. Activation
is also recorded in the [construction plan](construction_phase_plan.md).

## Scope and source of truth

Deliver [WB-007](features/project/WB-007-hierarchy-tile.md), following
[F02 modules and tiles](features/modules_and_tiles.md) and
[F06 hardware inspection](features/hardware_inspection.md).

- Add a reusable, opt-in hierarchy tile over existing structural evidence.
- Show the elaborated top, exact generating target/configuration, artifact and job.
- Browse expandable instances with independent selection, expansion and scrolling
  in each tile. Reuse the existing detailed inspector for ports and metadata.
- Distinguish current and historical evidence, including older generations for
  the same target/configuration.
- Distinguish the selected elaboration top from a simulation's declared DUT/top.
  Missing provider association is **unknown**, never inferred from selection or
  matching instance names.
- Give missing, pending, failed, cancelled, unsupported and read-error states useful
  explanations and explicit next actions.

WB-007 has no additional prerequisite ticket. WB-008 (leaf/out-of-context execution)
is adjacent but separate. Source navigation (WB-021) and signal annotations (WB-022)
also require additional evidence and are not included. Browsing a node must never
launch elaboration, implementation or simulation.

## Existing implementation to preserve

| Area | Starting point |
| --- | --- |
| Structural contract | `protocol/hierarchy.ml`: artifact-scoped node keys, parent/instance/circuit names, ports, metadata and provenance |
| Read and inspector | `terminal/main.ml`: `inspect_hierarchy`, `index_hierarchy`, tree navigation and `hierarchy_view_lines` |
| Current-generation identity | `terminal/state.ml`: `hierarchy_is_current` and its regression tests |
| Tile lifetime and actions | `terminal/workspace_host.ml`: tile-local state, lifetime identity, palette and input dispatch |
| Presentation | `terminal/host_view.ml`, `terminal/tile_presentation.ml`, `terminal/panel.ml` |
| Composition | `terminal/workspaces/`: presets, tile geometry and layout conventions |
| Verification | `terminal/dune`, existing terminal inline tests and native HTTP/PTY scripts |

The existing inspector uses session-level mutable navigation. Do not reuse that
single navigation object for multiple tiles. Share typed evidence/indexes while
giving each consumer its own navigation state. Structural hierarchy is neither a
signal/operator graph nor synthesized-netlist hierarchy.

## Proposed defaults and pre-implementation contract gate

1. Add `hierarchy` through the existing Add tile mechanism. Keep preset composition
   intact initially, matching the ticket's opt-in default.
2. Initially expand the root; keep compact browsing useful at ordinary tile sizes.
   Provide a detail action for full identifiers, ports and metadata without forcing
   all provenance into every small tree viewport.
3. Use existing project/target/configuration generation selection as the source.
   Explicitly specify selection-change behavior before coding: follow current
   evidence, or retain a visibly historical artifact until an explicit load.
   Neither behavior may mislabel a retained artifact as current.
4. Inspect simulation/provider contracts for an actual declared-DUT association.
   Render an association only with its evidence scope; otherwise show unknown.
   Producing a new DUT mapping is outside this ticket.
5. Reuse existing read transport and bounded artifact validation. Establish the
   shared cache/in-flight owner after tracing the reader; do not add a second
   authoritative store or per-tile provider engine.
6. Agree the typed module API before parallel edits: evidence identity, availability
   states, selection scope, load completion tokens, local navigation, viewport
   projection and inspector handoff. Record exact choices here before integration.

## Execution policies

- **Git:** no `git add`, commit, amend, push, PR creation or other operation that
  attributes AI authorship on GitHub. Read-only status/diff/log inspection is fine.
  Owner-approved scripts may invoke Git as described by the owner; do not use that
  allowance to perform authorship operations indirectly.
- **Job pool:** aggregate concurrency is at most **20**, including nested builds
  and test/provider subprocesses. Every Dune invocation has an explicit `-j` limit.
  Default concurrent allocation: agents A/B/C receive at most **6 each** (18 total);
  coordinator does not build concurrently. Avoid parallel unconstrained test runners.
  Coordinator may use `-j20` only after all agent jobs have stopped.
- **Agents:** use at most **three OpenCode general agents** for implementation.
  Agents do the substantial source work. Coordinator owns docs, interface agreement,
  orchestration, review, integration checks and light corrective edits.
- **Build isolation:** use `scripts/with-switch.sh` and the repository formatter.
  Assign distinct build directories when concurrent builds require them; inspect
  wrapper usage first. Do not share an actively written build tree across agents.
- **External repositories:** changes to `hardcaml_asic` and
  `hardcaml_asic_example` are permitted if needed. First record the concrete missing
  contract/fixture and check their local instructions and dirty state. Expect to
  reuse the current hierarchy evidence without external changes.
- Preserve unrelated owner work. Keep runtime tests isolated from live workspaces
  and evidence. No implementation work is authorized merely by writing this plan.

## Agent work packages

### A — Shared hierarchy model and reader lifecycle

**Own:** a dedicated terminal hierarchy module, its focused tests, and any narrowly
required shared reader changes. Coordinator assigns shared build-file edits.

- Trace existing hierarchy read validation, limits, identity and caching first.
- Extract reusable typed evidence/indexing and local-navigation operations from the
  existing inspector where appropriate, retaining its behavior.
- Define availability and freshness from exact evidence and current generation.
- Share decoded evidence and equivalent in-flight reads across consumers. Bound
  retention and avoid rebuilding indexes on each frame or navigation event.
- Fence completions against daemon/project changes, tile removal/recreation and
  superseding loads; stale responses may not overwrite the active view.
- Identify whether any supported simulation contract supplies DUT association;
  expose evidence-backed association or explicit unknown.

**Done when:** focused tests cover independent navigation over shared data,
collapse/selection consistency, same-selection newer generations, request reuse,
and delayed-response/lifetime rejection. Return API notes, changed paths and exact
commands/results to the coordinator.

### B — Tile, host controls and inspector integration

**Own:** `terminal/workspace_host.ml`, `terminal/host_view.ml`,
`terminal/main.ml`, and focused host/presentation tests. Consume A's agreed API;
do not independently implement another hierarchy reader.

- Register the opt-in tile and palette actions through existing host conventions.
- Add tile-local navigation and render a bounded compact tree with visible top,
  freshness and accessible exact provenance.
- Supply explicit loading/empty/error/unsupported states and appropriate actions
  using existing generation/read workflows.
- Route local browsing only when the tile is focused and no palette/modal/prefix
  owns input. Preserve global navigation and interrupt behavior.
- Open detail for the selected tile artifact/node. Detail must not silently switch
  to the globally selected job or mutate another tile's navigation.
- Handle small viewports and existing appearance/header/hints settings. Preserve
  existing inspector access and normal layout persistence.

**Done when:** two tiles browse independently, detail identifies the correct node
and artifact, and host/presentation checks cover focus, modal routing, clipping,
selection changes and nonempty unavailable states. Return controls and evidence.

### C — Native acceptance and regression proof

**Own:** a focused hierarchy HTTP/PTY acceptance script and isolated fixture additions.
Do not edit A/B's implementation files; report issues with reproducible evidence.

- Begin with existing harness/fixture investigation and scenario preparation while
  A/B establish interfaces; complete execution once integrated binaries are ready.
- Mount two hierarchy tiles over one retained artifact; move/expand independently
  and open selected-node detail.
- Observe read/job/provider counts to distinguish shared evidence access from
  forbidden regeneration. Verify opening, browsing, hiding and closing tiles never
  launches a job.
- Exercise target/configuration switches and a newer generation of the same
  selection, including delayed replies and tile removal/recreation.
- Exercise missing, pending, failed, cancelled, unsupported and malformed/read-error
  evidence, and absent DUT mapping. Verify recovery actions remain available.
- Verify existing inspector and opt-in layout behavior through real host input.

**Done when:** script assertions and retained receipts demonstrate the acceptance
matrix below. Record fixture limitations explicitly; synthetic evidence is not a
claim about real provider DUT mapping.

### Coordinator — Contract, integration and documentation

- Resolve the contract gate, allocate file ownership and job budgets, then launch
  up to three general agents. A/B may overlap only after API agreement; C can prepare
  its harness independently. Serialize any shared-file edits.
- Review returns against WB-007 and F02, especially shared-read ownership, stale
  responses, exact identity and the separation of elaboration versus tested top.
- Integrate and run focused checks first. After agents stop, run appropriate normal
  checks with explicit budgets, ordinarily `dune build -j20`,
  `dune build -j20 @fmt @lint`, and `dune runtest -j20` through the repository wrapper.
- Run C's native proof with controlled subprocess concurrency and retain receipts.
- Update this plan, user-facing controls and ticket status only after verification.
  Record blockers rather than marking unverified criteria complete.

## Acceptance matrix / delivery checklist

- [x] Contract gate resolved and interface/file ownership recorded.
- [x] WB-007.1: tile identifies top, artifact, generating job and exact target/configuration.
- [x] WB-007.2: target/configuration changes and newer same-selection generation
      cannot leave old evidence labeled current; delayed responses remain fenced.
- [x] WB-007.3: absent tested-top association displays unknown; supplied association
      is separately scoped and never copied from elaboration selection.
- [x] WB-007.4: two tile instances preserve independent browsing over shared evidence
      without new generation or duplicate equivalent in-flight reads.
- [x] WB-007.5: unsupported/pending/missing/error states are nonempty and actionable.
- [x] Detail inspector preserves selected artifact/node and existing inspection workflow.
- [x] Opt-in placement, compact rendering, modal/global input and tile lifetime verified.
- [x] Focused tests, native HTTP/PTY proof and appropriate integration checks pass.
- [x] Controls, exact commands, receipts and remaining limitations documented.

## Decisions and implementation evidence

Implementation authorized on the existing workbranch. Three general agents own
A/B/C respectively, with at most six build jobs each; coordinator builds wait until
agent builds finish.

Selection behavior: a tile retains its loaded artifact and local navigation until
an explicit load-current action. Freshness is recomputed from the selected
project/target/configuration and latest generation, so retained evidence becomes
historical immediately. Opening a tile does not generate RTL. Root initially
expanded; detail opens the tile's exact selected node/artifact.

Agent A owns the new reusable `terminal/hierarchy_view.ml` typed model and its
inline tests; B owns runtime shared-read coordination, host/presentation integration,
and `terminal/dune`; C owns the native acceptance script and isolated fixtures.
The shared model uses immutable per-view navigation over shared evidence/indexes.
Runtime requests are deduplicated by daemon/artifact identity and completion is
fenced by consumer lifetime and superseding intent. Existing protocol evidence
remains authoritative.

Delivered API: `Hierarchy_view.evidence` builds shared indexed evidence; `create`
creates an independent immutable navigation value; `move`, `toggle`, `select`,
`visible` and `rows` support browsing; `hierarchy`, `selected_key` and
`selected_node` preserve access to exact evidence. Runtime reads are shared across
tile and existing inspector consumers, with 16 pending / 16 completed limits.

All three work packages completed. Integration review corrected project-scoped host
binding semantics and added compact job/artifact identifiers. Normal-tree build,
full tests, lint and changed-file formatter checks passed after agents finished.
Native acceptance passed against the final binaries at
`/tmp/opencode/hierarchy-tile-w1de3jp1/`; fixture self-tests also passed.

The [delivery record](hierarchy_tile.md) owns exact controls, commands, receipts,
global-format baseline failures and limits. No current provider contract supplies
DUT association, so the positive association branch is not claimed/tested; unknown
is the delivered behavior. No external-repository changes were needed, and no Git
staging, commits or pushes were performed.
