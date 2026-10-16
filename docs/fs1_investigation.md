# FS1 — Retained ASIC evidence investigation

Recorded 2026-10-16 from actual Workbench/provider source and retained results.
**The FS1 functional evidence-investigation scope is complete for the adopted
declared/available evidence.** This includes rich timing paths,
measured clock reports, stage-attributed physical/routing evidence, and an exact
external binary handoff. It does not claim completion of every later F06 extension.

This is the followup to [FS1 acceptance](fs1_acceptance.md) and
[lifecycle and artifacts](fs1_lifecycle_and_artifacts.md). Their statements that
these investigation surfaces remain missing describe earlier slices. The original
[FS1 requirements](feature_sets.md#fs1--asic-evidence-investigation) and
[F06 requirements](features/hardware_inspection.md) remain accounted for below;
completion here is scoped to evidence actually supplied by this adoption.

## Evidence and verification status

The latest retained run is
`/tmp/opencode/workbench-fs1-investigation-hd0uuqio/` (called **E** below):

- `result.json`: `status: passed`, all recorded checks passed, four domains,
  17 allowlisted read-only provider calls, `input_files_unchanged: true`.
- `validated-indexes.json`: actual normalized timing/clocks/physical/routing
  indexes, including source hashes, inclusive line spans, producer attribution,
  diagnostics and freshness flags. The four validated indexes are not truncated.
- `independent-timing-paths.json`: independently enumerated original max/min
  report blocks, compared with the provider's complete path set.
- `*-detail-*.txt`, `*-source-*.txt`, axis/filter/sort captures and corresponding
  ANSI recordings: actual 120-column × 40-row PTY interaction.
- `binary-result.json`, `binary-viewer-calls.jsonl`, `klayout-command.json`,
  `klayout-layout.json`, `read-exported-gds.py`, `klayout.stdout` and
  `klayout.stderr`: exact binary export and actual layout-reader evidence.
- `commands.json`, `relay-policy.json`, `provider-calls.jsonl`, query stdout/stderr,
  and before/after inventories retain the invocation and isolation evidence.

The registered ASIC run is `965b68b0f7454e14bc7d6f12f32ab9c7`. Its exact execution is
`/tmp/opencode/workbench-fs1-physical-w0rftdi0/results/signoff-777507-32d94e083532545001af7184276233f2/execution-965b68b0f7454e14bc7d6f12f32ab9c7.json`,
with raw-byte SHA-256
`9c6a95c0a64ac0287425974ba5573c1c2d68a6a11c043f2ee95ff491f2d81a12`.
The accepted finalization reference comes from
`/tmp/opencode/workbench-fs1-acceptance-5oa67d8u/operation.json`.
Investigation adopts those existing references; it does not create another
physical execution or acceptance verdict.

Final parent verification passed, with checks run through the serialized wrapper:

- Provider: `dune build -j20 @test/inspection @test/ocaml-stage-report`.
- Workbench: `@fmt`, `@lint`, full build, and full `dune runtest -j20`.
- Installed native lifecycle/discovery/RTL/hierarchy/resize checks: latest run
  `vrXGZ6`, passed.
- Actual terminal interrupt checks:
  `/tmp/opencode/workbench-terminal-interrupt-xth8tynj/results.json`, all five
  cases passed (normal, filter-active, palette-active, unfinished-paste,
  completed-paste).
- Cached synthesis inspector:
  `/tmp/opencode/workbench-synthesis-inspector-arle_91_/result.json`, passed.
- Final retained-real rich investigation **E**, passed, including exact GDS
  export and headless KLayout loading.

The parser race, multi-clock, corner-conflict and budget edge cases have focused
provider fixture coverage; the final real run exercises the installed generation
containing those changes. It does not mean every adversarial fixture condition
occurred in the real reports. The prior `workbench-fs1-investigation-jmo4p9yg`
pass used the first provider candidate and is historical evidence.

## Source and provider boundary

Workbench uses `protocol/asic_inspection.ml`, `adapters/asic_adapter.ml`,
`backend/asic_inspection.ml`, `backend/asic_service.ml`, and
`terminal/inspection_view.ml`. The adapter invokes the public read-only contract:

```text
inspect EXECUTION --domain DOMAIN --stage STAGE --json
inspect EXECUTION --domain DOMAIN --stage STAGE --json --row-id ID --expected-digest DIGEST
```

The provider owns parsing in `execution/results/inspection_service.ml`; the
installed copy under the generation below is the implementation reference for
this acceptance. `../hardcaml_asic/execution/results/inspection_service.ml` is
the sibling development source location, not proof of a link to its current HEAD.
The contract is
`hardcaml-asic.inspection`, schema 1. Tiles consume typed rows and original
provenance rather than reverse-engineering reports. Selected checkpoint
`segment.json` supplies the exact run directory and returned-step sequence.
Numbered producer directories are checked against that sequence and retained
configuration metadata. Selection is not a newest-directory heuristic.

Each row preserves source path and raw-byte SHA-256, one-based inclusive span,
step ID/occurrence, boundary, carry-forward flag, configuration reference, units
evidence and design/constraint references. Row IDs hash source/span/domain/category/
name, not display position. The source digest covers execution identity, observed
source hashes, rows and diagnostics. The provider checks bounded regular files
for concurrent change and rechecks all observed hashes before returning.
Execution parsing/validation uses the captured execution bytes. Captured manifests
must agree with the validated snapshot, and each segment is decoded from the exact
captured bytes against its validated manifest inventory hash. This binds parsing
to the validated source generation: a stable replacement B after validation of A
cannot become accepted evidence merely because B's later hashes agree with B.
Workbench independently hashes the registered canonical execution before and
after reads and fences publication against allocation/cursor/execution changes
and cancellation. Detail must match the exact run/domain/stage/row/source digest.

Supplementary reports are explicitly labeled
`observed supplementary-not-checkpoint-inventoried`. Hashing the bytes observed
now does not retroactively make those reports checkpoint-inventoried immutable
artifacts. Original scope and carry-forward attribution stay visible.

### Installed development provider and deployment caveat

The final acceptance used this exact private generation (the reusable test resolves
the store's `current` pointer unless an explicit `--provider` is supplied):

```text
/tmp/opencode/workbench-fs1-inspection-provider/generations/59466eda06df463e8d921678830ff5c2/bin/hardcaml-asic-flow
```

The receipt read at
`/tmp/opencode/workbench-fs1-inspection-provider/current/receipt.json` identifies
that generation; its generation-local sibling `receipt.json` retains the receipt.
It records development source
`/home/wayne/devel/jane/hardcaml_asic`, captured snapshot SHA-256
`0423a76848cdc41f79ec5fd67502445b08b783050d8eba9de83991e8550cda09`,
recorded revision `1714764859274f80a9f5ad207421a04601824e99`, and observed base
revision `031498db573949793e980f4d645c343e6b705915`. Both difference flags are true.
The receipt says “captured bytes; not an atomic checkout or a clean-tree claim”
and “local refresh receipt, NOT P6.5 source stamp.” This identifies the installed
capture, not the sibling checkout's current HEAD or an automatically linked build.
Generation `4ec8d7b67cec41f391b68565e8ece460` (snapshot
`b6e6618fbb9eb1ccfff56d4bc8b6d83aa6fb40607c6e506524872d87bfc7adde`)
was the first candidate, not the final accepted provider.

The actual installed `--version --json` output in
`E/query-1792117711909609554.stdout` reports `source.stamped: false`, unknown
revision/state/inventory and unverified library/executor artifact match. A local
installation receipt and report-byte hashing do not supply that missing source
stamp. CLI4 compatibility is separate from source-artifact identity.

Manual-demo followup: an `invalid command: inspect` error was traced to the
example configuration still selecting the older provider. Its `provider_executable`
now selects the final generation above, whose metadata was checked to advertise
`inspection1: true`. The owner's active daemon/client were left running at that
point; restart and re-registration were required to adopt the new configuration. This config
correction is not a claim that the already-running daemon hot-reloaded it.
The acceptance harness used its own project configuration and read-only relay.
The owner subsequently opened the retained timing path in the manual client.
That observation establishes the viewed workflow, not migration of every saved
configuration namespace. The [README manual route](../README.md#open-the-completed-fs1-example)
records the exact registration and launch steps for the current provider.

To adopt the new provider in the owner application, `provider_executable` must
explicitly select the generation above and the project must be reopened so the
configuration is reread. Persistent ASIC registration/cache identity includes
configuration identity, so changing the provider path does not automatically
transfer the old registry. Preserve existing state/layout and re-register the
exact known allocation/execution and finalization references under the new
configuration. Use the owner's existing daemon/session lifecycle for that reopen;
this is not an instruction to start a competing daemon or overwrite saved layout.
The accepted test state's private relay has an ephemeral deadline and is not a
production/demo provider configuration to activate.

## Timing paths and navigation

### Escape responsiveness in tmux — 2026-10-16 followup

The reported pause when closing a table or path detail was reproduced with a
private tmux server. The owner's server reported `escape-time 500`: tmux waits
up to 500 ms to disambiguate a standalone Escape from a key sequence. Installed
Notty_async itself has no corresponding Escape timer. Workbench also previously
waited for its 100 ms display clock after mutating local navigation state.

The TUI now invalidates the Bonsai view immediately after local input and after
deferred actions/poll completion. Domain refresh still polls every 500 ms; the
100 ms display clock remains for time-dependent content. This is a local feedback
fix, not a claim of a fully subscription-driven transport rewrite.

Actual 200×60 PTY observations (three samples per transition):

| Candidate / private tmux setting | Timing table → workspace | Detail → table |
| --- | --- | --- |
| Before, 500 ms | 586–592 ms | 589–608 ms (cached source-detail pane) |
| Before, 0 ms | 3–108 ms | 105–107 ms (cached source-detail pane) |
| After, 500 ms | 503–505 ms | 502–505 ms (cached source-detail pane) |
| After, 10 ms | 13.5–14.3 ms | 12.7–14.7 ms (actual provider path detail) |

These are host-PTY-observation bounds, not remote display/compositor guarantees.
Evidence: `workbench-inspector-latency-03a5e823`, `...-9d3gcbak`, `...-pgsdv2mg`,
and final `...-pa1haj23`, all below `/tmp/opencode`. The final run passed an 80 ms
regression ceiling for palette/table/real-detail/filtered-table exits. Cached
indexes contain all 1020 actual timing paths; provider detail reads are allowed
only during setup, with no provider calls during measured Escape transitions.
Private source state/config inventories were unchanged. Format/lint, terminal
unit tests/build, installed native workflow, and all five Ctrl-C modes passed
(`workbench-terminal-interrupt-_1pdl_38`).

To reduce the tmux delay, explicitly run `tmux set-option -s escape-time 10` in
the relevant tmux server; this is a server-wide setting. Persist it with
`set -s escape-time 10` in the user's tmux configuration if desired. Workbench
does not change that setting automatically. Reopen only the rebuilt client to
get immediate local redraw; the existing daemon can remain running.

**Owner confirmation, 2026-10-16:** after the fix and setup guidance the owner
reported that it works fine. This closes the reported manual Escape-latency issue.
It is distinct from the measured private-tmux acceptance above and does not select
a final visual design or establish all lifecycle/terminal permutations.

Reproduce without affecting the owner's tmux server or application processes:

```sh
./scripts/with-switch.sh python3 -B scripts/test-inspector-latency.py \
  --detail-mode real \
  --provider /tmp/opencode/workbench-fs1-inspection-provider/generations/59466eda06df463e8d921678830ff5c2/bin/hardcaml-asic-flow \
  --tmux-escape-time 10 --single-escape-only --iterations 3 --max-latency-ms 80
```

The script owns its tmux socket, daemon, client, and rekeyed state copies. Omit
`--max-latency-ms` for diagnostic runs with an intentionally large Escape wait.
Its incremental screen parser has a pure `--self-test-screen` check, including
fragmented UTF-8/escape sequences and tmux erasure/charset controls.

### Current inspector mode and controls

Opening **Inspect timing paths** attaches a client-local explorer to the focused
tile and covers the current window. It is not another workspace or a persisted
layout change. Enter opens the selected path's detail; **Esc returns to its table,
then Esc again closes the explorer**. Switching to the already-active Overview
does not dismiss the inspector remembered by its focused tile. The global palette
remains available with Space c c, and Ctrl-C exits the client from every mode.

This behavior is functional but not sufficiently self-describing. Breadcrumbs,
mode-specific help, an explicit Close inspector palette command and less prominent
raw JSON/full paths are [presentation followups](backlog/README.md#inspector-usability-polish),
not implemented controls or remaining FS1 feature blockers.

The signoff timing index contains **1020 actual timing paths**, plus its recorded
input-reference row. Every max/min block matches the independently read original
report span, startpoint, endpoint, group, type and signed slack. Corners are
`nom_fast_1p32V_m40C`, `nom_slow_1p08V_125C`, and `nom_typ_1p20V_25C`, with
producer `OpenROAD.STAPostPNR@11-openroad-stapostpnr`. Max/setup and min/hold
remain separate fields; the group is `clk`. Known minima include slow max
approximately `11.6755 ns` and fast min `0.125029 ns` at report precision.

Rows retain arrival, required time and slack. Detail includes numbered original
pathpoints from `Startpoint:` through the slack line, with bounded surrounding
context. The repeated subtraction-form arrival in the arithmetic summary does
not replace the first actual arrival measurement. `ns` comes from the exact
retained generated Liberty selected by `state_out.json`, including its hashed
`time_unit: "1ns"` declaration; absent/conflicting unit evidence stays unknown.

Open the global palette with **Space c c**, then choose **Inspect timing paths**,
**Inspect clocks**, **Inspect physical**, or **Inspect routing** for the selected
run/stage. Defaults are timing/signoff, clocks/signoff, physical/placement and
routing/routing.

| Control | Behavior |
| --- | --- |
| `j` / `k`, up/down; `n` / `N` | Row navigation or detail scrolling/paging |
| `/`, text/backspace, Enter or Esc | Edit/finish a literal case-insensitive substring filter; no regex semantics |
| `s` | Numeric ascending, numeric descending, name; row ID breaks ties and selection remains by ID |
| `c` / `g` / `p` | Cycle actual corner/group/producer values and ALL |
| `v` in timing | Near/violated view: violated status or signed value ≤1 ns (also 1000 ps / 1e-9 s where supplied) |
| `t` | Cycle synthesis → floorplan → placement → CTS → routing → signoff |
| Enter | Explicit exact-row/digest detail request |
| `d` | Source metadata and diagnostics already present in the index |
| `r` | Explicit current-evidence refresh |
| Esc | Leave detail, then leave explorer |

Near-limit filtering is a fixed slack threshold, not a new timing-goal verdict.
Metadata, filters, axes, sorts, navigation and warm reopening are provider-free.
Stage changes explicitly request the selected index; the exercised synthesis
timing stage returns zero rows with “missing relevant retained evidence,” not zero
slack. Missing evidence is different from a filter matching zero rows.
The final PTY also proves that bracketed paste into the active filter keeps
`r`/`t`/`j`/`p` literal: it causes no refresh, stage change, navigation/producer
action or provider call. Command bindings apply outside filter editing.

Each tile owns its filter, selection, sort, near mode and scroll. The PTY proves
independent explorers, a pinned tile retaining local near mode while a following
tile loses its run selection, and provider-free warm reopening. Detail scrolling
is clamped: the first reverse key after overscrolling changes the viewport.

Constraint/configuration JSON pointers (`PNR_SDC_FILE`, `SIGNOFF_SDC_FILE`) and
`state_in.json` input-reference rows expose SDC, netlist/design and related inputs.
These are evidence references, not proof of complete constraint coverage or a
source jump into OCaml. No reliable OCaml/netlist mapping is inferred from names;
generated RTL/report locations remain distinct from original source mapping.

## Measured clocks, physical design and routing

Clock inspection retains actual rise/fall network measurements rather than
substituting the declared period. The slow-corner evidence verifies:

| Measurement | Value |
| --- | --- |
| Rise → rise network skew | 0.085678 ns |
| Fall → fall network skew | 0.079398 ns |
| Rise → rise minimum latency | 0.470431 ns |
| Fall → fall maximum latency | 0.545056 ns |

`latency_min/max` is labeled total source-plus-network latency; separately parsed
source/network quantities retain their semantics and transition/endpoints.
Minimum period and fmax are reported measurements; MHz labeling requires observed
ns units. `clock_check_skew` is separately labeled setup/hold check skew including
uncertainty and CRPR, not network skew.

The final clock parser maintains explicit clock/transition context across
multi-clock reports, preserves supplied sources and generated/master/source-clock
relationship fields, divide/multiply/edge/shift/invert headers, and assigns
network endpoints using the report's min/max columns. Switching clock context
resets transition/column context; quantities missing that context are diagnosed
rather than attached to the preceding clock. Supplied extension headers are
retained verbatim as `header:...` fields without assigning unsupported semantics.
These are parsed supplied fields, not proof that this real single-clock specimen
contains generated clocks or a complete generated-clock relationship graph.

Conflicting report-versus-directory corners are quarantined in timing paths,
clock network reports and check-skew reports: raw fields/source remain inspectable,
but value/unit/unit evidence are withheld and status is unavailable, with explicit
corner-conflict diagnostics. This distinct policy does not suppress the separately
retained header-versus-STA-propagation conflict described below.

The retained headers say `Virtual: yes` and `Propagated: no`, while each corner's
STA log says no propagation information was present in the input SDC and all
clocks were being propagated. Header rows and `clock_propagation` diagnostics are
preserved separately. The UI does not resolve that conflict into an invented
single propagation truth. Coverage/check/unpropagated/violator reports remain
inspectable; this does not prove complete generated-clock or constraint coverage.

Physical inspection includes retained floorplan geometry, counts/areas,
utilization, rows/sites and placement analysis, with earlier boundary data
explicitly carried forward. Actual legalized placement rows from
`OpenROAD.DetailedPlacement@21-openroad-detailedplacement` include 717 instances
and `13363.1 µm²`. These are not the earlier 673-cell synthesis snapshot.
Legalized HPWL before mirroring and post-mirroring HPWL are separately attributed;
neither is relabeled routed wirelength.

Routing inspection parses provider-owned per-layer resource, demand, usage,
horizontal/vertical/total overflow, native routing metrics and log quantities.
The retained Metal2 row exposes real congestion fields. DetailedRouting reports
`route__net = 1051` and `route__vias = 5543` as native counts. Global routing,
detailed routing/DRC and antenna records preserve separate categories/producers.
The missing RepairAntennas `or_metrics_out.json` is diagnosed, not replaced by a
zero or an antenna pass. Investigation detail does not create a signoff verdict.

Native duplicate scalar keys are preserved as separate source-span occurrences,
with diagnostics, rather than last-key-wins JSON normalization. This occurs in
the retained floorplan, placement and routing indexes. The bounded provider policy
allows up to 16 occurrences per key and reports overflow/truncation. Malformed
or nonfinite native quantities retain raw evidence with null value/unavailable
status and diagnostics; malformed timing blocks are diagnosed rather than given
synthetic measurements. Nonfinite handling is source/fixture coverage, not a
claim that this real specimen contains every malformed-input case. Workbench
also rejects duplicate normalized row IDs and nonfinite normalized/cache values.

## Bounds, caches and responsiveness

Provider input work is bounded separately from response/cache size: **64 MiB
aggregate input, 512 sources, 256 producers, 64 corners and 256 logs**, with a
32 MiB per-source cap. Metadata validation participates in the input admission
budget. Directory enumeration, parser lines/records, relationship headers and
diagnostics also have bounds; record/output limits stop further parsing and
limits are reported as errors or explicit truncation/diagnostics, never a claim
of complete coverage. Index queries retain no excerpts for every row; only the
requested detail row retains its bounded excerpt from the observed bytes.

Indexes are bounded to **4096 rows / 2 MiB**, including normalized Workbench size
validation. Detail text is bounded to **64 KiB**. Truncation and unavailable/error
states are explicit; details are fetched on demand, not embedded en masse in the
run summary. Workbench retains at most **8 L1 indexes and 8 detail entries**;
versioned L2 retains **8 indexes**, with an aggregate file bound of
`8 × 2 MiB + 64 KiB`, content digests and project/provider identity checks.

An explicit Inspect can fetch on a cold/missing/invalid cache. Warm Inspect reuses
L1/L2; repaint, polling, context changes and local browsing do not extract reports.
After daemon restart, L2 indexes reopen as **CACHED UNVERIFIED**, preserving the
complete original rows, identities and diagnostics. Reopening/filtering all four
domains after restart caused no provider calls. Explicit refresh is required to
claim current validation. Failed refresh leaves prior evidence visibly unverified.

Projection/search/sort and wrapped detail lines are memoized locally and rebased
onto equivalent polled records. This avoids repeatedly scanning large source
strings and rewrapping long metadata during input/repaint. Selected row detail
precedes lengthy diagnostic metadata; source mode makes that metadata reachable.
Generation/scope tickets prevent late responses from restoring an obsolete view.

Historical failed runs are retained, including `workbench-fs1-investigation-8losxxol`
(detail reachability), `-fhzavzf6` (reverse-scroll assertion), `-fh2f6p61` (row
detail hidden behind metadata), and `-1kobgply` (binary action absent in the
exercised client). An earlier `-op537w4d` run also hit cold-cache opening behavior.
These are failed harness assertions, not passing acceptance evidence. Subsequent
responsiveness/detail-order/cold-open fixes and PTY synchronization changes are
represented in the accepted implementation. The latest `-hd0uuqio` run passed:
it acknowledges
filter editing/deletions, anchors row counts, waits for the actual Enter-dispatched
detail completion and observes rendered reverse-scroll changes.

## Exact binary handoff and actual KLayout read

`terminal/artifact_binary_export.ml` and the artifact byte-read contract export
known physical extensions (`.gds`, `.png`, `.def`, `.odb`) on explicit `b`, enabled
by an absolute `--artifact-binary-viewer` executable. The viewer runs on the
**terminal-client host**, with only a private local exported path as its argument,
without shell interpretation. A daemon/provider path is not assumed local there.
Byte pages use at most 64 KiB raw bytes (hex transport doubles that size), with
identity/offset/size/EOF checks, a 16 MiB export bound, and a 120-second deadline.
The complete SHA-256 must match before publishing or launching.

The accepted `tt_um_controlled_fifo.gds` reference has **4,751,922 bytes** and hash
`3e92e491336136af9a4cf4450451c87064b1b6d1247bd8c0dfd60fa82f1b4943`.
The actual PTY `b` action invoked the recording viewer exactly once with
`E/client-tmp/hardcaml_binary_.tmp.1zwCzG/artifact.gds`. Full exported bytes equal
the retained source, not just a prefix or decoded text. The export and
`metadata.sexp` are mode 0600 in a mode-0700 directory; metadata retains the exact
original reference and verified hash. Artifact reading/export was provider-free.

The recording launcher is a fixture, but the subsequent layout read is real:
KLayout 0.30.4 ran `-b -r E/read-exported-gds.py`, exit 0 in about 1.35 seconds,
with empty retained stdout/stderr. The script calls `pya.Layout().read` on the
actual exported file. It records `dbu = 0.001`, top cell
`tt_um_controlled_fifo`, and nonempty bbox `(0,0;1289280,710640)`.
This establishes **byte-exact external handoff and headless KLayout loading**.
It establishes neither interactive GUI rendering nor an embedded layout viewer,
and adds no physical-flow/signoff result. The retained PNG catalog is empty;
generic PNG eligibility does not establish a real PNG rendering demonstration.

## Requirements disposition and later F06 scope

“Supported-unavailable” means the surface preserves absent/conflicting evidence
honestly for this specimen. It does not quietly remove the desired requirement.

| Original requirement / desired capability | Disposition in this adoption | Remaining scope |
| --- | --- | --- |
| Synthesis resources/diagnostics, elaborated hierarchy and RTL/artifacts | Delivered by prior slices; retained alongside these explorers | Explicit cross-domain mapping still required for reliable links |
| Timing setup/hold, corners/modes/groups, near/failing paths and paginated detail | Delivered for retained max/min reports, with literal filtering, axes, sorting and raw pathpoints | New report formats/providers and richer hierarchy expansion are later extensions |
| Constraints, warnings and source context | Delivered references, numbered report spans, unit evidence and diagnostics | Supported-unavailable where retained coverage evidence is absent; no inferred coverage pass |
| Declared/generated clocks and relationships, measured skew/insertion | Declared-clock context, supplied multi-clock/header relationship fields, measured transition-specific latency/network skew and separate check skew delivered | Unreported generated-clock relationships or missing coverage remain unknown; parsing fields does not establish a complete relationship graph; new providers/coverage are later F06 scope |
| Die/core, utilization, cell/macro areas and placement quality | Delivered provider-attributed native geometry/metrics/analysis | Unreported density/quality semantics are supported-unavailable, not Workbench-defined metrics |
| Routing/congestion/antenna/DRC evidence | Delivered retained per-layer congestion, metrics, logs and producer-specific diagnostics | Missing RepairAntennas native output remains supported-unavailable |
| Independent checks, finalization, acceptance and cancellation | Delivered by lifecycle/acceptance slices, with original outcomes preserved | Investigation success does not promote unknown checks to pass |
| Original reports and external physical artifacts | Delivered bounded text browsing and exact binary terminal-host handoff; real GDS KLayout read verified | Interactive GUI rendering is unverified; real PNG rendering coverage absent |
| File/range source jumps and OCaml/netlist correspondence | Report locations and input references delivered; reliable original source mapping unavailable | Explicit typed source mapping/navigation is later F06 work, never guessed from similar names |
| Embedded graphical/layout/editor surfaces | Later extension, not delivered by external handoff | Embedded layouts remain an explicit requirement for a separately adopted scope |
| Shared evidence with independent local explorers and bounded on-demand detail | Delivered L1/L2 reuse, freshness, tile-local controls and exact detail fences | New selection coordination/providers need their own evidence |

Missing coverage and new generated-clock providers remain unknown or later F06
extensions rather than implementation requirements invented to block this retained
FS1 investigation. Parent review can adopt this functional scope with final
verification passed while retaining those original broader requirements.
Embedded graphics and reliable source mapping remain later work; unsupported
semantics from new providers are not delivered by this acceptance.

## Reusable bounded investigation

`scripts/test-fs1-investigation.py` reuses the lifecycle/metrics/FS0 harness with
existing binaries and exact retained inputs. It supports one domain or all four,
`--skip-binary`, a 60–600-second total budget, 1–90-second per-query cap, and a
20-CPU affinity cap. Its generated read-only wrapper allowlists exact execution,
allocation, stage/domain and known row/digest queries, records every call, and
enforces remaining time. The private project denies project execution and guards
generic jobs. It requests no EDA, build, installation or new finalization flow.
The separate headless KLayout process is only a bounded reader of exported bytes.

The script defaults intentionally pin the private provider generation above.
`commands.json` records the binaries/options actually exercised; inventories
verify retained source/results/config/provider inputs were unchanged. This makes
the investigation reusable by the parent without treating its private test
configuration as the user's deployed configuration. The generated relay deadline
is tied to that test process's time budget; its retained state is evidence, not
a persistent production demo to reopen after the deadline.
