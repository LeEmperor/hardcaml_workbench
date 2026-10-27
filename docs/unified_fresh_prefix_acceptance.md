# Unified fresh-prefix acceptance

## Native acceptance (2026-10-27)

Implemented `scripts/test-unified-fresh-prefix.py` and its private producers in
`scripts/fixtures/unified_fresh_prefix.py`, following A's final handoff. Actual
native HTTP **and real client PTY** acceptance passes. The preparation/checklist
harnesses are migrated to unified intents and preserve their standalone
same-selection pinned-preview regression. The recovery defect found during the
broader follow-up is **corrected and verified on the final frozen A/B sources**.
Its earlier failure evidence remains historical below. The original standalone
publisher remains unchanged.

The final evidence directory and assertion total are recorded below. Earlier
incremental runs include HTTP-only and PTY-only subsets; they are explicitly
marked partial in their `result.json`. Initial harness failures and shared-lock
contention were retained rather than presented as passing product evidence.

**Final result: PASS — unified 99 + checklist 83 + preparation 37 + native probe 4
= 223 scripted assertions, plus forced full Workbench build/runtest/lint.**

Comprehensive receipt:
`/tmp/opencode/workbench-fresh-final-81cac6ffa064/receipt.json`.
All active native assertion records pass. The receipt references exact command
logs, individual results, time budgets, durations and tested/final binary hashes.
The final matching build completed, and the later forced full build retained
byte-identical daemon/client/exporter hashes. `git diff --check` passes.

Matching final tested binary SHA-256:

| Binary | SHA-256 |
| --- | --- |
| `_build/default/daemon/main.exe` | `5978abb70d869e9542b0e5e60a783b4b318e574ccc58047a738ee80c4345a07c` |
| `_build/default/terminal/main.exe` | `6d40c5ed46a9bf8944712af5bacceeb06771cccbfac8a2d487ea5e10191c2e08` |
| `_build/default/terminal/workspaces/export_presets.exe` | `5f8e0b57f17fd0009f8b41792d90b27c51239fccaa7a8bb5411bd8ed2a02407b` |

The final run proves source-build completion precedes emission, which precedes
direct-provider admission, using native job timestamps and producer event times.
The preallocation PTY capture zooms an explicitly added private `planned-run`
tile and asserts the **exact workflow ID and submission key** alongside
`Elaboration: emitting`; a project-latest preparation headline cannot satisfy
this assertion. The selected historical run remains independently unavailable
until the guarded allocation changes the context. Final tile-preservation
assertions include this explicitly added fixture tile.

## Final frozen-source verification

The matching binaries were built first. All three native suites then ran against
that exact pair, followed by the full forced Dune checks:

```sh
flock /tmp/opencode/workbench-fresh-prefix-build.lock \
  scripts/with-switch.sh dune build -j6 \
  daemon/main.exe terminal/main.exe terminal/workspaces/export_presets.exe

# Each script also received its own new --evidence directory recorded below.
python3 scripts/test-unified-fresh-prefix.py \
  --daemon _build/default/daemon/main.exe --client _build/default/terminal/main.exe \
  --preset-export _build/default/terminal/workspaces/export_presets.exe
python3 scripts/test-checklist-launch-workflow.py \
  --daemon _build/default/daemon/main.exe --client _build/default/terminal/main.exe \
  --preset-export _build/default/terminal/workspaces/export_presets.exe
python3 scripts/test-preparation-frontend.py \
  --daemon _build/default/daemon/main.exe --client _build/default/terminal/main.exe \
  --preset-export _build/default/terminal/workspaces/export_presets.exe

flock /tmp/opencode/workbench-fresh-prefix-build.lock \
  scripts/with-switch.sh dune build -j6 --force @runtest @all @lint \
  daemon/main.exe terminal/main.exe terminal/workspaces/export_presets.exe
```

All six recorded commands (matching build, three suites, forced full Dune, diff
check) exited **0**. The full Dune command had a 1,200-second budget and completed
in 19.952 seconds, including rerun aliases rather than cached test success.
No product or source blocker remains in this acceptance matrix.

