#!/usr/bin/env python3
"""C-owned PT6 broad/native regression recorder. Existing private fixture routes only.

Builds and each native suite hold the shared PT6 lock. All nested fixture builds
are already explicit six-job Dune calls. A new receipt directory is required.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WB = HERE.parent
EXAMPLE = WB.parent / "hardcaml_asic_example"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("broad", "unified", "checklist", "layout", "saved-layout", "asic-full"), required=True)
    parser.add_argument("--resume", action="store_true", help="ASIC-only resume without forcing already completed tests")
    parser.add_argument("--output", type=Path, required=True, help="new receipt directory")
    args = parser.parse_args()
    g = module("pt6_regression_groundwork", HERE / "test-resource-inspector.py")
    output = args.output.resolve()
    g.require(output.parent.is_dir(), "Receipt parent exists")
    output.mkdir()
    before = g.protected(EXAMPLE)
    g.write_new(output / "protected-before.json", before)
    shutil.copyfile(Path(__file__), output / "tested-recorder.py")
    bins = {"daemon": WB / "_build/default/daemon/main.exe",
            "client": WB / "_build/default/terminal/main.exe",
            "preset-export": WB / "_build/default/terminal/workspaces/export_presets.exe",
            "workspace-cli": WB / "_build/default/workspace_cli/main.exe",
            "setup": WB / "_build/default/setup/main.exe"}

    def hashes():
        return {name: dict(path=str(path), sha256=g.sha(path)) for name, path in bins.items() if path.is_file()}

    def sources():
        roots = ("adapters", "backend", "daemon", "native_http", "project_integration", "protocol",
                 "provider", "setup", "terminal", "web", "workspace_cli")
        return {str(p.relative_to(WB)): g.sha(p) for root in roots for p in sorted((WB / root).rglob("*"))
                if p.is_file() and (p.suffix in (".ml", ".mli") or p.name == "dune")}

    native_root = Path("/tmp/opencode") / ("resource-inspector-regression-" + args.suite + "-" + secrets.token_hex(6))
    lock = ["flock", "/tmp/opencode/workbench-pt6-build.lock"]
    cwd = WB
    if args.suite == "asic-full":
        cwd = WB.parent / "hardcaml_asic"
        command = ["flock", "/tmp/opencode/asic-pt6-build.lock", str(HERE / "with-switch.sh"),
                   "dune", "runtest", "-j6"] + ([] if args.resume else ["--force"])
        timeout = 2400
    elif args.suite == "broad":
        command = lock + [str(HERE / "with-switch.sh"), "dune", "build", "-j6", "--force",
                          "@runtest", "@all", "@lint", *map(str, (p.relative_to(WB) for p in bins.values()))]
        timeout = 1800
    else:
        name = {"unified": "test-unified-fresh-prefix.py", "checklist": "test-checklist-launch-workflow.py",
                "layout": "test-default-layout-restore.py", "saved-layout": "test-resource-inspector-saved-layout.py"}[args.suite]
        script = HERE / name
        shutil.copyfile(script, output / ("tested-" + name))
        command = lock + [sys.executable, "-B", str(script), "--evidence", str(native_root)]
        flags = ("daemon", "client", "workspace-cli", "setup") if args.suite in ("layout", "saved-layout") else ("daemon", "client", "preset-export")
        for flag in flags:
            command += ["--" + flag, str(bins[flag])]
        if args.suite not in ("layout", "saved-layout"):
            command += ["--timeout", "1200"]
        timeout = 900 if args.suite in ("layout", "saved-layout") else 1260
    receipt = dict(status="failed", suite=args.suite, command=command, cwd=str(cwd), resume=args.resume, timeout=timeout, jobs=6,
                   binaries_before=hashes(), sources_before=sources(), native_evidence=str(native_root),
                   recorder_sha256=g.sha(output / "tested-recorder.py"))
    started = time.monotonic()
    process = None
    try:
        with (output / "command.stdout").open("wb") as out, (output / "command.stderr").open("wb") as err:
            process = subprocess.Popen(command, cwd=cwd, stdout=out, stderr=err, start_new_session=True,
                                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="6", OPENROAD_THREADS="6"))
            try:
                receipt["exit"] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                receipt["timed_out"] = True
                os.killpg(process.pid, signal.SIGINT)
                try:
                    receipt["exit"] = process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    receipt["exit"] = process.wait(timeout=10)
        if args.suite not in ("broad", "asic-full") and (native_root / "result.json").is_file():
            result = g.load(native_root / "result.json")
            receipt["native_result"] = result
            receipt["native_result_sha256"] = g.sha(native_root / "result.json")
        if receipt["exit"] == 0 and not receipt.get("timed_out"):
            receipt["status"] = "passed"
    finally:
        receipt["seconds"] = time.monotonic() - started
        receipt["binaries_after"] = hashes()
        receipt["sources_after"] = sources()
        receipt["sources_unchanged_during_run"] = receipt["sources_before"] == receipt["sources_after"]
        after = g.protected(EXAMPLE)
        g.write_new(output / "protected-after.json", after)
        receipt["protected_unchanged"] = before == after
        if not receipt["protected_unchanged"]:
            receipt["status"] = "failed"
        for name in ("command.stdout", "command.stderr"):
            receipt[name + "_sha256"] = g.sha(output / name)
        g.write_new(output / "receipt.json", receipt)
        print(json.dumps(dict(output=str(output), status=receipt["status"], exit=receipt.get("exit"),
                              seconds=receipt["seconds"], sources_unchanged=receipt["sources_unchanged_during_run"],
                              protected_unchanged=receipt["protected_unchanged"],
                              checks=len(receipt.get("native_result", {}).get("checks", []))), indent=2))
    sys.exit(0 if receipt["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
