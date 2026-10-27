#!/usr/bin/env python3
"""Real native HTTP/PTY fresh-prefix acceptance with synthetic EDA providers only.

Uses explicit prebuilt binaries and new /tmp/opencode state. Never contacts a
pre-existing daemon. Every nested Dune call uses the shared lock and -j6.
"""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import time
import traceback
from types import SimpleNamespace
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


c = module('fresh_composition', HERE / 'test-frontend-composition.py')
field, sexp, require = c.field, c.sexp, c.require
Client = c.demo.Client


def wait(predicate, label, timeout=120):
    return c.wait(predicate, label, timeout=timeout)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


class Fixture:
    def __init__(self, args, label, check):
        self.args, self.check = args, check
        self.base = c.demo.prepare(args.evidence / label, delay=.05)
        self.root = root = self.base / 'project'
        settings = root / 'synthetic-settings.json'
        settings.write_text(json.dumps(dict(json.loads(settings.read_text()), executable_timing=True)))
        self.process = None
        self.histories = []
        for name in ('home', 'config', 'client-state', 'state', 'discovery', 'bin'):
            (self.base / name).mkdir(exist_ok=True)
        shutil.copyfile(HERE / 'fixtures/unified_fresh_prefix.py', root / 'fixture.py')
        shutil.copyfile(REPO / 'backend/test/fresh_provider.py', root / 'physical.py')
        fixture = root / 'fixture.py'
        for name, role in [('publisher-source', 'emit'), ('provider', 'provider'), ('pinned', 'pinned')]:
            path = root / name
            path.write_text('#!' + sys.executable + '\nimport os\nos.execv(' + repr(sys.executable) +
                            ', ' + repr([sys.executable, str(fixture), role, str(root)]) + ' + __import__("sys").argv[1:])\n')
            path.chmod(0o700)
        (root / 'generation').write_text('generation-1')
        (root / 'build-trigger').write_text('0')
        (root / 'dune').write_text('(rule (target publisher.exe) (deps publisher-source build-trigger) '
                                  '(action (run ' + sexp(sys.executable) + ' ' + sexp(str(fixture)) +
                                  ' build ' + sexp(str(root)) + ')))\n')
        prep = [['schema_version', 1], ['build_target', 'publisher.exe'],
                ['results_root', str(self.base / 'publication')], ['timeout_seconds', 180]]
        (root / 'hardcaml-workbench-preparation.sexp').write_text(sexp(prep))
        self.config = [['schema_version', 1], ['project_executable', str(root / 'pinned')],
                       ['provider_executable', str(root / 'provider')], ['results_root', str(self.base / 'results')],
                       ['toolchain', str(root)], ['python', [str(root / 'configured-python')]],
                       ['support_tools', [str(root / 'configured-support')]], ['pdk_root', [str(root / 'configured-pdk')]],
                       ['stage_timeout_seconds', ['45']]]
        (root / 'hardcaml-workbench-asic.sexp').write_text(sexp(self.config))
        # The daemon uses Inherit_daemon, so its Dune resolves to this private wrapper.
        # with-switch runs inside the wrapper after flock acquisition, never outside it.
        wrapper = self.base / 'bin/dune'
        wrapper.write_text('#!/bin/bash\nset -euo pipefail\n'
                           'if [[ "$1" == "build" && " $* " != *" -j6 "* ]]; then exit 64; fi\n'
                           'exec flock '
                           '/tmp/opencode/workbench-fresh-prefix-build.lock ' +
                           '"' + str(HERE / 'with-switch.sh') + '" dune "$@"\n')
        wrapper.chmod(0o700)

    def start(self):
        # Wait outside the HTTP open-project timeout for another owner's shared build.
        subprocess.run(['flock', '-w', '120', '/tmp/opencode/workbench-fresh-prefix-build.lock', 'true'],
                       check=True, timeout=125)
        metadata = self.base / 'discovery/daemon.sexp'
        metadata.unlink(missing_ok=True)
        self.log = (self.base / 'daemon.log').open('ab')
        self.process = subprocess.Popen([str(self.args.daemon), '--port', '0', '--discovery-dir',
                                         str(metadata.parent), '--state-dir', str(self.base / 'state')],
            stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True,
            env=dict(os.environ, PATH=str(self.base / 'bin') + ':' + os.environ['PATH'],
                     HOME=str(self.base / 'home'), OPAMROOT=os.environ.get('OPAMROOT', str(Path.home() / '.opam')),
                     XDG_CONFIG_HOME=str(self.base / 'config'), XDG_STATE_HOME=str(self.base / 'client-state'),
                     OMP_NUM_THREADS='6', OPENROAD_THREADS='6', PYTHONDONTWRITEBYTECODE='1'))
        wait(lambda: metadata.exists() or self.process.poll() is not None, 'private daemon start')
        require(self.process.poll() is None, 'Daemon exited; see ' + str(self.base / 'daemon.log'))
        self.url = field(c.parse(metadata.read_text()), 'endpoint')
        endpoint = urlsplit(self.url)
        require(endpoint.hostname in ('127.0.0.1', 'localhost', '::1') and endpoint.port != 41735,
                'Only private loopback daemon endpoint permitted')
        self.http = Client(self.url, self.root)  # Inherit_daemon is intentional provenance coverage.
        self.histories.append(self.http.history)
        return self.http

    def stop(self):
        if self.process is not None:
            if self.process.poll() is None:
                os.killpg(self.process.pid, signal.SIGTERM)
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait(timeout=5)
            self.log.close()
            save(self.base / 'http.json', self.histories)
            self.process = None

    def events(self, kind=None):
        path = self.root / 'events.jsonl'
        values = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        return [e for e in values if kind is None or e['kind'] == kind]

    def mode(self, stage, value):
        (self.root / (stage + '-release')).unlink(missing_ok=True)
        (self.root / (stage + '-mode')).write_text(value)
        if stage == 'build':
            (self.root / 'build-trigger').write_text(str(time.time_ns()))

    def snapshot(self):
        return self.http.rpc(wait=False)

    def workflow(self, key):
        return next((w for w in field(self.snapshot(), 'workflows') if field(w, 'key') == key), None)

    def stage(self, endpoint='synthesis', only=False, expected=None):
        selected = [['flow', 'synthetic'], ['profile', 'success'], ['endpoint', endpoint], ['assignments', []]]
        snap = self.http.rpc('(Stage_fresh (selection %s) (elaboration_only %s) (expected_plan_identity %s))' %
                             (sexp(selected), str(only).lower(), sexp([] if expected is None else [expected])), wait=False)
        return field(snap, 'fresh_intent')[0]

    def launch(self, key, intent=None, **kwargs):
        intent = intent or self.stage(**kwargs)
        op = '(Launch_fresh (key %s) (intent_id %s))' % (sexp(key), sexp(field(intent, 'id')))
        self.http.rpc(op, wait=False)
        return wait(lambda: self.workflow(key), 'durable reservation ' + key)

    def done(self, key, phase='Completed'):
        def poll():
            w = self.workflow(key)
            if w and field(w, 'phase') in ('Completed', 'Failed', 'Cancelled', 'Interrupted'):
                return w
        w = wait(poll, 'terminal workflow ' + key, timeout=180)
        save(self.base / (key + '-workflow.json'), w)
        self.check(field(w, 'phase') == phase, key + ': expected ' + phase + ', got ' + field(w, 'phase') +
                   (': ' + str(field(w, 'error')) if field(w, 'phase') != phase else ''))
        return w

    def cancel(self, w):
        self.http.rpc('(Cancel_workflow %s)' % sexp(field(w, 'id')), wait=False)

    def exact(self, w, endpoint):
        prepared = field(w, 'prepared')[0]
        admitted = next(e for e in self.events('physical-admitted')
                        if e['plan_identity'] == field(prepared, 'plan_identity') and
                        e['argv'][e['argv'].index('--workspace') + 1] in field(field(w, 'reference')[0], 'attempt'))
        plan_path = Path(field(prepared, 'methodology_plan_path'))
        raw = plan_path.read_bytes()
        plan = json.loads(raw)
        receipt = next(json.loads(Path(e['receipt']).read_text()) for e in self.events('emit-finished')
                       if e['plan_identity'] == admitted['plan_identity'])
        self.check(admitted['argv'][1] == field(prepared, 'bundle_directory') == receipt['output_dir'] and
                   admitted['bundle_identity'] == field(prepared, 'bundle_identity') == receipt['bundle_identity'] and
                   admitted['plan_identity'] == field(prepared, 'plan_identity') == receipt['plan_identity'] and
                   plan == receipt['plan'] and admitted['plan_sha256'] == hashlib.sha256(raw).hexdigest() ==
                   field(prepared, 'methodology_plan_digest'),
                   field(w, 'key') + ': direct provider consumes exact receipt bundle, plan bytes/digest and identity')
        prefix = ['synthesis', 'floorplan', 'placement', 'cts'][:1 if endpoint == 'synthesis' else 4]
        self.check(admitted['stages'] == prefix, field(w, 'key') + ': exact physical prefix ' + str(prefix))
        build, emission = field(w, 'build_job')[0], field(w, 'emission_job')[0]
        def timestamp(job, key):
            return datetime.fromisoformat(field(job, key)[0]).timestamp()
        self.check(field(build, 'state') == 'Complete' and field(emission, 'state') == 'Complete' and
                   field(w, 'preparation_id') and field(w, 'elaboration_status') == 'completed' and
                   field(w, 'elaboration_started_at') and field(w, 'elaboration_finished_at') and
                   timestamp(build, 'finished_at') <= timestamp(emission, 'started_at') <=
                   timestamp(emission, 'finished_at') <= admitted['time_ns'] / 1e9,
                   field(w, 'key') + ': own completed source jobs, build-before-emit-before-provider timing and durable lineage')
        emit_event = next(e for e in self.events('emit-finished') if e['plan_identity'] == admitted['plan_identity'])
        self.check(emit_event['time_ns'] < admitted['time_ns'], 'Emission receipt precedes physical admission')


