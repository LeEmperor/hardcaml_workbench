---
id: WB-050
title: Upward project discovery
category: project
feature_sets: [FS3]
status: closed
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
- [x] Launching below a valid root selects that same canonical project/session identity.
- [x] Nested supported projects choose the documented nearest root deterministically.
- [x] Explicit --project-root bypasses upward search and retains validation errors.
- [x] No marker or inaccessible ancestry yields a useful bounded diagnostic.
- [x] Discovery itself neither writes configuration nor executes project flows.

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

## Delivery notes

**Owner closure — 2026-10-21:** closed under the owner's authorization to close
the non-signoff-dependent tickets in this set. Discovery remains explicit/opt-in.

- **Resolver:** one shared module, `setup/project_discovery.ml{,i}`
  (`Hardcaml_workbench_setup.Project_discovery`). Marker: the nearest directory
  directly containing a **regular file** `dune-project` (a symlink to a regular file
  counts, as in the daemon's opener; a directory or dangling link does not). A
  `dune`-only directory or VCS root is never a project. The walk inspects the start
  and each ancestor up to `/` (guarded at 4096 levels) and reads metadata only.
- **Symlinks:** the starting directory is `realpath`-canonicalized before walking, so
  a symlinked directory is searched from its target's physical ancestors, not from
  the logical `$PWD` path that contained the link. The selected root is therefore
  already canonical and opens the same session as passing it explicitly.
- **Nested projects:** nearest wins. The report also names the next enclosing
  project, if any, and the explicit flag to open it instead.
- **Failures:** no match names the start, the number of ancestors searched, any
  ignored non-regular `dune-project` entries and the explicit-root escape hatch. An
  ancestor whose marker cannot be inspected (e.g. no search permission) stops the walk
  with that path and errno instead of being skipped, so a farther root is never
  chosen past a possibly nearer one.
- **Entrypoints (decision):** no entrypoint defaulted to the current directory
  (the terminal without `--project-root` opens no project; the initializer requires a
  root), so discovery is an explicit, opt-in flag rather than a changed default:
  - `hardcaml-workbench --discover-project` (terminal; plain, TUI and `--api`).
    The resolved root goes to stderr except in `--api` mode; an `--api` conflict is
    one typed `Invalid_request` response. With `--project-root` it is an error.
  - `hardcaml-workbench-init --discover-project` (alternative to `--root`; exactly
    one is required). The root is reported on stderr so `--dry-run` stdout stays the
    exact manifest.
  - `hardcaml-workbench-simulation-setup init|check --discover-project` (WB-039).
  Explicit `--project-root` is still passed to the daemon unchanged (same errors, and
  a relative path keeps its pre-existing daemon-side resolution); explicit `--root`
  keeps the initializer's direct-root validation. Making discovery the terminal's
  default when no root is given would be a one-line change if wanted later.
- **Verification:**
  - `dune runtest setup`: `setup/test/test_project_discovery.ml` (root itself,
    dune-only subdirectories, nested nearest/outer report, non-regular marker, no
    marker with ignored entries, symlinked start/link-out-of-project/symlinked and
    dangling markers, unsearchable start, missing/non-directory start, `resolve`
    explicit passthrough and conflict, metadata-only listing) and `test_cli.py`
    (initializer `--discover-project` from a subdirectory, conflicts, no-marker,
    nothing written) pass, alongside the existing initializer tests.
  - Manual private daemon: `--discover-project` from `proj/src/rtl` and via a
    symlink returned the same workspace `session_id` as `--project-root /abs/proj`;
    no-marker, conflict and `--api` conflict produced the diagnostics above.
  - `python3 -B scripts/test-fs3-adoption.py` (with snapshot binaries): PASSED;
    full `dune build -j20`, `dune runtest -j20`, `@setup/fmt @setup/lint
    @terminal/lint` pass.

## References
- [Root validation](../../../backend/service.ml)
- [Setup entrypoint](../../../setup/main.ml)
- [Current adoption behavior](../../fs3_adoption.md)
