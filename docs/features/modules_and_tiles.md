# F02 — Providers, modules and tiles

Status (2026-10-15): **FS0 execution boundary, daemon ASIC service and tile host
delivered**. See [Execution](../fs0_execution_module.md), [terminal](../fs0_terminal.md)
and the [plan](../construction_phase_plan.md) for implementation/evidence and gaps.
Requirements below remain normative; fully reactive publication/redraw and measured
high-tile-count scaling remain followups (current redraw is clock-driven).

## Ownership

| Element | Owns |
| --- | --- |
| Provider adapter | External protocol translation, capability discovery and supported operations |
| Feature module | Typed semantic state, shared projections, queries, revisions and commands |
| Tile | Rendering, filters, expanded nodes, selection and scrolling local to that view |
| Host/session state | Tile identity, geometry, input routing, focus, workspace bindings and shared run contexts |

Modules expose structured domain values, not preformatted terminal rows. A module
can serve several tiles; a composite summary tile can consume several modules.
Stage-oriented presentation does not require one module per execution stage:
timing measured after synthesis and routing belongs to one contextual timing model.

“Simulation tile” or “synthesis tile” can name a user-facing feature in discussion;
specifications distinguish its module (semantic model/actions) from its tile(s)
(views). The simulation/test module starts with a generic runner (F09). Run-selector
tiles are controllers/views over shared run contexts (F10), not owners of ASIC data.

F12 adds frontend theme/component/layout boundaries and mountable utility tiles.
Module facts retain units, severity/verdict, availability and evidence references;
they do not encode colors, candidate styles, header/tab geometry or icon glyphs.
Utility tiles can consume host/session state instead of an EDA feature module.

## Requirements

- Reuse the existing supervisor, transport, artifact handling and event reducers.
- Share published data and expensive extraction across consumers.
- Use bounded snapshots/updates and paginated detail queries; keep run/query/revision
  identity on responses and reject stale arrivals after context changes.
- Subscription or rendering does not start a tool. Explicit commands own expensive
  work and return operation/job identity.
- Hidden or closed views do not stop execution. Reader lifetime and execution
  lifetime are separate.
- Two timing explorers have independent filters/selection over shared report data.
- Linked run selectors share only context selection, not focus/filter/scroll.
  Context changes are revisioned session transitions, separate from provider updates.
- Static typed assembly is sufficient initially; dynamic plugins are not required.

## First demonstration

### Asynchronous access and fan-out

The daemon hosts feature modules and the provider adapter. Tiles subscribe/query
through the Workbench application API; they never spawn provider executables or
parse raw provider reports. This extends the existing Async daemon/HTTP boundary;
it does not require a process per module or tile.

```text
Tile instances (possibly in several windows)
  → typed Workbench queries/subscriptions
  → daemon modules + shared cache/in-flight request coordination
  → provider adapter → installed public read/watch commands
  ← typed results/updates → relevant subscriptions → reactive rendering
```

- A render is a pure view of currently available state. A subscription/query may
  trigger bounded provider reads on a cache miss; it must not launch implementation
  or expensive new analysis. Read-only CLI processes are distinct from EDA jobs.
- Cache/share requests by project/provider, run, query arguments, source revision
  and adapter/schema version. Context IDs govern delivery, not duplicate data caches.
  Equivalent in-flight queries join one fetch rather than starting one per tile.
- One aggregate provider report may feed several module projections. Different
  queries may execute concurrently, subject to bounded adapter/provider limits and
  consistency guarantees. Do not serialize every read behind a long physical job,
  and do not launch an unbounded subprocess per tile.
- Coordinate readers for the same observation stream. A provider watch process or
  bounded polling loop can update shared daemon state for many subscribers. Use the
  supported public interface; no assumption of a multiplexed provider RPC server.
- On run switch, change context once, render loading/available state immediately,
  and prioritize visible summaries before optional detail. Publish each compatible
  result as it arrives; no all-tiles-ready barrier. Pinned tiles retain their scope.
- Superseded responses may populate their correctly keyed cache but never the new
  context's views. Release obsolete interest; cancel only unneeded read requests
  where safe. Never cancel a shared fetch still needed elsewhere or a physical job
  merely because a workspace switched runs.
- Bound page sizes, response bytes, queued work and cache retention. Batch high-rate
  events and avoid synchronous large parsing/file reads on the UI event loop.
- Async concurrency is not a promise of CPU parallelism. Profile expensive decoding
  and isolate it when needed; initial modules remain statically assembled.

The concrete limits and read scheduling are implementation choices to measure in
FS0. Separate execution admission (existing per-root job queues) from safe concurrent
read/observation scheduling; provider locking rules still govern conflicting actions.

[F11](run_summary_cache.md) specifies the cache layers: L1 decoded module summaries,
L2 persistent normalized data, then canonical provider evidence on a cold/invalid
entry. Cache semantic data once, not rows/frames per tile. Separate small summaries
from paginated detail; context identity controls delivery rather than cache duplication.

### Acceptance

Extract execution/log access, then one ASIC synthesis projection. Render two views
of shared information, move/hide one and verify no new execution or duplicate
extraction occurs. Keep pure module tests and real frontend interaction tests.
Exercise many tile subscribers over a few shared fixture queries: assert fetch
deduplication, bounded concurrency, partial arrival, one-reader fan-out and continued
input responsiveness. Test A→B→A switches with delayed replies and pinned consumers;
verify unsubscribe does not cancel shared work or execution. Record provider-call
counts before/after a warm-cache switch rather than assuming one call per tile.

Ches is a reference for host/input/lifecycle design. Shared runtime packages are a
later choice, not a prerequisite. Major/minor roles, if retained, are layout policy
rather than domain or interaction restrictions.

Dependencies: F01 feeds modules; F04 hosts tiles; F05 defines evidence bindings;
F10 owns shared-selection semantics. F09 reuses execution for simulation/testing.
F12 presents the same contracts under several skins; it adds no per-style provider.
