---
id: WB-050
title: Upward project discovery
category: project
feature_sets: [FS3]
status: proposed
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: S
points: 5
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [project-root, discovery, adoption]
depends_on: []
related: []
---

# WB-050 — Discover the enclosing project

## Request
Original size: **Unspecified**. Launch conveniently from a project subdirectory
and discover the enclosing project root upward.

## Current baseline
The ordinary opener and initializer require a root directly containing a regular
dune-project file; a subdirectory containing only dune is rejected.
Canonical roots plus execution environment identify existing sessions.
FS3 explicitly did not change discovery or manifest precedence.

## Scope
- Add bounded upward search for the nearest supported project marker.
- Keep explicit root selection authoritative and report the resolved canonical root.
- Share resolution rules across the agreed entrypoints without changing provider lookup.
- Explain no-match and nested-project selection rather than choosing by VCS alone.

## Out of scope
Configuration relocation, recursive whole-filesystem scans, provider autodetection
and changing the initializer into a new-project generator.

## Acceptance criteria
1. Launching below a valid root selects that same canonical project/session identity.
2. Nested supported projects choose the documented nearest root deterministically.
3. Explicit --project-root bypasses upward search and retains validation errors.
4. No marker or inaccessible ancestry yields a useful bounded diagnostic.
5. Discovery itself neither writes configuration nor executes project flows.

## Dependencies
Required: delivered canonical root validation and entrypoint parsing; no new blocker.
Related: none; a future configuration-location policy can extend marker recognition later.

## Estimate rationale
5 points cover one resolver, selected entrypoint wiring and boundary-case verification.
Exclude new root types, configuration migration and general build-system detection.

## Assumptions and decisions needed
Default: nearest regular dune-project marker, stopping at filesystem root.
TBD: initial entrypoints, symlink ancestry semantics and any explicit search boundary.
A VCS root alone does not establish a Dune project under this ticket.

## References
- [Root validation](../../../backend/service.ml)
- [Setup entrypoint](../../../setup/main.ml)
- [Current adoption behavior](../../fs3_adoption.md)
