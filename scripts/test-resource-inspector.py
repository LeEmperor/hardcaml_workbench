#!/usr/bin/env python3
"""PT.6 C acceptance: hashed groundwork, synthetic bridge and native HTTP route.

--prepare copies public evidence projections and records byte inventories. --verify
checks those inputs without executing any provider. Neither mode is UI acceptance.
--smoke tests the synthetic provider, --http requires matching new native binaries.
Add --pty to --http for final-schema native navigation/retry/qualification checks.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WB = HERE.parent
DEFAULT_EXAMPLE = WB.parent / "hardcaml_asic_example"
FIXTURES = HERE / "fixtures/resource-inspector"
MEASUREMENTS = Path("acceptance/resource-measurements")
RUN = MEASUREMENTS / "accepted-live-01/run"
GENERATION = Path(".dev/asic-pt5b/generations/4848a66eeda54751b12d645ee9bcd5c4")
RUN_ID = "be961b2c95f74c81ad6af81ca4d2b269"
BUILD = "fa38d9064dffdf2ec1578c79c2e8890eba81bf704af460e85fcc6031b707d53c"


def require(value, message):
    if not value:
        raise AssertionError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    return json.loads(path.read_text())


def write_new(path, value):
    with path.open("x") as out:
        json.dump(value, out, indent=2, allow_nan=False)
        out.write("\n")


def inventory(root, relative):
    directory = root / relative
    require(directory.is_dir(), f"Missing retained directory: {directory}")
    result = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), f"Unexpected retained symlink: {path}")
        if path.is_file():
            result[str(path.relative_to(root))] = sha(path)
    return result


def protected(example):
    capture = load(example / MEASUREMENTS / "accepted-live-01/capture.json")
    historical_expected = {p: digest for p, digest in capture["protected_before"].items()
                           if p.startswith("acceptance/sram/")}
    history = {p: sha(example / p) for p in historical_expected}
    require(history == historical_expected, "Original 276-file historical inventory changed")
    augmented = inventory(example, RUN)
    require(len(history) == 276, f"Expected 276 historical files, got {len(history)}")
    require(len(augmented) == 333, f"Expected 333 augmented files, got {len(augmented)}")
    captured_expected = {str(MEASUREMENTS / "accepted-live-01" / e["destination"]):
                         e["destination_sha256"] for e in capture["entries"]}
    require(augmented == captured_expected, "Augmented bytes differ from original capture")
    files = dict(history, **augmented)
    for name in ("hardcaml-workbench-asic.sexp", "hardcaml-workbench-preparation.sexp",
                 "hardcaml-workbench-simulation.sexp", "asic-dependency.json",
                 ".dev/workbench-real-demo/manifest.json"):
        files[name] = sha(example / name)
    pointers = {}
    for path in sorted((example / ".dev").glob("*/current")):
        require(path.is_symlink(), f"Unexpected current pointer type: {path}")
        pointers[str(path.relative_to(example))] = dict(
            target=str(path.readlink()), mtime_ns=path.lstat().st_mtime_ns)
    return dict(files=files, current_pointers=pointers,
                history_count=len(history), augmented_count=len(augmented))


def final(evidence):
    return next(o for o in evidence["observations"] if o["stage"] == "final_physical")


def fixture_projection(evidence):
    """Raw schema-2 facts, NOT a guessed resource-inspection bridge envelope."""
    result = copy.deepcopy(evidence)
    for observation in result["observations"]:
        for row in observation["resources"]:
            for field, collection in (("timing_links", "paths"), ("electrical_links", "points")):
                links = row.get(field, {})
                if collection in links:
                    links["fixture_original_count"] = len(links[collection])
                    # Exact original rows; keep bounded preparation data, not 372 repetitions.
                    links[collection] = links[collection][:2]
    return result


def source_oracles(example, evidence):
    observation = final(evidence)
    row, = observation["resources"]
    paths = row["timing_links"]["paths"]
    selected = []
    for corner, mode in (("nom_slow_1p08V_125C", "max"), ("nom_fast_1p32V_m40C", "min")):
        path, = [p for p in paths if p["corner"] == corner and p["path_type"] == mode
                 and p["provenance"]["first_line"] == 7]
        provenance = path["provenance"]
        relative = provenance["report"]["path"]
        report = example / RUN / relative
        raw = report.read_bytes()
        first, last = provenance["first_line"], provenance["last_line"]
        span = b"".join(raw.splitlines(keepends=True)[first - 1:last])
        require(span.startswith(b"Startpoint:"), "Raw span starts at native path header")
        require(b"slack (" in span, "Raw span includes native slack")
        selected.append(dict(corner=corner, path_type=mode, path=relative,
                             sha256=sha(report), first_line=first, last_line=last,
                             span_sha256=hashlib.sha256(span).hexdigest(),
                             span_utf8=span.decode("utf-8"), public_path=path))
    return dict(scope="independent raw byte spans; not bridge output",
                paths=selected, expected_paths=186, expected_points=372,
                macro_area_um2=28127.104, nonspacer_area_um2=4793.6448,
                gross_core_area_um2=902417.2416)


def prepare(example, directory):
    require(directory.is_dir(), "Fixture parent must exist")
    require(not (directory / "manifest.json").exists(), "Refusing to replace prepared fixtures")
    before = protected(example)
    sources = {
        "original": MEASUREMENTS / "installed-final/evidence-46.json",
        "augmented": MEASUREMENTS / "installed-final/evidence-50.json",
        "synthesis": Path("acceptance/resource-realization/synthesis.json"),
        "fifo-preparation": Path("acceptance/preparation/capture-final/fifo-zero-resources/resources.json"),
        "flops-manifest": Path("acceptance/resource-realization/installed-final/emitted-flops/manifest.json"),
        "fallback-manifest": Path("acceptance/resource-realization/installed-final/emitted-fallback/manifest.json"),
    }
    generated = {}
    for name, relative in sources.items():
        data = load(example / relative)
        if name in ("original", "augmented", "synthesis"):
            data = fixture_projection(data)
        elif name == "fifo-preparation":
            data = {"resources": data["resources"], "circuit_identity": data["circuit_identity"]}
        filename = name + ".json"
        write_new(directory / filename, dict(
            fixture_scope="public evidence projection; not bridge wire format or a new run",
            source=str(relative), source_sha256=sha(example / relative), data=data))
        generated[filename] = sha(directory / filename)
    evidence = load(example / sources["augmented"])
    write_new(directory / "byte-oracles.json", source_oracles(example, evidence))
    generated["byte-oracles.json"] = sha(directory / "byte-oracles.json")
    # Retain an actual public failed-verdict payload from historical diagnostic tests.
    receipt_path = MEASUREMENTS / "installed-final/receipt.json"
    receipt = load(example / receipt_path)
    for command in receipt["commands"]:
        if command["exit"] != 1:
            continue
        relative = MEASUREMENTS / "installed-final" / command["stdout"]
        try:
            data = load(example / relative)
        except ValueError:
            continue
        if data.get("contract") == "hardcaml-asic.resource-evidence":
            write_new(directory / "failed-evidence.json", dict(
                fixture_scope="retained disposable diagnostic; NOT a failed actual SRAM run",
                source=str(relative), source_sha256=sha(example / relative),
                command=command, data=fixture_projection(data)))
            generated["failed-evidence.json"] = sha(directory / "failed-evidence.json")
            sources["failed-evidence"] = relative
            break
    require("failed-evidence.json" in generated, "No retained public failed-verdict payload")
    after = protected(example)
    require(before == after, "Protected evidence/configuration changed during preparation")
    write_new(directory / "manifest.json", dict(
        scope="PT6 C groundwork ONLY; no HTTP/PTY/bridge acceptance",
        script_sha256=sha(Path(__file__)), fixtures=generated,
        sources={str(p): sha(example / p) for p in sources.values()},
        protected=before, provider_record=str(MEASUREMENTS / "provider-final-binaries.json"),
        provider_record_sha256=sha(example / MEASUREMENTS / "provider-final-binaries.json")))
    return verify(example, directory)


def verify(example, directory):
    manifest = load(directory / "manifest.json")
    current = protected(example)
    # PT6 is an explicitly authorized dedicated store, absent at groundwork capture.
    # All pre-existing pointers remain strict; individual runs protect PT6 too.
    if ".dev/asic-pt6/current" not in manifest["protected"]["current_pointers"]:
        current["current_pointers"].pop(".dev/asic-pt6/current", None)
    require(manifest["protected"] == current, "Protected bytes or existing current pointers changed")
    for filename, digest in manifest["fixtures"].items():
        require(sha(directory / filename) == digest, f"Changed fixture {filename}")
    for relative, digest in manifest["sources"].items():
        require(sha(example / relative) == digest, f"Changed source {relative}")
    augmented = load(example / MEASUREMENTS / "installed-final/evidence-50.json")
    require(augmented["provenance"]["run_id"] == RUN_ID, "Exact coarse run identity")
    require(augmented["provenance"]["build_identity"] == BUILD, "Exact build identity")
    for ref in augmented["evidence_refs"]:
        target = (example / RUN / ref["path"]).resolve()
        require(target.is_relative_to((example / RUN).resolve()), "Contained source reference")
        require(sha(target) == ref["sha256"], f"Source closure: {ref['path']}")
    row, = final(augmented)["resources"]
    require(row["area"]["value"] == 28127.104, "Exact macro footprint")
    physical = final(augmented)["physical"]
    require(physical["measurements"]["nonspacer_component_area"]["value"] == 4793.6448,
            "Exact nonspacer component area")
    require(len(row["timing_links"]["paths"]) == 186, "186 sampled paths")
    require(len(row["electrical_links"]["points"]) == 372, "372 electrical points")
    original = load(directory / "original.json")["data"]
    original_row, = final(original)["resources"]
    require(original_row["timing_links"]["status"] == "unavailable", "Original timing unavailable")
    fifo = load(directory / "fifo-preparation.json")["data"]
    require(fifo["resources"]["resources"] == [], "FIFO resource inventory empty")
    oracle = load(directory / "byte-oracles.json")
    require(source_oracles(example, augmented) == oracle, "Exact retained report byte spans")
    identities = load(example / manifest["provider_record"])
    require(sha(example / manifest["provider_record"]) == manifest["provider_record_sha256"],
            "Frozen provider identity record")
    for relative, digest in identities["binaries"].items():
        require(sha(example / GENERATION / relative) == digest, f"Provider companion: {relative}")
    return dict(status="groundwork_verified", ui_acceptance="NOT_RUN",
                bridge_acceptance="NOT_RUN", historical_files=276, augmented_files=333,
                evidence_refs=len(augmented["evidence_refs"]),
                provider_binaries=len(identities["binaries"]),
                acceptance_scope="input precheck only; acceptance modes require explicit matching provider/binaries")


CASES = ("augmented", "original", "empty", "flops", "fallback", "named", "failed",
         "invalid", "malformed", "oversize", "row-budget", "detail-budget", "incompatible",
         "old", "old-empty", "unavailable", "truncated", "exit1-pass", "exit0-fail",
         "estimate-a", "estimate-b", "missing-estimate")


def seed_provider(base, fixtures):
    (base / "targets").mkdir()
    shutil.copytree(fixtures, base / "fixtures")
    for case in CASES:
        root = base / "targets" / case
        root.mkdir()
        control = dict(case=case, generation="a")
        if case in ("estimate-a", "estimate-b", "missing-estimate"):
            control.update(case="estimate", area=11 if case == "estimate-a" else 12 if case == "estimate-b" else None,
                           reason="missing-estimate-source")
        write_new(root / "control.json", control)
    provider = base / "provider"
    provider.write_text("#!" + sys.executable + "\nimport os,sys\nos.execv(sys.executable, " + repr(
        [sys.executable, "-B", str(base / "fixtures/provider.py"), "--fixture-root", str(base)])
                        + " + sys.argv[1:])\n")
    provider.chmod(0o700)
    # The backend identities must see implementation bytes, not just the dispatcher.
    shutil.copyfile(base / "fixtures/provider.py", base / "hardcaml-asic-experimental-resource-inspect")
    return provider


def smoke(args):
    """Test the synthetic provider itself. This deliberately starts no daemon/client."""
    verify(args.example_root, args.fixtures)
    if args.evidence:
        base = args.evidence.resolve()
        require(base.parent.is_dir(), "Evidence parent must exist")
        base.mkdir()
    else:
        base = Path(tempfile.mkdtemp(prefix="resource-inspector-fixture-", dir="/tmp/opencode"))
    result = dict(status="failed", scope="synthetic provider smoke ONLY",
                  ui_acceptance="NOT_RUN", bridge_acceptance="NOT_RUN", checks=[], commands=[])
    before = protected(args.example_root)
    provider = seed_provider(base, args.fixtures)
    shutil.copyfile(Path(__file__), base / "tested-script.py")
    result["script_sha256"] = sha(base / "tested-script.py")
    result["provider_sha256"] = sha(base / "fixtures/provider.py")

    def check(ok, message):
        result["checks"].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)

    def invoke(case=None, extra=(), code=0, decode=True):
        argv = [str(provider)] + (["--version", "--json"] if case is None else
                ["resource-inspect", str(base / "targets" / case), "--kind", "coarse_run", "--json", *extra])
        process = subprocess.run(argv, capture_output=True, timeout=40,
                                 env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        stem = "%03d" % len(result["commands"])
        (base / (stem + ".stdout")).write_bytes(process.stdout)
        (base / (stem + ".stderr")).write_bytes(process.stderr)
        result["commands"].append(dict(argv=argv, exit=process.returncode, expected_exit=code, stem=stem))
        check(process.returncode == code, "expected fixture exit: " + stem)
        return json.loads(process.stdout) if decode else process.stdout

    try:
        metadata = invoke()
        check(metadata["cli_contract"]["capabilities"]["resource_inspection1"], "separate capability advertised")
        (base / "unsupported-capability").touch()
        check(not invoke()["cli_contract"]["capabilities"]["resource_inspection1"],
              "CLI4 alone does not imply resource inspection capability")
        (base / "unsupported-capability").unlink()
        index = invoke("augmented")
        digest = index["source_digest"]
        check(index["rows"][0]["instances"] == ["hc_resource_7_program"], "exact stock instance in fixture")
        check(invoke("empty")["rows"] == [], "resource-free inventory distinct from failure")
        for case in ("flops", "fallback", "named"):
            row, = invoke(case)["rows"]
            check(row["final"] == "unavailable" and row["measurements"][0]["value"] is None,
                  case + " has no invented realization/area")
        check(invoke("failed", code=1)["verdict"] == "fail", "readable failed verdict uses exit 1")
        invoke("invalid", code=2)
        raw = invoke("malformed", decode=False)
        try:
            json.loads(raw)
        except ValueError:
            check(True, "malformed payload deliberately unparsable")
        else:
            check(False, "malformed payload deliberately unparsable")
        check(len(invoke("oversize", decode=False)) > 2 * 1024 * 1024, "index byte-budget negative exceeds bound")
        check(len(invoke("row-budget")["rows"]) == 4097, "row-budget negative exceeds 4096")
        entries = []
        for offset in (0, 32, 64):
            page = invoke("augmented", ["--query", "artifacts", "--expected-digest", digest,
                                        "--offset", str(offset), "--limit", "32"])
            entries.extend(page["entries"])
        check(len(entries) == len({e["id"] for e in entries}) == 76, "all 76 opaque source handles reachable")
        raw = bytearray()
        for offset in range(0, len(b"resource source 75\n"), 5):
            page = invoke("augmented", ["--query", "bytes", "--expected-digest", digest,
                "--artifact-id", entries[-1]["id"], "--offset", str(offset), "--limit", "5"])
            raw.extend(bytes.fromhex(page["bytes_hex"]))
        check(bytes(raw) == b"resource source 75\n" and hashlib.sha256(raw).hexdigest() == entries[-1]["sha256"],
              "paged artifact raw bytes and full hash match independent oracle")
        invoke("augmented", ["--query", "bytes", "--expected-digest", digest,
            "--artifact-id", "../../etc/passwd"], code=2)
        invoke("augmented", ["--query", "artifacts", "--expected-digest", "0" * 64], code=2)
        invoke("augmented", ["--query", "artifacts", "--expected-digest", digest, "--limit", "65"], code=2)
        for section in ("inventory", "geometry", "timing", "electrical", "provenance"):
            page = invoke("augmented", ["--query", "detail", "--expected-digest", digest,
                "--resource-id", "program", "--section", section])
            check(page["items"] and page["section"] == section, "exact detail section: " + section)
        large = invoke("detail-budget")
        check(len(invoke("detail-budget", ["--query", "detail", "--expected-digest", large["source_digest"],
            "--resource-id", "program", "--section", "inventory"], decode=False)) > 65536,
            "detail-budget negative exceeds 64KiB")
        compatible = index["rows"][0]["measurements"][0]
        incompatible = invoke("incompatible")["rows"][0]["measurements"][0]
        check(compatible["stage"] != incompatible["stage"] and compatible["scope"] != incompatible["scope"],
              "comparison negative retains incompatible semantics")
        # Prove the fixture really can deliver an old response after a newer generation.
        control = base / "targets/augmented/control.json"
        control.write_text(json.dumps(dict(case="augmented", generation="late-old", delay=.8)))
        old_digest = sha(control)
        argv = [str(provider), "resource-inspect", str(control.parent), "--kind", "coarse_run", "--json"]
        late = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not (control.parent / "query-started").exists():
                require(time.monotonic() < deadline and late.poll() is None, "delayed query start barrier")
                time.sleep(.02)
            control.write_text(json.dumps(dict(case="augmented", generation="new")))
            newest = invoke("augmented")
            stdout, stderr = late.communicate(timeout=5)
            (base / "late-old.stdout").write_bytes(stdout)
            (base / "late-old.stderr").write_bytes(stderr)
            result["commands"].append(dict(argv=argv, exit=late.returncode, expected_exit=0, stem="late-old"))
            check(late.returncode == 0 and json.loads(stdout)["source_digest"] == old_digest
                  and newest["source_digest"] != old_digest,
                  "fixture returns genuinely delayed old generation; UI fencing remains untested")
        finally:
            if late.poll() is None:
                late.kill()
                late.communicate(timeout=5)
        result["status"] = "fixture_smoke_passed"
    finally:
        result["protected_unchanged"] = protected(args.example_root) == before
        if not result["protected_unchanged"]:
            result["status"] = "failed"
        write_new(base / "result.json", result)
        print(json.dumps(dict(evidence=str(base), status=result["status"],
                             checks=len(result["checks"]), protected_unchanged=result["protected_unchanged"],
                             ui_acceptance="NOT_RUN", bridge_acceptance="NOT_RUN"), indent=2))
    require(result["protected_unchanged"], "Protected example state unchanged")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def native_setup(args, base, provider):
    fs0 = module("resources_fs0", HERE / "test-fs0.py")
    http_module = module("resources_native_http", WB / "demo/synthetic_flow/http_client.py")

    class NativeSession(fs0.Session):
        """Direct native HTTP also works before B's terminal binary is compiled."""
        def start(self):
            super().start()
            self.http = http_module.Client(self.url, self.root)
            self.flush_history()

        def flush_history(self):
            with (self.evidence / "native-http.jsonl").open("a") as out:
                for item in self.http.history:
                    out.write(json.dumps(item) + "\n")
            self.http.history.clear()

        def rpc(self, domain, operation="Get", wait=False, success=True):
            def request(op):
                try:
                    return self.http.raw("/api/v1/" + domain, [
                        ["instance_id", self.http.instance], ["project", self.http.project],
                        ["operation", http_module.Atom(op)]])
                finally:
                    self.flush_history()
            result = request(operation)
            if wait and domain == "asic":
                deadline = time.monotonic() + self.args.outer_timeout
                while any(fs0.field(o, "state") in ("pending", "executing")
                          for o in fs0.field(result, "operations")):
                    require(time.monotonic() < deadline, "Native HTTP resource query timeout")
                    time.sleep(.05)
                    result = request("Get")
            return result

        def mutate(self, snapshot, mutation):
            return self.rpc("workspace", '(Mutate (expected_revision %s)(mutation %s))' %
                            (fs0.field(snapshot, "revision"), mutation))
    root = base / "project"
    root.mkdir()
    for name in ("state", "results", "home", "config", "client-state", "tmp"):
        (base / name).mkdir()
    (root / "dune-project").write_text("(lang dune 3.17)\n(name resource_inspector_acceptance)\n")
    deny = base / "no-project-execution"
    deny.write_text("#!" + sys.executable + "\nimport sys\nsys.exit('PT6 acceptance forbids project execution')\n")
    deny.chmod(0o700)
    fs0.write_config(root, deny, provider, base / "results")
    session = NativeSession(args, base, root)
    session.env.update(HOME=str(base / "home"), XDG_CONFIG_HOME=str(base / "config"),
                       TMPDIR=str(base / "tmp"), PYTHONDONTWRITEBYTECODE="1",
                       OMP_NUM_THREADS="6", OPENROAD_THREADS="6", _OPENLANE_MAX_CORES="6")
    # The shared native parser handles decimal escaped UTF-8 byte sequences correctly.
    fs0.parse = http_module.parse
    return fs0, session


