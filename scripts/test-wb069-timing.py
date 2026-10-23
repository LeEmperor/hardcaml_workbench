#!/usr/bin/env python3
"""Fixture-only WB-069 native HTTP/PTY acceptance; matching prebuilt binaries only.

Uses the existing private synthetic harness and a private provider overlay. No
builds, sibling repositories, EDA, or user-state access. Nested work is serial:
the daemon/client and bounded read-only Python provider processes only.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import signal
import sys
import urllib.request

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observation(execution_file, generation='a'):
    execution_file = Path(execution_file).resolve()
    attempt = execution_file.parent.name
    directory = execution_file.parent / 'fixture-sta'
    def source(name):
        return dict(path=str(directory / name), sha256='f' * 64)
    metrics = []
    for key, raw, value, unit in (
        ('setup_slack', 'timing__setup__ws', -.125, 'ns'),
        ('hold_slack', 'timing__hold__ws', 0., 'ns'),
        ('setup_violations', 'timing__setup_vio__count', 1., 'count'),
        ('hold_violations', 'timing__hold_vio__count', 0., 'count')):
        metrics.append(dict(key=key, raw_key=raw + '__corner:slow', corner='slow',
            availability='available', value=value, unit=unit, reason=None,
            source=dict(file=source('slow/sta.log'), state=source('state_out.json'), line=1),
            units_source=source('slow/generated.lib') if unit == 'ns' else None))
    return dict(contract='hardcaml-asic.timing-analysis', schema_version=1,
        attempt_id=attempt, occurrence_id=attempt + '/implementation.signoff',
        analysis_id=attempt + '/post-pnr-sta', stage='signoff',
        execution_file=str(execution_file),
        execution_sha256=hashlib.sha256(execution_file.read_bytes()).hexdigest(),
        source_digest=generation * 64, status='completed', reason=None,
        enclosing_status='failed', evidence_scope='terminal_supplementary_not_checkpoint',
        native_grammar='librelane-3.1.0.dev3-step-output-runtime-v1',
        duration=dict(seconds=1.575, precision_seconds=.001, basis='librelane_step_wall_clock', source=source('runtime.txt')),
        producer=dict(class_id='OpenROAD.STAPostPNR', directory=str(directory), config=source('config.json')),
        inventory=[source(n) for n in ('config.json', 'runtime.txt', 'state_out.json', 'slow/sta.log', 'slow/generated.lib')],
        corners=[dict(corner='slow', status='measured', setup_goal='fail', hold_goal='pass')],
        metrics=metrics, timing_goal='fail')


def provider(base, args):
    """Overlay public read results, preserving the harness's real request logging."""
    original = load('wb069_private_provider', base / 'project/synthetic-provider/provider.py')
    old_report, old_inspect = original.report, original.inspect
    def generation():
        return (base / 'analysis-generation').read_text().strip()
    def report(path):
        result = old_report(path)
        result['execution']['status'] = 'failed'
        result['checkpoints'] = []
        result['timing_analysis'] = observation(path, generation())
        return result
    def inspect(path, domain, stage, row_id=None, expected=None):
        if domain != 'timing' or stage != 'signoff':
            return old_inspect(path, domain, stage, row_id, expected)
        a = observation(path, generation())
        digest = 'b' * 64
        if expected != (digest if row_id else a['source_digest']):
            raise ValueError('captured analysis source changed')
        result = dict(contract='hardcaml-asic.inspection', schema_version=1,
            execution_file=a['execution_file'], execution_sha256=a['execution_sha256'],
            attempt_id=a['attempt_id'], domain=domain, stage=stage,
            analysis_id=a['analysis_id'], analysis_digest=a['source_digest'], source_digest=digest,
            diagnostics=['Fixture: STA completed before later DRC timeout; no signoff checkpoint'],
            truncated=False, rows=[dict(id='wb069-path', category='timing_path', producer='OpenROAD.STAPostPNR',
                corner='slow', group='setup', name='captured-wb069-path', value=-.125, unit='ns', status='violated',
                source='{}', fields=[['startpoint', 'fixture/start'], ['endpoint', 'fixture/end']])])
        if row_id:
            if row_id != 'wb069-path':
                raise ValueError('wrong captured row')
            result.update(row_id=row_id, detail='WB069 exact retained analysis detail; no checkpoint or execution')
        return result
    original.report, original.inspect = report, inspect
    sys.argv = [str(base / 'project/synthetic-flow')] + args
    original.main()


