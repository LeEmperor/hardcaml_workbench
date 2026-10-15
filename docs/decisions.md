# Product decisions and design intake

Updated 2026-10-15. **D1 accepted; D2 open; D3 partially settled.** Accepted choices
below are architectural requirements, not implementation claims. Architecture,
rendering, features and the demo plan are synchronized with D1.

## D1 — Workspace vocabulary and selection ownership

**Accepted by owner, 2026-10-15:** shared run selection by default, with explicit
independent inspection and per-tile references. This supersedes both the October 12
window-owned selection and the initial proposal of independent selection per workspace.

```text
Project session: shared providers/modules/run catalog and run contexts
  Main run context: selected run R43
  Window: attached terminal surface
    Workspace: Overview / Timing / Resources (named tile arrangement)
      Binding to Main (default) or an independent run context
      Tile instances
```

- Overview, Timing and Resources are **workspaces**, switchable in a window or
  displayed across windows. A **window** is an attached terminal/application surface.
- A **run context** owns selected-run state independently of workspace/tile lifetime.
  Default workspaces follow one project-session **Main** context.
- Any number of run-selector tiles control the same context. Overview's large
  selector and other workspaces' compact selectors are separate instances, not a
  replicated tile. Overview has no special ownership or control priority.
- Shared selected run does not share focus, filter, browsing cursor or scroll.
  Other selectors indicate the selection without forcibly stealing navigation.
- **Make independent** creates a context initialized from the workspace's current
  selected run. **Link to context** adopts that context's current selection.
- Following data tiles use the workspace's bound context. Per-tile pinning overrides
  it. Moving a following tile to another workspace adopts the destination context;
  pinned references remain unchanged. Moving a whole workspace between windows
  retains its context binding.
- Hiding/closing a selector does not destroy its context or affect execution.
  Closing a workspace cannot remove a context still used by another workspace.
- Linkage, per-tile binding and persistence are separate concerns. Templates create
  distinct tile/workspace instances; default Main linkage is deliberate. Saved
  sessions retain context identities/linkage rather than accidentally cloning them.
- Run contexts are Workbench UI/session state. Provider records never store them.

See [F04](features/workspaces_and_layouts.md) for host behavior and
[F10](features/run_contexts.md) for the shared-selection contract. Advanced named
groups can follow Main/independent support; no concrete serialization/API is imposed.

## D2 — Command and context semantics

Status: **open**. D1 settles the target vocabulary but does not approve all palette
execution/default-selection policy below.

**Need:** `Space c c`, `run synth`, remembered flow/profile, and shared button/CLI APIs.

Recommendation:

- Stable command IDs and typed arguments; fuzzy strings/keys are presentation.
- Remember launch flow/profile per project, separately from inspected run.
- Capture the invocation's project/workspace/run-context target, resolve explicit arguments and
  revalidate availability at acceptance. Never silently retarget after navigation.
- Show effective flow/profile/endpoint; provider preview identity guards launch.
- Prefer explicit command names for “run through stage” versus “continue from
  checkpoint”; expose only supported provider operations.

Questions: accept these defaults? Should a missing remembered flow require a new
selection (recommended) or explicitly offer the current project default? Numeric
flow aliases and richer command grammar can follow after the basic palette.

Unlocks F03 registry/context tests and consistent palette/button/automation behavior.

## D3 — Run-versus-snapshot binding

Status: **partially settled**. Follow-workspace-context and per-tile pinned-run
references are accepted as part of D1. Exact immutable-snapshot UX, first-demo
scope and missing-evidence retention policy remain open.

**Need:** following the selector, reference comparisons, and saved stage captures.

Binding distinctions:

| Mode | Behavior |
| --- | --- |
| Follow workspace context (accepted) | Bound context's selected run and relevant latest evidence |
| Pin run (accepted) | Named run; later published evidence can update the tile |
| Pin result snapshot (scope open) | Exact immutable observation, if supported and retained |

Recommendation: model all three distinctions now; deliver follow + pin-run first,
and enable exact snapshot pinning only when adopted provider references guarantee
it. Labels distinguish a live run reference from a frozen observation.

Questions: is a first-demo live reference sufficient, or must the first comparison
freeze a synthesis snapshot? What should a saved capture retain when canonical
evidence disappears: explicit unavailable, or a clearly labeled cached copy?

Unlocks F05 binding identities, persistence and revision tests. A layout template
should not accidentally capture an experiment-specific run unless explicitly saved
as such; a session restoration may preserve those references.

## D4 — Appearance intake and implementation scope

Recorded 2026-10-15 from the owner's supplied handoffs and instruction that initial
demos need not prioritize aesthetics. This records design direction, not a selected
visual default or delivered UI. See [source interpretation](design/README.md).

- Newer gallery v0.5 supersedes the older design-system handoff for appearance.
  Both exports are retained locally; update the newer handoff in place after review.
- Theme/components/layout are separate from domain modules and workspace identity.
  A–E remain candidates; D's tabs are composable with other skins. Color, icons and
  density stay independent. A provisional demo skin does not choose the final default.
- Navigation/status/legend chrome is generally mountable tiles, most headers are
  configurable/default-on, and thin host input/recovery works even with chrome hidden.
- Planned daemon registry owns semantic instances and run-context linkage; clients
  own local presentation. The export's “already implemented” wording is corrected
  by source review. Implement the registry once in the main host workstream.
- Inspect/adapt Ches single-transient-float APIs before overlay work; do not infer
  arbitrary stacking, nonmodal peeks or reusable editor embedding from them.
- FS0/M2 gets structural seams and legibility. FS5/V1 gets the actual five-candidate
  terminal gallery. The export's gallery-first schedule does not delay functional
  ASIC/test demos. No new provider formats or appearance-dependent cache keys.

Open after prototypes: preferred default/combinations, concrete dimensions/tokens,
shared-library packaging, richer float behavior and real Ches editor hosting.
