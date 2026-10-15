#!/usr/bin/env python3
"""Raw Ctrl-C PTY regression matrix; stdlib only, existing binaries, no builds.

Evidence is retained under /tmp/opencode. Exit 1 means any case failed (including
a three-second interrupt timeout); all cases run even when earlier cases fail.
Only the test's own processes are terminated, using SIGTERM. The disposable
generic Dune project has no driver, ASIC configuration, or executable targets.
Only hello and read-only snapshot metadata are requested by this harness; the
interactive client opens the project normally (which may run dune describe).
"""

import argparse
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import sys
import tempfile
import termios
import time
import traceback


# Reuse the FS0 transport/parser without writing __pycache__ in the checkout.
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location(
    "fs0", Path(__file__).with_name("test-fs0.py"))
FS0 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FS0)


def digest(path):
    with open(path, "rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def flags(fd):
    local = termios.tcgetattr(fd)[3]
    return {name: bool(local & getattr(termios, name))
            for name in ("ISIG", "ECHO", "ICANON")}


def terminate(process):
    if process is not None and process.poll() is None:
        process.terminate()
        process.wait(timeout=20)


def metadata(session):
    hello = session.raw("/api/hello")
    assert FS0.field(hello, "instance_id") == session.metadata["instance_id"]
    snapshot = session.raw("/api/v1/snapshot", [
        ["instance_id", session.metadata["instance_id"]]])
    assert snapshot[0] == "Ok", snapshot
    payload = FS0.record(snapshot[1])
    # Snapshot covers all supervisor jobs, rather than only generic attempts.
    assert payload["jobs"] == [], f"Unexpected jobs: {payload['jobs']}"
    assert payload["artifacts"] == [], "Unexpected job artifacts"
    asic_state = list(session.state_dir.glob("asic-*"))
    assert not asic_state, f"Unexpected persisted ASIC state: {asic_state}"
    return dict(daemon_alive=session.process.poll() is None, jobs=payload["jobs"],
                artifacts=payload["artifacts"], asic_state_files=[],
                project_count=len(payload["projects"]))


def exercise(session, name, setup):
    stem = session.evidence / name
    result = dict(case=name, passed=False, errors=[], keys=[])
    chunks = []
    master, slave = pty.openpty()
    process = None
    started = time.monotonic()

    def drain(seconds):
        deadline = time.monotonic() + seconds
        data = bytearray()
        while time.monotonic() < deadline:
            if select.select([master], [], [], min(.025, max(0, deadline-time.monotonic())))[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                data.extend(chunk)
        chunks.append(bytes(data))
        return bytes(data)

    def send(label, data):
        result["keys"].append(dict(label=label, hex=data.hex(),
                                   seconds=time.monotonic()-started))
        assert os.write(master, data) == len(data)

    try:
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 180, 0, 0))
        result["tty_before"] = flags(slave)
        assert all(result["tty_before"].values()), "PTY did not start cooked"
        argv = [str(session.args.client), "--connect", session.url,
                "--project-root", str(session.root), "--environment", "inherited"]
        result["argv"] = argv
        process = subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave,
                                   cwd=session.root, start_new_session=True,
                                   env=dict(session.env, TERM="xterm-256color"))
        result["pid"] = process.pid
        initial = b""
        deadline = time.monotonic() + 20
        while b"Overview" not in initial or flags(slave)["ISIG"]:
            assert process.poll() is None, "Client exited before workspace rendered"
            assert time.monotonic() < deadline, "Workspace startup timeout"
            initial += drain(.1)
        drain(.3)
        result["tty_running"] = flags(slave)
        assert not any(result["tty_running"].values()), "Client did not enter raw mode"
        for label, data, marker in setup:
            send(label, data)
            output = drain(.3)
            if marker:
                assert marker in output, f"Missing setup marker {marker!r}"
        assert process.poll() is None, "Client exited during setup"
        result["metadata_before_interrupt"] = metadata(session)
        interrupt_at = time.monotonic()
        send("raw Ctrl-C", b"\x03")
        deadline = interrupt_at + 3
        while process.poll() is None and time.monotonic() < deadline:
            drain(min(.025, max(0, deadline-time.monotonic())))
        result["interrupt_seconds"] = time.monotonic() - interrupt_at
        result["hung"] = process.poll() is None
        result["returncode_before_cleanup"] = process.poll()
        result["tty_after_interrupt"] = flags(slave)
        if result["hung"]:
            result["errors"].append("raw Ctrl-C did not exit within 3 seconds")
        else:
            if process.returncode != 0:
                result["errors"].append(f"Client exit status {process.returncode}")
            if result["tty_after_interrupt"] != result["tty_before"]:
                result["errors"].append("ISIG/ECHO/ICANON were not restored")
        result["metadata_after_interrupt"] = metadata(session)
        assert result["metadata_after_interrupt"]["daemon_alive"], "Daemon exited with client"
    except Exception:
        result["errors"].append(traceback.format_exc())
    finally:
        try:
            result["cleanup_sigterm"] = process is not None and process.poll() is None
            terminate(process)
            drain(.1)
            result["returncode_after_cleanup"] = process.poll() if process else None
            result["metadata_after_client_exit"] = metadata(session)
            assert result["metadata_after_client_exit"]["daemon_alive"], "Daemon exited"
        except Exception:
            result["errors"].append(traceback.format_exc())
        os.close(master)
        os.close(slave)
        stem.with_suffix(".ansi").write_bytes(b"".join(chunks))
        stem.with_suffix(".keys.json").write_text(json.dumps(result["keys"], indent=2)+"\n")
        result["ansi_sha256"] = digest(stem.with_suffix(".ansi"))
        result["passed"] = not result["errors"]
        stem.with_suffix(".json").write_text(json.dumps(result, indent=2)+"\n")
    return result


