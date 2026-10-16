# Frontend composition and palette delivery

Activated 2026-10-16 after the completed FS2 milestone and aesthetics merge.
This is frontend/F12 follow-on work, not a reopening of FS2. It is the shared
implementation plan for the coordinator and up to three implementation agents.

## Accepted direction

1. Bounded command-palette overlay preserving the underlying workspace or explorer;
   ranked fuzzy matching with highlighted matched characters; Tab/Shift-Tab and
   arrows select results without moving underlying focus. Esc restores the source
   view; captured commands retain their existing execution/revalidation semantics.
2. Composable tile presentation: title, binding badge, run-reference row, freshness,
   hints, frame and padding. Follow is the normal binding and hidden by default;
   pins remain visible by default. Project-scoped badges are likewise quiet by
   default. Settings alter presentation only, not identity, availability or binding.
3. Semantic status styling driven by typed freshness/outcomes, not string searches.
   Validated means validated evidence, not a passing implementation or check.
4. One discoverable OCaml workspace definition per Overview, Timing and Testing,
   composed from common reusable tiles and responsive layout primitives. Stable
   preset identity, not display name, selects layout. Existing saved customizations
   are not silently reset. Extra/duplicate/custom tiles remain usable.
5. Overview has a wide shallow upper-main run selector (default four visible runs),
   compact Session, vertical checklist, and wider stacked main evidence panels.
   Workspace navigation is a configurable tile; title/project badge/hints are quiet
   by default. Narrow surfaces gracefully stack or use focused-tile fallback.
6. Synthetic setup consumes the same preset definitions as normal Workbench.
   Synthetic stage labels become production-like Synthesis/Floorplan/Placement/CTS/
   Routing/Signoff; keep synthetic provenance in session/run/evidence. Do not strip
   arbitrary provider text in generic renderers.
7. Multiple instances of Session/navigation share existing daemon registry/project
   facts while retaining tile-local interaction. No new provider per tile and no
   new global shared selection. Data/query caches remain keyed by semantic identity;
   width/theme/scroll-specific rendered frames need not be shared.

## Current source and reference

- Defaults: `terminal/workspace_host.ml`; Overview fit: `terminal/overview_layout.ml`;
  generic placement/rendering/palette: `terminal/host_view.ml`.
- Saved workspace registry: daemon `--state-dir/workspace-<digest>.sexp`, keyed by
  canonical project/environment. Preserve legacy snapshot loading.
- Current palette search is substring filtering, not fuzzy ranking.
- Ches reference (read-only): `/home/wayne/devel/ches/palette/fuzzy.ml{,i}`,
  `screen/palette_tile.ml`, `screen/picker_text.ml`, `screen/floating.ml{,i}`.
  Prefer adapting pure helpers with attribution over coupling to Ches editor/runtime.
- Real modules are already shared in daemon services; Session and Workspaces are
  existing tile kinds `live-status` and `workspace-tabs`.

## Ownership and coordination

No staging, commits, merges, pushes or authorship-related Git changes. Preserve
user demo state/configuration. Source changes are limited to this checkout; Ches is
read-only. Test artifacts/state go under `/tmp/opencode` in private directories.
No physical/ASIC flow is required.

Build budget: agents may use **2 jobs each**, commands serial within each agent and
separate absolute build dirs `/tmp/opencode/frontend-{palette,presentation,layout}`.
Coordinator runs no build during agent builds. Final integration checks are serial
at `-j 2`; do not raise concurrency merely because the maximum permitted is 20.

### Agent A — palette and integration owner

Own `terminal/host_view.ml`, `terminal/workspace_host.ml`, `terminal/main.ml`,
`terminal/dune`, and new palette search/view modules. Implement palette end to end
first. After B/C publish their stable helper APIs, integrate presentation/presets
into these shared files. Only this agent changes those shared files until handoff.
Preserve forms, explicit commands, FS1 inspectors, FS2 simulation input and exports.

### Agent B — presentation helper owner