| Final check | Outcome | Actual evidence |
| --- | --- | --- |
| Unified real HTTP + PTY | **99/99 passed**, exit 0 | `/tmp/opencode/workbench-fresh-final-0c3f35f00e3c/unified/result.json` |
| Full synthetic checklist | **83/83 passed**, exit 0 | `/tmp/opencode/workbench-fresh-final-0c3f35f00e3c/checklist/result.json` |
| Preparation frontend | **37/37 passed**, exit 0 | `/tmp/opencode/workbench-fresh-final-0c3f35f00e3c/preparation/result.json` |
| Owned capability-probe cancel/shutdown | **4/4 passed** | `/tmp/opencode/workbench-fresh-final-81cac6ffa064/probe-native/result.json` |
| Forced full Dune build/runtest/lint and explicit matching targets | **exit 0** | `/tmp/opencode/workbench-fresh-final-0c3f35f00e3c/full-dune-forced.log` |

### Same selection, different scope: native replacement and recovery

The preparation suite now strengthens its captured-palette supersession case:
the replacement keeps the **identical selection** but changes the preparation
configuration timeout from 90 to 91 seconds. It asserts distinct opaque captured
scope and intent ID, rejects the old captured launch without any workflow or
producer, restores configuration and stages again in the **same client**. Manual
launch then succeeds. Both the scope fence and same-client recovery assertions
pass; no fresh-client fallback was taken in the final run.

Exact original/replacement receipts:
`/tmp/opencode/workbench-fresh-final-0c3f35f00e3c/preparation/native/same-selection-scope-replacement.json`.
Relevant actual PTY captures are `superseded-stage-rejected.*` and
`restaged-intent-launch-eligibility.*` in that same `native/` directory.

### Native capability-probe cancellation and shutdown

An additional synthetic-only native check holds the physical provider's capability
probe before preparation. Workflow cancellation stops/reaps the exact probe in
**0.055 seconds**; graceful private-daemon shutdown stops/reaps its next owned
probe in **0.015 seconds**. Both checks require the probe PID to be absent from
`/proc`, including zombies, with no external gate release and no downstream
build/emission/physical events.

The daemon deliberately preserves SIGTERM exit semantics after its shutdown hook
(`daemon/main.ml` uses `Shutdown.shutdown_with_signal_exn`), so Python reports
**-15**, not zero. The first extra probe harness incorrectly expected zero and
marked its aggregate failed despite successful cleanup. That assertion was
corrected to the documented signal semantics and only the probe check was rerun
in a fresh isolated tree. The final comprehensive receipt transparently imports
the already-passing suite/build records and retains the obsolete harness failure
under `historical_probe_harness_failure`; it does not relabel the old receipt or
repeat the unaffected suites. Reproducible orchestration is retained at
`/tmp/opencode/workbench-fresh-final-run.py`.

All final fixtures are isolated, and no provider selections, deployed binaries,
runtime pointers, real examples or live user sessions were changed.

## Inspected reusable fixtures

| Existing source | Reuse | Necessary adaptation |
| --- | --- | --- |
| `scripts/test-launch-stage-consistency.py`, `PrivateDaemon` | Native daemon on port zero, private discovery/state, HTTP request history, owned process shutdown and restart | Add endpoint assertion excluding port 41735; retain all restart request histories and binary hashes |
| `scripts/test-frontend-composition.py`, `Terminal`, `Screen`, `wait` | Real client PTY, palette/keyboard actions, ANSI/text/cell/SVG evidence | Use A/B's actual launch labels and linkage; avoid the composition harness's legacy physical-launch assumptions |
| `demo/synthetic_flow/http_client.py` and `scripts/real-asic-example-demo.py`, `Client` | Existing native S-expression HTTP and workspace mutation transport | Use only its transport; no real-example inventory, provider, or canonical evidence access |
| `scripts/synthetic-flow-demo.py`, `prepare` | Private source project, synthetic catalog and historical observation seed | Install a test-local direct-`stages` provider wrapper; never change shared demo or example provider configuration |
| `demo/synthetic_flow/provider.py` | Observation allocation, structured physical stage prefix, stream updates, report and terminal reconciliation | Existing dispatch supports `flow run`, **not direct `stages`**; adapt a private copy/wrapper without invoking or rerendering through `flow run` |
| `scripts/fixtures/preparation_publisher.py` | EDA-less `flow emit`, bundle manifest/configuration hashes, exact plan identity and receipt | Existing plan uses `stages=[endpoint]`, so CTS needs a test-local complete-prefix plan; retain original publisher for standalone regression |
| `scripts/test-preparation-frontend.py` | Standalone build/emission setup and same-selection pinned-preview mismatch regression | Migrate staging/lineage/timing to unified workflows; preserve all four standalone preview-ownership routes and strict explicit mismatch |

