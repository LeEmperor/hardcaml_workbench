# Backlog

This directory holds discussed work deliberately deferred beyond the active
[plan](../construction_phase_plan.md). It is not an automatic next-phase queue.
Reactivate an item by moving its concrete requirements into the architecture/plan.
Create a dedicated note here when an item warrants more detail, instead of adding
another top-level planning document. These entries are planning status, not code.

| Deferred item | Preserved intent | Reactivation trigger |
| --- | --- | --- |
| Dedicated comparator tile | Explicit A/B selection, contextual deltas, corner/stage/unit/constraint alignment | Pinned reference tiles prove insufficient for a real comparison task |
| Bonsai Web and embedded graphical views | Browser tiles, graphs, floorplan/layout views, richer timing paths | A concrete visual inspection need that terminal/external viewers cannot serve |
| Live FPGA integration | Vivado and project-side Hardcaml Xilinx/report providers, synthesis/implementation | Owner begins a real FPGA-only workflow; fixtures already protect shared boundaries |
| Persistent vendor/Tcl sessions | Tool process framing, serialization and lifecycle | Batch project operations prove inadequate |
| Hardware programming/ILA | Device operations and captures using the same jobs/artifacts | Actual board/emulation debug requirement |
| Waveform and signal-graph exploration | Simulation traces, circuit graphs, cross-probing | Real inspection workflow; not needed for flow monitoring |
| Power-domain analysis | Intent, crossings, isolation/retention and supplied verification | Design introduces relevant domains; distinct from physical-design PD |
| Rich power analysis | Activity/model/corner-qualified reports and comparison | Provider supplies meaningful evidence; an unimplemented tile must say unsupported |
| Multi-project workspaces | Multiple independent roots in one workspace | One-project/multiple-window organization no longer suffices |
| Distributed workers / workstation-native attachment validation | Separate execution dispatch or a local client through an SSH forward | Actual deployment need; server-side terminals remain the first target |
| Dynamic plugins and extra themes | Independently loaded extensions and user styling | Static typed features and one theme no longer cover concrete use |

Canonical result storage, a rebuildable Workbench catalog/cache, named workspace
layouts, multi-window selection and pinned reference tiles are **active plan
items**, not deferred under a generic "history/customization" label.