Own new `terminal/tile_presentation.ml{,i}` and `terminal/evidence_style.ml{,i}`,
and existing `terminal/synthesis_view.ml{,i}`, `terminal/terminal_result_view.ml`
and `terminal/overview_tiles.ml` as needed. Build pure policy/typed semantic span
helpers, meaningful tests, and integration instructions for A. Do not edit A's
shared files. In a subsequent pass own new frontend acceptance scripts as needed.

Presentation policy must support inherited overrides, Exceptions/Always/Hidden
binding badge modes, header/title, run reference, freshness, hints, frame, padding
and run-selector visible rows. Resolve app -> workspace -> tile options. Prefer
typed sparse overrides; do not overload existing binding or layout identity.
Runtime palette controls should expose these options, with reset-to-inherit.
Persistence of deliberately local appearance is not an implicit daemon semantic
mutation; explicitly document the implemented lifetime.

### Agent C — workspace definitions and synthetic owner

Own `terminal/workspaces/` as a standalone small library, protocol workspace preset
identity/mutations/backward-compatible loading and tests, `terminal/overview_layout.ml`
as a compatibility shim if useful, and `scripts/synthetic-flow-demo.py`, synthetic
provider/tests. Do not edit A's shared files. Publish an API and concrete integration
instructions, including any new record fields call sites A must fill.

Workspace library should provide per-workspace OCaml definitions, tile membership,
requested geometry/default presentation fields, layout tree/placement, stable
Overview/Timing/Testing IDs, and a machine-readable preset export for the Python
demo. A adds the export CLI to main. Keep presentation defaults in neutral fields
(optional booleans, badge string/variant, row count) if importing B's terminal-local
module would create a dependency cycle; A maps them into the presentation policy.

Use explicit additive Apply preset and explicit Reset arrangement behavior. Reset
must preserve run contexts/pins and user-owned extras (e.g. restore preset geometry
without deleting unrelated tiles). Old snapshots without preset metadata must load;
one-time deterministic legacy inference is acceptable, subsequent rename must not
change the chosen preset. New fields must have compatible sexp defaults; any wire
change requires rebuilding daemon/client together. Tests must cover both migration
and rename/custom tile retention.

## Acceptance

- Fuzzy ranking/positions include multiword, aliases, Unicode boundaries and empty
  queries; matched highlighting and selected-row styling remain distinct.
- Overlay is bounded at normal sizes, keeps actual underlying explorer visible,
  handles narrow terminals, clips by display cells and keeps selected results visible.
- Actual PTY demonstrates Tab/Shift-Tab choice between similar commands, Esc return,
  command execution against captured target, and forms retained.
- Following Synthesis is quiet; pinned Synthesis has exact visible identity by default.
  Toggles alter chrome only; independent tiles and source evidence remain unchanged.
- Typed validated/failure/pending/stale states are styled correctly, including
  validated evidence of a failing run. No keyword-colored human logs.
- Overview/Timing/Testing definitions are easy to find and compose; synthetic seed
  consumes the same definitions; legacy snapshots, rename, added tiles, duplicates,
  pin/follow, explicit apply/reset and narrow/zoom behavior are exercised.
- Real synthetic HTTP/PTY, FS2 HTTP/PTY and Ctrl-C regression pass on integrated code.
  Capture representative 80x24/120x40/large layouts. Keep all tests PDK-free.

## Delivery status

**Implemented and verified.** Final full format/lint, test suite and build passed
serially at `-j 2` in the normal `_build`. Final actual frontend HTTP/PTY acceptance
passed 41 checks at `/tmp/opencode/frontend-composition-359220233ca9/`; synthetic
flow, FS2 Cyclesim and all five interrupt modes also passed after density review.
See [controls, source map, evidence and limits](frontend_composition.md).

The handoffs below are chronological implementation notes. Their intermediate
build/format/precedence blockers are superseded by the final verification above.
No Git staging, commits, pushes or real ASIC flows were performed. Existing user
demo state/configuration was left untouched; acceptance used private state.

### Agent A first-pass handoff — palette (2026-10-16)

- Implemented `terminal/palette_search.ml`: pure ranked token-AND subsequence
  matching adapted with attribution from Ches, boundary/consecutive bonuses, gap
  penalties, stable ties, weighted title/alias/ID fields, codepoint-boundary match
  offsets. ASCII case folds; non-ASCII scalars compare exactly (no Unicode case
  normalization). No editor/runtime dependency.
