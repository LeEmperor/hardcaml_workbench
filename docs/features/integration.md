# F01 — Project integration and capabilities

Status (2026-10-16): **FS0 public ASIC adapter and FS1 adopted-evidence integration
delivered**, alongside generic Dune and driver integration. Public named-flow
launch, durable observation/read/report, capability-checked physical endpoints,
finalization collect/accept and read-only rich inspection are implemented.
See [FS0 limits](../fs0_provider_integration.md),
[FS1 lifecycle](../fs1_lifecycle_and_artifacts.md) and
[FS1 investigation](../fs1_investigation.md) for exact contracts, installed provider
generation and evidence. Requirements below remain normative; broader provider-store
discovery is absent, later F06 graphics/source mapping remain open, and FS2 is unstarted.

## User outcome

Open an independent project and operate the capabilities it actually supplies.
Neither Workbench nor `hardcaml_asic` becomes mandatory for ordinary CLI use.

## Requirements

- Generic Dune projects support inspection, build/test and logs.
- The simulation/test module (F09) starts on this generic test path. Optional
  simulation adapters can add cases/seeds/artifacts without requiring an ASIC flow.
- Static project configuration supplies names, aliases, environments and entry
  points. It need not contain an executable hardware driver.
- A versioned driver supplies dynamic knowledge: targets/configurations, RTL
  outputs and optionally hierarchy. This can be a small Hardcaml-only integration.
- An ASIC adapter consumes the configured project's public discovery/plan/launch
  interface and provider observation/report APIs. It does not infer flow identity
  from directory order or scrape human summaries.
- Discover capabilities and explain unavailable operations. Unsupported timing is
  different from timing that was requested but has not yet been produced.
- Keep execution environments explicit; project tools run in the project's selected
  environment, independently of Workbench's compiler/packages.

## Current and next boundary

Existing contracts: `project_integration/manifest.ml`, `driver_protocol.ml`,
`adapters/`, and `protocol/v1.ml`. Extend compatibly or version incompatible changes.
Do not force the existing RTL driver to implement every ASIC operation.

The sibling FIFO specimen's `flow list/describe/plan/run` and provider observation
interfaces are the adopted first ASIC path. Its standalone headless client is a
behavioral reference, not a required runtime dependency. Adoption is tied to the
recorded installed generation, not the sibling checkout's current HEAD. The FS1
inspection generation advertises `inspection1=true` and schema 1; its local receipt
does not supply the absent verified provider source stamp. Provider configuration
changes require reopening and exact-reference re-registration as documented in
[deployment notes](../fs1_investigation.md#installed-development-provider-and-deployment-caveat).

The initial adapter uses configured public project/provider executables, not sibling
source paths or private helper binaries. Building the project entry point requires
its compatible `hardcaml_asic` library/environment; Workbench itself need not link
that library. The installed provider retains its runtime/tool-resource requirements.
One public executable with several subcommands can serve launch/read/watch; multiple
public executables are also adaptable if versioned/configured. Neither layout
requires one shared process or one executable invocation per tile. F02 owns daemon
query coalescing, caching and bounded asynchronous reads over this boundary.
The adapter must also define F11's source revision/result identity and freshness
validation strategy. Distinguish inexpensive validation from report materialization;
if the provider lacks an efficient revision query, document the limitation rather
than promise fresh zero-I/O reads or parse tool-specific directory trees in tiles.

## First demo / later

Delivered: configure the specimen, negotiate capabilities, run synthesis/known
physical endpoints and inspect/finalize exact adopted evidence. Later: additional
providers and FPGA workflows. Tool interoperability and recipe
validation remain project/provider responsibilities.

Dependencies: F03 commands; supplies F02 domain data and F05 evidence identity.
