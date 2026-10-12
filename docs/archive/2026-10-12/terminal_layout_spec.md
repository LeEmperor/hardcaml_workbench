# Terminal layout specification (archived)

**Historical fixed-layout proposal — superseded 2026-10-12.** The active
[module/tile architecture](hardcaml_workbench_architecture.md#active-direction--modules-and-tiles-2026-10-12)
and [construction plan](construction_phase_plan.md) replace this mandatory screen
contract with a configurable workspace. Retain the cell-budget analysis as input
to an ASIC preset and compact tile design, not as global layout acceptance criteria.

Written 2026-09-20 for
[prettification P0](prettification.md#p0--establish-a-bounded-visual-target-and-test-seam),
item 2: the compact/wide cell budgets and the essential persistent summaries.

This document is a **layout contract**, not an implementation plan. It fixes how many
cells each region gets at 80×24 and 120×40, what must never disappear, what shortens,
wraps, moves to a detail view, or scrolls, and what happens outside those two sizes.
P1–P3 implement it; the acceptance criteria in section 14 are what they are tested
against.

It is bounded deliberately. There is no layout engine, no theme implementation, no
transport change, and no new dependency here. The renderer is not modified by this
document and the [baseline captures](terminal_baseline_captures.md) are not regenerated:
they remain the record of the *current* screen, which this specification replaces.

## 1. Authority, inputs, and what this fixes

- The [architecture's historical release scope](hardcaml_workbench_architecture.md#historical-release-scope--protemu-monitoring-2026-09-20)
  stays authoritative for product scope and evidence semantics. Its six required
  dashboard regions (identity, flow strip, timing, results/checks, execution/log,
  compact design summary) are the regions budgeted below. Section 13 records every
  place this design compacts one of them, and confirms that none is weakened.
- The [archived construction plan](construction_phase_plan_2026_09.md#active-release--scaf-build-and-flow-dashboard-2026-09-20)
  owns D1–D4. This document does not move a release gate.
- [prettification.md](prettification.md) owns P0–P5 and the visual/interaction
  direction. The schematic wide layout sketched there is superseded by section 6;
  its abbreviated flow strip with a trailing ellipsis was explicitly illustrative.
- The [baseline captures](terminal_baseline_captures.md) supply the eleven concrete
  layout defects this design has to answer. They are referenced as B1–B11 below,
  numbered as in that document's "Layout problems these captures record".

The declared flow sequence is `build → emit → preflight → run → postcheck → collect →
report → archive` — eight stages, none hidden. The desired capability/check badges are
`lint, emit, sim, GDS, harden, signoff-block, signoff-chip` plus the separately
reported `DRC, LVS, antenna, TT precheck, gate-level simulation` — twelve badges, none
hidden. Capability badges are **not** flow stages: `emit` appears in both lists and
means two different things (a runnable step versus a declared capability with its own
evidence). They are drawn in different regions with different cell geometry and are
never merged.

## 2. Measurement, glyphs, and why every wireframe here is ASCII

`fit`, `middle_truncate`, `wrap_path`, and `wrap_value` in
[`presentation.ml`](../terminal/presentation.ml) measure **bytes**. This
specification is written in **terminal display cells**. The two agree only for ASCII,
so every wireframe below is pure ASCII and its width was checked by counting
characters. That makes the arithmetic verifiable today without waiting for the
cell-measurement fix, which P1 owns.

Field widths in this document are therefore cell counts. An implementation that keeps
byte measurement will violate them as soon as a project, target, or instance name
contains a non-ASCII character. `View.uchar_tty_width` is the available primitive.

Decoration glyphs are specified as an **ASCII layout with an optional 1:1
substitution**. Every substitute must measure exactly one cell via
`View.uchar_tty_width`; anything that does not falls back to its ASCII counterpart.
Box-drawing characters and `·`, `…`, `▶` have East Asian Width *Ambiguous*, so they are
two cells in a CJK-ambiguous-wide terminal and must not be assumed.

| Role | ASCII (specified) | Permitted substitute |
| --- | --- | --- |
| Rule / separator run | `-` | `─` |
| Column separator | `\|` | `│` |
| Overlay border | `+ - \|` | `┌ ─ │ ┐ └ ┘` |
| Selection marker | `>` | `▸` |
| Tree expanded / collapsed | `v` / `>` | `▾` / `▸` |
| Stdout / stderr stream marker | `\|` / `!` | `│` / `!` |
| Wrapped-line continuation | `\` | `\` |

## 3. State vocabulary

One vocabulary is shared by the flow strip, the capability badges, the check badges,
and the job rows, so a state never means two things. Every state has a distinct
one-cell ASCII glyph and a distinct five-cell word; both are listed in the help
overlay. Colour is additive only — state meaning survives monochrome.

| State | Glyph | Word | Applies to |
| --- | --- | --- | --- |
| passed | `+` | `PASS` | stages, capabilities, checks, jobs |
| failed | `x` | `FAIL` | stages, capabilities, checks, jobs |
| running | `>` | `run` | stages, capabilities, jobs |
| queued | `:` | `queue` | stages, jobs |
| not run | `-` | `n/run` | stages, capabilities |
| skipped | `~` | `skip` | stages, capabilities, checks |
| blocked | `!` | `block` | stages, capabilities |
| cancelled / interrupted | `/` | `canc` | stages, capabilities, jobs |
| unsupported | `?` | `unsup` | capabilities, checks |
| pending (not yet produced) | `o` | `pend` | capabilities, checks, timing |
| unavailable (no source) | `_` | `unavl` | checks, timing, design |
| unconstrained | `*` | `UNCON` | timing |

`pending`, `unavailable`, `unconstrained`, and `unsupported` are four different
answers and never render as a zero, a blank, or a green tick. `unconstrained` is a
problem state and is styled like a warning, not like a missing value.

## 4. Region model

The screen is a stack of full-width horizontal bands. There is no persistent
left-hand sidebar. That is a deliberate change from the current terminal, whose
one-third-width project pane is 26 cells at 80 columns and is the direct cause of
B3 (whole sections falling off the project pane) and B6 (node detail running out of
pane before it runs out of content). Workspace metadata does not need a permanent
column; timing and stage outcomes do.

| Band | Rows | Contents | Persistence |
| --- | --- | --- | --- |
| Status bar | 1 | app, project/target, connection health, observation age | always, including under overlays |
| Command bar | 1 | primary actions, `[?] Help`, `[q] Quit` | every normal layout |
| Identity | 2 (compact) / 3 (wide) | run, target, configuration, source revision + dirty, result inputs, extent, clock, technology, worktree | every normal layout |
| Flow strip | 1 rule + 2 | all eight declared stages with state and elapsed | every normal layout |
| Instrument | 1 rule + 3 (compact) / 5 (wide) | timing; capability and check badges; design summary | every normal layout |
| Main region | 1–2 rules + content | a *pair* of stacked panels, see below | every normal layout |
| Contextual hints | 1 | bindings for the focused panel | every normal layout |
| Notification | 1 | command feedback, errors, expandable diagnostics | every normal layout |

The **main region** is always the same skeleton: `rule + upper panel + rule + lower
panel`. Only its content pair changes:

| Pair | Upper | Lower | Opened by |
| --- | --- | --- | --- |
| default | `JOBS` | `OUTPUT` | — |
| hierarchy | `HIERARCHY` | `NODE` | `h` |
| artifact | `JOBS` | `ARTIFACT` | `v` |
| stage evidence | `STAGES` | `STAGE` | Enter on the flow strip |
| badge grid | `BADGES` | `EVIDENCE` | `k` |
| connection | `CONNECTION` | `DIAGNOSTIC` | `d`, or Enter on a notification |

This is the answer to "ordinary drilldown must not erase the monitoring context":
**every drilldown is a main-region pair, so the status bar, command bar, identity,
flow strip, and instrument bands are byte-identical to the default view for the same
data.** `z` maximises the focused panel to the whole main region; that still does not
touch the bands above it.

Exactly two things cover the bands, and both are explicit and dismissible:

- **Overlays** (help, run picker, flow-extent picker, target/configuration picker)
  occupy rows 2 … H-1 at full width. Row 1 and row H are never covered, so a
  connection drop and the last notification stay readable with help open. `Esc` or the
  opening key closes them. An overlay consumes input before any pane or global
  binding, so typing in a future search field cannot launch a build or quit.
- **The reader** (`shift-M`) is the one deliberate full-screen mode: it gives rows
  2 … H-1 to one artifact, report, or diagnostic. It exists because reading 620 lines
  of generated RTL through a five-row viewport is not reading. It keeps the status bar
  and the notification row, labels itself `READER` in its rule, and exits with `Esc`.
## 5. Cell primitives

Every band is built from a small number of fixed-geometry primitives. `W` is the
terminal width in cells, `H` the height in rows. All arithmetic below is integer.

### 5.1 Rule row

`-- <TITLE> ` at each column origin, `-` to fill, ` <META> --` flush right. One row.
It carries the panel title *and* the panel's own summary — count, scroll position,
follow state, freshness, staleness — so no content row is spent on a header.

**Meta has priority over title.** When the meta would overlap a title, the title
degrades through a declared chain and the meta is never truncated:

| Full title | Degrades to | Then to |
| --- | --- | --- |
| `CAPABILITIES / CHECKS` | `CHECKS` | dropped |
| `OUTPUT  <subject>` | `OUTPUT` | dropped |
| `NODE  <name>` | `NODE` | dropped |
| `TIMING` | `TIMING` | dropped |

A truncated panel title costs nothing: the rows beneath it are self-labelling. A
truncated meta loses the follow state, the scroll position, or the staleness age,
which is exactly the information B7 and B9 show going missing today.

### 5.2 Stage cell (flow strip)

Four cells per row, two rows, eight stages. One cell per declared stage, always,
before and after execution. This is the answer to requirement "account for all stage
outcomes at compact widths": the strip **wraps to a fixed two rows**; it never elides
a stage behind an ellipsis, and the number of rows does not vary with width.

```text
cell_width Cc = (W - 10) / 4        row = 1 indent + 4 cells + 3 separators of 3
```

| Cc | Cell contents | Widths | Minimum W |
| --- | --- | --- | --- |
| ≥ 23 | glyph, name, elapsed, state word | 1 + 1 + 9 + 1 + 5 + 1 + 5 | 102 |
| 17–22 | glyph, name, elapsed | 1 + 1 + 9 + 1 + 5 | 78 |
| 11–16 | glyph, name | 1 + 1 + 9 | 54 |

`preflight` and `postcheck` are nine cells, so the name field is nine and never
truncates a declared stage name. Elapsed is `MM:SS` up to `99:59`, then `HHhMM`
(`02h47`) — always five cells. Not-yet-started stages show `--` right-aligned in the
elapsed field. When elapsed does not fit, the running stage's elapsed appears in the
flow rule's meta instead, so it is never lost.

### 5.3 Badge cell (capabilities and checks)

| Mode | Geometry | Per badge | Per row |
| --- | --- | --- | --- |
| compact | name 4 + glyph 1, gutter 1 | 6 | 7 capabilities = 41, 5 checks = 29 |
| wide | name 6 + space 1 + word 5, gutter 1 | 13 | 3 badges = 38, plus a 4-cell group prefix |

Compact names: `lint emit sim  gds  hard sgnB sgnC` and `drc  lvs  ant  ttp  gls`.
Wide names: `lint emit sim gds harden sgnBlk sgnChp` and `drc lvs antenn ttprec gsim`.

Row assignment is fixed and testable: **capabilities first, checks second.** At wide
each badge row carries an explicit `cap`/`chk` prefix. At compact the prefix does not
fit and the grouping is positional — capabilities on instrument row 1, checks on
instrument row 2, always, with full names and groups in the `k` badge grid and in the
help overlay. That is the one grouping cue this design compacts away; it does not
change any badge's state, name, or presence.

### 5.4 Timing row

Fields are separated by one space, which the total includes.

| Mode | label | value | qualifier | total |
| --- | --- | --- | --- | --- |
| compact | 6 | 11 | 17 | 6+1+11+1+17 = 36 at W=80 |
| wide | 10 | 11 | 21 | 10+1+11+1+21 = 44 at W=120 |

The qualifier carries corner/mode, producing stage, and age or provenance — `ss_100C
postcheck`, `0006 not measured`, `HIST 0004 3h12m`, `STALE ss_100C 47s`. The value
field holds `-0.084 ns`, `pending`, `unavail.`, or `UNCON`. A historical value is
labelled `HIST` with its source run and age in the qualifier and is placed on its own
`prev` row — never in the current run's `Setup` or `Hold` value field.

### 5.5 Job row

Action-first, which is the direct answer to B2 (the full internal identifier leading
the row and consuming it). The human operation name comes first; the identifier is a
right-aligned compact display id; the complete `Job_id` is in the job detail.

| Field | compact (W=80) | wide (W=120) |
| --- | --- | --- |
| selection marker | 1 | 1 |
| state word | 6 | 6 |
| elapsed | 5 | 5 |
| operation name | 50 | 60 |
| display id | 13 | 24 |
| phase | — | 15 |

Single spaces separate the marker, state, elapsed, and name fields; two-cell gutters
separate name, display id, and phase. Compact: `1+1+6+1+5+1+50+2+13 = 80`. Wide:
`1+1+6+1+5+1+60+2+24+2+15 = 118`, with a 2-cell right margin.

Compact allocates `W - 30` to the operation name and 13 to the display id. Wide adds
the phase column and a column header row.

### 5.6 Output row

One-cell stream marker, one space, `W - 2` cells of content. `|` for stdout, `!` for
stderr, `\` for a wrapped continuation. No `[stdout]` prefix is repeated per line.
Log lines wrap (up to two continuation rows, then truncate with `>`); artifact and
report content does not wrap and scrolls horizontally instead, because column
alignment is meaningful in generated RTL.

### 5.7 Command bar

`[<key>] <Label>` pairs separated by two spaces. The **last 18 cells are reserved** for
`[?] Help  [q] Quit` in every normal layout. The left group is filled with complete
pairs while one more pair plus a separating space still fits in columns 1 … W-19; the
first pair that does not fit ends the bar. Nothing is cut mid-pair, and no arbitrary
suffix of a 148-character control string is ever truncated (B9).

Unavailable commands are drawn in the disabled role and their key is bracketed with
parentheses — `(c) Cancel` — so the state survives monochrome. When the bar is full,
unavailable commands are dropped **before** available ones; every command, available
or not, is listed in the help overlay with its reason.
## 6. Wide layout — exactly 120 × 40

### 6.1 Row budget

| Rows | Count | Band |
| --- | --- | --- |
| 1 | 1 | status bar |
| 2 | 1 | command bar |
| 3–5 | 3 | identity (3 fields per row) |
| 6 | 1 | rule `FLOW STAGES` — meta: requested extent, total elapsed, current stage elapsed |
| 7–8 | 2 | flow strip, four stages per row |
| 9 | 1 | rule `TIMING` / `CAPABILITIES / CHECKS` / `DESIGN` — meta: run id, evidence freshness |
| 10–14 | 5 | instrument region, three columns |
| 15 | 1 | rule `JOBS` — meta: selected/total, focus |
| 16 | 1 | job column header |
| 17–26 | 10 | job rows |
| 27 | 1 | rule `OUTPUT` — meta: follow state, record counts, idle time |
| 28–38 | 11 | output rows |
| 39 | 1 | contextual hints for the focused panel |
| 40 | 1 | notification |

Chrome and summaries: 19 rows. Browsable content: 21 rows. `1+1+3+1+2+1+5+1+1+10+1+11+1+1 = 40`.

### 6.2 Column budget

| Band | Columns |
| --- | --- |
| status bar | left 88 (app, project/target) + right 32 (connection glyph, state, age, poll interval) |
| command bar | left 102 + reserved right 18 |
| identity | three fields of 38 with two 2-cell gutters = 118, 2-cell right margin |
| flow strip | 1 indent + 4 cells of 27 + 3 separators of 3 = 118, 2-cell right margin |
| instrument | `TIMING` 44 + sep 1 + `CAPABILITIES / CHECKS` 42 + sep 1 + `DESIGN` 32 = 120 |
| job row | 15 + name 60 + 2 + id 24 + 2 + phase 15 = 118, 2-cell right margin |
| output row | marker 1 + space 1 + content 118 |

The instrument region's five rows carry: setup WNS, hold WNS, corner/mode, setup TNS,
hold TNS on the left; seven capability badges (3+3+1) then five check badges (3+2) in
the middle; five design metrics on the right. TNS and violating-path counts are
always-visible at wide and move to the timing drilldown at compact.

### 6.3 Wireframe — populated dashboard, flow running

```text
 ....:....1....:....2....:....3....:....4....:....5....:....6....:....7....:....8....:....9....:....0....:....1....:....2
+------------------------------------------------------------------------------------------------------------------------+
|Workbench  scaf / protemu_top_physical_emulation_harness                                > connected   2s ago  poll 1s   |
|[F] Flow  [b] Build  [t] Test  [c] Cancel  [h] Hierarchy  [v] Artifact  [Tab] Pane                    [?] Help  [q] Quit|
|run:      2026-09-20T19-41-02Z-full     target:   protemu_top_physical_emu...   config:   sky130_hd_slow_corner_sig...  |
|src:      9f2c1ab  +dirty (3 files)     inputs:   9f2c1ab  clean at launch      extent:   full (build..archive)         |
|worktree: ../scaf  branch main          clock:    clk_core 100 MHz (10.00 ns)   tech:     sky130_hd  sram 1 macro       |
|-- FLOW STAGES ------------------------------------------------------- requested full   total 41:08   stage run 38:03 --|
| + build     02:41 PASS        + emit      00:18 PASS        + preflight 00:06 PASS        > run       38:03 run        |
| - postcheck    -- n/run       - collect      -- n/run       - report       -- n/run       - archive      -- n/run      |
|-- TIMING ------------------------------------- CAPABILITIES / CHECKS -------------------- DESIGN ---- run 0005  live --|
|Setup WNS  -0.084 ns   ss_100C @ postcheck  |cap lint   PASS  emit   PASS  sim    pend |cell area      12843 um2        |
|Hold WNS   +0.031 ns   ss_100C @ postcheck  |cap gds    n/run harden run   sgnBlk unsup|utilisation    58.4%            |
|Corner     ss_100C     signoff_max / func   |cap sgnChp unsup        [k] badge detail  |std cells      18274            |
|Setup TNS  -1.902 ns   14 violating paths   |chk drc    pend  lvs    pend  antenn pend |flip-flops     2941             |
|Hold TNS   +0.000 ns   0 violating paths    |chk ttprec PASS  gsim   n/run             |macros         3 (sram 1x)      |
|-- JOBS -------------------------------------------------------------------------------------------------- 4/8  focus --|
|  STATE   TIME OPERATION                                                     JOB ID                    PHASE            |
|  run    38:03 flow run (full)                                               ...02Z/0005-flow-run      route            |
|> FAIL   02:14 dune runtest physical_emulation                               ...11Z/0004-runtest       3 expect tests   |
|  canc   00:44 flow emit (cancelled by user)                                 ...11Z/0007-flow-emit     signalled TERM   |
|  queue     -- flow archive                                                  ...11Z/0006-flow-arch     queued           |
|  PASS   00:02 project driver generate-rtl                                   ...11Z/0003-gen-rtl       wrote 1 file     |
|  PASS   00:01 project driver describe                                       ...11Z/0002-describe      2 targets        |
|  PASS   00:26 dune build @default                                           ...11Z/0001-dune-build    42 steps         |
|  FAIL   00:00 project driver flow-report                                    ...11Z/0008-flow-rpt      launch failed    |
|                                                                                                                        |
|                                                                                                                        |
|-- OUTPUT  flow run (full)  stage run --------------------------------------------------- FOLLOWING  430/430  4s idle --|
|| protemu run: detailed routing, iteration 3 of 12                                                                      |
|| protemu run: congestion 0.74 (threshold 0.90), 0 overflow on met1..met4                                               |
|! openroad: [WARNING GRT-0043] antenna check deferred to postcheck stage                                                |
|| protemu run: writing 6-metal DEF to flow_results/0005/route/route.def                                                 |
|| protemu run: elapsed 38:03 in stage run; last tool output 4s ago                                                      |
||                                                                                                                       |
|| (log tail follows; 430 of 430 cached records shown, client cache holds 500)                                           |
||                                                                                                                       |
||                                                                                                                       |
||                                                                                                                       |
||                                                                                                                       |
|Jobs  up/down select   Enter details   z maximize   o output   ! first failure   Esc back                               |
|i  flow run (full) submitted 41:08 ago as run 2026-09-20T19-41-02Z-full                                                 |
+------------------------------------------------------------------------------------------------------------------------+
```

Reading the frame: `run` is at stage 4 of 8 and 38:03 into that stage; `postcheck`
through `archive` are `n/run` rather than absent; setup and hold each carry their own
corner and producing stage; `sgnBlk` and `sgnChp` are `unsup` rather than blank or
green; the selected job is row 18 and the marker is visible; the two empty job rows are
the viewport not shrinking to fit eight jobs into ten rows.

## 7. Compact layout — exactly 80 × 24

### 7.1 Row budget

| Rows | Count | Band |
| --- | --- | --- |
| 1 | 1 | status bar |
| 2 | 1 | command bar |
| 3–4 | 2 | identity (2 fields per row) |
| 5 | 1 | rule `FLOW` — meta: requested extent, total elapsed |
| 6–7 | 2 | flow strip, four stages per row |
| 8 | 1 | rule `TIMING` / `CAPABILITIES / CHECKS` — meta: run id, freshness |
| 9–11 | 3 | instrument region, two columns |
| 12 | 1 | rule for the main region's upper panel — meta: selected/total, `^N`/`vN` |
| 13–16 | 4 | upper panel (jobs by default) |
| 17 | 1 | rule for the main region's lower panel — meta: follow state, counts |
| 18–22 | 5 | lower panel (output by default) |
| 23 | 1 | contextual hints for the focused panel |
| 24 | 1 | notification |

Chrome and summaries: 15 rows. Browsable content: 9 rows. `1+1+2+1+2+1+3+1+4+1+5+1+1 = 24`.

Five rows of output is the answer to "how much useful output remains at 80×24". `z`
raises the focused panel to all nine content rows plus the freed rule, giving ten. The
current UI gives ten console rows at 80×24 but spends its upper ten rows on a 26-cell
project pane and a selected-job detail block that pushes the selected job off screen
entirely (B1, B3, B4); this layout spends them on timing, stage outcomes, and badges.

### 7.2 Column budget

| Band | Columns |
| --- | --- |
| status bar | left 60 + right 20 (connection glyph, state, age) |
| command bar | left 62 + reserved right 18 |
| identity | field 1 = 36, gutter 2, field 2 = 42 |
| flow strip | 1 indent + 4 cells of 17 + 3 separators of 3 = 78, 2 spare |
| instrument | left `TIMING` 36, gutter 2, right `CAPABILITIES / CHECKS` 42 |
| job row | 15 + name 50 + gutter 2 + display id 13 = 80 |
| output row | marker 1 + space 1 + content 78 |

Identity fields at compact: `run` and `target` on row 3; `src` + `inputs` and `config`
on row 4. Requested extent moves to the flow rule's meta; run id and freshness move to
the instrument rule's meta. Clock target, technology, and worktree move to the identity
overlay (`i`) — they are "where supplied" context, not monitoring state.

### 7.3 Wireframe A — populated jobs/output dashboard, flow running

```text
 ....:....1....:....2....:....3....:....4....:....5....:....6....:....7....:....8
+--------------------------------------------------------------------------------+
|Workbench  scaf / protemu_top_physical_emulation            > connected   2s ago|
|[F] Flow  [b] Build  [c] Cancel  [Tab] Pane                   [?] Help  [q] Quit|
|run:  2026-09-20T19-41-02Z-full       target:  protemu_top_phys...tion_harness  |
|src: 9f2c1ab+dirty  inputs: 9f2c1ab   config:  sky130_hd_slow_corner_signoff    |
|-- FLOW ------------------------------------------- extent full   total 41:08 --|
| + build     02:41   + emit      00:18   + preflight 00:06   > run       38:03  |
| - postcheck    --   - collect      --   - report       --   - archive      --  |
|-- TIMING ------------------------------ CAPABILITIES / CHECKS  run 0005 live --|
|Setup  -0.084 ns   ss_100C postcheck  lint+ emit+ sim o gds - hard> sgnB? sgnC? |
|Hold   +0.031 ns   ss_100C postcheck  drc o lvs o ant o ttp + gls -             |
|Corner sky130_hd ss_100C func_max     area 12843 um2   util 58.4%   (collect)   |
|-- JOBS ---------------------------------------------------------- 4/8  ^2 v2 --|
|  run    38:03 flow run (full)                                     0005-flow-run|
|> FAIL   02:14 dune runtest physical_emulation                     0004-runtest |
|  PASS   00:02 project driver generate-rtl                         0003-gen-rtl |
|  PASS   00:01 project driver describe                             0002-describe|
|-- OUTPUT  flow run (full) -------------------------------- FOLLOWING 430/430 --|
|| protemu run: detailed routing, iteration 3 of 12                              |
|| protemu run: congestion 0.74 (threshold 0.90)                                 |
|! openroad: [WARNING GRT-0043] antenna check deferred to postcheck              |
|| protemu run: writing 6-metal DEF to flow_results/0005/route.def               |
|| protemu run: stage run still active (38:03 elapsed, 4s since output)          |
|Jobs  up/down select   Enter details   z maximize   o output   ! failure        |
|i  flow run (full) submitted 41:08 ago as run 2026-09-20T19-41-02Z-full         |
+--------------------------------------------------------------------------------+
```

Verified against the frame: row 1 ends at column 80 with the connection block in
columns 61–80; `[?] Help  [q] Quit` occupies columns 63–80 of row 2; all eight stages
appear in rows 6–7; all twelve badges appear in rows 9–10; the selected job (`0004`) is
visible in row 14 with its `>` marker; five output rows survive.

## 8. Generic-project layout before ASIC telemetry

The dashboard must be shippable in P1, against the projects Workbench can already open,
before D1 delivers a result contract and before D2 delivers live stage evidence. The
structure does not change; only two data sources swap.

| Band | Generic Dune project today | With the scaf adapter (D1/D2) |
| --- | --- | --- |
| Status bar | unchanged | unchanged |
| Command bar | `[b] Build [t] Test [g] RTL [h] Hierarchy` | gains `[F] Flow`, `[R] Runs`, `[c] Cancel` |
| Identity | `project`, `target`, `config`, `src`; `inputs: n/a` | `run`, `target`, `config`, `src` + `inputs` |
| Flow strip | rule `OPERATIONS`, meta `no project flow declared`; one cell per runnable operation, showing its most recent job's state | rule `FLOW STAGES`; one cell per declared stage |
| Instrument left | `WORKSPACE`: target, configuration, artifact, and Dune item counts | `TIMING`: setup, hold, corner (+TNS at wide) |
| Instrument right | `INTEGRATION`: manifest, driver, discovery, hierarchy | `CAPABILITIES / CHECKS` plus the design summary |
| Main region | jobs/output, hierarchy/node, jobs/artifact pairs | unchanged, plus stage-evidence and badge-grid pairs |

Three rules keep this honest:

1. **The flow strip renders the project's *declared* stage list.** No declaration means
   no stage cells; it does not mean eight invented ones. A generic Dune project has no
   flow, so the strip becomes the operations lane above, with its own rule title. A
   project whose adapter is present but declares nothing runnable shows the eight names
   in `unsup` or `block` with the reason in the rule meta.
2. **The instrument panel set is chosen by declared capability**, not by whether a
   number happens to be available. The generic set shows the workspace and integration
   facts the current UI already reports — the same data that today falls off the bottom
   of the 26-cell project pane (B3). The ASIC set appears when the adapter declares a
   result schema, and everything in it starts `pend`, `unavl`, or `unsup`.
3. **No fixture is evidence.** The `--capture-baseline` fixtures and any development
   data populate these panels for layout work only; they do not demonstrate that
   project telemetry exists. D1 and D2 own that.

### 8.1 Wireframe B — generic Dune project, no declared flow

```text
+--------------------------------------------------------------------------------+
|Workbench  hardcaml_protemu / generic dune                  > connected   1s ago|
|[b] Build  [t] Test  [g] RTL  [h] Hierarchy  [Tab] Pane       [?] Help  [q] Quit|
|project: hardcaml_protemu_physical    target:  protemu_top_phys...tion_harness  |
|src: 9f2c1ab+dirty  inputs: n/a       config:  sky130_hd_slow_corner_signoff    |
|-- OPERATIONS -------------------------------------- no project flow declared --|
| + build     00:26   x test      02:14   + rtl       00:02   + describe  00:01  |
| + hierarchy 00:03   + artifact     --                                          |
|-- WORKSPACE --------------------------- INTEGRATION --------- discovery 0001 --|
|targets    2    configurations  3     manifest  available v1   driver  avail v1 |
|artifacts  3    (1 unavailable)       discovery Complete (job 0001), 2 targets  |
|dune items 6    lib 2 exe 1 test 3    hierarchy available (job 0003, 9 nodes)   |
|-- JOBS  focus ------------------------------------------------------ 2/4  v1 --|
|  PASS   00:02 project driver generate-rtl                         0003-gen-rtl |
|> FAIL   02:14 dune runtest physical_emulation                     0004-runtest |
|  PASS   00:01 project driver describe                             0002-describe|
|  PASS   00:26 dune build @default                                 0001-dune-bld|
|-- OUTPUT  dune runtest physical_emulation ----------------- 43/43  ! failure --|
|! FAILED: test_..._regression.ml, line 118: capture_fifo_occupancy              |
|| -|expected occupancy 4096                                                     |
|| +|actual   occupancy 4090                                                     |
|! 3 failing expect tests; run dune promote to accept the new output             |
|| dune runtest exited with status 2                                             |
|Jobs  up/down select   Enter details   z maximize   o output   ! failure        |
|i  no ASIC flow adapter declared; timing and check panels appear with D1        |
+--------------------------------------------------------------------------------+
```

The right-hand `INTEGRATION` column is the current UI's `WORKBENCH INTEGRATION`,
`Discovery`, `ARTIFACTS`, and `DUNE ITEMS` sections compressed into three rows that
are always fully drawn, instead of five sections concatenated and cut by `List.take`.
The notification row states plainly that the ASIC panels are not yet populated, so an
empty timing panel is never mistaken for a measurement.

## 9. Scenario layouts

All four required scenarios at the harder of the two reference sizes. In each one,
rows 1–11 are the same bands with the same geometry.

### 9.1 Hierarchy inspection — drilldown keeps the monitoring context

```text
+--------------------------------------------------------------------------------+
|Workbench  scaf / protemu_top_physical_emulation            > connected   2s ago|
|[F] Flow  [b] Build  [c] Cancel  [Tab] Pane                   [?] Help  [q] Quit|
|run:  2026-09-20T19-41-02Z-full       target:  protemu_top_phys...tion_harness  |
|src: 9f2c1ab+dirty  inputs: 9f2c1ab   config:  sky130_hd_slow_corner_signoff    |
|-- FLOW ------------------------------------------- extent full   total 41:08 --|
| + build     02:41   + emit      00:18   + preflight 00:06   > run       38:03  |
| - postcheck    --   - collect      --   - report       --   - archive      --  |
|-- TIMING ------------------------------ CAPABILITIES / CHECKS  run 0005 live --|
|Setup  -0.084 ns   ss_100C postcheck  lint+ emit+ sim o gds - hard> sgnB? sgnC? |
|Hold   +0.031 ns   ss_100C postcheck  drc o lvs o ant o ttp + gls -             |
|Corner sky130_hd ss_100C func_max     area 12843 um2   util 58.4%   (collect)   |
|-- HIERARCHY  focus ---------------------------------------------- 6/9  ^1 v2 --|
|  v protemu_top_physical_emulation_harness            circuit  top              |
|    v stimulus_capture_subsystem                       instance                 |
|>     fifo_memory_dual_clock_capture_buffer_wrapper    instance                 |
|      sram_macro_wrapper_sky130_sram_1rw1r_32x256_8    instance                 |
|-- NODE  fifo_memory_dual_clock_capture_buffer_wrapper ----------- Enter open --|
|  circuit  protemu_sky130_capture_fifo_dual_clock                               |
|  key      protemu_top/stimulus_capture_subsystem/fifo_memory_dual_c...         |
|  inputs   clk_write[1] write_enable[1] write_data[32] clk_read[1]              |
|           read_enable[1] reset_n[1] flush_request[1] test_mode[1]              |
|  outputs  read_data[32] full[1] empty[1] occupancy[9]   (+3 metadata)          |
|Hierarchy  up/down node   left/right collapse/expand   Esc back to jobs         |
|i  hierarchy from run 0003 (generate-rtl); flow run 0005 still active           |
+--------------------------------------------------------------------------------+
```

The `HIERARCHY`/`NODE` pair replaces only rows 12–22. The flow strip still shows `run`
executing and the timing panel still shows the postcheck values, which is the whole
point: inspecting a circuit does not stop the flow and must not stop monitoring it.
The tree gets a derived four-row viewport rather than `height - 13` clamped to one row,
which is B5: at 80×24 the current inspector shows a single node.
Node inputs **wrap** across the detail panel's rows instead of being cut inside the
second port (B6), and the overflow is stated (`+3 metadata`) rather than silently
dropped. Artifact inspection uses the same skeleton with `JOBS`/`ARTIFACT`, and
`shift-M` promotes the artifact to the reader (section 9.5).

### 9.2 Pending timing with an explicit historical reference

```text
+--------------------------------------------------------------------------------+
|Workbench  scaf / protemu_top_physical_emulation            > connected   1s ago|
|[F] Flow  [R] Runs  [c] Cancel  [Tab] Pane                    [?] Help  [q] Quit|
|run:  2026-09-20T19-58-33Z-full       target:  protemu_top_phys...tion_harness  |
|src: 3e81f04+dirty !inputs: 3e81f04   config:  sky130_hd_slow_corner_signoff    |
|-- FLOW ------------------------------------------- extent full   total 01:12 --|
| + build     01:04   > emit      00:08   - preflight    --   - run          --  |
| - postcheck    --   - collect      --   - report       --   - archive      --  |
|-- TIMING ------------------------------ CHECKS  0006 pending  prev 0004 HIST --|
|Setup  pending     0006 not measured  lint+ emit> sim o gds o hardo sgnB? sgnC? |
|Hold   pending     0006 not measured  drc o lvs o ant o ttp o gls -             |
|prev   -0.031 ns   HIST 0004 3h12m    area  HIST 0004 12801 um2   util 58.2%    |
|-- JOBS  focus ---------------------------------------------------------- 1/4 --|
|> run    00:08 flow run (full)                                     0006-flow-run|
|  PASS   01:04 flow build                                          0006-flow-bld|
|  PASS   41:52 flow run (full)  [archived 3h12m ago]               0004-flow-run|
|  PASS   00:51 flow report      [archived 3h12m ago]               0004-flow-rpt|
|-- OUTPUT  flow emit ---------------------------------------- FOLLOWING 12/12 --|
|| protemu emit: elaborating protemu_top_physical_emulation_harness              |
|| protemu emit: sky130_hd_slow_corner_signoff, 1 sram macro                     |
|| protemu emit: no timing produced by emit; run stage measures it               |
|| No timing for run 0006 yet. Values marked HIST come from run 0004             |
|| (2026-09-20T16-46-21Z) and are not a measurement of the current design.       |
|Jobs  up/down select   Enter details   R pick run   o output   Esc back         |
|!  source edited since run 0006 launched: inputs 3e81f04, tree +dirty           |
+--------------------------------------------------------------------------------+
```

Run `0006` is one minute into `build → emit` and has produced no timing. Setup and hold
read `pending`, qualified `0006 not measured`. The previous run's slack appears on a
separate `prev` row, labelled `HIST 0004 3h12m`, and the area figure carries the same
`HIST 0004` marker. The instrument rule's meta says `0006 pending  prev 0004 HIST`, so
the title degrades from `CAPABILITIES / CHECKS` to `CHECKS` (section 5.1) rather than
truncating the provenance. The archived run's own jobs are in the list, marked
`[archived 3h12m ago]`. `inputs:` on row 4 is prefixed `!` because the working tree has
been edited since `0006` launched.

Nothing in this frame can be read as a current measurement of the edited design, and
nothing is green.

### 9.3 Failure and disconnection with a long diagnostic

```text
+--------------------------------------------------------------------------------+
|Workbench  scaf / protemu_top_physical_emulation            x offline    47s ago|
|[r] Reconnect  (F) Flow  (c) Cancel  [Tab] Pane               [?] Help  [q] Quit|
|run:  2026-09-20T19-41-02Z-full       target:  protemu_top_phys...tion_harness  |
|src: 9f2c1ab+dirty  inputs: 9f2c1ab   config:  sky130_hd_slow_corner_signoff    |
|-- FLOW ----------------------------------- OBSERVATION LOST 47s   last 41:08 --|
| + build     02:41   + emit      00:18   + preflight 00:06   > run       38:03  |
| - postcheck    --   - collect      --   - report       --   - archive      --  |
|-- TIMING ------------------------------ CHECKS --------- run 0005  STALE 47s --|
|Setup  -0.084 ns   STALE ss_100C 47s  lint+ emit+ sim o gds - hard> sgnB? sgnC? |
|Hold   +0.031 ns   STALE ss_100C 47s  drc o lvs o ant o ttp + gls -             |
|Corner sky130_hd ss_100C func_max     area 12843 um2   util 58.4%  STALE 47s    |
|-- CONNECTION ------------------------------------- attempt 3   next retry 4s --|
|  endpoint   http://127.0.0.1:41733   daemon instance d41d8cd9                  |
|  last reply 2026-09-20T20-22-09Z (47s ago)   polls lost 12                     |
|  jobs and stages below are last-known values, not current evidence             |
|  no work was cancelled: the daemon owns execution across reattach              |
|-- DIAGNOSTIC  read_log 0005 ------------------------ wrapped 1/2   PgDn more --|
|  ! failed to read job log: Connect_failed("connect: Connection refused         |
|    (os error 111)") while requesting POST /v1/read_log for job                 |
|    daemon/job/2026-09-20T19-41-02Z/0005-project-driver-flow-run-full           |
|    from http://127.0.0.1:41733 after 3 attempts over 47s; the daemon           |
|    may have exited. Reattaching does not resubmit work: the daemon own         |
|Diagnostic  PgUp/PgDn scroll   r reconnect   Esc back   Enter copy path         |
|!  daemon unreachable for 47s; last stage update 38:03 into stage run           |
+--------------------------------------------------------------------------------+
```

The rules this frame demonstrates:

- **Last-known values are retained, not reset and not advanced.** `run` keeps its `>`
  glyph and its last elapsed; no stage transitions to passed, failed, or cancelled.
  Loss of observation is not completion and a quiet tool is not a hung one.
- **Staleness is stated where the value is.** The flow rule says `OBSERVATION LOST
  47s`, the instrument rule says `STALE 47s`, and each affected qualifier repeats it.
- **Connection health and command feedback stay separate.** The status bar owns
  connection state (`x offline  47s ago`); the notification row owns the message.
  Polling can no longer overwrite useful feedback, which it does today.
- **Unavailable actions remain discoverable.** `(F) Flow` and `(c) Cancel` keep their
  slots in the disabled role; `[r] Reconnect` is promoted to the first slot; `[?] Help`
  and `[q] Quit` are untouched.
- **A long diagnostic wraps into a panel, not into a truncated single row.** The
  notification row shows the head; `Enter` opens the `CONNECTION`/`DIAGNOSTIC` pair,
  which wraps the message across the lower panel and pages it (`wrapped 1/2`). At
  120×40 the same message fits in one page.

### 9.4 Help overlay

```text
+--------------------------------------------------------------------------------+
|Workbench  scaf / protemu_top_physical_emulation            > connected   2s ago|
|+-- HELP  commands ------------------------------------------ page 1/2  PgDn --+|
|| GLOBAL                                  EXECUTE  (daemon owns the work)      ||
|| ?           this help                   F           flow... pick extent      ||
|| q  ^C       quit the client             b           build                    ||
|| Tab         next pane                   t           test                     ||
|| S-Tab       previous pane               g           generate RTL             ||
|| Esc         leave pane / overlay        c           cancel selected job      ||
|| z           maximize focused pane       r           reconnect                ||
||                                         i           refresh integration      ||
|| SELECT                                  NAVIGATE  (focused pane)             ||
|| R           pick run / archive          up  down    previous / next item     ||
|| n           next target                 PgUp PgDn   page                     ||
|| m           next configuration          Home End    first / last             ||
|| a           next artifact               left right  collapse / expand        ||
|| v           inspect artifact            Enter       open details             ||
|| h           hierarchy inspector         f           follow output on/off     ||
|| k           capability / check grid     !           first actionable failure ||
||                                                                              ||
|| STATE  + pass   x fail   > running      - not run   : queued   ~ skipped     ||
||        ! blocked  ? unsupported         o pending  _ unavailable  * unconstr ||
|| Unavailable commands appear as (k)      with the reason in the pane hint.    ||
|+------------------------------------------------------------------------------+|
|i  flow run (full) submitted 41:08 ago as run 2026-09-20T19-41-02Z-full         |
+--------------------------------------------------------------------------------+
```

The overlay occupies rows 2–23 and leaves the status bar and the notification row
visible. Twenty content rows hold two columns of `key 10 + gap 2 + label 24`, four
group headings, and the state legend; the remaining commands and the badge/evidence
mapping are on page 2 (`PgDn`). Every binding in the client appears here exactly once,
generated from the same command definitions that build the command bar and the
contextual hints, so the three cannot drift.

Key scopes must not silently collide. `m` is `next configuration` globally, so the
maximise binding is `z`, and the jump to the first actionable failure is `!` rather
than a second meaning for `g`. Where a focused-pane binding does shadow a global one,
the help overlay states the scope and the contextual hint row shows the binding in
force. Resolving the final alphabet is P1's work; not reusing a key across two scopes
without a stated shadowing rule is this specification's constraint.

### 9.5 The reader — the one deliberate full-screen mode

```text
+--------------------------------------------------------------------------------+
|Workbench  scaf / protemu_top_physical_emulation            > connected   2s ago|
|-- READER  protemu_top_physical_emulation_harness.v ------------ line 121/620 --|
|    121  module protemu_top_physical_emulation_harness (                        |
|    122      input         clk_core_i,                                          |
|    123      input         reset_n_i,                                           |
|    124      input  [31:0] stimulus_data_i,                                     |
|    125      input         stimulus_valid_i,                                    |
|    126      output [31:0] capture_data_o,                                      |
|    127      output        capture_valid_o                                      |
|    128  );                                                                     |
|    129                                                                         |
|    130    // generated by hardcaml_protemu emit_rtl from run 0005              |
|    131    wire        capture_fifo_full;                                       |
|    132    wire        capture_fifo_empty;                                      |
|    133    wire [8:0]  capture_fifo_occupancy;                                  |
|    134                                                                         |
|    135    protemu_sky130_capture_fifo_dual_clock capture_fifo (                |
|    136        .clk_write_i      (clk_core_i),                                  |
|    137        .write_enable_i   (stimulus_valid_i),                            |
|    138        .write_data_i     (stimulus_data_i),                             |
|    139        .clk_read_i       (clk_core_i),                                  |
|    140        .read_enable_i    (~capture_fifo_empty),                         |
|    141        .read_data_o      (capture_data_o),                              |
|!  artifact fetch stopped at the 1 MiB limit; 620 of ~4100 lines held           |
+--------------------------------------------------------------------------------+
```

`shift-M` gives rows 2 … H-1 to one artifact, report, or diagnostic: 21 content rows at
80×24 instead of five. It is justified by B8 — the console shows the *first*
`console_height` lines of an artifact, so the `[artifact view truncated at 1 MiB]`
notice appended at the end is unreachable today. Here the retrieval limit is stated in
the notification row, which the reader does not cover, and the rule's meta carries the
line position. The status bar is not covered either, so a disconnection during a long
read is still visible. `Esc` returns to the previous main-region pair with its scroll
position intact.

This is the only full-screen mode. `z` is *not* one: it maximises a panel inside the
main region and leaves rows 1–11 alone.

## 10. Responsive behaviour

### 10.1 Mode selection

Layout mode is selected by threshold, not by interpolation:

```text
wide      W >= 118 and H >= 32
compact   W >= 70  and H >= 20
reduced   W >= 70  and H >= 18      (compact with a single main panel)
small     otherwise
```

Wide requires 118 columns because its third column plus a `TIMING` column wide enough
for `ss_100C @ postcheck` needs `32 + 42 + 2 separators + 42 = 118`. It requires 32 rows
because three identity rows and five instrument rows raise its chrome to 19, and below
32 rows the two main panels would be smaller than compact's. Between 80 and 117 columns
the compact layout simply grows — at 110 columns its timing column is 66 cells, far
roomier than a cramped three-column split would be.

This makes the mode boundary a deliberate discontinuity: 117×40 gives 25 content rows
in compact, 120×40 gives 21 in wide. Wide trades three content rows for TNS and
violating-path counts, corner/mode, five design metrics, per-stage state words, a third
identity row, and a job column header. That is the right trade on a desk monitor and
the wrong one in a narrow split, which is what the threshold encodes.

### 10.2 Derived dimensions

```text
compact/reduced:  R = min(42, max(35, W - 29))        right instrument column
                  L = W - 2 - R                      left instrument column  (L >= 27)
wide:             TIMING = min(60, W - 76), CHECKS = 42, DESIGN = 32
all:              Cc = (W - 10) / 4                   flow stage cell
compact rows:     content = H - 15
                  upper = min(8,  max(2, content / 2)),  lower = content - upper
wide rows:        content = H - 19
                  upper = min(12, max(2, content / 2)),  lower = content - upper
reduced rows:     content = H - 14, single panel
```

Surplus rows go to the **lower** panel (output) first, then the upper panel (jobs),
which is capped so a long list never squeezes the log. Surplus columns beyond `L = 60`
in the wide timing column become right margin rather than stretched fields.

| W × H | Mode | Main region rows | Instrument columns / flow stage cell |
| --- | --- | --- | --- |
| 70 × 18 | reduced | single pane 4 | L 27, R 41 / Cc 15 (name only) |
| 70 × 20 | compact | jobs 2, output 3 | L 27, R 41 / Cc 15 (name only) |
| 76 × 24 | compact | jobs 4, output 5 | L 32, R 42 / Cc 16 (name only) |
| 78 × 24 | compact | jobs 4, output 5 | L 34, R 42 / Cc 17 (+ elapsed) |
| 80 × 19 | reduced | single pane 5 | L 36, R 42 / Cc 17 (+ elapsed) |
| 80 × 24 | compact | jobs 4, output 5 | L 36, R 42 / Cc 17 (+ elapsed) |
| 90 × 28 | compact | jobs 6, output 7 | L 46, R 42 / Cc 20 (+ elapsed) |
| 100 × 30 | compact | jobs 7, output 8 | L 56, R 42 / Cc 22 (+ elapsed) |
| 110 × 31 | compact | jobs 8, output 8 | L 66, R 42 / Cc 25 (+ state word) |
| 117 × 40 | compact | jobs 8, output 17 | L 73, R 42 / Cc 26 (+ state word) |
| 118 × 32 | wide | jobs 6, output 7 | T 42, C 42, D 32 / Cc 27 (+ state word) |
| 120 × 40 | wide | jobs 10, output 11 | T 44, C 42, D 32 / Cc 27 (+ state word) |
| 160 × 50 | wide | jobs 12, output 19 | T 60 (capped), C 42, D 32 / Cc 37 |
| 69 × 24 | small | — | — |
| 80 × 17 | small | — | — |

### 10.3 The reduced tier, and the minimum

`reduced` exists because 18–19 rows is an ordinary tmux split. It drops the main
region's split: one panel, one rule, chrome 14. Its rule meta names what was hidden
(`z jobs`), so the pane is not silently missing.

**The proposed minimum supported size is 70 × 18.** Both numbers are derived:

- **Width 70** is `27 + 2 + 41`: the narrowest `TIMING` column that still fits a label,
  an eleven-cell slack value, and an eight-cell qualifier, plus the 41 cells that seven
  capability badges occupy at six cells each. At 70 columns the flow strip consumes
  exactly `1 + 4×15 + 3×3 = 70`, with the per-stage elapsed moved to the rule meta.
- **Height 18** is `14 + 4`: the reduced chrome plus the smallest main panel that shows
  a selected row with context above and below it.

The current constants are `minimum_width = 68` and `minimum_height = 20` in
[`main.ml`](../terminal/main.ml). The new minimum is two columns wider and two rows
shorter. 68 columns was two cells short of what this layout actually needs, and 20 rows
excluded terminals this layout serves; the resemblance is coincidence, not inheritance.

The mechanical floor is lower — dropping the design row and merging the footer rows
would render at 70 × 15 — and is deliberately not adopted. Three further degradation
steps to gain three rows is more layout modes than the gain justifies, and below 18 rows
the main panel cannot show a selected row in context.

### 10.4 Below the minimum

```text
+----------------------------------------------------------------+
|                                                                |
|                                                                |
|                                                                |
|                                                                |
|                       Hardcaml Workbench                       |
|                                                                |
|         Terminal is 64x14; the dashboard needs 70x18.          |
|        Enlarge the window or the tmux pane to continue.        |
|                                                                |
|             q  quit      ?  help      r  reconnect             |
|                                                                |
|                                                                |
|                                                                |
|                                                                |
+----------------------------------------------------------------+
```

The small-terminal view states the actual size and the required size, says what to do,
and keeps `q`, `?`, and `r` working, so a client that is resized too small is
recoverable and a client whose daemon died while the window was small can still be
reconnected. It is centred and needs no minimum of its own beyond one readable line.
The current message omits `?`; the new one includes it.

### 10.5 Reduced-tier wireframe

```text
+--------------------------------------------------------------------------------+
|Workbench  scaf / protemu_top_physical_emulation            > connected   2s ago|
|[F] Flow  [b] Build  [c] Cancel  [Tab] Pane                   [?] Help  [q] Quit|
|run:  2026-09-20T19-41-02Z-full       target:  protemu_top_phys...tion_harness  |
|src: 9f2c1ab+dirty  inputs: 9f2c1ab   config:  sky130_hd_slow_corner_signoff    |
|-- FLOW ------------------------------------------- extent full   total 41:08 --|
| + build     02:41   + emit      00:18   + preflight 00:06   > run       38:03  |
| - postcheck    --   - collect      --   - report       --   - archive      --  |
|-- TIMING ------------------------------ CAPABILITIES / CHECKS  run 0005 live --|
|Setup  -0.084 ns   ss_100C postcheck  lint+ emit+ sim o gds - hard> sgnB? sgnC? |
|Hold   +0.031 ns   ss_100C postcheck  drc o lvs o ant o ttp + gls -             |
|Corner sky130_hd ss_100C func_max     area 12843 um2   util 58.4%   (collect)   |
|-- OUTPUT  flow run (full) ----------------------- FOLLOWING 430/430   z jobs --|
|| protemu run: detailed routing, iteration 3 of 12                              |
|| protemu run: congestion 0.74 (threshold 0.90)                                 |
|! openroad: [WARNING GRT-0043] antenna check deferred to postcheck              |
|| protemu run: writing 6-metal DEF to flow_results/0005/route.def               |
|| protemu run: stage run still active (38:03 elapsed, 4s since output)          |
|Output  PgUp/PgDn scroll   f follow   z jobs   Tab pane   ! failure             |
|i  jobs list hidden: 19 rows cannot hold both panes (needs 20)                  |
+--------------------------------------------------------------------------------+
```

## 11. Overflow, identity, and selection rules

### 11.1 What shortens, wraps, moves, or scrolls

| Content | Behaviour when it does not fit |
| --- | --- |
| Run, job, artifact, node identifiers | middle-truncate keeping the final `/` component; full value in the drilldown |
| Target and configuration names | middle-truncate keeping the distinguishing tail (`..._slow_corner_signoff`) |
| Project root and paths | middle-truncate keeping the final component, as `Presentation.middle_truncate` already does |
| Stage names | never truncated; the name field is nine cells, the longest declared stage |
| Per-stage elapsed | moves to the flow rule's meta below `Cc = 17` |
| TNS, violating paths, corner/mode detail | move from the instrument region to the timing drilldown at compact |
| Clock target, technology, worktree | move from identity to the `i` identity overlay at compact |
| Design metrics beyond area and utilisation | move to the design drilldown at compact |
| Node ports and metadata | wrap across the detail panel; the remainder is counted (`+3 metadata`), never dropped silently |
| Log lines | wrap up to two continuation rows marked `\`, then truncate with `>` |
| Artifact and report lines | do not wrap; scroll horizontally |
| Long diagnostics | head in the notification row, full text wrapped and paged in the `DIAGNOSTIC` panel |
| Job list, output, tree, artifact | scroll with an explicit position in the rule meta |
| Command bar | drops whole pairs, unavailable first; never cuts a pair; never touches the reserved 18 cells |
| Panel titles | degrade through the chain in section 5.1; the meta is never truncated |

Every truncation in the table above is either a wrap or a middle-truncate that keeps a
meaningful component. That is B11: today only `Root:` truncates intelligently and every
other line is a byte-length prefix plus `...`.

Truncation always costs the marker: a field of `n` cells shows at most `n - 3`
characters plus `...`. A field narrower than eight cells is not truncated but replaced
by `...`, because three characters of an identifier identify nothing. No field in any
band specified here is narrower than eight cells at the minimum size.

### 11.2 Keeping identity useful

An identifier that has been shortened must still distinguish the thing it names. Three
rules, in order:

1. Job and run display ids are the **final `/`-separated component** of the full id,
   middle-truncated. `daemon/job/2026-09-20T19-41-02Z/0005-project-driver-flow-run-full`
   displays as `0005-flow-run`. No numeric-suffix assumption is made: the component is
   taken as text.
2. Target, configuration, and circuit names are middle-truncated, which keeps the
   **tail**. In this project the tail is what differs (`sky130_hd_slow_corner_signoff`
   versus `sky130_hd_fast_corner_signoff`), so a leading-prefix truncation would make
   two configurations look identical.
3. The complete value is always reachable: the job detail, the identity overlay, the
   node detail, and the badge grid each carry the untruncated text, wrapped.

### 11.3 Keeping the selection visible

B1 is that the selected job is not on screen at 80×24 and there is no scroll offset
tied to selection. The invariant:

> After any change to the selection, the item list, or the viewport height, the scroll
> offset `s` satisfies `s <= i <= s + n - 1` for the selected index `i` and viewport
> height `n`, and `s` is clamped to `[0, max(0, count - n)]`. When `n >= 5`, a one-row
> margin is preferred: `s + 1 <= i <= s + n - 2` where the clamp allows it.

This is computed in layout preparation, from the selection and the data, and never as a
side effect of drawing — the current `hierarchy_view_lines` and connection-detail
rendering mutate scroll state while drawing, which is what makes the defect invisible
until a resize. Hidden items are counted in the rule meta as `^N` and `vN`.

Selection is by stable identity (`Job_id`, node key, artifact id), not by index into a
newest-first list, so an arriving job cannot move the selection. Viewport heights do not
shrink to fit a short list: eight jobs in a ten-row viewport leave two blank rows rather
than reflowing the whole screen.

## 12. Command bar and footer budgets

| Band | Budget | Contents |
| --- | --- | --- |
| Command bar (row 2) | `W - 18` left, 18 reserved right | primary actions; `[?] Help  [q] Quit` |
| Contextual hints (row H-1) | `W` | focused panel name, then its bindings |
| Notification (row H) | `W` | one marker cell, then command feedback or an error |

The complete shortcut list does not go in one row; that is what produced the
148-character control string and B9. The bar carries at most the primary actions for
the current project capability — at 80 columns that is four pairs plus the reserved
help/quit block — and the full list lives behind `?`.

The hint row is derived from the focused panel, which is named first so focus is
legible even without colour: `Jobs  up/down select  Enter details  z maximize  o
output  ! failure`. Focus is also marked on the focused panel's rule (`-- JOBS  focus
---`), so the two cannot disagree.

The notification row's marker is `i` for feedback, `!` for a problem. It is written only
by user actions and by errors, never by the polling loop; connection state belongs to
the status bar. Feedback persists until it is superseded, dismissed with `Esc`, or ages
out, so normal polling cannot erase it. When the text exceeds `W - 3` cells it is
truncated with `+` and `Enter` opens the full text in the `DIAGNOSTIC` panel.

## 13. Relationship to the existing requirements

**No product requirement is weakened by this design.** Every architecture dashboard
region and every declared stage and badge is present in both reference layouts. What
changes is *where* secondary detail lives, which the architecture explicitly permits:
"resizing may compact them but must preserve identity, execution state, timing summary,
and stage outcomes".

Compactions, all of them reversible by widening the terminal:

| Requirement | Wide (120×40) | Compact (80×24) |
| --- | --- | --- |
| Eight flow stages with elapsed | present, with state words | present, with elapsed |
| Twelve capability/check badges | present, grouped with `cap`/`chk` prefixes | present; grouping is positional |
| Setup and hold with corner, stage, age | present | present |
| TNS and violating-path counts | present | timing drilldown |
| Compact design summary | five metrics | area and utilisation |
| Clock target, technology, worktree | identity rows | identity overlay |
| Tool substep within a stage | stage cell, when `Cc >= 23` | stage drilldown and output rule meta |

Three deliberate divergences, stated rather than assumed:

1. **No persistent left-hand sidebar in the terminal.** Architecture section 8's
   sidebar-plus-workspace sketch is explicitly the *browser* client's layout; the
   terminal is only required to present the same state "as panes, tables, and trees".
   Horizontal bands are that presentation. The sidebar is what causes B3 and B6.
2. **The minimum supported size changes from 68 × 20 to 70 × 18.** This is a code
   constant, derived in section 10.3, not a product requirement.
3. **The prettification schematic is superseded.** Its abbreviated flow strip ended in
   `...`; this design wraps to two rows instead, as that document itself required.

One open question that belongs to D1, not here: the architecture lists `lint, emit,
sim, GDS, harden, signoff-block, signoff-chip` as *desired* badges and requires the
project to declare their mapping to real operations and evidence. This specification
reserves seven capability slots and renders `unsup` for any that the project does not
declare. If D1 finds that the real mapping needs a different number of badges, the
compact right column's width changes with it (`7 × 6 - 1 = 41` today) and section 5.3
must be updated. Nothing else in the layout depends on the count.

## 14. Acceptance criteria

Objective and mechanically checkable. `L1`–`L6` are frame-geometry properties best
tested by rendering at many sizes; `L7`–`L15` are display-model or single-region
properties that do not need a whole-screen snapshot. None of them requires a real
daemon, a real flow, or a colour judgement.

| ID | Criterion |
| --- | --- |
| L1 | For every `W` in 70…200 and `H` in 18…60, the frame is exactly `H` rows of exactly `W` display cells, measured with `View.uchar_tty_width`, for every scenario fixture including non-ASCII names. |
| L2 | In every `wide`, `compact`, or `reduced` frame, all of the bands in section 4 are present with the row counts section 10.2 derives, and no row is unassigned. |
| L3 | All eight declared flow stages appear, each with a state glyph and a name that is not truncated, in every `wide`, `compact`, and `reduced` frame. No frame contains an ellipsis in place of a stage. |
| L4 | All seven capability badges and all five check badges appear in every `wide`, `compact`, and `reduced` frame; capabilities precede checks; no badge renders as blank. |
| L5 | Columns `W-17`…`W` of the command-bar row are exactly `[?] Help  [q] Quit` in every `wide`, `compact`, and `reduced` frame. The `small` view contains `q` and `?`. No command-bar pair is cut mid-pair. |
| L6 | For every item count 1…200, every selected index, and every viewport height ≥ 2, the selected row is inside the viewport and the scroll offset is inside `[0, max(0, count - n)]`; hidden counts in the rule meta equal the real hidden counts. |
| L7 | `pending`, `unavailable`, `unconstrained`, `unsupported`, `not run`, `skipped`, `blocked`, and `cancelled` each render as their own distinct glyph and word. No such state renders as `0.000`, as blank, or with the passed style. |
| L8 | A timing value from a run other than the selected one renders on a `prev` row, carries `HIST`, its source run id, and its age, and never appears in the selected run's setup or hold value field. |
| L9 | With observation lost, no stage or badge state changes, every previously known value is retained, and a staleness age appears in the flow rule, the instrument rule, and each affected qualifier. |
| L10 | For identical display data, rows 1 through the end of the instrument band are byte-identical across all six main-region pairs and with a panel maximised by `z`. |
| L11 | Overlays occupy rows 2…`H-1` only; row 1 and row `H` are unchanged from the underlying frame. An overlay consumes a key that would otherwise trigger a global action. |
| L12 | Below 70 × 18 the frame is the small-terminal view; it contains the actual size, the required size, and `q`, `?`, and `r`; and `q` exits from it. |
| L13 | No rendered field exceeds its allocation. A truncated field ends in `...`, and a field of ≥ 12 cells that held a `/`-separated value still shows its final component. |
| L14 | Mode and every derived dimension follow section 10.2 exactly for all `W`, `H`: per-stage elapsed appears iff `Cc ≥ 17`, state words iff `Cc ≥ 23`, `wide` iff `W ≥ 118 and H ≥ 32`. |
| L15 | Surplus rows go to the lower main panel before the upper one, the upper panel is capped at 8 (compact) or 12 (wide), and a viewport does not shrink below its derived height when the list is short. |

`L1`, `L3`, `L4`, `L5`, and `L14` replace the whole-screen expectation habit with a
property check over a size sweep; they are cheap and they catch the entire class of
defect the baseline captures recorded. Keep whole-screen expectations for the
representative frames in sections 6, 7, 8, and 9 only — one per layout, not one per
state × size combination.

## 15. Out of scope here

- Colour values, palette selection, and contrast. Section 3 of
  [prettification.md](prettification.md) owns the semantic roles; this document only
  requires that every state be distinguishable without colour.
- Any renderer change. P1 implements this; the
  [baseline captures](terminal_baseline_captures.md) stay as the record of what the
  screen looked like before it.
- A generic layout engine, a theme system, a transport refactor, and new dependencies.
  The derived dimensions in section 10.2 are a dozen lines of integer arithmetic over
  `Bonsai_term.Dimensions.t`, not a constraint solver.
- Mouse support, search and filter, resource charts, and per-node measurement views.
  Those are P5.
