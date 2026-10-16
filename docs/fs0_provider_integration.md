# FS0 installed-provider integration

This slice implements the public named-flow boundary in `protocol/asic.ml`,
`project_integration/asic_config.ml`, `adapters/asic_adapter.ml` and
`backend/asic_{service,process,public}.ml`. It does not link `hardcaml_asic`.

**FS1 extension:** the historical synthesis-only launch/cache limits below describe
FS0. Current code also capability-checks known physical endpoints and supports
explicit read-only finalization import with aggregate timing/resources/checks and
declared-clock provenance. Later [lifecycle/artifact](fs1_lifecycle_and_artifacts.md)
and [investigation](fs1_investigation.md) slices deliver owned collect/accept,
bounded report paging, timing/clock/physical/routing exploration and exact binary
handoff. Summary blobs write v4/read v1–v4, with separate bounded inspection caches;
launcher stop grace is 15 seconds (queries retain 5). Those later records own
current adopted scope, verification and limits; the body below retains FS0 evidence.

## Delivered daemon integration

`backend/dune` and package declarations include **`yojson`**. The daemon owns the
ASIC service through `backend/service.ml`; `/api/v1/asic` dispatch in
`daemon/rpc_server.ml` validates instance/project through that service. Integration
is delivered, not pending parent wiring. Exact candidate hashes and consolidated
evidence links are in the [active plan](construction_phase_plan.md#evidence-and-candidate-baseline).

The exact backend API is:

```ocaml
Asic_service.create : state_dir:string -> Asic_service.t
Asic_service.handle
  : Asic_service.t
  -> root:string
  -> environment:V1.Environment_selection.t
  -> Asic.Operation.t
  -> Asic.Response.t Deferred.t
Asic_service.completion : Asic_service.t -> unit Deferred.t
Asic_service.shutdown : Asic_service.t -> unit Deferred.t
```

The daemon creates one service with an **absolute**, single-writer Workbench state
directory. `create` does no I/O. RPC dispatch validates instance/project,
then passes the opened project's root and selected environment to `handle`.
`Asic.Request.t` contains `{ instance_id; project; operation }`;
`Asic.Response.t` is `(Asic.Snapshot.t, V1.Error.t) Result.t`.
Do not call `shutdown` on client detach. Call and await it on daemon shutdown.
`completion` is a quiescence barrier for acceptance/tests, not a tile-read API.

Get returns flows/profiles, the most recently requested description/preview,
registered runs, operation states, shared normalized summaries and cache errors.
Describe/plan replies are fenced against later selections. Provider queries are
scheduled in the background; clients poll `Get` and correlate operation keys.
Run reservation and explicit registration await small atomic registry writes.
Domain summaries are independent of workspace/context/layout/appearance. Clients
must apply their workspace binding/selection-revision fence before displaying a
returned run's summary. Use the **returned** `Run_ref.t` unchanged when selecting,
pinning or querying; `id` is the public stream ID, not a directory-derived ID.

Operations:

- `Get`, `Discover`, `Describe flow`, `Plan selection`.
- `Run { key; preview }`: stable caller idempotency key plus the exact returned
  preview. Only `endpoint = "synthesis"` is executable in FS0. A key reused with a
  different preview fails; the same key never launches twice, including restart.
- `Register { attempt; stream_id }`: exact explicit allocation references, for
  reader-only reconnect/import. It neither launches nor discovers directories.
- `Observe run`: bounded public read-updates + inspect, persisting cursor/status.
- `Load_summary run`: L1, asynchronous L2, or coalesced public observation/report.
- `Refresh run`: explicit observation and report validation/materialization.
- `Cancel key`: use the key returned in `Snapshot.operations` (`run:KEY` for a
  launch). Cancelling an execution also stops its automatic reader. A reader's
  cancellation never signals a historical producer. Summary/reader cancellation
  does not cancel another operation's execution.

New launches start an automatic reader **as soon as allocation is persisted**,
before launcher EOF. Automatic readers stop after terminal observation/report or
their bounded reader budget; reconnect uses Observe/Refresh. An inactive writer
without a terminal outcome is not completion. All updates through the inspected
terminal cursor must be consumed before terminal materialization. Failure before
publication may legitimately have no execution reference. Run status, command
status, report availability and acceptance are distinct; `not_evaluated` remains
`not_evaluated`.

## Opt-in project configuration (schema 1)

At the project root, create `hardcaml-workbench-asic.sexp`. This independent
record does not change the existing generic manifest grammar:

```scheme
((schema_version 1)
 (project_executable /absolute/installed-or-built/project)
 (provider_executable /absolute/prefix/bin/hardcaml-asic-flow)
 (results_root /absolute/project/_flow_results)
 (toolchain /absolute/project/_flow_tools)
 (python (/absolute/project/_flow_tools/.venv/bin/python))
 (support_tools (/absolute/project/_flow_tools/tt))
 (pdk_root (/absolute/project/_flow_tools/pdk))
 (stage_timeout_seconds (3600)))
```

All fields are required in the record; optional fields use `()` for none or
`(VALUE)` for some. Unknown/duplicate fields and unsupported schema versions are
rejected by the record decoder. Paths must be absolute and are retained verbatim
for execution, including aliases and symlink-parent/`..` traversal. The cache must
be outside the provider result store (physical separation is checked without
rewriting execution paths). A positive integer stage timeout forwards **only** to
project `flow run --timeout`; `()` preserves the provider default. Configuration
is read on first use in a daemon; restart to change it. Missing configuration is
reported by `Get` as `configured = false`.

The selected environment is applied to both project and provider invocations via
the existing adapter's argv prefix (`opam exec --switch=... --set-switch -- ...`
or direct inheritance). There is no shell and no runtime Dune invocation. The
project executable must already be linked against its compatible ASIC library;
the installed provider must retain its public runtime resources/toolchain.

