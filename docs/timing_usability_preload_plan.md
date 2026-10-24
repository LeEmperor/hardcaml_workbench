# Timing usability and background index loading

**Status: implemented, verified and deployed to the retained example binaries.**
See [controls, settings and acceptance](timing_workspace_usability.md).

## Authorized scope — 2026-10-23

Owner requests configurable three-decimal Timing values, default-on per-tile string
compression, a wider paths column, colored/readable Timing provenance and Session,
ordinary inspection inside the built-in Timing workspace, workspace order
Overview → Testing → Waveforms → Timing, and background index preparation so a
completed selected run is ready when Timing is opened. Keep explicit-only loading
and optional separate investigations available.

This builds on the [actual-run diagnosis](timing_workspace_loading.md). Preserve all
uncommitted preceding fixes, including correct Timing-stage inspection and the live
removal of the extra simulation catalog. Do not rerun physical EDA to verify UI work.

## Behavior and shared contracts

### Presentation

- Default displayed Timing slack/measurements to **three decimal places**. Honor
  the requested truncation toward zero; sorting, comparisons, status and source bytes
  continue using original precision. Preserve negative near-zero identity/verdict
  rather than implying a tiny violation passed. Expose bounded per-tile precision
  choices (0–9) with persistent preferences and workspace-config support.
- Add a reusable per-tile **string compression** presentation trait, default on for
  Timing and Session/run identity surfaces. Long identifiers use first four and last
  four characters; source paths retain a recognizable filename/short source identity.
  Full text remains available by disabling compression. Never rewrite RPC selectors,
  evidence identity, raw stored reports or exported source bytes.
- Use semantic theme roles for Session connection status and Timing provenance:
  green/success for connected/validated, warnings for cached/unavailable, failure
  roles for errors, muted labels and differentiated source/context values. Reuse
  Overview's Session conventions rather than hardcoding unrelated colors.
- Widen the roomy Timing path column from approximately 40% to approximately 50%
  of content width (about ten percentage points), with selected-path/provenance
  stacked on the right. Preserve small-terminal fallbacks and user custom layouts.

### Workspace routing and ordering

- Ordinary Inspect timing paths uses the existing built-in Timing workspace in the
  current window; it does not create a captured temporary workspace by default.
- Built-in Timing follows its resolved selected run. Explicit navigation captures
  the requested analysis, including stage/source, and prepares that workspace for
  the matching run without silently rewriting unrelated Main contexts or pins.
  If an existing pin conflicts, show an actionable explanation/explicit separate
  inspection option rather than silently stealing the pin or opening a new workspace.
- Preserve an explicitly named **separate Timing investigation** action and provide
  a discoverable close action for those extra workspaces, using existing lifecycle
  guards. Ordinary Inspect never depends on knowing how to close a temporary tab.
- Fresh default order: Overview, Testing, Waveforms, Timing. Apply the requested
  order to this user's saved built-in tabs with a targeted protocol mutation;
  preserve other custom workspaces, selected contexts, pins and stored evidence.
- New runs/source changes invalidate stale inspection state. Existing empty Signoff
  views must not trap the built-in Timing workspace on the wrong stage.

### Background index policy

- Default: bounded **background index** warm-up for exact run/analysis sources
  resolved by built-in Timing workspaces, including when hidden. Trigger when a
  completed Timing analysis becomes available, even if Signoff is still running.
- Also warm a newly selected completed run and reopen exact retained L2 indexes on
  client restart; there is no need to wait for a new completion transition forever.
- Do not change the active workspace, focus, run selection or pins. Bind prepared
  rows to the workspace's resolved run/source and reject stale responses.
- One background inspection request at a time, deduplicated per exact source;
  bounded queues and finite failure attempts. Interactive inspection wins before
  starting another background request. Respect the daemon's serialized inspection
  publication lane rather than flooding it with speculative details.
- Load/cache the index and prepare reusable search/filter/sort state; **do not draw
  hidden terminal images or fetch every detail**. Full detail remains lazy with the
  existing finite selected/neighbor demand after explicit visible inspection.
- Provide a persistent, discoverable **explicit-only** option (and CLI override if
  appropriate). Explicit-only means no new speculative provider inspection reads;
  already-published matching evidence may still hydrate passively.
- Show not-loaded/loading/ready/empty/error and cached-unverified state honestly.
  Switching to Timing while a warm-up is pending should attach to the same request,
  not duplicate it. Warm-up failure does not spin on every poll.

## Agent ownership and sequence

At most three general implementation agents; sequential stable handoffs because
presentation, navigation and warm-up share `terminal/main.ml` and host state.
Each agent gets at most six jobs with explicit Dune limits and serialized heavy
checks. Parent integrates after allocations are released, at most twenty jobs.

**Crash-recovery override:** after the owner reported another server crash during
the navigation package, all remaining builds/tests use **`-j 2`**, one build/test
group at a time across agents and parent. No old Dune/compiler processes remained
after reboot. Retain the partial edits and verify them rather than restarting work.

**Second recovery override:** the server crashed again during Agent C's initial
implementation. Navigation was completed and verified before that crash; warm-up
source edits survived but have not completed acceptance. All remaining builds and
test groups now use **`-j 1`**, run serially, with numerical worker environment
limits set to one where applicable. No broad suite runs concurrently with another
agent or provider measurement. Do not assume interrupted checks passed.

### Agent A — presentation and layout

Own tile presentation/config/preference plumbing, formatting helpers, Timing/Session
rendering, palette settings, stock Timing column layout and corresponding tests.

