# PT.6 A — frozen provider/backend handoff

## Final reader freeze `PT6-A-contract-r3` — C R1/R2 corrections, 2026-10-28

**A is frozen for C's final capture/acceptance.** This supersedes the WB implementation
fingerprints in r2 below. Public provider JSON, capability, protocol record fields and
cache schema are unchanged from r2. No B terminal, C capture/script, user state or
application provider selection was changed.

### R1: preserve and validate resource process exit status

`Asic_process.run_with_status` exposes the same bounded/cancellable process execution
as `run`, returning `Asic_process.Output.t = {stdout:string; exit_code:int}`. Only
resource queries opt into accepted exit 1. Ordinary `run` callers retain their string
result, default nonzero-exit rejection, timeout/output budgets and cleanup behavior.

New backend validation seam:

```ocaml
Asic_resources_service.parse_process_result
  : Asic_process.Output.t -> Yojson.Safe.t
```

Production index **and detail/catalog/bytes** callbacks preserve the status, pass the
output through this check, then perform the existing strict envelope/source/digest/
lineage validation. The actual native CLI uses the same verdict rule for all queries:

| Process exit | Envelope verdict | Admission |
| --- | --- | --- |
| 0 | pass or not_evaluated | readable, subject to ordinary strict validation |
| 1 | fail | readable failed evidence, subject to ordinary strict validation |
| 1 | pass or not_evaluated | reject exit/verdict disagreement |
| 0 | fail | reject exit/verdict disagreement |
| other / signal / malformed verdict | any | reject |

Inconsistent results never replace a previously admitted index or page. A genuine
exit-1/fail resource index remains inspectable with no transport error. JSON-only
`parse_index` remains a pure schema/association decoder: callers performing their own
process reads must preserve status and use `parse_process_result` first. No selection
or reconciliation logic was duplicated in Workbench.

### R2: clear only the active diagnostic after committed cache repair

A successful explicit load clears the resource cache's active corruption diagnostic
only **after** its atomic replacement completes. Failed provider reads, rejected
envelopes and failed atomic saves retain the diagnostic. A repaired live service and
a new reader reopening its repaired disk cache both report no active cache error.
This does not clear unrelated registry/cache diagnostics elsewhere in the service.

### Final focused verification

All commands used the required repository locks and explicit `-j6`:

* WB `backend/test/resources`: **128 checks passed**, including end-to-end
  `Asic_service` exit1/pass and exit0/fail rejection; recovery with genuine exit0/pass
  and exit1/fail; accepted status retention; all four query kinds' exit/verdict
  combinations; corruption/read/parse/save-failure recovery; and the prior r2 typed
  availability/classification, cache, provenance and actual-provider checks.
* ASIC `test/resource_inspection`: **77 checks passed** with both retained actual
  SRAM and synthesis sources. Native subprocess checks explicitly verified exit1/fail
  for index/detail/catalog/bytes, exit0/not_evaluated for empty-bundle index/catalog/
  bytes, and exit0/pass for actual retained SRAM index/detail/catalog/bytes. Provider
  production source was not changed for these checks.
* WB `@backend/runtest`, `@backend/lint`, `@protocol/test/runtest` passed, including
  ordinary process failure/cancellation/cleanup, existing inspection/simulation and
  unified fresh-prefix fixtures. These do not replace C's final native acceptance.

Exact final WB source SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `backend/asic_process.ml` | `4074b3c87f7b1f18d6c55b868759eed7faefc785e1b6d43ac6e75e94f7c99045` |
| `backend/asic_service.ml` | `746b00f47a7decbee363bfe3e9ed87d7eb08ea09264a5fbc2fee6abc06c9d4a0` |
| `backend/asic_resources_service.ml` | `382dd101adc3cebafdb27775c3e76f3a9795a46db8fd15170b57cc60623cf169` |
| `backend/asic_resources_service.mli` | `eb40c48309863887c9ae98228edcc96697b13df0b023422e4f612dd26eda60f5` |
| `protocol/asic_resources.ml` (unchanged r2) | `8a81631c16da47d0f86e454d69d24eef04913e66460c325a1a11c5decf092d7b` |

