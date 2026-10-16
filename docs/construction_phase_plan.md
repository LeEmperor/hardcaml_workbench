# Hardcaml Workbench — Demo construction plan

Updated 2026-10-15. **FS0 Demos A–C delivered with bounded limitations.** This is
the active status/checklist, replacing the October 12 P0–P7 plan in the
[archive](archive/construction_phase_plan_2026_10_12.md). The
[feature inventory](feature_list.md) owns product scope; the
[decision log](decisions.md) owns accepted D1/D2/D3 defaults and later policy.
M0–M5 are implementation phases, distinct from feature sets and ASIC phases.

FS0 covers M0–M3's functional slices, not every normative feature requirement.
FS1/FS2 map to richer M4 evidence and simulation; FS3 maps to M5 adoption.
FS5/V1 is an independent appearance gallery, not a functional-demo gate.
FS1's synthesis and aggregate terminal/physical investigation slices and FS5's
first appearance slice are recorded below. FS1 remains open for richer paths,
measured CTS, stage-specific physical/routing investigation and artifact viewers.
No FS2 structured simulation implementation is claimed.

## Evidence and candidate baseline

Use these records together rather than interpreting an old audit as current status:

| Record | Scope / retained evidence |
| --- | --- |
| [Environment inventory](fs0_environment_inventory.md#ready-executable-pair) | Exact executable paths, SHA-256 inventory, capture receipts, tools and wire versions; historical audit, whose pending-wiring/test notes are superseded below |
| [Provider integration](fs0_provider_integration.md) | Implemented API/configuration, supervision, summary identities, budgets and freshness limits |
| [Execution module](fs0_execution_module.md) | Protocol projection and daemon routing over the existing generic supervisor |
| [Terminal host](fs0_terminal.md) | Controls, ownership, launch policy, renderer coverage and known UI limits |
| [Installed checks](fs0_install_checks.md) | Native installed workflow, external fixture, legacy capture checks: all passed |
| [Native acceptance](fs0_acceptance.md) | Actual HTTP/PTY fixtures, real serial synthesis, allocation/detach, warm/restart identity and live cached UI reopening |

Exact accepted candidate (not an assertion that today's sibling HEAD was linked):

```text
project  /home/wayne/devel/jane/hardcaml_asic_example/_build_namedflow_real/default/bin/project.exe
SHA-256  5e8bdaab7dc4a5f5dbda8dae22a3e9946c4db09bf16951381d125a418d3a49b1
provider /tmp/opencode/namedflow-real-20261015/provider/bin/hardcaml-asic-flow
SHA-256  2c6604d355b819ee5cec8f731b4ba810ea9415ebf56f24ebac798a8d346bcdd5
tools    /home/wayne/devel/jane/hardcaml_asic_example/_flow_tools
```

Provider package `0.1.0`, CLI contract **4**, `namedflow1=true`; observation reads
v2, allocation v1, reports/historical methodology v1. Source stamping is absent.
The inventory records captured source checksum
`a12a763f842f283ab31649e8ded40786b304277f8e572d0f68e500e1fdc1686d`
and receipts under `/tmp/opencode/namedflow-real-20261015/`; package version alone
does not identify the linked source. The normal `.dev/asic/current` installation
is distinct from this explicitly selected pair.

Primary Workbench acceptance roots:

- `/tmp/opencode/workbench-fs0-91em64rl/`: fixtures plus real balanced **673** /
  synth_delay **685**, both completed, acceptance **`not_evaluated`**; early
  allocation while launcher executing, submission-client detach, durable contexts,
  pins and L2 identity. `real/verified.json` and `outcome.json` retain results.
- `/tmp/opencode/workbench-fs0-unzwt0kn/`: actual 120×40 cached real UI reopening;
  **673 → 685**, pin back to **673**, then **pinned 673 beside following 685**;
  current-screen assertions, unchanged run registry and restart restoration.
- `/tmp/opencode/workbench-fs0-etbs6c68/`: strengthened fixture-only verification.
- `/tmp/opencode/workbench-fs0-6_1ymcsd/`: initial fixtures and preserved real
  preallocation timeout-CLI failure; successful rerun preserved its configured
  `results/` root. The authorized config correction sets stage timeout to `()`.

Exact run/report paths, plan identities and normalized report digests are in
[acceptance](fs0_acceptance.md#successful-real-rerun). Real report-call counts are
not instrumented; fixture warm/restart report calls remain **2 → 2**. Timing `[]`
means unsupported, and synthesis counts are checkpoint-boundary measurements,
not signoff acceptance or per-step attribution.

Final parent validation passed, serially: `dune build -j20 @fmt @lint`,
`dune runtest -j20`, `dune build -j20`, then current HTTP/PTY fixture acceptance
(`/tmp/opencode/workbench-fs0-botbl2jn`), installed native application checks and
legacy baseline checks. The installed PTY test now selects attempts by their exact
submitted IDs and checks full repaints, not incidental ANSI delta retransmission.
External counter fixture acceptance also passed. No additional real EDA was needed
after the recorded two-profile acceptance and real cached-screen verification.

### Takeover reconciliation — 2026-10-15

The checkout was clean at `560ad8f` when inspected; the handoff's uncommitted-work
description was historical. Read-only execution and adopted-provider reviews found
stale FS1/FS5 status statements in the documentation index/inventory, corrected to
match the delivered slices below. No provider adoption or new EDA was performed.

Fresh parent verification, serialized through `scripts/with-switch.sh`:

- `dune build -j20 terminal/main.exe daemon/main.exe` passed.
- `python3 -B scripts/test-terminal-interrupt.py` passed all five cases, with clean
  client exit, restored ISIG/ECHO/ICANON, and the private daemon surviving each client.
  Evidence: `/tmp/opencode/workbench-terminal-interrupt-tb4fj7ht/`.

The inspected regression creates its own metadata-only project, client directories,
state and daemon under a new evidence root; it submits no jobs and performs no Git
operations. This is actual frontend/HTTP behavior over a disposable fixture, not
real synthesis evidence or a full tmux/concurrent-client responsiveness acceptance.
Earlier full-suite and real-tool results above remain historical evidence.

During FS1 integration the owner advanced HEAD to `1a3df25` ("Staging for fs3
parallelization"). Integration preserved that current tree; no agent-created
commit, staging or other mutative Git operation was performed on a live checkout.

## M0 — Decisions, provider baseline and demo fixtures

Features: F01–F06, F09–F11. **Delivered baseline; remaining coverage is explicit.**

- [x] D1: shared Main contexts, independent/relink, multiple selectors and tile pins.
- [x] D2/D3 FS0 defaults approved by the owner's initial **Approve scope** answer:
  captured/revalidated targets, no missing-flow fallback, ordinary launch does not
  select, launch-and-view selects only matching captured revisions; follow/pin-run
  first, immutable snapshots deferred.
- [x] Record explicit candidate executables, hashes, tools and supported wire versions.
- [x] Verify discover/describe/plan/run/observe/report through fixtures and actual
  installed-provider HTTP synthesis. Use returned exact allocation/report references.
- [x] Retain two distinguishable fixture and real runs; backend fixtures cover
  preallocation failure, malformed output, timeout, cancellation, changed/missing
  evidence and cache races. Existing counter fixture remains available.
- [x] Bound the demo to synthesis; expose cell count/breakdown, provenance,
  completion, acceptance and freshness; mark unsupported timing honestly.
- [x] Specify cache keys, source/revision invalidation, missing-source and
  schema/corruption behavior. No cheap provider revision query is available.
- [x] Generic project-scoped Dune test path and deterministic supervisor fixtures;
  installed counter tests and actual HTTP generic test pass without ASIC tools.
- [ ] Complete a single end-to-end matrix for late-response, reconnect, failure and
  cancellation cases across interactive and concurrent clients. Existing focused
  tests cover subsets, not every permutation.

## M1 — Module/command contracts and headless ASIC path

Features: F01/F02/F03/F05/F06/F09/F11. **Demo A delivered.**

- [x] `protocol/execution.ml` projects exact project Build/Test attempts;
  `backend/execution_module.ml` delegates to `Service`. Daemon submit/cancel/log
  handlers route through it; no second scheduler, job store or inferred test cases.
- [x] Daemon-owned ASIC service: four bounded public queries, one launcher,
  coalesced cold reads, automatic reader after persisted allocation, cursor fences.
- [x] L1 decoded summaries (32), L2 indexed summaries (128), bounded payloads and
  explicit retention limits; tiles do not own provider processes or execute EDA on read.
- [x] Typed terminal command catalog, captured target/revalidation, availability,
  shared Build/Test/RTL/cancel actions, exact preview and launch idempotency keys.
- [x] Generic test attempts/status/log/cancel retain project scope, submission
  identity and the existing supervisor's process lifecycle.
- [x] ASIC discovery, description, explicit flow/profile/endpoint preview, exact
  identity-guarded synthesis launch and early allocation without fabricated IDs.
- [x] Durable observation/read-updates and exact report references; distinguish
  command state, execution completion and acceptance. Client detach preserves work.
- [x] Project synthesis resources into shared summaries with checkpoint origin.
- [x] Fixture-owned process cancellation/deadline/output bounds; generic supervisor
  retains descendant cancellation coverage.
- [ ] Broader real provider/container descendant termination acceptance. ASIC
  process cleanup signals only owned PIDs; stopping a reader is not producer
  termination. Full physical-operation acceptance belongs to FS1.

**Demo A:** native HTTP client discovers/previews/runs both real synthesis profiles,
observes allocation before launcher completion, detaches, and retrieves exact reports.

## M2 — Tile host, named arrangements and palette

Features: F02–F06/F09–F12 (minimal F12 seams). **Demo B delivered.**

- [x] Separate transport ownership, pure host reducer/local state and typed rendering.
  Daemon/project/request-order and binding/selection guards reject stale responses.
- [x] One daemon-owned semantic registry: stable session/window/workspace/tile/context
  IDs, Overview/Timing linked to Main, independent/relink and exact per-tile pins.
- [x] Selectors share selected run, retaining local cursor/filter/scroll/focus.
  Moving following tiles adopts the destination context; pins remain exact.
- [x] Tile add/hide/restore/move/reorder/resize/zoom; shelf order/preferred sizes,
  compact focused-tile fallback, with no backend lifecycle side effects.
- [ ] Freeform x/y placement and richer geometry interaction. Stored geometry fields
  do not make the shelf renderer a free-positioned layout system.
- [x] Provisional semantic-role skin, configurable local headers/chrome, mountable
  navigation/status, commands/recovery without chrome, clipped narrow rendering.
- [x] Ches single-transient lifecycle reviewed; bounded palette capture/return focus
  and paste suppression implemented locally. No general float manager claimed.
- [x] `Space c c` palette with effective targets, typed actions and availability;
  remembered explicit launch inputs are persisted independently of inspected runs.
- [x] Run selector, execution/log/project-test/synthesis/evidence tiles and preserved
  legacy RTL/artifact/hierarchy inspector with return to host.
- [x] Reducer/renderer tests cover modal input, delayed-view guards, linkage/pins,
  switching, clipping and local state. Native PTY checks cover real host transport,
  installed discovery/hierarchy and resize down to 1×1.
- [x] Fixture warm A/B switching uses no new report calls; actual cached real UI
  shows 673→685 and pinned 673 beside following 685 with explicit scope/freshness.
- [ ] Expand actual frontend concurrent-client, pending-response, reconnect-during-
  allocation and interactive launch-and-view/cancellation coverage. HTTP Run and
  RPC-driven live selection do not prove every interactive launch path.
- [ ] Measure high-tile-count fan-out, responsiveness, latency and memory/disk use.
- [ ] Fully reactive publication/redraw and richer capability-aware endpoint forms.
  Current refresh/repaint is clock-driven; assignments are whitespace-separated.

**Demo B:** linked/independent workspaces, following/pinned synthesis comparison,
palette operations and project-scoped tests/logs are delivered. Synthetic renderer
fixtures (50/73) and actual real UI evidence (673/685) are separately labeled.

## M3 — Historical reopening and saved arrangements

Features: F04/F05/F10/F11. **Demo C delivered via autosaved session state.**

- [x] Persist bounded run registry/index and versioned normalized L2 summaries
  outside provider results; atomic publication, corrupt/incompatible handling.
- [x] Reopen explicit known provider references after restart without tool execution.
  Broad provider-store discovery is unavailable; no guessed newest directory.
- [x] L2 loads avoid public report materialization and show `Cached_unverified`.
  Fixture refresh/missing/corrupt/eviction tests exist; real warm/restart summaries
  preserve every field except freshness, including original observation time.
- [x] Autosave named workspaces, tile order/hidden/size/zoom/bindings, Main linkage,
  independent contexts and selected exact run references. Actual restart restores
  the full workspace snapshot, including the two-tile real demo.
- [x] Separate semantic registry from client focus/filter/scroll/dimensions; clamping
  stays local. Interactive launch inputs have a separate client preference store.
- [ ] Template export/clone and project-shared template versus personal session UX.
  Autosaved named arrangements are not a template library.
- [ ] Persist local chrome/header preferences and other deliberately local appearance
  choices if selected for adoption; they currently reset with the client.
- [x] Later observations invalidate freshness; explicit Refresh materializes current
  public reports. Missing-source/refresh-failed data remains labeled.
- [ ] Benchmark cold/L1/L2 latency and sizes; expand full missing-reference and
  schema-change interactive restoration coverage. No speed target is asserted.
- [x] Preserve existing hierarchy current/historical evidence labeling in installed
  checks rather than relabeling old hierarchy as a newly selected run.

**Demo C:** daemon restart restores contexts/pins/arrangement and reopens exact
cached real summaries without EDA. Immutable snapshots/archival retention are
deferred by accepted D3 scope, not missing FS0 implementation.

## Remaining FS0 followups

Dashboard usability correction (2026-10-15): the saved acceptance state's empty
Overview was traced to its selector-movement test. Startup now distinguishes loading
from an empty saved arrangement. Fit-to-window is the default local layout mode;
the additive Overview preset supplies 13 views including honest unrequested/
unsupported stages. Requested shelf sizes remain selectable and persisted pins
unchanged. Actual PTY reproduction over a private state copy passed with real
cached 673/685 evidence, all five skins and no provider/result changes:
`scripts/test-fs0-dashboard.py`, `/tmp/opencode/workbench-fs0-dashboard-52akmtcc/`.
Terminal tests, format/lint, installed workflow and legacy baselines passed.

**Owner review, 2026-10-15:** the user reports the Overview works and content renders
correctly inside its tiles. The row/grid arrangement and visual styling are accepted
only as provisional demo presentation, not the intended final layout/aesthetic.
Raw JSON and absolute paths in producer/source provenance are too verbose for the
overview. Follow up with concise semantic labels and an inspectable full reference
(F06/rendering); this does not block the next domain slice. This feedback records
human functional acceptance of the viewed Overview, not broader flow/signoff coverage.

The unchecked M0–M3 items are bounded followups, not grounds to label delivered
demos “not started.” Final parent-wide checks passed. Prioritize missing interactive
race/reconnect/launch-and-view/cancellation coverage, then measured scaling and
adoption choices. Template export/clone, freeform geometry, persisted local chrome
and richer endpoint forms remain explicit gaps; clock-driven redraw remains current.

## M4 — Rich evidence and live acceptance (FS1/FS2)

**FS1 in progress: synthesis and aggregate physical/terminal inspection delivered.
FS2 remains unstarted.** Exact commands/results are in [FS1 acceptance](fs1_acceptance.md).
Features: F06/F09 and execution/regression extensions.

- [x] F06 synthesis inspection over existing cache: count/name sorting, literal
  filtering, stable selected row, count/share detail and full evidence inspection.
  Concise summary labels replace raw producer JSON/absolute-path dumps.
- [x] Validate local state across sort/filter and run/digest changes, missing/zero/
  mismatched totals, overflow handling and independent pinned views. Actual 120×40
  PTY uses real cached 685/673 totals and checks a cell count changing 58→56.
- [x] Verify no provider work is caused by inspection: private-daemon syscall trace
  after cached load has no subprocess launches or provider-result access; original
  state/config/results unchanged. Evidence:
  `/tmp/opencode/workbench-synthesis-inspector-pmzn1twc/`.
  Format/lint, repository unit tests and full build passed serially at `-j20`.
  [Controls/test command](synthesis_inspection.md).
- [x] Hidden-filter recovery followup: persistent filter-input indicator, displayed
  query/match count and Ctrl-U clear, verified through actual PTY after polling.
  The reported apparent crash was not confirmed as process termination: live client/
  daemon remained running and hello responded. See synthesis inspection evidence.
- [x] Subsequent input-hang report reproduced a real Ctrl-C routing defect in raw
  mode. Interrupt now precedes filter/palette/paste capture. Actual PTY before/after
  matrix verifies all five cases exit and restore terminal settings while the daemon
  remains alive. `scripts/test-terminal-interrupt.py`; details in synthesis inspection.

- [x] Synthesis area and diagnostic counters with explicit units, availability and
  checkpoint references; choose the explicit synthesis boundary even after later
  physical failure. Old cache versions remain readable with semantic repair.
- [x] Explicit finalization import validates execution/results hashes, structural
  execution identity and selected checkpoints. Persist the exact operation for
  Refresh; ordinary viewing/restart uses the bounded shared cache.
- [x] Aggregate setup/hold, final physical area/utilization, reported DRC/LVS/antenna
  statuses and full source/context inspection. Preserve distinct execution,
  collection, timing-goal, postcheck and acceptance facts.
- [x] Verified historical declared-clock configuration, not measured CTS or coverage.
- [x] Actual native HTTP/PTY import of collection-only, accepted and rejected
  operations; independent tiles/pins, exact reference form, restart/L2, no warm
  provider reads, Unicode/paste entry and bottom/reverse-scroll recovery.
- [ ] Rich timing path/corner/group exploration, measured CTS/skew/coverage and
  stage-specific placement/routing/congestion views.
- [ ] Project-declared simulation/regression cases, seeds and failure/trace artifacts.
- [x] Bounded terminal-result report/artifact catalog and text paging, exact
  run/attempt/hash/offset/limit identity and explicit stale/expired-page recovery.
  Optional external text opening exports verified sanitized text to the terminal
  host before invoking a configured executable, never opening a daemon path locally.
- [ ] General source viewers, binary/graphical artifact rendering and provenance
  navigation beyond the selected adopted terminal result.
- [x] Real synthesis→floorplan→placement→CTS→routing→signoff completion; separate
  external precheck/gate-level acceptance pass. Earlier 600-second signoff timeout
  remains retained, with earlier synthesis evidence visible through Workbench.
- [x] Actual Workbench signoff launch/client detach/cancel of a confirmed active owned
  container. Launcher stop grace increased from 5 to 15 seconds so provider cleanup
  and terminal publication finish. No owned survivors or later-stage launch.
- [x] Finalization/acceptance producer lifecycle inside Workbench: explicit collateral,
  persistent exact-key reservation, early allocation, phase/status, client detach,
  owned cancellation, automatic validated result import and restart without replay.
- [ ] Cancellation coverage at every physical boundary and broader concurrent
  reconnect/publication race combinations.

**Parent verification:** format/lint, full build, full `runtest -j20` and installed
native lifecycle/RTL/hierarchy/resize checks passed serially. Latest retained real
UI tests: metrics `workbench-fs1-metrics-c00xpq9e`, accepted physical import
`workbench-fs1-terminal-results-5yvke5ek`, original synthesis inspector
`workbench-synthesis-inspector-xf0ihqfd`, interrupt matrix
`workbench-terminal-interrupt-rxwy7wd1` (all under `/tmp/opencode`). Real owned
cancellation passed at `workbench-fs1-cancellation-nyiu2n23`.

**Provider/flow evidence:** unchanged installed provider; only the example launcher
was rebuilt in `/tmp/opencode/fs1-timeout-project-SAuuX0/build` to expose its existing
stage-timeout flag. Successful physical evidence is
`/tmp/opencode/workbench-fs1-physical-w0rftdi0`; setup **11.67551954830797 ns**, hold
**0.12502899069955042 ns**, final area **18916.9 µm²**, utilization **0.0209625**.
Collection acceptance is `not_evaluated`; the separate explicit acceptance operation
at `/tmp/opencode/workbench-fs1-acceptance-5oa67d8u` reports **pass**, with TT precheck
and gate-level replay passing. This is not a universal signoff assertion. Exact
identities, failed attempts and remaining scope are in the linked acceptance record.

**Lifecycle/artifact followup delivered:** [controls and evidence](fs1_lifecycle_and_artifacts.md).
Actual palette→daemon→provider collection, acceptance (**pass**) and cancellation
during external postcheck passed in separate private evidence directories:
`/tmp/opencode/workbench-fs1-lifecycle-qkm54grn`, `...-2p10_520`, and `...-wtprmfgc`.
Each has one producer, unchanged canonical inputs, no owned survivors and restart
without replay. Artifact reads launch no provider work. External text handoff was
verified with a local observer executable, not a claim about a real GUI renderer.
Final format/lint, full build/runtest, installed workflow and five-mode interrupts
passed after integration. No provider upgrade or new physical implementation run
was needed for this followup.

### Earlier proposed execution followup — deferred in favor of FS1

The initial takeover review proposed an identity-safe selected-attempt detail view. This
is a follow-on to F02/F09's existing execution UI within M4, not delivery of FS2
structured simulation or a new ASIC orchestration engine. **Not implemented yet.**

- [ ] Enter/Esc detail navigation over existing `Job.t` identity, kind, state, phase,
  created/started/finished timestamps and exact outcome, with explicit missing fields.
- [ ] Tile-local selection and scrolling retain exact job identity through updates;
  disappearance or daemon-instance replacement must not silently retarget details.
- [ ] Wire bounded stream-labelled logs through existing job log RPC, deduplicating
  interest across visible consumers and rejecting stale-instance responses.
- [ ] Exercise actual HTTP/PTY selection of an earlier attempt, independent tiles,
  live output and return navigation. Keep the five-mode interrupt regression intact.

Preserve the execution tile's existing RTL/driver-job inspection and hierarchy
entry points; do not replace its job list with the generic Build/Test-only
`Execution.attempts` projection. Project-test filtering remains project-scoped.
No historical argv, test cases, progress percentage or ASIC-run association should
be inferred from job kind, log text or current project configuration. Existing
generic supervisor and ASIC process-service boundaries remain separate.

**Original timing gate, now superseded for aggregate terminal evidence:** the
stage-summary adapter still emits `timing = []` because
CLI4 lacks normalized timing attribution/units. The retained accepted 673/685
checkpoint metrics contain synthesis/lint measurements, not setup/hold slack;
`synth_delay` is a profile name, not measured timing improvement. The adopted
provider's `execution/results/stage_report_service.ml` forwards unknown metric
keys with no unit and labels metrics as accumulated boundary snapshots. Its
separate coarse collector and newer source declarations do not establish timing
through the adopted named-flow report path. First require timing-bearing evidence
and a supported units/corner/measurement-origin contract before a timing slice.
The subsequent FS1 implementation uses the existing public finalization-results
contract for aggregate timing, rather than guessing units in stage metrics.
Synthesis area/check counters are now projected into the current summary.

## M5 — Multi-window polish and adoption (FS3)

**Later scope; shared registry primitives exist, adoption acceptance pending.**

- [ ] Two attached monitor surfaces, convergence/local navigation and cross-window
  workspace/tile movement acceptance.
- [ ] Starter templates, existing-project initialization and explicit config migration.
- [ ] High-volume log/event responsiveness and help/discoverability measurements.
- [ ] Reviewed appearance presets, SSH/tmux controls and glyph fallback validation.
- [ ] Final adopted-scope checks and deliberate provider-version adoption.

## V1 — Independent appearance gallery (FS5)

**Aesthetics worktree slice (2026-10-16):** added pure utility-tile presentation
and nonuniform Overview geometry, a three-row workspace navigation tile, session
status and stage checklist, explicit Testing workspace creation, Shift-Tab reverse
focus, brighter Instrument defaults and comfortable padding. Opaque run IDs are
shortened in compact labels with full session inspection available. Stage entries
remain `not reported` until explicit stage observations reach the ASIC snapshot;
available aggregate outcomes/checks are displayed separately. See
[controls and limits](appearance_presets.md#aesthetics-worktree-first-pass-2026-10-16).

Verification: `@fmt`, `@lint`, full `dune runtest -j20` and default build passed;
terminal tests were repeated after navigation/inspection fixes. The raw Ctrl-C PTY
matrix passed all five modes at
`/tmp/opencode/workbench-terminal-interrupt-vqupx_j0/`. Production-renderer A–E
captures now include an aesthetic Overview fixture at 80×24 and 120×40 under
`/tmp/opencode/aesthetics-review/` (synthetic evidence). Owner visual review and
spinner/Nerd Font experiments remain open.

**First skin slice delivered; richer gallery/review pending.** See
[appearance presets](appearance_presets.md) for controls, captures and tests.
This is a reusable renderer over actual FS0 tiles, not a selected final aesthetic.

- [ ] Reuse installed rendering/Ches seams and the existing semantic registry.
- [x] Implement A–E thin skins using shared host rendering, semantic colors, optional
  frames/headers, focus treatments and small-tile fallback. Independent color,
  off/ASCII/Unicode and density controls are available in the actual palette.
- [x] Capture identical synthesis/timing-unavailable/pinned/palette fixtures at wide
  and modest cell grids. Test 90 combinations and actual PTY switching without
  registry changes or provider calls; installed workflows/legacy captures pass.
- [ ] Compare A Instrument, B Structured, C Minimal, D Studio and E Structured Studio
  over identical labeled synthetic Overview/Timing data.
- [ ] Independent color/icon/density axes, reusable tabs and configurable chrome.
  Color/density/basic icon axes are delivered; reusable tab groups and Nerd Font
  mode remain. Studio title badges do not pretend to be navigation tabs.
- [ ] Actual wide/narrow terminal captures, focus/input/glyph/geometry checks and
  owner review before selecting defaults. Mock peeks remain labeled mock.

## Phase summary

| Phase | Current status |
| --- | --- |
| M0 | Accepted FS0 defaults and candidate/fixture baseline delivered; broader matrix remains |
| M1 | Headless Demo A delivered; full physical/container cancellation acceptance later |
| M2 | Tile-host Demo B delivered; bounded UI/coverage/performance gaps above |
| M3 | Autosaved-session/L2 Demo C delivered; templates and appearance persistence gaps above |
| M4 | FS1 synthesis/aggregate terminal timing/check/resources/declared clocks delivered with real physical/acceptance/cancellation evidence; rich explorers and FS2 pending |
| M5 | Later adoption scope; no full multi-monitor acceptance claim |
| V1 | A–E skins/axes/captures delivered; rich gallery and default review pending |

Keep acceptance records authoritative for exact commands/results. New provider
capabilities or normative feature requirements alone do not check a delivery box.
