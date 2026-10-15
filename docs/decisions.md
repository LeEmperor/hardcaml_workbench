# Product decisions and design intake

Updated 2026-10-15. **D1 and D2/D3 FS0 defaults accepted.** The owner explicitly
approved the bounded defaults in the initial tool question, **Approve scope**.
Later command grammar, immutable snapshots and retention policy remain unresolved.
These are product decisions; delivered behavior and gaps are tracked in the
[construction plan](construction_phase_plan.md) and [acceptance](fs0_acceptance.md).

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

Status: **FS0 defaults accepted** by the owner's **Approve scope** answer.

**Need:** `Space c c`, `run synth`, remembered flow/profile, and shared button/CLI APIs.

Accepted defaults:

- Stable command IDs and typed arguments; fuzzy strings/keys are presentation.
- Remember launch flow/profile per project, separately from inspected run.
- Capture the invocation's project/workspace/run-context target, resolve explicit arguments and
  revalidate availability at acceptance. Never silently retarget after navigation.
- Show effective flow/profile/endpoint; provider preview identity guards launch.
- Prefer explicit command names for “run through stage” versus “continue from
  checkpoint”; expose only supported provider operations.
- A missing remembered flow/profile requires explicit selection; never substitute
  the first catalog entry or current project default.
- Ordinary launch does not select its allocated run. Explicit **Launch and view**
  selects only when the captured workspace/context binding and selection revisions
  still match. Navigation or a newer selection must not be overwritten.

Delivered FS0 includes the palette, target revalidation, exact preview launch and
persisted client-local remembered Plan inputs; see [terminal policy](fs0_terminal.md).
Later policy: numeric flow aliases, richer grammar and shared preference services.

Unlocks F03 registry/context tests and consistent palette/button/automation behavior.

## D3 — Run-versus-snapshot binding

Status: **FS0 scope accepted**: follow-workspace-context and per-tile pinned-run
references first; exact immutable snapshots deferred. The owner approved this
first-demo scope in **Approve scope**. Later immutable-snapshot UX and archival/
missing-evidence retention policy remain open.

**Need:** following the selector, reference comparisons, and saved stage captures.

Binding distinctions:

| Mode | Behavior |
| --- | --- |
| Follow workspace context (accepted) | Bound context's selected run and relevant latest evidence |
| Pin run (accepted) | Named run; later published evidence can update the tile |
| Pin result snapshot (deferred beyond FS0) | Exact immutable observation, if supported and retained |

Accepted FS0 delivery: follow + pin-run, with labels distinguishing a live run
reference from a frozen observation. Enable exact snapshot pinning later only when
adopted provider references guarantee it; the current wire binding has no snapshot mode.

Later questions: snapshot identity/retention guarantees and what an archival saved
capture retains when canonical evidence disappears. FS0 already labels L2 data
`Cached_unverified`, refresh failure and missing source explicitly; cached bytes
are not an authoritative frozen observation.

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
- The delivered daemon registry owns semantic instances and run-context linkage;
  clients own local presentation. The imported export was not implementation
  evidence; FS0 now supplies the single registry used by the host.
- Inspect/adapt Ches single-transient-float APIs before overlay work; do not infer
  arbitrary stacking, nonmodal peeks or reusable editor embedding from them.
- FS0/M2 gets structural seams and legibility. FS5/V1 gets the actual five-candidate
  terminal gallery. The export's gallery-first schedule does not delay functional
  ASIC/test demos. No new provider formats or appearance-dependent cache keys.

Open after prototypes: preferred default/combinations, concrete dimensions/tokens,
shared-library packaging, richer float behavior and real Ches editor hosting.
