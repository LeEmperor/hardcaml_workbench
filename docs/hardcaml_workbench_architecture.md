# Hardcaml Workbench — Initial Architecture and Implementation Brief

This document is the main source of truth for the system's architecture and scope. The
[project idea and philosophy](project_idea_and_philosophy.md) defines the product intent and
guiding boundaries. The [construction phase plan](construction_phase_plan.md) tracks
implementation order and completion criteria for the phases described here. Design changes
belong in this document first; the plan should then be updated to match.

## Purpose

Build a standalone development application that opens and operates on independent
Hardcaml-based RTL projects.

The Workbench is a control plane over an opened project's existing development flow. The
project continues to own its synthesizable source, Dune build, tests, target constructors,
and command-line entry points. The Workbench discovers or requests those operations, runs
them in the project's environment, and presents their state and results coherently.

The goal is **not** to replace Emacs, Git, or normal source editing. The workbench should instead become the primary place to:

- elaborate and inspect Hardcaml designs,
- run simulations and tests,
- generate RTL,
- invoke synthesis/implementation tools,
- inspect timing, area, and utilization,
- browse hierarchy and design structure,
- visualize generated RTL/circuit graphs,
- manage vendor tool runs and ASIC flow runs,
- program/debug FPGA hardware,
- compare design iterations,
- and eventually provide a unified interactive view over the entire RTL development flow.

The motivating problem is that a Hardcaml/FPGA workflow is currently split across:

- Emacs,
- `dune`,
- expect tests,
- generated RTL,
- Verilator or other simulators,
- `hardcaml_xilinx_reports`,
- Vivado batch runs,
- the Vivado GUI,
- ASIC flow scripts and their pinned tool environments,
- report files,
- hardware manager,
- and ad-hoc shell scripts.

The Workbench should act as the **control plane** for these systems without absorbing the
opened repository into the Workbench's source tree or replacing its build.

---

# 1. Frontend Choice and Delivery Order

Build two frontends over one typed application protocol: a `bonsai_term` terminal client and
a `bonsai_web` browser client. Neither is a port of the other. Both are views over
daemon-owned projects, jobs, artifacts, and tool sessions.

Jane Street's Bonsai ecosystem is deliberately split into:

- `bonsai`: general incremental/composable state machines,
- `bonsai_web`: browser-based GUIs,
- `bonsai_term`: terminal UIs.

Both clients share the Bonsai computation model, so state and request logic can be shared
even where views cannot.

