---
id: WB-074
title: Normalized suite/parameter/seed fields and run inputs in the simulation catalog
category: verification
feature_sets: [FS2, FS5]
status: needs-design
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [simulation, catalog, parameters, seeds, launch]
depends_on: []
related: [WB-030, WB-032, WB-039, WB-063]
---

# WB-074 — Normalized suite/parameter/seed fields and run inputs in the simulation catalog

## Request
Owner notes, 2026-10-20: in the simulation-catalog, the suite/parameter/seed
structure should be much more clearly separated and normalized. Perhaps add more
enterable or interactive fields right there, so that the command run on Run has
those values injected as CLI arguments.

## Current baseline
FS2 v1 discovers suites and cases, and each submission carries one seed plus
declared parameters. In Catalog, Enter or `r` opens a launch form for the exact
suite/subset/digest; the form edits fields (Ctrl-U clears, Enter accepts). Suite,
case, parameter and seed information is shown combined rather than in separate columns.
The provider is invoked with the configured executable and prefix args; values reach
it through the structured submission, not raw shell text.

## Scope
- Show suite, case, declared parameters (name, type, default) and seed as separate,
  aligned fields.
- Edit seed and declared parameter values inline in the catalog, validated against
  their declared types, with the effective values visible before Run.
- Run submits those values through the existing structured seed/parameter submission.
  The provider turns them into its own CLI arguments; the preview shows the exact command.

## Out of scope
Free-form extra CLI arguments not declared by the provider (needs an FS2 contract
change), seed sweeps and parameter matrices (WB-030), and saving named run presets.

## Acceptance criteria
- [ ] Suite, case, parameters and seed are visually and structurally separate.
- [ ] Inline edits are validated; invalid values block Run with a reason.
- [ ] Run uses exactly the shown values; the attempt records them and they appear in history.
- [ ] Reset returns fields to the discovered defaults.
- [ ] Narrow widths keep field identity readable.

## Dependencies
None required. WB-030 builds sweeps on the same field model.

## Estimate rationale
13 points, medium confidence: the launch form and structured submission exist;
inline editing inside a list view and the field layout are the new work.

## Assumptions and decisions needed
- Should undeclared raw CLI arguments ever be allowed? That would be a new,
  explicitly opt-in provider capability.
- Do edited values persist per suite between sessions?

## References
- [Simulation contract](../../fs2_simulation_contract.md)
- [Catalog controls](../../testing_workspace.md)
- [Catalog view](../../../terminal/simulation_catalog.ml)