The tested native companion remains
`d0d6db3efded30c063a6e6cb14a6f583bbe2230c1891dee032bb1621bf104c72`, dispatcher remains
`18ff0e7ffa39d08d603f792cb268f156e586e9a2e82ab2c1c113916eac3cadbd`, and ASIC production
reader source remains `df255c0c2ebc93233e9f9dd0f48984e0a780771d4c2be45a0a4ccc0995435008`.
These are observed development artifacts, not compiled-source authentication stamps.
C's final build/capture should bind the r2 provider contract to this r3 WB ingestion.

## Revised joint contract — 2026-10-28, implement against these fields NOW

This revision supersedes the inventory/count and stage-only measurement qualification
in the initial handoff below. B owns all terminal changes; C updates scripts/capture
after A reports the final tested freeze. No terminal files are owned/edited by A.

WB `Asic_resources.Inventory_status.t = Available | Unavailable | Unknown`.
`Asic_resources.Index.t` adds:

```ocaml
inventory_status : Inventory_status.t  (* absent old sexp defaults Unknown *)
inventory_reason : string option      (* absent old sexp defaults None *)
```

JSON inspection index adds `inventory_status` = `available|unavailable|unknown` and
`inventory_reason` = string|null. Available-empty is a verified zero-resource
inventory. Unavailable requires a nonempty reason and zero rows; it is never a zero
resource assertion. Unknown is incomplete/legacy knowledge, not available. Available
requires null reason. Old JSON lacking both fields reads as Unknown/None; old cached
indexes restore Unknown and Cached_unverified. Missing/unsupported sources still use
the separate Source freshness/error and operation outcomes.

WB `Asic_resources.Measurement.Classification.t = Observed | Derived | Estimate | Unknown`.
Each `Measurement.t` adds `classification : Classification.t` (old sexp defaults
Unknown). JSON scalar adds `classification` = `observed|derived|estimate|unknown`;
absent older JSON reads Unknown. Unrecognized enum strings or malformed fields reject.
`Measurement.compatible` now also requires equal classification, in addition to exact
name/unit/stage/definition/scope. New helper:

```ocaml
val Measurement.is_measured : Measurement.t -> bool
(* true only for Observed or Derived; independent of stage and value availability *)
```

For measured deltas B must require compatible metadata/classification, is_measured on
both values, present finite values and finite subtraction. Check missing/nonfinite
values explicitly, not after an estimate-stage guard. No stage-only inference remains.
Observed means producer/source-reported quantities; Derived means ASIC-computed counts,
footprints, arithmetic or ratios with recorded source proof; Estimate means library/
combined synthesis area estimates. Classification is provider-owned and explicit at
projection construction, never inferred in WB from names, stages or description text.
Ratios are Derived. Unknown never receives a measured delta. Original full provider
measurement definitions/scope/provenance remain intact.

Default-valued fields are omitted from sexp output, preserving the historical derived
cache content digest on decoding/re-encoding. New nondefault fields participate in
cache content hashes and complete normalized-index identity. Underlying evidence
source_digest still does NOT identify the provider projection; comparison validation
must also match provider_identity and full captured normalized index contents. The
public bridge remains pre-release inspection schema 1 / resource_inspection1; raw
resources-inspect resource-evidence schemas 1/2 remain unchanged.

### A final freeze: `PT6-A-contract-r2` — 2026-10-28

**Provider/protocol/strict decoder/cache are implemented and frozen for B/C.** C must
update synthetic fields and recapture its private provider from this revision; the
earlier capture lacks the new proof classifications and must not be called available
or measured through defaults. No application provider pointer was changed.

Provider normalization explicitly distinguishes absent historical bundle inventory
from an available empty bundle; malformed present inventory still rejects. Historical
named executions without recoverable inventory emit unavailable + reason. Coarse and
finalized evidence with a verified inventory retain available status even when their
resource verdict fails. Inventory availability is independent of measured realization.

Provider measurement classifications are attached from the ASIC producer contract at
projection construction: native final metrics observed; parsed counts, exact component
geometry/sums, gross rectangles and all ratios derived; synthesis library/sequential/
combined area estimates estimate; unestablished sequential ownership/count or unknown
quantities unknown. Missing values keep their reasons independently of classification.
WB never guesses classification from units, stage or free-form definitions.

The strict decoder rejects malformed/unrecognized enum strings, incomplete availability
field pairs, available-with-reason and unavailable-without-reason/with asserted rows or
resource verdict. Older JSON without fields reads unknown; an older live index lacking
inventory status is cached-unverified. Default-valued sexp fields are omitted so actual
old-style cache content hashes continue to verify. Restart never upgrades old empty
indexes to available-zero. Duplicate cache indexes for one source reject.

