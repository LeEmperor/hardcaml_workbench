#!/usr/bin/env python3
"""WB-028 independent acceptance using a prebuilt waveform_probe, never builds.

Use --vcd for a retained real native FIFO trace (repeatable). Defaults discover
retained pass/failure/long FIFO fixtures under /tmp/opencode. Each subprocess is
bounded to 30s. Evidence includes exact commands, hashes, CPU/wall time and Linux
peak RSS via /usr/bin/time. PTY checks cover quick inspection, real Waveforms
tiles, exact pinned logs, delayed byte completions and client/daemon restoration.
Synthetic files test semantics, not another parser. Enter toggles; Space c c
remains global. All fixture producers only replay retained bytes, never simulate.
"""
import argparse
import fcntl
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import urllib.error
import urllib.request

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('waveform_wire', HERE / 'fixtures/fs2_wire.py')
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)

HEADER = ('$timescale 10 ps $end\n$scope module top $end\n'
          '$var wire 1 ! clk $end\n$var wire 4 " bus [3:0] $end\n'
          '$scope module child $end\n$var wire 4 " alias [0:3] $end\n'
          '$upscope $end\n$upscope $end\n$enddefinitions $end\n')


class DelayedBytesProxy:
    """Loopback-only test gate: fetch a real byte page, then hold its response.

    Other requests continue on separate threads. A one-shot gate captures exactly
    one Read_artifact_bytes response, so a replacement viewer can load normally.
    Both waits and upstream requests have deadlines; teardown releases all gates.
    """
    def __init__(self, upstream, evidence):
        self.upstream, self.evidence = upstream, evidence
        self.lock = threading.Lock()
        self.pending = None
        self.gates = []
        self.records = []
        proxy = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *_args):
                pass

            def handle(self):
                try:
                    super().handle()
                except (ConnectionResetError, BrokenPipeError):
                    pass  # Normal idle keep-alive close during owned client restart.

            def do_GET(self):
                self.forward()

            def do_POST(self):
                self.forward()

            def forward(self):
                data = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                operation = None
                if self.path == '/api/v1/simulation' and data:
                    operation = dict(wire.parse(data.decode()))['operation']
                is_bytes = isinstance(operation, list) and operation[0] == 'Read_artifact_bytes'
                gate = None
                if is_bytes:
                    with proxy.lock:
                        if proxy.pending is not None:
                            gate, proxy.pending = proxy.pending, None
                            gate['request'] = dict(operation[1:])
                request = urllib.request.Request(proxy.upstream + self.path,
                    data=data if self.command == 'POST' else None,
                    headers={k: v for k, v in self.headers.items()
                             if k.lower() not in ('host', 'connection', 'content-length')},
                    method=self.command)
                try:
                    response = urllib.request.urlopen(request, timeout=20)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    payload, status = response.read(), response.status
                    content_type = response.headers.get('Content-Type', 'application/sexp')
                if is_bytes:
                    with proxy.lock:
                        proxy.records.append(dict(request=dict(operation[1:]), status=status,
                            gated=gate is not None, response_sha256=hashlib.sha256(payload).hexdigest()))
                if gate is not None:
                    gate['response_status'] = status
                    gate['response_bytes'] = len(payload)
                    buffered_at = time.monotonic()
                    gate['ready'].set()
                    gate['timed_out'] = not gate['release'].wait(20)
                    gate['held_ms'] = (time.monotonic() - buffered_at) * 1000
                try:
                    self.send_response(status)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Length', str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    if gate is not None:
                        gate['client_disconnected'] = True
                finally:
                    if gate is not None:
                        gate['delivered'].set()

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:%d' % self.server.server_port

    def arm(self, label):
        gate = dict(label=label, ready=threading.Event(), release=threading.Event(),
                    delivered=threading.Event(), timed_out=False, client_disconnected=False)
        with self.lock:
            assert self.pending is None, 'previous gate has not captured its request'
            gate['record_start'] = len(self.records)
            self.pending = gate
            self.gates.append(gate)
        return gate

    def close(self):
        for gate in self.gates:
            gate['release'].set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        report = dict(byte_requests=self.records,
            gates=[{k: (v.is_set() if isinstance(v, threading.Event) else v)
                    for k, v in gate.items()} for gate in self.gates])
        (self.evidence / 'delayed-byte-proxy.json').write_text(json.dumps(report, indent=2) + '\n')


def replay_provider():
    """Private FS2 producer: replay retained bytes, never invoke a simulator."""
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--calls', type=Path, required=True)
    p.add_argument('operation', choices=['discover', 'run'])
    p.add_argument('--protocol-version', required=True)
    p.add_argument('--request', type=Path)
    p.add_argument('--events', type=Path)
    p.add_argument('--artifact-dir', type=Path)
    a = p.parse_args(sys.argv[2:])
    with a.calls.open('a') as out:
        out.write(json.dumps(dict(operation=a.operation)) + '\n')
    if a.operation == 'discover':
        print(wire.sexp(wire.catalog(cases=['first', 'second'])))
        return
    request = dict(wire.parse(a.request.read_text()))
    selected = dict(request['selection'])
    case = selected['cases'][0]
    print('WB028_LOG_ATTEMPT=' + request['attempt_id'], flush=True)
    print('WB028_LOG_CASE=' + case, flush=True)
    print('WB028_LOG_SEED=' + selected['seed'], flush=True)
    writer = wire.EventWriter(a.events, request['attempt_id'])
    writer.emit('Started')
    writer.emit(['Case_started', case])
    path = a.artifact_dir / 'retained.vcd'
    path.write_bytes(a.fixture.read_bytes())
    writer.artifact('retained-vcd', case, 'waveform', 'text/vcd', path.name)
    alternate = a.artifact_dir / 'alternate.vcd'
    alternate.write_bytes(path.read_bytes().replace(b'$scope module outputs ', b'$scope module alternate_outputs '))
    writer.artifact('alternate-vcd', case, 'waveform', 'text/vcd', alternate.name)
    writer.finish_case(case)
    writer.emit(['Finished', 'Passed'])


def plot_region(shot):
    rows = shot.lines()
    top = next(i for i, row in enumerate(rows) if '┌Waves' in row)
    left = rows[top].index('┌Waves') + 1
    right = rows[top].index('┐', left)
    bottom = next(y for y in range(top + 1, shot.height)
                  if shot.cells[y][left - 1][0] == '└' and shot.cells[y][right][0] == '┘')
    return dict(left=left, right=right, top=top + 1, bottom=bottom, columns=right - left,
                glyphs=tuple(tuple(c for c, _ in row[left:right]) for row in shot.cells[top + 1:bottom]),
                attrs=tuple(tuple(a for _, a in row[left:right]) for row in shot.cells[top + 1:bottom]))


def raster_scale(text):
    scales = {(int(n), unit) for n, unit in re.findall(r'(\d+) (cells/tick|ticks/cell)', text)}
    if len(scales) != 1:
        raise AssertionError('expected one consistent displayed integer raster scale: ' + repr(scales))
    return next(iter(scales))


def expected_cursor_column(start, stop, cursor, scale):
    if cursor < start or cursor > stop:
        return None
    amount, unit = scale
    return (cursor - start) * amount if unit == 'cells/tick' else (cursor - start) // amount


def cursor_attr_change(check, before, after, old_column, new_column, label):
    a, b = plot_region(before), plot_region(after)
    check(a['glyphs'] == b['glyphs'], label + ': underlying wave glyphs are unchanged by cursor movement')
    changed = {(y, x) for y, row in enumerate(a['attrs']) for x, attrs in enumerate(row)
               if attrs != b['attrs'][y][x]}
    wanted = set() if old_column == new_column else {old_column, new_column}
    check({x for _, x in changed} == wanted,
          label + ': attribute changes occur only at exact old/new cursor columns')
    for row_name, offset in [('labels', 3), ('marks', 2)]:
        old = before.cells[a['top'] - offset][a['left']:a['right']]
        new = after.cells[b['top'] - offset][b['left']:b['right']]
        check([c for c, _ in old] == [c for c, _ in new] and
              {x for x, ((_, aa), (_, bb)) in enumerate(zip(old, new)) if aa != bb} == wanted,
              label + ': ruler ' + row_name + ' highlight stays aligned with the plot without changing glyphs')
    if wanted:
        highlighted = {b['attrs'][y][new_column] for y, x in changed if x == new_column}
        check(len({y for y, x in changed if x == new_column}) >= 2 and bool(highlighted),
              label + ': visible vertical cursor styling spans multiple wave rows')
        return highlighted
    return set()


def check_ruler_image(check, image, label, magnitude, unit, bounds=None):
    plot = plot_region(image)
    rows = image.lines()
    labels = rows[plot['top'] - 3][plot['left']:plot['right']]
    marks = rows[plot['top'] - 2][plot['left']:plot['right']]
    scale = raster_scale(image.text())
    window_match = re.search(r'window (\d+)\.\.(\d+)', image.text())
    if bounds is not None:
        start, stop = bounds
        header = rows[0].rstrip()
        offset = header.find('window ')
        if offset >= 0:
            visible = header[offset:]
            exact = 'window %d..%d' % bounds
            check(visible == exact or (len(header) == image.width and exact.startswith(visible)),
                  label + ': displayed endpoint digits are exact, allowing only viewport-edge clipping')
    elif window_match:
        start, stop = map(int, window_match.groups())
    else:
        raise AssertionError(label + ': missing displayed absolute tick window')
    found = list(re.finditer(r'(\d+) (fs|ps|ns|us|ms|s)\b', labels))
    check(bool(found), label + ': absolute physical-time labels remain visible with quiet hints')
    records = []
    for match in found:
        physical = int(match[1])
        tick, remainder = divmod(physical, magnitude)
        anchor = expected_cursor_column(start, stop, tick, scale)
        check(match[2] == unit and remainder == 0 and anchor is not None and
              0 <= anchor < plot['columns'] and marks[anchor] in '┬+',
              label + ': absolute physical label anchors at its exact plotted tick column')
        check(match.start() <= anchor < match.end(),
              label + ': physical label is positioned at its mark or shifted only to fit its end')
        records.append(dict(tick=tick, physical=physical, column=anchor, text_column=match.start(), text=match[0]))
    check(all(a.end() + 2 <= b.start() for a, b in zip(found, found[1:])),
          label + ': ruler labels are complete, nonoverlapping and separated')
    major = [i for i, c in enumerate(marks) if c in '┬+']
    minor = [i for i, c in enumerate(marks) if c in "╷'"]
    last_column = expected_cursor_column(start, stop, stop, scale)
    check(bool(major) and all(c <= last_column for c in major + minor),
          label + ': major/minor marks stop at retained data bounds')
    if last_column >= 16:
        check(bool(minor), label + ': adaptive minor marks remain visible between major marks')
    return dict(start=start, stop=stop, scale=scale, labels=records,
                major_columns=major, minor_columns=minor, plot_columns=plot['columns'])


