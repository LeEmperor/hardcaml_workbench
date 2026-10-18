# Restore a workspace's default layout

Implemented and verified 2026-10-18. This is the one-step recovery command for a
workspace that has accumulated extra tiles, hidden defaults, unusual sizes or zoom.
[Implementation plan and evidence](default_layout_restore_plan.md).

## Use it

Go to the workspace you want to repair, open **Space c c**, and choose:

- **Restore default layout: Overview (hide extras)**
- **Restore default layout: Timing (hide extras)**
- **Restore default layout: Testing (hide extras)**

There is also **Restore default layout (current preset; hide extras)**. It uses
the workspace's stable preset ID, not its display name. If you accidentally applied
the wrong preset, choose the explicit named command instead. Unknown/custom current
presets disable the current-preset command with an explanation; the named choices
remain available.

**Named commands apply to the current captured workspace.** Choosing Overview
while in Testing changes that workspace's preset; it does not switch to the workspace
named Overview or rename the current workspace.

## What one restore does

The daemon atomically:

1. Reuses matching default tiles, including hidden ones, preserving their IDs/pins.
2. Creates missing default tiles as following views in the same workspace context.
3. Shows defaults and restores their requested sizes.
4. Hides every extra/duplicate occurrence beyond the preset's declared membership.
5. Sets the selected preset ID and clears that workspace's zoom.

The initiating client switches to **Fit** only after receiving success and saves
that choice through the existing project/environment-scoped preference store.
Fit remains a client-level layout preference; other workspaces' saved registry
arrangements are not modified. Responsive/narrow fallback still applies when the
terminal cannot fit the normal composition.

For Overview this restores tabs across the top, Session/Runs/Stage checklist/
Planned run down the left, and six domain panels down the right.

Extras are **hidden, not deleted**. Their identities, bindings and geometry remain
available through the existing **Restore … tile** palette commands. Total stored
tile counts can therefore remain larger than the visible default arrangement.
Showing extras again may change Fit packing, as expected.

Run selection, contexts, pins, evidence, workspace name/window, existing tile order
and all other workspace records are preserved. Appearance, header/padding/badge
choices and skin/scheme are not reset. Matching uses the first unclaimed tile of
each kind in registry order; excess duplicates are hidden, including pinned extras
whose pin remains stored. Repeating the command does not accumulate new tiles.

## How it differs from Apply and Reset

| Command | Add missing defaults | Restore sizes | Show hidden defaults | Hide extras | Clear zoom / select Fit |
| --- | --- | --- | --- | --- | --- |
| Apply preset / Apply default layout | Yes | No | No | No | No |
| Reset arrangement | Yes | Yes | No | No | No |
| **Restore default layout** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |

The older additive commands retain their original behavior. Nothing restores a
layout automatically during startup, rendering, palette opening or a skin change.
The built-in definitions in `terminal/workspaces/` are the default source of truth;
this command does not freeze a private copy of an old version or save a custom
arrangement as a new default. Portable template export/import remains available
separately.

## Captured commands and failures

The palette captures workspace identity, preset definition and registry revision.
The daemon applies one compare-and-swap mutation; a conflict is reported without
silently retrying against changed state. Failed or uncertain receipts do not
optimistically change the local mode. A later layout choice, workspace roundtrip,
new restore intent, reconnect or project/daemon change prevents a late receipt from
overriding current local intent. The server may already have restored the originally
captured workspace; a suppressed local Fit does not claim that server work was undone.

Upgrade matching daemon/client binaries together to use the new mutation. Stored
workspace snapshots are unchanged and remain readable. No flow, build or test job
is launched by restoration.

Normal binaries and the prepared real-demo copies are refreshed. Restart the
matching daemon/client after active jobs finish; no reseed is needed. Receipt under
the example's `.dev/workbench-real-demo/`:
`receipts/refresh-binaries-573452bea4d94baeb0635f81832ce473/`.

## Verification

Full normal build, format/lint and tests passed serially at `-j20` within the shared
20-job budget. Native proof uses a private metadata-only project and observing HTTP
proxy, not the owner's running daemon or live arrangements.

- **58 native checks:** `/tmp/opencode/default-layout-restore-t4rz4qvv/result.json`.
  Eight captured restore receipts: seven successful, one expected stale Conflict.
  Actual 120x40/180x55 composed Overview, all three presets, hidden/default duplicates,
  missing defaults, pins, independent selected contexts, zoom, unchanged appearance,
  restart-persistent Fit, delayed acknowledgement and newer-local-choice precedence.
- **141 FS3 adoption checks:** `/tmp/opencode/fs3-adoption-l4x5amz6/result.json`.
  The historical Testing starter count was updated from7 to10 with exact ordered
  cooperative-pane membership; all other assertions remain.
- **15 cooperative Testing checks:** `/tmp/opencode/testing-workspace-srv7uj24/verified.json`.
- **5/5 interrupt cases:** `/tmp/opencode/workbench-terminal-interrupt-ljbc28w3/results.json`.

Pure reducer tests additionally cover invalid/empty definitions, allocation/revision
exhaustion, stale CAS, duplicate occurrence counts, repeat restoration and protocol
roundtrips. Client tests cover unknown presets, renamed workspaces and failed/late
receipt guards. No real EDA or live layout mutation was used for feature verification.

```sh
python3 -B scripts/test-default-layout-restore.py \
  --daemon _build/default/daemon/main.exe \
  --client _build/default/terminal/main.exe \
  --workspace-cli _build/default/workspace_cli/main.exe \
  --setup _build/default/setup/main.exe
```

Use prebuilt matching binaries and allow600 seconds for the HTTP/PTY proof.
