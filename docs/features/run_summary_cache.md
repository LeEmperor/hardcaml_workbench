# F11 — Tiered run-summary caching and fast switching

Status (2026-10-16): **FS0 bounded summary L1/L2 and FS1 bounded inspection caches,
coalesced reads, observation invalidation and explicit Refresh implemented**.
[Provider integration](../fs0_provider_integration.md)
defines numerical budgets/freshness. [Acceptance](../fs0_acceptance.md) proves fixture
report calls 2→2 and exact real warm/restart identities with `Cached_unverified`.
Requirements below remain normative: no cheap provider revision query exists,
ordinary switching is not perpetual validation, and performance/size benchmarks
remain open. [FS1 investigation](../fs1_investigation.md#bounds-caches-and-responsiveness)
proves provider-free warm/restart inspection and local browsing; local input now
invalidates the view immediately while domain delivery remains polled. The owner
confirms Escape works. Canonical evidence and retention remain provider-owned.

## User outcome

Switch Main from R1 (50 cells) to R2 (73 cells) and following synthesis tiles show
R2's value without repeatedly parsing its entire result entry. Previously loaded,
unchanged runs switch using cached summaries; cold results arrive asynchronously.
Pinned references and independent contexts keep their own evidence scope.

Cache normalized domain data, not terminal rows, tile geometry or rendered frames.
One synthesis summary serves an overview count, cell breakdown and other clients.
F12 appearance changes reuse these same entries: color, icons, skin and density
are not domain cache keys. Explicitly requesting additional detail may query its
own data, but merely repainting/restyling available facts must not refetch them.

## Storage layers and ownership

| Layer | Contents / owner | Lifetime |
| --- | --- | --- |
| L1: daemon memory | Decoded typed summaries shared by modules/views | Bounded hot working set |
| L2: persistent Workbench cache | Versioned normalized summaries and lookup metadata | Rebuildable, bounded disk store |
| Canonical provider evidence | Original results/reports/observations behind public provider interfaces | Provider/project-owned source of truth |

The canonical store (for example `_flow_results/`) is not an expendable L3 cache.
Workbench must not write its derived summaries into canonical run records or delete
provider evidence during eviction. L1/L2 can be discarded and rebuilt from available
source evidence. Generic test-history persistence is a separate F09 requirement;
a summary cache does not establish durable records for daemon-memory-only jobs.

Implemented L2 lives in the daemon's configured Workbench state directory, checked
to be outside canonical provider results. `backend/asic_service.ml` writes
`asic-<identity-digest>.sexp` for the registry and
`asic-<identity-digest>-summary-v1-<report-digest-hash>.summary.sexp` for normalized
summary blobs. The namespace includes project root, selected environment and complete
ASIC configuration. Summary blobs write schema v4 and read v1–v4; the filename's
v1 is not the blob schema. Same-directory temporary files and atomic rename publish
entries; this is a single-writer store, not an fsync-backed archive.

Summary L1 retains **32** entries; L2 indexes up to **128** runs, with **256 KiB**
per summary and **4096** cell types (at most **32 MiB** indexed summary payload).
Run registrations and launch reservations are each bounded to **256**.
FS1 inspection uses `asic-<identity-digest>-inspections-v1.sexp`: **8 L1 indexes**,
**8 L1 details**, and **8 L2 indexes**, each index at most **4096 rows / 2 MiB**.
The aggregate L2 inspection file bound is **8 × 2 MiB + 64 KiB**; detail text is
bounded separately to **64 KiB** and fetched on demand. These are derived domain
caches, not per-tile copies or immutable evidence retention.

## Summary identity and freshness

A conceptual cache key includes:

- Stable project/provider identity, distinguishing different result stores as needed.
- Provider run identity and specific result/observation identity or source revision.
- Query kind/parameters, including stage/corner/mode where relevant.
- Adapter and normalized-schema version.

Workspace/window/context IDs are delivery state, not part of domain cache identity.
Independent contexts inspecting the same evidence share the same cached summary.
Keep a small current-observation index for each run/query separate from entries for
specific observations; advancing a live run must not rewrite an older result's identity.

Each entry retains producer stage, measurement context/units, source references,
source revision/digest and observation/validation times as available. Carried-forward
metrics keep their actual producer context. A completed run may acquire new collection
or postcheck revisions; completion does not permanently validate every cache entry.

Use provider revisions/immutable identities to refresh the affected entries/index.
If these are absent, define and test an explicit adapter validation strategy, such
as a supported digest or refresh policy. Never claim freshness solely from run ID,
directory order or completion. Publish only complete validated normalized entries.
An obsolete fetch must not regress the current-observation index when it finishes.

## Read and selection path

1. Change context selection/revision once. Tiles immediately adopt the new label
   and display matching available data or an explicit loading/unavailable state.
2. On L1 hit, return the typed summary without a provider read or report parse.
3. On L1 miss/L2 hit, load the small entry asynchronously and populate L1.
4. On cold miss or invalidation, join/start one bounded provider read through F02,
   normalize once, publish the entry and notify interested subscribers.

Provider access goes through F01, not tile-specific parsing of `_flow_results/`.
Separate any lightweight freshness validation from expensive report materialization.
No selection/cache miss implicitly launches EDA or new expensive analysis.

Implemented L2 data reopens with **cached/unverified** status; ordinary switching
or inspection browsing does not start automatic source validation. Explicit Refresh
is required for current validation. Distinguish validated current evidence,
validation pending, source
unavailable, and refresh failure. A failed refresh must not silently bless old data.
Missing canonical evidence remains explicit even if a cached summary is retained.
Long-term retention/export of orphaned evidence remains D3 policy; a cache hit does
not make an immutable snapshot or guarantee archival preservation.

Late replies may populate their correctly keyed cache entry but cannot update a
tile bound to a different run/context revision. Do not cancel fetches needed by
other subscribers/pinned views, and never cancel execution on cache eviction.

## Bounded retention and detail

- Use byte/entry budgets plus recency. The last 3–5 runs is a useful workload to
  measure, not a promise to retain arbitrarily large datasets for five runs.
- Prioritize small summaries used by visible/selected and pinned views, then recent
  runs. Bound active working sets as well as inactive caches; visible data is not
  permission to load an unbounded report.
- Keep cheap counts/slacks/check summaries separate from large timing-path pages,
  traces, raw reports and physical artifacts. Paginate detail and bound it separately.
- Coalesce concurrent equivalent misses. Multiple tiles/windows do not multiply
  provider queries or normalized copies of the same observation.
- Eviction releases derived entries only, without changing run selection/pins or
  provider retention. A view reference does not guarantee every detail stays resident.
- L2 readers reject partial/corrupt/incompatible entries and rebuild safely. Publish
  complete entries atomically; version and document ownership if multiple daemons
  can access the same cache. Cache failure must not alter provider truth or falsely
  mark an otherwise successful flow failed.
- Optional adjacent-run prefetch and more elaborate eviction/indexing follow measured
  need; prioritize requested reads and avoid speculative work flooding the provider.

## FS0 acceptance

1. Load distinct R1/R2 summaries, then switch R1 → R2 → R1 while unchanged and
   resident: correct values, no additional summary materialization/report queries.
   Account separately for any necessary lightweight freshness checks/live observation.
2. Multiple tiles/contexts requesting the same entry share one cold fetch; changing
   layout or repainting causes no provider access.
3. A later source revision refreshes the affected summary/index. Other run entries
   and exact older observations remain distinct; delayed older reads cannot roll back
   newer state or display an old value under the new selected-run label.
4. Restart and load from L2 without re-materializing unchanged large reports. Validate
   source identity/freshness separately; pending/unavailable validation is visible.
5. Exercise eviction, schema/adapter-version change, corrupt/partial entries and
   missing source records. Rebuild where possible, preserve correct labels and verify
   canonical evidence is untouched.
6. Measure cold/L1/L2 switching, query counts and memory/disk working-set sizes with
   representative summaries before committing to a millisecond target.

Dependencies: F01 source identities/queries; F02 asynchronous coordination; F05
evidence semantics; F10 context invalidation. F06/F09 modules consume the cache where
their data has genuine stable evidence identity. The construction plan owns checkboxes.
