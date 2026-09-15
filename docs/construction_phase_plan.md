# Hardcaml Workbench Construction Phase Plan

## 1. Purpose and document authority

Turn the [project idea and philosophy](project_idea_and_philosophy.md) and
[architecture](hardcaml_workbench_architecture.md) into an ordered construction backlog with
demonstrable milestones. The philosophy defines product intent and ownership boundaries;
the architecture remains the main source of truth for system design and scope. This plan
owns implementation order, dependencies, acceptance checks, and progress.

- Preserve the architecture's four phases. Milestone IDs such as **1A** subdivide those
  phases; they do not introduce a competing roadmap.
- Read each milestone's architecture references before implementing it. The steps below
  are implementation guidance, not replacement interface or protocol specifications.
- When implementation reveals a new architectural decision or a conflict, update the
  relevant architecture section first, then revise this plan and the affected code.
- Keep durable design decisions in the architecture. Keep milestone status and completion
  evidence here. Follow the [formatting guide](formatting_guide.md) for coding conventions.
- Treat later-phase details as a planning baseline. Refine their tasks when prerequisites
  are demonstrated, while retaining the scope established by the architecture.

Apply these established boundaries throughout construction:

- Ship a standalone installed application: a native OCaml daemon plus precompiled HTML,
  JavaScript, and CSS assets from the Bonsai frontend, launched as one local application.
- Open independent Dune/Hardcaml repositories by root. Projects own hardware source,
  libraries, target constructors, configurations, tests, constraints, and CLI entry points.
  The Workbench owns project sessions, jobs, artifacts, processes, and tool adapters.
- Support integration progressively: generic Dune operations without Workbench files;
  an optional versioned `hardcaml-workbench.sexp`; and a versioned project-side driver
  built in the opened project's compiler/package environment for typed Hardcaml operations.
- Compile the shared typed application protocol for native OCaml and JavaScript. Keep
  native backend/adapter dependencies and operating-system resources out of browser code
  and portable protocol types. The daemon resolves artifact IDs to private storage paths.
- Keep synthesizable circuits in independent projects, including a small integration fixture.
  Internal application libraries and an optional project-integration SDK do not constitute
  a production hardware library. Do not dynamically load project modules into the daemon.

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
All milestones below begin as **Not started**. Existing unrelated working-tree changes are
outside this documentation task.

## 3. Roadmap and dependencies

