# Timing detail cache and duration-column implementation plan

## Goal and policy

Restore aligned status/duration columns in Runs and the stage checklist, removing
redundant Time/Elapsed prefixes there. Establish bounded configurable in-memory
inspection-detail reuse and lazy, selected-first Timing loading. Preserve all existing
work; no staging, commits, pushes or other mutative Git operations. Three implementation
agents may each use `-j4` (12 jobs total); combined checks run serially at `-j4` after
agents finish. No physical EDA run is needed for this work.

## Existing behavior

Indexes already load on demand through bounded L1/L2 caches. Detail publications retain
eight recent entries, but backend requests still query the provider instead of checking
a reusable cache. Cold provider detail reads reparse retained inspection sources.
Increasing the snapshot window alone would retransmit excessive text on every poll.
Timing currently loads an index on explicit open and requests detail only on activation.

## Agent A — duration alignment

Owned files: `terminal/host_view.ml`, `terminal/overview_tiles.ml`,
`terminal/execution_time_view.ml` and focused duration rendering tests.

- Compute shared status and duration column widths across filtered candidate rows,
  not independently for each row. Runs and checklist statuses are left-aligned;
  duration values are right-aligned.
- Remove Time/Elapsed prefixes on these list surfaces only. Retain unknown values;
  lifecycle status distinguishes running from terminal duration. Keep descriptive
  labels in standalone summary/detail views.
- Preserve selection markers, semantic colors, Unicode display-cell accounting,
  filtering and scrolling. Truncate identity/label first; at very small widths omit
  duration consistently rather than shifting individual statuses.
- Cover mixed duration/status lengths, selection and scrolling, icon modes and narrow
  widths. Keep horizontal stage-strip duration labels prefix-free.

## Agent B — reusable backend detail cache

Owned files: `backend/asic_service.ml/.mli`, `backend/service.ml`, `daemon/main.ml`,
backend inspection cache modules/tests/fixtures as necessary.

- Add a successful-detail LRU independent of the existing bounded publication window.
- Configure per-project limits through daemon options:
  `--inspection-detail-cache-entries` (default 64) and
  `--inspection-detail-cache-bytes` (default 4194304). Validate limits; document
  serialized-payload accounting versus actual heap overhead. Zero may disable reuse
  if supported consistently. These are daemon policy, not project identity changes.
- Validate exact current index/run/reference/cursor/execution identity, source digest
  and row before cache use. Hits promote recency and republish without provider reads;
  misses preserve existing hash/digest checks. Cache activity reports lookup versus read.
- Invalidate on source/index replacement, execution/cursor changes and eviction. Never
  reuse failed/cancelled details; explicit retry remains possible.
- Test provider call counts, coalescing, entry/byte eviction, invalidation during held
  reads, retry, publication bounds and config validation.

## Agent C — lazy Timing detail demand and bounded warming

Owned files: `terminal/main.ml`, `terminal/inspection_view.ml`,
`terminal/timing_workspace.ml/.mli`, optional scheduler module and `terminal/dune`.
Avoid Agent A's rendering files; coordinate mechanical test-constructor changes only.

- Explicitly opening Timing activates demand, including when its index is warm.
- Show index endpoint/context metadata immediately, then request selected detail.
- Warm at most two neighboring rows in current filtered/sorted order, one request at
  a time. Prioritize changed selection over unissued speculative work. Do not eagerly
  fetch all rows or queue an entire viewport behind the shared provider lock.
- Provide a client setting to disable/reduce warming (0–2 neighbors); daemon options
  bound reusable cache memory. No new provider work originates from rendering.
- Stop obsolete scheduling on close/workspace/run/stage/source/connection changes;
  preserve existing stale-response fences. Do not cancel shared daemon detail tasks
  merely because one client navigates away.
- Repeated identical polls must not retry failed warming forever. Explicit retry must
  work. Preserve a selected successful detail across unrelated snapshot-window eviction
  only while exact source and row identity remain valid.
