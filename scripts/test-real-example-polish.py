#!/usr/bin/env python3
"""Native status/sidebar polish proof using PRIVATE SYNTHETIC evidence, not real ASIC.

Matching prebuilt --daemon/--client/--preset-export are required. No implicit build,
EDA, live-session mutation or canonical evidence writes. Actual HTTP and PTY cells,
ANSI attributes, SVGs and receipts remain in a new private /tmp/opencode directory.
Also exercises the sidebar harness's exact planning, delayed error, explicit launch,
cancellation, pinning, live schemes and unchanged Timing topology checks.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import signal
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('polish_sidebar', HERE / 'test-overview-sidebar.py')
sidebar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sidebar)
composition = sidebar.composition
field, sexp, require = sidebar.field, sidebar.sexp, sidebar.require
pane_rect, pane_body = sidebar.pane_rect, sidebar.pane_body


def startup_check(t, check, http, screen):
    sidebar.refinement.sidebar_geometry(screen, check)
    # This is before any palette command can replace the fresh client's default.
    left, top, right, bottom = pane_rect(screen, 'session')
    background = screen.cells[top + 1][right - 2][1][1]
    check(background.startswith('rgb:') and max(map(int, background[4:].split(','))) <= 16,
          'Fresh default paints an explicit black/near-black Session background')
    for title in ('session', 'runs', 'stage checklist', 'planned-run', 'synthesis',
                  'timing', 'placement', 'routing', 'checks', 'finalization'):
        _, y, _, _ = pane_rect(screen, title)
        x = screen.lines()[y].casefold().index(title)
        fg = screen.cells[y][x][1][0]
        channels = list(map(int, fg[4:].split(','))) if fg.startswith('rgb:') else []
        check(len(channels) == 3 and min(channels) >= 210 and max(channels) - min(channels) <= 20,
              'Fresh default has bright neutral header text: ' + title)


def acceptance(t, check, http, runs, presets):
    sidebar.acceptance(t, check, http, runs, presets)
    t.command('Color scheme: Carbon')
    t.command('Appearance: Color Vivid')
    def registry(): return http.rpc(domain='workspace')
    overview = next(w for w in field(registry(), 'workspaces') if field(w, 'preset') == ['overview'])
    wid = field(overview, 'id')
    def tile(kind):
        return next(x for x in field(registry(), 'tiles')
                    if field(x, 'workspace') == wid and field(x, 'kind') == kind)
    def zoom(kind):
        ws = registry()
        http.mutate(ws, '(Set_zoom (workspace %s) (tile (%s)))' %
                    (sexp(wid), sexp(field(tile(kind), 'id'))))
    def select(run):
        ws = registry()
        context = next(c for c in field(ws, 'contexts') if field(c, 'id') == field(overview, 'context'))
        http.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' %
                    (sexp(wid), sexp(field(context, 'id')), field(context, 'selection_revision'), sexp(run)))

    # Exact typed evidence row; do not infer meaning from arbitrary report strings.
    screen = t.capture('polish-evidence-label-value', ['Evidence: validated'])
    evidence_rows = [i for i, line in enumerate(screen.lines()) if 'Evidence: validated' in line]
    check(bool(evidence_rows), 'Validated summary evidence is visible in actual composed Overview')
    for y in evidence_rows:
        line = screen.lines()[y]
        x = line.index('Evidence: validated')
        label = [a[0] for _, a in screen.cells[y][x:x + len('Evidence:')]]
        value = [a[0] for _, a in screen.cells[y][x + len('Evidence: '):x + len('Evidence: validated')]]
        check(len(set(label)) == 1 and len(set(value)) == 1 and label[0] != value[0],
              'Evidence label stays neutral while only validated takes the semantic color')
        check(label[0] == 'rgb:216,216,220', 'Evidence label uses exact Carbon neutral foreground')
        check(value[0] == 'rgb:151,198,151', 'Validated evidence uses exact Carbon success green')

    # Allocate only private synthetic files. Registration/observation use normal HTTP;
    # there is no new provider execution or invented daemon Run_ref.
    provider = composition.demo.provider
    long_id = 'synthetic-readable-prefix-implementation-' + '0123456789abcdef' * 4
    created = []
    for name, complete in ((long_id, True), ('synthetic-polish-running-abcdef0987654321', False)):
        attempt = provider.allocate(t.base / 'results', provider.selection('success'), name)
        if complete:
            while provider.load(attempt / 'observation.json')['writer_active']:
                provider.advance(attempt)
        else:
            # Explicit static UI-token fixture: the ordinary synthetic provider
            # exposes live observations as "observing", not "running". Freeze
            # this private snapshot with the literal token under test. It has no
            # execution/report/metrics and makes no real producer-lifecycle claim.
            observation = provider.load(attempt / 'observation.json')
            observation.update(writer_active=False, observation_status='final',
                               state=dict(outcome=dict(status='running', exit_code=None)))
            provider.save(attempt / 'observation.json', observation)
        http.rpc('(Register %s)' % sexp([['attempt', str(attempt)], ['stream_id', name]]), wait=False)
        snapshot = sidebar.wait(lambda: (s if any(field(field(r, 'reference'), 'stream_id') == name
            for r in field(s, 'runs')) else None) if (s := http.rpc(wait=False)) else None,
            'private synthetic run registration ' + name)
        run = next(field(r, 'run') for r in field(snapshot, 'runs')
                   if field(field(r, 'reference'), 'stream_id') == name)
        http.rpc('(Observe %s)' % sexp(run), wait=False)
        created.append(run)
    sidebar.wait(lambda: [r for r in field(http.rpc(wait=False), 'runs')
                         if field(r, 'run') == created[1] and field(r, 'status') == 'running'],
                 'literal private running token observed')
    select(created[0])
    session = t.capture('polish-session-long-id-120x40', ['planned-run', 'Run: synthetic-readable', long_id[-8:]])
    run_row = next(line for line in pane_body(session, 'session') if line.startswith('Run:'))
    check('synthetic' in run_row and long_id[-8:] in run_row,
          'Narrow Session preserves meaningful first word and final eight hash characters')
    check(long_id not in run_row and any(marker in run_row for marker in ('~', '…')),
          'Long Session identity is visibly abbreviated within its actual one-third-width pane')
    zoom('live-status')
    t.capture('polish-session-zoom', ['Session'], ['planned-run'])
    t.key(b'\r')
    detail = t.capture('polish-session-exact-detail', ['Run: asic/' + long_id])
    check('Run: asic/' + long_id in detail.text(), 'Session inspection retains exact unabridged run identity')
    t.key(b'\x1b')
    t.command('Unzoom workspace')

    zoom('run-selector')
    t.capture('polish-selector-focused', ['runs'], ['planned-run'])
    # Local cap is bounded by actual viewport; ten rows fit in this zoomed panel.
    for _ in range(6): t.command('Run selector: More visible rows (+1)')
    screen = t.capture('polish-selector-exact-status-colors', ['completed', 'failed', 'running'])
    expected = {'completed': 'rgb:151,198,151', 'failed': 'rgb:235,139,151', 'running': 'rgb:151,177,226'}
    seen = set()
    for y, line in enumerate(screen.lines()):
        match = re.search(r'\b(completed|failed|running)\s*│\s*$', line)
        if not match: continue
        token = match.group(1)
        attrs = [a[0] for _, a in screen.cells[y][match.start(1):match.end(1)]]
        check(attrs == [expected[token]] * len(token),
              'Exact selector lifecycle token has field-specific ANSI color: ' + token)
        if token in ('completed', 'failed'):
            x = line.index('asic/')
            check(screen.cells[y][x][1][0] not in (expected['completed'], expected['failed']),
                  'Run identity remains independently readable beside ' + token)
        seen.add(token)
    check(seen == set(expected), 'Actual selector rows expose completed, failed and running tokens independently of IDs')
    baseline = registry()
    def non_poll_calls():
        # Normal client observation polling remains active for a running token.
        # The sidebar acceptance above checks byte-identical provider logs while
        # all runs are settled; here exclude only those explicit read-only polls.
        return [json.loads(line)['argv'] for line in
                (t.base / 'project/provider-calls.jsonl').read_text().splitlines()
                if json.loads(line)['argv'][:1] != ['observation']]
    calls = non_poll_calls()
    t.command('Color scheme: Crimson')
    crimson = t.capture('polish-selector-crimson-live', ['completed', 'failed', 'running'])
    check(crimson.cells != screen.cells, 'Live alternative scheme repaints actual selector attributes')
    t.command('Color scheme: Carbon')
    t.command('Reset presentation overrides (inherit)')
    t.command('Unzoom workspace')
    check(non_poll_calls() == calls,
          'Styling and selector capacity invoke no provider work beyond ordinary observation polling')
    select(runs[0])
    t.capture('polish-overview-restored', ['planned-run', 'Evidence: validated'])
    # Selection restoration is explicit; all presentation changes preserve registry.
    after = registry()
    check(field(after, 'tiles') == field(baseline, 'tiles'), 'Polish controls preserve exact tile/pin/hidden/geometry records')
    return 'Overview'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'client', 'preset-export'): parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    for name in ('daemon', 'client', 'preset_export'): setattr(args, name, getattr(args, name).resolve(strict=True))
    args.evidence = args.evidence or Path('/tmp/opencode') / ('real-example-polish-synthetic-' + secrets.token_hex(6))
    require(args.evidence.resolve().is_relative_to('/tmp/opencode'), 'Evidence must be private /tmp/opencode state')
    args.palette_only = False
    args.harness = 'Real-example frontend polish (PRIVATE SYNTHETIC fixture, no real ASIC claim)'
    os.umask(0o077)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Polish acceptance budget exhausted')))
    signal.alarm(args.timeout)
    try: composition.run(args, acceptance=acceptance, startup_check=startup_check)
    finally: signal.alarm(0)


if __name__ == '__main__': main()
