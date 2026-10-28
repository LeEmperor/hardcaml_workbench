#!/usr/bin/env python3
r"""Package C: private native HTTP/PTY default-layout restoration acceptance.

Usage (only after matching normal binaries are ready):
  python3 scripts/test-default-layout-restore.py \
    --daemon _build/default/daemon/main.exe \
    --client _build/default/terminal/main.exe \
    --workspace-cli _build/default/workspace_cli/main.exe \
    --setup _build/default/setup/main.exe

No builds. Uses FS3's strict metadata-only Dune fixture, S-expression/HTTP helpers
and PTY screen decoder. Everything, including HOME/preferences, is private under
/tmp/opencode. A loopback observing proxy records actual client CAS receipts and
can delay their delivery; no live endpoint, state, provider or job is used.
"""
import argparse
import copy
import fcntl
import http.server
import importlib.util
import json
import re
import os
from pathlib import Path
import signal
import struct
import sys
import tempfile
import termios
import threading
import time
import traceback
import urllib.error
import urllib.request

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('fs3', Path(__file__).with_name('test-fs3-adoption.py'))
fs3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs3)
field, require, sexp, parse = fs3.field, fs3.require, fs3.sexp, fs3.parse


def workspace(snapshot, wid):
    return next(w for w in field(snapshot, 'workspaces') if field(w, 'id') == wid)


def tiles(snapshot, wid):
    return [t for t in field(snapshot, 'tiles') if field(t, 'workspace') == wid]


