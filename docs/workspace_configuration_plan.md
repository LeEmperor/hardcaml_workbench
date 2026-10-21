# User-composable windows and workspaces

Status: **implemented and verified** (2026-10-21).
The owner authorized implementation and clarified that shipped layouts must themselves
use the same specification as user layouts, serving as complete editable examples.
Delivery is tracked in M5 in [the construction plan](construction_phase_plan.md).
The [authoring guide](workspace_configuration.md) documents the actual interface.

Selected scope: responsive trees and sparse presentation defaults, explicit client-read
config paths, atomic initialization and additive reapply, Main-linked/follow defaults,
persisted resolved definitions and stable authoring keys. Reset-to-config and automatic
directory discovery remain follow-ons. The design discussion below records the
original proposals; the implementation record and user guide describe shipped behavior.

## Goal and ticket ownership

Users can author configuration describing windows, their workspaces, and the
tiles in each workspace. The shipped workspaces are defaults, not the only
possible compositions. Built-ins must remain independently available as a recovery
path even when users supply their own definitions.

- [WB-015](features/workspaces/WB-015-layout-file-usability.md): editable workspace
  definitions, diagnostics, round-tripping and explicit edit/apply semantics.
- [WB-016](features/workspaces/WB-016-window-configuration.md): named window
  composition, atomic application and session-restoration precedence.
- Related: [WB-045](features/workspaces/WB-045-template-picker.md) for browsing,
  [WB-049](features/project/WB-049-config-migration.md) for eventual config location
  unification, and [WB-048](features/presentation/WB-048-presentation-persistence.md)
  for existing local presentation persistence.
- Live window attachment belongs to
  [WB-047](features/workspaces/WB-047-window-attachment.md). File composition can be
  validated without OS-window orchestration or multiple attached surfaces.

## Discovery baseline (before implementation)

| Boundary | Existing behavior | Relevant source |
| --- | --- | --- |
| Portable workspace | Version-1 S-expression: name, optional preset, ordered tile kinds, visibility and requested geometry; bounded validation and atomic import/clone | `protocol/workspace_template.ml`, `workspace_cli/main.ml` |
| Compiled composition | Membership, responsive layout trees and presentation defaults; Overview, Timing, Testing and Waveforms catalog | `terminal/workspaces/{common,definition,presets,layout}.ml` |
| Live registry | Project session → windows → workspaces → tiles; stable identities, Main/independent contexts and tile follow/pin bindings | `protocol/workspace.ml` |
| Persistence | Revision-checked mutation, per-project serialization, validated atomic save; restart restores live state | `backend/workspace_service.ml` |
| Rendering | Known presets use compiled trees; unknown presets use generic Fit; constrained layouts fall back to grid/focused tile | `terminal/host_view.ml`, `terminal/workspaces/layout.ml` |
| Local presentation | Separate versioned preferences, including identity-scoped tile overrides | `terminal/presentation_preferences.ml` |
| Recovery | Distinct Apply, Reset arrangement and Restore default layout operations | `docs/default_layout_restore.md`, `protocol/workspace.ml` |

Important qualifications:

- Template export does not export a responsive tree or presentation defaults.
  A preset reference selects compiled policy rather than freezing its definition.
- Requested `x/y` survive storage, but the terminal shelf renderer does not provide
  arbitrary free placement. File documentation must describe this honestly.
- `Presets.starters` lists Overview, Timing and Testing, but the base registry
  creates Overview/Timing and initialize-once Bootstrap targets those two original
  arrangements. Demo/default catalog wording is not a complete startup contract.
- Unknown tile kinds can survive template import; executable tile behavior remains
  compiled into the host. Composition of existing tiles is already a useful goal.
- Existing project manifests reject unknown fields and have no composition field.
  `.workbench/` is a WB-049 candidate, not an established config location.
- The terminal has no attached-window selection state; its workspace switcher
  currently spans the registry. `web/main.ml` is a stub.

Delivered foundations and their evidence:
[FS3 adoption](fs3_adoption.md), [composition plan](frontend_composition_plan.md),
[FS3 integration plan](fs3_integration_plan.md), and
[default restoration plan](default_layout_restore_plan.md).

## Proposed contract

This section records the design used to partition implementation. Final semantics
are in the authoring guide; in particular explicit invalid paths fail before
connection, and startup without a selected file consumes the canonical stock window
composition. The old placeholder Bootstrap is retained for legacy sessions only.

### 1. Three distinct kinds of state

1. **Portable configuration:** reusable workspace definitions and named window
   compositions. Stable authoring keys are separate from display names and live IDs.
2. **Daemon session:** instantiated identities, order/visibility/requested geometry,
   contexts, bindings and saved user edits. This is authoritative after creation.
3. **Client state:** viewport, focus/navigation and personal presentation overrides.
   Configuration defaults do not overwrite saved explicit presentation choices.

Use a versioned S-expression composition envelope that references reusable
workspace definitions. Retain version-1 template support; choose compatible
extension versus a versioned wrapper in task A1. Share codecs/validation rather
than copy terminal-only types into a second independent format.

