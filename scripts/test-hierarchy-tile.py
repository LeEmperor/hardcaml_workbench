#!/usr/bin/env python3
"""WB-007 real native HTTP/PTY acceptance; existing binaries only, no builds/EDA.

Run with --daemon PATH --client PATH. All state, HOME, Dune/driver stand-ins,
loopback servers, jobs and transcripts belong to a new /tmp/opencode directory.
Explicit setup generations replay tiny structural records patterned on the existing
example_project driver. Browsing must neither submit jobs nor invoke that driver.
HTTP observations prove equivalent in-flight read reuse and delayed reply fencing.
Synthetic structural evidence does not establish a real provider's tested-DUT map.
--self-test checks fixture protocol and the HTTP gate without native binaries.
"""
import argparse
import fcntl
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import traceback
import urllib.error
import urllib.request

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


native = load('hierarchy_native', HERE / 'test-fs0.py')
pty_harness = load('hierarchy_pty', HERE / 'test-inspector-latency.py')
wire = load('hierarchy_http', HERE.parent / 'demo/synthetic_flow/http_client.py')
fixture = load('hierarchy_fixture', HERE / 'fixtures/hierarchy_tile_driver.py')
field, sexp, require = wire.field, wire.sexp, native.require


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


class HierarchyProxy:
    """Observe real requests and hold one real read reply, never manufacture UI data.

Adapted from test-embedded-waveform.py's DelayedBytesProxy. Request admission is
recorded *before* forwarding, so a duplicate cannot hide behind a held response.
"""
    def __init__(self, upstream, evidence):
        self.upstream, self.evidence = upstream, evidence
        self.lock, self.records, self.gates = threading.Lock(), [], []
        self.pending = None
        proxy = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *_):
                pass

            def do_GET(self):
                self.forward()

            def do_POST(self):
                self.forward()

            def forward(self):
                data = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                gate = None
                with proxy.lock:
                    record = dict(method=self.command, path=self.path,
                                  request=data.decode(), admitted=time.monotonic())
                    proxy.records.append(record)
                    if self.path == '/api/v1/read-hierarchy' and proxy.pending:
                        gate, proxy.pending = proxy.pending, None
                        gate['request'] = wire.parse(data.decode())
                        record['gate'] = gate['label']
                try:
                    request = urllib.request.Request(proxy.upstream + self.path,
                        data=data if self.command == 'POST' else None, method=self.command,
                        headers={k: v for k, v in self.headers.items()
                                 if k.lower() not in ('host', 'connection', 'content-length')})
                    try:
                        response = urllib.request.urlopen(request, timeout=20)
                    except urllib.error.HTTPError as error:
                        response = error
                    with response:
                        payload, status = response.read(), response.status
                        content_type = response.headers.get('Content-Type', 'application/sexp')
                    record.update(status=status, response_sha256=hashlib.sha256(payload).hexdigest(),
                                  buffered=time.monotonic())
                    if gate:
                        gate['ready'].set()
                        require(gate['release'].wait(30), 'Delayed hierarchy gate expired')
                        if gate.get('malformed_response'):
                            payload = b'('
                            record['fault_injection'] = 'malformed S-expression after real upstream read'
                    self.send_response(status)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Length', str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    self.wfile.flush()
                    record['delivered'] = time.monotonic()
                except (BrokenPipeError, ConnectionResetError):
                    record['disconnected'] = True
                except Exception:
                    record['error'] = traceback.format_exc()
                    self.close_connection = True
                finally:
                    if gate:
                        gate['delivered'].set()

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:%d' % self.server.server_port

    def arm(self, label):
        gate = dict(label=label, ready=threading.Event(), release=threading.Event(),
                    delivered=threading.Event())
        with self.lock:
            require(self.pending is None, 'Previous read gate not captured')
            self.pending = gate
            self.gates.append(gate)
        return gate

    def reads(self, artifact=None):
        with self.lock:
            return [r.copy() for r in self.records if r['path'] == '/api/v1/read-hierarchy'
                    and (artifact is None or field(wire.parse(r['request']), 'artifact') == artifact)]

    def close(self):
        for gate in self.gates:
            gate['release'].set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        save(self.evidence / 'http-proxy.json', dict(requests=self.records,
            gates=[{k: v.is_set() if isinstance(v, threading.Event) else v
                    for k, v in gate.items()} for gate in self.gates]))


