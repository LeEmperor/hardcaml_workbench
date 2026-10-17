#!/usr/bin/env python3
"""Private exact-launch HTTP/PTY and read-only retained-real stage acceptance.

Requires matching prebuilt binaries; never builds, starts EDA, contacts the user's
daemon, or writes canonical evidence. --inventory-only needs no binaries. All
receipts, synthetic producers and daemon registrations stay under /tmp/opencode.
"""
import argparse
import hashlib
from http.client import HTTPConnection
import importlib.util
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import traceback
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


composition = module('consistency_composition', 'test-frontend-composition.py')
real = module('consistency_real', 'real-asic-example-demo.py')
field, sexp, require, wait = composition.field, composition.sexp, composition.require, composition.wait
Client = real.Client
STAGES = ('synthesis', 'floorplan', 'placement', 'cts', 'routing', 'signoff')
EXACT = ('20261017T040517848061Z_fac7d0bc', '20261017T040844955822Z_6c006def')


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def hashes(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths)) if p.is_file()}


def inventory(args):
    """Identity comes from public records, never a directory's abbreviated suffix."""
    manifest = json.loads((args.real_demo / 'manifest.json').read_text())
    root, provider = Path(manifest['project_root']), Path(manifest['provider'])
    attempts = [args.real_demo / 'results/observations' / name for name in EXACT]
    allocation_file = root / real.EVIDENCE / 'client/run.stdout.jsonl'
    allocation = json.loads(allocation_file.read_text().splitlines()[0])
    require(allocation == dict(allocation, **manifest['allocation']), 'Historical allocation agrees with prepared manifest')
    attempts.append(Path(allocation['attempt']))
    paths = [args.real_demo / 'manifest.json', root / 'hardcaml-workbench-asic.sexp', provider, allocation_file]
    for attempt in attempts:
        paths += list(attempt.glob('*.json'))
    paths += [Path(item['path']) for item in manifest['hashes']]
    before = hashes(paths)
    save(args.evidence / 'canonical-before.json', before)
    references = []
    for index, attempt in enumerate(attempts):
        records = [json.loads(p.read_text()) for p in sorted(attempt.glob('[0-9]*.json'))]
        ids = {r['stream_id'] for r in records}
        require(len(ids) == 1, 'Exact public records have one stream identity: ' + str(attempt))
        stream = ids.pop()
        require(all(r['contract'] == 'hardcaml-asic.stage-observation' and r['schema_version'] == 2 for r in records),
                'Supported canonical observation record contract')
        observed = real.query(provider, ['observation', 'inspect', attempt, '--json'], root, args.evidence, 'real-' + str(index))
        require(observed['stream_id'] == stream, 'Public inspect identity matches exact records')
        require(not observed['writer_active'] and observed['state']['outcome']['status'] == 'completed', 'Retained run is terminal completed')
        requested = list(STAGES) if index == 2 else ['synthesis']
        require(observed['state']['plan']['stages'] == requested, 'Exact public requested recipe')
        require({o['action_key'] for o in observed['state']['occurrences'] if o['status'] == 'completed' and o['exit_code'] == 0}
                == {'implementation.' + s for s in requested}, 'Exact completed occurrences support every claimed stage')
        execution = Path(observed['execution_file'])
        # Add newly disclosed exact references before any subsequent query.
        before.update(hashes([execution]))
        report = real.query(provider, ['report', execution, '--json'], root, args.evidence, 'report-' + str(index))
        require(report['execution']['attempt_id'] == stream, 'Report is the exact observation execution')
        before.update(hashes([Path(c['reference']['path']) / 'manifest.json' for c in report['checkpoints']]))
        references.append(dict(attempt=str(attempt), stream_id=stream, observation=observed, execution_file=str(execution)))
    require(references[-1]['stream_id'] == allocation['stream_id'], 'Historical original receipt identity')
    after = hashes(map(Path, before))
    require(before == after, 'Read-only public inventory leaves canonical hashes unchanged')
    save(args.evidence / 'canonical-before.json', before)
    save(args.evidence / 'canonical-after.json', after)
    save(args.evidence / 'real-inventory.json', references)
    return manifest, references, before


