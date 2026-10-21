#!/usr/bin/env python3
"""FS3 adoption acceptance against built binaries and a private real HTTP daemon.

Run: python3 scripts/test-fs3-adoption.py [--skip-pty] [--evidence NEW-DIR]
No builds or toolchain activation. Dune metadata is a strict, logged fixture;
no real Dune, opam, provider, driver, Git, or ASIC tools are executed. All evidence
and disposable project/state remain under /tmp/opencode; owned processes stop
even on failure. Uses the existing FS0 protocol/screen helpers (stdlib only).
"""
import argparse
import copy
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import traceback
import urllib.error
import urllib.request

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('fs0', Path(__file__).with_name('test-fs0.py'))
fs0 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs0)
sexp, field, require = fs0.sexp, fs0.field, fs0.require
REPO = Path(__file__).resolve().parents[1]


def parse(text):
    """Decode Sexplib decimal escapes without feeding raw control bytes to JSON."""
    tokens = iter(re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+', text))

    def value(token):
        if token == '(':
            result = []
            for child in tokens:
                if child == ')':
                    return result
                result.append(value(child))
            raise AssertionError('Unclosed S-expression')
        require(token != ')', 'Unexpected closing S-expression')
        if token.startswith('"'):
            token = re.sub(r'\\(?:[0-9]{3}|.)',
                           lambda m: json.dumps(chr(int(m[0][1:])))[1:-1]
                           if m[0][1:].isdigit() else m[0], token)
            return json.loads(token)
        return token

    result = value(next(tokens))
    require(next(tokens, None) is None, 'Trailing protocol data')
    return result


def optional_field(value, name, default=None):
    return next((entry[1] for entry in value if entry[0] == name), default)


def replace_field(value, name, content):
    result = copy.deepcopy(value)
    for entry in result:
        if entry[0] == name:
            entry[1] = content
            return result
    raise AssertionError('Missing field: ' + name)


def portable(value, name=None):
    """Canonical output schema, including an explicit absent preset for legacy files."""
    return [['version', field(value, 'version')], ['name', name or field(value, 'name')],
            ['preset', optional_field(value, 'preset', [])], ['views', field(value, 'views')]]


def stop(process):
    if process is not None and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=8)


