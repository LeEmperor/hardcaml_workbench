# Real launch/plan/checklist consistency

Activated2026-10-17 from owner screenshots after real synthesis launches.
Observed exact new execution `6c006def1f794542a1c4cf481e8eba2f` records a requested
`synthesis` stage and a completed `implementation.synthesis` occurrence with exit0.
The UI currently ignores that structured observation unless optional `stage_plan`
is present. The plan display also still asserts no allocated job after launch.

## Required fixes

1. Track an exact launch associated with its preview/submission key, rather than
   treating retained preview readiness as proof no execution exists. Display
   submitting/allocated/running/completed/failed/cancelled or unavailable honestly.
   Plan readiness and producer lifecycle remain separate facts. Explicit new launches
   may reuse a valid preview; never replay automatically or associate the selected
   historical run merely because it is visible.
2. Map the provider's already-public structured requested stage plan and per-stage
   occurrence statuses into the checklist. Do not infer individual completion from
   overall process status, existence of cell metrics, or a published checkpoint while
   its occurrence is still running. Synthesis-only leaves other canonical stages
   not_requested; failure/interruption/missing/unknown evidence remains explicit.
3. Prefer adapter normalization over a provider upgrade if the current public API
   already contains sufficient facts. Current `state.plan` and `state.occurrences`
   do; preserve optional stage-plan extension behavior and cursor fences. No parsing
   raw EDA reports, guessing newest paths, or editing stored provider results.
4. Verify against the owner's exact two new runs and retained historical signoff
   through private read-only registration. No new EDA is required. Refresh matching
   persistent Workbench demo binaries after final build; do not stop live user jobs.

## Working rules / ownership

Preserve current uncommitted work and Git index/history. No staging/commits/pushes,
no real EDA reruns, no user daemon/state mutations during tests. Three agents max,
each2 build jobs, serial per agent, separate `/tmp/opencode/consistency-{launch,stages,acceptance}`.
Coordinator final checks serial at2.

### A — launch projection and plan lifecycle

Own protocol/asic.ml additions if needed, backend/asic_service.ml launch snapshot
projection, terminal/planned_run.ml{,i}, main.ml/workspace_host.ml/host_view.ml and
minimal related fixtures/tests. Existing durable `submissions` retain exact key,
full Preview and allocated run ID, so expose bounded typed launch references if
needed for restart/multi-client attribution. Do not guess newest runs or parse labels.
Prefer additive/defaulted snapshot field and authoritative reservation order when
choosing a matching latest submission. State transitions/fences must survive
replanning, retry, different clients, missing operation details and daemon restart.
Never mislabel detached launch ownership as active producer ownership.

### B — public structured stage normalization

Own backend/asic_public.ml and focused backend/protocol stage tests/fixtures. Avoid
asic_service.ml (A owns it) unless a tiny hook is coordinated. Inspect real public
Observation API source/contracts read-only; normalize from supported explicit schema
and known action keys. Requested stages and occurrence identity must agree with
stream/attempt, legal statuses and cursor. Unknown contracts/keys remain unknown
rather than false success. Explicit stage actions may remain absent unless the
actual public provider advertises a supported fresh selection; don't invent actions
from a run's overall status. Document that separately from now-readable stages.

### C — integration/real evidence acceptance and demo handoff

Own new bounded `scripts/test-launch-stage-consistency.py` and helper/regression script
adaptations, plus real demo binary refresh/verification after A/B readiness. Inspect
current daemon/read-only persisted references to identify original exact allocations:
`.../results/observations/20261017T040517848061Z_fac7d0bc` and
`.../results/observations/20261017T040844955822Z_6c006def`; retrieve exactstreamIDs from
records/public observations rather than directories alone. Verify original results
unchanged. Native fixture should exercise launch receipt/allocation/running/terminal,
same preview reuse/new plan, missing receipt and restart with exact ledger identities.
Actual real imports prove synthesis Completed and remaining stages Not_requested,
plus historical full-run stages from explicit evidence. No EDA needed.

## Acceptance

- Planned-run no longer claims no allocated job after a successful submission;
  exact run/key visible when known, plan versus launch states clearly labeled.
- Real new synthesis maps Completed from its completed occurrence, not aggregate
  completion; running publication and failure/interruption fixtures prove no falsepass.
- Unknown/malformed/legacy state handling, cursor race and optional extension
  compatibility; fresh read updates old cached missing stages without result edits.
- Multiple runs with same plan, another client's launch, restart and replan do not
  attach unrelated/latest-directory results. All effects remain explicit/idempotent.
- Full format/lint/tests/build at2, native fixture + actual retained evidence proof,
  matching persistent binaries refreshed and exact manual restart/Refresh guidance.

## Status

**Implemented and verified.** Final normal format/lint/full tests/build passed at2.
Final native acceptance27 checks passed at
`/tmp/opencode/launch-stage-consistency-a2201a488574/`; exact public observations
from both owner synthesis runs show completed synthesis/other stages not requested,
and historical signoff shows six explicit completions. Canonical hashes unchanged.
Persistent Workbench copies are refreshed and actual-project rich-inspection
acceptance passed again. [Current semantics and restart/Refresh instructions](launch_stage_consistency.md).
Handoffs below retain chronological implementation details; transient findings are
superseded by final checks. No EDA or live user-state changes were performed.

