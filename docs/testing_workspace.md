# Testing catalog and cooperative investigation

Implemented and automatically verified 2026-10-17 for WB-032, WB-034 and WB-063.
Native provider migration (WB-066) delivered 2026-10-18; see
[adapter boundary and verification](native_provider_plan.md).
The actual `hardcaml_asic_example` now has a genuine project-owned FIFO Cyclesim
provider. The Testing workspace exposes catalog, attempts, cases, result detail,
artifacts and logs as coordinated panes. The original FS2 milestone remains closed;
this is an adoption/investigation extension using its existing contract.

[Shared implementation plan and evidence](testing_cluster_plan.md).
Owner visual review of the new composition remains separate from automated acceptance.

## Open it in the real example

The FIFO provider is already installed persistently and the root companion config
is present. Start matching refreshed Workbench binaries after active jobs finish:

Binary refresh receipt under the example's `.dev/workbench-real-demo/`:
`receipts/refresh-binaries-3dc29d7ad10a45c58a856bab877984b4/`.

**Terminal 1:**

```sh
cd /home/wayne/devel/jane/hardcaml_workbench
python3 -B scripts/real-asic-example-demo.py daemon
```

**Terminal 2:**

```sh
cd /home/wayne/devel/jane/hardcaml_workbench
python3 -B scripts/real-asic-example-demo.py client
```

No reseed or ASIC rerun is needed. Existing live processes were not restarted by
implementation. The helper reopens saved state; tests were executed in private
acceptance state, so they do not appear as preseeded attempts in your live history.

1. Open **Space c c → Create Testing workspace** for a new default arrangement.
2. Tab to **simulation-catalog**, press **d** for explicit discovery.
3. Choose cases, then press **Enter** to prepare the normal launch form.
4. Review cases, seed and parameters; only final confirmation launches simulation.

If you already have a customized Testing workspace, **Apply default layout (add
missing tiles)** adds the new panes and preserves extras, pins, hidden state and
geometry. Older `simulation`, run-selector or log tiles may remain as extras. Hide
unwanted extras explicitly, or create a new Testing arrangement for the clean
default; the upgrade does not erase them.

## Layout and selection

At ordinary terminal sizes the layout has three columns:

```text
session          catalog          selected result / captured inputs
generic tests    attempts         artifacts
execution        cases            selected attempt job logs
```

The compact utility column is one fifth of the width; the two investigation
columns share the rest. Cases and artifacts refer to the selected simulation
attempt, not the ASIC run selected in Overview. Full IDs and captured provenance
remain inspectable in Detail. The artifact list prioritizes labels/case ownership;
selecting an artifact exposes its exact ID, bytes, digest and media type in Detail.

- The six panes share one **client/workspace-local** investigation and one polling
  stream. A second Testing workspace/client has its own selection.
- Focus and scrolling belong to each tile. Catalog/attempt/case/artifact cursors
  remain visible as lists grow; manual scroll pauses cursor-follow until navigation.
- Selecting another case clears the old artifact selection. Selecting an artifact
  identifies its owning case when supplied. Attempt changes invalidate old detail.
- Same-session reconnect preserves appropriate browsing while fencing pending
  responses. Replacement sessions/workspace identities do not inherit stale state.
- Generic Dune tests remain process results, not structured case counts or ASIC
  acceptance. The legacy standalone **simulation** tile still works independently.

## Controls

| Focus | Key/action | Effect |
| --- | --- | --- |
| Any simulation pane | `d` | Explicitly discover/refresh suites; never implied by rendering |
| Catalog | `n` / `p` | Choose next/previous declared suite |
| Catalog | `j` / `k`, arrows | Browse cases without changing attempt investigation |
| Catalog | `x` | Toggle the current case in the explicit subset |
| Catalog | `a` | Explicitly select all currently declared cases |
| Catalog | `/`, then text; Enter/Esc | Edit/finish a case filter; matching never launches work |
| Catalog | `u` | Accept current refreshed discovery/defaults after reviewing changes |
| Catalog | Enter or `r` | Open a launch form with exact suite/subset/digest |
| Attempts | `j` / `k`, arrows | Select an exact retained attempt and observe its detail |
| Cases | `j` / `k`, arrows | Select a case for shared investigation |
| Artifacts | `j` / `k`, arrows | Select an exact artifact; list explicitly includes all cases |
| Artifacts | `e` / `v` | Export verified bytes / open configured external viewer |
| Investigation panes | `r` / `f` | Rerun selected case / all failed cases using original inputs on current project |
| Any simulation pane | `h` | Newest history page; palette also provides older pages |
| All panes | `[` / `]`, Tab/Shift-Tab | Independent scroll; move focus |
| Palette | Zoom focused tile / Unzoom workspace | More room for full inputs, failures, metadata or logs |

The existing multi-step launch form accepts cases, canonical uint64 seed, each
declared parameter and final `launch` confirmation. Ctrl-U clears a field. Catalog
defaults are not guessed: the initial declared suite defaults are shown, and
changed/removed selections disable launch until explicitly corrected/accepted.
Failed/in-flight discovery can retain browsable catalog rows without enabling Run.
Already-open palette/forms keep captured inputs; stale launch requests are rejected
by the normal backend digest/config checks rather than retargeted.

