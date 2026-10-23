#!/usr/bin/env python3
"""Serial fixture-only native HTTP/PTY executable Timing acceptance; prebuilt binaries.

The opt-in synthetic recipe is isolated from the historical six-stage regressions.
No nested builds, EDA, network beyond loopback, or Git mutations.
"""
import json
import os
from pathlib import Path
import sys
import subprocess
import urllib.request

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
import importlib.util


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OLD = load('executable_timing_legacy', HERE / 'test-wb069-timing.py')


def provider(base, args):
    p = load('executable_timing_provider', base / 'project/synthetic-provider/provider.py')
    finish, report, inspect = p.finish, p.report, p.inspect

    def completed_timing(path):
        return any(o['action_key'] == 'implementation.timing' and o['status'] == 'completed'
                   for o in p.load(path)['occurrences'])

    def observation(path):
        frozen = Path(str(path) + '.timing-source')
        a = OLD.observation(frozen)
        attempt = Path(path).parent.name
        a.update(schema_version=2, attempt_id=attempt, occurrence_id=attempt + '/implementation.timing',
                 analysis_id=attempt + '/post-pnr-sta', stage='timing', enclosing_status='running',
                 evidence_scope='immutable_timing_execution_source_not_checkpoint')
        return a

    def finish_with_source(attempt, state, status):
        finish(attempt, state, status)
        path = attempt / 'execution.json'
        if completed_timing(path):
            captured = p.load(path)
            captured['status'] = 'running'
            captured['occurrences'] = [o for o in captured['occurrences'] if o['action_key'] != 'implementation.signoff']
            p.save(str(path) + '.timing-source', captured)

    def timing_report(path):
        result = report(path)
        if completed_timing(path):
            result['timing_analysis'] = observation(path)
        return result

    def timing_inspect(path, domain, stage, row_id=None, expected=None):
        if domain != 'timing' or stage != 'timing':
            return inspect(path, domain, stage, row_id, expected)
        a = observation(path)
        if expected != ('b' * 64 if row_id else a['source_digest']):
            raise ValueError('captured analysis source changed')
        result = dict(contract='hardcaml-asic.inspection', schema_version=1,
            execution_file=str(path), execution_sha256=p.digest(path),
            attempt_id=a['attempt_id'], domain=domain, stage=stage, analysis_id=a['analysis_id'],
            analysis_digest=a['source_digest'], source_digest='b' * 64, diagnostics=['Synthetic executable Timing'],
            truncated=False, rows=[dict(id='timing-path', category='timing_path', producer='OpenROAD.STAPostPNR',
                corner='slow', group='setup', name='exact-executable-timing-path', value=-.125, unit='ns',
                status='violated', source='{}', fields=[['startpoint', 'fixture/start'], ['endpoint', 'fixture/end']])])
        if row_id:
            if row_id != 'timing-path':
                raise ValueError('wrong row')
            result.update(row_id=row_id, detail='Exact executable Timing retained detail')
        return result

    p.finish, p.report, p.inspect = finish_with_source, timing_report, timing_inspect
    sys.argv = [str(base / 'project/synthetic-flow')] + args
    p.main()


def native(http, operation='Get'):
    c = HARNESS.composition
    body = '((instance_id %s)(project %s)(operation %s))' % (c.sexp(http.instance), c.sexp(http.project), operation)
    request = urllib.request.Request(http.url + '/api/v1/asic', data=body.encode(),
        headers={'Content-Type': 'application/sexp', 'X-Workbench-Protocol': '1',
                 'X-Workbench-Asic-Timing-Analysis': '2', 'X-Workbench-Execution-Timing': '1'})
    with urllib.request.urlopen(request, timeout=30) as response:
        text = response.read().decode()
    http.history.append(dict(path='/api/v1/asic', request=body, response=text))
    result = c.parse(text)
    if result[0] != 'Ok':
        raise AssertionError(text)
    return result[1]


