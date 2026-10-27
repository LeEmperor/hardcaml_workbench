"""Shared synthetic-only native frontend setup for migrated regression scripts."""
import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
import sys
import threading
from types import SimpleNamespace
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('fresh_frontend_api', HERE / 'test-unified-fresh-prefix.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
c = api.c
field, sexp, wait = api.field, api.sexp, api.wait


def setup(args, label, check, preparation=True, configure=None, cold=False):
    f = api.Fixture(args, label, check)
    if not preparation:
        (f.root / 'hardcaml-workbench-preparation.sexp').unlink()
    # Generic source operations still request -j20; normalize only this private
    # daemon's wrapper, so every actual nested build has the authorized -j6 bound.
    wrapper = f.base / 'bin/dune'
    wrapper.write_text('#!/bin/bash\nset -euo pipefail\na=()\n'
                       'for x in "$@"; do [[ "$x" == -j* ]] || a+=("$x"); done\n'
                       'if [[ "${a[0]}" == build ]]; then a=(build -j6 "${a[@]:1}"); fi\n'
                       'exec flock /tmp/opencode/workbench-fresh-prefix-build.lock "' +
                       str(HERE / 'with-switch.sh') + '" dune "${a[@]}"\n')
    if configure:
        configure(f)
    try:
        f.start()
        f.http.rpc('Discover', wait=False)
        wait(lambda: field(f.snapshot(), 'flows'), 'synthetic catalog')
        presets = c.demo.workspace_presets(args.preset_export)
        ws = c.demo.ensure_workspaces(f.http, f.http.rpc(domain='workspace'), presets)
        ws = c.demo.apply_workspace_presets(f.http, ws, presets)
        overview = next(w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview'])
        ws = f.http.mutate(ws, '(Create_tile (workspace %s) (kind planned-run) '
                             '(geometry ((x 0) (y 56) (width 100) (height 18))))' % sexp(field(overview, 'id')))
        f.planned_tile = field(field(ws, 'tiles')[-1], 'id')
        ref = [['attempt', str(f.base / 'results/synthetic-reference')], ['stream_id', 'synthetic-reference']]
        f.http.rpc('(Register %s)' % sexp(ref), wait=False)
        historical = wait(lambda: next(iter(field(f.snapshot(), 'runs')), None), 'historical reference')
        f.http.rpc('(Observe %s)' % sexp(field(historical, 'run')), wait=False)
        wait(lambda: any(field(r, 'stages') for r in field(f.snapshot(), 'runs')), 'historical stages')
        context = next(x for x in field(ws, 'contexts') if field(x, 'id') == field(overview, 'context'))
        f.http.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' %
                      (sexp(field(overview, 'id')), sexp(field(context, 'id')), field(context, 'selection_revision'),
                       sexp(field(historical, 'run'))))
        if cold:
            f.stop()
            f.start()
        client = f.base / 'inherited-client'
        client.write_text('#!' + sys.executable + '\nimport os,sys\na=sys.argv[1:]\n'
                          'a[a.index("--environment")+1]="inherited"\nos.execv(' + repr(str(args.client)) +
                          ', [' + repr(str(args.client)) + '] + a)\n')
        client.chmod(0o700)
        f.client_args = SimpleNamespace(client=client)
        f.client_url = f.url
        f.terminal = c.Terminal(f.base, f.client_args, f.url, 180, 55)
        f.terminal.capture('initial', ['stage checklist'])
        return f, presets
    except BaseException:
        try:
            if hasattr(f, 'terminal'):
                f.terminal.close()
        finally:
            f.stop()
        raise


def zoom(f, kind):
    ws = f.http.rpc(domain='workspace')
    overview = next(w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview'])
    tile = next(t for t in field(ws, 'tiles') if field(t, 'workspace') == field(overview, 'id') and field(t, 'kind') == kind)
    f.http.mutate(ws, '(Set_zoom (workspace %s) (tile (%s)))' %
                  (sexp(field(overview, 'id')), sexp(field(tile, 'id'))))


def finish(f):
    try:
        if hasattr(f, 'terminal'):
            f.terminal.close()
        if f.process is not None and f.process.poll() is None:
            api.save(f.base / 'final-snapshot.json', f.snapshot())
    finally:
        f.stop()


class StageReplyGate:
    """Transparent native HTTP proxy; holds one real Stage_fresh RESPONSE only.

    This replaces the old pinned-Plan subprocess gate at the same client async
    boundary. Bodies are forwarded byte-exactly; no synthetic protocol replies.
    """
    def __init__(self, f):
        self.entered, self.release = threading.Event(), threading.Event()
        self.requests = []
        target = urlsplit(f.url)
        gate = self
        class Server(ThreadingMixIn, HTTPServer):
            daemon_threads = True
            def process_request(self, request, address):
                self.pool.submit(self.process_request_thread, request, address)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def forward(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                conn = HTTPConnection(target.hostname, target.port, timeout=30)
                try:
                    conn.request(self.command, self.path, body=raw if self.command == 'POST' else None,
                                 headers={'Content-Type': 'application/sexp', 'X-Workbench-Protocol': '1'})
                    reply = conn.getresponse()
                    body = reply.read()
                    gate.requests.append(dict(path=self.path, request=raw.decode(), status=reply.status, response=body.decode()))
                    if b'(Stage_fresh' in raw:
                        gate.entered.set()
                        if not gate.release.wait(45):
                            raise TimeoutError('Stage_fresh reply gate timed out')
                    self.send_response(reply.status)
                    self.send_header('Content-Type', 'application/sexp')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                finally:
                    conn.close()
            do_GET = forward
            do_POST = forward
        self.server = Server(('127.0.0.1', 0), Handler)
        self.server.pool = ThreadPoolExecutor(max_workers=6)
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)
        api.require(self.server.server_port != 41735, 'Private proxy port')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.f = f

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.server.pool.shutdown(wait=True)
        self.thread.join(timeout=5)
        api.save(self.f.base / 'stage-gate-http.json', self.requests)
