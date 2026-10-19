# FS2 — Structured simulation delivery

## Activated WB-028 implementation — 2026-10-18

### Waveforms workspace extension — active owner request

Keep `w` as quick full-area inspection. Add `W` on a selected Testing VCD to open
an actual dedicated Waveforms workspace, with independent Signals, Waves, VCD picker
and Logs tiles. All signal names remain visible whether enabled or disabled. Global
command-palette access must work in both quick inspection and workspace mode; do not
let Space signal-toggle consume the palette prefix (use Enter/toggle command instead
where required). Workspace actions preserve exact project/attempt/case/artifact/digest
identity; selecting a different VCD explicitly retargets the coordinated tiles and
associated logs. Missing/expired logs must be honest, not borrowed from a current job.

Use existing workspace registry/persistence/layout and appearance machinery. The
waveform workspace should remain usable after switching away/back and reopen with
explicit unavailable state if retained data no longer exists. Separate signal picking
from waveform rendering so disabled signals never disappear from the picker.

Implementation ownership for this extension: Agent A owns workspace definitions,
registry/host/view integration and publishes the tile/action contract; Agent B owns
waveform_view and terminal/main integration (loading, keyboard/palette, `W`, pinned
selection/logs). Agent C owns acceptance tests. A and B coordinate changes to shared
host/view interfaces; no duplicate implementation. Initial builds disabled for A
until contract handoff, then allocations A=4, B=8, C=4 (16 maximum); every Dune and
nested build requires explicit bounded jobs. No mutative git operations. Coordinator
owns docs and verification. Current state: implemented and automatically verified.
350 combined acceptance checks passed, including exact-attempt logs, pin restoration,
picker fencing and ordinary palette/workspace controls. Disabled names stay visible;
Enter toggles and Space c c remains global. Subsequent missing-availability marker
fix passed focused tests/build/lint. [Controls and evidence](testing_workspace.md#dedicated-waveforms-workspace).
Existing delivery records below describe the initial quick-viewer implementation.

Owner presentation refinements implemented: compact Session tile replaces the
Waveforms global header; Signals is narrower and defaults to aligned inline values
with a persisted Stacked option. Ctrl-Backspace/Ctrl-W word deletion works in filter
editing. Idle controls use hint policy, hidden by default for Waveforms. Existing
custom layouts require explicit Apply preset + Fit to add Session; tests verify
preserved pins/custom state and no extra artifact load. Final evidence:
`/tmp/opencode/wb028-accept-xkuv7752/report.json` (305 checks).

Subsequent compact layout verified with 350 checks:
`/tmp/opencode/wb028-accept-f4m244ea/report.json`. Session now sits above Signals in
a 1:4 target left/right split (left minimum 24), Waves spans their combined height,
signal columns use content width, and attempt IDs use first-four/last-four shortening.
Owner manual appearance review is pending. Vertical cursor and absolute-time ruler
are agreed next directions but **must wait for that review**; neither is implemented.

### Cursor and absolute ruler — activated by owner

The owner has now authorized implementing the cursor/ruler follow-up. Preserve the
validated layout. Both quick viewing and the workspace Waves pane need a visible
cursor column and adaptive absolute physical-time ruler. Use one exact integer
tick-to-cell mapping shared with the installed Waveterm raster; no float-based loss
of large timestamps. Highlight the cursor column without destroying wave glyphs,
including an explicit off-screen direction when panning leaves it outside the plot.
Compressed columns represent multiple ticks honestly while the exact cursor tick and
inspected values remain unchanged. Major labels/minor marks must avoid overlap at
narrow widths, work with declared timescale magnitude/unit, and stop at trace bounds.
Ruler/cursor are data presentation, not idle hints, so quiet hints must not hide them.

Agent B owns waveform_view integration and focused mapping/ruler tests; Agent C owns
independent probe/PTY acceptance. Build allocations B=8, C=4, serial within each;
coordinator does not compile concurrently. No mutative git commands. Acceptance:
first/interior/last ticks, expanded and compressed scales, off-screen cursor, pan,
zoom, resize, huge timestamps/non-unit timescales, all themes/presets and no glyph
corruption or drift between cursor/value/ruler. Rebuild client/daemon/probe/exporter
for the existing refresh workflow. Status: implemented and automatically verified.
Shared `terminal/waveform_time.ml/.mli` provides exact scale, cell bounds, cursor
position and physical-time/ruler formatting; both view surfaces use it. Full
acceptance passed 1,773 checks at `/tmp/opencode/wb028-accept-2swfin7h/report.json`,
including glyph-preserving cursor attrs, compressed cells, off-screen directions,
adaptive labels, huge timestamps, all schemes/presets and prior workflow regressions.
Builds/inline tests/lint/formatting and synthetic preset smoke passed. All four
refresh binaries are rebuilt in `/tmp/opencode/wb028-accept-build`.

This section governs the embedded-waveform extension in
`/home/wayne/devel/jane/sim-artifacts`; historical FS2 allocations below do not apply
to this extension. Design: [WB-028](features/verification/WB-028-waveform-viewer.md).

Deliver a bounded retained-VCD viewer opened from Testing, using installed
`hardcaml_waveterm` rendering where its API permits faithful integration. Investigate
the actual installed API before choosing the conversion/rendering boundary. Preserve
time units, hierarchy, buses and explicit unknown/high-impedance behavior; unsupported
input must fail clearly rather than silently change meaning. No simulation reruns.

The initial UI is a full-area investigation surface with return to the same Testing
context. Capture exact project/attempt/case/artifact/digest at open, verify the existing
byte transport before parsing, and fence stale asynchronous completions. Signal
selection/filtering, cursor/value inspection, pan/zoom, resize and bounded loading are
required. Keep external export/viewing available. Surver integration remains separate.

### Ownership and resource rules

- No git staging, commits, pushes, checkout/reset or authorship changes.
- Coordinator owns docs, integration review and final checks.
- Agent A owns new `terminal/waveform_data.ml` (and interface if useful): installed
  library investigation, bounded VCD parsing/model/conversion and semantic tests.
- Agent B owns new `terminal/waveform_view.ml`, terminal/main.ml and terminal/dune:
  embedded rendering, full-area host integration, loading actions and UI controls.
  Coordinate the data API with A using its interface/source; do not duplicate parsing.
- Agent C owns new acceptance/probe files and any necessary test-only Dune stanza:
  real VCD integration/interaction verification; coordinate stanza edits with B.
- Agents initially perform implementation without running builds. Coordinator grants
  build allocations explicitly. Total concurrent build/test jobs must be <=20;
  all Dune commands require explicit `-j`, including nested script builds. Prefer
  serial coordinator checks at `-j 10`; do not run full physical flows.
- Preserve existing launcher edits and all unrelated work. No sibling repository
  edits are expected; report a concrete need before expanding scope.

### Acceptance and evidence

Verify a real retained FIFO/native VCD, malformed/unsupported/oversized data, exact
time/value navigation, alias/bus/X/Z behavior, responsive bounded rendering, selection
changes during load, return-to-Testing and no accidental simulation side effects.
Run focused inline tests and native terminal build/lint; add a practical PTY/probe
check for the UI path where feasible. Record measured parsing/rendering costs and
limits, commands/results, actual controls and remaining gaps before completion.

Implementation status: bounded embedded slice implemented and automatically verified.
139 combined semantic/probe/PTY checks passed after appearance/scale refinement;
terminal inline tests, native builds,
lint and formatting passed. Builds used separate -j 8 and -j 4 allocations (12 total).
Delayed actual byte responses were delivered after closing/replacing the viewer;
old completions neither reopened nor retargeted it. Narrow values/back controls were
fixed and checked at 80x24, 120x40 and 180x55. No physical flow or sibling-repository
changes were needed. [Controls, bounds and measurements](testing_workspace.md#embedded-waveform-viewer).
Wide-terminal coverage now includes a filled 198-column plot at 230 columns, regular
clock periods, all four color schemes and all five appearance presets. Compact
metadata and exact identity inspection replace the original raw multi-line header.
WB-028 remains partial for lazy loading and four-state graphical rendering; the
bounded initial user workflow is implemented. Owner interactive review is pending.

**Subsequent activated extension, 2026-10-17:** WB-034 genuine FIFO adoption,
WB-032 test catalog and WB-063 cooperative Testing investigation are implemented
and automatically verified. The shared coordination plan is
[testing_cluster_plan.md](testing_cluster_plan.md); [current controls](testing_workspace.md).
This leaves the original accepted milestone below closed.

**Milestone closed, 2026-10-16: structured project-scoped simulation delivered and
accepted.** The owner confirmed the basic demo works and authorized closeout after
automated verification. This is the retained implementation/coordination plan for
the FS2 worktree. The user approved the recommendations below. The construction plan
remains the overall delivery index; this document records FS2 contracts, work
ownership and acceptance. Record actual results, not intended results, as delivered.

Remaining adoption/performance/extensions are [named followups](backlog/fs2_followups.md).
Owner integration and post-merge checks are a separate
[handoff](fs2_acceptance.md#integration-handoff), not claimed complete here.

## Scope and accepted decisions

- Project-scoped structured suites/cases, seeds and parameters; optional exact ASIC
  input association. A selected ASIC run never supplies implicit provenance.
- Reuse the existing supervisor's jobs, per-root queue, cancellation and submission
  deduplication. No separate simulation process scheduler.
- Versioned project-owned discovery/launch/event contract; ordinary Dune tests and
  driver-less projects remain supported. Do not infer case outcomes from human logs.
- Capture invocation inputs. Targeted reruns create new jobs linked to the original
  attempt, and explicitly mean rerun on the current project, not an archived build.
- Bounded live observations, summary/detail views, failure reports and traces.
- Workbench-owned bounded durable normalized test records; explicit missing artifacts
  and interrupted history after restart. No automatic process replay on restart.
- Byte-exact trace export to the terminal host and explicit external viewer actions.
  Factor small shared export mechanics where useful, preserve ASIC behavior, and do
  not invent ASIC identities for simulation artifacts.
- Real PDK-free Cyclesim demonstration. Embedded waveform UI and automatic ASIC
  acceptance contribution are later extensions. Gate-level support is an optional
  evidence-backed adapter, not a prerequisite to this delivery.

## Feature-set contract direction

FS0 -> FS2 supplies execution/identity/transport/tiles, already delivered.
FS1 -> FS2 supplies artifact/investigation patterns and optional ASIC evidence,
already delivered; adaptation is now FS2 work, not an unfinished FS1 gate.
FS2 -> FS3 supplies simulation configuration/view identifiers that setup/templates
may expose later. FS3 conveniences are not required for this implementation.
FS2 -> ASIC acceptance is a separately activated evidence bridge, never automatic.

## Working rules

- Work in `/home/wayne/devel/jane/fs2`; no git add/commit/push or authorship changes.
- Up to three general implementation agents. The coordinator owns documentation,
  integration and scheduling builds/tests. Agents must not run Dune/build/test jobs
  unless explicitly allocated a budget. Total active job budget must not exceed 20.
  Initial implementation allocation: backend 8 jobs, terminal 6 jobs, provider 6
  jobs, each in a separate absolute build directory under `/tmp/opencode`. Each
  agent must run its own commands serially and bound nested fixture builds too.
  The coordinator runs no concurrent compilation during these allocations.
- Use `scripts/with-switch.sh dune ... -j 20` for coordinator-run Dune checks when no
  other compiler/test process is running. Avoid nested unbounded builds in fixtures.
- Evidence/state under `/tmp/opencode`. Prefer PDK-free fixtures and Cyclesim; no full
  physical flow is needed for the core acceptance.
- Preserve other agents' changes. Agents own separate file groups below; protocol
  changes after the initial contract require communicating the change in handoff.

## Implementation ownership

1. Backend agent: protocol and provider/config contract, simulation adapter and
   supervisor integration, daemon RPC, durable records/artifacts and backend tests.
   Owns protocol/, project_integration/, adapters/, backend/, daemon/ and any HTTP
   transport wiring required by the new endpoint.
2. Terminal agent: typed simulation view/state, command/palette actions, captured
   launch/rerun forms, polling/fences, trace export/viewer and terminal tests.
   Owns terminal/. Keep generic tests and ASIC investigation available.
3. Provider/acceptance agent: project-owned real Cyclesim provider demonstration,
   deterministic malformed/failing/cancellation provider fixtures and end-to-end
   acceptance scripts. Owns new example/fixture files and scripts/test-fs2-*.
   Changes to hardcaml_asic_example may be small and additive if needed; prefer an
   in-repository reproducible example when that provides stronger independent tests.

The backend agent first publishes the concrete contract files and a handoff here
before implementation agents 2/3 start. Stable contract definitions are the shared
source of truth, not independently invented client/provider schemas.

## Delivery order

1. Freeze versioned discovery/config/event/RPC/types and input/artifact limits.
2. Implement supervisor-backed execution and reducer/store with focused tests.
3. Implement actual terminal suite/attempt/case investigation and explicit commands.
4. Integrate real Cyclesim provider and trace artifacts, targeted rerun and history.
5. Verify formatter/lint/build/tests and native HTTP/PTY acceptance, with job budgets.
6. Update feature inventory, construction plan and acceptance/controls documentation.

## Required acceptance

- Generic tests continue without ASIC configuration.
- Discovery is bounded/versioned; cases/seeds/parameters are explicit.
- Retried submission keys launch once; different payload with same key conflicts;
  intentional reruns produce distinct linked attempts with original inputs.
- Process exit and semantic test outcome remain separate; malformed/truncated or
  duplicate event streams cannot manufacture successful case/suite completion.
- Partial results survive cancellation/crash; unfinished cases are honest.
- Live progress, failure detail and logs are usable; two tiles have independent
  selection; hiding/switching views does not cancel jobs or relabel project tests.
- Exact raw trace bytes survive daemon-to-client export; stale/missing/changed
  artifacts fail explicitly; actual external handoff is exercised.
- Historical records reopen after daemon restart without launching jobs; missing or
  corrupt records have bounded honest behavior.
- One actual Cyclesim run with explicit seed/parameters and rerun, plus deterministic
  failure/malformed/cancellation fixtures and actual terminal input acceptance.

## Contract handoff

Initial interface frozen by backend agent, 2026-10-16. Agents 2/3 may implement
against these concrete definitions now:

- `protocol/simulation.ml`: standalone `Simulation` RPC, portable discovery,
  explicit selection/captured invocation, provider request/events, attempt/case
  states, history summaries and hex-encoded raw-byte pages. No V1 event-union or
  manifest changes. Endpoint `/api/v1/simulation`, hello capability `simulation`.
- `project_integration/simulation_config.ml`: parsed/validated independent
  `hardcaml-workbench-simulation.sexp` with required fields `schema_version=1`,
  absolute `provider_executable`, `provider_args`, `discovery_timeout_seconds`
  (1..60), `run_timeout_seconds` (1..86400). No implicit provider build.
- `project_integration/simulation_protocol.ml`: bounded discovery and event-line
  parsers, structural validation, selection validation/normalization.
- `adapters/simulation_adapter.ml`/`.mli`: exact executable/environment/cwd/argv
  contract. `native_http/client.ml`: typed `Client.simulation` helper, same outer
   transport Or_error as ASIC. Endpoint implementation is now delivered.
- `docs/fs2_simulation_contract.md`: authoritative external framing/examples,
  lifecycle/reducer semantics, RPC operation effects/errors and durable limits.

Provider handoff: from canonical project-root cwd run
`EXEC [provider_args...] discover --protocol-version 1`, stdout exactly one
`Simulation.Discovery.t` sexp, stderr diagnostics, exit 0. Run argv is
`EXEC [provider_args...] run --protocol-version 1 --request ABS_REQUEST --events
ABS_EVENTS --artifact-dir ABS_ARTIFACT_DIR`. Request is
`Simulation.Provider.Request.t`; append/flush LF-delimited machine sexps of
`Simulation.Provider.Event.t` to events file. Stdout/stderr are human logs only.
Sequence zero Started, contiguous sequence numbers, explicit case start/finish,
optional progress/artifact declarations, final Finished Passed/Failed. Close
artifacts before announcing normalized relative paths; no symlinks. See the
contract for exact syntax, including named-record variant payloads.

Terminal handoff: operations Get, Discover, Launch, Rerun, Observe, History,
Cancel, Read_artifact_bytes. Poll snapshots; no simulation V1 update events.
Discover schedules/coalesces a normal supervisor job; Get never launches tools.
Launch supplies current discovery_digest, unique submission_key, nonempty explicit
case list, canonical uint64 decimal seed string, every declared parameter, optional
exact ASIC refs. Rerun supplies original attempt ID and explicit nonempty subset;
captures original seed/parameters/ASIC refs against current project catalog/config,
new job/attempt and immediate parent job/attempt identity. Snapshot detail and byte
page are response-local; two tiles must retain independent selections/fences.
Use existing Read_log with attempt.job; historical logs need not survive restart.

Limits frozen: 64 suites/1024 cases total/32 parameters per suite, 1 MiB catalog,
16 KiB event including LF, 100000 events/16 MiB stream, last 256 accepted events
retained plus normalized state; 128 artifacts, 64 MiB each/256 MiB per attempt;
64 KiB decoded raw-byte page. Per-root durable history 100 attempts/16 MiB
normalized records/512 MiB artifact copies, oldest-terminal eviction, active never
evicted. History pages <=25. Raw bytes use lowercase hex with expected SHA256;
missing/changed evidence is explicit. Artifact size/hash may be absent when capture
failed; availability is typed, never inferred from a zero length.

Semantic freeze: process exit and case outcome remain separate. Valid terminal
stream plus exit 0 required for overall Passed/Failed. Duplicates/gaps/truncation,
bad identity/transitions, overflow/nonzero exit/timeout => Incomplete; preserve
accepted case results, unfinished cases Incomplete. Cancel => Cancelled/Incomplete;
restart => Interrupted/Incomplete without replay. Unknown progress total stays
indeterminate. No implicit ASIC evidence or automatic acceptance contribution.

Initial publication supplied contracts/codecs/adapters without running builds/tests.
Backend implementation has now resumed and delivered the endpoint/capability,
Service supervisor operations and submission-registry hooks, live tail/reducer,
durable root-keyed reservations/history, artifact capture/verification and RPC
responses. No public `Simulation` wire definitions changed during the implementation
resume. Optional ASIC refs remain provenance references only in v1, not implicit
collateral staging; acceptance validates the exact current adopted validated terminal
summary/catalog, hashes its bytes and rechecks adoption before accepting association.

Backend technical handoff (2026-10-16):

- New backend files: `simulation_task.ml`, `simulation_files.ml`,
  `simulation_reducer.ml`, `simulation_service.ml`. `Service` exclusively creates,
  queues, logs, times out, cancels and reaps simulation processes. RPC serialization
  in the simulation service protects reservations; it is not a process scheduler.
- State is `<state-dir>/simulation-v1/<SHA256 canonical root>/<opaque attempt>/`:
  atomic fsynced `record.sexp`, hashed-ID `*.bytes` copies and ephemeral `work/`.
  Restart marks unfinished records Interrupted, removes work/orphan copies and
  never signals or replays historical producers. Missing/changed artifact reads
  return typed errors; Observe also exposes missing/size-changed availability.
- Native endpoint `/api/v1/simulation` and hello `simulation` are wired. Client
  helper retains the normal outer transport Or_error and inner typed response.
- Meaningful tests are in `backend/test/test_simulation.ml` with deterministic
  `backend/test/fs2_provider.py`; daemon endpoint/fence checks extend `test_rpc.ml`.
  Tests cover accepted and invalid reducer transitions, live unknown totals, detail
  bounds, actual provider concurrency/conflicts/rerun/queue/cancel/timeout, oversized
  streams, binary pages, stale catalogs/config, missing/changed/symlink artifacts,
  unadopted ASIC rejection, durable reservations/interruption/corruption, pagination
  and active-preserving eviction/exhaustion.
- All backend-owned verification commands use the absolute separate build directory
  `/tmp/opencode/fs2-build-backend` with `-j 8`, run serially. Targeted Dune tests
  cover `backend/test protocol/test project_integration/test adapters/test daemon/test`.
  Backend/daemon/native client compilation, owned-library lint and owned-file
  `ocamlformat --check` are also exercised. Final command/results are returned in
  the backend agent handoff. Real provider/native PTY acceptance remains coordinated
  with the terminal/provider agents; no physical flow was started by this agent.

## Verification record

Final combined format/lint, full `dune runtest`, and full `dune build` passed serially
with `-j 20` using `/tmp/opencode/fs2-build-backend`. Actual post-review native
HTTP/PTY acceptance passed **45 checks** at `/tmp/opencode/fs2-native-yx27d5_b/`.
Real standalone Cyclesim proof passed at `/tmp/opencode/fs2-provider-tzid09_h/`;
all five interrupt modes passed at `/tmp/opencode/workbench-terminal-interrupt-ou1stfm9/`.

Review followups are included: environment/config capture and reservation fences,
persistence failure handling, chunked/yielding event drain, retained job/closure
bounds, stale frontend receipt rejection, wrapped scrollable failure detail, and
worker-thread export hashing/writing. No public Simulation wire changes were needed.

See [FS2 acceptance](fs2_acceptance.md) for exact commands, controls, evidence and
remaining scope. Metadata/capture filesystem work retains slow-storage latency
limits; historical logs and archived-build replay are not promised. No physical
flow, sibling edits or mutative Git operations were performed.
