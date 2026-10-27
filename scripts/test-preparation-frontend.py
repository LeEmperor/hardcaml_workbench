#!/usr/bin/env python3
"""WB004 real native HTTP/PTY regression using an isolated EDA-less publisher.

Uses existing binaries; all generated projects/evidence live under /tmp/opencode.
"""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import secrets
import signal
import sys
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('preparation_composition', HERE / 'test-frontend-composition.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
field, wait, require, sexp = c.field, c.wait, c.require, c.sexp
shared_spec = importlib.util.spec_from_file_location('preparation_fresh_frontend', HERE / 'fixtures/fresh_frontend.py')
shared = importlib.util.module_from_spec(shared_spec)
shared_spec.loader.exec_module(shared)


def acceptance(t, check, http, runs, presets, args):
    root = t.base / 'project'
    def snapshot():
        return http.rpc(domain='preparation', wait=False)
    def latest():
        w = workflow()
        return next((a for a in field(snapshot(), 'history') if field(a, 'id') in field(w, 'preparation_id')), None) if w else None
    def workflow():
        return next(iter(field(http.rpc(wait=False), 'workflows')), None)
    def staged():
        return next(iter(field(http.rpc(wait=False), 'fresh_intent')), None)
    def terminal(outcome):
        return wait(lambda: a if (a := latest()) and field(a, 'outcome') == outcome else None,
                    'preparation ' + outcome)
    def calls():
        path = root / 'preparation-calls.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    timer_detail = False
    def checklist_time(label, status):
        nonlocal timer_detail
        shared.zoom(args.fixture, 'planned-run')
        t.capture(label + '-workflow', ['Workflow ID:', field(workflow(), 'id')])
        if not timer_detail:
            t.key(b'\r')
            timer_detail = True
        screen = t.capture(label, ['Elaboration: ' + status, 'Time:'])
        match = re.search(r'Time:\s+(\d+)s', screen.text())
        check(match is not None, label + ': inclusive preparation duration belongs to the exact workflow')
        return int(match.group(1))
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
              ['results_root', str(t.base / 'publication')], ['timeout_seconds', 90]]))
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
    t.capture('elaboration-selected', ['Elaboration:', 'unavailable'])
    check('Elaboration:' in t.capture('elaboration-unknown-time').text(),
           'Historical run without workflow linkage remains unavailable, independent of project preparation config')
    t.key(b'\r')
    t.capture('elaboration-read-only', ['Elaboration linkage unavailable', 'historical run'])
    check(not calls(), 'Elaboration Enter inspects preparation without a producer')
    t.key(b'\x1b')
    jobs_before = {field(j, 'id') for j in field(http.raw('/api/v1/snapshot', [['instance_id', http.instance]]), 'jobs')}
    t.key(b'r')
    intent = wait(staged, 'input intent staging')
    t.drain(1)
    state = http.raw('/api/v1/snapshot', [['instance_id', http.instance]])
    check(not calls() and not field(snapshot(), 'latest') and
          {field(j, 'id') for j in field(state, 'jobs')} == jobs_before,
          'Elaboration r stages exact input plan with zero producer/jobs')
    t.open_palette('Launch and view planned run')
    # Identical selection is insufficient evidence of receipt ownership: replace
    # it under a genuinely different captured preparation configuration scope.
    prep_path = root / 'hardcaml-workbench-preparation.sexp'
    original_config = prep_path.read_bytes()
    different_scope = c.parse(original_config.decode())
    next(pair for pair in different_scope if pair[0] == 'timeout_seconds')[1] = '91'
    try:
        prep_path.write_text(sexp(different_scope))
        http.rpc('(Stage_fresh (selection %s) (elaboration_only true) (expected_plan_identity ()))' % sexp(field(intent, 'selection')),
                 wait=False)
        superseded = staged()
        shared.api.save(t.base / 'same-selection-scope-replacement.json',
                        dict(captured=intent, replacement=superseded))
        t.key(b'\r')
        t.drain(1)
        t.capture('superseded-stage-rejected')
        check(field(superseded, 'selection') == field(intent, 'selection') and
              field(superseded, 'scope') != field(intent, 'scope') and
              field(superseded, 'id') != field(intent, 'id') and not calls() and not workflow(),
              'Same-selection different-scope replacement cannot satisfy or launch the captured original fresh intent')
    finally:
        prep_path.write_bytes(original_config)
    t.key(b'\x1b')
    t.key(b'r')
    wait(lambda: staged() != superseded, 'fresh manual preparation intent')
    t.drain(.5)
    t.open_palette('Launch and view planned run')
    recovery = t.capture('restaged-intent-launch-eligibility', ['Launch and view planned run'])
    recovered = '[Fresh intent' not in recovery.text()
    check(recovered, 'Same client can launch a newly staged intent after rejecting a superseded captured action', fatal=False)
    t.key(b'\x1b')
    if not recovered:
        # Keep the failing recovery assertion and final nonzero result, while a
        # fresh client allows independent log/artifact/standalone regressions to run.
        t.close()
        c.Terminal.__init__(t, t.base, args.fixture.client_args, http.url, 180, 55)
        t.capture('fresh-client-recovery-for-independent-cases', ['stage checklist'])
        old_intent = staged()
        t.key(b'r')
        wait(lambda: staged() != old_intent, 'independent fresh-client input stage')
        t.drain(.7)
    t.type_action('launch and vi', 'Launch and view planned run', 'manual-preparation-selected-action')
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
    t.open_palette('Preparation ' + completed_id + ': artifact ' + artifact)
    t.capture('exact-artifact-palette', ['> Preparation ' + completed_id[:36], artifact[-32:]], ['No matching commands'])
    t.key(b'\r')
    t.capture('bundle-artifact', ['PREPARATION BUNDLE ARTIFACT', 'WB004 published config'])
    t.key(b'\x1b')
    (root / 'preparation-mode').write_text('fail')
    t.focus_view('preparation')
    t.key(b'\x1b'); t.key(b'r')
    t.drain(.7)
    check(len(calls()) == 1 and field(latest(), 'id') == completed_id,
          'Preparation tile r stages inputs without creating another attempt or producer')
    t.command('Unzoom workspace'); t.focus_view('stage checklist'); t.command('Zoom focused tile')
    t.key(b'k' * 20)
    t.command('Quick-launch behavior: keep current context')
    workspace_before_named = http.rpc(domain='workspace')
    t.type_action('launch elab', 'Launch elaboration bundle', 'named-elaboration-selected-action')
    failed = terminal('Emission_failed')
    check(http.rpc(domain='workspace') == workspace_before_named,
          'Named elaboration launch retains captured context and registry')
    t.open_palette('Quick-launch behavior: keep current context')
    t.capture('elaboration-preference-unchanged', ['keep current context (selected)'])
    t.key(b'\x1b')
    check(len(calls()) == 2 and field(failed, 'selection') == field(completed, 'selection'),
          'Named elaboration stages and emits exact selected inputs once after manual launch')
    check(field(field(failed, 'build_job')[0], 'state') == 'Complete', 'Emission failure retains completed source build')
    t.command('Unzoom workspace'); t.focus_view('preparation'); t.command('Zoom focused tile')
    t.capture('newest-failure-headline', ['emission failed'])
    t.key(b'j')
    t.capture('prior-success-history', [completed_id])
    check(any(field(a, 'id') == completed_id and field(a, 'bundle') for a in field(snapshot(), 'history')),
          'Newest failure retains historical completed publication')
    (root / 'preparation-mode').write_text('hold')
    t.key(b'\x1b'); t.key(b'R')
    terminal('Emitting')
    check(len(calls()) == 3, 'Preparation tile R emits once for a new exact staged receipt')
    first_time = checklist_time('emitting-duration', 'emitting')
    t.drain(1.2)
    second_time = int(re.search(r'Time:\s+(\d+)s', t.capture('emitting-live-duration').text()).group(1))
    check(second_time >= first_time + 1, 'Active preparation timer advances monotonically across build plus emission')
    t.command('Unzoom workspace'); t.focus_view('preparation'); t.command('Zoom focused tile')
    count_before_reconnect = len(calls())
    t.close()
    c.Terminal.__init__(t, t.base, args.fixture.client_args, http.url, 180, 55)
    timer_detail = False  # Utility-detail mode is intentionally session-local.
    t.capture('reconnected-active', ['emitting elaboration bundle'])
    check(len(calls()) == count_before_reconnect,
          'Fresh client connection retrieves active preparation and history without resubmission')
    t.key(b'x')
    terminal('Cancelled')
    t.capture('cancelled-headline', ['cancelled'])
    frozen = checklist_time('cancelled-duration', 'cancelled')
    t.drain(1.2)
    check(int(re.search(r'Time:\s+(\d+)s', t.capture('cancelled-frozen-duration').text()).group(1)) == frozen,
          'Cancelled preparation duration freezes instead of animating as active')
    # The configured ASIC executable and the freshly built publisher deliberately
    # produce different methodology identities for the SAME selected inputs.
    # Exercise the real dispatcher: the palette's initial eligibility check alone
    # cannot catch accidentally borrowing the ASIC identity when lowering to Stage.
    (root / 'preparation-mode').write_text('success')
    t.command('Preparation inputs: ' + field(flow, 'id') + ' / ' + field(flow, 'profiles')[0])
    t.key(b'\x15'); t.key(b'synthesis'); t.key(b'\r')
    selected = [['flow', field(flow, 'id')], ['profile', field(flow, 'profiles')[0]],
                ['endpoint', 'synthesis'], ['assignments', []]]
    http.rpc('(Plan %s)' % sexp(selected))
    preview = wait(lambda: next(iter(field(http.rpc(wait=False), 'preview')), None),
                   'same-selection ASIC preview')
    check(field(preview, 'selection') == selected, 'ASIC preview exactly matches standalone preparation selection')
    t.drain(1)
    def fresh_completed(previous):
        return wait(lambda: a if (a := latest()) and field(a, 'id') != previous and
                    field(a, 'outcome') == 'Completed' else None, 'fresh standalone preparation completion')
    def independent(attempt, route):
        check(not field(attempt, 'expected_plan_identity') and
              field(attempt, 'selection') == selected and
              field(field(attempt, 'bundle')[0], 'plan_identity') != field(preview, 'plan_identity'),
              route + ' builds fresh source without borrowing same-selection ASIC preview identity')
        check(field(http.rpc(wait=False), 'preview') == [preview], route + ' preserves ASIC preview')
    t.command('Unzoom workspace'); t.focus_view('stage checklist'); t.command('Zoom focused tile')
    t.key(b'k' * 20)
    previous = field(latest(), 'id')
    old_stage = staged()
    before_calls = len(calls())
    t.key(b'r')
    intent = wait(lambda: s if (s := staged()) != old_stage else None,
                  'same-selection standalone input stage')
    check(not field(intent, 'expected_plan_identity') and field(intent, 'selection') == selected and
          len(calls()) == before_calls and field(latest(), 'id') == previous,
          'Regular Elaboration r stages unpinned current-source inputs without launching')
    t.command('Launch and view planned run')
    manual = fresh_completed(previous)
    independent(manual, 'Regular r/manual launch')
    t.key(b'R')
    quick = fresh_completed(field(manual, 'id'))
    independent(quick, 'Elaboration R')
    t.type_action('launch elab', 'Launch elaboration bundle', 'same-selection-palette-elaboration')
    named = fresh_completed(field(quick, 'id'))
    independent(named, 'Named elaboration palette launch')
    t.command('Quick launch selected stage')
    selected_quick = fresh_completed(field(named, 'id'))
    independent(selected_quick, 'Selected Elaboration palette quick launch')
    # Explicit API callers still own their expectation. The same unrelated identity
    # must fail backend receipt validation rather than being silently discarded.
    http.rpc('(Stage_fresh (selection %s) (elaboration_only true) '
             '(expected_plan_identity (%s)))' % (sexp(selected), sexp(field(preview, 'plan_identity'))), wait=False)
    http.rpc('(Launch_fresh (key explicit-stale-preview) (intent_id %s))' % sexp(field(staged(), 'id')), wait=False)
    stale = terminal('Emission_failed')
    check(field(stale, 'expected_plan_identity') == [field(preview, 'plan_identity')] and
          field(field(stale, 'build_job')[0], 'state') == 'Complete' and not field(stale, 'bundle') and
          'Expected plan mismatch' in str(field(stale, 'diagnostic')),
          'Explicit stale API expectation survives dispatch and fails backend publication validation')
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
    parser.add_argument('--timeout', type=int, default=360)
    args = parser.parse_args()
    for name in ('daemon', 'client', 'preset_export'):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    args.evidence = args.evidence or Path('/tmp/opencode') / ('wb004-frontend-' + secrets.token_hex(6))
    require(args.evidence.resolve().is_relative_to('/tmp/opencode'), 'Evidence must be under /tmp/opencode')
    args.palette_only = False
    args.harness = 'WB004 preparation frontend'
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('WB004 budget exhausted')))
    signal.alarm(args.timeout)
    args.evidence = args.evidence.resolve()
    args.evidence.mkdir(exist_ok=False)
    print('Evidence: ' + str(args.evidence), flush=True)
    result = dict(status='failed', checks=[], evidence=str(args.evidence),
                  binaries={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (args.daemon, args.client, args.preset_export)})
    fixture = None
    def check(ok, message, fatal=True):
        result['checks'].append(dict(passed=bool(ok), expectation=message))
        if fatal:
            require(ok, message)
    try:
        fixture, presets = shared.setup(args, 'native', check, preparation=False)
        args.fixture = fixture
        acceptance(fixture.terminal, check, fixture.http, (), presets, args)
        require(all(item['passed'] for item in result['checks']), 'One or more retained regression assertions failed; see result.json')
        result['status'] = 'passed'
    except BaseException:
        result['error'] = traceback.format_exc()
        raise
    finally:
        signal.alarm(0)
        try:
            if fixture is not None:
                shared.finish(fixture)
        finally:
            shared.api.save(args.evidence / 'result.json', result)
    print('PASS WB004 unified preparation frontend: ' + str(len(result['checks'])) + ' assertions; ' + str(args.evidence))


if __name__ == '__main__':
    main()
