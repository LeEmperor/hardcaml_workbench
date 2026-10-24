#!/usr/bin/env python3
"""Private HTTP/PTY cooperative Testing acceptance; requires prebuilt executables.

No builds, EDA, live sessions or project configuration are touched. All daemon,
client, fixture and evidence state lives in a new /tmp/opencode directory.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import struct
import sys
import tempfile
import termios
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('native_testing', HERE / 'test-fs2-native.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
field, require, sexp = native.field, native.require, native.sexp
PANES = ['simulation-catalog', 'simulation-attempts', 'simulation-cases',
         'simulation-detail', 'simulation-artifacts', 'simulation-logs']


class Terminal(native.Terminal):
    width, height = 120, 40

    def drain(self, seconds=.3):
        super().drain(seconds)
        return native.fs0.terminal_screen(bytes(self.data), self.width, self.height)

    def resize(self, width, height):
        self.width, self.height = width, height
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
        # This child has no controlling PTY, so ioctl alone need not notify it.
        # Wait for painted edges, not old text reconstructed in a resized grid.
        os.kill(self.process.pid, signal.SIGWINCH)
        self.wait_viewport('resize-%dx%d' % (width, height))

    def wait_viewport(self, label):
        deadline = time.monotonic() + 15
        while True:
            text = self.drain(.2)
            rows = text.splitlines()
            top = rows[1] if len(rows) > 1 else ''
            bottom = rows[self.height - 2] if len(rows) >= self.height - 1 else ''
            footer = rows[self.height - 1] if len(rows) >= self.height else ''
            # Border rows contain only single-cell box-drawing/plain glyphs.
            if (len(top) == self.width and top.endswith('╮') and
                    len(bottom) == self.width and bottom.endswith('╯') and
                    footer.startswith('Space c c commands')):
                break
            if time.monotonic() >= deadline:
                self.save(label + '-unpainted', text)
                raise AssertionError('%s: no painted %dx%d viewport; top=%d bottom=%d footer=%r' %
                                     (label, self.width, self.height, len(top), len(bottom), footer))
        self.save(label + '-painted', text)
        proof = dict(label=label, width=self.width, height=self.height,
                     top_right_border_column=len(top), bottom_right_border_column=len(bottom),
                     bottom_pane_row=self.height - 1, footer_row=self.height, passed=True)
        with (self.session.evidence / 'viewport-checks.jsonl').open('a') as out:
            out.write(json.dumps(proof) + '\n')


def run(args):
    evidence = args.evidence
    for name in ('project', 'state', 'home', 'config', 'tmp'):
        (evidence / name).mkdir()
    root = evidence / 'project'
    (root / 'dune-project').write_text('(lang dune 3.22)\n(name testing_workspace_acceptance)\n')
    control, calls = evidence / 'control.json', evidence / 'calls.jsonl'

    def mode(value):
        control.write_text(json.dumps(dict(mode=value)))

    mode('pass')
    (root / 'hardcaml-workbench-simulation.sexp').write_text(sexp([
        ('schema_version', 1), ('provider_executable', sys.executable),
        ('provider_args', [str(HERE / 'fixtures/fs2_provider.py'), '--control', str(control), '--calls', str(calls)]),
        ('discovery_timeout_seconds', 10), ('run_timeout_seconds', 90)]))
    session = native.Session(args, evidence, root)
    session.env.update(HOME=str(evidence / 'home'), XDG_CONFIG_HOME=str(evidence / 'config'),
                       TMPDIR=str(evidence / 'tmp'), PYTHONDONTWRITEBYTECODE='1')
    terminal = None
    result = dict(status='failed', checks=[])

    def check(ok, message):
        result['checks'].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)

    def records():
        return [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []

    def workspace():
        return session.api(domain='workspace')

    def mutate(mutation):
        snapshot = workspace()
        return session.api(domain='workspace', operation=['Mutate',
            ['expected_revision', field(snapshot, 'revision')], ['mutation', mutation]])

    def wait_for(predicate, message):
        deadline = time.monotonic() + 25
        while not predicate():
            require(time.monotonic() < deadline, message)
            if terminal:
                terminal.drain(.15)
            time.sleep(.1)

    try:
        session.start()
        terminal = Terminal(session)
        terminal.capture('startup', ['Overview'])
        # This suite checks exact provenance; compact rendering has its own WB-073 suite.
        terminal.palette('Strings (global): Show full identifiers')
        terminal.palette('Create Testing workspace')
        wait_for(lambda: any(field(w, 'preset') == ['testing'] for w in field(workspace(), 'workspaces')),
                 'Testing bootstrap')
        terminal.capture('testing-layout-120x40', ['simulation-catalog', 'simulation-detail', 'Project tests'])
        terminal.wait_viewport('initial-120x40')
        check(True, 'initial Testing viewport painted at actual 120 columns and 40 rows')
        terminal.resize(180, 55)
        terminal.capture('testing-layout-180x55', ['simulation-catalog', 'simulation-detail', 'Generic project tests'])
        check(True, 'resized Testing viewport painted at actual 180 columns and 55 rows')
        terminal.resize(120, 40)
        terminal.capture('testing-layout-return-120x40', ['simulation-catalog', 'simulation-detail', 'Generic project tests'])
        check(True, 'Testing viewport repainted at actual 120 columns and 40 rows after returning')
        check(not records(), 'render and workspace navigation never invoke discovery or tools')
        snapshot = workspace()
        testing = next(w for w in field(snapshot, 'workspaces') if field(w, 'preset') == ['testing'])
        wid = field(testing, 'id')
        tiles = [t for t in field(snapshot, 'tiles') if field(t, 'workspace') == wid]
        check(all(any(field(t, 'kind') == kind for t in tiles) for kind in PANES), 'all six cooperative panes installed')
        check(not any(field(t, 'kind') == 'run-selector' for t in tiles), 'project-only Testing has no ASIC selector')
        # Navigation, Session, generic tests, execution, Catalog.
        for _ in range(4):
            terminal.key(b'\t')
        terminal.palette('Zoom focused tile')
        terminal.key(b'd')
        wait_for(lambda: len(records()) == 1, 'explicit Discover reaches provider')
        terminal.capture('catalog-discovered', ['first', 'second', 'Ready for explicit launch'])
        terminal.key(b'x')  # remove first: exact subset is second
        terminal.key(b'/'); terminal.key(b'second'); terminal.key(b'\r')
        terminal.capture('catalog-filter-subset', ['Selected cases: second'], absent=['[x] first'])
        terminal.key(b'\r')
        terminal.capture('subset-form', ['CASES', 'second'])
        check(len(records()) == 1, 'filter/subset/form navigation invokes no tools')
        # Cases, seed, then confirmation (the fixture declares no parameters).
        terminal.key(b'\r'); terminal.key(b'\r')
        terminal.capture('subset-confirm', ['CONFIRM', 'second'])
        terminal.key(b'\r')
        wait_for(lambda: any(r['operation'] == 'run' for r in records()), 'explicit launch reaches provider')
        run_call = next(r for r in records() if r['operation'] == 'run')
        selection = field(run_call['request'], 'selection')
        check(field(selection, 'cases') == ['second'] and field(selection, 'asic_inputs') == [],
              'PTY launch captures exact selected subset without ASIC provenance')
        aid = field(run_call['request'], 'attempt_id')
        done = session.done(aid)
        check(field(done, 'outcome') == 'Passed', 'selected subset produces actual normalized fixture result')
        terminal.palette('Unzoom workspace')
        terminal.key(b'\t')  # Attempts shares the just launched attempt.
        terminal.palette('Simulation: Reopen ' + aid + ' fixture')
        terminal.key(b'\t')  # Cases
        terminal.key(b'j')
        terminal.key(b'\t')  # Detail
        terminal.palette('Zoom focused tile')
        terminal.capture('shared-detail', ['second', aid])
        terminal.palette('Unzoom workspace')
        terminal.key(b'\t')  # Artifacts
        terminal.key(b'j')
        terminal.palette('Zoom focused tile')
        terminal.capture('shared-artifacts', ['second-raw'])
        terminal.key(b'e')
        wait_for(lambda: bool(list((evidence / 'tmp').glob('*simulation*/artifact*'))),
                 'cooperative exact artifact export')
        exported = list((evidence / 'tmp').glob('*simulation*/artifact*'))[0]
        artifact = next(a for a in field(done, 'artifacts') if field(a, 'id').endswith('-second-raw'))
        check(hashlib.sha256(exported.read_bytes()).hexdigest() == field(artifact, 'sha256')[0],
              'cooperative export retains exact selected artifact bytes and SHA256')
        terminal.palette('Unzoom workspace')
        terminal.key(b'\t')  # Logs
        terminal.palette('Zoom focused tile')
        terminal.capture('shared-exact-logs', [aid, field(done, 'job')[:25], 'job-2'])
        terminal.palette('Simulation: Rerun case second (original inputs; current project)')
        wait_for(lambda: len([r for r in records() if r['operation'] == 'run']) == 2,
                 'cooperative captured targeted rerun')
        child_call = [r for r in records() if r['operation'] == 'run'][-1]
        child = session.done(field(child_call['request'], 'attempt_id'))
        check(field(child, 'id') != aid and field(field(child, 'parent')[0], 'attempt_id') == aid
              and field(field(field(child, 'captured'), 'selection'), 'cases') == ['second'],
              'cooperative targeted rerun captures exact parent and original selected case inputs')
        terminal.palette('Simulation: Reopen ' + aid + ' fixture')
        terminal.palette('Unzoom workspace')
        # A second workspace with identical definitions must not inherit selection.
        created = mutate(['Create_workspace', ['window', field(testing, 'window')],
                          ['name', 'Independent Testing'], ['context', field(testing, 'context')]])
        other = next(w for w in field(created, 'workspaces') if field(w, 'name') == 'Independent Testing')
        specs = [[field(t, 'kind'), field(t, 'requested_geometry')] for t in tiles]
        mutate(['Apply_preset', ['workspace', field(other, 'id')], ['preset', 'testing'], ['tiles', specs]])
        terminal.palette('Switch to Independent Testing')
        terminal.capture('independent-workspace', ['Select an attempt for outcome'])
        terminal.palette('Switch to Testing')
        terminal.palette('Zoom focused tile')  # restores Logs focus
        terminal.capture('workspace-selection-retained', [aid, field(done, 'job')[:25]])
        terminal.palette('Unzoom workspace')
        # Add a hidden legacy tile, then apply the updated template additively.
        added = mutate(['Create_tile', ['workspace', wid], ['kind', 'simulation'],
                        ['geometry', [('x', 0), ('y', 0), ('width', 80), ('height', 12)]]])
        extra = field(added, 'tiles')[-1]
        mutate(['Set_tile_hidden', ['tile', field(extra, 'id')], ['hidden', 'true']])
        mutate(['Set_tile_binding', ['tile', field(extra, 'id')], ['binding', ['Pin_run',
            [('backend', 'saved-fixture'), ('id', 'preserved-pin'), ('build', []), ('label', [])]]]])
        moved = next(t for t in tiles if field(t, 'kind') == 'simulation-artifacts')
        mutate(['Move_tile', ['tile', field(moved, 'id')], ['workspace', field(other, 'id')]])
        before = workspace()
        terminal.palette('Apply default layout (add missing tiles)')
        wait_for(lambda: len(field(workspace(), 'tiles')) == len(field(before, 'tiles')) + 1,
                 'Apply adds missing cooperative pane')
        after = workspace()
        previous = {field(t, 'id'): t for t in field(before, 'tiles')}
        check(all(previous.get(field(t, 'id'), t) == t for t in field(after, 'tiles')),
              'additive upgrade preserves saved hidden legacy extras, pins and geometry')
        # Revisit Catalog: failed discovery retains rows but disables launch.
        terminal.palette('Switch to Independent Testing')
        for _ in range(4):
            terminal.key(b'\t')
        terminal.palette('Zoom focused tile')
        mode('discovery-malformed')
        terminal.key(b'd')
        wait_for(lambda: bool(field(session.api(), 'discovery_error')), 'failed discovery completes')
        terminal.capture('stale-catalog', ['Launch disabled:'])
        count = len([r for r in records() if r['operation'] == 'run'])
        terminal.key(b'\r')
        terminal.drain(.6)
        check(len([r for r in records() if r['operation'] == 'run']) == count,
              'failed authoritative discovery blocks Enter launch')
        check(len([r for r in records() if r['operation'] == 'discover']) == 2,
              'cooperative panes poll observation only; discovery remains explicit')
        before_restart = records()
        terminal.close(); terminal = None
        session.stop(); session.start()
        terminal = Terminal(session)
        terminal.capture('restart-startup', ['Overview'])
        terminal.palette('Switch to Testing')
        # The moved artifact pane was re-added at the end; Logs is now eighth.
        for _ in range(8):
            terminal.key(b'\t')
        terminal.palette('Simulation: Reopen ' + aid + ' fixture')
        terminal.palette('Zoom focused tile')
        terminal.capture('historical-exact-logs-unavailable', ['Job logs unavailable in this daemon'])
        check(records() == before_restart, 'historical reopen reports absent exact-job logs without replay or discovery')
        result['status'] = 'passed'
    except BaseException:
        result['traceback'] = traceback.format_exc()
        if terminal:
            terminal.save('failure', terminal.drain(.1))
        raise
    finally:
        if terminal:
            terminal.close()
        session.stop()
        (evidence / 'verified.json').write_text(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--daemon', type=Path, required=True)
    parser.add_argument('--client', type=Path, required=True)
    args = parser.parse_args()
    args.daemon = args.daemon.resolve(strict=True)
    args.client = args.client.resolve(strict=True)
    args.outer_timeout = 30
    os.umask(0o077)
    args.evidence = Path(tempfile.mkdtemp(prefix='testing-workspace-', dir='/tmp/opencode'))
    print('Evidence: ' + str(args.evidence), flush=True)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('acceptance budget exhausted')))
    signal.alarm(300)
    try:
        run(args)
    finally:
        signal.alarm(0)
    print('PASS cooperative Testing HTTP + PTY', flush=True)


if __name__ == '__main__':
    main()