Evidence digest semantics are intentionally preserved. An explicit refresh with the
same source digest but a different provider projection replaces the normalized index,
binds the new provider identity, and clears detail LRU/catalog/byte publications. Full
index equality includes availability and measurement classifications. B's capture
validation must compare full index and provider identity in addition to evidence digest.

Focused final checks passed with the required locks and explicit `-j6`:

* ASIC `test/resource_inspection`: **57 checks**, including retained augmented SRAM,
  the separate retained synthesis specimen, 76-reference paging, native CLI-1 failed
  evidence, available empty versus unavailable historical bundles/executions, malformed
  inventory and observed/derived/estimate/unknown classifications.
* WB `backend/test/resources`: **86 checks**, including strict enum/availability
  negatives, missing-field old JSON and digest-valid old caches (including empty),
  classification-aware compatibility/is_measured, same-digest changed projections,
  page/LRU invalidation, malformed/duplicate caches and actual native-provider projection.
* WB `@protocol/test/runtest`, `@backend/lint`, `@protocol/lint` passed.
* Forced raw API compatibility aliases passed: **27** PT.5 CLI cases, **19** independent
  review regressions and **56** PT.5b physical/schema/replay observations. These remain
  separate suites, not one additive count. Terminal/C acceptance belongs to B/C.

Exact tested native binary SHA-256 (development build, not a compiled-source stamp):

| Artifact | SHA-256 |
| --- | --- |
| ASIC `_build/default/bin/experimental_resource_inspect.exe` | `d0d6db3efded30c063a6e6cb14a6f583bbe2230c1891dee032bb1621bf104c72` |
| ASIC `_build/default/bin/flow_cli.exe` | `18ff0e7ffa39d08d603f792cb268f156e586e9a2e82ab2c1c113916eac3cadbd` |
| ASIC `execution/results/resource_inspection_service.ml` | `df255c0c2ebc93233e9f9dd0f48984e0a780771d4c2be45a0a4ccc0995435008` |
| WB `protocol/asic_resources.ml` | `8a81631c16da47d0f86e454d69d24eef04913e66460c325a1a11c5decf092d7b` |
| WB `backend/asic_resources_service.ml` | `07eb2c3ed811c16b6e054fecf08762d27b681a24ad932d71fb3e841a80a0dfb0` |

No B terminal files, C scripts/captures, user state, provider selection or raw
resource-evidence schema were edited by A. No EDA, user-daemon or Git operation was
performed in this correction. Subsequent semantic source changes require a new freeze
and C capture; later operating documentation does not imply a source-authentication stamp.


Published 2026-10-28 before dependent UI/acceptance implementation. The plan is
`resource_inspector_plan.md`. Signatures below are the integration contract; this
initial publication does not claim implementation/tests completed.

## WB wire contract (available now in protocol/asic_resources.ml)

`Asic.Operation.Resources of Asic_resources.Operation.t` schedules read-only work.
`Asic.Snapshot.resources : Asic_resources.Snapshot.t option` is additive/default None;
new backend returns Some (possibly empty). Existing `Asic.Get` returns cached facts
only. Pending keys are `Asic_resources.Operation.key operation`. Load keys normalize
refresh=false/true to the same target key (refresh upgrades an in-flight read).

Operations:

* `Load {target; refresh}` explicitly adopts/imports and loads a source. Targets:
  `Workflow_bundle workflow_id`, `Run run_ref`, `Finalization {run;attempt}`,
  `Coarse_run absolute_root`, `Bundle absolute_root`. Coarse/Bundle are durable explicit
  resource imports, **not Register** and never allocate an observation or physical run.
* `Detail {source_id;expected_digest;resource_id;section;offset;limit}`
* `Artifacts {source_id;expected_digest;offset;limit}`
* `Read_artifact {source_id;expected_digest;artifact_id;offset;limit}`

The Snapshot has sources/indexes/details/artifacts/bytes lists. Exact record types
are in `protocol/asic_resources.ml`. Index rows include contract, requirement,
policy, implementation, reason, role, instances, separate synthesis/final statuses,
measurements and section counts. Measurements carry name/value/unit_/stage/definition/
scope/reason. `Measurement.compatible` requires all semantic fields exactly equal;
only two present finite values support a numeric delta. Never compare different
definitions/scopes by guessing equivalence.

