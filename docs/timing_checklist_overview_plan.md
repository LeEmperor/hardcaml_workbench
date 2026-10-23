# WB-069 — Timing checklist and Overview implementation plan

This records the completed original supplementary-analysis increment. The owner's
subsequent [executable Timing plan](executable_timing_stage_plan.md) explicitly
supersedes the six-stage/non-runnable restriction for capable new providers.

## Status and scope

**Implementation and automated acceptance complete — 2026-10-21.** The owner
approved proceeding after reviewing this plan. The planning pass performed no source
implementation or tests. [Controls and acceptance](timing_checklist_overview.md)
record delivered behavior, exact verification receipts and remaining limitations.

Delivery decision: use terminal/end-of-segment observations for this increment.
Keep native STA runtime provenance and conservative corner-scoped verdicts; preserve
the six physical execution stages. Provider schema/selector details are owned by
Agent A and handed to Agent B before consumer integration. Agent C starts from B's
typed API. This sequencing avoids speculative incompatible contracts.

Re-estimate: 13 points, medium confidence, reflecting provider recovery and exact
inspection, wire/cache compatibility, two Overview surfaces and regression coverage.
Ownership: A owns the sibling provider; B owns Workbench protocol/backend/transport;
C owns terminal/UI and focused PTY coverage; parent owns documentation/integration.
Each agent is capped at 6 jobs; heavy checks are serialized within an agent and use
isolated build directories where the repository supports them.

Primary ticket: [WB-069](features/evidence/WB-069-timing-checklist-stage.md).
It explicitly requires both surfaces in **Overview**:

1. A separate Timing checklist item after Routing and before Signoff, with its
   own analysis execution status and measured duration.
2. A richer Timing tile for the same analysis, with status/duration, available
   setup/hold metrics, violations/goals, and stage/corner/source context.

The defining acceptance case is **STA completed, later DRC timed out**: Timing
remains completed and inspectable while Signoff is failed. Analysis completion,
timing-constraint verdict, and signoff acceptance are three independent facts.

Related tickets:

- [WB-009](features/evidence/WB-009-timing-coherency.md): preserve distinctions
  between missing evidence, unavailable/import-failed reports and zero filtered
  paths. Its original empty-path report remains undiagnosed; this work does not
  implicitly close it.
- [WB-001](features/presentation/WB-001-checklist-column-alignment.md): retain
  existing aligned status/duration columns and display-cell-aware clipping.
- [WB-004](features/project/WB-004-build-bundle-status.md): coordinate projected
  row order with preparation/elaboration before Synthesis.
- [WB-006](features/evidence/WB-006-evidence-timestamps.md): production and
  observation timestamps remain distinct from execution duration.

The local ticket catalog was available. GitHub CLI issue lookup was blocked by
missing authentication; this plan is based on repository tickets and source review.

## Pre-implementation baseline and implementation seams

### Provider (`../hardcaml_asic`)

- `flow/hardcaml_asic_flow/librelane_bridge.py:execute` writes successful segment
  evidence only after `flow.start` returns. A later failure can leave STA files
  without a published signoff segment/checkpoint.
- `execution/backends/librelane/segment_service.ml:call` records transport
  termination, then raises for unsuccessful transport before consuming segment
  evidence. Host-side collection after transport cleanup is the proposed seam for
  retaining completed STA evidence even after timeout or cancellation.
- Failed backend replies currently require zero artifacts. Do not smuggle partial
  analysis into successful checkpoint publication or unversioned reply changes.
- `execution/results/inspection_service.ml:run` authorizes producer/report access
  through selected published checkpoints. It needs an exact supplementary-analysis
  selector that can work without a signoff checkpoint, retaining existing path,
  digest, metadata and bounded-read validation.
- `stage_report_service.ml` reports accumulated checkpoint metrics;
  `finalization_service.ml` requires successful full execution. Neither supplies
  an independent failed-attempt STA observation today.