The envelope needs stable keys for windows and workspace instances, display names,
ordered workspace membership, and built-in/user definition references. Inline user
definitions should allow tile kind, order, visibility and requested size. If richer
layout authoring is included, support the existing tree vocabulary rather than
introducing another layout engine. Give duplicate same-kind tiles distinct authoring
keys before allowing per-instance layout or presentation references.

Initial bindings should use existing Main-linked workspaces and following tiles.
Independent-context defaults can be added only with explicit creation semantics;
portable files must not contain live run pins or selections.

### 2. Built-ins remain recoverable

- Keep built-in definitions immutable and independently addressable. Reserve their
  identities; reject user-definition collisions rather than silently shadowing them.
  Existing unqualified preset IDs need a compatibility mapping if namespacing changes.
- User configurations can select a subset of built-ins and add custom compositions.
  Availability in the catalog does not require instantiating every built-in at startup.
- Expose explicit creation of any built-in workspace even from a wholly custom setup.
- Distinguish restoring a custom definition's defaults from selecting a shipped
  built-in. A custom workspace with no built-in ancestry must not acquire an arbitrary
  built-in through a misleading Restore command.
- Missing/invalid optional configuration must leave built-ins reachable with a clear
  diagnostic. An explicitly requested invalid apply must fail without changing the
  session. Corrupt saved registry state must retain the existing explicit error
  behavior, rather than being silently replaced with default state.

### 3. Initialization and explicit application

Recommended first workflow: **explicit config path; initialize once; explicit apply
after edits**. This avoids committing to WB-049 directory discovery or live reload.

| Situation | Proposed behavior |
| --- | --- |
| Fresh session, valid selected config | Instantiate the complete composition atomically |
| Fresh session, no selected config | Preserve the existing built-in startup path |
| Existing saved session | Restore it; do not replay config over user edits |
| File edited while running | No implicit change; validate and explicitly apply |
| Same composition applied again | Stable keys prevent duplicate windows/workspaces |
| Existing key renamed in file | Match by key, not display name |
| Keys removed from file | Retain live objects until an explicit removal policy exists |
| Invalid reference or failed save | No partial publication or cache update |
| Two clients initializing/applying | One serialized atomic result; explicit conflict handling |

For the first explicit reapply, prefer additive creation of missing keyed objects,
preserving existing live arrangements. Reset-to-config should be a separate explicit
operation with documented effects on membership, visibility, geometry and names.
Do not silently equate it with today's built-in Restore command.

The existing `Get` creates initial arrangements before terminal Bootstrap. Task A2
must resolve this ordering: config initialization needs a fresh-session marker or
equivalent atomic entrypoint so it neither duplicates those placeholders nor treats
an edited existing session as disposable. Do not infer freshness from revision alone.

Resolved custom layout policy must survive restart and file disappearance. Recommended
design: persist a versioned resolved definition and provenance with the instantiated
composition, leaving live edits authoritative. Ordinary reconnect should not depend
on the attaching client's filesystem. Confirm this storage choice before schema work.

## Decisions to settle before implementation

1. **First delivery breadth:** membership/order/visibility/requested sizes only, or
   also responsive trees and sparse per-tile presentation defaults? The latter uses
   the existing engine but expands WB-015/WB-016's estimated schema/integration work.
2. **Application modes:** confirm additive reapply and whether reset-to-config ships
   immediately. Specify handling of changed kinds, moved keys and removed definitions.
3. **Identity/storage:** settle authoring-key namespaces, resolved-definition storage,
   snapshot migration and compatibility for old clients and version-1 templates.
4. **Loading:** confirm explicit path as the initial interface and whether startup
   loading is required in the first slice. Define client-read versus daemon-read
   behavior for remote connections; prefer sending validated data, not remote paths.
5. **Context defaults:** Main-only first, or explicit independent/named shared contexts?
6. **Bounds:** define aggregate windows/workspaces/tiles, tree depth and total bytes;
   existing template limits alone do not bound a multi-window composition.

Implementation uses the selected scope above. The schema is versioned so additional
tile/window capabilities can be introduced deliberately as the product grows.

## Agent-sized implementation work

At most **three general implementation agents** at a time. The parent owns docs,
interface coordination and integrated verification. File ownership transfers must
be explicit where phases share files.

