# Client reconnect, navigation restoration and retained-state hydration

## Goal

A new terminal connected to an existing daemon should reuse discovered catalogs and
retained reports, restore its last investigation selection, and populate a newly
activated tab without waiting behind the normal polling chain. Opening the UI must
not automatically discover providers or launch tests/flows.

## Diagnosis

Read-only measurements against the existing demo daemon returned Simulation Get in
about 0.5 ms and a 1.89 MB ASIC Get in about 25–30 ms. These exclude OCaml decoding
and rendering, so are not an end-to-end latency claim. Source inspection identifies
serial startup hydration behind Updates and other workspace refreshes, no immediate
tab-activation hydration, no fresh-client Timing view attachment, and no persisted
Testing selection. Testing Get does return an already-discovered catalog; the backend
retains a finished discovery-job ID which can incorrectly keep a fresh view disabled.

## Policy and ownership

No mutative Git operations. Preserve current edits and live daemon state. At most
three implementation agents, each using explicit `-j4`; final checks serial `-j4`.
No physical flow or simulation launch is needed except isolated synthetic test fixtures.
Use existing build caches. Main agent owns this plan and integration review/docs.

## Agent A — navigation sidecar

Own new `terminal/navigation_preferences.ml/.mli` and standalone tests; avoid
`main.ml`, `workspace_host.ml`, `testing_workspace.ml`, `simulation_view.ml`.

Implement a bounded, versioned, atomic sidecar keyed by existing project/environment
preference key. Public record contract (strings are serialized stable IDs):

- `member = { tile : string; kind : string }`
- `artifact = { id : string; sha256 : string option; size : int option }`
- `testing = { attempt : string option; case_id : string option;
  artifact : artifact option }`
- `timing = { stage : string; filter : string; row_id : string option;
  run : string option; source_digest : string option }`
- `workspace = { id : string; members : member list; focus : string option;
  testing : testing option; timing : timing option }`
- `t = { schema_version : int; project_key : string; session : string;
  active : string option; workspaces : workspace list }`
- expose `create ~project_key ~session ~active ~workspaces`,
  `load ~state_directory ~project_key`, `save ~state_directory`, `encode`, `decode`.
  Load absent -> None; malformed files fail visibly without overwriting original.

Persist navigation intent only, not evidence, runtime project IDs, task state or
freshness. Bound file/entry/string sizes, reject duplicates and inconsistent records.
Provide tests for round-trip, missing/corrupt files, identity isolation and atomic save.
Agent C owns `terminal/dune` module registration and production integration; communicate
any necessary API deviation rather than independently editing that shared file.

## Agent B — Testing defaults and retained catalog readiness

Own `backend/simulation_service.ml`, backend simulation tests,
`terminal/simulation_view.ml`, `terminal/testing_workspace.ml` and its interface/tests.

- Stop reporting finished discovery as active; a retained successful catalog is
  available through Get without another Discover, including missing/pruned jobs.
  Preserve failures and in-flight discovery semantics. No new auto-discovery.
- When no saved/user selection exists, choose newest initial history attempt. Once
  detail arrives, choose a sensible case and available VCD (otherwise available
  artifact). Never overwrite an explicit current selection on ordinary polling.
- Expose minimal helpers for Agent C to restore exact attempt/case/artifact intent
  after establishing current project scope, validating artifact digest/size.
- Saved attempts outside the newest page are observed directly, not treated as
  missing. A genuinely unavailable saved selection is explained; do not silently
  substitute unrelated evidence. Explicit first-available fallback may be offered.
- Tests for cold defaults, retained catalog from Get without new job, explicit
  selection stability, staged detail restore and missing/changed artifacts.

## Agent C — startup/tab hydration and restoration integration

Own `terminal/main.ml`, `terminal/workspace_host.ml`, `terminal/dune`, optional pure
hydration helper/tests and Timing attachment helpers. Avoid Agent B's Testing files
and Agent A's sidecar implementation except coordinated API use.

- Start retained workspace/ASIC state hydration without waiting for Updates or
  unrelated waveform/log work. Coalesce requests and preserve transport/project/
  registry/selection fences. Publish local tab switch before awaiting requests.
- Numeric and command switches share immediate retained-data attachment and bounded
  Get hydration. Do not call the broad provider-capable refresh path as a shortcut.
- A fresh existing Timing workspace creates its local view from its exact context run
  and retained index; attach matching published detail locally. Preserve unverified
  labels. Ordinary activation/restoration must not imply Inspect/provider execution.
- Load the navigation sidecar once per identity/replacement, validate registry session
  and workspace membership, establish Testing scope before restoring IDs, then Get /
  Observe exact selected attempt to hydrate case/artifact. No implicit Launch/Rerun.
- Persist active workspace/focus, Testing attempt/case/artifact and Timing stage/filter/
  row. Existing daemon contexts remain authoritative for selected ASIC runs. Existing
  waveform-pin sidecar remains authoritative for dedicated VCD pins; re-arm it after
  reconnect/replacement. Quick-view modal reopening is not required; its selected
  artifact should be retained in Testing so opening it again needs no j/k nudge.
- Never save empty intermediate hydration over saved intent. Late restore cannot
  overwrite newer user input. One-shot consumption avoids repeated poll resets.
- Add focused held-response/scheduling and fresh-process restore tests. Test both tab
  switch routes, identity replacement, inactive tabs and exact old attempt restoration.