### A API handoff (implemented; focused checks passed)

`Asic.Launch.t = { key : string; preview : Asic.Preview.t; run_id : string option }`.
`Asic.Snapshot.launches : Asic.Launch.t list [@sexp.default []]` projects the
durable submissions ledger in newest **reservation** order (bounded at256 by the
existing ledger). Match the full `Asic.Preview.equal`, never selection or identity
alone. `key` is the raw submission key; its Pending key is `"run:" ^ key`.
`run_id` is authoritative even if the corresponding Run is absent; resolve against
`snapshot.runs` by exact ID only. Empty/legacy ledger means association unavailable,
not proof that no job was allocated. C fixtures should consume actual snapshots.
The UI labels the first exact match **last launch using this plan**. Plan readiness
remains separate from producer/ownership state. No wire compatibility with old
binaries is implied: rebuild daemon and client together (old S-expression caches
continue loading with `launches=[]`).

A final semantics / C integration handoff (2026-10-17):

- `backend/asic_service.ml` exposes all existing durable reservations (at most256;
  existing retained-preview budget <3MiB), including not-yet-allocated entries. It
  preserves ledger order, without sorting by completion, paths, time, or runs.
  An absent `Run` does not discard a known `run_id`. No launch guard, reservation,
  idempotence, ownership, provider invocation, or FS2 behavior was changed.
- `Planned_run.model.launch = { key : string option; run_id : string option;
  state : launch_status; message : string }`, with `Submitting | Allocated | Running
  | Completed | Launch_failed | Cancelled | Detached | Unavailable`. These are
  distinct from the existing plan `status`. Messages distinguish producer terminal
  facts from launch-operation failure/cancellation, and explicitly state whether a
  launch operation is active. Producer terminal status comes from the exact Run,
  never task completion or the selected historical run. Nonterminal observations
  require active exact launch ownership to be called running; missing ownership is
  detached. Known terminal outcomes remain visible with no active owner.
- Client-only `begin_launch : t -> key:string -> Asic.Preview.t -> t * launch_ticket`
  and `launch_receipt : t -> launch_ticket -> floor:int -> (unit,string) Result.t -> t`
  are wired before issuing the Run RPC. Tickets fence scope and independent launch
  generation; replanning does not overwrite them. Reconciliation requires the exact
  key/full preview in a snapshot requested after the receipt. Older-issued responses,
  another launch's receipt, and old-owner receipts cannot resolve that local intent.
  A transport failure remains allocation-unknown until exact authoritative evidence
  resolves it; no replay/retry is automatic. A failed/cancelled operation before
  observed allocation is explicit, not asserted to be a producer terminal result.
- `launchable` keeps full-preview/plan readiness checks and blocks unresolved local
  intent, active exact launch operations (including older exact reservations), the
  latest submitting/allocated/running/detached launch, or an allocated failed/cancelled
  operation without producer-terminal evidence. A terminal exact launch with no
  active launch operation can explicitly launch the same preview under a new key.
  An empty/old ledger shows unavailable, never "no job allocated"; it does not invent
  a producer association or block a first explicit launch. Detached launches need
  explicit Observe/Refresh to establish a terminal outcome before reuse.
- Replanning replaces the candidate, not ledger entries. Only full-preview matches
  are associated; while a candidate plan is pending/stale, the display explicitly
  labels any launch as using the **retained shared preview**. Compact rendering
  includes plan state and launch state even in shallow panels; normal/detail panels
  additionally expose exact key/run ID. Launch and launch-and-view disable reasons
  now point to unresolved launch evidence rather than recommending endless replans.
- After daemon restart there is intentionally no current shared preview or completed
  Plan operation. In that case only, the panel may display the newest authoritative
  reservation (or unresolved local intent) separately as **last launch reference
  (no current plan)**. `model.launch_preview : Asic.Preview.t option` carries that
  exact provenance; `model.preview` remains None and the plan is not launchable.
  Detail shows its exact identity and selection as a separate, non-reusable preview.
  With a current shared preview, only exact matches are displayed; there is no
  fallback to an unrelated ledger entry. `Planned_run.launch_label : model -> string`
  supplies the appropriate exact/retained/separate label for renderers.
- C should use `snapshot.launches`, `snapshot.operations`, and `snapshot.runs` from
  actual RPC snapshots in its native fixture. Native CLI's Run command already
  returns the additive snapshot field. Both rebuilt executables are available at
  `/tmp/opencode/consistency-launch/default/{daemon,terminal}/main.exe`; persistent
  demo binary refresh and retained real-run acceptance remain C's integration step.

Verified serially in exact switch `5.2.0+ox`, jobs2:

```
opam exec --switch=5.2.0+ox -- dune runtest --build-dir /tmp/opencode/consistency-launch -j 2 protocol terminal backend/test/asic backend/test/stage_normalization
opam exec --switch=5.2.0+ox -- dune build --build-dir /tmp/opencode/consistency-launch -j 2 daemon/main.exe terminal/main.exe @terminal/lint @backend/lint @protocol/lint
```

