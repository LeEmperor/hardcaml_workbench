# Execution durations in Overview and Testing

Execution duration answers **how long the work took**. It is separate from evidence
age, which answers when a report was produced or validated.

## Visible fields

- Overview's stage checklist and horizontal stage strip show each stage's time.
- The Runs tile shows attempt-wide time separately from run status.
- All six Overview summary tiles include a time field within their default layout.
- Testing's simulation-attempts pane shows timing in each attempt entry, with the
  same information in attempt details.

Runs and checklist rows show bare durations such as `2m 07s`, right-aligned in a
shared duration column beside left-aligned statuses. They omit redundant Time/Elapsed
prefixes; the lifecycle status identifies active work. Standalone summary/detail views
retain descriptive timing labels. Completed measurements freeze; live estimates use
a recorded start. Zero is a valid measured duration. Unknown timing is explicitly
unknown, not zero. Extremely narrow checklist/run rows may omit timing to preserve
readable status. Live display updates use the existing repaint clock, not new provider
requests.

## Meaning and availability

| Surface | Timed work |
| --- | --- |
| ASIC stage | Provider-reported terminal occurrence duration; live estimates require a real start and active lifecycle |
| ASIC run | Attempt allocation through outcome, using provider elapsed time; never a sum of stages |
| Synthesis, Placement, Routing summaries | The exact matching stage |
| Timing, Checks summaries | Unknown unless an exact timed stage exists; report age is not analysis runtime |
| Finalization summary | The separate selected finalization receipt's start/end interval; ambiguous receipts remain unknown |
| Simulation attempt | Workbench simulation service start through finish, persisted with the attempt; includes service handling, not simulator CPU time alone |

Completed measurements remain frozen. A retained start alone does not authorize a live
estimate. Restart, writer loss or failed observation disables applicable live estimates;
recovering an interrupted attempt does not invent an end timestamp. Invalid, negative,
nonfinite or future-start durations do not produce misleading elapsed values.

Existing ASIC stage projections can obtain retained stage durations on **Refresh**.
An old registry may already have consumed the start/outcome journal events without
retaining their timing: those old run totals/start anchors remain unknown because
this implementation does not replay historical events. Old simulation records without
timing likewise remain unknown; newly executed attempts persist their timing.

## Theme and terminology

The Session context's `linked` keyword uses a semantic `Linked` role mapped to the
theme's success color plus bold. Built-in schemes supply green success colors.
`Host_view.utility_attrs` controls this mapping and `Host_view.Role.palette` supplies
scheme colors. Custom colors currently require OCaml changes; there is no arbitrary
user-theme configuration file. Built-in schemes remain selectable through Appearance.

An **inspector** is a detailed report view opened from a tile, such as timing paths,
clocks or artifact details. **Space c x** closes the focused detail view.

## Compatibility and verification

The optional `X-Workbench-Execution-Timing: 1` HTTP request header independently
negotiates timing fields on ASIC and simulation responses. Without that exact opt-in,
the daemon omits timing fields at serialization so strict old readers remain compatible.
Evidence-metadata negotiation alone does not enable execution timing. Old records and
old-server responses decode with missing timing as unknown.

Full combined build, tests and lint passed with `-j4`. Focused tests cover provider
timing validation, lifecycle/restart retention, transport compatibility, visible default
tile layouts, exact stage/run selection, frozen and live values, and narrow clipping.
Owner feedback on 2026-10-21 accepts Testing behavior and authorizes closing the
non-signoff-dependent work in this set. Simulation-attempt duration presentation is
therefore accepted. Clock/timing report review is blocked by the failed signoff run;
no successful signoff-report validation is implied by that closure.

The later Runs/checklist alignment refinement has automated rendering coverage and
awaits owner appearance review. See the
[duration alignment and lazy Timing cache plan](timing_cache_and_duration_alignment_plan.md)
for shared-column behavior and configurable inspection caching.
