#!/usr/bin/env python3
"""Default-on native HTTP/PTY index warm-up acceptance. Prebuilt binaries only.

Private synthetic read-only provider overlay; no EDA or production state. Retains
provider calls, HTTP, ANSI, SVG cells and assertions through the composition harness.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OLD = load('preload_legacy', HERE / 'test-wb069-timing.py')
EX = load('preload_executable', HERE / 'test-executable-timing.py')
H = load('preload_sidebar', HERE / 'test-overview-sidebar.py')
C = H.composition
field, sexp, wait = C.field, C.sexp, C.wait
EX.HARNESS = H


def provider(base, args):
    p = load('preload_provider', base / 'project/synthetic-provider/provider.py')
    report = p.report

    def control():
        return json.loads((base / 'preload-control.json').read_text())

    def observation(path):
        frozen = Path(str(path) + '.timing-source')
        if not frozen.exists():
            captured = json.loads(Path(path).read_text())
            captured['status'] = 'running'
            frozen.write_text(json.dumps(captured))
        a = OLD.observation(frozen, control()['generation'])
        a.update(schema_version=2, stage='timing',
                 occurrence_id=Path(path).parent.name + '/implementation.timing',
                 evidence_scope='immutable_timing_execution_source_not_checkpoint',
                 enclosing_status='running')
        return a

    def timing_report(path):
        result = report(path)
        if control()['available']:
            result['timing_analysis'] = observation(path)
        return result

    def inspect(path, domain, stage, row_id=None, expected=None):
        state = control()
        time.sleep(state.get('delay', 0))
        if state.get('fail'):
            raise ValueError('deliberate preload fixture failure')
        a = observation(path)
        if expected != ('b' * 64 if row_id else a['source_digest']):
            raise ValueError('captured analysis source changed')
        result = dict(contract='hardcaml-asic.inspection', schema_version=1,
            execution_file=str(path), execution_sha256=p.digest(path),
            attempt_id=a['attempt_id'], domain=domain, stage=stage,
            analysis_id=a['analysis_id'], analysis_digest=a['source_digest'], source_digest='b' * 64,
            diagnostics=['Preload fixture exact frozen source'], truncated=False,
            rows=[dict(id='preload-path', category='timing_path', producer='OpenROAD.STAPostPNR',
                corner='slow', group='setup', name='preload-ready-path', value=-.125029, unit='ns',
                status='violated', source='{}', fields=[['startpoint', 'fixture/start'], ['endpoint', 'fixture/end']])])
        if row_id:
            result.update(row_id=row_id, detail='Explicit selected preload detail')
        return result

    p.report, p.inspect = timing_report, inspect
    sys.argv = [str(base / 'project/synthetic-flow')] + args
    p.main()


def calls(base):
    return [json.loads(line)['argv'] for line in (base / 'project/provider-calls.jsonl').read_text().splitlines()]


def acceptance(t, check, http, runs, presets):
    runs = [runs[0], runs[2]]  # The harness's second seed intentionally fails before STA.
    base = t.base
    control = base / 'preload-control.json'
    state = dict(available=True, generation='a', delay=1.5, fail=False)
    def set_control(**kw):
        state.update(kw)
        control.write_text(json.dumps(state))
    set_control()
    wrapper = base / 'project/synthetic-flow'
    wrapper.write_text('#!' + sys.executable + '\nimport os,sys\nos.execv(sys.executable, ' +
        repr([sys.executable, str(Path(__file__).resolve()), '--fixture-provider', str(base)]) + ' + sys.argv[1:])\n')
    def native(op='Get'): return EX.native(http, op)
    def registry(): return http.rpc(domain='workspace')
    original = registry()
    overview = next(w for w in field(original, 'workspaces') if field(w, 'name') == 'Overview')
    timing = next(w for w in field(original, 'workspaces') if field(w, 'name') == 'Timing')
    def select(run):
        r = registry()
        context = next(x for x in field(r, 'contexts') if field(x, 'id') == field(overview, 'context'))
        http.mutate(r, '(Select_run (workspace %s)(context %s)(expected_selection_revision %s)(run (%s)))' %
            (sexp(field(overview, 'id')), sexp(field(context, 'id')), field(context, 'selection_revision'), sexp(run)))
    def indexes(): return [a for a in calls(base) if a[:1] == ['inspect'] and '--row-id' not in a and '--expected-digest' in a]
    def details(): return [a for a in calls(base) if a[:1] == ['inspect'] and '--row-id' in a]
    def refresh(run):
        native('(Refresh %s)' % sexp(run))
        wait(lambda: any(field(s, 'run') == run and dict(s).get('timing_analysis') and
             field(field(field(s, 'timing_analysis')[0], 'target'), 'source_digest') == state['generation'] * 64
             for s in field(native(), 'summaries')), 'new exact summary')
    def index(run, generation):
        t.drain(.02)
        return next((i for i in field(native(), 'inspections') if field(i, 'run') == run and
            dict(i).get('analysis') and field(field(i, 'analysis')[0], 'source_digest') == generation * 64), None)
    def settle(): t.drain(2)
    run = runs[0]
    select(run)
    baseline = registry()
    refresh(run)
    wait(lambda: len(indexes()) == 1, 'default-on hidden index request')
    wait(lambda: index(run, 'a'), 'hidden publication')
    settle()
    check(not details(), 'Overview completion warms index only: zero hidden selected/neighbor reads')
    check(registry() == baseline, 'Hidden warm-up preserves every workspace, context, pin and tile ID')
    t.capture('hidden-ready-overview', ['Overview', 'planned-run'])
    t.wait_active_workspace(registry(), field(overview, 'id'), 'hidden-overview')
    before = len(indexes())
    t.command('Switch to Timing')
    t.capture('switch-ready-table', ['preload-ready-path', '-0.125', 'Stage: timing'])
    settle()
    check(len(indexes()) == before and not details(), 'Switch displays prepared rows without duplicate index or implicit detail')
    t.command('Switch to Overview')
    # Explicit-only is persisted and forbids speculative reads for a new selection.
    t.command('Timing preload: Explicit only')
    select(runs[1])
    refresh(runs[1])
    settle()
    check(len(indexes()) == before, 'Explicit-only issues zero speculative reads for newly selected completed run')
    set_control(delay=5)
    t.command('Timing preload: Background index')
    wait(lambda: len(indexes()) == before + 1, 'second run pending warmup')
    t.command('Inspect timing paths asic/' + field(runs[1], 'id'))
    check(index(runs[1], 'a') is None, 'Explicit Inspect arrives while exact provider warm-up is still pending')
    t.capture('inspect-joined-loading', ['Loading timing index'])
    t.capture('inspect-joins-pending', ['preload-ready-path', 'Explicit selected preload detail'])
    check(len(indexes()) == before + 1, 'Immediate explicit Inspect joins exact warm-up without refresh or duplicate read')
    t.command('Switch to Overview')
    set_control(delay=1.5)
    settle()
    # A new frozen source is warmed, while changes to mutable main execution alone
    # must not invalidate the exact retained source.
    main = next(r for r in field(native(), 'runs') if field(r, 'run') == runs[1])
    path = Path(field(main, 'execution_file')[0])
    path.write_text(path.read_text() + '\n')
    native('(Observe %s)' % sexp(runs[1]))
    refresh(runs[1])
    settle()
    check(len(indexes()) == before + 1, 'Changing main execution hash does not re-read frozen Timing source')
    set_control(generation='c', delay=2)
    refresh(runs[1])
    wait(lambda: len(indexes()) == before + 2, 'source C pending')
    set_control(generation='e')
    refresh(runs[1])
    wait(lambda: index(runs[1], 'e'), 'replacement exact source E')
    check(index(runs[1], 'c') is None, 'Obsolete in-flight source C never publishes as replacement source E')
    t.command('Switch to Timing')
    t.focus_view('path provenance')
    t.command('Strings: Show full identifiers and source paths')
    t.capture('changed-source-fenced', ['Analysis digest: ' + 'e' * 32], ['Analysis digest: ' + 'c' * 32])
    t.command('Switch to Overview')
    set_control(generation='f', delay=3)
    refresh(runs[1])
    wait(lambda: len(indexes()) == before + 4, 'old selection source F pending')
    select(run)
    wait(lambda: index(runs[1], 'f'), 'old selection source F publication')
    t.command('Switch to Timing')
    t.focus_view('path provenance')
    t.command('Strings: Show full identifiers and source paths')
    t.capture('old-selection-fenced', ['Analysis digest: ' + 'a' * 32], ['Analysis digest: ' + 'f' * 32])
    t.command('Switch to Overview')
    # One failure is finite, with explicit refresh providing the only retry.
    set_control(generation='d', delay=.2, fail=True)
    refresh(run)
    wait(lambda: len(indexes()) == before + 5, 'failed warmup')
    settle()
    failed_count = len(indexes())
    settle()
    check(len(indexes()) == failed_count, 'Failed background source is attempted once across repeated polls')
    t.command('Switch to Timing')
    t.capture('failure-visible', ['ERROR:'])
    check(any('deliberate preload fixture failure' in ''.join(field(op, 'error'))
              for op in field(native(), 'operations')), 'Visible error corresponds to exact provider failure')
    set_control(fail=False)
    t.resize(180, 55)
    t.focus_view('timing paths')
    t.key(b'r')
    wait(lambda: index(run, 'd'), 'explicit failed-source retry')
    t.capture('explicit-retry-ready', ['preload-ready-path'])
    check(len(indexes()) == failed_count + 1, 'Explicit refresh retries failed source exactly once')
    t.command('Switch to Overview')
    # Materialize a genuine fixture observation with Timing completed and Signoff
    # still running. Only private synthetic bytes are constructed here.
    p = load('preload_live_fixture', base / 'project/synthetic-provider/provider.py')
    attempt = p.allocate(base / 'results', p.selection('success'), 'preload-live-signoff')
    while next(x for x in p.load(attempt / 'observation.json')['stage_plan']['stages']
               if x['status'] == 'running')['id'] != 'signoff':
        p.advance(attempt)
    live = p.load(attempt / 'observation.json')
    p.finish(attempt, p.load(attempt / 'observation.json'), 'completed')
    execution = p.load(attempt / 'execution.json')
    execution.update(status='running', exit_code=None)
    p.save(attempt / 'execution.json', execution)
    live['execution_file'] = str(attempt / 'execution.json')
    p.save(attempt / 'observation.json', live)
    native('(Register ((attempt %s)(stream_id preload-live-signoff)))' % sexp(str(attempt)))
    live_run = next(field(r, 'run') for r in field(native(), 'runs')
                    if field(field(r, 'reference'), 'attempt') == str(attempt))
    native('(Observe %s)' % sexp(live_run))
    select(live_run)
    refresh(live_run)
    wait(lambda: index(live_run, 'd'), 'STA ready while Signoff remains running')
    observed = next(r for r in field(native(), 'runs') if field(r, 'run') == live_run)
    check(field(observed, 'status') == 'observing' and
          any(field(x, 'id') == 'signoff' and field(x, 'status') == 'Running' for x in field(observed, 'stages')),
          'Hidden index prepares before enclosing run completes, while Signoff is Running')
    t.capture('signoff-running-hidden-overview', ['Overview'])
    select(run)
    settle()
    (base / 'preload-restart.json').write_text(json.dumps(dict(run=run, indexes=len(indexes()), details=len(details()))))
    check(len(field(registry(), 'workspaces')) == len(field(original, 'workspaces')) and
          field(registry(), 'tiles') == field(original, 'tiles'), 'All navigation keeps stock tabs, tiles and pins intact')
    return 'Overview'


def restart_acceptance(t, check, http, runs, presets):
    t.capture('restart-hidden-overview', ['Overview', 'planned-run'])
    expected = json.loads((t.base / 'preload-restart.json').read_text())
    def retained():
        return next((i for i in field(EX.native(http), 'inspections') if field(i, 'run') == expected['run'] and
             dict(i).get('analysis') and field(field(i, 'analysis')[0], 'source_digest') == 'd' * 64), None)
    index = wait(retained, 'automatic hidden L2 reopen after daemon/client restart')
    check(field(index, 'cached_unverified') == 'true', 'Default preload automatically reopens exact retained L2 as cached-unverified')
    observed = calls(t.base)
    check(len([a for a in observed if a[:1] == ['inspect'] and '--row-id' not in a and '--expected-digest' in a]) == expected['indexes'],
          'Restart cache reopen needs zero provider index reads')
    check(len([a for a in observed if a[:1] == ['inspect'] and '--row-id' in a]) == expected['details'],
          'Hidden restart performs zero provider detail reads')
    t.command('Switch to Timing')
    t.capture('restart-cached-ready', ['preload-ready-path', 'CACHED UNVERIFIED'])
    t.command('Switch to Overview')
    def restart_client(policy):
        t.drain(.6)
        t.close()
        ARGS.timing_preload = policy
        C.Terminal.__init__(t, t.base, ARGS, http.url, 180, 55)
        t.capture('policy-restart-' + str(policy), ['Overview', 'planned-run'])
    def selected(title):
        t.open_palette(title)
        t.capture('policy-selected-' + str(len(t.keys)), [title + ' (selected)'])
        t.key(b'\x1b')
    restart_client('explicit-only')
    selected('Timing preload: Explicit only')
    check(True, 'CLI explicit-only initial override wins over saved background-index')
    t.command('Timing preload: Background index')
    selected('Timing preload: Background index')
    check(True, 'Palette can durably change policy after a CLI initial override')
    t.command('Timing preload: Explicit only')
    restart_client(None)
    selected('Timing preload: Explicit only')
    check(True, 'Palette explicit-only survives a fresh client without CLI override')
    restart_client('background-index')
    selected('Timing preload: Background index')
    check(True, 'CLI background-index initial override wins over saved explicit-only')


def main():
    global ARGS
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'client', 'preset-export', 'evidence'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    ARGS = args
    for name in ('daemon', 'client', 'preset_export'):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    if not args.evidence.resolve().is_relative_to('/tmp/opencode'):
        parser.error('private /tmp/opencode evidence required')
    args.palette_only = False
    args.harness = 'default-on Timing preload'
    C.demo.provider.STAGES = C.demo.provider.STAGES[:-1] + ['timing', 'signoff']
    C.demo.provider.EXECUTABLE_TIMING = True
    prepare = C.demo.prepare
    def prepare_timing(*a, **kw):
        base = prepare(*a, **kw)
        settings = base / 'project/synthetic-settings.json'
        value = json.loads(settings.read_text())
        value['executable_timing'] = True
        settings.write_text(json.dumps(value))
        return base
    C.demo.prepare = prepare_timing
    os.umask(0o077)
    C.run(args, acceptance=acceptance, focused=True, extra_runs=(3,), restart_acceptance=restart_acceptance)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--fixture-provider':
        provider(Path(sys.argv[2]), sys.argv[3:])
    else:
        main()
