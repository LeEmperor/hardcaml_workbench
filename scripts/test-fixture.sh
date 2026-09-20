#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${FIXTURE_OPAM_SWITCH:-}" ]]; then
  echo "error: set FIXTURE_OPAM_SWITCH to the fixture project's existing opam switch" >&2
  exit 2
fi

if ! opam switch list --short | grep -qx "$FIXTURE_OPAM_SWITCH"; then
  echo "error: fixture opam switch '$FIXTURE_OPAM_SWITCH' not found" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
external_root="$(mktemp -d "${TMPDIR:-/tmp}/hardcaml-workbench-fixture.XXXXXX")"
trap 'rm -rf "$external_root"' EXIT

cp -R "$repo_root/test/fixtures/example_project/." "$external_root/"
printf 'Fixture root: %s\n' "$external_root"
printf 'Fixture opam switch: %s\n' "$FIXTURE_OPAM_SWITCH"
opam exec --switch="$FIXTURE_OPAM_SWITCH" -- dune build --root "$external_root"
opam exec --switch="$FIXTURE_OPAM_SWITCH" -- dune runtest --root "$external_root"
