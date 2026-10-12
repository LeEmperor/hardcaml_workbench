# Hardcaml Workbench Construction Plan (pre-consolidation snapshot)

## Direction reset — 2026-10-12

Build a modular hardware-operation workspace suitable for a dedicated monitor.
Feature **modules** own processing and semantic state; movable **tiles** present
that state and issue typed actions. Support ASIC projects (including their FPGA
emulation targets) and FPGA-only projects through shared infrastructure and
capability-specific providers.

The [architecture](hardcaml_workbench_architecture.md#active-direction--modules-and-tiles-2026-10-12)
owns the boundaries and decisions. This plan owns sequence and completion evidence.
It replaces the scaf-dependent D1–D4 release and the P0–P5 prettification sequence.
The old plan is retained as [historical evidence](construction_phase_plan_2026_09.md).

**Status:** planning reset only. No new module runtime, tile workspace, test ASIC,
or ASIC tool integration is implemented by this revision. W0–W6 are not started.
Names and exact APIs below are implementation guidance, not frozen wire schemas.

## Existing foundation to carry forward

- Installed native daemon/client and typed HTTP protocol.
- Independent project opening, environment selection, Dune build/test jobs.
- Supervision, root-serialized scheduling, cancellation, logs, reconnect reduction.
- Manifest/driver discovery, target/configuration selection, RTL generation.
- Artifact/provenance handling and elaborated hierarchy inspection.
- Pure presentation/reducer helpers, installed/PTY checks and baseline captures.

Milestones 1A–1C have recorded automated and human acceptance in the archive and
[development log](development.md). That is prior evidence, not a claim that the
new architecture is implemented or that today's environment has been revalidated.

## W0 — Fix the development specimen and contract examples

**Goal:** development no longer depends on a moving product or missing worktree.

- [ ] Choose the test ASIC's location, small design, pinned tool/PDK environment,
  and ordinary CLI entry points. Record exact revisions and reproduction commands.
  Keep its Dune root independent of the application; retain the existing counter
  fixture for fast generic/RTL tests.
- [ ] Define a minimal operation catalog: build, unit test, bounded regression,
  RTL generation and physical flow. Operations declare environment, cancellation
  ownership, supported scope and expected evidence. Workbench delegates execution.
- [ ] Obtain one real small-design physical run, archive its original reports and
  record tool versions, constraints, corners, build/run identity and expected
  observations. Select which actual Magic/KLayout operations the reference flow
  supports; executable availability alone is not integration.
- [ ] Define bounded recorded-event replay and explicit synthetic cases for pending,
  failure, cancellation, missing/unconstrained timing, partial results, stale
  observation and malformed reports. Synthetic outcomes stay labeled as such.
- [ ] Write worked contract examples for operations, timing observations and artifact
  evidence; settle the first report/progress formats before extending RPC.

**Exit:** the specimen builds/tests outside Workbench; a real archived result can
be reproduced in its declared environment; deterministic fixtures need no installed
PDK/vendor tools. Do not make every local test run execute a physical flow.

**Open choices:** design/PDK/runner selection and location need owner agreement.
Pin `hardcaml_asic` if used, or use a small project-owned script; never depend on
its moving branch implicitly. Contracts can be prototyped while live provisioning
is pending, but replay alone does not close the real-tool part of W0.

## W1 — Prove the module boundary with timing and execution

**Depends on:** W0 contract examples; recorded fixtures suffice for early development.

- [ ] Introduce typed module contracts: scoped identity, capabilities, snapshot,
  incremental update/revision, commands, availability and evidence references.
  Extend the existing protocol additively where possible; document compatibility.
- [ ] Adapt existing jobs/logs into the execution feature without replacing its
  supervisor. Add the declared-operation path needed by the specimen.
- [ ] Implement a timing provider importing the named archived run. Keep setup/hold,
  corner/mode, stage, constraints, units and source report distinct. Missing values
  remain missing. Parse report semantics once on the backend.
- [ ] Exercise two consumers of the same timing data headlessly, including a compact
  WNS projection and detailed corner projection. Consumers must not reparse reports
  or trigger extraction on render.
- [ ] Verify lifecycle, cancellation, partial imports, stale updates, reconnect and
  run switching. Module state must not depend on whether any tile is mounted.

**Exit:** daemon/contract tests and a plain client can inspect real recorded timing;
two independent consumers share one imported result. This is the first vertical
module slice, not a general plugin framework.

## W2 — Establish the tile workspace and headless interaction seam

**Depends on:** W1; host prototyping may use existing job/hierarchy data earlier.

- [ ] Separate terminal transport, application data, workspace state and rendering
  from executable startup. Keep production reducers and stale-response protections.
- [ ] Add stable tile-instance IDs, explicit data bindings (follow/pinned), common
  shell, focus/input routing, and shared requested/effective geometry.
- [ ] Support keyboard move/reorder, resize, hide/restore and zoom. Permit two views
  of the same module with independent filters and scrolling. Start with a bounded
  split layout and presets; exact persistence format follows a concrete layout.
- [ ] Add initial jobs, logs and timing tiles. Apply a restrained Ches-inspired
  theme, readable selection and command/help surfaces as these tiles migrate.
- [ ] Establish Bonsai Term headless tests using the actual frontend event path,
  an injected transport and controlled time. Check supported key/pointer events,
  action dispatch, focus, resize, no-input updates and explicit log follow state.
- [ ] Verify moving/hiding/restoring a tile neither changes run identity nor creates
  a job; duplicate submission and input leakage remain observable test failures.

**Exit:** a useful, movable three-tile workspace; automated interaction proves its
behavior without manual clicking. A few frame expectations check layout, rather
than making every behavioral test snapshot the whole screen.

## W3 — Operate the test ASIC end to end

**Depends on:** W0 live specimen, W1 contracts, W2 workspace.

- [ ] Launch build/tests, regression and the reference physical flow through the
  project entry points. Preserve normal standalone CLI behavior.
- [ ] Consume structured project/tool progress with known/unknown substeps, elapsed
  times, liveness and observation freshness. Verify descendant cancellation for
  the actual runner, including containers if used.
- [ ] Populate execution, timing, checks and artifact tiles from the same named run.
  Expose supported Magic/KLayout activity and reports with tool and step identity;
  never infer a successful check from a tool exiting or a GDS file existing.
- [ ] Add artifact browsing, bounded text/report inspection and an explicit external
  viewer action. Document whether the viewer runs on the daemon host or the client
  machine, transfer requirements and unavailable-display behavior.
- [ ] Exit/reconnect during execution; recover without resubmission. Reopen the
  archived result after daemon restart without rerunning the physical flow.

**Exit:** one real flow plus bounded failure/cancellation cases is operated through
the workspace; displayed results match original reports. Record live and replay
evidence separately.

## W4 — Add clock and physical-design feature slices

**Depends on:** W3's real evidence; choose a narrow useful slice for each module.

- [ ] Clock slice: declared/generated clocks, periods and relationships, available
  constraint coverage, timing clock groups and CTS observations. Reference timing
  data rather than implementing a second slack parser. Unsupported CDC analysis
  remains unavailable rather than inferred from a clock list.
- [ ] Physical-design slice: floorplan/core/die context, cell/macro area, utilization,
  placement/routing stage and congestion evidence where produced. Checks remain
  separate evidence, with shared artifact links.
- [ ] Add concise explanations of metrics and checks: what is measured, why it
  matters, where the evidence came from, and which declared goal is unmet. Avoid
  invented thresholds or automatic claims of signoff.
- [ ] Prove composition with an overview tile consuming several modules, and a
  second presentation of one module without additional backend work.

**Exit:** the workspace helps a first-time ASIC developer locate a concrete issue
and its supporting report, not merely display an unexplained red number.

## W5 — Daily monitor workspace and FPGA boundary proof

**Depends on:** W3; W4 supplies the richer ASIC workspace.

- [ ] Save/restore named client layouts and tile bindings. Preserve layout intent
  across resize/reconnect; unavailable saved run identities are not rebound to a
  different run silently. Support independent clients observing one daemon.
- [ ] Exercise a wide dedicated-monitor workspace plus compact/tiny terminal
  recovery. Bound log/event retention and update batching during a long regression.
- [ ] Add an FPGA-only profile fixture and an ASIC profile with FPGA emulation to
  prove capability composition. Shared tiles work without fake ASIC checks or a
  second execution model. Recorded FPGA evidence does not claim live vendor support.
- [ ] Run appropriate format/lint/build/unit, installed, external-fixture and PTY
  checks. Keep a focused human review for readability/comfort; routine interaction
  correctness is established by headless tests.

**Release exit:** a reproducible test ASIC can be built, tested, run and inspected
from a configurable monitor workspace, with traceable timing/check/artifact evidence
and reliable detach/reattach. No production emulator or scaf worktree is required.

## W6 — Adopt in a real project; extend from actual needs

**After the first release.** Integrate the current production ASIC project using
the proven boundary. Record contract gaps rather than moving its flow into
Workbench. Activate live FPGA tooling, embedded graphical viewers, cross-run
comparison, power analysis or other features when an actual workflow needs them.

## Next construction task

W0: agree on a small independent test ASIC and its pinned flow, then collect the
first archived run and contract examples. In parallel conceptually, use existing
jobs and recorded observations to design W1/W2's narrow test seams; do not wait
for the whole ASIC environment to refactor the terminal startup boundary.
