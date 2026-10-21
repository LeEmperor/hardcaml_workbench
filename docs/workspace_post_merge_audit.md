# Post-merge workspace composition audit

Baseline: merge `74b6c2a` (2026-10-21), including hierarchy, reconnect/navigation
hydration, and Testing/Timing/Overview changes from oxcaml. The owner requested an
audit and reconciliation against the shared window/workspace specification, with no
stale parallel workspace definitions. **Implementation and verification complete.**

## Work partition

| Owner | Audit and implementation boundary | Completion criteria |
| --- | --- | --- |
| Agent 1 | `terminal/workspaces/` and Overview compatibility shim | Delivered stock membership/layout/presentation reflected in `stock.sexp`; remove unused competing tables; regressions for catalog and legacy preservation |
| Agent 2 | Host/view and domain integration | Custom tile compositions get merged functionality without built-in preset gating; shared layout fallback; presentation/navigation regressions |
| Agent 3 | Native startup/actions, CLI and demo/acceptance consumers | Canonical template/config creation; no implicit preset application over custom investigations; metadata/PTY acceptance |
| Parent | Documentation, integration and verification | Record exact outcomes; central builds at `-j20`; no Git staging/commits/pushes |

All three implementation units are complete. Agents ran no builds. Checks run
serially against private fixtures; real project state is not an acceptance fixture.

## Findings and changes

### Canonical catalog

- The merged catalog declared **Overview, Timing and Testing** as starters
  (`471419a:terminal/workspaces/presets.ml`; retained when Waveforms was added in
  `994cc85`). The canonical default window omitted Testing. It now declares all three.
- Overview and Timing's delivered membership and presentation already matched the
  shared spec. Testing retains the six cooperative panes and **2:3:3** column weights.
- Hierarchy is deliberately opt-in in the merged feature, not a missing mandatory
  stock tile. A custom definition can contain `(kind hierarchy)` with the ordinary
  template/key/tree fields. No separate Hierarchy workspace format is needed.
- Removed unused compiled stock helpers and the obsolete shell from `common.ml`,
  including a stale checklist minimum. `overview_layout.ml` remains a projection.
- Removed the renderer's duplicated generic grid; its fallback uses the shared engine.

### Feature behavior follows tile membership

- Timing investigation reuse checks visible Timing panes and their resolved run
  bindings, not the workspace's preset name. Unrelated pins do not prevent reuse.
- Opening an investigation into a compatible custom workspace previously applied the
  built-in Timing preset afterward. It now leaves the entire live arrangement and
  frozen configuration untouched. Only a genuinely new investigation instantiates
  the canonical template, atomically, before establishing its independent context.
- Testing convenience availability/creation follows actual cooperative pane membership.
- Waveforms chrome/hints follow visible/focused waveform tiles and effective presentation
  policy, so custom mixtures do not depend on the `waveforms` preset label.
- Hierarchy rendering and input already dispatch by kind. Same-artifact refresh now
  preserves selection/expansion, with stale transport completions fenced on reconnect.
- Shared-spec tests exercise a custom mixture of hierarchy, Testing, Timing, checklist
  and synthesis, including restored navigation and local presentation precedence.

### Creation, exports and demos

- Built-in `starter` exports now return the exact nested canonical template instead
  of a compatibility conversion that regenerated visibility as `hidden = false`.
- Synthetic and real-ASIC demo seeders consume the exported full configuration for
  fresh initialization, and exact canonical templates for legacy Bootstrap or explicit
  missing-workspace creation. They retain `workspace-config.json` as seed evidence.
- Terminal config loading validates the encoded resolved size before connection,
  matching the CLI's expanded-catalog bound.
- Existing users' saved arrangements are not overwritten to add Testing. Use
  **Create built-in workspace: Testing** to add it explicitly to such a session.

## Intentional compatibility boundaries

The following are supported adapters, not competing stock layout definitions:

- Protocol `Get` placeholders and initialize-once legacy `Bootstrap` protect old
  sessions and import-before-first-terminal behavior.
- Version-1 `generic`/`asic` portable templates and import/export/clone remain usable.
  They describe portable membership/geometry, not an alternate responsive layout engine.
- `overview.ml`, `timing.ml`, `testing.ml` and `waveforms.ml` project `stock.sexp` for
  existing consumers; new stock authoring belongs in the spec.
- Saved resolved definitions intentionally retain the user's earlier layout policy.
  They are not automatically refreshed from current stock. Explicit built-in Restore
  selects current defaults while preserving IDs/pins/context and detaching old policy.
- Domain rendering, navigation and provider integration remain OCaml implementations;
  the specification composes these capabilities rather than embedding executable code.

## Verification and acceptance maintenance

Passed:

- Protocol, workspace persistence, workspace-definition and terminal tests, including
  separate-process navigation/presentation retention.
- Native daemon/client/CLI/setup/exporter build; `@lint`; changed OCaml formatting.
- Config CLI/HTTP/PTY: `/tmp/opencode/workspace-config-rzp8m2pd/result.json`.
- Legacy FS3 adoption: `/tmp/opencode/fs3-adoption-8x1n81br/result.json`.
- Hierarchy HTTP/PTY: `/tmp/opencode/hierarchy-tile-mrpxyal2`.
- Focused custom Timing reuse/atomic creation:
  `/tmp/opencode/frontend-refinement-6cde00c3cd9e/result.json`.
- Synthetic Testing and canonical reseed/restart preservation:
  `/tmp/opencode/synthetic-flow-sxzv2uoz`.
- Full frontend refinement, including Overview viewport geometry, local row overrides,
  layered Timing close behavior, canonical investigation creation, custom Timing reuse
  and exact navigation restoration:
  `/tmp/opencode/frontend-refinement-cc87d7ab1197/result.json` and its
  `-two-runs` companion directory.
- Reconnect with the single canonical Testing instance, preserved attempt/artifact
  evidence and zero extra provider jobs:
  `/tmp/opencode/client-reconnect-dytn7abb/result.json`.

Merged UI behavior made several older acceptance assumptions stale: uppercase body
headings moved to lowercase borders; saved focus/workspace is restored on reconnect;
Closing an overlay preserves underlying Timing detail; Testing already exists at
fresh startup. Tests now establish focus and close-layer preconditions explicitly,
derive stock membership from the shared export, and assert preserved navigation and
provenance instead of recreating a second Testing workspace.

The real-ASIC demo seeder now consumes the same exports, but its live demo was not
reseeded as part of this audit. Its integration change was reviewed; private synthetic
fixtures exercise the initialization contract without touching retained real evidence.

Final source/document diff review and whitespace checks passed. Failed development
runs are retained separately; the receipts above are the successful evidence.
No Git staging, commits, pushes or sibling-repository changes were performed.
