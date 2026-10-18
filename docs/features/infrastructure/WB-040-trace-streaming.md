---
id: WB-040
title: Bounded-memory large-trace streaming
category: infrastructure
feature_sets: [FS2, FS1]
status: proposed
kind: enhancement
priority: P2
severity: n/a
requested_size: Unspecified
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [traces, streaming, artifacts]
depends_on: []
related: [WB-028, WB-042]
---

# WB-040 — Bounded-memory large-trace streaming

## Request
Stream large trace artifacts to verified private files with bounded memory,
instead of retaining whole traces in memory or silently lifting existing caps.

## Current baseline
FS2 exports byte-exact traces under declared paging/artifact limits, including a
64 MiB artifact cap. FS2-F02 preserves larger-trace streaming as additional scope.

## Scope
- Write pages incrementally to a private temporary file while hashing bytes.
- Define transport, total-size and storage limits explicitly.
- Publish only after complete byte-count/digest verification and atomic finalization.
- Preserve shared ASIC external handoff behavior where the path is reused.

## Out of scope
- Embedded waveform rendering or unlimited artifact size/retention.
- Launching a viewer against incomplete or unverified output.

## Acceptance criteria
- A declared large trace exports with measured bounded peak memory.
- Final bytes/digest match the registered artifact exactly.
- Missing/changed pages, oversize output and digest mismatch reject publication.
- Cancellation and timeout clean up private partial output.
- Viewer launch occurs only after complete verified publication.
- Existing bounded simulation and ASIC handoff paths retain their identity guarantees.

## Dependencies
No additional prerequisite tickets; a bounded streaming slice can declare its own limits.
[WB-042](WB-042-resource-budgets.md) can unify reservations and retention later.
[WB-028](../verification/WB-028-waveform-viewer.md) is a separate consumer-facing viewer,
not required to demonstrate verified export.

## Estimate rationale
13 points, M, medium confidence: existing paging/provenance seams are known, while
incremental hashing, cleanup and publication cross storage/transport boundaries.
Estimate is incremental and excludes embedded rendering and broader budget policy.

## Assumptions and decisions needed
Select new maximum sizes and temporary-file policy before implementation. Streaming
reduces memory pressure but does not remove disk or transport limits.

## References
- [FS2-F02 streaming](../../backlog/fs2_followups.md#fs2-f02--large-trace-streaming).
- [Current artifact limits](../../../protocol/simulation.ml).
- [Private/atomic file helpers](../../../backend/simulation_files.ml).
