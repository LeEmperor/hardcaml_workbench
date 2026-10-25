# Layout-defined tile focus order

Status: implemented and validated, 2026-10-25. The user authorized execution after
reviewing the plan. Three general agents completed the work packages below.

## Goal

Tab should move through workspace tiles in a predictable layout-defined order;
Shift-Tab should traverse the exact reverse, with wraparound. In Overview, complete
the left column before moving to the right: Session → Runs → Stage checklist →
Planned run, then the stage tiles. Preserve the existing workspace-tabs focus stop.

## Findings

- `terminal/workspace_host.ml`: `tiles` filters the persisted tile list for the
  active workspace, visibility and zoom. The `input` focus branch cycles that list.
- `protocol/workspace.ml`: preset application and arrangement reset retain existing
  tiles and append missing ones. This can leave Runs last in an older session,
  even though `terminal/workspaces/stock.sexp` already places it after Session.
  The user's live snapshot has not been inspected; its specific history is unknown.
- The declarative layout tree already expresses grouping and sequence. Its leaf
  order can supply navigation without a separate focus-order configuration field.
- `terminal/workspaces/layout.ml` resolves layout keys and appends unmatched tiles.
  Its geometry output is deliberately returned in input-index order; changing that
  output order could break tile/rectangle associations.
- `render_definition` and `layout_keys` in `terminal/workspace_host.ml` resolve
  configured layouts and keyed tile identities, including repeated kinds.

## Implemented behavior and API

Add a pure layout helper returning input indices in resolved tree traversal order.
Traverse stacks top-to-bottom, columns left-to-right (completing each subtree),
and treat `Narrow` as transparent. Reuse layout resolution so missing leaves,
duplicate references and unmatched extras have the same semantics as placement.
Keep geometry output ordering unchanged.

Add a separate host navigation helper rather than changing `tiles` globally.
Start with eligible tiles, use the active render definition and configured keys,
then map traversal indices back to tile identities. Use that sequence in forward
and reverse focus cycling. Without a usable layout definition, retain existing
registry order. Do not reorder persisted tiles or require a session migration.

### Final layout-mode decision

Fit uses the declared tree, but Preferred currently packs tiles in registry order;
small Fit layouts can also fall back to a registry-ordered grid. Compact renders
only the focused tile. A geometry-only navigation sequence would trap Compact
focus and is therefore unsuitable.

Implemented policy: tree order in Fit, including its Compact fallback; registry
order in Preferred. Responsive Fit fallback retains semantic tree order across
resizes. Agent 3 verified and documented this policy with rendering and navigation
tests. The small-window grid can therefore have a different visual row order from
Tab order. Exact visual order in every responsive fallback would require a future
shared placement/navigation policy change.

Public helpers are `Layout.navigation_order definition ~kinds : int list` and
`Workspace_host.navigation_tiles host`. Geometry computation and persisted tile
order are unchanged.

## Agent work packages

Use up to three **general** implementation agents. The coordinator owns this plan,
handoffs, integration review and final checks. Agree on the helper signature and
layout-mode policy before overlapping implementation.

### Agent 1 — Pure layout traversal

Owned files: `terminal/workspaces/layout.ml` and
`terminal/workspaces/test_workspaces.ml` (plus an interface if required).

- [x] Add the input-index traversal helper, reusing resolved layout semantics.
- [x] Assert stock layout sequences, especially Overview's left-column sequence.
- [x] Cover shuffled input with Runs last, missing leaves, extras, nested/weighted
  columns, Narrow and empty layouts.
- [x] Cover configured keys with duplicate tile kinds.
- [x] Verify geometry remains associated with the same original input indices.

Handoff: helper signature, traversal/fallback contract and focused test results.

### Agent 2 — Host focus integration

Owned file: `terminal/workspace_host.ml`.
Depends on Agent 1's helper contract and the agreed mode policy.

- [x] Add a navigation-specific tile sequence using `render_definition` and
  `layout_keys`; preserve the existing general-purpose `tiles` contract.
- [x] Use it for Tab and Shift-Tab, preserving input precedence and effects.
- [x] Add a persisted-order regression with Runs last and exact forward/reverse
  cycles, including wraparound.
- [x] Cover hidden tiles, zoom, missing focus, empty workspaces, configured layouts
  and stable extras; retain prefix-reset and no-effect behavior.
- [x] Preserve palette/filter capture and existing overlay routing semantics.

Handoff: host behavior, compatibility notes and focused test results.

### Agent 3 — Rendering consistency and integration coverage

Owned files: `terminal/host_view.ml` tests and
`terminal/workspaces/README.md`. Audit `terminal/main.ml` overlay routing read-only
unless a necessary change is agreed with the coordinator.

- [x] Resolve the mode-policy question above before implementation integration.
- [x] Verify declared traversal matches normal Fit grouping for stock layouts and
  a custom layout whose keyed order differs from tile registry order.
- [x] Add meaningful Fit/Preferred/Compact/responsive fallback coverage, preserving
  tile-to-geometry association and navigation reachability.
- [x] Document layout authoring order and any responsive-mode qualification.
- [x] Report any cross-file fix to the coordinator before editing another agent's
  owned files.

Handoff: final mode policy, integration coverage and user-facing documentation.

## Execution policies

- No direct mutative Git operations: no add, commit, amend, push, or authorship
  changes. Read-only status/diff inspection is allowed. Existing script-internal
  Git operations are allowed by the user, but operations that create GitHub
  authorship require manual approval.
- The aggregate build/test job pool must never exceed **20**. Prefer coordinator-
  only validation with agents doing no builds, and run Dune with `-j 20` or less.
  If concurrent agent tests are necessary, allocate at most 6 jobs to each agent
  (18 total), leaving 2 for the coordinator; every Dune invocation must use its
  assigned `-j` cap. Account for subprocess parallelism too.
- The coordinator primarily handles docs, orchestration and verification; agents
  perform the substantial implementation work. At most three general agents may
  implement concurrently.
- Changes to `hardcaml_asic` and `hardcaml_asic_example` are permitted if necessary;
  none are currently expected for this terminal interaction feature.
- Preserve unrelated local changes. The implementation hold was lifted by the
  user's subsequent authorization.

## Coordinator acceptance checklist

- [x] Record the agreed mode policy and agent ownership before implementation.
- [x] Review diffs for consistent identity handling and unchanged persistence.
- [x] Run relevant workspace and terminal Dune test targets with an explicit job
  cap; inspect their Dune definitions to select exact targets before execution.
- [x] Demonstrate in regression tests Overview Tab/Shift-Tab with Runs last in registry order: Session
  → Runs → Stage checklist, reverse traversal, and wraparound.
- [x] Verify hidden/zoom/custom-layout cases and the decided responsive behavior.
- [x] Record commands, outcomes and remaining limitations in this document.

## Validation results

All builds/tests ran centrally and sequentially; implementation agents ran none.

- `dune runtest -j 20 terminal/workspaces terminal` — passed.
- `ocamlformat --inplace terminal/workspaces/layout.ml terminal/workspaces/test_workspaces.ml terminal/workspace_host.ml terminal/host_view.ml` — completed.
- `dune build -j 20 terminal/main.exe @terminal/runtest` — passed after formatting,
  including workspace and terminal regression tests and the terminal executable.
- `git diff --check` — passed.

The Runs-last reproduction is a snapshot-round-trip regression fixture, not an
inspection of the user's running session. Headless input/render tests verify the
interaction; no interactive terminal session was driven. Existing unrelated local
changes were preserved. No mutative Git operations or external repository changes
were made.
