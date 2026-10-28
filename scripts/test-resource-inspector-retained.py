#!/usr/bin/env python3
"""PT6 installed public bridge and private native HTTP/PTY retained-evidence acceptance."""
import argparse
import importlib.util
import json
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location(
    "resource_groundwork", Path(__file__).with_name("test-resource-inspector.py"))
groundwork = importlib.util.module_from_spec(spec)
spec.loader.exec_module(groundwork)

FIFO_BUNDLE = Path(".dev/workbench-real-demo/preparation-results/bundles/213b276e993b344a0077763a45abb940783830c5671e5dea62cbdbfd14573ad6")


def relay(policy_file, argv):
    """Only version and bounded read-only bridge commands reach the installed binary."""
    policy = groundwork.load(policy_file)
    allowed = argv == ["--version", "--json"]
    observation = policy.get("observation", {})
    allowed |= argv == ["observation", "inspect", observation.get("attempt"), "--json"]
    allowed |= (len(argv) == 8 and argv[:3] == ["observation", "read-updates", observation.get("attempt")]
                and argv[3:6] == ["--stream-id", observation.get("stream_id"), "--after"]
                and argv[6].isdigit() and argv[7] == "--json")
    allowed |= argv == ["report", policy.get("execution"), "--json"]
    if argv[:1] == ["resource-inspect"]:
        parser = argparse.ArgumentParser()
        parser.add_argument("command", choices=["resource-inspect"])
        parser.add_argument("target")
        parser.add_argument("--kind", required=True)
        parser.add_argument("--json", action="store_true", required=True)
        parser.add_argument("--query", choices=["detail", "artifacts", "bytes"])
        parser.add_argument("--expected-digest")
        parser.add_argument("--resource-id")
        parser.add_argument("--section")
        parser.add_argument("--artifact-id")
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--limit", type=int, default=16)
        a = parser.parse_args(argv)
        allowed = policy["targets"].get(a.target) == a.kind
        allowed &= a.query is None or bool(re.fullmatch("[0-9a-f]{64}", a.expected_digest or ""))
        allowed &= 0 <= a.offset <= 128 * 1024 * 1024
        allowed &= 1 <= a.limit <= (16384 if a.query == "bytes" else 64)
        if a.query == "detail":
            allowed &= a.resource_id == "program" and a.section in (
                "inventory", "synthesis", "final", "geometry", "timing", "electrical", "provenance")
        if a.query == "bytes":
            allowed &= bool(re.fullmatch("[0-9a-f]{64}", a.artifact_id or ""))
    base = policy_file.parent
    with (base / "provider-calls.jsonl").open("a") as log:
        log.write(json.dumps(dict(argv=argv, allowed=bool(allowed))) + "\n")
    if not allowed or (base / "deny-queries").exists():
        sys.exit("PT6 retained acceptance: query denied; no producer commands allowed")
    stem = base / ("provider-" + str(os.getpid()))
    proc = subprocess.run([policy["provider"], *argv], capture_output=True, timeout=120,
                          env=dict(os.environ, PATH="/nonexistent/pt6-no-tools", TOOLCHAIN="/nonexistent/pt6"))
    stem.with_suffix(".stdout").write_bytes(proc.stdout)
    stem.with_suffix(".stderr").write_bytes(proc.stderr)
    groundwork.write_new(stem.with_suffix(".json"), dict(argv=argv, exit=proc.returncode))
    sys.stdout.buffer.write(proc.stdout)
    sys.stderr.buffer.write(proc.stderr)
    return proc.returncode


def decode_fields(fs0, item):
    result = {}
    for key, value in fs0.field(item, "fields"):
        try:
            result[key] = json.loads(value)
        except ValueError:
            result[key] = value
    return result