class PrivateDaemon:
    def __init__(self, args, base):
        self.args, self.base, self.process = args, base, None
        self.histories = []

    def start(self):
        discovery = self.base / 'discovery'
        discovery.mkdir(exist_ok=True)
        metadata = discovery / 'daemon.sexp'
        if metadata.exists(): metadata.unlink()
        self.log = (self.base / 'daemon.log').open('ab')
        self.process = subprocess.Popen(real.switch_command([self.args.daemon, '--port', '0',
            '--discovery-dir', discovery, '--state-dir', self.base / 'state']),
            stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True,
            env=dict(os.environ, HOME=str(self.base / 'home'),
                     OPAMROOT=os.environ.get('OPAMROOT', str(Path.home() / '.opam')),
                     XDG_CONFIG_HOME=str(self.base / 'config'), XDG_STATE_HOME=str(self.base / 'client-state')))
        wait(lambda: metadata.exists() or self.process.poll() is not None, 'private daemon starts')
        require(self.process.poll() is None, 'Private daemon failed; see daemon.log')
        self.url = field(composition.parse(metadata.read_text()), 'endpoint')
        self.http = Client(self.url, self.base / 'project', switch=composition.demo.switch_name())
        self.histories.append(self.http.history)
        return self.http

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try: self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
        if self.process is not None:
            self.log.close()
            save(self.base / 'http.json', self.histories)


def stage_status(run):
    return {field(s, 'id'): field(s, 'status') for s in field(run, 'stages')}


