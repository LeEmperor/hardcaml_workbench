# Hardcaml Workbench — Project Idea and Philosophy

## 1. The idea

Hardcaml Workbench is a standalone development application for working with independent
Hardcaml hardware projects. A user opens a project directory, selects a design target, runs
the project's existing build and hardware operations, and inspects the resulting hierarchy,
logs, RTL, reports, waveforms, and hardware state in one interface.

The Workbench is a control plane over the hardware-development workflow. It does not own the
hardware source and is not the build system. An opened project remains a normal OCaml/Dune
repository whose libraries, executables, tests, and command-line workflows continue to work
without the Workbench.

For example:

```text
/home/user/devel/
├── hardcaml-workbench/       standalone application source
└── mac/                      independent hardware repository
    ├── dune-project
    ├── hardcaml-workbench.sexp
    ├── lib/                  MAC circuit source
    ├── test/
    └── workbench/            optional project integration driver
```

Opening `../mac` does not copy or link its circuits into the Workbench application. The
Workbench asks Dune and the project's integration driver to perform work in the `mac`
repository and records the resulting jobs and artifacts.

## 2. Product boundary

The Workbench should become the primary place to:

- understand a design and its hierarchy,
- start and monitor builds, tests, simulations, and synthesis,
- generate and inspect RTL,
- inspect timing, utilization, waveforms, and tool reports,
- compare runs and configurations,
- control Vivado and, later, attached hardware,
- preserve the relationship between an action, its inputs, logs, and artifacts.

The Workbench should not become a source editor or replace the project's normal tools.
Emacs, Neovim, or another editor remains responsible for editing and language tooling. Git
remains responsible for version control. Dune remains responsible for building OCaml code,
and the opened repository remains usable through ordinary terminal commands.

This boundary lets the Workbench specialize in hardware structure, execution, measurement,
and debugging without becoming another general-purpose IDE.

## 3. The project owns the design

Synthesizable Hardcaml source belongs to the opened project. The Workbench repository may
contain a small hardware project under test fixtures, but only to demonstrate and verify
integration. It should not expose a production library of example circuits as part of the
application architecture.

The opened project owns:

- circuit implementations and configuration types,
- Dune libraries, executables, aliases, and tests,
- target constructors and valid parameter sets,
- board, part, clock, and constraint information,
- project-specific simulation and report entry points,
- any command-line tools useful without the Workbench.

The Workbench owns:

- the project session visible in the application,
- job scheduling, process supervision, and cancellation,
- captured logs and job status,
- the artifact registry and run provenance,
- adapters for Dune, Vivado, and other external tools,
- the typed application protocol,
- the Bonsai user interface.

## 4. Progressive project integration

Project integration should have three levels. A project can adopt the Workbench gradually
without surrendering its existing Dune workflow.

### 4.1 Generic Dune support

The Workbench can open a directory containing `dune-project` without any Workbench-specific
files. It can use Dune's supported commands and RPC facilities to inspect the workspace, run
build and test aliases, and show build progress and diagnostics.

Generic inspection cannot reliably identify Hardcaml semantics. Dune can reveal libraries,
executables, rules, and aliases, but it cannot infer which OCaml function constructs a top
level, which parameter values are valid, or which clock and FPGA part belong to a target.

### 4.2 Versioned project manifest

An optional `hardcaml-workbench.sexp` file declares the project's explicit integration
points. The format is versioned and intentionally small. It refers to Dune targets and
project-owned entry points instead of reproducing the project's build graph.

For example:

```lisp
(lang hardcaml-workbench 1)

(project
 (name mac))

(dune
 (driver ./workbench/project_driver.exe)
 (build_alias @all)
 (test_alias @runtest))
```

The initial format should contain only information that Dune cannot provide or that the user
must choose explicitly. Optional execution-environment, FPGA-part, and default-target fields
can be added when their behavior is defined.

### 4.3 Project-side Hardcaml driver

Some operations must call the project's OCaml code directly. For these, the project may
provide a small Dune executable that links its circuit library and exposes a versioned
Workbench driver protocol.

Conceptually, the daemon runs:

```text
dune exec --root /path/to/mac ./workbench/project_driver.exe -- describe
dune exec --root /path/to/mac ./workbench/project_driver.exe -- generate-rtl ...
```

The driver can discover registered targets, elaborate circuits, extract hierarchy, generate
RTL, and invoke typed project-side library APIs. Because it is built inside the opened
project, it uses that project's OCaml compiler, package set, Hardcaml version, and circuit
libraries.