def main():
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", type=Path, default=repo / "_build/default/terminal/main.exe")
    parser.add_argument("--daemon", type=Path, default=repo / "_build/default/daemon/main.exe")
    args = parser.parse_args()
    args.client, args.daemon = args.client.resolve(), args.daemon.resolve()
    evidence = Path(tempfile.mkdtemp(prefix="workbench-terminal-interrupt-", dir="/tmp/opencode"))
    print(f"Evidence: {evidence}", flush=True)
    root = evidence / "project"
    root.mkdir()
    (root / "dune-project").write_text("(lang dune 3.0)\n(name interrupt_fixture)\n")
    (root / "dune").write_text("; Metadata-only fixture: no executable or build rules.\n")
    for directory in ("home", "runtime", "tmp", "cache", "config"):
        (evidence / directory).mkdir()
    session = FS0.Session(args, evidence, root)
    session.env.update(HOME=str(evidence / "home"), XDG_RUNTIME_DIR=str(evidence / "runtime"),
                       XDG_CACHE_HOME=str(evidence / "cache"), XDG_CONFIG_HOME=str(evidence / "config"),
                       TMPDIR=str(evidence / "tmp"))
    paths = [args.client, args.daemon, Path(__file__).resolve(),
             Path(__file__).with_name("test-fs0.py").resolve()]
    report = dict(evidence=str(evidence), hashes_before={str(p): digest(p) for p in paths},
                  cases=[], errors=[])
    try:
        session.start()
        report["daemon_pid"] = session.process.pid
        report["initial_metadata"] = metadata(session)
        cases = [
            ("normal", []),
            ("filter-active", [("open filter", b"/", b"FILTER INPUT")]),
            ("palette-active", [("open palette", b" cc", b"COMMAND PALETTE")]),
            ("unfinished-paste", [("start bracketed paste", b"\x1b[200~", None),
                                  ("paste text", b"interrupt_probe", None)]),
            ("completed-paste", [("start bracketed paste", b"\x1b[200~", None),
                                 ("paste text", b"interrupt_probe", None),
                                 ("end bracketed paste", b"\x1b[201~", None)]),
        ]
        for name, setup in cases:
            result = exercise(session, name, setup)
            report["cases"].append(result)
            print(f"{name}: {'PASS' if result['passed'] else 'FAIL'} "
                  f"(hung={result.get('hung')}, exit={result.get('returncode_before_cleanup')})",
                  flush=True)
    except Exception:
        report["errors"].append(traceback.format_exc())
    finally:
        try:
            report["daemon_alive_before_cleanup"] = session.process is not None and session.process.poll() is None
            terminate(session.process)
            report["daemon_returncode_after_sigterm"] = session.process.poll() if session.process else None
        except Exception:
            report["errors"].append(traceback.format_exc())
        if hasattr(session, "log"):
            session.log.close()
        report["hashes_after"] = {str(p): digest(p) for p in paths}
        if report["hashes_before"] != report["hashes_after"]:
            report["errors"].append("Binary or harness hash changed during test")
        report["passed"] = (len(report["cases"]) == 5 and not report["errors"]
                            and all(case["passed"] for case in report["cases"]))
        (evidence / "results.json").write_text(json.dumps(report, indent=2)+"\n")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
