# Timing workspace: actual-run diagnosis and loading policy

The recommended warm-up policy below was subsequently authorized and implemented.
See [Timing usability and preloading](timing_workspace_usability.md) for current
defaults, settings, built-in workspace navigation and completed actual-run verification.
The following diagnosis/cache research is retained as the baseline for that work.

## Delivered fixes — 2026-10-23

### Unwanted simulation catalog

The stock Timing workspace already excludes `simulation-catalog`. The real demo's
saved layout had an extra visible catalog (`tile-38`, `workspace-4`). The requested
live mutation hid only that tile using the existing workspace protocol:

```text
(Set_tile_hidden (tile tile-38) (hidden true))
```

Revision advanced 175 → 176. Testing's catalog (`tile-50`) remained visible; all other
tiles, workspaces and contexts were checked unchanged. This is persistent removal
from visible membership, retaining the saved tile record. No whole-layout reset or
blanket migration of custom workspaces was performed. Added tests verify stock Timing
and exported Timing templates exclude the catalog while Testing retains it.

Mutation receipt: `/tmp/opencode/timing-followup-layout.json`.

### Why `a023` showed no timing paths

Exact attempt: `a02325d9895a428aa7b90734314e4e4a`, selection
`standard / balanced / timing`, completed at observation cursor 22.

```text
/home/wayne/devel/jane/hardcaml_asic_example/.dev/workbench-real-demo/results/
  timing-817177-2eeaceb51e3413c008ecd50516122412/
  execution-a02325d9895a428aa7b90734314e4e4a.json
```

The run completed six requested stages through Timing under recipe schema 4; Signoff
was not requested. Timing segment duration was **18.068718s**, native STA runtime
**1.557s**. Its three corners have six max/min reports with 170 paths each:
**1,020 timing paths**, plus one input-reference index row. All declared producer
file hashes matched the analysis inventory.

The generic palette and some contextual inspection commands still hardcoded
`domain=timing, stage=signoff`. The provider correctly returned zero rows with
`missing published checkpoint for stage signoff`. The daemon persisted this empty
Signoff index even though its summary cache contained the correct Timing analysis.
This was a frontend routing error, not a missing report, lost summary, or provider
failure. Overview's captured-analysis action already used the correct source.

The fix resolves the selected run's published analysis target, including its stage,
attempt, digest and immutable execution source. If no analysis is available, it uses
that run's observed stage set—Timing for new seven-stage executions, Signoff for
historical six-stage executions—not the current provider catalog. Both generic
palette and contextual actions now use this resolution. Historical inspection and
captured-source fencing remain supported.

Empty states now distinguish an index not loaded, a genuinely empty provider index
with its stage/diagnostic, a filter hiding loaded rows, and an error.

Private native HTTP/PTY verification opened the **actual retained run** through the
generic command and displayed 1,021 index rows (1,020 paths plus input reference),
with source stage Timing and exact frozen source. No physical rerun was performed.

Identities:

```text
analysis: 446a38ceacca9e53f6d457deaa0d8c27b73525ef20319f9302c9ba73ff82190b
index:    5c7b15a8b83882befbdbefed2c36db44e56fe0a3ebd1ff433d83f4239f65a10f
```

## Current loading and cache behavior

Timing supports caching, but **completion does not currently load its path index**.

| Layer/event | Current behavior |
| --- | --- |
| Owned run completion | Reconciles execution and materializes Overview/run summaries, including timing-analysis metadata; no index/detail inspection |
| Ordinary ASIC `Get` | Returns published state; does not fetch provider indexes or reopen inspection L2 |
| Explicit Inspect | Reuses matching L1/L2 index or reads the provider; activates selected-detail demand |
| Merely switch to Timing | Attaches matching already-published evidence; activation alone does not request missing index/detail |
| Hidden Timing workspace | Can reconcile published evidence and retain searchable/filter/sort projections; does not initiate provider reads or draw |
| Active inspection navigation | Selected detail first, then a finite 0–2 total neighbors (default 2); obsolete demand stops when inactive |

### Cache layers

- **Index:** bounded daemon L1 and persistent L2, up to eight inspection indexes per
  project; each at most 4,096 rows / 2 MiB. L2 reopening publishes cached-unverified
  evidence without a provider read. Explicit refresh validates the source.
- **Detail:** reusable daemon-memory LRU defaults to 64 entries / 4 MiB serialized
  payload per project, plus an eight-detail published snapshot window. No persistent
  detail cache; daemon restart loses this reuse. Detail text is bounded to 64 KiB.
- **Client transformations:** searchable projection and filtered/sorted rows are
  memoized in memory. Navigation intent persists, including run/stage/analysis/source,
  filter and selected row; transformed rows and rendered terminal frames do not.
- **Rendering:** active, visible tiles are drawn. Hidden-workspace data preparation
  does not require off-screen terminal rendering or repeated image generation.

