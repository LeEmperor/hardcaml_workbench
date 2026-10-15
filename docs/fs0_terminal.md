# FS0 terminal host

## Assembly and ownership

The interactive entry point remains `terminal/main.ml`. Once the project registry
is available, `Host_view.render` is the default renderer. `--plain`, the original
baseline fixtures, and RTL artifact/hierarchy inspection retain their existing
paths. Closing artifact/hierarchy inspection returns to the workspace host.

- `terminal/workspace_host.ml`: local navigation model, typed command catalog,
  captured command targets, event decoding, modal reducer, registry projection,
  and launch-allocation selection policy. It does no transport I/O.
- `terminal/host_view.ml`: provisional semantic-role skin, cell-clipped components,
  shelf geometry, tiles, and palette. It renders current typed data only.
- `terminal/main.ml`: startup, existing job/artifact workflows, asynchronous
  workspace/ASIC transport, polling, stale-response guards, effect dispatch, and
  production-renderer capture hooks.

`Native_http.Client.workspace` and `.asic` use their corresponding protocol request
and response types. The daemon registry remains authoritative. The terminal sends
CAS mutations and refreshes after an error; it does not automatically retry a stale
mutation. A pristine registry receives a small terminal preset through those same
operations. Requested widths/heights remain persisted; terminal clamping does not
rewrite them. The default Fit layout distributes visible tiles over the surface;
**Layout: Requested tile sizes** restores shelf order/preferred sizes. These are
client-local layout modes, independent of appearance. Neither implements free x/y
placement. Compact screens explicitly fall back to the focused tile.

Overview and Timing initially share Main. Selection, independent contexts, relinking,
tile bindings, hiding, movement, size, order and zoom all use registry operations.
Focus, browsing cursor, filters, scrolling, log follow, headers, palette and chrome
are client-local. Switching workspaces restores local focus and retains tile state.
Accepted registry mutations autosave named arrangements, requested sizes/order,
hidden/zoom state, contexts/selections and pins. This is session restoration, not
template export/clone. Local header/chrome preferences are not persisted across
client restarts. Remembered Plan inputs use the separate store described below.

Default Overview now includes stage placeholders (placement/CTS/routing/timing/
checks/finalization) alongside synthesis and generic tools. The old acceptance
state has an empty Overview because its sole selector was moved into Timing.
Use the additive **Apply default layout** action to populate it without rewriting
contexts or existing pins. Loading now shows a dedicated host message rather than
a misleading transient legacy dashboard. See the README dashboard instructions.

## Controls

Appearance commands now offer five experimental skins plus independent color,
icon and density settings. Search **appearance** in the palette; see the
[preset guide](appearance_presets.md). Choices are client-local and preserve
workspace/run/pin state. Structured/selective/ASCII/compact is the provisional
startup treatment, not an accepted final aesthetic.

| Input | Action |
| --- | --- |
| `Space c c` | Searchable command palette; `Esc` closes, arrows browse, `Enter` executes |
| `1`, `2` | Overview, Timing |
| `Tab` | Next visible tile |
| `j` / `k`, down / up | Browse runs or project attempts in the focused tile |
| `Enter` in a run selector | Select the browsed run in the workspace's context |
| `/` | Edit the focused tile's filter; `Enter`/`Esc` finishes |
| `[` / `]` | Scroll focused content; logs pause following |
| `b` / `t` | Build / project-scoped generic test |
| `c` | Cancel the focused tile's browsed job, if cancellable |
| `i` | Refresh hardware integration |
| `q` | Exit outside text-entry/modal capture |
| Ctrl-C | Exit client from every view, including filters, palette and incomplete paste; daemon work continues |

The palette includes add/hide/restore/move/resize/reorder-to-end/zoom/unzoom,
pin-run/follow, independent/relink-Main, header/chrome toggles, resume-log-follow,
explicit job cancellation, and existing RTL/hierarchy inspection commands.
Navigation remains available with navigation tiles or chrome hidden. On a surface
too small for the preferred shelves, the focused tile receives the available
surface; `Tab`, palette and workspace switching remain usable.

Existing `n`/`m`, `g`, `a`/`v`, `h`, and hierarchy/connection controls remain available
through the legacy workflow. Artifact/hierarchy views use their existing controls;
close them with the corresponding inspection key. Palette/filter entry captures
shortcut characters, and bracketed paste is suppressed rather than dispatched as
commands.

## ASIC path

Synthesis views now support the first FS1/F06 inspection slice: Enter opens the
cell table; `/` filters, `s` cycles sort, Enter opens row details, `e` opens full
evidence and Esc returns. `j`/`k` selects rows or scrolls details. See
[synthesis inspection](synthesis_inspection.md) for exact semantics and acceptance.
The underlying ASIC wire/storage schema and cached summaries are unchanged.

