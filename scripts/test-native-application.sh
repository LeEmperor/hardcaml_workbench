#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
switch="${OPAM_SWITCH:-5.2.0+ox}"
work_root="$(mktemp -d "${TMPDIR:-/tmp}/hardcaml-workbench-native.XXXXXX")"
prefix="$work_root/prefix"
outside="$work_root/outside"
fixture="$work_root/fixture"
integrated_fixture="$work_root/integrated-fixture"
manifest_fixture="$work_root/manifest-fixture"
missing_driver_fixture="$work_root/missing-driver-fixture"
invalid_manifest_fixture="$work_root/invalid-manifest-fixture"
runtime="$work_root/runtime"
explicit_runtime="$work_root/explicit-runtime"
mkdir -p \
  "$prefix" "$outside" "$fixture" "$integrated_fixture" "$manifest_fixture" \
  "$missing_driver_fixture" "$invalid_manifest_fixture" \
  "$runtime" "$explicit_runtime"

cp -R "$repo_root/test/fixtures/example_project/." "$fixture/"
cp -R "$repo_root/test/fixtures/example_project/." "$integrated_fixture/"
cp -R "$repo_root/test/fixtures/example_project/." "$manifest_fixture/"
cp -R "$repo_root/test/fixtures/example_project/." "$missing_driver_fixture/"
cp -R "$repo_root/test/fixtures/example_project/." "$invalid_manifest_fixture/"
rm -rf "$fixture/_build"
rm -rf \
  "$integrated_fixture/_build" "$manifest_fixture/_build" \
  "$missing_driver_fixture/_build" "$invalid_manifest_fixture/_build"
rm -f "$fixture/hardcaml-workbench.sexp"
rm -rf "$fixture/workbench"
rm -rf "$manifest_fixture/workbench"
cat >"$manifest_fixture/hardcaml-workbench.sexp" <<'EOF'
(lang hardcaml-workbench 1)
(project (name manifest-only-fixture))
(dune (build_alias @workbench-build) (test_alias @workbench-test))
EOF
cat >"$missing_driver_fixture/hardcaml-workbench.sexp" <<'EOF'
(lang hardcaml-workbench 1)
(project (name missing-driver-fixture))
(dune (driver ./workbench/missing_driver.exe))
EOF
cat >"$invalid_manifest_fixture/hardcaml-workbench.sexp" <<'EOF'
(lang hardcaml-workbench 99)
(project (name invalid-manifest-fixture))
(dune)
EOF

metadata_path="$runtime/hardcaml-workbench/daemon.sexp"
client="$prefix/bin/hardcaml-workbench"

metadata_field() {
  local field="$1"
  perl -ne "print \"\$1\\n\" if /\\($field ([^()[:space:]]+)\\)/" "$metadata_path"
}

wait_dead() {
  local pid="$1"
  local attempt
  for attempt in $(seq 1 100); do
    if ! kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
    sleep 0.05
  done
  return 1
}

cleanup() {
  if [[ -f "$metadata_path" ]]; then
    local pid
    pid="$(metadata_field pid || true)"
    if [[ -n "$pid" ]]; then
      kill -TERM "$pid" 2>/dev/null || true
      wait_dead "$pid" || true
    fi
  fi
  rm -rf "$work_root"
}
trap cleanup EXIT

(
  cd "$repo_root"
  opam exec --switch="$switch" -- dune build -p hardcaml_workbench @install
  opam exec --switch="$switch" -- dune install --prefix "$prefix" hardcaml_workbench
)

# The copied project remains a normal external Dune workspace.
opam exec --switch="$switch" -- dune build --root "$fixture"
opam exec --switch="$switch" -- dune runtest --root "$fixture"
opam exec --switch="$switch" -- dune clean --root "$fixture"

(
  cd "$outside"
  XDG_RUNTIME_DIR="$runtime" "$client" --plain \
    --project-root "$fixture" --environment "opam:$switch" >first.txt
)
first_pid="$(metadata_field pid)"
first_endpoint="$(metadata_field endpoint)"
kill -0 "$first_pid"
grep -Fq "root=$fixture" "$outside/first.txt"
grep -Fq "Environment request: opam switch $switch  resolved=opam switch $switch" \
  "$outside/first.txt"
grep -Eq "Generic Dune workspace: contexts=[^;]+; [1-9][0-9]* inspected item" \
  "$outside/first.txt"
grep -Fq "Jobs: 0" "$outside/first.txt"

XDG_RUNTIME_DIR="$runtime" \
  "$repo_root/scripts/test-terminal-resize.py" "$client" \
  --project-root "$fixture" --environment "opam:$switch"

# A single attached terminal session must consume discovery events and render the result.
XDG_RUNTIME_DIR="$runtime" \
  "$repo_root/scripts/test-terminal-resize.py" "$client" \
  --project-root "$integrated_fixture" --environment "opam:$switch" \
  --expect-live-discovery

XDG_RUNTIME_DIR="$explicit_runtime" "$client" --plain --connect "$first_endpoint" \
  --project-root "$fixture" --environment "opam:$switch" \
  >"$work_root/explicit-success.txt"
