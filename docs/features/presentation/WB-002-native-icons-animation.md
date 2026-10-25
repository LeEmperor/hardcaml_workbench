---
id: WB-002
title: Further native icons and animation
category: presentation
feature_sets: [FS5]
status: closed
kind: enhancement
priority: P3
severity: n/a
requested_size: Ticket
size: S
points: 5
confidence: medium
estimate_scope: incremental
origin: owner-intake
tags: [native, indicators, animation]
depends_on: []
related: [WB-001, WB-007, WB-058, WB-059]
---

# WB-002 — Further native icons and animation

## Request
Add **more** useful icons and animation using native Bonsai Term capabilities.
Requested size: **Ticket**; this is incremental expansion of delivered indicators.

## Current baseline
The existing implementation delivers native Dot/Line spinners and semantic
icons for lifecycle, readiness, pins, artifacts, logs and simulation context.
Unicode/ASCII/Off controls, persistence and deterministic capture fallbacks exist.
The installed spinner API is known; a broad imported icon catalog is not assumed.

## Scope
- Review remaining high-value status/context locations and select a bounded set.
- Reuse the shared indicator policy and native components where appropriate.
- Keep text labels, semantic distinctions and width-tested ASCII/Off alternatives.

## Out of scope
Rebuilding native animation, introducing decorative title dots, or importing an
unverified general icon API. Nerd Font support is a separate optional feature.

## Acceptance criteria
- [x] Agree and document the additional locations and intended semantic value.
- [x] Existing and new indicators distinguish activity, completion and verdicts.
- [x] Animation follows real typed activity and stops for terminal states.
- [x] Unicode/ASCII/Off preserve labels, layout and keyboard actions.
- [x] Presentation changes and animation cause no provider execution or extra polling.

## Delivery — 2026-10-25

The owner approved a bounded expansion across evidence freshness, context
relationships and hierarchy navigation. Implemented and automatically verified;
owner acceptance and the deferred hierarchy review are recorded below.

- **Evidence:** typed freshness markers distinguish validated, cached/unverified,
  source-unavailable and refresh-failed summaries in Session and host evidence
  displays. Inspector and Timing observation markers animate only for a scoped,
  active typed evidence read. Validation is evidence freshness, not run acceptance;
  existing labels and verdicts remain authoritative.
- **Contexts:** Session and the global context header distinguish linked and
  independent contexts; existing pin badges are reused without duplication.
  Missing Session context has an explicit unavailable marker.
- **Hierarchy:** expanded/collapsed branches and leaves use shared markers. A
  childless root has a top marker; expandable roots retain their expansion marker
  and root label. Off leaves a blank marker column so selection and indentation
  stay in place. Navigation and source evidence are unchanged.
- **Policy:** all additions follow Appearance Icons Unicode / ASCII / Off. Static
  semantic markers do not animate. Rendering changes add no provider requests,
  polling or execution paths; native animation reuses existing shared frames.

Verification:

- `scripts/with-switch.sh dune build -j8 @all @runtest` passed on the combined tree.
- `scripts/with-switch.sh ocamlformat --check terminal/indicator.ml terminal/indicator.mli terminal/hierarchy_view.ml terminal/hierarchy_view.mli terminal/host_view.ml terminal/overview_tiles.ml terminal/evidence_session_test.ml` passed.
- Focused tests cover one-cell glyphs, all icon modes, narrow rendering, context
  labels, pin duplication, hierarchy navigation and typed activity fencing for
  terminal/cache-only/unreported/obsolete requests.
- No new live terminal/font matrix acceptance is claimed by these automated checks.

### Owner review and follow-up — 2026-10-25

The owner confirmed the context marker and observed refresh animation and cached
evidence markers in Timing inspection. Their Overview screenshot exposed a missed
rendering path: stock stage cards are rendered by `overview_summary.ml`. That path
now decorates Evidence rows for synthesis, placement, routing, checks and finalization,
and the Timing Evidence/compact Goal freshness display. Regression tests render the
actual stock cards in all icon modes and freshness states rather than only helpers.

Hierarchy visual acceptance is blocked for the real FIFO example by its absent
generic hardware-driver integration, not missing icon rendering. The unavailable
guidance now explains this prerequisite. Owner acceptance of the Overview correction
and hierarchy markers was pending at that review.

### Owner acceptance and closure — 2026-10-25

The owner confirmed the Overview correction and context indicators work, and
authorized independent closure of the icon ticket with remaining hierarchy-specific
review deferred to [WB-007](../project/WB-007-hierarchy-tile.md). WB-002 is closed.
Timing's cached/unverified text describes retained evidence freshness and is not an
outstanding icon defect. Hierarchy markers are implemented and automatically tested;
real-example integration and their owner visual review remain tracked under WB-007
and do not block this closure. WB-001 checklist alignment was already closed.

## Dependencies
Required: none; native integration and shared semantic indicators are delivered.
Related: [WB-001](WB-001-checklist-column-alignment.md) shares cell budgeting;
[WB-058](WB-058-nerd-font-mode.md) is an optional alternate glyph mode;
[WB-059](WB-059-terminal-glyph-validation.md) broadens compatibility evidence.

## Estimate rationale
Five incremental points cover a bounded expansion and integration verification,
excluding the already delivered spinner and indicator foundations.

## Assumptions and decisions needed
Owner review selects useful additions. Dense packing, lowercase titles and no
decorative dots are current preferences, subject to later explicit review.

## References
- [Implemented native indicator plan](../../terminal_indicators_plan.md)
- [Appearance controls](../../appearance_presets.md)
- [Indicator implementation](../../../terminal/indicator.ml)