def http_acceptance(f):
    check = f.check
    try:
        f.start()
        # A genuine pinned preview with the exact selection must differ from fresh source.
        selected = [['flow', 'synthetic'], ['profile', 'success'], ['endpoint', 'synthesis'], ['assignments', []]]
        f.http.rpc('(Plan %s)' % sexp(selected), wait=False)
        preview = wait(lambda: next(iter(field(f.snapshot(), 'preview')), None), 'pinned preview')
        f.launch('synthesis')
        synth = f.done('synthesis')
        f.exact(synth, 'synthesis')
        check(field(field(synth, 'prepared')[0], 'plan_identity') != field(preview, 'plan_identity'),
              'Fresh source plan differs from same-selection pinned preview; no implicit pinned guard')
        counts = [len(f.events(k)) for k in ('emit-start', 'physical-admitted')]
        replay = f.launch('synthesis', field(synth, 'intent'))
        check(replay == synth and counts == [len(f.events(k)) for k in ('emit-start', 'physical-admitted')],
              'Same-key replay returns exact workflow without producer replay')
        for key, intent in [('different-key-consumed', field(synth, 'intent')), ('synthesis', f.stage())]:
            try:
                f.launch(key, intent)
            except RuntimeError as error:
                check(('Conflict' in str(error) or 'Invalid_request' in str(error)) and any(
                    reason in str(error).lower() for reason in ('superseded', 'consumed', 'different', 'used')),
                    'Consumed intent/conflicting key explicitly rejects: ' + key)
            else:
                raise AssertionError('Conflicting or consumed intent accepted: ' + key)
        scope = field(field(synth, 'intent'), 'scope')
        check('Inherit_daemon' in scope and all(str(f.root / name) in scope for name in
              ('configured-python', 'configured-support', 'configured-pdk', 'provider', 'pinned')),
              'Inherited daemon environment and configured tool/provider paths captured in workflow provenance')
        f.launch('cts', endpoint='cts')
        cts = f.done('cts')
        f.exact(cts, 'cts')
        f.launch('repeat')
        repeated = f.done('repeat')
        check(field(repeated, 'id') != field(synth, 'id') and
              field(repeated, 'preparation_id') != field(synth, 'preparation_id') and
              field(field(repeated, 'build_job')[0], 'id') != field(field(synth, 'build_job')[0], 'id') and
              len(f.events('emit-start')) == 3 and f.events('emit-finished')[-1]['reused'],
              'Distinct fresh submission builds/emits again even with reused identical publication')
        physical_count = len(f.events('physical-admitted'))
        f.launch('standalone', only=True)
        standalone = f.done('standalone')
        check(not field(standalone, 'run') and not field(standalone, 'reference') and
              len(f.events('physical-admitted')) == physical_count and len(f.events('emit-start')) == 4,
              'Standalone Elaboration completes source build/emission with zero physical admission')
        (f.root / 'generation').write_text('generation-2')
        f.launch('changed-source')
        changed = f.done('changed-source')
        f.exact(changed, 'synthesis')
        check(field(field(changed, 'prepared')[0], 'plan_identity') !=
              field(field(synth, 'prepared')[0], 'plan_identity') and
              field(field(changed, 'prepared')[0], 'bundle_identity') !=
              field(field(synth, 'prepared')[0], 'bundle_identity'),
              'New source execution captures new generated bundle/plan bytes without a pinned preview guard')
        physical_count = len(f.events('physical-admitted'))
        for stage, mode, key in [('build', 'fail', 'build-failure'), ('emit', 'fail', 'emit-failure'),
                                 ('emit', 'malformed', 'receipt-failure')]:
            f.mode(stage, mode)
            f.launch(key)
            failed = f.done(key, 'Failed')
            check(field(failed, 'error') and not field(failed, 'run') and
                  len(f.events('physical-admitted')) == physical_count,
                  key + ': diagnostic and no downstream physical work')
            f.mode(stage, 'success')
        f.launch('mismatch', expected=field(preview, 'plan_identity'))
        failed = f.done('mismatch', 'Failed')
        check('mismatch' in str(field(failed, 'error')).lower() and not field(failed, 'prepared') and
              len(f.events('physical-admitted')) == physical_count,
              'Explicit expected pinned identity remains strict and blocks physical admission')
        for stage in ('build', 'emit'):
            f.mode(stage, 'hold')
            old = len(f.events(stage + '-held'))
            key = 'cancel-' + stage
            w = f.launch(key)
            wait(lambda: len(f.events(stage + '-held')) > old, stage + ' producer held')
            active = f.workflow(key)
            counts = [len(f.events(k)) for k in ('build-start', 'emit-start', 'physical-admitted')]
            replay = f.launch(key, field(w, 'intent'))
            check(all(field(replay, k) == field(active, k) for k in ('id', 'preparation_id', 'build_job', 'emission_job')) and
                  counts == [len(f.events(k)) for k in ('build-start', 'emit-start', 'physical-admitted')],
                  'Active ' + stage + ' same-key replay retains exact attempt/jobs and starts no new producer')
            f.cancel(w)
            cancelled = f.done(key, 'Cancelled')
            wait(lambda: f.events(stage + '-stopped'), stage + ' owned producer stopped')
            (f.root / (stage + '-release')).write_text('release')
            f.mode(stage, 'success')
            check(field(cancelled, 'cancel_requested') == 'true' and not field(cancelled, 'run') and
                  len(f.events('physical-admitted')) == physical_count,
                  key + ': cancellation latches, owned producer stops, no physical handoff')
        # Source-root queue: second workflow must not start build/emission while first holds lease.
        f.mode('emit', 'hold')
        old = len(f.events('emit-held'))
        blocker = f.launch('source-blocker')
        wait(lambda: len(f.events('emit-held')) > old, 'source lease held')
        builds = len(f.events('build-start'))
        queued = f.launch('cancel-source-queue')
        wait(lambda: field(f.workflow('cancel-source-queue'), 'phase') == 'Building', 'queued workflow admitted to source wait')
        check(not field(f.workflow('cancel-source-queue'), 'build_job') and len(f.events('build-start')) == builds,
              'Source-root lease keeps queued workflow from starting a build')
        f.cancel(queued)
        f.done('cancel-source-queue', 'Cancelled')
        f.cancel(blocker)
        f.done('source-blocker', 'Cancelled')
        f.mode('emit', 'success')
        check(len(f.events('physical-admitted')) == physical_count, 'Cancelled source queue cannot later launch physical work')
        (f.root / 'hold-physical').touch()
        w = f.launch('cancel-physical')
        wait(lambda: field(f.workflow('cancel-physical'), 'run'), 'physical allocation')
        admitted = len(f.events('physical-admitted'))
        queued = f.launch('cancel-physical-queue', endpoint='cts')
        wait(lambda: field(f.workflow('cancel-physical-queue'), 'phase') == 'Physical', 'queued physical workflow')
        check(not field(f.workflow('cancel-physical-queue'), 'run') and
              field(f.workflow('cancel-physical-queue'), 'prepared'),
              'Queued physical workflow has its own completed preparation and no allocation')
        f.cancel(queued)
        f.cancel(w)
        f.done('cancel-physical-queue', 'Cancelled')
        f.done('cancel-physical', 'Cancelled')
        wait(lambda: (f.root / 'physical-stopped').exists(), 'physical owned cleanup')
        check((f.root / 'physical-stopped').read_text() == field(field(f.workflow('cancel-physical'), 'reference')[0], 'stream_id'),
              'Physical cancellation stops the exact allocated synthetic stream')
        check(len(f.events('physical-admitted')) == admitted and not field(f.workflow('cancel-physical-queue'), 'run'),
              'Cancelling queued physical handoff never starts its provider after throttle release')
        (f.root / 'hold-physical').unlink()
        # Capture fences: literal inherited ASIC config and provider bytes are provenance.
        for kind in ('config', 'provider'):
            intent = f.stage()
            path = f.root / ('hardcaml-workbench-asic.sexp' if kind == 'config' else 'provider')
            original = path.read_bytes()
            path.write_bytes(original.replace(b'"45"', b'"44"') if kind == 'config'
                             else original + b'\n# generation drift\n')
            try:
                try:
                    f.launch('drift-' + kind, intent)
                except RuntimeError as error:
                    check(('Conflict' in str(error) or 'Invalid_request' in str(error)) and
                          ('changed' in str(error) or 'scope' in str(error)),
                          kind + ' drift explicitly rejects captured scope')
                else:
                    raise AssertionError(kind + ' drift was accepted')
            finally:
                path.write_bytes(original)
        # Failed staging invalidates old unlaunched intent, and missing prep cannot bypass.
        prep = f.root / 'hardcaml-workbench-preparation.sexp'
        original = prep.read_bytes()
        prep.unlink()
        try:
            try:
                f.stage()
            except RuntimeError as error:
                check('preparation' in str(error).lower() or 'configured' in str(error).lower(),
                      'Missing preparation configuration explicitly rejects fresh staging')
            else:
                raise AssertionError('Missing preparation configuration accepted')
        finally:
            prep.write_bytes(original)
        check(not any(e['argv'][:2] == ['flow', 'run'] for e in f.events('pinned-call')),
              'Every physical submission bypasses pinned project flow run')
        before = f.snapshot()
        counts = [len(f.events(k)) for k in ('build-start', 'emit-start', 'physical-admitted')]
        f.stop()
        f.start()
        restored = f.snapshot()
        for old in (synth, cts, standalone, failed):
            w = f.workflow(field(old, 'key'))
            check(all(field(w, k) == field(old, k) for k in
                      ('id', 'intent', 'phase', 'prepared', 'preparation_id', 'run', 'reference',
                       'elaboration_status', 'elaboration_started_at', 'elaboration_finished_at')) and
                  not field(w, 'build_job') and not field(w, 'emission_job'),
                  field(old, 'key') + ': restart retains own durable facts and clears session handles')
        f.launch('synthesis', field(synth, 'intent'))
        check(counts == [len(f.events(k)) for k in ('build-start', 'emit-start', 'physical-admitted')],
              'Private restart/read/same-key replay starts no source or physical producer')
        check(field(f.workflow('synthesis'), 'preparation_id') != field(f.workflow('standalone'), 'preparation_id') and
              field(f.workflow('synthesis'), 'run') == field(synth, 'run'),
              'Later standalone/failures preserve older physical run lineage')
        save(f.base / 'before-restart.json', before)
        save(f.base / 'after-restart.json', restored)
        # Abrupt daemon loss, followed by cleanup of the precise fixture producer.
        f.mode('emit', 'hold')
        held_before = len(f.events('emit-held'))
        interrupted = f.launch('crash-emitting')
        wait(lambda: len(f.events('emit-held')) > held_before, 'emission held before crash')
        producer = f.events('emit-held')[-1]
        counts = [len(f.events(k)) for k in ('build-start', 'emit-start', 'physical-admitted')]
        f.process.kill()
        f.process.wait(timeout=10)
        f.stop()
        require(producer['pgid'] != os.getpgrp() and producer['pid'] != os.getpid(), 'Owned fixture producer group')
        try:
            os.killpg(producer['pgid'], signal.SIGTERM)
        except ProcessLookupError:
            pass
        f.start()
        w = f.done('crash-emitting', 'Interrupted')
        f.launch('crash-emitting', field(interrupted, 'intent'))
        f.cancel(w)  # historical cancellation has no new ownership
        check(field(f.workflow('crash-emitting'), 'phase') == 'Interrupted' and
              counts == [len(f.events(k)) for k in ('build-start', 'emit-start', 'physical-admitted')],
              'Unclean restart marks interrupted producer explicitly; replay and cancel never relaunch it')
    finally:
        if f.process is not None and f.process.poll() is None and hasattr(f, 'http'):
            save(f.base / 'final-snapshot.json', f.snapshot())
        f.stop()


