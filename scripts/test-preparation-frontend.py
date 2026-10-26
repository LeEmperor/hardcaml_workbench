#!/usr/bin/env python3
"""WB004 real native HTTP/PTY regression using an isolated EDA-less publisher.

Uses existing binaries; all generated projects/evidence live under /tmp/opencode.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import secrets
import signal
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('preparation_composition', HERE / 'test-frontend-composition.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
field, wait, require, sexp = c.field, c.wait, c.require, c.sexp


def acceptance(t, check, http, runs, presets, args):
    root = t.base / 'project'
    def snapshot():
        return http.rpc(domain='preparation', wait=False)
    def latest():
        return next(iter(field(snapshot(), 'latest')), None)
    def terminal(outcome):
        return wait(lambda: a if (a := latest()) and field(a, 'outcome') == outcome else None,
                    'preparation ' + outcome)
    def calls():
        path = root / 'preparation-calls.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    registry_before = http.rpc(domain='workspace')
    historical = http.rpc(wait=False)
    t.focus_view('preparation')
    t.command('Zoom focused tile')
    t.capture('unavailable', ['unavailable: not configured'])
    t.key(b'r')
    check(not field(snapshot(), 'latest') and not calls(), 'Unavailable preparation r submits no work')
    # Actual driver discovery/generation through normal Dune and normal daemon binaries.
    driver = root / 'rtl-driver.py'
    driver.write_bytes((HERE / 'fixtures/preparation_generic_rtl_driver.py').read_bytes())
    driver.chmod(0o700)
    (root / 'dune').write_text('(rule (target rtl-driver.exe) (deps rtl-driver.py) '
                             '(action (copy %{deps} %{target})))\n')
    (root / 'hardcaml-workbench.sexp').write_text(
        '(lang hardcaml-workbench 1)\n(project (name wb004-generic))\n(dune (driver ./rtl-driver.exe))\n')
    t.command('Refresh hardware integration')
    def generic_job():
        state = http.raw('/api/v1/snapshot', [['instance_id', http.instance]])
        return next((j for j in field(state, 'jobs') if field(j, 'kind') ==
                     [['namespace', 'project-driver'], ['name', 'generate-rtl']]), None)
    def driver_ready():
        state = http.raw('/api/v1/snapshot', [['instance_id', http.instance]])
        return any(field(p, 'targets') for p in field(state, 'projects'))
    wait(driver_ready, 'generic project driver discovery')
    t.drain(1)
    t.command('Generate RTL: WB004 generic counter / WB004 default')
    generic = wait(lambda: j if (j := generic_job()) and field(j, 'state') == 'Complete' else None,
                   'actual generic RTL generation')
    t.capture('generic-rtl-observed', ['Generic RTL (not ASIC bundle)', 'completed'])
    generic_screen = c.status_text(t.capture('generic-emission-unavailable').text())
    check('Elaboration-bundle emission: unavailable' in generic_screen,
          'Completed generic RTL cannot turn unavailable ASIC emission into not-requested or completed')
    t.key(b'\r')
    t.capture('generic-rtl-log', ['WB004 exact generic RTL job log'])
    t.key(b'a')
    t.capture('generic-rtl-artifact', ['WB004 generic RTL only; not ASIC publication'])
    t.key(b'\x1b'); t.key(b'\x1b')
    check(field(generic_job(), 'id') == field(generic, 'id') and not field(snapshot(), 'latest'),
          'Generic fallback inspection/log/artifact actions do not submit preparation or generation')
    source = root / 'publisher.py'
    source.write_bytes((HERE / 'fixtures/preparation_publisher.py').read_bytes())
    source.chmod(0o700)
    with (root / 'dune').open('a') as dune:
        dune.write('(rule (target publisher.exe) (deps publisher.py) '
                             '(action (progn (echo "WB004 exact build log") (copy %{deps} %{target}))))\n')
    (root / 'hardcaml-workbench-preparation.sexp').write_text(
        sexp([['schema_version', 1], ['build_target', 'publisher.exe'],
              ['results_root', str(t.base / 'publication')], ['timeout_seconds', 30]]))
    (root / 'preparation-mode').write_text('success')
    t.command('Discover ASIC flows and runs')
    flows = wait(lambda: field(http.rpc(wait=False), 'flows'), 'current selected-flow catalog')
    flow = flows[0]
    t.command('Preparation inputs: ' + field(flow, 'id') + ' / ' + field(flow, 'profiles')[0])
    t.key(b'synthesis X=frontend'); t.key(b'\r')
    t.capture('available-not-requested', ['no session history'])
    t.command('Unzoom workspace')
    t.focus_view('stage checklist')
    t.command('Zoom focused tile')
    t.key(b'k' * 20)
    t.capture('elaboration-selected', ['Elaboration:', 'not requested'])
    t.key(b'\r')
    t.capture('elaboration-read-only', ['Current project preparation', 'no session history'])
    check(not calls(), 'Elaboration Enter inspects preparation without a producer')
    t.key(b'\x1b')
    t.key(b'r')
    completed = terminal('Completed')
    completed_id = field(completed, 'id')
    bundle = field(completed, 'bundle')[0]
    check(field(completed, 'selection') == [['flow', field(flow, 'id')],
          ['profile', field(flow, 'profiles')[0]], ['endpoint', 'synthesis'], ['assignments', ['X=frontend']]],
          'Preparation captures exact current flow, profile, endpoint and overrides')
    check(field(bundle, 'bundle_identity') and field(bundle, 'artifacts'), 'Successful selected-flow publication exposes bundle and artifacts')
    t.command('Unzoom workspace')
    t.focus_view('preparation')
    t.command('Zoom focused tile')
    t.capture('completed', ['completed', 'Elaboration-bundle emission'])
    check(len(calls()) == 1 and calls()[0][:2] == ['flow', 'emit'], 'Preparation keyboard action invokes flow emit once')
    t.key(b'\r')
    t.capture('exact-build-inspection', ['WB004 exact build log'])
    # Scroll through the read-only details until the exact emission stage log is visible.
    found = False
    for _ in range(35):
        screen = t.capture('inspection-scroll')
        if 'WB004 exact emission log' in screen.text():
            found = True
            break
        t.key(b']' * 4)
    check(found, 'Exact emission job log fetched through ordinary Read_log and reachable by scrolling')
    artifact = field(bundle, 'artifacts')[-1]
    t.command('Preparation ' + completed_id + ': artifact ' + artifact)
    t.capture('bundle-artifact', ['PREPARATION BUNDLE ARTIFACT', 'WB004 published config'])
    t.key(b'\x1b')
    (root / 'preparation-mode').write_text('fail')
    t.focus_view('preparation')
    t.key(b'\x1b'); t.key(b'r')
    failed = terminal('Emission_failed')
    check(field(field(failed, 'build_job')[0], 'state') == 'Complete', 'Emission failure retains completed source build')
    t.capture('newest-failure-headline', ['emission failed'])
    t.key(b'j')
    t.capture('prior-success-history', [completed_id])
    check(any(field(a, 'id') == completed_id and field(a, 'bundle') for a in field(snapshot(), 'history')),
          'Newest failure retains historical completed publication')
    (root / 'preparation-mode').write_text('hold')
    t.key(b'\x1b'); t.key(b'r')
    terminal('Emitting')
    count_before_reconnect = len(calls())
    t.close()
    c.Terminal.__init__(t, t.base, args, http.url)
    t.capture('reconnected-active', ['emitting elaboration bundle'])
    check(len(calls()) == count_before_reconnect,
          'Fresh client connection retrieves active preparation and history without resubmission')
    t.key(b'x')
    terminal('Cancelled')
    t.capture('cancelled-headline', ['cancelled'])
    current = http.rpc(wait=False)
    check(field(current, 'launches') == field(historical, 'launches') and
          field(current, 'runs') == field(historical, 'runs'),
          'Prepare, history, logs, artifact and cancel never launch or mutate historical physical executions')
    check(all(a[:2] == ['flow', 'emit'] for a in calls()), 'Every preparation producer is EDA-less emission')
    # Registry edits here were explicit zoom operations only; no preparation migration.
    check(field(http.rpc(domain='workspace'), 'tiles') == field(registry_before, 'tiles'),
          'Preparation operations preserve saved tile membership and bindings')
    return 'Overview'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'client', 'preset-export'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--timeout', type=int, default=150)
    args = parser.parse_args()
    for name in ('daemon', 'client', 'preset_export'):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    args.evidence = args.evidence or Path('/tmp/opencode') / ('wb004-frontend-' + secrets.token_hex(6))
    require(args.evidence.resolve().is_relative_to('/tmp/opencode'), 'Evidence must be under /tmp/opencode')
    args.palette_only = False
    args.harness = 'WB004 preparation frontend'
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('WB004 budget exhausted')))
    signal.alarm(args.timeout)
    try:
        c.run(args, acceptance=lambda *values: acceptance(*values, args), extra_runs=(), focused=True)
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