def exercise_pty(args, base, session, fs0, targets, check, snapshot, load_case):
    g = groundwork
    dashboard = g.module("resource_pty_dashboard", g.HERE / "test-fs0-dashboard.py")

    class Terminal(dashboard.Terminal):
        def save(self, label, text):
            (base / (label + ".txt")).write_text(text)
            with (base / "pty-screens.jsonl").open("a") as out:
                out.write(json.dumps(dict(label=label, ansi_bytes=len(self.data))) + "\n")

        def key(self, raw):
            with (base / "pty-keys.jsonl").open("a") as out:
                out.write(json.dumps(dict(hex=raw.hex(), text=raw.decode(errors="replace"))) + "\n")
            os.write(self.master, raw)
            return self.drain(.12)

        def palette(self, title):
            for key in (b" ", b"c", b"c"):
                self.key(key)
            self.key(title.encode())
            self.capture("palette-" + str(len(self.data)), [title])
            self.key(b"\r")

    t = Terminal(session)
    field = fs0.field
    sequence = 0

    def shot(label, expected=()):
        nonlocal sequence
        sequence += 1
        return t.capture("pty-%03d-%s" % (sequence, label), expected)

    def select(case):
        path, tag, _ = targets[case]
        t.palette("Resources: Import emitted bundle" if tag == "Bundle" else "Resources: Import retained resource evidence")
        shot("import-form", ["exact absolute directory", "IMPORT"])
        t.key(str(path).encode())
        t.key(b"\r")
        shot("selected-" + case, ["Resources"])

    def scroll_until(label, tokens, steps=130):
        screens = []
        for n in range(steps):
            text = shot(label + "-%03d" % n)
            screens.append(text)
            if all(token in "\n".join(screens) for token in tokens):
                return screens
            t.key(b"]")
        check(False, "PTY did not expose " + repr(tokens))

    try:
        shot("startup", ["Overview"])
        select("augmented")
        # Keep enough room for provider-owned facts; this mutation is private and retained.
        workspace = session.rpc("workspace")
        resources = next(w for w in field(workspace, "workspaces") if field(w, "preset") == ["resources"])
        tile = next(tile for tile in field(workspace, "tiles") if field(tile, "workspace") == field(resources, "id")
                    and field(tile, "kind") == "resources")
        session.mutate(workspace, '(Set_zoom (workspace %s)(tile (%s)))' %
                       (fs0.sexp(field(resources, "id")), fs0.sexp(field(tile, "id"))))
        shot("actual-table", ["program", "RM_IHPSG13_1P_256x16_c2_bm_bist", "matched"])
        check(True, "PTY actual program/stock macro/matched table")
        calls_before = (base / "provider-calls.jsonl").read_bytes()
        t.key(b"/")
        t.key(b"no-such-resource")
        t.key(b"\r")
        shot("filter-empty", ["No resource matches this filter", "available inventory"])
        t.key(b"\x15")
        shot("filter-clear", ["program"])
        check((base / "provider-calls.jsonl").read_bytes() == calls_before, "PTY filter/clear is provider-free")
        t.key(b"g")
        shot("geometry-loaded", ["Detail section: geometry", "Page items"])
        scroll_until("geometry", ["28127.104", "40000", "236.8"])
        check(True, "PTY actual macro placement/footprint geometry visible")
        t.key(b"d")
        shot("gross-reset", ["Source digest:"])
        scroll_until("gross-area", ["902417.2416", "4793.6448"], steps=80)
        check(True, "PTY gross core and component area visible in provider-owned detail")
        t.key(b"t")
        shot("timing-loaded", ["Detail section: timing", "/ 186"])
        source, index = load_case("augmented")
        sid = field(source, "id")
        raw_paths = g.final(g.load(args.example_root / g.MEASUREMENTS /
                                   "installed-final/evidence-50.json"))["resources"][0]["timing_links"]["paths"]
        oracles = g.load(args.fixtures / "byte-oracles.json")["paths"]
        for oracle in sorted(oracles, key=lambda item: raw_paths.index(item["public_path"])):
            position = raw_paths.index(oracle["public_path"])
            for _ in range(32):
                state = snapshot()
                candidates = [p for p in field(state, "details") if field(p, "source_id") == sid
                              and field(p, "section") == "timing"]
                current = candidates[0]
                if int(field(current, "offset")) <= position < int(field(current, "next_offset")):
                    break
                t.key(b"n")
                shot("timing-next", ["Detail section: timing", "Page items"])
                session.rpc("asic", wait=True)
            else:
                check(False, "PTY timing page reaches native oracle")
            values = oracle["public_path"]
            scroll_until("timing-native", [str(values["slack"]), str(values["data_end"]["slew"])
                         if values["path_type"] == "min" else str(values["data_start"]["slew"])], steps=180)
            check(True, "PTY actual signed slack/slew: " + oracle["path_type"])
        t.key(b"e")
        shot("electrical-loaded", ["Detail section: electrical", "/ 372"])
        scroll_until("electrical", ["not_assessed"])
        check(True, "PTY electrical sampled qualification visible")
        t.key(b"a")
        shot("sources-first", ["Source references:", "/ 76"])
        for _ in range(4):
            t.key(b"n")
            shot("sources-next", ["Source references:"])
            session.rpc("asic", wait=True)
        shot("sources-last", ["64", "76"])
        t.key(b"\r")
        shot("source-bytes", ["SHA256:", "Byte span:"])
        check(True, "PTY source catalog reaches last page and opens authorized byte view")
        select("original")
        shot("original-table", ["program"])
        t.key(b"t")
        shot("original-timing", ["Detail section: timing"])
        scroll_until("original-unavailable", ["unavailable"])
        check(True, "PTY original snapshot timing unavailable")
        select("augmented")
        shot("compare-a-source", ["program", "matched"])
        t.palette("Resources: Capture comparison A")
        select("original")
        shot("compare-b-source", ["program", "matched"])
        t.palette("Resources: Capture comparison B")
        t.palette("Resources: Compare captured A / B (c)")
        scroll_until("compatible-comparison", ["Δ(B−A)=0", "final_physical"], steps=80)
        check(True, "PTY compatible actual physical scopes have explicit zero delta")
        select("synthesis")
        shot("compare-synthesis-source", ["program"])
        t.palette("Resources: Capture comparison B")
        t.palette("Resources: Compare captured A / B (c)")
        scroll_until("incompatible-comparison", ["no delta", "incompatible"], steps=80)
        check(True, "PTY incompatible synthesis/physical measurements have no numeric delta")
        select("fifo")
        shot("fifo-empty", ["verified empty inventory", "not_evaluated"])
        check(True, "PTY actual verified FIFO bundle empty inventory")
        for case in ("flops", "fallback"):
            select(case)
            shot(case + "-table", ["program", "flops", "unavailable"])
            check(True, "PTY actual emitted " + case + " unavailable realization")
        select("failed")
        shot("failed-diagnostic-table", ["program", "fail"])
        check(True, "PTY diagnostic failed verdict stays inspectable, not a fabricated real execution")
        select("augmented")
        shot("warm-return", ["program", "matched"])
        check(not field(session.rpc("asic"), "runs"), "PTY imports never fabricate an observation")
        # Adopt the genuine historical FIFO allocation solely to test existing run pins.
        manifest = g.load(args.example_root / ".dev/workbench-real-demo/manifest.json")
        reference = [[k, manifest["allocation"][k]] for k in ("attempt", "stream_id")]
        registered = session.rpc("asic", "(Register %s)" % fs0.sexp(reference), wait=True)
        actual_runs = field(registered, "runs")
        check(len(actual_runs) == 1 and field(actual_runs[0], "reference") == reference,
              "pin test adopts only genuine historical FIFO allocation, no fabricated SRAM observation")
        run = field(actual_runs[0], "run")
        observed = session.rpc("asic", "(Observe %s)" % fs0.sexp(run), wait=True)
        observed_run = next(r for r in field(observed, "runs") if field(r, "run") == run)
        check(field(observed_run, "execution_file") == [manifest["execution_file"]],
              "read-only Observe binds genuine historical FIFO execution before resource inventory query")
        unavailable = session.rpc("asic", '(Resources (Load (target (Run %s))(refresh true)))' % fs0.sexp(run), wait=True)
        resource_state = g.resource_snapshot(fs0, unavailable)
        historical_source = next(s for s in field(resource_state, "sources") if field(s, "target") == ["Run", run])
        historical_index = next(i for i in field(resource_state, "indexes") if field(i, "source_id") == field(historical_source, "id"))
        historical_provenance = json.loads(field(historical_index, "provenance"))
        check(field(historical_index, "inventory_status") == "Available" and not field(historical_index, "rows")
              and historical_provenance["build_identity"] == historical_provenance["methodology"]["bundle_identity"],
              "actual historical FIFO inventory is empty through its own bound methodology, never borrowed from SRAM")
        t.palette("Resources: Select execution " + field(run, "id"))
        shot("actual-bound-historical-inventory", ["verified empty inventory"])
        check(True, "PTY historical FIFO displays its own verified zero inventory")
        select("augmented")
        shot("restore-explicit-after-historical", ["program", "matched"])
        workspace = session.rpc("workspace")
        session.mutate(workspace, '(Set_tile_binding (tile %s)(binding (Pin_run %s)))' %
                       (fs0.sexp(field(tile, "id")), fs0.sexp(run)))
        t.palette("Inspect resources (open Resources workspace)")
        shot("explicit-source-survives-pin", ["program", "matched", "Explicit source"])
        check(True, "PTY explicit coarse SRAM source survives genuine FIFO run pin")
        # A new terminal process reuses warm source facts without a provider read.
        t.close()
        (base / "pty.ansi").rename(base / "pty-first-process.ansi")
        session.rpc("asic", wait=True)
        baseline = (base / "provider-calls.jsonl").read_bytes()
        t = Terminal(session)
        shot("reopen-startup", ["Resources"])
        select("augmented")
        shot("reopen-warm-table", ["program", "matched"])
        check((base / "provider-calls.jsonl").read_bytes() == baseline,
              "PTY new-process warm explicit-source reopening is provider-free")
    finally:
        t.close()