The Workbench should not dynamically load arbitrary project modules into its daemon. A
separate driver process isolates compiler and dependency differences, gives the daemon a
clear lifecycle to supervise, and preserves the project's standalone build.

A small `hardcaml_workbench_project` SDK may later help projects declare targets and implement
the driver protocol. This SDK is integration code, not a synthesizable hardware library. The
protocol must remain versioned so the daemon can report compatibility errors clearly.

## 5. Application shape

The application has two runtime halves written in OCaml and compiled for different
environments:

```text
+---------------------------------------------------------------+
| Browser                                                       |
|                                                               |
| Bonsai frontend compiled from OCaml to JavaScript             |
+-----------------------------+---------------------------------+
                              | typed RPC / WebSocket
+-----------------------------v---------------------------------+
| Local native OCaml daemon                                     |
|                                                               |
| projects | jobs | artifacts | Dune | tools | Vivado           |
+-----------------------------+---------------------------------+
                              | supervised processes
+-----------------------------v---------------------------------+
| Opened project and its toolchain                              |
|                                                               |
| Dune | project driver | tests | simulators | report tools     |
+---------------------------------------------------------------+
```

The browser cannot directly read arbitrary local files, start Dune, or control Vivado. It
renders state and sends typed requests to the daemon. The native daemon performs local
operations and streams results back to the frontend.

An installed Workbench should include the native daemon and the precompiled HTML,
JavaScript, and CSS assets. Its launcher can start the daemon, serve those assets on a local
address, and open the application in the user's browser. Development may run the frontend
builder and daemon separately, but installation should feel like launching one application.

## 6. Internal boundaries are application boundaries

Separate Dune libraries inside the Workbench exist to enforce application dependencies; they
are not separate hardware libraries.

The main roles are:

- **Protocol:** portable project summaries, IDs, requests, responses, job updates, and
  artifact metadata compiled for both native OCaml and JavaScript.
- **Project integration:** manifest parsing and the contract used to communicate with a
  project-side driver.
- **Backend:** native project sessions, job state, artifact storage, and orchestration.
- **Adapters:** native translation to Dune, Hardcaml project drivers, report tools, Vivado,
  simulators, and hardware interfaces.
- **Daemon:** process lifetime, RPC serving, configuration, and local asset serving.
- **Web:** Bonsai components, browser state, navigation, and presentation.

Portable protocol values describe data that crosses the browser/daemon boundary. They must
not contain native process handles, file descriptors, or other operating-system resources.
For example, the frontend receives an artifact ID and metadata rather than a daemon-local
filesystem handle. The backend resolves that ID when the user requests the artifact.

## 7. Design principles

1. **Projects remain independent.** Opening a project does not make it part of the Workbench
   source tree or Dune workspace.
2. **Dune remains the build authority.** The Workbench requests builds and observes their
   results; it does not recreate Dune's dependency graph.
3. **Use explicit semantics where discovery stops.** A small manifest and typed driver are
   preferable to guessing which OCaml modules constitute hardware targets.
4. **Preserve command-line use.** Workbench integration should be built from ordinary Dune
   executables, aliases, and libraries that remain useful without the UI.
5. **The daemon owns application state.** Browser reconnects must recover projects, jobs,
   logs, and artifacts without repeating work.
6. **Tools perform work through adapters.** UI code does not construct shell commands or
   depend on Vivado, Dune, or project internals.
7. **Every result has provenance.** Artifacts and reports retain their project, target,
   configuration, source identity, tool version, and generating job.
8. **Start local and preserve a remote path.** The first application runs beside the project;
   later remote workers can implement the same typed backend contracts.
9. **Specialize in hardware development.** Editing, general Git workflows, and generic IDE
   features remain outside the product unless they directly support inspecting or operating
   the hardware flow.

## 8. A representative workflow

```text
$ hardcaml-workbench /home/user/devel/mac
```

1. The daemon resolves the Dune project root.
2. It reads `hardcaml-workbench.sexp` if present.
3. It uses Dune inspection for generic workspace information.
4. It runs the declared project driver to obtain Hardcaml targets.
5. The browser displays the project and target hierarchy.
6. The user requests RTL generation for a target.
7. The daemon creates a job and runs the project driver through Dune.
8. Logs and status stream to the browser.
9. The daemon registers the generated RTL with its provenance.
10. The user opens the artifact or starts another report, simulation, or synthesis job.

The same project remains buildable and testable with its normal Dune commands throughout
this workflow.
