#!/usr/bin/env python3
"""WB-066 independent Python/native equivalence; prebuilt executables only.

No build/install, real project config changes, physical tools, or live daemon.
Pass --daemon to also prove both native adapters through private real HTTP state.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'fixtures'))
from fs2_wire import parse, record, sexp


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def field(value, key):
    return record(value)[key]


def canonical(value):
    # Record-field order is not significant; list/event/case order is.
    if isinstance(value, list):
        if value and all(isinstance(p, list) and len(p) == 2 and isinstance(p[0], str)
                         for p in value) and len({p[0] for p in value}) == len(value):
            return sorted((p[0], canonical(p[1])) for p in value)
        return [canonical(v) for v in value]
    return value


def stable_bytes(name, raw):
    # Hardcaml VCD timestamps may differ; preserve every other header/body byte.
    if name.endswith('.vcd') and b'$date' in raw:
        start = raw.index(b'$date')
        end = raw.index(b'$end', start) + len(b'$end')
        return raw[:start] + b'$date <timestamp> $end' + raw[end:]
    return raw


def invoke(command, argv, directory, label):
    result = subprocess.run(command + argv, cwd=directory, capture_output=True, timeout=45,
                            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    (directory / (label + '.stdout')).write_bytes(result.stdout)
    (directory / (label + '.stderr')).write_bytes(result.stderr)
    (directory / (label + '.json')).write_text(json.dumps(dict(
        argv=command + argv, returncode=result.returncode), indent=2))
    return result


def run_provider(command, selected, directory, valid=True):
    directory.mkdir()
    artifacts = directory / 'artifacts'
    artifacts.mkdir()
    request = directory / 'request.sexp'
    request.write_text(sexp([('protocol_version', 1), ('attempt_id', 'conformance'),
                             ('selection', selected)]))
    events = directory / 'events.sexp'
    # The daemon creates an empty event file first. Verify append ownership too.
    events.touch()
    result = invoke(command, ['run', '--protocol-version', '1', '--request', str(request),
                             '--events', str(events), '--artifact-dir', str(artifacts)], directory, 'run')
    if not valid:
        require(result.returncode != 0 and events.read_bytes() == b'' and not list(artifacts.iterdir()),
                'invalid request emitted evidence: ' + str(directory))
        return
    require(result.returncode == 0, str(directory) + ': ' + result.stderr.decode(errors='replace'))
    raw = events.read_bytes()
    require(raw.endswith(b'\n') and b'\r\n' not in raw, 'LF event framing')
    stream = [parse(line.decode()) for line in raw.splitlines()]
    require([field(e, 'sequence') for e in stream] == [str(i) for i in range(len(stream))], 'sequence')
    require(field(stream[0], 'payload') == 'Started', 'Started')
    data = {p.name: p.read_bytes() for p in artifacts.iterdir()}
    declared = [field(field(e, 'payload')[1], 'path') for e in stream
                if isinstance(field(e, 'payload'), list) and field(e, 'payload')[0] == 'Artifact']
    require(set(declared) == set(data), 'exact closed declared artifacts')
    for case in field(selected, 'cases'):
        require(b'$enddefinitions' in data[case + '.vcd'], 'genuine VCD')
    return stream, data


def selection(kind, cases=None, seed='42', failure=False):
    fifo = kind == 'fifo'
    return [('suite', 'controlled-fifo' if fifo else 'counter'),
            ('cases', cases or (['directed', 'seeded'] if fifo else ['wrap', 'reset', 'seeded'])),
            ('seed', seed), ('parameters', [('cycles', '64'), ('checker', 'mismatch' if failure else 'normal')]
             if fifo else [('cycles', '64'), ('step', '3'), ('inject_failure', 'true' if failure else 'false')]),
            ('asic_inputs', [])]


def equivalent(kind, commands, evidence):
    directory = evidence / kind
    directory.mkdir()
    catalogs = []
    for name, command in commands.items():
        result = invoke(command, ['discover', '--protocol-version', '1'], directory, name + '-discover')
        require(result.returncode == 0, result.stderr.decode(errors='replace'))
        catalogs.append(parse(result.stdout.decode()))
    require(canonical(catalogs[0]) == canonical(catalogs[1]), kind + ' parsed discovery equality')
    cases = ['directed', 'seeded'] if kind == 'fifo' else ['wrap', 'reset', 'seeded']
    scenarios = [('all', selection(kind)), ('max-seed', selection(kind, seed=str(2**64 - 1))),
                 ('zero', selection(kind, seed='0')),
                 ('failure', selection(kind, seed=str(2**64 - 1), failure=True))]
    scenarios += [(case, selection(kind, cases=[case])) for case in cases]
    runs = {}
    for label, selected in scenarios:
        outputs = {name: run_provider(command, selected, directory / (label + '-' + name))
                   for name, command in commands.items()}
        py, native = outputs['python'], outputs['native']
        require(canonical(py[0]) == canonical(native[0]), kind + '/' + label + ' parsed event equality')
        expected = 'Failed' if label == 'failure' else 'Passed'
        require(field(native[0][-1], 'payload') == ['Finished', expected], 'semantic result with exit zero')
        require(set(py[1]) == set(native[1]), 'artifact names')
        for name in py[1]:
            require(stable_bytes(name, py[1][name]) == stable_bytes(name, native[1][name]),
                    kind + '/' + label + ' artifact byte equality: ' + name)
        labels = {field(field(e, 'payload')[1], 'label'): field(field(e, 'payload')[1], 'path')
                  for e in native[0] if isinstance(field(e, 'payload'), list)
                  and field(e, 'payload')[0] == 'Artifact'}
        runs[label] = dict(selection=selected, artifacts=native[1], labels=labels)
    invalid = []
    for seed in ('-1', '01', '+1', '18446744073709551616', '1.0', ''):
        invalid.append(('seed-' + str(len(invalid)), dict(selection(kind), seed=seed)))
    bad_choices = dict(field(selection(kind), 'parameters'))
    bad_choices['checker' if kind == 'fifo' else 'step'] = 'unknown'
    asic = [('run', [('backend', 'fixture'), ('id', 'fixture-run'), ('build', []), ('label', [])]),
            ('attempt', 'fixture-attempt'), ('artifact_id', 'fixture-artifact'), ('sha256', '0' * 64)]
    for label, update in [('case', dict(cases=['unknown'])), ('duplicate-case', dict(cases=[cases[0]] * 2)),
                          ('empty-case', dict(cases=[])), ('suite', dict(suite='unknown')),
                          ('asic', dict(asic_inputs=[asic])),
                          ('choice', dict(parameters=list(bad_choices.items()))),
                          ('missing-parameter', dict(parameters=[])),
                          ('duplicate-parameter', dict(parameters=field(selection(kind), 'parameters') * 2))]:
        invalid.append((label, dict(selection(kind), **update)))
    for label, selected in invalid:
        run_provider(commands['native'], list(selected.items()), directory / ('invalid-' + label), valid=False)
    if kind == 'counter':
        for cycles in ('31', '100001', 'not-an-integer'):
            selected = dict(selection(kind))
            selected['parameters'] = [(k, cycles if k == 'cycles' else v)
                                      for k, v in selected['parameters']]
            run_provider(commands['native'], list(selected.items()),
                         directory / ('invalid-cycles-' + cycles), valid=False)
    return runs


def daemon_acceptance(args, commands, expected, evidence):
    spec = importlib.util.spec_from_file_location('native_http', HERE / 'test-fs2-native.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    for kind in commands:
        directory = evidence / (kind + '-http')
        directory.mkdir()
        for name in ('state', 'home', 'config', 'tmp', 'project'):
            (directory / name).mkdir()
        root = directory / 'project'
        (root / 'dune-project').write_text('(lang dune 3.22)\n(name provider_acceptance)\n')
        command = commands[kind]['native']
        (root / 'hardcaml-workbench-simulation.sexp').write_text(sexp([
            ('schema_version', 1), ('provider_executable', command[0]), ('provider_args', command[1:]),
            ('discovery_timeout_seconds', 10), ('run_timeout_seconds', 90)]))
        session = helper.Session(args, directory, root)
        session.env.update(HOME=str(directory / 'home'), XDG_CONFIG_HOME=str(directory / 'config'),
                           TMPDIR=str(directory / 'tmp'), OMP_NUM_THREADS='6', OPENROAD_THREADS='6')
        details = []
        try:
            session.start()
            require(field(session.api(), 'attempts') == [], 'private empty history')
            discovered = session.discover()
            require(not field(discovered, 'discovery_error'), 'native discovery through daemon')
            digest = field(discovered, 'discovery_digest')[0]
            for label in ('max-seed', 'failure'):
                selected = expected[kind][label]['selection']
                submitted = session.api(operation=['Launch', ['submission_key', label],
                    ['discovery_digest', digest], ['selection', selected]])
                aid = field(field(submitted, 'detail')[0], 'id')
                detail = session.done(aid)
                require(field(detail, 'outcome') == ('Failed' if label == 'failure' else 'Passed')
                        and field(detail, 'exit_code') == ['0'], 'HTTP semantic outcome')
                require(canonical(field(field(detail, 'captured'), 'selection')) == canonical(parse(sexp(selected))),
                        'HTTP captured inputs')
                artifacts = field(detail, 'artifacts')
                require(len(artifacts) == len(expected[kind][label]['artifacts']), 'HTTP artifact count')
                for artifact in artifacts:
                    raw = bytearray()
                    while True:
                        snap = session.api(operation=['Read_artifact_bytes', ['attempt_id', aid],
                            ['artifact_id', field(artifact, 'id')], ['sha256', field(artifact, 'sha256')[0]],
                            ['offset', len(raw)], ['limit', 997]])
                        page = field(snap, 'byte_page')[0]
                        block = bytes.fromhex(field(page, 'bytes_hex'))
                        require(int(field(page, 'offset')) == len(raw), 'HTTP byte offset')
                        raw.extend(block)
                        if field(page, 'eof') == 'true':
                            break
                        require(block, 'HTTP page advances')
                    require(hashlib.sha256(raw).hexdigest() == field(artifact, 'sha256')[0], 'HTTP SHA256')
                    name = expected[kind][label]['labels'][field(artifact, 'label')]
                    require(stable_bytes(name, bytes(raw)) == stable_bytes(name, expected[kind][label]['artifacts'][name]),
                            'HTTP genuine artifact equality: ' + name)
                details.append(detail)
            session.stop()
            session.start()
            for detail in details:
                restored = field(session.api(operation=['Observe', field(detail, 'id')]), 'detail')[0]
                require(canonical(restored) == canonical(detail), 'durable attempt after private restart')
            (directory / 'details.json').write_text(json.dumps(details, indent=2))
        finally:
            if session.process:
                session.stop()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--only', choices=('counter', 'fifo'), help='test one adapter while the other is being built')
    p.add_argument('--counter-provider', type=Path)
    p.add_argument('--counter', type=Path)
    p.add_argument('--fifo-provider', type=Path)
    p.add_argument('--fifo-simulator', type=Path)
    p.add_argument('--fifo-root', type=Path, default=HERE.parent.parent / 'hardcaml_asic_example')
    p.add_argument('--daemon', type=Path, help='prebuilt daemon; enables private HTTP/restart acceptance')
    p.add_argument('--evidence', type=Path, help='new evidence directory (must not exist)')
    args = p.parse_args()
    for kind, names in [('counter', ('counter_provider', 'counter')),
                        ('fifo', ('fifo_provider', 'fifo_simulator'))]:
        if args.only is None or args.only == kind:
            for name in names:
                if getattr(args, name) is None:
                    p.error('--' + name.replace('_', '-') + ' is required for ' + kind)
    for name in ('counter_provider', 'counter', 'fifo_provider', 'fifo_simulator', 'fifo_root', 'daemon'):
        if getattr(args, name):
            setattr(args, name, getattr(args, name).resolve(strict=True))
    os.umask(0o077)
    if args.evidence:
        args.evidence = args.evidence.absolute()
        args.evidence.mkdir()
    else:
        args.evidence = Path(tempfile.mkdtemp(prefix='native-provider-', dir='/tmp/opencode'))
    print('Evidence: ' + str(args.evidence), flush=True)
    commands = {}
    if args.only in (None, 'counter'):
        commands['counter'] = {
            'python': [sys.executable, str(HERE.parent / 'examples/fs2_cyclesim/provider.py'), '--counter', str(args.counter)],
            'native': [str(args.counter_provider), '--counter', str(args.counter)]}
    if args.only in (None, 'fifo'):
        commands['fifo'] = {
            'python': [sys.executable, str(args.fifo_root / 'simulation/provider.py'), '--simulator', str(args.fifo_simulator)],
            'native': [str(args.fifo_provider), '--simulator', str(args.fifo_simulator)]}
    result = dict(status='failed', http=bool(args.daemon))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('600s acceptance budget')))
    signal.alarm(600)
    try:
        expected = {kind: equivalent(kind, command, args.evidence) for kind, command in commands.items()}
        if args.daemon:
            daemon_acceptance(args, commands, expected, args.evidence)
        result.update(status='passed', artifact_sha256={kind: {label: {
            name: hashlib.sha256(raw).hexdigest() for name, raw in run['artifacts'].items()}
            for label, run in runs.items()} for kind, runs in expected.items()})
    except BaseException:
        result['error'] = traceback.format_exc()
        raise
    finally:
        signal.alarm(0)
        (args.evidence / 'result.json').write_text(json.dumps(result, indent=2))
    print('PASS native provider equivalence' + (' + private daemon HTTP/restart' if args.daemon else ''))


if __name__ == '__main__':
    main()
