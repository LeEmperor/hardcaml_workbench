# FS3 — Existing-project setup and reusable workspaces

Implemented on the FS3 worktree, 2026-10-15. This slice delivers an existing-project
initializer, portable workspace templates and persistent client presentation choices.
Multi-monitor UX, configuration-location migration and new-project creation remain
later scope.

## Build

```sh
scripts/with-switch.sh dune build -j 10
```

Installed executable names are `hardcaml-workbench-init` and
`hardcaml-workbench-workspace`. Examples below use the local build directly.

## Initialize an existing project

```sh
_build/default/setup/main.exe --root /absolute/path/to/project --dry-run
_build/default/setup/main.exe --root /absolute/path/to/project
```

The explicit root must contain a regular `dune-project` or `dune` file. The project
name defaults to its directory name. Optional flags are `--project-name NAME`,
`--driver ./path/to/driver.exe`, `--build-alias @all` and `--test-alias @runtest`.
Driver and alias syntax is validated through the existing manifest parser; targets
need not exist yet. The initializer performs no build, driver or provider execution.

The only published file is `hardcaml-workbench.sexp`, in the existing version-1
format. Publication is atomic and refuses any existing destination, including a
symlink. It never replaces an existing configuration or edits build/VCS files.
Temporary files are cleaned on ordinary failure. Filesystems must support local
hard links for no-replace publication; unsupported publication fails explicitly.

Open the initialized root with the ordinary terminal `--project-root` and
`--environment` flags. This slice does not change root discovery, manifest
precedence or configuration storage location.

## Workspace templates

Templates contain a version, workspace name and ordered views with kind, hidden
state and requested geometry. They exclude run selections, pins, session/context/
tile IDs, zoom and appearance. Import and clone create fresh view identities in a
new workspace linked to Main; every tile follows that context. A clone copies the
layout, not the source investigation's selected run or independent context.

Start Workbench and open the project first. Use its daemon endpoint and project ID
(shown by the plain client/project snapshot), then list registry IDs:

```sh
_build/default/workspace_cli/main.exe list \
  -endpoint http://127.0.0.1:8080 -project PROJECT_ID

_build/default/workspace_cli/main.exe starter generic > generic.sexp
_build/default/workspace_cli/main.exe import \
  -endpoint http://127.0.0.1:8080 -project PROJECT_ID \
  -window WINDOW_ID -name "Project work" generic.sexp

_build/default/workspace_cli/main.exe export \
  -endpoint http://127.0.0.1:8080 -project PROJECT_ID WORKSPACE_ID > layout.sexp
_build/default/workspace_cli/main.exe clone \
  -endpoint http://127.0.0.1:8080 -project PROJECT_ID \
  -window WINDOW_ID -name "Layout copy" WORKSPACE_ID
```

`starter generic` supplies project, execution, project-test and log views.
`starter asic` supplies selection, ASIC controls, synthesis and stage/evidence
views. Both are offline operations. Imported workspaces become available through
the terminal's existing workspace-switch palette after refresh.

Import/clone each use one atomic compare-and-swap registry mutation. Conflicts are
reported rather than retried against a changed context. Invalid templates cannot
leave a partially created workspace. Input is bounded to 1 MiB and 1000 views;
unknown view kinds remain portable identifiers, not executable extensions.
Requested geometry still uses the existing shelf/Fit renderer, not free placement.

Templates can be checked into a project's chosen location; personal session state
remains in the daemon store. No automatic template discovery or TUI file picker is
introduced. Rebuild daemon and clients together to use the new template mutation;
the stored workspace snapshot format is unchanged.

## Persistent presentation preferences

The existing palette's appearance preset, color, icon, density, layout-mode,
chrome and tile-header actions now save their explicit choices. Normal terminal
exit waits for queued writes. Preferences use a separate versioned
`presentation-<digest>.sexp` under
`${XDG_STATE_HOME:-$HOME/.local/state}/hardcaml-workbench/terminal/`, keyed by
canonical project root and execution environment.

Tile-header choices additionally match session, tile, workspace and view kind.
Replacement sessions do not inherit stale tile preferences. Focus, scroll, filters,
active workspace, run selection and provider data are not persisted in this file.
Malformed or oversized files fall back to defaults with a visible notice and are
left untouched until a later explicit preference change saves a replacement.
Concurrent clients use last-writer-wins files; preferences do not synchronize live.

## Verification

The full build, `@lint`, changed-file OCaml formatting and `dune runtest -j 10`
pass. Repository-wide `@fmt` still reports inherited formatting differences in
`backend/asic_evidence_file.ml{,i}`, `backend/asic_public.ml`,
`backend/asic_service.ml`, `backend/test/asic/test_asic.ml`,
`terminal/synthesis_view.ml{,i}` and `terminal/terminal_result_view.ml`.
The report is `/tmp/opencode/fs3-format-check.log`.
Tests cover initializer validation,
no-clobber publication races, template identity/provenance stripping and atomic
failure, and fresh-process presentation persistence/failure handling.

```sh
scripts/with-switch.sh dune build -j 10 @fmt @lint
scripts/with-switch.sh dune runtest -j 10
python3 scripts/test-fs3-adoption.py
```

The integration script uses private state and a strict metadata-only Dune fixture:
actual initializer and template executables, a real HTTP daemon, exact registry
restoration across daemon restart, rejected malformed/stale operations, and actual
PTY palette selection and presentation restoration in a new terminal process.
It records transcripts and a `result.json` under `/tmp/opencode/fs3-adoption-*`.
Final passing run: `/tmp/opencode/fs3-adoption-ry427qxc/result.json`.
The existing five-mode terminal interrupt regression also passes:
`/tmp/opencode/workbench-terminal-interrupt-sfrzonk0/`.
It does not claim real tool runs, installed-package acceptance or full multi-monitor
convergence/responsiveness acceptance.
