#!/usr/bin/env python3
"""Replay actual Overview state in a private native daemon and PTY (no EDA).

Only Get RPCs reach --live-url. Copies retained state and presentation bytes;
all toggles, zooms and restarts target the private daemon/client state.
"""
import argparse
from decimal import Decimal, ROUND_DOWN
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.request

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('overview_composition', HERE / 'test-frontend-composition.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
spec = importlib.util.spec_from_file_location('overview_fs0', HERE / 'test-fs0.py')
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
from http_client import Client, field, sexp, parse


class EvidenceClient(Client):
    def raw(self, path, data=None):
        # Match the native client's opt-in metadata negotiation. Legacy HTTP
        # callers deliberately receive summaries without timing_analysis.
        request = urllib.request.Request(self.url + path,
            data=None if data is None else sexp(data).encode(),
            headers={'Content-Type': 'application/sexp', 'X-Workbench-Protocol': '1',
                     'X-Workbench-Asic-Evidence-Metadata': '1',
                     'X-Workbench-Asic-Timing-Analysis': '2'})
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode()
        self.history.append(dict(path=path, response=text))
        result = parse(text)
        if path == '/api/hello':
            return result
        C.require(result[0] == 'Ok', text)
        return result[1]


def run(args):
    base = args.evidence
    for name in ('state', 'client-state', 'home', 'config'):
        (base / name).mkdir()
    original = {p: p.read_bytes() for p in args.source_state.glob('*.sexp')}
    original[args.preferences] = args.preferences.read_bytes()
    for path, raw in original.items():
        if path != args.preferences:
            (base / 'state' / path.name).write_bytes(raw)
    pref = base / 'client-state/hardcaml-workbench/terminal' / args.preferences.name
    pref.parent.mkdir(parents=True)
    pref.write_bytes(original[args.preferences])
    # Bypass Client.__init__: do not Open_project on the user's daemon.
    live = Client.__new__(Client)
    live.url, live.history = args.live_url, []
    if args.read_only_receipt:
        live.history = json.loads(args.read_only_receipt.read_text())
        def recorded(path):
            response = parse(next(e['response'] for e in live.history if e['path'] == path))
            return response if path == '/api/hello' else response[1]
        live.instance = field(recorded('/api/hello'), 'instance_id')
        snapshot = recorded('/api/v1/snapshot')
    else:
        live.instance = field(live.raw('/api/hello'), 'instance_id')
        snapshot = live.raw('/api/v1/snapshot', [['instance_id', live.instance]])
    live.project = next(field(p, 'id') for p in field(snapshot, 'projects')
                        if field(field(p, 'root'), 'path') == str(args.project_root))
    ws = recorded('/api/v1/workspace') if args.read_only_receipt else live.rpc(domain='workspace')
    asic = recorded('/api/v1/asic') if args.read_only_receipt else live.rpc(wait=False)
    (base / 'live-read-only.json').write_text(json.dumps(live.history, indent=2))
    session = F.Session(args, base, args.project_root)
    session.env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', OPENROAD_THREADS='1',
                       _OPENLANE_MAX_CORES='1', HOME=str(base / 'home'), XDG_CONFIG_HOME=str(base / 'config'),
                       OPAMROOT=os.environ.get('OPAMROOT', str(Path.home() / '.opam')))
    terminal = None
    result = dict(status='failed', instance=live.instance, session=field(ws, 'session_id'),
                  revision=field(ws, 'revision'), checks=[])

    def check(ok, message):
        C.require(ok, message)
        result['checks'].append(message)

    def preferences():
        return parse(pref.read_text())

    def header_visible(screen, kind):
        return kind in screen.lines()[1].casefold()

    def without_compression(value):
        # Compare all other sparse fields, including exact header/title overrides.
        if not isinstance(value, list):
            return value
        result = [without_compression(v) for v in value
                  if not (isinstance(v, list) and v and v[0] in
                          ('global_compression', 'workspace_compression', 'string_compression'))]
        if result and all(isinstance(v, list) and len(v) == 2 for v in result):
            if set(dict(result)) == {'tile', 'workspace', 'kind'}:
                return None  # a compression-only sparse tile record
        return [v for v in result if v is not None]

    try:
        session.start()
        http = EvidenceClient(session.url, args.project_root, C.demo.switch_name())
        private = http.rpc(domain='workspace')
        check(private == ws, 'Exact live workspace/session/tile/selection identity copied')
        overview = next(w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview'])
        wid = field(overview, 'id')
        context = next(c for c in field(ws, 'contexts') if field(c, 'id') == field(overview, 'context'))
        selected = field(context, 'selected_run')[0]
        execution = next(r for r in field(asic, 'runs') if field(r, 'run') == selected)
        result.update(run=selected, execution_status=field(execution, 'status'),
                      endpoint=field(field(execution, 'selection')[0], 'endpoint'))
        # Both HTTP and PTY use the exact root/environment, hence the same ASIC
        # cache identity. No project action is submitted.
        terminal = C.Terminal(base, args, session.url, project_root=args.project_root)
        terminal.capture('baseline', ['Overview'])
        before = preferences()
        check(field(before, 'tile_headers') == field(parse(original[args.preferences].decode()), 'tile_headers'),
              'Initial saved headers restored exactly')
        terminal.command('Timing preload: Explicit only')
        terminal.capture('explicit-preload', ['Overview'])
        # The private client hydrates retained summaries; the live daemon's Get
        # may not have loaded the selected summary at the time of capture.
        def loaded_summary():
            summaries = [s for s in field(http.rpc(wait=False), 'summaries')
                         if field(s, 'run') == selected]
            return next((s for s in summaries if dict(s).get('timing_analysis')),
                        summaries[0] if summaries else None)
        selected_summary = loaded_summary()
        if not selected_summary:
            terminal.drain(1.2)
            selected_summary = loaded_summary()
        analysis = dict(selected_summary).get('timing_analysis', []) if selected_summary else []
        metrics = field(analysis[0], 'metrics') if analysis else []
        slack = next((m for m in metrics if field(m, 'key') == 'setup_slack'
                      and field(m, 'value') and field(m, 'unit_') == ['ns']), None)
        result['timing_precision_checked'] = bool(slack) and not args.baseline
        if slack and not args.baseline:
            def displayed(places):
                value = Decimal(field(slack, 'value')[0])
                return format(value.quantize(Decimal(10) ** -places, rounding=ROUND_DOWN), '.%df' % places)
            timing = next(t for t in field(ws, 'tiles') if field(t, 'workspace') == wid and field(t, 'kind') == 'timing')
            http.mutate(http.rpc(domain='workspace'), '(Set_zoom (workspace %s) (tile (%s)))' %
                        (sexp(wid), sexp(field(timing, 'id'))))
            terminal.drain(1.2)
            terminal.capture('overview-timing-default-three', ['setup ' + displayed(3) + ' ns'])
            terminal.command('Timing: Truncate to 6 decimal places')
            terminal.capture('overview-timing-six', ['setup ' + displayed(6) + ' ns'])
            terminal.key(b'd')
            terminal.capture('overview-timing-detail-six', ['setup_slack /', displayed(6) + ' ns'])
            terminal.command('Timing: Truncate to 3 decimal places')
            terminal.capture('overview-timing-detail-three', ['setup_slack /', displayed(3) + ' ns'])
            terminal.key(b'\x1b')
            terminal.command('Unzoom workspace')
            check(any(dict(s).get('timing_analysis') == analysis
                      for s in field(http.rpc(wait=False), 'summaries') if field(s, 'run') == selected),
                  'Overview Timing 3/6 compact/detail formatting preserves raw analysis')
            result['checks'].append('Overview Timing default 3 and focused-tile 6 verified in native cells')
        for kind in ('placement', 'routing'):
            tile = next(t for t in field(ws, 'tiles') if field(t, 'workspace') == wid and field(t, 'kind') == kind)
            http.mutate(http.rpc(domain='workspace'), '(Set_zoom (workspace %s) (tile (%s)))' %
                        (sexp(wid), sexp(field(tile, 'id'))))
            terminal.drain(1.2)  # acknowledge private workspace poll/zoom/focus
            initial = terminal.capture(kind + '-headers-false', [kind + ': completed'])
            check(not header_visible(initial, kind), kind + ' saved header=false intentionally hides its border title')
            if not args.baseline:
                check('No terminal result imported' not in initial.text(), kind + ' uses stage evidence without a terminal result')
            # Headers intentionally gates titles. Verify it independently, then
            # restore the actual false override before the compression matrix.
            terminal.command('Toggle focused tile header')
            titled = terminal.capture(kind + '-header-on', [kind])
            check(header_visible(titled, kind), kind + ' Header control restores border title')
            terminal.command('Toggle focused tile header')
            check(not header_visible(terminal.capture(kind + '-header-off'), kind), kind + ' Header control hides only heading')
            terminal.key(b'\r')
            detail = terminal.capture(kind + '-detail', ['No terminal result imported'] if args.baseline else
                                      [kind + ': completed', 'Stage ID: ' + kind])
            # Palette notices reclaim the bottom row; compare the common body
            # viewport, excluding the bottom border/notice geometry only.
            body = detail.lines()[2:-3]
            for scope in ('global', 'workspace', 'focused tile'):
                saved = without_compression(preferences())
                for label in ('Compress identifiers', 'Show full identifiers', 'Reset compression (inherit)'):
                    terminal.command('Strings (%s): %s' % (scope, label))
                    screen = terminal.capture(kind + '-' + scope.replace(' ', '-') + '-' + label.split()[0])
                    if not args.baseline:
                        check('No terminal result imported' not in screen.text() and 'completed' in screen.text(),
                              kind + '/' + scope + '/' + label + ' retains stage body')
                    check(screen.lines()[2:-3] == body and not header_visible(screen, kind),
                          kind + '/' + scope + '/' + label + ' preserves exact body and title visibility')
                    check(without_compression(preferences()) == saved,
                          kind + '/' + scope + '/' + label + ' preserves unrelated preferences')
            # Retain explicit choices at every scope across a real process restart.
            for scope, label in (('global', 'Show full identifiers'), ('workspace', 'Compress identifiers'),
                                 ('focused tile', 'Show full identifiers')):
                terminal.command('Strings (%s): %s' % (scope, label))
            terminal.key(b'\x1b')
            terminal.capture(kind + '-escape-recovery', [kind + ': completed'],
                             ['No terminal result imported', 'Stage ID: ' + kind])
            check(field(preferences(), 'tile_headers') == field(before, 'tile_headers'),
                  kind + ' Escape recovers compact stage summary without changing headers')
            persisted = preferences()
            terminal.close()
            terminal = C.Terminal(base, args, session.url, project_root=args.project_root)
            screen = terminal.capture(kind + '-restart', [kind + ': completed'])
            check(preferences() == persisted, kind + ' exact scoped choices survive fresh client restart')
            check(field(preferences(), 'tile_headers') == field(before, 'tile_headers'),
                  kind + ' header overrides survive compression and client restart')
            terminal.command('Unzoom workspace')
        check(field(http.rpc(domain='workspace'), 'contexts') == field(ws, 'contexts'), 'Exact selected run preserved')
        jobs = http.raw('/api/v1/snapshot', [['instance_id', http.instance]])
        check(not field(jobs, 'jobs'), 'Zero private provider/domain jobs')
        terminal.close()
        terminal = None
        session.stop()
        # Derived, explicitly labelled missing-domain fixture: remove only the
        # physical observations from the PRIVATE retained cache. Keep the actual
        # Timing observation, summary and absent finalization. No provider runs.
        changed = []
        for path in (base / 'state').glob('asic-*.sexp'):
            cached = parse(path.read_text())
            fields = dict(cached)
            if 'runs' not in fields:
                continue
            found = False
            for execution in fields['runs']:
                if field(execution, 'run') == selected:
                    for pair in execution:
                        if pair[0] == 'stages':
                            pair[1] = [s for s in pair[1] if field(s, 'id') == 'timing']
                            found = True
            if found:
                path.write_text(sexp(cached))
                changed.append(path.name)
        check(bool(changed), 'Derived Timing-only missing-domain cache created privately')
        result['timing_only_fixture'] = changed
        session.start()
        http = EvidenceClient(session.url, args.project_root, C.demo.switch_name())
        cached = http.rpc(wait=False)
        observed = next(r for r in field(cached, 'runs') if field(r, 'run') == selected)
        check([field(s, 'id') for s in field(observed, 'stages')] == ['timing'],
              'Private native daemon restored Timing-only observation')
        check(not [f for f in field(cached, 'finalizations') if field(f, 'run') == selected],
              'No finalization fabricated for Timing-only fixture')
        terminal = C.Terminal(base, args, session.url, project_root=args.project_root)
        terminal.capture('timing-only-overview', ['Overview'])
        for kind in ('placement', 'routing'):
            tile = next(t for t in field(ws, 'tiles') if field(t, 'workspace') == wid and field(t, 'kind') == kind)
            http.mutate(http.rpc(domain='workspace'), '(Set_zoom (workspace %s) (tile (%s)))' %
                        (sexp(wid), sexp(field(tile, 'id'))))
            terminal.drain(1.2)
            terminal.capture('timing-only-' + kind, ['Stage: not reported'], ['completed'])
            terminal.key(b'\r')
            terminal.capture('timing-only-' + kind + '-detail',
                             ['No terminal result imported'] if args.baseline else
                             ['Stage: not reported', 'Stage ID: ' + kind],
                             [] if args.baseline else ['No terminal result imported', 'completed', 'Cell count:'])
            terminal.command('Unzoom workspace')
        jobs = http.raw('/api/v1/snapshot', [['instance_id', http.instance]])
        check(not field(jobs, 'jobs'), 'Timing-only domain-missing views allocate zero jobs')
        result['status'] = 'passed'
    finally:
        if terminal:
            terminal.close()
        session.stop()
        check(all(p.read_bytes() == raw for p, raw in original.items()), 'Source state and user preferences byte-identical')
        (base / 'verified.json').write_text(json.dumps(result, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'client', 'source-state', 'project-root', 'preferences'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--live-url', required=True)
    p.add_argument('--read-only-receipt', type=Path,
                   help='Replay an earlier live-read-only.json capture without contacting the live daemon')
    p.add_argument('--baseline', action='store_true', help='Capture pre-fix output without fixed-body assertions')
    args = p.parse_args()
    for name in ('daemon', 'client', 'source_state', 'project_root', 'preferences'):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    args.outer_timeout = 30
    os.umask(0o077)
    args.evidence = Path(tempfile.mkdtemp(prefix='overview-compression-', dir='/tmp/opencode'))
    print('Evidence: ' + str(args.evidence), flush=True)
    run(args)
    print('PASS Overview compression private HTTP/PTY', flush=True)


if __name__ == '__main__':
    main()
