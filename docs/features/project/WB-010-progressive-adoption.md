---
id: WB-010
title: Useful operation at varying project integration levels
category: project
feature_sets: [FS0, FS3]
status: partial
kind: enhancement
priority: P2
severity: n/a
requested_size: Ticket
size: M
points: 13
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [adoption, capabilities, generic-projects]
depends_on: []
related: []
---

# WB-010 — Progressive project adoption

## Request
Original size: **Ticket**. Be useful on an arbitrary project before requiring a
complete Workbench manifest or hardware-provider integration.

## Current baseline
Generic Dune, manifest and driver levels are explicitly additive in the protocol.
An unusable driver degrades capability rather than preventing generic Dune use.
The opener still requires a direct regular dune-project and probes Dune.
FS3 already supplies an existing-project initializer and generic workspace template.

## Scope
- Improve capability-led onboarding for generic and partially integrated projects.
- Define a minimal read-only directory/project mode for a non-Dune root, with only
  capabilities that can honestly work there and explicit build-provider absence.
- Explain the next optional integration step without demanding full configuration.
- Keep partial provider failure localized to that capability.

## Out of scope
Universal build-system detection, executing guessed commands, and replacing Dune.
No automatic driver/configuration generation or provider installation.

## Acceptance criteria
1. A generic Dune project remains usable without a Workbench manifest.
2. A plain directory opens into the agreed minimal surface without a Dune probe failure.
3. Missing hardware hooks disable only their actions and explain how to add them.
4. Malformed optional integration reports its reason while preserving available views.
5. The user can identify supported actions before choosing any integration upgrade.

## Dependencies
Required: delivered additive capability model and starter layouts; no open blocker.
Related: none; broader filesystem editing and new-project creation are separate outcomes.

## Estimate rationale
13 points cover a minimal generic-root mode and one bounded onboarding/capability pass.
Exclude new build adapters, a file browser and provider-template authoring.

## Assumptions and decisions needed
Default: non-Dune roots are read-only, with build/test unavailable until configured.
TBD: minimum useful plain-directory views and whether explicit arbitrary commands
belong to a later provider contract; they are not included in this estimate.

## References
- [Integration levels](../../../protocol/project_integration.ml)
- [Current root validation](../../../backend/service.ml)
- [Delivered adoption](../../fs3_adoption.md)