## Acceptance

New client + retained daemon catalog/history restores or defaults Testing selections
without Discover or j/k. Existing Timing index renders on activation without Inspect.
Read-only hydration is not blocked by the periodic Updates wait. No additional
execution jobs, automatic provider discovery, or workspace/run-selection mutations
occur. Restored artifact identity is checked before use; stale evidence never becomes
fresh merely because it was restored. Concurrent clients share last-saved local
preferences for the same user/state-directory; independent profiles are future work.

Full build/tests/lint and scoped formatting must pass. Confirm daemon/process restarts
are not performed automatically. Refresh prepared binaries only after checks.

## Progress

Implemented and verified. Broader rendering optimizations and reducing the large
ASIC snapshot payload remain follow-ups; end-to-end latency has not been measured.

### Delivered behavior

- Retained-state hydration starts independently of the Updates long poll. Repeated
  requests join existing hydration instead of continually rescheduling it; queued
  invalidation and dirty preference saves complete at idle boundaries.
- Numeric, palette and sidebar workspace switches use the same immediate activation
  path. Cached data attaches locally, with read-only hydration following asynchronously.
- Fresh Timing views attach existing indexes and matching detail without issuing
  Inspect. Stored row IDs restore only against their original serialized run reference
  and source digest; changed or legacy-unidentified evidence remains unselected with
  an explanation instead of substituting a different path.
- Completed discovery jobs no longer leave a retained simulation catalog falsely
  marked in flight. An existing daemon's catalog is reused by Get; no reconnect
  discovery job is scheduled.
- With no saved choice, Testing selects the newest initial attempt and, after its
  detail arrives, an appropriate case/artifact, preferring an available VCD. Explicit
  choices remain stable across ordinary polls.
- Active workspace/focus, Testing attempt/case/artifact and Timing stage/filter/row
  restore from the navigation sidecar. Saved attempts outside the newest history page
  are observed directly. Missing or changed saved artifacts remain explicitly
  unavailable rather than silently switching evidence.
- Suite-level artifacts are valid without a selected case; artifact identity requires
  an attempt, not a case. Run/source fields on Timing preferences are optional on
  schema-1 decode for compatibility, but absent identity cannot authorize row restore.
- Interrupted preference loads re-arm even on same-daemon transport reconnect. Actual
  workspace/focus/selection changes protect newer user intent; unrelated input does not
  discard pending navigation restoration. Existing dedicated waveform pins re-arm on
  replacement and continue using byte/digest verification.

### Preference ownership and remaining limits

Navigation lives in `navigation-<project-key-digest>.sexp` beside the existing terminal
preferences under `$XDG_STATE_HOME/hardcaml-workbench/terminal/` (or the default user
state directory). The demo launcher supplies its own persistent XDG state directory.
No daemon client identifier or new project namespace is introduced. Two clients using
the same state directory share last-saved navigation; they are not independent profiles.

Simulation discovery is still daemon-memory state. Reopening a client on the same daemon
reuses it; restarting the daemon may still require explicit provider discovery. Saved
UI state is not evidence and does not establish provider readiness. Quick waveform
modal reopening is not persisted; its selected Testing artifact and the dedicated
Waveforms pin are retained through their respective mechanisms.

### Verification

- Full combined `dune build -j4`, `dune runtest -j4`, `dune build -j4 @lint` and
  `git diff --check` passed after audit corrections.
- `scripts/test-client-reconnect.py` runs two real native frontend PTYs against one
  private daemon and a cheap synthetic provider. It verifies active Testing, retained
  catalog, exact attempt/case/artifact including digest/size, and no keyboard input
  for the second client. Reconnect adds zero jobs/discoveries/runs and leaves the
  registry and retained evidence unchanged. Latest evidence:
  `/tmp/opencode/client-reconnect-hdll6oc8/result.json`.
- Production coordinator/host regressions cover held responses, load cancellation,
  save starvation, sidebar activation, suite-level artifacts, and Timing run/digest
  fences. Navigation storage tests cover bounds, corruption preservation and legacy
  records. Fixture clients and daemon are cleaned up.
- The PTY fixture is simulation-only. Timing attachment/restoration is covered by
  production-helper tests, not a Timing PTY scenario. Owner reconnect/tab appearance
  and perceived latency review remain outstanding.

### Attempts-pane tab-switch follow-up

**Owner acceptance — 2026-10-21:** the owner approved the final Testing correction.
Testing reconnect/default-selection behavior and the Attempts-pane fixes are accepted;
WB-063's manual workflow gate is closed. This does not claim an end-to-end Timing
latency measurement or a successful signoff-report review.

Background Get/Observe requests previously inserted and removed a loading row above
retained attempt history, shifting rows and cursor offsets. Loading text now appears
only before the first snapshot; background refresh preserves existing row positions.
Restoring a different attempt also releases busy state from the invalidated request,
and Get-to-Observe continuation checks request generation and transport/project/
workspace identity before proceeding. Scope initialization precedes busy checks.

Held-response regressions cover restoration, paging, coalescing and identity changes.
Full combined build, tests and lint passed at `-j4`, along with formatting/whitespace
checks. These reproduce the row-shift and busy-state defects; no separate live
overlapping-text defect has been established. Owner tab-switch approval is recorded above.
