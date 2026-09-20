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
driver_output="$(opam exec --switch="$FIXTURE_OPAM_SWITCH" -- \
  dune exec --root "$external_root" ./workbench/project_driver.exe -- \
  describe --protocol-version 1)"
grep -Fq '(key counter)' <<<"$driver_output"
grep -Fq '(key four-bit)' <<<"$driver_output"
grep -Fq '(key eight-bit)' <<<"$driver_output"
grep -Fq 'generate-rtl-hierarchy' <<<"$driver_output"

four_dir="$external_root/direct-four"
eight_dir="$external_root/direct-eight"
mkdir "$four_dir" "$eight_dir"
four_result="$(opam exec --switch="$FIXTURE_OPAM_SWITCH" -- \
  dune exec --root "$external_root" ./workbench/project_driver.exe -- \
  generate-rtl --protocol-version 1 --target counter --configuration four-bit \
  --output-dir "$four_dir")"
eight_result="$(opam exec --switch="$FIXTURE_OPAM_SWITCH" -- \
  dune exec --root "$external_root" ./workbench/project_driver.exe -- \
  generate-rtl --protocol-version 1 --target counter --configuration eight-bit \
  --output-dir "$eight_dir")"
grep -Fq '(configuration four-bit)' <<<"$four_result"
grep -Fq '(configuration eight-bit)' <<<"$eight_result"
grep -Eq 'output[[:space:]]+\[3:0\][[:space:]]+count_o' "$four_dir/counter-4.v"
grep -Eq 'output[[:space:]]+\[7:0\][[:space:]]+count_o' "$eight_dir/counter-8.v"
grep -Fq 'module counter' "$four_dir/counter-4.v"
grep -Fq '(circuit_name counter_top)' "$four_dir/counter-4.hierarchy.sexp"
grep -Fq '(instance_name (u_counter_0))' "$four_dir/counter-4.hierarchy.sexp"
grep -Fq '(instance_name (u_counter_1))' "$four_dir/counter-4.hierarchy.sexp"
grep -Fq '(key /11:u_counter_0)' "$four_dir/counter-4.hierarchy.sexp"
grep -Fq '(key /11:u_counter_1)' "$four_dir/counter-4.hierarchy.sexp"
grep -Fq '((name count_o) (width 4))' "$four_dir/counter-4.hierarchy.sexp"
grep -Fq '((name count_o) (width 8))' "$eight_dir/counter-8.hierarchy.sexp"
test "$(grep -o '(key /[^)]*)' "$four_dir/counter-4.hierarchy.sexp")" = \
  "$(grep -o '(key /[^)]*)' "$eight_dir/counter-8.hierarchy.sexp")"
