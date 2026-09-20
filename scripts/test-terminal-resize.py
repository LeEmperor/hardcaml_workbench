#!/usr/bin/env python3
"""Exercise Bonsai Term resize repaint and recovery through a pseudoterminal."""

import argparse
import fcntl
import os
import pty
import re
import select
import signal
import struct
import subprocess
import tempfile
import termios
import time


def set_size(fd: int, columns: int, rows: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))


def read_available(fd: int, duration: float = 0.5) -> bytes:
    deadline = time.monotonic() + duration
    chunks = []
    while time.monotonic() < deadline:
        readable, _, _ = select.select([fd], [], [], min(0.05, deadline - time.monotonic()))
        if not readable:
            continue
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            break
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("client")
    parser.add_argument("--project-root")
    parser.add_argument("--environment", default="inherited")
    parser.add_argument("--expect-live-discovery", action="store_true")
    args = parser.parse_args()

    master, slave = pty.openpty()
    initial_size = (120, 40) if args.expect_live_discovery else (80, 24)
    set_size(slave, *initial_size)
    runtime = tempfile.TemporaryDirectory(prefix="hardcaml-workbench-resize-")
    diagnostics = os.path.join(runtime.name, "resize.log")
    command = [args.client, "--diagnostics-file", diagnostics]
    if args.project_root:
        command.extend(["--project-root", args.project_root, "--environment", args.environment])
    environment = os.environ.copy()
    environment["XDG_RUNTIME_DIR"] = runtime.name
    process = subprocess.Popen(
        command,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=environment,
        close_fds=True,
        start_new_session=True,
    )
    os.close(slave)
    try:
        initial = read_available(master, 2.0)
        if not initial:
            raise RuntimeError("client produced no initial terminal frame")
        if b"PROJECT / GENERIC DUNE" not in initial:
            raise RuntimeError("initial frame did not contain the bounded project pane")
        if b"Daemon instance:" in initial:
            raise RuntimeError("verbose daemon identity leaked into the default project view")
        if args.expect_live_discovery:
            discovery = initial
            deadline = time.monotonic() + 60
            expected = (b"Integration: Driver", b"Four-bit counter")
            while time.monotonic() < deadline and not all(value in discovery for value in expected):
                if process.poll() is not None:
                    raise RuntimeError("client exited while waiting for live discovery")
                discovery += read_available(master)
            missing = [value for value in expected if value not in discovery]
            if missing:
                raise RuntimeError(
                    f"attached client did not render live discovery without input: {missing!r}"
                )
        stages = [(120, 40), (40, 10), (1, 1), (80, 24), (100, 24), (80, 24)]
        evidence = []
        for columns, rows in stages:
            set_size(master, columns, rows)
            os.kill(process.pid, signal.SIGWINCH)
            output = read_available(master)
            if process.poll() is not None:
                raise RuntimeError(f"client exited after resize to {columns}x{rows}")
            if not output:
                raise RuntimeError(f"client did not repaint after resize to {columns}x{rows}")
            evidence.append(f"{columns}x{rows}:{len(output)}")
        os.write(master, b"d")
        details = read_available(master)
        if b"CONNECTION DETAILS" not in details or b"Daemon instance:" not in details:
            raise RuntimeError("connection details view did not expose daemon diagnostics")
        scrolled_details = details
        for _ in range(30):
            os.write(master, b"]")
            scrolled_details += read_available(master, 0.1)
        for label in (b"Requested environment:", b"Resolved environment:", b"Dune version:"):
            if label not in scrolled_details:
                raise RuntimeError(f"scrolled connection details did not expose {label!r}")
        os.write(master, b"d")
        project = read_available(master)
        if b"PROJECT / GENERIC DUNE" not in project:
            raise RuntimeError("project pane did not recover after closing connection details")
        os.write(master, b"q")
        process.wait(timeout=5)
        if process.returncode != 0:
            raise RuntimeError(f"client exited with status {process.returncode}")
        with open(diagnostics, encoding="utf-8") as channel:
            diagnostics_text = channel.read()
        for columns, rows in [(40, 10), (1, 1), (80, 24), (100, 24)]:
            marker = f"dimensions width={columns} height={rows}"
            if marker not in diagnostics_text:
                raise RuntimeError(f"missing diagnostic marker: {marker}")
        print("Terminal resize checks: passed")
        if args.expect_live_discovery:
            print("Attached-client live discovery: passed")
        print("Repaint bytes: " + ", ".join(evidence))
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        os.close(master)
        metadata = os.path.join(runtime.name, "hardcaml-workbench", "daemon.sexp")
        if os.path.exists(metadata):
            with open(metadata, encoding="utf-8") as channel:
                match = re.search(r"\(pid ([0-9]+)\)", channel.read())
            if match:
                try:
                    os.kill(int(match.group(1)), signal.SIGTERM)
                except ProcessLookupError:
                    pass
        runtime.cleanup()


if __name__ == "__main__":
    main()