class Terminal(pty_harness.Terminal):
    def palette(self):
        self.ready()
        for key in (b' ', b'c', b'c'):
            self.press(key)
        self.capture('palette-open-' + str(self.offset), ['COMMAND PALETTE'])

    def capture(self, label, expected=(), absent=()):
        return self.wait(lambda text: all(s.casefold() in text.casefold() for s in expected)
                         and all(s.casefold() not in text.casefold() for s in absent), label)

    def command(self, title):
        self.palette()
        self.key(title.encode())
        self.capture('palette-' + str(self.offset), [title], ['No matching commands'])
        # Query edits retain old command identity: explicitly select first match.
        self.key(b'\x1b[A' * 60)
        self.idle(.1)
        self.key(b'\r')
        self.capture('command-' + str(self.offset), absent=['COMMAND PALETTE'])
        self.idle(.3)

    def press(self, key):
        self.key(key)
        self.idle(.3)

    def resize(self, width, height):
        self.idle(.1)
        self.screen = pty_harness.Screen(width, height)
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
        os.kill(self.process.pid, signal.SIGWINCH)
        self.idle(.5)


class Acceptance:
    def __init__(self, args, result):
        self.args, self.result, self.base = args, result, args.evidence
        self.session = self.proxy = self.t = self.http = None
        self.generation = 0
        self.hierarchy_capable = True
        self.expected_jobs = set()

    def check(self, ok, message):
        self.result['checks'].append(dict(passed=bool(ok), expectation=message))
        save(self.base / 'result.json', self.result)
        require(ok, message)

    def wait(self, predicate, label, timeout=20):
        deadline = time.monotonic() + timeout
        while True:
            value = predicate()
            if value:
                return value
            if self.t:
                self.t.idle(.05)
            else:
                time.sleep(.05)
            require(time.monotonic() < deadline, 'Timeout: ' + label)

    def snapshot(self):
        return self.http.raw('/api/v1/snapshot', [['instance_id', self.http.instance]])

    def project(self):
        return next(p for p in field(self.snapshot(), 'projects') if field(p, 'id') == self.http.project)

    def jobs(self):
        return field(self.snapshot(), 'jobs')

    def counts(self):
        calls = self.base / 'driver-calls.jsonl'
        return dict(jobs=sorted(field(j, 'id') for j in self.jobs()),
                    driver=calls.read_text().splitlines() if calls.exists() else [])

    def quiet(self, before, label):
        self.t.idle(.5)
        self.check(self.counts() == before, label + ': no new jobs or driver/tool invocations')

    def generate(self, mode='valid', configuration='four-bit', target='counter', wait=True):
        self.generation += 1
        save(self.base / 'control.json', dict(mode=mode, generation='generation-%d' % self.generation))
        (self.base / 'release-generation').unlink(missing_ok=True)
        if self.hierarchy_capable != (mode != 'unsupported'):
            self.hierarchy_capable = mode != 'unsupported'
            response = self.http.raw('/api/v1/refresh-integration', [
                ['instance_id', self.http.instance], ['project', self.http.project]])
            discovery = field(field(response, 'job')[0], 'id')
            self.expected_jobs.add(discovery)
            self.wait(lambda: any(field(j, 'id') == discovery and field(j, 'state') == 'Complete'
                                  for j in self.jobs()), 'fixture capability refresh')
        project = self.project()
        tid = next(field(t, 'id') for t in field(project, 'targets') if field(t, 'id').endswith('/' + target))
        cid = next(field(c, 'id') for c in field(project, 'configurations') if field(c, 'id').endswith('/' + configuration))
        response = self.http.raw('/api/v1/generate-rtl', [
            ['instance_id', self.http.instance], ['project', self.http.project],
            ['target', tid], ['configuration', cid], ['submission_key', 'acceptance-%d' % self.generation]])
        job = field(response, 'job')
        jid = field(job, 'id')
        self.expected_jobs.add(jid)
        if wait:
            job = self.wait(lambda: next((j for j in self.jobs() if field(j, 'id') == jid
                            and field(j, 'state') in ('Complete', 'Failed', 'Cancelled')), None), jid)
            self.check(field(job, 'state') == ('Failed' if mode in ('failed', 'malformed') else 'Complete'),
                       'Explicit setup generation reaches expected state: ' + mode)
            # Setup uses an independent HTTP client. Let the terminal's ordinary
            # 500ms update poll acquire that generation before sending explicit r;
            # otherwise r legitimately captures the previously observed latest job.
            if self.t:
                self.t.idle(1.2)
        save(self.base / ('generation-%d.json' % self.generation), dict(mode=mode, job=job))
        return job

    def artifact(self, job):
        return next(a for a in field(self.snapshot(), 'artifacts')
                    if field(a, 'generating_job') == field(job, 'id')
                    and field(field(a, 'kind'), 'name') == 'elaboration-hierarchy')

    def setup(self):
        for name in ('project', 'state', 'home', 'config', 'cache', 'tmp', 'bin'):
            (self.base / name).mkdir(mode=0o700)
        root = self.base / 'project'
        (root / 'dune-project').write_text('(lang dune 3.22)\n(name hierarchy_acceptance)\n')
        (root / 'hardcaml-workbench.sexp').write_text(
            '(lang hardcaml-workbench 1)\n(project (name hierarchy-acceptance))\n'
            '(dune (driver ./hierarchy-driver.exe))\n')
        # Private adapter boundary: no real Dune command is ever executed. The
        # production adapter's -j20 is merely logged by this serial Python shim.
        driver = self.base / 'bin/dune'
        driver.write_text('#!' + sys.executable + '\n' + (HERE / 'fixtures/hierarchy_tile_driver.py').read_text())
        driver.chmod(0o700)
        session = self.session = native.Session(self.args, self.base, root)
        session.deadline = self.args.deadline
        session.env.update(HOME=str(self.base / 'home'), XDG_CONFIG_HOME=str(self.base / 'config'),
            XDG_CACHE_HOME=str(self.base / 'cache'), TMPDIR=str(self.base / 'tmp'),
            HIERARCHY_FIXTURE_BASE=str(self.base), PYTHONDONTWRITEBYTECODE='1',
            PATH=str(self.base / 'bin') + os.pathsep + os.environ.get('PATH', ''),
            OMP_NUM_THREADS='1', OPENROAD_THREADS='1', _OPENLANE_MAX_CORES='1')
        session.start()
        self.proxy = HierarchyProxy(session.url, self.base)
        self.http = wire.Client(self.proxy.url, root)
        self.wait(lambda: len(field(self.project(), 'targets')) == 2, 'driver discovery')
        self.wait(lambda: all(field(j, 'state') in ('Complete', 'Failed', 'Cancelled') for j in self.jobs()), 'discovery idle')
        self.check(all(field(j, 'state') == 'Complete' for j in self.jobs()), 'Native project discovery completes')
        self.expected_jobs.update(field(j, 'id') for j in self.jobs())
        registry = self.http.rpc(domain='workspace')
        self.check(not any(field(t, 'kind') == 'hierarchy' for t in field(registry, 'tiles')),
                   'Hierarchy is opt-in: absent from fresh default workspace')
        window = field(field(registry, 'windows')[0], 'id')
        registry = self.http.mutate(registry, '(Create_workspace (window %s) (name "Hierarchy acceptance") (context %s))' %
                                   (sexp(window), sexp(field(registry, 'main_context'))))
        self.workspace = field(field(registry, 'workspaces')[-1], 'id')
        session.url = self.proxy.url
        self.t = Terminal(session)
        self.t.capture('startup', ['Overview', 'Space c c commands'])
        self.t.command('Switch to Hierarchy acceptance')

    def detail(self, label, node, job, artifact):
        self.t.press(b'i')
        text = self.t.capture(label, ['HARDWARE HIERARCHY', 'Node instance: ' + node,
                                   field(job, 'id'), field(artifact, 'id')])
        self.check('count_o' in text and 'clock_i' in text, 'Existing detail inspector exposes exact selected-node ports')
        self.check('Exact target/configuration:' in text and 'Tested top / DUT: unknown' in text,
                   'Detail exposes exact selection provenance and explicitly unknown tested top')
        # The legacy inspector toggles with h, not Escape. When detail retained
        # an older artifact, the first h may open the current global candidate;
        # a second h closes that candidate. Neither action submits a generation.
        for _ in range(2):
            self.t.press(b'h')
            self.t.idle(1)
            if 'HARDWARE HIERARCHY' not in self.t.screen.text():
                break
        self.t.capture(label + '-back', absent=['HARDWARE HIERARCHY'])

    def run(self):
        self.setup()
        t = self.t
        before = self.counts()
        t.command('Add hierarchy tile')
        t.capture('empty-tile', ['hierarchy', 'Load'])
        t.command('Add hierarchy tile')
        self.wait(lambda: len(self.tiles()) == 2, 'two opt-in tiles registered')
        self.quiet(before, 'Opening two empty tiles')
        # A compact viewport is not used as evidence for clipped identities: zoom
        # gives the exact generating job/artifact room to be inspected.
        t.command('Zoom focused tile')
        t.press(b'r')
        t.capture('missing-generation', ['Missing hierarchy', 'generate RTL'])
        self.quiet(before, 'Missing hierarchy load action')
        first = self.generate()
        artifact = self.artifact(first)
        aid = field(artifact, 'id')
        before = self.counts()
        gate = self.proxy.arm('equivalent-inflight-two-tiles')
        start = len(self.proxy.reads(aid))
        t.command('Load current hierarchy')
        self.wait(gate['ready'].is_set, 'first hierarchy read buffered')
        t.command('Unzoom workspace')
        t.press(b'\t')
        t.command('Zoom focused tile')
        t.press(b'r')
        t.idle(.7)
        self.check(len(self.proxy.reads(aid)) - start == 1,
                   'Two equivalent concurrent tile loads share exactly one HTTP hierarchy read')
        gate['release'].set()
        t.capture('second-root-expanded', ['counter_top', 'u_counter_0', 'u_counter_1', 'HIERARCHY [current]', 'unknown'])
        self.check(all(field(first, key)[0] in t.screen.text() for key in ('target', 'configuration')),
                   'Loaded tile shows complete exact generating target and configuration IDs')
        self.check('u_leaf' not in t.screen.text(), 'Initially only root is expanded, nested branch remains collapsed')
        self.detail('second-root-detail', '<root>', first, artifact)
        t.press(b'j')
        t.press(b'\r')
        t.capture('second-branch-expanded', ['u_leaf'])
        t.press(b'\x1b[B')
        self.detail('second-leaf-detail', 'u_leaf', first, artifact)
        t.command('Unzoom workspace')
        t.press(b'\t')
        t.command('Zoom focused tile')
        t.capture('first-independent-root', ['counter_top', 'u_counter_0'], ['u_leaf'])
        self.detail('first-still-root-detail', '<root>', first, artifact)
        # Both character and arrow movement must return to the exact root.
        t.press(b'j'); t.press(b'k'); t.press(b'\x1b[B'); t.press(b'\x1b[A')
        self.detail('first-root-after-navigation', '<root>', first, artifact)
        t.press(b'\r')
        t.capture('first-root-collapsed', ['counter_top'], ['u_counter_0', 'u_counter_1'])
        t.press(b'\r')
        t.capture('first-root-reexpanded', ['u_counter_0', 'u_counter_1'])
        t.palette()
        t.press(b'jk')  # palette query input must not navigate the hierarchy
        t.capture('palette-owns-navigation-keys', ['COMMAND PALETTE', 'jk'])
        t.press(b'\x1b')
        t.capture('palette-dismissed', absent=['COMMAND PALETTE'])
        self.detail('palette-did-not-move-root', '<root>', first, artifact)
        t.resize(80, 24)
        t.capture('compact-80x24', ['HIERARCHY [current]', 'counter_top', 'u_counter_0'])
        t.resize(self.args.width, self.args.height)
        t.capture('restored-size', ['HIERARCHY [current]', 'u_counter_0', 'u_counter_1'])
        self.quiet(before, 'Loading, browsing, expanding and detail inspection')

        # Current project target/config selection is local terminal state. Exercise
        # its real global n/m input while hierarchy tile retains its evidence.
        t.press(b'm')
        t.capture('configuration-switch-historical', ['HIERARCHY [historical]', 'counter_top'])
        t.press(b'm')
        t.capture('configuration-restored-current', ['HIERARCHY [current]', 'counter_top'])
        t.press(b'n')
        t.capture('target-switch-historical', ['HIERARCHY [historical]', 'counter_top'])
        t.press(b'n')
        t.capture('target-restored-current', ['HIERARCHY [current]', 'counter_top'])
        self.quiet(before, 'Target/configuration selection changes')
        t.press(b'm')
        t.capture('eight-bit-retains-four-bit', ['HIERARCHY [historical]'])
        t.press(b'r')
        t.capture('eight-bit-missing-generation', ['Missing hierarchy'])
        eight = self.generate(configuration='eight-bit')
        t.press(b'r')
        t.capture('eight-bit-loaded', ['HIERARCHY [current]', '/configuration/eight-bit'])
        self.detail('eight-bit-detail', '<root>', eight, self.artifact(eight))
        t.press(b'm')
        t.capture('four-bit-retains-eight-bit-historical', ['HIERARCHY [historical]', '/configuration/eight-bit'])
        t.press(b'r')
        t.capture('four-bit-explicitly-restored', ['HIERARCHY [current]', '/configuration/four-bit'])
        newer = self.generate()
        newer_artifact = self.artifact(newer)
        t.capture('newer-generation-retained-historical', ['HIERARCHY [historical]', 'counter_top'])
        self.detail('retained-detail-still-old-artifact', '<root>', first, artifact)
        t.press(b'r')
        t.capture('explicit-reload-new-current', ['HIERARCHY [current]', 'counter_top'])
        self.detail('new-generation-detail', '<root>', newer, newer_artifact)

        # A third generation is read but held. Supersede it with a fourth generation
        # and explicit load. Releasing the old completion may never restore it.
        delayed = self.generate()
        old_gate = self.proxy.arm('superseded-load')
        t.press(b'r')
        self.wait(old_gate['ready'].is_set, 'superseded read buffered')
        latest = self.generate()
        latest_artifact = self.artifact(latest)
        t.press(b'r')
        t.capture('superseding-load-current', ['HIERARCHY [current]', 'counter_top'])
        self.detail('superseding-detail', '<root>', latest, latest_artifact)
        old_gate['release'].set()
        self.wait(old_gate['delivered'].is_set, 'superseded reply delivered')
        t.idle(.5)
        self.detail('stale-reply-did-not-overwrite', '<root>', latest, latest_artifact)
        self.check(field(delayed, 'id') != field(latest, 'id'), 'Stale-reply scenario used distinct real generation identities')

        # Public workspace mutations support hiding, not deletion. Hold a hidden
        # tile's reply while another instance loads a newer generation. This
        # proves cross-consumer isolation, not remove/recreate lifetime fencing.
        self.generate()
        lifetime = self.proxy.arm('hidden-tile-delayed-reply')
        t.press(b'r')
        self.wait(lifetime['ready'].is_set, 'hidden tile read buffered')
        registry = self.http.rpc(domain='workspace')
        workspace = next(w for w in field(registry, 'workspaces') if field(w, 'id') == self.workspace)
        hidden = field(workspace, 'zoomed_tile')[0]
        t.command('Unzoom workspace')
        t.command('Hide focused tile')
        self.wait(lambda: any(field(tile, 'id') == hidden and field(tile, 'hidden') == 'true'
                              for tile in self.tiles()), 'tile hidden')
        t.idle(1)
        t.command('Add hierarchy tile')
        self.wait(lambda: len(self.tiles()) == 3, 'additional tile created')
        newest = self.generate()
        # Whichever visible tile owns focus, the hidden consumer's completion
        # must not change its evidence or navigation.
        t.command('Zoom focused tile')
        t.press(b'r')
        t.capture('visible-consumer-current', ['HIERARCHY [current]', 'counter_top'])
        lifetime['release'].set()
        self.wait(lifetime['delivered'].is_set, 'hidden tile reply delivered')
        t.idle(.5)
        self.detail('visible-consumer-after-hidden-completion', '<root>', newest, self.artifact(newest))

        for mode, expected in [('unsupported', 'unsupported'), ('failed', 'failed'),
                               ('malformed', 'failed')]:
            self.generate(mode)
            before = self.counts()
            t.press(b'r')
            t.capture('unavailable-' + mode, [expected])
            t.command('Load current hierarchy')  # recovery remains accessible
            self.quiet(before, mode + ' display and retry')
        # The native backend validates structural bytes at registration and serves
        # retained typed evidence thereafter. A transport-corrupted response is the
        # separate read-error scenario; the proxy marks that fault in its receipt.
        self.generate()
        fault = self.proxy.arm('malformed-transport-response')
        fault['malformed_response'] = True
        t.press(b'r')
        self.wait(fault['ready'].is_set, 'read-error response buffered')
        fault['release'].set()
        t.capture('unavailable-read-error', ['read error', 'retries'])
        before = self.counts()
        t.command('Load current hierarchy')
        t.capture('read-error-recovered', ['HIERARCHY [current]', 'counter_top'])
        self.quiet(before, 'Malformed read-response recovery')
        pending = self.generate('pending', wait=False)
        self.wait(lambda: any(field(j, 'id') == field(pending, 'id') and field(j, 'state') == 'Running'
                              for j in self.jobs()), 'pending fixture running')
        t.capture('pending-generation-observed', ['HIERARCHY [historical]'])
        t.press(b'r')
        t.capture('unavailable-pending', ['Hierarchy Running'])
        self.http.raw('/api/v1/cancel-job', [['instance_id', self.http.instance], ['job', field(pending, 'id')]])
        self.wait(lambda: any(field(j, 'id') == field(pending, 'id') and field(j, 'state') == 'Cancelled'
                              for j in self.jobs()), 'fixture cancelled')
        t.idle(1.2)
        t.press(b'r')
        t.capture('unavailable-cancelled', ['cancelled'])
        recovered = self.generate()
        before = self.counts()
        t.command('Load current hierarchy')
        t.capture('recovered-current', ['HIERARCHY [current]', 'counter_top', 'unknown'])
        self.detail('recovered-detail', '<root>', recovered, self.artifact(recovered))
        # Existing h/u/o/e inspector access must continue independently of tile i.
        t.press(b'h')
        t.capture('legacy-inspector-h', ['HARDWARE HIERARCHY', 'Node instance: <root>'])
        t.press(b'o')
        t.capture('legacy-inspector-o', ['Node instance: u_counter_0'])
        t.press(b'u')
        t.capture('legacy-inspector-u', ['Node instance: <root>'])
        t.press(b'h')
        t.capture('legacy-inspector-closed', absent=['HARDWARE HIERARCHY'])
        t.command('Unzoom workspace')
        t.command('Hide focused tile')
        t.idle(.5)
        self.quiet(before, 'Recovery, legacy inspector and hiding')
        self.check(all(json.loads(line)['allowed'] for line in
                       (self.base / 'driver-calls.jsonl').read_text().splitlines()),
                   'No generic build/test/EDA invocation attempted')
        t.close()
        self.t = None
        self.check(self.counts() == before, 'Closing the native client creates no jobs or provider work')
        self.check({field(j, 'id') for j in self.jobs()} == self.expected_jobs,
                   'Every native job belongs to explicit setup discovery/generation; no unaccounted browsing jobs')
        calls = [json.loads(line) for line in (self.base / 'driver-calls.jsonl').read_text().splitlines()]
        generated = [call for call in calls if 'generate-rtl' in call['argv']]
        self.check(len(generated) == self.generation,
                   'Exactly one lightweight driver invocation per explicit setup generation')
        self.result['observations'] = dict(explicit_generations=self.generation,
            native_jobs=len(self.expected_jobs), hierarchy_reads=len(self.proxy.reads()),
            delayed_gates=len(self.proxy.gates))
        self.result['status'] = 'passed'

    def tiles(self):
        return [tile for tile in field(self.http.rpc(domain='workspace'), 'tiles')
                if field(tile, 'workspace') == self.workspace and field(tile, 'kind') == 'hierarchy']

    def close(self):
        errors = []
        # Release gates before stopping PTY/daemon, including partially failed cases.
        if self.proxy:
            for gate in self.proxy.gates:
                gate['release'].set()
        for action in ([self.t.close] if self.t else []) + ([self.proxy.close] if self.proxy else []) + (
                [self.session.stop] if self.session and self.session.process else []):
            try:
                action()
            except Exception:
                errors.append(traceback.format_exc())
        if self.http:
            save(self.base / 'http-setup.json', self.http.history)
        if errors:
            self.result['cleanup_errors'] = errors
            self.result['status'] = 'failed'