def pty_acceptance(f):
    """Actual keyboard dispatcher plus independent native RPC/provider assertions."""
    t = None
    try:
        f.start()
        f.http.rpc('Discover', wait=False)
        wait(lambda: field(f.snapshot(), 'flows'), 'PTY flow catalog')
        presets = c.demo.workspace_presets(f.args.preset_export)
        registry = c.demo.ensure_workspaces(f.http, f.http.rpc(domain='workspace'), presets)
        registry = c.demo.apply_workspace_presets(f.http, registry, presets)
        overview = next(w for w in field(registry, 'workspaces') if field(w, 'preset') == ['overview'])
        registry = f.http.mutate(registry, '(Create_tile (workspace %s) (kind planned-run) '
                                 '(geometry ((x 0) (y 56) (width 100) (height 18))))' % sexp(field(overview, 'id')))
        planned_tile = field(field(registry, 'tiles')[-1], 'id')
        tiles_before = field(registry, 'tiles')
        config_before = (f.root / 'hardcaml-workbench-asic.sexp').read_bytes()
        reference = [['attempt', str(f.base / 'results/synthetic-reference')], ['stream_id', 'synthetic-reference']]
        f.http.rpc('(Register %s)' % sexp(reference), wait=False)
        historical = wait(lambda: next(iter(field(f.snapshot(), 'runs')), None), 'historical registration')
        f.http.rpc('(Observe %s)' % sexp(field(historical, 'run')), wait=False)
        wait(lambda: any(field(r, 'stages') for r in field(f.snapshot(), 'runs')), 'historical stages')
        overview = next(w for w in field(registry, 'workspaces') if field(w, 'preset') == ['overview'])
        context = next(x for x in field(registry, 'contexts') if field(x, 'id') == field(overview, 'context'))
        f.http.mutate(registry, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' %
                      (sexp(field(overview, 'id')), sexp(field(context, 'id')), field(context, 'selection_revision'),
                       sexp(field(historical, 'run'))))
        # Composition's PTY oracle defaults to opam selection. Explicitly exercise
        # inherited daemon provenance here so nested builds keep the locked Dune wrapper.
        client_wrapper = f.base / 'inherited-client'
        client_wrapper.write_text('#!' + sys.executable + '\nimport os,sys\na=sys.argv[1:]\n'
                                  'a[a.index("--environment")+1]="inherited"\nos.execv(' +
                                  repr(str(f.args.client)) + ', [' + repr(str(f.args.client)) + '] + a)\n')
        client_wrapper.chmod(0o700)
        args = SimpleNamespace(client=client_wrapper)
        t = c.Terminal(f.base, args, f.url, 180, 55)
        t.capture('pty-initial', ['stage checklist'])
        t.capture('pty-historical-unlinked', ['Elaboration:', 'unavailable'])
        f.check(not any(field(w, 'run') == [field(historical, 'run')] for w in field(f.snapshot(), 'workflows')),
                'Historical run without preparation linkage displays Elaboration unavailable')

        def checklist(index):
            t.command('Unzoom workspace')
            t.focus_view('stage checklist')
            t.command('Zoom focused tile')
            t.key(b'k' * 15)
            t.key(b'j' * index)

        def new_workflow(before):
            return wait(lambda: next((w for w in field(f.snapshot(), 'workflows')
                        if field(w, 'id') not in before), None), 'PTY daemon-owned workflow')

        def ids():
            return {field(w, 'id') for w in field(f.snapshot(), 'workflows')}

        def selected_run():
            t.drain(.05)
            ws = f.http.rpc(domain='workspace')
            overview = next(w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview'])
            return field(next(x for x in field(ws, 'contexts') if field(x, 'id') == field(overview, 'context')), 'selected_run')

        # Manual r must only capture input intent. Launch is a separate palette action.
        checklist(1)
        before = ids()
        f.mode('emit', 'hold')
        t.key(b'r')
        intent = wait(lambda: next(iter(field(f.snapshot(), 'fresh_intent')), None), 'PTY manual input intent')
        f.check(not field(intent, 'expected_plan_identity') and not f.events('emit-start') and ids() == before,
                'Real checklist r stages unpinned source inputs without a producer')
        t.command('Unzoom workspace')
        ws = f.http.rpc(domain='workspace')
        f.http.mutate(ws, '(Set_zoom (workspace %s) (tile (%s)))' %
                      (sexp(field(overview, 'id')), sexp(planned_tile)))
        t.capture('pty-manual-source-intent', ['Fresh launch:', 'source build'])
        t.command('Launch and view planned run')
        manual = new_workflow(before)
        wait(lambda: f.events('emit-held'), 'PTY manual emission held')
        t.capture('pty-manual-preallocation', ['Elaboration: emitting', field(manual, 'id'), field(manual, 'key')])
        f.check(not field(f.workflow(field(manual, 'key')), 'run') and not f.events('physical-admitted'),
                'Real UI shows workflow Elaboration while no physical allocation exists')
        (f.root / 'emit-release').write_text('release')
        manual = f.done(field(manual, 'key'))
        f.exact(manual, 'synthesis')
        wait(lambda: selected_run() == field(manual, 'run'), 'manual guarded launch-and-view')
        checklist(1)
        t.capture('pty-manual-completed', ['Elaboration:', 'completed', 'Synthesis:'])
        f.mode('emit', 'success')

        for route, endpoint in [('checklist-R', 'cts'), ('named-palette', 'synthesis'), ('selected-palette', 'cts')]:
            checklist(4 if endpoint == 'cts' else 1)
            before = ids()
            emissions, physical = len(f.events('emit-start')), len(f.events('physical-admitted'))
            if route == 'checklist-R':
                t.key(b'R')
            elif route == 'named-palette':
                t.type_action('launch syn', 'Launch synthesis and view', 'pty-named-action')
            else:
                t.type_action('quick lau', 'Quick launch selected stage', 'pty-selected-action')
            w = new_workflow(before)
            w = f.done(field(w, 'key'))
            f.exact(w, endpoint)
            wait(lambda: selected_run() == field(w, 'run'), route + ' exact linked selected run')
            t.capture('pty-' + route + '-completed', ['Elaboration:', 'completed', 'Synthesis:', 'CTS:'])
            f.check(len(ids() - before) == 1 and field(field(w, 'intent'), 'selection') ==
                    [['flow', 'synthetic'], ['profile', 'success'], ['endpoint', endpoint], ['assignments', []]] and
                    len(f.events('emit-start')) == emissions + 1 and len(f.events('physical-admitted')) == physical + 1,
                    route + ': keyboard dispatch starts exactly one fresh chain for exact selected endpoint')
        linked = w
        selected = selected_run()
        # Preserve the standalone fix through the real dispatcher with an EXACT
        # same-selection pinned preview, rather than testing only eligibility.
        standalone_selection = field(field(linked, 'intent'), 'selection')
        f.http.rpc('(Plan %s)' % sexp(standalone_selection), wait=False)
        pinned_preview = wait(lambda: next(iter(field(f.snapshot(), 'preview')), None), 'same-selection standalone pinned preview')
        f.check(field(pinned_preview, 'selection') == standalone_selection,
                'Standalone frontend regression has an exact same-selection pinned ASIC preview')
        before, physical = ids(), len(f.events('physical-admitted'))
        t.command('Launch elaboration bundle')
        standalone_success = new_workflow(before)
        standalone_success = f.done(field(standalone_success, 'key'))
        f.check(field(field(standalone_success, 'intent'), 'selection') == standalone_selection and
                not field(field(standalone_success, 'intent'), 'expected_plan_identity') and
                field(field(standalone_success, 'prepared')[0], 'plan_identity') != field(pinned_preview, 'plan_identity') and
                not field(standalone_success, 'run') and selected_run() == selected and
                len(f.events('physical-admitted')) == physical,
                'Real standalone dispatcher builds fresh source without borrowing same-selection pinned preview or allocating physical work')
        t.capture('pty-standalone-same-selection-pinned-preview', ['Elaboration:', 'completed'])
        # A later standalone failure must not relabel the selected physical run.
        f.mode('emit', 'fail')
        before = ids()
        count = len(f.events('physical-admitted'))
        t.command('Launch elaboration bundle')
        w = new_workflow(before)
        standalone = f.done(field(w, 'key'), 'Failed')
        t.capture('pty-selected-run-lineage-after-standalone-failure', ['Elaboration:', 'completed'])
        f.check(field(field(standalone, 'intent'), 'elaboration_only') == 'true' and not field(standalone, 'run') and
                selected_run() == selected == field(linked, 'run') and len(f.events('physical-admitted')) == count,
                'Later standalone failure retains context and older selected run completed Elaboration linkage')
        # UI cancellation before provider allocation, addressed by actual workflow command.
        f.mode('emit', 'hold')
        before = ids()
        checklist(1)
        held = len(f.events('emit-held'))
        t.key(b'R')
        w = new_workflow(before)
        wait(lambda: len(f.events('emit-held')) > held, 'PTY cancellable emission')
        t.command('Cancel fresh workflow ' + field(w, 'key'))
        cancelled = f.done(field(w, 'key'), 'Cancelled')
        f.check(field(cancelled, 'cancel_requested') == 'true' and not field(cancelled, 'run') and
                len(f.events('physical-admitted')) == count,
                'Real palette workflow cancellation latches before allocation and blocks synthesis')
        pinned_calls = f.events('pinned-call')
        f.check(not any(e['argv'][:2] == ['flow', 'run'] for e in pinned_calls) and
                sum(e['argv'][:2] == ['flow', 'plan'] for e in pinned_calls) == 1,
                'Every fresh PTY route uses input intent; only the deliberate regression preview calls pinned Plan, never flow run')
        t.capture('pty-final-evidence', ['Elaboration:', 'completed'])
        # Context focus fence: let the daemon finish, but never steal the user's new selection.
        checklist(1)
        before, held = ids(), len(f.events('emit-held'))
        t.key(b'R')
        w = new_workflow(before)
        wait(lambda: len(f.events('emit-held')) > held, 'held focus-fence emission')
        ws = f.http.rpc(domain='workspace')
        overview = next(x for x in field(ws, 'workspaces') if field(x, 'preset') == ['overview'])
        context = next(x for x in field(ws, 'contexts') if field(x, 'id') == field(overview, 'context'))
        f.http.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run ()))' %
                      (sexp(field(overview, 'id')), sexp(field(context, 'id')), field(context, 'selection_revision')))
        t.capture('pty-focus-changed-before-allocation', ['Run: none selected'])
        (f.root / 'emit-release').write_text('release')
        w = f.done(field(w, 'key'))
        t.capture('pty-focus-guarded-after-completion', ['Run: none selected'])
        f.check(not selected_run() and field(w, 'run'),
                'Real async launch finishes its captured workflow without stealing a changed selected-run context')
        final_workspace = f.http.rpc(domain='workspace')
        f.check(field(final_workspace, 'tiles') == tiles_before and
                (f.root / 'hardcaml-workbench-asic.sexp').read_bytes() == config_before,
                'Fresh UI routes preserve saved tile membership/bindings and configured provider/tool selections')
        save(f.base / 'final-workspace.json', final_workspace)
    finally:
        if t is not None:
            t.close()
        if f.process is not None and f.process.poll() is None and hasattr(f, 'http'):
            save(f.base / 'final-snapshot.json', f.snapshot())
        f.stop()