grep -Fq "root=$fixture" "$work_root/explicit-success.txt"
test ! -e "$explicit_runtime/hardcaml-workbench/daemon.sexp"

# Submit without waiting, let that client exit, and observe the same daemon-owned job.
XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$fixture" \
  --environment "opam:$switch" --action build >"$work_root/detached-submit.txt"
grep -Fq "Submitted build job" "$work_root/detached-submit.txt"
XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$fixture" \
  --environment "opam:$switch" >"$work_root/during-detached-job.txt"
grep -Fq "Jobs: 1" "$work_root/during-detached-job.txt"
grep -Eq '^Job .*: (Queued|Starting|Running) ' "$work_root/during-detached-job.txt"
test "$(metadata_field pid)" = "$first_pid"
for _attempt in $(seq 1 500); do
  XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$fixture" \
    --environment "opam:$switch" >"$work_root/after-detached-job.txt"
  if grep -Eq '^Job .*: Complete ' "$work_root/after-detached-job.txt"; then
    break
  fi
  sleep 0.1
done
grep -Fq "Jobs: 1" "$work_root/after-detached-job.txt"
grep -Eq '^Job .*: Complete ' "$work_root/after-detached-job.txt"

printf '.\n' >>"$fixture/lifecycle-trigger"
(
  cd "$outside"
  XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$fixture" \
    --environment "opam:$switch" --action build --wait >build.txt
) &
build_client=$!
for _attempt in $(seq 1 500); do
  if grep -Fq "[stdout] fixture build: started" "$outside/build.txt" 2>/dev/null; then
    break
  fi
  kill -0 "$build_client"
  sleep 0.02
done
grep -Fq "[stdout] fixture build: started" "$outside/build.txt"
kill -0 "$build_client"
if grep -Fq "fixture build: complete" "$outside/build.txt"; then
  echo "error: build output was not observed before completion" >&2
  exit 1
fi
wait "$build_client"
grep -Fq "Submitted build job" "$outside/build.txt"
grep -Fq "[stdout] fixture build: started" "$outside/build.txt"
grep -Fq "[stdout] fixture build: complete" "$outside/build.txt"
grep -Eq '^Job .*: Complete$' "$outside/build.txt"

printf '.\n' >>"$fixture/lifecycle-trigger"
XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$fixture" \
  --environment "opam:$switch" >"$work_root/reattach.txt"
test "$(metadata_field pid)" = "$first_pid"
kill -0 "$first_pid"
grep -Fq "Jobs: 2" "$work_root/reattach.txt"

XDG_RUNTIME_DIR="$runtime" "$client" --plain >"$work_root/second-observer.txt" &
observer_one=$!
XDG_RUNTIME_DIR="$runtime" "$client" --plain >"$work_root/third-observer.txt" &
observer_two=$!
wait "$observer_one"
wait "$observer_two"
grep -Fq "Jobs: 2" "$work_root/second-observer.txt"
grep -Fq "Jobs: 2" "$work_root/third-observer.txt"
test "$(metadata_field pid)" = "$first_pid"

XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$fixture" \
  --environment "opam:$switch" --action test --wait >"$work_root/test.txt"
grep -Fq "Submitted test job" "$work_root/test.txt"
grep -Fq "[stdout] fixture test: started" "$work_root/test.txt"
grep -Fq "[stdout] fixture test: complete" "$work_root/test.txt"
grep -Eq '^Job .*: Complete$' "$work_root/test.txt"

XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$fixture" \
  --environment "opam:$switch" >"$work_root/jobs.txt"
grep -Fq "Jobs: 3" "$work_root/jobs.txt"
test "$(metadata_field pid)" = "$first_pid"

# A valid manifest without a driver uses its declared aliases and remains manifest-only.
XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$manifest_fixture" \
  --environment "opam:$switch" >"$work_root/manifest-only.txt"
grep -Fq "Project: manifest-only-fixture" "$work_root/manifest-only.txt"
grep -Fq "Integration: Manifest" "$work_root/manifest-only.txt"
grep -Fq "driver=absent" "$work_root/manifest-only.txt"
XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$manifest_fixture" \
  --environment "opam:$switch" --action test --wait >"$work_root/manifest-test.txt"
grep -Eq '^Job .*: Complete$' "$work_root/manifest-test.txt"

# Compatible driver discovery is daemon-owned, cached on repeat-open, and explicitly refreshable.
XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$integrated_fixture" \
  --environment "opam:$switch" >"$work_root/integrated-open.txt"
for _attempt in $(seq 1 500); do
  XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$integrated_fixture" \
    --environment "opam:$switch" >"$work_root/integrated-ready.txt"
  if grep -Fq "driver=available v1" "$work_root/integrated-ready.txt"; then
    break
  fi
  sleep 0.05