class ReceiptProxy:
    """Observe real client requests, independently of polling/file-save timing.

    Only Restore_default_layout responses are gated. Other requests, including
    client polling and later local layout choices, remain independently runnable.
    """
    def __init__(self, test):
        self.test, self.events = test, []
        self.seen_revision = None
        self.lock = threading.Lock()
        self.delay_next = False
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *_):
                pass

            def do_GET(self):
                self.forward()

            def do_POST(self):
                self.forward()

            def forward(self):
                if self.headers.get('Transfer-Encoding', '').lower() == 'chunked':
                    chunks = []
                    while True:
                        size = int(self.rfile.readline().split(b';', 1)[0], 16)
                        if not size:
                            while self.rfile.readline().strip():
                                pass
                            break
                        chunks.append(self.rfile.read(size))
                        require(self.rfile.read(2) == b'\r\n', 'Invalid HTTP chunk terminator')
                    body = b''.join(chunks)
                else:
                    body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                event = None
                if b'Restore_default_layout' in body:
                    with owner.lock:
                        event = dict(request=parse(body.decode()), received=threading.Event(),
                                     release=threading.Event(), delivered=threading.Event())
                        if not owner.delay_next:
                            event['release'].set()
                        owner.delay_next = False
                        owner.events.append(event)
                headers = {k: v for k, v in self.headers.items()
                           if k.lower() not in ('host', 'connection', 'content-length', 'transfer-encoding')}
                request = urllib.request.Request(owner.test.url + self.path,
                    data=body if self.command == 'POST' else None,
                    headers=headers, method=self.command)
                try:
                    try:
                        response = owner.opener.open(request, timeout=30)
                    except urllib.error.HTTPError as error:
                        response = error
                    with response:
                        status, content = response.status, response.read()
                    if event is not None:
                        event.update(status=status, response=parse(content.decode()))
                        with (owner.test.evidence / 'client-receipts.jsonl').open('a') as out:
                            out.write(json.dumps({k: event[k] for k in
                                ('request', 'status', 'response')}) + '\n')
                        event['received'].set()
                        require(event['release'].wait(25), 'Delayed receipt was never released')
                    self.send_response(status)
                    self.send_header('Content-Type', 'application/sexp')
                    self.send_header('Content-Length', str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    self.wfile.flush()
                    if self.path == '/api/v1/workspace':
                        decoded = parse(content.decode())
                        if decoded[0] == 'Ok':
                            owner.seen_revision = field(decoded[1], 'revision')
                    if event is not None:
                        event['delivered'].set()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except BaseException:
                    if event is not None:
                        event['failure'] = traceback.format_exc()
                        event['received'].set()
                    self.close_connection = True

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:%d' % self.server.server_port

    def sync(self, terminal, snapshot):
        deadline = time.monotonic() + 20
        while self.seen_revision != field(snapshot, 'revision'):
            require(time.monotonic() < deadline, 'Client never observed current authoritative revision')
            terminal.drain(.1)
        terminal.drain(.3)

    def receipt(self, terminal, index, success=True):
        deadline = time.monotonic() + 20
        while len(self.events) <= index or not self.events[index]['received'].is_set():
            require(time.monotonic() < deadline, 'No actual restore HTTP receipt')
            terminal.drain(.1)
        event = self.events[index]
        require('failure' not in event, event.get('failure', ''))
        response = event['response']
        self.test.check(response[0] == ('Ok' if success else 'Error'),
                        'Actual initiating client HTTP receipt is ' + ('Ok' if success else 'Error'))
        if event['release'].is_set():
            require(event['delivered'].wait(5), 'Restore receipt delivery failed')
            terminal.drain(.3)
        return event

    def close(self):
        for event in self.events:
            event['release'].set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class Terminal(fs3.Terminal):
    width, height = 120, 40

    def __init__(self, test, label, proxy):
        # FS3's subprocess helper uses test.url; only the TUI uses the observer.
        actual = test.url
        test.url = proxy.url
        try:
            super().__init__(test, label)
        finally:
            test.url = actual

    def drain(self, seconds=.15):
        super().drain(seconds)
        return fs3.fs0.terminal_screen(bytes(self.data), self.width, self.height)

    def resize(self, width, height):
        self.width, self.height = width, height
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
        os.kill(self.process.pid, signal.SIGWINCH)
        self.wait('resize-%dx%d' % (width, height), ['Space c c commands'])

    def palette(self, title, dispatch=True):
        for key in (b' ', b'c', b'c'):
            self.key(key)
        self.wait('palette-open', ['COMMAND PALETTE'])
        self.key(title.encode())
        # Long labels are clipped by the palette's inner width. The exact typed
        # query selects it; the observed HTTP mutation proves what was dispatched.
        self.wait('palette-query', ['COMMAND PALETTE', title[:28]])
        if dispatch:
            self.key(b'\r')
            self.wait('palette-closed', absent=['COMMAND PALETTE'])

    def composed(self, label):
        """Assert native track positions, not just membership or saved geometry."""
        deadline = time.monotonic() + 20
        while True:
            text = self.drain(.2)
            rows = text.splitlines()

            def position(token, right=False):
                return next(((x, y) for y, row in enumerate(rows)
                             if (x := row.find(token, self.width // 3 if right else 0)) >= 2
                             and row[x - 2:x] in ('┌ ', '╭ ', '+ ')), None)

            names = ['runs 0/0', 'stage checklist', 'planned-run', 'synthesis',
                     'timing', 'placement', 'routing', 'checks', 'finalization']
            p = {name: position(name, right=i >= 3) for i, name in enumerate(names)}
            right = [p[name] for name in names[3:]]
            left = [p[name] for name in names[:3]]
            # The tabs are an unframed full-width top row; each right summary
            # must be painted on a distinct row in a single common right track.
            # With five starters and imported roundtrips, bounded tabs need not
            # show both the renamed active workspace and an inactive Timing tab.
            # Match an actual top-row workspace label; assert active scope in footer.
            tab_names = [field(w, 'name') for w in field(self.test.workspace(), 'workspaces')]
            tabs = next((y for y, row in enumerate(rows[:2])
                         if any(name in row for name in tab_names)), None)
            active_scope = ('Renamed source' in rows[-1] or 'Renamed after capture' in rows[-1]
                            or re.search(r'\[\d+ Renamed (?:source|after capture)\]', rows[0]))
            ok = (all(p.values()) and tabs is not None and
                   active_scope and
                  all(x < self.width // 2 for x, _ in left) and
                  len({x for x, _ in right}) == 1 and right[0][0] > self.width // 4 and
                  [y for _, y in right] == sorted({y for _, y in right}) and
                  tabs < left[0][1] < left[1][1] < left[2][1] and
                  tabs < right[0][1] and 'simulation-catalog' not in text and
                  'timing · paths' not in text and
                  len(rows) == self.height and rows[-1].startswith('Space c c commands') and
                  any(len(row) == self.width and row.endswith(('╮', '┐', '+')) for row in rows[:8]) and
                  any(len(row) == self.width and row.endswith(('╯', '┘', '+')) for row in rows[-5:-1]))
            if ok:
                (self.test.evidence / (label + '.txt')).write_text(text)
                (self.test.evidence / (label + '-positions.json')).write_text(json.dumps(
                    dict(width=self.width, height=self.height, tabs_row=tabs, positions=p), indent=2))
                self.test.check(True, label + ': actual painted viewport, top tabs, left sidebar and six right-stack panes')
                return text
            require(time.monotonic() < deadline, label + ': composed layout timeout:\n' + text)


def preferences(test, terminal, mode, appearance=None):
    deadline = time.monotonic() + 15
    while True:
        files = list((test.evidence / 'client-state').rglob('presentation-*.sexp'))
        stored = parse(files[0].read_text()) if len(files) == 1 else None
        if (stored is not None and field(stored, 'layout_mode') == mode and
                (appearance is None or field(field(stored, 'appearance'), 'preset') == appearance)):
            require(files[0].stat().st_mode & 0o077 == 0, 'Preferences must be private')
            return stored
        require(time.monotonic() < deadline, 'Preference mode not persisted: ' + mode)
        terminal.drain(.1)


def preserved_preferences(test, before, after, label):
    test.check(fs3.replace_field(before, 'layout_mode', field(after, 'layout_mode')) == after,
               label + ': all appearance, chrome and exact tile-header choices preserved')


def assert_restore(test, before, after, wid, template):
    """Independent occurrence and targeted policy-detachment oracle.

    Derive every allowed provenance change from the pre-Restore snapshot, never
    from the returned policy/definitions/mappings. Unconfigured targets must not
    acquire provenance; already-detached targets must retain it exactly.
    """
    expected = copy.deepcopy(before)
    old_tiles = tiles(before, wid)
    claimed, missing = {}, []
    for view in field(template, 'views'):
        match = next((t for t in old_tiles if field(t, 'id') not in claimed and
                      field(t, 'kind') == field(view, 'kind')), None)
        if match is None:
            missing.append(view)
        else:
            claimed[field(match, 'id')] = view
    expected_tiles = []
    for tile in field(before, 'tiles'):
        if field(tile, 'workspace') == wid:
            view = claimed.get(field(tile, 'id'))
            tile = fs3.replace_field(tile, 'hidden', 'false' if view is not None else 'true')
            if view is not None:
                tile = fs3.replace_field(tile, 'requested_geometry', field(view, 'geometry'))
        expected_tiles.append(tile)
    actual_tiles = field(after, 'tiles')
    test.check(actual_tiles[:len(expected_tiles)] == expected_tiles,
               'Existing registry order/IDs/bindings retained; defaults repaired and only unclaimed extras hidden')
    added = actual_tiles[len(expected_tiles):]
    test.check(len(added) == len(missing) and all(
        field(t, 'workspace') == wid and field(t, 'kind') == field(v, 'kind') and
        field(t, 'requested_geometry') == field(v, 'geometry') and
        field(t, 'binding') == 'Follow' and field(t, 'hidden') == 'false'
        for t, v in zip(added, missing)) and
        len({field(t, 'id') for t in actual_tiles}) == len(actual_tiles),
        'Only missing default occurrences allocated as fresh visible Follow tiles')
    ws = workspace(expected, wid)
    ws = fs3.replace_field(ws, 'preset', field(template, 'preset'))
    ws = fs3.replace_field(ws, 'zoomed_tile', [])
    expected = fs3.replace_field(expected, 'workspaces',
        [ws if field(w, 'id') == wid else w for w in field(expected, 'workspaces')])
    expected = fs3.replace_field(expected, 'tiles', actual_tiles)
    expected = fs3.replace_field(expected, 'revision', str(int(field(before, 'revision')) + 1))
    expected = fs3.replace_field(expected, 'next_id', str(int(field(before, 'next_id')) + len(missing)))
    old_provenance = field(before, 'config_workspaces')
    require(sum(field(p, 'workspace') == wid for p in old_provenance) <= 1,
            'Restore fixture must have at most one provenance record per workspace')
    expected_provenance = [
        fs3.replace_field(p, 'policy_detached', 'true')
        if field(p, 'workspace') == wid else copy.deepcopy(p)
        for p in old_provenance]
    test.check(field(after, 'config_workspaces') == expected_provenance,
               'Restore detaches only target frozen policy; config keys, definitions, tile mappings, '
               'record order and all non-target provenance remain exact unchanged')
    expected = fs3.replace_field(expected, 'config_workspaces', expected_provenance)
    test.check(after == expected,
               'Exactly one CAS revision restores target preset, clears zoom and detaches its config policy; '
               'all other snapshot fields are exact unchanged')
    return added


def restore_mutation(wid, template):
    return ['Restore_default_layout', ['workspace', wid],
            ['preset', field(template, 'preset')[0]],
            ['tiles', [[field(v, 'kind'), field(v, 'geometry')] for v in field(template, 'views')]]]


def fixture(test, templates):
    snapshot = test.workspace()
    target = next(w for w in field(snapshot, 'workspaces') if field(w, 'preset') == ['overview'])
    wid = field(target, 'id')

    def mutate(m):
        nonlocal snapshot
        snapshot = test.mutate(snapshot, m)

    mutate(['Rename_workspace', ['workspace', wid], ['name', 'Renamed source']])
    mutate(['Make_independent', wid])
    cid = field(workspace(snapshot, wid), 'context')
    run = [['backend', 'saved-fixture'], ['id', 'selected-source-run'], ['build', []], ['label', []]]
    context = next(c for c in field(snapshot, 'contexts') if field(c, 'id') == cid)
    mutate(['Select_run', ['workspace', wid], ['context', cid],
            ['expected_selection_revision', field(context, 'selection_revision')], ['run', [run]]])
    # Independent destination retains a default pane, guaranteeing a missing
    # occurrence on the target as well as exact other-workspace preservation.
    mutate(['Create_workspace', ['window', field(target, 'window')],
            ['name', 'Untouched witness'], ['context', field(snapshot, 'main_context')]])
    other = field(field(snapshot, 'workspaces')[-1], 'id')
    mutate(['Make_independent', other])
    other_cid = field(workspace(snapshot, other), 'context')
    other_context = next(c for c in field(snapshot, 'contexts') if field(c, 'id') == other_cid)
    mutate(['Select_run', ['workspace', other], ['context', other_cid],
            ['expected_selection_revision', field(other_context, 'selection_revision')],
            ['run', [fs3.replace_field(run, 'id', 'selected-witness-run')]]])
    moved = next(t for t in tiles(snapshot, wid) if field(t, 'kind') == 'finalization')
    mutate(['Move_tile', ['tile', field(moved, 'id')], ['workspace', other]])
    mutate(['Set_zoom', ['workspace', other], ['tile', [field(moved, 'id')]]])
    for view in field(templates['testing'], 'views') + field(templates['timing'], 'views'):
        mutate(['Create_tile', ['workspace', wid], ['kind', field(view, 'kind')],
                ['geometry', field(view, 'geometry')]])
    # More than one existing occurrence, with the earliest run selector hidden.
    for tile in tiles(snapshot, wid):
        mutate(['Resize_tile', ['tile', field(tile, 'id')], ['geometry',
            [['x', '11'], ['y', '13'], ['width', '37'], ['height', '9']]]])
    selector = next(t for t in tiles(snapshot, wid) if field(t, 'kind') == 'run-selector')
    mutate(['Set_tile_hidden', ['tile', field(selector, 'id')], ['hidden', 'true']])
    for kind in ('synthesis', 'simulation-catalog'):
        tile = next(t for t in tiles(snapshot, wid) if field(t, 'kind') == kind)
        pin = fs3.replace_field(run, 'id', 'pinned-' + kind)
        mutate(['Set_tile_binding', ['tile', field(tile, 'id')], ['binding', ['Pin_run', pin]]])
    zoom = next(t for t in tiles(snapshot, wid) if field(t, 'kind') == 'simulation-catalog')
    mutate(['Set_zoom', ['workspace', wid], ['tile', [field(zoom, 'id')]]])
    (test.evidence / 'cluttered-source.sexp').write_text(sexp(snapshot) + '\n')
    test.check(field(workspace(snapshot, wid), 'context') != field(snapshot, 'main_context'),
               'Fixture source has independent selected-run context, hidden default, duplicate/extras, changed geometry, default/extra pins and zoom')
    return snapshot, wid


def exercise(test):
    (test.root / 'dune-project').write_text('(lang dune 3.22)\n(name restore_acceptance)\n')
    (test.root / 'dune').write_text('(dirs)\n')
    test.command(test.args.setup, ['--root', test.root, '--project-name', 'FS3 acceptance'], 'setup')
    templates = {name: parse(test.command(test.args.workspace_cli, ['starter', name], 'preset-' + name))
                 for name in ('overview', 'timing', 'testing', 'resources')}
    test.start()
    proxy = ReceiptProxy(test)
    terminal = None
    try:
        terminal = Terminal(test, 'bootstrap', proxy)
        terminal.wait('ready', ['Space c c commands'], ['Loading workspace...'], ready=True)
        # The first interactive frame can precede asynchronous default composition.
        # Wait for the authoritative initialization receipt, not just terminal chrome.
        deadline = time.monotonic() + 20
        while field(test.workspace(), 'defaults_initialized') != 'true':
            require(time.monotonic() < deadline, 'Native shared defaults bootstrap timeout')
            terminal.drain(.1)
        require(field(test.workspace(), 'defaults_initialized') == 'true', 'Native shared defaults bootstrapped')
        terminal.close()
        terminal = None
        before, wid = fixture(test, templates)
        terminal = Terminal(test, 'restore', proxy)
        terminal.wait('ready', ['Space c c commands'], ['Loading workspace...'], ready=True)
        terminal.resize(180, 55)
        proxy.sync(terminal, before)
        terminal.palette('Switch to Untouched witness')
        terminal.palette('Toggle focused tile header')
        terminal.palette('Switch to Renamed source')
        terminal.palette('Appearance: B - Structured')
        terminal.palette('Layout: Requested tile sizes')
        original_preferences = preferences(test, terminal, 'Preferred')
        test.check(bool(field(original_preferences, 'tile_headers')),
                   'Actual palette establishes explicit persisted header intent and nondefault appearance/Preferred mode')
        test.check(test.workspace() == before, 'Startup, resize, appearance and palette viewing leave cluttered registry exact unchanged')

        title = 'Restore default layout: Overview (hide extras)'
        index = len(proxy.events)
        terminal.palette(title)
        event = proxy.receipt(terminal, index)
        after = event['response'][1]
        test.check(field(field(event['request'], 'operation')[1:], 'expected_revision') == field(before, 'revision'),
                   'Palette command sends its captured registry CAS revision')
        added = assert_restore(test, before, after, wid, templates['overview'])
        test.check(len(added) == 1 and field(added[0], 'kind') == 'finalization',
                   'Native restore creates the deliberately missing finalization occurrence only')
        fitted_preferences = preferences(test, terminal, 'Fit')
        preserved_preferences(test, original_preferences, fitted_preferences, 'Acknowledged restore')
        terminal.composed('overview-restored-180x55')
        terminal.resize(120, 40)
        terminal.composed('overview-restored-120x40')
        terminal.resize(180, 55)

        # The current-preset command must use stable identity despite source rename.
        # Use its stable searchable title prefix; confirm exact preset in HTTP body.
        index = len(proxy.events)
        terminal.palette('Restore default layout (current preset')
        event = proxy.receipt(terminal, index)
        before, after = after, event['response'][1]
        assert_restore(test, before, after, wid, templates['overview'])
        test.check(field(after, 'next_id') == field(before, 'next_id'),
                   'Repeated current-preset restore on renamed workspace allocates no duplicate IDs')

        # Capture the palette, change the authoritative revision, then dispatch.
        terminal.palette('Layout: Requested tile sizes')
        stale_preferences = preferences(test, terminal, 'Preferred')
        proxy.sync(terminal, after)
        terminal.palette(title, dispatch=False)
        before = test.mutate(after, ['Rename_workspace', ['workspace', wid], ['name', 'Renamed after capture']])
        index = len(proxy.events)
        terminal.key(b'\r')
        event = proxy.receipt(terminal, index, success=False)
        test.check(field(event['response'][1], 'kind') == 'Conflict' and test.workspace() == before,
                   'Palette-open stale capture rejects with Conflict and no partial mutation')
        terminal.wait('stale-palette-closed', absent=['COMMAND PALETTE'])
        terminal.drain(1)
        test.check(preferences(test, terminal, 'Preferred') == stale_preferences,
                   'Rejected actual restore does not switch or persist Fit')

        # Gate a successful receipt after the server commits. Force an unrelated
        # preference save while it is withheld to expose any optimistic Fit state.
        proxy.sync(terminal, before)
        index = len(proxy.events)
        proxy.delay_next = True
        terminal.palette(title)
        event = proxy.receipt(terminal, index)
        after = event['response'][1]
        assert_restore(test, before, after, wid, templates['overview'])
        terminal.palette('Appearance: D - Studio')
        delayed_preferences = preferences(test, terminal, 'Preferred', appearance='Studio')
        test.check(field(field(delayed_preferences, 'appearance'), 'preset') == 'Studio',
                   'With successful HTTP response withheld, fresh local preference save still records Preferred')
        # A newer explicit local layout choice must fence the late success even
        # when choosing the same mode. This tests intent, not value comparison.
        terminal.palette('Layout: Requested tile sizes')
        event['release'].set()
        require(event['delivered'].wait(5), 'Delayed receipt delivery')
        terminal.drain(1.5)
        terminal.palette('Appearance: B - Structured')
        late_preferences = preferences(test, terminal, 'Preferred', appearance='Structured')
        test.check(field(late_preferences, 'layout_mode') == 'Preferred',
                   'A newer layout choice wins over delayed successful restore acknowledgement')

        # Named commands all act on the captured current workspace; none switches
        # to a display-name workspace. Export/import checks stable preset identity.
        for name in ('timing', 'testing', 'resources', 'overview'):
            before = test.workspace()
            proxy.sync(terminal, before)
            index = len(proxy.events)
            terminal.palette('Restore default layout: ' + name.title() + ' (hide extras)')
            event = proxy.receipt(terminal, index)
            after = event['response'][1]
            assert_restore(test, before, after, wid, templates[name])
            exported = parse(test.cli('export', [wid], 'export-restored-' + name))
            test.check(field(exported, 'preset') == [name] and
                       field(exported, 'name') == 'Renamed after capture',
                       name + ': stable preset ID exported from renamed captured workspace')
            path = test.evidence / ('roundtrip-' + name + '.sexp')
            path.write_text(sexp(exported))
            destination = test.cli('import', ['-window', field(workspace(after, wid), 'window'),
                                            '-name', 'Roundtrip ' + name, path], 'import-restored-' + name).strip()
            roundtrip = parse(test.cli('export', [destination], 'export-roundtrip-' + name))
            test.check(roundtrip == fs3.replace_field(exported, 'name', 'Roundtrip ' + name),
                       name + ': HTTP CLI import/export roundtrip retains stable ID and all hidden/default views')
        preferences(test, terminal, 'Fit')
        terminal.composed('overview-final')

        # Unknown/custom current identity must be visibly disabled, and Enter must
        # not silently choose a named fallback or change presentation mode.
        unknown = fs3.replace_field(templates['testing'], 'preset', ['future-restore-preset'])
        path = test.evidence / 'unknown.sexp'
        path.write_text(sexp(unknown))
        destination = test.cli('import', ['-window', field(workspace(after, wid), 'window'),
                                        '-name', 'Unknown current preset', path], 'import-unknown').strip()
        proxy.sync(terminal, test.workspace())
        terminal.palette('Switch to Unknown current preset')
        terminal.palette('Layout: Requested tile sizes')
        unknown_preferences = preferences(test, terminal, 'Preferred')
        before = test.workspace()
        count = len(proxy.events)
        terminal.palette('Restore default layout (current preset', dispatch=False)
        disabled = terminal.wait('unknown-disabled', ['COMMAND PALETTE'])
        test.check('No built-in preset' in disabled,
                   'Unknown current-preset restore displays an explicit disabled reason')
        terminal.key(b'\r')
        terminal.drain(.5)
        test.check(test.workspace() == before and len(proxy.events) == count and
                   preferences(test, terminal, 'Preferred') == unknown_preferences,
                   'Disabled unknown current-preset command issues no restore and preserves registry/mode')
        terminal.key(b'\x1b')
        index = len(proxy.events)
        terminal.palette(title)
        event = proxy.receipt(terminal, index)
        assert_restore(test, before, event['response'][1], destination, templates['overview'])
        preferences(test, terminal, 'Fit')

        # Restart the client and observe composed Fit in addition to disk storage.
        terminal.close()
        terminal = None
        registry = test.workspace()
        terminal = Terminal(test, 'restart', proxy)
        terminal.wait('ready', ['Space c c commands'], ['Loading workspace...'], ready=True)
        terminal.resize(180, 55)
        terminal.palette('Switch to Renamed after capture')
        terminal.composed('fit-restored-after-client-restart')
        stored = preferences(test, terminal, 'Fit')
        preserved_preferences(test, fitted_preferences, stored, 'Client restart')
        test.check(test.workspace() == registry, 'Client restart restores Fit without implicit registry restoration')
        test.quiet()
    finally:
        try:
            if terminal:
                try:
                    (test.evidence / 'last-screen.txt').write_text(terminal.drain(.1))
                finally:
                    terminal.close()
        finally:
            proxy.close()
    test.result['status'] = 'passed'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for flag, dest in [('daemon', 'daemon'), ('client', 'terminal'),
                       ('workspace-cli', 'workspace_cli'), ('setup', 'setup')]:
        parser.add_argument('--' + flag, dest=dest, type=Path, required=True,
                            help='Explicit matching prebuilt executable (never built by this script)')
    parser.add_argument('--evidence', type=Path, help='New directory under /tmp/opencode')
    args = parser.parse_args()
    for name in ('daemon', 'terminal', 'workspace_cli', 'setup'):
        binary = getattr(args, name).resolve(strict=True)
        require(binary.is_file() and os.access(binary, os.X_OK), 'Not executable: ' + str(binary))
        setattr(args, name, binary)
    os.umask(0o077)
    base = Path('/tmp/opencode')
    require(base.is_dir(), '/tmp/opencode must exist')
    if args.evidence:
        args.evidence = args.evidence.resolve()
        require(args.evidence.is_relative_to(base) and args.evidence != base,
                'Evidence must be a new directory under /tmp/opencode')
        args.evidence.mkdir(mode=0o700)
    else:
        args.evidence = Path(tempfile.mkdtemp(prefix='default-layout-restore-', dir=base))
    print('Evidence:', args.evidence, flush=True)
    test = fs3.Acceptance(args)
    try:
        exercise(test)
    except BaseException:
        test.result['failure'] = traceback.format_exc()
        (args.evidence / 'failure.txt').write_text(test.result['failure'])
        traceback.print_exc()
    finally:
        test.close()
        test.result['owned_daemon_stopped'] = test.process is None or test.process.poll() is not None
        (args.evidence / 'result.json').write_text(json.dumps(test.result, indent=2) + '\n')
    print(test.result['status'].upper() + ': ' + str(args.evidence / 'result.json'))
    return 0 if test.result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