def no_asic_acceptance(f):
    try:
        (f.root / 'hardcaml-workbench-asic.sexp').unlink()
        f.start()
        f.launch('source-only', only=True)
        w = f.done('source-only')
        f.check(field(f.snapshot(), 'configured') == 'false' and field(w, 'prepared') and
                not field(w, 'run') and not f.events('provider-call') and not f.events('pinned-call'),
                'Elaboration-only works with inherited environment and preparation config but no ASIC/provider companion')
    finally:
        f.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--daemon', type=Path, required=True)
    parser.add_argument('--client', type=Path)
    parser.add_argument('--preset-export', type=Path)
    parser.add_argument('--http-only', action='store_true', help='partial backend acceptance; PTY not claimed')
    parser.add_argument('--pty-only', action='store_true', help='partial frontend diagnostic; HTTP matrix not repeated')
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    for name in ('daemon', 'client', 'preset_export'):
        if getattr(args, name):
            setattr(args, name, getattr(args, name).resolve(strict=True))
    if args.http_only and args.pty_only:
        parser.error('--http-only and --pty-only are mutually exclusive')
    if not args.http_only and (not args.client or not args.preset_export):
        parser.error('--client and --preset-export are required for PTY acceptance')
    args.evidence = (args.evidence or Path('/tmp/opencode') / ('unified-fresh-prefix-' + secrets.token_hex(6))).resolve()
    require(args.evidence.is_relative_to('/tmp/opencode'), 'Private /tmp/opencode evidence required')
    os.umask(0o077)
    args.evidence.mkdir(exist_ok=False)
    coverage = 'HTTP-only (partial)' if args.http_only else 'PTY-only (partial)' if args.pty_only else 'HTTP + PTY'
    result = dict(status='failed', coverage=coverage, checks=[], evidence=str(args.evidence),
                  binaries={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (args.daemon, args.client, args.preset_export) if p},
                  fixture_sha256={str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (Path(__file__), HERE / 'fixtures/unified_fresh_prefix.py',
                                            REPO / 'backend/test/fresh_provider.py',
                                            REPO / 'demo/synthetic_flow/provider.py')})
    def check(ok, message):
        result['checks'].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)
    print('Evidence: ' + str(args.evidence), flush=True)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Fresh-prefix acceptance budget exhausted')))
    signal.alarm(args.timeout)
    try:
        if not args.pty_only:
            http_acceptance(Fixture(args, 'http', check))
            no_asic_acceptance(Fixture(args, 'source-only', check))
        if not args.http_only:
            pty_acceptance(Fixture(args, 'pty', check))
        result['status'] = 'passed'
    except BaseException:
        result['error'] = traceback.format_exc()
        raise
    finally:
        signal.alarm(0)
        save(args.evidence / 'result.json', result)
    print('PASS ' + coverage + ' fresh-prefix: ' + str(len(result['checks'])) + ' assertions; ' + str(args.evidence))


if __name__ == '__main__':
    main()
