# Executable Timing stage — implementation plan

## Authorization and intent

**Implemented, verified and deployed to the retained example pair.** Live processes
were left running; the owner must restart the daemon/client to load the new binaries.
See [controls, deployment and acceptance](executable_timing_stage.md).

Owner authorized implementation on 2026-10-21 following WB-069's supplementary
Timing delivery. This explicitly extends that ticket's earlier non-runnable scope.
Timing must now support the normal checklist **`r` → prepare → explicit launch**
workflow, backed by a real provider execution segment and checkpoint.

The preceding [observation implementation](timing_checklist_overview_plan.md) remains
the baseline. Preserve its exact-source evidence, failed-attempt recovery and honest
constraint verdicts while extending the physical execution graph.

## Stage contract

New executions use:

```text
synthesis → floorplan → placement → cts → routing → timing → signoff
```

- Routing still ends at `OpenROAD.DetailedRouting`.
- Timing starts at Routing's immediate Classic successor and ends at
  `OpenROAD.STAPostPNR`. It includes required post-route cleanup/checks, fill and
  parasitic extraction; it cannot skip prerequisites by invoking STA alone.
- Signoff continues at the immediate successor of STA (`OpenROAD.IRDropReport` in
  the supported Classic flow) through `Misc.ReportManufacturability`.
- Preserve Classic ordering, configured gates, checkpoint closure validation and
  deferred-check semantics. Validate supported image sequencing rather than assuming
  arbitrary LibreLane versions have identical boundaries.
- A timing endpoint prepares/runs a prefix ending at Timing. Provider continuation
  must support compatible Routing → Timing and Timing → Signoff checkpoints.
  Existing checklist preparation remains a new-run operation, not an implicit
  restart of the selected execution.
- Stage completion, successful STA analysis, constraint goal and final acceptance
  remain separate facts. Explicitly skipped STA cannot earn completed analysis.

### Duration and evidence semantics

The real Timing checklist row uses provider **segment** status and execution time,
including preparation/extraction. The Overview tile must clearly distinguish this
from **STA analysis runtime** and its goal/metrics. Both refer to the same exact
attempt; neither borrows Signoff time or another analysis's measurements. During
Signoff, a completed Timing checkpoint/observation stays available. Failed Timing
segments may still retain independently proven STA output, as previously supported.

### Compatibility requirements

1. Read existing six-stage execution records/checkpoints and signoff-scoped analysis
   observations without inventing a seventh historical execution occurrence.
2. Advertise the executable endpoint through provider capabilities/catalog discovery.
   A legacy provider cannot acquire a runnable Timing action from the UI label alone.
3. Distinguish new seven-stage recipes from historical six-stage recipes in validators,
   finalization and observation logic. Do not globally replace every count of six.
4. Checkpoint reuse must validate bridge/configuration/source compatibility. Historical
   evidence remains readable even where an old checkpoint cannot resume with a new
   bridge. Reject incompatible continuation explicitly rather than silently rerunning.
5. Timing inspection must support the new stage as well as historical signoff sources.
   Captured analysis targets, index/detail cache keys and navigation persistence must
   retain stage identity. Version additive contracts and retain old decoding defaults.
6. Exactly one Timing item appears: a physical-stage item for a new recipe, or the
   existing supplementary analysis item for historical/legacy data. `Enter` must still
   inspect the exact analysis; `r` on an executable item prepares endpoint `timing`.
   A supplementary historical row may also prepare a NEW Timing run if the current
   catalog supports it, without changing or inventing historical execution facts.

Provider Agent A owns the final schema/capability decisions and documents its stable
contract before Agent B consumes it. B hands the typed API/fixtures to Agent C.
This avoids implementing incompatible speculative APIs in parallel.

## Work packages

### Parent — contract, docs and integration

- [x] Record authorization, boundaries, compatibility requirements and ownership.
- [x] Review Agent A's final capability/schema and continuation/finalization rules.
- [x] Integrate the three packages and run cross-repository verification.
- [x] Update controls, ticket scope and acceptance docs with exact results/limitations.

### Agent A — `hardcaml_asic` executable stage

Own provider source/tests/docs; change `hardcaml_asic_example` only if required.

- [x] Extend typed stage graph, recipe/plan endpoint discovery, public CLI choices,
  bridge endpoints/successors, protocol validation and checkpoint transitions.
- [x] Execute and publish Timing independently; stop before downstream Signoff work.
- [x] Support Routing → Timing → Signoff continuation without rerunning STA on the
  second transition. Preserve supported legacy evidence and explicit compatibility.
- [x] Update observation/reporting/finalization for recipe-specific six/seven-stage
  behavior, including failed/cancelled executions and timing-only endpoints.
- [x] Generalize retained STA observation and inspection to timing-scoped producers;
  preserve historical signoff observations and failed-attempt recovery.
- [x] Add deterministic transport/bridge/recipe/checkpoint/report/finalization tests.
  Return exact contract, invocation examples and a retained new-stage fixture.

### Agent B — Workbench backend/protocol

Own protocol, backend, adapters, daemon/native HTTP and corresponding tests.

- [x] Discover/normalize seven stages and executable timing endpoint without adding
  actions for unsupported legacy providers.