The existing publisher deliberately produces a different methodology identity from
the pinned synthetic executable for the same selection. The new fixture must
preserve and explicitly assert this distinction. A test using the same pinned
identity would miss the old source/pinned-plan mismatch.

## Implemented fixture

All files and evidence go in a newly created `/tmp/opencode/unified-fresh-prefix-*`
tree. Each independently configured scenario gets private source, HOME, XDG
configuration/state, daemon state/discovery, results and checkpoint directories.
The daemon binds port zero. Validate the discovered endpoint is loopback and is
not port 41735 before any HTTP call. Cleanup targets only process objects/groups
created by this fixture. Record their ownership, termination and reap evidence.

The fixture uses a synthetic source publisher and physical provider only. The provider's
`flow run` branch records the attempted bypass and fails closed. Its direct
`stages` branch records actual argv, input paths, plan bytes/SHA-256, selected
bundle identity and stage prefix before allocating an ordinary observation. It
must independently validate the manifest, plan identity and expected identity;
the physical observation must use that plan rather than call the pinned planner.
Read-only pinned preview/catalog calls remain available and separately logged.

The fixture's source build target records each actual build-rule execution and
can fail or hold. Incremental builds may legitimately skip that rule: assertions
must also inspect each workflow's distinct build job and completed build-before-
emit ordering. Emission records every invocation and can fail, hold, return a
malformed receipt, or emit an explicit identity mismatch. Identical bundle bytes
may be reused across separate submissions. Count invocations, not directories.

Use bounded file gates for deterministic race windows, with entered/release
receipts and producer PID/group facts. Avoid sleep-only races. A gate whose
boundary the public API cannot expose must be reported as untested, rather than
represented by a nearby cancellation. Release gates and reap owned processes in
`finally` paths, including assertion failures.

## Acceptance matrix

This is the feature-level matrix; the coverage limits below distinguish the
implemented script from additional backend-only fault and scheduling checks.

| Scenario | Required assertions beyond successful exit |
| --- | --- |
| Fresh Synthesis and CTS | Distinct workflow and preparation per submission; completed build precedes emit and provider admission; receipt bundle/plan identities equal direct provider inputs; immutable plan bytes and SHA-256 match; physical recipe is exactly synthesis or synthesis/floorplan/placement/CTS; zero pinned `flow run` and zero second render |
| Standalone Elaboration | Build plus one emission, completed exact bundle receipt, no physical admission; same-selection pinned preview identity differs and is not implicitly imposed |
| Repeated fresh launch | New key creates new workflow, build job and emission, even when bundle bytes/output are reused |
| Same-key replay and conflict | Active, terminal and restarted retries retain workflow/preparation/run identities and producer counts; conflicting selection or captured scope rejects explicitly |
| Preparation failure | Build failure, emit failure, malformed/invalid receipt, explicit expected-identity mismatch and missing preparation configuration each retain honest diagnostic/lineage and admit no physical process |
| Scope and persistence failure | Exercise A's supported capture/persistence fault seams; changed source/profile/provider scope cannot silently retarget a captured intent; failed durable admission cannot start a producer |
| Cancellation | Gate build, emit, queued preparation, post-emission/prephysical handoff and allocated physical execution where supported; cancellation latches, owned work stops/reaps, releases cannot start later work, terminal evidence remains cancelled |
| Source-root serialization | Hold one source build/emission while submitting standalone and chained preparation; prove no overlapping source-root producer intervals and cancellation of queued work prevents its producer start |
| Restart | Restart private daemon with completed, failed and interrupted workflows; compare durable lineage and producer counts; replay/read/observe do not rerun source or physical work; unresolved ownership is explicit |
| Selected-run linkage | Keep an older successful physical run selected while a later standalone preparation fails or is cancelled; its Elaboration remains tied to its own preparation; historical unlinked runs show unavailable rather than borrowing latest preparation |
| Real PTY entry paths | Exercise stage `r` plus manual launch, checklist `R`, named palette launch and selected-stage palette launch; each creates one daemon-owned chain; standalone Elaboration remains emission-only |
| PTY progress and context | Capture Elaboration before physical allocation, then linked physical stages; cancel from actual UI; focus/selection change during async planning cannot retarget launch-and-view; tile bindings and saved provider selection survive |

