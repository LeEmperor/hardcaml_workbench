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
- inspect timing and utilization,
- browse hierarchy and design structure,
- visualize generated RTL/circuit graphs,
- manage Vivado runs,
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
- report files,
- hardware manager,
- and ad-hoc shell scripts.

The Workbench should act as the **control plane** for these systems without absorbing the
opened repository into the Workbench's source tree or replacing its build.

---

# 1. Primary UI Choice

Use **Bonsai Web** as the primary frontend.

Jane Street's Bonsai ecosystem is deliberately split into:

- `bonsai`: general incremental/composable state machines,
- `bonsai_web`: browser-based GUIs,
- `bonsai_term`: terminal UIs.

This project should start with Bonsai Web because many useful hardware-development views are inherently graphical:

- hierarchical block diagrams,
- DAGs,
- RTL/netlist visualization,
- timing path visualization,
- waveforms,
- utilization treemaps,
- floorplanning/device views,
- large sortable/filterable tables,
- resizable panes,
- dockable/tabbed workspaces,
- source/RTL viewers.

A Bonsai Term frontend may later be useful for SSH-heavy workflows, but it should be a secondary frontend over the same backend/domain model.

Conceptually, the Workbench frontend and daemon operate a separately built project:

```text
                 Bonsai Web              Bonsai Term
                 primary GUI             optional TUI
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
  ; part : string option
  ; clocks : clock_constraint list
  }
```

Avoid coupling the entire application directly to command-line flags.

The project model should become the source of truth from which adapters derive typed tool
requests. Project-local paths must be resolved relative to the selected, validated root.

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
Bonsai web application ----> shared protocol <---- native daemon
                                                      |
                                                      v
                                      backend services and adapters
                                                      |
                                                      v
                                       independently built project
```

Browser code must not depend on native backend or adapter libraries. These are application
boundaries inside the Workbench repository, not libraries of synthesizable hardware.

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
Bonsai graph renderer
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

# 9. Vivado Integration Strategy

## Core Principle

Treat **Vivado as an engine**, not as a widget.

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

# 10. Vivado Tcl Control

Yes: a persistent Tcl-controlled Vivado instance is a strong design direction.

Vivado contains a full Tcl interpreter and exposes most design operations through Tcl.

The workbench can therefore establish a **long-lived Vivado worker** rather than starting a new Vivado process for every action.

There are three reasonable levels of integration.

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
type artifact_kind =
  | Verilog
  | Waveform
  | Vivado_checkpoint
  | Bitstream
  | Timing_report
  | Utilization_report
  | Synthesis_log
  | Implementation_log

type artifact =
  { id : Artifact_id.t
  ; kind : artifact_kind
  ; project : Project_id.t
  ; target : Target_id.t
  ; configuration : Configuration_id.t
  ; generating_job : Job_id.t
  ; metadata : artifact_metadata
  }
```

The backend stores each artifact's filesystem location privately. Browser-visible protocol
values contain the artifact ID, kind, availability, and metadata. Content is retrieved from
the daemon by ID so browser code never relies on a daemon-local path.

Store provenance including:

```text
project root identity
target and configuration
tool version
git commit
creation time
source design hash
dirty working-tree state where available
generating job
```

Do not claim an exact committed source identity for dirty or non-Git inputs. Complete
provenance will enable design comparisons later.

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
- synthesis strategy,
- FPGA part,
- clock target.

---

# 20. Suggested MVP

Do not start with a complete hardware IDE.

## Phase 1

Build:

1. Workbench daemon.
2. Bonsai Web frontend.
3. Open an independent Dune/Hardcaml project by root.
4. Discover/select a design target through its Workbench integration contract.
5. Generate Verilog through the project-side driver.
6. Run `hardcaml_xilinx_reports`.
7. Show hierarchy.
8. Show resource/timing table.
9. Show live job/log output.
10. Allow clicking a hierarchy node to inspect its report.

This already produces a useful tool.

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
- optional Bonsai Term frontend,
- remote build-machine support.

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

> Create a minimal Bonsai Web application plus native OCaml daemon. The daemon should expose
> a small typed RPC API. Open a deterministic external fixture project, obtain generic project
> information through a Dune adapter, and display its fixture hierarchy, a jobs table, and a
> console/log pane. Implement one backend action as a supervised job and stream its
> output/status to the frontend. Keep process management, project adapters, and UI code in
> their defined runtime boundaries.

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

Do not make Vivado, Dune, a project driver, a shell script, or the browser itself the
application state model. Do not duplicate the opened project's Dune graph or hardware source
inside the Workbench.

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
Bonsai Web
    |
typed RPC
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

Ship the Workbench as its own application. Its OCaml source produces a native daemon and a
JavaScript Bonsai frontend. Opened hardware repositories remain ordinary Dune projects. Use
generic Dune discovery first, a small versioned `hardcaml-workbench.sexp` manifest for
explicit integration, and a project-side driver for operations that must link the project's
Hardcaml code.

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
- and FPGA programming/debugging from the same control plane.