- Implemented `terminal/palette_view.ml`: centered maximum 88x20 overlay with
  per-axis margins, cell-based clipping/query tail, matched spans, alias/ID match
  context that stays discoverable beside a clipped title. Selected row backdrop
  and marker differ from warm underlined match characters.
- `workspace_host.ml` uses ranked results, retains selected command identity across
  query edits where still available, handles Unicode text/backspace, and captures
  Tab/Shift-Tab plus Up/Down inside the palette. Navigation clamps at endpoints.
  Existing captured commands, availability checks, forms, paste and interrupt
  handlers remain authoritative.
- `host_view.ml` now constructs the actual source background before adding the
  palette. FS1 inspector stays full-viewport beneath the overlay; Esc restores its
  exact frame. Forms retain their existing submission/help logic inside the overlay.
  Tiny surfaces reclaim padding/header/footer cells; normal results scroll to the
  selected command.
- `terminal/dune` publishes `palette_search`, `palette_view`, `tile_presentation`
  and `evidence_style`; dependency on `hardcaml_workbench_workspaces` is present
  because C's `overview_layout` compatibility shim already imports it. No B/C
  policy/preset APIs have been guessed or integrated into host behavior yet.
- Verification: `opam exec -- dune runtest --build-dir
  /tmp/opencode/frontend-palette -j 2 terminal` and `opam exec -- dune build
  --build-dir /tmp/opencode/frontend-palette -j 2 terminal/main.exe` pass. New tests
  cover fuzzy ranking/ties/Unicode offsets, aliases/highlight spans, overlay bounds,
  background preservation, actual FS1 source and Esc restoration, similar-command
  Tab/arrows, stable command selection, captured execution/unavailability, selected
  result scrolling and tiny/cell-clipped rendering. No physical EDA or stale
  expectation-heavy acceptance scripts run.
- Resume hooks: `H.ranked_matches` supplies command plus matched-field positions;
  `H.matches` remains command-only compatibility API. `render_palette` composes over
  any source frame; `Palette_view.bounds` is reusable by acceptance captures.
  Presentation/preset host integration and actual HTTP/PTY acceptance remain for
  coordinator handoff/resume. `terminal/main.ml` is unchanged in this first pass.

### C API handoff (implementation available)

- Add `hardcaml_workbench_workspaces` to `terminal/dune` libraries. It is an
  independently buildable library in `terminal/workspaces/`, wrapped under
  `Hardcaml_workbench_workspaces` (abbreviated `P` below).
- `Workspace.Arrangement.t` adds `preset : string option [@sexp.default None]`.
  Fill record literals with `preset = None` for custom workspaces, or `Some
  "overview"`, `Some "timing"`, `Some "testing"`. Record updates need no change.
  Initial Overview/Timing already carry IDs. Legacy sexp parsing infers from exact
  Overview/Timing/Testing names only when the field is absent, writes it on the
  next persistence, and never infers again from an explicit `None` or on rename.
  Rebuild daemon/client together (bin_io record and mutation variants changed).
- `P.Presets.all : P.Definition.t list`; `find : string -> t option`;
  `for_arrangement : Workspace.Arrangement.t -> t option` uses ONLY preset ID.
  Per-workspace entry points: `P.Overview.definition`, `P.Timing.definition`,
  `P.Testing.definition`. `Definition.t = { id : string; name : string;
  tiles : Common.tile list; layout : Common.tree }`.
- `P.Definition.apply definition ~workspace` returns ONE
  `Workspace.Mutation.Apply_preset { workspace; preset : string;
  tiles : (string * Workspace.Geometry.t) list }`. It adds missing kinds, claiming
  occurrences one-to-one, sets stable metadata, and preserves existing geometry,
  order, hidden state, pins, zoom, context and extras. `Definition.reset` returns
  `Reset_arrangement` with the same fields: also restores claimed preset tile
  geometry; it still preserves pins/context/hidden state/zoom/extras. Expose both
  explicit actions. Initialize revision-zero defaults through `apply`; do not
  automatically reset saved arrangements. Create Testing, then apply its definition.