Sources carry target, actual provider kind/path, provider identity, freshness/error.
Indexes carry source_id/digest, concise rows/scalars, verdict, diagnostics, artifact
count and full provenance JSON string (inspectable, not normal overview text).
Source freshness is independent of index verdict. Restart is Cached_unverified;
refresh failure retains prior index with Refresh_failed, never fresh success.

Detail sections (stable IDs): `inventory`, `synthesis`, `final`, `geometry`, `timing`,
`electrical`, `provenance`. Items are `{id;title;fields:(string*string) list}`. Nested
values are provider-rendered JSON strings; WB does not parse tool/legacy evidence.
Items include source references and report spans where supplied. Offset/next_offset/
total are item counts. Request limit 1..64. Pages <=64KiB; a too-large single item
fails explicitly. Resource ID is always exact row.id, never an instance-name guess.

Artifact catalog entries `{id;label;sha256;format}` use opaque IDs, with paginated
offset/next_offset/total (limit 1..64). Byte requests use those IDs only, limit
1..16384 bytes. Hex transport; offset/next_offset/total count original bytes. No
arbitrary path read operation exists. Every detail/catalog/bytes response echoes
digest and source association. Clients discard late responses after target/context/
binding/generation changes and must not silently retarget pinned compare sources.

Run-follow uses existing context/pin selection, passing Target.Run. Pre-run selection
passes explicit Workflow_bundle ID from `snapshot.workflows`; use that workflow's
prepared bundle, not latest preparation. The backend resolves all target paths and
checks exact lineage. No automatic load in render/Get; an explicit view-open Load
may cold-read; warm Load(false) is cache-only. No resource operation launches EDA,
preparation, finalization or source project code.

## ASIC public CLI (new command, legacy resources-inspect unchanged)

```
hardcaml-asic-flow resource-inspect TARGET --kind bundle|coarse_run|execution|finalization --json
hardcaml-asic-flow resource-inspect TARGET --kind KIND --query detail --resource-id ID --section SECTION --expected-digest SHA --offset 0 --limit 16 --json
hardcaml-asic-flow resource-inspect TARGET --kind KIND --query artifacts --expected-digest SHA --offset 0 --limit 32 --json
hardcaml-asic-flow resource-inspect TARGET --kind KIND --query bytes --artifact-id OPAQUE --expected-digest SHA --offset 0 --limit 4096 --json
```

New capability `resource_inspection1:true`; this is not implied by CLI4,
inspection1 or resource_evidence2. Public library
`Resource_inspection_service.run ~kind ~target ?query ?resource_id ?section
?expected_digest ?artifact_id ?offset ?limit ()` returns `(Evidence_json.t,string) result`.

Envelope common fields: contract=`hardcaml-asic.resource-inspection`, schema_version=1,
kind, target (canonical path), query, source_digest, provenance. Index fields:
rows, measurements, artifact_count, diagnostics, truncated, verdict. JSON row
measurements use `unit` (WB projects to unit_). Row fields match WB Row otherwise.
Detail fields: resource_id, section, offset, next_offset, total, items. Catalog:
offset,next_offset,total,entries. Bytes: artifact_id,sha256,offset,next_offset,total,
bytes_hex. JSON Item/Artifact fields match WB types. A fresh digest covers complete
evidence and actual verified sources, not only displayed/truncated rows.

Exit 0 = readable evidence without failed required resource verdict; exit 1 =
readable failed resource evidence (JSON MUST be consumed); exit 2 = query/invalid
source failure. Existing raw resources-inspect exits/output remain unchanged.

Bundle verifies manifest and every advertised member byte before inventory. Coarse
uses existing Resource_evidence engine. Named execution reuses execution/checkpoint
validation and bound methodology inventory; unsupported realization stays unavailable.
Finalization uses exact operation/results/context and source replay. No guessed
parent directories, newest-run selection or synthetic coarse run records.

## Budgets and caching

Index <=2MiB/4096 rows; detail/catalog <=64KiB; bytes <=16KiB decoded; bounded
provider process output and 30s timeout. Provider inputs retain Resource_evidence
bounds. WB retains <=32 source descriptors, <=8 indexes (2MiB each), <=64/4MiB LRU
detail pages and <=8 published detail/catalog/byte pages. Durable descriptors and
indexes live in WB state, not provider roots. Details need not survive restart.
Cache keys include target, project/environment/provider configuration, actual
dispatcher AND resource-inspection companion bytes, not dispatcher hash alone.
All page requests source-revalidate and fence expected digest on cache misses;
cached pages are invalidated with any index/source/provider identity change.