Filter entry is explicitly marked by a persistent footer. Ctrl-U clears the focused
filter even outside entry mode (or clears the palette query when the palette is
open). A no-match synthesis table is not a failed provider query; clear the filter
to recover the cached rows.

1. Palette: **Discover ASIC flows and runs**.
2. **Describe ASIC flow …** publishes provider capability JSON in an ASIC tile.
3. **Plan ASIC flow / profile …** opens endpoint entry. Enter the exact endpoint,
   optionally followed by whitespace-separated `name=value` assignments. Missing
   endpoints have no fallback. The provider validates supported inputs.
4. Inspect the returned plan identity, selection and plan JSON in the ASIC tile
   (scroll or zoom as needed).
5. **Launch …** passes that exact preview and an idempotency key to the service.
   **Launch and view …** additionally captures the workspace/context, binding and
   selection revisions. Allocation selects only if those still match. A normal
   launch does not select a run. One launch-and-view may await allocation at a time.

Visible run-evidence tiles create deduplicated observation/summary interest;
selectors and project-scoped tiles do not independently acquire ASIC evidence.
Replies are
guarded by daemon/project identity and request order; summaries remain keyed by
their exact run, and the renderer resolves current tile bindings on every frame.
Missing saved runs stay unavailable. Pinning means a live run reference, never an
immutable snapshot. Freshness, completion, acceptance and evidence identity are
shown separately. Unknown timing and case-level test details are not fabricated.
Generic tests and their output always remain explicitly project-scoped.

## Synthesis tile and additive preset

New pristine Overview layouts include a **synthesis** tile. It follows the workspace
run context unless pinned, and displays cell count first, followed by freshness,
compact cell-type breakdown and evidence identity. Full source paths, observation
metadata and expanded per-type counts remain below those compact rows. Timing tiles
continue to display timing evidence independently. The host header puts workspace,
selected run and linkage ahead of long project names.

For an existing persisted registry, including one bootstrapped through raw RPC:

- Open **Space c c**, search **Add synthesis tile**, then Enter. Use **Tab** to focus
  it; **j/k** and **Enter** in a run selector choose the shared context's run.
- Alternatively choose **Apply default layout (add missing tiles)**. This explicitly
  adds missing preset kinds to the current workspace, including synthesis in
  Overview. It is idempotent and preserves existing tiles (including hidden tiles),
  geometry, order, pins, zoom, run selection and context linkage. It does not reset
  a saved registry or automatically migrate an existing layout.
- **Pin tile to selected run** keeps the synthesis reference when the workspace
  selects another run; **Unpin tile (follow context)** resumes following. Scroll or
  zoom the tile to inspect full evidence paths and breakdown details.

## Headless hooks and verification

Inline tests in the new modules cover production event decoding/modal capture,
paste suppression, context linkage/pins, delayed-view fences, local state retention,
allocation selection guards, actual-renderer scope labels and cell clipping.

`--capture-baseline DIR` keeps the historical fixture captures.
`--capture-fs0 DIR` captures the actual default host renderer at 80×24, 120×40 and
32×8, with Overview, Timing, independent, pinned-reference, palette, project-test
and log scenarios, plus `synthesis-a`, `synthesis-b` and `pinned-synthesis`.
The shared, explicit `Fs0_fixture` supplies A=50 and B=73 cells. The actual-renderer
tests assert warm A→B→A switching, simultaneous following B=73/pinned A=50, and
count/freshness/breakdown/evidence visibility in a 32×8 frame. Cached fixture
switches emit no observation or summary-load intents.
FS0 capture data is explicitly synthetic and never installed in a live session.
Both hooks emit plain and ANSI frames without a daemon.

During synthesis-tile integration, `dune build -j20 terminal/main.exe` and
`dune runtest -j20 terminal` passed, and fresh legacy plain/ANSI captures matched
the existing baselines without changes. FS0 synthetic frames were also generated;
these establish renderer behavior, not live tool metrics. Additional follow-up
coverage should expand transport completion ordering, concurrent-client races,
reconnect during allocation, interactive launch-and-view and actual generic-test
cancellation. Real ASIC plan/launch/read and stale CAS rejection have since passed
through actual HTTP; this does not prove every interactive path. The host retains the existing
clock-driven repaint loop; fully reactive publication and richer capability forms
remain future refinements. The endpoint form currently accepts whitespace-separated
assignments, not quoted values with spaces.