- `P.Layout.compute definition ~width ~height ~kinds : Grid of Geometry.t list |
  Compact` preserves input order/cardinality including arbitrary/duplicate extras.
  Pass visible kinds only; host retains existing focused-tile fallback on Compact
  and existing zoom short-circuit. For custom/unknown preset use existing preferred
  geometry behavior (do not infer by display name). `Overview_layout.compute` is
  now only an Overview compatibility shim with the same old signature/result.
- `Common.tile = { kind : string; geometry : Workspace.Geometry.t;
  presentation : Common.presentation }`. `Definition.specs` exports geometry pairs;
  `Definition.presentation definition ~kind` returns an optional sparse default.
  Presentation record fields: `title`, `run_reference`, `freshness`, `hints`,
  `frame : bool option`; `binding_badge : string option` (currently `"hidden"` only);
  `padding`, `visible_rows : int option`. Map these to B's policy before local
  overrides. Navigation disables title/badge/hints; selector requests four rows.
- `P.Presets.export_sexp () : Sexp.t` exports the full definitions. Standalone
  helper `terminal/workspaces/export_presets.exe` prints it; A may additionally
  expose it from main. Python seeder accepts `--preset-export /path/to/helper`
  (or `WORKBENCH_PRESET_EXPORT`), uses one centralized export, and sends the same
  Apply_preset mutation rather than maintaining Python layouts.

#### C verification and integration limits

Resume review: no OCaml API changes. Owned OCaml/Dune files now match switch
formatter `3aa293b`; `@terminal/workspaces/fmt`, `@protocol/fmt` and explicit
`ocamlformat --check terminal/overview_layout.ml` pass. Added regression coverage
for unknown preset identity across rename, malformed option encoding/empty IDs,
duplicate spec occurrence matching after reorder, hidden primary preservation,
nonempty selected context preservation, invalid reset rejection, and every sparse
Overview membership subset at resize thresholds (1,280 viewport/subset cases).
Synthetic visual-only checks now also reject unsolicited `flow plan` calls;
explicit checklist `r` must plan exactly once. Seeder selects Overview by stable
preset metadata and preserves an explicit exporter path in printed commands.

Integrated build attempt on resume was blocked in A-owned code:
`terminal/workspace_host.ml:569`, `"hidden" -> Some Hidden`,
`Error: Unbound constructor "Hidden"`. Command:
`scripts/with-switch.sh dune build --build-dir /tmp/opencode/frontend-layout -j 2 daemon/main.exe terminal/main.exe terminal/workspaces/export_presets.exe`.
C did not edit the shared file; PTY awaits that integration fix.

Additional integration review for A: current `Workspace_host.policy` applies
`t.presentation` before preset `defaults` (`let app = T.apply app defaults`). That
would force preset selector rows back to four after an explicit app-level choice,
and similarly prevent app-level navigation defaults from overriding the preset.
Apply preset/navigation defaults below explicit app/workspace/tile overrides.
C's library exposes sparse defaults only; it has no runtime row override or data
dimension mutation. Latest resumed provider/export smoke evidence is
`/tmp/opencode/synthetic-flow-w5_kce7s` (passed).

- Passed serially at `-j 2`, build directory `/tmp/opencode/frontend-layout`:
  `scripts/with-switch.sh dune build --build-dir /tmp/opencode/frontend-layout -j 2 protocol/hardcaml_workbench_protocol.cma terminal/workspaces/export_presets.exe`
  and `scripts/with-switch.sh dune runtest --build-dir /tmp/opencode/frontend-layout -j 2 protocol terminal/workspaces`.
- Passed `python3 scripts/test-synthetic-flow.py --smoke --preset-export /tmp/opencode/frontend-layout/default/terminal/workspaces/export_presets.exe`.
  Latest evidence: `/tmp/opencode/synthetic-flow-zhavvxst`. This exercises six-stage
  producer labels/provenance, bounded provider playback/cancellation, retained FS1
  evidence, and the actual OCaml-export-to-seeder path (including rename/custom
  identity checks). Protocol tests cover legacy migration, explicit custom None,
  rename stability, additive/idempotent apply, reset, pins/context/zoom/hidden and
  duplicate/custom tile retention. Layout tests cover viewport cell bounds,
  gutters, cardinality/order, shuffled/duplicate kinds and focused fallback.
