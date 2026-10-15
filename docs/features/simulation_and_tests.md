# F09 — Simulation and test module, runner and tiles

Status (2026-10-15): **FS0 generic execution/test module and project-scoped tile
delivered** over the existing supervisor, with attempts/status/log/cancel and no
second scheduler. See [Execution](../fs0_execution_module.md),
[installed checks](../fs0_install_checks.md) and [acceptance](../fs0_acceptance.md).
Requirements remain normative: structured cases/seeds/regressions/traces (FS2) and
generic test-history restart persistence are not implemented.

## User outcome

Run the project's tests/simulations, see what is executing, inspect failures and
logs, cancel an attempt, and retain its identity/evidence. Start with a generic test
runner; grow richer simulation adapters as actual projects supply structured data.
“Simulation tile” names the feature conversationally; the module owns semantic
test state/commands and one or more tiles provide its views.

## First slice: generic test runner

- Reuse the existing daemon supervisor and configured Dune test alias. Preserve
  generic operation without a hardware driver or `hardcaml_asic` dependency.
- Expose a typed test command through the same command registry as build/flow
  commands. Palette, button and shortcut dispatch one action, with deduplication.
- Give each invocation an attempt/job identity and retain queued, starting, running,
  completed, failed and cancelled states, timestamps, exit/launch-failure details
  and bounded stdout/stderr access. Do not create a second process scheduler.
- A simulation/test tile lists attempts, lets the user select one, shows status,
  elapsed time and logs, and offers run/cancel/inspect actions where available.
- Label the declared command/suite and execution environment. Generic success means
  the command exited successfully; it does not establish a count of passed cases,
  that tests reran rather than hitting a cache, or physical signoff.
- When only logs/exit status exist, say case details/progress are unavailable.
  Do not parse arbitrary human output into invented per-case outcomes or percentages.
- Retain earlier attempts when rerunning. Closing/hiding the tile or switching run
  contexts does not cancel tests; explicit cancellation targets one selected attempt.
- A simulation tile can be part of Overview or an optional Simulation workspace.
  Multiple tiles share module state but have independent attempt selection/scroll.

## Scope and run-context behavior

A generic test is project-scoped. It need not consume an ASIC build or belong to an
ASIC run, and must not be assigned to the currently selected physical run merely
because it was launched while that run was visible. Source/environment provenance
is recorded where available; unknown association stays unknown.

The initial generic tile explicitly displays **Project tests** and its selected
attempt. It remains usable with no selected ASIC run. A later run-scoped simulation
view follows the workspace context only when the adapter provides a real association
(for example gate-level simulation of a named output). Switching contexts must never
show unrelated project results beneath a new run label.

Shared run contexts (F10) govern ASIC evidence selection, not every local control
inside every tile. Test-attempt selection is a separate, typed view context.

## Later structured simulation/regression adapters

- Project-declared suites/cases, seeds, parameters, durations and outcomes with
  explicit schema/capability discovery. Test semantics remain project-owned.
- Cyclesim/step-testbench, generated-RTL and gate-level simulation integrations
  where useful; none is implied by the generic runner.
- Live case events and bounded regression summaries, failed-case detail and reruns
  using explicit original inputs/seeds where supported.
- Trace/waveform/report artifacts with provenance and explicit external viewer
  actions. Embedded waveform/signal exploration remains deferred, not a first-demo
  dependency. Registering a trace is distinct from implementing a waveform viewer.
- Persistent historical test evidence when a provider supplies durable records or
  a separately specified Workbench-owned test record store is implemented. Current
  daemon-memory job state does not establish restart-persistent test history.

## Acceptance and delivery

M1: use the existing test invocation through the new module/command API; exercise
success, nonzero exit, launch failure, cancellation and bounded logs with deterministic
fixtures. Verify two submissions produce distinct attempts and a retry of one
submission key does not double-launch. Run the counter/specimen's ordinary PDK-free
tests to establish a real project path.

M2: dispatch from actual frontend input once, inspect/select/cancel an attempt,
switch workspaces/context while it runs, and hide/restore the tile without lifecycle
side effects or false ASIC-run association. Rich case/seed adapters follow in M4;
waveform UI is later scope.

Dependencies: F01 configured operations/environments; F02 shared semantic state;
F03 command registry; F04 tile host; F05 genuine provenance/artifact references.
The generic first slice can proceed before the ASIC adapter or physical tools.
