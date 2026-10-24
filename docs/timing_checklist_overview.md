# Timing in Overview — WB-069

Overview shows **Timing** between Routing and Signoff. Timing is now also a real
executable provider stage: see [executable Timing controls and deployment](executable_timing_stage.md).
Its tile distinguishes full stage status/duration from native STA status/runtime,
corner-specific setup/hold slack, violations and goal. Historical six-stage runs retain
their supplementary analysis representation without an invented physical occurrence.

## Reading the result

These are separate facts:

- **Timing stage completed:** the full segment completed and published its checkpoint.
- **STA completed:** the exact STA producer completed and published its output.
- **Timing goal pass/fail/unknown:** the reported measurements and corner coverage
  establish a scoped constraint result. Completion alone is not a pass.
- **Signoff outcome:** the enclosing physical segment may fail after STA finishes.
  Finalization and signoff acceptance remain separate from both analysis and goal.

For example, completed STA followed by DRC timeout can show Timing completed and
Signoff failed, while keeping the exact timing paths available. Stage duration includes
extraction and preparation; separately labeled STA runtime identifies the native
wall-clock measurement basis and millisecond precision. Historical supplementary
Timing rows display STA runtime rather than fabricating stage duration.

The compact Timing tile puts status and duration together on its first body row.
It then shows the timing goal/source and corner-scoped measurements; full context
is available in details. Missing measurements, unknown units and incomplete corner
coverage stay unavailable/unknown. The tile does not substitute unrelated terminal
or inherited timing metrics when the supplementary observation is absent.

## Controls

| Focus | Control | Result |
| --- | --- | --- |
| Stage checklist | `j` / `k` | Select a projected checklist item, including Timing |
| Checklist Timing or Overview Timing tile | `Enter` | Open the matching captured analysis in a Timing investigation |
| Checklist Timing or Overview Timing tile | `d` | Show scrollable analysis details and provenance |
| Checklist Timing | `r` | Prepare a NEW run through Timing when the current provider/catalog supports it; explicit Launch is still required |
| Overview Timing tile | `r` | Refresh retained evidence for that tile's resolved run |

This also works while historical evidence is selected, without changing that old
execution. Unsupported providers show an explicit explanation instead of silently
ignoring the key. Ordinary stage preparation and launch semantics remain unchanged.

Both inspection entry points capture the resolved run/pin, attempt, analysis and
source digest. Normal inspection now uses the built-in Timing workspace; its state
tracks the selected source and clears incompatible path/detail state. Explicit
separate investigations retain their captured source and reject replacement.
Restored caches retain exact identity and show cached-unverified until revalidated.
A filter hiding all paths is distinct from unavailable evidence. See
[Timing usability and preloading](timing_workspace_usability.md) for current routing,
background index loading, compression and decimal settings.

## Provider availability

Analysis requires `timing_analysis1`; executable Timing additionally requires
`timing_stage1` and a declared fresh endpoint. New recipe schema 4 has seven stages
and Timing-scoped analysis schema 2; historical six-stage recipes and signoff-scoped
schema-1 analyses remain readable. See the sibling
[executable provider contract](../../hardcaml_asic/docs/development/executable-timing.md).

The provider captures an immutable source **at successful Timing completion**, before
Signoff starts, and can recover proven STA evidence after a failed segment. Historical
schema-1 evidence was captured after the enclosing Signoff segment ended. Completion requires
validated native output/runtime records from the exact fresh request-bound producer.
Per-corner measurements require native measurement provenance, not cumulative keys alone.

Previously installed provider executables require refresh. The configured real-example
provider/project and retained Workbench binaries have now been refreshed; restart
the daemon/client as described in the [deployment guide](executable_timing_stage.md#refreshed-example-deployment).
Existing historical executions
are not automatically backfilled. Host death before capture can leave no observation.
Inspection revalidates captured source files and refuses changed/deleted reports;
immutable completion facts can remain visible when their reports are no longer present.

## Original supplementary-delivery verification — 2026-10-21

The following receipts describe the original supplementary delivery; the
[executable-stage verification](executable_timing_stage.md#verification-record) supersedes
its non-runnable restriction and records the refreshed deployment. No new physical EDA flow was
run; the failed-signoff cases use deterministic native-grammar and transport fixtures.
Owner visual acceptance and deployment to previously installed providers are separate.

| Check | Result / retained evidence |
| --- | --- |
| Workbench full build + lint | `./scripts/with-switch.sh dune build -j 20 @all @lint` passed |
| Workbench full tests | `./scripts/with-switch.sh dune runtest -j 20` passed |
| Final rebuilt native HTTP/PTY WB-069 test | 20 checks passed; `/tmp/opencode/wb069-timing-053c0c973a73/` |
| Overview sidebar regression | 135 checks passed; `/tmp/opencode/overview-sidebar-2749858538de/` |
| Launch-stage consistency regression | 30 checks passed; `/tmp/opencode/launch-stage-consistency-c315edec5ce7/` |
| Synthetic checklist preparation/launch | Passed; `/tmp/opencode/checklist-workflow-14bd8c8ae19a/` |
| Provider native grammar/availability suite | 18 cases plus cancellation, report/index/detail, identity, mutation/deletion and read-only assertions passed |
| Provider stage preparation | 62 checks passed, including successful STA followed by DRC failure, timeout and actual SIGTERM cancellation |
| Provider segment service | 70 checks passed |
| Provider inspection/stage-report regression and full build | Passed, using explicit `-j 6`; whole provider runtest was not run |
| Cross-repository retained fixture | Workbench parsed actual provider report/index/detail for `/tmp/opencode/wb069-provider-handoff-a/execution-attempt.json`: failed Signoff, no checkpoints, STA completed in 1.575s, timing goal fail |

The final WB-069 receipt records exact daemon/client/preset hashes. It exercises both
Overview surfaces, details, captured index/detail digests, pins, changed sources,
read-only actions and daemon/client restart. Backend tests additionally cover generic
cache-to-exact-analysis misses, legacy HTTP negotiation and cache-only reopening.

The launch regression now distinguishes graceful daemon SIGTERM, which cancels/reaps
owned producers, from daemon-only SIGKILL, which leaves a detached producer. This
corrects its previous shutdown oracle rather than weakening lifecycle checks.

Repository-wide `@fmt` remains blocked by pre-existing formatting in
`terminal/retained_hydration.ml`, `terminal/navigation_hydration_probe.ml`,
`terminal/waveform_data.ml/.mli`, `terminal/waveform_probe.ml`,
`terminal/workspaces/test_workspaces.ml` and `workspace_cli/main.ml`.
The navigation probe has only a mechanical absent-field addition for this feature;
its reported formatting differences are in existing simulation-refresh code.
Feature implementation formatting, scoped backend/protocol/transport checks and
`git diff --check` passed. No staging, commits or pushes were performed.

Reproduce the focused acceptance with prebuilt matching binaries:

```sh
python3 -B scripts/test-wb069-timing.py \
  --daemon _build/default/daemon/main.exe \
  --client _build/default/terminal/main.exe \
  --preset-export _build/default/terminal/workspaces/export_presets.exe \
  --timeout 300
```

The [implementation plan](timing_checklist_overview_plan.md) records ownership,
contract decisions, job budgets and agent work packages.
