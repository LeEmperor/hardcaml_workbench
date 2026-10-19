# Native project test providers (WB-066)

Status: **implemented, verified and adopted**, 2026-10-18.

**Accepted and closed, 2026-10-19:** the owner tried the native-provider workflow,
reported it works, and requested documentation/ticket closeout. This is scoped
human workflow acceptance alongside the automated evidence below, not a claim
that every suggested manual scenario was individually exercised.

## Agreed boundary

Tests remain project-owned standalone executables with project-defined arguments,
results and checkers. Only the project-owned `test_provider.exe` depends on the
new separately packaged `hardcaml_workbench_provider` library. The adapter launches
the existing simulator; no checker extraction or in-process migration is required.
The library supplies FS2v1 wire/validation and runner/event plumbing, not a test
framework. The root simulation S-expression continues to name an explicitly
installed executable. Discovery and run never build or install.

Preserve FS2v1 encodings, exact seed mapping, artifact bytes, case semantics,
normal CLI/Dune behavior, ownership-checked installation and live investigations.
Execution completion remains distinct from test verdict. Independent Python
fixtures remain conformance references. No real physical flows are needed.

## Ownership and resource budget

Baseline Workbench `866c70b` is clean; the example at `2069b6d` contains existing
uncommitted Python provider/config/test-support work which must be preserved.
No staging, commits, resets, pushes or other mutative Git operations.

- A: new provider package, shared wire type extraction/aliases, pure validators,
  runner, package metadata and focused conformance tests. Own `provider/`,
  `protocol/`, `project_integration/simulation_protocol*`, their relevant dune
  dependencies and `dune-project`/generated opam metadata.
- B: real example native `simulation/test_provider.ml`, dune/install integration,
  sibling README and installer tests. Own `hardcaml_asic_example` changes; keep the
  actual simulator and independent checker unchanged. Use library A's public API.
- C: native migration/equivalence acceptance and independent counter example port.
  Own `examples/fs2_cyclesim/` and new focused acceptance script(s), coordinating
  against the published library API. Existing Python reference providers stay.
- Coordinator: this plan, guides/ticket reconciliation, interface coordination,
  review, serial final checks and explicit persistent provider adoption.

Each worker receives at most 6 jobs, in separate build directories under
`/tmp/opencode`; 2 jobs reserved. No parent builds until worker builds stop.
Parent verification then uses at most 20 jobs. All OCaml commands and formatting
use `scripts/with-switch.sh`; installed switch APIs are authoritative.

## Verification gates

- [x] Provider-only package builds/installs with no daemon/TUI dependency.
- [x] Shared encodings/validators and runner errors/events are covered.
- [x] Native real provider matches Python discovery, cases/events, full uint64
  seed behavior, mismatch semantics and report/VCD bytes.
- [x] Native provider works through actual daemon APIs using private state.
- [x] Installer preserves ownership checks and publishes persistent generations
  without modifying old generations or restarting live jobs.
- [x] Counter example adoption and full normal build/format/lint/tests pass.
- [x] Current guides and WB-066 status reflect actual evidence and limitations.
- [x] Owner manual workflow acceptance and ticket closeout recorded.

## Results

### Shared library and test independence

`provider/` publishes `hardcaml_workbench_provider` with `Wire`, `Validation`, and
`Runner`. Runtime/build dependencies are Core/Core_unix/ppx_jane and OCaml; Python
is test-only. Provider-visible types and reference types are shared with protocol
aliases; application history/RPC records stay in `protocol/simulation.ml`.
Independent frozen sexp/bin_io tests cover moved types and event constructors.

The synchronous runner handles strict bounded input, project validation, explicit
event emission, contiguous sequencing, state/progress checks, limits and flushes.
It logs/forwards child stdout and reports process/callback failures separately.
It does not impose a PRNG mapping or require test code to depend on Workbench.

Both real FIFO and counter examples now have project-owned `test_provider.exe`
adapters around unchanged simulator executables. Python references remain for
foreign-language conformance; synthetic/fault fixtures retain Python.

### Verification

- Full normal `dune build -j 20 @all @fmt @lint` and `dune runtest -j 20` passed.
- Provider-only package install and isolated external consumer passed; its opam
  test target is `@provider/test/runtest`, independent of application executables.
- Combined standalone equivalence and actual private-daemon HTTP/restart:
  `/tmp/opencode/native-provider-s0e__xh7/result.json`.
- Installed FIFO generation checked again through standalone equivalence and
  private-daemon HTTP/restart: `/tmp/opencode/native-provider-dk6v5t_n/result.json`.
- FIFO-specific native/Python proof covers five scenarios including reversed
  case/parameter order, high-bit and maximum uint64 seeds, exact stdout/events and
  report/VCD bytes; eight invalid selections rejected before events.
- Combined proof covers full/individual cases, zero/max seed and checker failure;
  artifact byte paging/digests and retained records after restart. Counter VCD
  comparison excludes its variable date stanza; FIFO comparison is byte-exact.
- Original FIFO directed/20,000-cycle CLI tests passed. Twelve private installer
  tests cover ownership refusal, approved migration, backups and failure recovery.

An initial equivalence failure exposed runner normalization of standalone inputs.
The final runner validates without reordering project callback input; upstream
daemon normalization is unchanged. Regression tests cover both callback order and
emitted case order. Initial Dune formatting differences were corrected before
final normal checks.

### Persistent adoption

The owner explicitly approved replacement of the edited companion configuration.
The installer required its exact SHA256 and verified the original owned generation
before publishing. Default edited/unrelated-config refusal remains intact.

Under `hardcaml_asic_example/.dev/`:

- Native generation: `fifo-simulation/4158d5b458804b8a8428bc28862e5a49/`.
- Backup/receipt: `fifo-simulation-receipts/4158d5b458804b8a8428bc28862e5a49/`.
- Reusable SDK prefix: `workbench-provider-sdk/` (build adapters with
  `OCAMLPATH=/home/wayne/devel/jane/hardcaml_asic_example/.dev/workbench-provider-sdk/lib`).

Config names `test_provider.exe` with empty arguments and retains 10/120-second
timeouts. Old generation/config/ownership bytes are preserved. Explicit Catalog
discovery is required before new launches because provider configuration changed;
historical attempts are not rewritten. No live daemon restart, reseed, physical
flow or Git mutation occurred. The package is locally installable but not published
to an external opam repository. No native-provider PTY-specific acceptance is
claimed; native wire/HTTP and existing terminal tests cover the unchanged interface.
