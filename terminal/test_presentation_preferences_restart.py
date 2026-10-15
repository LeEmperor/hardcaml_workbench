"""Run after the serialized build: python3 terminal/test_presentation_preferences_restart.py
_build/default/terminal/presentation_preferences_probe.exe

Also wired into the terminal runtest alias. Each probe invocation is a fresh process.
"""

import pathlib
import subprocess
import sys
import tempfile


def main():
    probe = str(pathlib.Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="fs3-presentation-") as directory:
        state = pathlib.Path(directory) / "state"

        def run(mode, path=state):
            subprocess.run([probe, mode, str(path)], check=True)

        run("missing")
        run("write")
        run("read")
        files = list(state.iterdir())
        assert len(files) == 1 and files[0].name.startswith("presentation-")
        assert files[0].stat().st_mode & 0o077 == 0
        original = files[0].read_bytes()
        run("write")
        run("read")
        assert files[0].read_bytes() == original
        assert len(list(state.iterdir())) == 1, "temporary file leaked"

        unknown_version = original.replace(b"(schema_version 1)", b"(schema_version 99)")
        assert unknown_version != original
        for malformed in (b"(", unknown_version, b" " * 65537):
            files[0].write_bytes(malformed)
            run("malformed")
            assert files[0].read_bytes() == malformed

        run("write")  # An explicit new choice may replace an unreadable old file.
        run("read")
        blocked = pathlib.Path(directory) / "blocked"
        blocked.write_text("not a directory")
        run("save-error", blocked)
    print("Presentation preferences: fresh-process retention and failure checks passed")


if __name__ == "__main__":
    main()
