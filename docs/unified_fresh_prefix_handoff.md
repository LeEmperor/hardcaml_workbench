# Unified fresh-prefix — A backend handoff

Contract frozen 2026-10-27; slice A implemented and verified. A owns this file, protocol,
backend/adapters and backend tests. B owns all terminal changes and terminal fixture
record defaults; C owns script acceptance. No ASIC/example changes are planned.

## Public protocol (existing ASIC RPC)

`Asic.Fresh.Intent.t` fields:
`id : string`, `selection : Asic.Selection.t`, `elaboration_only : bool`,
`expected_plan_identity : string option`, `scope : string`, `created_at : Timestamp.t`.
This is an INPUT intent, not an exact generated plan. Ordinary fresh UI staging
must pass `expected_plan_identity = None`. An explicit `Some` is a strict guard.
`scope` is a stable serialized captured-scope receipt (source root, environment,
ASIC/preparation configurations, provider generation stamp); treat it as opaque
for equality and optionally show it in expanded inspection. It is not a plan ID.

Operations:

```ocaml
Stage_fresh of { selection : Selection.t; elaboration_only : bool;
                 expected_plan_identity : string option }
Launch_fresh of { key : string; intent_id : string }
Cancel_workflow of string (* workflow id *)
```

`Asic.Snapshot` gains defaulted `fresh_intent : Fresh.Intent.t option` and
`workflows : Fresh.Workflow.t list` (newest first). Existing record constructors
outside backend/protocol need `fresh_intent = None; workflows = []` (B/C ownership).

`Asic.Fresh.Workflow.t` fields:

- `id`, `key : string`; `intent : Intent.t`
- `phase : Phase.t` = `Reserved | Building | Emitting | Prepared | Physical |
  Completed | Failed | Cancelled | Interrupted`
- `cancel_requested : bool`
- `preparation_id : string option`
- `elaboration_started_at`, `elaboration_finished_at : Timestamp.t option`
  (defaulted; durable inclusive preparation timing, independent of live job handles)
- `elaboration_status : string` = `not_requested`, `building`, `emitting`,
  `completed`, `build_failed`, `emission_failed`, `cancelled`, or `interrupted`
- `build_job`, `emission_job : Job.t option` (live session handles only; cleared on restart)
- `prepared : Prepared.t option`
- `run : Run_ref.t option`; `reference : Asic.Reference.t option`
- `error : string option`; `created_at : Timestamp.t`; `finished_at : Timestamp.t option`

`Asic.Fresh.Prepared.t` fields:
`bundle_identity`, `bundle_directory`, `plan_identity`, `methodology_plan_path`,
`methodology_plan_digest : string`.

Before allocation, select/display workflow by returned key/id; after allocation,
find workflow by exact `run`. Never substitute project-wide latest preparation.
Missing historical linkage means unavailable. Elaboration-only has no run allocation.
Existing guarded view-on-allocation should track the workflow key, which is also
the physical submission key. No client-side continuation is needed.

`Launch_fresh` returns promptly after durable reservation. Poll `Get`. Replaying
the same key/intent observes the original workflow, including after restart; a new
staging supersedes the current unlaunched intent. A conflicting key/intent fails.
An accepted intent is consumed once: a different key must stage a new intent.
`Cancel_workflow` latches cancellation and cancels owned preparation/physical work.
Use workflow cancellation before allocation as well as after allocation.
Legacy `Cancel` also accepts workflow id, workflow key, `workflow:ID`, and `run:KEY`
and routes all of them through the same latch. Historical Interrupted records never
acquire cancellation ownership.

Legacy `Run { key; preview }` also chains, with its preview identity as strict
expectation. It must not be used by ordinary new UI staging (pinned plans can be
stale). Existing read-only `Plan` remains a legacy generated preview operation.

## Internal integration

Preparation core exposes a workflow-owned operation with a unique key (no attempt
coalescing), plus exact attempt wait/update/cancel. Source build-through-emission
is serialized across standalone and workflow-owned preparations. Service reuses
its existing supervisor/import hooks. ASIC service owns durable workflow progression
and the sole physical producer. Provider invocation is direct `stages BUNDLE
--methodology-plan FILE --expected-plan-identity ID`, never project `flow run`.
The internal runner also receives a live cancellation predicate, held by the exact
preparation attempt and checked at build/emission/import admission boundaries; this
closes cancellation during asynchronous preparation acceptance, before its ID is
returned to orchestration. Source-lease waiters have no Job until admitted.
The existing generic root queue respects that source lease too: generic source jobs
remain queued between preparation build and emission. Source transactions do not
hold the physical execution throttle while waiting for preparation.