def stop_session(session):
    if hasattr(session, "log"):
        session.stop()


def resource_snapshot(fs0, snapshot):
    resources = fs0.field(snapshot, "resources")
    require(len(resources) == 1, "Matching PT6 daemon/client must expose resources snapshot")
    return resources[0]


def source_index(fs0, resources, path):
    source = next(s for s in fs0.field(resources, "sources") if fs0.field(s, "path") == str(path.resolve()))
    index = next(i for i in fs0.field(resources, "indexes")
                 if fs0.field(i, "source_id") == fs0.field(source, "id"))
    return source, index


def operation_load(fs0, path, kind="Coarse_run", refresh=False):
    return '(Resources (Load (target (%s %s)) (refresh %s)))' % (
        kind, fs0.sexp(str(path)), str(refresh).lower())


def synthetic_pty_race(args, base, session, fs0, check):
    """Real client navigation while an old target's provider read is in flight."""
    require(args.client and args.client.is_file(), "--pty needs matching --client")
    dashboard = module("resources_synthetic_pty", HERE / "test-fs0-dashboard.py")
    t = dashboard.Terminal(session)
    field, sexp = fs0.field, fs0.sexp

    def key(raw):
        with (base / "pty-keys.jsonl").open("a") as out:
            out.write(json.dumps(dict(hex=raw.hex())) + "\n")
        os.write(t.master, raw)
        t.drain(.1)

    def select(case, expected=("program",)):
        t.palette("Resources: Import retained resource evidence")
        t.capture("race-form-" + case, ["exact absolute directory"])
        key(str(base / "targets" / case).encode())
        key(b"\r")
        t.capture("race-selected-" + case, expected)

    def scroll(label, expected, absent=()):
        pages = []
        for n in range(30):
            pages.append(t.capture(label + "-%02d" % n))
            joined = "\n".join(pages)
            if all(token in joined for token in expected):
                check(not any(token in joined for token in absent), label + ": qualified comparison has no fabricated delta")
                return joined
            key(b"]")
        require(False, "Missing synthetic PTY facts: " + repr(expected))

    try:
        t.capture("race-startup", ["Overview"])
        select("original")
        workspace = session.rpc("workspace")
        resources = next(w for w in field(workspace, "workspaces") if field(w, "preset") == ["resources"])
        tile = next(x for x in field(workspace, "tiles") if field(x, "workspace") == field(resources, "id") and field(x, "kind") == "resources")
        session.mutate(workspace, '(Set_zoom (workspace %s)(tile (%s)))' % (sexp(field(resources, "id")), sexp(field(tile, "id"))))
        t.capture("race-original", ["targets/original", "program"])
        control = base / "targets/original/control.json"
        control.write_text(json.dumps(dict(case="original", generation="late-ui", delay=4,
                                          role="LATE_OLD_SOURCE")))
        started = control.parent / "query-started"
        if started.exists():
            started.unlink()
        key(b"r")
        deadline = time.monotonic() + 5
        while not started.exists():
            require(time.monotonic() < deadline, "PTY delayed refresh start barrier")
            time.sleep(.02)
        # Navigation is submitted before the old result exists, not after a sleep.
        select("augmented")
        session.rpc("asic", wait=True)
        text = t.capture("race-new-source-after-old-reply", ["targets/augmented", "program"], ["LATE_OLD_SOURCE"])
        check("targets/original" not in text, "PTY old target reply cannot replace newly selected explicit source")
        resources_snapshot = resource_snapshot(fs0, session.rpc("asic"))
        _, old_index = source_index(fs0, resources_snapshot, base / "targets/original")
        check(field(field(old_index, "rows")[0], "role") == "LATE_OLD_SOURCE",
              "late old payload actually completed in its own source, not a vacuous race")
        control = base / "targets/augmented/control.json"
        saved_control = control.read_bytes()
        control.write_text(json.dumps(dict(case="invalid", generation="retry-fail")))
        key(b"r")
        t.capture("retry-failed", ["Refresh failed"])
        control.write_bytes(saved_control)
        key(b"r")
        t.capture("retry-success-same-key", ["Validated source", "program"], ["Refresh failed", "Resource read failed"])
        check(True, "PTY reused-key retry clears prior failure after current successful receipt")
        select("empty", ("verified empty inventory",))
        select("old-empty", ("inventory unknown",))
        text = t.capture("old-empty-not-zero", ["inventory unknown"], ["verified empty inventory"])
        check(True, "PTY old empty payload is unknown rather than available zero")
        select("unavailable", ("inventory unavailable", "no bound historical inventory"))
        t.capture("missing-inventory-not-zero", ["inventory unavailable"], ["verified empty inventory"])
        check(True, "PTY missing inventory reason stays distinct from zero resources")
        select("truncated", ("TRUNCATED", "program"))
        t.palette("Resources: Capture comparison A")
        select("estimate-a")
        t.palette("Resources: Capture comparison B")
        t.palette("Resources: Compare captured A / B (c)")
        scroll("truncated-comparison", ["TRUNCATED"])
        check(True, "PTY captured comparison keeps incomplete-projection qualification")
        select("estimate-a")
        t.palette("Resources: Capture comparison A")
        select("estimate-b")
        t.palette("Resources: Capture comparison B")
        t.palette("Resources: Compare captured A / B (c)")
        scroll("final-stage-estimate", ["no measured delta", "estimate"], ["Δ(B−A)"])
        select("missing-estimate")
        t.palette("Resources: Capture comparison B")
        t.palette("Resources: Compare captured A / B (c)")
        scroll("missing-estimate-reason", ["missing-estimate-source", "unavailable measurement; no delta"], ["Δ(B−A)"])
        select("old")
        t.palette("Resources: Capture comparison A")
        t.palette("Resources: Capture comparison B")
        t.palette("Resources: Compare captured A / B (c)")
        scroll("legacy-unknown-no-delta", ["unknown classification", "no measured delta"], ["Δ(B−A)"])
        # Restore the primary source for cache-only restart assertions.
        session.rpc("asic", operation_load(fs0, base / "targets/augmented", refresh=True), wait=True)
        select("augmented")
    finally:
        t.close()


