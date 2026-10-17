# Restore real checklist r -> plan -> explicit launch

Activated2026-10-17. Owner refreshed real stage status successfully but `r` still
had no action and Launch was missing. Live snapshot after restart has flows=[],
preview=None, known `standard/balanced/synthesis` run selection and normalized
stage rows with action=None. This is an integration/affordance gap, not user error.

## Verified public capability

The current real project's `flow list --json` and `flow describe --flow standard
--json` schema1 advertise:

- backend_recipe `librelane.classic.v1`, input `fresh`;
- stage_selection `complete-prefix-through-declared-endpoint`;
- endpoints synthesis/floorplan/placement/cts/routing/signoff;
- profiles balanced/synth_delay; catalog default pair standard/balanced.

Use this explicit declaration; never invent endpoint names or resume behavior from
historical success. The same stage can be not_requested in the inspected run and
still be a supported endpoint for a NEW run.

## Required behavior

- Focus checklist, j/k select stage, r prepares a new run through that stage.
- Provider-explicit Stage.action stays supported. Otherwise resolve from normalized
  current fresh-prefix capabilities, with captured launch inputs: explicitly
  remembered selection first; else captured observed run selection where available;
  else the actual declared catalog default pair. Preserve assignments. A stale
  explicit choice must error, not silently fall back to another flow/profile.
- If current capabilities are missing after restart, r performs bounded discovery
  as part of that explicit command, then resolves/plans the captured stage. No tools
  on rendering/passive polling. Registry/instance/project/intent fences prevent
  stale discovery results or changed context from silently retargeting the command.
- Existing normal Plan/Run/idempotency/launch ledger remain authoritative; no
  second scheduler or provider install. Invalid/missing/unsupported mapping is
  actionable in the UI and cannot cause a producer launch.
- Launch/Launch-and-view commands remain visible while unavailable, with useful
  missing/pending/failed/stale preview reasons. Never use a fabricated Preview for
  a disabled command; preserve exact Preview capture for enabled commands.
- Planned-run and checklist detail show the resolved flow/profile/endpoint and
  readiness. Pressing r never executes EDA; only explicit Launch does.

## Ownership and resource rules

Preserve existing user work and index/history; no Git staging/commits/pushes/resets.
Three agents maximum, each2 jobs serial in `/tmp/opencode/checklist-{contracts,ui,acceptance}`.
Parent full checks serial at2, no competing builds. No new real EDA, no live user
daemon mutations or result edits. Public real discovery/planning are allowed for
bounded verification; actual producer launches only use synthetic fixtures.

### A — capability normalization

Shared API names for parallel implementation: add
`Asic.Flow.fresh_stage_endpoints : string list [@sexp.default []]` and
`Asic.Flow_default.t = { flow : string; profile : string }`, exposed as
`Asic.Snapshot.catalog_default : Flow_default.t option [@sexp.default None]`.
An empty endpoint list means no validated fresh stage mapping, not all stages.
Catalog default is the provider's actual pair, never the first discovered item.

Own protocol/asic.ml and backend/asic_public.ml, backend/asic_service.ml plus focused
fixtures/tests. Publish typed fresh-prefix endpoint capabilities and exact catalog
default pair, with legacy optional/defaulted wire fields. Do not force frontend
to parse provider JSON. Validate contract/version, recipe/input/stage semantics,
declared endpoints/profiles/default pair and bounded text/counts. Preserve existing
synthetic explicit Stage.action and opaque unsupported-provider behavior.
Publish exact API in this plan before B integrates. Avoid frontend/shared edits
except minimal fixture record literal updates coordinated with B.

### B — real input/command workflow

Own terminal/workspace_host.ml, main.ml, host_view.ml and a pure stage action resolver
module if useful (terminal/dune for it). Use A's typed capability model. Implement
explicit r -> discovery-if-needed -> captured resolution -> normal Plan; report
progress/unsupported failure without accidentally enabling the old preview. Keep
launch commands visible disabled rather than absent, and preserve exact availability
revalidation on Enter/dispatch. Keep pins/historical run selection and current plan
producer associations separate; stage navigation remains local and never executes.

### C — acceptance and release handoff

Own new `scripts/test-checklist-launch-workflow.py`, existing harness adaptations,
and eventual persistent binary refresh after parent verification. Native test cold
daemon with persisted real run but no catalog; keyboard j/k/r on routing obtains
real standard/balanced/routing preview, no real Run. Validate declared defaults for
historical imports, missing/stale choice failure, preserved assignments, target
changes/delayed responses. Synthetic fixture completes r -> visible Launch -> exact
allocation with one producer; before preparation Launch visible disabled and why.
Preserve prior stage/lifecycle/FS2/interrupt regressions. User live sessions untouched.

## Status

**Implemented and verified.** Final normal format/lint/full tests/build passed
serially at2. Final normal-binary native acceptance passed61 assertions at
`/tmp/opencode/checklist-workflow-7dbc9ab8d388/`, including actual real routing
preparation from a cold catalog and synthetic-only explicit producer launch.
Persistent demo copies are refreshed. See [restored workflow and evidence](checklist_launch_workflow.md).
Handoffs below are chronological; no real EDA, live user-state mutation or Git
staging/commits/pushes were performed.

### A API published (2026-10-17)

Protocol fields are now present: `Asic.Flow.fresh_stage_endpoints : string list`
(`[@sexp.default []]`), `Asic.Flow_default.t = { flow : string; profile : string }`,
and `Asic.Snapshot.catalog_default : Flow_default.t option`
(`[@sexp.default None]`). B owns frontend record literal updates (including
`Fs0_fixture`); initialize unsupported/synthetic catalogs to empty endpoints and
`None`. Service/normalization implementation and focused verification underway.

### A completed — backend/protocol handoff (2026-10-17)

- Exact API above is implemented, including legacy sexp defaults. Protocol codec
  tests round-trip populated capabilities/default and decode absent legacy fields.
- `Asic_public.flow_catalog : Yojson.Safe.t -> Asic.Flow.t list *
  Asic.Flow_default.t option` normalizes one flow-list response atomically;
  existing `Asic_public.flows` remains a projection. Fresh endpoints require both
  public capabilities and methodology to declare `librelane.classic.v1`/`fresh`,
  with public complete-prefix stage selection and `continuation=false`. Endpoints
  come only from that methodology's declared list; all six production endpoints
  are supported, with no inference from run observations or omitted endpoints.
- Supported catalogs require an explicit valid default pair. Legacy catalogs
  without that declaration return `None`; supplied null/partial/unknown pairs
  reject. Entry default profiles must exist. Duplicate flow/profile/endpoint IDs,
  unsupported envelope versions, malformed IDs and unknown recognized endpoints
  reject. Bounds: 1 MiB catalog, 128 flows, 64 profiles per flow, six recognized
  endpoints per flow, 256-byte normalized identifiers/capability strings.
- `Discover` clears both old fields immediately, uses the immutable captured
  project configuration, performs the bounded query, checks cancellation and
  parses everything before publishing both fields without yielding. Failed or
  pending refresh has no ready mapping. Discovery remains explicit; catalog is
  not persisted/restored on restart. Other providers retain empty fresh mappings;
  existing explicit `Stage.action`, stage normalization, summary and launch ledger
  behavior pass existing focused regressions.
- Added production-shaped flow-list fixture with standard/balanced, synth_delay
  and all six declared endpoints, pure unsupported recipe/input/continuation,
  defaults/schema/duplicates/budget/subset/legacy tests, plus service failure,
  pending invalidation, recovery and restart/explicit-rediscovery checks.
- Passed serial, at `-j2`, build dir `/tmp/opencode/checklist-contracts`:
  `dune build @backend/test/asic/runtest
  @backend/test/stage_normalization/runtest @protocol/test/runtest
  @backend/test/asic/lint @backend/lint @protocol/lint @protocol/test/lint`.
  Changed OCaml files formatted with installed ocamlformat. No live daemon or EDA
  invoked. B owns remaining frontend record literals; protocol test literals are
   updated here. Coordinator should run integrated frontend/daemon acceptance.

### B completed — frontend handoff (2026-10-17)

- Added `terminal/stage_action.ml/.mli`, registered in `terminal/dune`. Resolver
  takes typed captured stage, remembered selection, observed selection and snapshot;
  provider-explicit actions win. Otherwise validates the exact flow/profile and
  fresh endpoint, replaces only endpoint, preserves assignments, and uses only
  `catalog_default` when both captured selection sources are absent. Historical
  stage status (including `not_requested`) does not restrict new-run endpoints.
- Checklist `r` now captures stage/run, remembered/observed inputs, registry
  session/revision/workspace, transport/project/daemon identity and preparation
  generation before dispatch. Missing fresh capabilities trigger explicit
  `Discover`, then at most 50 metadata `Get` polls spaced 100ms apart. Checks run
  before further requests and before Plan; changed context or newer preparation /
  ordinary Plan cancels the captured continuation. Rendering does no discovery.
  Successful resolution uses existing `Planned_run.begin_plan` / receipt fencing
  and preference saving. This preparation path never sends Run.
- Preparation/failure state disables the previous preview in launch dispatch and
  catalog, and replaces the old ready-plan panel headline. A normal new Plan
  supersedes preparation. Checklist detail and matching-preview hints share the
  same resolver and show flow/profile/endpoint/assignments.
- `Workspace_host.launch_commands` always supplies both Launch catalog entries,
  including no-preview states. Missing entries use `Unavailable_launch`, never a
  fabricated Preview. Ready entries capture exact Preview; existing dispatch
  guards still check authoritative exact availability. Disabled messages retain
  captured availability and explicitly tell already-open palettes to reopen.
- Updated frontend fixture literals for A's new fields in `fs0_fixture`,
  `asic_intents`, `overview_tiles`, `workspace_host`, `plain_rpc`, `artifact_view`,
  and `launch_preferences`. Backend/protocol files were not edited by B.
- Added resolver cases for exact assignments/precedence, actual non-first catalog
  default, imported absent selection, stale explicit choices, missing capabilities,
  unsupported endpoint and provider-explicit action. Added searchable disabled
  Launch, exact ready Preview capture, pending/failed/stale launch availability and
  preparation-over-old-ready-panel checks. Existing terminal regressions pass.
- Verification passed serially with `opam exec --switch=5.2.0+ox --`, build dir
  `/tmp/opencode/checklist-ui`, `-j 2`: `dune build terminal/main.exe`,
  `dune runtest terminal`, and `dune build @terminal/lint`. Changed OCaml files
  formatted using that switch's `ocamlformat -i`. No EDA or live user state used.
- Integration blockers: none found by frontend build/unit/lint checks. C/parent
  still owns cold-daemon keyboard acceptance, delayed-discovery/context/new-Plan
  races across actual HTTP, synthetic exact allocation, and binary refresh.
