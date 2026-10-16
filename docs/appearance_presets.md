# Experimental appearance presets

First FS5 slice implemented 2026-10-15. These are skins over the actual FS0 tile
host, not a separate renderer or synthetic-only application. No final product
default has been selected. The aesthetics worktree now starts with A/Instrument,
vivid color, Unicode markers and comfortable density as an experimental review preset.

**Frontend composition follow-on delivered:** bounded fuzzy palette with matched
character highlighting and Tab/Shift-Tab navigation, quiet default Follow/project
badges, per-tile presentation controls, typed status colors and centralized OCaml
workspace definitions. See [source map, controls and acceptance](frontend_composition.md).

The subsequent [refinement](frontend_refinement.md) supplies styled palette/short
panel borders, titles in borders, zero default vertical inset, one-row navigation,
wide width-aware run labels, horizontal stages, compact Overview panels and a
dedicated Timing investigation workspace. Padding now applies horizontally;
explicit visibility/badge controls and the density axis remain supported.

## Try them

Start the client using the normal [README instructions](../README.md). Press
**Space c c**, search for one of these commands, and press **Enter**:

| Palette command | Treatment |
| --- | --- |
| `Appearance: A - Instrument` | Rounded Unicode frames, uppercase labels and synthesis-count emphasis |
| `Appearance: B - Structured` | Rectangular frames and clear focus emphasis |
| `Appearance: C - Minimal` | Borderless, quieter chrome |
| `Appearance: D - Studio` | Filled card surfaces and tile-title badges |
| `Appearance: E - Structured studio` | Structured frames plus Studio header treatment |

Independent commands:

- `Appearance: Color Vivid`, `Selective`, or `Restrained`.
- `Appearance: Icons Off`, `ASCII`, or `Unicode`.
- `Appearance: Density Compact` or `Comfortable`.

Search `appearance` to see all controls; `[active]` indicates the current choice.
Try **E + Unicode + Selective + Comfortable**, or **A + Unicode + Vivid + Compact**.
Existing header/chrome toggles still work. ASCII/off modes use ASCII framing and
do not require a special font; Unicode uses standard box drawing, not Nerd Font.
Provider text is preserved, so icon mode does not transliterate source/log content.

Changes affect only this client. They retain workspace, selected run, pinned tile
references, focus, filters, scroll and requested layout. They do not submit provider
work or change the daemon registry. Preferences currently reset when the client
restarts; persistence remains a later small extension.

Frames/padding degrade on small tiles to protect evidence rows. Comfortable density
adds default inner padding when space permits; explicit padding overrides take
priority. Appearance does not populate workspaces or
change layout mode: **Layout: Fit tiles to window** fills the available surface,
while **Layout: Requested tile sizes** uses the saved shelf sizes. Fit is the new
client default; requested geometry remains intact. Filled title badges indicate focus; they are not fake
navigation tabs. Real tile-local tab groups, richer path inspectors, source peeks,
Nerd Font mode and final visual polish remain subsequent F12/gallery work.

## Captures

Generate plain-text and ANSI terminal frames without a daemon or EDA:

```sh
_build/default/terminal/main.exe --capture-appearance /tmp/opencode/wb-appearance-review
```

The command emits A–E × compact/comfortable × five identical synthetic scenarios
(aesthetic Overview, synthesis, timing-unavailable, pinned synthesis, palette)
× 80×24/120×40, in `.txt` and `.ansi`: 200 files. ANSI files retain colors for terminal viewing. The synthetic
50/73 counts are labeled fixtures; this is not new ASIC evidence or a complete rich
Timing gallery. Current captures: `/tmp/opencode/workbench-appearance-20261015/`.

## Verification

- Terminal build and inline tests passed; formatter and lint checks passed.
- Renderer tests cover all 90 preset/color/icon/density combinations, cell bounds
  down to 1×1, headerless views, ASCII fallback, distinct skins and following/pinned
  73/50 evidence at compact sizes.
- Pure state tests retain contexts, pins and local state while changing appearance.
- Actual PTY palette selection exercised all five presets and verified their active
  markers, unchanged daemon registry and no provider calls caused by restyling:
  `/tmp/opencode/workbench-fs0-cub6u1kx/fixture/pty.ansi` and its recorded responses.
- Installed client/discovery/hierarchy/resize workflow and legacy capture checks
  passed after integration. No real EDA run was needed for this appearance change.

## Empty or sparse saved workspaces

### Aesthetics worktree first pass (2026-10-16)

Use **Apply default layout (add missing tiles)** from Overview to add the new
**Session**, **Workspaces**, and **Stage checklist** tiles to an existing layout.
**Layout: Fit tiles to window** gives Overview a compact workspace strip across
the top, session/run/checklist sidebar, and larger content panels when space permits.
Requested sizes remain available through the separate Requested layout mode.
Narrow surfaces fall back to a grid or focused-tile view.

The subsequent [composition delivery](frontend_composition.md) moves the run selector
to the wider upper-main region, stacks main panels, and centralizes Overview/Timing/
Testing in `terminal/workspaces/`. Use **Apply preset: Overview (add missing tiles)**
for additive membership or explicit **Reset arrangement** for requested geometry;
both preserve extras, pins and contexts. Navigation is quiet by default; Testing now
includes the FS2 simulation tile. The earlier geometry description above is historical.

- **Tab / Shift-Tab** focus the next/previous visible tile.
- In **Workspaces**, **j/k or arrows** browse and **Enter** opens the destination;
  **1–9** also switch registry workspaces. **Create Testing workspace** explicitly
  adds a testing arrangement. These are workspaces within a terminal window.
- **Session** shows project, context linkage, connection/status and selected run.
  Its presence removes the redundant global header. **Enter** opens full details,
  **[ / ]** scroll, and **Esc** returns. Long opaque run IDs use six leading and
  six trailing characters; identities used for actions remain exact.
- **Stage checklist** uses explicit stage statuses, symbols and semantic colors.
  Providers supplying the optional stage-plan extension populate live rows; others
  still say **not reported**. **j/k** selects a stage, **Enter** inspects it and
  **r** prepares its advertised new-run action. Use the existing palette launch
  command after planning. Imported aggregate outcomes/check verdicts and freshness
  remain separate from stage completion. The [synthetic flow demo](synthetic_flow.md)
  exercises this end to end without EDA tools.
- Rounded Instrument frames, brighter semantic colors and comfortable padding
  are the provisional startup combination. Palette appearance controls still work;
  ASCII/off modes provide font-independent alternatives. Decoration degrades at
  small sizes to keep evidence readable.

`bonsai_term_spinners` was not installed in the selected switch during this slice;
animated indicators and Nerd Font experiments remain follow-ups.

### Earlier saved layouts

The original acceptance state left Overview empty by moving its only tile into
Timing, and its FS0 comparison workspace contains just two small synthesis tiles.
That is saved test layout, not missing run evidence. Use **Switch to Overview →
Apply default layout (add missing tiles)** for the full dashboard, then **Fit tiles
to window**. Appearance presets change style only. Default stage views explicitly
report not-requested/unsupported evidence for a synthesis-only run.

Regression coverage: `python3 -B scripts/test-fs0-dashboard.py` operates on a private
copy of saved Workbench state and verifies startup/loading, additive 13-tile Overview,
full-surface pinned/following comparison, Preferred/Fit transitions and unchanged
provider evidence. Captures: `/tmp/opencode/workbench-fs0-dashboard-52akmtcc/`.
