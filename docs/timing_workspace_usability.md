# Timing workspace: presentation, navigation and preloading

The built-in Timing workspace is now the normal destination for timing inspection.
Its index is prepared in the background by default, including while Overview is
active. Presentation and loading choices persist across client restarts.

## Display and controls

- Timing measurements default to **three decimal places**, truncated toward zero:
  `0.125029 ns` displays as `0.125 ns`. Sorting, comparisons, constraints and stored
  evidence retain their original precision. Tiny negatives keep a minus sign, such
  as `-0.000`, rather than appearing to be a passing zero.
- Long identities default to **first four / last four** compression, for example
  `a023…4e4a`. Source paths retain a recognizable filename and shortened source
  identity. Provider report-source headers are compacted for display; technical
  report bodies, exports, selectors and stored raw evidence remain intact.
- Session uses the same semantic status styling as Overview: connected is the
  theme's success color, normally green. Timing provenance distinguishes labels,
  source identity, verified state, warnings and failures instead of uniform text.
- The paths column and right-hand detail/provenance stack now share width equally
  in roomy layouts. At 120 columns they each occupy 60, expanding the old paths
  area by roughly ten percentage points. Narrow layouts remain bounded.

Focus the relevant tile, open **Space c c**, and choose:

| Palette command | Effect |
| --- | --- |
| `Timing: Truncate to 3 decimal places` | Set focused-tile precision; choices 0–9 are available |
| `Strings: Compress identifiers and source paths` | Enable compact strings for the focused tile |
| `Strings: Show full identifiers and source paths` | Reveal full strings; scrolling uses the full wrapped content |
| `Reset presentation overrides (inherit)` | Restore defaults/inheritance for the focused tile |

Portable workspace-config presentation fields are `decimal_places : int option`
and `string_compression : bool option`. Explicit per-tile client overrides persist
with session/workspace/tile/kind identity checks. Preferences use schema 5 and read
schemas 1–4; older records inherit three decimals, compression and background indexes.

## Where inspection opens

Normal **Inspect timing paths** and Overview Timing inspection open the existing
built-in **Timing** workspace in the current window. Repeated inspection does not
add tabs. Switching selected runs updates its exact source and invalidates stale
path/detail state. New seven-stage Timing and historical Signoff analyses retain
their respective stage/source identities.

The built-in follows its resolved run and honors pins/independent contexts. If an
explicit request conflicts with its bindings or hidden panes, the client explains
the conflict rather than stealing pins or silently opening another workspace.

For an intentional independent comparison, choose **Separate Timing investigation**
for the desired run. Inside such a workspace, **Close separate investigation** is
available in the palette. Closing is revision-checked and protects configured/shared
workspaces, Main/shared contexts and the last workspace in a window.

Default tabs are now:

```text
Overview → Testing → Waveforms → Timing
```

The owner's saved built-ins were reordered to match. Existing extra investigations
remain after them; use the close command to dismiss those when no longer needed.
Tiles, geometry records, contexts, pins and evidence were verified unchanged.

## Background loading

Default **Background index** mode observes exact completed analyses resolved by
built-in Timing workspaces, even when hidden. It handles:

- newly published analysis when Timing completes, including during later Signoff;
- selecting an already-completed run;
- reopening a cached index after client/daemon restart.

It loads the **index**, then prepares reusable searchable/filter/sort state. It does
not draw hidden terminal frames, fetch every full path report, change focus, select
a newer run, or alter pins. Thus a run that finishes while Overview is displayed can
have its paths table ready before the user switches to Timing.

Full path detail remains lazy. The index already supplies row-level slack, endpoints,
corner and reported status. Enter/explicit inspection activates exact selected-detail
demand and the existing bounded neighbor policy; a cold full-detail read can still
take several seconds with the current provider.

### Loading policy controls

| Control | Effect |
| --- | --- |
| Palette `Timing preload: Background index` | Enable and persist project loading policy; default |
| Palette `Timing preload: Explicit only` | Suppress speculative reads and persist that choice |
| Client `--timing-preload background-index` | Initial override of the saved policy |
| Client `--timing-preload explicit-only` | Initial explicit-only override |

CLI policy wins initially; subsequent palette changes take effect and persist.
Explicit-only can still display already-published evidence and permits ordinary
explicit inspection. It does not purge cached data.

### Bounds and correctness

- One speculative index request at a time, reserved until daemon publication/failure,
  not merely HTTP acknowledgement. Matching explicit Inspect joins it without a
  second refresh. Interactive inspection has priority before the next speculative read.