Owned OCaml files formatted with this same switch. Protocol tests round-trip a
nonempty launch association through sexp/bin_io and remove the field to prove old
snapshots default to `[]`. Existing backend native launch tests now assert exact
key/full preview, early allocation, newest reservation order and identical restart
projection. Terminal tests cover local pending/no allocation, allocated/live/terminal,
preallocation failure, transport unknown, replan during launch, explicit same-plan
reuse, multiple exact/near-miss previews and run IDs, late receipts/polls, another
client, scope replacement, detached/missing Run, and actual rendered key/run state.

### B stage adapter handoff (2026-10-17, implemented and focused checks passed)

Owned changes: `backend/asic_public.ml` and new
`backend/test/stage_normalization/{dune,test_stage_normalization.ml}`. No service,
protocol, UI, provider installation, or canonical evidence changes by B.

Public API inspected read-only in both source
`../hardcaml_asic/execution/observation/observation.mli` and the configured installed
generation `../hardcaml_asic_example/.dev/asic-workbench/generations/bd70b370807044e6b43bfab9aae3a4c6/lib/hardcaml_asic/execution/observation/observation.mli`.
They agree: inspect exposes a provider-validated immutable journal prefix with
`state.attempt_id`, explicit plan, occurrences, artifacts and outcome. Source
`execution/execution_plan.ml` defines schema3 `stages`/`initial_boundary`, and
`lib/flow/recipe.ml` requires a nonempty contiguous sequence after the source.
Occurrence identity is exactly `stream_id/implementation.<stage>`; completion is
an explicit completed occurrence with integer exit0. Published checkpoints alone
are not completion. No report-text parsing or provider upgrade is needed.

Normalization semantics:

- Absent/null `stage_plan` uses supported schema3 state. Supported stage-plan v1
  retains precedence, including its actions. Present unsupported extensions remain
  opaque (`[]`), without fallback that might reinterpret a newer contract. Malformed
  supported shapes/duplicate identities/unknown action keys are rejected; absent,
  legacy or unknown plan versions remain unavailable (`[]`).
- Validate attempt/stream and exact occurrence identity, uniqueness, canonical
  stage names, contiguous recipe, `best_effort=false`/`verdict=null`, and status/exit.
  Requested missing occurrences and unknown/inconsistent statuses become `Unknown`,
  never success. Structural invalidity fails the observation read.
- `unreached` maps Pending; running remains Running even with a checkpoint or later
  outer outcome. Failed maps Failed; interrupted maps Cancelled (existing protocol
  vocabulary), with a reason explicitly distinguishing interruption from user
  cancellation. No aggregate outcome promotes a stage.
- Synthesis-only adds the other five canonical stages as Not_requested. Explicit
  unrequested completed occurrences remain requested=false and are visibly labeled
  **carried forward**; a resume input boundary alone is Not_requested, explicitly
  not newly measured. Exact existing inspection/update cursor fence is preserved;
  ahead-of-updates checklists are cleared until caught up.
- New normalized entries have `action=None`. The configured **project executable**
  `flow describe --flow standard --json` advertises fresh complete-prefix selection,
  but observation state supplies no per-stage fresh Selection. Do not infer one
  from historical endpoint/profile or status. Existing `r` remains unsupported for
  these entries; explicit user planning remains available separately. The provider
  executable supplies observation APIs, not the project's `flow describe` command.

Focused verification (serial builds, jobs2, private build directory):

```
opam exec -- dune runtest --build-dir /tmp/opencode/consistency-stages/build -j 2 backend/test/stage_normalization backend/test/asic
opam exec -- dune build --build-dir /tmp/opencode/consistency-stages/build -j 2 @backend/lint
opam exec -- ocamlformat --check backend/asic_public.ml backend/test/stage_normalization/test_stage_normalization.ml
```

Fixtures cover all five provider statuses, live/final/detached writer states,
publication while running, later outer failure/interruption, invalid exits, missing
occurrences, malformed/duplicate/foreign identities, unknown contracts/action keys,
resume/carry-forward distinction, full explicit signoff, cursor ahead/catchup/regress
and optional extension compatibility. Existing backend ASIC fixtures also pass.

Read-only retained proof: `/tmp/opencode/consistency-stages/prove_retained.py`
queries exact public observations, captures JSON under that directory, invokes the
new test executable against each captured response, and checks before/after byte
inventories of the three observation directories. Results:

- `6c006def1f794542a1c4cf481e8eba2f`, cursor7: synthesis Completed; remaining five
  Not_requested.
- `fac7d0bc5aaf42daab72d381b6e653e5`, cursor7: synthesis Completed; remaining five
  Not_requested.
- Historical `344ac175531e46fcbd021a1d4c79c361`, cursor22: six requested stages
  Completed from exact explicit occurrences.

All three observation inventories unchanged. C can reuse captured JSON/proof
executable for integration; private daemon registration and persistent demo binary
refresh remain coordinator/C handoff work. Fresh Observe re-normalizes previously
missing cached stages without editing provider evidence.
