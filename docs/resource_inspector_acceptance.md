# PT.6 C — resource inspector acceptance

## Coordinator deployment note — after final acceptance

The final receipts below preserve the test-time unchanged application configuration.
After acceptance, the owner explicitly approved upgrading only the example's
`provider_executable` to generation `97b85a9e25e24615b758b97b21ca9697`; the coordinator
applied it and read the actual SRAM index successfully. All generation pointers and
other settings remain unchanged. This does not rewrite C's receipts. The matching
default app binaries are built; user restart/visual verification remains manual.
See [operating instructions](resource_inspector.md).

## Current result (2026-10-28)

**Final C acceptance passed against `PT6-A-contract-r3` and B's final freeze. Ready
for coordinator application-provider approval.** No application configuration or
provider selection was changed. The initial generation and all current pointers,
including the dedicated PT6 `current`, remain intact.

Final closure: example `acceptance/resource-inspector/closeout-final-02.json`.
It verifies the frozen r3 source hashes, complete matching WB source inventory,
all19 installed executables, eight exact actual source IDs/provider identities/
digests, five retained timing-screen assertions, all276 historical/333 augmented
bytes, and3648 previously frozen receipt files. ASIC source still matches the final
captured snapshot after the full default suite.

| Final route | Result | Receipt/evidence |
| --- | --- | --- |
| Private nonpublishing provider capture | passed, six jobs | example `capture-final/receipt.json` |
| Real installed public bridge | **533 checks passed** | example `public-final-01/result.json` |
| Actual retained SRAM native HTTP+PTY | **52 checks passed** | example `actual-final-03/result.json` |
| Synthetic final-schema HTTP+PTY/correction cases | **70 checks passed** | `/tmp/opencode/resource-inspector-http-lfieyui4/result.json` |
| Forced full WB `@runtest @all @lint` + matching binaries | exit0, **39.304s** | example `wb-broad-final/receipt.json` |
| Core unified native fresh-prefix | **99/99**,109.892s | example `wb-unified-final/receipt.json` |
| Saved explicit `Custom resources` + new builtin coexistence | **17/17**,5.125s | example `wb-saved-layout-final/receipt.json` |
| Full default ASIC `dune runtest -j6 --force` | exit0, **564.606s** | example `asic-full-final-01/receipt.json` |

Example paths in this table are under `acceptance/resource-inspector/`. Counts are
per-route assertions rather than additive feature-suite counts. The full ASIC run
finished on its first attempt with a2400s caller budget; no interruption/resume or
cached-only rerun was used. Its default resource-inspection group reports51 checks;
A's retained-input77-check focused run remains separate. Full final WB/unified ran
after the product corrections; the earlier83-check checklist/72-check layout runs
remain historical receipts and were not redundantly repeated on this final pair.

### Final capture and binary identities

Final immutable generation:

```text
.dev/asic-pt6/generations/97b85a9e25e24615b758b97b21ca9697
```

| Identity | SHA-256 |
| --- | --- |
| Captured ASIC source snapshot |`304dee9cb923e57a1e2aaeadb39cafcacff91a8c35e0b32e8a6185d6a90f9b4a`|
| Installed resource-inspection companion |`7a61c319d9d3073f3e9217cb57ef89e7002b80b19c9d18d9ab1727f74d5ef080`|
| Installed dispatcher |`d31fee3dca0d6c90f31b8dd269b630412135fdfb8e8d68f46ecb5e761f19579a`|
| WB daemon |`d8f08e4de5c19aaa764566d4c9894b2bb7c94b534151cff7b16a0cdd940e4a4c`|
| WB terminal |`ae9373490327e0ea0555798c7f1f7884e27a4e9abe5470d5b0530e1a5b9edae2`|
| Preset exporter |`2070b02af86cfda06f817c52db4557f412021fe8e6310a6876f47c7e5d92d7a7`|
| Workspace CLI |`4e7b3abb3efd060847116a20238f0140a090c6ff838b2052a297c3b43853ef17`|
| Setup |`0595d8e27c1915b9c12a176a6e158ae917e3a9a6aa960d8a6ad28c313ff9cce0`|

The dispatcher matches the initial capture while the companion changed. Final
receipts bind all19 companions and captured source bytes. `capture_provider.py
--preserve-current` builds/installs/probes with explicit six-job limits but suppresses
only publication of its new private current selection. It retains the existing
symlink object/target/timestamps and returns the immutable generation directly.
No activation was applied to the user shell or shared opam installation.

