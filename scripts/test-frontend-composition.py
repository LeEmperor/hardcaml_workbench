#!/usr/bin/env python3
"""Bounded real HTTP/PTY frontend acceptance. Existing binaries only; no builds/EDA.

Retains current-screen text, ANSI transcripts, cell attributes, SVG screenshots,
HTTP/key logs and result.json in a private /tmp/opencode directory. SVGs depict
actual terminal cells, not simulated UI fixtures. --palette-only diagnoses the
palette before presentation integration is ready; full acceptance is the default.
"""
import argparse
import fcntl
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import pty
import re
import secrets
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import traceback
import unicodedata

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('composition_demo', HERE / 'synthetic-flow-demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
from http_client import field, parse, sexp


def require(ok, message):
    if not ok:
        raise AssertionError(message)


STATUS_PADDING = re.compile(r'(?<=\S:) {2,}(?=\S)')


def status_text(text):
    """Checklist keywords share a padded column (WB-001); oracles match `Label: status`."""
    return STATUS_PADDING.sub(' ', text)


def wait(predicate, label, timeout=20):
    deadline = time.monotonic() + timeout
    while True:
        value = predicate()
        if value:
            return value
        require(time.monotonic() < deadline, 'Timeout: ' + label)
        time.sleep(.05)


class Screen:
    """Small ANSI cell/SGR oracle, including Notty cursor moves and erasures."""
    def __init__(self, data, width, height):
        self.width, self.height = width, height
        self.cells = [[(' ', ('default', 'default', False, False)) for _ in range(width)] for _ in range(height)]
        x = y = 0
        fg = bg = 'default'
        underline = bold = False
        for token in re.findall(r'\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\)|.)|[^\x1b]+', data.decode('utf-8', 'replace')):
            if token.startswith('\x1b['):
                code, values = token[-1], token[2:-1]
                if values.startswith('?'):
                    continue
                args = [int(v or 0) for v in values.split(';')]
                n = args[0] or 1
                if code in 'Hf':
                    y, x = n - 1, (args[1] or 1) - 1 if len(args) > 1 else 0
                elif code == 'A': y = max(0, y - n)
                elif code == 'B': y = min(height - 1, y + n)
                elif code in 'EF':
                    y, x = min(height - 1, y + n) if code == 'E' else max(0, y - n), 0
                elif code == 'C': x = min(width - 1, x + n)
                elif code == 'D': x = max(0, x - n)
                elif code == 'G': x = n - 1
                elif code == 'm':
                    i = 0
                    while i < len(args):
                        a = args[i]
                        if a == 0: fg = bg = 'default'; underline = bold = False
                        elif a == 1: bold = True
                        elif a == 22: bold = False
                        elif a == 4: underline = True
                        elif a == 24: underline = False
                        elif a == 39: fg = 'default'
                        elif a == 49: bg = 'default'
                        elif 30 <= a <= 37 or 90 <= a <= 97: fg = 'ansi:' + str(a)
                        elif 40 <= a <= 47 or 100 <= a <= 107: bg = 'ansi:' + str(a - 10)
                        elif a in (38, 48) and i + 2 < len(args):
                            count = 1 if args[i + 1] == 5 else 3
                            color = ('index:' if count == 1 else 'rgb:') + ','.join(map(str, args[i + 2:i + 2 + count]))
                            if a == 38: fg = color
                            else: bg = color
                            i += count + 1
                        i += 1
                elif code in 'JKX':
                    targets = []
                    if code == 'J':
                        targets = [(yy, xx) for yy in range(height) for xx in range(width)
                                   if args[0] in (2, 3) or (args[0] == 0 and (yy, xx) >= (y, x)) or (args[0] == 1 and (yy, xx) <= (y, x))]
                    elif 0 <= y < height:
                        start, end = (x, min(width, x + n)) if code == 'X' else ((0, width) if args[0] == 2 else ((0, x + 1) if args[0] == 1 else (x, width)))
                        targets = [(y, xx) for xx in range(max(0, start), min(width, end))]
                    for yy, xx in targets: self.cells[yy][xx] = (' ', (fg, bg, underline, bold))
            elif not token.startswith('\x1b'):
                for char in token:
                    if char == '\r': x = 0
                    elif char == '\n': y = min(height - 1, y + 1)
                    elif char == '\b': x = max(0, x - 1)
                    elif unicodedata.combining(char):
                        if 0 < x <= width and 0 <= y < height:
                            old, attr = self.cells[y][x - 1]
                            self.cells[y][x - 1] = (old + char, attr)
                    elif char >= ' ':
                        if 0 <= y < height and 0 <= x < width:
                            self.cells[y][x] = (char, (fg, bg, underline, bold))
                        x += 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1

    def lines(self):
        return [''.join(c for c, _ in row) for row in self.cells]

    def text(self):
        return '\n'.join(line.rstrip() for line in self.lines())

    def attrs_for(self, text):
        found = []
        for y, line in enumerate(self.lines()):
            offset = 0
            while (x := line.find(text, offset)) >= 0:
                found.append([a for _, a in self.cells[y][x:x + len(text)]])
                offset = x + len(text)
        return found

    def save(self, stem):
        stem.with_suffix('.txt').write_text(self.text())
        stem.with_suffix('.cells.json').write_text(json.dumps(self.cells))
        colors = ['#20242b', '#e06c75', '#98c379', '#e5c07b', '#61afef', '#c678dd', '#56b6c2', '#e6e6e6']
        def color(value, background=False):
            if value == 'default': return '#15191f' if background else '#dedede'
            if value.startswith('rgb:'): return 'rgb(' + value[4:] + ')'
            if value.startswith('ansi:'): return colors[(int(value[5:]) - 30) % 8]
            index = int(value[6:])
            if index < 16: return colors[index % 8]
            if index >= 232: return '#%02x%02x%02x' % ((8 + 10 * (index - 232),) * 3)
            index -= 16
            levels = [0, 95, 135, 175, 215, 255]
            return '#%02x%02x%02x' % (levels[index // 36], levels[index // 6 % 6], levels[index % 6])
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width * 9}" height="{self.height * 18}" viewBox="0 0 {self.width * 9} {self.height * 18}">', '<rect width="100%" height="100%" fill="#15191f"/>']
        for y, row in enumerate(self.cells):
            for x, (char, (fg, bg, ul, bold)) in enumerate(row):
                if bg != 'default': out.append(f'<rect x="{x*9}" y="{y*18}" width="9" height="18" fill="{color(bg, True)}"/>')
                if char.strip(): out.append(f'<text x="{x*9}" y="{y*18+14}" font-family="monospace" font-size="15" fill="{color(fg)}" font-weight="{"bold" if bold else "normal"}" text-decoration="{"underline" if ul else "none"}">{html.escape(char)}</text>')
        stem.with_suffix('.svg').write_text('\n'.join(out + ['</svg>']))


class Terminal:
    def __init__(self, base, args, url, width=120, height=40, project_root=None):
        self.base, self.width, self.height = base, width, height
        self.data, self.keys = bytearray(), []
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
        self.process = subprocess.Popen(demo.switch_command([args.client, '--connect', url,
            '--project-root', project_root or base / 'project', '--environment', 'opam:' + demo.switch_name()] +
            (['--timing-preload', args.timing_preload] if getattr(args, 'timing_preload', None) else [])),
            stdin=slave, stdout=slave, stderr=slave, start_new_session=True,
            env=dict(os.environ, TERM='xterm-256color', HOME=str(base / 'home'),
                     OPAMROOT=os.environ.get('OPAMROOT', str(Path.home() / '.opam')),
                     XDG_CONFIG_HOME=str(base / 'config'), XDG_STATE_HOME=str(base / 'client-state')))
        os.close(slave)

    def drain(self, seconds=.2):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if select.select([self.master], [], [], min(.05, max(0, end-time.monotonic())))[0]:
                try: chunk = os.read(self.master, 65536)
                except OSError: break
                if not chunk: break
                self.data.extend(chunk)
        screen = Screen(bytes(self.data), self.width, self.height)
        if self.process.poll() is not None:
            self.save('client-exited', screen)
            raise AssertionError(f'Client exited with {self.process.returncode}: {screen.text()}')
        return screen

    def key(self, data):
        self.keys.append(dict(hex=data.hex(), time=time.monotonic()))
        os.write(self.master, data)
        return self.drain()

    def resize(self, width, height):
        self.drain()
        if (width, height) == (self.width, self.height):
            return self.drain(.5)
        self.width, self.height = width, height
        # A full redraw follows SIGWINCH. Start a fresh cell transcript so old
        # coordinates cannot masquerade as content in the resized viewport.
        self.data.clear()
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
        os.kill(self.process.pid, signal.SIGWINCH)
        return self.drain(.5)

    def capture(self, label, expected=(), absent=()):
        deadline = time.monotonic() + 12
        while True:
            screen = self.drain()
            visible = status_text(screen.text()).casefold()
            if all(s.casefold() in visible for s in expected) and all(s.casefold() not in visible for s in absent):
                break
            if time.monotonic() > deadline:
                self.save(label + '-failure', screen)
                raise AssertionError(f'{label}: expected {expected}, absent {absent}\n{screen.text()}')
        self.save(label, screen)
        return screen

    def save(self, label, screen):
        screen.save(self.base / label)
        (self.base / (label + '.ansi')).write_bytes(self.data)
        (self.base / 'keys.json').write_text(json.dumps(self.keys, indent=2))

    def open_palette(self, query=''):
        for key in (b' ', b'c', b'c'): self.key(key)
        self.capture('palette-open', ['COMMAND PALETTE'])
        if query: self.key(query.encode())

    def command(self, title):
        self.open_palette(title)
        self.capture('command-' + str(len(self.keys)), [title], ['No matching commands'])
        # Query edits preserve selected command identity. Explicitly choose the
        # highest-ranked title match instead of accidentally executing a previously
        # selected fuzzy alias (especially runs sharing "reference" in long IDs).
        self.key(b'\x1b[A' * 100)
        self.key(b'\r')

    def focus_view(self, view, limit=32):
        """Observe the focused-view breadcrumb; never infer focus from visible panes."""
        for _ in range(limit):
            screen = self.drain()
            footer = screen.lines()[-1].casefold()
            if re.search(r'(?<![\w-])' + re.escape(view.casefold()) + r'(?=\s*(?:[›>]|$))', footer):
                self.save('focused-' + view.replace(' ', '-'), screen)
                return screen
            self.key(b'\t')
        self.save('focus-' + view.replace(' ', '-') + '-failure', self.drain())
        raise AssertionError('Could not focus view through real Tab navigation: ' + view)

    def wait_active_workspace(self, registry, workspace, label):
        """Check exact saved navigation identity independently of clipped tab labels."""
        expected_members = sorted((field(tile, 'id'), field(tile, 'kind'))
            for tile in field(registry, 'tiles') if field(tile, 'workspace') == workspace)
        directory = self.base / 'client-state/hardcaml-workbench/terminal'
        deadline = time.monotonic() + 12
        while True:
            for path in directory.glob('navigation-*.sexp'):
                try:
                    navigation = parse(path.read_text())
                except (OSError, ValueError, IndexError):
                    continue
                if (field(navigation, 'session') != field(registry, 'session_id') or
                        field(navigation, 'active') != [workspace]):
                    continue
                saved = next((w for w in field(navigation, 'workspaces')
                              if field(w, 'id') == workspace), None)
                if saved is None:
                    continue
                members = sorted((field(member, 'tile'), field(member, 'kind'))
                                 for member in field(saved, 'members'))
                if members == expected_members and all(tile in dict(members) for tile in field(saved, 'focus')):
                    (self.base / (label + '-navigation.json')).write_text(json.dumps(
                        dict(source=str(path), expected_workspace=workspace, navigation=navigation), indent=2))
                    return navigation
            if time.monotonic() >= deadline:
                self.save(label + '-navigation-failure', self.drain())
                raise AssertionError(label + ': saved active workspace/session/membership did not match ' + workspace)
            self.drain(.1)

    def close(self):
        try:
            self.save('last-screen', Screen(bytes(self.data), self.width, self.height))
        finally:
            if self.process.poll() is None:
                self.process.terminate()
                try: self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill(); self.process.wait(timeout=5)
            os.close(self.master)


def palette_acceptance(t, check, http):
    before = t.capture('palette-source', ['Overview'])
    registry = http.rpc(domain='workspace')
    t.open_palette('ap col')
    overlay = t.capture('fuzzy-overlay', ['COMMAND PALETTE', 'Color Vivid', 'Color Selective', 'Color Restrained'])
    # 120x40 bounds are x=16,y=10,w=88,h=20. Require real nonblank
    # background outside the panel and exact cell equality there.
    # The final global status row legitimately dismisses transient notices on input;
    # all workspace cells outside the palette must remain byte/attribute-identical.
    outside = [(y, x) for y in range(t.height - 1) for x in range(t.width)
               if not (16 <= x < 104 and 10 <= y < 30)]
    check(any(before.cells[y][x][0].strip() for y, x in outside), 'Underlying workspace visibly survives outside bounded overlay')
    check(all(before.cells[y][x] == overlay.cells[y][x] for y, x in outside), 'Overlay preserves source cells and attributes outside bounds')
    result_rows = [(y, line) for y, line in enumerate(overlay.lines()) if 'Appearance: Color ' in line]
    check(all(any(a[2] for _, a in overlay.cells[y]) for y, _ in result_rows), 'Actual fuzzy result characters have ANSI underline attributes')
    highlighted = []
    for y, line in result_rows:
        x = line.index('Appearance: Color')
        highlighted.append(''.join(char for char, attr in overlay.cells[y][x:x + len('Appearance: Color')] if attr[2]).casefold())
    check(highlighted == ['apcol'] * 3, 'ANSI underline marks exact noncontiguous ap/col title matches, not entire result rows')
    def selected(screen):
        title_y = next(y for y, line in enumerate(screen.lines()) if 'COMMAND PALETTE' in line)
        rows = [line for line in screen.lines()[title_y + 2:] if re.search(r'>\s+Appearance:', line)]
        require(len(rows) == 1, 'Exactly one selected palette command: ' + screen.text())
        return rows[0]
    # Query edits intentionally preserve command identity. Explicitly navigate
    # to the first ranked result before testing the similar-color sequence.
    overlay = t.key(b'\x1b[A' * 30)
    first = selected(overlay)
    check('Color Vivid' in first, 'Arrow navigation reaches first ranked fuzzy Color result')
    second = selected(t.key(b'\t'))
    t.save('palette-tab', t.drain())
    check(second != first and 'Selective' in second, 'Tab selects similar Color Selective command')
    check(selected(t.key(b'\x1b[Z')) == first, 'Shift-Tab restores first similar command')
    t.key(b'\t'); t.key(b'\r')
    t.capture('palette-executed', absent=['COMMAND PALETTE'])
    t.open_palette('Appearance: Color Selective')
    active = t.capture('palette-executed-active', ['Color Selective [active]'])
    check('[active]' in selected(active), 'Enter executed selected Color Selective')
    t.key(b'\x1b')
    stable = t.capture('before-escape')
    t.open_palette('ap col')
    t.key(b'\t'); t.key(b'\x1b[Z'); t.key(b'\x1b')
    restored = t.capture('escaped-workspace', absent=['COMMAND PALETTE'])
    check(stable.cells[:-1] == restored.cells[:-1], 'Esc restores exact source workspace cells and focus after Tab/Shift-Tab (status notices may dismiss)')
    check(http.rpc(domain='workspace') == registry, 'Palette navigation and appearance do not mutate semantic workspace state')


def fixture_workspace(http, name, kinds):
    snapshot = http.rpc(domain='workspace')
    snapshot = http.mutate(snapshot, '(Create_workspace (window %s) (name %s) (context %s))' %
        (sexp(field(field(snapshot, 'windows')[0], 'id')), sexp(name), sexp(field(snapshot, 'main_context'))))
    workspace = field(field(snapshot, 'workspaces')[-1], 'id')
    tiles = []
    for kind in kinds:
        snapshot = http.mutate(snapshot, '(Create_tile (workspace %s) (kind %s) (geometry ((x 0) (y 0) (width 59) (height 15))))' % (sexp(workspace), sexp(kind)))
        tiles.append(field(snapshot, 'tiles')[-1])
    return workspace, tiles


def full_acceptance(t, check, http, runs, presets):
    workspace, tiles = fixture_workspace(http, 'Presentation acceptance', ['synthesis', 'synthesis', 'live-status', 'workspace-tabs'])
    def mutate(op): return http.mutate(http.rpc(domain='workspace'), op)
    second = field(tiles[1], 'id')
    mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' % (sexp(second), sexp(runs[1])))
    t.capture('registry-presentation-ready', ['Presentation acceptance'])
    t.command('Switch to Presentation acceptance')
    screen = t.capture('quiet-follow-pin-project', ['PIN', 'Cell count:', 'Session'], absent=['[FOLLOW', '[PROJECT'])
    check(field(runs[1], 'id') in screen.text(), 'Pinned header exposes exact run ID by default')
    baseline = http.rpc(domain='workspace')
    # Commands are intentionally tested by their actual public palette titles.
    # A exposes local controls during integration; a missing command is a failure,
    # not a skipped or inferred presentation success.
    t.command('Toggle focused tile header')
    hidden = t.capture('header-hidden', ['PIN', 'Cell count:'])
    check(http.rpc(domain='workspace') == baseline, 'Per-tile header control leaves bindings/registry unchanged')
    t.command('Toggle focused tile header')
    t.capture('header-restored', ['PIN', 'Cell count:'])
    t.command('Binding badge: Always')
    t.capture('badge-always-local', ['FOLLOW', 'PIN'])
    t.command('Binding badge: Hidden')
    t.capture('badge-hidden-local', ['PIN'], absent=['FOLLOW'])
    t.command('Reset presentation overrides (inherit)')
    t.capture('badge-inherited', ['PIN'], absent=['FOLLOW'])
    check(http.rpc(domain='workspace') == baseline, 'Badge modes/reset affect one tile without changing registry or another pin')
    t.command('Zoom focused tile')
    t.key(b'm')
    metrics = t.capture('validated-metrics', ['Freshness: Validated', 'Acceptance (reported):'])
    validation = metrics.attrs_for('Validated')
    check(bool(validation), 'Typed Validated freshness is visible in actual synthesis Metrics')
    freshness_labels = metrics.attrs_for('Freshness:')
    check(bool(freshness_labels) and freshness_labels[0][0][0] != validation[0][0][0],
          'Typed Freshness label remains neutral independently of the validated value color')
    semantic_before = http.rpc(domain='workspace')
    t.command('Toggle focused tile title')
    t.capture('title-hidden', ['Synthesis metrics', '940'], absent=['SYNTHESIS/METRICS'])
    t.command('Reset presentation overrides (inherit)')
    t.command('Toggle focused tile run reference')
    t.capture('run-reference-visible', ['Run: asic/', '940'])
    t.command('Toggle focused tile run reference')
    t.capture('run-reference-hidden', ['940'], absent=['Run: asic/'])
    framed = t.drain()
    t.command('Toggle focused tile frame')
    frameless = t.capture('frame-hidden', ['940'])
    corners = lambda screen: sum(line.count('╭') + line.count('┌') + line.count('+') for line in screen.lines())
    check(corners(framed) > 0 and corners(frameless) == 0, 'Focused tile frame control removes the actual terminal border')
    t.command('Toggle focused tile frame')
    def column(screen, text):
        return next(line.index(text) for line in screen.lines() if text in line)
    metric_evidence = ['Mapped cell area: 940', 'Freshness: Validated', 'Acceptance (reported):']
    # Density supplies inherited padding; establish zero explicitly through the
    # public Compact command before asserting the direction of a local toggle.
    t.command('Appearance: Density Compact')
    unpadded = t.capture('density-compact', metric_evidence)
    t.command('Appearance: Density Comfortable')
    comfortable = t.capture('density-comfortable', metric_evidence)
    check(column(comfortable, 'Mapped cell area:') == column(unpadded, 'Mapped cell area:') + 1, 'Actual Comfortable density moves inherited evidence one cell right from Compact')
    t.command('Appearance: Density Compact')
    t.capture('padding-before', metric_evidence)
    t.command('Toggle focused tile padding')
    padded = t.capture('padding-after', metric_evidence)
    check(column(padded, 'Mapped cell area:') == column(unpadded, 'Mapped cell area:') + 1, 'Focused padding control moves real evidence exactly one display cell')
    t.command('Appearance: Density Comfortable')
    explicit_comfortable = t.capture('explicit-padding-comfortable', metric_evidence)
    check(column(explicit_comfortable, 'Mapped cell area:') == column(padded, 'Mapped cell area:'), 'Explicit tile padding survives switching to Comfortable density')
    t.command('Appearance: Density Compact')
    explicit_compact = t.capture('explicit-padding-compact', metric_evidence)
    check(column(explicit_compact, 'Mapped cell area:') == column(padded, 'Mapped cell area:'), 'Explicit tile padding survives switching back to Compact density')
    t.command('Reset presentation overrides (inherit)')
    inherited = t.capture('density-padding-inherited', metric_evidence)
    check(column(inherited, 'Mapped cell area:') == column(unpadded, 'Mapped cell area:'), 'Reset tile padding inherits Compact zero padding again')
    t.command('Appearance: Density Comfortable')
    t.capture('density-comfortable-restored', metric_evidence)
    check(http.rpc(domain='workspace') == semantic_before, 'Title/run-reference/frame/padding/density controls are presentation-only')
    t.command('Toggle focused tile freshness')
    t.capture('freshness-hidden', ['Acceptance (reported):'], absent=['Freshness: Validated'])
    t.command('Toggle focused tile hints')
    t.capture('hints-hidden', ['Synthesis metrics'], absent=['j/k scroll | e Evidence'])
    t.command('Reset presentation overrides (inherit)')
    t.capture('freshness-hints-inherited', ['Freshness: Validated', 'j/k scroll | e Evidence'])
    t.command('Unzoom workspace')
    t.key(b'\t')
    t.command('Zoom focused tile')
    t.key(b'm')
    failed = t.capture('validated-pending-metrics', ['Validated', 'Acceptance (reported): not_evaluated', '1080'])
    valid_attrs, pending_attrs = failed.attrs_for('Validated'), failed.attrs_for('not_evaluated')
    check(bool(valid_attrs and pending_attrs) and valid_attrs[0][0][0] != pending_attrs[0][0][0], 'Validated freshness and pending acceptance have distinct ANSI foreground colors')
    t.command('Toggle focused tile header')
    headerless = t.capture('headerless-pin-identity', ['PIN asic/' + field(runs[1], 'id'), '1080'])
    check(all('SYNTHESIS' not in line for line in headerless.lines() if 'PIN asic/' in line), 'Headerless pinned tile retains exact identity in its independent badge row')
    t.command('Toggle focused tile header')
    t.command('Unzoom workspace'); t.key(b'\x1b[Z'); t.command('Zoom focused tile')
    t.capture('first-instance-independent', ['Synthesis metrics', 'Validated', '940'], absent=['1080'])
    check(True, 'Two synthesis instances retain independent Metrics mode and exact following/pinned evidence')
    t.command('Unzoom workspace')
    status_workspace, status_tiles = fixture_workspace(http, 'Status acceptance', ['checks'])
    mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' % (sexp(field(status_tiles[0], 'id')), sexp(runs[1])))
    t.capture('registry-status-ready', ['Status acceptance'])
    t.command('Switch to Status acceptance')
    t.command('Zoom focused tile')
    failed = t.capture('validated-failed-terminal', ['Validated', 'Timing goal (reported): fail'])
    valid_attrs, fail_attrs = failed.attrs_for('Validated'), failed.attrs_for('fail')
    # The pin ID contains "failed" too; compare the explicit verdict row.
    fail_attrs = [attrs for y, line in enumerate(failed.lines()) if 'Timing goal (reported): fail' in line
                  for attrs in [failed.cells[y][line.index('fail')][1]]]
    check(bool(valid_attrs and fail_attrs) and valid_attrs[0][0][0] != fail_attrs[0][0], 'Validated freshness and explicit failed timing verdict have distinct ANSI foreground colors')
    t.command('Inspect timing paths ' + field(runs[0], 'id'))
    source = t.capture('timing-workspace-source', ['Timing · Paths', 'Timing · Selected path', 'Timing · Provenance', 'signoff', '12 paths', 'No tool report or binary layout is claimed.', 'Evidence: idle'],
                       ['Waiting for explicitly requested index'])
    t.open_palette('ap col')
    t.capture('inspector-overlay', ['COMMAND PALETTE'])
    t.key(b'\t'); t.key(b'\x1b[Z'); t.key(b'\x1b')
    check(t.capture('timing-workspace-restored', ['Timing · Paths', 'signoff']).cells == source.cells, 'Palette Esc restores exact Timing workspace panes and selection')
    # Actual preset mutations with extras and a pin, then rename without identity drift.
    snapshot = http.rpc(domain='workspace')
    overview = next(w for w in field(snapshot, 'workspaces') if field(w, 'preset') == ['overview'])
    wid = field(overview, 'id')
    snapshot = mutate('(Create_tile (workspace %s) (kind logs) (geometry ((x 3) (y 4) (width 45) (height 13))))' % sexp(wid))
    extra = field(snapshot, 'tiles')[-1]
    synth = next(tile for tile in field(snapshot, 'tiles') if field(tile, 'workspace') == wid and field(tile, 'kind') == 'synthesis')
    snapshot = mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' % (sexp(field(synth, 'id')), sexp(runs[1])))
    snapshot = mutate('(Rename_workspace (workspace %s) (name "Renamed dashboard"))' % sexp(wid))
    specs = [[field(tile, 'kind'), field(tile, 'geometry')] for tile in field(presets['overview'], 'tiles')]
    # The terminal polls the registry; allow it to acquire the external rename
    # before opening a palette whose target/catalogue is intentionally captured.
    t.drain(1)
    t.command('Switch to Renamed dashboard')
    for operation, title in (
            ('Apply_preset', 'Apply preset: Overview (add missing tiles)'),
            ('Reset_arrangement', 'Reset arrangement: Overview (preserve extras and pins)')):
        revision = int(field(http.rpc(domain='workspace'), 'revision'))
        t.command(title)
        def applied():
            current = http.rpc(domain='workspace')
            return current if int(field(current, 'revision')) > revision else None
        snapshot = wait(applied, title + ' actual registry mutation')
        after_extra = next(tile for tile in field(snapshot, 'tiles') if field(tile, 'id') == field(extra, 'id'))
        after_synth = next(tile for tile in field(snapshot, 'tiles') if field(tile, 'id') == field(synth, 'id'))
        check(after_extra == extra and field(after_synth, 'binding') == ['Pin_run', runs[1]], operation + ' retains exact extra tile and pinned identity')
        current = next(w for w in field(snapshot, 'workspaces') if field(w, 'id') == wid)
        check(field(current, 'preset') == ['overview'] and field(current, 'name') == 'Renamed dashboard', operation + ' uses stable preset identity after rename')
        if operation == 'Reset_arrangement':
            for kind, geometry in specs:
                tile = next(tile for tile in field(snapshot, 'tiles') if field(tile, 'workspace') == wid and field(tile, 'kind') == kind)
                check(field(tile, 'requested_geometry') == geometry, 'Actual palette Reset restores exported geometry: ' + kind)
    t.capture('preset-renamed-reset', ['Reported cells (agg.)', 'PIN'])
    t.wait_active_workspace(snapshot, wid, 'preset-renamed-reset')
    check(True, 'Renamed Overview remains the exact active workspace despite clipped navigation labels')


def run(args, acceptance=full_acceptance, extra_runs=(3, 4, 5, 6), startup_check=None, focused=False,
        restart_acceptance=None):
    base = demo.prepare(args.evidence, manual=True, delay=.05)
    print('Evidence: ' + str(base), flush=True)
    # Six real registered synthetic observations make the four-row selector
    # limit observable. No Python layout or daemon state-file editing is used.
    manifest = demo.provider.load(base / 'manifest.json')
    for number in extra_runs:
        name = (f'synthetic-long-distinguishable-run-reference-{number}-suffix'
                if number in (3, 4) else f'synthetic-row{number}')
        attempt = demo.provider.allocate(base / 'results', demo.provider.selection('success'),
            name)
        while demo.provider.load(attempt / 'observation.json')['writer_active']:
            demo.provider.advance(attempt)
        manifest['runs'].append(dict(attempt=str(attempt), stream_id=attempt.name,
            finalization=str(attempt / 'finalizations' / ('synthetic-collection-' + attempt.name))))
    demo.provider.save(base / 'manifest.json', manifest)
    for name in ('home', 'config', 'client-state', 'discovery'): (base / name).mkdir()
    result = dict(status='failed', checks=[], evidence=str(base), palette_only=args.palette_only,
                  scope='focused' if focused else 'full',
                  harness=getattr(args, 'harness', 'frontend composition'),
                  related_evidence=getattr(args, 'related_evidence', []),
                  binaries={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.client, args.daemon, args.preset_export)})
    def check(ok, message):
        result['checks'].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)
    daemon = terminal = http = None
    log = (base / 'daemon.log').open('wb')
    try:
        daemon = subprocess.Popen(demo.switch_command([args.daemon, '--port', '0', '--discovery-dir', base / 'discovery', '--state-dir', base / 'state']), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        metadata = base / 'discovery/daemon.sexp'
        wait(lambda: metadata.exists() or daemon.poll() is not None, 'daemon metadata')
        require(daemon.poll() is None, 'Daemon failed; see daemon.log')
        url = field(parse(metadata.read_text()), 'endpoint')
        http, runs = demo.seed(base, url, args.preset_export)
        presets = demo.workspace_presets(args.preset_export)
        terminal = Terminal(base, args, url)
        startup = terminal.capture('startup-120x40', ['Overview', 'Reported cells (agg.)'])
        if startup_check is not None: startup_check(terminal, check, http, startup)
        if not args.palette_only and not focused:
            def selector_count(screen):
                lines = screen.lines()
                top = next(y for y, line in enumerate(lines) if 'runs ' in line.casefold() and '╭' in line)
                title_x = lines[top].casefold().index('runs ')
                left = lines[top].rfind('╭', 0, title_x)
                right = lines[top].index('╮', title_x)
                bottom = next(y for y in range(top + 1, len(lines)) if lines[y][left:left + 1] == '╰')
                return sum('asic/' in line[left + 1:right] for line in lines[top + 1:bottom])
            check(selector_count(startup) == 4, 'Overview sidebar run selector shows exactly four of six registered runs by default')
            check('WORKSPACES' not in startup.text() and '[PROJECT' not in startup.text(), 'Default navigation has quiet title/project chrome')
            registry = http.rpc(domain='workspace')
            terminal.focus_view('run selector')
            terminal.command('Run selector: More visible rows (+1)')
            expanded = terminal.capture('selector-five-rows', ['Runs 5/6'])
            check(selector_count(expanded) == 5, 'Focused selector row control exposes fifth run')
            terminal.command('Reset presentation overrides (inherit)')
            reset = terminal.capture('selector-four-inherited', ['Runs 4/6'])
            check(selector_count(reset) == 4 and http.rpc(domain='workspace') == registry, 'Selector reset inherits four rows without semantic mutation')
        if not focused:
            palette_acceptance(terminal, check, http)
        final_title = 'Overview' if args.palette_only else (acceptance(terminal, check, http, runs, presets) or 'Renamed dashboard')
        if restart_acceptance is not None:
            # Optional retained-state acceptance: restart both real native processes
            # against the same private directories. Never reseed or rewrite sidecars.
            terminal.close(); terminal = None
            (base / 'pre-restart-http.json').write_text(json.dumps(http.history, indent=2))
            os.killpg(daemon.pid, signal.SIGTERM)
            daemon.wait(timeout=15)
            metadata.unlink(missing_ok=True)
            daemon = subprocess.Popen(demo.switch_command([args.daemon, '--port', '0', '--discovery-dir', base / 'discovery', '--state-dir', base / 'state']),
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            wait(lambda: metadata.exists() or daemon.poll() is not None, 'restarted daemon metadata')
            require(daemon.poll() is None, 'Restarted daemon failed; see daemon.log')
            url = field(parse(metadata.read_text()), 'endpoint')
            http = demo.Client(url, base / 'project', switch=demo.switch_name())
            terminal = Terminal(base, args, url, 180, 55)
            restart_acceptance(terminal, check, http, runs, presets)
        if not focused:
            final_registry = http.rpc(domain='workspace')
            final_workspaces = [w for w in field(final_registry, 'workspaces') if field(w, 'name') == final_title]
            require(len(final_workspaces) == 1, 'Final workspace name must resolve to one known live identity')
            final_workspace = field(final_workspaces[0], 'id')
            terminal.wait_active_workspace(final_registry, final_workspace, 'final-workspace')
        terminal.close(); terminal = None
        # New clients ensure resizing does not confuse the terminal reconstruction.
        for width, height in (() if focused else ((80, 24), (120, 40), (180, 55))):
            terminal = Terminal(base, args, url, width, height)
            terminal.capture(f'overview-{width}x{height}',
                             ['Compact: focused tile only'] if width == 80 else ['Reported cells (agg.)'])
            terminal.wait_active_workspace(final_registry, final_workspace, f'overview-{width}x{height}')
            check(http.rpc(domain='workspace') == final_registry,
                  f'{width}x{height} client restores exact active workspace and rendered content without registry mutation')
            terminal.open_palette('ap col')
            terminal.capture(f'overlay-{width}x{height}', ['COMMAND PALETTE', 'Color'])
            terminal.key(b'\x1b')
            terminal.close(); terminal = None
        result['status'] = 'passed'
    except BaseException:
        result['error'] = traceback.format_exc()
        raise
    finally:
        if terminal:
            try: terminal.close()
            except Exception: result['cleanup_error'] = traceback.format_exc()
        if http: (base / 'http.json').write_text(json.dumps(http.history, indent=2))
        if daemon is not None and daemon.poll() is None:
            os.killpg(daemon.pid, signal.SIGTERM)
            try: daemon.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(daemon.pid, signal.SIGKILL); daemon.wait(timeout=5)
        log.close()
        (base / 'result.json').write_text(json.dumps(result, indent=2))
    print('PASS ' + result['harness'] + (' (palette-only)' if args.palette_only else ''), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--daemon', type=Path, required=True)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--preset-export', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, help='NEW directory under /tmp/opencode')
    parser.add_argument('--palette-only', action='store_true')
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    for name in ('daemon', 'client', 'preset_export'): setattr(args, name, getattr(args, name).resolve(strict=True))
    if args.evidence:
        require(args.evidence.resolve().is_relative_to('/tmp/opencode'), 'Evidence must be private /tmp/opencode state')
    else:
        # prepare expects a nonexistent directory with an existing parent.
        args.evidence = Path('/tmp/opencode') / ('frontend-composition-' + secrets.token_hex(6))
    os.umask(0o077)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Acceptance wall-clock budget exhausted')))
    signal.alarm(args.timeout)
    try: run(args)
    finally: signal.alarm(0)


if __name__ == '__main__':
    main()