Assign frontends by product verb rather than by feature parity. The verbs are the ones in
[project idea and philosophy](project_idea_and_philosophy.md#2-product-boundary):

| Verb | Primary frontend | Reason |
| --- | --- | --- |
| run, measure, compare, deploy | terminal | Project/target trees, job tables, streaming logs, metric tables, run history, comparison tables, and tool consoles are text. |
| understand, inspect, debug | browser | Block diagrams, elaboration DAGs, timing-path overlays, utilization treemaps, and floorplan/device views are inherently graphical. |

The browser client remains necessary. These views have no useful terminal form:

- hierarchical block diagrams,
- DAGs,
- RTL/netlist visualization,
- timing path visualization,
- utilization treemaps,
- floorplanning/device/die views,
- dockable/tabbed workspaces.

Deliver the terminal client first, for three reasons.

1. **It is not blocked.** The
   [JavaScript toolchain prerequisite](development.md#javascript-toolchain-prerequisite)
   currently prevents compiling the browser client at all. A native terminal client has no
   `js_of_ocaml` dependency path, so frontend work can proceed while that is unresolved.
2. **It retires the protocol's main design risk.** "The protocol is frontend-agnostic" is an
   untested claim until a second frontend exists. Building Phases 1-3 against one frontend
   lets browser-shaped assumptions accumulate in shared types, which turns a later terminal
   client into a rewrite rather than a client.
3. **Phase 1's output is already text.** The report, hierarchy, and inspector sketches in
   sections 6 and 8 are tables and trees. Terminal rendering loses little of Phase 1 and
   nothing of the job and log workflow.

`hardcaml_waveterm` renders waveforms in a terminal, so waveform inspection is not by itself
an argument for the browser client. Schematic, graph, overlay, and floorplan views are the
browser client's distinguishing scope.

Graphical feature parity between the clients is not a goal. A view with no useful terminal
form is explicitly unavailable there rather than degraded.

Conceptually, both frontends and the daemon operate a separately built project:

```text
                 Bonsai Term             Bonsai Web
                 operate / measure       visualize / inspect
                       \                    /
                        +---- typed RPC ---+
                                  |
                     Hardcaml Workbench daemon
                                  |
              +-------------------+-------------------+
              |                   |                   |
          Dune adapter       Tool adapters       Artifact store
              |                   |                   |
              +-------------------+-------------------+
                                  |
                      independently owned project
                    circuits / tests / driver / tools
```

---

# 2. Project Boundary

Hardcaml Workbench is its own installed application. It opens a user-selected project root;
it is not itself the container for that project's hardware source.

For example:

```text
/home/user/devel/
├── hardcaml-workbench/     application repository
└── mac/                    independent hardware repository
    ├── dune-project
    ├── hardcaml-workbench.sexp
    ├── lib/
    └── test/
```

The `mac` repository owns its synthesizable libraries and remains buildable with ordinary
Dune commands. The Workbench may contain a deterministic hardware project under test
fixtures, but it should not expose an application-owned library of production circuits.

Do **not** initially build another general-purpose IDE.

Emacs should remain responsible for:

- editing OCaml,
- LSP,
- refactoring,
- Git,
- normal text navigation,
- general development.

The Workbench should focus on:

```text
understand design
run design
inspect design
measure design
compare design
debug design
deploy design
```

This boundary is important. Otherwise the project risks becoming a reimplementation of VS
Code or Emacs rather than a useful hardware-specific tool.

---

# 3. Recommended High-Level Architecture

Use a native OCaml daemon and a Bonsai Web frontend compiled from OCaml to JavaScript. The
installed application should contain the daemon and the compiled frontend assets. The daemon
may serve those assets from a local address and open that address in the user's browser.

```text
+--------------------------------------------------------------+
|                       Bonsai Web UI                          |
|                                                              |
| hierarchy | workspace tabs | inspector | jobs | console      |
+----------------------------+---------------------------------+
                             |
                       typed RPC / WS
                             |
+----------------------------v---------------------------------+
|                  Hardcaml Workbench Daemon                   |
|                                                              |
|  Project model                                               |
|  Job scheduler                                               |
|  Artifact registry                                           |
|  Circuit/elaboration service                                 |
|  Simulation service                                          |
|  Vivado service                                              |
|  Xilinx-report service                                       |
|  Hardware service                                            |
|  Process supervision                                         |
+-------+----------------+---------------+----------------------+
        |                |               |
     Dune /         Vivado Tcl      external tools
 project driver     / process       verilator/yosys/etc.
        |
+-------v------------------------------------------------------+
| Independently owned Hardcaml project                         |
| circuits | tests | target declarations | project toolchain   |
+--------------------------------------------------------------+
```

The daemon should own long-lived processes and heavyweight tool execution.

The browser frontend should **not** directly execute Vivado or shell commands.

The daemon should not dynamically link arbitrary project modules into its own process. Code
that must call the project's Hardcaml APIs should run in a project-side driver built by Dune
inside that project's compiler and package environment.

Nothing in this structure requires the daemon to run on the machine displaying the UI. The
daemon must be co-located with the project and its toolchain; clients need only the typed
RPC connection. Section 4.4 defines the supported deployment modes and their transport and
trust rules.

---

# 4. Major Backend Subsystems

## 4.1 Project Model

Represent an opened, independently owned project explicitly. A project record is Workbench
session state associated with an external root; it is not a collection of source modules
owned by the Workbench.

Example concepts:

```ocaml
type project =
  { id : Project_id.t
  ; root : string
  ; name : string
  ; integration : project_integration
  ; targets : target list
  ; boards : board list
  ; build_configs : build_config list
  }

type target =
  { id : Target_id.t
  ; name : string
  ; top : string
  ; clocks : clock_constraint list
  ; backend : Backend_id.t (* fpga, asic, simulation-only, ... *)
  ; facts : Target_fact.t list (* namespaced, backend-declared *)
  }
```

Target facts are extensible and backend-tagged rather than a fixed record. An FPGA part
number is one backend's fact, not a field every target has; an ASIC target instead carries
harness, technology, and resolved geometry facts, and a simulation-only target may carry
neither. Do not promote one backend's vocabulary into the shared target type, and do not
require a target to produce a bitstream.

The implemented schema in `protocol/` follows these concepts with three refinements, made
while deriving milestone 1A's types and recorded here so this section stays the source of
truth:

- `build_configs` is named `configurations`, matching `Configuration_id.t`. A configuration
  carries its identity, target, and description; the settings it selects belong to the
  versioned driver contract and are added in 1C rather than duplicated here.
- `boards` is not implemented. A board is an FPGA-backend concept, and representing it as a
  field every project has would be the coupling the paragraph above prohibits. It returns as
  backend-declared facts or its own type when Phase 4 needs it.
- A target fact carries an optional `display` string, so a backend can control how a
  structured value is shown without the UI interpreting the backend's vocabulary.

Avoid coupling the entire application directly to command-line flags.

The project model is the Workbench session's view from which adapters derive typed tool
requests. The opened project remains authoritative for design constructors and configuration;
driver-derived target facts must not become a second independently edited design description.
Project-local paths must be resolved relative to the selected, validated root.

Project integration has three levels:

1. **Generic Dune project:** detect `dune-project`, inspect the workspace, and expose normal
   build/test actions without requiring Workbench-specific files.
2. **Versioned manifest:** read `hardcaml-workbench.sexp` for explicit integration points and
   metadata that cannot be inferred safely.
3. **Project-side driver:** run a Dune executable linked against the project's own Hardcaml
   code to discover targets, elaborate circuits, generate RTL, and perform other typed
   project operations.

The manifest should be small and additive. It should refer to Dune executables and aliases
rather than reproducing the Dune build graph. An initial shape is:

```lisp
(lang hardcaml-workbench 1)

(project
 (name mac))

(dune
 (driver ./workbench/project_driver.exe)
 (build_alias @all)
 (test_alias @runtest))
```

Dune and Opam inspection can reveal workspace structure, build targets, dependencies, and
execution context. They cannot generally infer which parameterized OCaml function constructs
a hardware top level or which configurations, clocks, constraints, and FPGA parts are valid.
Those semantics require the explicit manifest and project-side driver contract.

The driver protocol must be versioned. The daemon invokes the driver through Dune in the
opened project's environment, supervises it as a job when appropriate, and reports missing
or incompatible integration without preventing generic Dune use.

A small `hardcaml_workbench_project` SDK may help external projects declare targets and
implement the driver protocol. It is project-integration code, not synthesizable hardware,
and projects must remain usable through their ordinary Dune commands without launching the
Workbench.

---

### ASIC projects and `hardcaml_asic`

The [ASIC library architecture](../../hardcaml_asic/docs/architecture.md) defines an
independent project declaration, temporary elaboration context, resolved target, immutable
build bundle, and separate execution record. The
[protocol emulator](../../scaf/docs/construction-plan.md) is its first reference consumer.
These are planned integration boundaries, not a claim of implemented ASIC support here.

For such a project, the driver calls the project's own `hardcaml_asic` version. The
declaration/build supplies harness plus technology, clocks, valid configurations, resource
selection policies, source sets, constraints, collateral, and generated TT metadata. The
Workbench manifest identifies the driver/aliases; it must not duplicate those facts as a
second configuration authority. Discovery can expose immutable summaries and supported
configuration choices without permitting raw edits to protected target values.

The ASIC adapter owns flow rendering, tool-specific invocation semantics, and result
interpretation. A project command or optional library runner executes the same emitted
bundle available from the CLI. Workbench owns job scheduling/supervision, cancellation,
logs, and presentation of the resulting records. Define one execution owner per request;
do not launch an independent flow again merely to import its results. Environment/PDK
provisioning remains explicit and is not a side effect of opening or elaborating a project.

Integration can progress from generic build/test commands (1B), to versioned project
operations and build/run artifact import (1C plus the ASIC operation extension), to typed
simulation/waveforms when 3B is available. It does not require the Vivado milestones and does
not change their exit gates. Section 20's report gate is stated so that an ASIC reporting path
satisfies it, so this progression reaches a usable Workbench without a Xilinx installation.
Keep backend-specific target facts extensible rather than assuming every target has an FPGA
part or produces a bitstream, per section 4.1. Exact ASIC operation, capability, result, and
cancellation schemas must be recorded before implementation.

Workbench jobs and artifact IDs reference ASIC build-manifest and execution identities;
they do not replace or rewrite those records. Preserve model/synthesis source-set roles,
requested versus selected resources, fallback/override reasons, requested versus actual
tools, and links to original reports. Distinguish bundle emission, flow completion, timing
closure, and physical checks; an unavailable metric stays unknown. Sections 4.2 and 18 define
the build/run identity, staged-completion, metric, and check representations this requires.
Frontend retrieval still uses artifact IDs, with paths and input-content preservation managed
by the backend.

The emulator retains its device host API, firmware loader, protocol tests, and recovery
logic. Generic design inspection fits Workbench's scope; a protocol-emulator operator
extension is a separate future decision, not implied by FPGA Hardware Manager support.
Neither Workbench nor commercial EDA adapters gate the emulator's hardware/tapeout path.
Sibling links above identify workspace documentation, not runtime/build path requirements.

## 4.2 Job System

Every substantial action should become a job.

Examples:

```text
Generate RTL
Run expect tests
Run simulation
Run Verilator
Run hierarchical synthesis report
Run Vivado synthesis
Run Vivado implementation
Generate bitstream
Program FPGA
Capture ILA
```

Suggested state model:

```text
Queued
  |
Starting
  |
Running
  |
+----> Complete
|
+----> Failed
|
+----> Cancelled
```

A job should record:

- ID,
- type,
- configuration,
- creation/start/end times,
- current phase,
- stdout/stderr/log stream,
- generated artifacts,
- exit status,
- structured result,
- parent/child jobs.

The frontend should receive incremental job updates.

### Jobs, builds, and runs

A job is Workbench's unit of supervision. It is not the unit of design identity. Some
backends separate an immutable build description from repeated executions of it, and the job
model must reference those identities rather than replace them.

For the ASIC path in section 4.1, one emitted build bundle can be executed many times:

```text
build (immutable)             one per emitted bundle
  |
  +-- run (execution record)  many per build
        |
        +-- job (supervision) Workbench's view of one run attempt or stage
```

A job therefore carries optional build and run identities supplied by the project or its
adapter. The FPGA path may leave them absent where a single invocation both defines and
performs the work. Re-running must not alter the original build's provenance, and reopening a
stored result must not execute the flow again. Do not synthesize Workbench-local substitutes
for backend identities that already exist.

### Staged and resumable operations

Some flows are a sequence of separately runnable stages rather than one invocation. An ASIC
flow can emit, preflight, run a synthesis or implementation stage, postcheck, collect, and
report, and the user must be able to run only the later stages against an existing run.

Model this with parent/child jobs over a shared run identity, and record which stages were
requested and which actually completed. A completed earlier stage is not evidence that a
later stage passed. Do not require every backend to follow one fixed stage sequence.

### Long-running work and client lifetime

Job duration spans minutes to hours: a Vivado implementation takes tens of minutes, and a
full ASIC hardening run can exceed a working day. The daemon's lifetime is therefore
independent of any client's. A client exiting must not cancel or orphan a job, and a
reconnecting client must recover state without resubmission. Section 4.4 describes the
deployment consequences.

## 4.3 Application Protocol and Runtime Boundaries

The daemon and browser share a typed application protocol. Its OCaml definitions are
compiled to native code for the daemon and to JavaScript for the Bonsai frontend. They cover
portable values such as:

- project, target, configuration, job, artifact, and hierarchy IDs,
- project and target summaries,
- typed requests and responses,
- job snapshots and incremental updates,
- structured report results and artifact metadata,
- protocol and project-driver version information.

Shared protocol types must not contain process handles, file descriptors, or other
native-only resources. A browser receives an artifact ID and public metadata rather than a
daemon-local filesystem handle. The daemon resolves the ID when the browser requests
artifact content.

Native backend services are the application logic that runs on the local machine: project
sessions, manifest parsing, Dune invocation, job supervision, artifact storage, Vivado
control, and RPC serving. These services are implemented in OCaml but compiled as native
code, while the Bonsai source is compiled into browser assets. Bonsai provides the client UI
and state model; the daemon remains responsible for machine and tool access.

Internal Dune libraries should enforce this direction:

```text
Bonsai term client ----+
                       +--> shared protocol <---- native daemon
Bonsai web client -----+                              |
                                                      v
                                      backend services and adapters
                                                      |
                                                      v
                                       independently built project
```

Frontend code must not depend on native backend or adapter libraries. These are application
boundaries inside the Workbench repository, not libraries of synthesizable hardware.

Both clients depend on the shared protocol only. The terminal client is compiled natively and
could therefore link backend or adapter libraries directly; it must not. Being native is not
permission to bypass the daemon, resolve project paths, or start tools in-process. Frontend
code observes and requests state transitions regardless of how it is compiled.

More than one client may be attached to one daemon at once, including one of each kind.
Projects, jobs, artifacts, and tool sessions are daemon-owned and shared between them;
selection, layout, and scroll position are per-client. Record which state is shared before
implementing the second client, and define one owner for cancellation so two attached clients
cannot both claim a job.

## 4.4 Deployment and Client Attachment

The daemon owns state, processes, and tool access; a client is a view. That separation already
permits the daemon to run somewhere other than the machine displaying the UI. Distinguish
three deployment modes, because their costs differ sharply.

| Mode | Shape | Cost |
| --- | --- | --- |
| Local | Daemon, project, and tools on the user's machine | None beyond Phase 1 |
| Attached | Daemon, project, and tools on one remote machine; clients attach from elsewhere | Transport and trust only |
| Distributed workers | Daemon local; jobs dispatched to remote build machines | Source transfer, cross-machine identity, and recovery |

The attached mode is the cheap one and should be available early. The project, its Dune
environment, its toolchain, and its artifacts all stay on one machine, so there is no source
transfer, no cross-machine source-identity problem, and no risk of executing a submitted job
twice on reconnect. The daemon is the only component that must be co-located with the tools.

This matters most where the environment cannot move. An ASIC consumer's process design kit,
pinned flow virtual environments, harness support tooling, and multi-hour runs belong to the
machine that provisioned them. Attaching to a daemon there is the natural deployment, and a
daemon that outlives its clients is what makes an overnight run survivable: start a stage,
detach, attach later, and run only the remaining stages.

Distributed workers remain a separate and later concern (section 23). Attached operation is
not a partial implementation of that mode, and that mode is not needed to reach it.

### Transport and trust

The daemon executes project build commands, project drivers, and vendor tools. It must not be
reachable as a network service.

Bind the daemon to loopback only, in every mode. Remote attachment is an SSH port forward to
that loopback address, which the user already authenticates and encrypts. This delivers the
attached mode with no Workbench-specific authentication, key management, or transport
security to design, and the browser client works unchanged over a forwarded port.

If a later requirement genuinely needs a daemon listening on a shared address, that is an
explicit product decision requiring an authentication and authorization design. It is not a
configuration default.

---

# 5. Hardcaml Integration

Prefer direct Hardcaml library integration inside the opened project's driver where
practical. The driver links the project's circuit libraries and Hardcaml version, then
returns versioned structured results to the Workbench daemon.

Useful categories include:

- elaboration,
- hierarchy inspection,
- circuit traversal,
- simulation,
- waveform generation,
- Verilog generation,
- synthesis/report generation.

Do not ask the daemon to discover and dynamically link arbitrary OCaml modules from an
external repository. The process boundary allows each project driver to compile in its own
Dune and Opam environment while still using typed Hardcaml APIs internally. The daemon owns
the job and supervises the driver; the project driver owns calls into project code.

Do not convert typed project-side library operations into ad-hoc shell pipelines when a
driver can expose a stable structured operation. Generic Dune builds, tests, and existing
project commands may still be launched directly through the Dune adapter.

---

# 6. `hardcaml_xilinx_reports`

`hardcaml_xilinx_reports` is an especially good first integration.

It can take a hierarchical Hardcaml design and run Vivado synthesis on modules in the hierarchy, producing timing and utilization estimates.

It produces those numbers by running Vivado. It is therefore the best first *FPGA* report
integration, not the only way to satisfy the Phase 1 report milestone. Section 20 states that
gate in backend-neutral terms so a project whose reporting path is an ASIC flow can satisfy it
without a Xilinx installation.

When compatible with the opened project, its library API should be called from the
project-side driver that already links the target's Hardcaml circuit. The daemon supervises
that driver operation and records its structured results, raw reports, logs, and provenance.
If an existing project exposes only a CLI initially, a native adapter may invoke it behind
the same typed Workbench operation.

Suggested UI:

```text
message_dispatch
  LUTs:     741
  FFs:      315
  BRAM:       0
  DSP:        0
  Delay:   4.80 ns
  Slack:  +0.42 ns
```

Possible hierarchy view:

```text
top
├── ethernet
│   ├── pcs
│   └── mac
├── feed_parser
│   ├── packet_header
│   ├── message_header
│   └── message_dispatch
└── order_book
```

Each node may show:

- LUTs,
- FFs,
- BRAM,
- URAM,
- DSP,
- worst path,
- slack,
- synthesis status.

This is a strong MVP feature because the library already exposes useful structured hardware information.

---

# 7. RTL / Elaboration Visualization

This should be a long-term first-class feature, not merely decorative UI.

Hardcaml already has a structured representation of the circuit before Verilog generation.

Do not parse generated Verilog back into a schematic unless required for external RTL.

Instead use:

```text
Project-side Hardcaml circuit
       |
       v
versioned Workbench graph representation
       |
       +-- hierarchy
       +-- instances
       +-- signals
       +-- registers
       +-- memories
       +-- operators
       +-- muxes
       +-- clock/reset information
       |
       v
Bonsai Web graph renderer
```

The graph representation crosses from the project driver to the daemon as data. The
Workbench does not need to link the opened project's circuit modules into the daemon or
browser.

The visualization should be hierarchical.

Example high level:

```text
+----------+      +------------+      +-----------+
| Ethernet | ---> | MDP Parser | ---> | Orderbook |
+----------+      +------------+      +-----------+
```

Drill down:

```text
+---------------+
| Packet Header |
+-------+-------+
        |
        v
+---------------+
| Message Header|
+-------+-------+
        |
        v
+---------------+
| Dispatcher    |
+---------------+
```

Eventually drill down to primitives/operators/registers.

Useful interactions:

- click instance,
- expand/collapse,
- trace signal,
- show fan-in/fan-out,
- search signal,
- jump to source,
- overlay resource estimates,
- overlay timing information,
- highlight clock/reset domains,
- highlight critical paths.

---

# 8. Suggested UI Layout

This is the browser client's layout. The terminal client presents the same project, job, log,
and report state as panes, tables, and trees, and omits the schematic, graph, and overlay
views per section 1.

A useful initial desktop-style layout:

```text
+--------------------+-------------------------------------------+
| PROJECT / HIERARCHY| RTL | Schematic | Timing | Wave | Reports|
|                    |                                           |
| top                |              MAIN WORKSPACE               |
| |- mac             |                                           |
| |- parser          |                                           |
| |  |- header       |                                           |
| |  `- decoder      |                                           |
| `- orderbook       |                                           |
+--------------------+-------------------------------------------+
| JOBS / CONSOLE / VIVADO OUTPUT / TEST OUTPUT                   |
+----------------------------------------------------------------+
```

Optional right-hand inspector:

```text
Selected: message_dispatch

Type: Hardcaml instance
Clock: clk_156
LUT: 741
FF: 315
Worst delay: 4.80 ns
Source: message_dispatch.ml
```

Useful Bonsai/Web building blocks include:

- split panes,
- tabs,
- CodeMirror,
- tree layouts,
- DAG visualization,
- drag/drop,
- large tables,
- keyboard shortcuts.

---

# 9. Tool Worker Strategy

## Core Principle

Treat an external tool as **an engine**, not as a widget. Vivado is the first and most
detailed instance below; the principle is not specific to it.

Good:

```text
Workbench
   |
   +--> start/control Vivado
   +--> issue Tcl commands
   +--> receive results
   +--> parse reports
   +--> display structured data
   +--> launch full Vivado GUI when desired
```

Avoid making "embed the native Vivado GUI inside the browser" a core requirement.

Embedding an arbitrary X11/Wayland GUI inside a Bonsai browser window would require display/window-system hacks, streaming, VNC-like techniques, or a native shell.

It is possible in principle, but gives little architectural value.

Instead expose:

```text
[ Open in Vivado ]
```

for situations where the user needs the native GUI.

---

# 10. Persistent Tcl Tool Control

Yes: a persistent Tcl-controlled Vivado instance is a strong design direction.

Vivado contains a full Tcl interpreter and exposes most design operations through Tcl.

The workbench can therefore establish a **long-lived Vivado worker** rather than starting a new Vivado process for every action.

There are three reasonable levels of integration.

Sections 10-16 are mostly not Vivado-specific. Command framing, serialization through one
executor, timeouts, cancellation, worker death and restart, session invalidation, and Tcl
event-loop hazards apply to any long-lived Tcl-driven tool process. Name the subsystem for
that role rather than for its first instance: a `Tcl_worker` with Vivado as its first adapter,
and OpenROAD as a plausible second; the initial ASIC flow already drives it. Yosys exposes a
comparable interactive shell.

Keep tool-specific command vocabulary, report parsing, and result interpretation in each
tool's adapter. Only the worker mechanics are shared.

---

## 10.1 Level 1 — Batch Invocation

Initial/simple implementation:

```text
vivado -mode batch -source command.tcl
```

Advantages:

- simplest,
- deterministic,
- easiest to debug,
- robust,
- easy job isolation.

Disadvantages:

- Vivado startup is expensive,
- no persistent in-memory design,
- poor interactive latency.

This is appropriate for the first implementation.

---

## 10.2 Level 2 — Persistent Vivado Tcl Subprocess

Recommended next step.

Start:

```text
vivado -mode tcl
```

and keep the process alive.

The Workbench daemon owns:

```text
stdin  ---> Vivado Tcl interpreter
stdout <--- Vivado
stderr <--- Vivado
```

Then implement a framing protocol around commands.

Conceptually:

```text
Workbench
   |
   | RPC
   v
VivadoAdapter
   |
   | command ID 42
   v
persistent Vivado Tcl
   |
   | result 42
   v
VivadoAdapter
```

Example operations:

```text
open_project ...
synth_design ...
open_run synth_1
report_timing_summary ...
report_utilization ...
get_cells ...
get_nets ...
write_checkpoint ...
launch_runs impl_1
wait_on_run impl_1
```

The adapter should wrap commands so completion/result boundaries are explicit.

Do **not** depend solely on recognizing the normal `%` Tcl prompt.

Example conceptual wrapper:

```tcl
proc wb_eval {id command} {
    if {[catch {uplevel #0 $command} result options]} {
        puts "__WB_ERROR_BEGIN__ $id"
        puts $result
        puts "__WB_ERROR_END__ $id"
    } else {
        puts "__WB_RESULT_BEGIN__ $id"
        puts $result
        puts "__WB_RESULT_END__ $id"
    }
    flush stdout
}
```

This is only a sketch. The implementation should also serialize structured data safely.

---

# 11. Vivado Tcl Socket Server

A socket-based design is also possible.

Vivado's interpreter is Tcl, and Tcl supports TCP sockets.

A bootstrap Tcl script loaded into Vivado could create a server:

```tcl
socket -server wb_accept 9900
```

Conceptual model:

```text
                  TCP localhost
Workbench daemon <------------> Vivado Tcl
                                  |
                                  +-- in-memory design
                                  +-- project state
                                  +-- timing database
                                  +-- hardware manager
```

This gives a very attractive architecture:

```text
Bonsai UI
    |
    v
Workbench daemon
    |
    v
Vivado RPC client
    |
  TCP
    |
    v
Vivado Tcl bridge
```

The Tcl bridge can expose a deliberately small RPC-like protocol.

For example:

```text
OPEN_PROJECT
RUN_SYNTH
GET_TIMING_SUMMARY
GET_UTILIZATION
GET_HIERARCHY
GET_CRITICAL_PATHS
PROGRAM_DEVICE
GET_ILA_DATA
```

Rather than exposing arbitrary Tcl strings from the browser, implement typed commands in the Workbench daemon and corresponding Tcl procedures.

Example:

```tcl
proc wb_get_timing_summary {} {
    # execute Vivado commands
    # serialize structured result
}
```

This significantly improves correctness and security.

---

# 12. Socket vs Persistent stdin/stdout

Start with **persistent stdin/stdout**, not sockets.

Reason:

- fewer moving parts,
- the daemon already launches/owns the Vivado process,
- process lifetime is naturally tied to the project/session,
- stdout/stderr logs are already captured,
- no port management,
- no socket authentication,
- no question of stale Vivado instances.

Add socket mode later when useful.

Sockets become particularly attractive when:

- Vivado was started independently by the user,
- multiple Workbench clients may attach,
- Vivado runs on another machine,
- a long-lived Vivado process should survive Workbench restarts,
- the native Vivado GUI should remain open while Workbench controls the same session.

---

# 13. Particularly Interesting Case: Controlling an Open Vivado GUI

A strong future feature is:

```text
vivado -mode gui -source workbench_server.tcl
```

The Tcl bootstrap initializes the socket bridge while the normal Vivado GUI remains open.

Then:

```text
                  +--------------------+
                  |  Vivado GUI        |
                  |                    |
                  | in-memory project  |
                  +---------+----------+
                            |
                       Tcl interpreter
                            |
                         socket
                            |
                  +---------v----------+
                  | Hardcaml Workbench |
                  +--------------------+
```

This is much more useful than trying to visually embed Vivado.

The user could:

1. inspect/edit something manually in Vivado,
2. click an action in Workbench,
3. Workbench injects Tcl into the same Vivado process,
4. Vivado updates,
5. Workbench queries the new state,
6. both views remain synchronized.

This is a realistic and potentially very powerful workflow.

---

# 14. Important Tcl/Event-Loop Considerations

A socket bridge needs care.

Tcl server sockets invoke callbacks through Tcl's event loop.

GUI-mode Vivado already has an event-driven application environment, which is favorable.

For Tcl-only mode, a bridge may need an explicit event wait such as a `vwait`-style loop.

More importantly, Vivado commands can be long-running.

Do not allow multiple commands to mutate the same in-memory design concurrently.

Recommended model:

```text
socket/request input
       |
       v
command queue
       |
       v
single Vivado executor
       |
       v
response
```

Vivado should effectively be treated as a single-threaded stateful engine.

The Workbench daemon can be concurrent; each individual Vivado session should serialize design-mutating commands.

---

# 15. Structured Vivado API

Do not expose raw Tcl as the primary Workbench API.

Use OCaml types.

For example:

```ocaml
type vivado_command =
  | Open_project of string
  | Synthesize of synthesis_config
  | Implement of implementation_config
  | Timing_summary
  | Utilization
  | Critical_paths of { count : int }
  | Program_device of { bitstream : string }
```

Responses:

```ocaml
type timing_summary =
  { wns : float
  ; tns : float
  ; whs : float option
  ; failing_endpoints : int
  }

type utilization =
  { luts : int
  ; ffs : int
  ; brams : int
  ; urams : int
  ; dsps : int
  }
```

This keeps Vivado-specific string manipulation confined to the adapter.

These are the Vivado adapter's own result types. `utilization` above is an FPGA resource
vocabulary and must not become the application's general metric representation; section 18
defines how adapter results map onto backend-neutral metrics with units and analysis context.

A lower-level "raw Tcl console" can still exist for advanced users.

---

# 16. Raw Tcl Console

A very useful optional panel:

```text
Vivado Tcl Console
> get_cells -hier *parser*
...
> report_timing -from ...
...
```

The Workbench can forward these commands to the persistent Vivado session.

This should be treated as an expert escape hatch, not the main application protocol.

---

# 17. Hardware Manager Integration

Vivado hardware operations are Tcl-accessible as well.

The current AMD documentation exposes operations such as:

```text
open_hw
connect_hw_server
get_hw_targets
current_hw_target
open_hw_target
get_hw_devices
program_hw_devices
```

A future Hardware page could show:

```text
Hardware Server: localhost:3121

Target:
  Digilent / ...

Device:
  xc7a35t...

Bitstream:
  build/top.bit

[ Program ]

ILA cores:
  ila_0
  ila_1

[ Arm ] [ Trigger ] [ Capture ]
```

This means the Workbench can eventually handle FPGA deployment/debugging without requiring the user to navigate Vivado Hardware Manager for common operations.

---

# 18. Artifact Model

Treat generated outputs as typed artifacts rather than random files.

Examples:

```ocaml
(* Artifact kinds are open, not a closed variant: a new backend must be able to
   introduce a kind without revising the protocol schema. *)
type artifact_kind =
  { namespace : string (* hardcaml, vivado, librelane, tt, ... *)
  ; name : string (* verilog, gds, lef, def, sdc, netlist, ... *)
  ; role : Artifact_role.t (* source, report, log, collateral, deliverable *)
  ; media : string option (* concrete format, where it is known *)
  }

type artifact =
  { id : Artifact_id.t
  ; kind : artifact_kind
  ; project : Project_id.t
  ; target : Target_id.t
  ; configuration : Configuration_id.t
  ; generating_job : Job_id.t
  ; build : Build_ref.t option (* backend build identity, section 4.2 *)
  ; run : Run_ref.t option (* backend execution identity, section 4.2 *)
  ; metadata : artifact_metadata
  }
```

The implemented schema in `protocol/` makes `target` and `configuration` optional on both
artifacts and jobs. A generic Dune project has no targets, so its build log is an artifact of
a project rather than of a target; requiring one would force a placeholder identifier that
names nothing. `availability` is a peer of the metadata rather than part of it, because an
artifact whose content has since been removed is still a registered result with intact
provenance.

A closed kind variant would force a protocol revision for every backend. The FPGA vocabulary
is one namespace: Verilog, checkpoints, bitstreams, timing and utilization reports, and tool
logs. An ASIC flow adds GDS, LEF/DEF, SDC constraints, gate-level netlists, simulation
collateral, build manifests, harness submission metadata, and physical-verification reports.
The UI selects a viewer from the kind; an unrecognized kind remains retrievable by ID.

The backend stores each artifact's filesystem location privately. Browser-visible protocol
values contain the artifact ID, kind, availability, and metadata. Content is retrieved from
the daemon by ID so browser code never relies on a daemon-local path.

Store provenance including:

```text
project root identity
target and configuration
backend build and run identity, where the backend has them
requested and actual tool versions
execution environment identity
git commit
creation time
source design hash
dirty working-tree state where available
generating job
```

Execution environment identity is part of provenance. A flow can depend on a process design
kit, a pinned tool virtual environment, harness support tooling, and an interpreter version;
two runs of the same build in different environments are not the same run. Record those
identities. Do not copy credentials or license secrets into a manifest, and do not treat
recording an environment as provisioning one; provisioning stays explicit and external.

Do not claim an exact committed source identity for dirty or non-Git inputs. Preserve
the input contents needed for reproduction as well as hashes. For ASIC integration, retain
the immutable build manifest and separate execution record under their original identities;
link the Workbench job/artifacts to them as described in section 4.1. Complete provenance
will enable design comparisons later.

## Metrics and Checks

Do not represent results as a fixed resource record. A metric needs its unit and the analysis
context that makes it comparable:

```ocaml
type metric =
  { name : string
  ; value : Metric_value.t
  ; unit : string option
  ; tool : Tool_version.t
  ; stage : string (* the stage that produced it *)
  ; corner : string option (* corner or mode, where applicable *)
  ; source : Artifact_id.t (* the report it was read from *)
  }
```

A missing, unsupported, or unparseable metric is unavailable with a recorded reason. It is
never zero and never a pass. This rule already governs the ASIC library's results and applies
equally to Vivado's. The implemented `Metric.Value.t` carries `Unavailable of
{ reason : string }` as one of its cases rather than pairing a value with a separate
availability flag, so there is no representation of a metric that is both absent and
numeric. Its `source` is optional for the same reason: a metric that is unavailable because
no report was produced has no report to cite.

Timing is not a single number. Report setup and hold analyses separately, and report per
corner or mode wherever the flow analyses more than one; a single worst slack cannot represent
a multi-corner run. Area, timing, and power definitions must stay distinguishable before any
value is compared across tools or runs.

Keep three result categories separate:

```text
completion    which stages the tool actually finished
goals         timing and resource objectives met or missed
verification  required physical checks: passed, failed, or not run
```

Physical-verification and submission checks such as DRC, LVS, antenna, and harness precheck
rules are first-class pass/fail/not-run results, not timing metrics. An emitted build is not a
completed run, a completed run is not timing closure, and timing closure is not physical
verification. Never display one as another.

---

# 19. Design Comparison

Long-term useful feature:

```text
                   Baseline     Current      Delta
LUT                 8,412        7,901       -511
FF                  9,032        9,180       +148
DSP                    64           48        -16
WNS                +0.08ns      +0.41ns    +0.33ns
Latency               8 cyc        10 cyc      +2
```

This is particularly valuable for hardware optimization.

Possible comparison keys:

- Git commit,
- branch,
- parameter set,
- clock target,
- synthesis strategy and FPGA part, for an FPGA target,
- harness, technology, flow adapter version, and resource selection policy, for an ASIC
  target.

Compare only metrics whose units and analysis context agree. A row whose two sides came from
different tools, stages, or corners is not a delta, and a metric unavailable on one side must
render as unavailable rather than as a change. The table above is a single-corner FPGA
example; a multi-corner comparison is a table over corners, not one slack column.

---

# 20. Suggested MVP

Do not start with a complete hardware IDE.

## Phase 1

Build:

1. Workbench daemon.
2. A Bonsai frontend; the terminal client first, per section 1.
3. Open an independent Dune/Hardcaml project by root.
4. Discover/select a design target through its Workbench integration contract.
5. Generate RTL through the project-side driver.
6. Obtain one structured hierarchical or staged report through the project's own reporting
   path. `hardcaml_xilinx_reports` satisfies this for an FPGA project; an ASIC project's flow
   report satisfies it equally. The gate is a structured, provenance-carrying result mapped
   onto the design, not a specific vendor tool.
7. Show hierarchy.
8. Show a metric table with units and analysis context.
9. Show live job/log output.
10. Allow clicking a hierarchy node to inspect its report.

This already produces a useful tool.

Stating item 6 in terms of the project's reporting path rather than one library keeps the MVP
gate reachable without a Vivado installation, and keeps the first useful Workbench available
to an ASIC project. Vivado's own integration begins in Phase 2, where it belongs.

---

# 21. Phase 2

Add:

- persistent Vivado process,
- synthesis/implementation jobs,
- structured report parsing,
- timing summary page,
- utilization page,
- generated RTL viewer using CodeMirror,
- run history.

---

# 22. Phase 3

Add:

- Hardcaml elaboration graph,
- hierarchy drilldown,
- signal search,
- fan-in/fan-out inspection,
- waveform viewer,
- timing-path overlay,
- design comparison.

---

# 23. Phase 4

Add:

- FPGA hardware manager,
- programming,
- ILA integration,
- optional Vivado GUI socket bridge,
- distributed remote build workers.

The terminal frontend is delivered in Phase 1 (section 1), not here. Attached remote operation
is a deployment mode available from Phase 1 (section 4.4); this phase adds only the
distributed-worker model, which needs source transfer, cross-machine source identity, tool
discovery, and recovery semantics.

---

# 24. Initial Repository Layout

Suggested layout:

```text
hardcaml-workbench/
├── dune-project
├── protocol/
│   ├── project.ml
│   ├── target.ml
│   ├── job.ml
│   ├── artifact.ml
│   └── rpc.ml
├── project_integration/
│   ├── manifest.ml
│   └── driver_protocol.ml
├── project_sdk/
│   └── target.ml
├── backend/
│   ├── project_session.ml
│   ├── job_store.ml
│   ├── artifact_store.ml
│   └── process_supervisor.ml
├── adapters/
│   ├── dune_adapter.ml
│   ├── project_driver_adapter.ml
│   ├── xilinx_reports_adapter.ml
│   └── vivado/
│       ├── vivado_process.ml
│       ├── vivado_protocol.ml
│       ├── vivado_tcl.ml
│       ├── vivado_reports.ml
│       └── vivado_hardware.ml
├── daemon/
│   ├── rpc_server.ml
│   └── main.ml
├── web/
│   ├── app.ml
│   ├── hierarchy_view.ml
│   ├── jobs_view.ml
│   ├── reports_view.ml
│   ├── rtl_view.ml
│   └── console_view.ml
│
├── tcl/
│   ├── workbench_bootstrap.tcl
│   └── workbench_server.tcl
└── test/
    └── fixtures/
        └── example_project/    independent miniature Dune/Hardcaml project
```

These directories may contain several private Dune libraries even when the application ships
as one package. Their purpose is to enforce browser/shared/native dependency directions.

The initial 1A Dune layout uses one `hardcaml_workbench` opam package with these private
build targets:

| Role | Dune target | Allowed direct dependencies |
| --- | --- | --- |
| Shared application protocol | `hardcaml_workbench_protocol` | `core`; portable preprocessors |
| Project integration | `hardcaml_workbench_project_integration` | shared protocol and portable parsing libraries |
| Native backend | `hardcaml_workbench_backend` | shared protocol, project integration, `core`, and `core_unix` |
| Native adapters | `hardcaml_workbench_adapters` | shared protocol, project integration, `core`, and `core_unix` |
| Native daemon | `daemon/main.exe` | shared protocol, backend, adapters, `core`, and `core_unix` |
| Browser frontend | `web/main.bc` initially; `web/main.bc.js` before RPC wiring | shared protocol, `core`, `bonsai`, and `bonsai_web` |

The protocol and project-integration libraries remain free of `core_unix` and operating-system
resources. The web executable has no dependency path to the backend or adapters. The initial
structure-only target builds bytecode to validate that dependency graph; it is not a browser
deliverable. Promote it to a js_of_ocaml target before the later 1A task compiles the shared
protocol for JavaScript. The daemon and web executable remain private build targets, and the
package is explicitly allowed to have no install stanzas, until the installation task adds the
launcher and asset rules.

Application build dependencies such as `core_unix`, Bonsai, and js_of_ocaml are normal package
dependencies rather than test-only dependencies. Test frameworks remain conditional on tests,
and formatter/linter packages remain development-only. The application package itself does not
depend on Hardcaml circuit libraries or `ppx_hardcaml`: circuit dependencies belong to the
independent fixture and opened projects. Add a project SDK only if the 1C driver work demonstrates
that it is useful, and keep it separate from circuit ownership. Transport/server packages are
deferred until the RPC and serialization decision is recorded later in 1A.

The Workbench repository does not contain a production library of synthesizable circuits.
`test/fixtures/example_project` represents a separately owned repository for integration
tests and demos. The optional project SDK is integration support linked by an external
project's driver; it does not own or replace that project's hardware library.

Do not treat the exact directory names as mandatory; preserve the roles and dependency
boundaries.

---

# 25. First Implementation Task for Codex

A useful first milestone is:

> Create a minimal Bonsai Term client plus native OCaml daemon. The daemon should expose
> a small typed RPC API. Open a deterministic external fixture project, obtain generic project
> information through a Dune adapter, and display its fixture hierarchy, a jobs table, and a
> console/log pane. Implement one backend action as a supervised job and stream its
> output/status to the frontend. Keep process management, project adapters, and UI code in
> their defined runtime boundaries.

The terminal client comes first per section 1; the browser client implements the same typed
API and adds the graphical views. Building the client against the shared protocol only, with
no dependency path to the backend or adapters, is part of this milestone regardless of which
client is built.

Then add:

> Define the versioned manifest and project-driver contract, use it to elaborate and generate
> RTL from the external fixture project, then integrate `hardcaml_xilinx_reports` through the
> project boundary and expose hierarchical utilization/timing results in the UI.

Only after this base architecture works should the first persistent Vivado integration be added.

---

# 26. Recommended Vivado Milestone

The first Vivado milestone should be:

1. start `vivado -mode tcl`,
2. maintain the process,
3. send a wrapped command,
4. identify command completion reliably,
5. capture stdout/stderr,
6. return a structured result,
7. serialize Vivado commands through one executor,
8. gracefully terminate/restart the worker.

Test initially with simple commands such as:

```tcl
version
pwd
get_parts xc7a35*
```

Then advance to:

```tcl
open_project ...
open_run synth_1
report_utilization
report_timing_summary
```

A socket transport can then be introduced behind the same OCaml interface without changing application-level code.

---

# 27. Design Rule

The central abstraction should be:

```text
Opened projects own hardware source and build definitions.
Workbench owns application state.
Tools perform work.
Adapters translate between them.
UI observes and requests state transitions.
```

Do not make Vivado, Dune, a project driver, a shell script, or a frontend itself the
application state model. Do not duplicate the opened project's Dune graph or hardware source
inside the Workbench.

Do not let one backend's vocabulary become the application model either. FPGA parts,
bitstreams, and LUT/FF counts are one backend's facts; they are not the shape of a target, an
artifact, or a metric.

---

# 28. Useful Upstream References

Bonsai:

https://github.com/janestreet/bonsai

Bonsai Web:

https://github.com/janestreet/bonsai_web

Bonsai Web Components:

https://github.com/janestreet/bonsai_web_components

Bonsai Examples:

https://github.com/janestreet/bonsai_examples

Hardcaml:

https://github.com/janestreet/hardcaml

Hardcaml Xilinx Reports:

https://github.com/janestreet/hardcaml_xilinx_reports

Hardcaml Waveterm (terminal waveform rendering):

https://github.com/janestreet/hardcaml_waveterm

Bonsai Term is part of the Bonsai repository above.

Dune workspace inspection:

https://dune.readthedocs.io/en/stable/reference/cli.html#dune-describe

Dune RPC:

https://dune.readthedocs.io/en/stable/rpc.html

AMD Vivado Tcl Command Reference (UG835):

https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands

AMD Vivado Tcl Scripting Guide (UG894):

https://docs.amd.com/r/en-US/ug894-vivado-tcl-scripting

AMD Programming and Debugging Guide (UG908):

https://docs.amd.com/r/en-US/ug908-vivado-programming-debugging

---

# 29. Summary

The target should be a **Hardcaml-specific hardware workbench**, not a generic editor.

Use:

```text
Bonsai Term        Bonsai Web
        \             /
        +- typed RPC -+
              |
      native OCaml daemon
    |
+----------------------+----------------------+------------------+
| Dune/project driver  | Vivado adapter       | external tools   |
| external project     | persistent Tcl       | Verilator/etc.   |
+----------------------+----------------------+------------------+
            |
            v
independently owned Hardcaml source, tests, and target definitions
```

Ship the Workbench as its own application. Its OCaml source produces a native daemon, a
native terminal client, and a JavaScript Bonsai frontend. Deliver the terminal client first;
the browser client owns the graphical views. Opened hardware repositories remain ordinary Dune
projects. Use generic Dune discovery first, a small versioned `hardcaml-workbench.sexp`
manifest for explicit integration, and a project-side driver for operations that must link the
project's Hardcaml code.

Keep the application backend-neutral where the backend is not the point. Targets, artifacts,
metrics, and jobs must describe an FPGA flow and an ASIC flow without either one's vocabulary
becoming the shared model, and the daemon must be attachable from another machine because some
toolchains cannot move.

Use the native Vivado GUI only when it is actually useful.

For deep integration, control Vivado through Tcl.

Begin with batch processes, advance to a persistent Tcl subprocess, and optionally add a Tcl socket bridge so the Workbench can control an already-running Vivado GUI/session.

The potentially distinctive features of the project are:

- Hardcaml-aware hierarchy inspection,
- interactive elaborated circuit visualization,
- timing/resource overlays,
- persistent Vivado control,
- integrated synthesis/implementation history,
- design comparisons,
- backend-neutral structured results and provenance spanning FPGA and ASIC flows,
- a daemon that outlives its clients and is attachable from another machine,
- and FPGA programming/debugging from the same control plane.
