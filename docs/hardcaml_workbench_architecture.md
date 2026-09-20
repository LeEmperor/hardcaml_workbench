# Hardcaml Workbench — Initial Architecture and Implementation Brief

This document is the main source of truth for the system's architecture and scope. The
[project idea and philosophy](project_idea_and_philosophy.md) defines the product intent and
guiding boundaries. The [construction phase plan](construction_phase_plan.md) tracks
implementation order and completion criteria for the phases described here. Design changes
belong in this document first; the plan should then be updated to match.

## Active release scope — protemu monitoring (2026-09-20)

The next release is a terminal build/flow dashboard for **`hardcaml_protemu` in the
`../scaf/` worktree**. Its job is to launch the existing project flow, show what is
running without consulting `btop`, and keep timing, flow outcomes, and system/design
information visible. This scope takes precedence over the broader delivery order and
MVP requirements below. Sections 21–23 and the browser frontend are parked roadmap
ideas, not commitments or prerequisites for this release.

Use the installed native daemon and server-side TUI over ordinary SSH. Reuse the
existing supervisor, project environment, logs, artifact access, and integration
contracts. Keep project commands and flow semantics in the project; Workbench must
not become a second LibreLane orchestrator. A small project-side adapter may expose
the existing CLI and records without requiring every operation to be a typed
Hardcaml elaboration call.

### First real integration and evidence boundary

[`scaf/docs/flow.md`](../../scaf/docs/flow.md) is authoritative for the project's
flow. At this scope revision its public entry point is `./flow.sh`, whose full
sequence is `build → emit → preflight → run → postcheck → collect → report → archive`.
Named steps do not implicitly execute their prerequisites. Existing run selection
must be explicit; never guess the intended run from the newest directory.

The project already records `run.json`, `results.json`, postchecks, reports, and
archives under `flow_results/`. Its reporter exposes setup/hold slack, per-corner
timing detail, unconstrained modes, and verification checks; the collector includes
final standard-cell area and utilization. Reuse these results through a project-owned
adapter. Availability of final records does **not** establish live substep telemetry:
the first integration slice must identify or add a bounded machine-readable
progress/status path on the project side, with its schema and update behavior
documented before wiring it into Workbench.

### Always-visible terminal dashboard

Use a stable full-screen layout with these regions; resizing may compact them but
must preserve identity, execution state, timing summary, and stage outcomes:

1. **Identity/header:** project and worktree, target/configuration, source revision
   and dirty state, selected build/run, requested flow extent, clock target and
   technology where supplied. Distinguish the currently edited source from the
   immutable inputs of the displayed result.
2. **Flow strip:** persistent boxes for declared stages with not-run, queued, running,
   passed, failed, cancelled/interrupted, skipped, blocked, or unsupported states as
   appropriate. Show elapsed time and let selection open the supporting log/result.
   Retain boxes before and after execution. A later stage cannot inherit an earlier
   stage's success, and a result from another build/run cannot silently fill a box.
3. **Timing panel:** setup and hold worst slack separately, units, corner/mode,
   producing stage, clock constraint, and result age. Add TNS and violating-path
   counts when the project exposes them, with per-corner drilldown. Unconstrained,
   unavailable, and not-yet-produced are explicit states, never green zeroes.
4. **Results/checks panel:** lint, emit, simulation, GDS, harden, signoff-block, and
   signoff-chip are desired persistent capability/result badges. The project must
   declare their mapping to actual operations and evidence. These names are not all
   current `flow.sh` stages: unsupported badges stay visible as unsupported; a GDS
   artifact is not proof of signoff, and block signoff is not chip signoff. Display
   DRC, LVS, antenna, TT precheck and gate-level simulation separately when supplied.
5. **Execution/log panel:** active project stage and tool substep when known, total
   and stage elapsed time, last progress/log activity, connection/observation freshness,
   and a log tail with access to the first actionable failure. Process liveness and
   log activity are separate from verified progress and successful completion. A quiet
   tool is not automatically hung; loss of observation is not completion. Do not invent
   percentage complete or ETA without meaningful project/tool evidence.
6. **Compact design summary:** standard-cell area and utilization from existing
   collected results. Cell/FF/memory/macro counts, die/core area, and routing/congestion
   summaries may be added when already available with clear stage/unit context.

Timing and metrics are the **latest available measurements for a named run/stage**,
not continuously measurable quantities. While a new run has no timing result, show
pending; an explicitly labeled previous-result reference may remain visible. Never
present previous timing as a fresh measurement of the running or edited design.

The dashboard must launch a full flow or explicitly selected supported steps, show
their requested extent, and offer existing cancellation/log navigation. The daemon
owns execution so detach/reattach does not launch duplicate work. Import/reopen a
selected project-owned stored result without executing the physical flow. This is
required now; a general daemon database and cross-run comparison UI are not.

Host CPU/RAM/free-disk and supervised-process resource usage are useful secondary
indicators, not completion evidence. Add them only after the flow/timing dashboard
works and if cheap to obtain. Power estimates require a meaningful activity/model
context and are not an initial gate. Full graph/waveform viewers, elaborate resource
analytics, and arbitrary dashboard customization remain parked.

### Release boundary