## Genuine FIFO provider

| Field | Declared values |
| --- | --- |
| Suite | `controlled-fifo` |
| Cases | `directed`, `seeded` |
| Default seed | `42`; the entire canonical uint64 range is supported |
| `cycles` | `64`, `4096` (default), `20000`; affects seeded traffic only |
| `checker` | `normal` (default), `mismatch` |

The provider uses the real `Controlled_fifo` DUT, existing directed traffic and
independent ordered-list reference model. `checker=mismatch` changes one expected
post-edge occupancy value at edge 17. It does not change the DUT or input stimuli:
normal and mismatch modes produce byte-identical VCDs for the same case/seed.
It deliberately demonstrates semantic **Failed** with process exit 0; use `normal`
for actual success checking. Full cycle/phase/expected/observed/stimulus/history
evidence is retained in the native report and logs.

FS2 seeds map to four little-endian 16-bit PRNG words, preserving all 64 bits.
This documented mapping differs from the old single-int CLI seed mapping. The
ordinary CLI/Dune tests keep their prior behavior. Deterministic replay is verified
for the same executable/toolchain, not claimed as archived-build reproducibility.

Persistent generation:

```text
hardcaml_asic_example/.dev/fifo-simulation/4158d5b458804b8a8428bc28862e5a49/
  fifo_sim.exe
  test_provider.exe
```

Only `test_provider.exe` links the shared provider library; the simulator/checker
retains its standalone executable interface. Python adapters remain source-level
conformance references. The former installed Python generation is preserved.

Root configuration is `hardcaml-workbench-simulation.sexp`; installation ownership
is `.dev/fifo-simulation-install.json`. Discovery/run never build or install.
The explicit installer supports a bounded build or an already-verified executable
and refuses unrelated/edited companion configuration. See the sibling's
`simulation/README.md` for maintenance and standalone commands. ASIC configuration
and canonical physical results are separate and were not modified.

## Availability limits

Logs remain the existing supervisor's bounded job logs, not newly durable full
history. After daemon restart, normalized cases/reports/traces remain available,
while absent exact-job logs are explicitly labelled unavailable. Waveforms use
byte-verified export/external viewer handoff; there is no embedded waveform viewer.
Simulation is project-scoped and supplies no automatic ASIC acceptance verdict.
There is no seed-matrix scheduler, new test schema or archived-input replay in this
slice. Missing artifacts/errors are retained as explicit states.

## Acceptance

Normal build, repository-wide format/lint and full tests passed serially at `-j20`.
Implementation agents used separate build directories at 6 jobs each, within the
shared 20-job pool. No physical EDA ran.

| Proof | Final evidence under `/tmp/opencode` |
| --- | --- |
| Genuine FIFO standalone + public HTTP + new/legacy PTY | `fifo-testing-wx4xhzjp/`: 21 cooperative assertions, 6 native attempts, 12 actual standalone case results across 8 valid runs, 12 rejected invalid requests |
| Cooperative synthetic UI | `testing-workspace-w56bs6_c/verified.json`: 15 checks |
| Synthetic demo/legacy compatibility | `synthetic-flow-58wxhzay/testing-result.json`:44 checks |
| Native indicators, including Off | `terminal-indicators-06485dae9a88/result.json`:351 checks |
| Independent real counter FS2 regression | `fs2-native-xh0meb_6/result.json`:45 checks |
| Checklist launch | `checklist-workflow-5eba10136566/result.json`:61 checks |
| Terminal interruption/restoration | `workbench-terminal-interrupt-268f0z3w/results.json`:5/5 |

The real acceptance proves exact catalog-selected cases, seed/parameters/digest,
case selection across repeated polls, coherent detail/log/artifact ownership,
byte-identical report/VCD export and targeted-rerun parent identity. The source
project's ordinary tests also passed: 7,330 directed edges and 20,017 edges using its
original seeded CLI. The expanded FS2 long-seed example checked 20,018 edges; these
different totals reflect different documented seed mappings/drain lengths.

The final real and synthetic captures validate actual painted edges/footer at
120x40 and 180x55. Earlier wide captures matched stale 120-column frames immediately
after PTY resize; explicit SIGWINCH and geometry assertions fixed that harness gap.
Model/reducer tests cover catalog changes, late receipts, workspace independence
and long-list cursor visibility; this is not exhaustive multi-monitor acceptance.

Reproduce with prebuilt binaries (allow 600 seconds for real PTY):

```sh
scripts/with-switch.sh python3 -B scripts/test-fifo-testing.py \
  --daemon _build/default/daemon/main.exe \
  --client _build/default/terminal/main.exe \
  --simulator /home/wayne/devel/jane/hardcaml_asic_example/.dev/fifo-simulation/af97d67d923441a0a654e27b6afd728f/fifo_sim.exe
scripts/with-switch.sh python3 -B scripts/test-testing-workspace.py \
  --daemon _build/default/daemon/main.exe \
  --client _build/default/terminal/main.exe
```