def cached_pty(args, base, session, targets, check):
    g = groundwork
    dashboard = g.module("resource_cached_pty", g.HERE / "test-fs0-dashboard.py")
    if (base / "pty.ansi").exists():
        (base / "pty.ansi").rename(base / "pty-warm-reopen.ansi")
    baseline = (base / "provider-calls.jsonl").read_bytes()
    t = dashboard.Terminal(session)
    try:
        t.capture("cached-pty-startup", ["Resources"])
        t.palette("Resources: Import retained resource evidence")
        t.capture("cached-pty-import", ["exact absolute directory"])
        raw = str(targets["augmented"][0]).encode()
        with (base / "pty-keys.jsonl").open("a") as out:
            out.write(json.dumps(dict(phase="cached-restart", hex=raw.hex())) + "\n")
        os.write(t.master, raw)
        t.drain(.2)
        os.write(t.master, b"\r")
        t.capture("cached-pty-actual-sram", ["program", "CACHED UNVERIFIED", "matched"])
        check((base / "provider-calls.jsonl").read_bytes() == baseline,
              "PTY daemon-restart cached-unverified actual SRAM reopens provider-free")
    finally:
        t.close()
        (base / "pty.ansi").rename(base / "pty-cached-restart.ansi")


def native_retained(args):
    g = groundwork
    g.require(args.daemon and args.provider, "--http needs explicit new --daemon and --provider")
    args.daemon, args.provider = args.daemon.resolve(), args.provider.resolve()
    if args.client:
        args.client = args.client.resolve()
    g.verify(args.example_root, args.fixtures)
    base = args.evidence.resolve() if args.evidence else Path(tempfile.mkdtemp(
        prefix="resource-inspector-retained-http-", dir="/tmp/opencode"))
    if args.evidence:
        g.require(base.parent.is_dir(), "Evidence parent exists")
        base.mkdir()
    before = g.protected(args.example_root)
    g.write_new(base / "protected-before.json", before)
    targets = {"augmented": (args.example_root / g.RUN, "Coarse_run", "coarse_run"),
               "original": (args.example_root / "acceptance/sram/physical-p4", "Coarse_run", "coarse_run"),
               "synthesis": (args.example_root / "acceptance/sram/8b48d7d0-functional", "Coarse_run", "coarse_run"),
               "fifo": (args.example_root / FIFO_BUNDLE, "Bundle", "bundle"),
               "flops": (args.example_root / "acceptance/resource-realization/installed-final/emitted-flops", "Bundle", "bundle"),
               "fallback": (args.example_root / "acceptance/resource-realization/installed-final/emitted-fallback", "Bundle", "bundle")}
    # Same semantic-negative recipe as independent PT5b acceptance, on disposable bytes.
    # No producer record or new run identity is fabricated; source labels remain diagnostic.
    failed = base / "diagnostic-failed-evidence"
    shutil.copytree(targets["augmented"][0], failed)
    lef = failed / "baseline-inputs/0-RM_IHPSG13_1P_256x16_c2_bm_bist.lef"
    old_sha = g.sha(lef)
    text = lef.read_text()
    g.require("CLASS BLOCK" in text, "exact diagnostic mutation anchor")
    lef.write_text(text.replace("CLASS BLOCK", "CLASS CORE SPACER", 1))
    preflight = g.load(failed / "preflight.json")
    matches = [r for r in preflight["references"] if r.get("sha256") == old_sha]
    g.require(matches, "diagnostic retained bound LEF reference")
    for reference in matches:
        reference["sha256"] = g.sha(lef)
    (failed / "preflight.json").write_text(json.dumps(preflight) + "\n")
    g.write_new(base / "diagnostic-mutation.json", dict(
        scope="disposable semantic-negative; not a newly executed or qualified run",
        base=str(targets["augmented"][0]), changes={str(p.relative_to(failed)): dict(
            original_sha256=g.sha(targets["augmented"][0] / p.relative_to(failed)),
            changed_sha256=g.sha(p)) for p in (lef, failed / "preflight.json")}))
    targets["failed"] = (failed, "Coarse_run", "coarse_run")
    original_manifest = g.load(args.example_root / ".dev/workbench-real-demo/manifest.json")
    allowed_targets = {str(p.resolve()): kind for p, _, kind in targets.values()}
    allowed_targets[str(Path(original_manifest["execution_file"]).resolve())] = "execution"
    g.write_new(base / "relay-policy.json", dict(provider=str(args.provider),
                targets=allowed_targets,
                observation=original_manifest["allocation"], execution=original_manifest["execution_file"]))
    shutil.copyfile(Path(__file__), base / "tested-script.py")
    shutil.copyfile(g.HERE / "test-resource-inspector.py", base / "tested-common.py")
    wrapper = base / "read-only-provider"
    wrapper.write_text("#!" + sys.executable + "\nimport os,sys\nos.execv(sys.executable," + repr(
        [sys.executable, "-B", str(Path(__file__).resolve()), "--relay", str(base / "relay-policy.json")]) + " + sys.argv[1:])\n")
    wrapper.chmod(0o700)
    companion = args.provider.parent / "hardcaml-asic-experimental-resource-inspect"
    g.require(companion.is_file(), "actual installed new bridge companion")
    (base / companion.name).symlink_to(companion)
    fs0, session = g.native_setup(args, base, wrapper)
    field, sexp = fs0.field, fs0.sexp
    result = dict(status="failed", scope="actual retained installed bridge over native HTTP",
                  contract_revision="PT6-A-contract-r3 + B final",
                  ui_acceptance="NOT_RUN", checks=[], provider=str(args.provider),
                  daemon_sha256=g.sha(args.daemon), script_sha256=g.sha(base / "tested-script.py"),
                  common_sha256=g.sha(base / "tested-common.py"),
                  companions={p.name: g.sha(p) for p in sorted(args.provider.parent.glob("hardcaml-asic*")) if p.is_file()})
    generation_receipt = args.provider.parent.parent / "receipt.json"
    if generation_receipt.is_file():
        result["provider_capture"] = g.load(generation_receipt)

    def check(ok, message):
        result["checks"].append(dict(passed=bool(ok), expectation=message))
        g.require(ok, message)

    def snapshot(op="Get", wait=False):
        return g.resource_snapshot(fs0, session.rpc("asic", op, wait=wait))

    def load_case(case, refresh=False):
        path, tag, _ = targets[case]
        state = snapshot(g.operation_load(fs0, path, tag, refresh), wait=True)
        return g.source_index(fs0, state, path)

    def detail(source, index, section, offset=0, limit=8):
        state = snapshot('(Resources (Detail (source_id %s)(expected_digest %s)(resource_id program)(section %s)(offset %d)(limit %d)))' %
                         (sexp(field(source, "id")), sexp(field(index, "digest")), sexp(section), offset, limit), wait=True)
        return next(p for p in field(state, "details") if field(p, "source_id") == field(source, "id")
                    and field(p, "section") == section and int(field(p, "offset")) == offset)

    def calls():
        return (base / "provider-calls.jsonl").read_bytes()

    try:
        session.start()
        saved_workspace = session.rpc("workspace")
        source, index = load_case("augmented")
        sid, digest = field(source, "id"), field(index, "digest")
        provenance = json.loads(field(index, "provenance"))
        check(provenance["run_id"] == g.RUN_ID and provenance["build_identity"] == g.BUILD, "HTTP exact original coarse run/build")
        row, = field(index, "rows")
        check(field(index, "inventory_status") == "Available" and not dict(index).get("inventory_reason", []),
              "HTTP final typed actual inventory is available with no missing reason")
        check(field(row, "id") == "program" and field(row, "instances") == ["hc_resource_7_program"], "HTTP actual program/instance")
        check(field(row, "synthesis") == field(row, "final") == "matched", "HTTP separate synthesis/final matching")
        check(not field(session.rpc("asic"), "runs"), "HTTP coarse import creates no fake observation")
        for name, value in (("nonspacer_component_area", 4793.6448), ("gross_core_area", 902417.2416)):
            check(any(field(m, "name") == name and abs(float(field(m, "value")[0]) - value) < 1e-7
                      for m in field(index, "measurements")), "HTTP actual scalar: " + name)
            check(any(field(m, "name") == name and field(m, "classification") == "Derived"
                      for m in field(index, "measurements")), "HTTP provider-owned derived classification: " + name)
        geometry = detail(source, index, "geometry")
        check(any(decode_fields(fs0, item).get("instances", [{}])[0].get("area_um2") == 28127.104
                  for item in field(geometry, "items") if "instances" in decode_fields(fs0, item)), "HTTP actual geometry footprint")
        raw_evidence = g.load(args.example_root / g.MEASUREMENTS / "installed-final/evidence-50.json")
        raw_paths = g.final(raw_evidence)["resources"][0]["timing_links"]["paths"]
        for oracle in g.load(args.fixtures / "byte-oracles.json")["paths"]:
            position = raw_paths.index(oracle["public_path"])
            page = detail(source, index, "timing", position, 1)
            value = decode_fields(fs0, field(page, "items")[0])
            check(all(value.get(k) == v for k, v in oracle["public_path"].items()), "HTTP exact native timing path/span/blank columns")
            check(int(field(page, "total")) == 186, "HTTP timing total186")
        electric = detail(source, index, "electrical", 0, 1)
        check(int(field(electric, "total")) == 372 and "not_assessed" in str(field(electric, "items")), "HTTP electrical372/compliance qualification")
        entries = []
        for offset in (0, 32, 64):
            state = snapshot('(Resources (Artifacts (source_id %s)(expected_digest %s)(offset %d)(limit 32)))' %
                             (sexp(sid), sexp(digest), offset), wait=True)
            page = next(p for p in field(state, "artifacts") if field(p, "source_id") == sid and int(field(p, "offset")) == offset)
            entries.extend(field(page, "entries"))
        check(len(entries) == 76, "HTTP all76 source artifacts reachable")
        refs = {r["path"]: r["sha256"] for r in raw_evidence["evidence_refs"]}
        check({field(e, "label"): field(e, "sha256") for e in entries} == refs, "HTTP source catalog exact original hashes")
        oracle = g.load(args.fixtures / "byte-oracles.json")["paths"][0]
        entry, = [e for e in entries if field(e, "label") == oracle["path"]]
        raw = (targets["augmented"][0] / oracle["path"]).read_bytes()
        start = sum(map(len, raw.splitlines(keepends=True)[:oracle["first_line"] - 1]))
        state = snapshot('(Resources (Read_artifact (source_id %s)(expected_digest %s)(artifact_id %s)(offset %d)(limit 4096)))' %
                         (sexp(sid), sexp(digest), sexp(field(entry, "id")), start), wait=True)
        page = next(p for p in field(state, "bytes") if field(p, "source_id") == sid)
        check(bytes.fromhex(field(page, "bytes_hex")) == raw[start:start + 4096], "HTTP raw native report byte span")
        baseline = calls()
        rejected = session.rpc("asic", '(Resources (Artifacts (source_id %s)(expected_digest %s)(offset 0)(limit 32)))' %
                               (sexp(sid), sexp("0" * 64)), wait=True)
        check(any(field(o, "state") == "failed" and "0" * 64 in field(o, "key")
                  for o in field(rejected, "operations")) and calls() == baseline,
              "HTTP stale actual-source digest rejects before provider read")
        for case in ("original", "synthesis", "fifo", "flops", "fallback"):
            other_source, other_index = load_case(case)
            if case == "fifo":
                check(not field(other_index, "rows") and field(other_index, "verdict") == "not_evaluated"
                      and field(other_index, "inventory_status") == "Available", "HTTP verified resource-free FIFO bundle")
            else:
                other_row, = field(other_index, "rows")
                if case == "original":
                    check(all(int(field(s, "count")) == 0 for s in field(other_row, "sections") if field(s, "id") in ("timing", "electrical")), "HTTP original timing absent; no augmented borrowing")
                if case in ("flops", "fallback"):
                    check(field(other_row, "implementation") == "flops" and field(other_row, "final") == "unavailable", "HTTP actual emitted bundle selection, no flop ownership: " + case)
        failed_source, failed_index = load_case("failed")
        check(field(failed_index, "verdict") == "fail" and field(failed_source, "freshness") == "Validated",
              "installed bridge CLI1 diagnostic is readable failed evidence over HTTP")
        failed_page = detail(failed_source, failed_index, "geometry", 0, 1)
        check(bool(field(failed_page, "items")), "failed evidence retains usable diagnostic detail")
        baseline = calls()
        load_case("augmented")
        detail(source, index, "geometry")
        check(calls() == baseline, "HTTP warm index/detail reopening provider-free")
        if args.pty:
            g.require(args.client and args.client.is_file(), "--pty requires matching compiled --client")
            result["client_sha256"] = g.sha(args.client)
            exercise_pty(args, base, session, fs0, targets, check, snapshot, load_case)
            result["ui_acceptance"] = "initial_pty_passed"
            saved_workspace = session.rpc("workspace")
        (base / "deny-queries").touch()
        session.stop()
        session.start()
        restored_source, restored_index = g.source_index(fs0, snapshot(), targets["augmented"][0])
        check(field(restored_source, "freshness") == "Cached_unverified" and restored_index == index, "HTTP restart exact cached-unverified actual evidence")
        baseline = calls()
        load_case("augmented")
        check(calls() == baseline, "HTTP restarted warm source provider-free")
        if args.pty:
            cached_pty(args, base, session, targets, check)
        check(session.rpc("workspace") == saved_workspace, "HTTP actual imports preserve layout/context bindings")
        # Let B's later PTY reuse this guarded private session description, not user state.
        result["status"] = "retained_http_and_initial_pty_passed" if args.pty else "retained_http_passed_pty_pending"
    finally:
        g.stop_session(session)
        after = g.protected(args.example_root)
        g.write_new(base / "protected-after.json", after)
        result["protected_unchanged"] = before == after
        if before != after:
            result["status"] = "failed"
        g.write_new(base / "result.json", result)
        print(json.dumps(dict(evidence=str(base), status=result["status"], checks=len(result["checks"]), ui_acceptance=result["ui_acceptance"]), indent=2))
    g.require(result["protected_unchanged"], "actual HTTP retained/config/pointer preservation")


