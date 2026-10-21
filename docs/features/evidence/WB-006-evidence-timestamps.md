---
id: WB-006
title: Stage/report timestamps and age
category: evidence
feature_sets: [FS1]
status: delivered
kind: enhancement
priority: P2
severity: n/a
requested_size: Ticket
size: M
points: 8
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [timestamps, provenance, freshness]
depends_on: []
related: []
---

# WB-006 — Trustworthy evidence age

## Request
Original size: **Ticket**. Show when stages/reports were produced and how old they
are, without confusing production with Workbench refresh time.

## Current baseline
Inspection indexes retain run/stage, source digests, producer and cache freshness.
Jobs have lifecycle timing, but job timing is not automatically report production time.
FS1 preserves carried-forward and supplementary evidence attribution.
Refreshing old bytes cannot make them newly produced evidence.

## Scope
- Define typed timestamp meanings and provenance for stage/report presentation.
- Show producer-supplied production time when available, alongside separately labeled
  observed/imported/refreshed time where actually recorded.
- Render absolute time and useful age without implying an unsupported precision.
- Preserve unknown timestamps and clock-skew diagnostics.

## Out of scope
Rewriting provider timestamps, using mtime as authoritative production time,
or declaring stale evidence invalid solely because of its age.

## Acceptance criteria
- [x] 1. Refreshing unchanged old evidence changes only the labeled observation/refresh time.
- [x] 2. Missing production time stays unknown rather than borrowing a job completion time.
- [x] 3. Carried-forward evidence retains its original producer/stage attribution and age.
- [x] 4. Absolute timestamps identify timezone; future/skewed values do not show negative age.
- [x] 5. Cached-unverified status remains visible independently of the displayed timestamp.

## Dependencies
Required: delivered evidence provenance and cache states; no additional ticket blocker.
Related: none; activity indication can ship independently of timestamp semantics.

## Estimate rationale
8 points cover a bounded timestamp contract extension and report/stage presentation.
Exclude universal historical reconstruction and changes to every provider's report format.

## Assumptions and decisions needed
Default: unknown production time is acceptable and explicit.
TBD: first authoritative producer fields and whether filesystem mtime is useful only
as a clearly labeled observation; it must never masquerade as production evidence.

## References
- [Inspection index](../../../protocol/asic_inspection.ml)
- [Existing evidence service](../../../backend/asic_inspection.ml)
- [Attribution/freshness contract](../../fs1_investigation.md)

## Follow-up resolution — 2026-10-20

**Human-review status — 2026-10-21:** clock/timing evidence timestamp review is blocked
by failed signoff and absent published reports in the current run. Implementation
remains delivered, but successful report-view acceptance is not claimed. The owner
accepted Testing behavior, including its separately implemented execution-duration
surface; execution duration is distinct from this ticket's evidence-age semantics.


**Code fixes delivered and automatically verified.** Producer parsing checks the
nanosecond parser's result against the wider time representation to reject wraparound,
while retaining accepted nanosecond precision. Age arithmetic widens epoch values to
Int64 before subtraction. Regression tests cover representable endpoints, one
nanosecond beyond either endpoint, equivalent offsets and offset crossings, 1700/2200
inputs, 1850 versus 2026, the full valid range, and the 60-second skew threshold.
Tests also assert production/validation/filesystem metadata across cache/service
restart and clock-only minute changes invalidating memoized ages.

**Wire compatibility:** native ASIC requests send
`X-Workbench-Asic-Evidence-Metadata: 1`. The daemon includes `times` and `activity`
only for that exact negotiated value; absent/empty/unsupported values omit those
fields at serialization, preserving stored metadata. Protocol version and request
bodies are unchanged. Frozen legacy-decoder tests cover populated responses, and a
loopback native-client test covers the optional header with a legacy-style response.
Old servers can ignore the optional header; new readers default absent metadata.

Full combined `dune build -j4`, `dune runtest -j4` and `dune build -j4 @lint` passed.
Scoped formatting checks passed; repository formatting still has the three previously
recorded waveform files. Interactive visual acceptance remains outstanding. Actual
production times still require provider-supplied metadata; unknown remains correct
when none is supplied. The earlier review findings below are resolved.

## Initial completion review — 2026-10-20 (resolved by follow-up)

**Review-time verdict: partial; completion sign-off withheld.** Independent combined-tree build, tests and
lint passed. Production/observation separation is implemented, but static review found
two timestamp correctness issues requiring executable boundary regressions:

- **P2: unchecked timestamp representability.**
  `backend/asic_inspection.ml:production_time` treats successful
  `Time_ns.of_string_with_utc_offset` parsing as sufficient validation. Bounded integer
  arithmetic can wrap out-of-range dates instead of raising. Validate representability
  and reject values that cannot faithfully retain the producer's instant; include a
  date such as `2200-01-01T00:00:00Z` and offset/boundary cases.