- [x] Add configurable decimal truncation and reusable persistent compression trait.
- [x] Apply readable identifiers/report paths, raw-precision safety and full-text toggle.
- [x] Color Session/provenance via theme roles; widen Timing paths column.
- [x] Verify defaults, preferences/restart, raw numeric ordering, near-zero negatives,
  Unicode/narrow layouts and ANSI semantic roles. Hand API/settings details to B/C.

### Agent B — built-in workspace navigation/order

Starts after A; owns workspace selection/inspection lifecycle, built-in startup order,
explicit separate/close controls and related unit/native tests.

- [x] Ordinary inspection reuses built-in Timing, with run/stage/source/pin fencing.
- [x] Built-in Timing can hydrate the resolved run without explicit opening of a new
  workspace; expose helpers for C that never activate/select/retarget pins.
- [x] Preserve explicit separate investigation with discoverable close action.
- [x] Set fresh default order and provide exact targeted saved-order migration steps.
- [x] Verify repeat inspection creates no tabs, selected-run change, pin conflicts,
  explicit separate/close behavior and historical Signoff compatibility.

### Agent C — background warm-up and integrated acceptance

Starts after A/B; owns finite index-warmup planner, scheduling/loading preferences,
passive Timing hydration and focused native completion/background acceptance.

- [x] Implement default-on, source-fenced hidden index loading and explicit-only option.
- [x] Coalesce with interactive demand, bound concurrency and suppress failure storms.
- [x] Hydrate built-in Timing while hidden without drawing, changing selection or
  triggering full-detail fan-out.
- [x] Prove a completion observed from Overview prepares hidden Timing, switching
  displays rows without another provider index read, explicit-only makes no read,
  and restart/source/selection races preserve identity.
- [x] Verify integrated presentation/navigation against retained actual a023 evidence
  in a private daemon/client, with before/after read counts and screenshots.

### Parent — integration, saved state and deployment

- [x] Record requested behavior, contracts, ownership and policies before edits.
- [x] Integrate packages, run full build/lint/tests and focused real-run acceptance.
- [x] Apply only requested live saved tab order/layout adjustments through revision-
  checked APIs; preserve extra workspaces until explicitly closed by user intent.
- [x] Refresh retained demo client/daemon binaries as needed without stopping live
  processes. Record exact restart steps, tests, settings and limits in docs.

## Acceptance and policies

No repository Git staging/commits/pushes. Preserve user work and previous feature
edits; scripts' existing isolated test Git fixtures are allowed by owner policy.
Shared build/test job cap 20 including nested subprocesses. Sibling repos may change
if justified, but this slice should primarily be Workbench. No physical EDA run.

Acceptance includes: 0.125029 ns → 0.125 ns by default; configurable persisted
precision/compression; raw sort/verdict unchanged; recognizable short identifiers;
green Connected and readable provenance; wider table; built-in tab reuse and order;
selected run ready in hidden Timing after completion; explicit-only no speculative
reads; bounded scheduling with no stale retargeting/pin changes; correct cold/warm/
restart/error UI. Test actual retained path data as well as deterministic completion
fixtures. Record any global formatting baseline separately from new-file failures.

## Execution record

Agent A completed presentation traits, schema-4 preferences, semantic colors and
equal-width Timing columns; terminal/protocol tests and changed-file formatting
passed. Agent B recovered and verified navigation/order at two jobs, including
actual a023 evidence in `/tmp/opencode/b-navigation-a023/`, built-in source changes,
explicit separate/close and synthetic Testing/flow regressions.

Agent C recovered its partial work and completed verification at one job. It adds
`Timing_preload`, one request reserved until publication/failure, explicit-request
coalescing, finite source-attempt tracking, loading UI and schema-5 preferences.
Default is background index; palette controls persist it and CLI supplies an initial
override. Hidden reads do not activate detail demand. At 128 attempted sources per
scope, further loading stays explicitly available rather than evicting failed keys
into retry loops. Exact selection/source/project fences remain enforced.

Native warm-up acceptance passed 20 assertions at
`/tmp/opencode/c-preload-native-final/`. Actual retained a023 preparation at
`/tmp/opencode/c-preload-actual-a023-measured/` loaded 1,021 rows with one index read,
zero detail reads, Overview still active and registry unchanged. Switching to Timing
added no index/detail reads. Hidden wait was 8.03s; switch/capture 2.18s includes
deliberate PTY delays and is not a render benchmark. Explicit-only regression passed.

Parent full build/lint/runtest passed using `-j 1`, serially. All changed OCaml files
pass configured formatting; global unrelated baseline remains. Existing pre-reboot
VCD fixture loss blocked full embedded-waveform acceptance, while its edited startup
assertions passed deterministic replay. No physical flow was launched.

The production daemon was absent after reboot. Parent used a short-lived owned
daemon to apply only saved tab-order mutations (revision179→182), backed up the
workspace file and verified contexts/pins/tiles/extra workspaces unchanged. Legacy
preset references already pick up new stock widths; no geometry reset was needed.
Receipt: `timing-tab-order-8c502a0922b54e95a98d8bd3b76db8c9` under the real-demo
receipts directory. Refreshed binaries are recorded in
`refresh-binaries-986bfa8c3947499699d5ff3d5af9cc04`. Start the refreshed daemon and
client; no reseeding/provider installation is required. Detailed controls and
evidence are in [the delivery record](timing_workspace_usability.md).
