---
id: WB-039
title: Simulation provider setup assistance
category: project
feature_sets: [FS2, FS3]
status: partial
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
1. Generated configuration round-trips through the existing strict parser.
2. Existing files, including links, are refused rather than overwritten.
3. Dry-run creates no config and invokes no provider or build tool.
4. Explicit discovery reports provider errors and the actual suite/case catalog.
5. Setup does not launch tests merely because configuration was generated.

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

## References
- [Simulation configuration parser](../../../project_integration/simulation_config.ml)
- [Provider contract](../../fs2_simulation_contract.md)
- [Initializer implementation](../../../setup/initialization.ml)