## Verified public CLI shapes and corrections

Inspected the current sibling `bin/project.ml`, provider
`bin/{flow_cli,flow_cli_args,flow_cli_identity,experimental_stages}.ml`,
`execution/results/stage_report_service.ml` and the headless reference client.
Those source inspections define the decoder boundary. Installed-binary and real
synthesis verification subsequently passed; see [acceptance](fs0_acceptance.md).

```text
PROVIDER --version --json
PROJECT flow list --json
PROJECT flow describe --flow FLOW --json
PROJECT flow plan --flow FLOW --profile PROFILE --endpoint synthesis \
  --source-root SOURCE --json [--set KEY=VALUE ...]
PROJECT flow run <identical selection/source/assignments> \
  --expected-plan-identity PLAN_ID --provider PROVIDER \
  --results-root RESULTS --toolchain TOOLS [--timeout SECONDS] \
  [--python PYTHON] [--support-tools SUPPORT] [--pdk-root PDK]
PROVIDER observation read-updates ATTEMPT --stream-id STREAM --after CURSOR --json
PROVIDER observation inspect ATTEMPT --json
PROVIDER report EXACT_RETURNED_EXECUTION_FILE --json
```

Require exact integer CLI contract **4** and boolean `namedflow1=true`.
Discovery/catalog/description/plan use v1 envelopes; allocation/error-terminal
JSONL uses observation v1; reads/events/inspection use observation **v2**.
Successful Runner delivery has **no outer schema discriminator**; its nested stage
plan is v3 and methodology execution reference v1. Reports use report v1 and
historical-methodology v1. Duplicate JSON keys, malformed required scalar types,
nonfinite numbers and unsupported envelopes fail. The provider computes and
checks canonical plan identity; Workbench does not recompute that algorithm.

Report selection follows inspection's exact `execution_file`, checking attempt,
plan and (for launched runs) bundle identity. No guessed `execution.json`, private
helper, current-catalog lookup or provider-directory scan is used. Launcher
execution references are checked against inspection. Returned checkpoint metrics
provide `design__instance__count`; supplementary `mapped_cell_types` is optional.
The last returned checkpoint's normalized count/breakdown is retained with its
actual public checkpoint reference and metric-origin context, not falsely labeled
as a per-step measurement. This CLI has no normalized timing-attribution/units
contract: `timing = []` means unsupported in this adapter, not zero slack.

## L1/L2 identity, freshness and retention

Namespace: root + selected environment + complete explicit ASIC config; normalized
schema/adapter v1; provider stream ID; digest of the public report envelope.
L1 holds at most **32** decoded summaries. Each summary is bounded to **256KiB**
and **4096** cell types. L2 retains the most recent summary for up to **128** runs
in that namespace (at most 32MiB of indexed summary payload), with a separate
atomic registry/index. Registered runs and launch reservations are retained up to
**256** each; retained preview payload is capped at **3MiB**. Capacity exhaustion
is explicit rather than silently forgetting an idempotency key or a pinned run.
L1 uses recency; L2 admission/refresh uses recency. Repaint does not query anything.

L1 hits perform no provider reads. L2 hits load only the normalized summary, mark
it `Cached_unverified`, and do not parse a large provider report. Cold misses join
one operation; report publication and observation cursor updates are serialized
to prevent late reads from regressing the index. Advancing an observed cursor or
execution reference invalidates resident summary freshness; a report fetched
against an obsolete cursor/reference cannot replace the current index. Explicit refresh materializes a
public report and hashes it, yielding a new digest when evidence changes. A failed
refresh keeps old data labeled `Refresh_failed`; an inspection without a public
execution reference labels retained data `Missing_source`.