## Acceptance integration

Use private synthetic provider for lifecycle/races. Real source:
`hardcaml_asic_example/acceptance/resource-measurements/accepted-live-01/run`.
Original physical-p4 remains separate and timing unavailable. Preserve true original
run/build IDs and coarse origin; no Asic.Register for either import. C may capture
new provider privately after A signals focused completion; no app provider changes.

B owns all terminal and workspace_config builtins/default fixtures. A owns other
protocol/backend defaults. No implementation depends on real EDA or live daemon.

## A implementation / focused verification — ready for B/C integration

Provider and backend source are implemented. C can capture this provider privately;
there is no application-provider change. B can consume the frozen records above.
Additional public typed library entry:

```ocaml
Resource_inspection_service.inspect
  (Bundle path | Coarse_run path | Execution path | Finalization path)
  ?query ?resource_id ?section ?expected_digest ?artifact_id ?offset ?limit ()
```

Backend helper signatures are in `backend/asic_resources_service.mli`. All resource
work travels through existing `Asic_service`, scheduling and query throttles. The
resource operation process explicitly accepts CLI exit 1; generic commands retain
their existing nonzero-exit failure behavior. Resource stdout/record budgets are
enforced during draining, not only after building the response string.

### Projection details important to UI/acceptance

* Summary contract text is provider-normalized kind plus canonical contract S-expression.
  Requirement/role are lowercase; selection reasons distinguish `explicit_flops`,
  `exact_mapping (technology)` and `flop_fallback (technology)`. Original structured/
  legacy inventory remains available in inventory detail. No consumer selector exists.
* `geometry` pages also expose floorplan gross rectangles, component measurements and
  full numerator/denominator ratio objects. Index scalar names include
  `gross_core_area`, `gross_die_area`, `nonspacer_component_area`, native quantities,
  and scoped ratio measurements. Resource-area observations remain per-stage.
* Unavailable section counts are zero; opening such a section returns its bounded
  reason item. Provenance is split into provider-owned field items. A section's
  summary count is an availability/count hint; page total/next_offset govern paging.
* Timing/electrical items retain explicit coverage fields; electrical items include
  `electrical_compliance=not_assessed`. Index diagnostics include the same qualification
  when sampled links exist, plus optional timing diagnostics. Therefore projection
  diagnostics are not identical to the raw PT.5b parser's zero-diagnostic assertion.
* All 76 advertised references are cataloged, not all 333 captured files. Byte reads
  hash the same open descriptor they page, cap hash input at 128MiB and decoded pages
  at 16KiB. Requesting a new source/unknown ID never grants arbitrary path access.
* Finalization validates operation/results/execution hashes, selected checkpoint
  association, build association, recorded context/origin and resource source replay.
  It preserves execution and finalization IDs separately. It does not execute or
  requalify finalization, and is not producer authentication.
* Old providers are classified Unsupported through capability probing before trying
  the new native companion. A provider generation is bound to canonical dispatcher
  location/content and canonical companion location/content. Cached reopen retains
  its recorded provider identity; explicit refresh adopts a newly validated generation.
* Named execution advancement marks existing run-linked resource sources Stale and
  clears their detail/artifact publications. An explicit refresh is required before
  reading pages from a known stale observation. Warm cached facts can remain visible
  with their source freshness; they never become new producer observations.
* Workflow-bundle refresh also verifies the frozen methodology-plan bytes/digest and
  recorded plan/bundle association. Run/finalization responses must agree with any
  exact retained unified-workflow bundle link; historical unlinked runs cannot borrow
  a newer workflow's preparation.

### Executed checks

With the specified shared locks, switch and explicit `-j6`:

* ASIC `test/resource_inspection`: **39 checks passed** with `PT6_RETAINED_ROOT` set
  to the augmented actual SRAM capture. Includes native CLI-1 JSON, member-byte
  tamper/escape/size/count/page negatives, full 81-entry synthetic catalog paging,
  failed resource evidence, finalization without synthetic run.json and mismatched
  execution/results/checkpoint negatives. Actual checks retain 76 refs, exact instance,
  186 paths/372 points and electrical-compliance qualification.