class Acceptance:
    def __init__(self, args):
        self.args, self.evidence = args, args.evidence
        self.root = self.evidence / 'project with spaces'
        self.root.mkdir()
        self.state = self.evidence / 'daemon-state'
        self.state.mkdir(mode=0o700)
        self.process, self.log, self.sequence = None, None, 0
        self.result = dict(status='failed', checks=[], evidence=str(self.evidence),
                           metadata='fixture only; real daemon/HTTP/CLI/PTY')
        self.env = dict(os.environ, XDG_STATE_HOME=str(self.evidence / 'client-state'),
                        XDG_RUNTIME_DIR=str(self.evidence / 'runtime'),
                        XDG_CONFIG_HOME=str(self.evidence / 'config'),
                        HOME=str(self.evidence / 'home'))
        for name in ('runtime', 'config', 'home'):
            (self.evidence / name).mkdir(mode=0o700)
        for name in list(self.env):
            if name.startswith('GIT_'):
                del self.env[name]
        self.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
                        GIT_OPTIONAL_LOCKS='0')
        private_bin = self.evidence / 'private-bin'
        private_bin.mkdir()
        # Only the exact two read-only metadata requests are recognized. Never
        # relay to the host's Dune. This also makes attempted actions observable.
        guard = private_bin / 'dune'
        guard.write_text('#!' + sys.executable + '\n' +
            'import json, pathlib, sys\n' +
            'a = sys.argv[1:]\n' +
            'probe = a == ["--version"]\n' +
            'describe = a == ["describe", "workspace", "--root", ' + repr(str(self.root)) + ', "--format=sexp", "--lang=0.1"]\n' +
            'with pathlib.Path(' + repr(str(self.evidence / 'metadata-calls.jsonl')) + ').open("a") as f: f.write(json.dumps(dict(argv=a, allowed=probe or describe)) + "\\n")\n' +
            'if not (probe or describe): sys.exit("FS3 forbids Dune actions")\n' +
            'print("3.22.0" if probe else ' + repr(sexp([['root', str(self.root)], ['build_context', '_build/default']])) + ')\n')
        guard.chmod(0o700)
        # Deny toolchain/provider access even if an unexpected path tries it.
        for name in ('opam', 'git', 'hardcaml-asic', 'yosys', 'openroad', 'docker'):
            blocked = private_bin / name
            blocked.write_text('#!' + sys.executable + '\nimport pathlib, sys\n' +
                'with pathlib.Path(' + repr(str(self.evidence / 'forbidden-tools.jsonl')) + ').open("a") as f: f.write(repr(sys.argv) + "\\n")\n' +
                'sys.exit("FS3 forbids this tool")\n')
            blocked.chmod(0o700)
        self.env['PATH'] = str(private_bin) + os.pathsep + self.env.get('PATH', '')

    def check(self, condition, message):
        self.result['checks'].append(dict(passed=bool(condition), expectation=message))
        require(condition, message)
        print('PASS:', message, flush=True)

    def command(self, binary, argv, label, error=None):
        self.sequence += 1
        stem = self.evidence / f'{self.sequence:03d}-{label}'
        command = [str(binary)] + list(map(str, argv))
        process = subprocess.Popen(command, env=self.env, cwd=self.evidence,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            timed_out = True
            stop(process)
            stdout, stderr = process.communicate(timeout=5)
        finally:
            stop(process)
        stem.with_suffix('.stdout').write_bytes(stdout)
        stem.with_suffix('.stderr').write_bytes(stderr)
        stem.with_suffix('.json').write_text(json.dumps(dict(argv=command, returncode=process.returncode,
                                                           timed_out=timed_out), indent=2))
        require(not timed_out, label + ': command timeout; see ' + str(stem))
        if error is None:
            require(process.returncode == 0, f'{label}: exit {process.returncode}: {stderr.decode()}')
        else:
            self.check(process.returncode != 0 and error.lower() in (stdout + stderr).decode().lower(),
                       label + ': rejected with expected diagnostic')
        return stdout.decode()

    def cli(self, verb, extra, label, error=None):
        return self.command(self.args.workspace_cli,
                            [verb, '-endpoint', self.url, '-project', self.project] + extra,
                            label, error=error)

    def raw(self, path, data=None):
        route = '/api/hello' if path == 'hello' else '/api/v1/' + path
        request = urllib.request.Request(self.url + route,
            data=None if data is None else sexp(data).encode(),
            headers={'Content-Type': 'application/sexp', 'X-Workbench-Protocol': '1'})
        try:
            response = urllib.request.urlopen(request, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            text = response.read().decode()
            status = response.status
        with (self.evidence / 'http.jsonl').open('a') as out:
            out.write(json.dumps(dict(path=path, request=data, status=status, response=text)) + '\n')
        return parse(text)

    def start(self):
        discovery = self.evidence / ('discovery-' + str(time.time_ns()))
        discovery.mkdir(mode=0o700)
        self.log = (self.evidence / (discovery.name + '.log')).open('wb')
        self.process = subprocess.Popen([str(self.args.daemon), '--port', '0',
            '--discovery-dir', str(discovery), '--state-dir', str(self.state)],
            env=self.env, cwd=self.evidence, stdout=self.log, stderr=subprocess.STDOUT,
            start_new_session=True)
        deadline = time.monotonic() + 20
        while not (discovery / 'daemon.sexp').exists():
            require(self.process.poll() is None, 'Daemon exited; inspect daemon log')
            require(time.monotonic() < deadline, 'Daemon discovery timeout')
            time.sleep(.05)
        metadata = dict(parse((discovery / 'daemon.sexp').read_text()))
        self.url, self.instance = metadata['endpoint'], metadata['instance_id']
        hello = self.raw('hello')
        self.check(field(hello, 'instance_id') == self.instance, 'Private discovery and actual HTTP hello agree')
        opened = self.raw('open-project', [['instance_id', self.instance], ['root', str(self.root)],
                                         ['environment', 'Inherit_daemon']])
        require(opened[0] == 'Ok', 'Project open failed: ' + str(opened))
        project = field(opened[1], 'project')
        self.project = field(project, 'id')
        (self.evidence / ('opened-' + self.instance + '.sexp')).write_text(sexp(opened) + '\n')
        self.check(field(project, 'name') == 'FS3 acceptance', 'Actual daemon opens initialized manifest with its display name')

    def close(self):
        stop(self.process)
        if self.log:
            self.log.close()
            self.log = None

    def workspace(self, operation='Get', success=True):
        response = self.raw('workspace', [['instance_id', self.instance], ['project', self.project],
                                           ['operation', operation]])
        if success:
            require(response[0] == 'Ok', 'Workspace HTTP failed: ' + str(response))
            return response[1]
        return response

    def mutate(self, snapshot, mutation, success=True):
        return self.workspace(['Mutate', ['expected_revision', field(snapshot, 'revision')],
                               ['mutation', mutation]], success=success)

    def quiet(self):
        snapshot = self.raw('snapshot', [['instance_id', self.instance]])
        self.check(snapshot[0] == 'Ok' and field(snapshot[1], 'jobs') == [],
                   'No generic build/test/driver jobs were submitted')
        calls = [json.loads(line) for line in (self.evidence / 'metadata-calls.jsonl').read_text().splitlines()]
        self.check(bool(calls) and all(c['allowed'] for c in calls) and
                   not (self.evidence / 'forbidden-tools.jsonl').exists(),
                   'Only fixture metadata probes executed; no toolchain/provider actions')

    def imported(self, before, template, source, name, label, clone=False):
        window = field(field(before, 'windows')[0], 'id')
        created = self.cli('clone' if clone else 'import',
                           ['-window', window, '-name', name, str(source)], label).strip()
        after = self.workspace()
        new = [w for w in field(after, 'workspaces') if field(w, 'id') == created]
        self.check(len(new) == 1 and int(field(after, 'revision')) == int(field(before, 'revision')) + 1
                   and len(field(after, 'workspaces')) == len(field(before, 'workspaces')) + 1,
                   label + ': exactly one workspace and one atomic revision')
        workspace = new[0]
        self.check(field(workspace, 'name') == name and field(workspace, 'window') == window
                   and field(workspace, 'context') == field(after, 'main_context')
                   and field(workspace, 'zoomed_tile') == []
                   and field(after, 'contexts') == field(before, 'contexts'),
                    label + ': correct destination/name, Main-linked, no copied context or zoom')
        self.check(field(workspace, 'preset') == optional_field(template, 'preset', []),
                   label + ': optional preset identity preserved independently of name')
        tiles = [t for t in field(after, 'tiles') if field(t, 'workspace') == created]
        actual = [[['kind', field(t, 'kind')], ['hidden', field(t, 'hidden')],
                   ['geometry', field(t, 'requested_geometry')]] for t in tiles]
        old_ids = {field(t, 'id') for t in field(before, 'tiles')}
        self.check(actual == field(template, 'views') and all(field(t, 'binding') == 'Follow' for t in tiles)
                   and len({field(t, 'id') for t in tiles}) == len(tiles)
                   and not old_ids.intersection(field(t, 'id') for t in tiles),
                   label + ': ordered kinds/hidden/geometry preserved, fresh IDs and Follow bindings')
        self.check(all(w in field(after, 'workspaces') for w in field(before, 'workspaces'))
                   and all(t in field(after, 'tiles') for t in field(before, 'tiles')),
                   label + ': existing registry objects preserved')
        return after, created


class Terminal:
    def __init__(self, test, label):
        self.test, self.label, self.data = test, label, bytearray()
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))
        try:
            self.process = subprocess.Popen([str(test.args.terminal), '--connect', test.url,
                '--project-root', str(test.root)], stdin=slave, stdout=slave, stderr=slave,
                env=dict(test.env, TERM='xterm-256color'), start_new_session=True)
        finally:
            os.close(slave)

    def drain(self, seconds=.15):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if select.select([self.master], [], [], .04)[0]:
                try:
                    data = os.read(self.master, 65536)
                except OSError:
                    break
                if not data:
                    break
                self.data.extend(data)
        require(self.process.poll() is None, 'Terminal unexpectedly exited')
        return fs0.terminal_screen(bytes(self.data), width=120, height=40)

    def wait(self, label, expected=(), absent=(), ready=False):
        deadline = time.monotonic() + 20
        while True:
            text = self.drain()
            raw = not (termios.tcgetattr(self.master)[3] & (termios.ICANON | termios.ECHO))
            if (all(s in text for s in expected) and all(s not in text for s in absent)
                    and (not ready or raw)):
                break
            require(time.monotonic() < deadline, label + ': PTY timeout:\n' + text)
        (self.test.evidence / (self.label + '-' + label + '.txt')).write_text(text)
        return text

    def key(self, key):
        with (self.test.evidence / 'pty-keys.jsonl').open('a') as out:
            out.write(json.dumps(dict(session=self.label, hex=key.hex())) + '\n')
        os.write(self.master, key)
        self.drain()

    def palette(self, title, dispatch=True):
        for key in (b' ', b'c', b'c'):
            self.key(key)
        self.wait('palette', ['COMMAND PALETTE'])
        self.key(title.encode())
        self.wait('query-' + str(time.time_ns()), ['COMMAND PALETTE', title[:40], title[-60:]])
        if dispatch:
            self.key(b'\r')
            self.wait('dispatched', absent=['COMMAND PALETTE'])

    def close(self):
        stop(self.process)
        os.close(self.master)
        (self.test.evidence / (self.label + '.ansi')).write_bytes(self.data)
        self.test.result.setdefault('terminals', []).append(
            dict(label=self.label, pid=self.process.pid, stopped=self.process.poll() is not None))


