# FS2 — Structured simulation, reruns and trace evidence

**Milestone closed: structured project-scoped simulation delivered and accepted,
2026-10-16.** This records the agreed substantial FS2 slice, verified with an actual
Hardcaml Cyclesim provider and native HTTP/PTY interaction. No ASIC physical flow or
sibling-project change was required.

## Owner acceptance and closeout

After receiving daemon/client startup and Cyclesim demo instructions, the owner
reported **“alrighty seems to work fine”**, then authorized milestone closeout.
This records manual acceptance of the basic demo launch/view workflow. It does not
claim the owner manually exercised every cancellation, restart, export or race case;
those claims remain tied to the automated evidence below.

The agreed milestone requires no further feature implementation. Remaining work is
tracked as [named followups](backlog/fs2_followups.md), with reactivation triggers
and acceptance criteria, rather than unfinished milestone gates. Repository
integration and post-integration verification remain an owner handoff, described
below; worktree acceptance does not claim the main branch has been updated.

## Delivered scope

- Versioned project-owned discovery and explicit suite/case/seed/parameter inputs.
- Discovery and runs use the existing supervisor, per-root queue, jobs, logs,
  process-group cancellation and deadlines; no second process scheduler.
- Structured live case events/progress, failure messages and reports. Process exit,
  lifecycle and semantic result remain separate. Invalid/incomplete streams cannot
  create successful attempts; accepted partial results survive cancellation.
- Targeted selected-case/all-failed reruns with original seed/parameters and immediate
  parent identity, producing a new job. Retrying the same submission key deduplicates.
- Independent simulation tiles, launch forms, case/attempt selection, logs, history
  paging and bounded scroll. Generic Dune tests remain available separately.
- Bounded Workbench-owned historical records and artifact copies; restart interrupts
  unfinished history without replay. Missing/corrupt evidence is explicit.
- Byte-exact report/trace export and explicit external viewer on the terminal host.
  The acceptance invokes a recording viewer with an actual Cyclesim-produced VCD.