### Final independent correction coverage

* **R1 exit/verdict enforcement:** synthetic native requests reject exit1/pass and
  exit0/fail for index, detail, catalog and byte queries. Prior admitted indexes
  remain intact. Genuine CLI1/fail index/catalog/bytes are usable; the actual installed
  failed diagnostic also supplies readable geometry detail through HTTP and PTY.
* **R2 committed cache repair:** ordinary persisted provider-metadata alteration
  rejects the cache and publishes its error. An explicit successful read/replacement
  clears that live corruption diagnostic and restores the exact admitted index.
* **B retry:** a real PTY refresh fails, then succeeds using the same operation key;
  current successful facts display with no old failure. The guarded old-target reply
  still completes only in its own source after client navigation changes target.
* **Availability/classification:** available-zero, unavailable with reason, and old
  missing-field Unknown are independently asserted in HTTP and PTY. Old JSON remains
  Cached_unverified. Final real quantities carry provider-owned Derived/Observed/
  Estimate classifications; synthesis library area is Estimate. Unknown and even
  final_physical Estimate comparisons receive no measured delta. Missing estimate
  values show `missing-estimate-source` before the classification guard.
* **Truncation:** table and captured comparison disclose TRUNCATED while source
  validation stays separate. Compact truncation and exhaustive callback interleavings
  remain B's focused coverage rather than being counted as C native assertions.
* **Saved Custom resources:** a version1 explicit `Custom resources` definition is
  saved/reopened with independent context, geometry and pin intact. Explicit new
  builtin creation coexists without reinterpreting/renaming the custom key, resetting
  its definition/mappings, or creating duplicate workspaces.
* **Actual sources:** program stock macro, exact instance, distinct synthesis/final
  retention,28127.104µm² footprint,4793.6448µm² nonspacer sum,902417.2416µm² gross core,
 186 sampled paths/372 electrical points, precise native path fields/bytes and separate
  fast analysis/model temperatures remain verified. Original physical-p4 has no timing
  links. The emitted FIFO/flop/fallback bundles remain separate exact sources.

The actual source's evidence digest is still
`08d2adf094fc8fd1b157eed71929bdb3ee292e8e81316e27f54b938ba3926417`.
Its private WB source ID is
`fdbc736b3866d8e9b5dea60dbad0c68476bb7e6e5f195fa3839aa588158f5a22`;
the complete eight-source ID/provider/digest table is in `closeout-final-02.json`.
These are run-specific/private-project identities, not project-latest aliases.

### Final attempts, limits and approval boundary

`actual-final-01` retained a stale C filter-text expectation after B made empty-filter
wording availability-aware. `actual-final-02` retained C's attempt to inspect a merely
registered reference before read-only Observe. Investigation also corrected C's
assumption that the original FIFO had no inventory: its own bound methodology proves
available-empty. Final acceptance Observe-binds the exact historical execution,
verifies that own methodology/build association and shows its genuine zero inventory.
Unavailable inventory is separately exercised by explicit synthetic fixtures. Both
failed attempts remain unchanged, with no product workaround or invented SRAM run.

The SRAM is always an explicit retained coarse source. Only the genuine historical
FIFO allocation is registered for the independent run-pin test. Semantic-negative
copies remain labeled disposable diagnostic evidence, not new executions. All
build/test processes were bounded to C's six-job allocation and required shared locks;
no C builds overlapped each other. Only directly owned private native daemons/clients
were used. No EDA, user-daemon action, mutative Git, Protemu or A/B source edit occurred.

Remaining interpretation limits are unchanged: sampled/non-exhaustive timing,
electrical compliance not_assessed, no timed SRAM/IR-EM/resource-power/flop-ownership
qualification or new named SRAM execution. Captured development-byte identity is not
historical producer authentication or a clean-source stamp. C's live retries cover
important outcomes; exhaustive poll/receipt interleavings remain B's focused suite.

**Coordinator readiness:** approve the application provider path explicitly before
switching from the unchanged PT.5 `dd1ec9002cdc40f2936488cedd9eb0fe` selection to
`.../.dev/asic-pt6/generations/97b85a9e25e24615b758b97b21ca9697/bin/hardcaml-asic-flow`.
After approval, use the matching WB daemon/client above and **Resources: Import
retained resource evidence** with the exact augmented capture directory. C has left
the app and all provider pointers unchanged.

## Initial acceptance and review follow-up history

**Initial C acceptance passed against the captured A implementation and compiled B UI.**
At this stage independent review/source freeze was pending. No ASIC or
Workbench product-source workaround was made by C.

