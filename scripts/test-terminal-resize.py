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


def terminal_text(output: bytes) -> bytes:
    """Strip CSI styling/cursor controls from a captured full repaint or notice."""
    return re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("client")
    parser.add_argument("--project-root")
    parser.add_argument("--environment", default="inherited")
    parser.add_argument("--expect-project-name")
    parser.add_argument("--expect-live-discovery", action="store_true")
    parser.add_argument("--expect-hierarchy", action="store_true")
    args = parser.parse_args()

    master, slave = pty.openpty()
    initial_size = (120, 40) if args.expect_live_discovery or args.expect_hierarchy else (80, 24)
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
        if b"PROJECT / GENERIC DUNE" not in initial and b"Overview |" not in initial:
            raise RuntimeError("initial frame did not contain the project or workspace host")
        if b"Daemon instance:" in initial:
            raise RuntimeError("verbose daemon identity leaked into the default project view")
        if args.expect_live_discovery or args.expect_hierarchy:
            # The host exposes discovery as an execution attempt and exposes the
            # resulting targets/configurations as commands, not an old left pane.
            # Find execution by identity, independent of the preset's tile order,
            # select the attempt,
            # then wait for its event-driven completion without further input.
            for _ in range(16):
                os.write(master, b"\t")
                focused = read_available(master, 0.2)
                if b"> execution [PROJECT]" in focused:
                    break
            else:
                raise RuntimeError("could not focus the execution tile")
            os.write(master, b"j")
            discovery = focused + read_available(master)
            deadline = time.monotonic() + 60
            expected = (b"> execution [PROJECT]", b"STATUS: Complete")
            while time.monotonic() < deadline and not all(value in discovery for value in expected):
                if process.poll() is not None:
                    raise RuntimeError("client exited while waiting for live discovery")
                discovery += read_available(master)
            missing = [value for value in expected if value not in discovery]
            if missing:
                raise RuntimeError(
                    f"attached client did not render live discovery without input: {missing!r}; "
                    f"recent output: {discovery[-4096:]!r}"
                )
            os.write(master, b" ccGenerate RTL")
            commands = read_available(master)
            for label in (
                b"Generate RTL: Four-bit counter / 4-bit counter",
                b"Generate RTL: Four-bit counter / 8-bit counter",
            ):
                if label not in commands:
                    raise RuntimeError(f"discovery did not populate host commands: {label!r}")
            os.write(master, b"\x1b")
            read_available(master)
        if args.expect_hierarchy:
            # The Fit dashboard intentionally clips long job IDs in small cards.
            # Zoom the focused execution tile before asserting the exact ID below.
            os.write(master, b" ccZoom focused tile")
            read_available(master)
            os.write(master, b"\r")
            read_available(master)
            os.write(master, b"g")
            submission = read_available(master)
            deadline = time.monotonic() + 60
            submitted = re.search(rb"Submitted RTL as ([-a-zA-Z0-9]+-job-[0-9]+)",
                                  terminal_text(submission))
            while submitted is None and time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("client exited while submitting RTL generation")
                submission += read_available(master)
                submitted = re.search(rb"Submitted RTL as ([-a-zA-Z0-9]+-job-[0-9]+)",
                                      terminal_text(submission))
            if submitted is None:
                raise RuntimeError(f"no RTL submission identity received: {submission!r}")
            generation_id = submitted.group(1)
            # The submission notice is emitted after the exact job is added.
            # Move from discovery to that newer job, and check its identity,
            # rather than inferring selection from a status shared by both jobs.
            os.write(master, b"k")
            selection = read_available(master)
            # Notty emits changed cells, not complete frames. If both jobs are
            # already Complete, selection need not repaint STATUS at all. A
            # deterministic resize requests a full current-state projection; it
            # neither changes the selected job nor waits for generation to finish.
            set_size(master, initial_size[0] + 1, initial_size[1])
            os.kill(process.pid, signal.SIGWINCH)
            generation = read_available(master)
            selected_identity = b"> " + generation_id + b" "
            if selected_identity not in terminal_text(generation):
                raise RuntimeError(
                    f"execution tile did not select submitted RTL job {generation_id!r}; "
                    f"submission: {submission!r}; selection: {selection!r}; "
                    f"current repaint: {generation!r}"
                )
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and b"STATUS: Complete" not in terminal_text(generation):
                if process.poll() is not None:
                    raise RuntimeError("client exited while waiting for hierarchy generation")
                generation += read_available(master)
            if b"STATUS: Complete" not in terminal_text(generation):
                raise RuntimeError(
                    f"attached client did not observe RTL completion for {generation_id!r}; "
                    f"submission: {submission!r}; selection: {selection!r}; "
                    f"current repaint/updates: {generation!r}"
                )
            os.write(master, b"h")
            hierarchy = b""
            deadline = time.monotonic() + 10
            expected_hierarchy = (b"HARDWARE HIERARCHY [current]", b"u_counter_0", b"u_counter_1")
            while time.monotonic() < deadline and not all(
                value in hierarchy for value in expected_hierarchy
            ):
                hierarchy += read_available(master)
            missing = [value for value in expected_hierarchy if value not in hierarchy]
            if missing:
                raise RuntimeError(f"hierarchy view was incomplete: {missing!r}")
            os.write(master, b"m")
            historical = read_available(master)
            if b"HARDWARE HIERARCHY [historical]" not in historical:
                raise RuntimeError("older hierarchy was not labeled historical after selection changed")
            os.write(master, b"m")
            current = read_available(master)
            if b"HARDWARE HIERARCHY [current]" not in current:
                raise RuntimeError("hierarchy did not return to current after restoring selection")
            os.write(master, b"o")
            selected = read_available(master)
            if b"Node instance: u_counter_0" not in selected:
                raise RuntimeError("hierarchy node navigation did not update the inspector")
            os.write(master, b"u")
            root_selected = read_available(master)
            if b"Node instance: <root>" not in root_selected:
                raise RuntimeError("hierarchy navigation did not return to the root")
            os.write(master, b"e")
            collapsed = read_available(master)
            if b">+ <root>" not in collapsed:
                raise RuntimeError("hierarchy root did not collapse")
            os.write(master, b"e")
            expanded = read_available(master)
            if (
                b">- <root>" not in expanded
                or b"u_counter_0" not in expanded
                or b"u_counter_1" not in expanded
            ):
                raise RuntimeError("hierarchy root did not re-expand")
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
        # Dimension diagnostics belong to the legacy inspector renderer. Exercise
        # its resize path as well as the default workspace host above, rather than
        # assuming the host emits those legacy-only diagnostic records.
        for columns, rows in stages:
            set_size(master, columns, rows)
            os.kill(process.pid, signal.SIGWINCH)
            output = read_available(master)
            if process.poll() is not None or not output:
                raise RuntimeError(
                    f"connection details did not survive/repaint at {columns}x{rows}"
                )
            evidence.append(f"details-{columns}x{rows}:{len(output)}")
            details += output
        scrolled_details = details
        for _ in range(30):
            os.write(master, b"]")
            scrolled_details += read_available(master, 0.1)
        for label in (b"Requested environment:", b"Resolved environment:", b"Dune version:"):
            if label not in scrolled_details:
                raise RuntimeError(f"scrolled connection details did not expose {label!r}")
        os.write(master, b"d")
        project = read_available(master)
        if args.expect_hierarchy:
            expected_restored = (b"HARDWARE HIERARCHY",)
        else:
            identity = (args.expect_project_name or "Workbench").encode()
            expected_restored = (identity, b"Overview", b"Linked: Main", b"run none")
        missing = [value for value in expected_restored if value not in project]
        if missing:
            raise RuntimeError(
                f"workspace/inspector did not recover after closing connection details: "
                f"{missing!r}; terminal output: {project!r}"
            )
        if args.expect_hierarchy:
            scrolled_hierarchy = project
            for _ in range(20):
                os.write(master, b"]")
                scrolled_hierarchy += read_available(master, 0.1)
            if b"Signals/source:" not in scrolled_hierarchy:
                raise RuntimeError("compact hierarchy pane could not scroll to the inspector")
            restored_hierarchy = b""
            for _ in range(20):
                os.write(master, b"[")
                restored_hierarchy += read_available(master, 0.1)
            if b"HARDWARE HIERARCHY" not in restored_hierarchy:
                raise RuntimeError("compact hierarchy pane could not scroll back to its header")
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
        if args.expect_hierarchy:
            print("Attached-client hierarchy navigation: passed")
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
