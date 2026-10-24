#!/usr/bin/env python3
"""Real sibling FIFO acceptance. Prebuilt binaries only; private daemon/PTY state.

--standalone needs only --simulator. Native modes use the actual example root's
already installed FS2 config. No builds, config edits, ASIC operations or live
daemon access. --skip-pty permits independent HTTP verification during UI work.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


native = load('fifo_native_support', HERE / 'test-fs2-native.py')
support = load('fifo_terminal_support', HERE / 'test-synthetic-testing.py')
field, require = native.field, native.require
sexp, parse = support.sexp, support.parse


def selection(cases=('directed', 'seeded'), seed='18446744073709551615', checker='normal', cycles='64'):
    return [('suite', 'controlled-fifo'), ('cases', list(cases)), ('seed', seed),
            ('parameters', [('cycles', cycles), ('checker', checker)]), ('asic_inputs', [])]


def same_selection(actual, expected):
    actual, expected = dict(actual), dict(expected)
    actual['parameters'] = dict(actual['parameters'])
    expected['parameters'] = dict(expected['parameters'])
    return actual == expected


def standalone(args, evidence):
    isolated = evidence / 'standalone'
    isolated.mkdir()
    for name in ('provider.py', 'wire.py'):
        shutil.copy2(args.root / 'simulation' / name, isolated / name)
    shutil.copy2(args.simulator, isolated / 'fifo_sim.exe')
    command = [sys.executable, '-S', str(isolated / 'provider.py')]
    env = dict(os.environ, PYTHONPATH='', PYTHONNOUSERSITE='1')
    result = subprocess.run(command + ['discover', '--protocol-version', '1'], cwd=isolated,
                            env=env, capture_output=True, check=True, timeout=10)
    (isolated / 'catalog.sexp').write_bytes(result.stdout)
    require(field(parse(result.stdout.decode()), 'protocol_version') == '1', 'standalone FS2 catalog')
    runs = {}

    def run(label, selected, valid=True):
        directory = isolated / label
        directory.mkdir()
        artifacts = directory / 'artifacts'
        artifacts.mkdir()
        request = [('protocol_version', 1), ('attempt_id', 'standalone'), ('selection', selected)]
        path = directory / 'request.sexp'
        path.write_text(sexp(request))
        events = directory / 'events.sexp'
        result = subprocess.run(command + ['run', '--protocol-version', '1', '--request', str(path),
            '--events', str(events), '--artifact-dir', str(artifacts)], cwd=isolated, env=env,
            capture_output=True, timeout=30)
        (directory / 'stdout').write_bytes(result.stdout)
        (directory / 'stderr').write_bytes(result.stderr)
        if not valid:
            require(result.returncode != 0 and not events.exists() and not list(artifacts.iterdir()),
                    'invalid request rejected before evidence: ' + label)
            return
        require(result.returncode == 0, result.stderr.decode())
        stream = [parse(line) for line in events.read_text().splitlines()]
        require([int(field(e, 'sequence')) for e in stream] == list(range(len(stream))), 'contiguous events')
        expected = 'Failed' if dict(dict(selected)['parameters'])['checker'] == 'mismatch' else 'Passed'
        require(field(stream[-1], 'payload') == ['Finished', expected], label + ' outcome')
        finished = [field(e, 'payload')[1] for e in stream
                    if isinstance(field(e, 'payload'), list) and field(e, 'payload')[0] == 'Case_finished']
        require([field(c, 'case_id') for c in finished] == dict(selected)['cases'] and
                all(field(c, 'status') == expected for c in finished), 'exact selected native cases')
        require(any(isinstance(field(e, 'payload'), list) and field(e, 'payload')[0] == 'Progress' for e in stream), 'native progress')
        data = {f.name: f.read_bytes() for f in artifacts.iterdir()}
        for case in dict(selected)['cases']:
            require(b'$enddefinitions' in data[case + '.vcd'] and b'occupancy' in data[case + '.vcd'], 'real FIFO VCD')
            require(dict(selected)['seed'].encode() in data[case + '.sexp'], 'exact report seed')
        runs[label] = data

    run('pass', selection())
    run('repeat', selection())
    require(runs['pass'] == runs['repeat'], 'byte-identical real VCD and native report replay')
    run('failure', selection(checker='mismatch'))
    run('failure-repeat', selection(checker='mismatch'))
    require(runs['failure'] == runs['failure-repeat'], 'deterministic mismatch reports and traces')
    for case in ('directed', 'seeded'):
        require(runs['failure'][case + '.vcd'] == runs['pass'][case + '.vcd'], 'checker-only failure preserves DUT VCD')
        require(b'injected true' in runs['failure'][case + '.sexp'], 'native injected diagnostic')
    run('low-bits', selection(cases=('seeded',), seed='65535'))
    require(runs['low-bits']['seeded.vcd'] != runs['pass']['seeded.vcd'], 'high seed bits affect actual stimuli')
    run('zero', selection(cases=('seeded',), seed='0', cycles='4096'))
    run('long', selection(cases=('seeded',), seed='42', cycles='20000'))
    run('directed-only', selection(cases=('directed',), seed='42'))
    for index, seed in enumerate(('-1', '01', '+1', '18446744073709551616', '1.0')):
        run('invalid-seed-' + str(index), selection(seed=seed), valid=False)
    for label, update in [('case', {'cases': ['unknown']}), ('duplicate-case', {'cases': ['seeded', 'seeded']}),
                          ('suite', {'suite': 'unknown'}), ('asic', {'asic_inputs': ['x']}),
                          ('parameter', {'parameters': [('cycles', '65'), ('checker', 'normal')]}),
                          ('duplicate-parameter', {'parameters': [('cycles', '64'), ('cycles', '64'), ('checker', 'normal')]}),
                          ('missing-parameter', {'parameters': [('cycles', '64')]})]:
        run('invalid-' + label, list(dict(selection(), **update).items()), valid=False)
    wire = load('fifo_strict_wire', isolated / 'wire.py')
    for bad in ('"unterminated', '() garbage', '(x "\\q")', '(()', ')'):
        try:
            wire.parse(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('codec accepted ' + bad)
    install_root = isolated / 'install-root'
    (install_root / 'scripts').mkdir(parents=True)
    shutil.copytree(args.root / 'simulation', install_root / 'simulation')
    helper = install_root / 'scripts/install-fifo-simulation.py'
    shutil.copy2(args.root / 'scripts' / helper.name, helper)
    config = install_root / 'hardcaml-workbench-simulation.sexp'
    helper_command = [sys.executable, str(helper), '--simulator', str(args.simulator)]
    config.write_bytes(b'UNRELATED CONFIG\n')
    refusal = subprocess.run(helper_command, capture_output=True, timeout=10)
    require(refusal.returncode != 0 and config.read_bytes() == b'UNRELATED CONFIG\n' and
            not (install_root / '.dev').exists(), 'installer refuses unrelated config before changes')
    config.unlink()
    subprocess.run(helper_command, capture_output=True, check=True, timeout=10)
    require((install_root / '.dev/fifo-simulation-install.json').exists(), 'persistent install manifest')
    config.write_bytes(config.read_bytes() + b'\n')
    edited = config.read_bytes()
    refusal = subprocess.run(helper_command, capture_output=True, timeout=10)
    require(refusal.returncode != 0 and config.read_bytes() == edited, 'installer refuses edited owned config')
    (evidence / 'standalone.json').write_text(json.dumps(dict(status='passed',
        sha256={label: {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
                for label, files in runs.items()}), indent=2))
    return runs


class TestingTerminal(native.Terminal):
    width, height = 120, 40

    def drain(self, seconds=.3):
        super().drain(seconds)
        return native.fs0.terminal_screen(bytes(self.data), self.width, self.height)

    def resize(self, width, height):
        self.width, self.height = width, height
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
        # This harness starts a new session without assigning a controlling PTY;
        # TIOCSWINSZ alone need not notify its child. Fence the actual repaint,
        # rather than accepting unchanged text reconstructed in a larger grid.
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
            # These border rows use only single-cell box-drawing/plain glyphs.
            valid = (len(top) == self.width and top.endswith('╮') and
                     len(bottom) == self.width and bottom.endswith('╯') and
                     footer.startswith('Space c c commands'))
            if valid:
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


def cooperative(session, evidence, expected, passed):
    terminal = TestingTerminal(session)
    # Exact provenance assertions below deliberately request full display identities.
    terminal.palette('Strings (global): Show full identifiers')
    checks = []
    result = dict(status='failed', checks=checks)
    focus_index = 0

    def check(ok, label):
        checks.append(dict(passed=bool(ok), expectation=label))
        require(ok, label)

    def attempts():
        return field(session.api(), 'attempts')

    def focus(index):
        nonlocal focus_index
        for _ in range((index - focus_index) % 10):
            terminal.key(b'\t')
        focus_index = index

    def new_attempt(before):
        found = support.wait_for(lambda: [a for a in attempts() if field(a, 'id') not in before],
                                 'catalog confirmation submits a real FIFO attempt', seconds=30)
        check(len(found) == 1, 'exactly one new attempt from explicit confirmation')
        return session.done(field(found[0], 'id'))

    def launch(checker):
        before = {field(a, 'id') for a in attempts()}
        terminal.key(b'\r')
        terminal.capture('catalog-' + checker + '-cases-form', ['CASES', 'seeded'])
        terminal.key(b'\r')
        terminal.capture('catalog-' + checker + '-seed-form', ['SEED'])
        terminal.key(b'\x15'); terminal.key(b'18446744073709551615'); terminal.key(b'\r')
        terminal.capture('catalog-' + checker + '-checker-form', ['PARAMETER checker'])
        terminal.key(b'\x15'); terminal.key(checker.encode()); terminal.key(b'\r')
        terminal.capture('catalog-' + checker + '-cycles-form', ['PARAMETER cycles'])
        terminal.key(b'\x15'); terminal.key(b'64'); terminal.key(b'\r')
        terminal.capture('catalog-' + checker + '-confirm', ['CONFIRM', '18446744073709551615', 'seeded', checker, '64'])
        check({field(a, 'id') for a in attempts()} == before, 'form edits do not launch before confirmation')
        terminal.key(b'\x15'); terminal.key(b'launch'); terminal.key(b'\r')
        detail = new_attempt(before)
        captured = field(detail, 'captured')
        check(same_selection(field(captured, 'selection'), parse(sexp(selection(cases=('seeded',), checker=checker)))),
              'catalog launch retains exact subset, max uint64, cycles64, checker and empty ASIC inputs')
        check(field(detail, 'outcome') == ('Failed' if checker == 'mismatch' else 'Passed') and
              field(detail, 'exit_code') == ['0'], 'real catalog simulation semantic outcome separate from process exit')
        current = session.api()
        check(field(captured, 'discovery_digest') == field(current, 'discovery_digest')[0] and
              field(detail, 'project_root') == str(session.root) and not field(detail, 'parent'),
              'catalog launch captures exact discovery digest, actual project root and no fabricated parent')
        config = native.record(native.parse((session.root / 'hardcaml-workbench-simulation.sexp').read_text()))
        check(field(captured, 'provider_executable') == config['provider_executable'] and
              field(captured, 'provider_args') == config['provider_args'] and
              field(captured, 'environment') == 'Inherit_daemon', 'captured persistent genuine provider and environment')
        return detail

    try:
        terminal.capture('cooperative-startup', ['Overview'])
        terminal.palette('Create Testing workspace')
        terminal.capture('real-testing-empty-120x40', ['simulation-catalog', 'simulation-detail', 'Project tests'])
        terminal.wait_viewport('empty-120x40')
        terminal.resize(180, 55)
        terminal.capture('real-testing-empty-180x55', ['simulation-catalog', 'simulation-detail', 'Generic project tests'])
        terminal.resize(120, 40)
        snapshot = session.api(domain='workspace')
        workspace = next(w for w in field(snapshot, 'workspaces') if field(w, 'preset') == ['testing'])
        tiles = [t for t in field(snapshot, 'tiles') if field(t, 'workspace') == field(workspace, 'id')]
        check(all(any(field(t, 'kind') == kind for t in tiles) for kind in
                  ('simulation-catalog', 'simulation-attempts', 'simulation-cases', 'simulation-detail',
                   'simulation-artifacts', 'simulation-logs')), 'Create Testing installs all six cooperative panes')
        focus(4)
        terminal.palette('Zoom focused tile')
        old_job = field(session.api(), 'discovery_job')
        terminal.key(b'd')
        support.wait_for(lambda: field(session.api(), 'discovery_job') != old_job, 'explicit catalog discovery', seconds=30)
        terminal.capture('real-catalog-discovered', ['directed', 'seeded', 'Ready for explicit launch'])
        terminal.key(b'x')
        terminal.key(b'/'); terminal.key(b'seeded'); terminal.key(b'\r')
        terminal.capture('real-catalog-subset', ['Selected cases: seeded'], absent=['[x] directed'])
        failed = launch('mismatch')
        aid = field(failed, 'id')
        terminal.palette('Unzoom workspace')
        focus(5)
        terminal.palette('Simulation: Reopen ' + aid + ' controlled-fifo')
        focus(6)
        terminal.palette('Zoom focused tile')
        terminal.key(b'j')
        terminal.capture('real-cooperative-cases', ['> seeded: Failed'], absent=['directed:'])
        terminal.palette('Unzoom workspace')
        focus(7)
        terminal.palette('Zoom focused tile')
        terminal.capture('real-cooperative-detail', ['seeded: Failed', 'CHECK_FAILED', aid,
                         '18446744073709551615', 'Captured cases: seeded', 'checker mismatch', 'cycles 64'])
        terminal.palette('Unzoom workspace')
        terminal.capture('real-testing-failure-120x40', ['simulation-cases', 'simulation-detail', 'simulation-artifacts', 'simulation-logs'])
        terminal.wait_viewport('failure-120x40')
        terminal.resize(180, 55)
        terminal.capture('real-testing-failure-180x55', ['seeded: Failed', 'simulation-detail', 'simulation-artifacts', 'simulation-logs'])
        terminal.resize(120, 40)
        focus(8)
        terminal.palette('Zoom focused tile')
        terminal.key(b'j'); terminal.key(b'j')
        terminal.capture('real-cooperative-artifacts-report', ['seeded.sexp', 'Available'])
        for name, key in [('seeded.sexp', None), ('seeded.vcd', b'k')]:
            if key:
                terminal.key(key)
            before_exports = set((evidence / 'tmp').glob('*simulation*/artifact*'))
            terminal.key(b'e')
            files = support.wait_for(lambda: set((evidence / 'tmp').glob('*simulation*/artifact*')) - before_exports,
                                     'selected real artifact export', seconds=30)
            check(len(files) == 1, 'one exact selected artifact exported')
            exported = files.pop()
            artifact = next(a for a in field(failed, 'artifacts') if field(a, 'label') == name)
            raw = exported.read_bytes()
            check(raw == expected['failure'][name] and hashlib.sha256(raw).hexdigest() == field(artifact, 'sha256')[0],
                  'selected cooperative export matches native ' + name + ' bytes and captured digest')
        terminal.palette('Unzoom workspace')
        focus(9)
        terminal.palette('Zoom focused tile')
        terminal.capture('real-cooperative-logs', [aid, field(failed, 'job')[:25], 'FIFO seeded', 'CHECK_FAILED'])
        before = {field(a, 'id') for a in attempts()}
        terminal.palette('Simulation: Rerun case seeded (original inputs; current project)')
        child = new_attempt(before)
        check(field(field(child, 'parent')[0], 'attempt_id') == aid and
              field(field(child, 'parent')[0], 'job') == field(failed, 'job') and
              field(child, 'job') != field(failed, 'job') and field(child, 'outcome') == 'Failed' and
              same_selection(field(field(child, 'captured'), 'selection'), field(field(failed, 'captured'), 'selection')),
              'cooperative targeted rerun preserves original inputs and exact parent with fresh job/attempt')
        terminal.palette('Unzoom workspace')
        focus(6)
        terminal.palette('Simulation: Reopen ' + field(passed, 'id') + ' controlled-fifo')
        terminal.palette('Zoom focused tile')
        for case in ('seeded', 'directed'):
            terminal.palette('Simulation: Select case ' + case)
            for poll in range(3):
                terminal.drain(.8)
                terminal.capture('real-case-stable-' + case + '-' + str(poll), ['> ' + case + ': Passed'])
            terminal.palette('Unzoom workspace')
            focus(7)
            terminal.palette('Zoom focused tile')
            terminal.capture('real-detail-selected-' + case, [case + ': Passed', field(passed, 'id')],
                             absent=[('directed' if case == 'seeded' else 'seeded') + ': Passed'])
            terminal.palette('Unzoom workspace')
            focus(6)
            terminal.palette('Zoom focused tile')
        check(True, 'seeded then directed selection survives repeated polling and is coherent in shared Detail')
        terminal.palette('Unzoom workspace')
        focus(4)
        terminal.palette('Zoom focused tile')
        terminal.capture('real-catalog-retained-subset', ['Selected cases: seeded'])
        passing = launch('normal')
        terminal.palette('Unzoom workspace')
        focus(7)
        terminal.palette('Zoom focused tile')
        terminal.palette('Simulation: Select case seeded')
        terminal.capture('real-catalog-pass-detail', ['seeded: Passed', field(passing, 'id'), '18446744073709551615'])
        check(True, 'passing seeded-only launch also uses catalog form and cooperative detail')
        result.update(status='passed', failed=failed, rerun=child, passed=passing)
    finally:
        terminal.save('cooperative-final-state', terminal.drain())
        terminal.close()
        (evidence / 'cooperative.json').write_text(json.dumps(result, indent=2))


def http_pty(args, evidence, expected):
    (evidence / 'state').mkdir()
    for name in ('home', 'config', 'tmp'):
        (evidence / name).mkdir()
    session = native.Session(args, evidence, args.root)
    session.env.update(HOME=str(evidence / 'home'), XDG_CONFIG_HOME=str(evidence / 'config'),
                       TMPDIR=str(evidence / 'tmp'), PYTHONDONTWRITEBYTECODE='1')
    terminal = None
    try:
        session.start()
        initial = session.api()
        require(field(initial, 'attempts') == [], 'isolated empty attempt history')
        discovered = session.discover()
        digest = field(discovered, 'discovery_digest')[0]
        (evidence / 'catalog.sexp').write_text(sexp(discovered))
        details = []
        for label, selected in [('pass', selection()),
                                ('failure', selection(cases=('seeded',), checker='mismatch'))]:
            launch = '(Launch (submission_key %s) (discovery_digest %s) (selection %s))' % (sexp('fifo-' + label), sexp(digest), sexp(selected))
            submitted = session.api(operation=parse(launch))
            aid = field(field(submitted, 'detail')[0], 'id')
            detail = session.done(aid)
            require(field(detail, 'outcome') == ('Failed' if label == 'failure' else 'Passed') and field(detail, 'exit_code') == ['0'], 'HTTP semantic outcome')
            require(same_selection(field(field(detail, 'captured'), 'selection'), parse(sexp(selected))), 'HTTP exact captured selection')
            for artifact in field(detail, 'artifacts'):
                raw = bytearray()
                while True:
                    page_result = session.api(operation=parse(
                        '(Read_artifact_bytes (attempt_id %s) (artifact_id %s) (sha256 %s) (offset %d) (limit 65536))' %
                        (sexp(aid), sexp(field(artifact, 'id')), sexp(field(artifact, 'sha256')[0]), len(raw))))
                    page = field(page_result, 'byte_page')[0]
                    block = bytes.fromhex(field(page, 'bytes_hex'))
                    require(int(field(page, 'offset')) == len(raw), 'byte page offset')
                    raw.extend(block)
                    if field(page, 'eof') == 'true':
                        break
                    require(block, 'byte page advances')
                require(hashlib.sha256(raw).hexdigest() == field(artifact, 'sha256')[0], 'HTTP artifact digest')
                name = field(artifact, 'label')
                require(raw == expected[label][name], 'HTTP byte-identical real native evidence ' + name)
            details.append(detail)
        if not args.skip_pty:
            cooperative(session, evidence, expected, details[0])
            # Keep the independent legacy simulation pane as a regression.
            client = support.Client(session.url, args.root, switch=None)
            layout = client.rpc(domain='workspace')
            window = field(field(layout, 'windows')[0], 'id')
            layout = client.mutate(layout, '(Create_workspace (window %s) (name "FIFO acceptance") (context %s))' % (sexp(window), sexp(field(layout, 'main_context'))))
            workspace = field(field(layout, 'workspaces')[-1], 'id')
            client.mutate(layout, '(Create_tile (workspace %s) (kind simulation) (geometry ((x 0)(y 0)(width 110)(height 30))))' % sexp(workspace))
            terminal = native.Terminal(session)
            terminal.capture('ready', ['Overview', 'FIFO acceptance', 'connected'])
            terminal.palette('Switch to FIFO acceptance')
            support.Terminal.focus_simulation(terminal)
            terminal.palette('Simulation: Reopen ' + field(details[1], 'id') + ' controlled-fifo')
            terminal.palette('Zoom focused tile')
            terminal.capture('real-failure', ['Failed', 'controlled-fifo'])
            terminal.palette('Simulation: Select case seeded')
            terminal.capture('real-case', ['> seeded: Failed'])
            terminal.palette('Simulation: Toggle stream-labelled job logs')
            terminal.capture('real-logs', ['JOB LOG'])
            terminal.palette('Simulation: Toggle stream-labelled job logs')
            before = {field(a, 'id') for a in field(session.api(), 'attempts')}
            terminal.palette('Simulation: Rerun case seeded (original inputs; current project)')
            submitted = support.wait_for(lambda: [a for a in field(session.api(), 'attempts') if field(a, 'id') not in before], 'real FIFO rerun')
            require(len(submitted) == 1, 'one targeted rerun')
            child = session.done(field(submitted[0], 'id'))
            captured = dict(field(field(child, 'captured'), 'selection'))
            require(same_selection(captured, parse(sexp(selection(cases=('seeded',), checker='mismatch')))), 'PTY exact targeted rerun')
            require(field(child, 'outcome') == 'Failed' and field(child, 'job') != field(details[1], 'job'), 'new genuine failed checker rerun')
            terminal.capture('real-rerun', ['Failed', 'Rerun of'])
        (evidence / 'native.json').write_text(json.dumps(dict(status='passed', pty=not args.skip_pty, details=details), indent=2))
    finally:
        if terminal:
            try:
                terminal.save('final-state', terminal.drain())
            finally:
                terminal.close()
        session.stop()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=HERE.parent.parent / 'hardcaml_asic_example')
    p.add_argument('--simulator', type=Path, default=Path('/tmp/opencode/testing-cluster-fifo/default/simulation/fifo_sim.exe'))
    p.add_argument('--daemon', type=Path, default=HERE.parent / '_build/default/daemon/main.exe')
    p.add_argument('--client', type=Path, default=HERE.parent / '_build/default/terminal/main.exe')
    p.add_argument('--standalone', action='store_true')
    p.add_argument('--skip-pty', action='store_true')
    p.add_argument('--evidence', type=Path)
    args = p.parse_args()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('600s FIFO acceptance budget exhausted')))
    signal.alarm(600)
    args.root = args.root.resolve(strict=True)
    args.simulator = args.simulator.resolve(strict=True)
    evidence = args.evidence
    if evidence:
        evidence.mkdir()
    else:
        evidence = Path(tempfile.mkdtemp(prefix='fifo-testing-', dir='/tmp/opencode'))
    print('Evidence: ' + str(evidence), flush=True)
    expected = standalone(args, evidence)
    if not args.standalone:
        args.daemon = args.daemon.resolve(strict=True)
        args.client = args.client.resolve(strict=True)
        http_pty(args, evidence, expected)
    print('PASS real FIFO acceptance: ' + str(evidence))


if __name__ == '__main__':
    main()
