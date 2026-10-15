# Experimental appearance presets

First FS5 slice implemented 2026-10-15. These are skins over the actual FS0 tile
host, not a separate renderer or synthetic-only application. No final product
default has been selected; the initial skin is B/Structured with selective color,
ASCII markers and compact density.

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
adds inner padding when space permits. Appearance does not populate workspaces or
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

The command emits A–E × compact/comfortable × four identical synthetic scenarios
(synthesis, timing-unavailable, pinned synthesis, palette) × 80×24/120×40, in `.txt`
and `.ansi`: 160 files. ANSI files retain colors for terminal viewing. The synthetic
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
