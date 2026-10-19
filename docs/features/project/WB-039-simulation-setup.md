---
id: WB-039
title: Simulation provider setup assistance
category: project
feature_sets: [FS2, FS3]
status: delivered
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 8
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [simulation, setup, configuration]
depends_on: []
related: []
---

# WB-039 — Set up simulation integration

## Request
Original size: **Unspecified**. Assist simulation setup by generating the provider
configuration and checking the setup against declared tests.

## Current baseline
FS2's structured simulation protocol, discovery, execution and history are delivered.
Its opt-in root configuration requires an absolute executable, prefix arguments
and timeouts. FS3's initializer currently writes only the generic manifest.
Provider executables and their setup/build instructions remain project-owned.

## Scope
- Generate one valid simulation configuration from explicit provider inputs.
- Preview the destination and rendered fields before no-clobber publication.
- Explain provider build prerequisites and offer explicit discovery as a setup check.
- Show configured-empty, discovered tests and discovery failure distinctly.

## Out of scope
Creating real project test adapters, installing tools, automatically building providers,
or changing accepted FS2 execution semantics.

## Acceptance criteria
- [x] Generated configuration round-trips through the existing strict parser.
- [x] Existing files, including links, are refused rather than overwritten.
- [x] Dry-run creates no config and invokes no provider or build tool.
- [x] Explicit discovery reports provider errors and the actual suite/case catalog.
- [x] Setup does not launch tests merely because configuration was generated.

## Dependencies
Required: delivered simulation configuration/discovery and initializer patterns.
No additional ticket prerequisite; real project adapters are independently adoptable.
Related: none required for configuration assistance.

## Estimate rationale
8 points cover config generation, validation, no-clobber behavior and setup checks.
Exclude provider implementation, test-catalog redesign and test execution engines.

## Assumptions and decisions needed
Default: CLI setup first, requiring explicit absolute provider paths.
TBD: whether checks stop at discovery or include an explicitly selected smoke test;
the default is discovery only, with no automatic run.

## Delivery notes
- **CLI (new executable, CLI only, no TUI):** `hardcaml-workbench-simulation-setup`
  (`setup/simulation_main.ml`, logic in `setup/simulation_setup.ml{,i}`):
  ```sh
  hardcaml-workbench-simulation-setup init (--root DIR | --discover-project) \
    --provider-executable /ABSOLUTE/PATH [--provider-arg ARG ...] \
    [--discovery-timeout-seconds N] [--run-timeout-seconds N] [--dry-run]
  hardcaml-workbench-simulation-setup check (--root DIR | --discover-project) \
    [--environment inherited|opam:SWITCH]
  ```
  `--provider-arg` is repeatable and order-preserving. Timeouts default to 10 s and
  300 s; ranges are enforced by the existing `Simulation_config.validate`.
- **Generation:** the root is validated like the initializer (or found via WB-050
  discovery). The executable must be absolute (no PATH search or relative paths);
  it need not exist yet, and the preview reports whether it exists/is executable.
  The file is rendered one field per line and must parse back through the strict
  `Simulation_config.parse_string` to an equal value before anything is offered.
- **Preview / no-clobber:** both modes print the project root, destination, every
  field and the exact rendered bytes; `--dry-run` stops there. Publication reuses the
  initializer's atomic temp-file + no-replace hard link (now shared as
  `setup/no_clobber.ml`). Any existing destination (file, directory, symlink,
  dangling symlink, concurrent writer) is refused and untouched, in dry-run too.
  There was no overwrite flag in existing conventions, so none was added.
- **Check (decision: discovery only, never a smoke test):** reads the config with
  the daemon's restrictions (regular, not a symlink, <=16 KiB, strict parser) and
  runs exactly the daemon's discovery argv (`Simulation_adapter.discover`, including
  the opam prefix for `opam:SWITCH`) from the root, with the configured timeout, the
  1 MiB stdout bound and the daemon's discovery decoder. The provider's process
  group is killed on timeout/overflow. Distinct outcomes: not configured, invalid
  configuration, **discovery failed** (reason, command, working directory and a
  bounded provider stderr tail), **configured with zero suites**, and **discovered**
  (every suite with seed, parameters and cases). Exit 0 only for the last two. Every
  run output states that no tests were run. `inherited` means this process's
  environment (the daemon uses its own); the check does not touch the daemon or its
  cached catalog, so Workbench still requires its own Catalog discovery.
- **Prerequisites:** group/subcommand help and init output explain that provider
  executables are built/installed by the project, never by Workbench.
- **Verification:**
  - `dune runtest setup`: `setup/test/test_simulation_setup.ml` (round-trip incl.
    quoting/32 args, invalid inputs, preview fields and provider state, refusal of
    file/empty/directory/dangling and live symlinks, publish race, each check
    outcome incl. exit/garbage/wrong version/signal/timeout/1 MiB overflow/not-built
    executable, and a calls log proving only `discover` ever ran) and
    `setup/test/test_simulation_cli.py` (dry-run writes and runs nothing, init from a
    subdirectory then check, refusal incl. links, outcome exit statuses, rejected
    inputs, help text) pass.
  - Manual: init + check with the real `examples/fs2_cyclesim/provider.py` and
    `counter.exe` listed suite `counter` with cases `wrap`, `reset`, `seeded`.
    `check` in `examples/fs2_cyclesim` showed a real not-built native provider
    failure (`test_provider.exe` absent) and the nested-project report.
  - Full `dune build -j20`, `dune runtest -j20` and `@setup/fmt @setup/lint` pass.

### Delivery review follow-up: discovery timeout

Review found that a provider closing stdout/stderr before exiting bypassed the
discovery deadline at the subsequent blocking wait. Discovery now polls child exit
and output completion together under the deadline, including when both streams are
closed. Timeout cleanup kills the process group and reaps the direct child once.
Regression tests cover both closed streams with a still-running provider and an
exited provider whose descendant retains the streams. The original one-second
timeout reproducer now reports a timeout in approximately 1.01 seconds rather than
waiting for the provider's ten-second sleep. Focused setup tests, lint and formatting
checks passed.

## References
- [Simulation configuration parser](../../../project_integration/simulation_config.ml)
- [Provider contract](../../fs2_simulation_contract.md)
- [Initializer implementation](../../../setup/initialization.ml)
