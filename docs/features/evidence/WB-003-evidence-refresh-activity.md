---
id: WB-003
title: Evidence refresh activity and current-operation status
category: evidence
feature_sets: [FS1, FS5]
status: delivered
kind: enhancement
priority: P1
severity: n/a
requested_size: Ticket
size: S
points: 5
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [refresh, activity, session]
depends_on: []
related: []
---

# WB-003 — Visible evidence refresh activity

## Request
Original size: **Ticket**. Show “Updating Evidence” while evidence is being read;
a Session current-operation line may be the right compact surface.

## Current baseline
ASIC inspection already has explicit refresh, shared in-flight reads and bounded caches.
The terminal has session status, utility projections and native indicator primitives.
Existing icon/spinner delivery is a foundation; this ticket concerns semantic wiring,
not a new animation system or reopening FS1 acceptance.

## Scope
- Project active evidence reads/refreshes into a visible scoped activity state.
- Identify the operation and selected run/domain/stage where space permits.
- Retain old evidence with its honest freshness label while replacement is pending.
- Clear activity on success, error, cancellation or invalidated selection.

## Out of scope
Launching physical flows, treating repaint/polling as refresh, or adding a scheduler.
No invented percentage when the provider supplies no progress total.

## Acceptance criteria
- [x] 1. A deliberately delayed explicit refresh shows activity until its terminal result.
- [x] 2. A cache-only reopen does not display a fictitious provider operation.
- [x] 3. Failure clears activity and preserves a useful error plus prior freshness status.
- [x] 4. A late response cannot restore activity or evidence for an obsolete selection.
- [x] 5. Overlapping reads are summarized without falsely reporting the session idle.

## Dependencies
Required: delivered inspection lifecycle and indicator primitives; no new blocker.
Related: none; artifact production timestamps are independent evidence semantics.

## Estimate rationale
5 points cover activity projection, compact presentation and lifecycle edge cases.
Exclude animation-library work, transport redesign and performance instrumentation.

## Assumptions and decisions needed
Default: indeterminate activity with explicit operation text and accessible static label.
TBD: Session line versus tile-local indicator, and compact wording for concurrent reads.
The indicator must distinguish evidence reading from actual producer execution.

## References
- [Inspection lifecycle](../../../backend/asic_inspection.ml)
- [Utility projections](../../../terminal/overview_tiles.ml)
- [Indicator primitives](../../../terminal/indicator.ml)
- [Inspection cache behavior](../../fs1_investigation.md)

## Follow-up resolution — 2026-10-20

**Human-review status — 2026-10-21:** owner cannot exercise clock/timing inspection
because the current run failed signoff and has no corresponding published evidence.
Live inspection-refresh visual acceptance remains blocked on a usable retained
fixture; this is not a reported UI failure. Implementation remains delivered.


**Code fixes delivered and automatically verified.** Summary refreshes now carry their
run identity and project failures into Session. Cache lookups retain concurrent error
and prior-freshness detail. Inspection transport-error notices use the same
identity/generation/selection fences as the receipt.

`terminal/test/evidence_activity/` exercises a held real backend summary refresh through
the Session renderer, refresh failure with retained evidence, and an overlapping warm
lookup. Deferred receipt tests cover close/reopen, generation, selection, epoch and
notice ordering through the shared production receipt function. Full combined
`dune build -j4`, `dune runtest -j4` and `dune build -j4 @lint` passed after recovery
from the interrupted implementation. The review findings below are historical and
resolved by this follow-up.

Remaining validation is live delayed-provider visual acceptance and end-to-end HTTP
transport-failure injection; the latter is currently covered at the deferred receipt
seam rather than by injecting an actual HTTP failure. Neither is claimed performed.

## Initial completion review — 2026-10-20 (resolved by follow-up)

**Review-time verdict: partial; completion sign-off withheld.** Independent combined-tree build, tests and
lint passed, but code review found production wiring gaps that the current tests miss.
The implementation notes below describe the initial delivery and are qualified by
these open findings:

- **P1: summary refresh activity lacks run identity.** In
  `backend/asic_service.ml`, the `Load_summary | Refresh` branch sets `Evidence_read`
  but leaves the pending operation's run unset. `terminal/evidence_activity.ml`
  requires that run to match the displayed run, so an explicit summary refresh can
  appear idle. The unit fixture supplies a run that the backend does not. Wire the
  identity through and test the actual backend-to-Session projection. Summary-refresh
  failures also need inclusion; the failure projection currently only uses inspector
  operation keys.
- **P2: lookup/failure overlap loses error detail.** `Cache_lookup` takes precedence
  over existing failures and carries no failure payload. Preserve error and prior
  freshness details during a concurrent warm lookup; add coverage for this combination.
