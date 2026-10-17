# FS3 post-merge integration plan

Status: **implemented and verified**, 2026-10-17. Baseline: clean `oxcaml` at
`4f56ceb`. This is the shared implementation plan for the merged FS3 adoption
slice. FS1 remains delivered for adopted evidence; FS2 remains accepted and closed.

## Scope and architectural contracts

- Integrate initializer, templates and presentation persistence with the current
  core; keep existing FS1/FS2 services and project-owned tool execution boundaries.
- The daemon registry owns workspace identities, contexts, bindings and requested
  geometry. Client focus, navigation, viewport and investigation remain local.
- `terminal/workspaces/` remains the source of preset membership and composition.
  Portable templates retain optional preset identity, but never live references.
- Preferences record explicit presentation intent, including inheritance/reset;
  saved snapshots must not overwrite newer choices on ordinary polling.
- Same-session reconnect preserves appropriate local browsing while invalidating
  old asynchronous work. Replacement identities invalidate local state.
- Bootstrap completion must be explicit and atomic, independent of registry
  revision and startup order. Existing sparse saved arrangements are user state.
- Initializer roots must be accepted by the opener. Explicit manifest reload can
  succeed without a driver job; discovery remains an explicit operation.
- Full multi-monitor attachment, free placement, provider configuration generation,
  new-project creation and additional FS2 capabilities are outside this slice.

## Operational rules

No Git staging, commits, pushes, resets, merges or authorship changes. Preserve live
daemons, demo state, canonical results and unrelated edits. Use private fixture
state; no real EDA is needed. OCaml commands use `scripts/with-switch.sh`.

Build jobs share an aggregate pool of **20**, including nested builds/helpers.
Three implementation agents receive **6 each** in separate build directories;
the coordinator reserves 2 and normally waits. When agents finish, serial parent
verification may use `-j 20`. Do not run unbudgeted helper builds.

## Ownership and work packages

### A — Presentation and reconnect

Owner: presentation agent. Files: `terminal/main.ml` (exclusive during agent work),
`terminal/workspace_host.ml`, `terminal/presentation_preferences.ml`, preference
probe/restart tests. Separate build dir: `/tmp/opencode/fs3-integration-presentation`.

- Wire actual `Set_presentation` header changes/reset to persistence.
- Restore without repeated stale replay; preserve sparse overrides and current
  appearance schemes/defaults. Keep non-header tile overrides transient for now.
- Preserve same-daemon/session local state on reconnect, with identity validation
  and simulation/timing/launch response fences intact.
- Test real catalog actions where possible, polling/reset/restart, removed/retyped
  tiles, replacement sessions and delayed-response rejection.

### B — Templates and bootstrap protocol

Owner: templates agent. Files: `protocol/workspace.ml`,
`protocol/workspace_template.ml`, relevant protocol tests, `workspace_cli/`,
`terminal/workspaces/`, `terminal/host_view.ml`. Separate build dir:
`/tmp/opencode/fs3-integration-templates`.

- Add compatible optional preset identity; preserve unknown IDs honestly and
  retain membership/geometry/order/hidden state exactly.
- Honor generic Fit for custom workspaces without mutating requested geometry.
- Add explicit atomic/idempotent bootstrap semantics; distinguish newly created
  uninitialized state from legacy saved arrangements. Coordinate the final
  `main.ml` caller change through the coordinator, not a concurrent edit.
- Reuse shared definitions for current-preset starters where feasible; no second
  hard-coded current-layout table. Correct clone-name override validation.
- Test legacy templates/snapshots, renamed presets, stripped identities, stale CAS,
  startup ordering/idempotency and custom layout bounds.

### C — Setup and project reload

Owner: setup agent. Files: `setup/`, `project_integration/`, `backend/service.ml`
and focused backend tests, `protocol/v1.ml`, required HTTP plumbing,
`workspace_cli/` excluded, `dune-project`/generated opam metadata, installed-check
script if needed. Separate build dir: `/tmp/opencode/fs3-integration-setup`.

- Align initializer root validation with direct `dune-project` opener semantics.
- Define truthful successful manifest-only refresh alongside optional discovery
  jobs; adapt backend and protocol consumers except `terminal/main.ml` (send the
  coordinator exact required caller changes).
- Declare test-only Python tooling if supported by existing package conventions.
- Verify no-clobber initialization, initialize/open and initialize-after-open,
  aliases and controlled driver discovery without real ASIC work.

### Coordinator — integration, acceptance and documentation

