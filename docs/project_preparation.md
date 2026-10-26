# Project preparation — build and EDA-less bundle emission

WB-004 is implemented and automatically verified, awaiting owner acceptance.
Preparation builds the declared source executable, invokes selected-flow bundle
emission, and stops before synthesis or physical execution.

## Controls

Open the palette with **Space c c**.

1. In an existing saved workspace, choose **Add preparation tile**, or explicitly
   restore the default Overview layout. Fresh stock Overview includes the tile.
2. Choose **Preparation inputs: FLOW / PROFILE** and enter the endpoint and optional
   parameter overrides using the existing selection form. This selects inputs only.
   Existing remembered Plan inputs can also supply the selection.
3. Choose **Prepare elaboration bundle (EDA-less)**, or focus the preparation tile
   and press **r**. The checklist's **Elaboration** preparation row, before Synthesis,
   has the same EDA-less action.

The endpoint is part of the bundle's selected methodology; selecting `synthesis`
as the endpoint does **not** execute synthesis during preparation.

| Control on preparation tile | Action |
| --- | --- |
| `r` | Build current source executable, then emit selected bundle |
| Enter | Inspect scope, outcomes and existing job logs |
| `j` / `k` | Browse retained session attempts |
| `[` / `]` | Scroll inspection details/logs |
| `x` | Cancel active preparation |
| `a` | Inspect the selected attempt's bundle artifact |
| Esc | Leave inspection/artifact view |

Palette artifact entries expose individual imported files. **Build project** and
**Run project tests** remain separate commands. Merely viewing a row, log or artifact
does not submit work.

## What the statuses mean

- **Build:** the captured preparation build job's process result. If no preparation
  attempt exists, the tile can show the generic project build command result.
- **Elaboration-bundle emission:** a separately supervised `flow emit` operation;
  completion requires a validated receipt, selected plan, manifest and file digests,
  followed by successful artifact import. A successful build is insufficient.
- **Verification (project test command):** the configured test command's process
  outcome. It is not a structured all-cases-passed or ASIC acceptance verdict.
- **Generic RTL (not ASIC bundle):** an observed generation job matching the current
  project/target/configuration can be inspected separately. Its success does not
  establish an ASIC publication. No capability is inferred from target names alone.

Unavailable capability is distinct from supported but not requested/no session
history. New failed/cancelled attempts remain the headline; earlier attempts are
inspectable. Build success remains visible if the subsequent emission fails.

Preparation is current-project evidence, independent of a selected historical ASIC
run. The UI only reports an exact plan association when supplied identities match.
No preparation result completes a physical checklist stage.

## Project configuration

Opt in with `hardcaml-workbench-preparation.sexp` at the source root:

```scheme
((schema_version 1)
 (build_target bin/project.exe)
 (results_root /absolute/path/to/preparation-results)
 (timeout_seconds 600))
```

Workbench runs `dune build -j6` for that target using the selected project
environment, then executes `SOURCE/_build/default/bin/project.exe` directly.
It does not substitute the ASIC companion's pinned executable. Configuration is
revalidated before queued build/emission execution; changed configuration cannot
silently launch the old captured operation.

The executable must implement the versioned `project flow emit` contract. The FIFO
example now does, reusing existing `hardcaml_asic` methodology preparation and
bundle publication. No core `hardcaml_asic` changes were required.

The receipt contains `schema_version = 1`, `kind = "bundle_emission"`, bundle and
plan identities, absolute output directory, verified-reuse boolean and the full
selected methodology plan. The manifest and its files are imported as exact job
artifacts. Supported native store publication includes identity directories and
the provider's private-object publication links.

## Run the prepared real FIFO demo

The example's opt-in config publishes under
`hardcaml_asic_example/.dev/workbench-real-demo/preparation-results`, separately
from existing physical execution evidence.

After existing work finishes, close the old client and stop the old daemon normally.
The daemon shell needs the example's installed ASIC SDK to compile current sources:

```bash
cd /home/wayne/devel/jane/hardcaml_workbench
source /home/wayne/devel/jane/hardcaml_asic_example/.dev/asic-prepare/current/activate.sh
export OCAMLPATH="${OCAMLPATH}:/home/wayne/devel/jane/hardcaml_asic_example/.dev/workbench-provider-sdk/lib"
python3 -B scripts/real-asic-example-demo.py daemon
```

In a second terminal:

```bash
cd /home/wayne/devel/jane/hardcaml_workbench
python3 -B scripts/real-asic-example-demo.py client
```

No reseeding is needed. Demo daemon/client/exporter copies were refreshed after
verification; live processes were not restarted. Refresh receipt:
`hardcaml_asic_example/.dev/workbench-real-demo/receipts/refresh-binaries-b67182ad169a4862acf679ee4ac77c67/`.
The SDK environment was also checked with the demo's `opam:5.2.0+ox` build path.

## Verification and limits

- Combined `scripts/with-switch.sh dune build -j8 @all @runtest @lint` passed.
- Changed OCaml files pass formatting checks. Global `@fmt` still reports existing
  drift in unrelated hierarchy/indicator/hydration/waveform/workspace files; only
  WB-004 changes were formatted.
- Native HTTP/PTY regression passed against normal rebuilt binaries:
  `/tmp/opencode/wb004-final-native/result.json`. Covers scoped generic RTL,
  preparation inputs, unavailable state, logs/artifacts, failure history, reconnect,
  cancellation and separation from physical launch.
- Real FIFO HTTP acceptance passed:
  `/tmp/opencode/wb004-real-example-acceptance-review/report.json`.
  Selected `standard / synth_delay / synthesis`, with
  `SYNTH_ABC_BUFFERING=true` and `SYNTH_STRATEGY=AREA 0`.
  Both build and emission completed, 25 artifacts per successful attempt were read
  and digest-checked, reuse passed, and expected-identity mismatch failed without
  publication changes. Descendant execution tracing recorded zero provider/EDA
  executions; retained physical evidence stayed unchanged.
- Provider CLI tests cover selection, overrides, deterministic publication/reuse,
  identity mismatch and EDA-less operation. Backend regressions cover cancellation,
  config drift, malformed/tampered receipts, nonzero/timeout outcomes and deduplication.

Attempts, generic jobs, logs and imported artifact handles are **daemon-session
scoped**. Published bundles remain in their results store, but restart/external
receipt discovery is [deferred](backlog/README.md#preparation-history-and-external-emission-adoption).
Resource-preparation composition and exact-bundle verification remain separate work.
Owner visual/workflow acceptance is pending.
