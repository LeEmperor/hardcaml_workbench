---
id: WB-023
title: Additional typed provider evidence
category: evidence
feature_sets: [FS1]
status: partial
kind: enhancement
priority: P2
severity: n/a
requested_size: Feature
size: M
points: 13
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [providers, typed-evidence, adoption]
depends_on: []
related: []
---

# WB-023 — One further evidence adoption

## Request
Original size: **Feature**. Broaden useful provider evidence through one bounded
additional adoption, rather than promising every report format at once.

## Current baseline
FS1 already adopts timing, clocks, physical and routing domains through the public
inspection contract, with bounded detail, source hashes and stage attribution.
Missing retained coverage is supported-unavailable, not a remaining FS1 blocker.
Provider parsing belongs behind the adapter, not in terminal report scrapers.

## Scope
- Select one additional report family or provider capability with an actual specimen.
- Define typed semantics, units, producer/stage attribution and absence diagnostics.
- Extend one provider parser/contract and corresponding Workbench projection.
- Preserve cache identity, detail fencing, limits and original evidence access.

## Out of scope
All-provider/all-report support, manufacturing measurements, graphical viewers,
and the separately scoped power-analysis workflow.

## Acceptance criteria
1. The selected report family and producer/schema version are recorded explicitly.
2. Real retained input yields typed rows traceable to exact source bytes and spans.
3. Unsupported, malformed and missing input remain distinguishable from valid zero values.
4. New rows preserve units, stage/corner semantics and bounded/truncated status.
5. Existing domains and caches remain compatible or migrate with explicit version handling.

## Dependencies
Required: delivered inspection contract and one chosen producer specimen.
No additional ticket prerequisite; choosing and adopting that specimen is included here.
Related: none; power and alternate providers can be independently scoped later.

## Estimate rationale
13 points cover one new family end to end, including producer and consumer integration.
Exclude unrelated reports, new execution lifecycles and costs assigned to other tickets.

## Assumptions and decisions needed
TBD: first evidence family and its authoritative producer.
Default: extend the read-only typed contract without adding automatic tool execution.
Re-estimate if the selected family needs a substantially different data model.

## References
- [Delivered provider boundary](../../fs1_investigation.md)
- [Inspection protocol](../../../protocol/asic_inspection.ml)
- [ASIC adapter](../../../adapters/asic_adapter.ml)