Release when the real scaf workflow can be launched and monitored, its persisted
results reopened, and timing/check evidence inspected in the TUI. Validate a real
physical run plus failure/cancellation and reattachment behavior. Structured
elaborated hierarchy and per-node reports are no longer release gates. Browser work,
Vivado workers, a second report backend, graph/waveform/overlay views, hardware/ILA,
GUI bridging, and distributed workers require a new explicit user need before
activation. Workstation-native attachment validation stays deferred. A general
durable history store is reconsidered only if reopening project archives is inadequate.

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
                       typed RPC / HTTP
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

### 1C discovery contracts (2026-09-20)

This section records the first bounded 1C slice: manifest validation and target/configuration
discovery. The later sections below define the delivered RTL/artifact and hierarchy slices.

**Manifest version 1.** `hardcaml-workbench.sexp` is optional. When present it is a sequence of
exactly these top-level forms, each required exactly once and with `lang` first:

```lisp
(lang hardcaml-workbench 1)
(project (name mac))
(dune
 (driver ./workbench/project_driver.exe)
 (build_alias @all)
 (test_alias @runtest))
```

`project.name` is a required, nonempty atom. `dune.driver`, `dune.build_alias`, and
`dune.test_alias` are optional and may occur at most once. Driver absence means valid
manifest-only integration. Build and test default to `@all` and `@runtest`; an invalid manifest
falls back to those safe generic actions and the name from `dune-project` or the root basename.
Unknown top-level forms or fields, duplicate forms or fields, malformed records, an unsupported
language name/version, and empty values invalidate the optional integration with a diagnostic
that names the file and field. Version 1 has no environment, FPGA, board, or default-target field.

Driver and alias values are Dune target references, never shell fragments. They must be relative,
contain no empty, `.` or `..` path component, and remain under the canonical project root after
lexical resolution. Aliases have the form `@name` or `path/@name`; the alias name is nonempty.
The driver has the form `./path` and is passed as one argv element to `dune exec`. Validation is
syntactic at manifest load; Dune remains authoritative for whether the declared target exists.
Build and test use `dune build --root ROOT --no-buffer REFERENCE`, so declared aliases are honored
without shell interpolation. A missing target is an ordinary supervised job failure.

**Driver protocol version 1.** This is a separate process protocol, not application protocol V1.
The daemon runs the manifest's executable as:

```text
dune exec --root ROOT --no-buffer DRIVER -- describe --protocol-version 1
```

in the session's explicitly selected environment. The process writes exactly one S-expression to
stdout, bounded to 1 MiB including Dune/driver output, and may write human diagnostics to stderr.
The response is generated/parsed as the following portable shape:

```lisp
((protocol_version 1)
 (capabilities (describe))
 (targets
  (((key counter) (name Counter) (top counter) (backend simulation)
    (clocks ()) (facts ()))))
 (configurations
  (((key default) (target counter) (name Default) (description ("8-bit counter"))))))
```

The response version must equal 1. `describe` must be advertised; absence is an unsupported
capability, distinct from a successful empty target list. Unknown capability atoms are retained as
forward-compatible advertisement and ignored by this client. Output that exceeds the limit,
contains diagnostic text around the S-expression, is malformed, has duplicate/invalid keys, or
references an unknown target fails discovery. Target/configuration keys are stable project-owned
ASCII identifiers matching `[A-Za-z0-9][A-Za-z0-9._-]*`; target and configuration keys are unique
in their respective namespaces. Names, top names, backend IDs, clock names, fact namespaces/names,
and fact values are data, not executable command fragments.

The daemon maps a target key to `<project-id>/target/<key>` and a configuration key to
`<project-id>/configuration/<key>`. These are deterministic for the lifetime of the
`(canonical-root, environment)` session and across refreshes in that session. They are not durable
cross-daemon identities. Configuration references are resolved only within the same describe
result, preventing data from one project session from entering another.

Driver build/execution is one daemon job and uses the existing process-group supervisor, log
store, cancellation owner, and per-root Dune FIFO. `dune exec` owns any required driver build, so
build failure, missing targets, driver nonzero exit, and cancellation have the normal job outcome
and diagnostic stream. Supervised build, test, and driver jobs from sessions for different
environments but the same canonical root share that root FIFO because they contend on the same
build tree. Different roots may run concurrently. Initial environment probes/workspace inspection
remain the bounded open operation from 1B and rely on Dune's own lock. No second subprocess runner
is introduced.

The initial open parses the manifest and, for a valid declared driver, queues discovery once.
Repeat-open and reconnect return daemon-owned cached state and never rerun it. The additive
capability-advertised application operation `refresh-integration` first reloads and validates the
manifest, then queues a new discovery job when it declares a driver; this permits repair after an
absent/invalid manifest or failed driver without restarting the daemon. It rejects a valid manifest
with no driver and a concurrent refresh. An absent or newly invalid manifest immediately publishes
generic fallback with safe aliases. Starting discovery sets driver status to unavailable with a
`discovery pending` diagnostic and clears targets/configurations. Success
atomically publishes the new driver status and summaries. Failure/cancellation publishes an
actionable unusable status and leaves summaries empty, so an old successful result is never shown
as current. Generic build/test remains available throughout and uses manifest aliases only while
the manifest is valid.

