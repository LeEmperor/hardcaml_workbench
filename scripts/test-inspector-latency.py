#!/usr/bin/env python3
"""Parent-run real PTY ESC latency probe; existing binaries, retained cached data.

No builds, Git, EDA, installation, or source-evidence writes. All children and
evidence are private. Default detail is the cache-only `d` source-metadata pane.
--detail-mode real permits only exact cached
row/digest read-only detail queries, during setup outside measurement intervals.
--detail-mode denied diagnoses a provider-denied row-detail error rather than
claiming successful detail evidence.

Each case compares single-byte ESC with ESC followed 50 ms later by NUL (an
unmapped neutral control). A timeout is retained as a censored observation, not
silently fixed by another key. Detail ESC targets the table; table/palette ESC
targets Overview. Latencies are host PTY-observation upper bounds, including
screen reconstruction, not compositor/display or instrumented decoder timings.
--tmux-escape-time adds a private tmux server/attach transport with an explicit
escape-time in milliseconds. Without it the application runs directly in the PTY.
"""
import argparse
import codecs
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import signal
import statistics
import struct
import subprocess
import sys
import tempfile
import termios
import time
import traceback
import unicodedata

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location(
    'investigation', Path(__file__).with_name('test-fs1-investigation.py'))
investigation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(investigation)
metrics, fs0 = investigation.metrics, investigation.fs0
field, require, save = investigation.field, investigation.require, investigation.save
STAGES = investigation.DEFAULTS


