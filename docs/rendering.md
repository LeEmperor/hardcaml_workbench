# Hardcaml Workbench — Rendering and Interaction

The [architecture](hardcaml_workbench_architecture.md) owns semantic boundaries;
the [plan](construction_phase_plan.md) owns implementation order. This document
owns the intended Bonsai Term presentation. These are requirements for the new
workspace, not descriptions of the current fixed terminal renderer.

## 1. Workspace, windows and monitor use

A workspace contains windows. A window is a logical rendering surface normally
shown in one terminal window on one monitor; a monitor is not an application
identity. The terminal emulator/OS handles physical placement. Multiple windows
can show the same project with independent selected runs and layouts.

Start with a useful ASIC layout preset, then let the user move/reorder, resize,
hide/restore and zoom tiles. Save requested layout separately from effective
clamped geometry so shrinking does not destroy the preferred wide layout.
One run-selector tile controls its window's default run context.

Illustrative wide window, not a fixed cell budget:

```text
test-asic / bring-up     Window: physical     Selected run: C      Connected
┌ Runs ────────┐ ┌ Flow / operations · C ──────────────────────────────┐
│ C  running  ◀│ │ route: running · elapsed … · observed …             │
│ B  complete │ └────────────────────────────────────────────────────┘
│ A  failed   │ ┌ Timing · C ──────────┐ ┌ Checks / artifacts · C ─────┐
│             │ │ setup: pending      │ │ DRC: pending                │
│             │ │ hold: pending       │ │ report / layout links       │
└─────────────┘ └─────────────────────┘ └────────────────────────────┘
┌ Timing · B [PINNED REFERENCE] ───────┐ ┌ Output · C ─── FOLLOW ─────┐
│ setup/hold, corner, stage, source   │ │ …                           │
└────────────────────────────────────┘ └────────────────────────────┘
```

Clock, physical-design and regression tiles can replace or extend this preset.
The example's run statuses and pending values are illustrative, not captured tool
evidence. Wider dimensions do not automatically summon unwanted tiles.

## 2. Run selection and loading

- Follow-window is the default; tile titles identify the run being displayed.
- Selecting B changes ordinary tiles to B's data. Switching never starts a tool.
- Uncached content shows "Loading run B". Do not draw A's values below a B header.
- Pinned tiles prominently identify their reference run and remain unchanged.
- New background runs do not steal selection. An explicit launch-and-view action
  selects its new run only in the initiating window once its identity is known.
- Queued submission before provider allocation has its own label, not a fake run ID.
- Missing saved runs remain unavailable. Do not silently choose another run.

Expected work may show pending/running animation. Distinguish not requested,
unsupported, no result, failure, cancellation, stale observation and unconstrained
analysis. An unsupported power-analysis tile must not spin indefinitely. Elapsed
time, observation age and measurement age are different fields. Do not fabricate
percentage or ETA from elapsed time or log volume.

## 3. Shared shell and styles

Use Ches as a reference for comfortable spacing, restrained accents, rounded or
thin borders, title/footer labels and clear selection. Reuse design principles,
not editor-specific primary-document assumptions or a dependency on its UI code.

Centralize semantic theme roles: background, foreground, surface, muted, border,
focus, selection, running, success, warning and failure. One coherent default
theme comes first. Labels/markers retain meaning without color or special fonts.
Stderr is a stream identity, not evidence of failure; avoid a wall of red logs.

Measure terminal display cells, accounting for wide and combining characters.
One geometry computation supplies shell/content rectangles, clipping, scrolling,
cursor and any hit testing. Respect nonzero origins. Tile adapters declare useful
minimum/preferred sizes; degradation reduces decoration before essential context.
At tiny sizes, preserve recoverable navigation/help rather than throw exceptions.

Keep project/run identity and connection health easy to find, but move full IDs,
paths and environment details to inspection. A compact overview may remain visible
in the default preset; users are not forced into one global persistent dashboard.

## 4. Focus and commands

The window host routes input to the focused tile and visibly marks focus. A modal
picker/help surface captures input before tiles and global actions. Text entry
must not accidentally trigger build/cancel shortcuts. Keep focus/selection stable
when jobs, logs or results arrive. Select list items by identity, not row index.

Define command identity, availability/reason, bindings and description once; derive
dispatch, help and hints from that definition. Exact keys are settled during P3.
Provide discoverable run selection, tile movement/resize, focus navigation,
inspection, back/close, help and client exit. Moving a follow-window tile into a
different window adopts that window's run; pinned tiles keep their reference.

Logs have bounded scrollback and explicit follow state. Scrolling away pauses
follow; a visible command resumes it. Artifact readers page large content and show
retrieval limits. Closing/hiding readers does not stop their generating job.

## 5. Explain and inspect evidence

Timing summaries show setup/hold independently with units, corner/mode, stage,
clock/constraint context and source report. A failed goal links to details and a
short explanation. Checks identify their scope and evidence separately from flow
completion. GDS existence is an artifact fact, not signoff.

Clock and physical-design views explain available observations without inventing
coverage. An overview joining modules displays only compatible run contexts.
For a pinned timing reference, keep differences in corner/stage/constraints
visible. A dedicated comparator is [deferred](backlog/README.md).

Start artifact inspection with text/reports and external viewer actions. The UI
identifies the viewer host and reports unavailable display/transfer capability.
An SSH terminal cannot imply that a daemon-side GUI appears on the user's monitor.
Embedded graphical views are a later scope decision.

## 6. Headless-first implementation

Expose testable Bonsai components with explicit state, dimensions, time and
transport effects. Publish async state changes reactively; use clocks for actual
elapsed/freshness displays rather than periodically rereading all mutable state.
Batch large streams while keeping interactions responsive.

Tests send events through the production frontend, not just its reducers:

1. Select B while A queries are pending; complete A later and verify B stays correct.
2. Pin timing A, select B, and verify only ordinary tiles change.
3. Launch once, hide/move its tile, then reconnect without another submission.
4. Attach two windows; selection/focus/scroll remain independent while run data updates.
5. Resize, restore layout, scroll/pause/resume logs and exercise modal input capture.

Use injected responses and controlled clocks; assert actions/state separately from
a few component/frame expectations. PTY checks cover terminal plumbing. Human
review is for style/readability/comfort, not a prerequisite for every interaction.

## 7. Existing baselines

The pre-redesign capture script and fixtures remain useful historical evidence:

```sh
./scripts/capture-terminal-baseline.sh --check
```

Files remain under `test/baselines/terminal/`; the [archived capture notes](archive/2026-10-12/terminal_baseline_captures.md)
describe them. They include synthetic scenarios and do not establish live ASIC
integration. Replace affected expectations deliberately as the new renderer ships,
without promoting unrelated behavior or treating old fixed layouts as requirements.
