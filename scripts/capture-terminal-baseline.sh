#!/usr/bin/env bash
# Render the deterministic terminal UI fixtures and store them as baseline captures.
#
#   ./scripts/capture-terminal-baseline.sh            regenerate test/baselines/terminal
#   ./scripts/capture-terminal-baseline.sh --check    regenerate into a temporary
#                                                     directory and diff against the
#                                                     committed baselines
#
# The captures come from the production `render` in terminal/main.ml, driven by the
# fixtures in terminal/baseline_fixture.ml through the `--capture-baseline` development
# flag. No daemon, project, or ASIC flow is involved.
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
baseline_directory="$repository_root/test/baselines/terminal"

mode="write"
if [[ $# -gt 0 ]]; then
  case "$1" in
    --check) mode="check" ;;
    *)
      echo "usage: $(basename "$0") [--check]" >&2
      exit 2
      ;;
  esac
fi

cd "$repository_root"
./scripts/with-switch.sh dune build terminal/main.exe
client="$repository_root/_build/default/terminal/main.exe"

case "$mode" in
  write)
    # Remove only generated captures, so a renamed or retired scenario does not leave a
    # stale frame behind and any hand-written note in the directory survives.
    rm -f "$baseline_directory"/*.txt "$baseline_directory"/*.ansi
    "$client" --capture-baseline "$baseline_directory"
    ;;
  check)
    scratch="$(mktemp -d)"
    trap 'rm -rf "$scratch"' EXIT
    "$client" --capture-baseline "$scratch/terminal" >/dev/null
    if diff -r -x '*.md' "$baseline_directory" "$scratch/terminal"; then
      echo "terminal baselines are up to date"
    else
      echo "error: terminal baselines differ from a fresh capture" >&2
      exit 1
    fi
    ;;
esac