def manifest_reload(test, manifest):
    original = manifest.read_text()
    changed = original.replace('FS3 acceptance', 'FS3 reloaded manifest')
    require(changed != original, 'Manifest fixture must contain its display name')
    calls = (test.evidence / 'metadata-calls.jsonl').read_bytes()
    manifest.write_text(changed)
    response = test.raw('refresh-integration', [['instance_id', test.instance], ['project', test.project]])
    test.check(response[0] == 'Ok' and field(response[1], 'job') == [],
               'Explicit manifest-only HTTP reload succeeds with no discovery job')
    snapshot = test.raw('snapshot', [['instance_id', test.instance]])
    project = next(p for p in field(snapshot[1], 'projects') if field(p, 'id') == test.project)
    test.check(field(project, 'name') == 'FS3 reloaded manifest' and field(snapshot[1], 'jobs') == []
               and (test.evidence / 'metadata-calls.jsonl').read_bytes() == calls,
               'Manifest-only reload applies edited name without metadata probes or tool execution')
    manifest.write_text(original)
    response = test.raw('refresh-integration', [['instance_id', test.instance], ['project', test.project]])
    test.check(response[0] == 'Ok' and field(response[1], 'job') == [],
               'Repeated manifest-only reload remains successful and job-free')


def terminal_integration(test, before, starters, header_id):
    require(field(before, 'defaults_initialized') == 'false', 'First TUI must see a pending bootstrap')
    terminals = []
    try:
        # Both processes race from the same pending persisted registry. The service must
        # serialize initialize-once independently of all preceding import revisions.
        terminals.append(Terminal(test, 'first-tui'))
        terminals.append(Terminal(test, 'concurrent-tui'))
        deadline = time.monotonic() + 25
        observations = [before]
        while True:
            current = test.workspace()
            observations.append(current)
            if field(current, 'defaults_initialized') == 'true':
                break
            require(current == before, 'Bootstrap exposed partial registry before completion')
            require(time.monotonic() < deadline, 'First TUI bootstrap deadline')
            for terminal in terminals:
                terminal.drain(.03)
        (test.evidence / 'bootstrap-observations.json').write_text(json.dumps(observations, indent=2))
        test.check(int(field(current, 'revision')) == int(field(before, 'revision')) + 1,
                   'Import-before-first-TUI and concurrent startup commit exactly one bootstrap revision')
        test.check(field(current, 'workspaces') == field(before, 'workspaces')
                   and field(current, 'contexts') == field(before, 'contexts'),
                   'Atomic bootstrap retains all arrangement/context identities, names and bindings')
        initial_ids = {field(w, 'id') for w in field(before, 'workspaces')[:2]}
        test.check([t for t in field(current, 'tiles') if field(t, 'workspace') not in initial_ids] ==
                   [t for t in field(before, 'tiles') if field(t, 'workspace') not in initial_ids],
                   'Bootstrap leaves every imported tile intact, including sparse preset membership')
        for workspace in field(current, 'workspaces')[:2]:
            preset = field(workspace, 'preset')[0]
            actual = [t for t in field(current, 'tiles') if field(t, 'workspace') == field(workspace, 'id')]
            expected = field(starters[preset], 'views')
            test.check(len(actual) == len(expected) and
                       sorted(sexp([field(t, 'kind'), field(t, 'requested_geometry')]) for t in actual) ==
                       sorted(sexp([field(v, 'kind'), field(v, 'geometry')]) for v in expected)
                       and all(field(t, 'hidden') == 'false' for t in actual),
                       'Initial ' + preset + ' defaults match the shared OCaml starter definitions')
        for terminal in terminals:
            terminal.wait('ready', ['Space c c commands'], ['Loading workspace...'], ready=True)
        test.check(test.workspace() == current, 'Second concurrent client performs no bootstrap rewrite')
        test.check(any(field(parse(path.read_text()), 'snapshot') == current
                       for path in test.state.glob('workspace-*.sexp')),
                   'Completed bootstrap marker and complete defaults are persisted in one registry snapshot')
        # A later startup must preserve a deliberately sparse/resized initial arrangement,
        # rather than merely reapplying identical defaults invisibly.
        selector = next(t for t in field(current, 'tiles') if field(t, 'workspace') in initial_ids
                        and field(t, 'kind') == 'run-selector')
        current = test.mutate(current, ['Resize_tile', ['tile', field(selector, 'id')],
            ['geometry', [['x', '11'], ['y', '13'], ['width', '37'], ['height', '9']]]])
        current = test.mutate(current, ['Set_tile_hidden', ['tile', field(selector, 'id')], ['hidden', 'true']])
        (test.evidence / 'post-bootstrap-user-layout.sexp').write_text(sexp(current) + '\n')
        terminals.pop().close()
        terminal = terminals[0]
        appearance = 'Appearance: C - Minimal'
        terminal.palette(appearance)

        def preferences(label, headers):
            deadline = time.monotonic() + 10
            while True:
                files = list((test.evidence / 'client-state').rglob('presentation-*.sexp'))
                stored = parse(files[0].read_text()) if len(files) == 1 else None
                if stored is not None and field(stored, 'tile_headers') == headers:
                    break
                require(time.monotonic() < deadline, label + ': preference save deadline')
                terminal.drain(.1)
            test.check(field(field(stored, 'appearance'), 'preset') == 'Minimal'
                       and field(stored, 'session') == [field(current, 'session_id')]
                       and files[0].stat().st_mode & 0o077 == 0,
                       label + ': private stored appearance/session and exact sparse header preferences')
            (test.evidence / (label + '-preferences.sexp')).write_text(sexp(stored) + '\n')
            return files[0], stored

        # First create stored preferences, then mutate header intent. This catches stale
        # replay of an earlier on-disk preference snapshot during ordinary polling.
        preferences('appearance-first', [])
        terminal.palette('Switch to Header acceptance')
        terminal.wait('inherited-header', ['project-tests', 'Project tests (not ASIC-run scoped)'])
        header_tile = next(t for t in field(current, 'tiles') if field(t, 'workspace') == header_id)
        override = [[['tile', field(header_tile, 'id')], ['workspace', header_id],
                     ['kind', 'project-tests'], ['headers', 'false']]]
        terminal.palette('Toggle focused tile header')
        terminal.wait('header-hidden', ['Project tests (not ASIC-run scoped)'], ['project-tests'])
        pref_file, stored = preferences('header-toggle', override)
        # Force both elapsed polling and a server-side registry transition without changing
        # the tile. The client's older appearance-first snapshot must not restore its header.
        current = test.mutate(current, ['Rename_workspace', ['workspace', header_id],
                                        ['name', 'Header acceptance polled']])
        terminal.drain(2.5)
        terminal.wait('header-hidden-after-poll', ['Header acceptance polled',
                      'Project tests (not ASIC-run scoped)'], ['project-tests'])
        test.check(parse(pref_file.read_text()) == stored,
                   'Polling preserves explicit header toggle after an existing preference load')

        # WB-019: main-window and palette bottom hints hide independently, persist with
        # the other presentation choices and are restorable by keyboard alone.
        def hint_preferences(label, main, palette):
            deadline = time.monotonic() + 10
            expected = ('true' if main else 'false', 'true' if palette else 'false')
            while True:
                files = list((test.evidence / 'client-state').rglob('presentation-*.sexp'))
                stored = parse(files[0].read_text()) if len(files) == 1 else None
                if stored is not None and (optional_field(stored, 'main_hints'),
                                           optional_field(stored, 'palette_hints')) == expected:
                    break
                require(time.monotonic() < deadline, label + ': hint preference save deadline')
                terminal.drain(.1)
            test.check(field(stored, 'schema_version') == '3'
                       and field(stored, 'chrome') == 'true'
                       and field(stored, 'tile_headers') == override
                       and field(stored, 'tile_appearance') == [],
                       label + ': hint choices persist without altering chrome or headers')

        def chord(key):
            for k in (b' ', b'c', key):
                terminal.key(k)

        def palette_hints_shown(label, shown):
            for k in (b' ', b'c', b'c'):
                terminal.key(k)
            hint = 'Enter run · Esc return'
            terminal.wait('palette-' + label, ['COMMAND PALETTE', '> '] + ([hint] if shown else []),
                          [] if shown else [hint])
            terminal.key(b'\x1b')
            terminal.wait('palette-closed-' + label, absent=['COMMAND PALETTE'])

        chord(b'h')
        terminal.wait('main-hints-hidden', absent=['Space c c commands'])
        palette_hints_shown('main-hidden', True)
        hint_preferences('main-hidden', False, True)
        chord(b'p')
        palette_hints_shown('all-hidden', False)
        hint_preferences('all-hidden', False, False)
        chord(b'h')
        palette_hints_shown('palette-hidden', False)
        hint_preferences('palette-hidden', True, False)
        terminal.wait('main-hints-restored', ['Space c c commands'])
        chord(b'h')
        hint_preferences('all-hidden-again', False, False)
        terminal.close()
        terminals.clear()

        # Fresh client: both hint areas stay hidden, and the keyboard restores each one.
        terminal = Terminal(test, 'hints-restart')
        terminals.append(terminal)
        # With the footer hidden there is no ready marker: retry until the loaded
        # registry lets the palette capture a target.
        deadline = time.monotonic() + 20
        while 'COMMAND PALETTE' not in terminal.drain(.5):
            require(time.monotonic() < deadline, 'hints-restart: palette never opened')
            terminal.key(b'\x1b')
            for k in (b' ', b'c', b'c'):
                terminal.key(k)
        terminal.key(b'\x1b')
        terminal.wait('restart-loaded', absent=['COMMAND PALETTE'])
        palette_hints_shown('restart-all-hidden', False)
        terminal.wait('restart-main-hidden', absent=['Space c c commands', 'Loading workspace...'])
        chord(b'p')
        palette_hints_shown('restart-palette-restored', True)
        chord(b'h')
        terminal.wait('restart-main-restored', ['Space c c commands'])
        hint_preferences('restored', True, True)
        terminal.close()
        terminals.clear()

        # Restart both daemon and client; registry bootstrap and saved header must survive.
        test.close()
        test.start()
        test.check(test.workspace() == current, 'Daemon restart retains completed bootstrap without layout rewrite')
        terminal = Terminal(test, 'header-restart')
        terminals.append(terminal)
        terminal.wait('ready', ['Space c c commands'], ['Loading workspace...'], ready=True)
        terminal.palette(appearance, dispatch=False)
        terminal.wait('appearance-restored', [appearance + ' [active]'])
        terminal.key(b'\x1b')
        terminal.palette('Switch to Header acceptance polled')
        terminal.wait('header-restored-hidden', ['Project tests (not ASIC-run scoped)'], ['project-tests'])
        preferences('restart-toggle', override)
        terminal.palette('Reset presentation overrides (inherit)')
        terminal.wait('header-reset', ['project-tests', 'Project tests (not ASIC-run scoped)'])
        pref_file, reset = preferences('header-reset', [])
        current = test.mutate(current, ['Rename_workspace', ['workspace', header_id],
                                        ['name', 'Header acceptance reset']])
        terminal.drain(2.5)
        terminal.wait('header-reset-after-poll', ['Header acceptance reset', 'project-tests'])
        test.check(parse(pref_file.read_text()) == reset,
                   'Actual palette reset persists inheritance and survives subsequent polling')
        terminal.close()
        terminals.clear()

        terminal = Terminal(test, 'reset-restart')
        terminals.append(terminal)
        terminal.wait('ready', ['Space c c commands'], ['Loading workspace...'], ready=True)
        terminal.palette('Switch to Header acceptance reset')
        terminal.wait('reset-restored', ['project-tests', 'Project tests (not ASIC-run scoped)'])
        preferences('restart-reset', [])
        test.check(test.workspace() == current,
                   'Subsequent fresh clients restore reset intent without rewriting bootstrapped registry')
        return current
    finally:
        for terminal in reversed(terminals):
            terminal.close()