[Installed checks](fs0_install_checks.md) passed native lifecycle, external fixture
and legacy baselines, including live discovery/hierarchy and resize coverage.
[Native acceptance](fs0_acceptance.md) passed actual fixture HTTP+PTY, real serial
synthesis (673/685, completed, `not_evaluated`), early allocation/detach and full
workspace/L2 restart identity. The live real reopening check at
`/tmp/opencode/workbench-fs0-unzwt0kn/` used actual current-screen assertions for
673→685, pinned 673 and simultaneous PIN 673/FOLLOW 685. These metrics are distinct
from synthetic capture fixtures. Parent-wide checks previously passed; latest final
parent checks passed, including current HTTP/PTY and installed workflows.
Candidate/evidence inventory is consolidated in the
[active plan](construction_phase_plan.md#evidence-and-candidate-baseline).

## Headless typed HTTP controls

`--asic-operation SEXP` and `--workspace-operation SEXP` decode the public OCaml
operation types directly. They require `--project-root` and either `--plain` or
`--api`, and are mutually exclusive with each other and with the existing action,
artifact, hierarchy and integration-refresh options.

**`--api` emits exactly one complete protocol response S-expression on stdout**:
`(Ok SNAPSHOT)` or `(Error ((kind KIND) (message MESSAGE)))`. It implies headless
operation and suppresses the project/status preamble. Errors also produce a nonzero
exit status and an explanation on stderr. `--plain` without `--api` retains the
status preamble and then prints the complete response sexp. No shell commands or
human provider/log output are parsed to implement these operations.

Examples below invoke the built binary directly, avoiding build-tool output in
stdout. Set `ROOT` and `ENDPOINT` to the actual project and daemon. The illustrative
flow `synth` and profile `default` must be replaced with IDs returned by **Discover**;
there is no implicit first-flow/profile fallback.

```sh
BIN=_build/default/terminal/main.exe
ROOT=/absolute/path/to/project
ENDPOINT=http://127.0.0.1:41733

# Synchronous registry bootstrap/read. This does not install the TUI's tile preset.
"$BIN" --connect "$ENDPOINT" --project-root "$ROOT" --api \
  --workspace-operation Get

# CAS mutation: this exact example is for a pristine registry at revision 0.
# For an existing registry use its returned current revision and workspace ID.
"$BIN" --connect "$ENDPOINT" --project-root "$ROOT" --api \
  --workspace-operation '(Mutate (expected_revision 0) (mutation (Make_independent workspace-4)))'

# One immediate snapshot: no provider execution or automatic 1800-second wait.
"$BIN" --connect "$ENDPOINT" --project-root "$ROOT" --api \
  --asic-operation Get

# Bounded asynchronous capability discovery and description.
"$BIN" --connect "$ENDPOINT" --project-root "$ROOT" --api \
  --asic-operation Discover --wait --wait-timeout-seconds 30
"$BIN" --connect "$ENDPOINT" --project-root "$ROOT" --api \
  --asic-operation '(Describe synth)' --wait

# Exact selected inputs: record arguments have an extra record-list level.
"$BIN" --connect "$ENDPOINT" --project-root "$ROOT" --api \
  --asic-operation '(Plan ((flow synth) (profile default) (endpoint synthesis) (assignments (WIDTH=4))))' \
  --wait

# PREVIEW is the complete preview record returned by Plan, copied without changes.
# This command expects PREVIEW to have already been set from that machine response.
"$BIN" --connect "$ENDPOINT" --project-root "$ROOT" --api \
  --asic-operation "(Run (key acceptance-synth-001) (preview $PREVIEW))"

# Register exact public allocation references; never reconstruct them from paths.
"$BIN" --connect "$ENDPOINT" --project-root "$ROOT" --api \
  --asic-operation '(Register ((attempt /absolute/public/attempt-reference) (stream_id PUBLIC-STREAM-ID)))'

# Use the exact Run_ref returned by the daemon; RUN_REF is that complete record.
"$BIN" --connect "$ENDPOINT" --project-root "$ROOT" --api \
  --asic-operation "(Observe $RUN_REF)" --wait
"$BIN" --connect "$ENDPOINT" --project-root "$ROOT" --api \
  --asic-operation "(Load_summary $RUN_REF)" --wait
"$BIN" --connect "$ENDPOINT" --project-root "$ROOT" --api \
  --asic-operation "(Refresh $RUN_REF)" --wait

# Cancel by the operation key shown in snapshots. Without --wait this only requests it.
"$BIN" --connect "$ENDPOINT" --project-root "$ROOT" --api \
  --asic-operation '(Cancel run:acceptance-synth-001)'
```

For reference, a `Run_ref` with no optional build or label has this S-expression
shape (use actual values from the response):
`((backend asic) (id PROVIDER-RUN-ID) (build ()) (label ()))`.

### Wait semantics and exit status

- No implicit wait: omitting `--wait` makes one request and prints its response.
- `--wait` has a **60-second default budget**, configurable with the finite positive
  `--wait-timeout-seconds`. The terminal polls **Get**, never resubmits the original
  operation, and never cancels daemon-owned work on timeout.
- Discover/Describe/Plan/Observe/Load_summary/Refresh wait only for the corresponding
  daemon query task. In particular, **Observe does not wait for the physical run to
  finish**. The terminal does not infer completion from human-readable run status.
  When Observe coalesces with an already active automatic observer, it returns that
  stream's current snapshot instead of awaiting the stream's execution-long lifetime;
  this is not a promise of an additional independent fresh read.
- Run waits for its own execution task and its associated automatic observer when
  present. Other unrelated executions do not block a query's wait.
- `Get --wait` explicitly waits for the tasks pending/executing in its first
  snapshot; plain `Get` does not wait. Historical failures are inspectable in Get
  output but do not turn an ordinary successful Get into a failed command.
- Targeted failed/detached tasks, protocol/transport errors, unknown task states,
  evicted task identities and timeouts yield nonzero exit status. A timeout prints
  the latest full response snapshot (which may still be `(Ok ...)`) and explains the
  timeout on stderr; **check exit status before using output as completion evidence**.
- Workspace operations are synchronous; combining them with `--wait` is rejected.

The wait policy uses the ASIC service's current machine operation key/state
vocabulary. Its corresponding policy tests must change if that protocol changes.

## Automatic observation and cancellation policy

`terminal/asic_intents.ml` supplies the production TUI's pure read-intent policy.
The 500-ms host refresh still obtains daemon snapshots, but it no longer schedules
Observe and Load_summary unconditionally on every refresh:

- Cached terminal runs schedule neither automatic observation nor repeated summary
  loads. An uncached terminal run gets one summary-load intent per visible-interest
  lifetime; revisiting an evicted run can acquire it again.
- An active daemon observer, refresh operation, or allocated owned run suppresses
  duplicate reads. In particular, the backend's automatic launch reader owns live
  delivery through completion.
- An unowned live run can be observed at most once every two seconds, with no
  duplicate request while its read is active. An unknown execution gets one probe
  per visible-interest lifetime. Missing saved references are never substituted.
- Failed observations and failed summary requests are not automatically retried.
  **Refresh evidence** remains an explicit palette action. Cached/unverified data
  is not silently promoted to validated evidence by this gating policy.

Cancellation commands are derived from **active owned operations**, both before
and after allocation. An allocated `Pending.run` is not a reason to hide Cancel.
Completed, failed and detached history has no cancellation action. The dispatcher
checks current eligibility again before sending the exact operation key.

Launch-and-view matches the daemon's `run:<submission-key>` identity. Failed or
detached tasks release the pending view before considering any retained run
reference; a completed task without allocation is an explicit failure. A rejected
or unconfirmed launch request also releases its pending view, including when a
newer Get snapshot has overtaken the reply. Deferred dispatch only installs a
pending view after target revalidation, and never resubmits a failed launch.

## Remembered interactive launch choices

The TUI now persists the last explicitly requested Plan selection: flow, profile,
endpoint and assignments. This preference is independent of selected/pinned runs,
registry layouts and provider evidence. It is loaded on interactive startup, not
derived from historical runs or the last launched preview.

Storage is **client-local and project/environment-scoped**, under
`$XDG_STATE_HOME/hardcaml-workbench/terminal/launch-<digest>.sexp`, or
`$HOME/.local/state/hardcaml-workbench/terminal/` when XDG_STATE_HOME is unset. The key
uses the daemon's canonical project root plus the requested execution environment;
no transient daemon or project ID enters it. Versioned records verify that key on
load. Writes run off the UI thread, are serialized per client session, and use an
atomic rename. Provider/project files and the daemon workspace registry are not
rewritten to store these preferences.

**Plan remembered inputs** is available only after the exact flow/profile has been
discovered again. Its endpoint/assignments are still validated by the provider.
Planning the same flow/profile pre-fills its editable endpoint form. Missing flows
or profiles stay unavailable; opening the TUI never plans or launches automatically.
Preferences remember requested inputs even if the subsequent plan fails. Corrupt
or unavailable preference storage is nonfatal; load errors go to the optional
diagnostic log and write errors are surfaced in the host notice.

These are per-client UI preferences, not a daemon-shared preference service.
Different terminal clients use atomic last-writer-wins files. The headless RPC
utility deliberately does not change interactive launch preferences. Remembered
previews are not reusable launch authorization: each launch still requires the
exact current provider-prepared preview.
