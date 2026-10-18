---
id: WB-066
title: Shared OCaml simulation provider library
category: verification
feature_sets: [FS2, FS3]
status: proposed
kind: feature
priority: P2
severity: n/a
requested_size: Unspecified
size: L
points: 21
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [simulation, provider, packaging, ocaml]
depends_on: []
related: [WB-034, WB-039, WB-035]
---

# WB-066 — Shared OCaml simulation provider library

## Request
Move project simulation providers from Python to OCaml. Workbench publishes a small
provider library that projects link against, so a project's
`hardcaml-workbench-simulation.sexp` names a native provider executable instead of
`python3 provider.py`.

## Current baseline
The FS2 v1 provider contract is frozen and language-neutral: an absolute executable,
prefix arguments, `discover`/`run` argv and LF-terminated S-expression events. The
contract already notes that OCaml providers can emit
`Simulation.Provider.Event.sexp_of_t |> Sexp.to_string_mach`.

No project can do that today:
- The wire types live in `hardcaml_workbench_protocol` and the daemon's provider
  validators in `hardcaml_workbench_project_integration`. Neither library has a
  `public_name`, so neither is installed.
- Making them public inside the `hardcaml_workbench` package would still make every
  provider install that package and its daemon/terminal dependencies (Async,
  cohttp, Bonsai, Notty).
- `Simulation.Selection` reaches `Run_ref` (via `Asic_input`), and `Run_ref` reaches
  `Backend_id`/`Build_ref`. Other `Simulation` modules (`Captured`, `Parent`,
  `Attempt`, RPC types) depend on `V1` and `Job_id`, which providers do not need.

Every real provider is Python with its own copy of the codec:
- `hardcaml_asic_example/simulation/{provider.py,wire.py}` wraps `fifo_sim.exe`.
  `scripts/install-fifo-simulation.py` copies all three into
  `.dev/fifo-simulation/<generation>/`, and the root config runs `/usr/bin/python3.12`.
- `examples/fs2_cyclesim/provider.py` uses `scripts/fixtures/fs2_wire.py` from the
  Workbench checkout.
- `demo/synthetic_flow/simulation_{provider,wire}.py` is the synthetic demo provider.

Each codec handles sexp escaping, record strictness and request validation (seed
canonical uint64, unique declared cases, parameter choices) by hand. `wire.py` says
it was adapted from the protocol on 2026-10-17, and nothing detects drift after that.
JSON string escaping is only safe for ASCII, as the contract warns.

## Scope
- Publish a provider-facing opam package (working name `hardcaml_workbench_provider`)
  that depends only on `core`, `core_unix` and `ppx_jane`. It contains:
  - The provider-visible wire types: `Parameter`, `Case`, `Suite`, `Discovery`,
    `Selection`, `Asic_input` and its references, `Progress`, `Case_status`,
    `Outcome` and `Provider.{Request,Artifact,Event}`.
  - The pure validators `validate_discovery`, `validate_selection`, `validate_event`
    and `parse_event_line`, plus the `Limits` they enforce.
- Make the daemon consume that package so that daemon and providers share one
  definition. `Hardcaml_workbench_protocol.Simulation` re-exports the moved types,
  and their sexp and bin_io encodings stay byte-identical.
- Provide a runner that owns the boilerplate:
  - It parses the `discover`/`run` argv, checks `--protocol-version 1` and reads and
    validates the request against the provider's own discovery.
  - It hands the provider an event emitter that numbers events in order, validates
    each one, writes it as one line and flushes it.
  - It maps the provider's exceptions or errors to a non-zero exit and a stderr
    message.
  - Its typed helpers cover what providers repeat: the four-word little-endian seed
    split, artifact paths under the artifact directory, and running a child
    simulator while forwarding its stdout lines.
- Port the FIFO provider in `hardcaml_asic_example` to an OCaml executable built with
  this library. Update its installer to copy the native provider instead of
  `provider.py`/`wire.py`, and write a config with an empty or simulator-only
  `provider_args`.
- Port `examples/fs2_cyclesim` the same way, which removes its dependency on the
  checkout's fixture codec.
- Update `docs/fs2_simulation_contract.md` and the example READMEs so the library is
  the recommended path, and keep the language-neutral contract as normative.

## Out of scope
- Changing the FS2 v1 contract, argv, event grammar, limits or daemon reducer rules.
- Removing the Python fixtures used by `scripts/test-fs2-*.py` or the synthetic
  demo. They stay as independent, foreign-language conformance checks.
- Building or installing providers automatically from discovery or run (still
  [WB-039](../project/WB-039-simulation-setup.md)'s boundary).
- Embedding simulation in-process (Cyclesim inside the provider) where projects
  currently shell out to a separate simulator. Projects may choose this later.

## Acceptance criteria
1. A fresh project can build a provider with only the new package and its
   core/core_unix/ppx_jane dependencies installed, without `hardcaml_workbench`.
2. Daemon tests pass unchanged. A round-trip test proves that every moved type keeps
   its prior sexp and bin_io encoding.
3. The ported FIFO provider's discovery output equals the Python provider's catalog
   once both are parsed.
4. For the same request, the FIFO provider's event stream matches the Python one
   event for event after canonical sexp parsing. This covers directed, seeded,
   maximum-uint64 seed and `checker mismatch` runs.
5. Both ported providers pass discovery and runs through the real daemon, and the
   persisted attempt history and artifacts look the same as before the port.
6. The runner refuses invalid requests (unknown case, duplicate case, non-canonical
   seed, unknown parameter choice, unexpected ASIC inputs) with a non-zero exit
   before it emits any event.
7. The emitter cannot produce an event that `parse_event_line` would reject. A test
   covers non-ASCII and control characters in messages and labels.
8. The FIFO installer refuses to mix a native provider with stale `provider.py`
   companions, and its config never references a Python interpreter.

## Dependencies
No additional prerequisite tickets. This builds on the delivered FS2 contract and
[WB-034](WB-034-fifo-adapter.md)'s FIFO provider. [WB-039](../project/WB-039-simulation-setup.md)
setup assistance could later default to a native provider path.
[WB-035](WB-035-generated-rtl-simulation.md) adapters are likely early users.

## Estimate rationale
21 points, L, medium confidence. The estimate covers:
- extracting the provider-facing types without changing their encodings;
- separate opam packaging;
- the runner and helpers;
- two provider ports with equivalence tests;
- the installer change.

Most of the uncertainty is in packaging. The OCaml port itself is small.

## Assumptions and decisions needed
- **Default:** a separate opam package in this repository, released alongside
  `hardcaml_workbench`. **Decision:** confirm the package name, and whether projects
  pin it from the checkout or wait for it to be published.
- **Default:** projects that do not want any Workbench dependency keep vendoring a
  codec. The library is recommended, not required.
- **Decision:** whether the FIFO provider stays a separate executable that shells out
  to `fifo_sim.exe`, or `fifo_sim` links the runner and becomes the provider itself.
  Defaulting to separate keeps the native report/stdout behavior unchanged.
- **Assumption:** all projects build in the same `5.2.0+ox` switch as Workbench.
  Supporting other OCaml versions would widen the test matrix.

## References
- [Provider contract](../../fs2_simulation_contract.md)
- [Wire types](../../../protocol/simulation.ml)
- [Daemon validators](../../../project_integration/simulation_protocol.ml)
- [Simulation configuration parser](../../../project_integration/simulation_config.ml)
- [Testing workspace / FIFO generation](../../testing_workspace.md)
- [Cyclesim example](../../../examples/fs2_cyclesim/README.md)