The project-result event is published before the corresponding discovery job becomes terminal,
including process-launch failure. Clients reduce ordinary incremental events into their current
snapshot in sequence order. An `open-project` response is bootstrap/request metadata and must not
supersede a newer project record received in the snapshot or event stream. Likewise, queued job
records returned by submit/refresh operations must not overwrite newer event-applied job states.
Full snapshots remain for initial attachment, retained-event resynchronization, and reconnect; they
are not the ordinary discovery-update mechanism.

No SDK is introduced for this slice. The request/response is small enough for a project driver to
emit with its existing S-expression support, and a library would create a version/dependency
coupling before repeated implementation has demonstrated useful shared code. Later operations may
reuse the framing and negotiation rules, but their detailed schemas are deliberately not reserved
or implemented now.

### 1C RTL generation and artifact contracts (2026-09-20)

This is the second bounded 1C slice. It adds client-local target/configuration selection, one
supervised RTL operation, daemon-lifetime artifact registration, and bounded content retrieval.
At this slice boundary it did not add an elaborated hierarchy model; the final 1C section below
defines the subsequently delivered portable hierarchy data.

**Selection.** Target and configuration selection is client-local view state. The daemon owns the
declared project summaries and the jobs/artifacts that cite them; it does not own a shared “current
target.” On first usable discovery a client selects the first target in driver declaration order and
the first configuration declared for that target. A target with no declared configuration is
visible but cannot be submitted for RTL generation. Explicit terminal controls cycle targets and
only the configurations belonging to the selected target. Changing target selects that target's
first configuration.

After a project event or reconnect, a client preserves IDs that still exist and still have the
declared target/configuration association. If the target disappeared it selects the first remaining
target; if only the configuration disappeared or moved it selects the first configuration for the
selected target. No available replacement means an explicit unselected state. Switching to a
different project session resets both selections. Validation in this slice means exactly that the
submitted session IDs resolve to currently declared summaries and that the configuration's
`target` equals the submitted target. Configuration values remain project-owned, named declarations;
there is no generic parameter editor or expression language.

**Driver operation.** Driver protocol version 1 gains the advertised `generate-rtl` capability and
a separate request/result envelope; the existing describe shape does not change. The daemon runs:

```text
dune exec --root ROOT --no-buffer DRIVER -- generate-rtl --protocol-version 1 \
  --target TARGET_KEY --configuration CONFIGURATION_KEY --output-dir JOB_OUTPUT_DIR
```

The one operation elaborates and emits RTL. A separate public elaboration job would add no useful
lifecycle or result in this slice. The target and configuration are project-declared keys recovered
from the currently discovered session summaries, never client-supplied command fragments. The
driver must reject unknown keys and mismatched associations. The daemon rejects stale IDs before
queueing and validates them again immediately before execution, so a refresh queued ahead of the
operation can invalidate it consistently. Absence of `generate-rtl` is an explicit unsupported
operation and does not affect generic Dune build/test.

The result is exactly one S-expression on stdout, bounded by the existing 1 MiB driver stdout
limit; diagnostics remain on stderr. It repeats protocol version, target key, and configuration key,
declares a bounded nonempty list of output records, reports actual tool versions when known, and may
carry project-supplied backend build/run references. An output record contains a relative path,
backend-neutral artifact kind fields, display name, and optional description. RTL bytes never enter
the result envelope. Unknown fields are not accepted in version 1. A process exit of zero is only a
successful process outcome: malformed/incompatible results, key disagreement, duplicate or invalid
paths, missing/non-regular output files, output-boundary escapes, import failures, or registration
failures make the job fail.

**Handoff and storage.** Before launch, the daemon creates a private job output directory outside
the project root and passes only that destination to the driver. Each declared output must be a
normalized relative path with no empty, `.` or `..` component. The daemon resolves it under the
canonical job destination, rejects symlinks and non-regular files, opens it without treating a
client-visible path as authority, and copies it into a fresh daemon-owned artifact file. Each run
mints new artifact IDs and storage names, so a later run cannot overwrite an earlier registered
output. Driver scratch/output directories are removed after processing; imported artifact content
lasts for the daemon lifetime and is removed on daemon shutdown.

Registration is all-or-nothing for this operation. The daemon validates and imports every declared
output before publishing any artifact. On failure or cancellation before registration it removes
staged files and registers none. Successful registration is the commit point: a cancellation request
received from a registration event cannot turn the committed result into a cancelled job.
After successful import the daemon stores all artifacts, updates the generating job with their IDs,
then emits artifact upserts and the updated job before the terminal successful job event. This makes
the snapshot/event stream self-consistent when completion is advertised. Build/run references are
copied only when the driver supplies them; Workbench does not invent them.

**Application operations.** Application protocol V1 gains two additive, capability-advertised
operations without changing an existing wire shape:

- `generate-rtl`: daemon instance, project ID, target ID, configuration ID, and nonempty submission
  key in; the queued job out. Submission keys use the existing daemon-lifetime idempotency rule and
  conflict if reused for another exact selection.
- `read-artifact`: daemon instance, artifact ID, byte offset, and requested byte count in; bytes,
  next offset, total size, and EOF out. Reads are at most 256 KiB. Negative/future offsets, zero or
  oversized limits are invalid requests; unknown IDs are not found; registered metadata whose
  private content is missing returns not found and is marked unavailable before the response.

Snapshots and `Artifact_upsert` events carry metadata only. Content access is always by artifact ID;
no client receives a storage path as a handle. An artifact remains readable after the submitting
client exits and appears in same-daemon reconnect snapshots. Durable restart recovery remains 2C.