Paths in the receipt table are relative to `hardcaml_asic_example`, except `/tmp`:

| Route | Receipt | Result |
| --- | --- | --- |
| Private provider capture, six jobs | `acceptance/resource-inspector/capture-01/receipt.json` | Captured; protected state unchanged |
| Real installed public bridge | `acceptance/resource-inspector/public-04/result.json` | **528 checks passed** |
| Actual retained bridge, native HTTP + real PTY | `acceptance/resource-inspector/pty-05/result.json` | **46 checks passed** |
| Synthetic native HTTP + real late-reply PTY | `/tmp/opencode/resource-inspector-http-bvtahmmx/result.json` | **45 checks passed** |
| Source/receipt/protection closeout | `acceptance/resource-inspector/closeout-02.json` | `initial_acceptance_passed`; moving ASIC bytes match captured source; five additional retained-screen replay assertions |
| WB broad/control/layout follow-up | `acceptance/resource-inspector/wb-regressions-closeout-01.json` | Forced full build/test/lint plus unified99, checklist83, layout72 and saved-layout16 passed |

Counts are assertions within each route, not independent feature-suite test counts.
Public-only receipt status includes `ui_pending` because that route itself never
starts a terminal; `pty-05` supplies the actual UI evidence. Frozen tested scripts,
raw command/provider/HTTP bytes, PTY screens/ANSI/keys and mutation hashes are retained.

Captured generation:
`.dev/asic-pt6/generations/c6791625316c496e922b5fd1d55a741c`.
Source SHA-256: `74ce1ade4fbf30eb0306a50674cb354326a8ec5e5e3b1ae0a6b40e7ffb485bb6`.
New bridge companion SHA-256:
`5229cdec5dce3f9de95cd27d80ca68255be43f6c1398186d9342e2b085302de6`.
All **19 installed dispatcher/companion hashes** and exact captured source-file hashes
are recorded. Dispatcher-only identity is not used as implementation proof.

Matching tested daemon SHA-256:
`690141b019534d597fc0974ca11f2ebd7a26e1d0ec746aa777a22de6cb5c7cc2`.
Client SHA-256: `6042badca308364f98d391ec556c5f4ae567f05ebfbad624a436fc67ccbab25e`.

The **276 historical files**, **333 augmented files**, app/config bytes and every
pre-existing current-pointer target/timestamp stayed unchanged. Only the expressly
authorized new PT6 store gained a current pointer. Application provider remains the
PT.5 `dd1ec9002cdc40f2936488cedd9eb0fe` generation. Private capture builds used explicit
six jobs; Workbench daemon/client builds used the PT6 lock and explicit `-j6`.
Only directly owned private daemons/clients were launched. No EDA, mutative Git,
user-daemon action, Protemu work or A/B product-source edit occurred.

### Workbench broad and native regressions (review in progress)

The requested WB-only follow-up passed on the **same daemon/client bytes** as the
initial inspector acceptance. All five recorded binary identities and the product
source inventory were identical across the regression phases. No new provider capture
or ASIC broad suite was run; final capture remains deferred until review corrections
are frozen.

| Check | Outcome | Duration | Receipt directory under example `acceptance/resource-inspector/` |
| --- | --- | --- | --- |
| Forced `@runtest @all @lint`, explicit matching native targets | exit0 |40.707s|`wb-broad-01`|
| Core unified fresh-prefix native HTTP+PTY |**99/99**|109.525s|`wb-unified-01`|
| Complete checklist native HTTP+PTY |**83/83**|152.823s|`wb-checklist-01`|
| Default-layout restoration, including Resources roundtrip |**72/72**|75.661s|`wb-layout-04`|
| Saved custom layout + explicit Resources builtin |**16/16**|5.175s|`wb-saved-layout-01`|

The broad command was:

```sh
flock /tmp/opencode/workbench-pt6-build.lock scripts/with-switch.sh \
  dune build -j6 --force @runtest @all @lint \
  _build/default/daemon/main.exe _build/default/terminal/main.exe \
  _build/default/terminal/workspaces/export_presets.exe \
  _build/default/workspace_cli/main.exe _build/default/setup/main.exe
```

The receipt retains these exact argv spellings and command output. Each native
suite also held the shared PT6 lock. Unified/checklist's nested **private fixture** builds use explicit `-j6`
and their existing fresh-prefix lock inside that outer PT6 lock. Caller budgets were
1800s for broad,1260s for unified/checklist and900s for layout, with normal owned
fixture cleanup. No user endpoint or producer was contacted.