For each case retain raw HTTP requests/responses, provider/source event JSONL,
exact receipt and immutable plan bytes, daemon logs, final snapshots, binary
hashes and per-assertion `result.json`. PTY cases also retain key logs, ANSI,
current-screen text, cell data and SVG. On failure record the exception and case,
persist evidence before cleanup, and exit nonzero. Diagnostic subsets must identify
themselves as partial, never full acceptance.

## Contract and ownership

The frozen HTTP operation mapping is now known:

```text
Stage_fresh (selection S) (elaboration_only false) (expected_plan_identity ())
Launch_fresh (key K) (intent_id I)
Cancel_workflow WORKFLOW_ID
```

These are S-expression variant constructors with the usual outer parentheses,
not new endpoints. Use the existing ASIC RPC. `Get.fresh_intent` returns the
staged input intent; `Get.workflows` is newest-first. Match by key/id before
allocation, then exact `workflow.run`, never by latest preparation. Inspect
`phase`, `preparation_id`, `elaboration_status`, session-only build/emission jobs,
`prepared`, `reference`, and `error`. Prepared data includes bundle directory,
bundle/plan identities, immutable methodology-plan path and digest. Replay the
original key/intent pair after restart; do not stage a replacement for a replay.
Ordinary fresh staging has no expected identity; an explicit option is strict.

A owns protocol/backend/adapters and `backend/test/fresh_provider.py`; the latter
is copied into each private fixture and reused for observation/report envelopes.
C's wrapper additionally verifies canonical plan and methodology identities,
bundle identity/member hashes, configuration bytes, full recipe prefix and the
configured tool paths/timeout before admission. Historical seeded observations
use a private copy of the existing synthetic provider. All pinned calls are
logged, and pinned `flow run` fails closed.

B owns terminal dispatch and presentation. C changed no backend, protocol,
adapter, terminal or example files. Existing standalone/checklist script expectations
were subsequently migrated as described below. Product
reproduction failures belong to A/B/coordinator; fixture failures are retained
with their raw evidence.

## Coverage limits

- Script-level failure coverage: build, emission, malformed receipt, explicit
  expected-identity mismatch, missing preparation configuration, actual ASIC
  configuration drift, and provider executable-generation drift.
- Script-level cancellation coverage: held build, held emission, source-root
  queued preparation, completed preparation waiting on the physical throttle,
  and allocated physical cleanup. Entered/stopped events and exact stream IDs
  provide cleanup evidence. The internal asynchronous reservation/import windows
  are not independently gated by this HTTP fixture.
- Script-level replay/restart coverage: active build/emission replay, terminal
  replay, consumed/conflicting intent rejection, successful/failed history across
  graceful restart, and held emission across an unclean daemon crash. Interrupted
  ownership is explicit; replay/cancel cannot start another producer.
- The source-root queue test checks two chained workflows. Mixed legacy
  standalone/chained/generic source transactions and injected durable registry
  persistence failures remain A's backend tests, as recorded in the final handoff.