**Provenance.** Provenance is captured for the exact submitted target/configuration, not the
client's later selection. At execution start and again after the driver exits, the daemon records
Git HEAD and working-tree state when Git is available and computes a deterministic SHA-256 over the
project-relative path, mode category, and bytes of regular project files, excluding `.git`, `_build`,
and the daemon-owned output/store directories. Equal boundary hashes prove that those observed file
sets and bytes agreed at both boundaries; they do not prove that no file changed transiently during
execution, identify external package contents, or make the environment reproducible. Different or
failed boundary captures produce an honest unknown source identity rather than choosing one side.
A dirty tree retains its commit only as context, not as an exact source identity. Non-Git roots have
no commit but may still have a boundary hash. `preserved_inputs` remains empty in this slice, so the
hash is evidence, not a stored reconstructable source bundle.

Artifact provenance records the canonical project root identity, target/configuration, generating
job, registration time, selected environment description, Dune version, driver protocol version,
and actual OCaml, Hardcaml, driver, or RTL tool versions reported by the project driver. Missing
versions stay unknown. An opam switch name identifies only the selected execution context and is not
claimed to describe all installed packages, variables, licenses, or external tools. Source capture
occurs at execution boundaries rather than submission, because a queued operation has not consumed
the source yet; a queued refresh can also invalidate the submitted IDs before launch.

A small `hardcaml_workbench_project` SDK may help external projects declare targets and
implement the driver protocol. It is project-integration code, not synthesizable hardware,
and projects must remain usable through their ordinary Dune commands without launching the
Workbench.

### 1C elaborated hierarchy contracts (2026-09-20)

This final 1C slice exports the structural instance hierarchy produced by the same project-side
Hardcaml elaboration that emits RTL. It is deliberately smaller than Phase 3's signal/operator
graph: a hierarchy contains instance occurrences, parent relationships, logical instance and
circuit names, module input/output port names and widths, and small project-supplied metadata.
Source locations, signal connectivity, operators, registers, memories, clock/reset classification,
and report metrics are absent unless a later version explicitly supplies them. The daemon never
infers any of these facts from Verilog or from the Dune workspace.

**Driver capability and handoff.** Driver protocol version 1 retains its frozen describe and
`generate-rtl` response shapes. A hierarchy-capable driver additionally advertises
`generate-rtl-hierarchy`. This capability means that every successful `generate-rtl` invocation
declares exactly one output with kind `hardcaml/elaboration-hierarchy`, role `report`, and media
`application/x-hardcaml-workbench-hierarchy-sexp`. The output is a version-1 hierarchy sidecar in
the existing private output directory. It is capped at 8 MiB and never enters driver stdout. A
driver advertising the capability but omitting, duplicating, or returning a malformed hierarchy
fails the complete generation operation, and no RTL or hierarchy artifact is registered. A driver
without the capability remains fully usable for describe and RTL generation; hierarchy retrieval
for its RTL result reports unsupported rather than invalidating that result. A hierarchy output
from a driver that did not advertise the capability remains an ordinary opaque artifact.
The daemon pins the selected driver path and advertised capability into the queued generation
operation; a concurrent integration refresh cannot switch the executable or reinterpret an
in-flight result after its execution has started.

RTL and hierarchy therefore come from one process, one source observation interval, and one
elaboration. They share the Workbench project, target, configuration, generating job, optional
backend build/run references, environment, tool versions, source identity, and creation time. The
daemon imports the sidecar as an immutable artifact alongside the RTL and registers its decoded
structured result only after every output has validated and copied successfully. The hierarchy
result cites its hierarchy artifact and all RTL artifacts from that job. Artifact and structured
result registration precede the job's successful terminal update. Failure or cancellation exposes
neither partial artifacts nor a partial hierarchy.

**Portable representation.** The driver sidecar repeats protocol version, target key,
configuration key, root structural key, and a flat bounded node list. Each node has:

- a structural key and optional parent key;
- an optional logical instance name (`None` only for the root) and a circuit/module name;
- input and output ports, each with a nonempty name and positive bit width; and
- bounded `(name, value)` metadata for facts such as an unresolved/black-box implementation.

The application result adds its hierarchy artifact ID, project/target/configuration IDs, generating
job, RTL artifact IDs, and artifact provenance. A separate additive `read-hierarchy` application V1
operation accepts the daemon instance and hierarchy artifact ID and returns that result. Hierarchies
are not added to snapshots or incremental events: the small artifact metadata and the generating
job's existing artifact IDs advertise availability, while a client fetches the potentially large
tree explicitly. Same-daemon reconnect recovers it without elaboration replay. Durable restart
recovery remains milestone 2C.

The sidecar allows at most 10,000 nodes, depth 256, 4,096 ports or metadata entries per node, and
4,096 bytes per key/name/value. Validation requires exactly one root, the declared root to exist
and have no parent, every other parent to exist, every node to be reachable exactly once from the
root, unique structural keys, no cycles, unique sibling instance names, and no duplicate port or
metadata names within a node. Invalid UTF-8 is not assigned extra semantics: names are S-expression
strings and treated as bytes for identity and display truncation.