- Defaults deliberately keep three stacked main panels so the intended shape fits
  the actual `120x40` viewport after header/footer space: Overview = navigation,
  Session, selector, checklist, synthesis, timing, checks; Timing = navigation,
  Session, selector, checklist, timing, CTS, routing; Testing = navigation, Session,
  selector, project-tests (left), simulation, execution, logs (main). Existing
  additional kinds remain extras. Navigation is a quiet three-row band; Session
  stays seven rows; selector is seven rows with four requested visible runs.
- Full daemon/client/PTY acceptance is deferred to A's integration. The harness
  now derives membership from the export and updates producer-label/full-panel
  assertions, but integrated PTY/palette/presentation assertions have not been run.
  A should run HTTP then PTY and representative `80x24`/`120x40`/large captures,
  verifying title/hint policy and four visible selector rows with B's renderer.

### Agent B helper handoff

- New terminal-local modules: `tile_presentation.ml{,i}` and
  `evidence_style.ml{,i}`. Agent A must add `tile_presentation` and `evidence_style`
  to the existing terminal library modules before building. B did not edit dune.
- `Tile_presentation.resolve ~app ~workspace ~tile : t` takes three typed sparse
  `overrides` records. Start with `inherit_`; update individual option fields.
  Reset a setting to `None` to inherit again. Resolution order is defaults, app,
  workspace, tile. `navigation` is a sparse header/title/hints-off default: use
  `apply (apply defaults navigation) app |> ...` for navigation so explicit app,
  workspace and tile choices can override it. Other tiles use `resolve` directly.
- Resolved fields: `header`, `title`, `badge` (`Exceptions | Always | Hidden`),
  `run_reference`, `freshness`, `hints`, `frame`, `padding`, `run_selector_rows`.
  Default rows = 4; rows clamp to >=1 and padding to >=0. Defaults show title,
  header, freshness, hints and frame; hide the extra run-reference row.
- `show_title : t -> bool` honors header/title together. `show_badge : t ->
  Binding.t -> bool` accepts `Follow | Pinned | Project`. Exceptions hides Follow
  and Project, shows Pinned. Badge visibility is deliberately independent of
  header/title: preserve visible pin identity in a separate row if header is off.
  Host supplies exact identity from the actual binding, including unavailable pins;
  policy never resolves bindings or changes availability. Header hiding must not
  suppress that independent badge. Use an explicit run-reference row only when set.
- Helpers hold no state and persist nothing. Runtime overrides should live in A's
  local presentation state, with the implemented lifetime documented there; these
  controls do not require daemon mutations or a Session/navigation backend process.
- Stable semantic shape: `Evidence_style.span = { text : string; role : Role.t }`,
  `row = span list`. Roles are `Plain | Muted | Validated | Passed | Failed |
  Pending | Running | Stale`. Map Validated independently from Passed (e.g. cyan
  evidence freshness versus green outcome), Failed to failure, Pending to warning,
  Running to running/accent, Stale to warning/muted, Plain to foreground.
- `normalize : Field.t -> string -> Status.t` uses exact field-specific protocol
  vocabularies (`Operation | Physical_completion | Verdict | Summary_completion`),
  not human-log substring matching. `freshness_role` and `stage_role` take protocol
  variants directly. `fact ~label field value`, `freshness value`, `check check`
  construct spans. Reasons, labels, metric text and provider payloads remain plain.
- `wrap ~width row`, `clip ~width row`, `page ~width ~height ~offset rows` preserve
  typed roles with UTF-8 terminal-cell geometry. Adjacent equal roles are coalesced
  after wrapping. `render ~attrs rows` returns a Bonsai term view, where attrs maps
  `Role.t -> Bonsai_term.Attr.t list`. Use these rather than keyword classification.
- `Synthesis_view.semantic_rows` has the same arguments as `rows`, returning
  `Evidence_style.row list`. It styles Summary freshness and Metrics freshness/
  acceptance; Cells, Details and full raw Evidence stay plain. Plain-text rows,
  scroll bounds and existing source/acceptance expectations remain intact.