- **P2: unchecked age subtraction.** `terminal/evidence_time_view.ml:age` subtracts
  timestamps into a bounded span. Two valid timestamps can have an unrepresentable
  difference, causing old evidence to appear future-dated. Use overflow-safe ordering
  and duration arithmetic; include an 1850 timestamp with a 2026 test clock.
- **Compatibility follow-up:** nonempty `times` and `activity` fields are emitted
  under the existing protocol version. New-reader/old-record tests do not prove that
  old clients accept new records. Establish and test the supported mixed-version
  policy or negotiate compatible serialization. The activity field is shared with
  WB-003.

The arithmetic scenarios above were identified from source review, not reproduced by
a runtime probe in this review. Additional coverage should assert timestamp retention
across cache restart and minute-driven age refresh without metadata changes. Real
producer timestamps remain unavailable until the provider supplies `production_times`;
unknown is the correct current display. Interactive visual acceptance is outstanding.

## Initial implementation notes
- **Typed meanings (`protocol/evidence_time.ml`):**
  `Production.t = Unknown | Supplied of {at} | Rejected of {raw; reason}` and
  `Observation.t = Workbench_validated of {at} | File_modified of {at; path}`.
  `Asic_inspection.Index.times : Evidence_time.Index.t` holds production keyed by the
  exact row producer attribution plus Workbench observations. The field is
  sexp-optional and omitted when empty, so existing L2 inspection caches keep their
  content digests and reopen unchanged. `cached_unverified` stays a separate flag.
- **Producer field (decision: first authoritative field):** the inspection envelope may
  carry an optional `production_times: [{"producer": <row producer>, "produced_at":
  <RFC 3339 with Z or ±HH:MM>}]` (≤256, unique producers). A zone-less, oversized or
  unparseable value is kept as `Rejected` (bounded to 128 bytes) and rendered as
  unknown with the reason; it is never reinterpreted in a local zone. The current
  `hardcaml_asic` provider supplies no production time, so real evidence shows
  `produced unknown` everywhere. No provider, job lifecycle, refresh or cache time is
  ever substituted.
- **Observations actually recorded:** the daemon stamps `Workbench_validated` when a
  bounded provider read validates an index (explicit refresh or cold read), and records
  the registered execution record's filesystem mtime as `File_modified` (decision:
  mtime is shown only as an observation, labelled "filesystem mtime …, not
  production"). Both persist in the L2 cache, so after a restart the index shows
  `CACHED UNVERIFIED` together with its last validation age. Refreshing unchanged bytes
  replaces only the validation time.
- **Presentation (`terminal/evidence_time_view.ml`):** absolute times are UTC to the
  minute with an explicit `UTC` suffix; ages are coarse (`<1m`, `3m`, `2h 5m`, `30h`,
  `9d`, `2y`). A time more than 60 s ahead of the client clock renders `FUTURE +15m:
  clock skew?`, never a negative age; up to 60 s ahead renders `just now`.
  - Inspector list header: `N rows [CACHED UNVERIFIED] · produced <age|unknown|k/n
    producers known> · validated <age>`.
  - Inspector `d`/detail metadata and the Timing **Context** pane: one
    `Produced (<producer>): … · producer-reported` line per producer,
    `Validated by Workbench: … · provider read/refresh time, not production`, and the
    observed file modification line; the selected row shows `Produced: … · by
    <its own producer>`, so carried-forward rows keep their producer's time and age.
    Memoized detail lines are rebuilt when the times or the minute change.
  - Run summaries (Overview/stage detail/synthesis page) replace the bare
    `Observed at:` string with `Produced: unknown · not supplied by the producer` and
    `Observed by Workbench: <UTC> · read time, not production`.
- **Out of scope / not done:** no "imported" time is recorded anywhere today, so none is
  shown; `Asic.Summary.observed_at` remains the existing string (now parsed for
  display), not migrated to the typed record; Paths header in the Timing workspace keeps
  its existing status line (ages are in Context).
- **Tests:** `terminal/evidence_time_view.ml` (expect tests: UTC/absolute, coarse ages,
  future skew, unknown never borrowing other times, carry-forward, refresh moving only
  validation), `terminal/timing_workspace.ml` (criteria 1–5 through the inspector and
  Timing Context renderers, memo rebuild), `backend/test/inspection/test_inspection.ml`
  (production parsing incl. offsets/zone-less/garbage/duplicates; daemon refresh of
  unchanged bytes changes only the validation time and keeps production unknown),
  `protocol/test/test_asic_inspection.ml` (round trip, empty times omitted from sexp).
- **Verification:** same commands as WB-003 (build, `dune runtest`, `@lint` pass; `@fmt`
  only the pre-existing waveform files; overview-sidebar, frontend-composition,
  real-example-polish pass; indicators/refinement stop only at their known failures).