**There is no cheap provider revision query in the inspected contract.** Ordinary
switching deliberately does not claim current freshness for later provider edits.
`Validated` means validated at `observed_at`, not a perpetual immutability claim;
request Refresh for current validation. Restart cannot validate source existence
without provider I/O. Exact older observations are not separately selectable in
this FS0 API; replaced entries may be evicted. The provider is always authoritative.

Registry and summary files use same-directory temporary files and atomic rename;
they are not fsync-backed crash-durable archives. Launch reservation must be saved
before spawning. A crash between reservation and allocation is shown as detached /
allocation unknown and is never retried automatically. Corrupt/incompatible
registries block new launches rather than losing deduplication silently. In-flight
reservations are separate from committed submissions: duplicate Run requests await
the same reservation result, and a failed atomic write leaves the key retryable
without launching. Registry saves capture state at their turn in the single-writer
queue, so older queued saves cannot erase a newly committed reservation. Once
committed, the key is retained even if shutdown prevents launcher scheduling.
Corrupt/incompatible
**summary** entries rebuild through public references. The service
cleans orphaned blobs only in its own known namespace in the configured Workbench
cache. It never evicts provider evidence. Sharing a state directory between live
daemons is unsupported. Old config namespaces require explicit Workbench-cache
retention/cleanup by the owner; this module does not scan unrelated namespaces.

## Supervision and verification status

The parent-owned generic supervisor is not modified. `asic_process.ml` is a narrow
integration seam using native Async Process creation, incremental bounded pipe
draining, deadlines, SIGTERM followed by bounded SIGKILL escalation and reaping of
**only its own PID**. It never signals groups or finds historical PIDs. A daemon
uses a 15-second launcher grace and five-second query grace after the FS1
cancellation correction; the original FS0 seam used five seconds for both. It
starts the owned Async wait immediately and skips signalling already-reaped
children. Installed `async_unix/process.ml` also checks its own wait deferred
before signalling, protecting the exit/reap/PID-reuse race; no raw PID signalling
or independent `waitpid` is used here. A daemon
has at most **4** simultaneous public queries and **1** launcher (each synthesis
container uses 20 cores). Queries have a 30-second budget. A launch task and its
automatic reader share one 1800-second deadline starting before metadata lookup;
allocation does not restart that budget. Launcher failure cancels its automatic
reader. Deadline/cancellation stops polling and report publication, with bounded
child cleanup awaited; stopped observation does not imply provider termination
or successful completion. Stdout is bounded to 16MiB total /
8MiB per record, retained stderr 4KiB. Pending operations are capped at 64 per
project and the in-memory project working set at 32. Client detach leaves daemon
work running; daemon shutdown stops its owned children. ASIC operations have their
own bounded service state, not generic `Service` jobs; integrating them into a
shared generic job/event presentation would be a later change.

`backend/test/asic/` contains an injected executable fixture and an Async test for
discovery, early allocation, launch deduplication, two-profile distinct counts,
warm R1/R2 switching, restart/unverified L2, changed and missing evidence, corrupt
L2 rebuild, concurrent cold reads, L1 eviction/reload and owned cancellation. No
EDA is needed. Additional fixtures cover shared failed reservations, a transient
write obstruction followed by one retry launch and restart deduplication, natural
exit/repeated reaping, output limits, malformed stdout, timeout and cancellation.
With the parent's exclusive serialized execution grant, both checks passed:

```sh
./scripts/with-switch.sh dune build -j20 @lint
./scripts/with-switch.sh dune build -j20 @backend/test/asic/runtest
```

The edited service/test OCaml files also passed `ocamlformat --check` in the selected
switch. Format/lint, runtest, build, synthesis-tile checks and HTTP/PTY/installed
acceptance passed for this recorded FS0 slice. Later FS1 verification is recorded
separately in the construction plan and its linked acceptance records.
[Installed checks](fs0_install_checks.md) and [native acceptance](fs0_acceptance.md)
record passed installed native/external fixture/legacy captures, actual HTTP+PTY
fixtures and strictly serial real synthesis: **673/685 cells**, both completed,
acceptance **`not_evaluated`**. Allocation was observed while launchers were executing
after submission clients exited; warm/restart checks preserved report identity,
durable contexts and L2 summaries. Actual cached UI reopening then showed 673→685
and pinned 673 alongside following 685.

The successful real root is `/tmp/opencode/workbench-fs0-91em64rl/`; UI reopening
is `/tmp/opencode/workbench-fs0-unzwt0kn/`. Exact report paths, plan identities and
digests remain in the acceptance record. Fixture report calls stayed 2→2; real
call counts were not instrumented. The initial unsupported `--timeout` failure is
preserved; the authorized config change to `stage_timeout_seconds ()` allowed the
unchanged candidate binaries to complete. This FS0 run did not establish
placement/signoff, rich timing or real container termination. Subsequent FS1
records separately establish physical execution, inspection and owned-container/
postcheck cancellation specimens. Broader interactive race permutations remain
coverage followups, not unrun integration as a whole.