def acceptance(t, check, http, runs, presets):
    composition = HARNESS.composition
    field, sexp, wait = composition.field, composition.sexp, composition.wait
    base = t.base
    (base / 'analysis-generation').write_text('a')
    wrapper = base / 'project/synthetic-flow'
    wrapper.write_text('#!' + sys.executable + '\nimport os,sys\nos.execv(sys.executable, ' +
        repr([sys.executable, str(Path(__file__).resolve()), '--fixture-provider', str(base)]) + ' + sys.argv[1:])\n')
    # The failed signoff is a fixture observation, not an inference from its reports.
    for reference in json.loads((base / 'manifest.json').read_text())['runs']:
        path = Path(reference['attempt']) / 'observation.json'
        state = json.loads(path.read_text())
        state['state']['outcome']['status'] = 'failed'
        execution_path = path.parent / 'execution.json'
        execution = json.loads(execution_path.read_text())
        execution.update(status='failed', exit_code=1)
        execution['artifacts'] = [a for a in execution['artifacts'] if a['boundary'] != 'signoff']
        execution_path.write_text(json.dumps(execution))
        for stage in state['stage_plan']['stages']:
            if stage['id'] == 'signoff':
                stage.update(status='failed', reason='fixture later DRC timeout')
        path.write_text(json.dumps(state))
    run = runs[0]
    http.rpc('(Observe %s)' % sexp(run))
    http.rpc('(Refresh %s)' % sexp(run))
    def native_snapshot(name):
        request = urllib.request.Request(http.url + '/api/v1/asic',
            data=sexp([['instance_id', http.instance], ['project', http.project], ['operation', 'Get']]).encode(),
            headers={'Content-Type': 'application/sexp', 'X-Workbench-Protocol': '1',
                     'X-Workbench-Asic-Timing-Analysis': '2', 'X-Workbench-Execution-Timing': '1'})
        with urllib.request.urlopen(request, timeout=30) as response:
            native = response.read().decode()
        (base / (name + '.sexp')).write_text(native)
        return composition.parse(native)[1]
    snapshot = native_snapshot('wb069-native-summary')
    summary = next(s for s in field(snapshot, 'summaries') if field(s, 'run') == run)
    analysis = field(summary, 'timing_analysis')[0]
    check(field(analysis, 'status') == 'Completed', 'Native HTTP summary carries independently completed STA')
    def registry(): return http.rpc(domain='workspace')
    overview = next(w for w in field(registry(), 'workspaces') if field(w, 'preset') == ['overview'])
    wid = field(overview, 'id')
    def mutate(op): return http.mutate(registry(), op)
    def tile(kind): return next(x for x in field(registry(), 'tiles') if field(x, 'workspace') == wid and field(x, 'kind') == kind)
    def calls(): return [json.loads(line)['argv'] for line in (base / 'project/provider-calls.jsonl').read_text().splitlines()]
    baseline = calls()
    def zoom(kind):
        t.focus_view(kind.replace('-', ' '))
        mutate('(Set_zoom (workspace %s) (tile (%s)))' % (sexp(wid), sexp(field(tile(kind), 'id'))))
        def zoomed():
            left, _, right, _ = HARNESS.pane_rect(t.drain(), kind.replace('-', ' '))
            return right - left >= t.width - 2
        wait(zoomed,
             'client observed exact zoom before key activation')
    shot = t.capture('wb069-both-overview', ['completed 1.575s', 'Timing: completed', 'Signoff: failed'])
    def body(screen, title):
        left, top, right, bottom = HARNESS.pane_rect(screen, title)
        return [line[left + 1:right - 1].strip() for line in screen.lines()[top + 1:bottom - 1]]
    timing = body(shot, 'timing')
    check(any('1.575s' in line and 'completed' in line for line in timing), 'Stock compact tile retains status and duration together')
    check(any('fail' in line for line in timing), 'Compact tile separates failing goal from completed analysis')
    check(any('setup -0.125 ns' in line and 'hold 0 ns' in line for line in timing),
          'Compact Timing tile shows setup and hold metrics for the same slow corner')
    stages = [composition.status_text(line) for line in body(shot, 'stage checklist')]
    names = ['Routing:', 'Timing:', 'Signoff:']
    positions = [next(i for i, line in enumerate(stages) if name in line) for name in names]
    check(positions == sorted(positions), 'Checklist orders Routing, Timing, Signoff')
    zoom('stage-checklist')
    for _ in range(5): t.key(b'j')
    t.key(b'r')
    t.capture('wb069-read-only-r', ['Timing: completed', '1.575s', 'Unsupported fresh endpoint'])
    # Leave the UI untouched while its periodic workspace polling continues. Feedback
    # must remain readable, rather than merely appear in a transient draw window.
    t.drain(1.5)
    t.capture('wb069-unsupported-after-polls', ['Timing: completed', '1.575s', 'Unsupported fresh endpoint'])
    check(not any(a[:2] in (['flow', 'plan'], ['flow', 'run']) or a[:1] == ['finalize'] for a in calls()[len(baseline):]),
          'r on legacy unsupported Timing may discover read-only capabilities but never Plans/Runs/Finalizes')
    t.key(b'd')
    t.capture('wb069-checklist-full-details', ['Analysis ID:', 'Current execution outcome: failed', 'Duration: 1.575 s'])
    t.key(b'\x1b')
    t.key(b'\r')
    t.capture('wb069-checklist-enter', ['captured-wb069-path', 'WB069 exact retained analysis detail'])
    exact = [a for a in calls()[len(baseline):] if a[:1] == ['inspect']]
    check(exact and all('--expected-digest' in a for a in exact), 'Checklist Enter uses captured analysis digest for index and detail')
    check(any('--row-id' in a and a[a.index('--expected-digest') + 1] == 'b' * 64 for a in exact), 'Detail uses returned INDEX digest, not observation digest')
    t.command('Switch to Overview')
    mutate('(Set_zoom (workspace %s) (tile ()))' % sexp(wid))
    zoom('timing')
    t.key(b'd')
    t.capture('wb069-analysis-details', ['Analysis ID:', 'Current execution outcome: failed', 'Duration: 1.575 s'])
    t.key(b'\x1b')
    t.key(b'\r')
    t.capture('wb069-tile-enter', ['captured-wb069-path', 'WB069 exact retained analysis detail'])
    check(len([w for w in field(registry(), 'workspaces') if 'Timing · captured' in field(w, 'name')]) == 1,
          'Both Overview entry points reuse only the same captured-source investigation')
    # Source changes cannot turn refresh of a captured investigation into newest evidence.
    (base / 'analysis-generation').write_text('c')
    t.key(b'r')
    t.capture('wb069-stale-source', ['captured analysis source changed'])
    t.command('Switch to Overview')
    mutate('(Set_zoom (workspace %s) (tile ()))' % sexp(wid))
    timing_tile = tile('timing')
    mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' % (sexp(field(timing_tile, 'id')), sexp(run)))
    context = next(c for c in field(registry(), 'contexts') if field(c, 'id') == field(overview, 'context'))
    mutate('(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run ()))' %
           (sexp(wid), sexp(field(context, 'id')), field(context, 'selection_revision')))
    t.capture('wb069-pin-retains-source', ['completed 1.575s', 'PIN'])
    checklist = tile('stage-checklist')
    mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' % (sexp(field(checklist, 'id')), sexp(run)))
    zoom('timing')
    t.key(b'r')
    t.capture('wb069-pinned-summary-refreshed', ['completed 1.575s', 'PIN'])
    updated = wait(lambda: next((s for s in field(native_snapshot('wb069-refreshed-summary'), 'summaries')
        if field(s, 'run') == run and field(field(field(s, 'timing_analysis')[0], 'target'), 'source_digest') == 'c' * 64), None),
        'pinned summary source refresh')
    check(field(field(field(updated, 'timing_analysis')[0], 'target'), 'source_digest') == 'c' * 64,
          'Explicit pinned Overview refresh loads the new observation without selecting another run')
    mutate('(Set_zoom (workspace %s) (tile ()))' % sexp(wid))
    t.capture('wb069-pinned-surfaces-coherent', ['completed 1.575s', 'Timing: completed', 'Signoff: failed'])
    zoom('timing')
    t.key(b'\r')
    t.capture('wb069-new-source-new-investigation', ['captured-wb069-path', 'WB069 exact retained analysis detail'])
    check(len([w for w in field(registry(), 'workspaces') if 'Timing · captured' in field(w, 'name')]) == 2,
          'A new analysis digest creates a distinct investigation instead of retargeting the prior captured source')
    (base / 'restart-expected-target.json').write_text(json.dumps(dict(run=run,
        target=field(field(updated, 'timing_analysis')[0], 'target'))))
    check(not any(a[:2] in (['flow', 'plan'], ['flow', 'run']) or a[:1] == ['finalize'] for a in calls()[len(baseline):]),
          'All WB069 browsing/detail/refresh/pinning operations are read-only')
    return 'Overview'