- PTY coverage uses manual `r` plus launch, checklist `R`, named and selected
  palette shortcuts, named standalone Elaboration, cancellation, preallocation
  progress, old-run linkage after later standalone failure, historical unlinked
  unavailability, and changed-context guarded view-on-allocation. This fixture
  does not claim every layout, compression preference or local-cursor race.
- These are orchestration tests. The source emitter and physical results are
  synthetic; no real synthesis/P&R or EDA-result correctness is claimed.

## Build and execution discipline

Every Workbench Dune build, including nested fixture source builds, uses explicit
`-j6`, `scripts/with-switch.sh dune`, and the shared
`/tmp/opencode/workbench-fresh-prefix-build.lock`. The private daemon's inherited
PATH resolves Dune through a test-local wrapper that enforces `-j6` for builds and
takes the lock before entering the switch. Read-only `--version` and workspace
description probes also take the lock; their CLI does not use the build job flag.
Setup waits for the lock before the bounded open-project HTTP request. Preparation
timeout is 180 seconds to accommodate concurrent owner builds. Do not
hold the lock around an entire acceptance run: a nested daemon build would block
on that lock.

Example coordinator-approved matching binary build (from Workbench root):

```sh
flock /tmp/opencode/workbench-fresh-prefix-build.lock \
  scripts/with-switch.sh dune build -j6 \
  daemon/main.exe terminal/main.exe terminal/workspaces/export_presets.exe
```

Run the complete matrix:

```sh
python3 scripts/test-unified-fresh-prefix.py \
  --daemon _build/default/daemon/main.exe \
  --client _build/default/terminal/main.exe \
  --preset-export _build/default/terminal/workspaces/export_presets.exe
```

`--http-only` and `--pty-only` select explicitly partial diagnostic runs. Each run
requires a new evidence directory; the default creates one under `/tmp/opencode`.
The test itself performs no Workbench binary build. It uses real isolated Dune
source builds through the daemon. Full evidence includes binary/fixture SHA-256,
per-assertion results, native HTTP, producer events/receipts, immutable plans,
restarted snapshots and actual PTY ANSI/text/cells/SVG captures. Useful frontend
captures include `pty/pty-manual-preallocation.*`,
`pty/pty-standalone-same-selection-pinned-preview.*`,
`pty/pty-selected-run-lineage-after-standalone-failure.*`, and
`pty/pty-focus-guarded-after-completion.*`.

The prior standalone harness has now been migrated and rerun as described below.
No real synthesis/P&R, live-daemon access, deployment, example edits, provider
pointer changes or git mutation are part of this acceptance.

## Historical broader Workbench and harness migration follow-up

Both full Dune commands completed with **exit 0**, under the shared lock, with a
20-minute command budget each:

```sh
flock /tmp/opencode/workbench-fresh-prefix-build.lock \
  scripts/with-switch.sh dune build -j6 @runtest @all @lint
flock /tmp/opencode/workbench-fresh-prefix-build.lock \
  scripts/with-switch.sh dune runtest -j6 --force
```

The second command explicitly reran test aliases rather than relying on cached
success. Output included supervisor cancellation/descendant cleanup, FIFO and
submission keys, RTL/provenance retrieval, protocol wire validation, timing and
inspection scheduling, frontend fresh-process retention, FS2 simulation, and
both `Unified fresh synthesis` and `Unified fresh cts` backend suites. The two
Python groups reported 10 and 6 tests, both OK. No source/test failure occurred
in these Dune runs. This is a full build/test/lint pass, not a `@fmt` claim.

Existing script migrations:

- `scripts/fixtures/fresh_frontend.py` supplies private daemon/state, inherited
  environment, matching client, synthetic historical reference, and shared-lock
  nested Dune builds. Legacy generic build requests are normalized to `-j6` by
  the **private** Dune wrapper; no production adapter change is made.
