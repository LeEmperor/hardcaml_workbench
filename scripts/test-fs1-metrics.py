#!/usr/bin/env python3
"""Private retained-real FS1 metrics HTTP/PTY acceptance (stdlib; no builds).

Uses existing binaries. Copies/re-keys saved state and config under /tmp/opencode;
only explicit Refresh may invoke the adopted provider's read-only report command.
Never requests Run/Observe, builds, Git, or EDA. Originals are inventoried before
and after. All evidence and private state survive success and failure.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import traceback

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('dashboard', Path(__file__).with_name('test-fs0-dashboard.py'))
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)
fs0 = dashboard.fs0
field, record, require = fs0.field, fs0.record, fs0.require


def parse(text):
    """Sexplib disk records can contain decimal byte escapes (including NUL)."""
    tokens = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+', text)
    pos = 0

    def value():
        nonlocal pos
        token = tokens[pos]
        pos += 1
        if token == '(':
            result = []
            while tokens[pos] != ')':
                result.append(value())
            pos += 1
            return result
        require(token != ')', 'Unexpected close parenthesis')
        if token.startswith('"'):
            if '\\u' in token:
                return json.loads(token)
            raw, decoded, i = token[1:-1].encode(), bytearray(), 0
            escapes = {ord('n'): 10, ord('r'): 13, ord('t'): 9, ord('b'): 8,
                       ord('\\'): 92, ord('"'): 34, ord(' '): 32}
            while i < len(raw):
                if raw[i] != 92:
                    decoded.append(raw[i])
                    i += 1
                elif raw[i + 1:i + 4].isdigit() and len(raw[i + 1:i + 4]) == 3:
                    decoded.append(int(raw[i + 1:i + 4]))
                    i += 4
                else:
                    decoded.append(escapes[raw[i + 1]])
                    i += 2
            return decoded.decode()
        return token

    result = value()
    require(pos == len(tokens), 'Trailing disk S-expression data')
    return result


def mach(value):
    """Sexplib machine encoding, used only for private persistence identities."""
    if isinstance(value, list):
        parts = [mach(v) for v in value]
        out = ''
        for part in parts:
            if out and out[-1] not in ')"' and part[0] not in '("':
                out += ' '
            out += part
        return '(' + out + ')'
    if value and not re.search(r'[\s()";\\\x00-\x1f\x7f]', value) and '#|' not in value and '|#' not in value:
        return value
    quoted = json.dumps(value, ensure_ascii=False)
    return re.sub(r'\\u00([0-9a-f]{2})', lambda m: '\\%03d' % int(m[1], 16), quoted)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def put(value, key, replacement):
    require(sum(k == key for k, _ in value) == 1, 'Missing/duplicate field: ' + key)
    return [[k, replacement if k == key else v] for k, v in value]


# Use the byte-correct decoder for HTTP responses as well as disk state.
fs0.parse = parse


def no_generic_jobs(session, label):
    response = session.raw('/api/v1/snapshot', [['instance_id', session.metadata['instance_id']]])
    require(response[0] == 'Ok', 'Cannot inspect generic jobs: ' + str(response))
    jobs = field(response[1], 'jobs')
    with (session.evidence / 'generic-jobs.jsonl').open('a') as out:
        out.write(json.dumps(dict(label=label, jobs=jobs, time=time.time())) + '\n')
    require(jobs == [], label + ': unexpected generic jobs: ' + fs0.sexp(jobs))
    dune_calls = session.evidence / 'dune-calls.jsonl'
    if dune_calls.exists():
        require(all(json.loads(line)['allowed'] for line in dune_calls.read_text().splitlines()),
                label + ': forbidden generic Dune action attempted; see dune-calls.jsonl')


def guard_generic_builds(session):
    """Keep real read-only Dune metadata; reject every action before executing it."""
    dune = shutil.which('dune', path=session.env.get('PATH'))
    require(dune, 'Existing dune required for read-only project metadata')
    private_bin = session.evidence / 'private-bin'
    private_bin.mkdir()
    guard = private_bin / 'dune'
    guard.write_text('#!' + sys.executable + '\n' +
        'import json, os, pathlib, sys, time\n' +
        'a = sys.argv[1:]\n' +
        'ok = a == ["--version"] or a == ["describe", "workspace", "--root", ' + repr(str(session.root)) + ', "--format=sexp", "--lang=0.1"]\n' +
        'with pathlib.Path(' + repr(str(session.evidence / 'dune-calls.jsonl')) + ').open("a") as f: f.write(json.dumps(dict(argv=a, allowed=ok, time=time.time())) + "\\n")\n' +
        'if not ok: sys.exit("FS1 acceptance forbids generic Dune actions")\n' +
        'os.execv(' + repr(dune) + ', [' + repr(dune) + '] + a)\n')
    guard.chmod(0o700)
    session.env['PATH'] = str(private_bin) + os.pathsep + session.env.get('PATH', '')


class Terminal(dashboard.Terminal):
    height = 40

    def __init__(self, session):
        super().__init__(session)
        try:
            self.wait_ready('startup')
            no_generic_jobs(session, 'PTY startup')
        except BaseException:
            self.close()
            raise

    def wait_ready(self, label):
        # Rendering alone is insufficient: the first frame can arrive before the
        # terminal has disabled canonical input/echo. Do not send probe keys.
        deadline = time.monotonic() + 30
        stem = 'ready-' + label + '-' + str(time.time_ns())
        while True:
            text = self.drain(.1)
            attrs = termios.tcgetattr(self.master)
            raw = not (attrs[3] & (termios.ICANON | termios.ECHO))
            # The status suffix may be clipped by a long project/workspace name,
            # and later notices replace the footer. The authoritative workspace
            # header is present only after the registry has actually rendered.
            header = text.splitlines()[0]
            ready = (' | run ' in header and
                     (' | Linked: ' in header or ' | Independent: ' in header) and
                     'Loading workspace...' not in text)
            if label == 'startup':
                ready = ready and 'Space c c commands' in text
            if raw and ready:
                break
            if time.monotonic() >= deadline:
                self.save(stem, text)
                raise AssertionError('PTY not ready for input (raw=%s):\n%s' % (raw, text))
        self.save(stem, text)
        (self.session.evidence / (stem + '.json')).write_text(json.dumps(
            dict(raw=raw, lflag=attrs[3], icanon=bool(attrs[3] & termios.ICANON),
                 echo=bool(attrs[3] & termios.ECHO)), indent=2))

    def palette(self, title):
        self.wait_ready('before-palette')
        stamp = str(time.time_ns())
        for key in (b' ', b'c', b'c'):
            self.key(key)
        # Fail here rather than interpreting a command title as workspace keys.
        self.capture('palette-open-' + stamp, ['COMMAND PALETTE - Esc closes'])
        self.key(title.encode())
        self.capture('palette-query-' + stamp, ['COMMAND PALETTE - Esc closes', title])
        self.key(b'\r')
        self.capture('palette-dispatched-' + stamp, absent=['COMMAND PALETTE - Esc closes'])
        no_generic_jobs(self.session, 'palette: ' + title)

    def key(self, data):
        with (self.session.evidence / 'keys.jsonl').open('a') as out:
            out.write(json.dumps(dict(time=time.time(), hex=data.hex())) + '\n')
        os.write(self.master, data)
        return self.drain(.2)

    def close(self):
        try:
            if self.process.poll() is None:
                os.killpg(self.process.pid, signal.SIGTERM)
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait()
        finally:
            os.close(self.master)
            (self.session.evidence / 'pty.ansi').write_bytes(self.data)

    def resize(self, height):
        self.height = height
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack('HHHH', height, 120, 0, 0))
        os.killpg(self.process.pid, signal.SIGWINCH)
        self.drain(.5)

    def drain(self, seconds=.3):
        super().drain(seconds)
        return fs0.terminal_screen(bytes(self.data), width=120, height=self.height)


def prepare(args, cfg):
    root, state = args.evidence / 'project', args.evidence / 'state'
    root.mkdir()
    state.mkdir()
    # A minimal private project marker prevents opening/building the real project.
    (root / 'dune-project').write_text('(lang dune 3.17)\n(name fs1_metrics_acceptance)\n')
    registries = [p for p in args.source_state.glob('asic-*.sexp') if '-summary-' not in p.name]
    require(len(registries) == 1, 'Expected exactly one retained ASIC registry')
    registry = parse(registries[0].read_text())
    old_identity = field(registry, 'identity')
    identity = parse(old_identity)
    require(mach(identity) == old_identity, 'Cannot reproduce source identity encoding')
    require(registries[0].name == 'asic-' + digest(old_identity) + '.sexp', 'Registry identity hash mismatch')
    require(identity[1] == 'Inherit_daemon' and identity[2] == [cfg], 'Source registry/config mismatch')
    runs = field(registry, 'runs')
    require(len(runs) == 2, 'Expected exactly two retained registered executions')
    executions = [field(r, 'execution_file')[0] for r in runs]
    references = [record(field(r, 'reference')) for r in runs]
    require(all(Path(p).is_file() for p in executions), 'Retained execution files missing')
    provider = Path(field(cfg, 'provider_executable')).resolve()
    guard = args.evidence / 'read-only-provider'
    # This is a real-provider relay, not a metric fixture. Capture the exact report
    # bytes returned to the daemon. Fail closed on observation/run/other commands.
    guard.write_text('#!' + sys.executable + '\n' +
        'import json, pathlib, subprocess, sys\n' +
        'base = pathlib.Path(' + repr(str(args.evidence)) + ')\n' +
        'argv = sys.argv[1:]\n' +
        'allowed = argv == ["--version", "--json"] or (len(argv) == 3 and argv[0] == "report" and argv[1] in ' + repr(executions) + ' and argv[2] == "--json")\n' +
        'refs = ' + repr(references) + '\n' +
        'allowed = allowed or any(argv == ["observation", "inspect", r["attempt"], "--json"] or (len(argv) == 8 and argv[:3] == ["observation", "read-updates", r["attempt"]] and argv[3:6] == ["--stream-id", r["stream_id"], "--after"] and argv[6].isdigit() and argv[7:] == ["--json"]) for r in refs)\n' +
        'with (base / "provider-calls.jsonl").open("a") as f: f.write(json.dumps(dict(argv=argv, allowed=allowed)) + "\\n")\n' +
        'if not allowed: sys.exit("FS1 read-only provider guard rejected command")\n' +
        'p = subprocess.run([' + repr(str(provider)) + '] + argv, capture_output=True)\n' +
        'if argv[0] == "report": (base / ("report-" + pathlib.Path(argv[1]).name)).write_bytes(p.stdout)\n' +
        'if argv[:2] == ["observation", "inspect"]: (base / ("observation-" + pathlib.Path(argv[2]).name + ".json")).write_bytes(p.stdout)\n' +
        'if argv[:2] == ["observation", "read-updates"]: (base / ("updates-" + pathlib.Path(argv[2]).name + ".json")).write_bytes(p.stdout)\n' +
        'sys.stdout.buffer.write(p.stdout)\nsys.stderr.buffer.write(p.stderr)\nsys.exit(p.returncode)\n')
    guard.chmod(0o700)
    private_cfg = put(cfg, 'provider_executable', str(guard))
    (root / 'hardcaml-workbench-asic.sexp').write_text(fs0.sexp(private_cfg) + '\n')
    new_identity = mach([str(root), identity[1], [private_cfg]])
    old_prefix, new_prefix = 'asic-' + digest(old_identity), 'asic-' + digest(new_identity)
    copied = []
    for path in args.source_state.glob('*.sexp'):
        require(not path.is_symlink(), 'Refusing symlink state input')
        if path == registries[0]:
            target = state / (new_prefix + '.sexp')
            target.write_text(fs0.sexp(put(registry, 'identity', new_identity)))
        elif path.name.startswith(old_prefix + '-summary-'):
            blob = parse(path.read_text())
            require(field(blob, 'version') == '1' and 'metrics' not in record(field(blob, 'summary')),
                    'Source must contain genuine legacy v1 caches without metrics')
            target = state / path.name.replace(old_prefix, new_prefix, 1)
            shutil.copy2(path, target)  # Preserve legacy bytes/digest; do not synthesize metrics.
        elif path.name.startswith('workspace-'):
            stored = parse(path.read_text())
            key = field(stored, 'project_key')
            require(key == identity[0] + '\0Inherit_daemon', 'Unexpected workspace project key')
            key = str(root) + '\0Inherit_daemon'
            target = state / ('workspace-' + digest(key) + '.sexp')
            target.write_text(fs0.sexp(put(stored, 'project_key', key)).replace('\\u0000', '\\000'))
        else:
            raise AssertionError('Unexpected state input: ' + str(path))
        copied.append(dict(source=str(path), private=str(target)))
    require(sum('-summary-' in p['private'] for p in copied) == 2, 'Expected two old summary blobs')
    (args.evidence / 'copied-state.json').write_text(json.dumps(copied, indent=2))
    return root


KNOWN = {
    'design__instance__area': ('Mapped cell area', 'µm²'),
    'design__instance__count': ('Mapped cells', 'cells'),
    'design__instance_unmapped__count': ('Unmapped cells', 'cells'),
    'synthesis__check_error__count': ('Synthesis check errors', 'count'),
    'design__inferred_latch__count': ('Inferred latches', 'count'),
    'design__lint_error__count': ('Lint errors', 'count'),
    'design__lint_warning__count': ('Lint warnings', 'count'),
    'design__lint_timing_construct__count': ('Lint timing constructs', 'count'),
}


def synthesis_checkpoint(report):
    checkpoints = [c for c in report['checkpoints'] if c['reference']['boundary'] == 'synthesis']
    require(len(checkpoints) == 1, 'Expected exactly one explicitly referenced synthesis checkpoint')
    return checkpoints[0]


def exercise(args):
    config = args.example_root / 'hardcaml-workbench-asic.sexp'
    cfg = parse(config.read_text())
    watched = [args.source_state, config, Path(field(cfg, 'results_root')),
               Path(field(cfg, 'provider_executable'))]
    before = dashboard.inventory(watched)
    (args.evidence / 'files-before.json').write_text(json.dumps(before, indent=2))
    result = dict(status='failed', evidence=str(args.evidence), checks=[])
    session = terminal = None

    def check(ok, message):
        result['checks'].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)

    def calls():
        path = args.evidence / 'provider-calls.jsonl'
        return path.read_bytes() if path.exists() else b''

    def summary(snapshot, run):
        return next(s for s in field(snapshot, 'summaries') if field(s, 'run') == run)

    def run_map(values):
        keyed = {fs0.sexp(field(r, 'run')): record(r) for r in values}
        check(len(keyed) == len(values), 'Registered run identities are unique')
        return keyed

    def mutate(text):
        return session.mutate(session.rpc('workspace'), text)

    def select(run):
        ws = session.rpc('workspace')
        context = next(c for c in field(ws, 'contexts') if field(c, 'id') == field(demo, 'context'))
        return session.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' % (
            field(demo, 'id'), field(context, 'id'), field(context, 'selection_revision'), fs0.sexp(run)))

    try:
        root = prepare(args, cfg)
        session = fs0.Session(args, args.evidence, root)
        guard_generic_builds(session)
        # Process group ownership includes provider relays/report children.
        original_popen = fs0.subprocess.Popen

        def owned_popen(*a, **kw):
            kw.setdefault('start_new_session', True)
            return original_popen(*a, **kw)

        fs0.subprocess.Popen = owned_popen
        session.start()
        no_generic_jobs(session, 'initial daemon')
        baseline_calls = calls()
        registered = field(session.rpc('asic'), 'runs')
        runs = [field(r, 'run') for r in registered]
        for run in runs:
            session.rpc('asic', '(Load_summary %s)' % fs0.sexp(run), wait=True)
        legacy = session.rpc('asic')
        old = {int(field(s, 'cell_count')[0]): s for s in field(legacy, 'summaries')}
        check(set(old) == {673, 685}, 'Legacy L2 reopens real 673/685 executions')
        check(all(field(s, 'metrics') == [] and field(s, 'freshness') == 'Cached_unverified' for s in old.values()),
              'Legacy caches reopen with explicitly empty metrics and unverified freshness')
        check(calls() == baseline_calls, 'Legacy loads invoke no provider')
        ra, rb = field(old[673], 'run'), field(old[685], 'run')
        ws = session.rpc('workspace')
        ws = session.mutate(ws, '(Create_workspace (window %s) (name "FS1 Metrics Private") (context %s))' % (
            field(field(ws, 'windows')[0], 'id'), field(ws, 'main_context')))
        demo = field(ws, 'workspaces')[-1]
        tiles = []
        for kind in ('synthesis', 'synthesis', 'checks'):
            ws = mutate('(Create_tile (workspace %s) (kind %s) (geometry ((x 0) (y 0) (width 56) (height 14))))' % (field(demo, 'id'), kind))
            tiles.append(field(field(ws, 'tiles')[-1], 'id'))
        select(ra)
        mutate('(Set_zoom (workspace %s) (tile (%s)))' % (field(demo, 'id'), tiles[0]))
        terminal = Terminal(session)
        terminal.palette('Switch to FS1 Metrics Private')
        terminal.capture('01-legacy-summary', ['Cell count: 673'])
        terminal.key(b'm')
        terminal.capture('02-legacy-metrics', ['Synthesis metrics', 'Metrics unavailable in cached summary; explicit Refresh needed'])
        check(calls() == baseline_calls, 'Opening legacy PTY metrics does not implicitly refresh')
        refreshed = {}
        for count, run in ((673, ra), (685, rb)):
            snap = session.rpc('asic', '(Refresh %s)' % fs0.sexp(run), wait=True)
            s = summary(snap, run)
            refreshed[count] = s
            check(field(s, 'freshness') == 'Validated', 'Explicit Refresh validates %s' % count)
            check(field(s, 'acceptance') == 'not_evaluated' and field(s, 'timing') == [], 'No inferred acceptance/timing for %s' % count)
            report = json.loads((args.evidence / ('report-' + Path(field(s, 'execution_file')).name)).read_text())
            raw = {m['raw_key']: m for m in synthesis_checkpoint(report)['metrics'] if m['raw_key'] in KNOWN}
            actual = {field(m, 'key'): record(m) for m in field(s, 'metrics')}
            check(set(actual) == set(raw) == set(KNOWN), 'All eight actual area/count/diagnostic metrics projected for %s' % count)
            for key, m in actual.items():
                r = raw[key]
                check((m['label'], m['unit_'], m['availability']) == (KNOWN[key][0], [KNOWN[key][1]], r['availability']), 'Exact label/unit/availability: %s/%s' % (count, key))
                check(len(m['value']) == 1 and float(m['value'][0]) == r['value'], 'Actual available numeric metric: %s/%s' % (count, key))
                check(len(m['source']) == 1 and json.loads(m['source'][0]) == r['source'], 'Full exact source JSON: %s/%s' % (count, key))
                source = r['source']
                segment = json.loads(Path(source['path']).read_text())
                check(source['field'] == 'metrics.' + key and source['raw'] == segment['metrics'][key], 'Exact retained segment provenance: %s/%s' % (count, key))
            check(int(float(actual['design__instance__count']['value'][0])) == count, 'Mapped metric agrees with real total %s' % count)
        validated_runs = field(snap, 'runs')
        before_runs, after_runs = run_map(registered), run_map(validated_runs)
        check(set(before_runs) == set(after_runs), 'Refresh preserves exact run identities/count; no new allocation')
        refresh_changes = []
        for identity, original in before_runs.items():
            current = after_runs[identity]
            # Run identity (including build/label), public reference, selection,
            # execution file and any future fields remain immutable. Only the
            # actual read-only observation can advance cursor/status/clear error.
            dynamic = {'cursor', 'status', 'error'}
            check({k: v for k, v in original.items() if k not in dynamic} ==
                  {k: v for k, v in current.items() if k not in dynamic},
                  'Refresh preserves run/reference/selection/execution identity: ' + identity)
            reference = record(original['reference'])
            name = Path(reference['attempt']).name
            updates = json.loads((args.evidence / ('updates-' + name + '.json')).read_text())
            observation = json.loads((args.evidence / ('observation-' + name + '.json')).read_text())
            cursor = int(original['cursor'])
            check(updates['stream_id'] == observation['stream_id'] == reference['stream_id'] and
                  updates['after'] == cursor and updates['cursor'] >= cursor,
                  'Refresh cursor advances only from exact registered stream/after: ' + identity)
            for event in updates['events']:
                check(event['stream_id'] == reference['stream_id'] and cursor < event['sequence'] <= updates['cursor'],
                      'Refresh event sequence is monotonic and stream-bound: ' + identity)
                cursor = event['sequence']
            check(int(current['cursor']) == updates['cursor'] and observation['cursor'] >= updates['cursor'],
                  'Refreshed cursor equals actual validated update cursor: ' + identity)
            outcome = observation['state'].get('outcome')
            final = (observation['observation_status'] == 'final' and not observation['writer_active'] and
                     outcome is not None and observation['cursor'] == updates['cursor'])
            check(current['status'] == (outcome['status'] if final else 'observing') and current['error'] == [],
                  'Refreshed status/error exactly match validated observation: ' + identity)
            check(observation.get('execution_file') == original['execution_file'][0],
                  'Validated observation retains the original execution reference: ' + identity)
            refresh_changes.append(dict(run=original['run'], changes={
                k: dict(before=original[k], after=current[k]) for k in dynamic if original[k] != current[k]}))
        (args.evidence / 'run-refresh-validation.json').write_text(json.dumps(dict(
            before=registered, after=validated_runs, changes=refresh_changes), indent=2))
        warm_calls = calls()
        terminal.capture('03-refreshed-metrics', ['Synthesis metrics', 'Mapped cells: 673 cells', 'Mapped cell area:', 'Lint warnings:', 'not_evaluated'])
        terminal.resize(12)
        terminal.capture('04-metrics-small', ['Synthesis metrics'])
        terminal.key(b'j')
        down = terminal.capture('04-metrics-scroll-down')
        terminal.key(b'k')
        up = terminal.capture('04-metrics-scroll-up')
        check(down != up, 'Actual m-mode j/k scroll changes rendered page')
        terminal.resize(40)
        terminal.key(b'e')
        pages = [terminal.capture('05-evidence', ['Synthesis evidence'])]
        # Full raw sources and producer can exceed the viewport by many pages.
        for i in range(180):
            terminal.key(b'j')
            page = terminal.capture('05-evidence-%03d' % i)
            pages.append(page)
            if page == pages[-2]:
                break
        compact = lambda text: re.sub(r'\s+', '', text.replace('|', ''))
        screens = [compact(p) for p in pages]
        a = refreshed[673]
        for value in [field(a, 'execution_file'), field(a, 'producer')] + [field(m, 'source')[0] for m in field(a, 'metrics')]:
            check(any(compact(value) in p for p in screens), 'PTY Evidence exposes complete wrapped source: ' + value[:100])
        terminal.key(b'\x1b')
        terminal.key(b'm')
        terminal.palette('Synthesis: Inspect metrics')
        terminal.capture('06-palette-metrics', ['Synthesis metrics', 'Mapped cells: 673 cells'])
        select(rb)
        terminal.capture('07-run-switch', ['Synthesis metrics', 'Mapped cells: 685 cells'], ['Mapped cells: 673 cells'])
        terminal.key(b'\x1b')
        terminal.palette('Unzoom workspace')
        terminal.key(b'\t')
        terminal.palette('Zoom focused tile')
        terminal.capture('08-independent-tile-summary', ['Cell count: 685'], ['Synthesis metrics |'])
        terminal.key(b'm')
        terminal.capture('09-second-tile-metrics', ['Synthesis metrics', 'Mapped cells: 685 cells'])
        mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' % (tiles[0], fs0.sexp(ra)))
        terminal.palette('Unzoom workspace')
        terminal.key(b'\t')
        terminal.palette('Zoom focused tile')
        terminal.capture('10-checks', ['Checks: synthesis diagnostic counters', 'Synthesis check errors:', 'Lint errors:', 'Zero diagnostic counts do not imply signoff', 'not_evaluated', 'DRC/LVS: no terminal verification result imported'])
        terminal.palette('Unzoom workspace')
        terminal.key(b'\t')
        terminal.palette('Zoom focused tile')
        terminal.key(b'm')
        terminal.capture('11-pinned-run', ['Synthesis metrics', 'Mapped cells: 673 cells'], ['Mapped cells: 685 cells'])
        for _ in range(2):
            for run in (rb, ra):
                select(run)
                snap = session.rpc('asic', '(Load_summary %s)' % fs0.sexp(run), wait=True)
                check(summary(snap, run) == refreshed[673 if run == ra else 685], 'Warm switching preserves complete summary')
        check(calls() == warm_calls, 'Warm PTY/RPC switching launches no provider command')
        inspected_runs = field(session.rpc('asic'), 'runs')
        check(run_map(inspected_runs) == after_runs,
              'Warm inspection preserves every validated run field, independent of list order; no allocation')
        saved_ws = session.rpc('workspace')
        no_generic_jobs(session, 'before restart')
        terminal.close()
        terminal = None
        old_instance = session.metadata['instance_id']
        session.stop()
        session.start()
        check(session.metadata['instance_id'] != old_instance, 'Restart uses a new daemon instance')
        check(session.rpc('workspace') == saved_ws, 'Private workspace/pins survive restart')
        for count, run in ((673, ra), (685, rb)):
            s = summary(session.rpc('asic', '(Load_summary %s)' % fs0.sexp(run), wait=True), run)
            check(field(s, 'freshness') == 'Cached_unverified', 'L2 metric cache is unverified after restart')
            check({k: v for k, v in s if k != 'freshness'} == {k: v for k, v in refreshed[count] if k != 'freshness'}, 'L2 preserves every field except freshness for %s' % count)
        check(calls() == warm_calls, 'Restart/L2 reopening invokes no provider')
        no_generic_jobs(session, 'after restart/L2')
        check(True, 'No generic build/test/discovery jobs throughout private acceptance')
        provider_calls = [json.loads(line) for line in warm_calls.splitlines()]
        check(all(c['allowed'] for c in provider_calls) and
              sum(c['argv'][0] == 'report' for c in provider_calls) == 2,
              'Exactly two real reports, plus read-only metadata/observation queries; no producer commands')
        result.update(status='passed', summaries={str(k): record(v) for k, v in refreshed.items()})
    except BaseException:
        result['error'] = traceback.format_exc()
        raise
    finally:
        try:
            if terminal:
                terminal.close()
        finally:
            if session and session.process:
                # Terminate only this harness's process group, including a report
                # relay left behind by an interrupted/failed client request.
                try:
                    os.killpg(session.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                session.stop()
            after = dashboard.inventory(watched)
            (args.evidence / 'files-after.json').write_text(json.dumps(after, indent=2))
            result['input_files_unchanged'] = before == after
            if before != after:
                result['status'] = 'failed'
            (args.evidence / 'result.json').write_text(json.dumps(result, indent=2))
            require(before == after, 'Original state/config/results/provider changed; see inventories')


def main():
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-state', type=Path, default=Path('/tmp/opencode/workbench-fs0-91em64rl/real/state'))
    parser.add_argument('--example-root', type=Path, default=repo.parent / 'hardcaml_asic_example')
    parser.add_argument('--client', type=Path, default=repo / '_build/default/terminal/main.exe')
    parser.add_argument('--daemon', type=Path, default=repo / '_build/default/daemon/main.exe')
    parser.add_argument('--outer-timeout', type=int, default=90)
    args = parser.parse_args()
    for name in ('source_state', 'example_root', 'client', 'daemon'):
        setattr(args, name, getattr(args, name).resolve())
    require(args.source_state.is_dir(), 'Missing retained source state')
    require(args.client.is_file() and args.daemon.is_file(), 'Existing client/daemon binaries required')
    require(0 < args.outer_timeout <= 300, 'Timeout must be 1..300 seconds')
    args.evidence = Path(tempfile.mkdtemp(prefix='workbench-fs1-metrics-', dir='/tmp/opencode'))
    (args.evidence / 'commands.json').write_text(json.dumps(dict(argv=sys.argv, options={k: str(v) for k, v in vars(args).items()}, pty=dict(width=120, height=40)), indent=2))
    print('Evidence: ' + str(args.evidence), flush=True)
    def interrupted(signum, _frame):
        raise KeyboardInterrupt('Acceptance interrupted by signal %s' % signum)

    signal.signal(signal.SIGTERM, interrupted)
    exercise(args)
    print('PASS: private FS1 metrics Refresh / PTY / L2 restart', flush=True)


if __name__ == '__main__':
    main()
