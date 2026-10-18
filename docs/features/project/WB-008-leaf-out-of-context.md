---
id: WB-008
title: Leaf/IP out-of-context workflows
category: project
feature_sets: [FS1, FS2]
status: needs-design
kind: feature
priority: P2
severity: n/a
requested_size: Ticket
size: L
points: 21
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [leaf-ability, out-of-context, constraints]
depends_on: []
related: []
---

# WB-008 — Leaf-Ability

## Request
Original size: **Ticket**. Select an alternate internal IP as top and perform a
genuine out-of-context flow with appropriate constraints, not merely browse a leaf.

## Current baseline
Driver targets declare tops/configurations and can emit RTL plus structural hierarchy.
ASIC execution uses provider-owned selections and captured inputs.
A hierarchy node alone supplies neither an independently elaboratable top nor
valid boundary clocks, loads, IO assumptions or implementation constraints.

## Scope
- Adopt one provider-declared internal IP/top as a separate executable selection.
- Capture its out-of-context boundary assumptions and constraint references.
- Preview and explicitly launch a bounded provider flow for that selection.
- Keep results associated with the IP scope and distinguish them from full-chip runs.

## Out of scope
Automatically extracting every hierarchy node, arbitrary black-box constraint synthesis,
or proving full-system timing from isolated IP measurements.

## Acceptance criteria
1. Only provider-advertised alternate tops are launchable; browsing cannot launch one.
2. Preview identifies IP top, parameters, boundary assumptions and exact constraints.
3. Missing required out-of-context constraints block launch with a concrete reason.
4. Result identity distinguishes isolated IP from its enclosing design/configuration.
5. One declared IP flow retains its actual artifacts and outcome without full-chip claims.

## Dependencies
Required: delivered driver/ASIC launch boundaries and supervisor; no new ticket blocker.
Related: none required; hierarchy presentation is optional navigation, not a prerequisite.

## Estimate rationale
21 points cover one alternate-top provider contract, constrained launch and retained results.
Exclude a hierarchy-tile implementation, general partitioning and new verification engines.

## Assumptions and decisions needed
Default: explicit provider-declared OOC targets, never automatic node extraction.
TBD: first IP/provider, supported flow endpoint and mandatory boundary constraint schema.
Re-estimate if the producer cannot independently elaborate the chosen internal IP.

## References
- [Target and generation contract](../../../project_integration/driver_protocol.ml)
- [ASIC adapter boundary](../../../adapters/asic_adapter.ml)
- [Launch semantics](../../checklist_launch_workflow.md)
