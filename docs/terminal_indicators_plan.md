# Terminal icons and activity indicators

Status: **implemented and verified**, 2026-10-17. Clean baseline: `849c63b`.

## Intent

Add compact, useful status/context icons and native Bonsai Term activity animation
to the current workspaces. Preserve unadorned lowercase tile titles, dense geometry,
existing semantic colors, full text labels and exact identities. No new provider
queries, execution or state changes may be caused by animation or icon switches.

The installed API is authoritative: `bonsai_term_components/spinner/` exposes
`Bonsai_term_spinner.component`, with `Dot` and `Line` kinds. The local example is
`../bonsai_term_examples/spinner/src/bonsai_term_spinner_example.ml`. The base
`../bonsai_term` checkout is read-only. Its primitives render Unicode text; there
is no assumption of a general installed icon catalog or Nerd Font requirement.

## Shared presentation contract

New `terminal/indicator.ml{,i}` owns compact static glyphs and ASCII/off fallbacks.

```ocaml
type t = Running | Pending | Completed | Failed | Cancelled | Skipped
       | Not_requested | Unknown | Ready | Stale | Pin | Artifact | Log
       | Seed | Report | Trace | Info
type frames = { dot : Bonsai_term.View.t; line : Bonsai_term.View.t }
val text : Appearance.Icons.t -> t -> string
val view : ?frames:frames -> Appearance.Icons.t -> t -> Bonsai_term.View.t
```

`text` returns a glyph only (no padding), Off returns empty text. `view` returns
native current spinner frames for Running when supplied; otherwise a deterministic
static frame for tests/captures. All other kinds use `text`. Rendering code owns
padding, colors, cell-budgeting and unchanged labels. Use single-cell glyphs with
validated width; no emojis/private-use-font dependencies. An unknown state does
not receive a success icon. Completed is execution completion, not acceptance.

The top-level host renderer gains optional `?indicator_frames:Indicator.frames`;
the native client supplies one shared Dot/Line component pair, rather than clocks
per tile. Pure rendering/capture calls omit it and stay deterministic. The existing
100ms display clock and 500ms domain polling remain distinct; spinner activity
must never drive polling or invoke commands. Existing Appearance Icons Unicode /
ASCII / Off controls apply, including persisted preferences.

## Ownership and job budget

No Git staging/commits/pushes/resets/merges or authorship operations. Preserve live
daemons, demo state and canonical evidence. No real physical flows needed.
Shared aggregate build pool:20 jobs. Agents A/B may use6 each in separate build
directories; C uses prebuilt binaries only; parent may use at most8 while A/B run
and normally waits. Final serial verification may use20 after agents finish.

- **A primitives/native integration:** owns `indicator.ml{,i}`, `terminal/main.ml`,
  `terminal/dune`, `dune-project`, generated opam metadata. Uses
  `/tmp/opencode/indicators-native` at `-j6`. Implements the contract above and
  wires real native spinner components through optional renderer argument.
- **B rendering:** owns `terminal/host_view.ml`, `terminal/overview_tiles.ml` and
  `terminal/simulation_view.ml` (ownership expanded during integration to keep
  simulation text and typed indicator metadata in one canonical row projection).
  Uses `/tmp/opencode/indicators-render` at `-j6`. Integrates icons/activity into
  typed lifecycle rows (runs/jobs/stages/planned-run/simulation) and useful context
  such as explicit pins/artifacts. Keep titles undecorated, text and raw logs/reports
  intact, and layout/hit-testing budgets coherent. Optional animation plumbing must
  preserve existing callers. Add meaningful semantic/width/fallback renderer tests.
- **C native acceptance:** owns `scripts/test-terminal-indicators.py` only. Reuse
  private synthetic/public API and PTY helpers; no build. Prove animation advances
  for bounded synthetic work, terminal states stop spinning, Unicode/ASCII/Off
  choices work, captured commands/identities and geometry remain valid. No real EDA.
- **Coordinator:** this plan/guides, ownership seams, review, normal build/full
  checks and focused regression, persistent binary refresh after verification.

## Verification and completion

