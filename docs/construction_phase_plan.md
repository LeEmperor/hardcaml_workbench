# Hardcaml Workbench Construction Phase Plan

## 1. Purpose and document authority

Turn the [project idea and philosophy](project_idea_and_philosophy.md) and
[architecture](hardcaml_workbench_architecture.md) into an ordered construction backlog with
demonstrable milestones. The philosophy defines product intent and ownership boundaries;
the architecture remains the main source of truth for system design and scope. This plan
owns implementation order, dependencies, acceptance checks, and progress.

- Retain the four-phase roadmap as background and preserve completed milestone evidence.
  The active release below supersedes its default order and MVP gate; implement D1–D4
  before considering reactivation of parked work.
- Read each milestone's architecture references before implementing it. The steps below
  are implementation guidance, not replacement interface or protocol specifications.
- When implementation reveals a new architectural decision or a conflict, update the
  relevant architecture section first, then revise this plan and the affected code.
- Keep durable design decisions in the architecture. Keep milestone status and completion
  evidence here. Follow the [formatting guide](formatting_guide.md) for coding conventions.
- Treat parked details as options, not commitments. Reactivate them only for an explicit
  workflow need and revise their acceptance scope at that point.

Apply these established boundaries throughout construction:

- Ship a standalone installed native OCaml daemon and `bonsai_term` client for the
  active release. Browser assets and their toolchain work are parked, per
  [frontend choice](hardcaml_workbench_architecture.md#1-frontend-choice-and-delivery-order).
- Keep the application backend-neutral where the backend is not the point. Targets,
  artifacts, metrics, and jobs must describe an FPGA flow and an ASIC flow without either
  one's vocabulary becoming the shared model. Milestone gates name a capability, not a
  vendor tool.
- Open independent Dune/Hardcaml repositories by root. Projects own hardware source,
  libraries, target constructors, configurations, tests, constraints, and CLI entry points.
  The Workbench owns project sessions, jobs, artifacts, processes, and tool adapters.
- Support integration progressively: generic Dune operations without Workbench files;
  an optional versioned `hardcaml-workbench.sexp`; and a versioned project-side driver
  built in the opened project's compiler/package environment for typed Hardcaml operations.
- Compile the shared typed application protocol for native OCaml and JavaScript. Keep
  native backend/adapter dependencies and operating-system resources out of frontend code
  and portable protocol types. The terminal client is native and must still depend on the
  shared protocol only. The daemon resolves artifact IDs to private storage paths.
- The daemon's lifetime is independent of any client's, and clients may attach from another
  machine over an SSH port forward to its loopback address. See
  [deployment modes](hardcaml_workbench_architecture.md#44-deployment-and-client-attachment).
- Keep synthesizable circuits in independent projects, including a small integration fixture.
  Internal application libraries and an optional project-integration SDK do not constitute
  a production hardware library. Do not dynamically load project modules into the daemon.

## Active release — scaf build and flow dashboard (2026-09-20)

**User goal:** replace manual build/flow monitoring and process-list guesswork for
`hardcaml_protemu` in `../scaf/`. Launch work from the TUI, keep setup/hold timing in
a dedicated panel, keep stage and result boxes permanently visible, and inspect
flow status/results and general design information on one monitor.

This section is the active construction backlog and release gate, following the
[architecture scope decision](hardcaml_workbench_architecture.md#active-release-scope--protemu-monitoring-2026-09-20).
It supersedes the old `1C → 1D` gate and default phase order. Reuse delivered
1A–1C capabilities; final human hierarchy acceptance passed on 2026-09-20.
Structural hierarchy is delivered, while per-node reports remain deferred; first ship a staged project report. No code or live
integration completion is claimed by this planning revision.

### D1 — Open the real project and inspect one existing result

**Status:** Not started. **Depends on:** existing 1B and delivered 1C integration.

- [ ] Open `../scaf/` as an independent project in its intended environment; exercise
  ordinary build/test with logs and existing cancellation. Record root, revision,
  environment and commands; keep direct CLI use working.
- [ ] Inspect the current `scaf/docs/flow.md`, `flow.sh`, collected records and archived
  reports. Document the minimal project-side adapter contract for declared operations,
  explicit build/run selection, result schema/version and bounded progress updates.
  Reuse existing driver/job/artifact plumbing; extend only what this project needs.
- [ ] Import an explicitly selected existing result, including setup/hold, checks,
  final standard-cell area and utilization. Preserve original build/run identity and
  report references. Reopen it without rebuilding, provisioning, or starting hardening.
- [ ] Define a capability/evidence mapping for the desired persistent badges: lint,
  emit, sim, GDS, harden, signoff-block and signoff-chip. Do not assume each is a
  supported command or equate it to the project's adopted flow stage of a similar name.

**Demo:** open scaf and view one real archived run's timing/check summary in the TUI,
with unsupported/missing evidence explicit. Fixture-only results do not close D1.

### D2 — Launch and observe the existing flow

**Status:** Not started. **Depends on:** D1's project operation/identity contract.

- [ ] Launch the canonical project entry point (`./flow.sh`, or its project-owned
  adapter) through the daemon supervisor. Offer a full run and explicitly selected
  supported stages; show requested extent before launch. Respect project prerequisite
  and output-selection behavior rather than rebuilding the dependency graph in Workbench.
- [ ] Keep the real stage strip visible: currently `build → emit → preflight → run →
  postcheck → collect → report → archive`. Show declared unsupported capabilities
  separately from runnable stages. Distinguish process exit from goal/check verdicts.
- [ ] Establish live project-owned stage-start/end/failure and substep status evidence.
  Existing final JSON and a human-readable final summary are not sufficient proof of
  live progress support. Add a small structured status/event interface in the consumer
  if needed; Workbench must not infer success from process names or log silence.
- [ ] Display current stage/substep where known, elapsed times, last progress/log
  activity, connection freshness and log tail. Keep not-run, queued, running, passed,
  failed, skipped, blocked, cancelled/interrupted and unsupported distinguishable.
  Report unknown substeps honestly; no fabricated percent complete or ETA.
- [ ] Verify cancellation ownership including containerized tool descendants used by
  this actual flow. Confirm client detach/reattach preserves the same execution and
  state without duplicate submission. Observation loss must not display as completion.

**Demo:** start real flow work in the TUI, observe it without `btop`, detach/reattach,
and recover its status/logs. Exercise a bounded failing/cancelled invocation; no
general-purpose persistent Tcl worker or flow-resume framework is required.

### D3 — Deliver the always-visible timing/results dashboard

**Status:** Not started. **Depends on:** D1 results and D2 execution updates.

- [ ] Build the stable layout: identity/header, persistent flow strip, timing panel,
  result/check badges, compact area/utilization summary, and active job/log region.
  Keep essentials visible on resize and make a selected box open its evidence.
- [ ] Show setup and hold worst slack with units, corner/mode, producing stage,
  constraint context and freshness. Add per-corner detail, TNS and violation counts
  when available through the project adapter. Unconstrained timing is an explicit
  problem; missing/not-yet-produced measurements are not passing zeroes.
- [ ] Keep DRC/LVS/antenna, TT precheck, simulation and any declared block/chip signoff
  verdicts separate from stage completion and timing goals. GDS existence is an artifact
  fact, not a signoff verdict. Unsupported checks retain their place in the display.
- [ ] Keep current source, selected immutable build/run, and measurement source clear.
  While a new run has no timing, show pending; any previous-result reference must name
  its different run and age. Never assemble a misleading green dashboard from mixed runs.
- [ ] Publish completed/partial results and useful failure evidence through existing
  artifact access. Link the primary failure to its stage/log/report. Confirm values
  against the project's own reporter and underlying records.

**Demo:** a real run updates the same dashboard from pending to completion/failure;
setup and hold remain in a dedicated region, stage boxes persist, and every displayed
verdict is traceable to the selected run. Existing archives remain inspectable.

### D4 — Validate daily use and close the release

**Status:** Not started. **Depends on:** D1–D3.

- [ ] Complete one real physical flow launched from the installed Workbench and compare
  displayed results with the project's reports. Stored results validate display but
  do not substitute for live launch/progress evidence.
- [ ] Confirm the pending real SSH/tmux live-update check along with failure,
  cancellation, resize, client exit and reattachment in this workflow.
- [ ] Reopen a named project-owned result after daemon restart without launching a flow.
  This requires result import/reopen, not preservation of a live process across daemon
  restart or a general durable Workbench history store.
- [ ] Use the dashboard for normal project iterations; record and fix concrete friction
  before adding another subsystem. Retain relevant generic-project/fixture regression
  checks; do not expand the live acceptance matrix beyond the intended deployment.

**Release exit:** the user can launch, monitor and inspect scaf's actual build/flow
from the server-side TUI, see setup/hold and persistent stage/check outcomes, and no
longer needs a process monitor to guess whether the flow finished.

### Parked work and bounded follow-ups

| Scope | Disposition / reactivation trigger |
| --- | --- |
| 1C hierarchy human acceptance; per-node reports | Structural hierarchy is implemented, automated validation passes, and final human hierarchy inspection passed on 2026-09-20. Per-node reports stay deferred until an actual inspection task needs them. Neither blocks the dashboard. |
| 1E browser and JS/toolchain fixes | Parked; revisit when graphical inspection is needed. Existing blocker notes are historical evidence, not an active repair task. |
| 2A–2B persistent Vivado/Tcl worker and second report backend | Parked; use the real project's existing batch flow now. Revisit for an actual FPGA workflow. |
| 2C CodeMirror and general durable history | Parked. Explicit reopening of project-owned stored results is in D1/D4; reconsider a database only if that proves inadequate. |
| 3A–3C graphs, integrated waveforms, overlays and cross-run comparison | Parked. Existing simulation commands/results may appear in this dashboard without a waveform viewer. |
| 4A–4D hardware programming, ILA, GUI bridge and distributed workers | Parked until a concrete user workflow requires them. |
| Workstation-native client through forwarded HTTP | Remains deferred; server-side TUI over SSH is the acceptance deployment. |
| General ASIC resumability/multi-project framework | Deferred beyond the minimal scaf adapter. Preserve existing stage/build/run/check semantics without implementing a second runner. |
| Extra resource/system indicators | After D3, add cheap existing cell/FF/memory counts, core/die area, or CPU/RAM/free-disk context if useful. These are not new release gates. |

## 2. Starting point

Repository inspection on 2026-09-14 found a Dune/Opam scaffold, Hardcaml and Bonsai dependency
declarations, formatting/lint configuration, and `scripts/with-switch.sh` for building the
Workbench itself. The scaffold still describes a different product:

- `dune-project` and the generated `hardcaml_workbench.opam` describe synthesizable blocks
  installed as one wrapped library. Web and some native dependencies are classified as
  test/repository tooling rather than application build requirements.
- `lib/dune` declares a public synthesizable `hardcaml_workbench` library but has no
  implementation modules. `bin/generate.ml` is an application-owned RTL generator
  placeholder with its command runner commented out; the test source is empty.
- There is no native daemon, Bonsai application, shared protocol, project integration,
  independent fixture project, or installed launcher/frontend asset packaging yet.

1A must reconcile packaging and dependencies with the application roles in architecture
section 24. The existing generator and hardware-library declarations are scaffold to
replace or relocate as appropriate during implementation, not architecture to preserve.
The Workbench's switch wrapper does not establish the execution environment of an opened
project; selecting and using that environment belongs to project integration in 1B–1C.

These are scaffolding observations, not evidence that the toolchain or any milestone passes.
The starting-point observations are historical; checked items below record subsequent
progress, including the first 1A toolchain/packaging work. They do not establish complete
application or driver support.

## 3. Roadmap and dependencies

**Historical broader roadmap:** the table and dependency graph below retain the
original milestone organization. Their phase gates and order are superseded for the
active release by D1–D4 above. Parked milestones do not automatically become active
when their old prerequisites complete.

| Architecture phase | Construction milestones | Phase exit outcome |
| --- | --- | --- |
| [Phase 1: MVP](hardcaml_workbench_architecture.md#20-suggested-mvp) | 1A installed application foundation; 1B generic Dune projects, jobs, and terminal client; 1C manifest/driver integration; 1D first structured hierarchical report; 1E browser client and graphical views | Launch the installed application, open an independent project, select a driver-discovered target, generate RTL, and inspect a structured hierarchical report with live logs. |
| [Phase 2](hardcaml_workbench_architecture.md#21-phase-2) | 2A persistent Tcl tool worker; 2B synthesis/implementation and reports; 2C RTL viewer and history | Run and revisit synthesis/implementation work through a persistent, typed tool worker, with Vivado as its first adapter. |
| [Phase 3](hardcaml_workbench_architecture.md#22-phase-3) | 3A elaboration graph; 3B simulation/waveforms; 3C overlays and comparison | Explore circuit structure and behavior, relate timing to the design, and compare iterations. |
| [Phase 4](hardcaml_workbench_architecture.md#23-phase-4) | 4A hardware programming; 4B ILA; 4C optional GUI bridge; 4D distributed remote workers | Deploy/debug hardware and extend execution to remote build machines. |

Default order:

```text
1A -> 1B -> 1C -> 1D [MVP gate]
       |           |
       |           v
       |           2A -> 2B -> 2C [Phase 2 gate]
       |                        |
       |                        +-> 3A --+
       |                        +-> 3B --+-> 3C [Phase 3 gate]
       |                                      |
       |                                      +-> 4A -> 4B
       |                                      +-> 4C (optional)
       |                                      +-> 4D
       |
       +-> A.1 -> A.2 -> A.3   (ASIC track; A.2 also needs 1C)
       +-> 1E                  (browser client, gated on the JS toolchain)
```

The existing subdivision is retained. 1A establishes the installed runtime and an independent
fixture; 1B adds generic project opening through Dune and the supervised-job client required by
architecture section 25. 1C builds manifest/driver integration on that project and job
foundation; 1D uses the driver boundary for the first structured report before Phase 2 adds the
persistent tool worker. Generic Dune build/test support is delivered in 1B; Phase 3 adds typed
project simulation.

Two revisions to the earlier ordering:

- **The frontend order is terminal first.** 1A and 1B deliver the `bonsai_term` client; 1E
  adds the `bonsai_web` client and the graphical views. 1E is a Phase 1 milestone but not part
  of the MVP gate, because it depends on the external
  [JavaScript toolchain prerequisite](development.md#javascript-toolchain-prerequisite) that
  currently blocks compiling browser assets at all. The MVP must not be gated on an upstream
  fix outside this repository.
- **The MVP report gate is backend-parametric.** 1D requires one structured hierarchical or
  staged report obtained through the opened project's own reporting path. An FPGA project
  satisfies it with `hardcaml_xilinx_reports`; an ASIC project satisfies it with its flow
  report. Vivado's own integration begins in 2A, so Phase 1 does not require a Xilinx
  installation.

3A and 3B extend the project-driver integration from 1C and can be built independently after
Phase 2. In Phase 4, 4B depends on 4A; 4C and 4D are separate extensions. 4D is the
distributed-worker model only: attached operation, where clients connect to a daemon running
beside the project on another machine, is a deployment mode available from 1B and needs no
milestone of its own. Select and document 4D's transport when defining that milestone; it does
not inherently require a Vivado socket bridge. Optional extensions are recorded as deferred if
they are not selected, rather than marked complete.

### ASIC integration track

**Scope update (2026-09-20):** D1–D3 select scaf as the first consumer and implement
only its required operation/result contract. The broader A.2 requirements below are
design context, not a requirement to build general resumability before displaying
existing results. Preserve the consumer's supplied build/run, corner and check
semantics in the minimal integration.

Follow [ASIC project ownership](hardcaml_workbench_architecture.md#asic-projects-and-hardcaml_asic).
The existing four-phase roadmap and exit gates remain intact. This track runs parallel to them
from the relevant 1B/1C capabilities, without waiting for Vivado and without becoming a
prerequisite for the emulator's ASIC work. All items are initially open.

This track is no longer described as optional. `hardcaml_asic` already emits bundles and its
flow already produces a collected structured result, so the ASIC path is where a
provenance-carrying report exists today, while the FPGA equivalent still depends on the
unwritten Vivado worker. A.1 and A.2 are therefore the cheapest route to a Workbench that is
actually used, and the natural way to satisfy 1D's report gate. No Phase gate blocks on this
track, but that is a statement about the gates rather than a judgement that the work is
speculative.

The architecture changes this track depends on are recorded in
[jobs, builds, and runs](hardcaml_workbench_architecture.md#42-job-system) and the
[artifact model](hardcaml_workbench_architecture.md#18-artifact-model). Five requirements the
FPGA framing did not surface must hold before A.2 is implemented:

1. **Build and run identity are distinct.** One immutable build bundle has many runs. A job
   carries optional build and run references; re-running must not alter build provenance, and
   reopening a stored result must not execute the flow again.
2. **Staged runs are resumable.** Emit, preflight, run, postcheck, collect, and report are
   separately runnable. Record requested versus completed stages; a completed earlier stage is
   not evidence a later one passed.
3. **Results are multi-corner.** A single worst slack cannot represent a run that analyses
   several corners or modes. Metrics carry unit, tool, stage, corner, and source report.
4. **Physical and submission checks are first-class.** DRC, LVS, antenna, and harness
   precheck results are pass/fail/not-run, separate from timing metrics and from stage
   completion.
5. **Environment identity is provenance.** Process design kit, pinned flow virtual
   environments, harness support tooling, and interpreter version are part of the execution
   record. Recording them is not provisioning them.

- [ ] **A.1 — Open an ASIC consumer as an ordinary project.** After 1B, run its
  existing Dune build/test or project commands in its selected environment.
  This is level-1 integration only: running the project's existing commands needs no
  manifest, no driver, and no ASIC-specific Workbench code, which is itself the evidence
  that the integration layer is not FPGA-specific. Evidence: CLI use remains independent;
  jobs retain logs/status and do not implicitly install tools or a PDK.
- [ ] **A.2 — Integrate ASIC build and execution artifacts.** Depends on 1C's
  versioned driver/artifact support and a consumer with an emitted ASIC bundle
  (the emulator tracks this in P0.6/P0.7). Before implementation, define operation
  capabilities, ASIC target/configuration summaries, schema compatibility, and
  cancellation ownership in the architecture, and satisfy the five requirements above.
  Derive target facts from the consumer's declaration/build; keep the manifest small.
  Long-term the runner belongs to the ASIC library or a project entry point and Workbench
  only supervises it; do not let Workbench accumulate flow semantics or learn to call the
  flow's own scripts directly. Evidence: generate or
  run through the project entry point, display results with original manifest/
  execution IDs, preserve report/source-set roles and unknown metrics, and reject
  incompatible integration explicitly. Bundle emission must not display as
  physical closure. Reopening a result must not launch the flow again. Detaching and
  reattaching a client during a long run must not duplicate or orphan it.
- [ ] **A.3 — Reuse supported inspection views.** After A.2 and the relevant
  report/graph/simulation capabilities, display ASIC reports and project-provided
  traces with configuration/build/run identity. Evidence: views match source
  artifacts; unsupported views are explicit. Any emulator device-control extension
  remains a separate product/API decision over its own host library.

Record completion or explicit deferral per item. The helper library owns ASIC
resource/target/flow semantics; this track owns application integration. The
emulator's [L.4](../../scaf/docs/phase_plan.md#10-later--application-on-the-existing-host-api)
owns its project-side adapter. Exact driver APIs are not yet implemented or frozen.

## 4. Phase 1 — A usable MVP

### 1A. Establish the installed application and subsystem foundation

**References:** [project boundary](hardcaml_workbench_architecture.md#2-project-boundary),
[application runtime](hardcaml_workbench_architecture.md#3-recommended-high-level-architecture),
[shared protocol](hardcaml_workbench_architecture.md#43-application-protocol-and-runtime-boundaries),
[repository roles](hardcaml_workbench_architecture.md#24-initial-repository-layout),
[installed application](project_idea_and_philosophy.md#5-application-shape).
**Depends on:** existing scaffold.

Steps:

- [x] Validate the existing switch, dependencies, build, formatting, lint, and test commands;
  document the local startup workflow and any required dependency corrections.
- [x] Replace the scaffold's production hardware-library packaging with application
  packaging and correct dependency classifications. Establish shared protocol, project
  integration, native backend/adapters, daemon, and Bonsai web roles from section 24.
  Keep the project SDK optional; any SDK is driver integration support, not circuit source.
- [x] Implement the initial project, target, job, and artifact types needed by 1B–1D, derived
  from architecture sections 4 and 18. Represent external roots and integration availability;
  generic projects need not have Hardcaml targets. Keep native resources private and expose
  artifact IDs/metadata for daemon-mediated retrieval.
- [x] Keep those schemas backend-neutral from the start, per architecture sections 4.1, 4.2,
  and 18: extensible backend-tagged target facts rather than an FPGA part field; open
  namespaced artifact kinds rather than a closed variant; optional build and run references on
  jobs and artifacts; and metrics carrying unit, tool, stage, corner, and source report rather
  than a fixed LUT/FF/DSP record. These are cheap now and a protocol revision later.
- [x] Record the application RPC, serialization, update/reconnect, launcher, installation,
  and fixture decisions in the architecture. Decided 2026-09-19 in
  [protocol decisions](hardcaml_workbench_architecture.md#1a-application-protocol-decisions-2026-09-19)
  and [installation decisions](hardcaml_workbench_architecture.md#1a-launcher-installation-and-fixture-decisions-2026-09-19).
  This completes design only; transport dependencies and runtime behavior remain unvalidated.
- [x] Implement the versioned typed request/response and incremental update contracts from
  those decisions: S-expressions over HTTP, `hello`, empty `snapshot`, and long-poll `updates`.
  Compile and test the portable definitions natively; keep browser compatibility and leave
  actual JavaScript codec execution to 1E. Browser code depends on the shared protocol,
  not native backend or adapter libraries.
- [x] Package the native daemon and the native `bonsai_term` client, with a project-root
  argument for 1B. Bind the daemon to loopback only. Document both the development startup
  workflow and the installed application workflow. Browser asset packaging belongs to 1E and
  must not gate this milestone; the recorded JavaScript toolchain prerequisite currently
  prevents it.
- [x] Add a deterministic miniature Dune/Hardcaml project under test fixtures. Exercise it
  from an external temporary root with its own `dune-project`, build/test entry points,
  and environment; do not link its circuit modules into Workbench application libraries
  or absorb it into the Workbench Dune workspace. It needs no manifest/driver until 1C.

**Exit check:** build and install into a test prefix, then launch outside the Workbench
checkout. The installed daemon accepts a connection from the installed terminal client, which
obtains a typed response. Confirm that the client depends on the shared protocol only, with no
dependency path to the backend or adapters, and that ordinary fixture build/test commands work
in its separate root. Record exact commands; this establishes the foundation for section 25's
first implementation milestone. Record the browser client as blocked on its upstream
prerequisite rather than as incomplete work in this milestone.

### 1B. Open generic Dune projects and deliver the first job workflow

**References:** [first implementation task](hardcaml_workbench_architecture.md#25-first-implementation-task-for-codex),
[project integration levels](hardcaml_workbench_architecture.md#41-project-model),
[jobs](hardcaml_workbench_architecture.md#42-job-system),
[runtime boundaries](hardcaml_workbench_architecture.md#43-application-protocol-and-runtime-boundaries),
[UI layout](hardcaml_workbench_architecture.md#8-suggested-ui-layout).
**Depends on:** 1A.

**Status:** Complete. The root/session, environment, Dune inspection, V1 compatibility,
per-project FIFO scheduling, process-group cancellation, and daemon-session log decisions were
recorded in architecture section 4.3 on 2026-09-20. Automated and installed checks pass. The user
accepted the intended server-side terminal workflow over ordinary SSH, including repeated resize,
navigation, build/test, log selection, exit, and reattachment. This does not claim every
Ghostty/Xfce/tmux combination or the small-terminal threshold was exercised. At the user's explicit
request, the separate workstation-native client attachment through a forwarded HTTP endpoint is
deferred rather than passed; its original check and commands remain below as a visible follow-up.

Steps:

- [x] Open a user-selected independent root containing `dune-project`; validate the root,
  create a daemon-owned project session, and resolve project-local paths against it.
  Define how the project's execution environment is selected and reported; do not silently
  substitute the Workbench build switch for the project's environment.
- [x] Use supported Dune inspection commands/RPC through a native Dune adapter for generic
  workspace information and normal build/test actions without a manifest or driver.
  Keep Dune authoritative for the build graph; generic inspection does not infer hardware
  top-level constructors, valid parameter sets, clocks, or parts.
- [x] Implement daemon-owned process supervision and the job lifecycle, including exit
  status, failures, cancellation, timestamps, and stdout/stderr capture.
- [x] Expose job submission, state retrieval, and incremental log/status updates through RPC.
  Reconnecting a browser should recover current daemon state without launching the job again.
- [x] Build the project/hierarchy pane, jobs table, and console/log pane in the `bonsai_term`
  client. Show real generic project information and a clearly labeled fixture hierarchy until
  1C supplies elaborated hierarchy; present unavailable Hardcaml actions explicitly. Keep view
  state in the client and all project, job, and artifact state in the daemon, so 1E adds a
  second client rather than a second state model.
- [x] Wire project build/test requests through the typed API, Dune adapter, and supervisor
  to visible completion. At least one is the supervised backend action in section 25.
  Adapters derive tool invocations; the daemon supervisor owns processes; UI sends typed
  requests rather than constructing commands.
- [x] Verify success, nonzero exit, launch failure, cancellation, and daemon shutdown behavior
  with small local commands; ensure supervised child processes are cleaned up.
- [x] Confirm the daemon outlives its clients: exit the client during a running job, then
  reattach and recover the daemon-owned job without submitting another one.
- [ ] **Deferred by user:** confirm a workstation-native client works against a daemon on another
  machine through an SSH port forward, which is the attached deployment mode in architecture
  section 4.4 and needs no additional transport work. This is distinct from running both daemon
  and terminal client on the server and transporting the terminal over ordinary SSH. The current
  intended deployment is the latter. Exact commands and the retained acceptance checklist are in
  `docs/development.md`.

**Exit demo:** use the installed application to open the external fixture without any
Workbench-specific files, inspect Dune-derived information, and run build/test actions in
its environment with output visible before completion. Exercise failure and cancellation,
then reconnect during a job and recover the project, job, and logs without resubmission.
Verify that the fixture still builds/tests directly from the terminal and that no fixture
modules link into the application. This completes section 25's first milestone.

Acceptance scope adjustment recorded 2026-09-20: the exit demo is accepted using the installed
server-side terminal client over ordinary SSH. Workstation-native attachment through a forwarded
HTTP endpoint remains a supported architectural capability and a deferred live validation item;
it is not evidence claimed for 1B and does not block completion under the user-approved scope.

### 1C. Add the versioned manifest and project driver for real RTL

**Scope update (2026-09-20):** reuse the delivered discovery, RTL/artifact, and
structural-hierarchy work in D1–D4. Automated implementation and final human hierarchy
acceptance are complete. This does not change the active D1–D4 construction order.

**References:** [project model](hardcaml_workbench_architecture.md#41-project-model),
[Hardcaml integration](hardcaml_workbench_architecture.md#5-hardcaml-integration),
[runtime protocol](hardcaml_workbench_architecture.md#43-application-protocol-and-runtime-boundaries),
[progressive integration](project_idea_and_philosophy.md#4-progressive-project-integration),
[artifact model](hardcaml_workbench_architecture.md#18-artifact-model).
**Depends on:** 1B.

**Status:** Complete, including final human hierarchy acceptance on 2026-09-20. The first bounded slice defines manifest version 1 and driver describe
protocol version 1, implements optional-integration status, supervised discovery, refresh, and
fixture target/configuration display. The second bounded slice adds client-local selection,
supervised real RTL generation, daemon-owned artifact registration/retrieval, and execution-boundary
source provenance. The final bounded slice adds genuine elaborated structural hierarchy, stable
occurrence keys, atomic association/retrieval, and terminal inspection. Automated gates pass, and
the user confirmed the final hierarchy checklist in the intended server-side terminal workflow.

The user accepted the complete RTL/artifact terminal checklist on 2026-09-20: configuration
selection, distinct four/eight-bit generated output, artifact inspection and isolation,
resize/navigation, and same-daemon reconnect without regeneration. This accepts the second bounded
slice only, not hierarchy or the complete milestone.

A human check found that the first attached terminal session remained on its pending open response
after discovery completed, although reopening showed the daemon's cached result. The client now
reduces the production incremental event stream and prefers that current project record over the
open response. Automated reducer, backend-ordering, installed plain-client, and no-input PTY checks
cover the repair. The incremental-state repair and the later RTL/artifact workflow have now been
confirmed in the user's real terminal. The final hierarchy check also passed: live availability,
root and repeated-child identity, four/eight-bit port inspection, collapse/expansion, compact
scrolling, resize recovery, historical-result labeling, and reconnect without rerunning work.
Together with the recorded automated exit checks, this closes milestone 1C. Workstation-native
SSH-forward validation remains deferred, not passed.

Delivered in this slice:

- [x] Parse the optional manifest, honor valid aliases, preserve safe fallback aliases, and expose
  actionable invalid/unsupported integration without rejecting a generic Dune project.
- [x] Run compatible driver discovery through the existing root-serialized supervisor in the
  selected project environment, with bounded structured stdout, diagnostic stderr, cancellation,
  stable session identities, and typed project/job updates.
- [x] Reload manifest/discovery explicitly without daemon restart; repeat-open and reconnect remain
  cached and never repeat work. Failed refresh clears old summaries rather than presenting stale
  success.
- [x] Discover and display the external fixture's real counter target and default configuration,
  then expose the hierarchy produced by the same elaboration as its generated RTL.
- [x] Propagate initial and refreshed discovery results to the same attached client through ordered
  incremental project events, including failed-result invalidation, without reopening or routine
  full snapshots.
- [x] Select currently declared targets/configurations in each client, reconcile those selections
  across refresh, and reject stale or mismatched IDs both at submission and before execution.
- [x] Generate configuration-specific Verilog in the fixture's selected project environment through
  one supervised driver operation while retaining generic Dune fallback and cancellation behavior.
- [x] Import generated outputs all-or-nothing into private daemon-owned storage, publish immutable
  artifact identities before terminal job completion, and retrieve bounded content by ID without
  exposing storage paths.
- [x] Record target/configuration, generating job, environment, actual reported tool versions,
  Git context, dirty state, and deterministic source hashes captured at execution boundaries.
- [x] Import a bounded version-1 structural hierarchy sidecar atomically with RTL, preserve repeated
  instance occurrences with deterministic length-prefixed paths, retrieve it by artifact ID, and
  inspect its tree, node ports, metadata, and current/historical identity in the terminal.

Steps:

- [x] Define the initial schema/validation for optional `hardcaml-workbench.sexp`, beginning
  with `(lang hardcaml-workbench 1)`, project name, and Dune driver/build/test references
  from section 4.1. Keep it additive and small; do not reproduce Dune's graph. Add optional
  environment, FPGA-part, or default-target fields only after documenting their behavior.
- [x] Define the versioned driver describe/result contract, compatibility handling, target and
  configuration registration, session-scoped identity, framing/output limits, diagnostics,
  cancellation, and refresh. Generation and hierarchy contracts now include deterministic
  occurrence identity and versioned structured result retrieval; later-phase operations remain open.
- [x] Add a driver to the independent fixture, built and invoked through Dune in that
  project's compiler, package, and Hardcaml environment. Link circuit libraries only in
  the project driver; use typed library APIs there for discovery, elaboration, and Verilog
  generation. Any optional SDK helps implement this contract without owning circuits.
- [x] Discover registered targets/configurations through the driver, select one in the UI,
  and execute elaboration/RTL generation as daemon-supervised jobs. The project remains
  responsible for valid target constructors and configuration values.
- [x] Replace the labeled fixture hierarchy with driver-returned elaborated hierarchy as
  structured data; preserve instance identity for later reports and graphs.
- [x] Register RTL with project/root identity, target, configuration, generating job,
  tool versions, source identity/hash, commit where available, dirty state, and creation
  time. Represent unknown provenance for dirty or non-Git inputs honestly.
- [x] Retrieve artifact content through the daemon by ID; keep filesystem locations private.
  Handle invalid manifests, unsupported manifest/driver versions, missing drivers, invalid
  configurations, unavailable targets, and elaboration failures. Missing or incompatible
  optional integration must leave generic Dune operations usable.

**Exit demo:** demonstrate all three integration levels: a generic project with no manifest;
a manifest declaring aliases without a driver; and the external fixture with a compatible
driver. Discover/select its target, generate Verilog, inspect real hierarchy, and fetch the
artifact by ID with its generating job and provenance. Record that the driver uses the
project's selected environment and that ordinary project commands work without the
Workbench. Exercise missing/incompatible integration with generic build/test still usable.
Changing project, target, or configuration must not display previous results as current.

### 1D. Add the first structured hierarchical report

**Scope update (2026-09-20):** the active staged-report implementation and release
checks are D1–D4. The earlier gate below is retained as background; per-node report
mapping, a second backend and the full general ASIC integration track are
not prerequisites for the scaf dashboard.

**References:** [MVP checklist](hardcaml_workbench_architecture.md#20-suggested-mvp),
[metrics and checks](hardcaml_workbench_architecture.md#18-artifact-model),
[Xilinx reports integration](hardcaml_workbench_architecture.md#6-hardcaml_xilinx_reports),
[project-side operations](hardcaml_workbench_architecture.md#5-hardcaml-integration),
[batch invocation](hardcaml_workbench_architecture.md#101-level-1--batch-invocation).
**Depends on:** 1C, and one opened project with a working reporting path.

The gate is one structured hierarchical or staged report obtained through the opened project's
own reporting path, carrying provenance and mapped onto the design. Either path satisfies it:

| Path | Report source | Live prerequisite |
| --- | --- | --- |
| FPGA | `hardcaml_xilinx_reports` through the project driver | A usable Vivado installation |
| ASIC | The project's flow report, per A.2 | A provisioned flow environment and an emitted bundle |

Implement whichever path the first real opened project provides. Record which path closed the
gate and which remains pending; implementing the second one is not required to complete this
milestone.

Steps:

- [ ] Define the typed report operation on the driver contract independently of which tool
  answers it. Return structured results to the daemon with the metric representation from
  architecture section 18: unit, tool, stage, corner, and source report.
- [ ] For the FPGA path, integrate `hardcaml_xilinx_reports` through the project driver,
  preferring its library API when compatible with the project's Hardcaml version. If a project
  initially exposes only a CLI, invoke it through a native adapter behind the same typed
  operation and record the reason/follow-up.
- [ ] For the ASIC path, obtain the collected flow result through the project's own entry
  point per A.2, and preserve build and run identity rather than re-deriving it.
- [ ] Run report generation as supervised jobs using the initial batch flow; use project-owned
  target, clock, and constraint inputs and associate parent/child work and outputs with the
  selected project, target, and configuration. Supervision must cover the driver and its tool
  subprocesses, including cancellation and cleanup.
- [ ] Store structured results alongside raw reports and logs, and map results back to
  hierarchy instances.
- [ ] Display a metric table and a selected-node report inspector, including job status and
  explicit unavailable/failed results rather than misleading zero values. Keep stage
  completion, timing goals, and required verification checks visually distinct; an emitted
  build must not read as a completed run, and a completed run must not read as closure.
- [ ] Exercise report mapping and failures with fixtures, then validate a real run against its
  generated reports. Surface missing tools, licensing failures, unprovisioned environments,
  and invalid target or constraint configuration as actionable job failures.

**Phase 1 exit demo:** complete all ten MVP items in architecture section 20 on a real
Hardcaml target in an independent project: installed daemon and terminal client, project
opening, driver target discovery/selection, driver RTL generation, one structured hierarchical
or staged report, hierarchy, a metric table with units and analysis context, live logs, and
node inspection. Retain 1B's generic Dune workflow and 1C's compatibility/fallback checks. Run
from outside the Workbench checkout and verify the opened project remains usable through its
normal CLI. Canned report fixtures alone leave the live integration check pending for whichever
path was implemented. 1E is not required by this gate.

### 1E. Add the browser client and graphical views

**Status override (2026-09-20): Parked.** The prerequisite investigation below is
historical. No browser/toolchain repair or live browser validation is scheduled for
the active release.

**References:** [frontend choice](hardcaml_workbench_architecture.md#1-frontend-choice-and-delivery-order),
[shared application protocol](hardcaml_workbench_architecture.md#43-application-protocol-and-runtime-boundaries),
[UI layout](hardcaml_workbench_architecture.md#8-suggested-ui-layout),
[JavaScript prerequisite](development.md#javascript-toolchain-prerequisite).
**Depends on:** 1B for the typed client surface, and an aligned OxCaml/js_of_ocaml package pair
or an upstream compatibility fix. Not part of the MVP gate.

Steps:

- [ ] Promote the web target to JavaScript mode and require `web/main.bc.js` to build. Do not
  patch the shared opam switch ad hoc, and do not treat the bytecode target as evidence of
  this check.
- [ ] Package the compiled JavaScript, HTML, and CSS with the daemon, and extend the launcher
  to serve them from the daemon's loopback address and open a browser.
- [ ] Implement the project/hierarchy, jobs, console, and report views over the same typed
  requests the terminal client already uses. A type or request added for the browser client
  that the terminal client cannot use is a protocol design error, not a browser feature.
- [ ] Verify that two clients attached to one daemon observe the same projects, jobs, and
  artifacts, and that per-client selection and layout remain local to each client.

**Exit demo:** launch a job from the terminal client and observe it in the browser client, and
the reverse. Serve packaged assets from an installed daemon with no development asset server,
both locally and over a forwarded loopback port. The graphical views themselves arrive with the
Phase 3 milestones; this milestone delivers the client and the shared views.

Until this milestone is reactivated, record the browser client as parked, retaining
the prerequisite evidence for later revalidation. Do not describe the application
as shipping browser assets.

## 5. Phase 2 — Persistent tool workers and repeatable runs

### 2A. Build the persistent Tcl tool worker

**References:** [tool worker strategy](hardcaml_workbench_architecture.md#9-tool-worker-strategy),
[persistent subprocess](hardcaml_workbench_architecture.md#102-level-2--persistent-vivado-tcl-subprocess),
[transport order](hardcaml_workbench_architecture.md#12-socket-vs-persistent-stdinstdout),
[serialization](hardcaml_workbench_architecture.md#14-important-tclevent-loop-considerations),
[Vivado milestone](hardcaml_workbench_architecture.md#26-recommended-vivado-milestone).
**Depends on:** Phase 1 exit gate.

Steps:

- [ ] Start and own `vivado -mode tcl` in the daemon, with explicit session lifecycle and
  association to the opened project. Keep worker handles in native backend/adapter state.
- [ ] Name and structure the subsystem for its role rather than its first instance: worker
  mechanics (framing, serialization, timeouts, cancellation, restart, session invalidation)
  are tool-independent, while command vocabulary, report parsing, and result interpretation
  belong to each tool's adapter. Vivado is the first adapter; OpenROAD, which the ASIC flow
  already drives, is the plausible second. Do not generalize beyond one adapter speculatively,
  but do not put Vivado's vocabulary in the worker.
- [ ] Implement command IDs, completion/error framing, safe structured serialization, and
  stdout/stderr capture. Do not rely on the normal Tcl prompt as a completion boundary.
- [ ] Serialize commands through one executor per session; keep transport details behind
  the typed adapter interface.
- [ ] Define timeout, cancellation, process-death, shutdown, and restart behavior. A failed
  worker must settle affected jobs and expose invalidated session state.
- [ ] Test framing with fragmented/interleaved output and errors; validate live commands
  `version`, `pwd`, and `get_parts` before opening projects or running synthesis.

**Exit demo:** execute several typed requests in one real Vivado process, correlate each
result correctly, recover from a worker failure, and terminate/restart cleanly. Confirm the
worker mechanics contain no Vivado-specific command or report knowledge.

### 2B. Add synthesis, implementation, and structured reports

**References:** [structured API](hardcaml_workbench_architecture.md#15-structured-vivado-api),
[project model](hardcaml_workbench_architecture.md#41-project-model),
[tool worker strategy](hardcaml_workbench_architecture.md#9-tool-worker-strategy),
[Phase 2 scope](hardcaml_workbench_architecture.md#21-phase-2).
**Depends on:** 2A.

Steps:

- [ ] Add typed project/open-run, synthesis, implementation, timing, utilization, and
  checkpoint operations using the project/configuration model and existing job system.
- [ ] Connect driver-generated RTL artifacts and project-owned part/clock/constraint inputs
  to runs. Resolve artifact IDs and project-local paths in the daemon; register checkpoints,
  reports, and logs with project/run provenance and distinguish synthesis from implementation.
  Keep Vivado project/session state separate from the Workbench's opened Dune project model.
- [ ] Build timing-summary and utilization pages with explicit units and missing-data states.
- [ ] Validate structured results against raw Vivado output and exercise partial run failure.
- [ ] Provide an “Open in Vivado” action for native inspection, with a documented launch
  policy; sharing an already-running GUI session remains the optional 4C extension.

**Exit demo:** synthesize and implement a target from the independent fixture using its
generated RTL and constraints, inspect structured summaries and raw artifacts by ID, and
handle a failed run without replacing the last successful result. Switching opened projects
must not reuse another project's Vivado design state or display its results as current.

### 2C. Add RTL inspection and durable run history

**References:** [Phase 2 scope](hardcaml_workbench_architecture.md#21-phase-2),
[artifacts](hardcaml_workbench_architecture.md#18-artifact-model).
**Depends on:** 2B.

Steps:

- [ ] Add the generated RTL viewer using CodeMirror, bound to a selected project/run/artifact
  and fetching content from the daemon by artifact ID.
- [ ] Persist run records and artifact metadata; document storage, schema evolution, and
  restart behavior in the architecture before implementing the durable store.
- [ ] Browse previous runs with their inputs, status, logs, reports, and artifacts. Define
  how interrupted jobs are represented after daemon restart and how missing files appear.

**Phase 2 exit demo:** run the same target with two configurations, restart the daemon, and
recover the opened project and each run's RTL/reports with the correct provenance. Keep
history distinct across independent project roots and show missing/unavailable files
explicitly. Persistent Vivado work and the report pages from 2A–2B must also pass their
exit checks; history recovery does not require preserving a live Vivado process on restart.

## 6. Phase 3 — Design exploration and comparison

### 3A. Build the elaboration graph explorer

**References:** [visualization model](hardcaml_workbench_architecture.md#7-rtl--elaboration-visualization),
[project-side Hardcaml APIs](hardcaml_workbench_architecture.md#5-hardcaml-integration),
[portable protocol](hardcaml_workbench_architecture.md#43-application-protocol-and-runtime-boundaries).
**Depends on:** Phase 2 exit gate; project-driver contract and hierarchy identity from 1C.

Steps:

- [ ] Extend the project driver to traverse its Hardcaml circuit and return a versioned graph
  representation: hierarchy, instances, signals, operators, registers, memories, and
  available clock/reset information. Pass portable graph data through the daemon to Bonsai;
  keep project circuit modules in the driver and avoid reconstructing them from Verilog.
- [ ] Add hierarchical rendering, expand/collapse, node inspection, signal search, and
  fan-in/fan-out tracing. Link to source where source metadata is available.
- [ ] Validate graph connectivity and identity against known circuits. Select a representative
  larger target and record interaction/performance criteria before optimizing rendering.

**Exit demo:** navigate from top-level blocks to internal logic, find a signal, trace its
connections, and retain consistent selection between hierarchy and graph views. Verify
the graph against the independent fixture's circuit and handle unavailable graph support
from a driver without breaking its existing operations.

### 3B. Add typed project simulation and waveform inspection

**References:** [Hardcaml services](hardcaml_workbench_architecture.md#5-hardcaml-integration),
[job categories](hardcaml_workbench_architecture.md#42-job-system),
[Phase 3 scope](hardcaml_workbench_architecture.md#22-phase-3).
**Depends on:** Phase 2 exit gate; 1C's driver integration and 1B's Dune test jobs;
can proceed independently of 3A.

Steps:

- [ ] Extend the versioned driver contract for target-specific simulation/test entry points.
  Use direct Hardcaml simulation APIs inside the project driver and daemon-owned jobs for
  execution. Retain generic Dune test aliases and existing project commands from 1B.
- [ ] Store waveform and test-result artifacts with target/run provenance.
- [ ] Add a waveform viewer with signal selection and time navigation; surface failing tests
  and simulation errors in the existing jobs/logs workflow.
- [ ] Define external simulator adapter boundaries. Schedule Verilator or other engines as
  follow-up tasks when a concrete target needs them; they are not prerequisites for this gate.

**Exit demo:** execute a deterministic simulation and a failing test, inspect their results,
and open a waveform by artifact ID whose signal values match the known test stimulus.
Verify execution in the external project's environment and direct CLI use without the UI;
generic Dune tests remain available for projects without simulation integration.

### 3C. Add timing/resource overlays and design comparison

**References:** [graph interactions](hardcaml_workbench_architecture.md#7-rtl--elaboration-visualization),
[comparison](hardcaml_workbench_architecture.md#19-design-comparison).
**Depends on:** 3A, 3B, and Phase 2 reports/history.

Steps:

- [ ] Map resource estimates and timing paths onto hierarchy/graph entities. Document how
  synthesized names relate to elaborated identities and show unmapped paths explicitly.
- [ ] Add resource and critical-path overlays with drilldown to supporting report data.
- [ ] Compare stored runs by project/source/configuration, part, clock target, and tool settings;
  display baseline, current, and deltas with units and comparability context.
- [ ] Show unavailable metrics honestly. Add latency comparisons only when the target supplies
  a defined measurement; do not infer latency from utilization or timing reports.

**Phase 3 exit demo:** inspect a known timing path on the design, open the corresponding
waveform workflow, and compare two runs with verified resource/timing deltas. Exercise
unmapped entities and missing or incompatible metrics.

## 7. Phase 4 — Hardware and extended access

### 4A. Discover hardware and program a device

**References:** [hardware manager](hardcaml_workbench_architecture.md#17-hardware-manager-integration),
[Phase 4 scope](hardcaml_workbench_architecture.md#23-phase-4).
**Depends on:** Phase 3 exit gate in the default roadmap; technically uses 2A–2C.

Steps:

- [ ] Add bitstream generation and registration from an implemented run, retaining the
  independent project's target, part, constraints, and source provenance.
- [ ] Add typed hardware-server connection, target/device discovery, and status operations.
- [ ] Build the Hardware page with explicit target/device and bitstream selection, then
  implement programming as a job with logs and artifact provenance.
- [ ] Validate disconnection, missing device, and programming failure, followed by a real
  programming check on a supported board.

**Exit demo:** identify the intended device, program the selected run's bitstream, and inspect
the job outcome. Hardware fixtures support development but do not complete the board check.

### 4B. Integrate ILA capture

**References:** [hardware debugging](hardcaml_workbench_architecture.md#17-hardware-manager-integration).
**Depends on:** 4A and the waveform workflow from 3B.

Steps:

- [ ] Discover ILA cores and implement typed configure/arm/trigger/capture operations.
- [ ] Record capture artifacts with device, bitstream, probe configuration, and run provenance.
- [ ] Connect capture results to waveform inspection and handle timeouts/disconnections.

**Exit demo:** capture a known signal on hardware and inspect the trace with enough metadata
to identify the programmed design and capture setup.

### 4C. Optionally attach to an open Vivado GUI

**References:** [socket bridge](hardcaml_workbench_architecture.md#11-vivado-tcl-socket-server),
[GUI session](hardcaml_workbench_architecture.md#13-particularly-interesting-case-controlling-an-open-vivado-gui),
[event loop](hardcaml_workbench_architecture.md#14-important-tclevent-loop-considerations).
**Depends on:** Phase 3 exit gate in the default roadmap; reuses 2A's typed worker interface.

Steps:

- [ ] Define session ownership, connection/authentication, event-loop handling, and state
  refresh after manual GUI actions in the architecture.
- [ ] Add a Tcl socket transport behind the existing adapter, preserving serialized execution.
- [ ] Bootstrap GUI-mode Vivado and support attach, disconnect, reconnect, and stale-session
  detection without embedding the GUI in the browser.

**Exit demo:** make a manual GUI change, refresh the workbench's view, and execute a typed
workbench action in that same session. Verify disconnect behavior.

### 4D. Add distributed remote build workers

**References:** [Phase 4 scope](hardcaml_workbench_architecture.md#23-phase-4),
[deployment modes](hardcaml_workbench_architecture.md#44-deployment-and-client-attachment),
[project/runtime boundary](hardcaml_workbench_architecture.md#3-recommended-high-level-architecture),
[transport considerations](hardcaml_workbench_architecture.md#12-socket-vs-persistent-stdinstdout).
**Depends on:** Phase 3 exit gate in the default roadmap; reuses 1B–1C's project/environment
and driver contracts plus job supervision, artifact access, and history.

This milestone is the distributed-worker mode only: a local daemon dispatching jobs to remote
build machines. It is not how a user works against a remote machine in general. The attached
mode, where the daemon runs beside the project and its toolchain and clients connect over an
SSH port forward, is available from 1B and carries none of this milestone's cost. Prefer it,
and implement 4D only when work genuinely must be dispatched to a machine that does not hold
the project.

Steps:

- [ ] Define remote execution ownership, authentication, workspace/source transfer, tool
  discovery, artifact retrieval, and disconnect/recovery semantics in the architecture.
  Preserve independent project ownership and build the driver in the remote project's
  compiler/package environment; report driver compatibility and source identity explicitly.
- [ ] Implement remote job dispatch and status/log/artifact delivery through existing models.
  Keep remote paths/processes behind backend contracts and browser artifact access by ID.
- [ ] Validate source identity across machines and recovery without unintentionally executing
  a submitted job twice.

**Exit demo:** run a build on another machine, inspect its logs and artifacts locally, and
recover from a connection interruption with a correct final job state. Exercise a typed
driver operation in the remote project environment as well as generic Dune execution;
neither requires the project's hardware modules to be linked into the Workbench.

**Phase 4 exit:** 4A, 4B, and 4D pass their live checks; record whether each optional extension
was completed or deferred. Do not imply that untested hardware or remote flows are complete.
The terminal frontend moved to 1A/1B and the browser frontend to 1E; neither is a Phase 4
milestone any longer.

## 8. Decisions to resolve at the point of need

The standalone application, independent-project ownership, three integration levels,
project-side typed Hardcaml calls, native/frontend separation, terminal-first frontend order,
backend neutrality of the shared schemas, and loopback-only daemon binding are already
established. The table records decisions at each milestone; the 1A rows are resolved in sections 4.3
and 24 as of 2026-09-19, while later rows remain to close during implementation; it does not reopen those boundaries.

| Before implementation of | Decision to record in the architecture | Relevant section |
| --- | --- | --- |
| 1A | Application RPC transport/serialization, launcher and installation, and concrete Dune library/dependency layout within established runtime roles | 3, 4.3, 24 |
| 1A | Concrete backend-neutral schema shapes: extensible target facts, the artifact-kind namespace and role vocabulary, optional build/run references, and the metric representation with unit, tool, stage, corner, and source | 4.1, 4.2, 18 |
| 1B | Root validation, project environment selection, supported Dune inspection/commands/RPC, and project/job/log snapshot and reconnect semantics | 4.1–4.3, 25 |
| 1B | Which session state is daemon-owned and shared versus per-client, the single owner of cancellation with multiple clients attached, and the client's connection/reattach behavior against a forwarded loopback address | 4.3, 4.4 |
| 1C | Initial manifest schema/defaults, driver protocol operations/versions and compatibility errors, target/configuration validation, hierarchy identity, artifact registration/access, and source provenance; whether an SDK is useful | 4.1, 4.3, 5, 18, 24 |
| A.2–A.3 | ASIC driver capabilities/results, target summaries without FPGA-only assumptions, immutable build/execution identity mapping, one execution/cancellation owner, and supported views | 4.1, 18 |
| A.2–A.3 | Stage requested-versus-completed representation, per-corner metric grouping, physical/submission check results, and execution environment identity in provenance | 4.2, 18 |
| 1D | The typed report operation and result mapping independently of which tool answers it; then, for whichever path closes the gate, supported project/report-library and tool versions and fixture target/constraint inputs, or a justified existing CLI fallback | 5, 6, 10.1, 18 |
| 1E | Browser asset packaging and serving from the daemon's loopback address, and the resolution or pinning of the OxCaml/js_of_ocaml compatibility prerequisite | 3, 4.3, 24 |
| 2A | Framing, command serialization, timeout/cancellation, worker restart, and session invalidation | 10.2, 14, 15, 26 |
| 2C | Durable storage, artifact paths, schema evolution, and interrupted-run recovery | 18, 21 |
| 3A–3C | Versioned driver graph/simulation extensions, graph identity/scale, waveform format, timing-name mapping, and comparison compatibility | 4.3, 5, 7, 19, 22 |
| 4A–4B | Supported hardware, device/bitstream association, and ILA capture configuration | 17, 23 |
| 4C–4D | Connection trust, session ownership, remote transport and project environment, source/artifact transfer, and recovery. The attached deployment mode is already settled in 4.4; these decisions concern the distributed-worker mode only | 3, 4.1, 4.4, 11–14, 23 |

## 9. Completion and progress tracking

A milestone is complete when its deliverables exist, its exit demo passes, relevant failure
paths are checked, and documentation reflects any design decisions made during construction.
Use small implementation tasks within each milestone; keep enough end-to-end wiring in each
to demonstrate the behavior through the workbench.

For future Workbench code changes, use the repository switch wrapper:

```sh
./scripts/with-switch.sh dune build @fmt
./scripts/with-switch.sh dune build @lint
./scripts/with-switch.sh dune runtest
./scripts/with-switch.sh dune build
```

Those commands validate the Workbench build environment, not every opened project's
toolchain. Run independent fixture build/test and driver commands in the fixture's selected
environment and external root; record both application and project toolchain versions.

Add focused checks for job lifecycle, manifest/driver compatibility, adapter parsing,
provenance, artifact retrieval by ID, and generic Dune fallback as those components appear.
Check installation outside the checkout and native/browser dependencies. Visually verify
UI workflows and reconnect recovery. Keep fixture tests usable without Vivado or hardware,
and record live validation separately with project root, tool versions, target/configuration,
commands, and outcome. An unavailable prerequisite is a pending check.

Use **Not started**, **In progress**, **Blocked**, **Complete**, **Re-scoped**, or
**Deferred / Parked**. Re-scoped items point to their replacement acceptance checks;
they do not claim completion.
When blocked, record the concrete blocker and the next action. When complete, link the
implementation and validation evidence; a checked task list alone is insufficient.

| Milestone | Status | Implementation / validation evidence or blocker |
| --- | --- | --- |
| D1 — Real scaf project and existing result | Not started | Active release; project CLI/records inspected for scope, live Workbench integration not yet validated. |
| D2 — Launch and observe scaf flow | Not started | Active release; live structured stage/substep evidence needs an explicit project-side contract. |
| D3 — Persistent timing/results dashboard | Not started | Active release; dedicated timing, stage/check boxes, area/utilization, identity and logs. |
| D4 — Daily-use validation / release gate | Not started | Active release; real flow and SSH/tmux checks required. |
| 1A — Installed application foundation | Complete | Completed 2026-09-20. `protocol/V1`, `native_http/`, `daemon/rpc_server.ml`, the installed daemon/client, runtime discovery/locking, and the isolated counter fixture implement the recorded design. `scripts/test-native-application.sh` passed installed typed exchange from outside the checkout, concurrent startup, stale discovery, client exit/reattach, explicit endpoint failure without replacement, and shutdown. `FIXTURE_OPAM_SWITCH=5.2.0+ox ./scripts/test-fixture.sh` built and tested the copied external fixture. Codec/RPC tests cover malformed requests, unsupported versions, instance and cursor errors, timeout heartbeat, limits, and HTTP trust checks. `dune describe external-lib-deps` confirms the terminal has no backend/adapter/project-integration path. Native package build/install, opam lint, format, lint, tests, and default build pass; exact commands are in [development notes](development.md#milestone-1a-installed-native-foundation). Browser validation remains separately tracked in 1E and is not claimed by this milestone. |
| 1B — Generic Dune projects, jobs, and terminal client | Complete | Completed 2026-09-20 under the recorded acceptance scope adjustment. Protocol/RPC, adapter, supervisor, file-backed logs, installed external-fixture workflow, and PTY resize checks pass. The user confirmed repeated resizing while navigating, visible generic Dune workspace information, explicit unavailable hierarchy, build/test completion, per-job logs including repeated no-output jobs, diagnostics toggling, and state recovery after exit/relaunch in the intended server-side TUI over ordinary SSH. The UI follow-up makes state plus process outcome primary, distinguishes empty logs through known EOF, bounds verbose connection diagnostics behind `d`, middle-truncates the default root, and exposes complete wrapped diagnostic fields with `[`/`]` scrolling. This human evidence does not claim every terminal/tmux combination or crossing the small-terminal threshold. A workstation-native client through an SSH-forwarded HTTP endpoint is explicitly deferred by the user, not passed; commands remain in the development notes. |
| 1C — Versioned manifest/driver, RTL, and hierarchy | Complete | All three implementation slices pass automated validation on 2026-09-20. The final slice exports genuine Hardcaml instance occurrences from the same elaboration as RTL, imports hierarchy and RTL atomically, preserves deterministic structural keys, retrieves structured results by hierarchy artifact ID, and provides terminal tree/navigation/inspection with exact current-versus-historical labeling. Tests cover malformed/disconnected/cyclic/deep/oversized trees, duplicate identities and ports, repeated instances, configuration-specific widths, unsupported drivers, capability changes during an in-flight generation, cancellation at the registration commit boundary, event ordering, reconnect, collapse/expansion, compact scrolling, and resize. Direct fixture and installed outside-checkout workflows pass. Discovery, RTL/artifact, and final hierarchy human checklists are accepted. The user confirmed live hierarchy, repeated-child identity, four/eight-bit widths, navigation, collapse/expansion, scrolling, resize, historical labeling, and reconnect without rerunning work. Exact commands and acceptance evidence are in the development notes; workstation-native SSH-forward validation remains deferred. |
| 1D — First structured hierarchical report / former MVP gate | Re-scoped | D1–D4 own the active staged-report release; per-node report mapping is deferred. |
| 1E — Browser client and graphical views | Parked | Historical JS/toolchain blockers and subsequent probes remain in development notes. Revalidate only when browser work is reactivated. |
| A.1 — Open an ASIC consumer as an ordinary project | Re-scoped | D1 selects the real scaf consumer; integration validation remains open. |
| A.2 — ASIC build and execution artifacts | Re-scoped | D1–D3 deliver the minimal scaf path; general resumability/framework work is deferred. |
| A.3 — Reuse supported inspection views for ASIC | Re-scoped | D3 supplies the first dashboard; broader inspection is parked. |
| 2A — Persistent Tcl tool worker | Parked | Requires a concrete vendor-tool workflow. |
| 2B — Synthesis, implementation, reports | Parked | Existing project batch flow is the active path. |
| 2C — RTL viewer and history / Phase 2 gate | Parked | D1/D4 reopen project-owned results; general history and CodeMirror deferred. |
| 3A — Elaboration graph | Parked | — |
| 3B — Typed project simulation and waveforms | Parked | Existing project simulation results can appear in D3 without this subsystem. |
| 3C — Overlays and comparison / Phase 3 gate | Parked | — |
| 4A — Hardware programming | Parked | — |
| 4B — ILA capture | Parked | — |
| 4C — GUI socket bridge (optional) | Parked | — |
| 4D — Distributed remote workers | Parked | — |

1C's delivered hierarchy implementation and completed human acceptance evidence are retained
above. D4 still owns the active release's real-terminal dashboard check; hierarchy acceptance
does not establish that separate workflow.

**Next construction task:** D1 — open `../scaf/`, validate its ordinary build/test
workflow, and expose one explicitly selected existing physical result through the
smallest project-owned adapter. Then D2 adds launch/progress, D3 makes timing and
stage/check outcomes permanently visible, and D4 validates daily use. No parked
milestone is a prerequisite for this sequence.
