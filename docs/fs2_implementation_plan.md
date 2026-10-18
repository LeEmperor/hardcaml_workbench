# FS2 — Structured simulation delivery

**Subsequent activated extension, 2026-10-17:** WB-034 genuine FIFO adoption,
WB-032 test catalog and WB-063 cooperative Testing investigation are implemented
and automatically verified. The shared coordination plan is
[testing_cluster_plan.md](testing_cluster_plan.md); [current controls](testing_workspace.md).
This leaves the original accepted milestone below closed.

**Milestone closed, 2026-10-16: structured project-scoped simulation delivered and
accepted.** The owner confirmed the basic demo works and authorized closeout after
automated verification. This is the retained implementation/coordination plan for
the FS2 worktree. The user approved the recommendations below. The construction plan
remains the overall delivery index; this document records FS2 contracts, work
ownership and acceptance. Record actual results, not intended results, as delivered.

Remaining adoption/performance/extensions are [named followups](backlog/fs2_followups.md).
Owner integration and post-merge checks are a separate
[handoff](fs2_acceptance.md#integration-handoff), not claimed complete here.

## Scope and accepted decisions

- Project-scoped structured suites/cases, seeds and parameters; optional exact ASIC
  input association. A selected ASIC run never supplies implicit provenance.
- Reuse the existing supervisor's jobs, per-root queue, cancellation and submission
  deduplication. No separate simulation process scheduler.
- Versioned project-owned discovery/launch/event contract; ordinary Dune tests and
  driver-less projects remain supported. Do not infer case outcomes from human logs.
- Capture invocation inputs. Targeted reruns create new jobs linked to the original
  attempt, and explicitly mean rerun on the current project, not an archived build.
- Bounded live observations, summary/detail views, failure reports and traces.
- Workbench-owned bounded durable normalized test records; explicit missing artifacts
  and interrupted history after restart. No automatic process replay on restart.
- Byte-exact trace export to the terminal host and explicit external viewer actions.
  Factor small shared export mechanics where useful, preserve ASIC behavior, and do
  not invent ASIC identities for simulation artifacts.
- Real PDK-free Cyclesim demonstration. Embedded waveform UI and automatic ASIC
  acceptance contribution are later extensions. Gate-level support is an optional
  evidence-backed adapter, not a prerequisite to this delivery.

## Feature-set contract direction

FS0 -> FS2 supplies execution/identity/transport/tiles, already delivered.
FS1 -> FS2 supplies artifact/investigation patterns and optional ASIC evidence,
already delivered; adaptation is now FS2 work, not an unfinished FS1 gate.
FS2 -> FS3 supplies simulation configuration/view identifiers that setup/templates
may expose later. FS3 conveniences are not required for this implementation.
FS2 -> ASIC acceptance is a separately activated evidence bridge, never automatic.

## Working rules

- Work in `/home/wayne/devel/jane/fs2`; no git add/commit/push or authorship changes.
- Up to three general implementation agents. The coordinator owns documentation,
  integration and scheduling builds/tests. Agents must not run Dune/build/test jobs
  unless explicitly allocated a budget. Total active job budget must not exceed 20.
  Initial implementation allocation: backend 8 jobs, terminal 6 jobs, provider 6
  jobs, each in a separate absolute build directory under `/tmp/opencode`. Each
  agent must run its own commands serially and bound nested fixture builds too.
  The coordinator runs no concurrent compilation during these allocations.
- Use `scripts/with-switch.sh dune ... -j 20` for coordinator-run Dune checks when no
  other compiler/test process is running. Avoid nested unbounded builds in fixtures.
- Evidence/state under `/tmp/opencode`. Prefer PDK-free fixtures and Cyclesim; no full
  physical flow is needed for the core acceptance.
- Preserve other agents' changes. Agents own separate file groups below; protocol
  changes after the initial contract require communicating the change in handoff.

## Implementation ownership

1. Backend agent: protocol and provider/config contract, simulation adapter and
   supervisor integration, daemon RPC, durable records/artifacts and backend tests.
   Owns protocol/, project_integration/, adapters/, backend/, daemon/ and any HTTP
   transport wiring required by the new endpoint.
2. Terminal agent: typed simulation view/state, command/palette actions, captured
   launch/rerun forms, polling/fences, trace export/viewer and terminal tests.
   Owns terminal/. Keep generic tests and ASIC investigation available.
3. Provider/acceptance agent: project-owned real Cyclesim provider demonstration,
   deterministic malformed/failing/cancellation provider fixtures and end-to-end
   acceptance scripts. Owns new example/fixture files and scripts/test-fs2-*.
   Changes to hardcaml_asic_example may be small and additive if needed; prefer an
   in-repository reproducible example when that provides stronger independent tests.

The backend agent first publishes the concrete contract files and a handoff here
before implementation agents 2/3 start. Stable contract definitions are the shared
source of truth, not independently invented client/provider schemas.

## Delivery order

1. Freeze versioned discovery/config/event/RPC/types and input/artifact limits.
2. Implement supervisor-backed execution and reducer/store with focused tests.
3. Implement actual terminal suite/attempt/case investigation and explicit commands.
4. Integrate real Cyclesim provider and trace artifacts, targeted rerun and history.
5. Verify formatter/lint/build/tests and native HTTP/PTY acceptance, with job budgets.
6. Update feature inventory, construction plan and acceptance/controls documentation.

## Required acceptance

- Generic tests continue without ASIC configuration.
- Discovery is bounded/versioned; cases/seeds/parameters are explicit.
- Retried submission keys launch once; different payload with same key conflicts;
  intentional reruns produce distinct linked attempts with original inputs.
- Process exit and semantic test outcome remain separate; malformed/truncated or
  duplicate event streams cannot manufacture successful case/suite completion.
- Partial results survive cancellation/crash; unfinished cases are honest.
- Live progress, failure detail and logs are usable; two tiles have independent
  selection; hiding/switching views does not cancel jobs or relabel project tests.
- Exact raw trace bytes survive daemon-to-client export; stale/missing/changed
  artifacts fail explicitly; actual external handoff is exercised.
- Historical records reopen after daemon restart without launching jobs; missing or
  corrupt records have bounded honest behavior.
- One actual Cyclesim run with explicit seed/parameters and rerun, plus deterministic
  failure/malformed/cancellation fixtures and actual terminal input acceptance.

## Contract handoff

Initial interface frozen by backend agent, 2026-10-16. Agents 2/3 may implement
against these concrete definitions now:

- `protocol/simulation.ml`: standalone `Simulation` RPC, portable discovery,
  explicit selection/captured invocation, provider request/events, attempt/case
  states, history summaries and hex-encoded raw-byte pages. No V1 event-union or
  manifest changes. Endpoint `/api/v1/simulation`, hello capability `simulation`.
- `project_integration/simulation_config.ml`: parsed/validated independent
  `hardcaml-workbench-simulation.sexp` with required fields `schema_version=1`,
  absolute `provider_executable`, `provider_args`, `discovery_timeout_seconds`
  (1..60), `run_timeout_seconds` (1..86400). No implicit provider build.
- `project_integration/simulation_protocol.ml`: bounded discovery and event-line
  parsers, structural validation, selection validation/normalization.
- `adapters/simulation_adapter.ml`/`.mli`: exact executable/environment/cwd/argv
  contract. `native_http/client.ml`: typed `Client.simulation` helper, same outer
   transport Or_error as ASIC. Endpoint implementation is now delivered.
- `docs/fs2_simulation_contract.md`: authoritative external framing/examples,
  lifecycle/reducer semantics, RPC operation effects/errors and durable limits.

Provider handoff: from canonical project-root cwd run
`EXEC [provider_args...] discover --protocol-version 1`, stdout exactly one
`Simulation.Discovery.t` sexp, stderr diagnostics, exit 0. Run argv is
`EXEC [provider_args...] run --protocol-version 1 --request ABS_REQUEST --events
ABS_EVENTS --artifact-dir ABS_ARTIFACT_DIR`. Request is
`Simulation.Provider.Request.t`; append/flush LF-delimited machine sexps of
`Simulation.Provider.Event.t` to events file. Stdout/stderr are human logs only.
Sequence zero Started, contiguous sequence numbers, explicit case start/finish,
optional progress/artifact declarations, final Finished Passed/Failed. Close
artifacts before announcing normalized relative paths; no symlinks. See the
contract for exact syntax, including named-record variant payloads.

Terminal handoff: operations Get, Discover, Launch, Rerun, Observe, History,
Cancel, Read_artifact_bytes. Poll snapshots; no simulation V1 update events.
Discover schedules/coalesces a normal supervisor job; Get never launches tools.
Launch supplies current discovery_digest, unique submission_key, nonempty explicit
case list, canonical uint64 decimal seed string, every declared parameter, optional
exact ASIC refs. Rerun supplies original attempt ID and explicit nonempty subset;
captures original seed/parameters/ASIC refs against current project catalog/config,
new job/attempt and immediate parent job/attempt identity. Snapshot detail and byte
page are response-local; two tiles must retain independent selections/fences.
Use existing Read_log with attempt.job; historical logs need not survive restart.

Limits frozen: 64 suites/1024 cases total/32 parameters per suite, 1 MiB catalog,
16 KiB event including LF, 100000 events/16 MiB stream, last 256 accepted events
retained plus normalized state; 128 artifacts, 64 MiB each/256 MiB per attempt;
64 KiB decoded raw-byte page. Per-root durable history 100 attempts/16 MiB
normalized records/512 MiB artifact copies, oldest-terminal eviction, active never
evicted. History pages <=25. Raw bytes use lowercase hex with expected SHA256;
missing/changed evidence is explicit. Artifact size/hash may be absent when capture
failed; availability is typed, never inferred from a zero length.

Semantic freeze: process exit and case outcome remain separate. Valid terminal
stream plus exit 0 required for overall Passed/Failed. Duplicates/gaps/truncation,
bad identity/transitions, overflow/nonzero exit/timeout => Incomplete; preserve
accepted case results, unfinished cases Incomplete. Cancel => Cancelled/Incomplete;
restart => Interrupted/Incomplete without replay. Unknown progress total stays
indeterminate. No implicit ASIC evidence or automatic acceptance contribution.

Initial publication supplied contracts/codecs/adapters without running builds/tests.
Backend implementation has now resumed and delivered the endpoint/capability,
Service supervisor operations and submission-registry hooks, live tail/reducer,
durable root-keyed reservations/history, artifact capture/verification and RPC
responses. No public `Simulation` wire definitions changed during the implementation
resume. Optional ASIC refs remain provenance references only in v1, not implicit
collateral staging; acceptance validates the exact current adopted validated terminal
summary/catalog, hashes its bytes and rechecks adoption before accepting association.

Backend technical handoff (2026-10-16):

- New backend files: `simulation_task.ml`, `simulation_files.ml`,
  `simulation_reducer.ml`, `simulation_service.ml`. `Service` exclusively creates,
  queues, logs, times out, cancels and reaps simulation processes. RPC serialization
  in the simulation service protects reservations; it is not a process scheduler.
- State is `<state-dir>/simulation-v1/<SHA256 canonical root>/<opaque attempt>/`:
  atomic fsynced `record.sexp`, hashed-ID `*.bytes` copies and ephemeral `work/`.
  Restart marks unfinished records Interrupted, removes work/orphan copies and
  never signals or replays historical producers. Missing/changed artifact reads
  return typed errors; Observe also exposes missing/size-changed availability.
- Native endpoint `/api/v1/simulation` and hello `simulation` are wired. Client
  helper retains the normal outer transport Or_error and inner typed response.
- Meaningful tests are in `backend/test/test_simulation.ml` with deterministic
  `backend/test/fs2_provider.py`; daemon endpoint/fence checks extend `test_rpc.ml`.
  Tests cover accepted and invalid reducer transitions, live unknown totals, detail
  bounds, actual provider concurrency/conflicts/rerun/queue/cancel/timeout, oversized
  streams, binary pages, stale catalogs/config, missing/changed/symlink artifacts,
  unadopted ASIC rejection, durable reservations/interruption/corruption, pagination
  and active-preserving eviction/exhaustion.
- All backend-owned verification commands use the absolute separate build directory
  `/tmp/opencode/fs2-build-backend` with `-j 8`, run serially. Targeted Dune tests
  cover `backend/test protocol/test project_integration/test adapters/test daemon/test`.
  Backend/daemon/native client compilation, owned-library lint and owned-file
  `ocamlformat --check` are also exercised. Final command/results are returned in
  the backend agent handoff. Real provider/native PTY acceptance remains coordinated
  with the terminal/provider agents; no physical flow was started by this agent.

## Verification record

Final combined format/lint, full `dune runtest`, and full `dune build` passed serially
with `-j 20` using `/tmp/opencode/fs2-build-backend`. Actual post-review native
HTTP/PTY acceptance passed **45 checks** at `/tmp/opencode/fs2-native-yx27d5_b/`.
Real standalone Cyclesim proof passed at `/tmp/opencode/fs2-provider-tzid09_h/`;
all five interrupt modes passed at `/tmp/opencode/workbench-terminal-interrupt-ou1stfm9/`.

Review followups are included: environment/config capture and reservation fences,
persistence failure handling, chunked/yielding event drain, retained job/closure
bounds, stale frontend receipt rejection, wrapped scrollable failure detail, and
worker-thread export hashing/writing. No public Simulation wire changes were needed.

See [FS2 acceptance](fs2_acceptance.md) for exact commands, controls, evidence and
remaining scope. Metadata/capture filesystem work retains slow-storage latency
limits; historical logs and archived-build replay are not promised. No physical
flow, sibling edits or mutative Git operations were performed.