def real_acceptance(args, manifest, references, check):
    base = args.evidence / 'real-private'
    for name in ('project', 'state', 'home', 'config', 'client-state'): (base / name).mkdir(parents=True)
    root = base / 'project'
    (root / 'dune-project').write_text('(lang dune 3.22)\n(name consistency_real_private)\n')
    # Fail closed: even accidental Run/Plan/Discover requests cannot reach EDA.
    wrapper = root / 'readonly-provider'
    wrapper.write_text('#!' + sys.executable + '\nimport json, os, subprocess, sys\n' +
        'from pathlib import Path\na=sys.argv[1:]\n' +
        'refs=' + repr([{k: r[k] for k in ('attempt', 'stream_id', 'execution_file')} for r in references]) + '\n' +
        'ok=a==["--version","--json"]\n' +
        'for r in refs:\n' +
        ' ok |= a==["observation","inspect",r["attempt"],"--json"]\n' +
        ' ok |= len(a)==8 and a[:3]==["observation","read-updates",r["attempt"]] and a[3:6]==["--stream-id",r["stream_id"],"--after"] and a[6].isdigit() and a[7:]==["--json"]\n' +
        'with Path(' + repr(str(base / 'provider-calls.jsonl')) + ').open("a") as f: f.write(json.dumps(dict(argv=a,allowed=ok))+"\\n")\n' +
        'if not ok: raise SystemExit("read-only exact-observation allowlist rejected command")\n' +
        'control=Path(' + repr(str(base / 'fixture-mode')) + ')\n' +
        'if control.exists() and a[:2]==["observation","inspect"]:\n' +
        ' p=subprocess.run([' + repr(manifest['provider']) + ']+a,check=True,capture_output=True)\n' +
        ' j=json.loads(p.stdout); mode=control.read_text(); j.pop("stage_plan",None)\n' +
        ' if mode in ("running","failed","interrupted","completed"):\n' +
        '  for o in j["state"]["occurrences"]:\n' +
        '   o["status"]=mode; o["exit_code"]=0 if mode=="completed" else 1 if mode in ("failed","interrupted") else None\n' +
        '  j["writer_active"]=mode=="running"; j["observation_status"]="active" if mode=="running" else "final"\n' +
        '  j["state"]["outcome"]=None if mode=="running" else dict(status=mode,exit_code=0 if mode=="completed" else 1,error=None)\n' +
        ' elif mode=="unknown-plan": j["state"]["plan"]["schema_version"]=999\n' +
        ' elif mode=="identity-mismatch": j["state"]["attempt_id"]="unrelated-fixture-identity"\n' +
        ' elif mode=="no-structured-stages": j["state"].pop("plan",None); j["state"].pop("occurrences",None)\n' +
        ' print(json.dumps(j)); raise SystemExit(0)\n' +
        'os.execv(' + repr(manifest['provider']) + ',[' + repr(manifest['provider']) + ']+a)\n')
    wrapper.chmod(0o700)
    config = composition.parse((Path(manifest['project_root']) / 'hardcaml-workbench-asic.sexp').read_text())
    for entry in config:
        if entry[0] == 'provider_executable': entry[1] = str(wrapper)
        if entry[0] == 'results_root': entry[1] = str(base / 'results')
    (root / 'hardcaml-workbench-asic.sexp').write_text(sexp(config))
    daemon = PrivateDaemon(args, base)
    try:
        http = daemon.start()
        for index, reference in enumerate(references):
            ref = [[k, reference[k]] for k in ('attempt', 'stream_id')]
            http.rpc('(Register %s)' % sexp(ref), wait=False)
            def registered():
                return next((r for r in field(http.rpc(wait=False), 'runs') if field(r, 'reference') == ref), None)
            run = wait(registered, 'exact retained registration')
            http.rpc('(Observe %s)' % sexp(field(run, 'run')), wait=False)
            expected = {s: 'Completed' if index == 2 or s == 'synthesis' else 'Not_requested' for s in STAGES}
            run = wait(lambda: r if (r := registered()) and stage_status(r) == expected else None,
                       'real explicit stage projection ' + reference['stream_id'])
            check(stage_status(run) == expected, 'Exact real ' + reference['stream_id'] + ': ' + str(expected))
            save(base / ('run-' + str(index) + '.json'), run)
        check(not field(http.rpc(wait=False), 'launches'), 'Read-only historical registration creates no launch association')
        # PRIVATE response clones retain genuine exact public stream, journal cursor,
        # methodology and execution refs. No canonical provider result is modified.
        reference = references[1]
        target = next(r for r in field(http.rpc(wait=False), 'runs') if field(field(r, 'reference'), 'stream_id') == reference['stream_id'])
        run_id = field(target, 'run')
        for mode, expected in (('running', 'Running'), ('failed', 'Failed'), ('interrupted', 'Cancelled'), ('completed', 'Completed')):
            (base / 'fixture-mode').write_text(mode)
            http.rpc('(Observe %s)' % sexp(run_id), wait=False)
            def projected():
                r = next(r for r in field(http.rpc(wait=False), 'runs') if field(r, 'run') == run_id)
                return r if stage_status(r) == dict(zip(STAGES, [expected] + ['Not_requested'] * 5)) else None
            r = wait(projected, 'private raw-public-grammar fixture ' + mode)
            check(field(r, 'execution_file') == [reference['execution_file']], 'Private ' + mode + ' fixture retains real checkpoint/execution reference without inferring completion')
            save(base / ('PRIVATE-fixture-' + mode + '.json'), r)
        for mode in ('unknown-plan', 'no-structured-stages'):
            (base / 'fixture-mode').write_text(mode)
            http.rpc('(Observe %s)' % sexp(run_id), wait=False)
            def opaque():
                r = next(r for r in field(http.rpc(wait=False), 'runs') if field(r, 'run') == run_id)
                return r if not field(r, 'stages') else None
            r = wait(opaque, 'private opaque raw-public-grammar fixture ' + mode)
            check(not field(r, 'stages'), 'Private ' + mode + ' fixture clears prior completed checklist rather than inventing success')
            save(base / ('PRIVATE-fixture-' + mode + '.json'), r)
        (base / 'fixture-mode').unlink()
        http.rpc('(Observe %s)' % sexp(run_id), wait=False)
    finally: daemon.stop()


