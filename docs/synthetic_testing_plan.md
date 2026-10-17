# Synthetic Testing workspace and roomier Session layouts

Activated from owner request: the synthetic demo should open Overview, Timing and
Testing by default; Testing should have useful clearly synthetic FS2 data; Timing
and Testing Session/sidebar regions should be less cramped.

## Scope and rules

- Preserve the current uncommitted frontend/example work and all live demo state.
  No Git staging, commits, pushes, resets or merges.
- Up to two implementation agents, each2 build jobs, separate build dirs under
  `/tmp/opencode/testing-{provider,layout}`. Final parent checks serial at2.
- No ASIC/EDA or hardware simulation is needed: this is explicitly synthetic test
  data through the real existing FS2 provider/supervisor/RPC contract.
- Keep run context and project-scoped simulation independent; no manufactured ASIC
  association, acceptance verdict or inferred cases from human log output.

## A — synthetic provider and seed lifecycle

Own new `demo/synthetic_flow/simulation_provider.py` and self-contained wire helper,
`scripts/synthetic-flow-demo.py`, new native acceptance script and relevant synthetic
harness changes. Prepare copies all provider dependencies into the demo project and
writes optional FS2 companion config using the actual Python executable.

Supply bounded declared suites/cases, deterministic seeds/parameters, passing and
failing outcomes, readable labeled logs/reports and an explicitly synthetic trace
artifact. No dependency on a repo test fixture after prepare. Live events and reruns
use normal job supervision; process failure and semantic failure stay distinct.

Seed creates missing Testing using the exported OCaml preset and stable preset IDs,
then applies definitions additively. Do not duplicate Testing on repeated seed or
rename, overwrite custom workspaces, erase pins, or create a second layout registry.
Explicit seed discovers FS2 suites and submits two labeled representative attempts
(pass and failure) through `/api/v1/simulation`, using stable idempotency keys. Poll
boundedly for results, log useful progress, retain receipts. Ordinary daemon/client
startup and viewing must not launch tests; repeated seed within retained history
must not duplicate attempts. No direct writes to canonical daemon test records.

An existing prepared demo may be missing simulation config/provider files. Provide
an explicit additive upgrade path (seed can install missing owned demo files after
verifying the synthetic manifest, but must not overwrite a user's unrelated
simulation config). Do not require wiping saved layouts or evidence. Use clear
version/ownership checks and actionable conflict errors. The real ASIC launcher
and real example configuration must remain untouched.

## B — Timing/Testing layout width

Own `terminal/workspaces/timing.ml`, `testing.ml`, workspace geometry tests and
necessary existing Timing geometry assertions. Keep Timing Paths/Detail/Provenance
topology intact; widen Session from its hardcoded30-cell region to approximately
one third of a normal120-column viewport while preserving a usable selector.
Testing's left-side region should likewise be approximately one third, with wider
Session/generic-test content and a large FS2 simulation panel. Keep source-level
proportion/height settings clear and reuse Weighted_columns, rather than hardcoded
terminal coordinates. Preserve extras/pins/custom tiles and narrow/zoom fallback.

## Acceptance

- Exported definitions populate all three default synthetic workspaces. Repeated
  seed and renamed Testing keep one preset instance and unchanged saved custom data.
- Real daemon/client show seeded FS2 success/failure, cases/seeds/parameters, logs,
  available report/trace artifacts and targeted rerun with original inputs/new job.
- No new test runs on read/navigation/theme/client restart. Repeated seed uses exact
  existing reservations. Old demo upgrade works without replacing user config.
-120x40 and larger screenshots show widened Timing/Testing Session and usable data;
  tiny viewport geometry stays in bounds and preserve all instances/fallback.
- Existing synthetic ASIC launch/cancel, Timing investigation, FS2 and interrupt
  checks remain meaningful. Final format/lint/full tests/build serial at2.

## Status

Implementation pending. Chronological handoffs below; coordinator records actual
results and the user-facing upgrade/launch instructions at completion.
