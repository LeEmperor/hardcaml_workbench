# Appearance source material and interpretation

Imported 2026-10-15 from the owner's `~/Downloads/` exports:

| File | Role |
| --- | --- |
| [TUI candidate gallery handoff](tui_candidate_gallery_handoff.md) | Newer v0.5 living visual handoff; takes precedence over the older export |
| [TUI design-system handoff](tui_design_system_handoff.md) | Older foundation proposal, retained for provenance; superseded where conflicting |

Both Markdown files were copied verbatim on import. Subsequent visual reviews should
update the newer handoff in place, rather than accumulating versioned exports.
The HTML/PNG names mentioned in the handoff are external prototype references;
this import contains the two requested Markdown exports, not those assets. Their
described browser behavior is not evidence of terminal implementation or real EDA.

**Post-intake FS0 update:** the daemon workspace registry and provisional tile host
are now implemented; below, the implementation correction and Ches notes describe
what source inspection found at intake. First A–E skins and presentation controls
now run on the actual host; the richer gallery remains incomplete. See the
[preset guide](../appearance_presets.md) for controls and tested captures.
See the [delivery plan](../construction_phase_plan.md) for current evidence.

## Workbench interpretation and precedence

The gallery owns current appearance preferences/candidates. [F12](../features/appearance.md)
translates them into Workbench requirements; [rendering](../rendering.md) owns the
shared presentation rules, and the [construction plan](../construction_phase_plan.md)
owns ordering/evidence. The export's “gallery first” phases describe its visual
workstream, not a replacement for FS0's functional demo queue. The owner's current
instruction keeps polished aesthetics out of the initial-demo critical path.

- **Vocabulary matches:** Project session → Window → Workspace → Tiles, with shared
  run contexts alongside windows. Appearance presets are not workspace identities.
- **Implementation correction:** the gallery describes daemon tracking as existing.
  Workbench currently has project/job/artifact services and a fixed client, not the
  proposed window/workspace/tile registry. Implement one authoritative daemon-side
  semantic registry incrementally in M2; clients project it and own local rendering
  state. Do not claim the registry exists or add another one just for the gallery.
- **Ches inspection:** `screen/floating.mli` provides centered cell-based placement
  for a single float; `screen/ui_state.mli` documents one transient float, release on
  close and return-focus behavior. `tile/host.mli` supplies focus/input/paste ownership
  with editor-primary assumptions. These are useful reuse seams, not proof of a
  general stacked/nonmodal/floating-workspace API or an installable shared UI package.
  Inspect their implementation/dependencies before extraction; reuse via a bounded
  adapter/shared primitive and preserve Workbench's no-mandatory-editor model.
- **Interaction examples:** browser Ctrl+K does not replace intended `Space c c`.
  Selected-path/source examples are mock navigation, not source-map or Ches integration.
- **Scope:** preserve A–E and independent appearance axes; choose no final default.
  A temporary functional-demo skin is not a product selection. No web renderer,
  mandatory Nerd Font, new tool provider or full multi-client window manager is
  implied by the visual prototype.

FS0 builds the minimum appearance-independent host seams. [FS5](../feature_sets.md#fs5--appearance-experiments-and-candidate-gallery)
holds the comparative gallery and review. It can run alongside functional work once
the shared primitives exist; its number is not a required execution order.