def acceptance(t, check, http, runs, presets):
    c = HARNESS.composition
    field, sexp, wait = c.field, c.sexp, c.wait
    base = t.base
    settings = base / 'project/synthetic-settings.json'
    value = json.loads(settings.read_text())
    value.update(executable_timing=True, manual=False, delay_seconds=.15)
    settings.write_text(json.dumps(value))
    wrapper = base / 'project/synthetic-flow'
    wrapper.write_text('#!' + sys.executable + '\nimport os,sys\nos.execv(sys.executable, ' +
        repr([sys.executable, str(Path(__file__).resolve()), '--fixture-provider', str(base)]) + ' + sys.argv[1:])\n')
    def calls():
        return [json.loads(line)['argv'] for line in (base / 'project/provider-calls.jsonl').read_text().splitlines()]
    def registry(): return http.rpc(domain='workspace')
    overview = next(w for w in field(registry(), 'workspaces') if field(w, 'preset') == ['overview'])
    wid = field(overview, 'id')
    def tile(kind): return next(x for x in field(registry(), 'tiles') if field(x, 'workspace') == wid and field(x, 'kind') == kind)
    def mutate(op): return http.mutate(registry(), op)
    historical = runs[0]
    old_run = next(r for r in field(native(http), 'runs') if field(r, 'run') == historical)
    old_stages = field(old_run, 'stages')
    check(len(old_stages) == 6 and not any(field(s, 'id') == 'timing' for s in old_stages),
          'Upgrade begins with a genuine historical six-stage selection')
    historical_path = Path(field(old_run, 'execution_file')[0])
    historical_bytes = historical_path.read_bytes()
    mutate('(Set_tile_binding (tile %s)(binding (Pin_run %s)))' % (sexp(field(tile('stage-checklist'), 'id')), sexp(historical)))
    t.focus_view('stage checklist')
    mutate('(Set_zoom (workspace %s)(tile (%s)))' % (sexp(wid), sexp(field(tile('stage-checklist'), 'id'))))
    t.capture('upgrade-historical-checklist', ['Timing:', 'Signoff:'])
    for _ in range(5): t.key(b'j')
    before_upgrade = calls()
    t.key(b'r')
    wait(lambda: len([a for a in calls()[len(before_upgrade):] if a[:2] == ['flow', 'plan']]) == 1,
         'historical supplementary Timing prepares exactly once')
    wait(lambda: field(native(http), 'preview'), 'upgraded Timing preview')
    upgrade_calls = calls()[len(before_upgrade):]
    check(not any(a[:2] == ['flow', 'run'] or a[:1] == ['finalize'] for a in upgrade_calls),
          'Historical Timing r prepares without implicit Run or Finalize')
    check(all(a[a.index('--endpoint') + 1] == 'timing' for a in upgrade_calls if a[:2] == ['flow', 'plan']),
          'Historical supplementary row uses the current fresh Timing catalog endpoint')
    t.capture('upgrade-historical-prepared', ['Timing:', 'Signoff:'])
    existing = [field(r, 'run') for r in field(native(http), 'runs')]
    t.command('Launch synthetic / success → timing')
    def upgraded_finished():
        return next((r for r in field(native(http), 'runs') if field(r, 'run') not in existing and
                     field(r, 'status') == 'completed'), None)
    upgraded = wait(upgraded_finished, 'explicit upgraded Timing prefix launch')
    statuses = {field(s, 'id'): field(s, 'status') for s in field(upgraded, 'stages')}
    check(len(statuses) == 7 and statuses['timing'] == 'Completed' and statuses['signoff'] == 'Not_requested',
          'Explicit launch from historical Timing produces seven-stage Timing prefix')
    old_after = next(r for r in field(native(http), 'runs') if field(r, 'run') == historical)
    check(field(old_after, 'stages') == old_stages and historical_path.read_bytes() == historical_bytes,
          'Fresh upgrade preparation/launch leaves historical stages and source bytes unchanged')
    t.capture('upgrade-historical-evidence-unchanged', ['Timing:', 'Signoff:'])
    mutate('(Set_zoom (workspace %s)(tile ()))' % sexp(wid))
    # Start a seven-stage historical observation with independently failed Signoff.
    p = load('executable_seed_provider', base / 'project/synthetic-provider/provider.py')
    # Import the private overlay's finish function without executing its CLI.
    selected = p.selection('success', 'signoff')
    attempt = p.allocate(base / 'results', selected, 'executable-signofffailed')
    while p.load(attempt / 'observation.json')['writer_active']:
        state = p.load(attempt / 'observation.json')
        if next(s for s in state['stage_plan']['stages'] if s['status'] == 'running')['id'] == 'signoff':
            p.SCENARIOS['profiles']['success']['fail_stage'] = 'signoff'
        p.advance(attempt)
    path = attempt / 'execution.json'
    frozen = p.load(path)
    frozen['status'] = 'running'
    frozen['occurrences'] = [o for o in frozen['occurrences'] if o['action_key'] != 'implementation.signoff']
    p.save(str(path) + '.timing-source', frozen)
    http.rpc('(Register ((attempt %s)(stream_id %s)))' % (sexp(str(attempt)), sexp(attempt.name)))
    run = next(field(r, 'run') for r in field(native(http), 'runs') if field(field(r, 'reference'), 'attempt') == str(attempt))
    http.rpc('(Observe %s)' % sexp(run))
    http.rpc('(Refresh %s)' % sexp(run))
    def registry(): return http.rpc(domain='workspace')
    overview = next(w for w in field(registry(), 'workspaces') if field(w, 'preset') == ['overview'])
    wid = field(overview, 'id')
    def tile(kind): return next(x for x in field(registry(), 'tiles') if field(x, 'workspace') == wid and field(x, 'kind') == kind)
    def mutate(op): return http.mutate(registry(), op)
    for kind in ('timing', 'stage-checklist'):
        mutate('(Set_tile_binding (tile %s)(binding (Pin_run %s)))' % (sexp(field(tile(kind), 'id')), sexp(run)))
    def zoom(kind):
        t.focus_view(kind.replace('-', ' '))
        mutate('(Set_zoom (workspace %s)(tile (%s)))' % (sexp(wid), sexp(field(tile(kind), 'id'))))
        def zoomed():
            try:
                return HARNESS.pane_rect(t.drain(), kind.replace('-', ' '))[2] >= t.width - 2
            except AssertionError:
                return False
        wait(zoomed, 'zoom')
    t.capture('executable-signofffailed-overview', ['stage', 'STA runtime', '1.575s', 'signoff: failed'])
    zoom('stage-checklist')
    for _ in range(5): t.key(b'j')
    t.key(b'd')
    t.capture('executable-physical-details', ['Stage ID: timing', 'Current execution outcome: failed', 'Captured source status: running'])
    t.key(b'\x1b')
    before = calls()
    t.key(b'r')
    wait(lambda: len([a for a in calls()[len(before):] if a[:2] == ['flow', 'plan']]) == 1, 'single Timing prepare')
    check(not any(a[:2] == ['flow', 'run'] for a in calls()[len(before):]), 'r prepares exactly once without execution')
    check(any(a[a.index('--endpoint') + 1] == 'timing' for a in calls()[len(before):] if a[:2] == ['flow', 'plan']), 'r selects supported Timing endpoint')
    t.capture('executable-prepared-not-launched', ['timing: completed'])
    existing = [field(r, 'run') for r in field(native(http), 'runs')]
    t.command('Launch synthetic / success → timing')
    def finished():
        return next((r for r in field(native(http), 'runs') if field(r, 'run') not in existing and
                     field(r, 'selection') and field(field(r, 'selection')[0], 'endpoint') == 'timing' and field(r, 'status') == 'completed'), None)
    launched = wait(finished, 'explicit launch through Timing')
    statuses = {field(s, 'id'): field(s, 'status') for s in field(launched, 'stages')}
    check(statuses['timing'] == 'Completed' and statuses['signoff'] == 'Not_requested', 'Explicit launch stops at Timing; Signoff not requested')
    (base / 'executable-launched.sexp').write_text(sexp(launched))
    t.key(b'\r')
    t.capture('executable-checklist-exact', ['exact-executable-timing-path', 'Exact executable Timing retained detail'])
    t.command('Switch to Overview')
    mutate('(Set_zoom (workspace %s)(tile ()))' % sexp(wid))
    zoom('timing')
    t.key(b'\r')
    t.capture('executable-tile-exact', ['exact-executable-timing-path', 'Exact executable Timing retained detail'])
    exact = [a for a in calls()[len(before):] if a[:1] == ['inspect']]
    check(exact and all(a[a.index('--stage') + 1] == 'timing' and '--expected-digest' in a for a in exact), 'Both surfaces inspect stage-aware exact source and index digests')
    summary = next(s for s in field(native(http), 'summaries') if field(s, 'run') == run)
    target = field(field(summary, 'timing_analysis')[0], 'target')
    check(field(target, 'stage') == 'timing' and field(target, 'execution_file'), 'HTTP v2 preserves stage and frozen source path')
    (base / 'restart-expected-target.json').write_text(json.dumps(dict(run=run, target=target)))
    (base / 'executable-final-snapshot.sexp').write_text(sexp(native(http)))
    return 'Overview'


