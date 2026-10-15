# F05 — Run selection, references and historical evidence

Status (2026-10-15): **FS0 exact registered runs, follow/pin-run bindings and durable
reopening delivered**. [Acceptance](../fs0_acceptance.md) proves real 673/685 switching,
simultaneous pinned/following UI and restart identity. Requirements below remain
normative: broad store discovery is absent; immutable snapshots/archival retention
are deferred by accepted [D3](../decisions.md), not FS0 blockers.

## Requirements

- A run selector lists identified provider executions, including CLI-created runs
  when discoverable. Pending submissions remain separate until allocation.
- Selecting a run updates all following tiles. Clear old content immediately;
  never display A's measurements below B's label after a delayed response.
- Selection belongs to a project-session run context, shared by linked workspaces.
  Multiple selectors control it while retaining independent local interaction state.
  Main is shared by default; workspace independence and relinking are specified in
  [F10](run_contexts.md), accepted in D1.
- Pinned tiles prominently identify their evidence and do not follow selection.
- Show unsupported, not requested, pending, failed, missing and stale separately.
- Distinguish process completion, measurement goals and verification acceptance.
- Preserve producer stage, corner/mode, units, constraints and source/build identity.
- Separate provider canonical results, rebuildable Workbench indexes/caches, and UI
  preferences. Cache eviction never deletes provider evidence.
- Reopen named results after daemon restart without relaunching tools. Missing saved
  references remain unavailable, not silently replaced with a different run.
- Bound/paginate catalogs, logs and detailed report queries. Invalidate summaries
  on provider revisions, including later collection/postcheck changes.
- [F11](run_summary_cache.md) defines L1 decoded summaries and L2 persistent derived
  summaries, separate from canonical evidence. Warm context switches reuse data;
  cached/unverified and source-unavailable states remain explicit. Run pinning does
  not itself guarantee cache residency, immutable snapshots or archival retention.

## Accepted bindings and remaining snapshot decision

Desired behaviors include following the current run, keeping another run visible,
and saving a capture of a particular stage result. These are not necessarily the
same operation. Following the workspace context and per-tile pinned-run references
are accepted. [D3](../decisions.md#d3--run-versus-snapshot-binding) retains the open
later exact-snapshot and archival/missing-evidence retention questions; follow +
pin-run first and snapshot deferral are accepted FS0 scope.

A pinned run can acquire later results. An exact immutable result reference can
freeze an observation only if the provider guarantees its identity/retention.
Cached bytes alone must not be advertised as authoritative frozen evidence.

## First demo / later

First: two distinguishable runs, linked/independent contexts, one clearly labeled
reference and stale-response tests; historical reopening follows in M3. Broad store
discovery can follow explicit-reference import if upstream listing is unavailable.
Later: dedicated contextual A/B deltas and richer snapshot captures.

Dependencies: F01 identities; F02 revisioned queries; F04/F10 workspace contexts;
D3 for exact snapshot support. Generic test attempts may have no ASIC run binding
(see F09); never substitute the viewed run for missing provenance.
