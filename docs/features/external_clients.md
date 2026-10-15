# F08 — Ches, source navigation and automation

Status: requested future consumers of the module/command boundary.

## Requirements

- Keep typed query/command/subscription contracts independent of terminal widgets.
- A Ches companion tile can subscribe to execution, resources, timing and checks
  through a compact summary while Workbench's main surface is out of sight.
- A companion declares its context/reference binding explicitly. It can follow Main
  or a named run without sharing Workbench tile focus/scroll. Project-scoped test
  status may accompany the summary with its own scope label.
- Start by sharing semantic data; sharing renderer packages requires a separately
  validated host/input/geometry boundary.
- Offer an editor-open action carrying source file/range and source/build identity.
  Mark stale/unmapped locations explicitly. Never guess an OCaml source line from
  a synthesized name without mapping evidence.
- Explore an embedded Ches editing surface later; major/minor roles should remain
  layout policy rather than a restriction on inspection capability.
- The F12 Timing gallery's `ches-mini` is a clearly labeled placeholder. Inspect
  editor-host/focus/source-navigation APIs before real integration; reusable float
  placement/capture does not by itself constitute an embeddable editor.
- Aim for shared domain-free UI primitives with Ches, but establish a bounded
  adapter/extraction first. Do not make sibling source availability or a wholesale
  Ches runtime dependency necessary to run the Workbench gallery.
- CLI scripts, piping and MCP/AI adapters use the same semantic operations and
  evidence references as the palette, not screen scraping or synthetic keypresses.
- Version public contracts and keep bounded reads/subscriptions. External readers
  do not own flow lifetime merely because they attach or detach.

## First demo / later

First: prove the new module data and operation API through a plain/headless consumer.
Later: Ches summary, external source navigation, MCP adapter, then embedded editing
if the navigation workflow justifies it. None blocks the first ASIC tile demo.

Dependencies: F02/F03 public contracts; F06 source evidence for navigation.