def public_acceptance(args):
    """Exercise an explicitly supplied new installed bridge. No capture/build here."""
    g = groundwork
    g.verify(args.example_root, args.fixtures)
    provider = args.provider.resolve()
    bin_dir = provider.parent
    companion = bin_dir / "hardcaml-asic-experimental-resource-inspect"
    g.require(companion.is_file(), "New bridge companion required; PT5b dispatcher alone is insufficient")
    base = args.evidence.resolve() if args.evidence else Path(tempfile.mkdtemp(
        prefix="resource-inspector-retained-", dir="/tmp/opencode"))
    if args.evidence:
        g.require(base.parent.is_dir(), "Evidence parent must exist")
        base.mkdir()
    before = g.protected(args.example_root)
    g.write_new(base / "protected-before.json", before)
    shutil.copyfile(Path(__file__), base / "tested-script.py")
    result = dict(status="failed", scope="installed real bridge public acceptance ONLY",
                  contract_revision="PT6-A-contract-r3 + B final",
                  ui_acceptance="NOT_RUN", http_acceptance="NOT_RUN", checks=[], commands=[],
                  provider=str(provider), script_sha256=g.sha(base / "tested-script.py"),
                  binaries={p.name: g.sha(p) for p in sorted(bin_dir.glob("hardcaml-asic*")) if p.is_file()})
    targets = {
        "augmented": args.example_root / g.RUN,
        "original": args.example_root / "acceptance/sram/physical-p4",
        "synthesis": args.example_root / "acceptance/sram/8b48d7d0-functional",
    }
    result["targets"] = {k: str(v) for k, v in targets.items()}

    def check(ok, message):
        result["checks"].append(dict(passed=bool(ok), expectation=message))
        g.require(ok, message)

    def invoke(name=None, query=None, expected=None, resource=None, section=None,
               artifact=None, offset=0, limit=16, code=0):
        argv = [str(provider)]
        if name is None:
            argv += ["--version", "--json"]
        else:
            # Exact targets only; caller cannot supply arbitrary paths/producer args.
            argv += ["resource-inspect", str(targets[name]), "--kind", "coarse_run", "--json"]
            if query:
                argv += ["--query", query, "--expected-digest", expected,
                         "--offset", str(offset), "--limit", str(limit)]
            if resource:
                argv += ["--resource-id", resource]
            if section:
                argv += ["--section", section]
            if artifact:
                argv += ["--artifact-id", artifact]
        proc = subprocess.run(argv, capture_output=True, timeout=120,
                              env=dict(os.environ, PATH="/nonexistent/pt6-no-tools",
                                       TOOLCHAIN="/nonexistent/pt6", PYTHONDONTWRITEBYTECODE="1"))
        stem = "%03d" % len(result["commands"])
        (base / (stem + ".stdout")).write_bytes(proc.stdout)
        (base / (stem + ".stderr")).write_bytes(proc.stderr)
        result["commands"].append(dict(argv=argv, exit=proc.returncode, expected_exit=code, stem=stem))
        check(proc.returncode == code, "public command exit: " + stem)
        if code == 2 and not proc.stdout.strip():
            check(bool(proc.stderr.strip()), "rejected query has explicit stderr diagnostic")
            return {"error": proc.stderr.decode(errors="replace")}
        data = json.loads(proc.stdout)
        if name is not None and code == 0:
            check(data["contract"] == "hardcaml-asic.resource-inspection" and data["schema_version"] == 1,
                  "exact bridge envelope: " + stem)
            check(data["target"] == str(targets[name].resolve()) and data["kind"] == "coarse_run",
                  "exact coarse target identity: " + stem)
            if expected:
                check(data["source_digest"] == expected, "exact page digest: " + stem)
        return data

    def pages(name, index, query, section=None):
        offset, collected = 0, []
        while True:
            page = invoke(name, query=query, expected=index["source_digest"], section=section,
                          resource="program" if section else None, offset=offset, limit=32)
            key = "items" if query == "detail" else "entries"
            collected.extend(page[key])
            if page["next_offset"] == page["total"]:
                check(len(collected) == page["total"], "complete pagination: " + (section or query))
                return collected
            check(offset < page["next_offset"] <= page["total"], "bounded pagination makes progress")
            offset = page["next_offset"]

    def fields(item):
        result = {}
        for key, value in item["fields"]:
            try:
                result[key] = json.loads(value)
            except ValueError:
                result[key] = value
        return result

    try:
        metadata = invoke()
        check(metadata["cli_contract"]["capabilities"].get("resource_inspection1") is True,
              "installed provider advertises separate bridge capability")
        index = invoke("augmented")
        check(index["inventory_status"] == "available" and index["inventory_reason"] is None,
              "final public typed inventory availability")
        check(index["provenance"]["run_id"] == g.RUN_ID and index["provenance"]["build_identity"] == g.BUILD,
              "actual retained run/build, no synthetic named observation")
        row, = index["rows"]
        check(row["id"] == "program" and row["implementation"] == "RM_IHPSG13_1P_256x16_c2_bm_bist",
              "actual program and selected stock macro")
        check(row["instances"] == ["hc_resource_7_program"] and row["synthesis"] == row["final"] == "matched",
              "exact instance matched in distinct synthesis/final observations")
        counts = {section["id"]: section["count"] for section in row["sections"]}
        check((counts["timing"], counts["electrical"]) == (186, 372), "actual sampled path/electrical counts")
        measurements = index["measurements"]
        for name, classification in (("nonspacer_component_area", "derived"), ("gross_core_area", "derived"),
                                     ("native_nonspacer_area", "observed")):
            check(any(m["name"] == name and m["classification"] == classification for m in measurements),
                  "explicit provider-owned measurement classification: " + name)
        check(any(m["name"] == "nonspacer_component_area" and m["value"] == 4793.6448 for m in measurements),
              "actual nonspacer component footprint")
        geometry = [fields(item) for item in pages("augmented", index, "detail", "geometry")]
        check(geometry[0]["instances"][0]["area_um2"] == 28127.104, "actual macro geometry area")
        timing = [fields(item) for item in pages("augmented", index, "detail", "timing")]
        for oracle in g.load(args.fixtures / "byte-oracles.json")["paths"]:
            original = oracle["public_path"]
            matching = [p for p in timing if p["corner"] == original["corner"] and
                        p["path_type"] == original["path_type"] and
                        p["provenance"]["first_line"] == original["provenance"]["first_line"]]
            check(len(matching) == 1 and all(matching[0].get(k) == v for k, v in original.items()),
                  "actual timing fields preserve independently retained native span")
        electrical = pages("augmented", index, "detail", "electrical")
        check(len(electrical) == 372, "every electrical observation paginates")
        entries = pages("augmented", index, "artifacts")
        refs = {r["path"]: r for r in g.load(args.example_root / g.MEASUREMENTS /
                                            "installed-final/evidence-50.json")["evidence_refs"]}
        check(len(entries) == 76 and {entry["label"] for entry in entries} == set(refs), "all 76 actual sources navigable")
        for entry in entries:
            check(entry["sha256"] == refs[entry["label"]]["sha256"], "actual catalog source hash: " + entry["label"])
        # Verify actual byte slices independently, including native report path spans.
        for oracle in g.load(args.fixtures / "byte-oracles.json")["paths"]:
            entry, = [entry for entry in entries if entry["label"] == oracle["path"]]
            raw = (targets["augmented"] / oracle["path"]).read_bytes()
            start = sum(map(len, raw.splitlines(keepends=True)[:oracle["first_line"] - 1]))
            for offset in (0, start, max(0, len(raw) - 4096)):
                page = invoke("augmented", query="bytes", expected=index["source_digest"],
                              artifact=entry["id"], offset=offset, limit=4096)
                check(bytes.fromhex(page["bytes_hex"]) == raw[offset:offset + 4096], "native report bytes match retained oracle")
        invoke("augmented", query="artifacts", expected="0" * 64, code=2)
        invoke("augmented", query="bytes", expected=index["source_digest"], artifact="../../etc/passwd", code=2)
        original = invoke("original")
        original_row, = original["rows"]
        check(all(s["count"] == 0 and s["status"] == "unavailable" for s in original_row["sections"]
                  if s["id"] in ("timing", "electrical")), "original snapshot timing/electrical remain unavailable")
        synthesis = invoke("synthesis")
        check(any(m["name"] == "combined_cell_area_estimate" and m["value"] == 30309.8272
                  for m in synthesis["measurements"]), "separate synthesis combined area estimate")
        check(any(m["name"] == "combined_cell_area_estimate" and m["classification"] == "estimate"
                  for m in synthesis["measurements"]), "synthesis area is explicitly Estimate, never a measured delta")
        result["status"] = "public_bridge_passed_ui_pending"
    finally:
        after = g.protected(args.example_root)
        g.write_new(base / "protected-after.json", after)
        result["protected_unchanged"] = after == before
        if after != before:
            result["status"] = "failed"
        g.write_new(base / "result.json", result)
        print(json.dumps(dict(evidence=str(base), status=result["status"], checks=len(result["checks"]),
                              ui_acceptance="NOT_RUN", http_acceptance="NOT_RUN"), indent=2))
    g.require(result["protected_unchanged"], "Protected historical/configuration/pointers unchanged")


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--relay":
        sys.exit(relay(Path(sys.argv[2]), sys.argv[3:]))
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify-inputs", action="store_true")
    mode.add_argument("--public", action="store_true", help="new explicitly installed bridge only; no HTTP/PTY")
    mode.add_argument("--http", action="store_true", help="actual installed bridge over private native HTTP")
    parser.add_argument("--provider", type=Path)
    parser.add_argument("--daemon", type=Path)
    parser.add_argument("--client", type=Path)
    parser.add_argument("--pty", action="store_true", help="actual Resources UI over owned native HTTP session")
    parser.add_argument("--outer-timeout", type=int, default=120)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--example-root", type=Path, default=groundwork.DEFAULT_EXAMPLE)
    parser.add_argument("--fixtures", type=Path, default=groundwork.FIXTURES)
    args = parser.parse_args()
    if args.http:
        native_retained(args)
        return
    if args.public:
        if not args.provider:
            parser.error("--public requires an explicit new --provider after A's focused completion")
        public_acceptance(args)
        return
    if not args.verify_inputs:
        parser.exit(2, "Choose --verify-inputs, --public with an explicit provider, or --http with matching binaries\n")
    result = groundwork.verify(args.example_root.resolve(), args.fixtures.resolve())
    result["scope"] = "retained-input precheck only; no provider or daemon executed"
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