* WB `backend/test/resources`: **52 checks passed** with `PT6_RESOURCE_PROVIDER`
  naming the compiled public dispatcher and the same retained root. Includes strict
  typed projection, semantic measurement compatibility, corrupt/cache-kind/project
  collisions, stale/unauthorized pages, byte/hash/budget validation, bounded LRU,
  late-response rejection, CLI-1 process handling, real service coalescing/import/
  restart/failure/unsupported capability, companion-only identity change and actual
  native-provider index/area projection.
  Imported evidence roots may not contain the Workbench cache; overlap rejects before
  provider reads or cache publication, preserving retained input trees.
* WB `@backend/runtest`, `@protocol/test/runtest`, `@backend/lint`, `@adapters/lint`,
  `@protocol/lint` passed, including existing simulation, timing inspection and unified
  fresh-prefix tests. Terminal integration/build belongs to B/coordinator.
* Existing ASIC resource reconciliation **27 cases**, independent review **19**,
  physical/schema/replay **56**, stage-report and **43 CLI tests** passed. The combined
  command reached its 120s tool deadline with finalization unfinished; a separate
  300s resume of `@test/ocaml-finalization` completed exit 0 (**26 fixture invocation
  differentials plus 16 tests**). The timed-out command is not claimed as passing.
* Direct original `physical-p4` inspection retained unavailable timing/zero sampled
  paths and its reason detail. No augmented reports were borrowed. An existing real
  FIFO emitted bundle (`213b276e...`) verified member bytes and returned successful
  empty inventory, `not_evaluated` realization and 25 catalog artifacts.

Optional actual-provider test command (from WB):

```sh
PT6_RESOURCE_PROVIDER=/home/wayne/devel/jane/hardcaml_asic/_build/default/bin/flow_cli.exe \
PT6_RETAINED_ROOT=/home/wayne/devel/jane/hardcaml_asic_example/acceptance/resource-measurements/accepted-live-01/run \
flock /tmp/opencode/workbench-pt6-build.lock scripts/with-switch.sh \
  dune runtest backend/test/resources --force -j6
```

Limits: no new named macro realization/execution; historical execution inventory can
be unavailable without bound methodology. No independent PT.4-to-bundle association
is invented. Stock/R0 geometry, sampled timing and not-assessed electrical compliance
retain PT.5b's qualifications. Single detail items exceeding the page budget fail
explicitly. Sources are bounded at 32, indexes at eight; there is no automatic source
eviction/import sweep. New feature requires matching updated client/server; defaulted
fields preserve old stored facts, not arbitrary old-client wire negotiation. Existing
backend regression tests use disposable provenance fixtures; no checkout Git mutation,
EDA, Protemu edit, live daemon action or provider-selection change was performed by A.

## B UI integration — implemented and terminal verification passed

The Resources UI and matching default client/exporter/daemon binaries are built.
Terminal suites, terminal/protocol lint and protocol tests pass. C's actual native
HTTP/PTY and retained-provider acceptance remain separate receipts; the checks below
do not claim that real evidence was visually accepted through the terminal by B.

### Exact palette commands for C

Open `Space c c`, type a label below, then Enter. Import commands open a bounded
path-entry form: enter the **exact absolute directory**, then Enter. Spaces in a
directory are retained; do not quote the value inside the form.

* **Inspect resources (open Resources workspace)** — opens/creates the builtin;
  explicitly loads its exact current target, retaining an existing explicit source.
  If its run binding differs from the originating tile, it explains the mismatch
  rather than changing a pin/context. Explicit execution/source selection remains
  available. A focused custom `resources` tile is used directly, preserving its layout.
* **Resources: Import retained resource evidence** — coarse source, no Register/run.
* **Resources: Import emitted bundle** — verified bundle inventory, no fake run.
* **Resources: Select source LABEL · ID** — exact retained imported descriptor.
* **Resources: Select workflow bundle ID** — disabled with reason without a bundle.
* **Resources: Select execution ID** / **Resources: Select finalization ATTEMPT**.
* **Resources: Follow tile run binding** — leaves explicit source mode and loads the
  exact selected/pinned run. Run switching itself does not initiate resource reads.
* **Resources: Refresh exact evidence (r)** — source revalidation only.
* **Resources: Inspect inventory / synthesis / final / geometry / timing / electrical /
  provenance** — provider-owned detail pages, eight items per page.
* **Resources: Authorized sources (a)** — sixteen catalog entries per page.
* **Resources: Capture comparison A**, **Resources: Capture comparison B**,
  **Resources: Compare captured A / B (c)**, **Resources: Swap comparison A / B**.
