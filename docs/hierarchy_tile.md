# Hierarchy tile — controls and acceptance

WB-007 is implemented and automatically verified on 2026-10-21. The tile is opt-in;
existing preset layouts remain unchanged. See the
[implementation plan](hierarchy_tile_plan.md) for ownership and execution policies.

## Use

1. Open the command palette and choose **Add hierarchy tile**.
2. Select the desired project target/configuration and generate RTL through the
   existing generation command if no completed result exists.
3. Focus the tile and press **r**, or choose **Load current hierarchy** in the palette.

| Control | Action |
| --- | --- |
| `j` / `k`, down / up | Move the tile-local instance selection |
| Enter | Expand or collapse the selected instance |
| `i` / **Inspect hierarchy tile node** | Open existing detailed inspection for this artifact and node |
| `r` / **Load current hierarchy** | Load the latest generation for the selected target/configuration |

The root starts expanded. Each tile owns independent navigation over shared typed
evidence. Palette and host-prefix input take precedence over tree controls. Existing
inspector controls remain available, including `h` to close and `u`/`o` to scroll
the detail pane.

## Evidence and selection

The compact view shows the elaborated top, current/historical status, generating
target/configuration and shortened job/artifact identifiers. Detail exposes exact
artifact, job, project, target/configuration, provenance, RTL artifact references,
selected-node ports/widths and metadata.

A tile retains its loaded artifact until an explicit load. Selection changes do
not silently replace it. Freshness is recomputed against the current project,
target/configuration and latest generation; even an older generation of the same
selection becomes historical. `i` always inspects the tile's retained evidence,
not the currently selected job. Navigation is client-local; workspace layout
persistence does not persist the loaded artifact or expanded nodes across restart.

**Tested top / DUT is unknown.** The current simulation/provider contracts do not
supply a test-to-hierarchy association. The elaborated root is not evidence of
what a simulation tested. This tile is project-scoped, not an ASIC run-pinned view.

Loading reads existing evidence. Adding, browsing, hiding and closing tiles do not
launch tools or regenerate RTL. Equivalent concurrent reads are shared with other
tiles and the legacy inspector; retention is bounded to 16 completed results and
16 in-flight artifact reads. Errors can be retried. Request identity/lifetime checks
reject superseded tile loads, removed/retyped consumers and reconnect receipts.

Missing, queued/running, failed, cancelled, unsupported and read-error states give
explicit explanations and retry/generation guidance. An unsuccessful load retains
the prior tree with its freshness and the new load-status explanation.

## Verification

Final normal-tree commands:

```sh
scripts/with-switch.sh dune build -j20
scripts/with-switch.sh dune build -j20 @lint
scripts/with-switch.sh dune runtest -j20
scripts/with-switch.sh ocamlformat --check \
  terminal/hierarchy_view.ml terminal/hierarchy_view.mli \
  terminal/workspace_host.ml terminal/host_view.ml terminal/main.ml
python3 scripts/test-hierarchy-tile.py --self-test
python3 scripts/test-hierarchy-tile.py \
  --daemon _build/default/daemon/main.exe \
  --client _build/default/terminal/main.exe
```

All commands above passed. Agent builds used isolated directories at six jobs each;
normal-tree builds ran only after those jobs stopped.

Final native receipts: **`/tmp/opencode/hierarchy-tile-w1de3jp1/`**, including
`result.json`, binary hashes, HTTP requests/response gates, PTY screens and key logs.
The fixture exercises real native daemon/client transport with synthetic structural
evidence, including:

- Two independent trees, exact-node detail and retained inspector controls.
- One HTTP hierarchy read for equivalent concurrent loads.
- Target/configuration changes and newer same-selection generations.
- Superseded delayed reads and hidden-consumer isolation.
- Missing, unsupported, failed, pending, cancelled and malformed-provider states,
  plus injected malformed HTTP response and retry recovery.
- Explicit unknown DUT, palette routing and 80×24 rendering.
- No implicit generation: 13 explicit fixture generations, 16 fully accounted
  native jobs, 10 hierarchy reads and four response gates.

Pure tests additionally cover a 10,000-node tree, independent immutable navigation,
viewport bounds, malformed-value safety, display sanitization and removal/retyping/
reconnect request fences.

### Verification limits

The global `dune build -j20 @fmt @lint` check reports pre-existing formatting drift
in `backend/asic_service.ml`, `terminal/waveform_probe.ml`,
`terminal/waveform_data.ml` and `terminal/waveform_data.mli`. These files are unchanged
from branch HEAD. Changed OCaml files pass the explicit formatter check; standalone
global lint passes.

Native removal/recreation is not exercised because the public mutation API exposes
hiding rather than removal; pure host tests cover removal/retyping receipt fences.
Daemon restart/project reopen and real physical-tool flows are not claimed by this
fixture. There is no new provider DUT mapping. Owner interactive visual acceptance
is still separate from automated verification. No external-repository edits were
needed.