- Preparation now stages through ASIC `Stage_fresh`, resolves preparation
  attempts by the workflow's exact `preparation_id`, and shows standalone timing
  in workflow detail. Historical selected-run Elaboration correctly remains
  unavailable. Build/emission log inspection and exact artifact selection remain
  asserted; long artifact palette titles are checked using their identifying
  prefix/query suffix rather than requiring clipped text to fit.
- Checklist catalog/default/profile/rejection cases now use a synthetic catalog,
  with no real-demo inventory. `r` captures inputs, and explicit launch runs one
  source chain followed by exact direct stages. Failed/pending replacements still
  block launches. No-view preference persistence, named action withdrawal, source
  failure and changed-context behavior remain checked.
- Selected asynchronous cursor/action/capability tests use a bounded transparent
  loopback proxy holding the **actual daemon Stage_fresh response**. Requests and
  replies are byte-for-byte forwarded and retained. This replaces the obsolete
  pinned `Plan` subprocess gate without inventing protocol replies or disabling
  stale-action checks. Proxy worker count is bounded at six.

The following table predates the final A/B corrections and is retained as history;
the final passing receipts above supersede its preparation failure.

| Earlier run | Actual outcome at that time | Historical evidence |
| --- | --- | --- |
| Complete migrated checklist synthetic matrix | **PASS, 83 assertions**, exit 0 | `/tmp/opencode/checklist-workflow-0beba163e91c/result.json` |
| Migrated preparation frontend | **FAIL, 36 passed / 1 failed**, exit 1; all independent cases completed | `/tmp/opencode/wb004-frontend-1077371092f8/result.json` |
| Unified HTTP + PTY after shared-fixture change | **PASS, 99 assertions**, exit 0 | `/tmp/opencode/unified-fresh-prefix-542d250e2880/result.json` |

The earlier preparation failure is retained as a failing assertion and nonzero suite
result. A new client was used only **after recording the failure**, so the remaining
independent regressions can execute. In particular, manual Elaboration launch,
Elaboration `R`, named palette Elaboration and selected-stage palette Elaboration
all preserve the same-selection pinned-preview independence and leave the pinned
preview intact. Explicit stale expectation still fails publication validation.
Generic RTL separation, exact logs/artifacts, live and frozen duration,
reconnect-without-replay, cancellation and historical physical immutability pass.

### Corrected source recovery defect — historical reproduction

This defect occurred on the earlier binary hashes recorded in the old individual
receipts. It no longer reproduces on the final matching pair. Its historical
reproduction used the preparation command below:

```sh
python3 scripts/test-preparation-frontend.py \
  --daemon _build/default/daemon/main.exe \
  --client _build/default/terminal/main.exe \
  --preset-export _build/default/terminal/workspaces/export_presets.exe
```

1. Select Elaboration, press `r`, and open the captured manual-launch palette.
2. Through the ordinary native ASIC API, supersede that unlaunched intent with a
   new `Stage_fresh` using the same selection and no expected identity.
3. Accept the old captured action. It correctly starts no workflow or producer.
4. Close the palette, press `r` again, and verify the daemon returns a distinct
   current input intent. Reopen manual launch.
5. **Earlier defect:** the same client still advertised Launch as `[Fresh intent
   unavailable or superseded…]`, despite the newly staged intent. No workflow
   starts. A fresh client plus fresh staging recovers.

Primary capture:
`/tmp/opencode/wb004-frontend-1077371092f8/native/restaged-intent-launch-eligibility.txt`
(also `.ansi`, `.cells.json`, `.svg`). Nearby `superseded-stage-rejected.*`,
`fresh-client-recovery-for-independent-cases.*`, raw HTTP, keys and final snapshot
provide the ordering and identity evidence. The likely review area is unresolved
launch-intent state versus `Planned_run.fresh_launchable`; root cause is not claimed
as proven. C did not edit the frozen terminal/backend source.

**Final status: corrected.** B's fix is verified by the final preparation 37/37
result, including same-client recovery with the stronger same-selection,
different-scope replacement. The final matching binaries and all requested focused
and broad checks are complete. No additional source edits were made by C.
