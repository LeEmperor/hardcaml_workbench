#!/usr/bin/env python3
"""Two real native PTY clients, one private daemon, synthetic FS2 only; no builds.

Run: python3 scripts/test-client-reconnect.py [--evidence NEW-DIR]
Reuses the FS3 PTY/screen oracle and tool guards. Evidence is retained under
/tmp/opencode; all owned processes are stopped even on assertion/timeout.
Timing attachment is deliberately outside this simulation-only fixture.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


harness = load('reconnect_fs3', HERE / 'test-fs3-adoption.py')
wire = load('reconnect_wire', HERE / 'fixtures/fs2_wire.py')
field, require = harness.field, harness.require


def provider():
    parser = argparse.ArgumentParser()
    parser.add_argument('--calls', type=Path, required=True)
    parser.add_argument('operation', choices=['discover', 'run'])
    parser.add_argument('--protocol-version', required=True)
    parser.add_argument('--request', type=Path)
    parser.add_argument('--events', type=Path)
    parser.add_argument('--artifact-dir', type=Path)
    args = parser.parse_args(sys.argv[2:])
    with args.calls.open('a') as out:
        out.write(json.dumps(dict(operation=args.operation, pid=os.getpid())) + '\n')
    require(args.protocol_version == '1', 'FS2 protocol version')
    if args.operation == 'discover':
        print(wire.sexp(wire.catalog(cases=['reconnect-case'])))
        return
    request = dict(wire.parse(args.request.read_text()))
    selection = dict(request['selection'])
    require(selection['asic_inputs'] == [], 'Synthetic fixture forbids ASIC inputs')
    writer = wire.EventWriter(args.events, request['attempt_id'])
    writer.emit('Started')
    writer.emit(['Case_started', 'reconnect-case'])
    # Two distinct artifacts ensure a visible selection is more than an empty pane.
    for label in ('reconnect-primary', 'reconnect-secondary'):
        path = args.artifact_dir / (label + '.txt')
        path.write_text('SYNTHETIC reconnect evidence: ' + label + '\n')
        writer.artifact(label, 'reconnect-case', 'report', 'text/plain', path.name)
    writer.finish_case('reconnect-case')
    writer.emit(['Finished', 'Passed'])


class Terminal(harness.Terminal):
    def wait(self, label, expected=(), absent=(), ready=False):
        try:
            return super().wait(label, expected, absent, ready)
        finally:
            (self.test.evidence / (self.label + '-' + label + '.ansi')).write_bytes(self.data)
            (self.test.evidence / (self.label + '-' + label + '.txt')).write_text(
                harness.fs0.terminal_screen(bytes(self.data), width=120, height=40))

    def focus_catalog(self):
        for _ in range(11):
            for key in (b' ', b'c', b'c'):
                self.key(key)
            self.key(b'Simulation: Discover suites explicitly')
            text = self.drain()
            self.key(b'\x1b')
            if 'No matching commands' not in text and 'Simulation: Discover' in text:
                return
            self.key(b'\t')
        raise AssertionError('Could not focus simulation catalog')


def exercise(test):
    (test.root / 'dune-project').write_text('(lang dune 3.22)\n(name reconnect_fixture)\n')
    (test.root / 'hardcaml-workbench.sexp').write_text(
        '(lang hardcaml-workbench 1)\n(project (name "FS3 acceptance"))\n'
        '(dune (build_alias @never-build) (test_alias @never-test))\n')
    calls = test.evidence / 'provider-calls.jsonl'
    (test.root / 'hardcaml-workbench-simulation.sexp').write_text(wire.sexp([
        ('schema_version', 1), ('provider_executable', sys.executable),
        ('provider_args', [str(Path(__file__).resolve()), '_provider', '--calls', str(calls)]),
        ('discovery_timeout_seconds', 10), ('run_timeout_seconds', 10)]))
    test.start()
    daemon_pid, instance = test.process.pid, test.instance

    def api(operation='Get'):
        response = test.raw('simulation', [['instance_id', test.instance],
            ['project', test.project], ['operation', operation]])
        require(response[0] == 'Ok', str(response))
        return response[1]

    def jobs():
        response = test.raw('snapshot', [['instance_id', test.instance]])
        require(response[0] == 'Ok', str(response))
        return field(response[1], 'jobs')

    def counts():
        entries = [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
        return {op: sum(e['operation'] == op for e in entries) for op in ('discover', 'run')}

    terminal = None
    try:
        terminal = Terminal(test, 'first-client')
        terminal.wait('startup', ['Space c c commands'], ['Loading workspace...'], ready=True)
        test.check(counts() == dict(discover=0, run=0) and jobs() == [],
                   'First frontend startup performs no provider discovery or jobs')
        terminal.palette('Create Testing workspace')
        terminal.wait('testing', ['simulation-catalog', 'simulation-artifacts'])
        terminal.focus_catalog()
        terminal.palette('Simulation: Discover suites explicitly')
        terminal.wait('catalog', ['reconnect-case', 'fixture'])
        terminal.palette('Simulation: Launch selected catalog subset')
        for step in ('CASES', 'SEED', 'CONFIRM'):
            terminal.wait('launch-' + step.lower(), ['SIMULATION LAUNCH FORM', step])
            terminal.key(b'\r')
        deadline = time.monotonic() + 20
        while True:
            snapshot = api()
            attempts = field(snapshot, 'attempts')
            if attempts and field(attempts[0], 'lifecycle') == 'Finished':
                break
            require(time.monotonic() < deadline, 'Synthetic TUI launch did not complete: ' + str(snapshot))
            terminal.drain(.1)
        require(len(attempts) == 1, 'Exactly one synthetic attempt')
        aid = field(attempts[0], 'id')
        detail = field(api(['Observe', aid]), 'detail')[0]
        artifact = field(detail, 'artifacts')[0]
        label = field(artifact, 'label')

        def painted_identity(text, phase):
            rows = text.splitlines()
            left = rows[1].index('╭ simulation-detail')
            content = ''.join(row[left + 1:-1].strip() for row in rows[2:18])
            test.check(all(value in content for value in (
                'Selected artifact: ' + field(artifact, 'id'),
                'Artifact attempt: ' + aid,
                'SHA256: ' + field(artifact, 'sha256')[0],
                'Artifact bytes: ' + field(artifact, 'size')[0])),
                phase + ': actual painted frontend exposes exact artifact ID, attempt ID, SHA256 and size')

        # Explicit attempt selection is a frontend action; artifact is its default.
        terminal.key(b'\t')
        terminal.palette('Simulation: Reopen ' + aid + ' fixture')
        selected = ['> reconnect-case: Passed', '> ' + label, 'Finished/Passed']
        painted_identity(terminal.wait('selected', selected), 'First client')
        test.check(counts() == dict(discover=1, run=1), 'First client discovers once and launches one cheap synthetic run')
        deadline = time.monotonic() + 10
        while True:
            preferences = list((test.evidence / 'client-state').rglob('navigation-*.sexp'))
            if preferences and aid in preferences[0].read_text() and field(artifact, 'id') in preferences[0].read_text():
                break
            require(time.monotonic() < deadline, 'Selected navigation was not persisted')
            terminal.drain(.1)
        (test.evidence / 'navigation-before.sexp').write_bytes(preferences[0].read_bytes())
        before_jobs, before_calls, registry = jobs(), calls.read_bytes(), test.workspace()
        (test.evidence / 'before-reconnect.json').write_text(json.dumps(dict(
            daemon_pid=daemon_pid, instance=instance, attempt=aid, artifact=artifact,
            jobs=before_jobs, counts=counts()), indent=2))
        terminal.close()
        terminal = None
        terminal = Terminal(test, 'second-client')
        # No input at all to the second client: only drain the actual PTY output.
        painted_identity(terminal.wait('restored-no-input',
            ['[3 Testing]', 'Ready for explicit launch', 'simulation-catalog', 'simulation-artifacts', *selected],
            ['Loading workspace...', 'Select an attempt'], ready=True), 'Second client without input')
        terminal.drain(2.5)
        terminal.wait('restored-after-poll', selected)
        hello = test.raw('hello')
        test.check(test.process.pid == daemon_pid and test.process.poll() is None and
                   field(hello, 'instance_id') == instance, 'Both frontend processes use the same live daemon PID and instance')
        test.check(jobs() == before_jobs and calls.read_bytes() == before_calls and
                   counts() == dict(discover=1, run=1), 'Reconnect adds zero backend jobs, provider discovers, or provider runs')
        test.check(test.workspace() == registry, 'Reconnect preserves exact workspace registry and context')
        restored = field(api(['Observe', aid]), 'detail')[0]
        test.check(restored == detail, 'Exact retained attempt and artifact evidence remain unchanged')
        test.check(not (test.evidence / 'forbidden-tools.jsonl').exists(), 'No forbidden toolchain or EDA executable invoked')
        test.result.update(status='passed', daemon_pid=daemon_pid, instance=instance,
            attempt=aid, artifact=artifact, counts=counts(),
            limitation='Timing retained-index attachment not exercised by this simulation-only fixture')
    finally:
        if terminal:
            terminal.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--daemon', type=Path, default=REPO / '_build/default/daemon/main.exe')
    parser.add_argument('--terminal', '--client', type=Path, default=REPO / '_build/default/terminal/main.exe')
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    base = Path('/tmp/opencode')
    if args.evidence:
        args.evidence = args.evidence.resolve()
        require(args.evidence.is_relative_to(base) and args.evidence != base, 'Evidence must be under /tmp/opencode')
        args.evidence.mkdir()
    else:
        args.evidence = Path(tempfile.mkdtemp(prefix='client-reconnect-', dir=base))
    for name in ('daemon', 'terminal'):
        path = getattr(args, name).resolve(strict=True)
        require(os.access(path, os.X_OK), 'Missing executable: ' + str(path))
        setattr(args, name, path)
    test = harness.Acceptance(args)
    (args.evidence / 'binary-sha256.json').write_text(json.dumps({name:
        hashlib.sha256(getattr(args, name).read_bytes()).hexdigest() for name in ('daemon', 'terminal')}, indent=2))
    print('Evidence:', args.evidence, flush=True)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Reconnect acceptance budget exhausted')))
    signal.alarm(150)
    try:
        exercise(test)
    except BaseException:
        test.result['failure'] = traceback.format_exc()
        traceback.print_exc()
    finally:
        signal.alarm(0)
        test.close()
        test.result['owned_daemon_stopped'] = test.process is None or test.process.poll() is not None
        (args.evidence / 'result.json').write_text(json.dumps(test.result, indent=2) + '\n')
    print(test.result['status'].upper() + ': ' + str(args.evidence / 'result.json'))
    return 0 if test.result['status'] == 'passed' else 1


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '_provider':
        provider()
    else:
        sys.exit(main())
