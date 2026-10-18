---
id: WB-027
title: Workbench latency/resource/evidence-loading measurements
category: infrastructure
feature_sets: [FS0, FS3]
status: proposed
kind: validation
priority: P1
severity: n/a
requested_size: Feature
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [latency, memory, loading, measurements]
depends_on: []
related: [WB-043, WB-044, WB-005]
---

# WB-027 — Workbench latency/resource/evidence-loading measurements

## Request
Measure Workbench interaction latency, memory use and evidence-loading behavior
so optimization decisions rest on tool measurements rather than impressions.

## Current baseline
Construction records retain scoped responsiveness/cache evidence and defer broader
high-tile-count, latency and memory/disk measurements. These are not a complete baseline.

## Scope
- Define reproducible cold, warm and restart evidence-loading workloads.
- Measure input-to-visible-response, query/cancel latency and loading duration.
- Record daemon/client memory, allocation where practical and retained disk use.
- Include realistic tile counts, evidence sizes and local versus slow-storage conditions.
- Publish workload, environment, measurement method and uncertainty with results.

## Out of scope
- Measuring DUT timing, area or power as though they were Workbench performance.
- Broad optimization rewrites or fresh physical flows solely to collect sample data.

## Acceptance criteria
- A repeatable harness produces attributable latency/memory/loading measurements.
- Cold/warm/restart paths and cache-hit behavior are separately reported.
- Input responsiveness is measured through the actual host/transport where relevant.
- Results state sample counts, distributions and environment rather than one magic number.
- Instrumentation overhead and unsupported measurements are explicit.
- Proposed acceptance thresholds are documented for owner review, not invented delivery claims.

## Dependencies
No additional prerequisite tickets; use current fixtures and retained evidence.
[WB-043](WB-043-slow-storage.md) targets measured I/O bottlenecks and
[WB-044](WB-044-load-acceptance.md) consumes this measurement method.
[WB-005](WB-005-process-monitor.md) provides related live visibility, not DUT metrics.

## Estimate rationale
13 points, M, medium confidence: bounded instrumentation and workload design span
frontend/backend seams. Incremental estimate includes the measurement baseline,
excluding subsequent optimizations and separately ticketed load acceptance.

## Assumptions and decisions needed
Agree representative environments and responsiveness budgets. Reuse retained large
evidence where possible and distinguish synthetic workloads from actual user sessions.

## References
- [Construction coverage/scaling followups](../../construction_phase_plan.md).
- [FS1 measured interaction followup](../../fs1_investigation.md).
- [Cache architecture](../run_summary_cache.md).