Native saved-layout evidence verifies a custom-only saved session is **not reset or
silently augmented** with Resources on reconnect. Explicit **Inspect resources**
creates exactly one canonical builtin while retaining every old workspace/tile,
geometry, independent context, pin and authored mapping. Repeated open is idempotent;
daemon/client restart preserves the entire resulting registry. This metadata-only
fixture contains no SRAM or ASIC provider. Its synthetic pin is solely a layout
witness, never an SRAM run/observation.

The older default-layout harness needed C-only readiness/oracle corrections:
`wb-layout-01` assumed the first interactive frame completed asynchronous default
bootstrap. `wb-layout-02` demanded both active and inactive workspace labels in a
bounded tab bar after the five-starter layout plus roundtrips. `wb-layout-03` then
exposed that the active label can be clipped from the footer at120×40, although it
is present in the selected top tab. The corrected oracle checks actual top-row
workspace labels and active scope in either selected tab or footer, retaining all
pane-position/viewport/CAS/preservation assertions. All failed receipts remain
unchanged. Resources was added to the native restore/export/import matrix.
**No A/B product defect or source fix was required.**

Additional matching binary SHA-256:

| Binary | SHA-256 |
| --- | --- |
| Preset exporter |`4dec027edf561a8c805698c153d72cff479875ab89078e7b03ef1c7bd2c50e28`|
| Workspace CLI |`9f7ac32b75690ff96fb220a166431617a6cf1e3a34b4699a4fa86d8112820f48`|
| Setup |`c240a7ca00f0c3ef0ac150f578afbc0fca10e774933ac512ad43a8e3870460c0`|

`scripts/run-resource-inspector-regressions.py` records command stdout/stderr,
timeouts, exact binary/source hashes and before/after protected inventories.
`scripts/test-resource-inspector-saved-layout.py` owns the targeted native saved
session check. Example `record_wb_regressions.py` source/hash-verifies and closes
all passing receipts and native artifact bytes without rerunning tests. The
regression closeout again verifies all276 historical files,333 augmented files,
app bytes and every existing provider-pointer target/timestamp unchanged.

### Retained failed attempts and harness corrections

* The first preparation assertion counted all current SRAM files (361) rather than
  the original capture's exact 276-file historical inventory. It failed before fixture
  writes. The corrected verifier checks original hashes, not a replacement baseline.
* Synthetic HTTP `rboke0ew` exposed a C fixture missing the final page `verdict` field.
  `z9k4y1z2` expected a failed old-page operation although backend publication is
  serialized: the delayed page can complete before queued refresh clears it. Final
  tests verify settled operation plus no stale publication, and separately exercise
  a genuinely delayed old-target reply during actual client navigation.
* `public-01` expected path dictionaries to exclude newly added coverage fields.
  The corrected check preserves every original field while accepting added qualification.
  `public-02` hit the outer tool's 120-second deadline; it is **not a pass**. `public-03`
  incorrectly required JSON stdout on CLI2 rejection, which correctly used stderr.
  `public-04` passed with a 600-second caller budget.
* `http-01` compared a content-addressed FIFO symlink spelling to the canonical target;
  corrected target matching uses real paths. `http-02` passed.
* `pty-01` required a full prompt suffix clipped by the bounded form; `pty-02` searched
  one geometry page for values from another and demanded a decimal spelling absent
  from the full-precision JSON. Scoped index scalars provide the intended formatted
  values. `pty-03` passed initial UI checks; `pty-04` used C's wrong `Pinned` variant
  instead of public `Pin_run`. `pty-05` passed extended compare/pin/restart checks.

All these attempts remain retained and are hashed by closeout; none is relabeled a pass.

## Owned files and modes

* `scripts/test-resource-inspector.py`
  * `--prepare`: exclusive creation of public evidence projections and hash manifest.
  * `--verify`: read-only source/fixture/protected-state and provider-companion checks.
  * `--smoke`: private synthetic provider cases, no daemon/client.
  * `--http --daemon ABS`: native HTTP backend integration without requiring a client.
  * Add `--pty --client ABS` for the actual client late-old-target navigation race.
* `scripts/fixtures/resource-inspector/`: public evidence projections, emitted
  flop/fallback manifests, raw byte spans, frozen source hashes and synthetic provider.