done
grep -Fq "driver=available v1" "$work_root/integrated-ready.txt"
grep -Fq "Four-bit counter (top counter)" "$work_root/integrated-ready.txt"
grep -Fq "Default four-bit counter" "$work_root/integrated-ready.txt"
grep -Fq "Jobs: 1" "$work_root/integrated-ready.txt"
XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$integrated_fixture" \
  --environment "opam:$switch" --refresh-integration --wait \
  >"$work_root/integrated-refresh.txt"
grep -Fq "Submitted integration refresh job" "$work_root/integrated-refresh.txt"
grep -Eq '^Job .*: Complete$' "$work_root/integrated-refresh.txt"
grep -Fq "driver=available v1" "$work_root/integrated-refresh.txt"
grep -Fq "Four-bit counter (top counter)" "$work_root/integrated-refresh.txt"
grep -Fq "Default four-bit counter" "$work_root/integrated-refresh.txt"
XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$integrated_fixture" \
  --environment "opam:$switch" >"$work_root/integrated-reconnect.txt"
grep -Fq "driver=available v1" "$work_root/integrated-reconnect.txt"
grep -Fq "Jobs: 2" "$work_root/integrated-reconnect.txt"

# Missing and invalid optional integration remain actionable without disabling generic jobs.
XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$missing_driver_fixture" \
  --environment "opam:$switch" >"$work_root/missing-driver-open.txt"
for _attempt in $(seq 1 500); do
  XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$missing_driver_fixture" \
    --environment "opam:$switch" >"$work_root/missing-driver-ready.txt"
  if grep -Fq "driver=unusable: driver exited with code" \
    "$work_root/missing-driver-ready.txt"; then
    break
  fi
  sleep 0.05
done
grep -Fq "driver=unusable: driver exited with code" "$work_root/missing-driver-ready.txt"
XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$missing_driver_fixture" \
  --environment "opam:$switch" --action build --wait \
  >"$work_root/missing-driver-build.txt"
grep -Eq '^Job .*: Complete$' "$work_root/missing-driver-build.txt"
XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$invalid_manifest_fixture" \
  --environment "opam:$switch" >"$work_root/invalid-manifest-open.txt"
grep -Fq "Integration: Generic_dune" "$work_root/invalid-manifest-open.txt"
grep -Fq "unsupported hardcaml-workbench manifest version 99" \
  "$work_root/invalid-manifest-open.txt"
XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$invalid_manifest_fixture" \
  --environment "opam:$switch" --action test --wait \
  >"$work_root/invalid-manifest-test.txt"
grep -Eq '^Job .*: Complete$' "$work_root/invalid-manifest-test.txt"

if XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$outside" \
  --environment "opam:$switch" >"$work_root/invalid-root.txt" 2>&1; then
  echo "error: invalid project root unexpectedly succeeded" >&2
  exit 1
fi
grep -Fq "project root must directly contain dune-project" "$work_root/invalid-root.txt"

if XDG_RUNTIME_DIR="$runtime" "$client" --plain --project-root "$fixture" \
  --environment invalid >"$work_root/invalid-environment.txt" 2>&1; then
  echo "error: invalid environment unexpectedly succeeded" >&2
  exit 1
fi
grep -Fq -- "--environment must be inherited or opam:SWITCH" \
  "$work_root/invalid-environment.txt"

kill -TERM "$first_pid"
wait_dead "$first_pid"
XDG_RUNTIME_DIR="$runtime" "$client" --plain >"$work_root/stale.txt"
replacement_pid="$(metadata_field pid)"
test "$replacement_pid" != "$first_pid"
kill -0 "$replacement_pid"
grep -Fq "Jobs: 0" "$work_root/stale.txt"

kill -TERM "$replacement_pid"
wait_dead "$replacement_pid"
rm -f "$metadata_path"
XDG_RUNTIME_DIR="$runtime" "$client" --plain >"$work_root/concurrent-1.txt" &
client_one=$!
XDG_RUNTIME_DIR="$runtime" "$client" --plain >"$work_root/concurrent-2.txt" &
client_two=$!
wait "$client_one"
wait "$client_two"
concurrent_pid="$(metadata_field pid)"
kill -0 "$concurrent_pid"
grep -Fq "Hardcaml Workbench" "$work_root/concurrent-1.txt"
grep -Fq "Hardcaml Workbench" "$work_root/concurrent-2.txt"

if XDG_RUNTIME_DIR="$explicit_runtime" "$client" --plain --connect http://127.0.0.1:1 \
  >"$work_root/explicit.txt" 2>&1; then
  echo "error: unreachable explicit endpoint unexpectedly succeeded" >&2
  exit 1
fi
test ! -e "$explicit_runtime/hardcaml-workbench/daemon.sexp"

kill -TERM "$concurrent_pid"
wait_dead "$concurrent_pid"

printf 'Installed client: %s\n' "$client"
printf 'Installed daemon: %s\n' "$prefix/bin/hardcaml-workbench-daemon"
printf 'Installed launch directory: %s\n' "$outside"
printf 'External fixture: %s\n' "$fixture"
printf 'Integrated external fixture: %s\n' "$integrated_fixture"
printf 'Native lifecycle and installed workflow checks: passed\n'