- `Terminal_result_view.semantic_rows ?fallback ?request_context state ~run
  ~summary ~kind ~width ~height` likewise returns typed rows with exact-run guarding,
  freshness, operation/completion/acceptance and check roles. `semantic_lines
  terminal ~kind ~detail` provides unwrapped typed content. Existing `rows` and
  `lines` now project their text. Host can render both typed APIs using the same
  role mapping; selected tile styling remains a separate host concern.
- Existing `Overview_tiles.Role` is unchanged. A should use the typed freshness
  helper for its freshness-specific rendering instead of equating validated with
  successful synthesis. Existing aggregate/stage distinctions and tests remain.
- Inline tests added: three policy tests (inherit/reset; badge modes/headerless pins;
  dimensions), two evidence helper tests (validated failure/unknown vocabulary;
  Unicode wrapping/roles/paging), one synthesis parity+validated-failure test, one
  terminal checks/reasons/evidence/width test. Run, serially, after module integration:
  `dune runtest terminal --build-dir /tmp/opencode/frontend-presentation -j 2`.
  A subsequently added the modules. B compiled via that command (serial, `-j 2`)
  and then ran the built inline runner with `-only-test terminal/tile_presentation.ml
  -only-test terminal/evidence_style.ml -only-test terminal/synthesis_view.ml
  -only-test terminal/terminal_result_view.ml -only-test terminal/overview_tiles.ml
  -show-counts`: **31 tests and 2 test modules passed**. The broader terminal run
  failed only on the in-flight palette assertion at `terminal/palette_search.ml:121`
  (subsequence-ranking test), which belongs to A. B ran ocamlformat and
  `git diff --check`. No physical flow or native acceptance test has been run in
   this helper phase.

### Agent A integration handoff — active host policy and presets

- Actual host now resolves `Tile_presentation` defaults, quiet navigation defaults,
  compiled definition tile defaults, explicit client app overrides, explicit client
  workspace-ID overrides, then tile-ID overrides. Compiled presets are defaults:
  explicit global configuration wins (including selector rows over preset four).
  App/workspace values are typed OCaml config
  (`H.t.presentation`, `workspace_presentation`); compiled preset defaults come from
  `Definition.presentation`. Runtime palette changes are tile-local, survive polling
  and workspace switches, and expire at client restart/session replacement. They do
  not mutate registry bindings, evidence, contexts or remembered appearance.
- Controls (Space c c, fuzzy title search): `Toggle focused tile header/title/run
  reference/freshness/hints/frame/padding`; `Binding badge: Exceptions (pins only)`,
  `Binding badge: Always`, `Binding badge: Hidden`; `Run selector: More visible rows
  (+1)` / `Fewer visible rows (-1)`; `Reset presentation overrides (inherit)`.
  IDs: `tile.headers`, `tile.presentation.{title,run-reference,freshness,hints,frame,
  padding,badge.exceptions,badge.always,badge.hidden,rows.more,rows.fewer,reset}`.
  Actions capture the exact tile ID and sparse override, retaining existing target
  revalidation. Header/title hiding never implicitly hides a pinned badge.
- Follow/project badges are quiet by default; pins use full backend/run ID, including
  headerless tiles. Navigation has no title/hints/frame/padding by default. Selector
  defaults to four actual visible runs, adjustable per tile; renderer and input use
  the same cap/body geometry and keep the cursor in view.
- `host_view` consumes synthesis/terminal semantic APIs and typed roles. Validated
  is accent/evidence-colored separately from green Passed. Freshness/run chrome is
  removed at known typed row locations before paging; arbitrary logs, reports and
  full raw evidence retain their source text and identities. Terminal filtered pages
  and synthesis Metrics share policy-aware scrolling/bounds. Metrics scrolling is
  fenced to exact run/digest; ordinary source Evidence retains existing state pager.
- Layout now dispatches only through `Arrangement.preset`, `Presets.for_arrangement`
  and `Layout.compute`. Custom/unknown presets retain requested-geometry behavior.
  Revision-zero initialization and Create Testing apply the OCaml definitions;
  bootstrap prototype geometry is normalized from those definitions only at
  revision zero. Testing includes FS2 simulation. Compatibility default-list helpers project the
  definitions rather than maintaining another list.
