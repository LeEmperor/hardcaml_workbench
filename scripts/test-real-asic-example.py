#!/usr/bin/env python3
"""Bounded native HTTP/PTY acceptance of the actual retained ASIC example.

Uses prepared persistent binaries/config. No build, installation, EDA, or mocked
provider. Creates its own daemon/client state beneath the demo receipts directory.
"""
import argparse
from collections import Counter
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import pty
import signal
import struct
import subprocess
import sys
import termios
import time
import traceback
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


demo = load('real_asic_demo', 'real-asic-example-demo.py')
# Reuse only the terminal byte/cell oracle and key driver, never fixture seeding.
ui = load('real_asic_terminal_oracle', 'test-frontend-composition.py')
from http_client import field, parse, sexp


class Terminal(ui.Terminal):
    def __init__(self, base, binary, root, url, width=120, height=40):
        self.base, self.width, self.height = base, width, height
        self.data, self.keys = bytearray(), []
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
        self.process = subprocess.Popen(demo.switch_command([binary, '--connect', url,
            '--project-root', root, '--environment', 'opam:' + os.environ.get('OPAM_SWITCH', '5.2.0+ox')]),
            stdin=slave, stdout=slave, stderr=slave, start_new_session=True,
            env=dict(os.environ, TERM='xterm-256color', XDG_CONFIG_HOME=str(base / 'config'),
                     XDG_STATE_HOME=str(base / 'client-state')))
        os.close(slave)