- Test selected-first finite scheduling, warm reopen, rapid navigation, stale results,
  error retry, disconnect/source replacement and no repeated polling work.

## Integration and acceptance

Use the existing inspection protocol; no batch endpoint or provider-format change is
required. Main agent reviews cross-agent integration, runs full build/tests/lint and
checks formatting for touched files, documents actual CLI settings, and refreshes
prepared demo binaries without restarting live processes. Keep existing waveform
formatting debt separate. Verify no cache policy change alters ASIC project identity.

Success means repeated exact detail requests avoid provider work, neighboring warmed
details can be selected cheaply, and cache/prefetch memory and request counts stay
bounded. A first cold detail may still require provider parsing; do not promise instant
loading for every row. Live human latency/appearance review remains separate from
fixture-based correctness tests.

## Progress

- Agent A complete: Runs and checklist use shared status/duration columns across
  filtered candidates before paging. Bare durations are right-aligned; very narrow
  lists omit the duration consistently. Descriptive summary/detail labels remain.
- Agent B complete: successful-detail LRU is separate from the eight-publication
  snapshot window, bounded by entries and serialized payload bytes, with lookup/read
  activity distinction and exact-source invalidation.
- Agent C complete: explicit Timing open activates selected-first lazy loading and
  finite neighbor warming. Exact run reference/cursor/execution changes invalidate
  retained detail and demand. A missing acknowledged completion is explicitly retryable
  via Enter/reopen, rather than causing permanent blockage or a polling retry storm.
- Focused rendering, backend call-count/cache, scheduler/lifecycle and CLI validation
  tests pass. After the final audit's two lifecycle corrections, full combined
  `dune build -j4`, `dune runtest -j4`, `dune build -j4 @lint` and `git diff --check`
  all passed.

## Configuration and operating notes

The daemon accepts:

```sh
./scripts/with-switch.sh _build/default/daemon/main.exe \
  --port 8080 \
  --inspection-detail-cache-entries 64 \
  --inspection-detail-cache-bytes 4194304
```

These example flags can be combined with the existing `--state-dir` and
`--discovery-dir` options. Stop the existing owner before reopening the same state
directory. Entry limits are 0–4096; payload-byte limits are 0–268435456. Either limit
set to zero disables reusable detail caching. Limits apply **per project** and count
canonical serialized detail payload, not total OCaml heap usage or RPC envelope bytes.
An oversized detail is still published but is not cached. This is daemon policy and
does not change project identity or run-history namespace.

The terminal accepts:

```sh
./scripts/with-switch.sh _build/default/terminal/main.exe \
  --connect http://127.0.0.1:8080 \
  --project-root /absolute/path/to/project --environment opam:5.2.0+ox \
  --timing-prefetch-neighbors 2
```

Allowed neighbor counts are 0–2; the default is 2. Zero keeps selected-detail lazy
loading but disables speculative neighbor reads. The prepared demo launcher uses
these defaults; custom values are executable options, not currently launcher options.

Opening Timing explicitly loads its index as needed, then its selected detail, then
nearby rows in the current filtered/sorted order. Reopening activates demand even
when the index is already loaded. Selection changes prioritize new demand over
unissued neighbors; an already-running provider read is not preempted or cancelled
because other clients may share it. Closing or changing workspace/run/stage/source
stops obsolete scheduling. Repeated polls do not retry failures indefinitely; Enter
or reopening provides explicit retry.

Successful backend hits avoid provider and filesystem reads while their captured
identity remains current. Refresh/source changes invalidate cached data. A selected
successful detail survives unrelated snapshot-window eviction only while its exact
source, row, reference and cursor remain valid. Cache-only unverified indexes remain
visibly unverified. Cache contents are in-memory and are lost on daemon restart;
existing persistent index caching is unchanged.

This does not preload every path or make every cold read instantaneous. Provider
parsing and the existing per-project inspection queue still bound cold-read latency.
Interactive latency and appearance acceptance remains for the owner.