* Existing **Plan ASIC FLOW / PROFILE (enter endpoint)** and **Preparation inputs:
  FLOW / PROFILE** controls remain available; resource inspection invents no knobs.

Within the `resources` tile: **j/k** (or arrows) select resource/catalog rows; **Enter**
opens resource detail or authorized source text; **Esc** returns; **/** filters and
**Ctrl-U** clears; **r** refreshes; **a** sources; **d** full provenance;
**g/t/e** geometry/timing/electrical; **n/p** next/previous provider page;
**[/]** scroll eight wrapped lines; **j/k** scroll one line outside table/catalog;
**c** comparison. Byte pages are 4096 original bytes. Text display is sanitized;
the provider echoes source/digest/artifact/hash/byte span and transport remains hex.

Fresh stock sessions include Resources after Timing and a one-row Overview entry.
Existing saved sessions are not reset: use **Inspect resources** to instantiate it,
or **Add resource-summary tile** / explicit additive Overview Apply for the entry.
Comparison captures source+index+digest at the explicit action, never Main/latest;
unsupported stages/estimates have no measured delta. All source catalog entries are
reachable with n/p. Warm rendering/filtering/Get do not submit resource operations.

### Implemented boundaries and controls

`terminal/resources_view.ml` owns the pure table/detail/source/provenance/comparison
state and projections. `main.ml` owns explicit read effects and navigation;
`workspace_host.ml` owns captured commands/input/lifetimes; `host_view.ml` retains
frame, clipping and typed status styling. `plain_rpc.ml` waits on A's canonical
resource keys. Stock definitions and the Resources builtin registration use the
existing workspace configuration schema. Terminal fixtures carry `resources=None`.

* The table shows stable resource ID, selected implementation, actual elaboration
  role and separate synthesis/final status. The selected row's contract, requirement,
  policy, selection reason and exact instances remain inspectable. Filtering hides
  rows without silently changing the retained cursor; opening a filtered match is
  explicit. `/` from detail returns to the table without provider work.
* Detail sections preserve provider-owned geometry/area/ratio objects, sampled timing,
  absent values, analysis/model conditions and `electrical_compliance=not_assessed`.
  Full source context also exposes scoped index measurements. No tool report or legacy
  S-expression is parsed in the UI.
* Source freshness, exact execution/workflow status, resource verdict and realized
  stage availability are separate. Coarse imports remain retained coarse evidence;
  their original lifecycle is inspectable in provenance, not a fabricated named run.
  Behavioral/simulation elaboration is explicitly distinct from physical realization.
* Resource views are excluded from generic summary-reader demand: opening a workspace,
  filtering and cache-only polling do not indirectly request a stage report. Existing
  active-run observation remains the independent normal execution lifecycle.
* Source/index/detail/catalog/bytes are selected by exact typed target, source ID,
  digest, resource/section/artifact ID and page offset. Digests replace page state;
  run selection revisions fence A→B→A; close, retarget and reconnect invalidate read
  receipts. Explicit imports survive Main changes. Navigation additionally captures
  client/project/session/window and superseding local intent while creating a workspace.
* A/B captures retain exact source/index bytes and digests. Changed/evicted/current
  source observations are called out without retargeting the capture. Revalidation
  requires the captured provider identity and entire normalized index, not only the
  underlying evidence digest. Numeric deltas require finite inputs/results, equal
  name/unit/stage/definition/scope/classification and provider-owned Observed/Derived
  classification. Derived deltas carry an explicit source-qualified label. Estimates
  and Unknown never receive measured deltas, regardless of stage; unavailable values
  display their actual reason before classification handling. No stage-only inference
  remains. Request/policy/selection/reason/role/stage differences stay visible.
* Source pages retain opaque ID/hash/span, sanitize display controls and preserve line
  boundaries. The catalog cursor remains visible at narrow sizes; all 76 references
  are navigable. Byte-page boundaries may split a UTF-8 character; this is labeled,
  and display sanitization does not alter the protocol's original byte/hash identity.

### Executed B checks

Final command (exit 0), serialized with the WB PT6 lock and explicit six-job budget:

```sh
flock /tmp/opencode/workbench-pt6-build.lock scripts/with-switch.sh \
  dune build -j6 @terminal/runtest @terminal/lint @protocol/lint \
  @protocol/test/runtest terminal/main.exe \
  terminal/workspaces/export_presets.exe daemon/main.exe
```

Fifteen `terminal/resources_view_test.ml` cases cover exact explicit/follow scope,
stable filtering, digest/generation/close invalidation, 76-entry catalog pagination
and last-row visibility, authorized byte IDs/spans and sanitized multiline text,
failed verdict versus source freshness, compatible/incompatible/missing/nonfinite/
overflow/estimate comparisons, fixed A/B captures, bounded widths, typed keyboard/path
dispatch, and run A→B→A versus independent import lifetimes. Existing terminal tests
also pass: source-aware evidence receipts, workspace geometry/navigation, persistence,
reconnect hydration, scheduler responsiveness, presentation and simulation/timing views.
Updated stock tests verify five fresh starters while retaining legacy saved layouts.

Changed OCaml files were formatted with the installed `ocamlformat`; the final
explicit changed-file check passed. No repository-wide formatting success is asserted.
No EDA, provider-pointer/configuration change, live
daemon/session action or Git operation was performed by B.

### B independent-review fixes — complete, source frozen 2026-10-28

Consumed the repros at `/tmp/opencode/pt6-independent-resource-review/` and the revised
typed A contract at the top of this handoff. All six findings are fixed:

1. **Persisted Custom resources compatibility.** Version-1 custom-key reservations
   remain the original four names, independently of the expanding builtin catalog.
   Explicit `Custom` reference plus absent template preset remains custom; explicit
   `Builtin resources` plus matching ancestry selects the new builtin. Validation,
   resolved config decoding and catalog filtering no longer reinterpret old custom
   definitions by current catalog membership. No key rename, definition rewrite,
   layout reset or schema-field insertion is needed. The serialized legacy snapshot
   roundtrips byte-for-byte, retains pins/zoom/geometry/frozen definition, and supports
   explicit creation of the new builtin alongside it. Mixed old custom-plus-builtin
   exports retain the custom definition rather than dropping it.
2. **Reused-key retry fences.** Resource reads now have local generation, admission
   request floor and receipt floor. Before a matching receipt, operation polls cannot
   complete/fail the new intention. A successful receipt clears prior local error and
   requires a Get issued after that receipt; older in-flight polls cannot consume a
   prior task's failure. Successful current completion clears error. New index facts
   during an active Load preserve its admission fence; closing/retargeting/reconnect
   still invalidate old receipts. `main.ml` supplies actual ASIC issuance revisions.
3. **Comparison validation.** Full normalized index equality, provider identity and
   exact target/kind/path are required before current freshness validates a capture.
   Same digest under another provider or changed normalized projection is explicitly
   retained-only/not-revalidated, without changing the A/B capture.
4. **Inventory availability.** Compact/table/context use typed `inventory_status` and
   `inventory_reason`. Only Available-empty asserts verified zero. Unavailable and
   legacy Unknown remain explicit, including actual reasons; no diagnostic/provenance
   string is parsed to recover availability.
5. **Truncation.** Compact entry starts with `Resources TRUNCATED`; table/context and
   captured comparison disclose incomplete projection. Source validation remains a
   separate fact and never conceals the truncation flag.
6. **Measurement availability/classification.** Missing/nonfinite values and reasons
   are handled before classification. Typed Estimate/Unknown have no measured delta,
   including at final_physical. Matching Derived values may compare, explicitly
   labeled `derived (source-qualified)`; incompatible classes and overflow do not.

Final verification (exit 0), after the revised A fields landed:

```sh
flock /tmp/opencode/workbench-pt6-build.lock scripts/with-switch.sh \
  dune build -j6 @terminal/runtest @terminal/lint @protocol/test/runtest \
  @protocol/lint terminal/main.exe terminal/workspaces/export_presets.exe daemon/main.exe
```

Changed-file formatting check passed. The regression suite adds old/late retry polls
and receipts, actual new-attempt failure, index replacement during pending Load,
provider-only and projection-only same-digest changes, typed unknown/unavailable/empty,
legacy codec defaults, truncation on all surfaces, final-stage estimates, unavailable
synthesis estimates with real reasons, source-qualified derived deltas and mismatched
classes. Workspace tests add exact saved-custom upgrade plus new builtin coexistence.
No backend/A files or acceptance scripts were changed for these B fixes. B source is
frozen for coordinator/C integration; native acceptance remains C's own receipt.
