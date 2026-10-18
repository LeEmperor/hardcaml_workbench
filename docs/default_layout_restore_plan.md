# One-step default layout restoration

Status: **implemented and verified**, 2026-10-18. Preserve all existing dirty work
in the current `oxcaml` tree (HEAD `849c63b`). The owner's live Overview was repaired
separately through the active daemon; this feature must not change it implicitly.

## Agreed behavior

Add **Restore default layout: Overview / Timing / Testing (hide extras)** and a
current-preset variant. Named commands apply that preset to the captured current
workspace; they do not select another workspace by display name. An unknown/custom
current preset has an explicit disabled reason, with named choices available.

One atomic registry mutation:

1. Match preset tile occurrences by kind, using the first unclaimed existing tile
   in registry order, including hidden tiles. Preserve those exact IDs/bindings.
2. Create missing default occurrences as Follow tiles in the existing workspace.
3. Show matched/created defaults, restore their requested geometry.
4. Hide every unclaimed extra/duplicate in that workspace without deleting it or
   changing its geometry/binding. Preserve existing registry tile order.
5. Set stable preset ID and clear that workspace's zoom.

Preserve workspace name/window/context/binding revision, all run selections,
contexts, pins, evidence and other workspaces. Validate the whole request before
publication; bad definitions, exhausted IDs or stale CAS must not partially apply.
Repeated restore must not allocate duplicate tiles. Empty definitions are invalid.

After an acknowledged success, select **Fit** for the initiating client and persist
it through existing preferences. Do not optimistically switch modes on failure.
Late success must not override newer layout choices, workspace roundtrips, changed
project/daemon/client or superseding intent. The registry operation may finish on
its captured workspace even if the client navigates; never retarget it.

Appearance/header/badge/padding choices remain unchanged. Existing additive Apply
and geometry-only Reset keep their current semantics. No implicit restore on view,
restart, opening a palette or changing a skin. No provider or job execution.

## Ownership / budget

- **A protocol/presets:** `protocol/workspace.ml`, focused protocol tests,
  `terminal/workspaces/definition.ml` and shared workspace tests. Add
  `Mutation.Restore_default_layout { workspace; preset; tiles }` and
  `Definition.restore`. Build `/tmp/opencode/layout-restore-protocol` at `-j6`.
- **B client:** `terminal/workspace_host.ml`, `terminal/main.ml`, focused inline
  tests. Captured commands and success-only/local-intent-fenced Fit persistence.
  Build `/tmp/opencode/layout-restore-client` at `-j6`.
- **C native proof:** new `scripts/test-default-layout-restore.py`; private real
  HTTP/PTY state and prebuilt binaries, no builds. Prove cluttered/hidden/pinned/
  zoomed repair, all preset IDs, appearance/context preservation, one CAS revision,
  stale rejection and no provider/job execution.
- **Coordinator:** this plan/guides, integration review, final normal full checks
  and focused regression, then refresh matching pinned binaries without restarting
  live processes. No live state mutation/reseed as part of implementing the command.

Maximum shared build pool is20 including nested jobs; A/B get6 each, parent normally
waits and may use20 only after agent builds stop. Use `scripts/with-switch.sh` and
its formatter. No Git add/commit/push/reset/merge/authorship operations.

## Verification gates

- [x] Atomic reducer, matching/creation/visibility/geometry and preservation tests.
- [x] Captured palette commands, disabled states and late/failed receipt guards.
- [x] Native HTTP/PTY restores actual composed layout and persists Fit only on success.
- [x] Full normal format/lint/tests/build and relevant adoption/Testing/interrupt checks.
- [x] Current controls documented; matching persistent binaries refreshed.

## Delivery and evidence

[Current controls and exact semantics](default_layout_restore.md).

- `Mutation.Restore_default_layout` and `Definition.restore` implement the atomic
  server transition; original Apply/Reset tests remain valid.
- Named/current palette actions capture workspace and immutable shared definition.
  Main dispatches one CAS request at the captured revision with no retry. Local
  intent tokens guard success-only Fit/persistence, including same-value newer
  choices, workspace roundtrips and reconnects.
- Full normal `dune build -j20`, `dune build -j20 @fmt @lint`, and `dune runtest -j20`
  passed after separate agent builds at6 jobs each. No aggregate allocation exceeded20.
- Native proof: **58 checks**, `/tmp/opencode/default-layout-restore-t4rz4qvv/result.json`.
  The proxy observed7 successful restore receipts and1 expected stale Conflict;
  it delayed delivery to prove no optimistic Fit and superseding local choices.
- FS3 adoption: **141 checks**, `/tmp/opencode/fs3-adoption-l4x5amz6/result.json`.
- Cooperative Testing: **15 checks**, `/tmp/opencode/testing-workspace-srv7uj24/verified.json`.
- Interrupt/restoration: **5/5**, `/tmp/opencode/workbench-terminal-interrupt-ljbc28w3/results.json`.

The initial adoption regression stopped at its obsolete seven-tile Testing starter
expectation. The already-delivered cooperative preset has ten tiles; the fixture
now checks both count and exact ordered membership. Native restore pane-position
matching was anchored to borders so a workspace tab containing “timing” is not
misidentified as the Timing pane. Neither correction relaxed product assertions.

No live workspace, daemon, canonical evidence or selected run was changed by the
implementation/testing. The earlier user-authorized live Overview repair is a
separate receipt. No staging, commits, pushes or other Git authorship operations.

Normal binaries and the persistent real-demo daemon/client/exporter copies are
refreshed. Example receipt:
`.dev/workbench-real-demo/receipts/refresh-binaries-573452bea4d94baeb0635f81832ce473/`.
After active jobs finish, restart the matching pair to expose the new command.
No reseed is needed; live processes and workspace state were left untouched.
