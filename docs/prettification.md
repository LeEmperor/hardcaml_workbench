# Terminal prettification and Bonsai refactoring

Written 2026-09-20 following a source-level audit of the terminal client, the local
`bonsai_term_examples` checkout, and the installed Bonsai Term interfaces.

## 1. Purpose and release context

Make Workbench comfortable to use as the everyday ASIC build/flow dashboard for
`hardcaml_protemu` in `../scaf/`. The visual ambition is the readability and polish
of tools such as btop and the Jane Street Proctopus/Dissect demonstrations: stable
regions, clear selection, useful color, discoverable commands, and dense but
legible information. Those applications are visual references, not audited
implementation dependencies.

The current terminal is functional, but most of its presentation is diagnostic
text clipped into rectangles. Adding more flow information to that structure will
make it harder to use. A small presentation system and a more idiomatic Bonsai
state/component structure are worthwhile now, before the dashboard grows further.

This work must produce useful increments. A complete frontend rewrite, generic
widget framework, or exhaustive theme system must not become another monumental
prerequisite to seeing a real ASIC flow run.

### Authority and starting point

- The [architecture's active release scope](hardcaml_workbench_architecture.md#active-release-scope--protemu-monitoring-2026-09-20)
  remains authoritative for product scope and evidence semantics.
- The [construction plan](construction_phase_plan.md#active-release--scaf-build-and-flow-dashboard-2026-09-20)
  owns D1–D4 release progress. This document supplies the supporting UI/refactoring
  work packages, called P0–P5, rather than a competing release roadmap.
- The existing 1A–1C foundation includes daemon-owned execution, discovery, RTL,
  artifacts, and structured hierarchy. Final hierarchy human acceptance passed on
  2026-09-20. Preserve those capabilities while improving their presentation;
  per-node reports and broader graph exploration remain deferred.
- The findings below describe the source at audit time. They are not a new live
  terminal acceptance result. The implementation phases are initially unstarted.
- Proposed internal module boundaries below are implementation guidance. Record
  adopted architectural or protocol changes in the architecture first, and record
  validation evidence in [development.md](development.md).
- [terminal_layout_spec.md](terminal_layout_spec.md) is the concrete layout contract
  produced by P0 item 2: verified cell budgets at 80×24 and 120×40, the persistent
  summaries, overflow and responsive rules, and the layout acceptance criteria. The
  schematic wide layout in section 3 below is the earlier sketch it supersedes.

## 2. Audit: why the current screen is hard to read

The main concentration is [`terminal/main.ml`](../terminal/main.ml), especially
`render`, its local `pane` helper, the `*_lines` functions, and `tui`.

| Finding | Effect | Direction |
| --- | --- | --- |
| Almost all normal content is an unstyled `string list` | Titles, identifiers, statuses, and failures have equal visual weight | Compose styled views from semantic fields |
| Fixed one-third-width project pane and approximately half-height upper region | At 80×24 the project pane is just 26×10 cells | Content-aware compact and wide layouts |
| Project, integration, targets, configurations, artifacts, and Dune items are concatenated | Later sections disappear under `List.take` | Short summary plus focused browsers/details |
| Selected-job details precede job rows | At 80×24 a normal selected job leaves roughly three visible job rows | Compact detail summary and a real list viewport |
| Full internal job ID leads each row | State and action are pushed off-screen; `%-24s` is a minimum, not a maximum width | Action-first rows, compact display identity, full ID in details |
| Controls occupy one 148-column string | At 80 columns, important navigation/cancel/quit hints disappear | Short primary command bar, contextual hints, help overlay |
| Job selection has no matching scroll offset | Keyboard selection can leave the visible list | Keep selected item within the viewport |
| Logs always show the tail; artifact content shows its first lines | Long output cannot be properly explored | Scrollback, explicit follow state, paging |
| Selection is an index into a newest-first job list | A new arrival can change what is selected | Select by stable `Job_id`, derive the visible index |
| Connection state and command feedback share `session.status` | Polling overwrites useful action feedback with `connected` | Separate connection health and notifications |

`hierarchy_view_lines` and connection-details rendering also mutate scroll state
while drawing. Most application state is held in mutable session fields, and a
100 ms clock causes `render` to reread them. This works as a bridge, but obscures
which event caused a change and makes deterministic component tests harder.

The existing [`presentation.ml`](../terminal/presentation.ml) and
[`state.ml`](../terminal/state.ml) already contain useful pure functions and tests.
Preserve and build on these rather than replacing working protocol reduction.

### Text measurement is a prerequisite to decoration

`fit`, path truncation, wrapping, and padding currently use byte lengths/slices.
UTF-8 byte count is not terminal cell width. Unicode names, tree branches, and
wide characters can therefore break alignment or be split incorrectly.

For composed rows, prefer `View.width`, `View.dimensions`, and view-level cropping.
For text that needs wrapping or an ellipsis, use Unicode-aware iteration and cell
measurement; `View.uchar_tty_width` is available. Exercise combining and wide
characters as well as ordinary ASCII. Avoid requiring emoji, Nerd Fonts, or
Powerline glyphs for essential controls. Box drawing should have a simple fallback
if the actual terminal environment needs it.

## 3. Visual and interaction direction

### A restrained instrument dashboard

Use a neutral background, readable foreground, quiet panel boundaries, one focus
accent, and a small set of semantic status colors. Color should help answer
“what is selected?”, “what is running?”, and “what needs attention?”. It should
not make every heading compete for attention.

| Semantic role | Suggested treatment |
| --- | --- |
| Primary text | High-contrast foreground |
| Secondary metadata and inactive borders | Muted slate, still readable |
| Focused pane and hotkeys | Blue or lavender accent |
| Selected row | Full-row contrasting background plus a selection marker |
| Running | Cyan/blue with a `RUNNING` label; optional small activity indicator |
| Passed / complete | Green with an explicit state label |
| Failed | Red with an explicit state label |
| Warning / blocked | Amber with an explicit state label |
| Pending / skipped / unsupported / cancelled | Distinct labels, mostly neutral colors |

Keep palette names out of business logic: components ask for `Theme.failure`,
`Theme.focus`, or `Theme.secondary`, not a particular RGB value. Catppuccin Mocha
is a reasonable first palette. Ship one coherent default before adding extensive
customization. Allow a palette/monochrome fallback where needed; state meaning must
survive loss of color. Explicit foreground/background pairs avoid accidental
contrast failures from mixing a fixed foreground with an unknown terminal theme.

Stderr is not itself a failure verdict. Tool progress frequently uses stderr.
Use a quiet stream marker and reserve error emphasis for actual error evidence.
Logs should not turn into walls of red or repeat a large `[stdout]` prefix on
every line. If ANSI-styled tool output is later supported, decode supported
formatting into view attributes rather than passing control sequences as text.

### Persistent summaries, navigable details

The ASIC release requires identity, execution, timing, and stage outcomes to stay
visible. The main screen should devote space to these, with secondary workspace
metadata and complete identifiers in details views.

Schematic wide layout, using illustrative data rather than implemented telemetry:

```text
 Hardcaml Workbench   scaf / protemu                       ● Connected
 [b] Build  [t] Test  [g] RTL   [Tab] Focus   [?] Help   [q] Quit

 Run: selected-run    Target: protemu    Config: default
 Source: abc1234      Edited tree: dirty      Result inputs: abc1234

 ┌ Flow ─────────────────────────────────────────────────────────┐
 │ Build ✓  Emit ✓  Preflight ✓  Run ▶  Postcheck ·  Collect · ...│
 └───────────────────────────────────────────────────────────────┘
 ┌ Timing · selected run ─────────┐ ┌ Results / design ───────────┐
 │ Setup WNS     pending         │ │ DRC          pending       │
 │ Hold WNS      pending         │ │ LVS          pending       │
 │ Corner/mode   —               │ │ Cell area    unavailable   │
 └───────────────────────────────┘ └────────────────────────────┘
 ┌ Jobs ─────────────────────────────────────────────────────────┐
 │ ▸ Run physical flow       RUNNING       selected-run    03:42 │
 │   Emit RTL                COMPLETE      selected-run    00:02 │
 └───────────────────────────────────────────────────────────────┘
 ┌ Output · Run physical flow ─────────────────── FOLLOWING ─────┐
 │ ...                                                          │
 └───────────────────────────────────────────────────────────────┘
 Jobs: ↑/↓ select · Enter details                 Updated 1s ago
```

The final command bar must reflect declared available operations, including the
project flow launcher once available. The abbreviated flow strip above is only
an illustration: the implementation must preserve all declared stage outcomes,
for example by wrapping into two rows at compact widths.

That sketch is now superseded by [terminal_layout_spec.md](terminal_layout_spec.md),
which fixes the actual cell budgets, wraps the eight declared stages into two rows at
both reference sizes, and replaces the illustrative box borders with labelled rule rows
so the rows they would have cost go to output instead.

Define layout modes by available cell budgets, not by blindly scaling every pane:

- **Wide:** side-by-side timing/results and useful job/output viewports.
- **Compact (design against 80×24):** condensed identity, wrapped stage strip,
  setup/hold and check summaries, one main browsing/detail region at a time.
- **Below the usable budget:** explicit recoverable small-terminal view. Establish
  its threshold from the new layout; the current 68×20 limit is not a design goal.

Reduce decorative borders before sacrificing essential data. Every supported
layout must keep help/quit discoverable and focused selection visible. Scroll
overflow deliberately; do not silently clip entire features out of existence.

### Commands, focus, and tmux

Put primary actions at the top, contextual navigation and feedback at the bottom,
and the complete command list behind `?`. Highlight the key separately from its
description. Tmux's own status line occupies space outside the application pane;
top-positioned Workbench controls do not technically conflict with it. Avoid an
extra-heavy header so two adjacent bars do not become visually oppressive.

Introduce explicit pane focus and common navigation:

- Tab / Shift-Tab cycle focus; show the focused pane visibly.
- Up/down and optionally j/k navigate the focused list.
- Left/right collapse/expand trees where appropriate.
- Enter inspects the selected item; Escape closes a detail/overlay.
- Page Up/Down and Home/End navigate long lists and output.
- Scrolling away from the log tail disables follow; an explicit action resumes it.
- A modal help/picker handles input before underlying panes. Typing into future
  search fields must not accidentally trigger build, cancel, or quit shortcuts.

The current u/o hierarchy navigation and bracket-based diagnostics scrolling can
remain temporary compatibility bindings during migration. Shared navigation and
visible focus are the destination, rather than an expanding global alphabet.

Define commands once, with key, label, scope, availability, and action. Generate
the hints/help and dispatch from the same definitions. A command without its
required target or capability should have an understandable unavailable state.
Resolve exact shortcuts alongside implementation, retaining essential help at
compact widths rather than truncating an arbitrary suffix of the command list.

### Evidence must remain visually honest

- Separate process completion, flow-stage outcome, timing goals, and check verdicts.
- Show setup and hold independently, including units, corner/mode, source stage,
  constraint context, and age when available.
- Pending, unavailable, unconstrained, and unsupported are not successful zeroes.
- Associate every result with its named run/build. Current edited source and the
  immutable inputs of a displayed result are different identities.
- A previous-run reference must identify itself as historical; it cannot fill a
  current run's pending box as though it were current evidence.
- Separate connection freshness, log activity, and confirmed progress. A quiet
  process is not automatically hung, and a spinner is not percentage completion.
- Preserve the existing detailed distinctions for empty logs, fetch errors, EOF,
  cancellation, launch failure, and process exit status.

## 4. Refactoring toward idiomatic Bonsai

“More Jane-y” here means typed models/actions, explicit effects, reactive inputs,
small reusable components, and deterministic tests. It does not require copying
every detail of an example or moving transport resources into a UI state machine.

### Suggested ownership and data flow

```text
 daemon updates / request results
               │
       async client boundary
               │ typed events
               ▼
    application model + pure reducers
               │
       derived display models
               ▼
     Bonsai components → View.t
               ▲
   focus / selection / viewport actions
```

- **Transport boundary:** owns HTTP clients, polling, reconnection, and outstanding
  requests. Publish results through Bonsai effects/state or a narrow observable
  bridge. Preserve instance checks, event sequencing, and stale-response rejection.
- **Application data:** server-derived project/job/artifact state uses the existing
  pure reducers. UI changes must not weaken daemon execution ownership or replay
  commands after reconnect.
- **Client UI model:** typed focus, stable selected IDs, open inspector, per-view
  viewport/follow state, and notifications. Keep these local to the client.
- **Display models:** derive compact labels, semantic statuses, provenance, and
  availability from typed data. Do not reparse human-readable strings for styling.
- **Components:** consume data and dimensions, return views and events/effects.
  Let local state live in components where that keeps ownership clear.

Follow the Pomodoro example's separation of model, action, transition, rendering,
and keyboard handling, while retaining Workbench's stronger asynchronous identity
requirements. Use ordinary `Bonsai.state`/`Bonsai.state_machine` and derived values
where appropriate. Avoid a single enormous state machine that replaces the
current enormous mutable record without improving boundaries.

Update views when observable data changes. Reserve clocks for elapsed-time labels,
freshness, and bounded animations; remove the general 100 ms “reread everything”
tick once state publication is reactive. Reconcile selection and scroll offsets
in transitions/layout preparation, not as side effects of drawing. Inject `now`
into display calculations so tests can freeze time.

Illustrative module split, to be adjusted to actual component boundaries:

```text
terminal/
  main.ml             CLI and startup wiring
  client.ml           transport/polling boundary
  state.ml            pure server-data reducers and selection reconciliation
  app.ml              Bonsai root, focus, command routing
  theme.ml            semantic style roles
  commands.ml         binding/help/action definitions
  layout.ml           cell budgets and layout modes (terminal_layout_spec.md)
  widgets.ml          small shared panel, badge, key-hint, row helpers
  jobs.ml             list and selected-job summary
  output.ml           logs/artifact viewports and follow state
  dashboard.ml        flow, timing, checks, design summaries
  hierarchy.ml        existing hierarchy inspector presentation
```

Keep pure rendering/components in a testable library rather than burying them in
the executable. Avoid introducing a generic dashboard/plugin/layout framework.
Extract each part when its implementation phase needs it; preserve a working
installed client throughout.

## 5. Local examples and available APIs

These relative links intentionally reference the sibling checkout, which is kept
locally as reference material. They work in this workspace, not necessarily from
the Workbench repository alone on GitHub.

| Example | What to borrow | Qualification |
| --- | --- | --- |
| [Catppuccin](../../bonsai_term_examples/catppuccin/src/bonsai_term_catppuccin_example.ml) | Semantic palette source, colored spans, selected tabs, background and padding | Centralize Workbench roles rather than scattering palette lookups |
| [Pomodoro implementation](../../bonsai_term_examples/pomodoro_timer/src/bonsai_term_pomodoro_timer_example.ml) | Model/action split, state machine, effects, styled instructions | A small demo, not an asynchronous application architecture specification |
| [Scroller](../../bonsai_term_examples/scroller/src/bonsai_term_scroller_example.ml) | Scrollable regions and less-like navigation | Adapt handler ownership to pane focus; the embedded source path also needs checking before building the example |
| [Tree view](../../bonsai_term_examples/tree_view/src/bonsai_term_tree_view_example.ml) | Tree rendering and muted branch structure | Its example does not supply the full interactive selection/expansion model |
| [ncdu](../../bonsai_term_examples/ncdu/src/bonsai_term_ncdu_example.ml) | A composed weighted hierarchy browser | Useful later if actual per-node measurements justify it |
| [Process bar chart](../../bonsai_term_examples/bar_chart_process_info/src/bonsai_term_bar_chart_process_info_example.ml) | Reactive chart data and dimension-aware rendering | Secondary resource telemetry follows the flow dashboard |
| [Responsive dimensions](../../bonsai_term_examples/responsive_dimensions/src/bonsai_term_responsive_dimensions_example.ml) | Explicit reactive dimension input | Demonstrates the input, not a complete responsive layout system |
| [Pomodoro tests](../../bonsai_term_examples/pomodoro_timer/test/test_pomodoro_timer.ml) | Fixed dimensions, synthetic input, controlled clock | Use the harness idea, not the suite's snapshot granularity or every assertion |

The audited installed `5.2.0+ox` base library exposes `Attr.fg`, `Attr.bg`,
`Attr.bold`, RGB and xterm-256 colors, `View.hcat/vcat/zcat`, padding, cropping,
dimensions, `View.with_colors`, and `View.uchar_tty_width`. These are enough for
the first substantial facelift without adopting a different terminal library.

At audit time only `bonsai_term` of the relevant terminal/test packages was
installed; `bonsai_term_components`, `bonsai_term_test`, and `bonsai_test` were
absent. Matching `v0.18~preview.130.106+341` package metadata for the first two was
available. Verify dependency resolution and actual APIs before adoption. Installed
`.mli` files under `~/.opam/5.2.0+ox/lib/` are authoritative for the installed
version; a master-branch example is not proof of compatibility. Declare runtime
components and test-only dependencies in their appropriate package roles.

## 6. Testing without snapshot paralysis

A visual expectation is a reviewable contract for one chosen rendering. A deliberate
redesign legitimately changes that contract. Churn becomes excessive when every
behavioral test snapshots the entire application, including unrelated decoration.

The Pomodoro suite repeatedly snapshots a full 80×20 frame. Moving its instruction
block would affect many unrelated tests. More importantly, the test named “Timer
advances to next phase when it reaches zero” expects `Work / 24:59 / Running` after
the large clock advance. Whatever the scheduler mechanics, that expectation does
not prove the behavior named by the test. Promoting observed output is not a
substitute for deciding whether the output is correct.

Use four complementary levels:

1. **Behavioral assertions without frames.** Selection survives new jobs, focused
   navigation affects the right pane, scrolling pauses follow, overlays capture
   keys, stale responses cannot replace current data, and missing timing stays
   unavailable. Test timer-derived behavior with controlled time and the required
   stabilization steps rather than assuming one large advance replays every tick.
2. **Small component expectations.** A job row, command bar, stage strip, pending
   timing panel, or historical-result label. Freeze IDs, time, dimensions, and
   animation phase; snapshot the smallest region expressing the contract.
3. **A few whole-screen expectations.** Compact/wide layouts, failure/disconnection,
   help overlay, and small-terminal recovery. Prefer representative boundary cases
   over every state × theme × viewport combination.
4. **PTY and human checks.** Keep resize/recovery and installed-client coverage;
   inspect actual contrast, focus, density, and key behavior in the intended SSH/tmux
   environment. Text frames do not establish that a color scheme is readable.

The current [PTY script](../scripts/test-terminal-resize.py) checks emitted bytes,
text fragments, resizing, and interaction. It is not a screenshot comparison or
complete terminal emulator. Styled output may split text with escape sequences,
so migrate brittle raw-byte phrase checks to appropriate component assertions or
a decoded screen check while preserving integration coverage.

For each intentional visual change, inspect the diff before `dune promote`.
An unrelated new feature should not alter another component's baseline unless its
visible contract actually changed. Avoid assertions that merely duplicate the
implementation, and keep behavioral verdicts explicit even when a frame is shown.

## 7. Phased implementation plan

P0–P4 start **Not started**; P5 is **Deferred**. Checkboxes describe implementation
and acceptance, not claims that the audit has completed the work.

### P0 — Establish a bounded visual target and test seam

**Placement:** early D1; small enabling slice, not a release-wide prerequisite.

- [x] Capture the current UI with representative jobs, long names, hierarchy, and
  output at 80×24 and 120×40; use deterministic fixtures for repeatable comparisons.
  Done 2026-09-20: three deterministic fixtures in `terminal/baseline_fixture.ml` are
  rendered by the production `render` through the `--capture-baseline` development flag
  into `test/baselines/terminal/`, as a stripped character grid and as the emitted escape
  sequences. See [terminal_baseline_captures.md](terminal_baseline_captures.md) for the
  scenarios, the regeneration command, what the captures do and do not preserve, and the
  eleven layout problems they record. The captures show no colour or bold anywhere in
  the normal UI, so they document layout only, not appearance.
- [x] Define the compact/wide cell budgets and essential persistent summaries.
  Done 2026-09-20: [terminal_layout_spec.md](terminal_layout_spec.md) specifies the row
  and column allocation for every band at exactly 80×24 and 120×40, with ten ASCII
  wireframes whose dimensions were checked by counting display cells. It fixes the
  always-visible identity/flow/timing/check/design bands, the main-region panel pairs
  used for drilldown, the overlay and reader rules, the overflow and selection-visibility
  rules, the mode thresholds and derived dimensions between and beyond the two reference
  sizes, a minimum of 70×18 derived from the design rather than inherited from 68×20,
  and fifteen acceptance criteria (L1–L15). No requirement is weakened; section 13 of
  that document lists every compaction and the three deliberate divergences. The
  renderer is unchanged and the baseline captures are not regenerated.
- [ ] Separate a testable rendering entry point from executable startup, accepting
  explicit display data, UI state, dimensions, and time.
- [ ] Validate the compatible component/test dependency set. Reuse installed base
  primitives for the first slice if additional components need more integration work.
- [ ] Add a small baseline of meaningful layout and interaction checks.

**Exit:** a reproducible way to render/review the screen without starting a real
flow, plus a concrete compact/wide target. Existing installed behavior still works.

### P1 — Ship the first visible facelift

**Depends on:** P0. **Placement:** alongside D1, before adding more dashboard text.

- [ ] Add theme roles and shared panel, heading, badge, key-hint, and selected-row
  helpers; fix terminal-cell measurement in the migrated rendering paths.
- [ ] Replace the giant controls string with a top command bar and complete help
  overlay backed by shared command definitions.
- [ ] Condense project/target/configuration identity. Move full IDs, roots, endpoint,
  environment details, and workspace inventory into navigable details.
- [ ] Render action-first job rows with explicit status and compact display IDs;
  keep the complete identity available without assuming IDs are numeric suffixes.
- [ ] Separate connection health from command feedback; define when feedback expires
  or is dismissed so normal polling cannot erase it.
- [ ] Check compact/wide appearance in the actual terminal and add focused visual
  expectations for the new shared widgets.

**Exit:** the existing workflow is visibly clearer, help and quit never disappear,
and status/selection can be recognized without reading every line. This is the
first shippable result; do not hold it for a complete state refactor.

### P2 — Reactive state, focus, and usable viewports

**Depends on:** P1; state extraction can proceed in small pieces during P1.
**Placement:** alongside D1/D2 as browsing and live updates require it.

- [ ] Publish async results to observable state and use typed UI actions, preserving
  the current reducers, daemon-instance checks, and update ordering rules.
- [ ] Replace index-based job selection with stable identity and reconcile removal
  deterministically. Keep selections visible when new jobs arrive.
- [ ] Add focused event routing and common list/tree/detail navigation; capture
  overlay input before global actions.
- [ ] Provide job/artifact/detail viewports and bounded log scrollback with an
  explicit follow indicator. Show retention/retrieval limits honestly; the current
  500-record client cache and 1 MiB artifact fetch limit are not unlimited history.
- [ ] Make scroll/layout reconciliation explicit and rendering free of mutation.
- [ ] Retire the blanket render tick after data changes drive recomputation. Keep
  clocks only for the displays that genuinely depend on time.
- [ ] Preserve hierarchy selection/expansion, historical identity, and artifact
  inspection while migrating them to the common presentation/navigation patterns.

**Exit:** arrivals do not change the selected job unexpectedly; long output is
usable; focus is obvious; reconnect and view switching preserve valid local state.
Behavioral tests cover these transitions independently of whole-screen decoration.

### P3 — Apply the visual system to real ASIC evidence

**Depends on:** enough of P1/P2 for the affected panels, D1's result/identity
contract, and D2's live evidence for live portions. **Placement:** the UI portion
of D3, not an additional backend milestone.

- [ ] Compose persistent identity, flow strip, timing, result/check, compact design,
  and execution/output regions using the established widgets and cell budgets.
- [ ] First display an explicitly selected stored result from D1; then connect live
  stage/progress updates as D2 supplies them. Development fixtures are not evidence
  that project telemetry exists.
- [ ] Wrap/compact all declared stage outcomes at narrow widths. Keep setup and
  hold summaries visible and expose corner/stage/provenance detail on inspection.
- [ ] Render pending, historical, unknown, unconstrained, unsupported, failed, and
  cancelled states distinctly. Keep verdicts and artifact existence separate.
- [ ] Let a selected stage/check open its supporting output/report, preserving
  run identity and access to the first actionable failure where evidence permits.
- [ ] Verify displayed measurements/verdicts against actual project-owned records.

**Exit:** one screen answers which run is selected, what is executing, what timing
is known, and which checks passed/failed. A new run cannot inherit a misleading
green summary from an older one. Complete D3's existing demo with real evidence.

### P4 — Daily-use acceptance and cleanup

**Depends on:** P3 and the corresponding D1–D3 integration. **Placement:** D4.

- [ ] Exercise the installed client in the intended server-side SSH/tmux workflow:
  resize, focus, navigation, help, failure, cancellation, disconnect, and reattach.
- [ ] Review 80×24 and wide layouts, long labels, substantial logs, no-output jobs,
  stale observation, pending timing, and reopened archived results.
- [ ] Check palette contrast and non-color state cues. Confirm that chrome remains
  legible whether the user's tmux status bar is above or below the pane.
- [ ] Update the PTY checks to the new UI contracts; review representative component
  and whole-screen expectation diffs.
- [ ] Remove superseded rendering/state bridges after their replacements are
  validated; document the resulting module ownership and actual keybindings.
- [ ] Run relevant targeted tests while developing, then the repository's required
  format/lint/test/build checks serially through `scripts/with-switch.sh`. Run the
  affected installed-client/fixture checks and record actual results in development.md.

**Exit:** use the dashboard for real iterations and close D4 against its existing
release gate. Record concrete remaining friction rather than expanding acceptance
into every possible terminal or deferred workstation-native deployment.

### P5 — Optional improvements driven by use

**Status:** Deferred; not a D4 release gate.

- [ ] Search/filter large job lists and output when scroll/paging proves insufficient.
- [ ] Add light/alternate themes or user palette overrides if requested.
- [ ] Add mouse selection, modest resource charts, or weighted hierarchy views when
  the real workflow and available data justify them.
- [ ] Introduce further reusable components only after multiple real callers need them.

Keep the working ASIC dashboard as the measure of success. Attractive charts,
general-purpose customization, and deeper hierarchy analytics should earn their
place by solving an observed problem, not delay the first useful release.