def synthetic_acceptance(args, check):
    base = composition.demo.prepare(args.evidence / 'synthetic-private', manual=True, delay=.05)
    for name in ('home', 'config', 'client-state'): (base / name).mkdir()
    wrapper = base / 'project/synthetic-flow'
    original = wrapper.read_text()
    control = base / 'producer-control'
    wrapper.write_text('#!' + sys.executable + '\nimport time\nfrom pathlib import Path\n' +
        'c=Path(' + repr(str(control)) + ')\n' +
        'if __import__("sys").argv[1:3]==["flow","run"] and c.exists():\n' +
        ' c.with_suffix(".entered").write_text("entered")\n' +
        ' if c.read_text()=="fail": raise SystemExit("INJECTED pre-allocation failure")\n' +
        ' deadline=time.monotonic()+45\n' +
        ' while c.exists():\n' +
        '  if time.monotonic()>deadline: raise SystemExit("private allocation gate timeout")\n' +
        '  time.sleep(.05)\n' + original.split('\n', 1)[1])
    daemon = PrivateDaemon(args, base)
    terminal = None
    try:
        daemon.start()
        http, historical = composition.demo.seed(base, daemon.url, args.preset_export)
        daemon.histories.append(http.history)
        terminal = composition.Terminal(base, args, daemon.url, 180, 55)
        terminal.capture('initial-no-association', ['planned-run', 'Overview'])

        def snap(): return http.rpc(wait=False)
        def ledger(key): return next((l for l in field(snap(), 'launches') if field(l, 'key') == key), None)
        def run_for(key):
            launch = ledger(key)
            return next((r for r in field(snap(), 'runs') if field(field(r, 'run'), 'id') in field(launch, 'run_id')), None) if launch else None
        def plan(endpoint):
            selected = [['flow', 'synthetic'], ['profile', 'success'], ['endpoint', endpoint], ['assignments', []]]
            http.rpc('(Plan %s)' % sexp(selected), wait=False)
            return wait(lambda: next((p for p in field(snap(), 'preview') if field(p, 'selection') == selected), None), 'ready exact preview')
        def submit(key, preview):
            return http.rpc('(Run (key %s) (preview %s))' % (sexp(key), sexp(preview)), wait=False)
        def observe(key, expected):
            run = wait(lambda: run_for(key), 'exact allocation ' + key)
            http.rpc('(Observe %s)' % sexp(field(run, 'run')), wait=False)
            return wait(lambda: r if (r := run_for(key)) and stage_status(r) == dict(zip(STAGES, expected)) else None,
                        'exact observed stages ' + key)
        def detail(label, expected):
            ws = http.rpc(domain='workspace')
            overview = next(w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview'])
            tile = next(t for t in field(ws, 'tiles') if field(t, 'workspace') == field(overview, 'id') and field(t, 'kind') == 'planned-run')
            http.mutate(ws, '(Set_zoom (workspace %s) (tile (%s)))' % (sexp(field(overview, 'id')), sexp(field(tile, 'id'))))
            terminal.capture(label, expected, ['no job allocated', 'no queued job'])

        preview = plan('placement')
        check(not field(snap(), 'launches'), 'Preview and selected historical run alone allocate/associate nothing')
        detail('preview-ready-unassociated', ['ready:', 'association unavailable'])
        terminal.command('Unzoom workspace')
        terminal.command('Launch synthetic / success → placement')
        first = wait(lambda: field(snap(), 'launches'), 'explicit PTY Run ledger reservation')[0]
        key = field(first, 'key')
        first_run = observe(key, ['Running', 'Pending', 'Pending'] + ['Not_requested'] * 3)
        first_id = field(field(first_run, 'run'), 'id')
        check(field(ledger(key), 'preview') == preview and field(ledger(key), 'run_id') == [first_id], 'Explicit PTY Run retains full exact preview/key/allocation in ledger')
        detail('explicit-run-running', ['ready:', 'Producer running', 'submission key: ' + key, 'exact allocated run: ' + first_id])
        submit(key, preview)
        check(field(ledger(key), 'run_id') == [first_id], 'Retry same key retains exact allocation')
        attempt = Path(field(field(first_run, 'reference'), 'attempt'))
        provider = composition.demo.provider
        for statuses in (['Completed', 'Running', 'Pending'], ['Completed', 'Completed', 'Running'], ['Completed'] * 3):
            provider.advance(attempt)
            observe(key, statuses + ['Not_requested'] * 3)
        detail('explicit-run-completed', ['ready:', 'Producer completed', first_id])

        # Separate HTTP client: terminal has no local launch receipt for this key.
        other = Client(daemon.url, base / 'project', switch=composition.demo.switch_name())
        daemon.histories.append(other.history)
        other.rpc('(Run (key "same-preview-new-launch") (preview %s))' % sexp(preview), wait=False)
        second = observe('same-preview-new-launch', ['Running', 'Pending', 'Pending'] + ['Not_requested'] * 3)
        second_id = field(field(second, 'run'), 'id')
        check(second_id != first_id and field(ledger('same-preview-new-launch'), 'preview') == preview, 'Same plan explicit new key allocates distinct run; another client has exact ledger evidence')
        detail('other-client-no-local-receipt', ['Producer running', 'same-preview-new-launch', second_id],)
        http.rpc('(Cancel "run:same-preview-new-launch")', wait=False)
        wait(lambda: any(field(o, 'key') == 'run:same-preview-new-launch' and field(o, 'state') == 'failed' for o in field(snap(), 'operations')), 'cancel owned producer')
        http.rpc('(Observe %s)' % sexp(field(second, 'run')), wait=False)
        wait(lambda: field(run_for('same-preview-new-launch'), 'status') == 'cancelled', 'cancelled exact observation')
        detail('explicit-run-cancelled', ['cancelled', second_id])

        # Send the full HTTP request but deliberately never read its response.
        # The client must recover from the ledger, not from a local receipt or
        # whichever historical run happens to be selected in the workspace.
        url = urlsplit(daemon.url)
        connection = HTTPConnection(url.hostname, url.port, timeout=10)
        body = '((instance_id %s) (project %s) (operation (Run (key "unreceived-http-receipt") (preview %s))))' % (
            sexp(http.instance), sexp(http.project), sexp(preview))
        try:
            connection.request('POST', '/api/v1/asic', body=body.encode(), headers={
                'Content-Type': 'application/sexp', 'X-Workbench-Protocol': '1'})
            unreceived = observe('unreceived-http-receipt', ['Running', 'Pending', 'Pending'] + ['Not_requested'] * 3)
        finally: connection.close()
        save(base / 'deliberately-unreceived-http-request.json', dict(request=body, response_read=False))
        unreceived_id = field(field(unreceived, 'run'), 'id')
        detail('unreceived-http-receipt-recovered', ['unreceived-http-receipt', unreceived_id, 'Producer running'])
        check(unreceived_id not in (first_id, second_id), 'Deliberately unread Run response recovers its exact ledger allocation without historical association')
        submit('unreceived-http-receipt', preview)
        check(field(ledger('unreceived-http-receipt'), 'run_id') == [unreceived_id], 'Retry after missing HTTP receipt is idempotent')
        http.rpc('(Cancel "run:unreceived-http-receipt")', wait=False)
        wait(lambda: any(field(o, 'key') == 'run:unreceived-http-receipt' and field(o, 'state') == 'failed' for o in field(snap(), 'operations')), 'cancel missing-receipt fixture')

        control.write_text('fail')
        submit('preallocation-failure', preview)
        wait(lambda: any(field(o, 'key') == 'run:preallocation-failure' and field(o, 'state') == 'failed' for o in field(snap(), 'operations')), 'preallocation failure')
        check(field(ledger('preallocation-failure'), 'run_id') == [], 'Failed preallocation reservation has no invented run ID')
        detail('preallocation-failure', ['Launch operation failed', 'preallocation-failure'])
        control.write_text('gate')
        submit('preallocation-cancel', preview)
        wait(lambda: ledger('preallocation-cancel'), 'pending durable reservation')
        detail('preallocation-submitting', ['Submission reserved', 'preallocation-cancel'])
        http.rpc('(Cancel "run:preallocation-cancel")', wait=False)
        wait(lambda: any(field(o, 'key') == 'run:preallocation-cancel' and field(o, 'state') == 'failed' for o in field(snap(), 'operations')), 'preallocation cancel')
        check(field(ledger('preallocation-cancel'), 'run_id') == [], 'Cancel before allocation retains key without unrelated history association')
        control.unlink()
        new_preview = plan('routing')
        detail('replan-has-no-launch-association', ['ready:', 'association unavailable'],)
        check(not any(field(l, 'preview') == new_preview for l in field(snap(), 'launches')), 'Different exact preview never inherits a historical/latest launch')
        # Re-plan old selection: recover only its own latest durable reservation.
        preview = plan('placement')
        submit('detach-restart', preview)
        detached = observe('detach-restart', ['Running', 'Pending', 'Pending'] + ['Not_requested'] * 3)
        detached_id = field(field(detached, 'run'), 'id')
        terminal.close(); terminal = None
        check(field(run_for('detach-restart'), 'run') == field(detached, 'run'), 'Client detach leaves daemon producer and exact reservation intact')
        before_restart = field(snap(), 'launches')
        daemon.stop()
        http = daemon.start()
        check(field(snap(), 'launches') == before_restart, 'Daemon restart preserves authoritative exact launch ledger order and identities')
        terminal = composition.Terminal(base, args, daemon.url, 180, 55)
        terminal.capture('restart-overview', ['Overview'])
        detail('restart-separate-durable-launch-reference', ['no current plan', 'ownership detached', detached_id, 'detach-restart'])
        check(not field(snap(), 'preview'), 'Restart exposes separate durable launch reference without claiming a current ready preview')
        restored = plan('placement')
        check(restored == preview, 'Explicit post-restart replan reproduces the exact submitted preview')
        detail('restart-detached-ownership', ['ownership detached', detached_id, 'detach-restart'])
        check(field(ledger('detach-restart'), 'run_id') == [detached_id], 'Restart does not reacquire producer ownership or associate any selected historical run')
        calls = [json.loads(line)['argv'] for line in (base / 'project/provider-calls.jsonl').read_text().splitlines()]
        producers = [a for a in calls if a[:2] == ['flow', 'run']]
        check(len(producers) == 4, 'Exactly four successful synthetic provider invocations: initial, reuse, missing-receipt and detach/restart launches; no retry/restart/replan replay')
        check(not any(a[:1] == ['finalize'] for a in calls), 'Acceptance starts no finalization producer')
        save(base / 'final-snapshot.json', snap())
    finally:
        if terminal is not None: terminal.close()
        daemon.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('daemon', 'client', 'preset-export'): parser.add_argument('--' + name, type=Path)
    parser.add_argument('--real-demo', type=Path, default=real.EXAMPLE / '.dev/workbench-real-demo')
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--inventory-only', action='store_true')
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    args.evidence = args.evidence or Path('/tmp/opencode') / ('launch-stage-consistency-' + secrets.token_hex(6))
    args.evidence = args.evidence.resolve()
    require(args.evidence.is_relative_to('/tmp/opencode'), 'Evidence must be private /tmp/opencode state')
    args.real_demo = args.real_demo.resolve(strict=True)
    os.umask(0o077)
    args.evidence.mkdir(parents=True, exist_ok=False)
    result = dict(status='failed', checks=[], evidence=str(args.evidence))
    def check(ok, message):
        result['checks'].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Acceptance budget exhausted')))
    signal.alarm(args.timeout)
    before = None
    try:
        manifest, references, before = inventory(args)
        check(True, 'Exact public real-record identities and unchanged canonical hashes inventoried')
        if not args.inventory_only:
            for name in ('daemon', 'client', 'preset_export'):
                require(getattr(args, name) is not None, 'Matching prebuilt --' + name.replace('_', '-') + ' required')
                setattr(args, name, getattr(args, name).resolve(strict=True))
            result['binaries'] = hashes([args.daemon, args.client, args.preset_export])
            real_acceptance(args, manifest, references, check)
            synthetic_acceptance(args, check)
        result['status'] = 'passed'
    except BaseException:
        result['error'] = traceback.format_exc()
        raise
    finally:
        signal.alarm(0)
        if before is not None:
            after = hashes(map(Path, before))
            save(args.evidence / 'canonical-after.json', after)
            if before != after:
                result['status'] = 'failed'
                result['canonical_hash_error'] = 'Canonical evidence changed'
        save(args.evidence / 'result.json', result)
    require(result['status'] == 'passed', str(result))
    print('PASS exact launch/stage consistency: ' + str(args.evidence), flush=True)


if __name__ == '__main__': main()
