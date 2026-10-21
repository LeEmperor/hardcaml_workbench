---
id: WB-075
title: Human-readable job labels in the execution tile
category: presentation
feature_sets: [FS0, FS2, FS5]
status: proposed
kind: defect
priority: P2
severity: S3
requested_size: Unspecified
size: S
points: 3
confidence: high
estimate_scope: incremental
origin: owner-intake
tags: [execution, jobs, labels]
depends_on: []
related: [WB-064, WB-005, WB-063]
---

# WB-075 — Human-readable job labels in the execution tile

## Request
Owner note, 2026-10-20: why does the Testing workspace's execution tile say
`simulation.run` or `simulation.discover`? Is there a different run and discovery
that needs to be told apart?

## Current baseline
No — there is one run and one discovery. The tile prints the raw job kind,
`namespace.name` (`Job.Kind.to_string`, rendered at `host_view.ml`). `simulation.*`
jobs are the structured FS2 provider's discovery and run jobs. Generic project jobs
show as `dune.*`, and driver jobs as `project-driver.generate-rtl` / `.describe`.
The namespace is what separates structured simulation from generic Dune tests, but
the raw form reads like an internal ID.

## Scope
- Map known job kinds to short labels, e.g. `sim discover`, `sim run <case>`,
  `dune build`, `dune test`, `RTL generate`; unknown kinds keep the raw form.
- Keep the raw kind in job detail/inspection.

## Out of scope
Process-tree views (WB-005) and generic job detail (WB-064).

## Acceptance criteria
- [ ] Execution rows show readable labels that still distinguish structured simulation from generic tests.
- [ ] Unknown or provider-added kinds fall back to `namespace.name`.
- [ ] Job detail shows the exact raw kind.
- [ ] Test scripts that match the old strings are updated.

## Dependencies
None.

## Estimate rationale
3 points, high confidence: one label mapping plus script expectation updates.

## Assumptions and decisions needed
Confirm label wording; include the case or suite name on run rows when it fits?

## References
- [Job kinds](../../../protocol/job.ml)
- [Execution rendering](../../../terminal/host_view.ml)