| Architecture phase | Construction milestones | Phase exit outcome |
| --- | --- | --- |
| [Phase 1: MVP](hardcaml_workbench_architecture.md#20-suggested-mvp) | 1A installed application foundation; 1B generic Dune projects, jobs, and UI; 1C manifest/driver integration; 1D hierarchical reports | Launch the installed application, open an independent project, select a driver-discovered target, generate RTL, and inspect hierarchical reports with live logs. |
| [Phase 2](hardcaml_workbench_architecture.md#21-phase-2) | 2A persistent Vivado; 2B synthesis/implementation and reports; 2C RTL viewer and history | Run and revisit synthesis/implementation work through a persistent, typed Vivado integration. |
| [Phase 3](hardcaml_workbench_architecture.md#22-phase-3) | 3A elaboration graph; 3B simulation/waveforms; 3C overlays and comparison | Explore circuit structure and behavior, relate timing to the design, and compare iterations. |
| [Phase 4](hardcaml_workbench_architecture.md#23-phase-4) | 4A hardware programming; 4B ILA; 4C optional GUI bridge; 4D remote workers; 4E optional terminal UI | Deploy/debug hardware and extend access to remote tools and optional frontends. |

Default order:

```text
1A -> 1B -> 1C -> 1D [MVP gate]
                    |
                    v
2A -> 2B -> 2C [Phase 2 gate]
             |
             +-> 3A --+
             +-> 3B --+-> 3C [Phase 3 gate]
                          |
                          +-> 4A -> 4B
                          +-> 4C (optional)
                          +-> 4D
                          +-> 4E (optional)
```

The existing subdivision is retained. 1A establishes the installed runtime and an independent
fixture; 1B adds generic project opening through Dune and the supervised-job UI required by
architecture section 25. 1C builds manifest/driver integration on that project and job
foundation; 1D uses the driver boundary for reports before Phase 2 adds persistent Vivado.
Generic Dune build/test support is delivered in 1B; Phase 3 adds typed project simulation.

3A and 3B extend the project-driver integration from 1C and can be built independently after
Phase 2. In Phase 4, 4B depends on 4A; 4C, 4D, and 4E are separate extensions.
Remote support does not inherently require a Vivado
socket bridge: select and document its transport when defining that milestone. Optional
extensions are recorded as deferred if they are not selected, rather than marked complete.

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
- [ ] Implement the initial project, target, job, and artifact types needed by 1B–1D, derived
  from architecture sections 4 and 18. Represent external roots and integration availability;
  generic projects need not have Hardcaml targets. Keep native resources private and expose
  artifact IDs/metadata for daemon-mediated retrieval.
- [ ] Define the first typed request/response and incremental update contracts. Resolve the
  application RPC transport and serialization choice in the architecture before wiring the
  client. Compile shared definitions for both native OCaml and JavaScript; browser code
  depends on the shared protocol, not native backend or adapter libraries.
- [ ] Package the native daemon, compiled Bonsai JavaScript, HTML, and CSS. Provide a launcher
  that starts local serving and opens the browser, with a project-root argument for 1B.
  Document both the development startup workflow and the installed application workflow.
- [ ] Add a deterministic miniature Dune/Hardcaml project under test fixtures. Exercise it
  from an external temporary root with its own `dune-project`, build/test entry points,
  and environment; do not link its circuit modules into Workbench application libraries
  or absorb it into the Workbench Dune workspace. It needs no manifest/driver until 1C.

**Exit check:** build and install into a test prefix, then launch outside the Workbench
checkout. The installed daemon serves packaged frontend assets and the browser obtains a
typed response without a development asset server. Confirm native/browser dependency
separation and ordinary fixture build/test commands in its separate root. Record exact
commands; this establishes the foundation for section 25's first implementation milestone.

### 1B. Open generic Dune projects and deliver the first job workflow

**References:** [first implementation task](hardcaml_workbench_architecture.md#25-first-implementation-task-for-codex),
[project integration levels](hardcaml_workbench_architecture.md#41-project-model),
[jobs](hardcaml_workbench_architecture.md#42-job-system),
[runtime boundaries](hardcaml_workbench_architecture.md#43-application-protocol-and-runtime-boundaries),
[UI layout](hardcaml_workbench_architecture.md#8-suggested-ui-layout).
**Depends on:** 1A.

Steps:

- [ ] Open a user-selected independent root containing `dune-project`; validate the root,
  create a daemon-owned project session, and resolve project-local paths against it.
  Define how the project's execution environment is selected and reported; do not silently
  substitute the Workbench build switch for the project's environment.
- [ ] Use supported Dune inspection commands/RPC through a native Dune adapter for generic
  workspace information and normal build/test actions without a manifest or driver.
  Keep Dune authoritative for the build graph; generic inspection does not infer hardware
  top-level constructors, valid parameter sets, clocks, or parts.
- [ ] Implement daemon-owned process supervision and the job lifecycle, including exit
  status, failures, cancellation, timestamps, and stdout/stderr capture.
- [ ] Expose job submission, state retrieval, and incremental log/status updates through RPC.
  Reconnecting a browser should recover current daemon state without launching the job again.
- [ ] Build the project/hierarchy pane, jobs table, and console/log pane in Bonsai. Show
  real generic project information and a clearly labeled fixture hierarchy until 1C
  supplies elaborated hierarchy; present unavailable Hardcaml actions explicitly.
- [ ] Wire project build/test requests through the typed API, Dune adapter, and supervisor
  to visible completion. At least one is the supervised backend action in section 25.
  Adapters derive tool invocations; the daemon supervisor owns processes; UI sends typed
  requests rather than constructing commands.
- [ ] Verify success, nonzero exit, launch failure, cancellation, and daemon shutdown behavior
  with small local commands; ensure supervised child processes are cleaned up.

**Exit demo:** use the installed application to open the external fixture without any
Workbench-specific files, inspect Dune-derived information, and run build/test actions in
its environment with output visible before completion. Exercise failure and cancellation,
then reconnect during a job and recover the project, job, and logs without resubmission.
Verify that the fixture still builds/tests directly from the terminal and that no fixture
modules link into the application. This completes section 25's first milestone.

### 1C. Add the versioned manifest and project driver for real RTL

**References:** [project model](hardcaml_workbench_architecture.md#41-project-model),
[Hardcaml integration](hardcaml_workbench_architecture.md#5-hardcaml-integration),
[runtime protocol](hardcaml_workbench_architecture.md#43-application-protocol-and-runtime-boundaries),
[progressive integration](project_idea_and_philosophy.md#4-progressive-project-integration),
[artifact model](hardcaml_workbench_architecture.md#18-artifact-model).
**Depends on:** 1B.

Steps:

- [ ] Define the initial schema/validation for optional `hardcaml-workbench.sexp`, beginning
  with `(lang hardcaml-workbench 1)`, project name, and Dune driver/build/test references
  from section 4.1. Keep it additive and small; do not reproduce Dune's graph. Add optional
  environment, FPGA-part, or default-target fields only after documenting their behavior.
- [ ] Define the versioned driver request/result contract, compatibility handling, target
  registration, configuration validation, and hierarchy identity. Keep this process
  protocol distinct from the browser/daemon API, with portable results mapped by the adapter.
- [ ] Add a driver to the independent fixture, built and invoked through Dune in that
  project's compiler, package, and Hardcaml environment. Link circuit libraries only in
  the project driver; use typed library APIs there for discovery, elaboration, and Verilog
  generation. Any optional SDK helps implement this contract without owning circuits.
- [ ] Discover registered targets/configurations through the driver, select one in the UI,
  and execute elaboration/RTL generation as daemon-supervised jobs. The project remains
  responsible for valid target constructors and configuration values.
- [ ] Replace the labeled fixture hierarchy with driver-returned elaborated hierarchy as
  structured data; preserve instance identity for later reports and graphs.
- [ ] Register RTL with project/root identity, target, configuration, generating job,
  tool versions, source identity/hash, commit where available, dirty state, and creation
  time. Represent unknown provenance for dirty or non-Git inputs honestly.
- [ ] Retrieve artifact content through the daemon by ID; keep filesystem locations private.
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

### 1D. Add hierarchical timing and utilization reports

**References:** [Xilinx reports integration](hardcaml_workbench_architecture.md#6-hardcaml_xilinx_reports),
[project-side operations](hardcaml_workbench_architecture.md#5-hardcaml-integration),
[batch invocation](hardcaml_workbench_architecture.md#101-level-1--batch-invocation),
[MVP checklist](hardcaml_workbench_architecture.md#20-suggested-mvp).
**Depends on:** 1C; a usable Vivado installation for live integration validation.

Steps:

- [ ] Integrate `hardcaml_xilinx_reports` through the project driver, preferring its library
  API when compatible with the project's Hardcaml version. Return structured results to
  the daemon. If a project initially exposes only a CLI, invoke it through a native adapter
  behind the same typed operation and record the reason/follow-up.
- [ ] Run hierarchical report generation as supervised jobs using the initial batch flow;
  use project-owned part/clock/constraint inputs and associate parent/child work and outputs
  with the selected project, target, and configuration. Supervision must cover the driver
  and its tool subprocesses, including cancellation and cleanup.
- [ ] Store structured timing/utilization results alongside raw reports and logs, and map
  results back to hierarchy instances.
- [ ] Display a resource/timing table and a selected-node report inspector, including job
  status and explicit unavailable/failed results rather than misleading zero values.
- [ ] Exercise report mapping and failures with fixtures, then validate a real run against
  its generated reports. Surface missing tools, licensing failures, and invalid part or
  constraint configuration as actionable job failures.

**Phase 1 exit demo:** complete all ten MVP items in architecture section 20 on a real
Hardcaml target in an independent project: installed daemon/frontend, project opening,
driver target discovery/selection, driver Verilog generation, hierarchical reports,
hierarchy, resource/timing table, live logs, and node inspection. Retain 1B's generic Dune
workflow and 1C's compatibility/fallback checks. Run from outside the Workbench checkout
and verify the opened project remains usable through its normal CLI. Canned report
fixtures alone leave the live Vivado integration check pending.

## 5. Phase 2 — Persistent Vivado and repeatable runs

### 2A. Build the persistent Vivado worker

**References:** [persistent subprocess](hardcaml_workbench_architecture.md#102-level-2--persistent-vivado-tcl-subprocess),
[transport order](hardcaml_workbench_architecture.md#12-socket-vs-persistent-stdinstdout),
[serialization](hardcaml_workbench_architecture.md#14-important-tclevent-loop-considerations),
[Vivado milestone](hardcaml_workbench_architecture.md#26-recommended-vivado-milestone).
**Depends on:** Phase 1 exit gate.

Steps:

- [ ] Start and own `vivado -mode tcl` in the daemon, with explicit session lifecycle and
  association to the opened project. Keep worker handles in native backend/adapter state.
- [ ] Implement command IDs, completion/error framing, safe structured serialization, and
  stdout/stderr capture. Do not rely on the normal Tcl prompt as a completion boundary.
- [ ] Serialize commands through one executor per session; keep transport details behind
  the typed adapter interface.
- [ ] Define timeout, cancellation, process-death, shutdown, and restart behavior. A failed
  worker must settle affected jobs and expose invalidated session state.
- [ ] Test framing with fragmented/interleaved output and errors; validate live commands
  `version`, `pwd`, and `get_parts` before opening projects or running synthesis.

**Exit demo:** execute several typed requests in one real Vivado process, correlate each
result correctly, recover from a worker failure, and terminate/restart cleanly.

### 2B. Add synthesis, implementation, and structured reports

**References:** [structured API](hardcaml_workbench_architecture.md#15-structured-vivado-api),
[project model](hardcaml_workbench_architecture.md#41-project-model),
[Vivado strategy](hardcaml_workbench_architecture.md#9-vivado-integration-strategy),
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

### 4D. Add remote build-machine support

**References:** [Phase 4 scope](hardcaml_workbench_architecture.md#23-phase-4),
[project/runtime boundary](hardcaml_workbench_architecture.md#3-recommended-high-level-architecture),
[transport considerations](hardcaml_workbench_architecture.md#12-socket-vs-persistent-stdinstdout).
**Depends on:** Phase 3 exit gate in the default roadmap; reuses 1B–1C's project/environment
and driver contracts plus job supervision, artifact access, and history.

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

### 4E. Optionally add a Bonsai Term frontend

**References:** [frontend choice](hardcaml_workbench_architecture.md#1-primary-ui-choice),
[shared application protocol](hardcaml_workbench_architecture.md#43-application-protocol-and-runtime-boundaries),
[Phase 4 scope](hardcaml_workbench_architecture.md#23-phase-4).
**Depends on:** Phase 3 exit gate in the default roadmap; uses existing daemon/RPC services.

Steps:

- [ ] Select a focused terminal workflow: project/target selection, job launch, status, logs,
  and report summaries.
- [ ] Implement it over the shared typed application protocol with daemon-owned projects,
  jobs, artifacts, and tool execution.

**Exit demo:** launch and inspect a job in the terminal and observe the same state in the web
frontend. Graphical feature parity is not required by this optional milestone.

**Phase 4 exit:** 4A, 4B, and 4D pass their live checks; record whether each optional extension
was completed or deferred. Do not imply that untested hardware or remote flows are complete.

## 8. Decisions to resolve at the point of need

The standalone application, independent-project ownership, three integration levels,
project-side typed Hardcaml calls, and native/browser separation are already established.
The table records remaining details to close in the architecture when implementing each
milestone; it does not reopen those boundaries.

| Before implementation of | Decision to record in the architecture | Relevant section |
| --- | --- | --- |
| 1A | Application RPC transport/serialization, initial portable schemas, launcher/asset installation and serving, and concrete Dune library/dependency layout within established runtime roles | 3, 4.3, 24 |
| 1B | Root validation, project environment selection, supported Dune inspection/commands/RPC, and project/job/log snapshot and reconnect semantics | 4.1–4.3, 25 |
| 1C | Initial manifest schema/defaults, driver protocol operations/versions and compatibility errors, target/configuration validation, hierarchy identity, artifact registration/access, and source provenance; whether an SDK is useful | 4.1, 4.3, 5, 18, 24 |
| 1D | Supported project/report-library and Vivado versions, fixture FPGA part/constraints, and driver report operation/result mapping or justified existing CLI fallback | 5, 6, 10.1 |
| 2A | Framing, command serialization, timeout/cancellation, worker restart, and session invalidation | 10.2, 14, 15, 26 |
| 2C | Durable storage, artifact paths, schema evolution, and interrupted-run recovery | 18, 21 |
| 3A–3C | Versioned driver graph/simulation extensions, graph identity/scale, waveform format, timing-name mapping, and comparison compatibility | 4.3, 5, 7, 19, 22 |
| 4A–4B | Supported hardware, device/bitstream association, and ILA capture configuration | 17, 23 |
| 4C–4D | Connection trust, session ownership, remote transport and project environment, source/artifact transfer, and recovery | 3, 4.1, 11–14, 23 |

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

Use **Not started**, **In progress**, **Blocked**, **Complete**, or **Deferred (optional)**.
When blocked, record the concrete blocker and the next action. When complete, link the
implementation and validation evidence; a checked task list alone is insufficient.

| Milestone | Status | Implementation / validation evidence or blocker |
| --- | --- | --- |
| 1A — Installed application foundation | In progress | [Development baseline](development.md#baseline-recorded-for-milestone-1a) and [application packaging foundation](development.md#application-packaging-foundation): toolchain/dependency audit, passing repository checks, application-role Dune targets, and native/browser dependency separation recorded 2026-09-14. JavaScript promotion remains pending on the documented OxCaml/js_of_ocaml compatibility prerequisite; no application startup command exists until the remaining 1A runtime/installation work is implemented. |
| 1B — Generic Dune projects, jobs, and UI | Not started | — |
| 1C — Versioned manifest/driver and RTL | Not started | — |
| 1D — Hierarchical reports / MVP gate | Not started | — |
| 2A — Persistent Vivado worker | Not started | — |
| 2B — Synthesis, implementation, reports | Not started | — |
| 2C — RTL viewer and history / Phase 2 gate | Not started | — |
| 3A — Elaboration graph | Not started | — |
| 3B — Typed project simulation and waveforms | Not started | — |
| 3C — Overlays and comparison / Phase 3 gate | Not started | — |
| 4A — Hardware programming | Not started | — |
| 4B — ILA capture | Not started | — |
| 4C — GUI socket bridge (optional) | Not started | — |
| 4D — Remote builds | Not started | — |
| 4E — Bonsai Term (optional) | Not started | — |

**Next construction task:** implement 1A's installed application foundation and independent
fixture, then complete 1B's generic Dune project/job demo before adding the versioned
manifest and project driver in 1C and hierarchical reports in 1D. This plan revision does
not implement code or mark any milestone complete.
