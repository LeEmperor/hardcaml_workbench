# Identifier compression — WB-073

Identifier compression now has persistent **global, workspace and focused-tile**
controls. It applies to opaque identities rather than human/provider labels.

## Controls and precedence

Focus the relevant tile and open **Space c c**. Each scope offers Compress, Show
full identifiers, and Reset compression (inherit):

- **Strings (global): …** — default for this project's client presentation across
  its workspaces, matching the existing global appearance preference scope.
- **Strings (workspace): …** — override for the active workspace.
- **Strings (focused tile): …** — override for the captured focused tile.

Effective precedence, highest first:

1. Explicit tile runtime override.
2. Configured tile `string_compression`, if the workspace definition supplies it.
3. Explicit workspace runtime override.
4. Global project/client presentation default.
5. Built-in default: compression on.

Global/workspace controls and notices identify the focused tile's effective value
and source, so an authored tile override does not silently appear to ignore them.
Reset removes only the chosen compression override; it does not reset decimal
precision, hints, frames, scroll, filters, selection or pins. Global reset restores
the built-in default. A tile reset can expose its configured value before inheriting
workspace/global policy.

## Formatting and collisions

- Long **opaque ASCII IDs** normally display first four and last four characters,
  such as `a023…4e4a`.
- IDs of at most 12 characters and non-ASCII IDs are left unchanged by semantic
  compression. Human/provider labels are not semantically abbreviated.
- Lists resolve distinct IDs together. If normal abbreviated tokens collide, they
  extend prefix/suffix deterministically, falling back to complete IDs if necessary.
  Unchanged tokens participate too, including a literal Unicode ellipsis in an ID.
- Width-constrained selectors reserve stable list-local `#n` markers rather than
  clipping away distinguishing characters. Tokens are stable across scrolling within
  the loaded population. Loading a different history population can change expansion
  or ordinal assignment. A viewport too narrow even for a marker is still a physical
  visibility limit; full identities remain available in detail/full-string views.
- Equal raw IDs intentionally share a token. Display tokens are never RPC selectors,
  source keys, cache identities or exported evidence.

Compression operates on a tile's loaded identifier population before viewport
slicing where practical. It does not shorten arbitrary technical signal names or
report prose. Existing source-path compression keeps recognizable report filenames;
full-string mode reveals exact source metadata.

## Covered surfaces

- Testing attempt lists and simulation-detail attempt, job, discovery, parent and
  artifact identities, with shared collision resolution for displayed detail fields.
- Testing discovery/catalog and log metadata, legacy simulation and execution lists.
- Session and run-selector identities.
- Waveforms Session and quick-view attempt/digest headers.
- Timing provenance's opaque identifiers; technical endpoint and field values remain
  technical content, not blindly interpreted as source paths.

The old Testing, Overview and waveform ID-shortening helpers now delegate to the
shared `Presentation.identifier/identifiers` implementation. Effective policy flows
from `Workspace_host.policy`; changing display settings allocates no domain jobs
and does not change exact selected attempts/artifacts/runs.

## Persistence

Presentation preferences now write **schema 6**, reading schemas **1–5**.

- Global compression is a sparse optional project/environment preference and survives
  workspace-session replacement, like global appearance.
- Workspace overrides carry session/workspace identity; rename preserves them,
  removal/replacement discards them, and one-shot restoration prevents stale revival.
- Tile overrides retain session/workspace/tile/kind guards. Moving/retyping/removing
  tiles or replacing a session prevents stale tile overrides from attaching.
- Old records inherit compression on. Existing decimal settings and schema-5
  explicit-only Timing loading preferences remain intact during migration.
- Validation rejects duplicate or excessive workspace entries, missing scoped session
  identity, malformed values and invalid decimal bounds.

## Acceptance and deployment

WB-073 is **delivered at the implementation/automated-verification level**, awaiting
owner acceptance. WB-069 and WB-009 were separately explicitly verified/closed by
the owner; their acceptance does not automatically close WB-073.

Passed serially with `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1` and Dune `-j 1`:

- Full Workbench build, lint and test suite.
- All 27 global/workspace/tile true/false/inherit combinations in fresh processes;
  configured-tile precedence, independent resets and identity guards.
- Shared-formatter collisions, unchanged Unicode/short tokens, raw identity preservation,
  and actual width-fitted selectors at 16, 24, 40 and 100 columns.
- Native HTTP/PTY compression acceptance, including Testing at 32 columns, scoped
  palette effects and restart, attempt/job/discovery collisions, exact HTTP IDs,
  Unicode provider labels, quick/independent waveform views, unchanged artifact bytes
  and zero allocated provider/domain jobs.
- Separate default-on Timing preload regression.
- Configured formatting on changed OCaml files and `git diff --check`.

Receipts:

- `/tmp/opencode/identifier-compression-n537648w/verified.json` and adjacent screenshots.
- `/tmp/opencode/wb073-timing-preload/` for the independent background-index regression.

Some older Testing/FIFO/waveform acceptance oracles now explicitly request full-string
mode when asserting raw metadata; their entire standalone suites were not repeated.
The focused native suite, standard full Dune tests and preload regression above are
the verified coverage. Unrelated global formatting baseline remains separate.

Retained demo binaries were refreshed with receipt
`hardcaml_asic_example/.dev/workbench-real-demo/receipts/refresh-binaries-cd087c850b0240f7b4e72d1dcf3767fa/`.
Live user processes were not stopped. Restart the client to use the updated controls
and rendering; the receipt records whether other retained binary bytes changed.
No physical EDA, repository staging, commits or pushes were performed.

The [implementation/triage plan](timing_triage_identifier_completion_plan.md) records
scope, ownership and the separate WB-009 resolution.

## Overview title/detail follow-up

The reported blank Placement/Routing panes were traced to two independent conditions:
saved header-off preferences suppressed titles, while Enter/detail mode used an
incorrect generic finalization fallback. Compression did not change header/title
preferences in the actual-state replay. The reader now preserves typed stage evidence;
the [regression record](overview_compression_regression_plan.md) gives targeted header
recovery controls, current refresh receipt and passing native verification. No global
appearance reset or live preference rewrite was used.