**Structural identity.** An instance key is its elaborated occurrence path, not a module name,
signal UID, random ID, or traversal position. The root key is `/`. Every child segment is encoded as
`<decimal-byte-length>:<logical-instance-name>` and appended to its parent key after `/`; for example
`/11:u_counter_0`. Length-prefixing makes `/`, `:`, spaces, and arbitrary bytes in names
unambiguous. Duplicate logical instance names under one parent would produce the same path and are
rejected rather than disambiguated by visit order. Repeated instances of one circuit consequently
have distinct keys whenever their project-owned instance names differ.

For a deterministic elaboration that preserves logical instance names and parentage, structural
keys repeat across jobs and daemon restarts. They may also repeat across configurations whose
structure is unchanged, but this is not promised when configuration changes hierarchy or naming.
Every key is interpreted only inside its hierarchy artifact/result; the artifact ID plus key is the
unambiguous application reference. Workbench project, job, and artifact IDs remain daemon-session
identities and are intentionally separate. Hardcaml's circuit database stores module definitions;
the driver traverses each parent's actual `Circuit.instantiations`, resolving child circuits through
that database, so repeated occurrences are preserved. An unresolved instantiation is retained as a
leaf with explicit unavailable implementation metadata rather than fabricated children.

**Current versus historical presentation.** Target and configuration selection remains
client-local. For the current selection, the newest generation attempt is authoritative: queued or
running means pending, failure/cancellation is shown as such, and an older successful hierarchy is
not silently substituted. A completed hierarchy-capable result is current only when its exact
target/configuration matches the selection and its generating job is that selection's newest
generation attempt. A user may explicitly inspect any historical generation job; the terminal
labels its job, target, configuration, and historical status. Expansion, selected
node, and tree scroll are client-local. Refresh can remove declarations without rewriting immutable
historical results.

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

- project, target, configuration, job, artifact, and hierarchy structural identities,
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
selection, layout, and scroll position are per-client. The protocol decisions below define reconnect behavior and daemon-owned cancellation;
client selection, layout, and scroll position never become shared session state.

### 1A application protocol decisions (2026-09-19)

These decisions define the implemented 1A foundation. Optimize for a modest local task
runner with a terminal client first and a browser client later.

