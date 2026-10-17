# F04 — Named workspaces, tiles and saved layouts

Status (2026-10-15): **FS0 named workspace/tile host and autosaved session restoration
delivered** with Main/independent contexts and pins. See [terminal](../fs0_terminal.md)
and [acceptance](../fs0_acceptance.md). Requirements below remain normative: current
geometry is shelf-based and multi-monitor adoption acceptance remains later.
FS3 now provides CLI template export/import/clone and persistent local chrome/header
preferences; see [adoption guide](../fs3_adoption.md).

## User outcome

Switch between Overview, Timing and Resources arrangements like i3 workspaces.
Each contains the views useful for that task. Save an arrangement for later use or
as a starter template, and eventually attach independent monitor surfaces.

## Requirements

- Stable workspace/view and tile-instance identities, independent of screen size.
- Move/reorder, resize, hide/restore, focus and zoom tiles.
- Preserve requested geometry separately from effective clamped geometry.
- Recoverable compact/tiny rendering and cell-aware text measurement.
- Persist named layouts/templates with explicit schema versions.
- Keep layout templates separate from live session state and canonical run data.
- Switching arrangements preserves local investigation state. Overview, Timing and
  Resources are workspaces following the project session's Main run context by
  default. Selecting a run updates all linked workspaces, not just the visible one.
- Bind a workspace to an independent context for a separate investigation, then
  relink when desired. Per-tile references override the workspace's context.
- Background updates do not steal focus or selection. Modal input captures keys
  before tile/global bindings, including multi-key sequences and paste.
- Multiple terminal surfaces eventually share backend data and linked run contexts
  while retaining independent navigation, focus and scroll.
- F12 makes workspace/navigation/status/legend bars ordinary mountable tiles where
  practical. No required top/bottom/side bands; commands remain reachable without
  mounted navigation chrome. Most tile headers are configurable, including absent.
- Workspace semantics and appearance presets are independent. Switching skin/color/
  icons/density preserves tile IDs, context/pin bindings and local investigation;
  applying suggested geometry is a separate explicit operation.

## Accepted vocabulary and context

Project session → windows → workspaces → tile instances. A window is an attached
terminal/application surface; a workspace is a named arrangement (Overview, Timing,
Resources, optionally Simulation). Workspaces can be switched within one surface
or displayed across surfaces. Run contexts belong to the project session and are
referenced by workspaces, not owned by windows or selector tiles.

See [F10](run_contexts.md) for Main/independent linking, multiple run-selector tiles,
revision handling and persistence. Moving a workspace between windows retains its
binding; moving a following tile between workspaces adopts the destination binding.
Templates create independent view instances, but may deliberately link them to Main.

Major/minor roles are optional layout defaults, not mandatory editor/document
structure. Workbench can have an overview without a required primary document.

The daemon registry owns semantic session/window/workspace/tile instances
and context bindings. Clients project this registry and own local active-workspace
presentation, dimensions, focus, scroll, overlays and effective geometry. Saved
requested layouts/preferences are versioned UI configuration; do not turn another
client's terminal dimensions into global layout truth. The shared registry is
implemented once and reused across skins.

## First demo / later

Usability correction (2026-10-15): the real host now defaults to Fit, distributing
visible tiles across available cells with compact focused-tile fallback. Requested
sizes remain available through a separate layout command; appearance switches do
not alter either mode. The additive Overview preset includes honest stage views
even when synthesis is the only requested operation. Empty saved arrangements
remain explicit and recoverable, not silently overwritten.

First: at least two named arrangements on one surface sharing Main, differently
sized run selectors, unlink/relink and basic tile manipulation. Save/restore follows
in M3; multiple monitor windows and cross-window movement follow in M5.
Starter templates reduce visible complexity without disabling backend capabilities.

Dependencies: F02 host/tile contracts; F05 evidence; F10 contexts. Fixture data
supports independent verification. D1 and D2/D3 FS0 defaults are accepted; later
snapshot/retention policy does not block host geometry.
