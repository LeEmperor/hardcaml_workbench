---
id: WB-029
title: Git/Mercurial inspection and explicit operations
category: integrations
feature_sets: [FS4, FS3]
status: partial
kind: enhancement
priority: P3
severity: n/a
requested_size: Feature
size: L
points: 21
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [git, mercurial, read-only, provenance]
depends_on: []
related: []
---

# WB-029 — Read-only VCS integration first

## Request
Original classification: **Feature** (no numeric size was supplied).
Integrate Git and Mercurial, starting with read-only inspection. Any future writes
must be explicit user operations; automatic commits are not part of the request.

## Current baseline
The backend already captures Git commit/dirty observations alongside source-tree hashes.
Dirty-tree commit context is not an exact source identity, and non-Git roots remain valid.
This is a provenance baseline, not a full VCS browser or delivered Mercurial support.
Project setup explicitly treats VCS support as optional.

## Scope
- Add read-only Git/Mercurial status, revision and bounded change-summary inspection.
- Distinguish current working-tree state from source identity recorded for a run.
- Preserve absent tool, non-repository, unborn revision and query-error states.
- Document an explicit-operation extension seam without implementing writes initially.

## Out of scope
Automatic commits/staging, checkout/reset/merge, network fetch/push and replacing a VCS UI.
Optional future write operations require their own selected scope and estimate.

## Acceptance criteria
1. Both supported VCS adapters expose revision and dirty state with clear provenance.
2. A dirty working tree never presents its commit alone as exact run-source identity.
3. Non-VCS projects remain openable and usable without a misleading integration failure.
4. Change views are bounded and distinguish truncation from complete inspection.
5. Viewing/refreshing VCS state performs no repository/index/history mutation.

## Dependencies
Required: existing source identity and project-root model; no additional ticket blocker.
Related: none; archived replay and new-project creation are independent capabilities.

## Estimate rationale
21 points cover two read-only adapters, bounded inspection and source-context presentation.
Exclude all mutative operations, network integration and archived source reconstruction.

## Assumptions and decisions needed
Default: read-only baseline only; VCS commands run on the project/daemon host.
TBD: initial Mercurial versions, nested/worktree handling and exact change-summary limits.
Decide whether write operations warrant a separate future ticket after read-only adoption.

## References
- [Existing Git/source capture](../../../backend/service.ml)
- [Optional VCS ownership](../project_setup.md)
- [Run evidence identity](../runs_and_evidence.md)
