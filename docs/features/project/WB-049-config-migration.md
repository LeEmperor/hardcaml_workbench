---
id: WB-049
title: Configuration-location migration and precedence
category: project
feature_sets: [FS3]
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
tags: [configuration, migration, precedence]
depends_on: []
related: []
---

# WB-049 — Deliberate configuration migration

## Request
Original size: **Unspecified**. Move shareable project configuration toward a
dedicated location with explicit migration and unambiguous precedence.

## Current baseline
FS3 deliberately preserves root hardcaml-workbench.sexp and current lookup semantics.
ASIC and simulation each have separate configuration loaders and identities.
Personal presentation state already lives separately under XDG state.
The area spec suggests .workbench/ as a candidate, not an accepted directory name.

## Scope
- Select one project configuration directory and enumerate migrated file classes.
- Define lookup precedence and conflict diagnostics for old/new coexistence.
- Provide explicit dry-run and no-clobber migration of the agreed configuration set.
- Preserve provider path interpretation and explain identity/cache consequences.

## Out of scope
Moving canonical run evidence, merging personal state into source configuration,
or silently transferring registries between provider identities.

## Acceptance criteria
1. Old-only projects retain documented behavior throughout the compatibility window.
2. New-only and both-present cases have deterministic, visible resolution.
3. Conflicting content never silently selects a different provider or execution environment.
4. Dry-run describes every write; a failed migration leaves original configuration usable.
5. Generic, ASIC and simulation lookup behavior is documented consistently.

## Dependencies
Required: existing loaders and FS3 initializer; no additional ticket prerequisite.
Related: none; upward discovery can use today's root filenames independently.

## Estimate rationale
13 points cover one agreed migration policy, loader updates and bounded migration tooling.
Exclude root-discovery changes, template redesign and automatic run-registry migration.

## Assumptions and decisions needed
TBD: directory name, exact file set and compatibility duration.
Default: diagnose ambiguous coexistence rather than silently override differing files.
Relative paths must preserve their intended project-root meaning after relocation.

## References
- [Setup policy](../project_setup.md)
- [Generic manifest](../../../project_integration/manifest.ml)
- [ASIC configuration](../../../project_integration/asic_config.ml)
- [Simulation configuration](../../../project_integration/simulation_config.ml)
