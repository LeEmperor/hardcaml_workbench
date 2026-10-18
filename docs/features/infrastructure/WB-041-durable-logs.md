---
id: WB-041
title: Durable full logs with retention
category: infrastructure
feature_sets: [FS0, FS2]
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
tags: [logs, retention, history]
depends_on: [WB-042]
related: [WB-064, WB-043]
---

# WB-041 — Durable full logs with retention

## Request
Retain complete stdout/stderr for historical failure investigation within explicit
budgets, with honest truncation, eviction and missing-log behavior.

## Current baseline
The supervisor has per-job log paths and stream/offset indexes. Structured normalized
history does not by itself establish durable full generic logs across restart.

## Scope
- Persist indexed stdout/stderr and exact job/attempt association across restart.
- Apply shared per-job and aggregate output/storage policy.
- Expose offsets, truncation and retention/eviction status to readers.
- Keep full-log retention independent from normalized test records and artifacts.

## Out of scope
- Infinite logs, arbitrary external log ingestion or guaranteeing never-evicted history.
- Turning generic process output into inferred structured case results.

## Acceptance criteria
- A retained job's stdout/stderr can be investigated after daemon restart.
- Paging/index offsets remain consistent with retained stream bytes.
- Noisy/failed producers remain within policy and report truncation explicitly.
- Evicted or missing logs are labelled honestly without erasing normalized outcomes.
- Concurrent writes, cancellation and restart cannot publish misleading complete indexes.
- Retention cleanup preserves active-writer safety and exact attempt ownership.

## Dependencies
[WB-042](WB-042-resource-budgets.md) is required for shared output/storage policy.
[WB-064](WB-064-generic-job-detail.md) supplies related investigation UX and
[WB-043](WB-043-slow-storage.md) improves persistence responsiveness; neither is an
additional prerequisite to durable bounded logs.

## Estimate rationale
13 points, M, medium confidence: logging seams exist, but durable indexes and retention
need careful restart integration. Incremental estimate excludes WB-042 policy costs
and broad selected-job UI redesign.

## Assumptions and decisions needed
Confirm retention duration/bytes and whether budget exhaustion truncates, rejects or
terminates output production. “Full” means retained bytes within declared policy,
never an implicit promise to preserve unlimited producer output.

## References
- [FS2-F05 logs and budgets](../../backlog/fs2_followups.md#fs2-f05--durable-logs-and-output-budgets).
- [Supervisor log state](../../../backend/service.ml).
- [F09 generic history limits](../simulation_and_tests.md).
