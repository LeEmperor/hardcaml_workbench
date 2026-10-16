# Synthetic flow demo and regression harness

Implementation plan, 2026-10-16. This is an independent aesthetics/testing feature
group, not a second implementation of FS2 simulation suites.

## First delivery

Provide an isolated, explicitly synthetic project that can be opened in the normal
daemon and terminal client without PDKs or EDA tools. Populate retained FS1 evidence,
exercise a simulated named flow through the existing provider adapter, and publish
explicit checklist stages. A human must be able to launch and inspect it in a terminal.

Keep scenarios coherent across run identities, stage state, summaries, inspection
indexes/details and artifact references. Existing production validation remains in
force. Synthetic evidence must be labeled, and setup must not depend on historical
temporary directories. No sibling repository changes or actual EDA runs are expected.

## Shared implementation contract

Backend and frontend share these additive protocol definitions in `protocol/asic.ml`:

- `Asic.Stage.Status.t`: `Pending | Running | Completed | Failed | Skipped |
  Cancelled | Not_requested | Unsupported | Unknown of string`.
- `Asic.Stage.t`: `{ id : string; name : string; status : Status.t;
  requested : bool; reason : string option; action : Selection.t option }`.
- `Asic.Run.t` gains `stages : Stage.t list [@sexp.default []]`.

The synthetic provider's ordinary `observation inspect` response optionally includes
`stage_plan`, a versioned extension:

```json
{"contract":"hardcaml-asic.stage-plan","schema_version":1,"stages":[
  {"id":"placement","name":"Placement","status":"pending","requested":true,
   "reason":null,"action":{"flow":"synthetic","profile":"success",
     "endpoint":"placement","assignments":[]}}
]}
```

An absent extension produces no stage observations/actions. Unknown status strings
remain explicit unknowns. Bound entries/text and reject invalid/duplicate identities;
never infer stage success from aggregate completion. This extension is implemented
by the synthetic provider first; real providers are not claimed to support it.
Stage state is scoped to the exact observed run/cursor and persists with the run.

An action selection means **start a new run through this endpoint**, not independently
restart a stage in the existing run. Reuse existing `Plan`/`Run`/launch-and-view and
cancellation machinery. Checklist `j/k` selects rows, `r` prepares the advertised
stage action using normal planning; the existing explicit launch command may finish
the operation in this first slice. Clearly label that interaction. Unsupported or
absent actions explain why, without tool calls. Inspection and appearance changes
never launch operations.

## Ownership / parallel work

1. Backend agent: `protocol/asic.ml`, backend stage decoding/observation/persistence,
   focused protocol/backend tests. Preserve existing operation/cache behavior.
2. Provider agent: new `demo/synthetic_flow/` provider/scenario implementation and
   `scripts/synthetic-flow-demo.py` setup/launch support plus integration test script.
   Reuse existing provider JSON/HTTP contracts and valid FS1 inspection envelopes.
3. Terminal agent: checklist presentation and interaction, `terminal/host_view.ml`,
   `terminal/main.ml`, `terminal/workspace_host.ml`, `terminal/overview_tiles.ml`,
   associated terminal fixture updates and focused tests.

Parent owns documentation, integration edits, verification and build scheduling.
Agents do not run Dune or start EDA. Parent runs builds/tests serially with `-j20`;
provider smoke tests must be lightweight and bounded. No staging, commits, pushes,
or GitHub mutations. Use apply_patch for source edits.

## Scenarios and simulation

Start with a completed reference, a failed candidate and a command-driven success
or failure run. Include synthesis counts, aggregate timing/checks, and populated
timing/clocks/physical/routing inspection indexes and detail where feasible.
Use small text artifacts with valid hashes. Full binary layout/hierarchy production
and FS2 suite contracts are optional future extensions, not fabricated evidence.

The provider records calls and publishes state atomically. Interactive execution
uses short bounded delays. A manual/step mode or equivalent explicit advancement
supports deterministic tests without long sleeps. Cancellation publishes a terminal
cancelled outcome. Each launch has its own run identity; commands retain existing
idempotency behavior. Ordinary provider inspection is read-only.

## Verification and acceptance

- Build, formatting, lint and appropriate unit tests with bounded concurrency.
- Setup from a fresh temporary directory with no external tools or retained results.
- Real daemon HTTP registration, run observation, summary and FS1 inspection reads.
- Actual terminal/PTY opens the demo and exercises checklist interaction and a launch.
- Check explicit running/completed/failed states, request records and distinct run IDs.
- No provider mutation from rendering, scrolling, pinning or restyling.
- Document exact tested daemon/client commands and retained evidence directories.

## Delivery record

Delivered the first bounded slice. See [launch instructions and verified scope](synthetic_flow.md).
Three implementation agents owned backend, provider/demo and terminal slices; the
parent integrated and serialized Dune checks at `-j20`. No FS2 suite contracts or
sibling repository changes were introduced.

Formatting, lint, full tests and build passed, with terminal tests rerun after the
viewport refinements. Real provider/HTTP/PTY acceptance passed at
`/tmp/opencode/synthetic-flow-8rmfu7xu/`, including unzoomed Overview/Timing, timing
path sort/filter/detail, checklist planning, exactly one new launch, context adoption,
manual transitions and explicit cancelled-state reconciliation. Automatic timed
playback also passed. The user-facing guide records exact commands and captures.

Remaining scope: real-provider adoption of the optional stage-plan extension,
automatic post-cancel observation reconciliation, FS2 suites, richer hierarchy/binary
artifacts, and further compact-view presentation. Checklist `r` prepares a plan;
the existing explicit palette launch completes the action in this slice.
