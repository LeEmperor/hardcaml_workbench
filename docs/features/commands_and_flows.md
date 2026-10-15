# F03 — Command palette and project-owned flows

Status (2026-10-15): **FS0 palette, typed captured/revalidated commands, remembered
Plan inputs and exact-preview synthesis launch delivered**. [D2](../decisions.md)
FS0 defaults are accepted. See [terminal policy/limits](../fs0_terminal.md) and
[acceptance](../fs0_acceptance.md). Requirements remain normative; richer grammar,
capability forms and broader interactive launch-and-view coverage remain open.

## User outcome

Open a palette (requested binding: `Space c c`), search for an operation such as
`run synth`, and execute it against the remembered project flow/profile. Buttons,
shortcuts and automation invoke the same semantic operation.

## Requirements

- Commands have stable IDs, titles/search aliases, typed arguments, availability
  reasons and context requirements. Derive help and binding hints from definitions.
- Reuse definitions in optional header actions, help/legend tiles and palettes.
  Hiding a navigation/action tile cannot disable its commands. Workspace switch,
  tile-local tab switch and run-context selection are different semantic actions.
- F12's palette skin/overlay adapter reuses inspected Ches lifecycle primitives;
  start with a single transient capture. Do not assume every future peek is modal.
  `Ctrl+K` in the gallery browser is not an accepted Workbench binding change.
- Capture/revalidate the intended target; a background update must not retarget an
  accepted action. FS0 context policy is accepted in [D2](../decisions.md#d2--command-and-context-semantics).
- Workspace run selectors act on the workspace's bound context (F10), including
  other linked workspaces. Provide make-independent/link-to-context actions.
  A normal run launch does not change selection; any explicit launch-and-view
  command must identify its target context and therefore its shared effect (D2).
- Discover project-owned flow IDs, profiles, supported endpoints and parameters.
- Preview the provider-prepared plan and launch using its expected identity.
  Preserve the same selection/overrides; report invalidated previews explicitly.
- Show the effective flow/profile/endpoint in the palette. Last-used launch choices
  are separate from the historical run currently being inspected.
- Numeric shorthand such as `run synth 2` may alias a stable flow ID; list position
  is not a durable identity. Exact shorthand grammar remains a later UX choice.
- Differentiate fresh execution through a stage, continuation from a checkpoint,
  rerun and inspection. Offer only provider-supported operations.
- Cancellation targets an explicit owned operation/job. Closing the palette or
  changing workspace does not cancel a launched operation.

## Flow ownership

Recipes, algorithm choices, tool handoffs and profiles belong to the project and
`hardcaml_asic`. Workbench selects and operates them. Experimental CTS profiles or
Genus-to-LibreLane flows are desired integration examples, not current support claims.
Do not hardcode an illustrative stage list as a universal execution engine.

## First demo / later

First: build/test/cancel, workspace context actions, plus discover → select →
preview → run through synthesis. The simulation/test module (F09) reuses the same
test action and attempt identity rather than introducing a second runner.
Later: more endpoints, supported continuation, configurable command aliases and
external automation adapters. No second shell/recipe language is required.

Dependencies: F01 capabilities; F02 actions; F05 allocation and outcomes; D2.
