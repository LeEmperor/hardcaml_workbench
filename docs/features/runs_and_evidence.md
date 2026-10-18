# F05 — Run selection, references and historical evidence

**Ticket entry points:** [WB-006 timestamps](evidence/WB-006-evidence-timestamps.md),
[WB-009 Timing-coherency triage](evidence/WB-009-timing-coherency.md),
[WB-012 comparison](evidence/WB-012-run-comparison.md),
[WB-037 archived replay](verification/WB-037-archived-replay.md) and
[WB-038 acceptance bridge](verification/WB-038-acceptance-bridge.md).
Lifecycle, freshness, report availability and verdicts remain independent facts.
Estimates and concrete open decisions live in the [individual tickets](README.md).

Status (2026-10-16): **FS0 exact registered runs/follow/pin/reopening and FS1
adopted-evidence investigation delivered**. [FS0 acceptance](../fs0_acceptance.md)
proves real 673/685 switching and restart identity. [FS1 lifecycle](../fs1_lifecycle_and_artifacts.md)
adds exact finalization attempts, persistent keys, independent operation/acceptance
outcomes and selected terminal-result artifacts. [FS1 investigation](../fs1_investigation.md)
adds source-hashed, stage/producer-attributed timing/clock/physical/routing indexes,
exact row/digest detail and binary handoff. Requirements below remain normative:
broad store discovery is absent; immutable snapshots/archival retention remain
deferred by accepted [D3](../decisions.md). Later F06 source mapping/embedded graphics
and FS2 structured simulation are not delivered by this completion.

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

Delivered: two distinguishable runs, linked/independent contexts, clearly labeled
references, stale-response rejection and restart reopening, plus FS1 exact retained
execution/finalization investigation. Restarted finalizations are unowned and never
replay producers; inspection L2 reopens as cached/unverified until explicit refresh.
Source hashes bind observed bytes; supplementary reports explicitly remain
not-checkpoint-inventoried. Neither cached bytes nor external handoff establish
immutable retention, source mapping or signoff. Broad store discovery remains later
than the implemented explicit-reference registration/import path.
Later: dedicated contextual A/B deltas and richer snapshot captures.

Dependencies: F01 identities; F02 revisioned queries; F04/F10 workspace contexts;
D3 for exact snapshot support. Generic test attempts may have no ASIC run binding
(see F09); never substitute the viewed run for missing provenance.