- [x] Shared glyph/width policy and native spinner wiring.
- [x] Typed renderer integration with unchanged title/layout policy.
- [x] Native animation/fallback acceptance with private state and evidence.
- [x] Normal format/lint/full tests/build and relevant FS2/checklist/interrupt checks.
- [x] Updated controls, evidence and refreshed matching demo binaries.

Use `scripts/with-switch.sh` for OCaml/formatter commands. Verify the installed
package name before adding the dependency; no dependency installation or reference
checkout changes are authorized implicitly by this presentation task.

## Delivered controls and boundaries

- Existing **Appearance: Icons Unicode / ASCII / Off** controls select native Dot /
  Line animation or no indicator. These choices retain existing FS3 persistence.
- Checklist stages, run selectors, generic job rows and planned-run readiness/
  producer lifecycle have typed indicators. ASIC animation requires exact matching
  active producer ownership; a historical running observation alone stays static.
- Simulation request/attempt/case rows use their own typed lifecycle/outcome facts.
  Terminal cases cannot continue animating from a stale Running case status. Seed,
  artifact, log-header and explicit PIN context receive compact glyphs.
- Ordinary text labels and exact IDs remain; raw reports/logs/messages are not
  scanned for status words. Generic Complete is not a case pass, Ready is not a
  completed execution, and validated evidence is not acceptance.
- Simulation text and metadata originate in `Simulation_view.annotated_rows`;
  `rows` remains its unchanged string-only projection. No duplicated row-order
  annotation table needs maintaining.
- All indicator glyphs are one display cell in the installed renderer. Captures
  without native frames remain deterministic. Border titles remain lowercase and
  undecorated; frame rectangles and hit-testing geometry are unchanged.

## Verification

Normal full build, format/lint and full tests passed serially at `-j 20` after the
native Off-mode redraw correction and canonical simulation-row integration. Two
implementation agents built at six jobs each in separate directories; native
acceptance/regressions used prebuilt binaries and private state.

| Check | Result / evidence under `/tmp/opencode` |
| --- | --- |
| Actual native indicators HTTP/PTY |351 checks; `terminal-indicators-e67675e54fe0/result.json` |
| FS2 real Cyclesim/native HTTP/PTY |45 checks; `fs2-native-2rpio8up/result.json` |
| Existing Overview/sidebar/schemes/plan |130 checks; `overview-sidebar-b35870e85742/result.json` |
| Checklist discovery/plan/launch |61 checks; `checklist-workflow-0ab06cd1749e/result.json` |
| Interrupt and terminal restoration |5/5; `workbench-terminal-interrupt-8uzbhrkz/results.json` |

Native captures observed six distinct Unicode frames and four ASCII frames per
ten-sample active-request/producer sequence; Off remained empty. Ready/completed/
failed/skipped states settled. Tests preserve exact preview/allocation identities,
show full status labels, verify 120x40 and 180x55 geometry/unadorned titles, and
prove icon switches do not discover, plan or launch extra work. ANSI, cells, SVGs,
keys and frame-prefix samples are retained with the receipt.

An initial native test caught a real redraw regression: reducing clock/revision to
unchanged dimensions/animation-enabled values allowed reactive cutoffs to suppress
input redraw with Icons Off. The final implementation carries both clock and input
revision through rendering independently of native spinner state. Failed evidence
is retained at `terminal-indicators-03071f1ebf80`; it is superseded by the passing
receipt above, not counted as passing acceptance.

Reproduce without a build inside the harness:

```sh
python3 -B scripts/test-terminal-indicators.py \
  --daemon _build/default/daemon/main.exe \
  --client _build/default/terminal/main.exe \
  --preset-export _build/default/terminal/workspaces/export_presets.exe \
  --timeout 600
```

The native spinner library was already installed. The package dependency is now
declared; no package installation or reference-checkout modification was required.
No real EDA, canonical evidence edits or Git staging/commits/pushes were performed.

Normal binaries and the persistent real-demo daemon/client/exporter are refreshed.
Receipt under `hardcaml_asic_example`:
`.dev/workbench-real-demo/receipts/refresh-binaries-fbde120c096d41e289e57977fb58aabe/`.
Live processes and investigation state remain intact. After active jobs finish,
restart the matching daemon/client normally; no reseed is needed.
