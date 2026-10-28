#!/usr/bin/env python3
"""Native PT6 saved custom layout + explicit Resources builtin recovery.

Metadata-only project, private state and strict FS3 tool guards. The synthetic pin
is only a layout witness; there is no SRAM, producer allocation or ASIC provider.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag, dest in (("daemon", "daemon"), ("client", "terminal"),
                       ("workspace-cli", "workspace_cli"), ("setup", "setup")):
        parser.add_argument("--" + flag, dest=dest, type=Path, required=True)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    for name in ("daemon", "terminal", "workspace_cli", "setup"):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    g = module("pt6_saved_groundwork", HERE / "test-resource-inspector.py")
    c = module("pt6_saved_composition", HERE / "test-workspace-config.py")
    field, sexp = c.field, c.sexp
    before_protected = g.protected(g.DEFAULT_EXAMPLE)
    os.umask(0o077)
    if args.evidence:
        args.evidence = args.evidence.resolve()
        g.require(args.evidence.is_relative_to("/tmp/opencode"), "Private evidence root required")
        args.evidence.mkdir()
    else:
        args.evidence = Path(tempfile.mkdtemp(prefix="resources-saved-layout-", dir="/tmp/opencode"))
    test = c.Acceptance(args)
    test.result.update(scope="metadata-only saved-layout acceptance; no SRAM observation",
                       script_sha256=g.sha(Path(__file__)),
                       binaries={str(getattr(args, key)): g.sha(getattr(args, key))
                                 for key in ("daemon", "terminal", "workspace_cli", "setup")})
    terminal = None

    def wait_registry(predicate, label):
        deadline = time.monotonic() + 20
        while True:
            state = test.workspace()
            if predicate(state):
                return state
            g.require(time.monotonic() < deadline, label)
            terminal.drain(.1)

    try:
        (test.root / "dune-project").write_text("(lang dune 3.22)\n(name resources_saved_layout)\n")
        (test.root / "dune").write_text("(dirs)\n")
        test.command(args.setup, ["--root", test.root, "--project-name", "FS3 acceptance"], "setup")
        config_path = args.evidence / "legacy-custom-only.sexp"
        config = c.custom_config()
        definition = c.replace(field(config, "definitions")[0], "key", "resources")
        config = c.replace(config, "definitions", [definition])
        windows = []
        for window in field(config, "windows"):
            instances = [c.replace(instance, "definition", ["Custom", "resources"])
                         for instance in field(window, "workspaces")]
            windows.append(c.replace(window, "workspaces", instances))
        config = c.replace(config, "windows", windows)
        config_path.write_text(sexp(config) + "\n")
        test.start()
        terminal = c.Terminal(test, "custom-bootstrap", config_path)
        terminal.wait("ready", ["Config one", "project-tests", "execution"])
        initial = wait_registry(lambda state: field(state, "configuration_pending") == "false", "custom bootstrap")
        test.check(len(field(initial, "workspaces")) == 2 and not any(
            field(w, "preset") == ["resources"] for w in field(initial, "workspaces")),
            "Authored custom-only session initially has no Resources builtin")
        test.check(all(field(field(mapping, "definition"), "key") == "resources"
                       for mapping in field(initial, "config_workspaces")),
                   "Legacy explicit Custom resources key remains authored custom rather than new builtin")
        workspace = field(initial, "workspaces")[0]
        wid = field(workspace, "id")
        tile = next(t for t in field(initial, "tiles") if field(t, "workspace") == wid)
        tid = field(tile, "id")
        state = test.mutate(initial, ["Make_independent", wid])
        state = test.mutate(state, ["Rename_workspace", ["workspace", wid], ["name", "Saved legacy desk"]])
        state = test.mutate(state, ["Resize_tile", ["tile", tid], ["geometry", [
            ["x", "7"], ["y", "3"], ["width", "37"], ["height", "9"]]]])
        state = test.mutate(state, ["Set_tile_binding", ["tile", tid], ["binding", ["Pin_run", [
            ["backend", "layout-fixture"], ["id", "saved-pin-only"], ["build", []], ["label", []]]]]])
        terminal.wait("saved-name", ["Saved legacy desk"])
        terminal.close()
        terminal = None
        config_path.unlink()
        disk = test.disk()
        test.close()
        test.start()
        terminal = c.Terminal(test, "saved-session")
        terminal.wait("ready", ["Saved legacy desk", "project-tests", "execution"])
        test.check(test.workspace() == state and test.disk() == disk,
                   "Native restart without authored config preserves exact saved layout/context/pin and adds no Resources")
        (args.evidence / "saved-before-resources.sexp").write_text(sexp(state) + "\n")
        terminal.palette("Inspect resources (open Resources workspace)")
        opened = wait_registry(lambda current: any(field(w, "preset") == ["resources"]
                               for w in field(current, "workspaces")), "explicit Resources creation")
        terminal.wait("resources-open", ["Resources", "No loaded resource index"])
        created = [w for w in field(opened, "workspaces") if field(w, "preset") == ["resources"]]
        test.check(len(created) == 1 and len(field(opened, "workspaces")) == len(field(state, "workspaces")) + 1,
                   "Explicit Inspect resources creates exactly one builtin in saved custom session")
        test.check(all(w in field(opened, "workspaces") for w in field(state, "workspaces"))
                   and all(t in field(opened, "tiles") for t in field(state, "tiles"))
                   and all(context in field(opened, "contexts") for context in field(state, "contexts")),
                   "Resources creation preserves every old workspace, geometry, pin and independent context")
        test.check(field(opened, "config_workspaces") == field(state, "config_workspaces")
                   and field(opened, "config_windows") == field(state, "config_windows"),
                   "Explicit builtin creation preserves authored custom provenance/mappings")
        template = c.parse(test.command(args.workspace_cli, ["starter", "resources"], "resources-starter"))
        exported = c.parse(test.cli("export", [field(created[0], "id")], "export-resources"))
        test.check(exported == template, "Recovered Resources uses exact canonical stock template")
        terminal.palette("Inspect resources (open Resources workspace)")
        terminal.wait("resources-reopened", ["Resources", "No loaded resource index"])
        test.check(test.workspace() == opened, "Repeated Resources open does not duplicate or reset saved layout")
        terminal.close()
        terminal = None
        test.close()
        test.start()
        terminal = c.Terminal(test, "restarted-with-resources")
        terminal.wait("ready", ["Resources", "No loaded resource index"])
        test.check(test.workspace() == opened, "Resources builtin and all prior saved layout/pins survive daemon/client restart")
        test.quiet()
        test.result["status"] = "passed"
    except BaseException:
        test.result["failure"] = traceback.format_exc()
        traceback.print_exc()
    finally:
        if terminal:
            terminal.close()
        test.close()
        test.result["protected_unchanged"] = before_protected == g.protected(g.DEFAULT_EXAMPLE)
        if not test.result["protected_unchanged"]:
            test.result["status"] = "failed"
        (args.evidence / "result.json").write_text(json.dumps(test.result, indent=2) + "\n")
        print(json.dumps(dict(status=test.result["status"], evidence=str(args.evidence), checks=len(test.result["checks"]))))
    sys.exit(0 if test.result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