**Transport and runtime.** Use HTTP/1.1 on `127.0.0.1`, typed S-expression request/response
bodies, and long polling for incremental updates. Use Async and `cohttp-async` for the native
server and client; the browser will use its HTTP API with the same portable codecs.
[Cohttp provides an Async client/server implementation](https://github.com/mirage/ocaml-cohttp).
Exact compatibility with this repository's switch must be checked during implementation;
this decision does not claim the dependency is installed or tested. No WebSocket, custom TCP
framing, or binary RPC layer is required for Phase 1. Existing `bin_io` derivations can remain,
but the application wire format is `sexp`.

Freeze wire definitions under a versioned `Protocol.V1` module rather than serializing mutable
internal records without a version boundary. Encode one S-expression per HTTP body with
`Content-Type: application/sexp`; use the existing generated parsers/printers, not hand-written
string interpolation. HTTP supplies message framing. Treat log contents as bytes (escaped by
the S-expression codec); decode for display with replacement for invalid UTF-8.

**Endpoints and compatibility.** `GET /api/hello` returns a fixed bootstrap record containing
application version, supported protocol versions (initially `[1]`), daemon instance ID, and
capability names. Each daemon start creates a new instance ID. Every subsequent API call is
`POST /api/v1/<operation>` with a typed body containing the expected daemon instance ID.
Reject a mismatched instance before acting. Clients refuse unsupported protocol versions
with a useful error; build versions need not match when the protocol version does. Additive
operations are advertised by capability; changing existing wire shapes requires a new
protocol version. The project-driver protocol remains separately versioned in 1C.

Use an operation module with paired request/response types and a shared typed error record
for each endpoint. The native and browser transport wrappers expose these typed operations,
not an untyped dispatch interface to UI code. HTTP 200 contains a typed success/error result
for a decoded operation. Malformed input, unknown endpoint/version, and oversized requests
use 400, 404, and 413 respectively, with the common error envelope where possible. Common
errors include invalid request, unsupported operation, not found, conflict, instance changed,
and internal failure. Catch decoding failures at the boundary; never return native exception
traces as application results. Initially cap request bodies at 1 MiB and log response payloads
at 256 KiB; these are server limits, not new wire versions.

| Operation | Contract and milestone |
| --- | --- |
| `hello` | Bootstrap and compatibility information; 1A. |
| `snapshot` | Full current project/job/artifact metadata plus an atomic event cursor; 1A may return empty collections. No log bodies or artifact contents. |
| `updates` | Cursor in, bounded ordered event batch and next cursor out; may wait up to 25 seconds. 1A supports an empty heartbeat. |
| `open-project` | Root and explicit environment selection in, daemon-owned project summary out; implemented in 1B. |
| `submit-job` | Project ID, typed supported action, and submission key in, job snapshot out; implemented in 1B. |
| `cancel-job` | Job ID in, current job snapshot out; implemented in 1B. |
| `read-log` | Job ID and record offset in, bounded stdout/stderr records, next offset, and EOF flag out; implemented in 1B. |
| `refresh-integration` | Project ID in, queued driver-discovery job out; implemented in 1C. |
| `generate-rtl` | Project, target, configuration, and submission key in, queued generation job out; implemented in 1C. |
| `read-artifact` | Artifact ID and bounded byte range in, content page and EOF metadata out; implemented in 1C. |
| `read-hierarchy` | Hierarchy artifact ID in, associated immutable structural hierarchy result out; implemented in 1C. |

The milestone annotations record when each row became implemented; additive operations are
capability-advertised. Artifact content remains outside snapshots and uses its dedicated bounded
response. Root input is an explicit exception
to opaque-ID access: it denotes a path on the daemon's machine, never a client-side file handle.

**Updates and reconnect.** Use a single daemon-wide monotonically increasing event sequence
paired with the daemon instance ID. Capture a snapshot and its cursor atomically relative to
state mutations; updates after that cursor must include every subsequent mutation. Events
carry entity upserts/removals and log-available notices. Send full changed entity records
initially; no field-level patch language is needed. Clients apply events in order, ignore
already-applied sequence numbers, and resume from the last applied cursor. A bounded
in-memory event ring is enough (initial limit: 4096 events). If the cursor predates retained
events, return `Resync_required`; the client gets a fresh snapshot. Reject future cursors.
An empty timeout response retains the cursor. Canceling a poll affects only that HTTP request.
Slow clients must not block processes or grow an unbounded queue.

Logs live separately in daemon-owned files for the daemon session. Assign ordered record
offsets per job, with stream tags; ordering means observed capture order, not inferred causal
ordering between stdout and stderr. `read-log` pages from an offset; `updates` only announces
availability. A refreshed snapshot lets clients rediscover jobs and resume their log offsets
after event retention expires. EOF means both process output streams have closed and all
captured records are available. Logs and metadata need not survive a daemon restart until
2C; reconnecting to the same daemon must recover them.

Use reconnect backoff starting at 250 ms and capped at 5 seconds. A new daemon instance
invalidates previous cursors and session IDs; show that the session restarted, then fetch a
new snapshot. Never replay job submission automatically across daemon instances. Within one
instance, a submission key identifies one request: atomically store its action and resulting
job ID before starting the process; retrying the same key/action returns that job, while
reusing it with a different action is a conflict. Retain keys for the daemon lifetime. Ordinary
reconnection fetches state; it does not submit work. Any attached client may request
cancellation, but only the daemon supervisor performs it. Repeated cancellation is harmless;
a terminal job keeps its recorded outcome. Closing a client never cancels jobs.

### 1B generic-project and job decisions (2026-09-20)

These decisions complete the milestone 1B rows in the construction plan without changing an
existing V1 wire shape.

**Roots and sessions.** `open-project` accepts an absolute or relative directory path on the
daemon machine. The daemon resolves it with `realpath`, requires an existing directory and a
regular `dune-project` file directly in that directory, and stores the canonical absolute root.
Symlink spellings and paths containing `..` therefore identify the same root. One daemon has
one project session per `(canonical root, environment selection)`: repeating the same open
returns the same project ID and cached inspection without starting Dune again; selecting another environment creates a
separate session because its Dune view and jobs can differ. Opening never searches parents and
never modifies the project.

**Execution environments.** Selection is mandatory in the typed operation and is one of:

- `Inherit_daemon`, meaning the exact environment inherited when the daemon started; or
- `Opam_switch <name>`, executed as `opam exec --switch=<name> --set-switch -- <argv>`.

The response displays the selection, provenance (`daemon process` or the named opam switch),
resolved Dune version, and command prefix. The inherited choice is deliberate rather than a
fallback. A missing `opam`, unknown switch, missing `dune`, or failed probe rejects the open;
the daemon never substitutes the switch used to build Workbench. This milestone records and
uses environments but does not create, install, or mutate them. Secrets and the full native
environment are not exposed.

**Dune inspection.** The supported implementation is Dune 3.22 or newer, validated with
3.24.2. Inspection runs `dune describe workspace --root <root> --format=sexp --lang=0.1`
inside the selected environment and parses the versioned S-expression. The response exposes
generic workspace entries (library, executable, tests, and other Dune item kinds) and context
names; these are workspace structure, never inferred Hardcaml hierarchy. Dune RPC is not used
because Dune 3.24.2 labels it experimental and says not to use it. Build and test translate to
`dune build --root <root> --no-buffer @all` and
`dune runtest --root <root> --no-buffer`, with plain argv, no shell. `--no-buffer` lets action
output reach the supervisor before completion. Inspection probe or parse failure rejects the
open with bounded diagnostic text. Later Dune
formats require an explicit adapter update rather than permissive guessing.

**Compatibility.** Existing `Project.t`, `Job.t`, snapshot, and event shapes remain frozen.
V1 gains additive capability-advertised operation modules. `open-project` returns a project
plus its environment and workspace inspection; repeat-open retrieves refreshed details.
Snapshots and entity events carry the existing stable summaries. A future need to persist
workspace details in snapshots requires a new protocol version, not a silent record change.

**Scheduling and ownership.** The daemon owns project sessions, jobs, submission keys,
processes, process groups, log files, state transitions, and event order. Each project session
has a FIFO queue and at most one running Dune job, avoiding nondeterministic contention on
Dune's build lock. Different sessions may run concurrently. Jobs pass through queued,
starting, running, and one terminal state. Clients own only focus, selection, layout, scrolling,
and consumed log offsets. Any attached client may request cancellation; the supervisor is the
only component that signals processes.

**Processes and logs.** The adapter returns an executable, argv, working directory, and
environment selection. The supervisor starts a fresh process group, captures stdout and stderr
concurrently, and records chunks in observed callback order. Cancellation sends `SIGTERM` to
the group, drains output for a bounded interval, then sends `SIGKILL`; daemon shutdown first
rejects new work and applies the same sequence to every active group. Exit/cancel races settle
once, and descendants share the group. Client disconnection has no process effect.

Logs are append-only files in a private per-daemon temporary directory. An in-memory index
contains only record offsets and byte locations, so output volume is not retained in memory.
`read-log` returns at most 256 records and 256 KiB from an ordered record offset, preserves
stdout/stderr tags and bytes, returns the next record offset, and reports EOF only after both
pipes close and the process is reaped. Log bodies are absent from snapshots and events;
`Log_available` announces only the next offset. Log files and submission keys last for the
daemon instance and are removed at shutdown; durable restart recovery remains milestone 2C.

**Terminal resize behavior.** The 1A black-screen regression was a missed invalidation, not a
terminal, tmux, or signal-delivery failure. The client ignored Bonsai Term's `dimensions`
input and returned one physically identical `View.t`; Bonsai Term therefore skipped
`Term.image` after `SIGWINCH`. The switch's `notty-community` line-diff patch additionally
retains its previous-line cache in `Tmachine.set_size`, so forcing only a nominal view change
can still omit unchanged lines after a width-only resize. The repository does not patch the
shared switch. Its reproducible workaround makes the view depend on current dimensions and
places content over a real terminal-sized space rectangle. This changes Notty's operations
for width and height changes and repaints the resized alternate screen. Below 68 columns or
20 rows the client renders a clipped, recoverable “terminal too small” view. Optional
diagnostics append dimensions and caught errors to a file, never to the active terminal.
The upstream fix would require both Bonsai Term to render after resize regardless of physical
view equality and the patched Notty `Tmachine.set_size` to invalidate `previous_lines`.

**Local HTTP trust.** Preserve section 4.4's same-user local/SSH trust boundary without adding
accounts or tokens. Require the non-simple `X-Workbench-Protocol: 1` header and the specified
content type on all POST operations. Do not enable CORS; reject cross-origin browser requests
and reject a supplied Origin unless it matches the loopback Host authority, including port.
Validate Host as a literal loopback address or `localhost` (with its port), rejecting arbitrary
DNS names. Native clients may omit Origin. This blocks ordinary websites from invoking the
local command API; it does not isolate mutually untrusted local users. Serve browser assets
from the daemon's origin in 1E. SSH forwarding can use a different local port.

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

For the daemon-lifetime 1C implementation, private content is copied out of a driver's job-specific
output directory into a newly named store file before registration. Metadata and private locations
are held in the daemon's artifact repository; snapshots/events expose only the metadata. Reads are
bounded byte pages through the application protocol. Registration never points at a mutable project
build path, and repeated jobs retain distinct outputs. See the concrete handoff, validation,
partial-output, cancellation, retrieval, and reconnect rules in section 4.1's 1C RTL contracts.

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

The 1C RTL slice records a deterministic SHA-256 source-tree observation at execution start and end
but does not yet preserve a source bundle. This narrows accidental misattribution and detects normal
queued/running edits, while leaving a documented reproducibility gap: equal endpoint observations do
not exclude transient edits and do not identify external dependencies. A later durable history or
backend build bundle may populate `preserved_inputs`; it must not reinterpret this hash as proof of
a complete environment.

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

The active MVP is the [protemu monitoring release](#active-release-scope--protemu-monitoring-2026-09-20).
The construction plan's D1–D4 slices define its acceptance checks. The earlier
general-purpose checklist below is retained as historical scope, not a release gate.

## Earlier Phase 1 baseline (superseded as the active gate)

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

Hierarchy and node inspection from this baseline are deferred until the real workflow
needs them; the staged report dashboard does not depend on them.

Stating item 6 in terms of the project's reporting path rather than one library keeps the MVP
gate reachable without a Vivado installation, and keeps the first useful Workbench available
to an ASIC project. Vivado's own integration begins in Phase 2, where it belongs.

---

# 21. Phase 2

Parked, subject to an explicit workflow need rather than automatic implementation:

- persistent Vivado process,
- synthesis/implementation jobs,
- structured report parsing,
- timing summary page,
- utilization page,
- generated RTL viewer using CodeMirror,
- run history.

---

# 22. Phase 3

Parked, subject to an explicit workflow need rather than automatic implementation:

- Hardcaml elaboration graph,
- hierarchy drilldown,
- signal search,
- fan-in/fan-out inspection,
- waveform viewer,
- timing-path overlay,
- design comparison.

---

# 23. Phase 4

Parked, subject to an explicit workflow need rather than automatic implementation:

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
| Native HTTP client | `hardcaml_workbench_native_http` | shared protocol, Async, Cohttp, `core`, and `core_unix` |
| Native daemon transport | `hardcaml_workbench_rpc_server` | shared protocol, Async, Cohttp, and `core` |
| Native daemon | `hardcaml-workbench-daemon` | shared protocol, native transport, backend, adapters, `core`, and `core_unix` |
| Terminal client | `hardcaml-workbench` | shared protocol, native HTTP client, Async, Bonsai, and `bonsai_term` |
| Browser frontend | `web/main.bc` initially; `web/main.bc.js` in 1E | shared protocol, `core`, `bonsai`, and `bonsai_web` |

The protocol and project-integration libraries remain free of `core_unix` and operating-system
resources. The web executable has no dependency path to the backend or adapters. The initial
structure-only target builds bytecode to validate that dependency graph; it is not a browser
deliverable. Promote it to a js_of_ocaml target in 1E for the browser and JavaScript protocol gate. The daemon and web executable remain private build targets, and the
package is explicitly allowed to have no install stanzas, until the installation task adds the
launcher and asset rules.

Application build dependencies such as `core_unix`, Bonsai, and js_of_ocaml are normal package
dependencies rather than test-only dependencies. Test frameworks remain conditional on tests,
and formatter/linter packages remain development-only. The application package itself does not
depend on Hardcaml circuit libraries or `ppx_hardcaml`: circuit dependencies belong to the
independent fixture and opened projects. Add a project SDK only if the 1C driver work demonstrates
that it is useful, and keep it separate from circuit ownership. Transport/server packages are
selected in section 4.3; add and validate them during the remaining 1A implementation.

### 1A launcher, installation, and fixture decisions (2026-09-19)

Install two native executables: `hardcaml-workbench` (the `bonsai_term` client plus local
startup orchestration) and `hardcaml-workbench-daemon` (the server). Keep their libraries
private. Add `terminal/` and a private native HTTP client library; neither may depend on
backend, adapters, or project integration. The shared protocol contains only portable types
and codecs; Async/Cohttp transport code belongs outside it. The terminal may depend on
`bonsai_term`, Async, and the native HTTP client. The daemon links the server, backend, and
adapters. The launcher may spawn the installed daemon executable, but only the daemon starts
project tools.

The planned CLI is:

- `hardcaml-workbench [--project-root ROOT]`: attach to the user's default local daemon,
  starting it when absent, then enter the terminal UI.
- `hardcaml-workbench --connect http://127.0.0.1:PORT [--project-root ROOT]`: attach to the
  specified endpoint (including an SSH forward); never start a replacement daemon on failure.
- `hardcaml-workbench-daemon --port PORT`: run in the foreground, suitable for a service
  manager; port 0 requests an ephemeral port. Loopback binding cannot be overridden.

The root is interpreted on the daemon's machine. In 1A retain it as the pending open request
and show that project opening is unavailable; 1B sends `open-project`. Omitting it opens the
shared session view without implicitly choosing the client's working directory.

For automatic local startup, use a user-private runtime directory under `XDG_RUNTIME_DIR`,
falling back to `XDG_STATE_HOME/hardcaml-workbench` (default `~/.local/state/hardcaml-workbench`).
Use owner-only directory/file permissions. Serialize startup with an OS advisory lock; the
auto-started daemon holds a separate lifetime lock. It binds port 0 and atomically publishes
endpoint, instance ID, and PID only after it can answer `hello`. Probe readiness with a
10-second deadline. Validate the instance ID when attaching; a PID alone is not evidence of
identity, and stale metadata is never a reason to kill a PID. If the lifetime lock is held
but readiness fails, report the failure instead of spawning a second daemon. Manually
launched daemons need not participate in default-daemon discovery.

Launch the automatic daemon in a separate session with stdin detached and diagnostics in the
private runtime directory, so terminal exit or hangup does not stop it. The daemon persists
until explicitly stopped. On SIGINT/SIGTERM, stop accepting work, cancel supervised process
groups, drain output with a bounded grace period, then force termination and exit. Phase 1
does not recover jobs after daemon exit. Do not add idle shutdown, a service installer, or a
remote-daemon lifecycle manager in 1A.

The installed client locates its sibling daemon relative to the installation's executable
directory, with an explicit development override for build-tree use; it must not depend on
the checkout or launch the Workbench switch wrapper. Validate installation into a temporary
prefix and launch from an unrelated directory. Document actual development commands only
once implemented.

Keep the native application as `hardcaml_workbench`; make browser packaging a separate
optional `hardcaml_workbench_web` package in the same repository when packaging is implemented.
Move browser-only dependencies out of the native package so its build/install gate does not
require the browser toolchain. The web package will install precompiled assets under its
package share directory in 1E; missing assets leave terminal use available. Preserve the
browser/shared dependency boundary and run native protocol checks now. Require an actual
JavaScript codec build and round-trip execution in 1E; a bytecode build or compilation-only
probe is not that check.

The 1A implementation creates both generated package descriptions now so the native package
has no browser-only dependencies. `hardcaml_workbench_web` remains an empty packaging boundary
until 1E installs real assets. The native client also provides `--plain` for deterministic
non-TTY validation; this changes only presentation and performs the same typed exchange as the
interactive Bonsai Term view. `--discovery-dir` is a daemon-internal launcher argument, not a
remote lifecycle interface.

Create the deterministic fixture under `test/fixtures/example_project`, excluded from the
Workbench workspace (for example with Dune's `data_only_dirs`). Copy it into a temporary
external directory for every integration run. Give it its own `dune-project`, a tiny Hardcaml
counter, and a deterministic passing test. Its dependencies belong to the fixture. Select an
existing fixture environment explicitly in the harness; it may be the same installed switch
as Workbench, but must never be selected implicitly. Do not install dependencies or introduce
a manifest/driver for the 1A fixture. Record the environment and ordinary Dune build/test
commands as exit evidence.

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