Provider and RPC details: [simulation contract](fs2_simulation_contract.md).
Implementation ownership and feature-set relationships:
[implementation plan](fs2_implementation_plan.md). Accepted policy is recorded in
[D5](decisions.md#d5--fs2-simulation-evidence-and-feature-set-boundaries).

## Try it

The reproducible [Cyclesim example](../examples/fs2_cyclesim/README.md) has its own
Dune project, a real four-bit counter, directed wrap/reset checks, seeded enable
traffic, and real `Hardcaml.Vcd.wrap` waveforms. Its Python wrapper implements the
provider contract; it does not parse human test output into inferred results.

From the FS2 checkout, build serially:

```sh
scripts/with-switch.sh dune build -j 20 daemon/main.exe terminal/main.exe
scripts/with-switch.sh dune build \
  --root "$PWD/examples/fs2_cyclesim" \
  --build-dir /tmp/opencode/fs2-build-provider -j 20 counter.exe
```

Put `hardcaml-workbench-simulation.sexp` in the project root to inspect. Substitute
the absolute Python/checkout paths for your installation:

```sexp
((schema_version 1)
 (provider_executable /usr/bin/python3)
 (provider_args (/home/wayne/devel/jane/fs2/examples/fs2_cyclesim/provider.py
                 --counter /tmp/opencode/fs2-build-provider/default/counter.exe))
 (discovery_timeout_seconds 10)
 (run_timeout_seconds 90))
```

Use normal terminal startup and project/environment selection. Optionally pass
`--simulation-viewer /absolute/viewer-executable`. This is an alias of the existing
binary-viewer option: one shared executable receives one private local filename,
without shell interpretation. A viewer requiring additional arguments needs a wrapper.
Viewing historical evidence does not require the provider to remain configured.

### Terminal controls

1. **Space c c** opens the palette; choose **Add simulation tile** and focus it with
   **Tab**. The tile is explicitly project-scoped, independent of ASIC selection.
2. Choose **Simulation: Discover suites explicitly**. Discovery is an explicit job;
   routine polling and rendering do not run tools.
3. Choose **Simulation: Launch form …** for the desired suite. The form captures
   selected case IDs, canonical uint64 seed, and every declared parameter. **Enter**
   accepts each field, **Ctrl-U** clears, **Backspace** edits, and **Esc** abandons.
   Final confirmation shows captured inputs before submission.
4. For the example, use cases `wrap`, `reset`, `seeded`; `cycles` defaults to `64`,
   `step` to `1`, and `inject_failure` to `false`. Set failure injection to `true`
   to exercise actual checker mismatches and report inspection.

| Control | Effect in a simulation tile |
| --- | --- |
| `j` / `k` | Browse attempts on the current history page |
| `n` / `p` | Select case |
| `l` | Toggle stream-labelled current-job logs |
| `[` / `]` | Scroll wrapped detail/log content |
| Palette: newest / older history | Read another bounded history page |
| Palette: reopen attempt / select case | Explicit investigation selection |
| Palette: rerun selected case / all failed | New linked attempt, same captured seed/parameters, current project |
| Palette: cancel | Cancel the captured attempt only |
| Palette: export / open external viewer | Verify and copy the selected artifact to the client host |
| Palette: Zoom focused tile | More inspection space |

Two tiles retain independent selections. Hiding a tile stops its observation
polling, not its producer. Historic logs may be unavailable after restart or live
job retention eviction; normalized case results and retained artifacts are separate.

## Verification

Final combined-tree checks passed serially, with no other compilation running:

```sh
scripts/with-switch.sh dune build --build-dir /tmp/opencode/fs2-build-backend -j 20 @fmt @lint
scripts/with-switch.sh dune runtest --build-dir /tmp/opencode/fs2-build-backend -j 20
scripts/with-switch.sh dune build --build-dir /tmp/opencode/fs2-build-backend -j 20
```

Initial implementation used separate build directories with agent budgets 8 + 6 + 6
= 20. Initial combined formatting differences were corrected before the final
passing checks. Review fixes (capture/environment/config fences, persistence failure
handling, cancellation drain yielding, retention, stale frontend receipts, wrapped
failure scroll and export worker-thread hashing) are included in the final checks.

### Real provider proof

`python3 scripts/test-fs2-provider.py` passed with the prebuilt counter at
`/tmp/opencode/fs2-build-provider/default/counter.exe`.

Evidence: **`/tmp/opencode/fs2-provider-tzid09_h/`**. Four executions cover three
cases each, 768 cycle comparisons, maximum uint64 seed, deterministic signal-body
replay and deliberately injected checker failures. Actual VCDs and reports are
retained. VCD date headers are excluded from deterministic signal-body comparison.

### Final native HTTP and actual terminal PTY

```sh
scripts/with-switch.sh python3 scripts/test-fs2-native.py \
  --daemon /tmp/opencode/fs2-build-backend/default/daemon/main.exe \
  --client /tmp/opencode/fs2-build-backend/default/terminal/main.exe \
  --counter /tmp/opencode/fs2-build-provider/default/counter.exe
```

Evidence: **`/tmp/opencode/fs2-native-yx27d5_b/`**, `result.json`: **passed, 45 checks**.
It includes raw HTTP receipts, actual terminal screens/ANSI, provider call logs,
captured requests, exports and viewer receipts. The harness creates private state
and deliberately damages only its own copies for missing/changed/corrupt tests.

- HTTP: project-only operation, same-key deduplication/conflict, normalized case
  ordering, targeted rerun lineage/inputs, invalid streams and discovery, unknown
  progress totals, cancellation with retained partial results, real Cyclesim and
  rerun, byte paging including NUL/non-UTF8/CRLF, history continuation and restart,
  crash interruption, durable key retry, missing/changed artifacts and corrupt history.
- Actual PTY: edited launch form, real checker failure/detail and job logs,
  targeted rerun, two independent tile selections, and external viewer invocation
  with byte-identical actual VCD. This proves handoff, not interactive waveform GUI.
- Restart/Get/Observe/History/artifact reads are checked against provider call logs
  to prove they do not launch discovery or simulation.

Earlier implementation acceptance also passed at `fs2-native-n_tdckra` and the
terminal smoke at `fs2-terminal-8u4vtrvo` (under `/tmp/opencode`). The final native
run above supersedes those for the reviewed integrated code.

### Existing interrupt regression

```sh
scripts/with-switch.sh python3 scripts/test-terminal-interrupt.py \
  --daemon /tmp/opencode/fs2-build-backend/default/daemon/main.exe \
  --client /tmp/opencode/fs2-build-backend/default/terminal/main.exe
```

All five cases passed at **`/tmp/opencode/workbench-terminal-interrupt-ou1stfm9/`**:
normal, filter-active, palette-active, unfinished paste and completed paste; clean
client exit/restored terminal flags and daemon survival. Existing generic supervision,
RTL/artifact/hierarchy and ASIC tests also passed in the full Dune suite. This FS2
run did not repeat installed-package or physical-flow acceptance.

## Integration handoff

At closeout the FS2 implementation is in `/home/wayne/devel/jane/fs2`, based on
`e96ea6a`, with changes unstaged/uncommitted. The inspected main worktree is at
`0d3f046`, including the later Escape-latency fix and FS1 documentation updates;
FS3 is a separate worktree at `613ce31`. No staging, commit, merge or push was
performed as part of closeout, under the owner's Git-authorship restriction.

The owner should review and integrate the FS2 source/docs/fixtures. Inspect local
demo configuration separately: an absolute-path
`hardcaml-workbench-simulation.sexp` created while trying the example is installation
configuration, not a portable fixture to include accidentally. The example README
already contains the portable configuration instructions.

Resolve shared terminal changes deliberately, particularly `terminal/main.ml`,
`host_view.ml`, `workspace_host.ml` and `terminal/dune`. Preserve the later FS1
Escape fix and any adopted FS3 template/presentation behavior alongside FS2 commands
and response fences. Documentation merges must retain each set's actual status.

After integration, run these commands **from the integrated checkout**, serially,
with no other build consuming the 20-job budget. They use freshly built integrated
binaries rather than the previous FS2 candidate. These commands are a handoff,
**not a record of post-merge checks already performed**:

```sh
scripts/with-switch.sh dune build --build-dir /tmp/opencode/fs2-integration-build -j 20 @fmt @lint
scripts/with-switch.sh dune runtest --build-dir /tmp/opencode/fs2-integration-build -j 20
scripts/with-switch.sh dune build --build-dir /tmp/opencode/fs2-integration-build -j 20
scripts/with-switch.sh dune build \
  --root "$PWD/examples/fs2_cyclesim" \
  --build-dir /tmp/opencode/fs2-integration-counter -j 20 counter.exe
python3 scripts/test-fs2-provider.py \
  --counter /tmp/opencode/fs2-integration-counter/default/counter.exe
scripts/with-switch.sh python3 scripts/test-fs2-native.py \
  --daemon /tmp/opencode/fs2-integration-build/default/daemon/main.exe \
  --client /tmp/opencode/fs2-integration-build/default/terminal/main.exe \
  --counter /tmp/opencode/fs2-integration-counter/default/counter.exe
scripts/with-switch.sh python3 scripts/test-terminal-interrupt.py \
  --daemon /tmp/opencode/fs2-integration-build/default/daemon/main.exe \
  --client /tmp/opencode/fs2-integration-build/default/terminal/main.exe
git diff --check
```

Record the integrated revision and new evidence roots alongside this acceptance
record. No full physical ASIC flow is required for this FS2 integration check.

## Limits and next extensions

These remain explicit product boundaries after closure. Work items and activation
criteria are centralized in [FS2 followups](backlog/fs2_followups.md).

- Provider v1 discovers a bounded static case catalog, requires explicit seed and
  parameters, and uses a dedicated LF-delimited S-expression event file. Dynamically
  generated case catalogs and additional simulation engines need adapter extensions.
- Rerun means original inputs against the current project/config/environment. It is
  not an archived source/build/environment replay guarantee.
- Optional ASIC inputs are validated against exact adopted evidence through the RPC.
  V1 supplies references, not automatic collateral staging. No real FS2 gate-level
  adapter, ASIC-input launch form, or automatic ASIC acceptance contribution is claimed.
- History retains at most 100 attempts, 16 MiB normalized records and 512 MiB artifact
  copies per root; artifacts are capped at 64 MiB each/256 MiB per attempt. Oldest
  terminal records are evicted first; active records are not evicted. This is bounded
  history, not archival retention. Current terminal simulation jobs/logs are separately
  bounded to 100 per root with current discovery protected; per-job log volume and
  producer temporary output do not have a new FS2 byte quota.
- Metadata fsync/history loading/pruning and artifact capture still perform synchronous
  filesystem work. Live events are chunked/batched and final draining yields; byte
  reads/export hashing use workers. No hard slow-storage latency guarantee is asserted.
- Export retains up to 64 MiB decoded chunks in client memory. It is bounded, not
  disk-streamed. The external viewer is explicitly invoked; embedded waveforms remain
  a separately activated extension.
- Reconnection retains selected attempt but resets cached history pagination.
  A superseded submission receipt can leave an accepted attempt discoverable through
  newest history; the client does not automatically resubmit it.
- FS3 starter/setup integration and later upstream Escape-latency changes are not
  included merely by this FS2 implementation. Work started from `e96ea6a`; no Git
  merge/staging/commit/push was performed during implementation.