| Item / owner | Deliverable and files | Depends on | Completion gate |
| --- | --- | --- | --- |
| A1 / Agent 1: portable contract | Versioned composition types/codecs/validation near `protocol/workspace_template.ml`; stable keys, bounded references, legacy compatibility; example fixtures | Decisions above | Round-trip, duplicate keys, invalid refs, unsupported versions, aggregate bounds; no registry writes |
| A2 / Agent 2: atomic registry application | Operations/reducer in `protocol/workspace.ml`, persistence integration in `backend/workspace_service.ml`; initialization, stable-key matching, provenance and migration | A1 interface frozen | Multi-window all-or-nothing apply; repeat apply; concurrent clients; saved edits/pins/context preservation; failed-save and restart checks |
| A3 / Agent 3: composition catalog | Built-in + user definition resolver around `terminal/workspaces/`; immutable built-ins, explicit lookup/fallback, custom layout/presentation policy if selected | A1 interface frozen | Built-ins remain addressable, collision rejection, duplicate-tile addressing and bounded layout fallback |
| B1 / Agent 1: CLI authoring workflow | `workspace_cli/main.ml`: offline validation, export/example workflow and explicit apply; readable diagnostics | A1, A2 | Export/edit/validate/apply through native HTTP; failure leaves session intact; legacy commands work |
| B2 / Agent 3: terminal integration | `terminal/main.ml`, `workspace_host.ml`, `host_view.ml`: selected-config startup, resolved catalog consumption, recovery actions and notices | A2, A3 | Fresh startup versus existing restore; file edits do not replay; custom workspace and built-in recovery render correctly |
| B3 / Agent 2: integration acceptance | Focused cases in protocol/backend tests and FS3/default-restore acceptance scripts | A2; final run after B1/B2 | Multi-window persistence, missing config on reconnect, stale revisions, malformed files and fallback; reproducible evidence |
| C / Parent: docs and completion | User guide/examples, ticket evidence and activated construction checklist; targeted integrated verification | All selected scope | Document actual syntax/lifecycle/limits; record exact checks without claiming unimplemented follow-ons |

Scheduling: A1 freezes interfaces first; A2 and A3 can then proceed independently.
B1 and B2 use those agreed interfaces, while B3 adds acceptance coverage. Agent 1
owns new schema modules; Agent 2 owns registry operations; Agent 3 owns renderer and
catalog integration. Avoid concurrent edits to protocol operation definitions or
`terminal/main.ml`. Coordinate any WB-072 source moves separately.

## Verification plan for implementation time

Discovery ran no builds or tests. Later, one coordinator should run targeted checks
serially while agents have stopped builds, using the shared pool of **20 jobs**:

```sh
./scripts/with-switch.sh dune runtest -j20 protocol/test backend/test/workspace terminal/workspaces
./scripts/with-switch.sh dune runtest -j20 terminal
./scripts/with-switch.sh dune build -j20 daemon/main.exe terminal/main.exe workspace_cli/main.exe setup/main.exe
python3 scripts/test-fs3-adoption.py
python3 scripts/test-default-layout-restore.py --daemon _build/default/daemon/main.exe --client _build/default/terminal/main.exe --workspace-cli _build/default/workspace_cli/main.exe --setup _build/default/setup/main.exe
```

Add meaningful coverage for new semantics rather than relying solely on existing
scripts. Include narrow/wide rendering, repeated same-kind tiles, built-in recovery
from a custom-only composition, and exact preservation across restart. Run manifest
or setup tests only if their code changes.

If workers build concurrently, allocate 6/6/6 jobs with two reserved, or 10/10 for
two workers. Nested builds count toward the same cap; current real build/test
adapters may invoke `-j20`, so run those only with the full pool available. Prefer
isolated metadata fixtures for composition acceptance.

No Git add/commit/push or other authorship-changing operations are authorized.
No sibling-repository changes are expected for this feature.

## Delivery record

All A1–A3 and B1–B3 items are implemented, with parent-owned documentation and
integrated verification complete. Three general agents owned the bulk of schema/CLI,
registry/persistence/acceptance, and stock/catalog/terminal work respectively.

- Canonical `terminal/workspaces/stock.sexp` and `custom.sexp` use the shared spec.
  Stock startup uses its declared window composition; OCaml preset modules are
  compatibility projections. Responsive trees and sparse presentation are supported.
- `Initialize_config` atomically replaces only untouched initial placeholders.
  Revision-checked `Apply_config` adds missing authoring keys while preserving edits.
  Snapshots retain definitions and key mappings across restart/file disappearance.
- Native CLI supports `config export`, `config validate`, `config apply`; the
  terminal supports `--workspace-config`. Built-ins remain available from the palette.
- Explicit built-in Restore detaches frozen config policy while retaining identity
  mappings. Regression tests cover same-builtin restore and later additive apply.
- Targeted protocol/backend/workspace/terminal tests, native builds and `@lint` pass.
  All builds ran centrally at `-j20`, with no agent builds or real provider jobs.
- Native configuration: `/tmp/opencode/workspace-config-zbzojw2o/result.json`.
  FS3 adoption: `/tmp/opencode/fs3-adoption-574hfszu/result.json`.
  Default restoration: `/tmp/opencode/default-layout-restore-gekveke6/result.json`.
- Modified OCaml sources are formatted; full `@fmt` remains blocked by existing
  differences in untouched ASIC/waveform sources listed in the authoring guide.

During verification, compilation/type-scope and lint errors were fixed; the existing
template-size diagnostic was preserved. Restore's independent native oracle was
extended to require exact targeted policy detachment, and its clipped palette-reason
assertion was updated to the new wording. Successful evidence above supersedes
earlier failed development runs.

Follow-ons: reset-to-config/reconciliation, automatic file discovery, broader context
defaults, live surface attachment, and future spec capabilities as features grow.
No Git staging/commits/pushes or sibling-repository changes were performed.