Local LibreLane source in `../hardcaml_asic_example/_flow_tools/.venv/` shows
`Step.start` writing validated `state_out.json`, then `runtime.txt`, after successful
step execution. Runtime is wall-clock-derived `HH:MM:SS.mmm`; it is not the Runner's
monotonic stage duration. Validate these semantics against the supported execution
image before making them a provider contract. Directory/report existence alone is
not completion. Output-state metrics are cumulative, so inherited timing keys are
not proof that this producer measured them. Missing/equivalent corners and nonfinite
values require explicit handling.

Research inspected a successful retained example producer; the historical failed
run referenced by older acceptance docs was unavailable at its recorded temporary
path. The failure-path design therefore needs deterministic fixtures and, if
available later, a retained real failed-run specimen.

### Workbench

- `backend/asic_public.ml:canonical_stages` defines six physical stages. Keep that
  list intact. `observation_stages` imports physical occurrences; `summary` leaves
  legacy timing empty; `terminal_result` gets timing from finalization.
- `backend/asic_service.ml:materialize_unlocked`, `load_inspection` and
  `load_inspection_detail` are ingestion/inspection seams. Preserve exact execution,
  cursor and source fencing, bounded reads, and cached-unverified reopening.
- `protocol/asic.ml` and `protocol/asic_inspection.ml` lack a typed supplementary
  analysis observation/selector. Current inspection slots use run/domain/stage.
- `terminal/overview_tiles.ml`, `host_view.ml:utility_rows` and
  `workspace_host.ml:stage_cursor/reconcile_stages/browse_stages` currently project
  physical stages. Display and cursor/action dispatch must share one item list.
- `terminal/overview_summary.ml:rows` supplies the compact Timing tile from
  terminal metrics and defaults stage lookup to `timing`, which is not a canonical
  physical stage. A label-only change or reuse of signoff duration is insufficient.
- `workspace_host.ml:run_context_commands` currently targets timing at signoff;
  `main.ml:open_timing_workspace` captures run/stage, not a specific analysis.
  `inspection_view.ml`, `timing_workspace.ml`, `timing_demand.ml` and navigation
  preferences already fence path details by source and should retain those guarantees.
- `stage_action.ml:resolve` can derive actions from catalog capabilities even with
  `action=None`. A Timing item must bypass physical-stage preparation dispatch.

## Design and contract decisions

### Supplementary analysis, not a seventh execution stage

Use one authoritative post-PNR STA observation, rendered as a stage-like checklist
item and consumed by the Timing tile. It does not advertise a new checkpoint,
launch endpoint, automatic rerun, or stop/resume boundary. Signoff and finalization
retain their separate outcomes and lifecycles.

Recommended first-delivery decision: publish after the enclosing segment ends,
whether it succeeds, fails, times out or is cancelled. While signoff is running and
no authoritative observation exists, show **analysis not yet observed**, not an
invented running/completed status. Live completion reporting during later DRC is
deferred unless explicitly selected before implementation; it needs stable live
identity, atomic observation publication and additional cancellation/race coverage.

The implementation resolved the following contract review items:

1. Terminal-only delivery versus live delivery; terminal-only is this plan's estimate.
2. Versioned provider capability/schema and exact observation persistence/reference.
   Existing strict execution/reply decoders make unversioned extra fields unsafe.
3. Supported native completion grammar and duration source/precision, checked against
   the actual execution image. If monotonic STA duration is required, instrument it.
4. Exact inspection selector and cache-key behavior when a source/attempt changes.
5. Corner coverage and verdict rules, including equivalent or missing corners.