class Screen:
    """Incremental ANSI/VT screen, including tmux's erase/charset/scroll output."""
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.rows = [[' '] * width for _ in range(height)]
        self.x = self.y = 0
        self.top, self.bottom = 0, height - 1
        self.saved = (0, 0)
        self.alternate = None
        self.origin = self.insert = self.wrap_pending = False
        self.autowrap = True
        self.pending = ''
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')

    def feed(self, raw):
        self.pending += self.decoder.decode(raw)
        while self.pending:
            if self.pending[0] == '\x1b':
                if len(self.pending) == 1:
                    return
                # Dispatch by introducer: an incomplete CSI/OSC must never fall
                # back to a short generic ESC token. ESC ( B is one sequence,
                # not ESC ( followed by a printable B (charset selection).
                introducer = self.pending[1]
                pattern = (r'\x1b\[[0-?]*[ -/]*[@-~]' if introducer == '[' else
                           r'\x1b\].*?(?:\x07|\x1b\\)' if introducer == ']' else
                           r'\x1b[PX^_].*?\x1b\\' if introducer in 'PX^_' else
                           r'\x1b[ -/]*[0-~]')
                match = re.match(pattern, self.pending, re.S)
                if not match:
                    return  # Keep split escape sequences until their next bytes.
                token = match[0]
                self.pending = self.pending[len(token):]
                if introducer == '[':
                    self.csi(token[2:-1], token[-1])
                elif token == '\x1b7':
                    self.saved = (self.x, self.y)
                elif token == '\x1b8':
                    self.x, self.y = self.saved
                    self.wrap_pending = False
                elif token in ('\x1bD', '\x1bE'):
                    self.linefeed()
                    if token == '\x1bE':
                        self.x = 0
                elif token == '\x1bM':
                    self.wrap_pending = False
                    if self.y == self.top:
                        self.scroll(1, down=True)
                    else:
                        self.y = max(0, self.y - 1)
                elif token == '\x1bc':
                    self.rows = [[' '] * self.width for _ in range(self.height)]
                    self.x = self.y = 0
                    self.top, self.bottom = 0, self.height - 1
                    self.origin = self.insert = self.wrap_pending = False
                    self.autowrap = True
            else:
                end = self.pending.find('\x1b')
                if end < 0:
                    end = len(self.pending)
                text, self.pending = self.pending[:end], self.pending[end:]
                for char in text:
                    if char == '\r':
                        self.x = 0
                        self.wrap_pending = False
                    elif char in '\n\v\f':
                        self.linefeed()
                    elif char == '\b':
                        self.x = max(0, self.x - 1)
                        self.wrap_pending = False
                    elif char == '\t':
                        self.x = min(self.width - 1, (self.x // 8 + 1) * 8)
                        self.wrap_pending = False
                    elif char >= ' ' and char != '\x7f':
                        self.put(char)

    def scroll(self, count, down=False, top=None):
        top = self.top if top is None else top
        count = min(count, self.bottom - top + 1)
        blanks = [[' '] * self.width for _ in range(count)]
        region = self.rows[top:self.bottom + 1]
        self.rows[top:self.bottom + 1] = (blanks + region[:len(region) - count] if down
                                        else region[count:] + blanks)

    def linefeed(self):
        self.wrap_pending = False
        if self.y == self.bottom:
            self.scroll(1)
        else:
            self.y = min(self.height - 1, self.y + 1)

    def put(self, char):
        if unicodedata.combining(char):
            x = self.x if self.wrap_pending else max(0, self.x - 1)
            if self.rows[self.y][x] == '' and x:
                x -= 1
            self.rows[self.y][x] += char
            return
        size = 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
        if self.autowrap and (self.wrap_pending or self.x + size > self.width):
            self.x = 0
            self.linefeed()
        row = self.rows[self.y]
        if self.insert:
            row[self.x:self.x] = [' '] * size
            del row[self.width:]
        row[self.x] = char
        if size == 2 and self.x + 1 < self.width:
            row[self.x + 1] = ''
        self.wrap_pending = self.autowrap and self.x + size >= self.width
        self.x = min(self.width - 1, self.x + size)

    def csi(self, values, code):
        private = values.startswith('?')
        values = values[1:] if private else values
        if not re.fullmatch(r'[0-9;]*', values):
            return  # Styling/extensions with intermediate bytes do not paint.
        a = [int(v or 0) for v in values.split(';')]
        n = a[0] or 1
        if code in 'hl':
            enabled = code == 'h'
            for mode in a:
                if private and mode == 7:
                    self.autowrap = enabled
                elif private and mode == 6:
                    self.origin = enabled
                    self.x, self.y = 0, self.top if enabled else 0
                elif private and mode in (47, 1047, 1049):
                    if enabled and self.alternate is None:
                        self.alternate = (self.rows, self.x, self.y, self.top, self.bottom)
                        self.rows = [[' '] * self.width for _ in range(self.height)]
                        self.x = self.y = 0
                        self.top, self.bottom = 0, self.height - 1
                    elif not enabled and self.alternate is not None:
                        self.rows, self.x, self.y, self.top, self.bottom = self.alternate
                        self.alternate = None
                elif not private and mode == 4:
                    self.insert = enabled
            self.wrap_pending = False
            return
        if private:
            return
        # SGR/queries must not cancel the delayed wrap at the right margin.
        if code in 'mcn':
            return
        self.wrap_pending = False
        low, high = (self.top, self.bottom) if self.origin else (0, self.height - 1)
        if code in 'Hf':
            self.y = max(low, min(high, low + n - 1))
            self.x = min(self.width - 1, ((a[1] or 1) if len(a) > 1 else 1) - 1)
        elif code in 'ABeEF':
            self.y = max(low, min(high, self.y + (-n if code in 'AF' else n)))
            if code in 'EF':
                self.x = 0
        elif code in 'Ca':
            self.x = min(self.width - 1, self.x + n)
        elif code == 'D':
            self.x = max(0, self.x - n)
        elif code in 'G`':
            self.x = min(self.width - 1, n - 1)
        elif code == 'd':
            self.y = max(low, min(high, low + n - 1))
        elif code == 'J':
            # ED0 includes the cursor through end of display; ED1 includes
            # start through cursor. Neither operation moves the cursor.
            if a[0] in (0, 1, 2):
                for y in range(self.height):
                    start, end = 0, self.width
                    if a[0] == 0:
                        start = self.x if y == self.y else 0
                        if y < self.y:
                            continue
                    elif a[0] == 1:
                        end = self.x + 1 if y == self.y else self.width
                        if y > self.y:
                            continue
                    self.rows[y][start:end] = [' '] * (end - start)
            # ED3 erases scrollback only, not the visible screen.
        elif code == 'K':
            if a[0] in (0, 1, 2):
                start, end = ((0, self.width) if a[0] == 2 else
                              (0, self.x + 1) if a[0] == 1 else (self.x, self.width))
                self.rows[self.y][start:end] = [' '] * (end - start)
        elif code in 'X@P':
            count = min(n, self.width - self.x)
            row = self.rows[self.y]
            if code == 'X':
                row[self.x:self.x + count] = [' '] * count
            elif code == '@':
                row[self.x:self.x] = [' '] * count
                del row[self.width:]
            else:
                del row[self.x:self.x + count]
                row.extend([' '] * count)
        elif code in 'LM' and self.top <= self.y <= self.bottom:
            self.scroll(n, down=code == 'L', top=self.y)
        elif code in 'ST':
            self.scroll(n, down=code == 'T')
        elif code == 'r':
            top, bottom = n - 1, ((a[1] or self.height) if len(a) > 1 else self.height) - 1
            if 0 <= top < bottom < self.height:
                self.top, self.bottom = top, bottom
                self.x, self.y = 0, top if self.origin else 0
        elif code == 's':
            self.saved = (self.x, self.y)
        elif code == 'u':
            self.x, self.y = self.saved

    def text(self):
        return '\n'.join(''.join(row).rstrip() for row in self.rows)


def screen_self_check():
    """Pure Python only: no files, child processes, daemon, PTY, or tmux."""
    seed = '\x1b[1;1HAAAAAAAA\x1b[2;1HBBBBBBBB\x1b[3;1HCCCCCCCC\x1b[4;1HDDDDDDDD'
    cases = [
        ('charset', '\x1b(Bx\x1b)0y', ['xy', '', '', '']),
        ('erase-tail', seed + '\x1b[2;3H\x1b[J', ['AAAAAAAA', 'BB', '', '']),
        ('erase-head', seed + '\x1b[2;3H\x1b[1J', ['', '   BBBBB', 'CCCCCCCC', 'DDDDDDDD']),
        ('erase-all', seed + '\x1b[2;3H\x1b[2JQ', ['', '  Q', '', '']),
        ('scrollback-only', seed + '\x1b[3J', ['AAAAAAAA', 'BBBBBBBB', 'CCCCCCCC', 'DDDDDDDD']),
        ('stale-wait', 'Waiting\x1b[1;1H\x1b[Jready', ['ready', '', '', '']),
        ('insert-delete-chars', 'abcdef\x1b[1;3H\x1b[2@XY\x1b[P', ['abXYdef', '', '', '']),
        ('erase-chars', 'abcdef\x1b[1;3H\x1b[2X', ['ab  ef', '', '', '']),
        ('insert-line', seed + '\x1b[2;1H\x1b[L', ['AAAAAAAA', '', 'BBBBBBBB', 'CCCCCCCC']),
        ('delete-line', seed + '\x1b[2;1H\x1b[M', ['AAAAAAAA', 'CCCCCCCC', 'DDDDDDDD', '']),
        ('region-linefeed', seed + '\x1b[2;3r\x1b[3;1H\n', ['AAAAAAAA', 'CCCCCCCC', '', 'DDDDDDDD']),
        ('region-reverse', seed + '\x1b[2;3r\x1b[2;1H\x1bM', ['AAAAAAAA', '', 'BBBBBBBB', 'DDDDDDDD']),
        ('scroll-up', seed + '\x1b[S', ['BBBBBBBB', 'CCCCCCCC', 'DDDDDDDD', '']),
        ('scroll-down', seed + '\x1b[T', ['', 'AAAAAAAA', 'BBBBBBBB', 'CCCCCCCC']),
        ('save-restore', 'ab\x1b7\x1b[3;4HX\x1b8Y', ['abY', '', '   X', '']),
        ('alternate', 'main\x1b[?1049hother\x1b[?1049l!', ['main!', '', '', '']),
        ('strings-utf8', '\x1b]0;ignored\x07\x1bPignored\x1b\\café', ['café', '', '', '']),
        ('delayed-wrap', '12345678\x1b[0m9', ['12345678', '9', '', '']),
    ]
    for label, text, expected in cases:
        raw = text.encode('utf-8')
        # Check every two-chunk boundary, plus maximally fragmented bytes.
        chunks = [[raw[:i], raw[i:]] for i in range(len(raw) + 1)]
        chunks.append([raw[i:i + 1] for i in range(len(raw))])
        for parts in chunks:
            screen = Screen(8, 4)
            for part in parts:
                screen.feed(part)
            require(screen.pending == '' and screen.text() == '\n'.join(expected),
                    'Screen self-check failed: %s\n%r' % (label, screen.text()))
    print('PASS: pure-Python screen self-check (%d cases, all byte boundaries)' % len(cases))


def cpu(pid):
    try:
        s = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
        ticks = os.sysconf('SC_CLK_TCK')
        return dict(user_seconds=int(s[11]) / ticks, system_seconds=int(s[12]) / ticks,
                    start_ticks=s[19], state=s[0])
    except (OSError, ValueError):
        return None


def rekey_envelope(raw, old, new):
    """Replace only the top-level identity atom; keep every other byte exact."""
    tokens = re.finditer(rb'\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+', raw)
    depth, key, atoms = 0, None, 0
    spans = []
    for token in tokens:
        value = token[0]
        if value == b'(':
            if depth == 1:
                key, atoms = None, 0
            depth += 1
        elif value == b')':
            if depth == 2 and key == 'identity':
                require(atoms == 2, 'Envelope identity must be a single atom')
            depth -= 1
        elif depth == 2:
            if atoms == 0:
                key = metrics.parse(value.decode('utf-8'))
            elif key == 'identity':
                require(atoms == 1 and metrics.parse(value.decode('utf-8')) == old,
                        'Unexpected envelope identity atom')
                spans.append(token.span())
            atoms += 1
    require(depth == 0 and len(spans) == 1, 'Expected exactly one envelope identity')
    start, end = spans[0]
    replacement = fs0.sexp(new).encode('utf-8')
    require(metrics.parse(replacement.decode('utf-8')) == new, 'Invalid replacement identity encoding')
    return raw[:start] + replacement + raw[end:]


def prepare(args):
    base = args.evidence
    for name in ('project', 'state', 'results', 'home', 'config', 'cache', 'tmp', 'bin'):
        (base / name).mkdir(mode=0o700)
    root = base / 'project'
    (root / 'dune-project').write_text('(lang dune 3.17)\n(name inspector_latency)\n')
    registries = [p for p in args.source_state.glob('asic-*.sexp')
                  if '-summary-' not in p.name and '-inspections-' not in p.name]
    require(len(registries) == 1, 'Expected one source ASIC registry')
    registry = metrics.parse(registries[0].read_text())
    old = field(registry, 'identity')
    identity = metrics.parse(old)
    require(metrics.mach(identity) == old and identity[1] == 'Inherit_daemon', 'Unsupported identity')
    prefix = 'asic-' + metrics.digest(old)
    require(registries[0].name == prefix + '.sexp', 'Source registry hash mismatch')
    cfg = identity[2][0]
    cache_path = args.source_state / (prefix + '-inspections-v1.sexp')
    cache = metrics.parse(cache_path.read_text())
    require(field(cache, 'identity') == old and field(cache, 'version') == '1', 'Inspection identity mismatch')
    indexes = [field(e, 'index') for e in field(cache, 'entries')]
    # Typed Sexplib float canonicalization is authoritative for index digests;
    # Python's generic serializer cannot reproduce it. Preserve embedded payloads
    # byte-for-byte and let the backend validate their retained digests on load.
    chosen = {d: next(i for i in indexes if field(i, 'domain') == d and field(i, 'stage') == s)
              for d, s in STAGES.items()}
    require(sum(field(r, 'category') == 'timing_path' for r in field(chosen['timing'], 'rows')) == 1020,
            'Expected actual retained 1020 timing paths')
    runs = field(registry, 'runs')
    require(len(runs) == 1, 'Expected one accepted registered run')
    run = field(runs[0], 'run')
    require(all(field(i, 'run') == run for i in indexes), 'Mixed cached run identities')
    # The relay has no path to the expired source relay. Only exact detail tuples
    # from validated retained indexes may reach the optional current provider.
    allowed = []
    for index in chosen.values():
        for row in field(index, 'rows'):
            allowed.append(['inspect', field(index, 'execution_file'), '--domain', field(index, 'domain'),
                            '--stage', field(index, 'stage'), '--json', '--row-id', field(row, 'id'),
                            '--expected-digest', field(index, 'source_digest')])
    save(base / 'detail-allowlist.json', allowed)
    guard = base / 'provider-guard'
    guard.write_text('#!' + sys.executable + '\nBASE = ' + repr(str(base)) + '\n' +
                     'PROVIDER = ' + repr(str(args.provider) if args.provider else None) + '\n' + r'''
import json, pathlib, subprocess, sys, time
b = pathlib.Path(BASE)
a = sys.argv[1:]
ok = ((b / 'detail-setup-enabled').exists() and PROVIDER is not None
      and (a == ['--version', '--json'] or a in json.loads((b / 'detail-allowlist.json').read_text())))
with (b / 'provider-calls.jsonl').open('a') as f:
    f.write(json.dumps(dict(argv=a, allowed=ok, monotonic_ns=time.monotonic_ns())) + '\n')
if not ok:
    sys.exit('Inspector latency: provider denied outside exact read-only detail setup')
p = subprocess.run([PROVIDER] + a, capture_output=True, timeout=30)
stem = b / ('detail-query-' + str(time.time_ns()))
stem.with_suffix('.stdout').write_bytes(p.stdout)
stem.with_suffix('.stderr').write_bytes(p.stderr)
stem.with_suffix('.json').write_text(json.dumps(dict(argv=a, returncode=p.returncode)))
sys.stdout.buffer.write(p.stdout)
sys.stderr.buffer.write(p.stderr)
sys.exit(p.returncode)
''')
    guard.chmod(0o700)
    deny = base / 'bin' / 'deny'
    deny.write_text('#!' + sys.executable + '\nimport sys\nsys.exit("Inspector latency forbids project/tool execution")\n')
    deny.chmod(0o700)
    # No external metadata tools either: the private marker is sufficient.
    for name in ('git', 'nix', 'nix-shell', 'make', 'openroad', 'yosys'):
        (base / 'bin' / name).symlink_to('deny')
    for key, value in (('provider_executable', str(guard)), ('project_executable', str(deny)),
                       ('results_root', str(base / 'results'))):
        cfg = metrics.put(cfg, key, value)
    (root / 'hardcaml-workbench-asic.sexp').write_text(metrics.mach(cfg) + '\n')
    new = metrics.mach([str(root), identity[1], [cfg]])
    new_prefix = 'asic-' + metrics.digest(new)
    copied = []
    # Workspace is intentionally fresh (Overview); retain real registry, summary,
    # all inspection rows and their digests. Only envelope identities are rekeyed.
    for source in sorted(args.source_state.glob(prefix + '*.sexp')):
        require(not source.is_symlink(), 'Refusing symlink state input')
        target = base / 'state' / source.name.replace(prefix, new_prefix, 1)
        if source == registries[0] or source == cache_path:
            target.write_bytes(rekey_envelope(source.read_bytes(), old, new))
        else:
            require(source.name.startswith(prefix + '-summary-v1-'), 'Unexpected source state')
            target.write_bytes(source.read_bytes())
        copied.append(dict(source=str(source), target=str(target), source_sha256=investigation.sha256(source),
                           target_sha256=investigation.sha256(target)))
    require(any('-summary-v1-' in c['target'] for c in copied), 'No retained summary')
    save(base / 'copied-state.json', dict(files=copied, old_identity=old, new_identity=new,
         indexes={d: len(field(i, 'rows')) for d, i in chosen.items()}))
    return root, run, chosen


class Terminal:
    def __init__(self, session):
        self.session, self.args = session, session.args
        self.screen = Screen(self.args.width, self.args.height)
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ,
                    struct.pack('HHHH', self.args.height, self.args.width, 0, 0))
        self.raw = (session.evidence / 'pty.ansi').open('wb')
        self.events = (session.evidence / 'pty-events.jsonl').open('a')
        self.keys = (session.evidence / 'keys.jsonl').open('a')
        self.offset = 0
        self.process = None
        self.tmux_base = None
        self.app_tty = None
        self.env = dict(session.env, TERM='xterm-256color')
        self.env.pop('TMUX', None)
        self.env.pop('TMUX_PANE', None)
        app = [str(self.args.client), '--connect', session.url, '--project-root', str(session.root)]
        try:
            argv = app
            if self.args.tmux_escape_time is not None:
                socket = session.evidence / 'private.sock'
                config = session.evidence / 'tmux.conf'
                require(not socket.exists(), 'Private tmux socket already exists')
                config.write_text('set-option -s escape-time %d\n'
                                  'set-option -g status off\n'
                                  'set-option -g default-terminal xterm-256color\n'
                                  'set-option -s exit-empty on\n' % self.args.tmux_escape_time)
                self.tmux_base = [str(self.args.tmux), '-S', str(socket), '-f', str(config)]
                # Direct argv launch, no interactive shell, user config, or hooks.
                # exec keeps the newly created pane PID as the application PID.
                launcher = session.evidence / 'tmux-app.py'
                launcher.write_text('import os\nos.execv(' + repr(app[0]) + ', ' + repr(app) + ')\n')
                self.tmux_command(['new-session', '-d', '-s', 'latency',
                                   '-x', str(self.args.width), '-y', str(self.args.height),
                                   '--', sys.executable, str(launcher)])
                actual_escape_time = self.tmux_command(
                    ['show-options', '-s', '-v', 'escape-time']).stdout.decode().strip()
                require(actual_escape_time == str(self.args.tmux_escape_time),
                        'Private tmux escape-time differs from requested setting')
                info = self.tmux_command(['display-message', '-p', '-t', 'latency:0.0',
                                          '#{pane_pid}\n#{pane_tty}\n#{pid}']).stdout.decode().splitlines()
                require(len(info) == 3, 'Invalid private tmux pane identity')
                self.app_pid, self.app_tty, server_pid = int(info[0]), info[1], int(info[2])
                require(self.app_pid > 1 and server_pid > 1 and self.app_tty.startswith('/dev/pts/'),
                        'Invalid private pane PID/TTY')
                save(session.evidence / 'tmux.json', dict(
                    socket=str(socket), config=str(config), config_text=config.read_text(),
                    escape_time=self.args.tmux_escape_time, verified_escape_time=actual_escape_time,
                    pane_pid=self.app_pid,
                    pane_tty=self.app_tty, server_pid=server_pid,
                    pane_identity=cpu(self.app_pid), server_identity=cpu(server_pid)))
                # Synchronous new-session + display-message complete before attach
                # or any measurements. The daemon remains an independent child.
                argv = self.tmux_base + ['attach-session', '-t', 'latency']
                self.record_tmux(dict(argv=argv, kind='pty-attach', monotonic_ns=time.monotonic_ns()))
            self.process = subprocess.Popen(
                argv,
                stdin=slave, stdout=slave, stderr=slave, start_new_session=True,
                env=self.env)
            if self.tmux_base is None:
                self.app_pid = self.process.pid
            self.app_identity = cpu(self.app_pid)
            require(self.app_identity is not None, 'Newly launched application PID unavailable')
            save(session.evidence / 'pty-processes.json', dict(
                transport='tmux' if self.tmux_base else 'direct', app_pid=self.app_pid,
                app_identity=self.app_identity, pty_child_pid=self.process.pid,
                pty_child_identity=cpu(self.process.pid), argv=argv))
        except BaseException:
            self.close()
            raise
        finally:
            os.close(slave)

    def record_tmux(self, value):
        with (self.session.evidence / 'tmux-commands.jsonl').open('a') as out:
            out.write(json.dumps(value) + '\n')

    def tmux_command(self, extra, success=True):
        argv = self.tmux_base + extra
        self.record_tmux(dict(argv=argv, kind='command', monotonic_ns=time.monotonic_ns()))
        result = subprocess.run(argv, env=self.env, capture_output=True, timeout=10)
        self.record_tmux(dict(argv=argv, kind='result', monotonic_ns=time.monotonic_ns(),
                              returncode=result.returncode, stdout=result.stdout.decode(errors='replace'),
                              stderr=result.stderr.decode(errors='replace')))
        require(not success or result.returncode == 0, 'Private tmux command failed: ' + repr(argv))
        return result

    def cpu_snapshot(self):
        app = cpu(self.app_pid)
        if app and self.app_identity and app['start_ticks'] != self.app_identity['start_ticks']:
            app = None  # Never attribute a reused/historical pane PID to the app.
        return dict(client=app, daemon=cpu(self.session.process.pid),
                    tmux_client=cpu(self.process.pid) if self.tmux_base else None)

    def pump(self, seconds=.01):
        require(self.process.poll() is None, 'PTY client exited')
        if select.select([self.master], [], [], max(0, min(.01, seconds)))[0]:
            raw = os.read(self.master, 65536)
            stamp = time.monotonic_ns()
            require(raw, 'PTY EOF')
            self.raw.write(raw)
            self.events.write(json.dumps(dict(monotonic_ns=stamp, offset=self.offset, size=len(raw))) + '\n')
            self.offset += len(raw)
            self.screen.feed(raw)
        return self.screen.text()

    def key(self, data):
        before = time.monotonic_ns()
        require(os.write(self.master, data) == len(data), 'Short PTY key write')
        after = time.monotonic_ns()
        self.keys.write(json.dumps(dict(hex=data.hex(), before_ns=before, after_ns=after)) + '\n')
        self.keys.flush()
        return before, after

    def ready(self):
        flags = termios.tcgetattr(self.master)[3]
        require(not flags & (termios.ICANON | termios.ECHO), 'PTY input not raw/noecho')
        if self.app_tty:
            # Outer raw mode belongs to tmux; also verify the actual app's pane.
            fd = os.open(self.app_tty, os.O_RDONLY | os.O_NOCTTY)
            try:
                pane_flags = termios.tcgetattr(fd)[3]
                require(not pane_flags & (termios.ICANON | termios.ECHO), 'Application pane not raw/noecho')
            finally:
                os.close(fd)
        return flags

    def wait(self, predicate, label, timeout=15):
        deadline = min(self.session.deadline, time.monotonic() + timeout)
        while True:
            text = self.pump()
            if predicate(text):
                self.snapshot(label)
                return text
            require(time.monotonic() < deadline, label + ': screen timeout\n' + text)

    def idle(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.pump(end - time.monotonic())

    def snapshot(self, label):
        (self.session.evidence / (label + '.txt')).write_text(self.screen.text())
        return self.offset

    def palette(self, title=None):
        self.ready()
        for key in (b' ', b'c', b'c'):
            self.key(key)
            # Setup only: keep prefix keys from coalescing into one Text event.
            self.idle(.2)
        self.wait(lambda s: 'COMMAND PALETTE - Esc closes' in s, 'palette-open')
        if title:
            self.key(title.encode())
            self.wait(lambda s: title in s, 'palette-filtered')
            self.key(b'\r')

    def close(self):
        try:
            try:
                if self.tmux_base:
                    # Always address this evidence root's socket, never $TMUX or
                    # the default server. Also runs after partial startup failure.
                    self.tmux_command(['kill-server'], success=False)
            finally:
                if self.process and self.process.poll() is None:
                    os.killpg(self.process.pid, signal.SIGTERM)
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(self.process.pid, signal.SIGKILL)
                        self.process.wait()
        finally:
            self.snapshot('final-screen')
            os.close(self.master)
            for out in (self.raw, self.events, self.keys):
                out.close()


def overview(s):
    return ('Overview' in s.splitlines()[0] and 'INSPECT ' not in s
            and 'COMMAND PALETTE - Esc closes' not in s)


def table(s):
    return ('INSPECT timing' in s and re.search(r'^\d+ rows\b', s, re.M)
            and 'Row: ' not in s and 'COMMAND PALETTE - Esc closes' not in s)


def measure(t, label, predicate, neutral, result):
    t.idle(t.args.idle)
    flags = t.ready()
    require(not predicate(t.screen.text()), 'Measurement target already visible: ' + label)
    calls = t.session.evidence / 'provider-calls.jsonl'
    call_bytes = calls.read_bytes() if calls.exists() else b''
    sample = dict(label=label, neutral=neutral, raw_lflag=flags,
                  before_offset=t.snapshot(label + '-before'),
                  cpu_before=t.cpu_snapshot())
    start, sent = t.key(b'\x1b')
    sample.update(esc_before_ns=start, esc_after_ns=sent)
    deadline = min(t.session.deadline, start / 1e9 + t.args.timeout)
    neutral_at = start / 1e9 + t.args.neutral_delay
    observed = None
    while time.monotonic() < deadline:
        text = t.pump()
        if predicate(text):
            observed = time.monotonic_ns()
            break
        if neutral and 'neutral_before_ns' not in sample and time.monotonic() >= neutral_at:
            before, after = t.key(b'\x00')
            sample.update(neutral_before_ns=before, neutral_after_ns=after)
    sample.update(observed_ns=observed, timed_out=observed is None,
                  neutral_sent='neutral_before_ns' in sample,
                  elapsed_ms=((observed or time.monotonic_ns()) - start) / 1e6,
                  after_offset=t.snapshot(label + '-after'),
                  daemon_alive=t.session.process.poll() is None,
                  cpu_after=t.cpu_snapshot())
    sample['provider_calls_unchanged'] = (calls.read_bytes() if calls.exists() else b'') == call_bytes
    result['measurements'].append(sample)
    save(t.session.evidence / 'result.json', result)
    require(sample['provider_calls_unchanged'] and sample['daemon_alive'], 'Provider call or daemon exit during ESC')
    if observed is None:
        # Explicit recovery occurs only after the censored sample was persisted.
        # NUL can release a buffered standalone ESC; never send command letters.
        t.key(b'\x00')
        t.wait(predicate, label + '-recovered', timeout=5)


def exercise(args, result):
    session = terminal = None
    watched = [args.source_state, args.source_evidence / 'project']
    before = investigation.dashboard.inventory(watched)
    save(args.evidence / 'source-before.json', before)
    try:
        root, run, indexes = prepare(args)
        session = investigation.Session(args, args.evidence, root)
        session.deadline = args.deadline
        session.env.update(HOME=str(args.evidence / 'home'), XDG_CONFIG_HOME=str(args.evidence / 'config'),
                           XDG_CACHE_HOME=str(args.evidence / 'cache'), TMPDIR=str(args.evidence / 'tmp'),
                           PYTHONDONTWRITEBYTECODE='1',
                            PATH=str(args.evidence / 'bin') + os.pathsep + os.environ.get('PATH', ''))
        # Project opening requires Dune's read-only version/description probes.
        # Reuse the allowlisting guard; build/test/exec remain rejected.
        metrics.guard_generic_builds(session)
        session.start()
        summary = session.rpc('asic', '(Load_summary %s)' % fs0.sexp(run), wait=True)
        require(any(field(s, 'freshness') == 'Cached_unverified' for s in field(summary, 'summaries')),
                'Summary was not restored from cache')
        for domain, stage in STAGES.items():
            snap = session.rpc('asic', '(Inspect (run %s) (domain %s) (stage %s) (refresh false))' %
                               (fs0.sexp(run), domain, stage), wait=True)
            restored = next(i for i in field(snap, 'inspections') if field(i, 'domain') == domain)
            expected = metrics.put(indexes[domain], 'cached_unverified', 'true')
            require(restored == expected, domain + ': restored index differs from real retained cache')
        calls = args.evidence / 'provider-calls.jsonl'
        require(not calls.exists(), 'Cached startup unexpectedly invoked provider')
        ws = session.rpc('workspace')
        workspace = next(w for w in field(ws, 'workspaces') if field(w, 'name') == 'Overview')
        context = next(c for c in field(ws, 'contexts') if field(c, 'id') == field(workspace, 'context'))
        ws = session.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' %
                            (field(workspace, 'id'), field(context, 'id'), field(context, 'selection_revision'), fs0.sexp(run)))
        ws = session.mutate(ws, '(Create_tile (workspace %s) (kind timing) (geometry ((x 0) (y 0) (width 80) (height 30))))' % field(workspace, 'id'))
        tile = field(field(ws, 'tiles')[-1], 'id')
        session.mutate(ws, '(Set_zoom (workspace %s) (tile (%s)))' % (field(workspace, 'id'), tile))
        terminal = Terminal(session)
        terminal.wait(lambda s: overview(s) and 'Space c c commands' in s, 'startup')
        terminal.ready()
        title = 'Inspect timing paths asic/%s · signoff' % field(run, 'id')

        def open_table():
            terminal.palette(title)
            terminal.wait(lambda s: table(s) and 'CACHED UNVERIFIED' in s, 'cached-table')

        for iteration in range(args.iterations):
            for neutral in ((False,) if args.single_escape_only else (False, True)):
                tag = '%02d-%s' % (iteration, 'esc-nul' if neutral else 'esc')
                terminal.palette()
                measure(terminal, tag + '-palette-to-overview', overview, neutral, result)
                open_table()
                measure(terminal, tag + '-table-to-overview', overview, neutral, result)
                open_table()
                # Filter one real retained row: no synthetic rows/provider index.
                row = next(r for r in field(indexes['timing'], 'rows')
                           if field(r, 'category') == 'timing_path')
                row_id = field(row, 'id')
                terminal.key(b'/')
                terminal.wait(lambda s: 'EDIT filter=' in s, 'filter-edit')
                terminal.key(row_id.encode())
                terminal.wait(lambda s: bool(re.search(r'^1 rows\b', s, re.M)), 'one-real-row')
                terminal.key(b'\r')
                terminal.wait(lambda s: table(s) and 'EDIT filter=' not in s, 'filter-done')
                enabled = args.evidence / 'detail-setup-enabled'
                if args.detail_mode == 'real':
                    enabled.touch()
                try:
                    terminal.key(b'd' if args.detail_mode == 'source' else b'\r')
                    terminal.wait(lambda s: 'Row: ' + row_id in s, 'detail-open')
                    if args.detail_mode != 'source':
                        detail_deadline = min(session.deadline, time.monotonic() + args.outer_timeout)
                        while True:
                            snap = session.rpc('asic', wait=True)
                            matches = [d for d in field(snap, 'inspection_details')
                                       if field(d, 'row_id') == row_id]
                            if matches:
                                detail = matches[0]
                                break
                            terminal.pump()
                            require(time.monotonic() < detail_deadline, 'Exact detail did not complete')
                        require(field(detail, 'source_digest') == field(indexes['timing'], 'source_digest'),
                                'Detail source digest mismatch')
                        require((field(detail, 'error') == []) == (args.detail_mode == 'real'),
                                'Detail success/error does not match declared mode')
                        terminal.wait(lambda s: 'Waiting for exact row/digest' not in s and
                                      ('ERROR:' in s if args.detail_mode == 'denied' else 'Row: ' in s),
                                      'detail-complete')
                finally:
                    enabled.unlink(missing_ok=True)
                measure(terminal, tag + '-' + args.detail_mode + '-detail-to-table', table, neutral, result)
                measure(terminal, tag + '-filtered-table-to-overview', overview, neutral, result)
        metrics.no_generic_jobs(session, 'latency complete')
        result['status'] = 'completed-with-timeouts' if any(m['timed_out'] for m in result['measurements']) else 'passed'
        if args.max_latency_ms is not None:
            violations = [m['label'] for m in result['measurements']
                          if m['timed_out'] or m['elapsed_ms'] > args.max_latency_ms]
            result['latency_budget_ms'] = args.max_latency_ms
            result['latency_budget_violations'] = violations
            require(not violations, 'ESC latency budget exceeded: ' + repr(violations))
    finally:
        try:
            if terminal:
                terminal.close()
        finally:
            if session and session.process:
                session.stop()
            after = investigation.dashboard.inventory(watched)
            save(args.evidence / 'source-after.json', after)
            result['source_unchanged'] = before == after
            result['provider_calls'] = [json.loads(line) for line in calls.read_text().splitlines()] if (calls := args.evidence / 'provider-calls.jsonl').exists() else []
            require(before == after, 'Original source state/project changed')


def main():
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test-screen', action='store_true',
                        help='Run only pure-Python ANSI screen checks; no runtime children or evidence')
    parser.add_argument('--source-evidence', type=Path, default=Path('/tmp/opencode/workbench-fs1-investigation-hd0uuqio'))
    parser.add_argument('--source-state', type=Path, help='Defaults to SOURCE_EVIDENCE/state')
    parser.add_argument('--provider', type=Path, help='Current real provider; required only for --detail-mode real')
    parser.add_argument('--detail-mode', choices=('denied', 'source', 'real'), default='source')
    parser.add_argument('--client', type=Path, default=repo / '_build/default/terminal/main.exe')
    parser.add_argument('--daemon', type=Path, default=repo / '_build/default/daemon/main.exe')
    parser.add_argument('--tmux-escape-time', type=int, metavar='MS',
                        help='Use a private tmux server with escape-time 0..2000 ms')
    parser.add_argument('--iterations', type=int, default=3)
    parser.add_argument('--max-latency-ms', type=float,
                        help='Optional regression ceiling; omit for diagnostic runs with known tmux delay')
    parser.add_argument('--single-escape-only', action='store_true',
                        help='Measure standalone Escape only; ESC+NUL can be an Alt sequence in tmux')
    parser.add_argument('--width', type=int, default=200)
    parser.add_argument('--height', type=int, default=60)
    parser.add_argument('--idle', type=float, default=1.0)
    parser.add_argument('--timeout', type=float, default=3.0)
    parser.add_argument('--neutral-delay', type=float, default=.05)
    parser.add_argument('--outer-timeout', type=int, default=35)
    parser.add_argument('--budget', type=int, default=300)
    args = parser.parse_args()
    if args.self_test_screen:
        screen_self_check()
        return
    args.tmux = None
    if args.tmux_escape_time is not None:
        require(0 <= args.tmux_escape_time <= 2000, 'tmux escape-time must be 0..2000 ms')
        executable = shutil.which('tmux')
        require(executable is not None, 'Existing tmux executable required')
        args.tmux = Path(executable).resolve(strict=True)
    require(1 <= args.iterations <= 20 and 120 <= args.width <= 400 and 40 <= args.height <= 120,
             'iterations 1..20, width 120..400, height 40..120')
    require(args.max_latency_ms is None or 0 < args.max_latency_ms <= 30000,
            'Latency ceiling must be positive and at most 30000 ms')
    require(1 <= args.idle <= 10 and .01 <= args.neutral_delay < args.timeout <= 30 and
            60 <= args.budget <= 1800 and 1 <= args.outer_timeout <= 90, 'Invalid timing budgets')
    args.source_evidence = args.source_evidence.resolve(strict=True)
    args.source_state = (args.source_state or args.source_evidence / 'state').resolve(strict=True)
    require(json.loads((args.source_evidence / 'result.json').read_text())['status'] == 'passed',
            'Source evidence must be accepted/passed')
    for name in ('client', 'daemon') + (('provider',) if args.provider else ()):
        path = getattr(args, name).resolve(strict=True)
        require(path.is_file() and os.access(path, os.X_OK), 'Existing executable required: ' + str(path))
        setattr(args, name, path)
    require(args.detail_mode != 'real' or args.provider is not None, '--detail-mode real requires --provider')
    os.umask(0o077)
    args.evidence = Path(tempfile.mkdtemp(prefix='workbench-inspector-latency-', dir='/tmp/opencode'))
    args.deadline = time.monotonic() + args.budget
    result = dict(status='failed', measurements=[], detail_mode=args.detail_mode,
                  interpretation=__doc__, options={k: str(v) for k, v in vars(args).items()},
                  binaries={n: dict(path=str(getattr(args, n)), sha256=investigation.sha256(getattr(args, n)))
                            for n in ('client', 'daemon') + (('provider',) if args.provider else ())
                            + (('tmux',) if args.tmux else ())},
                  clock=dict(name='monotonic_ns', resolution=time.get_clock_info('monotonic').resolution))
    save(args.evidence / 'invocation.json', dict(argv=sys.argv, **result))
    print('Evidence: ' + str(args.evidence), flush=True)

    def interrupted(signum, _frame):
        raise KeyboardInterrupt('Interrupted/budget exhausted: %d' % signum)

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGALRM):
        signal.signal(sig, interrupted)
    signal.alarm(args.budget)
    try:
        exercise(args, result)
    except BaseException:
        result.update(status='failed', error=traceback.format_exc())
        raise
    finally:
        signal.alarm(0)
        groups = {}
        for sample in result['measurements']:
            groups.setdefault(sample['label'].split('-', 1)[1], []).append(sample)
        result['summary'] = {}
        for label, samples in groups.items():
            values = [s['elapsed_ms'] for s in samples if not s['timed_out']]
            result['summary'][label] = dict(
                observations=len(samples), timeouts=sum(s['timed_out'] for s in samples),
                min_ms=min(values) if values else None,
                median_ms=statistics.median(values) if values else None,
                max_ms=max(values) if values else None)
        save(args.evidence / 'result.json', result)
    print(result['status'] + ': ' + str(args.evidence), flush=True)


if __name__ == '__main__':
    main()