* `scripts/test-resource-inspector-retained.py`
  * `--verify-inputs`: read-only input precheck.
  * `--public --provider ABS`: installed real bridge CLI route, including full timing/
    electrical/catalog pagination and independent source-byte comparisons.
  * `--http --provider ABS --daemon ABS`: real bridge through a strict read-only relay
    and private configuration root. Add `--pty --client ABS` for actual Resources UI.
* Example `acceptance/resource-inspector/capture_provider.py` and `record_closeout.py`
  own capture/build receipts and read-only closure recording.

Default script invocations require an explicit mode and exit 2 otherwise. Existing fixtures are not overwritten
by preparation. The fixture projections are not strict new evidence assertions:
timing/electrical arrays are deliberately bounded with original counts and an explicit
projection label. Full immutable schema-2 source bytes remain in the example checkout.
Workbench does not consume these projections as real-run evidence.

## Actual retained source identities

Paths in this section are relative to `hardcaml_asic_example`.

* Augmented actual source: `acceptance/resource-measurements/accepted-live-01/run`.
  Original source: `acceptance/sram/physical-p4`.
* Original execution: `_flow_results/sram-physical/runs/20261025T034710180883Z_be961b2c`.
* Run ID: `be961b2c95f74c81ad6af81ca4d2b269`.
* Build: `fa38d9064dffdf2ec1578c79c2e8890eba81bf704af460e85fcc6031b707d53c`.
* Final public schema-2 output:
  `acceptance/resource-measurements/installed-final/evidence-50.json`, SHA-256
  `7b340a63a477a28d9f4b75277a2dbdb3367bea9e520abb213753402fed557156`.
* Original snapshot output: `installed-final/evidence-46.json`, SHA-256
  `1f680ee14eb417335d21d98be27b7f783bceeda3000c84a8edba9d076d7bb376`.
* Frozen PT.5b generation: `.dev/asic-pt5b/generations/4848a66eeda54751b12d645ee9bcd5c4`.
  Captured source SHA-256:
  `03b13eb7dd2b2918594754c19b41cbc5fe5042f309a9f2f91eae221b6aed4f4f`.
  Native old resources-inspection companion SHA-256:
  `84e2c061cf9aa45ee1fc2c232481ab0268a6555d8196f4340cbb13a8ee167ac9`.

The old PT.5b companion is an input identity, **not the new bridge**. Real bridge
acceptance requires the new `hardcaml-asic-experimental-resource-inspect` companion
and the separately advertised `resource_inspection1` capability. Its runner records
all installed `hardcaml-asic*` binaries, not only the unchanged dispatcher. These local
captured-byte hashes are not historical producer authentication or a clean-source stamp.

The exact historical failed-verdict source is
`acceptance/resource-measurements/installed-final/000.stdout`, SHA-256
`88a447d954a137268cb23ea4637151eb1a96fdf7b10684c7a3c179220250f2c0`.
It came from a disposable semantic-negative test, not an actual failed SRAM execution.
Original command/exit/test attribution remains in `failed-evidence.json`.

## Oracles and remaining acceptance matrix

| Requirement | Prepared evidence / status |
| --- | --- |
| `program`, exact 256×16 contract, stock macro and `hc_resource_7_program` | Actual public/HTTP facts and PTY table/detail passed; separate synthesis/final matched |
| Macro footprint28127.104µm²; nonspacer4793.6448; gross core902417.2416 | Public/native oracles and actual rendered geometry/scoped scalars passed |
| Sampled186 paths/372 points | Full public paging passed; actual HTTP and PTY counts/detail pages passed |
| Slow max11.246561ns/slew0.067838ns/load0.004815pF; fast min0.223533ns/slew0.167545ns/absent Cap | Every original path field source-compared; exact actual HTTP rows and PTY slack/slew reached through paging/scrolling |
| Fast analysis−40°C / SRAM model−55°C, roles, compliance not_assessed | Full path values preserved; sampled/not-assessed qualifications visible; closeout independently replays actual PTY screens for both labels,0.004815 load,null load and external-model-not-read qualifier |
| Original vs augmented timing | Original unavailable, augmented sampled; actual public/HTTP/PTY passed |
| Separate synthesis175 std cells+macro /30309.8272µm² | Public estimate and separate actual source import passed; no source borrowing |
| Empty FIFO bundle | Real prior `213b276e…` emitted bundle passed member verification via installed provider; HTTP/PTY empty/not_evaluated |
| Explicit flops/fallback | Real retained emitted bundles passed installed bridge/HTTP/PTY; unavailable realization stays explicit |
| Readable failed verdict | Disposable bound-LEF semantic-negative copy yields installed CLI1; HTTP keeps Validated source plus failed verdict/detail; PTY shows failure |
| Corrupt/malformed/stale/unsupported/budgets | Synthetic HTTP rejects malformed/oversize/4097-row/64KiB detail, unauthorized IDs and request budgets; stale actual-source requests rejected before provider read |
| Table → detail → source bytes | Actual76-entry catalog hashes match; PTY reaches final catalog page and reads bytes; HTTP/native report span bytes match independent oracle |
| Warm reopen/restart cached-unverified, failed refresh | Provider-free warm index/detail/filter and new terminal process passed; restarted actual PTY shows CACHED UNVERIFIED; failed refresh remains Refresh_failed |
| Delayed response fencing | Real synthetic HTTP+PTY old-target refresh completes with LATE_OLD_SOURCE in its own index, while new explicit target remains displayed; no cross-source publication |
| Compare scopes | Actual augmented/original compatible physical zero delta and actual synthesis/physical incompatible no-delta PTY passed |
| Layout/pins/explicit source preservation | Private zoom/layout and genuine original FIFO `Pin_run` survive restart; explicit SRAM source stays independent of that run pin |
| All workflow/cancelled/named/finalization branches | A's focused suite owns broader lineage coverage; C did not independently repeat every branch |