def restart_acceptance(t, check, http, runs, presets):
    composition = HARNESS.composition
    field, sexp, wait = composition.field, composition.sexp, composition.wait
    expected = json.loads((t.base / 'restart-expected-target.json').read_text())
    run, target = expected['run'], expected['target']
    calls_path = t.base / 'project/provider-calls.jsonl'
    def calls(): return [json.loads(line)['argv'] for line in calls_path.read_text().splitlines()]
    # Public evidence has moved on, but a cache-only retained read must keep C.
    (t.base / 'analysis-generation').write_text('d')
    baseline = calls()
    def native(operation='Get'):
        body = '((instance_id %s)(project %s)(operation %s))' % (sexp(http.instance), sexp(http.project), operation)
        request = urllib.request.Request(http.url + '/api/v1/asic', data=body.encode(),
            headers={'Content-Type': 'application/sexp', 'X-Workbench-Protocol': '1',
                     'X-Workbench-Asic-Timing-Analysis': '2', 'X-Workbench-Execution-Timing': '1'})
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode()
        http.history.append(dict(path='/api/v1/asic', request=body, response=text))
        result = composition.parse(text)
        check(result[0] == 'Ok', 'Restart native request succeeds')
        return result[1]
    native('(Inspect_analysis (run %s)(target %s)(refresh false))' % (sexp(run), sexp(target)))
    def retained_index():
        snapshot = native()
        return next((i for i in field(snapshot, 'inspections') if field(i, 'run') == run
                     and field(i, 'analysis') == [target]), None)
    index = wait(retained_index, 'restarted exact-target L2 index')
    check(field(index, 'cached_unverified') == 'true',
          'Daemon restart reopens the exact retained analysis index as cached-unverified')
    check(calls() == baseline, 'Restart warm exact-target cache lookup performs no provider read')
    t.capture('wb069-daemon-restart-exact-cached', ['captured-wb069-path', 'CACHED UNVERIFIED',
        'Captured analysis: ' + field(target, 'analysis_id'), 'Analysis digest: ' + 'c' * 64],
        ['Analysis digest: ' + 'd' * 64])
    check(True, 'Fresh client restores exact captured target/path after daemon restart, without selecting newer D evidence')
    t.key(b'r')
    t.capture('wb069-restart-no-silent-replacement', ['ERROR:', 'CACHED UNVERIFIED',
        'Analysis digest: ' + 'c' * 64], ['Analysis digest: ' + 'd' * 64])
    failed = field(native(), 'operations')
    check(any(field(op, 'state') == 'failed' and field(op, 'run') == [run]
              and 'captured analysis source changed' in ''.join(field(op, 'error')) for op in failed),
          'Restart refresh visibly fails for the exact captured run/source, rather than retargeting public D')
    check(not any(a[:2] in (['flow', 'plan'], ['flow', 'run']) or a[:1] == ['finalize'] for a in calls()[len(baseline):]),
          'Restart, restoration and rejected refresh start no physical execution')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'client', 'preset-export'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--evidence', type=Path)
    p.add_argument('--timeout', type=int, default=300)
    args = p.parse_args()
    for name in ('daemon', 'client', 'preset_export'):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    args.evidence = args.evidence or Path('/tmp/opencode') / ('wb069-timing-' + secrets.token_hex(6))
    if not args.evidence.resolve().is_relative_to('/tmp/opencode'):
        p.error('Evidence must be private /tmp/opencode state')
    args.palette_only = False
    args.harness = 'WB069 fixture-only timing Overview/exact navigation'
    os.umask(0o077)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('WB069 acceptance deadline')))
    signal.alarm(args.timeout)
    try:
        HARNESS.composition.run(args, acceptance=acceptance, extra_runs=(), focused=True,
                                restart_acceptance=restart_acceptance)
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--fixture-provider':
        try:
            provider(Path(sys.argv[2]), sys.argv[3:])
        except ValueError as error:
            print(str(error), file=sys.stderr)
            sys.exit(2)
    else:
        HARNESS = load('wb069_sidebar', HERE / 'test-overview-sidebar.py')
        main()