def native_http(args):
    """Backend integration using the frozen operations. PTY acceptance is separate."""
    require(args.daemon, "--http requires an explicit matching --daemon")
    args.daemon = args.daemon.resolve()
    if args.client:
        args.client = args.client.resolve()
    require(args.daemon.is_file(), "Matching native daemon must exist")
    verify(args.example_root, args.fixtures)
    if args.evidence:
        base = args.evidence.resolve()
        require(base.parent.is_dir(), "Evidence parent must exist")
        base.mkdir()
    else:
        base = Path(tempfile.mkdtemp(prefix="resource-inspector-http-", dir="/tmp/opencode"))
    provider = seed_provider(base, args.fixtures)
    fs0, session = native_setup(args, base, provider)
    field, sexp = fs0.field, fs0.sexp
    before = protected(args.example_root)
    result = dict(status="failed", scope="synthetic native HTTP backend acceptance",
                  ui_acceptance="NOT_RUN", checks=[], binaries={str(p): sha(p) for p in (args.daemon, args.client) if p})
    shutil.copyfile(Path(__file__), base / "tested-script.py")

    def check(ok, message):
        result["checks"].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)

    def snapshot(op="Get", wait=False):
        full = session.rpc("asic", op, wait=wait)
        result["last_operations"] = field(full, "operations")
        return resource_snapshot(fs0, full)

    def load_case(case, refresh=False):
        path = base / "targets" / case
        state = snapshot(operation_load(fs0, path, refresh=refresh), wait=True)
        return source_index(fs0, state, path)

    def calls():
        path = base / "provider-calls.jsonl"
        return path.read_bytes() if path.exists() else b""

    try:
        session.start()
        initial = session.rpc("workspace")
        source, index = load_case("augmented")
        sid, digest = field(source, "id"), field(index, "digest")
        check(field(index, "rows") and field(field(index, "rows")[0], "id") == "program", "native resource row identity")
        check(field(source, "target")[0] == "Coarse_run", "coarse import stays distinct from named Register")
        check(not field(session.rpc("asic"), "runs"), "resource import allocates no physical observation")
        baseline = calls()
        load_case("augmented")
        snapshot()
        check(calls() == baseline, "warm Load(false)/Get make no provider query")
        for case in ("original", "empty", "flops", "fallback", "failed", "incompatible"):
            _, other = load_case(case)
            check(field(other, "verdict") == ("fail" if case == "failed" else "not_evaluated" if case == "empty" else "pass"), "native readable fixture: " + case)
            if case == "empty":
                check(not field(other, "rows"), "empty inventory preserved")
            if case in ("flops", "fallback"):
                check(field(field(other, "rows")[0], "final") == "unavailable", "flop ownership remains unavailable")
        entries = []
        for offset in (0, 32, 64):
            state = snapshot('(Resources (Artifacts (source_id %s)(expected_digest %s)(offset %d)(limit 32)))' %
                             (sexp(sid), sexp(digest), offset), wait=True)
            page = next(p for p in field(state, "artifacts") if field(p, "source_id") == sid
                        and int(field(p, "offset")) == offset)
            entries.extend(field(page, "entries"))
        check(len(entries) == 76, "native artifact pagination reaches source 76")
        for section in ("inventory", "geometry", "timing", "electrical"):
            state = snapshot('(Resources (Detail (source_id %s)(expected_digest %s)(resource_id program)(section %s)(offset 0)(limit 16)))' %
                             (sexp(sid), sexp(digest), sexp(section)), wait=True)
            check(any(field(p, "source_id") == sid and field(p, "section") == section and field(p, "items")
                      for p in field(state, "details")), "native exact detail: " + section)
        state = snapshot('(Resources (Read_artifact (source_id %s)(expected_digest %s)(artifact_id %s)(offset 0)(limit 16384)))' %
                         (sexp(sid), sexp(digest), sexp(field(entries[-1], "id"))), wait=True)
        page = next(p for p in field(state, "bytes") if field(p, "source_id") == sid)
        check(bytes.fromhex(field(page, "bytes_hex")) == b"resource source 75\n", "native raw artifact byte oracle")
        def reject(op, text, provider_free=False):
            previous = calls()
            old_keys = {field(o, "key") for o in result["last_operations"]}
            snapshot(op, wait=True)
            new = [o for o in result["last_operations"] if field(o, "key") not in old_keys]
            check(new and all(field(o, "state") == "failed" and field(o, "error") for o in new), text)
            if provider_free:
                check(calls() == previous, text + " before provider query")
        reject('(Resources (Artifacts (source_id %s)(expected_digest %s)(offset 0)(limit 32)))' %
               (sexp(sid), sexp("0" * 64)), "stale digest rejects", True)
        reject('(Resources (Artifacts (source_id %s)(expected_digest %s)(offset 0)(limit 65)))' %
               (sexp(sid), sexp(digest)), "catalog request budget rejects", True)
        reject('(Resources (Detail (source_id %s)(expected_digest %s)(resource_id absent)(section inventory)(offset 0)(limit 16)))' %
               (sexp(sid), sexp(digest)), "unknown resource rejects", True)
        reject('(Resources (Read_artifact (source_id %s)(expected_digest %s)(artifact_id %s)(offset 0)(limit 16385)))' %
               (sexp(sid), sexp(digest), sexp(field(entries[-1], "id"))), "byte request budget rejects", True)
        previous = calls()
        snapshot('(Resources (Detail (source_id %s)(expected_digest %s)(resource_id program)(section geometry)(offset 0)(limit 16)))' %
                 (sexp(sid), sexp(digest)), wait=True)
        check(calls() == previous, "warm detail page reopens provider-free")
        control = base / "targets/augmented/control.json"
        original_control = control.read_bytes()
        control.write_text(json.dumps(dict(case="invalid", generation="failed-refresh")))
        failed_source, retained_index = load_case("augmented", refresh=True)
        check(field(failed_source, "freshness")[0] == "Refresh_failed" and retained_index == index,
              "failed refresh preserves cached facts with explicit failure freshness")
        control.write_bytes(original_control)
        load_case("augmented", refresh=True)
        for mode in ("exit1-pass", "exit0-fail"):
            control.write_text(json.dumps(dict(case=mode, generation=mode)))
            bad_source, unchanged = load_case("augmented", refresh=True)
            check(field(bad_source, "error") and unchanged == index, "exit/verdict disagreement rejects without replacing prior index: " + mode)
        control.write_bytes(original_control)
        recovered_source, recovered_index = load_case("augmented", refresh=True)
        check(not field(recovered_source, "error") and field(recovered_source, "freshness") == "Validated"
              and recovered_index == index, "same-key successful retry clears prior source failure")
        for case, override in (("augmented", 1), ("failed", 0)):
            page_source, page_index = load_case(case, refresh=True)
            page_sid, page_digest = field(page_source, "id"), field(page_index, "digest")
            catalog = snapshot('(Resources (Artifacts (source_id %s)(expected_digest %s)(offset 0)(limit 32)))' %
                               (sexp(page_sid), sexp(page_digest)), wait=True)
            page_catalog = next(p for p in field(catalog, "artifacts") if field(p, "source_id") == page_sid)
            artifact_id = field(field(page_catalog, "entries")[0], "id")
            write_new(base / "query-exit-override.json", {query: override for query in ("detail", "artifacts", "bytes")})
            reject('(Resources (Detail (source_id %s)(expected_digest %s)(resource_id program)(section provenance)(offset 0)(limit 7)))' %
                   (sexp(page_sid), sexp(page_digest)), "detail exit/verdict disagreement rejects: " + case)
            reject('(Resources (Artifacts (source_id %s)(expected_digest %s)(offset 1)(limit 7)))' %
                   (sexp(page_sid), sexp(page_digest)), "catalog exit/verdict disagreement rejects: " + case)
            reject('(Resources (Read_artifact (source_id %s)(expected_digest %s)(artifact_id %s)(offset 1)(limit 7)))' %
                   (sexp(page_sid), sexp(page_digest), sexp(artifact_id)), "byte exit/verdict disagreement rejects: " + case)
            (base / "query-exit-override.json").unlink()
        for case in ("old", "old-empty", "unavailable", "truncated"):
            source_case, index_case = load_case(case)
            if case.startswith("old"):
                check((field(index_case, "inventory_status") if any(k == "inventory_status" for k, _ in index_case) else "Unknown") == "Unknown",
                      "old envelope is readable without fabricated availability: " + case)
                check(field(source_case, "freshness") == "Cached_unverified", "old inventory stays cached-unverified: " + case)
            elif case == "unavailable":
                check(field(index_case, "inventory_status") == "Unavailable" and not field(index_case, "rows")
                      and field(index_case, "inventory_reason"), "unavailable inventory is distinct from available zero")
            else:
                check(field(index_case, "truncated") == "true", "incomplete projection retains truncation flag")
        # Re-admit the primary source after the bounded eight-index fixture churn.
        source, index = load_case("augmented", refresh=True)
        sid, digest = field(source, "id"), field(index, "digest")
        for case in ("invalid", "malformed", "oversize", "row-budget"):
            path = base / "targets" / case
            state = snapshot(operation_load(fs0, path), wait=True)
            bad = next(s for s in field(state, "sources") if field(s, "path") == str(path))
            check(bool(field(bad, "error")), "invalid source is not empty success: " + case)
        large_source, large_index = load_case("detail-budget")
        reject('(Resources (Detail (source_id %s)(expected_digest %s)(resource_id program)(section inventory)(offset 0)(limit 16)))' %
               (sexp(field(large_source, "id")), sexp(field(large_index, "digest"))),
               "over-budget normalized detail response rejects")
        reject('(Resources (Read_artifact (source_id %s)(expected_digest %s)(artifact_id %s)(offset 0)(limit 4096)))' %
               (sexp(sid), sexp(digest), sexp("0" * 64)), "unauthorized opaque artifact rejects")
        delayed_control = base / "targets/original/control.json"
        delayed_control.write_text(json.dumps(dict(case="original", generation="old", delay=.8)))
        delayed_source, delayed_index = load_case("original", refresh=True)
        started = delayed_control.parent / "query-started"
        started.unlink()
        old_sid, old_digest = field(delayed_source, "id"), field(delayed_index, "digest")
        snapshot('(Resources (Detail (source_id %s)(expected_digest %s)(resource_id program)(section provenance)(offset 0)(limit 16)))' %
                 (sexp(old_sid), sexp(old_digest)), wait=False)
        deadline = time.monotonic() + 5
        while not started.exists():
            require(time.monotonic() < deadline, "native delayed page start barrier")
            time.sleep(.02)
        delayed_control.write_text(json.dumps(dict(case="original", generation="new")))
        _, new_index = load_case("original", refresh=True)
        state = snapshot()
        check(field(new_index, "digest") != old_digest and not any(
            field(page, "source_id") == old_sid and field(page, "digest") == old_digest
            for page in field(state, "details")), "genuinely late old page cannot publish after source refresh")
        check(any(field(o, "state") in ("completed", "failed") and "Detail" in field(o, "key")
                  and old_digest in field(o, "key") for o in result["last_operations"]),
              "delayed old page settles and serialized refresh clears its publication")
        (base / "unsupported-capability").touch()
        state = snapshot(operation_load(fs0, base / "targets/named"), wait=True)
        unsupported = next(s for s in field(state, "sources") if field(s, "target") == ["Coarse_run", str(base / "targets/named")])
        check(field(unsupported, "freshness")[0] == "Unsupported", "CLI4 provider without resource capability is Unsupported")
        (base / "unsupported-capability").unlink()
        if args.pty:
            synthetic_pty_race(args, base, session, fs0, check)
            result["ui_acceptance"] = "synthetic_late_reply_passed"
        # Freeze a provider-free warm cache and restart only the directly owned daemon.
        (base / "deny-queries").touch()
        saved_workspace = session.rpc("workspace")
        stop_session(session)
        session.start()
        restored = snapshot()
        cached_source, cached_index = source_index(fs0, restored, base / "targets/augmented")
        check(field(cached_source, "freshness") == "Cached_unverified", "restart marks evidence cached/unverified")
        check(cached_index == index, "restart preserves exact cached index")
        baseline = calls()
        load_case("augmented")
        check(calls() == baseline, "restart warm load remains provider-free")
        check(session.rpc("workspace") == saved_workspace, "resource reads/restart preserve workspace layout and bindings")
        check(field(initial, "main_context") == field(saved_workspace, "main_context"), "Main context unchanged")
        stop_session(session)
        caches = list((base / "state").glob("asic-resources-*.sexp"))
        require(len(caches) == 1, "One private resource cache for repair test")
        old_cache = caches[0].read_text()
        recorded_provider = field(cached_source, "provider_identity")
        require(recorded_provider in old_cache, "Exact persisted provider identity witness")
        caches[0].write_text(old_cache.replace(recorded_provider, "f" * 64, 1))
        (base / "deny-queries").unlink()
        session.start()
        broken = session.rpc("asic")
        check(field(broken, "cache_error") and not field(resource_snapshot(fs0, broken), "indexes"),
              "ordinary changed cache metadata is rejected before publication")
        repaired_source, repaired_index = load_case("augmented", refresh=True)
        repaired = session.rpc("asic")
        check(not field(repaired, "cache_error") and not field(repaired_source, "error")
              and repaired_index == index, "successful explicit cache repair clears live corruption diagnostic")
        result["status"] = "http_and_synthetic_pty_passed" if args.pty else "http_passed_pty_pending"
    finally:
        stop_session(session)
        result["protected_unchanged"] = protected(args.example_root) == before
        if not result["protected_unchanged"]:
            result["status"] = "failed"
        write_new(base / "result.json", result)
        print(json.dumps(dict(evidence=str(base), status=result["status"], checks=len(result["checks"]),
                              ui_acceptance=result["ui_acceptance"]), indent=2))
    require(result["protected_unchanged"], "Protected example state unchanged")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example-root", type=Path, default=DEFAULT_EXAMPLE)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--smoke", action="store_true", help="synthetic provider checks only; no HTTP/PTY")
    mode.add_argument("--http", action="store_true", help="matching prebuilt native HTTP backend acceptance; PTY separate")
    parser.add_argument("--daemon", type=Path)
    parser.add_argument("--client", type=Path)
    parser.add_argument("--pty", action="store_true", help="synthetic old-target late-reply PTY test with --http")
    parser.add_argument("--outer-timeout", type=int, default=60)
    parser.add_argument("--evidence", type=Path, help="new output directory for --smoke")
    args = parser.parse_args()
    if args.smoke:
        smoke(args)
        return
    if args.http:
        native_http(args)
        return
    if not (args.prepare or args.verify):
        parser.exit(2, "Choose --prepare, --verify, --smoke, or --http with explicit matching binaries\n")
    result = (prepare if args.prepare else verify)(args.example_root.resolve(), args.fixtures.resolve())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
