# Feature ticket catalog

Updated 2026-10-17 from the owner's feature intake and current delivery records.
**Cataloging a ticket does not authorize implementation.** Delivery is claimed only
where its status and linked acceptance record explicitly say so.
FS0/FS1 delivered scope and the accepted FS2 milestone remain closed. FS3 adoption
and native icons/spinners are delivered foundations for several enhancements below.

**Current delivery update:** WB-032 catalog and WB-034 genuine FIFO adoption are
implemented and automatically verified. WB-063's cooperative Testing implementation
is verified, with its explicit owner visual-review gate still pending. See
[the Testing guide](../testing_workspace.md). Their original points record estimates,
not additional remaining implementation effort.

**2026-10-18:** WB-028's bounded embedded VCD viewer is implemented and automatically
verified (1,773 acceptance checks, including exact cursor/ruler rendering and a dedicated Waveforms workspace with
Session, Signals, Waves, VCD picker and Logs tiles).
Its status is partial for lazy loading and
four-state graphical rendering; [controls and evidence](../testing_workspace.md#embedded-waveform-viewer).

## How this directory works

- **WB-NNN** identifies one actionable feature/defect ticket; filenames and category
  placement do not change its identity. Each ticket has its own Markdown file.
- **F01–F12** remain architectural area specifications in this directory's root.
  They describe contracts and long-term requirements, not duplicate work items.
- **FS0–FS5** remain product themes; tickets may span several sets. **M0–M5/V1**
  remain delivery phases in the [construction plan](../construction_phase_plan.md).
- The 62 submitted entries become **61 distinct tickets**: both requests for more
  persistent per-tile presentation settings map to **WB-048**. Original labels and
  intent are retained in each ticket's Request section.
- **WB-062–065** carry forward four existing followups (uncertain simulation
  submissions, Testing-workspace usability, generic job detail and ASIC lifecycle
  coverage). They are explicitly marked existing-backlog, not new owner requests.
- [Dependency map](dependencies.md) explains cross-category sequencing. Required
  dependencies differ from related work; an existing delivered foundation is not
  an open blocker. Remaining older deferred ideas stay in [backlog](../backlog/README.md).
- [Intake crosswalk](intake.md) maps every submitted entry, including the duplicate,
  to its canonical ticket and preserves the original size/classification labels.

## Metadata and estimation conventions

All estimates/priorities are **provisional for owner review**. Story points measure
relative implementation, integration, testing and uncertainty—not elapsed days or
CPU hours. Re-estimate after a spike or material scope decision. A real physical
flow's wall-clock duration is a test-cost consideration, not a story-point formula.

| Field | Convention |
| --- | --- |
| Status | `proposed`, `needs-design`, `needs-triage`, `partial`, or `delivered` |
| Kind | `feature`, `enhancement`, `defect`, `research`, `epic`, or `validation` |
| Priority | P0 emergency (none assigned); P1 near-term unblocker/foundation; P2 valuable followup; P3 exploratory/later |
| Severity | S1 critical loss/outage; S2 substantial workflow impairment; S3 cosmetic/usability defect; `n/a` for non-defects. Reported defects remain unconfirmed until reproduced. |
| Requested size | Preserve the owner's label verbatim where supplied; `Ticket` is not an estimate. Unlabelled bullets use `Unspecified`. |
| Estimated size | XS = 1–2; S = 3–5; M = 8–13; L = 21–34; Mega = 55+ points |
| Points | Fibonacci-like 1, 2, 3, 5, 8, 13, 21, 34, 55, 89; current-scope estimate, never a delivery commitment |
| Confidence | High: narrow known seam; medium: known architecture with integration work; low: contract/research/product decisions remain |
| Estimate scope | `incremental`: work beyond delivered foundations; `standalone-epic`: bounded initial outcome, excluding separately ticketed prerequisites |
| Dependencies | `depends_on`: genuine additional prerequisite tickets; `related`: optional enablers, overlaps or shared foundations. Required relationships must be acyclic. |

Mega-ticket points cover only their described first coherent delivery, excluding
other WB tickets. Suggested phases inside them are **included**, not additional
estimates. If child tickets are created later, replace the parent's direct estimate
with a rollup or subtract the extracted work; never count both. Catalog totals are
not a schedule and are deliberately omitted. Continuous polish tickets estimate
one bounded review/implementation cycle, not endless future improvements.

Tickets use consistent YAML front matter: `id`, `title`, `category`, `feature_sets`,
`status`, `kind`, `priority`, `severity`, `requested_size`, `size`, `points`,
`confidence`, `estimate_scope`, `origin`, `tags`, `depends_on`, and `related`.
Body sections: Request; Current baseline; Scope; Out of scope; Acceptance criteria;
Dependencies (with rationale and links); Estimate rationale; Assumptions and decisions
needed; References. A dependency needs a reason, not just a list of IDs.

## Presentation and interaction

| Ticket | Feature | Sets | Priority | Points | Confidence |
| --- | --- | --- | --- | --- | --- |
| [WB-001](presentation/WB-001-checklist-column-alignment.md) | Checklist column alignment | FS5 | P2 | 3 | high |
| [WB-002](presentation/WB-002-native-icons-animation.md) | Further native icons and animation | FS5 | P3 | 5 | medium |
| [WB-019](presentation/WB-019-hideable-controls.md) | Independently hideable window/palette controls | FS5 | P2 | 3 | high |
| [WB-024](presentation/WB-024-context-link-label.md) | Context-link wording and semantic emphasis | FS5 | P2 | 2 | high |
| [WB-048](presentation/WB-048-presentation-persistence.md) | More persistent presentation overrides | FS3, FS5 | P2 | 8 | medium |
| [WB-053](presentation/WB-053-tile-local-tabs.md) | Reusable tile-local tabs | FS5 | P2 | 13 | medium |
| [WB-054](presentation/WB-054-contextual-controls.md) | Contextual actions, breadcrumbs and help | FS5, FS1, FS2 | P2 | 8 | medium |
| [WB-055](presentation/WB-055-source-path-peeks.md) | Lightweight source/path peek overlays | FS5, FS1 | P3 | 13 | medium |
| [WB-056](presentation/WB-056-floating-panes.md) | General floating-pane management | FS5, FS3 | P3 | 34 | low |
| [WB-057](presentation/WB-057-utility-placement.md) | Configurable status/help/navigation placement | FS5, FS3 | P3 | 13 | medium |
| [WB-058](presentation/WB-058-nerd-font-mode.md) | Optional Nerd Font icons with fallbacks | FS5 | P3 | 5 | medium |
| [WB-059](presentation/WB-059-terminal-glyph-validation.md) | Terminal/font/SSH/tmux glyph validation | FS5, FS3 | P2 | 8 | medium |
| [WB-060](presentation/WB-060-comparison-gallery.md) | Richer A–E comparison gallery | FS5 | P3 | 8 | medium |
| [WB-061](presentation/WB-061-aesthetic-refinement.md) | Bounded workspace aesthetic refinement | FS5 | P2 | 13 | low |
| [WB-063](presentation/WB-063-testing-workspace.md) | Testing-workspace investigation redesign | FS2, FS5 | P2 | 21 | medium |

## Workspaces, input and configuration

| Ticket | Feature | Sets | Priority | Points | Confidence |
| --- | --- | --- | --- | --- | --- |
| [WB-013](workspaces/WB-013-mouse-support.md) | Mouse focus, scrolling and actions | FS3, FS5 | P2 | 13 | medium |
| [WB-014](workspaces/WB-014-hotkey-configuration.md) | Hotkey configuration file | FS3, FS5 | P2 | 8 | medium |
| [WB-015](workspaces/WB-015-layout-file-usability.md) | Human-friendly workspace layout files | FS3, FS5 | P1 | 8 | medium |
| [WB-016](workspaces/WB-016-window-configuration.md) | Full window configuration files | FS3 | P2 | 13 | medium |
| [WB-045](workspaces/WB-045-template-picker.md) | TUI template browser/picker | FS3 | P2 | 8 | medium |
| [WB-046](workspaces/WB-046-interactive-layout-editing.md) | Interactive layout editing | FS3, FS5 | P2 | 34 | low |
| [WB-047](workspaces/WB-047-window-attachment.md) | Full window/monitor attachment | FS3 | P2 | 21 | medium |

## Project adoption and design scope

| Ticket | Feature | Sets | Priority | Points | Confidence |
| --- | --- | --- | --- | --- | --- |
| [WB-004](project/WB-004-build-bundle-status.md) | Core build, bundle emission and verification status | FS0, FS1, FS2 | P2 | 13 | medium |
| [WB-007](project/WB-007-hierarchy-tile.md) | Hierarchy tile and selected top visibility | FS1, FS2 | P2 | 13 | medium |
| [WB-008](project/WB-008-leaf-out-of-context.md) | Leaf/IP out-of-context workflows | FS1, FS2 | P2 | 21 | low |
| [WB-010](project/WB-010-progressive-adoption.md) | Useful operation at varying project integration levels | FS0, FS3 | P2 | 13 | medium |
| [WB-017](project/WB-017-project-files.md) | Project file exploration and explicit add-file operations | FS3, FS4 | P3 | 21 | low |
| [WB-039](project/WB-039-simulation-setup.md) | Simulation provider setup assistance | FS2, FS3 | P2 | 8 | medium |
| [WB-049](project/WB-049-config-migration.md) | Configuration-location migration and precedence | FS3 | P2 | 13 | medium |
| [WB-050](project/WB-050-upward-discovery.md) | Upward project discovery | FS3 | P2 | 5 | medium |
| [WB-051](project/WB-051-new-project-creation.md) | Provider-owned new-project creation | FS3 | P3 | 21 | low |
| [WB-052](project/WB-052-adoption-polish.md) | Adoption/help/SSH/tmux workflow polish | FS3, FS5 | P2 | 8 | medium |

## Evidence and hardware investigation

| Ticket | Feature | Sets | Priority | Points | Confidence |
| --- | --- | --- | --- | --- | --- |
| [WB-003](evidence/WB-003-evidence-refresh-activity.md) | Evidence refresh activity and current-operation status | FS1, FS5 | P1 | 5 | medium |
| [WB-006](evidence/WB-006-evidence-timestamps.md) | Stage/report timestamps and age | FS1 | P2 | 8 | medium |
| [WB-009](evidence/WB-009-timing-coherency.md) | Timing workspace availability/coherency investigation | FS1 | P1 | 8 | low |
| [WB-012](evidence/WB-012-run-comparison.md) | Provenance-aware run comparison | FS1, FS2 | P2 | 21 | medium |
| [WB-020](evidence/WB-020-graphical-physical-inspection.md) | Embedded physical/layout/heatmap inspection | FS1, FS5 | P3 | 55 | low |
| [WB-021](evidence/WB-021-source-navigation.md) | Evidence-backed RTL/OCaml source navigation | FS1, FS4 | P2 | 34 | low |
| [WB-022](evidence/WB-022-signal-name-annotations.md) | Provenance-safe generated-net naming annotations | FS1, FS4 | P3 | 21 | low |
| [WB-023](evidence/WB-023-provider-evidence.md) | Additional typed provider evidence | FS1 | P2 | 13 | low |
| [WB-026](evidence/WB-026-power-analysis.md) | Activity/corner-qualified power analysis | FS1 | P3 | 34 | low |

## Verification and simulation

| Ticket | Feature | Sets | Priority | Points | Confidence |
| --- | --- | --- | --- | --- | --- |
| [WB-025](verification/WB-025-formal-verification.md) | Formal verification support | FS2, FS4 | P3 | 89 | low |
| [WB-028](verification/WB-028-waveform-viewer.md) | Embedded waveform viewer | FS2, FS5 | P2 | 34 | low |
| [WB-030](verification/WB-030-seed-parameter-sweeps.md) | Seed sweeps and test-parameter matrices | FS2 | P2 | 21 | medium |
| [WB-032](verification/WB-032-test-catalog.md) | Project test catalog and discovery UI | FS2 | P1 | 13 | medium |
| [WB-034](verification/WB-034-fifo-adapter.md) | Real FIFO structured-test adapter | FS2 | P1 | 13 | medium |
| [WB-035](verification/WB-035-generated-rtl-simulation.md) | Generated-RTL simulation adapters | FS2 | P2 | 21 | low |
| [WB-036](verification/WB-036-gate-level-simulation.md) | Gate-level simulation adapters | FS2, FS1 | P2 | 34 | low |
| [WB-037](verification/WB-037-archived-replay.md) | Archived source/build/tool replay | FS2, FS1 | P3 | 34 | low |
| [WB-038](verification/WB-038-acceptance-bridge.md) | Simulation-to-ASIC acceptance evidence bridge | FS2, FS1 | P3 | 21 | low |
| [WB-062](verification/WB-062-submission-recovery.md) | Uncertain simulation submission/history recovery | FS2 | P2 | 13 | medium |

## Execution, storage and observability

| Ticket | Feature | Sets | Priority | Points | Confidence |
| --- | --- | --- | --- | --- | --- |
| [WB-005](infrastructure/WB-005-process-monitor.md) | BTOP-like owned-process view | FS0, FS2 | P2 | 13 | medium |
| [WB-027](infrastructure/WB-027-performance-measurement.md) | Workbench latency/resource/evidence-loading measurements | FS0, FS3 | P1 | 13 | medium |
| [WB-040](infrastructure/WB-040-trace-streaming.md) | Bounded-memory large-trace streaming | FS2, FS1 | P2 | 13 | medium |
| [WB-041](infrastructure/WB-041-durable-logs.md) | Durable full logs with retention | FS0, FS2 | P2 | 13 | medium |
| [WB-042](infrastructure/WB-042-resource-budgets.md) | Output/storage and aggregate execution budgets | FS0, FS2, FS3 | P1 | 13 | medium |
| [WB-043](infrastructure/WB-043-slow-storage.md) | Slow-storage responsiveness | FS0, FS2 | P2 | 13 | medium |
| [WB-044](infrastructure/WB-044-load-acceptance.md) | Large-regression and multi-client load acceptance | FS2, FS3 | P2 | 13 | medium |
| [WB-064](infrastructure/WB-064-generic-job-detail.md) | Generic selected-job detail and log investigation | FS0, FS2 | P2 | 8 | medium |
| [WB-065](infrastructure/WB-065-asic-lifecycle-coverage.md) | Broader ASIC lifecycle/cancellation race coverage | FS1 | P2 | 13 | medium |

## External providers and clients

| Ticket | Feature | Sets | Priority | Points | Confidence |
| --- | --- | --- | --- | --- | --- |
| [WB-011](integrations/WB-011-vivado.md) | FPGA/Vivado integration | FS4, FS1 | P3 | 34 | low |
| [WB-018](integrations/WB-018-ches-tiles.md) | Ches-hosted Workbench tile projections | FS4 | P3 | 21 | low |
| [WB-029](integrations/WB-029-version-control.md) | Git/Mercurial inspection and explicit operations | FS4, FS3 | P3 | 21 | low |

## Design-space exploration

| Ticket | Feature | Sets | Priority | Points | Confidence |
| --- | --- | --- | --- | --- | --- |
| [WB-031](exploration/WB-031-design-space-sweeper.md) | Performance-engineering design/build sweeper | FS2, FS1, FS4 | P3 | 55 | low |
| [WB-033](exploration/WB-033-quick-harn-playground.md) | Quick-Harn comparative editing playground | FS4, FS2, FS5 | P3 | 89 | low |

## Review priorities, not an implementation commitment

1. Reproduce WB-009 (timing coherency) without launching another physical flow.
2. Confirm small UX intent: WB-001, WB-003, WB-019 and WB-024.
3. Review delivered WB-032/WB-034 and the implemented WB-063 workflow. Remaining
   foundation choices include WB-015 layout-file UX, WB-027 measurements and WB-042
   resource budgets.
4. Decide first supported formats/tools/surfaces for WB-020/021/025/028/031/033
   before treating their estimates as implementation-ready.

Feature specs and historical acceptance remain authoritative about what already
works. The construction plan owns activated implementation and acceptance; this
catalog owns proposed scope, metadata, dependencies and owner-review decisions.