def self_test():
    # This checks the transport/fixture machinery, not a Python copy of UI logic.
    tree = wire.parse(fixture.sexp(fixture.hierarchy('counter', 'four-bit', 'self-test')))
    require(field(tree, 'root') == '/' and len(field(tree, 'nodes')) == 4, 'Fixture shape')
    require(field(field(tree, 'nodes')[2], 'parent') == ['/11:u_counter_0'], 'Nested fixture parent')
    require(field(field(tree, 'nodes')[2], 'output_ports')[0] == [['name', 'count_o'], ['width', '4']], 'Fixture ports')
    class Upstream(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            payload = self.rfile.read(int(self.headers['Content-Length']))
            self.send_response(200)
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
    with tempfile.TemporaryDirectory(prefix='hierarchy-self-test-', dir='/tmp/opencode') as directory:
        base = Path(directory)
        for name in ('project', 'state', 'tmp'):
            (base / name).mkdir()
        output = base / 'state/job-output'
        output.mkdir()
        save(base / 'control.json', dict(mode='valid', generation='self-test'))
        env = dict(os.environ, HIERARCHY_FIXTURE_BASE=str(base))
        def invoke(argv):
            return subprocess.run([sys.executable, str(HERE / 'fixtures/hierarchy_tile_driver.py')] + argv,
                                  env=env, capture_output=True, timeout=5)
        prefix = ['exec', '-j20', '--root', str(base / 'project'), '--no-buffer',
                  './hierarchy-driver.exe', '--']
        discovered = invoke(prefix + ['describe', '--protocol-version', '1'])
        require(discovered.returncode == 0 and len(field(wire.parse(discovered.stdout.decode()), 'targets')) == 2,
                'Fixture adapter discovery')
        generated = invoke(prefix + ['generate-rtl', '--protocol-version', '1', '--target', 'counter',
                                     '--configuration', 'four-bit', '--output-dir', str(output)])
        require(generated.returncode == 0 and len(field(wire.parse(generated.stdout.decode()), 'outputs')) == 2,
                'Fixture adapter generation')
        require(wire.parse((output / 'counter.hierarchy.sexp').read_text()) == tree, 'Fixture emitted exact structural bytes')
        require(invoke(['build', '-j20', '@all']).returncode != 0, 'Fixture must reject actual build commands')
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        proxy = HierarchyProxy('http://127.0.0.1:%d' % server.server_port, Path(directory))
        gate = proxy.arm('self-test')
        values = []
        def read():
            with urllib.request.urlopen(proxy.url + '/api/v1/read-hierarchy', data=b'((artifact fixture))', timeout=5) as response:
                values.append(response.read())
        reader = threading.Thread(target=read)
        try:
            reader.start()
            require(gate['ready'].wait(3), 'Proxy did not buffer real upstream reply')
            require(not values and len(proxy.reads('fixture')) == 1, 'Gate/count observation')
            gate['release'].set()
            reader.join(timeout=3)
            require(values == [b'((artifact fixture))'], 'Proxy altered response bytes')
        finally:
            proxy.close()
            reader.join(timeout=5)
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    print('PASS: fixture protocol and real loopback delayed-response gate (no native UI claim)')


def main():
    repo = HERE.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, default=repo / '_build/default/terminal/main.exe')
    parser.add_argument('--daemon', type=Path, default=repo / '_build/default/daemon/main.exe')
    parser.add_argument('--evidence', type=Path, help='New directory directly under /tmp/opencode')
    parser.add_argument('--budget', type=int, default=300)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    for name in ('client', 'daemon'):
        path = getattr(args, name).resolve(strict=True)
        require(path.is_file() and os.access(path, os.X_OK), 'Existing executable required: ' + str(path))
        setattr(args, name, path)
    require(60 <= args.budget <= 900, '--budget must be 60..900 seconds')
    os.umask(0o077)
    if args.evidence:
        args.evidence = args.evidence.absolute()
        require(args.evidence.parent.resolve() == Path('/tmp/opencode') and not args.evidence.exists(),
                '--evidence must be a NEW directory directly under /tmp/opencode')
        args.evidence.mkdir(mode=0o700)
    else:
        args.evidence = Path(tempfile.mkdtemp(prefix='hierarchy-tile-', dir='/tmp/opencode'))
    args.width, args.height, args.tmux_escape_time = 220, 65, None
    args.outer_timeout, args.deadline = 30, time.monotonic() + args.budget
    result = dict(status='failed', checks=[], evidence=str(args.evidence), argv=sys.argv,
        binaries={name: dict(path=str(getattr(args, name)), sha256=hashlib.sha256(getattr(args, name).read_bytes()).hexdigest())
                  for name in ('client', 'daemon')},
        limitations=['Synthetic structural fixture; no real provider declared-DUT association is asserted.',
                     'No daemon restart/project-reopen or physical-tool coverage.',
                     'Malformed provider bytes are rejected during generation. Read failure uses a marked malformed-response proxy fault after a real upstream read.',
                     'On-disk disappearing artifact is not injected; native hierarchy reads serve retained typed evidence.',
                     'No public remove-tile mutation exists: delayed hidden-consumer isolation is tested; remove/recreate lifetime fencing is not.',
                     'Addition/hiding use actual palette input; teardown closes the private native client.'])
    acceptance = Acceptance(args, result)
    print('Evidence: ' + str(args.evidence), flush=True)
    def interrupted(signum, _):
        raise TimeoutError('Interrupted or acceptance budget exhausted: %d' % signum)
    for sig in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupted)
    signal.alarm(args.budget)
    try:
        acceptance.run()
    except BaseException:
        result['error'] = traceback.format_exc()
        raise
    finally:
        signal.alarm(0)
        acceptance.close()
        save(args.evidence / 'result.json', result)
    require(result['status'] == 'passed', 'Cleanup failed; see result.json')
    print('PASS: native hierarchy HTTP/PTY acceptance; ' + str(args.evidence))


if __name__ == '__main__':
    main()