New source work is not replayed after daemon restart. Unfinished workflows become
Interrupted; retained run references can still be observed read-only. Job handles
are session-only; identities, diagnostics, plan file and provider linkage are durable.

## Verification/status

Verified command (all Dune uses shared flock and `-j6`):

```sh
flock /tmp/opencode/workbench-fresh-prefix-build.lock scripts/with-switch.sh dune build \
  @backend/test/runtest @protocol/test/runtest \
  @backend/lint @protocol/lint @adapters/lint daemon/main.exe -j6
```

Backend/protocol tests, backend/protocol/adapter lint, and daemon build pass.
Owned changed OCaml files pass `ocamlformat --check`; `git diff --check` passes.
The broader scoped `@backend/fmt` check reports an existing unmodified one-line
format difference in `backend/test/workspace/test_workspace.ml:516`; A did not edit it.

The actual supervisor-managed **synthetic fixture** tests exercise:

- Synthesis and CTS complete prefixes using the exact emitted bundle, frozen plan,
  expected identity, explicit tool paths and timeout; poisoned pinned project
  executable never runs.
- Elaboration-only with zero provider calls; repeat fresh launches rebuild/re-emit
  even with `reused=true`; same-key replay and conflicting/consumed intents.
- Source changes produce a new identity; an old explicit preview fails strictly.
  Legacy `Run` also goes through the source chain.
- Build/emission failure, explicit identity mismatch, input/config/provider-generation
  drift, failed/superseded staging and failed durable reservation block admission.
- Build/emission cancellation, active physical cleanup and queued physical cancellation.
- Standalone/chained source transactions plus an interposed generic Build preserve
  build→emit ordering.
- Successful/failed history, allocation linkage and timing survive read-only state
  reopening; unfinished work becomes Interrupted; replay never starts a producer;
  historical cancellation never signals another owner.

`backend/test/fresh_provider.py` verifies the plan/manifest/configuration/file hashes
and complete recipe prefix before allocating its synthetic physical attempt. No EDA
or real example source build was performed by slice A.

Scope fences include literal configurations/environment and the physical provider's
resolved path plus binary digest; advancing a provider generation requires a new
intent. Elaboration-only does not stat/probe/execute the physical provider.
`Workflow.elaboration_started_at`/`elaboration_finished_at` were added as defaulted
optional timestamps so restored Elaboration duration does not depend on job handles.

## B/C integration notes and remaining feature acceptance

- B owns terminal record defaults in `overview_tiles.ml`, `asic_intents.ml`,
  `fs0_fixture.ml`, `artifact_view.ml`, `plain_rpc.ml`, and `workspace_host.ml`, plus
  operation/wait-key dispatch. A updated the protocol test defaults only.
- Elaboration-only can use the ASIC RPC with `configured=false` (no ASIC companion)
  when preparation is configured. Do not require physical-provider configuration to
  enable that goal.
- Source-lease waiters intentionally show Building with no build Job yet. Do not
  interpret absent session job handles as absent workflow reservation.
- Physical launch ledger previews for new workflows retain compact identity metadata;
  the full generated plan is retained once at `prepared.methodology_plan_path`.
- Ordinary new UI staging must not call legacy pinned `Plan`/`Run`. The generated
  exact plan becomes known after emission, while `Stage_fresh` is inputs only.
- Terminal/HTTP/PTY acceptance and matching client build belong to B/C/coordinator.
  Slice A did not edit terminal files, scripts, ASIC/example sources or live daemons.
- History remains bounded (256 workflows and a 4-MiB registry per loaded project);
  frozen plans are individually bounded at 16 MiB. Job/log/artifact handles remain
  session-only. Completed history is retained fact, not a fresh revalidation of files.
- Crash windows around external process creation/allocation can leave Interrupted
  ownership with no known allocation. Such keys are never replayed automatically.

## B terminal integration

Terminal integration is implemented and focused verification passes.

- Checklist `r` and manual Plan capture `Stage_fresh` inputs; checklist `R`, selected
  and named palette launches stage and submit `Launch_fresh`. Ordinary UI staging
  always passes `expected_plan_identity = None`. The legacy preview launch action
  also restages fresh inputs rather than submitting pinned `Run`.
- Standalone Elaboration uses `elaboration_only = true` through the same ASIC RPC;
  it does not require a configured physical provider and never requests allocation.
- `planned-run` shows input scope, workflow/key, Elaboration progress, exact allocated
  run, and expanded prepared-bundle/plan facts. `x` there cancels its exact workflow;
  palette `Cancel fresh workflow KEY (Elaboration: STATUS)` works before allocation.
  Preparation's `x` also cancels the tracked fresh workflow when active.
