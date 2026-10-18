---
id: WB-017
title: Project file exploration and explicit add-file operations
category: project
feature_sets: [FS3, FS4]
status: needs-design
kind: feature
priority: P3
severity: n/a
requested_size: Medium Feature
size: L
points: 21
confidence: low
estimate_scope: incremental
origin: owner-intake
tags: [filesystem, project-membership, providers]
depends_on: []
related: []
---

# WB-017 — Explore and add project files

## Request
Original size: **Medium Feature**. Explore the filesystem and explicitly add a file
to the project where a project-owned file list supports that operation.

## Current baseline
Dune workspace inspection discovers build metadata, and artifacts have dedicated readers.
The generic manifest declares name, driver and build/test aliases, not source membership.
Adding a file to the filesystem does not universally mean adding it to a build.
Workbench must not become the owner of a project's Dune rules.

## Scope
- Add a bounded filesystem explorer scoped to the opened project root.
- Distinguish filesystem presence from provider-declared project membership.
- Adopt one provider-owned explicit add-existing-file operation with a preview
  of the authoritative list to be changed and an observable result.
- Offer read-only exploration when no membership-edit capability is declared.

## Out of scope
General text editing, moving/deleting trees, rewriting Dune stanzas and VCS staging.
Do not invent a Workbench source-file list to shadow the real build system.

## Acceptance criteria
1. Large/unreadable directories produce bounded pages or diagnostics, not a frozen view.
2. Entries distinguish ordinary files, directories, links and inaccessible paths.
3. Unsupported projects expose no misleading “add to build” operation.
4. Explicit add shows the provider-owned destination and reports unchanged/added/failure.
5. Navigation and refresh perform no membership writes or build execution.

## Dependencies
Required: delivered project identity and provider-command seam; no new ticket blocker.
Related: none; plain-directory adoption can be delivered without membership editing.

## Estimate rationale
21 points cover exploration and one bounded provider membership operation.
Exclude an editor, general project-file management and integration into every build system.

## Assumptions and decisions needed
Default: read-only explorer plus explicit add-existing-file where advertised.
TBD: first provider/file-list format, symlink traversal policy and refresh limits.
If no real project-owned list is selected, narrow the first delivery before implementation.

## References
- [Manifest fields](../../../project_integration/manifest.ml)
- [Dune workspace inspection](../../../adapters/dune_adapter.ml)
- [Project setup ownership](../project_setup.md)
