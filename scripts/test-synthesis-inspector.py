#!/usr/bin/env python3
"""FS1/F06 cached real synthesis inspector acceptance (stdlib + strace, no build).

Copies saved Workbench state, runs private existing binaries, retains RPC stdout,
commands, PTY ANSI/screens and syscall evidence. Never requests provider work.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import tempfile
import time
import traceback

spec = importlib.util.spec_from_file_location('dashboard', Path(__file__).with_name('test-fs0-dashboard.py'))
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)
fs0 = dashboard.fs0
field, record, require = fs0.field, fs0.record, fs0.require


class Terminal(dashboard.Terminal):
    def key(self, data):
        with (self.session.evidence / 'keys.jsonl').open('a') as out:
            out.write(json.dumps(dict(time=time.time(), hex=data.hex(), text=data.decode('ascii'))) + '\n')
        os.write(self.master, data)
        return self.drain(.2)

    def palette(self, title):
        for key in (b' ', b'c', b'c'):
            self.key(key)
        self.key(title.encode())
        self.capture('palette-' + str(time.time_ns()), [title])
        self.key(b'\r')


def exercise(args):
    source = args.source_state.resolve()
    config = args.example_root / 'hardcaml-workbench-asic.sexp'
    cfg = record(fs0.parse(config.read_text()))
    watched = [source, config, Path(cfg['results_root']), Path(cfg['provider_executable'])]
    before = dashboard.inventory(watched)
    (args.evidence / 'files-before.json').write_text(json.dumps(before, indent=2))
    state = args.evidence / 'state'
    state.mkdir()
    for path in source.glob('*.sexp'):
        require(not path.is_symlink() and path.name.startswith(('asic-', 'workspace-')), 'Unexpected state input')
        shutil.copy2(path, state / path.name)
    # -D leaves the daemon as Session's child, so normal Session.stop reaps it.
    trace = args.evidence / 'daemon.strace'
    daemon = args.daemon.resolve()
    wrapper = args.evidence / 'traced-daemon'
    wrapper.write_text('#!/bin/sh\nexec ' + shlex.join([
        shutil.which('strace'), '-D', '-f', '-qq', '-s', '4096', '-yy',
        '-e', 'trace=%file,%process', '-o', str(trace), str(daemon)]) + ' "$@"\n')
    wrapper.chmod(0o700)
    args.daemon = wrapper
    session = fs0.Session(args, args.evidence, args.example_root)
    terminal = None
    result = dict(status='failed', checks=[], evidence=str(args.evidence))

    def check(ok, message):
        result['checks'].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)

    def mutate(mutation):
        return session.mutate(session.rpc('workspace'), mutation)

    def select(workspace, run):
        ws = session.rpc('workspace')
        context = next(c for c in field(ws, 'contexts') if field(c, 'id') == field(workspace, 'context'))
        return session.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' % (
            field(workspace, 'id'), field(context, 'id'), field(context, 'selection_revision'), fs0.sexp(run)))

    def ordinary(text, summary):
        check(field(summary, 'execution_file') not in text and
              field(summary, 'producer') not in text and '"reference"' not in text and
              str(Path(cfg['results_root'])) not in text, 'Ordinary summary/table hides raw producer and execution paths')

    def table_order(text, mode, summary):
        rows = [(int(n), name) for n, name in re.findall(r'[ >]\s+(\d+)\s+(sg13\w+)', text)]
        check(len(rows) >= 2, 'Table exposes at least two real rows')
        key = {'count-desc': lambda r: (-r[0], r[1]), 'count-asc': lambda r: (r[0], r[1]),
               'name-asc': lambda r: r[1], 'name-desc': lambda r: r[1]}[mode]
        check(rows == sorted(rows, key=key, reverse=mode == 'name-desc'), 'Visible rows ordered ' + mode)
        cells = dict((name, int(n)) for name, n in field(summary, 'cells'))
        check(all(cells.get(name) == n for n, name in rows), 'Visible counts agree with cached source')

    try:
        session.start()
        initial = session.rpc('workspace')
        for run in field(session.rpc('asic'), 'runs'):
            session.rpc('asic', '(Load_summary ' + fs0.sexp(field(run, 'run')) + ')', wait=True)
        baseline = session.rpc('asic')
        summaries = {int(field(s, 'cell_count')[0]): s for s in field(baseline, 'summaries')}
        check(set(summaries) == {673, 685}, 'Real cached totals are 673 and 685')
        a, b = summaries[685], summaries[673]
        ra, rb = field(a, 'run'), field(b, 'run')
        check(all(field(s, 'freshness') == 'Cached_unverified' for s in summaries.values()), 'Replay is cached/unverified')
        demo = next(w for w in reversed(field(initial, 'workspaces'))
                    if len([t for t in field(initial, 'tiles') if field(t, 'workspace') == field(w, 'id')]) == 2
                    and all(field(t, 'kind') == 'synthesis' for t in field(initial, 'tiles') if field(t, 'workspace') == field(w, 'id')))
        tiles = [t for t in field(initial, 'tiles') if field(t, 'workspace') == field(demo, 'id')]
        for tile in tiles:
            mutate('(Set_tile_binding (tile %s) (binding Follow))' % field(tile, 'id'))
        select(demo, ra)
        terminal = Terminal(session)
        discovery = next(p for p in args.evidence.glob('discovery-*') if p.is_dir())
        (args.evidence / 'commands.json').write_text(json.dumps(dict(
            acceptance=['python3', str(Path(__file__).resolve())],
            daemon=[str(wrapper), '--port', '0', '--discovery-dir', str(discovery),
                    '--state-dir', str(state)],
            traced_daemon=wrapper.read_text(),
            pty=[str(args.client), '--connect', session.url, '--project-root', str(session.root)],
            environment_overrides={key: session.env[key] for key in
                ('XDG_STATE_HOME', 'OMP_NUM_THREADS', 'OPENROAD_THREADS', '_OPENLANE_MAX_CORES')},
            term='xterm-256color', pty_size=dict(width=120, height=40)), indent=2))
        terminal.capture('01-full-grid', ['Overview', 'Cell count: 685'])
        terminal.palette('Switch to ' + field(demo, 'name'))
        terminal.capture('02-two-tile-grid', ['Cell count: 685'])
        terminal.palette('Zoom focused tile')
        text = terminal.capture('03-zoom-summary', ['Cell count: 685', 'Cached_unverified'])
        ordinary(text, a)
        # Initial client metadata and cached loads have settled. All later UI/RPC
        # activity must be provider/report-free, including context changes.
        time.sleep(.3)
        trace_offset = trace.stat().st_size
        result['trace_baseline_offset'] = trace_offset
        terminal.key(b'\r')
        text = terminal.capture('04-default-cells', ['Cells | Count descending'])
        table_order(text, 'count-desc', a)
        ordinary(text, a)
        for label, mode in [('Count ascending', 'count-asc'), ('Cell type ascending', 'name-asc'),
                            ('Cell type descending', 'name-desc'), ('Count descending', 'count-desc')]:
            terminal.key(b's')
            text = terminal.capture('05-sort-' + mode, ['Cells | ' + label])
            table_order(text, mode, a)
        # Cursor identity survives sorting; exercise both character and arrow movement.
        terminal.key(b'j')
        down = terminal.capture('06-j')
        terminal.key(b'k')
        up = terminal.capture('06-k')
        check(down != up, 'j/k move selected cell')
        terminal.key(b'\x1b[B')
        check(terminal.capture('06-arrow-down') == down, 'Down arrow equals j')
        terminal.key(b'\x1b[A')
        check(terminal.capture('06-arrow-up') == up, 'Up arrow equals k')
        terminal.key(b'/mux2\r')
        text = terminal.capture('07-suffix-filter', ['sg13cmos5l_mux2_1', '128'], ['sg13cmos5l_dfrbpq_1'])
        ordinary(text, a)
        terminal.key(b'\r')
        terminal.capture('08-details', ['Cell type: sg13cmos5l_mux2_1', 'Count: 128',
            'Share: %.2f%% of reported total' % (128 / 685 * 100), 'Reported total: 685'])
        terminal.key(b'e')
        pages = [terminal.capture('09-evidence-start', ['Synthesis evidence'])]
        # Preserve every scroll screen. Strip only frame/padding/line wrapping when
        # checking exact long producer data; no substring/sentinel approximation.
        for i in range(100):
            terminal.key(b'j')
            pages.append(terminal.capture('09-evidence-scroll-%03d' % i))
        compact = ''.join(''.join(line.strip().strip('|').strip() for line in page.splitlines()[1:-1]) for page in pages)
        # The complete value occurs on consecutive body lines in at least one
        # contiguous scroll sequence; collect each screen independently as well.
        body_lines = []
        for page in pages:
            for line in page.splitlines():
                line = line.strip().strip('|').strip()
                if line not in body_lines:
                    body_lines.append(line)
        joined = ''.join(body_lines)
        check(field(a, 'execution_file') in compact or field(a, 'execution_file') in joined,
              'Evidence exposes full exact execution path across wrapped lines')
        producer = field(a, 'producer')
        check(producer in compact or producer in joined, 'Evidence exposes complete exact raw producer JSON through scrolling')
        terminal.key(b'\x1b')
        terminal.capture('10-evidence-back', ['Cells | Count descending', 'sg13cmos5l_mux2_1'])
        terminal.palette('Synthesis: Clear cell filter')
        terminal.palette('Synthesis: Sort name ascending')
        text = terminal.capture('11-palette-name-sort', ['Cells | Cell type ascending'])
        table_order(text, 'name-asc', a)
        terminal.key(b'/mux2.*')
        time.sleep(1.0)  # Allow normal daemon polling to clear transient notices.
        terminal.capture('12-editing-filter', ['FILTER INPUT', 'Ctrl-U clear', 'mux2.*'])
        terminal.key(b'\r')
        terminal.capture('12-no-match', ['No cells match.', 'Filter: "mux2.*"', '0 matches'])
        terminal.key(b'\r')
        terminal.capture('12-no-match-enter', ['No cells match.', 'Ctrl-U clears filter'], ['Cell type:'])
        terminal.key(b'\x15')  # Ctrl-U must recover even after leaving filter input.
        terminal.capture('12-filter-recovered', ['sg13cmos5l_'], ['No cells match.', 'FILTER INPUT'])
        terminal.key(b'\x1b')
        terminal.capture('12-no-match-back')
        terminal.palette('Synthesis: Clear cell filter')
        terminal.palette('Synthesis: Browse cell table')
        terminal.key(b'/a22oi\r')
        terminal.key(b'\r')
        terminal.capture('13-before-run-switch', ['Cell type: sg13cmos5l_a22oi_1', 'Reported total: 685', 'Count: 58'])
        select(demo, rb)
        text = terminal.capture('14-context-switch-cells', ['Cells |', field(rb, 'id')],
                                ['Cell type:', 'Reported total: 685', 'Share:'])
        ordinary(text, b)
        terminal.key(b'\r')
        check(re.search(r'\b56\s+sg13cmos5l_a22oi_1', text) is not None and
              re.search(r'\b58\s+sg13cmos5l_a22oi_1', text) is None,
              'New run label has new cell count 56, never old count 58')
        terminal.capture('15-new-run-details', ['Cell type: sg13cmos5l_a22oi_1',
            'Reported total: 673', 'Count: 56',
            'Share: %.2f%% of reported total' % (56 / 673 * 100)], ['Count: 58'])
        terminal.key(b'\x1b')
        terminal.palette('Unzoom workspace')
        terminal.key(b'\t')
        terminal.capture('16-other-tile-summary', ['Cell count: 673', 'Cells | Cell type ascending'])
        terminal.key(b'\r')
        terminal.capture('17-independent-sort', ['Cells | Count descending', 'Cells | Cell type ascending'])
        terminal.key(b'\t')
        mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' % (field(tiles[0], 'id'), fs0.sexp(ra)))
        terminal.palette('Synthesis: Clear cell filter')
        terminal.palette('Synthesis: Summary')
        terminal.key(b'\t')
        terminal.palette('Synthesis: Summary')
        text = terminal.capture('18-pin-A-follow-B', ['Cell count: 685', 'Cell count: 673', 'PIN', 'FOLLOW'])
        lines = text.splitlines()
        check('Cell count: 685' in '\n'.join(line[:60] for line in lines) and
              'Cell count: 673' in '\n'.join(line[60:] for line in lines), 'Pinned A left / following B right have correct independent totals')
        after = session.rpc('asic')
        check(field(baseline, 'runs') == field(after, 'runs'), 'No run launches or changes')
        check(field(baseline, 'operations') == field(after, 'operations'), 'No new operations after cached load')
        check(field(baseline, 'summaries') == field(after, 'summaries'), 'Cached summaries unchanged by inspection')
        tail = trace.read_bytes()[trace_offset:].decode()
        (args.evidence / 'post-cache.strace').write_text(tail)
        check('execve(' not in tail and 'execveat(' not in tail, 'No subprocess launches after initial cached load')
        check(str(Path(cfg['results_root'])) not in tail, 'No provider result/report accesses after initial cached load')
        all_trace = trace.read_text()
        check(not any('execve' in line and cfg['provider_executable'] in line for line in all_trace.splitlines()), 'Provider executable never launched')
        result['status'] = 'passed'
    except Exception:
        result['error'] = traceback.format_exc()
        raise
    finally:
        if terminal:
            terminal.close()
        if session.process:
            session.stop()
        after_files = dashboard.inventory(watched)
        (args.evidence / 'files-after.json').write_text(json.dumps(after_files, indent=2))
        result['input_files_unchanged'] = before == after_files
        if before != after_files:
            result['status'] = 'failed'
        (args.evidence / 'result.json').write_text(json.dumps(result, indent=2))
        require(before == after_files, 'Source state/config/provider files changed')


def main():
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-state', type=Path, default=Path('/tmp/opencode/workbench-fs0-91em64rl/real/state'))
    parser.add_argument('--example-root', type=Path, default=repo.parent / 'hardcaml_asic_example')
    parser.add_argument('--client', type=Path, default=repo / '_build/default/terminal/main.exe')
    parser.add_argument('--daemon', type=Path, default=repo / '_build/default/daemon/main.exe')
    args = parser.parse_args()
    require(shutil.which('strace'), 'strace is required for no-provider/report-access acceptance')
    args.outer_timeout = 60
    args.evidence = Path(tempfile.mkdtemp(prefix='workbench-synthesis-inspector-', dir='/tmp/opencode'))
    print('Evidence: ' + str(args.evidence), flush=True)
    exercise(args)
    print('PASS: FS1/F06 cached synthesis inspector', flush=True)


if __name__ == '__main__':
    main()