- The selected run checklist resolves Elaboration through `Workflow.run`, including
  durable start/finish timing and exact session logs. A project-latest preparation or
  coincident plan identity cannot relabel a historical run; absent linkage is unavailable.
- Allocation viewing tracks the fresh submission key and uses the existing captured
  workspace/context binding and selection revision guard. Elaboration-only retains
  context. Staging and launch receipts retain request-order, project/client/daemon,
  input-intent and selected-action fences; uncertain submissions are not retried.
- Plain RPC staging has no asynchronous wait key; launch/cancel use `workflow:ID`.
  Wait results consult durable workflow phase, so restored Completed history succeeds
  and Failed/Cancelled/Interrupted history fails even without live Pending records.
- Terminal snapshot fixtures now include `fresh_intent = None; workflows = []`;
  a decoder regression verifies historical S-expressions default those fields.

For C: ordinary Plan no longer creates a provider preview. After staging, select the
existing `asic.launch`/`asic.launch-view` commands; these carry the exact fresh intent.
The planned panel reports `endpoint: elaboration` for the elaboration-only goal and
`Elaboration: building`/`emitting` through the workflow lifecycle. Physical run selection
changes only after allocation and only if the captured target's guards still match.

Verified B command (exit 0, shared lock and six jobs):

```sh
flock /tmp/opencode/workbench-fresh-prefix-build.lock scripts/with-switch.sh dune build \
  @terminal/runtest @terminal/lint terminal/main.exe \
  terminal/workspaces/export_presets.exe -j6
```

Focused regression coverage includes: pre-receipt snapshot floors, pinned-preview
exclusion, uncertain submission blocking and exact-key recovery, source-lease waiters
without job handles, consumed-intent/new-intent behavior, cross-run lineage isolation
despite project preparation changes, durable elapsed time, preallocation cancellation
commands/key handling, allocation context revision guards, historical additive-field
defaults, and durable workflow wait outcomes without live operation handles.

All B-modified OCaml sources pass `ocamlformat --check`; `git diff --check` passes.
The broader `@terminal/fmt` check finds existing formatting differences in unmodified
evidence/hierarchy/navigation/indicator/waveform files (including waveform_data/probe),
not in the modified slice. Client and preset exporter are built at their normal
`_build/default/terminal/` paths, without deployment or user-daemon changes. HTTP/PTY
entry-route acceptance is C's separate receipt; B's checks do not claim EDA execution.

## A review correction — owned capability probe cancellation

The independent review confirmed a P2 in the pre-preparation capability probe:
`execute_fresh` supplied only its 30-second deadline, so workflow cancellation and
graceful daemon shutdown could wait for that query instead of stopping it promptly.

Corrected in `backend/asic_service.ml`:

- The workflow task's cancellation signal now reaches its capability probe, alongside
  the existing deadline. `Cancel_workflow` signals that task as well as any physical
  task; shutdown already signals owned tasks before joining their completions.
- A workflow-owned capability probe is explicitly uncached while running, so other
  workflows/readers cannot borrow its cancellation ownership. Failure/cancellation
  does not clear or poison another reader's shared metadata cache.
- `Asic_process.run` retains exclusive process termination and reap ownership; the
  correction adds no raw-PID signalling or separate process supervisor.
- Existing post-probe cancellation gates still block source build/emission and
  physical admission. No public protocol or B/C source changes were required.

`run_fresh_probe_fixture` in `backend/test/test_preparation.ml` adds gated regressions
for cancellation, independent concurrent probe ownership, failed probes, recovery,
positive source/physical continuation, and graceful Service shutdown. Cancellation
and shutdown must complete within three seconds, with the exact stopped probe PID
absent from `/proc` (including zombies) and no source/physical admission. Cleanup
releases the fixture gate on failure so a regression does not strand processes.

The original native failure evidence remains at
`/tmp/opencode/fresh-review-a/metadata-shutdown/result.json`. The corrected
`/tmp/opencode/fresh-review-a/metadata_repro.py` uses a new private evidence tree:
`/tmp/opencode/fresh-review-a/metadata-corrected/result.json`. It records:

- after cancellation, phase `Cancelled`, owned probe terminated and absent;
- after signalling only the private daemon PID, daemon and probe both absent;
- no external gate release required for shutdown, and zero downstream events.

Backend tests/lint and matching `daemon/main.exe` build pass with the shared lock
and `-j6`; changed-file formatting and `git diff --check` pass. This correction does
not change B/C acceptance receipts or claim that their earlier binary hashes identify
the rebuilt daemon. No EDA, live-session access, deployment or ASIC/example edits.