def exercise(test):
    root = test.root
    (root / 'dune-project').write_text('(lang dune 3.22)\n(name fs3_acceptance)\n')
    (root / 'dune').write_text('(dirs)\n')
    original = {p.name: p.read_bytes() for p in root.iterdir()}
    init = ['--root', root, '--project-name', 'FS3 acceptance',
            '--build-alias', '@acceptance-build', '--test-alias', '@acceptance-test']
    dry = test.command(test.args.setup, init + ['--dry-run'], 'initialize-dry-run')
    test.check({p.name: p.read_bytes() for p in root.iterdir()} == original,
               'Initializer dry run leaves disposable Dune project byte-for-byte unchanged')
    test.command(test.args.setup, init, 'initialize')
    manifest = root / 'hardcaml-workbench.sexp'
    test.check(manifest.read_text() == dry and set(p.name for p in root.iterdir()) == set(original) | {manifest.name}
               and all((root / name).read_bytes() == data for name, data in original.items()),
               'Initializer writes only the previewed manifest and preserves Dune inputs')
    test.command(test.args.setup, init, 'initialize-existing', error='refusing to overwrite')
    test.check(manifest.read_text() == dry, 'Repeated initialization preserves existing manifest')
    child = root / 'nested'
    child.mkdir()
    test.command(test.args.setup, ['--root', child], 'initialize-no-ancestor',
                 error='must directly contain a regular dune-project file')
    test.check(list(child.iterdir()) == [], 'Initializer does not discover ancestor Dune markers')
    test.start()
    manifest_reload(test, manifest)
    initial = test.workspace()
    test.check(field(initial, 'defaults_initialized') == 'false',
               'New registry explicitly awaits shared-definition bootstrap')
    current = initial
    starters = {}
    for kind, count in [('generic', 4), ('asic', 9), ('overview', 11), ('timing', 6), ('testing', 10)]:
        text = test.command(test.args.workspace_cli, ['starter', kind], 'starter-' + kind)
        template = parse(text)
        starters[kind] = template
        test.check(field(template, 'version') == '1' and len(field(template, 'views')) == count,
                   kind + ' offline starter has expected version and view count')
        if kind == 'testing':
            test.check([field(view, 'kind') for view in field(template, 'views')] ==
                       ['workspace-tabs', 'live-status', 'project-tests', 'execution',
                        'simulation-catalog', 'simulation-attempts', 'simulation-cases',
                        'simulation-detail', 'simulation-artifacts', 'simulation-logs'],
                       'Testing starter has exact ordered cooperative panes without ASIC run selector')
        path = test.evidence / (kind + '.sexp')
        path.write_text(text)
        current, created = test.imported(current, template, path, kind + ' imported', 'import-' + kind)
        exported = test.cli('export', [created], 'export-' + kind)
        expected = portable(template, kind + ' imported')
        test.check(parse(exported) == expected, kind + ' export contains exactly portable layout fields')
        if kind in ('overview', 'timing', 'testing'):
            current = test.mutate(current, ['Rename_workspace', ['workspace', created], ['name', kind + ' renamed']])
            renamed = parse(test.cli('export', [created], 'export-renamed-' + kind))
            test.check(renamed == portable(template, kind + ' renamed') and field(renamed, 'preset') == [kind],
                       kind + ' shared preset identity and exact composition survive an authoritative rename')
            renamed_path = test.evidence / (kind + '-renamed.sexp')
            renamed_path.write_text(sexp(renamed))
            current, _ = test.imported(current, renamed, renamed_path, kind + ' renamed roundtrip',
                                       'roundtrip-renamed-' + kind)
        if kind == 'generic':
            generic_id = created
    legacy = [entry for entry in portable(starters['generic'], 'Legacy custom') if entry[0] != 'preset']
    unknown = replace_field(portable(starters['generic'], 'Unknown preset'), 'preset', ['future-fs3-preset'])
    sparse = replace_field(portable(starters['overview'], 'Sparse preset'), 'views', [])
    for label, template in [('legacy', legacy), ('unknown-preset', unknown), ('sparse-preset', sparse)]:
        path = test.evidence / (label + '.sexp')
        path.write_text(sexp(template))
        current, created = test.imported(current, template, path, field(template, 'name'), 'import-' + label)
        test.check(parse(test.cli('export', [created], 'export-' + label)) == portable(template),
                   label + ' roundtrip preserves optional/unknown identity and sparse membership honestly')
    header = replace_field(portable(starters['generic'], 'Header acceptance'), 'views',
                           [v for v in field(starters['generic'], 'views') if field(v, 'kind') == 'project-tests'])
    header_path = test.evidence / 'header-acceptance.sexp'
    header_path.write_text(sexp(header))
    current, header_id = test.imported(current, header, header_path, 'Header acceptance', 'import-header')
    listing = test.cli('list', [], 'list-workspaces')
    test.check(all(field(w, 'id') in listing and field(w, 'name') in listing
                   for w in field(current, 'workspaces'))
               and all(field(w, 'id') in listing for w in field(current, 'windows')),
               'Workspace listing exposes window and workspace identities for CLI use')
    # Exercise nondefault geometry, hidden/unknown views, source independence and
    # zoom, so clone cannot pass merely by repeating a predefined starter.
    current = test.mutate(current, ['Make_independent', generic_id])
    tile = next(t for t in field(current, 'tiles') if field(t, 'workspace') == generic_id)
    current = test.mutate(current, ['Set_tile_hidden', ['tile', field(tile, 'id')], ['hidden', 'true']])
    current = test.mutate(current, ['Resize_tile', ['tile', field(tile, 'id')],
        ['geometry', [['x', '7'], ['y', '9'], ['width', '23'], ['height', '11']]]])
    visible = next(t for t in field(current, 'tiles')
                   if field(t, 'workspace') == generic_id and field(t, 'hidden') == 'false')
    current = test.mutate(current, ['Set_zoom', ['workspace', generic_id], ['tile', [field(visible, 'id')]]])
    current = test.mutate(current, ['Create_tile', ['workspace', generic_id], ['kind', 'future-fs3-view'],
        ['geometry', [['x', '2'], ['y', '3'], ['width', '17'], ['height', '13']]]])
    portable_text = test.cli('export', [generic_id], 'export-customized')
    template = parse(portable_text)
    custom = test.evidence / 'customized.sexp'
    custom.write_text(portable_text)
    test.check(any(field(v, 'hidden') == 'true' for v in field(template, 'views'))
               and any(field(v, 'kind') == 'future-fs3-view' for v in field(template, 'views')),
               'Export preserves hidden and extensible unknown views')
    current, clone_id = test.imported(current, template, generic_id, 'cloned custom', 'clone-custom', clone=True)
    current, imported_id = test.imported(current, template, custom, 'roundtrip custom', 'import-custom')
    stale = test.mutate(initial, ['Instantiate_template', ['window', field(field(current, 'windows')[0], 'id')],
                                ['template', template]], success=False)
    test.check(stale[0] == 'Error' and field(stale[1], 'kind') == 'Conflict'
               and test.workspace() == current, 'Stale template mutation conflicts without partial registry change')
    bad_geometry = copy.deepcopy(template)
    for entry in field(field(bad_geometry, 'views')[0], 'geometry'):
        if entry[0] == 'width':
            entry[1] = '0'
    rejected = test.mutate(current, ['Instantiate_template',
        ['window', field(field(current, 'windows')[0], 'id')], ['template', bad_geometry]], success=False)
    test.check(rejected[0] == 'Error' and field(rejected[1], 'kind') == 'Invalid_request'
               and test.workspace() == current,
               'Actual HTTP daemon independently rejects invalid template geometry atomically')
    for label, text, diagnostic in [
        ('version', portable_text.replace('(version 1)', '(version 99)'), 'Unsupported workspace template version'),
        ('geometry', sexp(bad_geometry), 'geometry'),
        ('oversized', ' ' * (1024 * 1024 + 1), 'exceeds 1 MiB'),
        ('malformed', '(', '')]:
        invalid = test.evidence / ('invalid-' + label + '.sexp')
        invalid.write_text(text)
        test.cli('import', ['-window', field(field(current, 'windows')[0], 'id'), invalid],
                 'reject-' + label, error=diagnostic)
        test.check(test.workspace() == current, label + ' invalid import leaves complete registry unchanged')
    test.cli('import', ['-window', 'missing-window', custom], 'reject-window', error='Not_found')
    test.check(test.workspace() == current, 'Missing destination rejects atomically')
    test.quiet()
    (test.evidence / 'registry-before-restart.sexp').write_text(sexp(current) + '\n')
    old_instance = test.instance
    test.close()
    test.check(bool(list(test.state.glob('workspace-*.sexp'))), 'Daemon produced a private persistent workspace registry')
    test.start()
    test.check(test.instance != old_instance and test.workspace() == current,
               'Fresh daemon instance restores exact registry: IDs, revision, contexts, tiles, geometry, hidden and zoom')
    (test.evidence / 'registry-after-restart.sexp').write_text(sexp(test.workspace()) + '\n')
    for workspace, name in [(clone_id, 'cloned custom'), (imported_id, 'roundtrip custom')]:
        test.check(parse(test.cli('export', [workspace], 'export-after-restart-' + workspace)) ==
                   portable(template, name),
                    'CLI exports restored ' + name + ' after daemon restart')
    if not test.args.skip_pty:
        current = terminal_integration(test, current, starters, header_id)
    else:
        test.result['skipped'] = ['PTY bootstrap/startup concurrency and header toggle/reset/restart']
    test.quiet()
    test.result['status'] = 'passed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name, directory in [('setup', 'setup'), ('workspace-cli', 'workspace_cli'),
                            ('daemon', 'daemon'), ('terminal', 'terminal')]:
        parser.add_argument('--' + name, type=Path, default=REPO / '_build/default' / directory / 'main.exe')
    parser.add_argument('--skip-pty', action='store_true', help='Run initializer/HTTP/CLI acceptance only')
    parser.add_argument('--evidence', type=Path, help='New evidence directory under /tmp/opencode')
    args = parser.parse_args()
    base = Path('/tmp/opencode')
    require(base.is_dir(), '/tmp/opencode must exist')
    if args.evidence:
        args.evidence = args.evidence.resolve()
        require(args.evidence.is_relative_to(base) and args.evidence != base, 'Evidence must be under /tmp/opencode')
        args.evidence.mkdir(mode=0o700)
    else:
        args.evidence = Path(tempfile.mkdtemp(prefix='fs3-adoption-', dir=base))
    for name in ('setup', 'workspace_cli', 'daemon', 'terminal'):
        binary = getattr(args, name).resolve()
        require(binary.is_file() and os.access(binary, os.X_OK), 'Missing built executable: ' + str(binary))
        setattr(args, name, binary)
    print('Evidence:', args.evidence, flush=True)
    test = Acceptance(args)
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
