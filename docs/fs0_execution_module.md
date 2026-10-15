# FS0 generic execution module boundary

`backend/execution_module.ml` is the generic Build/Test feature boundary over the
existing `Service.t`. `Execution_module.of_service service` is a lightweight wrapper
holding only that service reference. `Service` remains the authority for job IDs,
state, submission-key deduplication, per-root queues, process supervision,
cancellation, logs, events, and shutdown.

## API and endpoint routing

The daemon's existing RPC handlers in `daemon/rpc_server.ml` now route submit,
cancel and log reads through these functions without adapting V1 wire requests or
responses:

| Function | Existing V1 request | Existing V1 response (Async deferred) |
| --- | --- | --- |
| `Execution_module.submit` | `V1.Submit_job.Request.t` | `V1.Submit_job.Response.t` |
| `Execution_module.read_log` | `V1.Read_log.Request.t` | `V1.Read_log.Response.t` |
| `Execution_module.cancel` | `V1.Cancel_job.Request.t` | `V1.Cancel_job.Response.t` |

`submit` accepts the existing `Build` and `Test` actions. All three delegate directly
to the corresponding service operation, retaining instance checks, typed errors,
submission semantics, log bounds/offsets/streams/EOF, and cancellation behavior.
Log reads and cancellation remain job-addressed for **all** existing supervised
jobs, including RTL/driver jobs; generic view selection is not an access filter.

## Project attempts and tests

`Execution_module.snapshot t request ~project` reads one authoritative
`Service.snapshot` and returns `(Execution.t, V1.Error.t) Result.t` synchronously.
It preserves instance errors and returns `Not_found` for an unopened project.
An open project with no generic jobs has empty lists.

`protocol/execution.ml` provides reusable pure `is_generic`, `is_test`, and
`project_snapshot ~project jobs`. The projection contains:

- `project`: the selected project ID;
- `attempts`: that project's exact `dune.build` and `dune.test` jobs;
- `tests`: the `dune.test` subset of those attempts.

Both namespace and name must match. Driver discovery, RTL generation, and other
kinds are excluded. All states are included, with input ordering and full `Job.t`
metadata preserved, including failures, exit status, timestamps, and optional
results. The pure projection filters jobs only; open-project validation belongs
to the backend boundary. Clients can reuse it when projecting recovered snapshots.

An attempt is the existing supervised job, not a new run. No backend run/build
identity, structured result, test-case record, or success is inferred. There is no
second state store or cache. The new `protocol/Execution` projection supplies the
typed module view; existing submit/cancel/log RPC schemas remain unchanged.

## Focused verification

`backend/test/execution/test_execution.ml` exercises selection across two projects,
mixed generic/driver/RTL kinds, launch failure and nonzero-exit metadata, input
ordering, empty selections, and absence of fabricated backend identities. Existing
`backend/test/test_service.ml` regressions continue to cover the reused supervisor.
The focused test has its own test stanza. Parent checks passed:
`dune build -j20 @fmt @lint`, `dune runtest -j20`, and `dune build -j20`.
[Installed workflow checks](fs0_install_checks.md) passed native lifecycle,
external fixture and legacy captures. [FS0 acceptance](fs0_acceptance.md) additionally
ran a project-scoped generic test through actual native HTTP and verified its
completion/output. Final parent-wide checks and current installed acceptance passed;
this document does not claim structured cases/seeds/traces or persistent generic test history
have been added.