- Explicit controls: `Apply preset: Overview/Timing/Testing (add missing tiles)` and
  `Reset arrangement: Overview/Timing/Testing (preserve extras and pins)` work in
  custom workspaces too; `Reset arrangement (current preset; preserve extras and
  pins)` uses the stable current ID. IDs `workspace.apply-preset.{overview,timing,
  testing}`, `workspace.reset-arrangement.{overview,timing,testing}` and
  `workspace.reset-arrangement`. Existing `workspace.default-layout` applies the
  current preset additively; custom workspaces are directed to explicit choices.
- Integrated terminal tests and terminal/daemon executable builds have passed at
  `-j 2` in `/tmp/opencode/frontend-palette`; final verification is recorded in A's
  response. New host tests exercise real preset geometry/rename stability, four/six
  selector rows and cursor visibility, quiet defaults/headerless pins/explicit hide,
  sparse inheritance and exact tile actions, typed validated failing evidence, and
  preserved provider prose/raw evidence when chrome is hidden. Native acceptance
  scripts remain B's ownership; A has not run them concurrently.
- Final correctness/format pass: removed the duplicate legacy `local.headers` flag;
  header toggles, reset, legacy action dispatch and owned fixtures now use only
  `local.presentation.header`. Added policy regressions for preset four -> explicit
  app seven -> workspace six -> tile five -> reset inheriting six, including an
  explicit tile header overriding app hidden-header policy; actual selector rendering
  also asserts seven global rows. Form overlay query-tail rows now fit the available
  body on short terminals, so pagination cannot clip away the last input line;
  the form footer describes input acceptance instead of command result counts.
  Added a 40x4/80x24 form-tail and unchanged captured-form/Esc regression. Reviewed
  full explorer-background rendering; it still renders the full actual inspector
  before the overlay, with existing exact Esc/background tests intact.
- Formatting: `opam exec --switch=5.2.0+ox -- ocamlformat --inplace` applied to
  `terminal/{palette_search,palette_view,host_view,workspace_host,main}.ml` using
  switch formatter version `3aa293b`. Individual `--check` commands passed for all
  five files. No builds or tests run during this final pass, per parent instruction;
  new regressions await the parent's serial full suite.
- Density follow-up: base padding now derives from remembered appearance density
  (Compact 0 / Comfortable 1), before kind/preset defaults and explicit app,
  workspace and tile overrides. Navigation's kind default remains zero; existing
  `body_geometry` bounds clamp padding on small surfaces. A renderer test verifies
  changed geometry/evidence position, identical explicit-padding rendering across
  density changes, app/workspace overrides, unpadded navigation, tiny bounds, and
  untouched registry/no provider queries. The warm synthesis narrow-table fixture
  now uses 32x10 rather than 32x8 where it requires a cell row after all headings,
  retaining its exact Follow/pin/count/identity assertions. Exact-switch terminal
  `dune runtest --build-dir /tmp/opencode/frontend-palette -j 2 terminal` passed.
  B's native acceptance padding assertion currently assumes an initial zero and a
  +1 movement; it needs a Compact baseline or density-aware direction. A did not
  modify that script or rerun native acceptance during this follow-up.

### Agent B native acceptance handoff (2026-10-16)

- Added `scripts/test-frontend-composition.py`: existing-binary-only, stdlib real
  HTTP/PTY harness. Required options are `--daemon`, `--client`, `--preset-export`;
  optional `--evidence` must name a NEW directory under `/tmp/opencode`.
  Default wall-clock budget is 240 seconds. `--palette-only` is diagnostic only;
  the complete default run passed. The harness creates five genuine synthetic
  observations, seeds through the OCaml exporter/normal HTTP, uses normal terminal
  input, records binary hashes, and closes only its own daemon/client processes.
- Current-screen ANSI reconstruction records cell foreground/background, underline,
  bold, Unicode cell widths, text snapshots, full ANSI transcripts and SVG terminal
  screenshots. These are actual captured terminal frames, not generated UI mocks.
  HTTP/key logs and final `result.json` are retained on success/failure.