Frozen contract: provider `timing_analysis1`, optional stage-report
`hardcaml-asic.timing-analysis` schema 1, immutable execution sidecar; native
LibreLane 3.1.0.dev3 output/runtime grammar verified in the supported image.
Status is completed or unavailable, distinct from the enclosing outcome and scoped
goal. Missing/equivalent corners cannot earn a pass. Index requests pin the analysis
digest; detail requests pin the returned index digest and retain the analysis target.
Workbench exposes `Summary.timing_analysis`, `Inspect_analysis` and
`Inspect_analysis_detail`, negotiates `X-Workbench-Asic-Timing-Analysis: 1`, and
versions summary/analysis-index caches. See the sibling
[provider contract](../../hardcaml_asic/docs/development/timing-analysis.md).

### Contract requirements

| Area | Required information / invariant |
| --- | --- |
| Identity | Run/attempt, enclosing signoff occurrence, analysis ID, exact backend request and producer occurrence; no newest-directory discovery |
| Execution | Evidence-backed completion/failure/interruption; explicit unknown/unavailable or not-requested only when justified |
| Duration | Optional finite nonnegative measured seconds, source and precision; zero is valid; never use enclosing signoff duration |
| Source | Exact producer class/occurrence, stage, report references/hashes, source digest and bounded validated paths |
| Measurements | Available per-corner setup/hold worst slack and violation counts; optional WNS/TNS when trustworthy, with units and raw source attribution |
| Coverage/verdict | Measured/equivalent/missing corners; reported or explicitly derived scoped verdict; unknown coverage cannot become a pass |
| Context | Enclosing attempt outcome, freshness, and production/observation times separately from duration |
| Inspection | Captured analysis selector and digest for index/detail; changed or missing evidence must not silently select a replacement |

Successful analysis does not imply constraints passed. A bounded path sample cannot
establish full timing closure. Nonfinite/no-path metrics remain unavailable. Completed
analysis and subsequently missing report files remain distinguishable facts.

Publish both Overview surfaces from the same observation. Never combine one attempt's
status with another's duration, finalization slack, or cached inspection index. Old
providers/records must show explicit unsupported/unavailable state without losing
existing physical-stage functionality. Review HTTP field negotiation and serialized
cache versions as well as default-valued decoding.

### UI behavior

- Introduce a typed projected checklist item with stable identity and explicit
  capabilities, rather than manufacturing an `Asic.Stage.t` for Timing.
- Order: preparation/elaboration when present, Synthesis, Floorplan, Placement,
  CTS, Routing, **Timing**, Signoff. Do not add WB-004 scope merely to obtain this order.
- Reuse existing aligned status/time columns, selection, and scrolling. Timing
  `Enter`/inspect opens exact evidence; `r` cannot prepare or execute anything.
- In the compact Timing tile prioritize status and duration, then available slack/
  verdict and concise source context. Details carry full provenance and enclosing
  failure attribution. Test width and height separately: the stock tile has minimum
  height 5 and the checklist minimum height 10.
- Both entry points capture the tile-resolved run/pin, analysis and source. Preserve
  asynchronous workspace/session fences and reject changed sources visibly.
- Keep missing evidence distinguishable from a filter hiding all paths. Preserve
  run selection, pins and restoration without restoring onto a different source.

## Agent work packages and sequencing

Use at most **three OpenCode general implementation agents**. The parent owns
contract coordination, docs, integration decisions and verification. Research agents
used for this plan made no implementation changes.

### Gate 0 — Parent: freeze contract and authorize implementation

- [x] Confirm the five design decisions above and record the shared schema/fixtures.
- [x] Re-estimate WB-069: its original 8 points were low-confidence and precede the
  clarified provider-supported partial-evidence scope.
- [x] Obtain implementation go-ahead; only then activate delivery tasks in
  `construction_phase_plan.md`, which owns implementation order/checklists.
- [x] Assign non-overlapping file ownership and build directories before work starts.

Agents A, B and C implemented their packages in sequence with stable contract/API
handoffs; B/C ran only their bounded follow-up checks concurrently. Normal per-repo
build directories were used with serialized heavy checks in each checkout; no
competing heavy builds required isolated directories. Each agent used at most six
jobs, parent integration at most twenty after agent allocations were released.

