# Overview titles/content after compression toggle

**Status:** diagnosed, fixed and verified against a private replay of the supplied
state; retained client refreshed. Targeted header recovery controls are below.

## Report and scope

Owner reports that after toggling identifier compression in the real example client,
the Placement and Routing panes lose their titles and show generic finalization text.
The supplied live daemon is `http://127.0.0.1:42179`, selected run
`6f49ed76830e484ca025dc6115ec351a`. Diagnose and correct the actual state/rendering
interaction without resetting the user's workspace or other appearance preferences.

Initial read-only observation: presentation schema 6 records global compression
false and explicit `headers false` for `tile-12` (placement) and `tile-13` (routing).
This establishes the current settings, not their origin. Determine whether the
compression action changes them, or whether header policy improperly changes body
rendering and title behavior. Do not assume user error from saved settings alone.

## Work packages

### Agent A — reproduce and fix

- [x] Capture live workspace/presentation state read-only and reproduce in a private
  daemon/client, preserving exact tile/session identity and settings.
- [x] Trace compression commands, header/title/compact-summary policy and generic
  run fallback; establish the cause of both absent titles and unrelated body text.
- [x] Implement minimal source fix and regressions demonstrating compression does
  not modify unrelated headers/titles/content, including persistence/restart.
- [x] Validate Placement/Routing domain-specific missing states against a Timing-only
  run; no fake finalization or stage metrics.
- [x] Return exact targeted state recovery controls if existing saved overrides need
  correction; preserve all other user preferences.

### Parent — integration and recovery

- [x] Record report, initial state and ownership before source changes.
- [x] Review actual cause, run required integration checks and update ticket evidence.
- [x] Refresh retained binaries without stopping user processes. Repair only confirmed
  erroneous saved presentation state if needed, with backup and race-safe handling,
  or provide precise in-client correction controls.

## Policies

Single-job serialized build/test commands (`-j 1`, numerical worker limits one).
No Git staging/commit/push, no physical EDA, no mutation of retained run evidence,
no production daemon restart. Prefer one implementation agent for this focused
cross-file investigation; parent handles docs, light integration and deployment.
Use actual state plus a deterministic native regression; do not weaken assertions
to accommodate disappearing titles or unrelated body text.

## Evidence

## Established causes

The supplied run and registry were captured at workspace revision 194, session
`3f3e81418a82c8f32e906d7824783fa07a1ff134ac3feda3344d2d8f241b7fa9`.

1. Saved `headers=false` for Placement `tile-12` and Routing `tile-13` suppresses
   their border titles by the existing `show_title = header && title` policy.
   Compression did not change either setting in the private reproduction. The
   available saved state does not establish how or when those overrides originated.
2. Enter activates terminal-result detail mode. Without imported finalization, its
   old fallback discarded available stage observations and showed the generic
   finalization placeholder from the screenshot. A fresh client with the same prefs
   rendered correct compact summaries; header suppression alone did not cause the
   wrong body. The original binary reproduced the exact text after Enter.

`host_view.ml` now preserves typed Placement/Routing stage status, duration, evidence
availability and source context in that reader. Missing stage/domain evidence stays
explicit; no finalization or physical metrics are invented. Compression remains
independent of header/title and detail selection.

## Related precision correction

The screenshot also revealed that Overview Timing's `%g` metric formatting ignored
the previously requested tile decimal setting. Compact and expanded views now use
the existing configurable display precision (default three, choices 0–9), while
counts retain integer style and raw values/goals/provenance stay exact. An expanded
physical Timing detail-path crash found during native verification was corrected
by avoiding redundant summary metadata construction in that mode.

Shared decimal formatting also avoids binary scaling artifacts: `1.001` at three
places remains `1.001`, and `0.29` at two remains `0.29`. Formatting truncates a
shortest round-trip decimal representation without an epsilon. Genuine values below
a boundary still truncate below it; negative near-zero signs are preserved.

The actual captured hold metric was `0.12502899069955042`, so three-place display is
`0.125` and six-place truncation is correctly `0.125028`; the prior `%g` text
`0.125029` was rounded. Raw report/state values were not changed.

## Targeted recovery in the current client

For each blank pane (Placement, then Routing):

1. Focus the pane and press **Esc** to return from detail mode to its compact summary.
2. Open **Space c c** and choose **Toggle focused tile header** once.

The saved Title trait already inherits true; no Title toggle or whole-presentation
reset is needed. This restores the two titles while preserving the user's scheme,
run-selector row count, string/decimal choices and other workspace state.

Restart only the client to load the code fixes. The production daemon/client were
not stopped, and no live preference file was rewritten while the client could save
over it. No provider installation, physical run or state reseed is needed.

### Follow-up border-only report

The owner subsequently supplied run `ae43e03855f04ce49b632a4a5c766207`, whose
Placement/Routing bodies were now correct but whose titles were still absent.
Initial inspection again found those two saved headers false. While preparing a
targeted correction, the file changed; the guarded patch did not apply. Re-reading
confirmed both `tile-12` and `tile-13` now had `headers=true`, with the other settings
preserved. No preference overwrite or backup receipt was made by this follow-up.
The saved settings now request normal border titles; a client still holding older
in-memory values can reload them by restarting only the client.

## Verification and deployment

- Pre-fix actual-state reproduction:
  `/tmp/opencode/overview-compression-uq04y91p/placement-detail.txt`.
- Final actual-state native HTTP/PTY regression:
  `/tmp/opencode/overview-compression-rrmrmrl5/verified.json`.
  Covers all compression scopes, unrelated preferences, title policy, summary/detail,
  restart, missing-domain evidence, actual 3/6-digit Timing metrics and unchanged raw
  analysis. It allocated no provider/domain jobs and preserved source state/preferences.
- Full parent `dune build -j 1 @all @lint` and `dune runtest -j 1`: passed.
- Changed-file formatting and `git diff --check`: passed. Unrelated repository-wide
  formatting baseline remains separate.
- Retained client refresh receipt:
  `hardcaml_asic_example/.dev/workbench-real-demo/receipts/refresh-binaries-83a321a6e4b347c692ab41161e3bcc75/`.

All checks were serialized at one job with numerical worker limits one. No repository
staging, commits or pushes, physical EDA, raw-run mutation or live-process restart.