- Exact run/stage/analysis/source and connection/project identities fence attachment.
  Advancing the mutable execution record does not invalidate an unchanged frozen
  Timing source. Selection/source changes cannot attach obsolete data to the new view.
- Each daemon/project scope remembers at most **128 attempted exact sources**.
  Failures are not repeatedly retried by polling or evicted into retry loops. At the
  cap, further inspection remains explicitly available; a new client or daemon/project
  scope resets that budget.
- Loading, ready, empty, filtered, failure and cached-unverified states remain distinct.
  Explicit Inspect/refresh can retry a failed background load.
- Existing caches remain bounded: persistent indexes (eight per project, each at most
  4,096 rows / 2 MiB), memory-only reusable details (default 64 entries / 4 MiB), and
  client-memory projections. Warm-up does not add a persistent cache of rendered frames.

## Real-run evidence

Actual retained run `a02325d9895a428aa7b90734314e4e4a` was verified through a private
daemon/client using the installed provider and real report source:

- **1,021 index rows:** 1,020 timing paths and one input-reference row.
- **Exactly one provider index read**, **zero detail reads** during hidden warm-up.
- Overview stayed active; workspace/context/pin registry remained unchanged.
- Switching to Timing and viewing provenance issued **no additional index/detail reads**.
- Display showed `0.125 ns`, shortened `a023…4e4a`, equal-width columns and the
  built-in four-tab order.

Observed wait for hidden publication was **8.03 seconds**. Switch command plus capture
took **2.18 seconds including deliberate PTY interaction delays**; this is not a
rendering benchmark. Earlier cold provider measurements were approximately 7.5 seconds
for an index and 7.6 seconds for a detail, which is why detail preloading remains bounded
and lazy. No physical EDA run was performed.

## Verification and receipts

- Full Workbench `dune build -j 1 @all @lint` and `dune runtest -j 1`: passed.
- Changed OCaml files pass the configured formatter; `git diff --check` passes.
  Unrelated global waveform/hydration formatting baseline remains separate.
- Presentation tests cover precision 0–9, negative near-zero, exact sort values,
  compression/full text, schema migration/restart, semantic ANSI roles and narrow layouts.
- Built-in navigation, repeated source replacement, pin conflicts, explicit separate/
  close and legacy Signoff acceptance:
  `/tmp/opencode/b-navigation-wb069-verified/`,
  `/tmp/opencode/b-navigation-executable/`, `/tmp/opencode/b-navigation-a023/`.
- Default-on warm-up acceptance, 20 assertions plus screenshots:
  `/tmp/opencode/c-preload-native-final/`.
- Explicit-only legacy regression: `/tmp/opencode/c-preload-legacy-explicit-only/`.
- Actual source warm-up and presentation:
  `/tmp/opencode/c-preload-actual-a023-measured/`, with
  `actual-hidden-overview.svg`, `actual-ready-table-session.svg` and
  `actual-full-provenance.svg`.
- Synthetic Testing/flow regressions passed. Full embedded-waveform acceptance was
  blocked by missing pre-reboot retained FIFO VCD fixtures; its changed startup/
  navigation assertions passed with deterministic replay.

After server crashes, recovery preserved partial work and reduced verification from
six jobs to two, then **one job at a time**, with numerical worker limits of one.
Interrupted checks were not counted as passed. No repository staging, commits or
pushes were performed. The [implementation plan](timing_usability_preload_plan.md)
records the agent handoffs and recovery history.

## Updated retained example

The saved tab-order migration used an owned short-lived daemon after confirming no
production daemon remained running after reboot. It applied only revision-checked
reorders, then shut down its own process. Saved revision advanced 179 → 182.
The legacy saved preset references automatically use the new client’s stock layout;
no geometry reset was necessary.

Receipts under `hardcaml_asic_example/.dev/workbench-real-demo/receipts/`:

- `timing-tab-order-8c502a0922b54e95a98d8bd3b76db8c9/`: original workspace-file
  backup, protocol before/after and preservation checks.
- `refresh-binaries-986bfa8c3947499699d5ff3d5af9cc04/`: refreshed daemon, client and
  preset exporter, previous copies and exact hashes.

Start the daemon and client with the [existing demo commands](executable_timing_stage.md#refreshed-example-deployment).
Both binaries changed for this increment; use the refreshed pair. No reseeding or
provider installation is needed. In Overview, select the completed run and allow
index preparation, then switch to the built-in Timing tab.
