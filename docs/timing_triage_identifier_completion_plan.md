# WB-009 triage completion and WB-073 identifier compression

## Authorization and boundaries

The owner explicitly closed/verified WB-069 and authorized work on the remaining
WB-009 original timing report and WB-073 identifier compression. Preserve the
already delivered Timing stage, built-in workspace, precision and background-index
features. Do not count WB-069 acceptance as acceptance of the other tickets.

All remaining verification is **one job at a time**, explicit Dune `-j 1`, with
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1` where relevant. No repository Git staging,
commits or pushes. Existing isolated test-script Git fixtures remain allowed by
owner policy. Preserve unrelated and preceding uncommitted work. No physical EDA
rerun to reconstruct missing historical evidence.

## WB-009: resolve the evidence boundary

The known a023 Timing-only wrong-stage navigation defect is fixed and verified.
The older report described missing timing after reaching Signoff without Signoff
completion and lacks an exact recorded execution in its ticket.

- Locate surviving allocation/execution references in docs, receipts, persisted run
  registration and example retained results. Correlate only authoritative IDs and
  source records, never infer identity from newest-directory ordering alone.
- Use bounded read-only public report/inspection on identified candidates to separate
  incomplete Signoff publication, retained STA, unavailable source, incorrect stage,
  import failure and empty filters. Record which exact case can actually be reproduced.
- Fix any demonstrated remaining defect with meaningful regression coverage. Do not
  silently scrape/backfill historical run records or claim modern fixtures establish
  the cause of the unidentified original report.
- If no authoritative link to that report survives, document the exhaustive bounded
  search and ask for the missing run reference/owner confirmation. Do not fabricate
  a diagnosis or mark the ticket closed merely because a023 is fixed.

## WB-073: completion contract

### Scope and precedence

Compression is a display choice. Full IDs remain RPC selectors, cache/source keys,
stored evidence and exported report content.

Implement effective precedence:

1. Explicit focused-tile runtime override.
2. Configured tile compression override, when present.
3. Explicit workspace runtime override.
4. Global client/project presentation default.
5. Built-in default (on).

The global control applies to all workspaces in the current project's client
presentation preferences, matching existing global appearance scope. Workspace
overrides are guarded by session/workspace identity; tile guards preserve existing
session/workspace/tile/kind rules. Reset at each level restores inheritance and
must not reset unrelated precision/frame/hint preferences. Explain configured tile
overrides when they prevent a less-specific setting from changing a tile.

Provide discoverable compress/full/inherit palette controls at global, workspace
and focused-tile scopes, sparse persistence with schema migration, and tests of
precedence, zero provider reads, restart and moved/removed/replaced identities.

### Identifier rendering and collisions

- Default opaque ASCII ID format remains first four / last four for long IDs.
- Keep short IDs and any non-ASCII IDs unchanged per the original WB-073 acceptance
  criterion. Keep human/provider labels unchanged; terminal width clipping remains
  separate from semantic identifier compression.
- Resolve collisions within a rendered tile's identifier population by extending
  visible prefix/suffix deterministically, falling back to full IDs where needed.
  Distinct raw IDs must not get identical compressed display tokens. Equal raw IDs
  may share a label. Use the full list population for stable labels across paging
  where practical, rather than changing labels on every scroll.
- Apply the shared formatter/resolver to simulation-detail attempt/job/discovery IDs,
  Testing attempt lists, run selectors and relevant waveform identity displays.
  Consolidate duplicate ID helpers. Preserve Timing's numeric precision and source
  fidelity; full-string mode must reveal full identities.
- For fields of different kinds shown together, field labels identify the namespace;
  include displayed IDs in collision resolution where shortened tokens can otherwise
  be confused. Do not shorten arbitrary report prose or technical signal names.

## Agent-sized packages

### Agent A — WB-009 retained-evidence investigation

- [ ] Trace original report and candidate executions using read-only source/evidence.
- [ ] Reproduce available exact cases and identify any remaining fixable defect.
- [ ] Implement a demonstrated backend/provider fix if needed, or return a precise
  missing-evidence boundary for parent/user clarification. Do not edit parent docs.
- [ ] Return receipts, exact IDs, query results and recommended ticket disposition.

### Agent B — compression scopes and persistence

- [ ] Add global/workspace compression choices and effective precedence to Host policy.
- [ ] Add scoped palette actions/resets without changing unrelated settings.
- [ ] Extend sparse preference schema, guards and migration from prior versions.
- [ ] Test precedence, restart, resets, identity replacement and no provider effects.
- [ ] Hand effective-policy API and commands to Agent C.

### Agent C — shared collision-safe rendering and coverage

Starts after B to avoid overlapping host/rendering/preferences edits.

- [ ] Implement shared identifier formatting/collision resolver with short/Unicode
  preservation and stable deterministic output.
- [ ] Apply it across required Testing/Session/run/Waveform identity surfaces,
  including simulation-detail attempt/job/discovery fields; consolidate old helpers.
- [ ] Verify compress/full scope behavior in native terminal fixtures, including
  deliberate collisions, long labels, mixed Unicode, pins and exact source identity.
- [ ] Run targeted regressions and record final API/receipt handoff.

### Parent — closure, integration and deployment

- [x] Record owner's WB-069 closure and this plan before implementation.
- [ ] Resolve WB-009's disposition from actual evidence or ask for missing identity.
- [ ] Run serial integrated build/lint/tests and review scope-complete acceptance.
- [ ] Update ticket statuses honestly and publish controls/evidence documentation.
- [ ] Refresh retained binaries if needed without stopping live user processes.

## Verification gates

WB-009: identified report versus unresolved identity clearly distinguished; no EDA
rerun; exact-stage availability/error diagnostics regression-tested for any fix.

WB-073: all three scopes work with documented precedence and inheritance; settings
survive restart; simulation detail abbreviates opaque IDs by default; list collisions
expand; short/non-ASCII IDs and human labels remain unchanged; raw IDs and selection
are exact; presentation changes cause zero domain/provider work. Existing Timing
preloading/navigation and Testing/Waveforms remain functional.

## Execution record

Pending investigation/implementation.