### Agent A — Provider retained analysis observation

**Own:** `../hardcaml_asic` analysis schema/collector, `segment_service.ml`, reporting,
inspection selection, capability metadata and provider fixtures/docs.

- [x] Bind a bounded collector to the exact fresh segment request/producer; harvest
  after transport cleanup on success and failure without masking the original error.
- [x] Validate completion records, duration, metric attribution, units and coverage;
  persist an immutable versioned observation separately from checkpoint publication.
- [x] Expose it in reporting and exact-source timing index/detail, including when
  signoff has no checkpoint. Reject ambiguity, stale producers and changed evidence.
- [x] Cover timeout-after-STA, failure-before-STA, partial output, cancellation,
  malformed runtime/units, inherited metrics, wrong identities and source mutation.

**Handoff:** public schema/capability, invocation examples and deterministic fixture
showing completed STA plus failed Signoff and inspectable exact evidence. Changes to
`hardcaml_asic_example` are permitted if needed for a fixture/demo, but none are
currently identified as necessary. No new physical flow is required for this gate.

### Agent B — Workbench protocol, backend and transport

**Own:** `protocol/asic*.ml`, backend ASIC parsing/service/inspection and interfaces,
adapter invocation changes, native HTTP/daemon compatibility changes and their tests.

- [x] Add the typed observation and exact inspection target against the frozen contract.
- [x] Import/hydrate it independently of successful finalization; publish one coherent
  source for both Overview consumers with explicit legacy-provider fallback.
- [x] Fence refresh/cache/detail behavior by attempt, cursor, execution and analysis
  digest. Version/negotiation changes must cover persistent and mixed-version readers.
- [x] Provide fixtures for Agent C early, including zero values, failed constraints,
  missing evidence, stale replies and completed STA from a failed enclosing attempt.
- [x] Verify exact-source inspection and cache restart without initiating execution.

**Dependencies:** Gate 0; can proceed against contract fixtures alongside Agent A.
**Handoff:** stable consumer API and backend/wire fixture results.

### Agent C — Both Overview surfaces and exact navigation

**Own:** terminal projection, summary, host/cursor/action dispatch, timing navigation/
preferences/demand changes, terminal tests and focused WB-069 PTY acceptance script.

- [x] Make renderer, selection and dispatch consume the same projected checklist items.
- [x] Add Timing in the agreed order with independent status/duration; populate the
  compact Timing tile and details from the identical observation.
- [x] Route both inspect actions using captured run/attempt/analysis/source; retain
  pin and asynchronous-source fencing through workspace reuse and restart.
- [x] Explicitly prevent Timing from reaching stage preparation/action inference.
- [x] Verify compact layouts, scrolling, Unicode/ASCII/Off indicator alignment, missing
  evidence versus filtered paths, and read-only drilldown from both surfaces.

**Dependencies:** Gate 0 and Agent B's contract/API fixture handoff. Agent C owns all
terminal files to avoid overlapping ownership of `workspace_host.ml` and `main.ml`.
**Handoff:** fixture-driven PTY evidence plus terminal regression results.

### Parent — Integration and documentation closure

- [x] Integrate A/B contract behavior, then C; review changes against every WB-069 criterion.
- [x] Run the combined focused verification and required repository checks below.
- [x] Record actual commands, outcomes, evidence roots and limitations; update the
  ticket/construction checklist only for verified delivery.
- [x] Document end-of-segment availability, status/verdict distinction, source-change
  behavior and exact user controls in an accompanying user-facing doc.

## Execution policies

- No agent or parent may run `git add`, commit, push or other authorship-producing
  Git operations. Read-only status/diff/log are allowed. Do not create GitHub changes
  or attribute AI authorship. Any exception requires the owner's manual approval.