def run(args):
    base = args.dir.resolve(strict=True)
    manifest = json.loads((base / 'manifest.json').read_text())
    root = Path(manifest['project_root'])
    evidence = base / 'receipts' / ('acceptance-' + uuid.uuid4().hex)
    evidence.mkdir()
    for name in ('discovery', 'state', 'client-state', 'config'):
        (evidence / name).mkdir()
    print('Evidence: ' + str(evidence), flush=True)
    watched = [root / demo.EVIDENCE, root / 'hardcaml-workbench-asic.sexp',
               Path(manifest['provider']).parent.parent, Path(manifest['project_executable']),
               root / '.dev/asic/current/receipt.json', base / 'results']
    before = demo.inventory(watched)
    demo.save(evidence / 'inputs-before.json', before)
    outcome = dict(status='failed', synthetic=False, project_root=str(root), checks=[],
                   manifest_sha256=demo.digest(base / 'manifest.json'),
                   binaries={name: demo.digest(base / 'bin' / name) for name in ('daemon', 'client', 'preset-export')})
    daemon = terminal = client = None

    def check(ok, message):
        outcome['checks'].append(dict(passed=bool(ok), expectation=message))
        demo.require(ok, message)

    log = (evidence / 'daemon.log').open('wb')
    try:
        daemon = subprocess.Popen(demo.switch_command([base / 'bin/daemon', '--port', '0',
            '--discovery-dir', evidence / 'discovery', '--state-dir', evidence / 'state']),
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        metadata = evidence / 'discovery/daemon.sexp'
        ui.wait(lambda: metadata.exists() or daemon.poll() is not None, 'private daemon metadata')
        check(daemon.poll() is None, 'Private native daemon started')
        url = field(parse(metadata.read_text()), 'endpoint')
        client, run_ref = demo.seed(base, url, evidence / 'seed')
        outcome['run'] = run_ref
        snapshot = client.rpc()
        registered = field(snapshot, 'runs')
        check(len(registered) == 1 and field(registered[0], 'reference') ==
              [[k, manifest['allocation'][k]] for k in ('attempt', 'stream_id')],
              'Only original exact observation allocation registered; Run_ref returned by daemon')
        summary = next(s for s in field(snapshot, 'summaries') if field(s, 'run') == run_ref)
        check(field(summary, 'cell_count') == ['673'] and field(summary, 'freshness') == 'Validated',
              'Actual synthesis boundary: 673 cells, validated')
        check(field(summary, 'execution_file') == manifest['execution_file'], 'Exact public execution_file adopted')
        terminal_result = field(summary, 'terminal')[0]
        check(field(terminal_result, 'acceptance') == 'pass' and field(terminal_result, 'physical_completion') == 'full',
              'Retained full physical completion and passing acceptance adopted separately')
        metrics = {field(m, 'key'): m for m in field(terminal_result, 'metrics')}
        outcome['terminal_metrics'] = metrics
        outcome['inspections'] = []
        for domain, stage in demo.DOMAINS:
            index = next(i for i in field(snapshot, 'inspections') if field(i, 'domain') == domain and field(i, 'stage') == stage)
            expected = next(i for i in manifest['inspections'] if i['domain'] == domain)
            check(len(field(index, 'rows')) == expected['rows'] and field(index, 'source_digest') == expected['source_digest']
                  and field(index, 'cached_unverified') == 'false', domain + ': native rich index matches public provider')
            chosen = next(r for r in field(index, 'rows') if json.loads(field(r, 'source')).get('file'))
            detail = client.rpc('(Inspect_detail (run %s) (domain %s) (stage %s) (source_digest %s) (row_id %s))' %
                                (sexp(run_ref), domain, stage, sexp(field(index, 'source_digest')), sexp(field(chosen, 'id'))))
            detail = next(d for d in field(detail, 'inspection_details') if field(d, 'domain') == domain)
            check(field(detail, 'error') == [] and bool(field(detail, 'text')), domain + ': exact row/digest source detail available')
            outcome['inspections'].append(dict(domain=domain, stage=stage, rows=len(field(index, 'rows')),
                                                categories=dict(Counter(field(r, 'category') for r in field(index, 'rows'))),
                                                source_digest=field(index, 'source_digest')))
        terminal = Terminal(evidence, base / 'bin/client', root, url)
        terminal.capture('overview-120x40', ['Overview', '673', 'validated'])
        check(True, 'Actual 120x40 Overview renders retained 673-cell validated evidence')
        terminal.resize(180, 55)
        large = terminal.capture('overview-180x55', ['673', '11.6755', '0.125029', 'pass'])
        check('SYNTHETIC' not in large.text(), 'Actual project Overview has measured setup/hold and passing acceptance')
        terminal.command('Switch to Timing')
        terminal.capture('timing-workspace', ['Timing'])
        # The workspace opens retained paths through the same native inspector.
        terminal.command('Inspect timing paths asic/%s · signoff' % field(run_ref, 'id'))
        terminal.capture('timing-paths', ['1021 paths', 'Verified observation', 'timing · selected path'])
        terminal.key(b'\r')
        terminal.capture('timing-path-detail', ['Row:', 'Startpoint:', 'Endpoint:'])
        check(True, 'Timing workspace renders the 1021-row timing index and exact native path detail')
        terminal.key(b'\x1b')
        terminal.key(b'\x1b')
        for domain, stage in demo.DOMAINS[1:]:
            terminal.command('Inspect %s asic/%s · %s' % (domain, field(run_ref, 'id'), stage))
            terminal.capture('explorer-' + domain, ['INSPECT ' + domain])
            terminal.key(b'\x1b')
        check(True, 'Clock, placement and routing rich explorers open in actual terminal')
        terminal.command('Switch to Overview')
        terminal.capture('overview-return', ['673', '11.6755', '0.125029'])
        terminal.close()
        terminal = None
        outcome['status'] = 'passed'
    except BaseException:
        outcome['error'] = traceback.format_exc()
        raise
    finally:
        if terminal is not None:
            terminal.close()
        if client is not None:
            demo.save(evidence / 'http.json', client.history)
        if daemon is not None and daemon.poll() is None:
            daemon.terminate()
            try:
                daemon.wait(timeout=10)
            except subprocess.TimeoutExpired:
                daemon.kill()
                daemon.wait(timeout=5)
        log.close()
        after = demo.inventory(watched)
        demo.save(evidence / 'inputs-after.json', after)
        outcome['canonical_inputs_unchanged'] = before == after
        outcome['canonical_files_checked'] = len(before)
        if before != after:
            outcome['status'] = 'failed'
        demo.save(evidence / 'result.json', outcome)
        demo.require(before == after, 'Canonical inputs changed; inspect inventories')
    print('PASS actual ASIC retained signoff HTTP/PTY: ' + str(evidence), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', type=Path, default=demo.EXAMPLE / '.dev/workbench-real-demo')
    args = parser.parse_args()
    def stop(signum, frame):
        raise TimeoutError('Real example acceptance interrupted or exceeded 480 seconds')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGALRM, stop)
    signal.alarm(480)
    run(args)


if __name__ == '__main__':
    main()
