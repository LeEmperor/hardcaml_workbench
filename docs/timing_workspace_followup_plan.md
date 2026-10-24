# Timing workspace membership, empty paths and loading policy

**Status:** membership/navigation fixes implemented, verified and deployed to the
retained client; loading-policy research complete, automatic warm-up proposed for
owner agreement. [Findings and recommendation](timing_workspace_loading.md).

The owner subsequently authorized the recommendation and broader presentation/
navigation improvements. These are delivered in the
[Timing usability/preload increment](timing_workspace_usability.md).

## Owner request — 2026-10-23

1. Remove `simulation-catalog` from the Timing workspace.
2. Diagnose and fix empty `timing · paths` after “Inspect timing paths” on the most
   recent real `a023` run, which was executed through Timing.
3. Explain current Timing loading/cache behavior and agree whether to prepare paths
   in the background after completion or only on explicit demand.

Implementation is authorized for items 1–2. Item 3 is investigation and a concrete
recommendation; do not silently introduce speculative background work as part of a
navigation fix. No physical rerun is needed to inspect retained evidence.

## Agent-sized work packages

### Agent A — terminal/workspace fixes

Own terminal source/tests, preset definitions and relevant native HTTP/PTY scripts.

- [x] Trace Timing stock membership, generated definitions and saved-layout behavior;
  remove simulation catalog from Timing without removing it from Testing.
- [x] Trace generic palette “Inspect timing paths” and Timing workspace selection
  through stage/analysis target, query/filter and source fencing. In particular,
  verify the new Timing stage is not still routed to historical Signoff by default.
- [x] Implement identified frontend fixes and meaningful regressions. Preserve pins,
  exact source identity, legacy six-stage inspection and explicit execution controls.
- [x] Verify in a private daemon/client with the retained real run if possible.

### Agent B — real run evidence/backend diagnosis

Own backend/provider source/tests only if a defect is demonstrated; initially trace
the actual retained run and installed provider read-only.

- [x] Locate the exact latest `a023` attempt under the example results/state and
  identify execution/checkpoints, analysis schema/source, available reports and rows.
- [x] Compare exact `timing` versus legacy `signoff` public inspection, then Workbench
  parsing/hydration/cache state. Record commands, counts and source identities.
- [x] Assess demonstrated provider/backend defects; none found, so no backend/provider
  changes were needed. Do not modify
  raw run evidence, launch EDA, or replace it with a synthetic success specimen.
- [x] Hand exact run/source/inspection facts and any deployment requirements to parent.

### Agent C — loading/cache research

Research only; own no implementation files.

- [x] Trace index/detail loading, daemon L1/L2 caches, client transformed-row state,
  rendering and hidden-workspace scheduling; compare Testing/Waveforms/Overview.
- [x] Identify bounded costs, invalidation rules, concurrency and selected-row
  prefetch behavior. Distinguish loading/transformation from off-screen rendering.
- [x] Recommend a concrete completion-triggered warm-up versus explicit-demand
  policy, preserving run/pin intent and reporting missing/failed/filtered evidence.

### Parent — integration and documentation

- [x] Record scope, ownership and execution policies before implementation.
- [x] Integrate findings, verify the actual failure cause and run appropriate checks.
- [x] Refresh retained demo binaries if needed; preserve user state and live processes.
- [x] Record fixes/evidence and prepare loading-policy choices for owner discussion.

## Policies and acceptance

No Git staging/commits/pushes. Preserve existing work and saved user workspace
customizations. Up to three general agents; A/B each at most six jobs, C read-only;
total job pool at most 20 including subprocesses. Use explicit Dune limits and
separate build directories or serialized builds in a shared checkout. Parent heavy
integration checks start only after agent builds stop. Sibling ASIC/example changes
are allowed when justified; no physical EDA rerun for this diagnosis.

Acceptance: Timing has no simulation catalog; the actual run's timing evidence is
reachable via both generic palette and Overview entry points with correct stage and
identity, or a precise visible unavailable reason if evidence is genuinely absent.
Verify empty-filter versus missing-report states and retain legacy-stage behavior.
Document migration/deployment of stock versus saved workspace layouts. Item 3 must
end with an evidence-based explanation and recommendation, not a claim of unmeasured
rendering cost or unimplemented preloading.

## Findings and verification

Actual run `a02325d9895a428aa7b90734314e4e4a` has 1,020 timing paths across three
corners and one input-reference row. The generic/contextual palette hardcoded
Signoff, where this Timing-only run correctly has no checkpoint. The correct Timing
analysis already existed in the summary cache. Navigation now captures the published
run-specific target or falls back to that run's observed stage set; empty-state
diagnostics distinguish unloaded, missing, filtered and failed reads.

Stock Timing already excluded simulation catalog. The parent applied only the
requested saved-layout visibility mutation for `tile-38` in live Timing; revision
175 → 176, Testing's `tile-50` and other tiles/workspaces/contexts verified unchanged.
Regression tests protect stock and exported-template membership.

Actual provider index reads were about 7.5s (1.70 MB); one detail was about 7.6s.
These are cold command wall times, not render benchmarks. Existing Timing caching
includes persistent indexes and memory-only detail/projection reuse. Hidden workspace
reconciliation is already passive; completion triggers summaries but not path reads.
Recommendation: bounded selected/followed-source index warm-up when analysis becomes
available, no hidden drawing, details lazy, explicit-only option. Policy is not yet
implemented.

Full Workbench build/lint/runtest and changed-file formatting passed. Global formatting
still reports unrelated pre-existing sections. Actual a023 private HTTP/PTY, Timing-only
and historical Signoff palette regressions passed. Final retained-client refresh is
receipt `refresh-binaries-54ade3e08ab54997baa5adcddb18ca14`; daemon bytes did not change.
Restart only the client and reissue Inspect timing paths for a023. Exact source identities,
commands, counts, receipt paths and cache limits are in the
[findings and policy record](timing_workspace_loading.md).