def pty_acceptance(args, evidence, fixture, check):
    spec = importlib.util.spec_from_file_location('waveform_native', HERE / 'test-fs2-native.py')
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    cells = native.load_module('waveform_cell_support', 'test-frontend-composition.py')
    field = native.field
    directory = evidence / 'pty'
    directory.mkdir()
    binary_hashes = {name: hashlib.sha256(getattr(args, name).read_bytes()).hexdigest()
                     for name in ('client', 'daemon')}
    (directory / 'binary-sha256.json').write_text(json.dumps(binary_hashes, indent=2) + '\n')
    for name in ('project', 'state', 'home', 'config', 'tmp'):
        (directory / name).mkdir()
    root = directory / 'project'
    (root / 'dune-project').write_text('(lang dune 3.22)\n(name waveform_acceptance)\n')
    calls = directory / 'calls.jsonl'
    (root / 'hardcaml-workbench-simulation.sexp').write_text(wire.sexp([
        ('schema_version', 1), ('provider_executable', sys.executable),
        ('provider_args', [str(Path(__file__).resolve()), '_provider', '--fixture', str(fixture.resolve()), '--calls', str(calls)]),
        ('discovery_timeout_seconds', 10), ('run_timeout_seconds', 30)]))
    session = native.Session(args, directory, root)
    session.env.update(HOME=str(directory / 'home'), XDG_CONFIG_HOME=str(directory / 'config'),
                       TMPDIR=str(directory / 'tmp'), PYTHONDONTWRITEBYTECODE='1')

    class Terminal(native.Terminal):
        width, height = 120, 40

        def __init__(self, session):
            check(hashlib.sha256(args.client.read_bytes()).hexdigest() == binary_hashes['client'],
                  'each restarted client uses the same prebuilt executable bytes')
            super().__init__(session)
            self.received_bytes = 0
            self.history = bytearray()
            self.repaint_checkpoints = []
            self.capture_id = str(time.time_ns())

        def drain(self, seconds=.3):
            self.poll(seconds)
            if len(self.data) > 200_000:
                # The shared ANSI oracle replays its input from the beginning.
                # Keep that work bounded by requesting a real complete repaint,
                # while retaining EVERY original byte in the client archive.
                # A one-column resize roundtrip restores the exact viewport and
                # exercises normal application rendering, not synthesized cells.
                self.history.extend(self.data)
                self.data = bytearray()
                width, height = self.width, self.height
                for current_width in (width + 1, width):
                    self.width = current_width
                    fcntl.ioctl(self.master, termios.TIOCSWINSZ,
                                struct.pack('HHHH', height, current_width, 0, 0))
                    os.kill(self.process.pid, signal.SIGWINCH)
                    self.poll(.15)
                    if current_width != width:
                        self.history.extend(self.data)
                        self.data = bytearray()
                self.repaint_checkpoints.append(dict(width=width, height=height,
                    archived_bytes=len(self.history), received_bytes=self.received_bytes))
            return native.fs0.terminal_screen(bytes(self.data), self.width, self.height)

        def poll(self, seconds):
            before = len(self.data)
            super().drain(seconds)
            self.received_bytes += len(self.data) - before

        def close(self):
            super().close()
            (directory / ('client-' + self.capture_id + '.ansi')).write_bytes(self.history + self.data)
            (directory / ('client-' + self.capture_id + '-repaints.json')).write_text(
                json.dumps(self.repaint_checkpoints, indent=2) + '\n')

        def palette(self, title):
            # Query refinement preserves a previously highlighted command ID.
            # Explicitly choose the top exact-title match; do not assume typing
            # the query also resets selection after new waveform commands appear.
            for key in (b' ', b'c', b'c'):
                self.key(key)
            self.capture('palette-open-' + str(time.time_ns()), ['COMMAND PALETTE'])
            self.key(title.encode())
            self.capture('palette-query-' + str(time.time_ns()), ['COMMAND PALETTE', title[-60:]],
                         absent=['No matching commands'])
            self.key(b'\x1b[A' * 16)
            self.capture('palette-exact-selection-' + str(time.time_ns()),
                         ['> ' + title[:min(len(title), 36)]], absent=['No matching commands'])
            self.key(b'\r')

        def resize(self, width, height, waveform=True, hints=True):
            self.width, self.height = width, height
            before = self.received_bytes
            fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
            os.kill(self.process.pid, signal.SIGWINCH)
            deadline = time.monotonic() + 15
            while True:
                rows = self.drain(.05).splitlines()
                framed = rows and rows[0].startswith(('╭', '┌'))
                footer_row = height - (3 if framed else 2) if waveform else height - 1
                footer_text = 'j/k signal' if waveform else 'Space c c commands'
                painted = (len(rows) > footer_row and footer_text in rows[footer_row])
                if not waveform and not hints:
                    edge_row = height - 2  # Host retains its status-row space even when quiet.
                    painted = (len(rows) > edge_row and len(rows[edge_row]) == width
                               and rows[edge_row].endswith(('╯', '┘')))
                bottom = height - 1 if waveform else height - 2
                edges = (not framed or (len(rows) > bottom and len(rows[0]) == width
                         and rows[bottom].startswith(('╰', '└')) and len(rows[bottom]) == width))
                if self.received_bytes > before and painted and edges:
                    break
                if time.monotonic() > deadline:
                    self.save('resize-%dx%d-unpainted' % (width, height), '\n'.join(rows))
                    raise AssertionError('waveform resize did not repaint footer at actual viewport edge')

    terminal = proxy = None
    try:
        session.start()
        catalog = session.discover()
        launch = ['Launch', ['submission_key', 'replay-only'],
                  ['discovery_digest', field(catalog, 'discovery_digest')[0]],
                  ['selection', [('suite', 'fixture'), ('cases', ['first']), ('seed', '42'),
                                 ('parameters', []), ('asic_inputs', [])]]]
        snap = session.api(operation=launch)
        aid = field(field(snap, 'attempts')[0], 'id')
        detail = session.done(aid)
        check(field(detail, 'outcome') == 'Passed', 'private producer captured retained VCD without simulator')
        before = calls.read_bytes()
        proxy = DelayedBytesProxy(session.url, directory)
        session.url = proxy.url
        terminal = Terminal(session)
        terminal.capture('startup', ['Overview'])
        deadline = time.monotonic() + 15
        while True:
            initial_registry = session.api(domain='workspace')
            if field(initial_registry, 'defaults_initialized') == 'true':
                break
            if time.monotonic() > deadline:
                raise AssertionError('native shared workspace bootstrap did not complete')
            terminal.drain(.1)
        # Native startup consumes the canonical stock window composition. The
        # explicit Testing action also supports older saved two-workspace sessions.
        check(not any(field(w, 'preset') == ['waveforms'] for w in field(initial_registry, 'workspaces')),
              'ordinary startup never creates an empty Waveforms workspace')
        has_testing = any(field(w, 'preset') == ['testing'] for w in field(initial_registry, 'workspaces'))
        terminal.palette('Switch to Testing' if has_testing else 'Create Testing workspace')
        terminal.capture('testing', ['simulation-catalog', 'simulation-artifacts'])
        testing_registry = session.api(domain='workspace')
        check(len(field(testing_registry, 'workspaces')) == 3 and
              {field(w, 'preset')[0] for w in field(testing_registry, 'workspaces')} == {'overview', 'timing', 'testing'},
              'Testing setup contains exactly three starter workspaces; Waveforms remains explicit')
        for _ in range(5):
            terminal.key(b'\t')  # Navigation, Session, Tests, Execution, Catalog, Attempts
        terminal.palette('Simulation: Reopen ' + aid + ' fixture')
        for _ in range(3):
            terminal.key(b'\t')  # Cases, Detail, Artifacts (palette is captured-target scoped)
        artifacts = field(detail, 'artifacts')
        retained = next(a for a in artifacts if field(a, 'label') == 'retained-vcd')
        check(len(artifacts) == 2 and field(artifacts[0], 'sha256') != field(artifacts[1], 'sha256'),
              'two retained artifacts have distinct byte digests')

        def identity(label, artifact, cursor, return_key=b'\x1b'):
            terminal.key(b'i')
            terminal.capture(label, ['Captured waveform identity', 'Back to waveform'])
            shot = cells.Screen(bytes(terminal.data), terminal.width, terminal.height)
            shot.save(directory / label)
            # Inspector wraps at terminal cell boundaries. Join content rows without
            # inserting whitespace into IDs, preserving the exact captured strings.
            lines = shot.lines()
            framed = lines[0].startswith(('╭', '┌'))
            content = ''.join((line[1:-1] if framed else line).strip()
                              for line in (lines[1:-1] if framed else lines))
            expected = ['Project ' + session.project, 'Attempt ' + aid,
                        'Case ' + field(artifact, 'case_id')[0],
                        'Artifact ' + field(artifact, 'id'),
                        'SHA256 ' + field(artifact, 'sha256')[0]]
            check(all(value in content for value in expected),
                  label + ': inspector exposes exact project/attempt/case/artifact/digest')
            terminal.key(return_key)
            terminal.capture(label + '-return', ['Waveform', 'Cursor %d ticks' % cursor,
                             'Back to Testing'], absent=['Captured waveform identity'])
            check(True, label + ': inspector return preserves waveform and cursor')

        def window(text):
            found = re.search(r'window (\d+)\.\.(\d+)', text)
            if not found:
                raise AssertionError('missing exact visible window')
            return tuple(map(int, found.groups()))

        def plot_shot(label, expected=()):
            terminal.capture(label, expected)
            shot = cells.Screen(bytes(terminal.data), terminal.width, terminal.height)
            shot.save(directory / label)
            return shot

        def set_tick(time):
            terminal.key(b':' + b'\x7f' * 32 + str(time).encode() + b'\r')

        def cursor_ruler_acceptance(prefix, workspace=False):
            original_width, original_height = terminal.width, terminal.height
            measurements = []

            def shot(name, cursor, extra=()):
                image = plot_shot(prefix + '-' + name, ['Cursor %d ticks' % cursor, *extra])
                start, stop = window(image.text())
                scale = raster_scale(image.text())
                plot = plot_region(image)
                column = expected_cursor_column(start, stop, cursor, scale)
                check(column is None or 0 <= column < plot['columns'],
                      prefix + '-' + name + ': exact cursor tick maps inside the actual plotted cells')
                measurements.append(dict(name=name, cursor=cursor, start=start, stop=stop,
                    scale=scale, plot_columns=plot['columns'], cursor_column=column))
                return image, column

            def value(image, expected):
                if workspace:
                    rows = [row for row in image.lines() if 'inputs.-clock' in row and '[1]' in row]
                    check(any(re.search(r'=\s*' + expected + r'\s*[│ ]*$', row.split('│')[1]) for row in rows),
                          prefix + ': exact inspected FIFO clock value matches cursor tick')
                else:
                    check('Value 0..1/1: ' + expected in image.text(),
                          prefix + ': exact inspected FIFO clock value matches cursor tick')

            set_tick(0)
            terminal.key(b'+')
            expanded0, c0 = shot('expanded-0', 0)
            check(raster_scale(expanded0.text())[1] == 'cells/tick' and raster_scale(expanded0.text())[0] > 1,
                  prefix + ': expanded mode uses multiple exact cells per tick')
            value(expanded0, '1')
            terminal.key(b'l')
            expanded1, c1 = shot('expanded-1', 1)
            styles = cursor_attr_change(check, expanded0, expanded1, c0, c1, prefix + '-expanded-right')
            value(expanded1, '1')
            terminal.key(b'h')
            expanded_back, cb = shot('expanded-back', 0)
            cursor_attr_change(check, expanded1, expanded_back, c1, cb, prefix + '-expanded-left')
            terminal.key(b'lllll')
            expanded5, c5 = shot('expanded-5', 5)
            cursor_attr_change(check, expanded0, expanded5, c0, c5, prefix + '-expanded-exact-value')
            value(expanded5, '0')
            terminal.key(b']')
            offleft, cl = shot('offscreen-left', 5)
            check(cl is None and ('left' in offleft.text().lower() or '←' in offleft.text()),
                  prefix + ': panned-off cursor has an explicit left direction')
            check(not any(a in styles for row in plot_region(offleft)['attrs'] for a in row),
                  prefix + ': no highlighted plot column when cursor is off-screen left')

            terminal.key(b'G')
            last_image = plot_shot(prefix + '-last-timestamp', ['Cursor ', 'ticks'])
            last = int(re.search(r'Cursor (\d+) ticks', last_image.text())[1])
            last_start, last_stop = window(last_image.text())
            last_column = expected_cursor_column(last_start, last_stop, last, raster_scale(last_image.text()))
            last_plot = plot_region(last_image)
            check(last_column is not None and
                  {x for row in last_plot['attrs'] for x, a in enumerate(row) if a in styles} == {last_column},
                  prefix + ': last retained timestamp has a visible cursor at its exact plotted column')
            terminal.key(b'[[[')
            offright, cr = shot('offscreen-right', last)
            check(cr is None and ('right' in offright.text().lower() or '→' in offright.text()),
                  prefix + ': cursor beyond the panned window has an explicit right direction')
            check(not any(a in styles for row in plot_region(offright)['attrs'] for a in row),
                  prefix + ': no highlighted plot column when cursor is off-screen right')

            set_tick(0)
            terminal.key(b'----')
            compressed0, cc0 = shot('compressed-initial', 0)
            amount, unit = raster_scale(compressed0.text())
            extra_zoom_out = 0
            while unit != 'ticks/cell' or amount <= 5:
                check(extra_zoom_out < 4, prefix + ': sufficient compressed scale is reachable within bounded zoom steps')
                terminal.key(b'-')
                extra_zoom_out += 1
                compressed0, cc0 = shot('compressed-fit-%d' % extra_zoom_out, 0)
                amount, unit = raster_scale(compressed0.text())
            compressed0.save(directory / (prefix + '-compressed-0'))
            check(unit == 'ticks/cell' and amount > 5, prefix + ': compressed cells honestly represent multiple ticks')
            check('Cursor cell 0..%d ticks' % (amount - 1) in compressed0.text(),
                  prefix + ': compressed legend exposes the actual cursor cell tick interval')
            terminal.key(b'l')
            compressed1, cc1 = shot('compressed-1', 1)
            cursor_attr_change(check, compressed0, compressed1, cc0, cc1, prefix + '-compressed-same-cell')
            check(cc0 == cc1, prefix + ': adjacent compressed ticks can share the same highlighted column')
            value(compressed1, '1')
            terminal.key(b'llll')
            compressed5, cc5 = shot('compressed-5', 5)
            cursor_attr_change(check, compressed0, compressed5, cc0, cc5, prefix + '-compressed-different-value')
            check(cc5 == cc0, prefix + ': exact value can change within the same compressed cursor cell')
            value(compressed5, '0')
            terminal.key(b'l' * (amount - 5))
            compressed_next, ccn = shot('compressed-next-cell', amount)
            cursor_attr_change(check, compressed0, compressed_next, cc0, ccn, prefix + '-compressed-cell-boundary')
            check(ccn == cc0 + 1, prefix + ': crossing the compressed tick bucket moves exactly one plot cell')
            terminal.key(b']')
            panned, _ = shot('compressed-panned', amount)
            terminal.resize(120, original_height, waveform=not workspace, hints=not workspace)
            resized, _ = shot('compressed-resized', amount)
            # Exact absolute ruler checks are added below against its actual label
            # and mark cells, independently of the wave-data glyph comparison.
            rulers = [check_ruler_image(check, image, prefix + '-' + name, magnitude=1, unit='ns')
                      for name, image in [('expanded', expanded0), ('compressed', compressed0),
                                          ('panned', panned), ('resized', resized)]]
            check(rulers[0]['labels'] != rulers[1]['labels'] and rulers[1]['labels'] != rulers[2]['labels'] and
                  rulers[2]['labels'] != rulers[3]['labels'],
                  prefix + ': absolute ruler values/positions adapt to zoom, pan and resize')
            check(rulers[2]['start'] > 0 and all(l['tick'] >= rulers[2]['start'] for l in rulers[2]['labels']),
                  prefix + ': panned ruler retains absolute time rather than rebasing labels to zero')
            (directory / (prefix + '-ruler-measurements.json')).write_text(json.dumps(rulers, indent=2) + '\n')

            terminal.resize(original_width, original_height, waveform=not workspace, hints=not workspace)
            set_tick(0)
            terminal.key(b'+' * (3 + extra_zoom_out))  # Net zero zoom steps over this suite.
            plot_shot(prefix + '-restored', ['Cursor 0 ticks'])
            (directory / (prefix + '-cursor-measurements.json')).write_text(json.dumps(measurements, indent=2) + '\n')

        def await_gate(gate):
            deadline = time.monotonic() + 12
            while not gate['ready'].is_set():
                terminal.drain(.05)
                if time.monotonic() > deadline:
                    raise AssertionError('selected w did not reach deliberately delayed byte request')
            check(gate['response_status'] == 200 and gate['response_bytes'] > 0,
                  gate['label'] + ': real upstream byte response buffered before close')
            check(gate['request']['attempt_id'] == aid and gate['request']['artifact_id'] == field(artifacts[0], 'id'),
                  gate['label'] + ': selected w captured exact attempt and artifact')
            terminal.capture(gate['label'] + '-loading', ['Waveform', field(artifacts[0], 'label'),
                             'Fetching bounded bytes'], absent=['Cursor 0 ticks'])

        def release_gate(gate):
            gate['release'].set()
            check(gate['delivered'].wait(5) and not gate['timed_out'] and not gate['client_disconnected'],
                  gate['label'] + ': response released explicitly within deadline')
            terminal.drain(.7)
            check(gate['held_ms'] >= 100 and not any(
                  r['request']['artifact_id'] == gate['request']['artifact_id'] and not r['gated']
                  for r in proxy.records[gate['record_start']:]),
                  gate['label'] + ': stale load stops without fetching remaining pages')

        terminal.key(b'j')  # Select first actual artifact, rather than opening by palette label.
        gate = proxy.arm('close-during-load')
        terminal.key(b'w')
        await_gate(gate)
        terminal.key(b'q')
        terminal.capture('closed-before-release', ['simulation-artifacts'], absent=['Back to Testing'])
        release_gate(gate)
        terminal.capture('closed-after-old-completion', ['simulation-artifacts'], absent=['Back to Testing', 'Cursor 0 ticks'])
        check(calls.read_bytes() == before, 'closing delayed load and releasing old completion has no provider side effects')

        gate = proxy.arm('replace-during-load')
        terminal.key(b'w')
        await_gate(gate)
        terminal.key(b'\x1b')
        terminal.capture('replace-back-testing', ['simulation-artifacts'], absent=['Back to Testing'])
        terminal.key(b'j')
        terminal.key(b'w')
        secondary = field(artifacts[1], 'label')
        terminal.capture('replacement-ready-before-release', ['Waveform', secondary,
                         'Cursor 0 ticks'],
                         absent=['Fetching bounded bytes'])
        identity('replacement-exact-identity-before-release', artifacts[1], 0)
        terminal.key(b':\x7f40\r')
        marker = ('alternate_outputs' if secondary == 'alternate-vcd' else 'outputs') + '.data_out'
        terminal.key(b'/' + marker.encode() + b'\r')
        terminal.capture('replacement-cursor-before-release', ['Cursor 40 ticks', marker, 'Value 0..8/8: 11010101'])
        release_gate(gate)
        terminal.capture('replacement-after-old-completion', ['Waveform', secondary,
                         'Cursor 40 ticks', marker, 'Value 0..8/8: 11010101'],
                         absent=['Fetching bounded bytes', 'Cannot open retained VCD'])
        identity('replacement-exact-identity-after-release', artifacts[1], 40)
        check(calls.read_bytes() == before, 'artifact replacement during delayed load never invokes provider')
        check(True, 'old byte completion neither resurrects closed view nor retargets replacement identity/cursor')
        terminal.key(b'q')
        terminal.capture('delayed-fences-complete', ['simulation-artifacts'], absent=['Back to Testing'])
        workspace_before = session.api(domain='workspace')
        started = time.monotonic()
        terminal.palette('Simulation: Open embedded waveform retained-vcd')
        text = terminal.capture('waveform', ['Waveform', 'Cursor 0 ticks', 'inputs.', 'Back to Testing',
                                'Case first', 'attempt', 'SHA'])
        check(not any(value in text for value in (aid, field(retained, 'id'),
                  field(retained, 'sha256')[0], session.project)),
              'normal waveform uses compact metadata; full provenance is available through inspector')
        timings = {'open_palette_to_ready_upper_bound_ms': (time.monotonic() - started) * 1000}
        terminal.palette('Color scheme: Carbon')
        terminal.capture('quick-global-palette-return', ['Cursor 0 ticks', 'Back to Testing'])
        check(True, 'Space c c global palette works in quick waveform inspection')
        status = Path('/proc/%d/status' % terminal.process.pid).read_text()
        timings['client_peak_rss_kib_after_open'] = int(next(line.split()[1] for line in status.splitlines() if line.startswith('VmHWM:')))
        terminal.key(b':')
        terminal.key(b'\x7f')  # replace initial zero
        terminal.key(b'40\r')
        terminal.capture('cursor-40', ['Cursor 40 ticks', 'window 40..'])
        started = time.monotonic()
        os.write(terminal.master, b'l')
        deadline = started + 15
        while True:
            text = terminal.drain(.01)
            if 'Cursor 41 ticks' in text:
                break
            if time.monotonic() > deadline:
                raise AssertionError('cursor key failed to repaint')
        timings['cursor_key_to_painted_screen_upper_bound_ms'] = (time.monotonic() - started) * 1000
        terminal.save('cursor-41', text)
        previous_start, previous_stop = window(text)
        terminal.key(b'+')
        text = terminal.capture('zoom', ['window 41..', 'integer tick grid'])
        zoom_start, zoom_stop = window(text)
        check(zoom_start == 41 and 0 < zoom_stop - zoom_start + 1 <= previous_stop - previous_start + 1,
              'zoom fits a smaller exact integer raster anchored at cursor')
        terminal.key(b']')
        text = terminal.capture('pan', ['Cursor 41 ticks', 'integer tick grid'])
        pan_start, pan_stop = window(text)
        ticks = zoom_stop - zoom_start + 1
        check(pan_start == zoom_start + max(1, ticks // 2) and pan_stop - pan_start + 1 == ticks,
              'pan advances half the actually displayed integer-fit window')
        terminal.key(b'/outputs.occupancy\r')
        terminal.capture('filter', ['filter: outputs.occupancy', 'outputs.occupancy'])
        terminal.capture('quick-unselected-name', ['[ ] outputs.occupancy', 'Value 0..5/5: 00000'])
        check(True, 'disabled signal name and exact value remain visible before Enter enables it')
        terminal.key(b'\r')
        terminal.capture('selection', ['Value 0..5/5: 00000', '[*] outputs.occupancy'])
        terminal.palette('Waveform: Toggle focused signal (Enter)')
        terminal.capture('quick-toggle-palette-disabled', ['[ ] outputs.occupancy', 'Value 0..5/5: 00000'])
        terminal.key(b'\r')
        terminal.capture('quick-toggle-enter-enabled', ['[*] outputs.occupancy'])
        check(True, 'waveform-specific palette command toggles without hiding disabled name; Enter restores it')
        for width, height in [(80, 24), (180, 55), (120, 40)]:
            terminal.resize(width, height)
            terminal.capture('resize-%dx%d' % (width, height), ['Waveform', 'Cursor 41 ticks', 'j/k signal',
                             'Back to Testing', 'Value 0..5/5: 00000', 'outputs.occupancy'])
            check(True, '%dx%d exposes full exact focused bus value and Back-to-Testing hint' % (width, height))
            if width == 80:
                identity('80x24-exact-identity', retained, 41, return_key=b'q')
        terminal.key(b'q')
        terminal.capture('return-testing', ['simulation-catalog', 'simulation-artifacts'], absent=['Back to Testing'])
        terminal.palette('Simulation: Open embedded waveform retained-vcd')
        terminal.capture('reopen', ['Cursor 41 ticks', 'filter: outputs.occupancy'])
        identity('reopen-exact-identity', retained, 41)

        # Real FIFO clock has a 10-tick period. Inspect the painted plot itself,
        # excluding its frame, rather than accepting a wide empty panel.
        terminal.key(b'/' + b'\x7f' * len('outputs.occupancy') + b'\r')
        terminal.resize(230, 40)
        terminal.key(b'g--')  # target 256 ticks; renderer fits an integer raster
        text = terminal.capture('wide-230-clock', ['Cursor 0 ticks', '1 cells/tick',
                                'inputs.-clock', 'Waves', 'integer tick grid'])

        def clock_plot(label):
            shot = cells.Screen(bytes(terminal.data), terminal.width, terminal.height)
            shot.save(directory / label)
            rows = shot.lines()
            top = next(i for i, row in enumerate(rows) if '┌Waves' in row)
            left = rows[top].index('┌Waves') + 1
            right = rows[top].index('┐', left)
            clock_y = top + 1  # First plotted lane, independent of picker value placement.
            lanes = [rows[y][left:right] for y in (clock_y, clock_y + 1)]
            columns = right - left
            occupied = [i for i in range(columns) if any(row[i] != ' ' for row in lanes)]
            check(columns >= 180 and len(occupied) >= columns * .95 and max(occupied) == columns - 1,
                  label + ': clock occupies at least 95% of a 180+-column plot through its last cell')
            start, stop = window(shot.text())
            check(stop - start + 1 == columns,
                  label + ': displayed tick window equals actual one-cell-per-tick plot width')
            periods = [tuple(row[x:x + 10] for row in lanes) for x in range(20, columns - 9, 10)]
            check(len(periods) >= 15 and len(set(periods)) == 1 and
                  any('┐' in row for row in periods[0]) and any('┘' in row for row in periods[0]),
                  label + ': FIFO clock repeats complete equal 10-tick periods across plot')
            check('Signals' not in rows[top], label + ': no duplicate renderer signal-name column')
            (directory / (label + '-measurements.json')).write_text(json.dumps(dict(
                terminal_width=terminal.width, terminal_height=terminal.height,
                plot_columns=columns, occupied_clock_columns=len(occupied),
                last_occupied_clock_column=max(occupied),
                exact_window=[start, stop], equal_complete_periods=len(periods),
                clock_period_ticks=10, ticks_per_cell=1), indent=2) + '\n')
            return shot, (clock_y, left, right)

        wide, plot = clock_plot('wide-230-clock-cells')
        check(wide.cells[0][0][0] == '╭' and wide.cells[-1][-1][0] == '╯',
              'default Instrument waveform uses full-viewport rounded Workbench panel')
        identity('wide-exact-identity', retained, 0)
        cursor_ruler_acceptance('quick-cursor-ruler')

        # Appearance is changed through the actual Testing palette, then inherited
        # by the reopened full-area waveform. Sample painted cells with the shared
        # ANSI oracle, including graph strokes, background and panel corners.
        appearance_samples = []
        schemes = [('Carbon', 'rgb:220,196,147', 'rgb:0,0,0'),
                   ('Slate', 'rgb:214,197,157', 'rgb:28,31,36'),
                   ('Crimson', 'rgb:255,203,107', 'rgb:12,10,10'),
                   ('Neon', 'rgb:255,207,102', 'rgb:17,22,35')]
        variants = [(scheme, None, metric, background, '╭') for scheme, metric, background in schemes]
        variants += [('Neon', preset, 'rgb:255,207,102',
                      'rgb:25,34,53' if 'Studio' in preset or 'studio' in preset else 'rgb:17,22,35', corner)
                     for preset, corner in [('B - Structured', '┌'), ('C - Minimal', None),
                                            ('D - Studio', None), ('E - Structured studio', '┌')]]
        for scheme, preset, metric, background, corner in variants:
            terminal.key(b'q')
            terminal.capture('appearance-back-' + str(len(appearance_samples)), ['simulation-artifacts'])
            terminal.palette('Color scheme: ' + scheme if preset is None else 'Appearance: ' + preset)
            terminal.palette('Simulation: Open embedded waveform retained-vcd')
            label = 'appearance-' + scheme.lower() + ('-' + preset[0].lower() if preset else '')
            terminal.capture(label, ['Cursor 0 ticks', 'integer tick grid', 'inputs.-clock', 'Back to Testing'])
            shot = cells.Screen(bytes(terminal.data), terminal.width, terminal.height)
            shot.save(directory / label)
            rows = shot.lines()
            y = next(i for i, row in enumerate(rows) if '┌Waves' in row) + 1
            graph_left = next(row.index('┌Waves') + 1 for row in rows if '┌Waves' in row)
            stroke_attrs = [attrs for row in shot.cells[y:y + 2]
                            for char, attrs in row[graph_left + 1:-2] if char in '─┐└┘┌│']
            check(stroke_attrs and all(attrs[0] == metric for attrs in stroke_attrs),
                  label + ': actual waveform strokes inherit exact scheme metric foreground')
            check(shot.cells[-2][-2][1][1] == background,
                  label + ': actual blank panel backdrop inherits scheme/preset')
            check(shot.cells[0][0][0] == corner if corner else rows[0].startswith('Waveform'),
                  label + ': selected appearance preset controls rounded/square/unframed chrome')
            appearance_samples.append(dict(scheme=scheme, preset=preset or 'A - Instrument',
                stroke_foregrounds=sorted({a[0] for a in stroke_attrs}),
                background=shot.cells[-2][-2][1][1], corner=shot.cells[0][0][0], window=window(shot.text())))
            terminal.key(b'l')
            moved = plot_shot(label + '-cursor-right', ['Cursor 1 ticks'])
            first_column = expected_cursor_column(*window(shot.text()), 0, raster_scale(shot.text()))
            next_column = expected_cursor_column(*window(moved.text()), 1, raster_scale(moved.text()))
            cursor_attr_change(check, shot, moved, first_column, next_column, label + '-visible-cursor')
            check_ruler_image(check, moved, label + '-absolute-ruler', magnitude=1, unit='ns')
            terminal.key(b'h')
            terminal.capture(label + '-cursor-restored', ['Cursor 0 ticks'])
        (directory / 'appearance-samples.json').write_text(json.dumps(appearance_samples, indent=2) + '\n')
        identity('themed-exact-identity', retained, 0)
        terminal.key(b'\x1b')
        terminal.capture('escape-testing', ['simulation-artifacts'], absent=['Back to Testing'])
        check(calls.read_bytes() == before, 'open/navigation/resize/close/reopen never invokes provider')
        check(len(field(session.api(), 'attempts')) == 1, 'waveform investigation creates no attempts')
        check(session.api(domain='workspace') == workspace_before, 'return preserves exact Testing registry, context and selection')
        check(True, 'PTY cursor/filter/selection/pan/zoom/resize/return and retained navigation accepted')
        (directory / 'timings.json').write_text(json.dumps(timings, indent=2) + '\n')

        # Dedicated workspace extension. Seed a second real fixture job with a
        # deliberately different stdout marker; no navigation may borrow its logs.
        terminal.palette('Appearance: A - Instrument')
        terminal.palette('Color scheme: Carbon')
        second_launch = ['Launch', ['submission_key', 'unrelated-replay'],
            ['discovery_digest', field(catalog, 'discovery_digest')[0]],
            ['selection', [('suite', 'fixture'), ('cases', ['second']), ('seed', '99'),
                           ('parameters', []), ('asic_inputs', [])]]]
        second_snapshot = session.api(operation=second_launch)
        second_id = next(field(a, 'id') for a in field(second_snapshot, 'attempts') if field(a, 'id') != aid)
        second_detail = session.done(second_id)
        investigation_calls = calls.read_bytes()
        terminal.resize(230, 55, waveform=False)
        terminal.palette('Simulation: Reopen ' + aid + ' fixture')
        # Explicitly reselect the first row regardless of whether Reopen reset it.
        terminal.key(b'kkkk')
        registry_before_w = session.api(domain='workspace')
        terminal.key(b'W')
        terminal.capture('workspace-created', ['Waveforms', 'Session', 'Signals', 'Waves', 'VCD picker', 'Logs',
                         'Cursor 0 ticks'], absent=['Esc/q Back to Testing'])

        def workspace_registry():
            return session.api(domain='workspace')

        def wave_workspace(snapshot):
            found = [w for w in field(snapshot, 'workspaces') if field(w, 'preset') == ['waveforms']]
            check(len(found) == 1, 'exactly one actual Waveforms preset workspace exists')
            return found[0]

        registry = workspace_registry()
        wave_workspace_id = field(wave_workspace(registry), 'id')
        pane_kinds = {'waveform-session', 'waveform-signals', 'waveform-waves', 'waveform-picker', 'waveform-logs'}
        pane_tiles = {field(t, 'kind'): t for t in field(registry, 'tiles')
                      if field(t, 'workspace') == wave_workspace_id and field(t, 'kind') in pane_kinds}
        check(set(pane_tiles) == pane_kinds and len({field(t, 'id') for t in pane_tiles.values()}) == 5 and
              len([t for t in field(registry, 'tiles') if field(t, 'workspace') == wave_workspace_id]) == 6,
              'W creates five independent registered Session/Signals/Waves/Picker/Logs panes plus tabs')
        check(len(field(registry, 'workspaces')) == len(field(registry_before_w, 'workspaces')) + 1 and
              all(w in field(registry, 'workspaces') for w in field(registry_before_w, 'workspaces')),
              'W adds a real workspace and preserves existing Testing/Overview/Timing identities')

        def focus_pane(title):
            for _ in range(7):
                shot = cells.Screen(bytes(terminal.data), terminal.width, terminal.height)
                for y, row in enumerate(shot.lines()):
                    token = '╭ ' + title + ' '
                    if token in row and shot.cells[y][row.index(token)][1][0] == 'rgb:151,177,226':
                        return
                terminal.key(b'\t')
            terminal.save('focus-failed-' + title.replace(' ', '-'), terminal.drain())
            raise AssertionError('Tab cannot independently focus ' + title)

        def mutate_workspace(mutation):
            current = workspace_registry()
            return session.api(domain='workspace', operation=['Mutate',
                ['expected_revision', field(current, 'revision')], ['mutation', mutation]])

        def pane_image(title, label=None):
            shot = cells.Screen(bytes(terminal.data), terminal.width, terminal.height)
            if label:
                shot.save(directory / label)
            for top, row in enumerate(shot.lines()):
                token = '╭ ' + title + ' '
                if token in row:
                    left = row.index(token)
                    right = row.index('╮', left)
                    bottom = next(y for y in range(top + 1, terminal.height)
                                  if shot.cells[y][left][0] == '╰')
                    body = [line[left + 1:right] for line in shot.lines()[top + 1:bottom]]
                    return shot, (left, top, right, bottom), body
            raise AssertionError('missing actual ' + title + ' panel')

        def quiet_hints(label):
            text = terminal.capture(label, ['Session', 'Signals', 'Waves', 'VCD picker', 'Logs'],
                absent=['Enter toggle', 'j/k browse', 'j/k signal', 'Space c c commands',
                        'Enter explicitly retargets'])
            check(True, label + ': idle per-pane hints and global shortcut footer are hidden by default')
            return text

        def inline_values(label, minimum=12, expected=None, both_states=True):
            _, _, body = pane_image('Signals', label)
            pattern = re.compile(r'(?:>| )\[(?P<enabled>[ *])\]\s+(?P<name>.*?)\s+\[(?P<width>\d+)\]\s+(?:=\s*)?(?P<value>[01xz]+)\s*$')
            matched = [pattern.search(row) for row in body]
            matched = [m for m in matched if m]
            check(len(matched) >= minimum and (not both_states or {m['enabled'] for m in matched} == {'*', ' '}),
                  label + ': inline rows include enabled and disabled signals with exact values')
            check(len({m.start('value') for m in matched}) == 1 and
                  len({m.start('width') for m in matched}) == 1,
                  label + ': name/width and value columns have equal terminal-cell origins')
            longest = max(len(m['name'].rstrip()) for m in matched)
            first = matched[0]
            check(first.start('width') - 1 == first.start('name') + longest + 1 and
                  first.start('value') - first.end('width') - 1 == 3,
                  label + ': actual longest displayed name has one-cell gap before width and minimal value separator')
            expected = expected or {'inputs.-clock': '1', 'inputs.push_data': '00000000',
                                    'outputs.data_out': '00000000', 'outputs.occupancy': '00000'}
            found = {m['name'].strip(): m['value'] for m in matched}
            check(all(found.get(name) == value for name, value in expected.items()),
                  label + ': inline scalar/bus values agree with retained FIFO at tick zero')
            (directory / (label + '-alignment.json')).write_text(json.dumps([
                dict(name=m['name'].strip(), value=m['value'], enabled=m['enabled'],
                     width_column=m.start('width'), value_column=m.start('value'))
                for m in matched], indent=2) + '\n')
            return dict(longest_name_cells=longest, width_column=first.start('width'),
                        value_column=first.start('value'), signal_rows=len(matched))

        def compact_spacing(label):
            _, rect, body = pane_image('Signals', label)
            pattern = re.compile(r'(?:>| )\[[ *]\]\s+(?P<name>.*?)\s+\[(?P<width>\d+)\]\s+=\s*(?P<value>[01xz]+…?)\s*$')
            matched = [pattern.search(row) for row in body]
            matched = [m for m in matched if m]
            check(len(matched) >= 4 and len({m.start('value') for m in matched}) == 1 and
                  len({m.start('width') for m in matched}) == 1,
                  label + ': narrow inline rows retain aligned width/value columns, including explicit value elision')
            gaps = [m.start('width') - 1 - (m.start('name') + len(m['name'].rstrip())) for m in matched]
            check(min(gaps) == 1, label + ': names consume their measured column without a proportional blank gap')
            result = dict(terminal_width=terminal.width, signals_width=rect[2] - rect[0] + 1,
                          width_column=matched[0].start('width'), value_column=matched[0].start('value'),
                          minimum_name_gap=min(gaps), signal_rows=len(matched))
            (directory / (label + '-spacing.json')).write_text(json.dumps(result, indent=2) + '\n')
            return result

        def stacked_values(label, names=('inputs.-clock', 'inputs.push_data', 'outputs.data_out')):
            _, _, body = pane_image('Signals', label)
            found = []
            for i, row in enumerate(body[:-1]):
                if any(name + ' [' in row for name in names):
                    check('=' not in row and bool(re.search(r'=\s*[01xz]+\s*$', body[i + 1])),
                          label + ': named signal has its exact value on the following stacked row')
                    found.append(row)
            check(len(found) == len(names), label + ': stacked opt-in preserves scalar and bus names')

        def exact_signal_scope(label, scope):
            # Inline names may be intentionally elided in a narrow tile. Inspect
            # the actual full model names/values at zoom, not a typed filter query.
            focus_pane('Signals')
            terminal.palette('Zoom focused tile')
            terminal.capture(label, [scope + '.data_out', scope + '.occupancy'])
            inline_values(label, expected={scope + '.data_out': '00000000', scope + '.occupancy': '00000'})
            terminal.palette('Unzoom workspace')

        def session_metadata(label, artifact, loaded=True):
            _, rect, body = pane_image('Session', label)
            text = ' '.join(row.strip() for row in body)
            attempt = field(artifact, 'attempt_id')
            compact_id = attempt[:4] + '…' + attempt[-4:]
            compact = rect[2] - rect[0] - 1 < 80
            if compact or loaded:
                check(compact_id in text and attempt not in text,
                      label + ': compact attempt ID is literally first four and last four characters')
            name = field(artifact, 'label')
            label_visible = name in text
            if compact and not label_visible:
                rendered_label = body[0].replace(compact_id, '').strip(' ·')
                label_visible = (rendered_label.endswith('…') and len(rendered_label) >= 5
                                 and name.startswith(rendered_label[:-1]))
            check(label_visible and field(artifact, 'case_id')[0] in text,
                  label + ': Session preserves pinned case and exact or explicitly elided artifact label')
            if loaded:
                check('1 ns' in text and re.search(r'ready|loaded', text, re.I) is not None,
                      label + ': Session exposes actual loaded status and retained time units')
            (directory / (label + '-session.txt')).write_text(text + '\n')
            return text

        def workspace_geometry(label, expected_signals_width):
            shot, session_rect, _ = pane_image('Session', label)
            _, signals_rect, _ = pane_image('Signals')
            _, waves_rect, _ = pane_image('Waves')
            check('Overview' in shot.lines()[0] and 'Waveforms' in shot.lines()[0] and
                  'run none' not in shot.text() and 'Linked: Main' not in shot.text(),
                  label + ': tabs are first and Waveforms has no above-tabs global banner')
            check(session_rect[1] == 1 and session_rect[3] - session_rect[1] + 1 == 4 and
                  session_rect[0] == signals_rect[0] == 0 and session_rect[2] == signals_rect[2] and
                  signals_rect[1] == session_rect[3] + 1,
                  label + ': four-row Session is directly above Signals in the same left column')
            check(signals_rect[2] - signals_rect[0] + 1 == expected_signals_width and
                  waves_rect[1] == session_rect[1] and waves_rect[3] == signals_rect[3] and
                  signals_rect[2] + 1 == waves_rect[0] and waves_rect[2] == terminal.width - 1,
                  label + ': left 1:4/minimum-24 column and Waves spanning both left rows fill viewport')
            (directory / (label + '-geometry.json')).write_text(json.dumps(dict(
                terminal_width=terminal.width, terminal_height=terminal.height,
                session=session_rect, signals=signals_rect, waves=waves_rect,
                left_width=signals_rect[2] - signals_rect[0] + 1,
                waves_width=waves_rect[2] - waves_rect[0] + 1), indent=2) + '\n')

        def workspace_identity(label, artifact, job, cursor=0):
            focus_pane('Waves')
            terminal.palette('Zoom focused tile')
            terminal.palette('Waveform: Inspect exact identity')
            terminal.capture(label, ['Exact identity', 'SHA256', 'Captured logs'])
            _, _, body = pane_image('Waves', label)
            text = ''.join(row.strip() for row in body)
            expected = ['Project ' + original_project, 'Attempt ' + field(artifact, 'attempt_id'),
                        'Case ' + field(artifact, 'case_id')[0], 'Artifact ' + field(artifact, 'id'),
                        'SHA256 ' + field(artifact, 'sha256')[0], job, pin_instance]
            check(all(value in text for value in expected),
                  label + ': workspace inspector exposes exact pinned project/attempt/case/artifact/digest/job/instance')
            terminal.key(b'\x1b')
            terminal.capture(label + '-return', ['VCD unavailable'] if cursor is None else ['Cursor %d ticks' % cursor],
                             absent=['Exact identity'])
            terminal.palette('Unzoom workspace')

        def persisted_pin(label, expected_artifact, expected_job, recorded_project=None):
            deadline = time.monotonic() + 12
            while True:
                for path in (directory / 'client-state').rglob('waveforms-*.sexp'):
                    saved = dict(wire.parse(path.read_text()))
                    for pref in saved['pins']:
                        pref = dict(pref)
                        pin = dict(pref['pin'])
                        if pref['workspace'] == wave_workspace_id and pin['artifact'] == expected_artifact:
                            check(dict(pref['members']) == {field(t, 'id'): kind for kind, t in pane_tiles.items()
                                  if kind != 'waveform-session'},
                                  label + ': pin persists exact four coordinated tile IDs, excluding metadata-only Session')
                            log = pin['log']
                            source = dict(log[1:]) if log[0] == 'Job' else {}
                            check(source.get('job') == expected_job and
                                  source.get('instance_id') == pin_instance,
                                  label + ': logs pinned to exact attempt job and daemon instance')
                            check(pin['project'] == (recorded_project or original_project),
                                  label + ': recorded project provenance remains exact')
                            (directory / (label + '-pin.sexp')).write_text(path.read_text())
                            return pin
                if time.monotonic() > deadline:
                    raise AssertionError(label + ': exact captured waveform pin was not persisted')
                terminal.drain(.1)

        original_project, pin_instance = session.project, session.metadata['instance_id']
        first_job = field(detail, 'job')
        first_pin_artifact = artifacts[0]
        persisted_pin('workspace-created', first_pin_artifact, first_job)
        focus_pane('Signals')
        terminal.palette('Zoom focused tile')
        terminal.capture('workspace-all-disabled-names', ['[ ] outputs.occupancy',
                         '[ ] outputs.pop_accept', '[ ] outputs.push_accept'])
        check(True, 'unselected signal names remain in the dedicated Signals list before enabling')
        terminal.palette('Unzoom workspace')
        terminal.palette('Color scheme: Carbon')
        terminal.capture('workspace-global-palette-return', ['Signals', 'Waves', 'VCD picker', 'Logs'])
        terminal.palette('Waveform: Open dedicated Waveforms workspace')
        terminal.capture('workspace-specific-palette-return', ['Signals', 'Waves', 'VCD picker', 'Logs'])
        check(True, 'Space c c palette works while independent Waveforms tiles are active')

        quiet_hints('workspace-default-quiet-hints')
        workspace_geometry('workspace-session-230x55', 46)
        session_metadata('workspace-session-primary', first_pin_artifact)
        workspace_identity('workspace-session-exact-provenance', first_pin_artifact, first_job)
        inline_values('workspace-default-inline')
        for width, height, signals_width in [(80, 24, 24), (120, 40, 24), (230, 55, 46)]:
            terminal.resize(width, height, waveform=False, hints=False)
            quiet_hints('workspace-quiet-%dx%d' % (width, height))
            workspace_geometry('workspace-geometry-%dx%d' % (width, height), signals_width)
            session_metadata('workspace-compact-session-%dx%d' % (width, height), first_pin_artifact)
            compact_spacing('workspace-compact-inline-%dx%d' % (width, height))

        # On a wide Signals viewport the name field must follow the actual
        # longest filtered name, not grow proportionally with terminal width.
        focus_pane('Signals')
        terminal.palette('Zoom focused tile')
        zoom_spacing = []
        for width in (80, 120, 230):
            terminal.resize(width, 55, waveform=False, hints=False)
            terminal.capture('inline-zoom-%d-ready' % width, ['[ ] outputs.occupancy'])
            zoom_spacing.append(inline_values('inline-zoom-%d' % width))
        check(len({m['value_column'] for m in zoom_spacing}) == 1 and
              len({m['longest_name_cells'] for m in zoom_spacing}) == 1,
              '80/120/230-column Signals viewports keep the same compact name/value origin for the same filtered names')
        terminal.key(b'/clock\r')
        terminal.capture('inline-short-filter-ready', ['1 matching', 'inputs.-clock'])
        short_spacing = inline_values('inline-short-filter', minimum=1,
                                      expected={'inputs.-clock': '1'}, both_states=False)
        check(zoom_spacing[-1]['value_column'] - short_spacing['value_column'] ==
              zoom_spacing[-1]['longest_name_cells'] - len('inputs.-clock'),
              'filtering to a shorter actual name moves the value origin left by exactly the removed name width')
        terminal.key(b'/' + b'\x7f' * len('clock') + b'\r')
        terminal.capture('inline-filter-cleared', ['14 matching'])
        (directory / 'compact-inline-width-matrix.json').write_text(json.dumps(dict(
            widths=[80, 120, 230], unfiltered=zoom_spacing, short_filter=short_spacing), indent=2) + '\n')
        terminal.palette('Unzoom workspace')

        focus_pane('Signals')
        terminal.palette('Toggle focused tile hints')
        terminal.capture('workspace-hints-explicitly-enabled', ['Enter toggle', 'Space c c commands'])
        terminal.palette('Toggle focused tile hints')
        quiet_hints('workspace-hints-explicitly-disabled')
        check(True, 'focused tile hint override enables help and idle host footer without disabling global palette')

        transport_before_layout = len(proxy.records)
        terminal.palette('Waveform: Signal values: Stacked (two rows per signal)')
        terminal.capture('workspace-stacked-selected', ['inputs.-clock [1]', '= 00000000'])
        stacked_values('workspace-stacked-opt-in')
        terminal.palette('Switch to Overview')
        terminal.palette('Switch to Waveforms')
        stacked_values('workspace-stacked-after-navigation')
        terminal.palette('Waveform: Signal values: Inline (aligned columns; default)')
        inline_values('workspace-inline-restored')
        check(len(proxy.records) == transport_before_layout and calls.read_bytes() == investigation_calls,
              'changing inline/stacked placement and navigating does not reload bytes or invoke provider')
        persisted_pin('workspace-placement-keeps-pin', first_pin_artifact, first_job)

        # Notty's installed decoder preserves byte 08 as Ctrl-Backspace and
        # byte 17 as Ctrl-W. CSI-u encodings are not decoded by this dependency.
        focus_pane('Signals')
        terminal.palette('Zoom focused tile')

        def filter_query(label, expected):
            terminal.capture(label, ['/ '])
            _, _, body = pane_image('Signals', label)
            prompts = [row.strip()[2:].split(' · Enter/Esc', 1)[0].strip()
                       for row in body if row.strip().startswith('/ ')]
            check(prompts == [expected],
                  label + ': actual edit prompt retains exact query after word deletion')

        terminal.key(b'/outputs.occupancy temporary')
        filter_query('ctrl-backspace-before', 'outputs.occupancy temporary')
        for index, expected in enumerate(('outputs.occupancy', 'outputs.', '')):
            terminal.key(b'\x08')
            filter_query('ctrl-backspace-%d' % index, expected)
        terminal.key(b'\r')
        terminal.capture('ctrl-backspace-applied', ['14 matching'])
        terminal.key(b'/clock temporary')
        terminal.key(b'\x17')
        filter_query('ctrl-w-first-word', 'clock')
        terminal.key(b'\x17')
        filter_query('ctrl-w-empty', '')
        terminal.key(b'\r')
        terminal.key(b'/clockx\x7f')
        filter_query('ordinary-backspace-one-character', 'clock')
        terminal.key(b'\r')
        terminal.capture('ordinary-backspace-filter-applied', ['1 matching', 'inputs.-clock'])
        terminal.key(b'/\x17\r')
        terminal.capture('filter-editing-restored-all-names', ['14 matching', '[ ] outputs.occupancy'])
        terminal.palette('Unzoom workspace')
        quiet_hints('workspace-after-filter-editing')
        (directory / 'filter-key-sequences.json').write_text(json.dumps(dict(
            ctrl_backspace_hex='08', ctrl_w_fallback_hex='17', ordinary_backspace_hex='7f',
            csi_u_supported_by_installed_notty=False), indent=2) + '\n')
        check(calls.read_bytes() == investigation_calls, 'filter editing with hidden hints has no provider side effects')
        focus_pane('Waves')
        cursor_ruler_acceptance('workspace-cursor-ruler', workspace=True)
        quiet_hints('workspace-ruler-is-not-idle-help')

        focus_pane('Signals')
        terminal.key(b'/outputs.occupancy\r')
        terminal.capture('workspace-disabled-signal', ['[ ] outputs.occupancy', '= 00000'])
        terminal.key(b'\r')
        terminal.capture('workspace-enabled-signal', ['[*] outputs.occupancy'])
        check(True, 'Signals lists disabled names; Enter enables without consuming global Space prefix')
        focus_pane('Waves')
        terminal.key(b'l')
        terminal.capture('workspace-waves-focused-navigation', ['Cursor 1 ticks', '[*] outputs.occupancy'])
        focus_pane('Logs')
        terminal.palette('Zoom focused tile')
        terminal.capture('workspace-exact-first-job-logs', ['WB028_LOG_SEED=42', 'WB028_LOG_ATTEMPT=' + aid],
                         absent=['WB028_LOG_SEED=99'])
        check(field(wave_workspace(workspace_registry()), 'zoomed_tile') == [field(pane_tiles['waveform-logs'], 'id')],
              'independent Logs focus/zoom targets its actual registered tile')
        terminal.palette('Unzoom workspace')
        check(True, 'Logs contains actual matching provider stdout, never unrelated selected job stdout')

        # Hide is a tile operation, not a pin invalidation or a different viewer.
        mutate_workspace(['Set_tile_hidden', ['tile', field(pane_tiles['waveform-signals'], 'id')], ['hidden', 'true']])
        terminal.capture('workspace-signals-hidden', ['Waves', 'VCD picker', 'Logs'], absent=['╭ Signals '])
        persisted_pin('workspace-hidden', first_pin_artifact, first_job)
        mutate_workspace(['Set_tile_hidden', ['tile', field(pane_tiles['waveform-signals'], 'id')], ['hidden', 'false']])
        terminal.capture('workspace-signals-restored', ['Signals', 'Waves'])
        focus_pane('Signals')
        terminal.palette('Zoom focused tile')
        terminal.capture('workspace-delay-full-name-viewport', ['[*] outputs.occupancy', '= 00000'])
        gate = proxy.arm('workspace-picker-stale-load')
        terminal.palette('Waveform: Select VCD alternate-vcd')
        alternate = artifacts[1]
        deadline = time.monotonic() + 12
        while not gate['ready'].is_set():
            terminal.drain(.05)
            if time.monotonic() > deadline:
                raise AssertionError('workspace picker did not reach delayed alternate VCD bytes')
        check(gate['response_status'] == 200 and gate['request']['artifact_id'] == field(alternate, 'id')
              and gate['request']['attempt_id'] == aid,
              'workspace delayed picker captures exact alternate artifact and attempt')
        terminal.capture('workspace-picker-alternate-loading', ['Fetching bounded bytes'])
        terminal.palette('Waveform: Select VCD retained-vcd')
        persisted_pin('workspace-picker-replacement-before-release', first_pin_artifact, first_job)
        terminal.capture('workspace-picker-replacement-before-release', ['[ ] outputs.occupancy'],
                         absent=['alternate_outputs.', 'Fetching bounded bytes'])
        release_gate(gate)
        terminal.capture('workspace-picker-replacement-after-old-completion', ['[ ] outputs.occupancy'],
                         absent=['alternate_outputs.', 'Fetching bounded bytes', 'WB028_LOG_SEED=99'])
        persisted_pin('workspace-picker-replacement-after-old-completion', first_pin_artifact, first_job)
        terminal.palette('Unzoom workspace')
        terminal.capture('workspace-picker-replacement-matching-logs', ['WB028_LOG_SEED=42', 'retained-vcd'],
                         absent=['WB028_LOG_SEED=99'])
        check(calls.read_bytes() == investigation_calls,
              'stale workspace picker completion cannot retarget pin, signals or logs and invokes no provider')
        focus_pane('VCD picker')
        terminal.key(b'j\r')
        persisted_pin('workspace-picker-retarget', alternate, first_job)
        terminal.capture('workspace-picker-retarget', ['alternate-vcd', 'WB028_LOG_SEED=42'],
                         absent=['WB028_LOG_SEED=99'])
        exact_signal_scope('workspace-picker-exact-alternate-model', 'alternate_outputs')
        check(True, 'explicit picker retarget coordinates Signals/Waves identity and matching attempt Logs')
        alternate_session = session_metadata('workspace-session-alternate', alternate)

        terminal.palette('Switch to Testing')
        terminal.palette('Simulation: Newest history page')
        terminal.capture('testing-explicit-newest-history', [second_id, 'fixture seed=99'])
        terminal.palette('Simulation: Reopen ' + second_id + ' fixture')
        terminal.palette('Switch to Overview')
        terminal.capture('workspace-switch-overview', ['Overview'], absent=['╭ Signals '])
        terminal.palette('Switch to Waveforms')
        terminal.capture('workspace-switch-back-pinned', ['alternate-vcd', 'WB028_LOG_SEED=42'],
                         absent=['WB028_LOG_SEED=99'])
        persisted_pin('workspace-navigation-keeps-pin', alternate, first_job)
        check(session_metadata('workspace-session-after-testing-change', alternate) == alternate_session,
              'Session metadata remains pinned when Testing changes to a different attempt and case')
        workspace_identity('workspace-session-exact-after-testing-change', alternate, first_job)
        check(True, 'Testing attempt changes and cross-workspace navigation cannot retarget pinned artifact/logs')

        # Return to Testing (its original Artifacts focus), select the second
        # attempt's retained VCD, and prove W reuses the registered desk.
        terminal.palette('Switch to Testing')
        terminal.key(b'kkkk')
        terminal.key(b'W')
        terminal.capture('workspace-W-reused', ['Signals', 'Waves', 'VCD picker', 'Logs'])
        second_artifacts = field(second_detail, 'artifacts')
        second_artifact = second_artifacts[0]
        second_job = field(second_detail, 'job')
        persisted_pin('workspace-W-reused', second_artifact, second_job)
        session_metadata('workspace-session-second-case', second_artifact)
        after_reuse = workspace_registry()
        check(field(wave_workspace(after_reuse), 'id') == wave_workspace_id and
              len(field(after_reuse, 'workspaces')) == len(field(registry, 'workspaces')) and
              {field(t, 'id') for t in field(after_reuse, 'tiles') if field(t, 'workspace') == wave_workspace_id}
              == {field(t, 'id') for t in field(registry, 'tiles') if field(t, 'workspace') == wave_workspace_id},
              'W reuses existing workspace and all independent tile IDs')
        focus_pane('Logs')
        terminal.palette('Zoom focused tile')
        terminal.capture('workspace-second-job-logs', ['WB028_LOG_SEED=99', 'WB028_LOG_ATTEMPT=' + second_id],
                         absent=['WB028_LOG_SEED=42'])
        terminal.palette('Unzoom workspace')
        focus_pane('VCD picker')
        terminal.key(b'j\r')
        second_artifact = second_artifacts[1]
        persisted_pin('workspace-second-picker', second_artifact, second_job)
        terminal.capture('workspace-second-picker-logs', ['WB028_LOG_SEED=99', 'alternate-vcd'],
                         absent=['WB028_LOG_SEED=42'])
        exact_signal_scope('workspace-second-picker-exact-model', 'alternate_outputs')
        check(calls.read_bytes() == investigation_calls and len(field(session.api(), 'attempts')) == 2,
              'workspace create/reuse/focus/hide/zoom/picker/navigation never invokes or cancels simulations')
        focus_pane('Signals')
        terminal.palette('Waveform: Signal values: Stacked (two rows per signal)')
        stacked_values('workspace-second-stacked-before-restart',
                       names=('inputs.-clock', 'inputs.push_data', 'alternate_outputs.data_out'))

        def restart_client(label):
            nonlocal terminal
            terminal.save(label + '-before-close', terminal.drain())
            terminal.close()
            terminal = Terminal(session)
            terminal.capture(label + '-startup', ['Overview', 'Waveforms'])
            terminal.palette('Switch to Waveforms')

        restart_client('client-restart')
        terminal.capture('client-restart-restored', ['Session', 'Signals', 'Waves', 'WB028_LOG_SEED=99'],
                         absent=['WB028_LOG_SEED=42'])
        persisted_pin('client-restart-restored', second_artifact, second_job)
        session_metadata('client-restart-session-pinned', second_artifact)
        stacked_values('client-restart-stacked-persisted', names=('inputs.-clock',))
        focus_pane('Signals')
        terminal.palette('Waveform: Signal values: Inline (aligned columns; default)')
        terminal.palette('Zoom focused tile')
        inline_values('client-restart-inline-restored', expected={'inputs.-clock': '1',
                      'alternate_outputs.data_out': '00000000', 'alternate_outputs.occupancy': '00000'})
        terminal.palette('Unzoom workspace')
        check(True, 'fresh client restores exact persisted pin and reloads retained waveform plus matching logs')

        # Only private captured copies are removed. Keep other artifacts/jobs
        # intact so a fallback/substitution would be observable.
        terminal.close()
        terminal = None
        wanted_digest = field(second_artifact, 'sha256')[0]
        removed = []
        for path in (directory / 'state' / 'simulation-v1').rglob('*.bytes'):
            if second_id in path.parts and hashlib.sha256(path.read_bytes()).hexdigest() == wanted_digest:
                removed.append(str(path))
                path.unlink()
        check(len(removed) == 1, 'fixture removes only exact pinned retained artifact copy')
        (directory / 'removed-private-artifact.json').write_text(json.dumps(removed) + '\n')
        terminal = Terminal(session)
        terminal.capture('missing-restart-startup', ['Overview', 'Waveforms'])
        terminal.palette('Switch to Waveforms')
        terminal.capture('missing-restart-unavailable', ['VCD unavailable', 'Logs', 'WB028_LOG_SEED=99', '>* alternate-vcd'],
                         absent=['WB028_LOG_SEED=42', 'Cursor 0 ticks'])
        persisted_pin('missing-restart-exact-identity', second_artifact, second_job)
        session_metadata('missing-restart-session-compact-pin', second_artifact, loaded=False)
        focus_pane('Session')
        terminal.palette('Zoom focused tile')
        check('Unavailable' in session_metadata('missing-restart-session-pinned', second_artifact, loaded=False),
              'unavailable Session retains exact pinned case/label instead of current Testing metadata')
        terminal.palette('Unzoom workspace')
        check(True, 'missing retained data restores as unavailable without substituting another artifact')

        terminal.close()
        terminal = None
        session.stop()
        check(hashlib.sha256(args.daemon.read_bytes()).hexdigest() == binary_hashes['daemon'],
              'restarted daemon uses the same prebuilt executable bytes')
        session.start()
        proxy.upstream = session.url
        session.url = proxy.url
        new_catalog = session.discover()
        unrelated = session.api(operation=['Launch', ['submission_key', 'new-daemon-unrelated'],
            ['discovery_digest', field(new_catalog, 'discovery_digest')[0]],
            ['selection', [('suite', 'fixture'), ('cases', ['first']), ('seed', '777'),
                           ('parameters', []), ('asic_inputs', [])]]])
        unrelated_id = next(field(a, 'id') for a in field(unrelated, 'attempts')
                            if field(a, 'id') not in (aid, second_id))
        session.done(unrelated_id)
        after_restart_calls = calls.read_bytes()
        terminal = Terminal(session)
        terminal.capture('daemon-restart-startup', ['Overview', 'Waveforms'])
        terminal.palette('Switch to Waveforms')
        terminal.capture('daemon-restart-unavailable-stale-logs', ['VCD unavailable', 'Logs unavailable', '>* alternate-vcd'],
                         absent=['WB028_LOG_SEED=777', 'WB028_LOG_SEED=42', 'WB028_LOG_SEED=99'])
        persisted_pin('daemon-restart-recorded-identity', second_artifact, second_job)
        workspace_identity('daemon-restart-exact-unavailable-session', second_artifact, second_job, cursor=None)
        check(calls.read_bytes() == after_restart_calls,
              'daemon restart restoration does not replay simulations or substitute a new daemon job log')
        check(field(wave_workspace(workspace_registry()), 'id') == wave_workspace_id,
              'real Waveforms registry workspace survives daemon and client restart')

        # Simulate a retained pre-Session/custom desk using only public registry
        # mutations. Metadata membership must not invalidate the original pin.
        testing_id = next(field(w, 'id') for w in field(workspace_registry(), 'workspaces')
                          if field(w, 'preset') == ['testing'])
        old_session_id = field(pane_tiles['waveform-session'], 'id')
        mutate_workspace(['Move_tile', ['tile', old_session_id], ['workspace', testing_id]])
        mutate_workspace(['Set_tile_hidden', ['tile', old_session_id], ['hidden', 'true']])
        mutate_workspace(['Set_tile_hidden', ['tile', field(pane_tiles['waveform-signals'], 'id')], ['hidden', 'true']])
        custom_geometry = [('x', 3), ('y', 7), ('width', 71), ('height', 19)]
        mutate_workspace(['Resize_tile', ['tile', field(pane_tiles['waveform-waves'], 'id')], ['geometry', custom_geometry]])
        before_extra = {field(t, 'id') for t in field(workspace_registry(), 'tiles')}
        after_extra = mutate_workspace(['Create_tile', ['workspace', wave_workspace_id],
            ['kind', 'custom-waveform-note'], ['geometry', [('x', 11), ('y', 2), ('width', 29), ('height', 8)]]])
        extra = next(t for t in field(after_extra, 'tiles') if field(t, 'id') not in before_extra)
        mutate_workspace(['Set_tile_hidden', ['tile', field(extra, 'id')], ['hidden', 'true']])
        mutate_workspace(['Set_zoom', ['workspace', wave_workspace_id],
                          ['tile', [field(pane_tiles['waveform-picker'], 'id')]]])
        legacy = workspace_registry()
        (directory / 'legacy-custom-before-upgrade.sexp').write_text(wire.sexp(legacy) + '\n')
        persisted_pin('legacy-without-session-keeps-pin', second_artifact, second_job)
        restart_client('legacy-custom-restart')
        terminal.capture('legacy-custom-restored-without-session', ['VCD picker'], absent=['╭ Session '])
        check(workspace_registry() == legacy,
              'restart does not automatically add Session or reset legacy custom geometry/hidden state/zoom')
        persisted_pin('legacy-custom-restored-pin', second_artifact, second_job)
        byte_reads_before_upgrade = len(proxy.records)
        terminal.palette('Apply preset: Waveforms (add missing tiles)')
        upgraded = workspace_registry()
        check(all(t in field(upgraded, 'tiles') for t in field(legacy, 'tiles')),
              'additive Apply preset preserves every existing tile identity, geometry, binding and hidden flag')
        check(field(wave_workspace(upgraded), 'zoomed_tile') == field(wave_workspace(legacy), 'zoomed_tile') and
              field(wave_workspace(upgraded), 'context') == field(wave_workspace(legacy), 'context'),
              'additive Session upgrade preserves custom zoom and context')
        new_sessions = [t for t in field(upgraded, 'tiles') if field(t, 'workspace') == wave_workspace_id
                        and field(t, 'kind') == 'waveform-session']
        check(len(new_sessions) == 1 and field(new_sessions[0], 'id') != old_session_id,
              'explicit Apply adds exactly the missing Session tile to an existing Waveforms desk')
        pane_tiles['waveform-session'] = new_sessions[0]
        terminal.palette('Layout: Fit tiles to window')
        terminal.palette('Unzoom workspace')
        terminal.capture('legacy-upgraded-fit', ['Session', 'Waves', 'VCD picker', 'Logs'], absent=['╭ Signals '])
        persisted_pin('legacy-upgraded-pin-identical', second_artifact, second_job)
        check(len(proxy.records) == byte_reads_before_upgrade,
              'metadata-only Session migration and Fit do not reload or retarget the pinned artifact')
        mutate_workspace(['Set_tile_hidden', ['tile', field(pane_tiles['waveform-signals'], 'id')], ['hidden', 'false']])
        terminal.capture('legacy-upgraded-five-panes-visible', ['Session', 'Signals', 'Waves', 'VCD picker', 'Logs'])
        workspace_geometry('legacy-upgraded-fit-120x40', 24)
        check(calls.read_bytes() == after_restart_calls,
              'legacy restart and explicit additive layout upgrade invoke no providers or simulation jobs')
    finally:
        if terminal:
            terminal.close()
        if proxy:
            proxy.close()
        session.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', type=Path)
    parser.add_argument('--vcd', type=Path, action='append', default=[])
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--daemon', type=Path, help='optional prebuilt private daemon for PTY acceptance')
    parser.add_argument('--client', type=Path, help='optional prebuilt terminal; requires --daemon')
    parser.add_argument('--pty-only', action='store_true', help='run only terminal checks; requires --vcd, --daemon, --client')
    args = parser.parse_args()
    if args.pty_only:
        if not (args.vcd and args.daemon and args.client):
            parser.error('--pty-only requires --vcd, --daemon and --client')
    elif not args.probe:
        parser.error('--probe is required unless --pty-only')
    if args.probe:
        args.probe = args.probe.resolve()
    if bool(args.daemon) != bool(args.client):
        parser.error('--daemon and --client must be supplied together')
    if args.daemon:
        args.daemon, args.client = args.daemon.resolve(), args.client.resolve()
    evidence = args.evidence or Path(tempfile.mkdtemp(prefix='wb028-accept-', dir='/tmp/opencode'))
    evidence.mkdir(parents=True, exist_ok=True)
    print('WB028 evidence: ' + str(evidence), flush=True)
    results, checks = [], []

    def check(ok, label):
        checks.append(dict(passed=bool(ok), expectation=label))
        with (evidence / 'checks.jsonl').open('a') as out:
            out.write(json.dumps(checks[-1]) + '\n')
        if not ok:
            raise AssertionError(label)

    def probe(label, text=None, path=None, start=0, stop=10, times=(-1, 0, 4, 5, 10, 11), limits=None, view=False):
        if path is None:
            path = evidence / (label + '.vcd')
            path.write_text(text)
        command = [str(args.probe), str(path), str(start), str(stop), *map(str, times)]
        rss = evidence / (label + '.rss-kib')
        timed = ['/usr/bin/time', '-f', '%M', '-o', str(rss), *command]
        env = dict(os.environ, **{'WB028_' + k: str(v) for k, v in (limits or {}).items()})
        if view:
            env['WB028_VIEW'] = '1'
        since = time.monotonic()
        completed = subprocess.run(timed, env=env, capture_output=True, timeout=30)
        wall_ms = (time.monotonic() - since) * 1000
        (evidence / (label + '.stdout')).write_bytes(completed.stdout)
        (evidence / (label + '.stderr')).write_bytes(completed.stderr)
        check(completed.returncode == 0, label + ': probe exited normally')
        result = dict(wire.parse(completed.stdout.decode()))
        results.append(dict(label=label, command=command, wall_ms=wall_ms,
                            peak_rss_kib=int(rss.read_text().strip()),
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            result={k: v for k, v in result.items() if k not in ('render', 'view_frames')}))
        return result

    def values(result, name):
        return dict(next(dict(s)['values'] for s in result['signals'] if dict(s)['name'] == name))

    def rejected(label, text, substring, **kw):
        r = probe(label, text, **kw)
        check(r['status'] == 'error' and substring.lower() in r['error'].lower(), label + ': explicit ' + substring)

    report = dict(status='failed', checks=checks, measurements=results)
    try:
        if args.pty_only:
            pty_acceptance(args, evidence, args.vcd[0], check)
            report['status'] = 'passed'
            return
        r = probe('four-state', HEADER + '$dumpvars 0! b1 " $end #5 1! bx " #10 bz "')
        check(r['timescale'] == '10 ps' and r['bounds'] == ['0', '10'], 'exact units and terminal bounds')
        check(values(r, 'top.bus[3:0]') == {'-1': [], '0': ['0001'], '4': ['0001'],
              '5': ['xxxx'], '10': ['zzzz'], '11': ['zzzz']}, 'zero/X/Z extension and exact cursor hold')
        check(values(r, 'top.bus[3:0]') == values(r, 'top.child.alias[0:3]'), 'hierarchical alias shares exact values')
        check('X/Z' in r['conversion_error'], 'two-state renderer refuses four-state window explicitly')
        r = probe('exact-large-time', HEADER + '0! b0 " #9007199254740993 1! b1010 " #9007199254740993 0! #9007199254740997',
                  start=9007199254740992, stop=9007199254740997,
                  times=[9007199254740992, 9007199254740993, 9007199254740997])
        check(values(r, 'top.clk')['9007199254740993'] == ['0'], 'last same-timestamp assignment wins above float precision')
        check(r['conversion'] == 'verified' and int(r['render_bytes']) > 0, 'real waveterm conversion and rendering preserves exact events')
        r = probe('uninitialized', HEADER + '#5 1! b1 " #10')
        check(values(r, 'top.clk')['4'] == [] and 'uninitialized' in r['conversion_error'], 'uninitialized is distinct from binary zero')
        for label, body, message in [
            ('backwards', '0! #5 1! #4', 'monotonic'),
            ('undeclared', '0?', 'undeclared'), ('bus-scalar', '0"', 'bus'),
            ('wide-value', 'b10000 "', 'width'), ('real', 'r1.5 !', 'Unsupported'),
            ('string', 'shello !', 'Unsupported'), ('dump-off', '$dumpoff $end', 'Unsupported'),
            ('dump-on', '$dumpon $end', 'Unsupported'), ('truncated', '$dumpvars 0!', 'Unterminated'),
            ('overflow', '#9223372036854775808', 'int64'), ('negative', '#-1', 'timestamp'),
            ('invalid-bit', 'bq "', 'binary'), ('unexpected-end', '$end', 'Unexpected')]:
            rejected(label, HEADER + body, message)
        rejected('missing-timescale', HEADER.replace('$timescale 10 ps $end', '') + '0!', 'timescale')
        rejected('range-mismatch', HEADER.replace('[3:0]', '[7:0]') + '0!', 'range')
        rejected('alias-width', HEADER.replace('4 " alias', '3 " alias').replace('[0:3]', '[0:2]') + '0!', 'Alias')
        rejected('real-declaration', HEADER.replace('wire 1 !', 'real 1 !') + '0!', 'Unsupported')
        valid = HEADER + '0! b0 " #5 1! b1 " #10'
        for label, limit, n, message in [('bytes', 'MAX_BYTES', 20, 'input bytes'),
                ('signals', 'MAX_SIGNALS', 2, 'signal declarations'),
                ('width', 'MAX_WIDTH', 3, 'signal width'),
                ('changes', 'MAX_CHANGES', 3, 'value changes'),
                ('expanded', 'MAX_VALUE_BYTES', 9, 'expanded value bytes')]:
            rejected('limit-' + label, valid, message, limits={limit: n})
        r = probe('exact-budget', valid, limits={'MAX_BYTES': len(valid), 'MAX_SIGNALS': 3,
                  'MAX_WIDTH': 4, 'MAX_CHANGES': 4, 'MAX_VALUE_BYTES': 10})
        check(r['status'] == 'ok' and r['conversion'] == 'verified', 'budget boundaries accepted inclusively; aliases do not inflate value budget')
        r = probe('render-span-limit', HEADER + '0! b0 " #1000000', stop=1000000)
        check('1,000,000' in r['conversion_error'], 'render window refuses oversized exact span')
        rejected('default-byte-limit', ' ' * (8 * 1024 * 1024 + 1), 'input bytes')
        scalar = '$timescale 1 ns $end $var wire 1 ! a $end $enddefinitions $end '
        rejected('default-change-limit', scalar + '0! ' * 500001, 'value changes')
        r = probe('render-event-limit', scalar + '0! #1 ' + '1! 0! ' * 50001, stop=1)
        check('100,000' in r['conversion_error'], 'render conversion enforces unique event budget')

        paths = args.vcd
        if not paths:
            for kind in ('pass/artifacts/directed.vcd', 'failure/artifacts/seeded.vcd', 'long/artifacts/seeded.vcd'):
                found = sorted(Path('/tmp/opencode').glob('fifo-testing-*/standalone/' + kind))
                if found:
                    paths.append(found[-1])
        check(bool(paths), 'at least one real retained FIFO VCD supplied or discovered')
        for i, path in enumerate(paths):
            r = probe('retained-' + str(i), path=path.resolve(), stop=100,
                      times=[0, 19, 20, 29, 30, 39, 40, 100])
            check(r['status'] == 'ok' and r.get('conversion') == 'verified', str(path) + ': real retained trace parses and renders')
            names = {dict(s)['name'] for s in r['signals']}
            check({'outputs.occupancy', 'inputs.push_data', 'outputs.data_out'} <= names,
                  'native FIFO hierarchy/buses retained')
            if path.name == 'directed.vcd':
                check(values(r, 'inputs.push_data')['20'] == ['11010101'] and
                      values(r, 'outputs.data_out')['40'] == ['11010101'] and
                      values(r, 'outputs.occupancy')['30'] == ['00001'],
                      'directed native FIFO push/pop payload and occupancy at exact cycles')
        spec = importlib.util.spec_from_file_location('waveform_probe_cells', HERE / 'test-frontend-composition.py')
        view_cells = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(view_cells)
        for label, base, last, magnitude, unit in [
                ('nonunit', 1000, 11000, 10, 'ps'),
                ('huge', 9007199254740993, 9007199254750993, 10, 'ps'),
                ('int64-end', 9223372036854775700, 9223372036854775807, 100, 'fs')]:
            fixture = ('$timescale %d %s $end $scope module probe $end '
                       '$var wire 1 ! clk $end $var wire 4 # bus [3:0] $end '
                       '$upscope $end $enddefinitions $end '
                       '$dumpvars 0! b0 # $end #%d #%d 1! b1010 # #%d' %
                       (magnitude, unit, base, base + 5, last))
            result = probe('view-' + label, fixture, start=base, stop=base + 10, view=True)
            check(result['status'] == 'ok', label + ': non-unit/large-timestamp retained VCD parses')
            frames, images, rulers = {}, {}, []
            for raw in result['view_frames']:
                frame = dict(raw)
                name = frame['name']
                frames[name] = frame
                width, height = int(frame['width']), int(frame['height'])
                image = view_cells.Screen(bytes.fromhex(frame['ansi_hex']), width, height)
                image.save(evidence / ('probe-' + label + '-' + name))
                signals = view_cells.Screen(bytes.fromhex(frame['signals_ansi_hex']), width, height)
                signals.save(evidence / ('probe-' + label + '-' + name + '-values'))
                images[name] = image
                start, stop, cursor = map(int, (frame['start'], frame['stop'], frame['cursor']))
                code = int(frame['raster_code'])
                scale = ((1, 'cells/tick') if code == -1 else
                         (2 * (code + 1), 'cells/tick') if code >= 0 else (-code, 'ticks/cell'))
                column = expected_cursor_column(start, stop, cursor, scale)
                location = ['Column', str(column)] if column is not None else ('Left' if cursor < start else 'Right')
                check(frame['cursor_location'] == location and raster_scale(image.text()) == scale,
                      label + '/' + name + ': shared mapping agrees with independent integer tick/cell equation')
                check(frame['physical_cursor'] == '%d %s' % (cursor * magnitude, unit),
                      label + '/' + name + ': physical cursor formatting is exact beyond float and int64 products')
                plot = plot_region(image)
                bounds = frame['cell_bounds']
                expected_bounds = []
                for x in range(plot['columns']):
                    first = start + (x // scale[0] if scale[1] == 'cells/tick' else x * scale[0])
                    final = min(stop, first + (0 if scale[1] == 'cells/tick' else scale[0] - 1))
                    expected_bounds.append([] if first > stop else [str(first), str(final)])
                check(bounds == expected_bounds, label + '/' + name + ': every plotted cell has exact bounded tick interval')
                if code < -1 and column is not None:
                    first, final = bounds[column]
                    check('Cursor cell %s..%s ticks' % (first, final) in image.text(),
                          label + '/' + name + ': compressed legend retains the exact bounded cursor tick interval')
                if column is None:
                    direction = 'left' if cursor < start else 'right'
                    check('off-screen ' + direction in image.text().lower(),
                          label + '/' + name + ': off-screen cursor direction is explicit')
                for signal, option in frame['values']:
                    if option:
                        check(any(signal in row and re.search(r'=\s*' + option[0] + r'\s*$', row)
                                  for row in signals.lines()),
                              label + '/' + name + ': rendered inspection value matches exact cursor query')
                ruler = check_ruler_image(check, image, label + '/' + name, magnitude, unit, bounds=(start, stop))
                api_labels = [dict(a) for a in frame['ruler_labels']]
                check([dict(tick=str(a['tick']), column=str(a['column']), text_column=str(a['text_column']), text=a['text'])
                       for a in ruler['labels']] == api_labels and
                      ruler['major_columns'] == list(map(int, frame['major_columns'])) and
                      ruler['minor_columns'] == list(map(int, frame['minor_columns'])),
                      label + '/' + name + ': actual ruler text/marks occupy shared-helper coordinates exactly')
                rulers.append(dict(name=name, **ruler))
                if 'offscreen_ansi_hex' in frame:
                    baseline = view_cells.Screen(bytes.fromhex(frame['offscreen_ansi_hex']), width, height)
                    before = plot_region(baseline)
                    check(before['glyphs'] == plot['glyphs'],
                          label + '/' + name + ': cursor overlay preserves every native wave glyph')
                    changed = {(y, x) for y, row in enumerate(before['attrs']) for x, a in enumerate(row)
                               if a != plot['attrs'][y][x]}
                    check({x for _, x in changed} == (set() if column is None else {column}) and
                          (column is None or len(changed) >= 2),
                          label + '/' + name + ': cursor styling is one visible exact column, absent off-screen')
                    for row_name, offset in [('labels', 3), ('marks', 2)]:
                        old = baseline.cells[before['top'] - offset][before['left']:before['right']]
                        new = image.cells[plot['top'] - offset][plot['left']:plot['right']]
                        check([c for c, _ in old] == [c for c, _ in new] and
                              {x for x, ((_, aa), (_, bb)) in enumerate(zip(old, new)) if aa != bb}
                              == (set() if column is None else {column}),
                              label + '/' + name + ': ruler ' + row_name + ' cursor aligns with unchanged plot/ruler glyphs')
            a, b = plot_region(images['compressed-0']), plot_region(images['compressed-5'])
            check(a['glyphs'] == b['glyphs'] and a['attrs'] == b['attrs'] and
                  dict(frames['compressed-0']['values'])['probe.clk'] == ['0'] and
                  dict(frames['compressed-5']['values'])['probe.clk'] == ['1'],
                  label + ': different exact values within one compressed cell retain identical plot cursor column')
            (evidence / ('probe-' + label + '-ruler-measurements.json')).write_text(json.dumps(rulers, indent=2) + '\n')
        if args.daemon:
            pty_acceptance(args, evidence, paths[0], check)
        report['status'] = 'passed'
    finally:
        (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(dict(status=report['status'], checks=len(checks), evidence=str(evidence))))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '_provider':
        replay_provider()
    else:
        main()
