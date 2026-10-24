---
id: WB-009
title: Timing workspace availability/coherency investigation
category: evidence
feature_sets: [FS1]
status: closed
kind: defect
priority: P1
severity: S2
requested_size: Ticket
size: M
points: 8
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [timing, coherency, triage]
depends_on: []
related: [WB-069, WB-071]
---

# WB-009 — Reported missing timing paths

**Owner resolution/closure:** after the retained-evidence investigation below, the
owner selected **“Resolved by recent fixes”**, confirming the old missing-path report
is resolved and WB-009 can be closed as verified. The original exact run remains
unidentified; closure is based on that explicit resolution, not an invented linkage.

## Request
Original size: **Ticket**. The owner reports no timing paths after a run reached
signoff, while signoff was not performed. Investigate that exact observation.
The original report's exact execution remains unidentified. A later concrete report
for the Timing-only `a023` execution was reproduced and fixed as described below;
that does not retrospectively establish the cause of the original observation.

## Current baseline
Retained inspection supports historical Signoff and new Timing-stage analysis.
Generic/contextual navigation now resolves the selected run's published analysis
target rather than hardcoding Signoff. Empty states distinguish unloaded evidence,
provider-reported empty evidence with diagnostic, filtered-out rows and errors.
Normal navigation uses the built-in Timing workspace; exact source/pin fences remain.

## Scope
- Capture the exact run/execution, provider configuration/capability, requested and
  observed stages, selected inspection stage, filters and cache state.
- Inspect retained artifacts/import registration with read-only queries.
- Separate stage reached, stage completed, report produced, report available/imported
  and inspection-stage selected; repair a reproduced coherency/message defect only.

## Out of scope
Automatic EDA, performing signoff to manufacture missing evidence, or assuming a root
cause from the report. Existing FS1 delivery and milestones remain closed.

## Acceptance criteria
1. Triage records exact identities and reproduction steps, or explicitly remains unconfirmed.
2. Completed stages and available/imported timing reports are reported as separate facts.
3. Missing report, failed import, wrong stage and zero filtered rows are distinguishable.
4. A reproduced defect receives a targeted fix and regression against retained/fixture data.
5. Diagnosis does not launch a physical flow or promote “reached signoff” to completion.

## Reproduced later report — a023 Timing-only execution

Attempt `a02325d9895a428aa7b90734314e4e4a` completed the Timing endpoint under recipe
schema 4. It had **1,020 actual timing paths** across three corners plus one index
reference row, and no requested Signoff checkpoint. Its valid Timing analysis was
already in the summary cache, but the generic command requested `stage=signoff`;
the provider correctly returned an empty Signoff index, which was then cached.

The frontend routing correction selects the exact Timing analysis/stage, retaining
the frozen source and separate index digest. A private native client displayed the
actual retained paths without a physical rerun. Current and historical Signoff
palette regressions pass; missing evidence is no longer mislabeled as merely a filter
mismatch. Source replacement remains an explicit error.

Evidence: `/tmp/opencode/timing-followup-backend-evidence/` and
`/tmp/opencode/timing-followup-ui-real/`. Subsequent built-in navigation and hidden
index loading were also verified against a023 in
`/tmp/opencode/c-preload-actual-a023-measured/` (one index read, zero detail reads).
See [diagnosis](../../timing_workspace_loading.md) and
[current behavior/acceptance](../../timing_workspace_usability.md).

**Status boundary:** the a023 defect is fixed and automatically verified. The owner
subsequently confirmed the recent fixes resolve the older outstanding report, so this
ticket is closed/verified. This does not imply universal historical-report availability.

## Final retained-evidence investigation

A bounded read-only trace enumerated 36 execution records and 16 unique registered
run IDs in three persisted configuration namespaces. Two surviving candidates,
`d041691ff79b44a4b5a81e483be5576a` and `86d4cffe215547b49c4fb2acdd7b8365`, each failed
Signoff after approximately 607 seconds. Exact request-linked native reports contain
1,020 STA path blocks, but neither attempt published a completed Signoff checkpoint
or independent analysis observation. Their current public inspections explicitly
report missing publication. Neither was authoritatively linked to the original report.

Completed historical Signoff specimens `344ac175531e46fcbd021a1d4c79c361` and
`a883b090252b4a1faa887475df90086f` still return 1,020 paths plus one reference row;
the later a023 Timing result remains available with the documented digests. The older
`/tmp/opencode/workbench-fs1-physical-kzkr6vl_` evidence directory is absent.

Fifteen sequential public calls succeeded; before/after inventory of 6,024 files
showed zero changes. No new backend/provider defect was established, so no additional
source change, historical backfill or physical rerun was justified. Receipts:
`/tmp/opencode/wb009-readonly-trace/` (`disposition.json`, `candidate-table.json`,
`failed-native-evidence.json`, query bytes and snapshot comparison).

## Dependencies
Required: existing retained evidence, configuration and inspection APIs; no new blocker.
Related: WB-069's Timing execution/analysis source and WB-071's workspace routing;
refresh activity and timestamps aid diagnosis but are not prerequisites.

## Estimate rationale
8 points cover bounded reproduction, evidence tracing and one localized correction.
Exclude new report providers, EDA reruns and speculative architectural replacement.

## Assumptions and decisions needed
Read-only triage was completed. The a023 cause/fix is established; the original
run identity remains unknown, but the owner explicitly confirmed resolution by the
delivered behavior. Historical unpublished raw reports are not automatically imported.

## References
- [Actual a023 diagnosis and cache behavior](../../timing_workspace_loading.md)
- [Timing usability/preloading delivery](../../timing_workspace_usability.md)
- [Accepted timing behavior and deployment history](../../fs1_investigation.md)
- [Inspection service](../../../backend/asic_inspection.ml)
- [Stage/selection presentation](../../../terminal/inspection_view.ml)
