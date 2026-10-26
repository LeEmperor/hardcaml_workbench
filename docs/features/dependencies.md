# Ticket dependencies and interface handoffs

This is a reading map for the [ticket catalog](README.md), not a committed delivery
schedule. Ticket front matter is authoritative for required IDs. Arrows below mean
**prerequisite → consumer**. `related` links are useful coordination, not blockers.
The current hard-dependency graph has no cycles. Delivered F01–F12 foundations are
described in ticket bodies, not reintroduced as unfinished tickets.

## Required additional ticket interfaces

| Prerequisite | Consumers | What the consumer needs |
| --- | --- | --- |
| [WB-012 run comparison](evidence/WB-012-run-comparison.md) | [WB-031 design sweeper](exploration/WB-031-design-space-sweeper.md), [WB-033 Quick-Harn](exploration/WB-033-quick-harn-playground.md) | Reusable paired identity, quantity-compatibility and missing-result rules. Consumers own their variant/compile/test-result adapters; WB-012's initial UI covers synthesis/timing summaries, not arbitrary result types. |
| [WB-042 resource budgets](infrastructure/WB-042-resource-budgets.md) | [WB-030 test sweeps](verification/WB-030-seed-parameter-sweeps.md), WB-031, WB-033 | Shared admission/reservation and cancellation policy, bounded outputs and aggregate limits including nested jobs; no scheduler per feature |
| WB-042 | [WB-041 durable logs](infrastructure/WB-041-durable-logs.md) | Retention/eviction/truncation policy and shared byte-budget accounting |
| [WB-035 generated-RTL simulation](verification/WB-035-generated-rtl-simulation.md) | [WB-036 gate-level simulation](verification/WB-036-gate-level-simulation.md) | Reusable simulator input selection/staging and captured-build/artifact provenance; gate-specific collateral is owned by WB-036 |
| [WB-027 measurements](infrastructure/WB-027-performance-measurement.md), WB-042 | [WB-044 load acceptance](infrastructure/WB-044-load-acceptance.md) | Repeatable latency/memory/event measurements and declared resource limits for the exercised workload |

The WB-035 → WB-036 ordering is a proposed reuse decision, not a claim that gate-level
simulation intrinsically requires RTL simulation. Revisit it if the chosen backend
cannot share that scaffold. Likewise WB-042's aggregate-execution extension is an
explicit provisional assumption recorded in its ticket. Change the contracts and
dependency fields together if the owner chooses a different division.

## Useful parallel tracks and optional relationships

- **Immediate usability:** WB-001 alignment, WB-003 refresh visibility, WB-019
  hideable controls and WB-024 context wording can proceed independently. Native
  icons and the captured-command model already exist.
- **Timing diagnosis:** WB-009 starts with exact retained evidence and selection;
  it must not wait for a new graphical viewer, timestamps or another real EDA run.
- **Testing investigation:** WB-032 catalog, WB-034 FIFO adoption and WB-063 Testing
  redesign can share real fixtures. WB-028 waveforms, WB-030 sweeps and WB-062
  uncertain-submission recovery are distinct extensions, not prerequisites for all
  test browsing. The accepted FS2 provider/reducer/artifact contract is reusable.
- **Configuration versus interaction:** WB-015 layout-file UX, WB-016 window files,
  WB-045 template picker, WB-046 layout editing and WB-047 attachment must agree on
  stable identities/precedence. Existing templates/registry allow bounded versions
  independently. Mouse support WB-013 is optional for keyboard-first editing.
- **Evidence versus display:** WB-020 graphics, WB-021 source navigation and WB-022
  naming annotations need actual provider mappings for the particular data shown.
  They may extend contracts within their own scope; they do not all depend on the
  general WB-023 evidence-adoption ticket. User annotations never replace producer
  identities or claim a source mapping that does not exist.
- **Reproducibility:** WB-037 archived replay requires retained source/build/tool
  identities, not a Git browser. WB-029 is a useful read-only provenance surface,
  not a hard dependency; non-VCS projects remain valid.
- **Large artifacts:** WB-028 may start on bounded existing VCD artifacts. WB-040
  streaming is needed when its chosen workload exceeds current limits, not before
  any waveform UI is possible.
- **Ches versus native editor:** WB-018 consumes typed shared daemon data; WB-033
  explores a separate comparative editing workflow. Neither should copy terminal
  pixels or introduce another authoritative project/evidence store.

## Estimate accounting

Points in each ticket cover its own incremental work. In particular WB-025 (89),
WB-031 (55) and WB-033 (89) are not three equally sized “Mega” labels: their
bounded first deliveries reuse different existing foundations. WB-020 (55) is a
large graphical delivery despite the owner's original `Large Feature` label.
Confidence is low for all four; choose the first backend/format/editor surface and
complete a spike before relying on the estimate.

WB-031/033 do **not** include the separately listed WB-012/042 estimates. Suggested
internal phases are already included. WB-061 estimates one review iteration;
WB-023 estimates one additional bounded provider evidence slice. They do not budget
all possible future layouts or tool formats. Replacing an epic with child tickets
requires explicit estimate reconciliation, not addition of parent and child totals.

## Decisions that deserve owner review first

1. WB-009: exact run/stage/provider/filter state behind the reported empty Timing pane.
2. WB-004's initial meaning is now selected and implemented: source build plus
   EDA-less selected-flow `flow emit`, with verification labelled as the project
   test-command outcome. Exact-bundle verification/resource-preparation composition
   remain later work; WB-008 still needs the project's OOC-top command semantics.
3. WB-017: browsing files versus editing a project-owned membership list; which
   build systems actually require explicit membership?
4. WB-020/028: first supported data format and native-terminal versus graphical surface.
5. WB-025: property language, formal backend, supported bounded/unbounded modes.
6. WB-031: finite build variants versus adaptive optimization; initial measured metrics.
7. WB-033: the intended Quick-Harn experience, editor ownership and scratch/save model.
8. WB-016/048/049: personal versus shared config scope and precedence across clients.