- [x] Import timing-stage execution and analysis separately, extending captured target
  stage identity and cache/transport compatibility where necessary.
- [x] Preserve both historical signoff and new timing-stage exact inspection, including
  restart, stale responses and source replacement rejection.
- [x] Add representative seven-stage/legacy fixtures and report API to Agent C.

### Agent C — terminal/checklist and acceptance

Own terminal source/tests and focused native HTTP/PTY scripts.

- [x] Render/select exactly one Timing row, merging physical execution capability with
  matching analysis inspection rather than duplicating the supplementary row.
- [x] Enable `r` → prepare endpoint timing with explicit launch; keep Enter exact-source
  inspection and details available. Explain legacy unsupported actions visibly.
- [x] Distinguish full Timing-stage duration/status from native STA runtime in Overview.
- [x] Preserve pins, stage-aware navigation, cache restart and compact alignment.
- [x] Verify genuine timing endpoint preparation/launch in a fixture, stopping before
  Signoff; verify legacy behavior and the richer Timing tile remain coherent.

## Policies and resource allocation

- No staging, commits, pushes or other mutative/authorship-producing Git operations.
  Preserve all existing uncommitted feature work and unrelated user edits.
- Up to three OpenCode general implementation agents. Each has **at most six jobs**
  with explicit Dune `-j 6`; reserve two for light parent work. Serialize heavy work
  per checkout or use agreed isolated build directories. Total never exceeds 20.
- Audit nested test/build/EDA worker settings. Parent integrated build/tests use at
  most `-j 20` only after implementation agents release their allocations.
- Agents implement substantial source changes; parent owns docs, coordination,
  integration checks and necessary light edits.
- Prefer deterministic no-EDA fixtures for lifecycle and continuation coverage.
  Any real-tool validation must be resource bounded and recorded distinctly.

## Acceptance matrix

| Case | Required outcome |
| --- | --- |
| Discover/plan new provider | Timing advertised as fresh endpoint; seven-stage order is explicit |
| Run through Timing | Timing checkpoint published, no downstream Signoff steps launched |
| Continue Routing → Timing | Required extraction/preparation occurs before STA |
| Continue Timing → Signoff | Begins immediately after STA; does not rerun Routing/STA |
| Full successful flow | Seven-stage completion/finalization accepted under new recipe |
| Timing analysis fails constraints | Execution and goal remain distinct; acceptance honest |
| Failure/cancel before or during Timing | Correct stage outcomes and no fabricated analysis/checkpoint |
| Timing completes, Signoff fails | Completed Timing stage/STA evidence remains inspectable |
| Old six-stage records | Readable, no invented execution, exact old signoff analysis works |
| Incompatible old checkpoint | Readable evidence, explicit continuation incompatibility |
| Checklist `r` | Prepares timing endpoint exactly once; does not launch until explicit action |
| Enter/pins/refresh/restart | Exact run/stage/analysis source retained, no silent replacement |
| Compact Overview | One Timing row; stage duration vs STA runtime clearly labeled |

Run provider focused suites and relevant Workbench protocol/backend/terminal tests;
then full Workbench build/lint/runtest and focused native HTTP/PTY acceptance. Retain
existing formatting limitations separately from feature failures. Record actual
commands, source/binary identity where applicable and evidence paths at completion.

## Execution record

Completed with three general implementation agents, staged contract handoffs and
explicit worker allocations. Agent B used `/tmp/opencode/wb-agent-b-build`; other
heavy checks were serialized in their checkout. Parent final build/lint/runtest used
`-j 20` after agents released their allocations; install/rebuild used six jobs.

Final contract decisions:

- Provider advertises `timing_stage1`; recipe schema 4 is seven-stage. Historical
  schemas 2/3 decode using six-stage identities without automatic conversion.
- Analysis schema 2 names stage `timing` and exact immutable execution-prefix
  source; schema 1 retains stage `signoff`. Captured prefix status is distinct from
  the current execution outcome. Evidence is published before Signoff begins.
- Workbench target includes stage and optional exact source path; HTTP opt-in v2
  protects older consumers. Exact index/detail digests and prefix/main-execution
  identity are checked independently.
- Fresh endpoint intents are separate from historical physical observations. The
  original six-stage selection can prepare a new Timing run through the upgraded
  catalog, while an old provider displays persistent unsupported feedback.

Full Workbench build, lint and tests passed after integration. Final executable
HTTP/PTY acceptance has 11 checks; historical unsupported-provider acceptance and
the complete checklist launch matrix passed. Provider lifecycle, continuation,
legacy, finalization and cross-language parity suites passed. Actual supported-image
introspection confirmed the 80-step inventory. No new physical EDA flow was run.
Global formatting retains unrelated baseline differences; feature formatting and
`git diff --check` pass. Exact receipts are in the
[acceptance record](executable_timing_stage.md#verification-record).

Deployment follow-through: the example's standalone endpoint whitelist/help was
updated, its private provider installation and project driver rebuilt, and only
the executable bindings changed in its root ASIC config. Prior copies and timeout
configuration remain preserved. Retained Workbench binaries were refreshed through
the supported receipt-backed workflow. No live process was stopped; restart commands
and exact deployment receipts are in the [deployment guide](executable_timing_stage.md#refreshed-example-deployment).