Overview already materializes normalized summaries at completion. Testing has durable
attempt/result history but lazily hydrates selected detail. Waveforms persist
selection/pins/preferences, not parsed traces: active loading fetches/verifies/parses
the artifact; up to four parsed workspace models may remain resident, and restart
or eviction requires reading/parsing again. None implies eager loading of all reports.

Key implementation locations: `backend/asic_service.ml` (completion observer,
materialization, `Get`, inspection scheduling), `backend/asic_inspection.ml` (bounded
index persistence), `backend/inspection_detail_cache.ml` (detail LRU),
`terminal/inspection_view.ml` (projections/filter/sort), `terminal/timing_workspace.ml`
(passive attachment/presentation), `terminal/timing_demand.ml` (finite detail demand),
and `terminal/main.ml` (all-workspace reconciliation and active demand guards).

## Measurements from the actual run

These are individual cold **provider command wall times**, not UI render benchmarks
or guarantees. They include validation/parsing and can vary with machine state.

| Public query | Response | Measured time |
| --- | --- | --- |
| Report | 2,580,746 bytes | 10.51s |
| Timing index | 1,703,813 bytes; 1,021 rows, untruncated | 7.54s |
| Exact-pinned Timing index | Identical bytes | 7.58s |
| Exact-pinned selected path detail | 5,314 bytes, untruncated | 7.59s |
| Wrong Signoff index | 664 bytes; zero rows and diagnostic | 7.13s |

This establishes a meaningful cost to provider reads; it does **not** establish that
filtering/sorting or drawing 1,020 rows takes that time. Client rendering cost and heap
footprint were not benchmarked. Warming every path detail is unjustified by this data.

Timing inspection publication is serialized per project despite the broader query
throttle allowing four jobs. An unnecessary detail read can delay interactive work;
background scheduling needs priority/budget rules, not unbounded fan-out.

## Recommended policy — for owner agreement, not implemented

**Warm the index for the run a Timing workspace follows when a completed analysis
becomes available; keep full detail lazy.** This can happen after Timing finishes,
even if a full run is still doing Signoff. Prepare the data model, not hidden frames.

Proposed behavior:

1. Capture the exact selected/followed run and analysis source. Respect pins and
   independent contexts; never switch to the newest run just to preload it.
2. Once per new source, queue a coalesced, bounded, low-priority index read or
   cache reopen. Do not warm every historical run. Start with one background read
   at a time; interactive requests should take priority before the next read starts.
3. Let hidden workspace reconciliation prepare searchable/filter/sort state from
   the published index. This makes the path table ready without off-screen drawing.
4. Fetch exact provider detail when the user opens/selects a path. An optional
   single selected-detail warm-up can be considered later; do not eagerly load all
   details or automatically fan out hidden neighbor requests.
5. Keep an explicit-only option and visible not-loaded/loading/ready/empty/error,
   truncation and cached-unverified states. Source/run changes invalidate obsolete
   intent; no repeated polling retries or workspace/pin mutation.

An index-only warm-up makes the **table** ready, including its row-level slack,
corner and endpoints; the first full provider detail may still incur a cold read.
If instant first-detail display is important too, that is a separate bounded
warm-up choice. Persistent detail reuse or cheaper provider validation deserves
measurement before increasing speculative reads.

The present fix deliberately leaves this policy unchanged pending discussion.

## Verification and deployment

- Full `dune build -j 20 @all @lint` and `dune runtest -j 20` passed.
- Changed OCaml files pass configured `ocamlformat --check`; global `@fmt` retains
  pre-existing unrelated waveform/hydration/workspace CLI differences.
- Actual run provider receipts/counts/timings:
  `/tmp/opencode/timing-followup-backend-evidence/`.
- Actual run private native UI (generic palette, populated table and exact target):
  `/tmp/opencode/timing-followup-ui-real/`.
- Timing-only generic palette/Overview/restart regression:
  `/tmp/opencode/timing-followup-ui-pty-2/`.
- Historical Signoff generic palette/exact-source regression:
  `/tmp/opencode/timing-followup-ui-legacy-pty/`.
- Live saved-layout mutation: `/tmp/opencode/timing-followup-layout.json`.

Retained real-demo binaries were refreshed through the supported receipt-backed
workflow. Receipt under `hardcaml_asic_example/.dev/workbench-real-demo/receipts/`:
`refresh-binaries-54ade3e08ab54997baa5adcddb18ca14`.
Only the client hash changed; daemon and preset exporter match their prior bytes.
**Restart the client only**, then invoke **Inspect timing paths … a023… · timing**
again. Existing exact investigations are not silently retargeted, so this may open
a separate captured Timing investigation from the old empty Signoff view. No daemon
restart, reseeding, provider installation, physical flow, or run-artifact change is
required. The unwanted catalog was already hidden in live saved state.

No repository staging, commits or pushes were performed. Three agents handled UI
implementation, real-run evidence and cache research; total worker budget stayed
within 20. The [follow-up plan](timing_workspace_followup_plan.md) records ownership.