Numerators are component rectangle sums, denominators gross bounding rectangles;
timing is sampled, electrical compliance unassessed, and reported output load is not
intrinsic macro pin capacitance. Negative timing does not manufacture macro-retention
failure. Unsupported or corrupt evidence must not turn into an empty success.

## Concrete integration route

The frozen API is `Asic.Operation.Resources`, with `Load`, `Detail`, `Artifacts` and
`Read_artifact`. Retained SRAM uses `Target.Coarse_run`, not `Register`. The synthetic
provider implements exactly the documented `resource-inspect TARGET --kind …` command
and paginated queries. No producer command is implemented. Delayed responses capture
their old generation before sleeping, so they are suitable for real fencing tests.

The executed private capture uses six-job captured-source build/install/probe commands.
Source capture uses read-only Git observations through the established dependency
helper. It does not build in the ASIC checkout. Matching Workbench builds used:

```sh
flock /tmp/opencode/workbench-pt6-build.lock scripts/with-switch.sh \
  dune build daemon/main.exe terminal/main.exe -j6
```

Reproduction (new receipt destinations, explicit immutable provider):

```sh
# Matching binaries supplied by coordinator; no build inside the harness.
python3 -B scripts/test-resource-inspector.py --http --pty \
  --daemon /ABS/MATCHING/daemon/main.exe --client /ABS/MATCHING/terminal/main.exe

# After A's completion and an explicitly isolated installed capture:
python3 -B scripts/test-resource-inspector-retained.py --public \
  --provider /ABS/IMMUTABLE/PT6/generation/bin/hardcaml-asic-flow

python3 -B scripts/test-resource-inspector-retained.py --http --pty \
  --daemon /ABS/MATCHING/daemon/main.exe --client /ABS/MATCHING/terminal/main.exe \
  --provider /ABS/IMMUTABLE/PT6/generation/bin/hardcaml-asic-flow
```

HTTP uses private project/config/home/state/results/port and a deny-project executable.
The installed provider relay admits only metadata and bounded bridge reads for exact
source targets, plus the exact historical FIFO observation/report reads needed for
the pin test. It denies producer commands and arbitrary path access; child provider
queries run with no tools in PATH. No SRAM observation stream is manufactured.

The pin test deliberately adopts the **original real FIFO allocation**
`344ac175531e46fcbd021a1d4c79c361`; it does not relabel it SRAM. Its Register result is
asserted against the retained manifest. SRAM imports initially leave runs empty and
remain independently selected after the real FIFO pin. Failed evidence is a clearly
labeled disposable mutation, not a newly executed failed run or new qualification.

The historical groundwork smoke (`resource-inspector-fixture-puf_0ar4`,52 checks) and
18-binary PT5b precheck remain distinct from the 19-binary new bridge acceptance.
All source and executable identities above describe the tested captures, not moving
checkout claims. A later independent-review correction needs a new capture/receipt.

`closeout-01.json` is retained unchanged. `closeout-02.json` adds five assertions over
already retained actual timing-screen bytes, with exact screen hashes. This was
read-only screen replay, not a provider/UI rerun or an increase to the 46 live checks.