def restart_acceptance(t, check, http, runs, presets):
    c = HARNESS.composition
    field, sexp, wait = c.field, c.sexp, c.wait
    expected = json.loads((t.base / 'restart-expected-target.json').read_text())
    native(http, '(Inspect_analysis (run %s)(target %s)(refresh false))' % (sexp(expected['run']), sexp(expected['target'])))
    index = wait(lambda: next((i for i in field(native(http), 'inspections') if field(i, 'analysis') == [expected['target']]), None), 'exact restarted cache')
    check(field(index, 'cached_unverified') == 'true', 'Restart retains exact Timing-stage cache as unverified')
    t.capture('executable-restart', ['exact-executable-timing-path', 'CACHED UNVERIFIED', 'Stage: timing'])
    t.command('Switch to Overview')
    t.capture('executable-restart-pins', ['PIN', 'STA runtime', '1.575s'])


def cross_contract(provider, fixtures, evidence):
    """Read actual retained production-bridge fixtures with the prebuilt provider."""
    provider, fixtures, evidence = map(lambda p: Path(p).resolve(), (provider, fixtures, evidence))
    if not evidence.is_relative_to('/tmp/opencode'):
        raise ValueError('private evidence required')
    evidence.mkdir(exist_ok=False)
    results = []
    for case, outcome, stage_status in ((2, 'completed', 'completed'), (3, 'failed', 'completed'), (4, 'failed', 'failed')):
        retained = json.loads((fixtures / ('case-' + str(case)) / 'report.json').read_text())
        execution = retained['timing_analysis']['execution_file'].removesuffix('.timing-source')
        report = json.loads(subprocess.run([str(provider), 'report', execution, '--json'],
            check=True, capture_output=True, timeout=30).stdout)
        a = report['timing_analysis']
        occurrence = next(o for o in report['execution']['occurrences'] if o['action_key'] == 'implementation.timing')
        assert report['execution']['plan']['schema_version'] == 4
        assert report['execution']['status'] == outcome and occurrence['status'] == stage_status
        assert a['stage'] == 'timing' and a['status'] == 'completed'
        assert a['duration']['seconds'] == 1.575 and occurrence['duration_seconds'] != a['duration']['seconds']
        index = json.loads(subprocess.run([str(provider), 'inspect', execution, '--domain', 'timing',
            '--stage', 'timing', '--expected-digest', a['source_digest'], '--json'],
            check=True, capture_output=True, timeout=30).stdout)
        assert index['analysis_digest'] == a['source_digest'] and index['stage'] == 'timing'
        (evidence / ('case-%d-report.json' % case)).write_text(json.dumps(report, indent=2))
        (evidence / ('case-%d-index.json' % case)).write_text(json.dumps(index, indent=2))
        results.append(dict(case=case, outcome=outcome, timing_stage=stage_status,
            captured_status=a['enclosing_status'], stage_seconds=occurrence['duration_seconds'], sta_seconds=a['duration']['seconds']))
    (evidence / 'result.json').write_text(json.dumps(dict(status='passed', cases=results), indent=2))
    print('PASS retained actual-provider cross contract: ' + str(evidence))


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == '--cross-contract':
        cross_contract(*sys.argv[2:])
    elif len(sys.argv) > 1 and sys.argv[1] == '--fixture-provider':
        provider(Path(sys.argv[2]), sys.argv[3:])
    else:
        HARNESS = load('executable_timing_sidebar', HERE / 'test-overview-sidebar.py')
        prepare = HARNESS.composition.demo.prepare
        def prepare_executable(*args, **kwargs):
            base = prepare(*args, **kwargs)
            settings = base / 'project/synthetic-settings.json'
            value = json.loads(settings.read_text())
            value['executable_timing'] = True
            settings.write_text(json.dumps(value))
            wrapper = base / 'project/synthetic-flow'
            wrapper.write_text('#!' + sys.executable + '\nimport os,sys\nos.execv(sys.executable, ' +
                repr([sys.executable, str(Path(__file__).resolve()), '--fixture-provider', str(base)]) + ' + sys.argv[1:])\n')
            return base
        HARNESS.composition.demo.prepare = prepare_executable
        OLD.HARNESS = HARNESS
        OLD.acceptance = acceptance
        OLD.restart_acceptance = restart_acceptance
        OLD.main()
