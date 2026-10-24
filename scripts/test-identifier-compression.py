#!/usr/bin/env python3
"""WB-073 real HTTP/PTY formatting acceptance, using prebuilt binaries only.

Seeds private retained FS2 records with deliberately colliding identities; never
launches simulation, EDA or provider discovery. All state is under /tmp/opencode.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('compression_testing', HERE / 'test-testing-workspace.py')
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
field, sexp, require = T.field, T.sexp, T.require


def sexp(value):
    if isinstance(value, (list, tuple)):
        return '(' + ' '.join(map(sexp, value)) + ')'
    return json.dumps(str(value), ensure_ascii=False)


IDS = ['sim-' + c * 16 + 'abcd' for c in '01']
JOB = 'sim-' + '2' * 16 + 'abcd'
DIGEST = 'sim-' + '3' * 16 + 'abcd'
LABEL = 'Human provider waveform label 試験'
SCREEN_LABEL = 'Human provider waveform label 試 験'  # emulator stores wide-cell continuations
VCD = (b'$timescale 1 ns $end\n$scope module top $end\n'
       b'$var wire 1 ! technical_signal_name_never_compress $end\n'
       b'$upscope $end\n$enddefinitions $end\n#0\n0!\n#10\n1!\n')


def seed(base, root):
    selection = [('suite', 'fixture'), ('cases', ['case']), ('seed', '7'),
                 ('parameters', []), ('asic_inputs', [])]
    for i, aid in enumerate(IDS):
        directory = base / 'state/simulation-v1' / hashlib.sha256(str(root).encode()).hexdigest() / aid
        directory.mkdir(parents=True)
        sha = hashlib.sha256(VCD).hexdigest()
        artifact = [('id', 'trace'), ('attempt_id', aid), ('case_id', ['case']),
                    ('label', LABEL), ('kind', 'waveform'), ('media_type', 'text/vcd'),
                    ('size', [len(VCD)]), ('sha256', [sha]), ('availability', 'Available')]
        attempt = [('id', aid), ('job', JOB), ('project_root', str(root)),
                   ('created_at', '2026-10-24T00:00:0%dZ' % (1-i)), ('parent', []),
                   ('captured', [('selection', selection), ('discovery_digest', DIGEST),
                                 ('provider_executable', '/fixture/never-execute'),
                                 ('provider_args', []), ('environment', 'Inherit_daemon')]),
                   ('lifecycle', 'Interrupted'), ('outcome', 'Incomplete'), ('exit_code', []),
                   ('diagnostic', []), ('progress', []),
                   ('cases', [[('case_id', 'case'), ('status', 'Incomplete'),
                               ('message', []), ('progress', [])]]),
                   ('artifacts', [artifact]), ('next_sequence', 0), ('recent_events', [])]
        key = 'compression-%d' % i
        payload = ['Launch', ('submission_key', key), ('discovery_digest', DIGEST), ('selection', selection)]
        (directory / 'record.sexp').write_text(sexp([
            ('schema_version', 1), ('submission_key', key), ('payload', sexp(payload)), ('attempt', attempt)]))
        (directory / ('artifact-' + hashlib.sha256(b'trace').hexdigest() + '.bytes')).write_bytes(VCD)


def run(args):
    base = args.evidence
    for name in ('project', 'state', 'home', 'config', 'tmp'):
        (base / name).mkdir()
    root = base / 'project'
    (root / 'dune-project').write_text('(lang dune 3.22)\n(name compression_fixture)\n')
    seed(base, root)
    session = T.native.Session(args, base, root)
    session.env.update(HOME=str(base / 'home'), XDG_CONFIG_HOME=str(base / 'config'),
                       TMPDIR=str(base / 'tmp'), OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                       OPENROAD_THREADS='1', _OPENLANE_MAX_CORES='1')
    terminal = None
    result = dict(status='failed', checks=[])

    def check(message):
        result['checks'].append(message)

    def compact(aid):
        return aid[:5] + '…' + aid[-5:]

    def command(scope, choice):
        titles = {'full': 'Show full identifiers', 'compact': 'Compress identifiers',
                  'reset': 'Reset compression (inherit)'}
        terminal.palette('Strings (%s): %s' % (scope, titles[choice]))

    try:
        session.start()
        snapshot = session.api()
        require(len(field(snapshot, 'attempts')) == 2 and not field(snapshot, 'history_error'),
                'private retained collision fixtures loaded')
        terminal = T.Terminal(session)
        terminal.capture('startup', ['Overview'])
        terminal.palette('Timing preload: Explicit only')
        terminal.key(b'2')
        terminal.capture('testing', ['simulation-detail'])
        # Navigation, Session, project tests, execution, catalog, attempts.
        for _ in range(5):
            terminal.key(b'\t')
        terminal.palette('Zoom focused tile')
        terminal.capture('colliding-attempt-list', [compact(aid) for aid in IDS])
        terminal.resize(32, 24)
        terminal.capture('narrow-collision-list', [compact(aid) for aid in IDS])
        terminal.resize(120, 40)
        check('actual Testing renderer expands same-first4/last4 attempt IDs distinctly')
        command('global', 'full')
        terminal.capture('global-full-list', IDS)
        command('workspace', 'compact')
        terminal.capture('workspace-compact-list', [compact(aid) for aid in IDS], absent=IDS)
        command('focused tile', 'full')
        terminal.capture('tile-full-list', IDS)
        command('focused tile', 'reset')
        terminal.capture('tile-inherits-workspace', [compact(aid) for aid in IDS])
        check('global/full, workspace/compact, tile/full and tile/reset affect rendered list')
        terminal.palette('Unzoom workspace')
        terminal.key(b'\t'); terminal.key(b'\t')  # Cases, Detail
        terminal.palette('Zoom focused tile')
        terminal.capture('detail-compact', ['Attempt: ' + compact(IDS[0]),
            'Job: ' + compact(JOB), 'Discovery: ' + compact(DIGEST), SCREEN_LABEL])
        command('workspace', 'reset')
        terminal.capture('detail-global-full', ['Attempt: ' + IDS[0], 'Job: ' + JOB, 'Discovery: ' + DIGEST])
        command('workspace', 'compact')
        terminal.capture('detail-workspace-compact', ['Job: ' + compact(JOB)])
        check('detail attempt/job/discovery share collision population; provider label stays intact')
        # Restart the actual client against the same daemon and project preferences.
        terminal.close(); terminal = T.Terminal(session)
        terminal.capture('restart-scopes', ['Attempt: ' + compact(IDS[0]), 'Job: ' + compact(JOB)])
        check('workspace override and global default survive fresh client restart')
        terminal.palette('Unzoom workspace')
        terminal.key(b'\t')  # Artifacts
        terminal.palette('Zoom focused tile')
        terminal.capture('artifact-label', ['Human provider waveform label', 'Available'])
        terminal.key(b'w')
        terminal.capture('quick-waveform-compact', ['Waveform', 'sim-…abcd'])
        command('workspace', 'full')
        terminal.capture('quick-waveform-full', [IDS[0], hashlib.sha256(VCD).hexdigest()])
        command('workspace', 'compact')
        terminal.key(b'q')
        terminal.capture('back-to-artifacts', ['simulation-artifacts', 'Available'])
        check('quick waveform header obeys source tile policy; full mode reveals exact attempt/digest')
        terminal.key(b'W')
        terminal.capture('waveforms', ['Waveforms', 'Ready'])
        terminal.key(b'\t')  # Session, after workspace navigation
        terminal.palette('Zoom focused tile')
        # New workspace inherits global full, rather than Testing compact.
        terminal.capture('waveform-global-full', [IDS[0]])
        command('workspace', 'compact')
        terminal.capture('waveform-workspace-compact', ['sim-…abcd'], absent=[IDS[0]])
        command('focused tile', 'full')
        terminal.capture('waveform-tile-full', [IDS[0]])
        check('Waveforms Session inherits global, independent workspace and focused tile policy')
        # Presentation never changes retained exact selectors or artifact bytes.
        exact = field(session.api(operation=['Observe', IDS[0]]), 'detail')[0]
        require(field(exact, 'id') == IDS[0] and field(exact, 'job') == JOB, 'raw selectors exact')
        require(field(field(exact, 'captured'), 'discovery_digest') == DIGEST, 'raw discovery exact')
        # The reused ASCII S-expression fixture codec maps OCaml decimal byte escapes
        # to Latin-1 scalars. Decode that byte string for this Unicode assertion.
        raw_label = field(field(exact, 'artifacts')[0], 'label').encode('latin1').decode('utf8')
        require(raw_label == LABEL, 'provider Unicode label exact')
        sha = hashlib.sha256(VCD).hexdigest()
        page = field(session.api(operation=['Read_artifact_bytes', ['attempt_id', IDS[0]],
            ['artifact_id', 'trace'], ['sha256', sha], ['offset', 0], ['limit', 4096]]), 'byte_page')[0]
        require(bytes.fromhex(field(page, 'bytes_hex')) == VCD, 'raw artifact source bytes exact')
        require(not field(session.raw('/api/v1/snapshot', [('instance_id', session.metadata['instance_id'])])[1], 'jobs'),
                'no domain jobs allocated by display changes')
        check('exact HTTP source identities preserved; zero provider/domain jobs')
        result['status'] = 'passed'
    finally:
        if terminal:
            terminal.save('final', terminal.drain(.1))
            terminal.close()
        session.stop()
        (base / 'verified.json').write_text(json.dumps(result, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--daemon', type=Path, required=True)
    p.add_argument('--client', type=Path, required=True)
    args = p.parse_args()
    args.daemon = args.daemon.resolve(strict=True)
    args.client = args.client.resolve(strict=True)
    args.outer_timeout = 30
    os.umask(0o077)
    args.evidence = Path(tempfile.mkdtemp(prefix='identifier-compression-', dir='/tmp/opencode'))
    print('Evidence: ' + str(args.evidence), flush=True)
    run(args)
    print('PASS identifier compression HTTP/PTY', flush=True)


if __name__ == '__main__':
    main()
