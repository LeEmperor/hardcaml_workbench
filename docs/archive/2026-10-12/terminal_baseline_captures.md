# Terminal baseline captures (archived)

Recorded 2026-09-20 for
[prettification P0](prettification.md#p0--establish-a-bounded-visual-target-and-test-seam),
item 1. These captures fix what the terminal client looks like *before* any
prettification work, so later changes can be compared against something concrete rather
than against memory. They are a baseline, not a design: the clipping and space
allocation they show are the current behaviour, preserved deliberately.

## Regenerating and inspecting

```sh
./scripts/capture-terminal-baseline.sh          # rewrite test/baselines/terminal
./scripts/capture-terminal-baseline.sh --check  # rebuild, recapture, diff, change nothing
```

The script builds `terminal/main.exe` through `scripts/with-switch.sh` and invokes it
with the development flag `--capture-baseline DIR`. Nothing else is needed: no daemon,
no opened project, no ASIC flow, no network.

Read a frame with `cat` or in an editor:

```sh
cat test/baselines/terminal/dashboard.80x24.txt      # character cells, no styling
cat test/baselines/terminal/dashboard.80x24.ansi     # what the client would emit
```

The `.ansi` files contain raw escape sequences; view them with `cat` in a terminal, or
with `cat -v` / `less -R` to see the sequences themselves.

## How the captures are produced

The point is to capture production rendering, so the capture path reuses it rather than
reimplementing it:

- `terminal/baseline_fixture.ml` holds the fixture data as ordinary protocol values
  (`Project.t`, `Job.t`, `Artifact.t`, `Hierarchy.t`, log records). It lives in the
  `terminal_presentation` library beside the existing pure presentation and state code.
- `terminal/main.ml` gained `session_of_baseline_fixture`, which assembles the
  executable's own `session` record from a fixture using the same `reconcile_selection`,
  `preserve_selected_job`, `log_state`, and `index_hierarchy` functions the client uses,
  and `capture_baseline`, which calls the existing `render session dimensions` and
  serialises the returned `Bonsai_term.View.t`.
- Serialisation goes through `View.Private.notty_image` and `Notty.Render.to_buffer`,
  with `Notty.Cap.dumb` for the `.txt` frame and `Notty.Cap.ansi` for the `.ansi` frame.
  `notty-community` is already required by `bonsai_term`; it is now declared directly
  because the capture uses it directly.

`render`, `run`, and every function `render` calls are untouched. The only change to the
interactive client is the new `--capture-baseline` flag, which is handled in the command
wiring and short-circuits `run` entirely: no session flag is interpreted, no connection is
attempted, and neither the Async polling loop nor the Bonsai Term loop starts.

A fresh session is built for each scenario/size pair, because `render` reconciles
hierarchy and connection-detail scroll offsets in place while drawing; reusing one
session would leak the previous size's scroll state into the next capture.

## Scenarios

Three fixtures, each captured at 80×24 and 120×40, giving twelve files. All identifiers,
timestamps, ordering, and text are fixed in the fixture module. The names are long and
protemu-flavoured so the capture exercises realistic identifier lengths; **none of this
is evidence that the project reports such data**, and no value in it is a measurement or
a verdict.

| Scenario | Files | What it exercises |
| --- | --- | --- |
| `dashboard` | `dashboard.*` | Eight jobs covering Queued, Running, Complete, Cancelled (signalled), Failed (exit 2), and Failed (launch failure); a selected failing job with 43 interleaved stdout/stderr records; long project, target, configuration, job, and artifact identifiers; three artifacts including one `Unavailable`; six Dune workspace items. |
| `hierarchy` | `hierarchy.*` | The hierarchy inspector open over the project pane, nine nodes, two subtrees expanded, a deep selected node with eight input ports and three metadata entries, and long circuit names. |
| `artifact-output` | `artifact-output.*` | A retrieved RTL artifact of 620 lines flagged as truncated at the 1 MiB fetch limit, with many lines wider than 120 cells, while a Running job is selected. |

## What the captures preserve, and what they do not

They preserve:

- the **character-cell grid** at the given size — exactly `width` cells on each of
  `height` rows, including the space padding `render` writes into every pane;
- **layout**: pane widths and heights, where content is cut, what is scrolled away, and
  what never reaches the screen at all;
- the **terminal escape sequences** the client emits for these frames, in the `.ansi`
  files.

They do not establish:

- **that any colour scheme is readable.** These are bytes, not a rendered screen. At the
  time of capture the question does not arise: the only escape sequence in any of the
  six `.ansi` files is `ESC[0m`, an attribute reset. The current UI emits no colour, no
  bold, and no background outside the too-small-terminal message. Stripping the SGR
  sequences from each `.ansi` file yields its `.txt` file exactly.
- **interactive behaviour.** Nothing here presses a key, resizes, reconnects, or
  observes a real update. `scripts/test-terminal-resize.py` remains the PTY-level check.
- **real data.** The fixtures are synthetic by construction; see the note above.
- **font, terminal emulator, or tmux appearance.** A frame that fits in 80 cells here can
  still be wrapped or hidden by the surrounding environment.

The `.txt` files carry a trailing newline the rendered frame does not have; the `.ansi`
files are byte-exact.

## Layout problems these captures record

Observed directly in the committed frames. They correspond to the audit table in
[prettification.md](prettification.md#2-audit-why-the-current-screen-is-hard-to-read) and
are the concrete target for P1 and P2.

At 80×24 the header takes 1 row, the upper region 10, the separator/title/controls 3, and
the console 10. The project pane is 26 cells wide and the jobs pane 53.

1. **The selected job is not on screen.** `dashboard.80x24.txt` shows 2 of 8 job rows —
   the two newest — and the selected job (`0004-dune-runtest-...`) is not among them.
   There is no scroll offset tied to selection. At 120×40 all 8 rows fit and the `>`
   marker is visible, so the defect is invisible at desk width and total at 80 columns.
2. **The job row leads with the full internal identifier.** The fixture job IDs are 55
   to 79 characters, and `%-24s` is a minimum width, not a maximum, so the ID consumes
   the row before state, kind, and phase are reached. At 80 columns a row shows the ID
   and nothing else; at 120 columns the 55- and 63-character IDs leave room for a state
   label, the 79-character one does not.
3. **Whole sections fall off the project pane.** The pane concatenates project,
   integration, hierarchy status, artifacts, and Dune items and then takes the first
   `top_height` lines. At 80×24 it stops on the first target row: the second target, all
   three configurations, the hierarchy status line, the artifact list, the `DUNE ITEMS`
   heading, and all six workspace items are never drawn. At 120×40 the `ARTIFACTS`
   heading is drawn with zero artifact rows beneath it, which reads as "no artifacts"
   when three exist, and `DUNE ITEMS` is still missing.
4. **Selected-job detail crowds out the list.** The detail block precedes the rows, so a
   failing job's three outcome lines plus spacing leave 2 of 10 rows for the list.
5. **The hierarchy tree collapses to one line.** `hierarchy_view_lines` allocates
   `height - 13` rows to the tree. At 80×24 that is negative and clamps to 1:
   `hierarchy.80x24.txt` shows a single node and `Tree [6/8]`. At 120×40 it shows 5 of 9.
6. **Node detail is one long line per field, and the pane runs out first.** `Inputs:` on
   the selected SRAM macro wrapper puts all eight ports on one line: at 120 columns two
   of them survive, at 80 columns the cut lands inside the second. `Metadata:` is cut
   inside its first value. At 80×24 the pane ends at `Inputs:`, so `Outputs:`,
   `Metadata:`, and the `Signals/source:` note are not drawn at all.
7. **Log output is tail-only.** The console shows the last `console_height` records, so
   at 80×24 the first failing assertion (record 33 of 43) has already scrolled away and
   cannot be recovered. There is no scrollback and no follow indicator.
8. **Artifact content is head-only.** The console shows the *first* `console_height`
   lines of an artifact — 10 of 620 at 80×24, 18 at 120×40 — so the
   `[artifact view truncated at 1 MiB]` notice appended at the end can never be reached.
9. **The controls line loses its tail.** The 148-character control string is cut at
   `e exp...` at 80 columns and at `| c...` at 120 columns. Cancel, details, reconnect,
   and **`q exit`** are absent at both captured sizes.
10. **Everything has the same visual weight.** A `Failed` status, a heading, and a path
    are all plain default-attribute text; see the escape-sequence note above.
11. **Only one truncation is intelligent.** `Root:` uses `Presentation.middle_truncate`
    and keeps the final path component. Every other line uses `fit`, a byte-length
    prefix plus `...`.

## Limitations of this seam

`session_of_baseline_fixture` constructs the executable's mutable `session` record
directly, so it depends on that record's shape and must be updated alongside it. That is
deliberate for P0 item 1: the alternative is the rendering-entry-point extraction, which
is P0 item 3, and doing it here would mean the baseline was captured from restructured
code rather than from the code it is supposed to document.

The fixture module is part of the private `terminal_presentation` library, so it is
linked into the installed `hardcaml-workbench` executable along with the capture hook.
That is a few tens of kilobytes of fixture strings in the shipped binary; it is the price
of capturing through the real client rather than through a parallel test executable.

`fit`, the wrapping helpers, and the fixtures all use byte lengths. Every fixture string
is ASCII, so these captures say nothing about the UTF-8 cell-width problem described in
the audit. Add non-ASCII scenarios when the measurement fix lands, not before — a frame
captured now would be a baseline for behaviour that is known to be wrong.

The captures are not wired into `dune runtest`. `--check` exists so the comparison can be
run deliberately when rendering changes, without every unrelated test promoting a new
screenshot.