- Total concurrent build/test/flow worker budget is **20**, including subprocesses.
  With three agents, allocate A=6, B=6, C=6 and reserve 2 for parent/light work;
  use explicit Dune `-j 6` within each allocation. Each agent runs heavy checks
  serially, using separate agreed build directories. Parent integration checks run
  after agents stop heavy work, with at most `-j 20`.
- Audit scripts for internal Dune calls, EDA thread defaults and nested concurrency;
  an outer `-j` alone does not cap those. Partition or serialize those jobs. Do not
  run a physical flow concurrently with the full agent build allocation.
- Source implementation belongs primarily to the three agents. Parent work is docs,
  coordination, testing and necessary light integration edits.
- Preserve unrelated working-tree changes in every checkout. Changes to
  `hardcaml_asic` and `hardcaml_asic_example` are allowed within this feature's scope.

## Verification and acceptance

The original verification matrix follows. Actual results are recorded in
[controls and acceptance](timing_checklist_overview.md#verification--2026-10-21).
All feature-specific automated gates passed. Full Workbench build/lint/runtest passed;
repository-wide formatting still reports existing unrelated sections, enumerated in
that record. Provider focused suites and full build passed; no whole-provider runtest
or new physical flow was run. `hardcaml_asic_example` needed no changes.

### Required fixture matrix

| Scenario | Expected outcome |
| --- | --- |
| STA completes, later DRC times out/nonzero exits | Timing completed with its duration; Signoff failed; both Overview surfaces open exact retained evidence without a checkpoint |
| STA succeeds but negative slack/violations exist | Analysis completed; scoped timing goal failed; signoff acceptance stays separate |
| Failure before STA / partial or malformed producer output | No invented completion, duration or passing verdict |
| Missing corner, unknown unit, nonfinite/no-path metrics | Explicit unknown/unavailable values and conservative verdict |
| Two attempts or reused execution paths | No cross-attempt borrowing of status/time/metrics; wrong source rejected |
| Selection/pin/refresh changes with delayed replies | Both surfaces remain coherent; obsolete results cannot retarget navigation |
| Evidence changes/disappears after capture | Explicit changed/missing source, no silent replacement |
| Restart with cache / old provider | Cached-unverified exact source or explicit unsupported state; no fabricated fresh evidence |
| Enter from both surfaces; `r` on Timing | Matching read-only inspection; zero Plan/Run/Finalize requests |
| Narrow/short layouts and all indicator modes | Status/time readable, columns aligned, all rows reachable, full context in details |

Agent A should extend provider segment-service, stage-report and inspection fixtures
(including `test/check_segment_service.py`, `check_stage_report.py`,
`check_inspection.py` and parser tests), validating their current invocation and
worker behavior first.

For parent integration, after agents have released their allocations:

```sh
./scripts/with-switch.sh dune runtest -j 20 protocol/test
./scripts/with-switch.sh dune runtest -j 20 backend/test/inspection
./scripts/with-switch.sh dune runtest -j 20 backend/test/stage_normalization
./scripts/with-switch.sh dune runtest -j 20 terminal
```

Run the new fixture-only WB-069 PTY test and relevant existing scripts with explicit
matching prebuilt daemon/client/preset binaries:

- `scripts/test-overview-sidebar.py`
- `scripts/test-checklist-launch-workflow.py`
- `scripts/test-launch-stage-consistency.py`

Check retained-demo prerequisites and internal job limits before invoking them.
Optional `scripts/test-fs1-investigation.py` coverage needs explicit retained inputs;
its historical temporary-path defaults are not portable. A retained real failed-run
check is useful if available, but must not silently launch a replacement physical flow.

Finally run the repository's required formatting/lint, build and full test checks
once under the shared budget. Record prerequisites or failures honestly, including
which real-evidence paths were unavailable. Completion requires all WB-069 acceptance
criteria, including both Overview surfaces and preserved launch/alignment behavior.
