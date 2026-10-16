# FS1 — ASIC evidence investigation: implementation and acceptance

**Historical slice record.** The subsequent [FS1 investigation completion](fs1_investigation.md)
delivers the timing-path, measured-clock, physical/routing and binary-handoff work
listed as remaining here. Its final provider generation and verification record
own the current adopted-evidence completion status; the evidence below is preserved.

Recorded 2026-10-15 from current Workbench code and retained evidence.
**FS1 is substantially delivered, with bounded aggregate investigation and real
physical/acceptance/cancellation evidence; the full normative FS1/F06 scope is
not complete.** Rich timing paths, measured clock/CTS investigation, congestion,
and richer routing/binary artifact investigation remain gaps.

**Later followup:** [finalization lifecycle and bounded artifact viewing](fs1_lifecycle_and_artifacts.md)
are now implemented and verified. The original read-only-import scope described
below is retained as the evidence record for that earlier slice; it is no longer
the only way to operate finalization or view its reports in Workbench.

This record extends [FS0 acceptance](fs0_acceptance.md) and the
[cached synthesis inspector](synthesis_inspection.md). The desired scope remains
[FS1](feature_sets.md#fs1--asic-evidence-investigation) and
[F06](features/hardware_inspection.md); the delivered slices below do not replace
those requirements.

Final parent verification passed: serialized format/lint, full build, full
`dune runtest -j20`, and installed native lifecycle/discovery/RTL/hierarchy/resize
checks. The full suite's existing Git provenance fixture operates only in its
new temporary project; inherited Git selectors/configuration were cleared before
running it. No live-checkout Git mutation was performed.

Latest actual frontend results: synthesis metrics
`/tmp/opencode/workbench-fs1-metrics-c00xpq9e`, accepted physical import
`/tmp/opencode/workbench-fs1-terminal-results-5yvke5ek`, existing synthesis inspector
`/tmp/opencode/workbench-synthesis-inspector-xf0ihqfd`, and all five interrupt modes
`/tmp/opencode/workbench-terminal-interrupt-rxwy7wd1` passed. The latest physical
PTY adds Unicode input/backspace, bracketed reference paste, and immediate reverse
scrolling after overscrolling the bottom.

## Delivered implementation

### Synthesis resources and diagnostics

`backend/asic_public.ml` projects only the checkpoint explicitly identified by
`reference.boundary = synthesis`. No checkpoint means unavailable synthesis
data; multiple synthesis references are rejected as ambiguous. Cell totals,
type inventory, metrics and producer context all use that same checkpoint.
The last checkpoint of a physical execution is **not** synthesis: the real
balanced specimen has **673 synthesis cells**, whereas later routing/signoff
accumulated counts can be **1042**. Those later counts must not replace 673.

The stage-summary projection recognizes exactly these eight raw keys:

| Raw key | Display | Required unit |
| --- | --- | --- |
| `design__instance__area` | Mapped cell area | `µm²` |
| `design__instance__count` | Mapped cells | `cells` |
| `design__instance_unmapped__count` | Unmapped cells | `cells` |
| `synthesis__check_error__count` | Synthesis check errors | `count` |
| `design__inferred_latch__count` | Inferred latches | `count` |
| `design__lint_error__count` | Lint errors | `count` |
| `design__lint_warning__count` | Lint warnings | `count` |
| `design__lint_timing_construct__count` | Lint timing constructs | `count` |

Available values require the recognized unit and finite nonnegative numbers;
counts must be integral. Missing, malformed, negative or wrong-unit values are
unavailable, never manufactured zeros. Unknown keys are not assigned guessed
semantics. Every projected metric retains the full supplied source JSON.
`Summary.producer` retains checkpoint reference and `metric_origin` context.
These are accumulated **checkpoint-boundary snapshots**, not per-tool-step
measurement attribution. The provider's original availability/raw wrappers and
source identity remain inspectable.

The synthesis table, literal case-insensitive filter, sorting, row count/share,
full evidence, tile-local state and pin/follow behavior remain available.
`m` and **Synthesis: Inspect metrics** add a scrollable resource/diagnostic page.
Legacy summaries without metrics explain that explicit Refresh is needed;
opening the page does not refresh automatically. Before terminal import, Checks
can show synthesis diagnostic counters with an explicit distinction from DRC/LVS.
Zero synthesis diagnostic counts do not establish signoff or acceptance.

### Explicit read-only finalization import

`Asic.Operation.Inspect_finalization { run; attempt }` adopts an **existing exact
returned operation attempt**, using public `finalization-inspect ATTEMPT --json`.
It does not run `finalize`, perform collection, request acceptance, launch EDA or
guess the newest operation. `adapters/asic_adapter.ml` contains the read-only
inspector invocation; there is no Workbench finalization producer operation.
The installed contract remains exact **CLI4 + `namedflow1=true`**.

The import observes the registered execution, reads its stage report, inspects
the explicit operation and verifies referenced execution/results bytes. In
`backend/asic_public.ml` and `backend/asic_service.ml`, validation includes:

- Absolute attempt (at most 4096 bytes), exact execution path, raw-byte SHA-256
  and implementation stream/attempt identity.
- Structural equality of report execution and hashed execution contents, independent
  of JSON object-member order. Direct file reads open nonblocking, validate the
  opened descriptor as a regular file, and read bounded bytes from that descriptor.
  This avoids a pathname replacement with a FIFO blocking import. These are local
  regular-file reads, not a hard deadline guarantee for stalled remote filesystems.
- Terminal operation status and end time; `completed` iff exit code is zero.
- Ordered selected checkpoint path/identity/boundary agreement between receipt,
  stage report and hashed execution artifacts.
- Results schema 1, exact results SHA-256, operation provenance path, operation
  ID (`results.run_id`) and build/bundle identity. The finalization operation ID
  and implementation stream ID are distinct and both retained.
- `completion.physical = full` requires selected signoff evidence, a completed
  execution and a completed, exit-zero `implementation.signoff` occurrence.
- Evaluated acceptance requires an explicit `request.accept = true`; `pass`
  additionally requires completed operation and completed external postcheck.
- Publication is rejected if observation cursor/execution reference advanced
  during the read or cancellation occurred before publication.

A failed acceptance operation can still have valid results and be imported.
Successfully importing a `fail` verdict is a successful read, not an acceptance
pass. Invalid imports preserve prior cached evidence with `Refresh_failed`
freshness rather than publishing an unearned new result.

The last successfully adopted attempt is persisted per run. Explicit **Refresh
evidence** revalidates that attempt as well as stage evidence. Ordinary
`Load_summary` may reuse L1/L2 without provider access. It does not discover newer
finalization attempts. Restarted L2 data is `Cached_unverified`, preserving
original observation time and evidence identity. Missing source and failed
refresh have explicit freshness states.

### Terminal timing, checks, physical resources and declared clocks

`protocol/asic.ml` adds typed metric/check records and optional
`Summary.terminal`. `terminal/terminal_result_view.ml` renders the shared imported
result through timing, placement, checks, CTS, routing and finalization tiles.

| Tile | Actual current view |
| --- | --- |
| Timing | Aggregate signed setup/hold slack, as reported in ns; full corner/mode/source context in Details |
| Placement | Aggregate final standard-cell area and utilization; explicitly not placement-stage evidence |
| Checks | Independent reported DRC/LVS/antenna statuses, reasons and complete source context |
| CTS | Declared clock period from recorded historical configuration; explicitly not measured CTS |
| Routing | Explicit unsupported/not-reported routing-stage detail, plus imported outcome context |
| Finalization | Imported terminal operation, completion, acceptance, timing goal and metrics |

Terminal projection recognizes setup/hold slack, mapped/sequential area, mapped
cells, final standard-cell area, final utilization and three synthesis counters
(`unmapped_instances`, `synthesis_errors`, `inferred_latches`). Slack is **signed**;
other numeric values are finite/nonnegative, counts integral. Values require
exact recognized units and an explicitly null `unavailable_reason`. Absent keys
are not invented; supplied invalid/unavailable metrics retain their source and
show unavailable. Checks use supplied `pass`/`fail`/`unknown`, not a Workbench
zero-count-to-pass rule. Unknown or absent check status is unknown.

Full metric/check provenance includes operation attempt, operation path, results
path/SHA-256, field name, resolved source and the complete supplied object:
definition, tool/version, stage, corner, mode, raw values and origin boundary.
Relative sources resolve against the operation attempt. `origin_boundary:
signoff` denotes the accumulated publication, not proof that signoff freshly
measured every value. Workbench does not relabel this as an inferred OpenSTA or
OpenROAD step. Complete operation/results JSON, errors and postcheck detail are
retained in terminal evidence, not elided to fit overview rows.

Declared clock import independently reads the historical methodology-plan
snapshot referenced by the stage report. It verifies raw-byte SHA-256 and binds
plan, bundle, report, operation and implementation identities before decoding
`configuration_bytes`. `CLOCK_PORT` must be nonblank and `CLOCK_PERIOD` finite,
numeric and positive in ns. Provenance retains the snapshot reference/hash,
configuration bytes, fields and `resolved_settings`. Missing historical reference
produces explicit unavailable evidence; incomplete or mismatched references fail
validation. Current project configuration or a current preview is not substituted.
No measured frequency, clock inventory, skew, insertion delay or CTS coverage is
inferred from the period.

Execution completion, physical completion, collection operation status, timing
goal, individual check statuses, external postcheck and acceptance are separate
facts. The legacy stage-summary `timing` remains `[]`, and stage-summary
acceptance remains the stage report's `not_evaluated`, even when imported terminal
acceptance is `pass` or `fail`.

## Controls and exact-reference CLI

Open **Space c c** for the palette. Use **Add ... tile** commands to mount
the desired kind, Tab to focus, and **Zoom focused tile** for long evidence.

| Input / command | Effect |
| --- | --- |
| `m` on Synthesis / **Synthesis: Inspect metrics** | Synthesis metrics page |
| Enter / `e` on a terminal-result tile | Full context and evidence |
| `j` / `k`, down / up, `[` / `]` | Scroll terminal-result content |
| Esc | Return to terminal-result overview; synthesis navigation follows its own modes |
| **Inspect finalization for asic/… (enter exact attempt)** | Open `INSPECT FINALIZATION` argument form for that captured run |
| Enter in that form | Dispatch the exact attempt text; blank input is rejected |
| Esc in the form | Dismiss without import |
| UTF-8 typing / bracketed paste in the form | Enter printable exact path text; Backspace removes a codepoint; Enter after paste submits |
| **Refresh evidence asic/…** | Explicit read-only source revalidation, including adopted attempt |

The form captures project/workspace/context/run targeting and rejects stale
command capture; it never silently retargets the newly selected run. The backend
requires an absolute reference. Enter the returned **attempt directory**, not a
guessed execution/results path. Terminal detail/scroll state is local to each
tile and reconciles when run, summary digest or terminal result identity changes.
Pinned tiles retain their run while following tiles respond to context selection.
Reference input is bounded to 4096 bytes at UTF-8 boundaries; newline/control input
is rejected. Ordinary tile paste still suppresses commands, and Ctrl-C precedes all
modal/paste handling. Scrolling clamps stored offsets to current viewport geometry,
so reversing at the bottom moves immediately, including after resize.

The native API exposes the same operation through `--asic-operation`. For an
attached daemon, first use Get to obtain the exact current registered `Run_ref`;
set `URL`, `ROOT` and `RUN_REF` accordingly (the latter is the complete returned
S-expression, including build/label fields). These are reusable commands, not
commands executed by this documentation pass:

```sh
scripts/with-switch.sh timeout 120s _build/default/terminal/main.exe \
  --api --plain --project-root "$ROOT" --connect "$URL" \
  --asic-operation Get

scripts/with-switch.sh timeout 120s _build/default/terminal/main.exe \
  --api --plain --project-root "$ROOT" --connect "$URL" \
  --asic-operation "(Inspect_finalization (run $RUN_REF) (attempt /tmp/opencode/workbench-fs1-physical-w0rftdi0/operations/20261015T195210937702Z_3fa714bd))" \
  --wait
```

An unregistered execution is adopted with `Register` using its exact returned
`(attempt ...)(stream_id ...)` observation reference first. Do not fabricate a
`Run_ref` or use a finalization operation as an observation allocation. Requests
are bounded/coalesced background work. CLI wait watches the exact
`finalization:RUN_ID:SHA256(ATTEMPT)` task, so a previous import cannot satisfy a
new attempt's wait. Check command exit status and operation errors as well as
the returned snapshot. Read-only describes provider effects: import/selection
still updates Workbench's own registry, cache and workspace state.

## Cache compatibility: direction and semantic repair

Current Workbench **reads v1–v4 summary blobs and writes v4**. Registry persistence
is still version 1, with default-empty `terminal_attempts`; summary blob versions
are distinct from provider CLI4, results schema 1 and workspace schema 1.

| Summary blob | Current reader behavior |
| --- | --- |
| v1 | Defaults absent metrics to `[]`, terminal to `None`; verifies the original digest with both fields omitted |
| v2 | Preserves metrics, defaults absent terminal to `None`; verifies original digest with terminal omitted |
| v3 | Verifies full summary digest; terminal records may predate declared-clock evidence |
| v4 | Current full digest and explicit synthesis-boundary projection |

For **every pre-v4 blob**, if producer JSON does not explicitly identify a
synthesis boundary, the reader clears `cell_count`, `cells` and synthesis
`metrics` and labels producer `no synthesis checkpoint in legacy projection`.
Before v4 the last checkpoint could have been projected as synthesis on a physical
run. Clearing those fields prevents displaying old routing/signoff data as
synthesis. Explicit Refresh recovers the actual synthesis checkpoint from the
full public report. Valid legacy synthesis caches retain their 673/685 totals;
legacy terminal evidence is not fabricated or silently enriched with a clock.
Corrupt/incompatible entries fail validation and can be rebuilt by a bounded
read of provider evidence.

**Compatibility is new-reader → old-cache, not old-client → new-daemon/cache.**
The new `metrics`/`terminal` record fields and `Inspect_finalization` constructor
change derived sexp/bin_io shapes. No old-client compatibility negotiation or
down-conversion was added. Old readers do not acquire v4 support merely because
new readers support v1; old decoders can reject new fields/versions, and binary
record shapes also changed. Use matching rebuilt client/daemon binaries and do
not treat newly written v4 state as backward-readable by an older Workbench.
The earlier synthesis-inspector-only statement that its wire/cache shape stayed
unchanged does not extend to this later protocol change. This is an actual
compatibility limitation, not a generic upgrade warning.

Budgets remain explicit: four concurrent queries and one execution; report
queries have 30-second budgets; L1 holds 32 summaries and L2 indexes 128.
Normalized summaries are bounded to 256 KiB, synthesis cell rows to 4096 and
metric lists to 64. Import reads execution up to 8 MiB, results up to 128 KiB,
historical clock snapshot up to 256 KiB and full terminal evidence up to 160 KiB.
These bounds do not implement a rich paginated path/artifact database.

## Retained real evidence

All paths below are exact local evidence namespaces under `/tmp/opencode`.
They are historical observations, not results generated while writing this file.

### Physical failure followed by successful physical collection

1. **Failure:** `/tmp/opencode/workbench-fs1-physical-kzkr6vl_`.
   The original example launcher used the provider-default **600-second signoff
   segment timeout**; the log reached **Magic.DRC** before timing out. Physical
   client exit was 1 after `772.7699260770023` seconds. This was not the outer
   3600-second harness deadline. Synthesis, floorplan, placement, CTS and routing
   checkpoints survived; no completed signoff checkpoint or terminal finalization
   result was manufactured. `physical.json`, `physical.stderr` and the retained
   signoff log establish the failure and earlier evidence.
2. **Success:** `/tmp/opencode/workbench-fs1-physical-w0rftdi0`.
   A new timeout-capable example launcher at
   `/tmp/opencode/fs1-timeout-project-SAuuX0/build/default/bin/project.exe`
   forwarded stage timeout **2400 seconds**. Standard/balanced through signoff
   completed; physical client exit 0, `1651.396923591994` seconds, outer budget
   3000 seconds (headless budget 2940). Collection-only finalization completed
   in `18.537607398000546` seconds with budget 300. Both acceptance and external
   postcheck remained **`not_evaluated`**.

Both used the unchanged installed provider
`/tmp/opencode/namedflow-real-20261015/provider/bin/hardcaml-asic-flow`, SHA-256
`2c6604d355b819ee5cec8f731b4ba810ea9415ebf56f24ebac798a8d346bcdd5`.
The successful launcher SHA-256 is
`891fd3fd208bc234a00bb3cbf4f8309a72eb95f6ea83cdd8f92ef3355d7fb7bb`.
The expanded provider/example/physical permissions supported this parent-owned
work; no provider implementation change or reinstall is currently needed. Provider
documentation explains the existing public route in
`../hardcaml_asic/docs/development/workbench-terminal-contract.md`.

Successful exact identities:

```text
implementation stream: 965b68b0f7454e14bc7d6f12f32ab9c7
execution:
  /tmp/opencode/workbench-fs1-physical-w0rftdi0/results/signoff-777507-32d94e083532545001af7184276233f2/execution-965b68b0f7454e14bc7d6f12f32ab9c7.json
execution SHA-256:
  9c6a95c0a64ac0287425974ba5573c1c2d68a6a11c043f2ee95ff491f2d81a12
collection attempt:
  /tmp/opencode/workbench-fs1-physical-w0rftdi0/operations/20261015T195210937702Z_3fa714bd
results SHA-256:
  2898d35a1f7c2c63f335952c7dad744fe0390367b0cfd81b3169911db92b17d0
plan identity:
  1d4fc38c4c8ea114df2f44f9fc3cb304a8e7e20af72a044861db7c65a5bb8334
bundle identity:
  253882b0dc91a9882800cd6f6d436e09cac6894e6beb9589c8126ef9c15c8122
```

`summary.json`, `stage-report.json`, `operation.json`,
`normalized-results.json` and `workbench-inputs.json` preserve the handoff. Original
provider references remain authoritative; copied JSON is evidence, not a new
provider execution.

### Actual values and their scope

The successful collection results and verified historical clock evidence contain:

| Fact | Exact value | Scope / source |
| --- | --- | --- |
| Setup slack | `11.67551954830797 ns` | Worst reported corner `nom_slow_1p08V_125C`, setup, final metrics CSV |
| Hold slack | `0.12502899069955042 ns` | Worst reported corner `nom_fast_1p32V_m40C`, hold, final metrics CSV |
| Mapped cell area | `13041.6048 um^2` | Synthesis-state evidence, `nom_typ_1p20V_25C` |
| Mapped cells | `673` | Synthesis boundary, not final routing count |
| Sequential area | unavailable | Provider reason `report absent or metric missing` |
| Final standard-cell area | `18916.9 um^2` | Final accumulated physical evidence |
| Final utilization | `0.0209625 fraction` | Ratio as supplied, no percent conversion |
| Unmapped instances / synthesis errors / inferred latches | `0 / 0 / 0 count` | Synthesis counters, independent of signoff checks |
| DRC / LVS / antenna | `pass / pass / pass` | Explicit normalized check statuses with raw counts/source retained |
| Timing goal | `pass` | Provider verdict, independent of acceptance |
| Declared clock `clk` period | `20.833333333333336 ns` (about `20.833333 ns`) | Historical configuration, not measured CTS |

Clock snapshot:
`results/observations/20261015T192439611662Z_965b68b0/methodology-plan.json`
under the successful physical root; SHA-256
`4118df2c7c0248d49359ead3e25f62a6a1fa63de6cf26220a010324fac7d604e`.
These positive slacks and passed checks did **not** make collection acceptance
pass: its receipt still says `not_evaluated`.

### External acceptance: failed harness setup and actual pass

Both acceptance operations used the exact completed execution above; neither
reran implementation.

| Evidence root | Operation | Acceptance / external postcheck | Interpretation |
| --- | --- | --- | --- |
| `/tmp/opencode/workbench-fs1-acceptance-r9ulvcwv` | `failed`, exit 1 | `fail` / `failed` | Harness Nix wrapper used unsupported `nix-shell --offline`; precheck/gate-level remained pending |
| `/tmp/opencode/workbench-fs1-acceptance-5oa67d8u` | `completed`, exit 0 | `pass` / `completed` | Actual external `precheck: pass` and `gate_level: pass` |

The first is an external acceptance setup failure, not evidence of a silicon
check violation. Its valid failed receipt/results remain importable and retained.
The successful rerun corrected only the harness's legacy Nix invocation: it used
the already cached commit-pinned nixpkgs source, disabled local/remote builds and
substitution, restricted evaluation/URI access and import-from-derivation, and
ran the real precheck/version checks. It did not replace precheck with a fixture
or modify the provider/support-tools implementation.

Successful acceptance attempt:
`/tmp/opencode/workbench-fs1-acceptance-5oa67d8u/operations/20261015T203811140090Z_3bbfa7f1`.
Results SHA-256:
`a6669783147e16800f09cd2b391a4edc5e02f8aa9c87db68b198300bf44d6db1`.
Finalization took `684.6940722269937` seconds within the shared 900-second harness
budget. `summary.json`, `postcheck.json`, `operation.json`, acceptance report and
command logs retain the actual verdicts. Trace export used the already built
`/tmp/opencode/fs1-timeout-project-SAuuX0/build/default/acceptance/export_trace.exe`
and `acceptance/replay.v`; the 292918-byte replay trace SHA-256 was
`90a0fb4d98dc6d63df5595423cd4a064257d94ef74c83ab0e14be1b389f178d9`.

### Actual HTTP + PTY + L2 import acceptance

The following are **harness PASS** results, including when the imported verdict
or execution itself is failed:

| Evidence root | Specimen / expected outcome |
| --- | --- |
| `/tmp/opencode/workbench-fs1-terminal-results-pd3q6grd` | Successful collection, acceptance `not_evaluated` |
| `/tmp/opencode/workbench-fs1-terminal-results-0xggpftj` | Failed physical execution, earlier synthesis retained, no terminal import |
| `/tmp/opencode/workbench-fs1-terminal-results-nlpv5k0x` | Successful external acceptance imported as `pass` |
| `/tmp/opencode/workbench-fs1-terminal-results-eovlncjw` | Failed external acceptance imported as `fail` |
| `/tmp/opencode/workbench-fs1-terminal-results-5yvke5ek` | Final accepted-result candidate, Unicode/paste and overscroll recovery |

Each `result.json` says `status: passed` and `input_files_unchanged: true`.
The failed-execution test logged four exact-reference read-only provider calls;
the three terminal imports each logged nine. Once warm, inspection/scrolling,
selection, pinning and restart/L2 reopening issued no provider queries.

The harness adopts original public allocations into a private daemon/project,
guards against producer commands and generic Dune actions, and drives a real
120×40 PTY over native HTTP. Assertions cover exact values/units/provenance,
independent outcomes, the actual palette argument form, all relevant tiles,
tile-local detail, clearing follow selection, retained pin, and full evidence
reachability through overlapping scroll pages. It independently validates the
historical clock snapshot bytes/hash/identities. After restart, every summary
field except freshness is preserved; both HTTP and the reopened PTY show
`Cached_unverified`. Layout/selection/pins restore exactly. These tests do not
launch implementation or finalization.

Retained earlier harness attempts include `workbench-fs1-terminal-results-hni54rru`
(metric-source assertion failure) and `workbench-fs1-terminal-results-gvl4csbj`
(interrupted during slow evidence scrolling). They are not counted as passes.

### Real cancellation and terminal-publication grace

Initial evidence `/tmp/opencode/workbench-fs1-cancellation-3q2dv3c4` **failed**:
the launcher's old five-second SIGTERM grace was insufficient for provider cleanup
and terminal outcome publication. A failed Workbench operation alone did not
establish a terminal provider receipt. The harness expired after
`140.14915599499363` seconds; eventual empty survivor lists did not turn it into
a pass. `workbench-fs1-cancellation-c4i10qng` separately records a harness null
outcome handling failure, also not a pass.

Current `backend/asic_service.ml` gives the **launcher 15 seconds** to stop;
ordinary queries retain the **five-second** default in `backend/asic_process.ml`.
This accommodates child termination, the provider's terminal-publication window
and serialization before escalation.

After evidence `/tmp/opencode/workbench-fs1-cancellation-nyiu2n23` **PASS** in
`20.93962658700184` seconds:

- Captured Discover/Describe/Plan over HTTP, launched one signoff request using
  the timeout-capable launcher and stage timeout 2400, then detached the Run client.
- Correlated the actual live EDA container with observation occurrence, transport
  request, image, workspace mount and owned daemon descendants before exact-key
  cancellation.
- Workbench launcher became failed/cancelled; provider published a non-successful
  interrupted/failed outcome with inactive writer and retained execution receipt.
- Transport receipt recorded interrupted process and successful owned-container
  cleanup; no later stage/transport started and signoff was not completed.
- PID/start-time checked descendants and owned containers were absent, stable
  for three seconds. No fallback signals or manual Docker mutations were used.
- Explicit read-only Observe reconciled the run; the daemon remained responsive
  to independent HTTP requests. Original inputs were unchanged.

This proves cancellation of a real owned active backend transport on a signoff
request, not cancellation at every physical boundary or an integrated finalize
lifecycle.

## Reusable verification commands and caps

Run from this repository root through `scripts/with-switch.sh` (default switch
`5.2.0+ox`). Commands below are instructions for subsequent verification; none
was run for this document. Use existing matching binaries for Python acceptance.
Run physical/acceptance/cancellation specimens strictly serially. All builds/tests
are caller-owned; no mutative Git, provider implementation edit or reinstall is
required for the current route.

Historical targeted fixture passes cover protocol round trips, boundary selection,
numeric/unit validation, terminal identity/hash/checkpoint rejection, clock
provenance/invalid constraints, v1–v4 reopening/repair, freshness, exact-attempt
wait and tile-local controls. Reusable focused and full-suite commands are:

```sh
scripts/with-switch.sh timeout 600s dune build -j20 \
  @protocol/test/runtest @backend/test/asic/runtest @terminal/runtest

# Parent full-suite rerun passed; isolate inherited Git environment for its disposable fixture.
scripts/with-switch.sh timeout 900s dune runtest -j20

# Separate synthesis-metrics acceptance also passed.
scripts/with-switch.sh timeout --signal=TERM --kill-after=20s 600s \
  python3 -B scripts/test-fs1-metrics.py --outer-timeout 90

scripts/with-switch.sh timeout --signal=TERM --kill-after=20s 600s \
  python3 -B scripts/test-fs1-terminal-results.py \
  --physical-evidence /tmp/opencode/workbench-fs1-physical-w0rftdi0

scripts/with-switch.sh timeout --signal=TERM --kill-after=20s 600s \
  python3 -B scripts/test-fs1-terminal-results.py \
  --failed-execution /tmp/opencode/workbench-fs1-physical-kzkr6vl_/physical.json

scripts/with-switch.sh timeout --signal=TERM --kill-after=20s 600s \
  python3 -B scripts/test-fs1-terminal-results.py \
  --physical-evidence /tmp/opencode/workbench-fs1-acceptance-5oa67d8u \
  --expected-acceptance pass

scripts/with-switch.sh timeout --signal=TERM --kill-after=20s 600s \
  python3 -B scripts/test-fs1-terminal-results.py \
  --physical-evidence /tmp/opencode/workbench-fs1-acceptance-r9ulvcwv \
  --expected-acceptance fail

scripts/with-switch.sh timeout --signal=TERM --kill-after=5s 175s \
  python3 -B scripts/test-fs1-cancellation.py --budget 165
```

The read-only metrics/terminal harnesses bound each native command with
`--outer-timeout` (default 90, allowed 1–300 seconds); the enclosing 600-second
timeout bounds the entire sequence and permits owned-process cleanup. They create
private state/config/guards and inventory original inputs before/after. The
metrics harness accepts `--source-state`, `--example-root`, `--client`, `--daemon`;
terminal acceptance additionally chooses exactly one physical-evidence or
failed-execution input and validates `--expected-acceptance`.

The existing metrics attempts `workbench-fs1-metrics-x_0w82ok`,
`workbench-fs1-metrics-nx66kac8` and `workbench-fs1-metrics-ukke0lzc` are failed
historical harness runs (PTY readiness; overly strict equality of dynamic run
fields after Refresh; outdated Checks wording). Current harness code checks raw
input readiness, exact allowed cursor/status/error evolution and revised Checks
wording. The subsequent separate metrics run **passed** at
`/tmp/opencode/workbench-fs1-metrics-c00xpq9e`.

Parent-owned physical/acceptance commands, when a fresh specimen is wanted:

```sh
scripts/with-switch.sh timeout --signal=TERM --kill-after=75s 3450s \
  python3 -B scripts/run-fs1-physical.py \
  --project /tmp/opencode/fs1-timeout-project-SAuuX0/build/default/bin/project.exe \
  --stage-timeout 2400 --timeout 3000 --finalization-timeout 300

scripts/with-switch.sh timeout --signal=TERM --kill-after=75s 1000s \
  python3 -B scripts/run-fs1-finalization-acceptance.py \
  --physical-evidence /tmp/opencode/workbench-fs1-physical-w0rftdi0 \
  --trace-exporter /tmp/opencode/fs1-timeout-project-SAuuX0/build/default/acceptance/export_trace.exe \
  --timeout 900
```

The physical harness accepts outer budget 61–3600 seconds, collection budget
1–1800, and an optional positive stage budget smaller than outer minus 60; the
successful invocation above used 3000/300/2400. It reserves 60 seconds from the
headless budget and 60 seconds for owned group cleanup before forced termination.
External acceptance uses a shared 120–900-second budget plus bounded cleanup,
existing collateral and cached Nix dependencies, with no fetch/install/build.
Cancellation uses a 120–170-second total budget with cleanup reserve and rejects
overlapping LibreLane/Hardcaml containers; fallback cleanup cannot count as pass.

The physical and external-acceptance harnesses set CPU affinity to at most 20 available CPUs and thread limits to
20 (`OMP_NUM_THREADS`, `OMP_THREAD_LIMIT`, `OPENBLAS_NUM_THREADS`,
`MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `RAYON_NUM_THREADS`, `NUM_CORES`,
`NPROC`, `OPENROAD_THREADS`, `_OPENLANE_MAX_CORES`; acceptance also
`NIX_BUILD_CORES`). The cancellation/HTTP harness's shared Session sets
`OMP_NUM_THREADS`, `OPENROAD_THREADS` and `_OPENLANE_MAX_CORES` to 20 for its
daemon; it does not itself set the physical harness's host affinity mask. The
installed provider supplies its 20-CPU/thread Docker limits. Dune commands use
`-j20`. Workbench's own execution queue remains one launcher and a
hard **1800-second shared launcher/automatic-observer deadline**, starting before
metadata and not reset by allocation; client wait is also bounded to 1800 seconds.
The direct parent physical harness's 3000-second budget does not change that
Workbench limit. Launcher/query stop grace (15/5 seconds) is distinct from stage
timeout and these outer harness budgets.

Evidence is retained on success/failure: exact argv/exit/duration/stdout/stderr,
provider query logs, raw ANSI and reconstructed screens, input keys, private
registry/L2/workspace state, input inventories, machine-readable results and
physical/operation/hash handoff manifests. These paths are local retained files,
not repository-distributed fixtures.

## Remaining normative gaps

- Rich setup/hold path tables, failing/near-limit path filters, corner/mode/group
  navigation, constraints/warnings, hierarchy expansion and paginated path detail.
- Structured declared/generated clock relationships and constraint coverage;
  measured CTS trees, insertion/skew and achieved-clock evidence. The single
  verified declared period is a useful delivered slice, not this full scope.
- Stage-specific placement quality, die/core/macro investigation and congestion;
  rich routing evidence, routing/congestion exploration and binary/graphical
  artifact viewers. The subsequent bounded text catalog/viewer and explicit
  terminal-host text handoff do not implement those richer viewers.
- Cancellation at every physical boundary and broader lifecycle races. The
  subsequent Workbench-owned finalize/accept lifecycle includes live progress,
  read-only reconnect, detach and actual external-postcheck cancellation coverage.

The defensible acceptance statement is therefore: **substantial FS1 aggregate
evidence investigation delivered, with real physical completion, explicit
acceptance pass/fail import, declared-clock provenance, cache reopening and real
owned cancellation proven in the retained specimens; full FS1 remains open.**
