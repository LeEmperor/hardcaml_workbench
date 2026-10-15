# F12 — Composable appearance system and candidate gallery

Status (2026-10-15): **FS0 seams plus first A–E skins delivered**. The palette switches
preset, vivid/selective/restrained color, off/ASCII/Unicode markers and compact/
comfortable density. [Controls/captures](../appearance_presets.md) record tested scope.
Choices remain client-local/unpersisted. This starts FS5; rich Timing fixtures,
reusable tab groups, Nerd Font mode, source peeks and final default review remain.
Sources: [newer gallery](../design/tui_candidate_gallery_handoff.md) supersedes the
[older handoff](../design/tui_design_system_handoff.md). See the
[interpretation notes](../design/README.md) for implementation corrections.

## User outcome

Experiment with btop-like instruments, Lazygit-like framed investigation, gh-dash
minimalism, Posting-style tabs and their combinations without changing the project,
run context, workspace identity or domain logic. Review actual terminal examples
before selecting a default; retain alternate candidates.

## Separation of concerns

| Layer | Owns |
| --- | --- |
| Theme/tokens | Semantic text/status/focus roles, emphasis, spacing, borders and icon fallbacks |
| Components | Panel/header/tabs, metric, tree, table, diagnostics and inspector presentation |
| Layout | Tile rectangles, splits/docks/tab groups, minimum sizes and overflow |
| Tile adapter | Module-to-view mapping, local interaction and typed action intent |
| Host | Input/cursor/focus, overlay lifecycle, recovery and workspace attachment |
| Daemon | Authoritative session/window/workspace/tile identities, context bindings and domain data |

The daemon-side registry is delivered by FS0. Client-local active
workspace presentation, focus, dimensions, scroll, open overlay and effective geometry
are not global singleton state. Saved requested layouts can be daemon-managed UI
configuration; effective clamping stays local. Clients can cache/project registry
state, but cannot create a competing authoritative workspace model.

Providers and feature modules expose typed facts, units, severity/verdicts, source
references and operation availability. They do not emit terminal colors, border
glyphs, pixel positions or candidate names. UI severity emphasis must not invent
engineering acceptance. F11 summary cache keys/data remain independent of appearance.

## Independent presentation axes

1. Functional workspace composition: which tile instances are useful for the task.
2. Geometry: positions, splits, docks and tab grouping.
3. Component skin: framed/light borders, header treatment, badges and tabs.
4. Color treatment: `vivid`, `selective`, `restrained` via semantic roles.
5. Icons: `none`, `ascii`, `unicode`, `nerd_font`, with width-tested fallbacks.
6. Density: `compact`, `comfortable` spacing and secondary detail presentation.
7. Utility/chrome placement: optional navigation/status/legend/project-context tiles.

A preset can suggest geometry and utility placement plus styling, with overrides.
Changing colors/skin/icons/density never creates a new workspace or changes run
selection. Applying suggested layout changes is explicit and preserves stable
tile identities/bindings; avoid silently moving panes on a simple color change.
D-style tabs must be usable with A/B/C/E, not hardcoded to one candidate.

## Tile-first chrome and headers

- Workspace switchers, status summaries, navigation, action legends and project
  summaries are ordinary mountable tiles where practical. No mandatory global
  header/sidebar/footer bands; hiding a switcher does not disable its commands.
- Keep thin host infrastructure for renderer/input, overlay placement and recovery.
  Ensure keyboard navigation/help remain reachable with every utility tile hidden.
- Most tiles have a header by default: title, optional scope/status/subtitle, tabs,
  compact actions or metric/progress. Headerless tiny/full-bleed views are supported.
- Header style is token/component policy. Do not duplicate independent navigation
  controllers in each header; actions invoke F03 command identities.
- Focus, selected row, active tab, Main/independent binding, pinned reference and
  cache freshness must remain distinguishable. Headerless/minimal presentations
  still expose run/scope/freshness in content or inspection, never silently mislabel it.
- Workspace tabs select a workspace; tile-local tabs select a local view; run
  selectors change a run context. These visually similar controls have distinct intent.

## Floating surfaces and reusable primitives

Inspect/reuse Ches's actual float placement, release/return-focus and capture APIs
before implementing overlays. Prefer a thin adapter or bounded extraction of shared
primitives; a source-checkout dependency and wholesale Ches editor dependency are
not required. Start with the supported single transient palette lifecycle.

Palette, context-help and mock path/source peek are gallery showcases. Model input
capture/modal behavior explicitly; a future nonblocking peek must not accidentally
capture global input like a blocking palette. Arbitrary stacked floats, tiled↔floating
transitions, drag/reparenting and persistent floating panes remain candidates, not
FS0 requirements. “Pin floating position” is distinct from F05 evidence pinning.

Build on installed Bonsai Term/current rendering primitives. The suggested `tui_ui/`
tree is conceptual, not a mandated package split or an assumption that Nottui is a
Workbench dependency. Generic components must contain no ASIC/project I/O or domain
imports; prove reuse within Workbench before requiring cross-repository packaging.

## Candidates and gallery (FS5)

| Candidate | Treatment |
| --- | --- |
| A — Instrument | Framed, dense metrics/instruments inspired by btop |
| B — Structured | Strong master/detail frames and inspectors inspired by Lazygit |
| C — Minimal | Reduced chrome and text hierarchy inspired by gh-dash; retained |
| D — Studio | Rich tabs/contextual actions inspired by Posting |
| E — Structured Studio | B's framed structure plus D's tabs/polish |

A/B are currently preferred visually; D's tabs are valued. No default is selected.
E is specified in the export but not present in its described HTML prototype.

Compare **all five** with identical labeled synthetic Overview and Timing fixtures.
The gallery uses the same component/host contracts and injected state, not five
domain implementations or a second session registry. Preserve semantic selection
and local state across style changes where applicable. Include hierarchy, metrics,
diagnostics, path table/inspector and a clearly mocked source pane. Resources is a
future fixture; fake test counts/path mappings are never promoted to real evidence.

Support independent color/icon/density controls and showcase optional utility tile
placement, tab switching, focus/selection and a real reused or explicitly mocked
overlay. Capture wide and modest/narrow **terminal cell grids**, not browser pixels.
Primary use is one monitor of a four-monitor workstation; secondary use is a small
ThinkPad through SSH/tmux. Provide scroll/hide/tab/overflow recovery rather than
requiring sophisticated automatic responsive layouts immediately. Validate Unicode
width, fallback glyphs, contrast and bindings through terminal/tmux constraints.

## Delivery and acceptance

**FS0 / M2 minimum:** semantic tokens and replaceable skin, configurable headers,
mountable utility chrome, host-owned geometry, safe palette capture and local
presentation state. One provisional skin is sufficient. Show focus/selection and
evidence meaning without color or special fonts, recover at narrow sizes, and
verify a presentation change causes no provider fetch or command submission.

**FS5 / V1 gallery:** shared components render both fixtures under A–E; independent
axes work, C stays represented, E is a real variant, tabs are reusable, and no final
default is chosen before owner review. Use focused frame/geometry/input tests plus
human comparison; a browser mockup alone does not complete terminal acceptance.

**FS3 polish / FS4 integrations:** adopt reviewed presets, richer real evidence
views and eventually Ches source integration. Embedded editing, rich charts or
waveform rendering remain their own scoped features.

Dependencies: F02 typed data; F03 commands; F04 host/layout; F10 contexts; F11
appearance-independent summaries; F08 for eventual editor integration. Appearance
work does not depend on live ASIC execution. The main plan owns implementation tasks.