Own this plan, other docs, `scripts/test-fs3-adoption.py`, and final shared client
adaptations after agents finish. Review and integrate ownership seams; add actual
HTTP/PTY assertions for header toggle/reset, template composition, bootstrap order
and manifest-only reload. Run matching binaries and record exact evidence.

## Verification gates

1. Focused unit/reducer tests for each package (agent budgets above).
2. Normal build, format/lint and full tests after integration, serial at `-j 20`.
3. FS3 native/private HTTP/PTY acceptance using actual command routes and restart.
4. Checklist/launch and FS2 regressions; terminal interrupt/restoration. Focused
   preset/custom Fit layout assertions. No live demo reset or real flow launch.
5. Installed initializer/client handoff in a private prefix where feasible.

## Progress and final evidence

- [x] Read-only merged-source audit and clean-baseline inspection.
- [x] Presentation/reconnect integration.
- [x] Templates/bootstrap integration.
- [x] Setup/reload integration.
- [x] Shared client integration and expanded native acceptance.
- [x] Final checks, documentation reconciliation and recorded results.

### Final implementation

- Actual catalog header/reset actions use the durable preference path; only explicit
  header overrides persist among tile fields. Restoration is a one-shot handoff.
- Same-session reconnect retains identities and local browsing, advances request
  generations and fences responses by transport and tile lifetime. Removed/moved/
  retyped/replacement identities clear stale local state. Timing and launch fences
  remain authoritative.
- Version-1 templates gained backward-readable optional `preset`; legacy templates
  are custom, unknown IDs are retained. Clone-name overrides precede portable-name
  validation. Shared definition starters support Overview/Timing/Testing.
- `Workspace.Operation.Bootstrap` atomically populates fresh defaults and publishes
  `defaults_initialized`; repeated calls are no-ops, regardless of prior import
  revisions. Legacy disk snapshots without the marker default to initialized.
- Initializer roots require direct `dune-project`. Refresh returns `job = None` for
  a successful driverless manifest reload or `Some job` for normal driver discovery.
  Both terminal callers handle these outcomes. Test metadata declares Python 3.

### Verified evidence

Full normal build, repository-wide format/lint and full tests passed serially via
`scripts/with-switch.sh` at `-j 20`. Agent builds used separate directories at 6 jobs
each; no aggregate allocation exceeded 20. Installed checks used 6 jobs alone.

| Check | Result / evidence |
| --- | --- |
| FS3 actual HTTP/CLI/PTY |140 checks; `/tmp/opencode/fs3-adoption-n5sxf42_/result.json` |
| Installed initializer/client, private prefix and HOME/XDG, unrelated cwd |passed; `/tmp/opencode/fs3-installed-setup-evidence-20261017/` |
| Checklist discovery/Plan/Launch regression |61 checks; `/tmp/opencode/checklist-workflow-371b032839a6/` |
| Launch/stage consistency regression |27 checks; `/tmp/opencode/launch-stage-consistency-3b465919425f/` |
| FS2 real Cyclesim/native HTTP/PTY |passed; `/tmp/opencode/fs2-native-rbxswj1k/` |
| Terminal interrupt/restoration |5/5; `/tmp/opencode/workbench-terminal-interrupt-w_h5134h/` |

FS3 acceptance includes imports before first TUI, pending bootstrap across daemon
restart, concurrent terminal startup with exactly one bootstrap revision, preserved
imports/user edits, preset/legacy/unknown roundtrips, and actual header toggle/reset
through polling and process restart. Manifest reload creates no jobs or metadata
calls. Reconnect/delayed-response behavior has focused reducer coverage rather than
an exhaustive native disconnection matrix.

An initial acceptance run failed on an obsolete root-error substring; subsequent
harness fixes decode Sexplib decimal escapes and compare the disk wrapper's complete
snapshot. These were harness mismatches, not waived product assertions. Normal
formatter differences were corrected before the passing full checks.

No real EDA, canonical-result edits, live daemon resets or Git authorship operations
were performed. Full multi-monitor attachment and freeform geometry remain later
scope. Preferences are project/environment-scoped, last-writer-wins between clients;
non-header per-tile overrides remain transient. Upgrade daemon/client/CLI together
because live records changed; older stored templates/registries remain readable.

Normal binaries and the persistent real-demo daemon/client/preset-export copies
are refreshed. Receipt in `hardcaml_asic_example`:
`.dev/workbench-real-demo/receipts/refresh-binaries-14357dcbbedb43c6855fbfbf1c429988/`.
No live process was restarted and no demo state was seeded. After active jobs
finish, restart the matching daemon/client pair normally; no reseed is required.