- **P2: stale transport errors escape the local fence.** In `terminal/main.ml`, an
  obsolete inspection response is rejected locally, but its transport error can still
  replace the global notice after the inspector closes. Fence that notice with the
  inspector identity/generation and test the real asynchronous callback path.

Delayed-provider live/visual acceptance remains outstanding; the retained FS1 fixtures
needed by the existing scripts were reported absent. This review did not run those
scripts or repeat their baseline comparisons. Reopened criteria require the fixes and
focused regression checks above, not only the existing pure projection tests.

## Initial implementation notes
- **Surface (owner decision):** one `Evidence` row at the end of the Session
  (`live-status`) utility, not per tile. It fits the presets' 7-row Session tiles.
  - one read: `<spinner> updating evidence · timing/signoff` (a single unaligned label,
    so narrow tiles clip the scope and never the activity text);
  - several: `<spinner> updating evidence (N)`;
  - warm lookup only: `Evidence: cache lookup` (no spinner, no provider claim);
  - failure/cancellation: `Evidence: not updated: <daemon error>`;
  - nothing in flight: `Evidence: idle`.
  Expanded Session detail lists every read (`Reading index timing/signoff · run X ·
  read-only evidence read; not flow execution; no progress total reported`) and every
  failure with the prior freshness (`prior evidence kept: CACHED UNVERIFIED`). The
  spinner is the existing native Dot/Line pair; ASCII and Off keep the same static text.
- **Daemon truth, typed (`protocol/asic.ml`):** `Asic.Pending.activity :
  Unreported | Evidence_cache_lookup | Evidence_read` (sexp-optional, dropped when
  `Unreported`). The inspection task reports `Evidence_cache_lookup` for a warm
  `refresh=false` Inspect and switches to `Evidence_read` only when it actually enters
  the bounded provider query (explicit refresh, cold/invalid-cache fallback, or a
  refresh upgrade of an in-flight lookup). Row-detail reads and explicit summary
  `Refresh` report `Evidence_read`; summary loads make no claim. No scheduler, polling
  or request was added; repaint never reads.
- **Scope (`terminal/evidence_activity.ml`):** a pure projection of the latest snapshot.
  An index/detail operation counts only if an open inspector (inspector tile or timing
  workspace, deduplicated) currently wants that exact key; summary refreshes count for
  runs a tile shows. Changing stage/run, or closing the inspector, therefore drops an
  obsolete read; a late index for the old selection is not reconciled into the view
  (existing generation/selection fences). Failures shown are those of the view's own
  `operation_key`, matching the inspector's own `ERROR:` line.
- **Retained evidence:** unchanged behaviour, now asserted: while a refresh is pending
  the daemon keeps the previous index visible and labelled `CACHED UNVERIFIED`.
- **Not covered:** the few milliseconds between issuing an Inspect and receiving its
  prompt snapshot show no activity (no client-side guess is made). Cancellation is shown
  with the daemon's own error text (`Inspection read cancelled`) rather than a
  separately classified state.
- **Owner visual review:** the wording/placement was checked through the real tile
  renderer at 30x7 (`terminal/evidence_session_test.ml`), not in a live PTY against a
  delayed real provider (the retained FS1 evidence used by
  `scripts/test-fs1-investigation.py` / `test-inspector-latency.py` is not present on
  this machine).
- **Tests:** `terminal/evidence_activity.ml` (one test per criterion, plus icon modes),
  `terminal/evidence_session_test.ml` (real Session renderer, scoping, expect capture),
  `backend/test/inspection/test_inspection.ml` (held provider read reports
  `Evidence_read` on every poll and keeps prior evidence unverified; warm reopen reports
  `Evidence_cache_lookup` and makes no provider call), `protocol/test` round trips.
- **Verification:**
  ```sh
  ./scripts/with-switch.sh dune build -j20
  ./scripts/with-switch.sh dune runtest -j20          # pass
  ./scripts/with-switch.sh dune build @lint           # pass
  ./scripts/with-switch.sh dune build @fmt            # only pre-existing waveform_* diffs
  python3 -B scripts/test-overview-sidebar.py --daemon D --client C --preset-export E      # PASS
  python3 -B scripts/test-frontend-composition.py --daemon D --client C --preset-export E  # PASS
  python3 -B scripts/test-real-example-polish.py --daemon D --client C --preset-export E   # PASS
  python3 -B scripts/test-real-asic-binary-refresh.py                                       # OK
  python3 -B scripts/test-terminal-indicators.py ...   # first failure is the known cooperative-testing-default
  python3 -B scripts/test-frontend-refinement.py ...   # first failure is the known refinement-overview-final
  ```