- **Full acceptance passed: 37 recorded checks**, plus screen assertions, evidence:
  `/tmp/opencode/frontend-composition-72962f2c1f1c/result.json`.
  This includes exact noncontiguous `ap/col` match underlines (not whole-row styling),
  bounded overlay/background cell+attribute equality outside its rectangle, real
  fuzzy query/arrow/Tab/Shift-Tab selection, Enter Color Selective execution and active
  confirmation, exact Esc workspace/focus and FS1 inspector restoration, quiet default
  Follow/project/navigation chrome, exact/headerless pinned identity, per-tile
  header/title/badge/run-reference/freshness/hints/frame/padding/reset controls
  (including actual frame removal and one-cell padding movement), independent synthesis modes/evidence,
  distinct Validated/pending and Validated/failed ANSI foregrounds, and the actual
  palette Apply preset/Reset arrangement commands after HTTP rename. HTTP verifies
  exported reset geometry, unchanged extra tile and retained exact pin identity.
  Five registered runs verify four default selector rows, +1 exposing the fifth,
  and reset-to-inherit restoring four without semantic mutation.
- Screenshots are `overview-{80x24,120x40,180x55}.svg` and
  `overlay-{80x24,120x40,180x55}.svg` in that directory, with matching `.txt`,
  `.ansi`, `.cells.json`. Additional named captures cover inspector, controls,
  headerless pin, pending/failed colors and preset reset.
- Adapted only the palette-query acknowledgement in `scripts/test-fs2-native.py`
  for bounded geometry: require action prefix plus exact query identifying suffix
  instead of the entire >88-cell title on one line. Existing exact-attempt, edited
  inputs, real assertion failure, viewer byte hash and targeted-rerun behavior
  assertions remain intact. No change to `test-terminal-interrupt.py` was needed.
- Regressions passed against the same integrated candidate:
  - FS2 native real HTTP + PTY (including actual Hardcaml Cyclesim, forms, raw export,
    viewer, targeted rerun, independent tiles): `/tmp/opencode/fs2-native-4600bt3s`.
  - All five raw Ctrl-C cases, exit 0, terminal flags restored, daemon alive:
    `/tmp/opencode/workbench-terminal-interrupt-xa2_b0ij/results.json`.
  - Existing synthetic CLI/HTTP/PTY stages/launch/cancellation/FS1 suite:
    `/tmp/opencode/synthetic-flow-m7tjqdda`.
- Serial candidate build (2 jobs): `scripts/with-switch.sh dune build --build-dir
  /tmp/opencode/frontend-presentation -j 2 daemon/main.exe terminal/main.exe
  terminal/workspaces/export_presets.exe`. Counter built separately, serially, from
  `examples/fs2_cyclesim` with `scripts/with-switch.sh dune build --root . --build-dir
  /tmp/opencode/frontend-presentation/cyclesim -j 2 counter.exe` (invoke with-switch
  by its absolute repository path from that directory).
- Exact reruns, with `B=/tmp/opencode/frontend-presentation/default`:
  ```sh
  python3 scripts/test-frontend-composition.py --daemon "$B/daemon/main.exe" --client "$B/terminal/main.exe" --preset-export "$B/terminal/workspaces/export_presets.exe"
  python3 scripts/test-fs2-native.py --daemon "$B/daemon/main.exe" --client "$B/terminal/main.exe" --counter /tmp/opencode/frontend-presentation/cyclesim/default/counter.exe
  python3 scripts/test-terminal-interrupt.py --daemon "$B/daemon/main.exe" --client "$B/terminal/main.exe"
  python3 scripts/test-synthetic-flow.py --pty --daemon "$B/daemon/main.exe" --client "$B/terminal/main.exe" --preset-export "$B/terminal/workspaces/export_presets.exe"
  ```
- The earlier in-progress `Hidden` integration compile error was resolved by A.
  All final commands above passed; no remaining native-acceptance blocker was found.
  No shared terminal file was edited during this acceptance phase. `git diff --check`
  passed. No physical flow or user demo state was used.
