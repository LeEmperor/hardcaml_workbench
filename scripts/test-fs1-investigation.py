#!/usr/bin/env python3
"""Parent-run retained-real FS1 investigation; existing binaries, read-only provider.

Run serially, with no overlapping caller tests. No build, implementation, finalize,
runtime validation, Git, installation or GUI is requested. Evidence is retained in
/tmp/opencode. The recording viewer is a fixture; its GDS input and KLayout reader
are real. A successful layout read is not signoff or a new physical tool flow.
"""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import termios
import time
import traceback

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location(
    'lifecycle', Path(__file__).with_name('test-fs1-lifecycle.py'))
life = importlib.util.module_from_spec(spec)
spec.loader.exec_module(life)
metrics, fs0, dashboard = life.metrics, life.fs0, life.dashboard
field, record, require = life.field, life.record, life.require
load, sha256, save = life.load, life.sha256, life.save
DEFAULTS = dict(timing='signoff', clocks='signoff', physical='placement', routing='routing')
GDS_SHA = '3e92e491336136af9a4cf4450451c87064b1b6d1247bd8c0dfd60fa82f1b4943'


class Session(life.Session):
    def command(self, extra, label, timeout=90, success=True):
        return super().command(extra, label, timeout=min(timeout, self.args.outer_timeout), success=success)


class Terminal(life.Terminal):
    def capture_matching(self, label, predicate, expectation, timeout=12):
        deadline = min(self.session.deadline, time.monotonic() + timeout)
        while True:
            text = self.drain(.2)
            if predicate(text):
                self.save(label, text)
                return text
            if time.monotonic() >= deadline:
                self.save(label, text)
                raise AssertionError('%s: expected %s\n%s' % (label, expectation, text))

    def count(self, label, count, expected=(), absent=()):
        # The explorer is a full-screen surface: its count starts a screen line.
        # In particular, "1 rows" must never match "1021 rows" or "11 rows".
        pattern = re.compile(r'^%d rows(?=\s|$)' % count, re.MULTILINE)
        return self.capture_matching(label, lambda text: bool(pattern.search(text))
                                     and all(s in text for s in expected)
                                     and all(s not in text for s in absent),
                                     'anchored %d rows; expected %r; absent %r' % (count, expected, absent))

    def filter(self, label, value, previous, count):
        # Do not batch '/' with text/Enter: input may be delivered as one Text
        # event while the explorer is still outside its editing state.
        self.key(b'/')
        self.capture(label + '-editing', ['EDIT filter=' + previous])
        if previous:
            # Acknowledge each deletion rather than queueing control characters.
            for n in range(len(previous) - 1, -1, -1):
                self.key(b'\x7f')
                self.capture(label + '-delete-%03d' % n, ['EDIT filter=' + previous[:n] + ' ·'])
        if value:
            self.key(value.encode())
        self.count(label + '-query-visible', count, ['EDIT filter=' + value + ' ·'])
        self.key(b'\r')
        return self.count(label, count, ['filter=' + value + ' ·'], ['EDIT filter='])

    def wait_ready(self, label):
        # Inspection/artifacts deliberately replace the workspace header. Keep
        # the shared startup barrier, and admit only rendered, raw-mode explorers
        # when subsequently opening the real global command palette.
        if label != 'startup':
            text = self.drain(.1)
            flags = termios.tcgetattr(self.master)[3]
            if not flags & (termios.ICANON | termios.ECHO) and any(
                    text.splitlines()[0].startswith(s) for s in ('INSPECT ', 'REPORTS / ARTIFACTS')):
                self.save('ready-explorer-' + str(time.time_ns()), text)
                return
        return super().wait_ready(label)


def prepare(args, inputs, receipt, operation):
    root = args.evidence / 'project'
    root.mkdir()
    for name in ('state', 'results', 'daemon-tmp', 'client-tmp', 'config', 'home'):
        (args.evidence / name).mkdir(mode=0o700)
    (root / 'dune-project').write_text('(lang dune 3.17)\n(name fs1_investigation)\n')
    cfg = metrics.parse((args.example_root / 'hardcaml-workbench-asic.sexp').read_text())
    policy = dict(provider=str(args.provider), execution=inputs['execution_file'],
                  allocation=inputs['allocation'], attempt=str(Path(operation['results']['path']).parent),
                  selections=[[d, DEFAULTS[d]] for d in args.domains] + [['timing', 'synthesis']],
                  deadline=args.deadline - 20, timeout=args.outer_timeout)
    save(args.evidence / 'relay-policy.json', policy)
    relay = args.evidence / 'read-only-provider'
    relay.write_text('#!' + sys.executable + '\nBASE = ' + repr(str(args.evidence)) + '\n' + r'''
import fcntl, json, os, pathlib, subprocess, sys, time
base = pathlib.Path(BASE)
p = json.loads((base / 'relay-policy.json').read_text())
a = sys.argv[1:]
allocation, execution = p['allocation'], p['execution']
ok = a == ['--version', '--json'] or a == ['report', execution, '--json']
ok |= a == ['observation', 'inspect', allocation['attempt'], '--json']
ok |= (len(a) == 8 and a[:3] == ['observation', 'read-updates', allocation['attempt']]
       and a[3:6] == ['--stream-id', allocation['stream_id'], '--after']
       and a[6].isdigit() and a[7:] == ['--json'])
ok |= a == ['finalization-inspect', p['attempt'], '--json']
if len(a) in (7, 11) and a[:2] == ['inspect', execution]:
    domain, stage = a[3], a[5]
    head = ['inspect', execution, '--domain', domain, '--stage', stage, '--json']
    ok = [domain, stage] in p['selections'] and a[:7] == head
    if len(a) == 11:
        ok = ok and a[7] == '--row-id' and a[9] == '--expected-digest'
        found = False
        for path in base.glob('query-*.stdout'):
            try:
                j = json.loads(path.read_text())
                found |= (j.get('execution_file') == execution and j.get('domain') == domain
                          and j.get('stage') == stage and j.get('source_digest') == a[10]
                          and any(r['id'] == a[8] for r in j.get('rows', [])))
            except (ValueError, KeyError, UnicodeError):
                pass
        ok = ok and found
with (base / 'provider-calls.jsonl').open('a') as out:
    fcntl.flock(out, fcntl.LOCK_EX)
    out.write(json.dumps(dict(argv=a, allowed=bool(ok), time=time.time(), pid=os.getpid())) + '\n')
if not ok:
    sys.exit('FS1 investigation: non-allowlisted provider command')
remaining = p['deadline'] - time.monotonic()
if remaining <= 0:
    sys.exit('FS1 investigation query budget exhausted')
stem = base / ('query-' + str(time.time_ns()))
try:
    result = subprocess.run([p['provider']] + a, capture_output=True,
                            timeout=min(p['timeout'], remaining))
except subprocess.TimeoutExpired as e:
    stem.with_suffix('.stdout').write_bytes(e.stdout or b'')
    stem.with_suffix('.stderr').write_bytes(e.stderr or b'')
    sys.exit('FS1 investigation provider query timed out')
stem.with_suffix('.stdout').write_bytes(result.stdout)
stem.with_suffix('.stderr').write_bytes(result.stderr)
stem.with_suffix('.json').write_text(json.dumps(dict(argv=a, returncode=result.returncode)))
sys.stdout.buffer.write(result.stdout)
sys.stderr.buffer.write(result.stderr)
sys.exit(result.returncode)
''')
    relay.chmod(0o700)
    deny = args.evidence / 'no-project-execution'
    deny.write_text('#!' + sys.executable + '\nimport sys\nsys.exit("No project execution in FS1 investigation")\n')
    deny.chmod(0o700)
    for key, value in (('provider_executable', str(relay)), ('project_executable', str(deny)),
                       ('results_root', str(args.evidence / 'results'))):
        cfg = metrics.put(cfg, key, value)
    (root / 'hardcaml-workbench-asic.sexp').write_text(fs0.sexp(cfg) + '\n')
    return root


def prepare_viewer(session):
    viewer = session.evidence / 'record-binary-viewer'
    viewer.write_text('#!' + sys.executable + '\nBASE = ' + repr(str(session.evidence)) + '\n' + '''
import hashlib, json, os, pathlib, stat, sys
assert len(sys.argv) == 2
base = pathlib.Path(BASE)
p = pathlib.Path(sys.argv[1])
raw = p.read_bytes()
result = dict(argv=sys.argv, local_path=str(p), size=len(raw),
              sha256=hashlib.sha256(raw).hexdigest(),
              mode=stat.S_IMODE(p.stat().st_mode),
              directory_mode=stat.S_IMODE(p.parent.stat().st_mode))
with (base / 'binary-viewer-calls.jsonl').open('a') as out:
    out.write(json.dumps(result) + '\\n')
tmp = base / ('viewer-' + str(os.getpid()) + '.tmp')
tmp.write_text(json.dumps(result))
os.replace(tmp, base / 'binary-viewer.json')
''')
    viewer.chmod(0o700)
    wrapper = session.evidence / 'binary-viewer-client'
    wrapper.write_text('#!' + sys.executable + '\nimport os, sys\n' +
                      'os.execv(' + repr(str(session.args.client)) + ', [' +
                      repr(str(session.args.client)) + ', "--artifact-binary-viewer", ' +
                      repr(str(viewer)) + '] + sys.argv[1:])\n')
    wrapper.chmod(0o700)
    session.viewer_client = wrapper
    # lifecycle.Terminal supplies the wrapper only to the interactive client.


def rows(index):
    return [record(r) for r in field(index, 'rows')]


def oracle_paths(directory):
    """Read original max/min bytes independently of provider row construction."""
    result = []
    for path in sorted(directory.glob('*/m*.rpt')):
        if path.name not in ('max.rpt', 'min.rpt'):
            continue
        lines = path.read_text().splitlines()
        starts = [i for i, line in enumerate(lines) if line.startswith('Startpoint:')]
        for start in starts:
            end = next(i for i in range(start, len(lines)) if 'slack (' in lines[i])
            block = lines[start:end + 1]
            header = {k: next(line.split(':', 1)[1].strip() for line in block if line.startswith(k + ':'))
                      for k in ('Startpoint', 'Endpoint', 'Path Group', 'Path Type')}
            result.append(dict(path=str(path), first=start + 1, last=end + 1,
                               corner=path.parent.name, slack=float(lines[end].split()[0]), header=header))
    return result


def verify_clock_headers(args, check, rr, diagnostics):
    # Treat report bytes, not display names or a hard-coded clock identifier, as
    # the oracle. Known fields have schema keys; extension headers keep their
    # original label under header:<label> without invented generation semantics.
    keys = dict(zip(('Sources', 'Generated', 'Virtual', 'Propagated', 'Master Clock',
                     'Source Clock', 'Divide By', 'Multiply By', 'Edges', 'Edge Shifts', 'Invert'),
                    ('sources', 'generated', 'virtual', 'propagated', 'master_clock',
                     'source_clock', 'divide_by', 'multiply_by', 'edges', 'edge_shifts', 'invert')))
    reports = {}
    for r in rr:
        source = json.loads(r['source'])
        path = Path(source['file']['path'])
        if path.name == 'clock.rpt':
            reports[path] = path.read_text().splitlines()
    check(bool(reports), 'Clock flags have original retained clock.rpt sources')
    expected, contexts = [], {}
    for path, lines in reports.items():
        clock, relationships = None, {}
        for n, line in enumerate(lines, 1):
            text = line.strip()
            if text.startswith('Clock:'):
                clock = text.split(':', 1)[1].strip()
                relationships[clock] = {}
            elif re.fullmatch(r'Clock\s+\S+', text):
                clock = text.split()[1]
            elif re.match(r'^\S+\s+period_min\s*=', text):
                clock = text.split()[0]
            else:
                header = re.fullmatch(r'([A-Za-z][^:]{0,63}):\s*(.*)', text)
                if header and header[1] != 'Period':
                    check(bool(clock), 'Original clock header has explicit clock context: %s:%d' % (path, n))
                    label, value = header.groups()
                    key = keys.get(label, 'header:' + label)
                    relationships.setdefault(clock, {})[key] = value.strip()
                    expected.append((str(path), n, clock, key, value.strip()))
            contexts[path, n] = (clock, dict(relationships.get(clock, {})))
    actual = []
    for r in rr:
        source, supplied = json.loads(r['source']), dict(r['fields'])
        path = Path(source['file']['path'])
        if path not in reports or r['category'] not in ('clock_header', 'clock_network'):
            continue
        first, last = source['span']['first_line'], source['span']['last_line']
        clock, inherited = contexts[path, first]
        check(first == last and bool(clock) and supplied.get('clock') == clock
              and all(supplied.get(k) == v for k, v in inherited.items()),
              'Structured clock row preserves original per-clock flags/context at %s:%d' % (path, first))
        if r['category'] == 'clock_header':
            # The source line selects the field being reported. Other supplied
            # relationship fields may be inherited from earlier header lines.
            label, value = reports[path][first - 1].strip().split(':', 1)
            key = keys.get(label, 'header:' + label)
            check(supplied.get(key) == value.strip(), 'Exact reported structured clock flag: ' + key)
            actual.append((str(path), first, clock, key, supplied[key]))
    check(sorted(actual) == sorted(expected), 'All original clock header lines have exact structured rows, spans and clock identities')
    for path in reports:
        check({'sources', 'generated', 'virtual', 'propagated'} <=
              {key for p, _, _, key, _ in expected if p == str(path)},
              'Retained clock report supplies Sources/Generated/Virtual/Propagated: ' + str(path))
    propagation = [r for r in rr if r['category'] == 'clock_propagation']
    check(any(key == 'virtual' and value == 'yes' for _, _, _, key, value in expected)
          and any(key == 'propagated' and value == 'no' for _, _, _, key, value in expected)
          and bool(propagation)
          and any('clock header and STA propagation evidence retained separately' in d for d in diagnostics),
          'Conflicting original clock report flags and actual STA propagation diagnostics preserved separately')
    for r in propagation:
        source = json.loads(r['source'])
        path, n = source['file']['path'], source['span']['first_line']
        raw = Path(path).read_text().splitlines()[n - 1]
        check(dict(r['fields']).get('message') == raw
              and any('%s:%d: %s' % (path, n, raw) in d for d in diagnostics),
              'Separate STA propagation row and diagnostic preserve exact original log line')
    save(args.evidence / 'independent-clock-headers.json', expected)


def verify_index(args, check, index, domain, execution):
    rr = rows(index)
    check(field(index, 'execution_file') == execution and field(index, 'execution_sha256') == sha256(execution),
          domain + ': exact execution identity/hash')
    check(rr and field(index, 'truncated') == 'false' and field(index, 'cached_unverified') == 'false',
          domain + ': real nonempty complete validated index')
    sources = {}
    for r in rr:
        source = json.loads(r['source'])
        path = Path(source['file']['path'])
        if path not in sources:
            sources[path] = (sha256(path), len(path.read_bytes().split(b'\n')))
        check(path.is_absolute() and sources[path][0] == source['file']['sha256'], domain + ': source hash ' + r['id'])
        span = source['span']
        check(1 <= span['first_line'] <= span['last_line'] <= sources[path][1]
              and source['step_id'] in r['producer']
              and source['evidence_scope'] == 'observed supplementary-not-checkpoint-inventoried',
              domain + ': exact span, producer and supplementary evidence scope')
    if domain == 'timing':
        paths = [r for r in rr if r['category'] == 'timing_path']
        parent = Path(json.loads(paths[0]['source'])['file']['path']).parent.parent
        raw = oracle_paths(parent)
        actual = []
        for r in paths:
            src, f = json.loads(r['source']), dict(r['fields'])
            actual.append((src['file']['path'], src['span']['first_line'], src['span']['last_line'],
                           r['corner'][0], float(r['value'][0]), f['startpoint'], f['endpoint'], f['group'], f['type']))
            check(r['unit_'] == ['ns'] and bool(src['units_source']), 'Timing ns comes from retained Liberty declaration')
        expected = [(r['path'], r['first'], r['last'], r['corner'], r['slack'],
                     r['header']['Startpoint'], r['header']['Endpoint'], r['header']['Path Group'],
                     r['header']['Path Type']) for r in raw]
        check(sorted(actual) == sorted(expected) and len(raw) == 1020,
              'All 1020 signoff max/min paths equal independently counted original report spans and signed slack')
        check(len({r['corner'][0] for r in paths}) == 3 and {dict(r['fields'])['type'] for r in paths} == {'max', 'min'},
              'Three real corners, max/setup and min/hold groups')
        for corner, typ, expected_slack in [('slow', 'max', 11.6755), ('fast', 'min', .125029)]:
            value = min(float(r['value'][0]) for r in paths if corner in r['corner'][0] and dict(r['fields'])['type'] == typ)
            check(abs(value - expected_slack) < .0001, 'Known signed %s %s slack, six-digit report precision' % (corner, typ))
        save(args.evidence / 'independent-timing-paths.json', raw)
    elif domain == 'clocks':
        network = [r for r in rr if r['category'] == 'clock_network']
        for transition, label, value in [('rise -> rise', 'network_skew', .085678),
                                          ('fall -> fall', 'network_skew', .079398),
                                          ('rise -> rise', 'latency_min', .470431),
                                          ('fall -> fall', 'latency_max', .545056)]:
            check(any('slow' in ''.join(r['corner']) and transition in r['name'] and r['name'].endswith(label)
                      and r['unit_'] == ['ns'] and abs(float(r['value'][0]) - value) < 1e-6 for r in network),
                  'Measured slow clock %s %s = %s ns' % (transition, label, value))
        verify_clock_headers(args, check, rr, field(index, 'diagnostics'))
    elif domain == 'physical':
        for name, value in [('design__instance__count', 717), ('design__instance__area', 13363.1)]:
            check(any(r['name'] == name and r['producer'].startswith('OpenROAD.DetailedPlacement@')
                      and abs(float(r['value'][0]) - value) < .01
                      and json.loads(r['source'])['boundary'] == 'placement' for r in rr),
                  'Exact legalized placement producer %s = %s' % (name, value))
    else:
        check(any(r['category'] == 'global_congestion' and r['name'] == 'Metal2'
                  and {'resource', 'demand', 'total_overflow'} <= dict(r['fields']).keys() for r in rr),
              'Real Metal2 congestion resource/demand/overflow')
        for prefix in ('route__net', 'route__vias'):
            check(any(r['name'].startswith(prefix) and r['value'] and r['unit_'] == ['count']
                      and r['producer'].startswith('OpenROAD.DetailedRouting@') for r in rr),
                  'Detailed routing attributed native counts: ' + prefix)
        for name, value in [('route__net', 1051), ('route__vias', 5543)]:
            check(any(r['name'] == name and r['value'] and float(r['value'][0]) == value
                      and r['producer'].startswith('OpenROAD.DetailedRouting@') for r in rr),
                  'Known detailed-routing native count %s = %d' % (name, value))
    return rr


def exercise(args):
    inputs = load(args.inputs)
    receipt = load(inputs['physical_receipt'])
    operation = load(args.operation)
    require(inputs['allocation'] == receipt['allocation'] and inputs['execution_file'] == receipt['execution_file'],
            'Original registered allocation/execution must match physical receipt')
    require(operation['acceptance'] == 'pass' and operation['execution']['path'] == inputs['execution_file']
            and operation['execution']['sha256'] == sha256(inputs['execution_file']), 'Exact accepted execution required')
    watched = [args.inputs.parent, Path(receipt['config']['results_root']), args.operation.parent,
               args.provider.parent.parent, Path(receipt['config']['provider']).parent.parent,
               args.source_state, args.example_root / 'hardcaml-workbench-asic.sexp']
    before = dashboard.inventory(watched)
    save(args.evidence / 'files-before.json', before)
    outcome = dict(status='failed', checks=[])
    session = terminal = None

    def check(ok, expectation):
        outcome['checks'].append(dict(passed=bool(ok), expectation=expectation))
        require(ok, expectation)

    def calls():
        p = args.evidence / 'provider-calls.jsonl'
        return p.read_bytes() if p.exists() else b''

    def mutate(text):
        return session.mutate(session.rpc('workspace'), text)

    def inspect(domain, stage=None):
        stage = stage or DEFAULTS[domain]
        snap = session.rpc('asic', '(Inspect (run %s) (domain %s) (stage %s) (refresh false))' %
                           (fs0.sexp(run), domain, stage), wait=True)
        return next(i for i in field(snap, 'inspections') if field(i, 'domain') == domain and field(i, 'stage') == stage)

    def palette(domain):
        terminal.palette('Inspect %s asic/%s · %s' % (
            'timing paths' if domain == 'timing' else domain, field(run, 'id'), DEFAULTS[domain]))
        terminal.count('open-' + domain + '-' + str(time.time_ns()), len(rows(indexes[domain])),
                       ['INSPECT ' + domain])

    def select(value):
        ws = session.rpc('workspace')
        c = next(c for c in field(ws, 'contexts') if field(c, 'id') == field(workspace, 'context'))
        return session.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run %s))' % (
            field(workspace, 'id'), field(c, 'id'), field(c, 'selection_revision'),
            '()' if value is None else '(' + fs0.sexp(value) + ')'))

    def pages(label, expected):
        captured = []
        page = terminal.capture(label + '-00')
        for n in range(40):
            captured.append(page)
            if all(any(s in p for p in captured) for s in expected):
                return captured
            terminal.key(b'n')
            previous = page
            page = terminal.capture_matching(label + '-%02d' % (n + 1),
                lambda text: text != previous, 'detail page advances after n; still missing ' +
                repr([s for s in expected if not any(s in p for p in captured)]))
        raise AssertionError(label + ': detail/source text not reachable: ' + repr(expected))

    try:
        root = prepare(args, inputs, receipt, operation)
        session = Session(args, args.evidence, root)
        session.deadline = args.deadline - 20
        session.env.update(TMPDIR=str(args.evidence / 'daemon-tmp'), HOME=str(args.evidence / 'home'),
                           XDG_CONFIG_HOME=str(args.evidence / 'config'), PYTHONDONTWRITEBYTECODE='1')
        prepare_viewer(session)
        metrics.guard_generic_builds(session)
        session.start()
        reference = [[k, inputs['allocation'][k]] for k in ('attempt', 'stream_id')]
        snap = session.rpc('asic', '(Register %s)' % fs0.sexp(reference), wait=True)
        check(len(field(snap, 'runs')) == 1 and field(field(snap, 'runs')[0], 'reference') == reference,
              'Register adopts only the exact original public allocation')
        run = field(field(snap, 'runs')[0], 'run')
        session.rpc('asic', '(Load_summary %s)' % fs0.sexp(run), wait=True)
        indexes = {d: inspect(d) for d in args.domains}
        for d, index in indexes.items():
            verify_index(args, check, index, d, inputs['execution_file'])
        save(args.evidence / 'validated-indexes.json', indexes)
        ws = session.rpc('workspace')
        ws = session.mutate(ws, '(Create_workspace (window %s) (name "FS1 Investigation") (context %s))' % (
            field(field(ws, 'windows')[0], 'id'), field(ws, 'main_context')))
        workspace = field(ws, 'workspaces')[-1]
        tiles = []
        for x in (0, 57):
            ws = mutate('(Create_tile (workspace %s) (kind timing) (geometry ((x %d) (y 0) (width 56) (height 14))))' %
                        (field(workspace, 'id'), x))
            tiles.append(field(field(ws, 'tiles')[-1], 'id'))
        select(run)
        mutate('(Set_zoom (workspace %s) (tile (%s)))' % (field(workspace, 'id'), tiles[0]))
        session.env['TMPDIR'] = str(args.evidence / 'client-tmp')
        terminal = Terminal(session)
        terminal.palette('Switch to FS1 Investigation')
        for domain in args.domains:
            palette(domain)
            index = indexes[domain]
            rr = rows(index)
            warm = calls()
            terminal.key(b'd')
            pages(domain + '-source', ['Execution SHA256: ' + sha256(inputs['execution_file']),
                                      'Source digest: ' + field(index, 'source_digest'), 'Producer:', 'Source:'])
            terminal.key(b'\x1b')
            check(calls() == warm, domain + ': source metadata is provider-free')
            chosen = min(rr, key=lambda r: (float(r['value'][0]) if r['value'] else math.inf, r['id']))
            if domain == 'timing':
                # Every axis returns to ALL; compare counts with the actual index.
                for key, axis in ((b'c', 'corner'), (b'g', 'group'), (b'p', 'producer')):
                    values = sorted({r[axis][0] for r in rr if r[axis]} if axis != 'producer' else {r[axis] for r in rr})
                    for value in values + [None]:
                        terminal.key(key)
                        count = len([r for r in rr if value is None or (r[axis] == value if axis == 'producer' else r[axis] == [value])])
                        terminal.count('axis-' + axis + '-' + str(time.time_ns()), count)
                terminal.key(b'j')
                selected = terminal.capture('timing-selected-next')
                marker = next(line.strip() for line in selected.splitlines() if line.strip().startswith('> '))
                for _ in range(3):
                    terminal.key(b's')
                    terminal.capture('stable-sort-' + str(time.time_ns()), [marker[:65]])
                terminal.key(b'k')
                near = sum(r['status'].lower() == 'violated' or
                           (r['unit_'] == ['ns'] and r['value'] and float(r['value'][0]) <= 1) for r in rr)
                terminal.key(b'v')
                terminal.count('near-one-ns', near)
                terminal.key(b'v')
                terminal.count('near-cleared', len(rr))
                terminal.key(b'/')
                terminal.capture('paste-filter-editing', ['EDIT filter='])
                terminal.key(b'\x1b[200~paste r t j p\x1b[201~')
                terminal.count('paste-filter-literal', 0, ['EDIT filter=paste r t j p'])
                terminal.key(b'\x15')
                terminal.count('paste-filter-cleared', len(rr), ['EDIT filter='])
                terminal.key(b'\r')
                terminal.count('paste-filter-finished', len(rr), absent=['EDIT filter='])
                check(calls() == warm, 'Bracketed filter paste keeps r/t/j/p literal and launches no provider read')
                text = 'FS1_NO_SUCH_ENDPOINT_9f47'
                terminal.filter('filter-no-match', text, '', 0)
                terminal.filter('filter-cleared', '', text, len(rr))
                check(calls() == warm, 'c/g/p/s/v/filter/j/k are warm provider-free local controls')
            # Exact row filtering makes Enter deterministic even after sorting.
            terminal.filter(domain + '-one-exact-row', chosen['id'], '', 1)
            terminal.key(b'\r')
            terminal.capture(domain + '-detail-open', ['Row: ' + chosen['id']])
            # Wait on the actual dispatched Enter operation, not a direct detail
            # RPC that could conceal a lost key. Scrolling starts only once its
            # exact row/digest response has completed successfully.
            detail_deadline = min(session.deadline, time.monotonic() + args.outer_timeout)
            while True:
                snap = session.rpc('asic', wait=True)
                matching = [d for d in field(snap, 'inspection_details') if field(d, 'domain') == domain
                            and field(d, 'stage') == DEFAULTS[domain] and field(d, 'row_id') == chosen['id']
                            and field(d, 'source_digest') == field(index, 'source_digest')]
                if matching:
                    break
                screen = terminal.drain(.2)
                if time.monotonic() >= detail_deadline:
                    terminal.save(domain + '-detail-completion-timeout', screen)
                    raise AssertionError(domain + ': Enter did not complete exact row/digest detail\n' + screen)
            check(len(matching) == 1 and field(matching[0], 'error') == [],
                  domain + ': Enter completed exact row/digest detail before scrolling')
            terminal.capture(domain + '-detail-ready', ['Row: ' + chosen['id']],
                             ['Waiting for exact row/digest detail'])
            expected = ['Row: ' + chosen['id'], 'Producer: ' + chosen['producer']]
            source = json.loads(chosen['source'])
            if domain == 'timing':
                expected += ['Startpoint:', 'Endpoint:', 'slack (']
            else:
                expected += ['Source:']  # Long canonical paths wrap in the PTY.
            pages(domain + '-detail', expected)
            snap = session.rpc('asic', wait=True)
            detail = next(d for d in field(snap, 'inspection_details') if field(d, 'domain') == domain
                          and field(d, 'row_id') == chosen['id'])
            check(field(detail, 'source_digest') == field(index, 'source_digest') and field(detail, 'error') == [],
                  domain + ': actual Enter detail fences exact row and source digest')
            raw_lines = Path(source['file']['path']).read_text().splitlines()
            span = source['span']
            check(all('%d: %s' % (n, raw_lines[n - 1]) in field(detail, 'text')
                      for n in range(span['first_line'], min(span['last_line'], span['first_line'] + 5) + 1)),
                  domain + ': detail retains actual numbered original tool-phase/source excerpt')
            check('signoff pass' not in field(detail, 'text').lower(), domain + ': detail introduces no signoff claim')
            if domain == 'timing':
                terminal.key(b'j' * 1000)
                bottom = terminal.capture(domain + '-detail-bottom')
                terminal.key(b'k')
                check(terminal.capture_matching(domain + '-detail-reverse', lambda text: text != bottom,
                                                'first reverse key changes the rendered detail viewport') != bottom,
                      'Timing: bounded detail scroll reverses immediately')
            terminal.key(b'\x1b')
            terminal.count(domain + '-detail-escape', 1, ['filter=' + chosen['id'] + ' ·'],
                           ['Waiting for exact row/digest'])
            terminal.filter(domain + '-detail-filter-cleared', '', chosen['id'], len(rr))
            if domain == 'timing':
                terminal.key(b't')  # signoff -> synthesis: published checkpoint, no STA producer
                terminal.count('timing-synthesis-missing', 0, ['stage synthesis', 'missing relevant retained evidence'])
                terminal.key(b'\x1b')
            else:
                terminal.key(b'\x1b')
        if 'timing' in indexes:
            tile_warm = calls()
            palette('timing')
            terminal.key(b'v')
            mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' % (tiles[0], fs0.sexp(run)))
            terminal.palette('Unzoom workspace')
            terminal.key(b'\t')
            terminal.palette('Zoom focused tile')
            palette('timing')
            terminal.count('independent-second-tile', len(rows(indexes['timing'])), ['near=false'])
            select(None)
            terminal.capture('follow-cleared', ['No run selected'], ['INSPECT timing'])
            terminal.palette('Unzoom workspace')
            terminal.key(b'\t')
            terminal.palette('Zoom focused tile')
            terminal.capture('pin-retains-local-near', ['INSPECT timing', 'near=true'])
            select(run)
            terminal.key(b'\x1b')
            check(calls() == tile_warm, 'Independent tile explorers, pin/context changes and warm reopen are provider-free')
        if not args.skip_binary:
            binary(args, session, terminal, run, operation, check, calls)
        warm = calls()
        final_ws = session.rpc('workspace')
        terminal.close()
        terminal = None
        instance = session.metadata['instance_id']
        session.stop()
        session.env['TMPDIR'] = str(args.evidence / 'daemon-tmp')
        session.start()
        check(session.metadata['instance_id'] != instance and session.rpc('workspace') == final_ws,
              'Private daemon restart preserves layout, pins and context')
        for domain, original in indexes.items():
            restored = inspect(domain)
            check(field(restored, 'cached_unverified') == 'true'
                  and [(k, v) for k, v in restored if k != 'cached_unverified'] ==
                      [(k, v) for k, v in original if k != 'cached_unverified'],
                  domain + ': L2 cached_unverified preserves complete original index')
        session.env['TMPDIR'] = str(args.evidence / 'client-tmp')
        terminal = Terminal(session)
        terminal.palette('Switch to FS1 Investigation')
        for domain in args.domains:
            palette(domain)
            terminal.capture('restarted-' + domain, ['CACHED UNVERIFIED'])
            terminal.filter('restarted-filter-' + domain, 'NO_RESTART_MATCH', '', 0)
            terminal.count('restarted-filter-cached-' + domain, 0, ['CACHED UNVERIFIED'])
            terminal.key(b'\x1b')
        check(calls() == warm, 'Restart, index reopen, filtering and PTY make no provider invocations')
        snap = session.rpc('asic')
        check(len(field(snap, 'runs')) == 1 and field(field(snap, 'runs')[0], 'reference') == reference,
              'Original registered allocation remains exact')
        check(all(json.loads(line)['allowed'] for line in calls().splitlines()), 'Every provider invocation satisfies read-only exact-reference policy')
        metrics.no_generic_jobs(session, 'finished FS1 investigation')
        outcome.update(status='passed', run=run, provider_calls=len(calls().splitlines()), domains=args.domains)
    except BaseException:
        outcome['error'] = traceback.format_exc()
        raise
    finally:
        try:
            if terminal:
                terminal.close()
        finally:
            if session and session.process:
                session.stop()
            after = dashboard.inventory(watched)
            save(args.evidence / 'files-after.json', after)
            outcome['input_files_unchanged'] = before == after
            if before != after:
                outcome['status'] = 'failed'
            save(args.evidence / 'result.json', outcome)
            require(before == after, 'Original state/results/config/provider changed; inspect inventories')


def binary(args, session, terminal, run, operation, check, calls):
    attempt = str(Path(operation['results']['path']).parent)
    session.rpc('asic', '(Inspect_finalization (run %s) (attempt %s))' % (fs0.sexp(run), fs0.sexp(attempt)), wait=True)
    warm = calls()
    snap = session.rpc('asic', '(List_artifacts %s)' % fs0.sexp(run), wait=True)
    catalog = field(snap, 'artifacts')
    save(args.evidence / 'artifact-catalog.json', [record(a) for a in catalog])
    index, chosen = next((i, a) for i, a in enumerate(catalog) if field(a, 'path').endswith('.gds'))
    source = Path(field(chosen, 'path'))
    check(field(chosen, 'run') == run and field(chosen, 'terminal_attempt') == attempt
          and field(chosen, 'sha256') == sha256(source) == GDS_SHA
          and int(field(chosen, 'size')) == source.stat().st_size == 4751922,
          'Accepted List_artifacts exposes exact real GDS reference, 4751922 bytes and known SHA256')
    terminal.palette('Browse reports/artifacts asic/' + field(run, 'id'))
    terminal.capture('binary-catalog', ['REPORTS / ARTIFACTS', 'b: export exact physical binary'])
    for _ in range(index):
        terminal.key(b'\x1b[B')
    terminal.key(b'\r')
    terminal.capture('binary-reference', ['SHA256: ' + GDS_SHA])
    terminal.key(b'b')
    result_file = args.evidence / 'binary-viewer.json'
    deadline = min(session.deadline, time.monotonic() + 125)
    while not result_file.exists():
        screen = terminal.drain(.2)
        require(time.monotonic() < deadline, 'Binary PTY export timed out:\n' + screen)
    result = load(result_file)
    exported = Path(result['local_path'])
    check(result['argv'] == [str(args.evidence / 'record-binary-viewer'), str(exported)]
          and exported.is_absolute() and exported.is_relative_to(args.evidence / 'client-tmp')
          and exported.name == 'artifact.gds' and exported.resolve() == exported and not exported.is_symlink()
          and exported != source, 'Actual b invokes recording viewer with only private terminal-host GDS path')
    check(exported.read_bytes() == source.read_bytes() and sha256(exported) == result['sha256'] == GDS_SHA
          and result['size'] == source.stat().st_size, 'Complete binary export is bit-exact to retained source')
    metadata_path = exported.parent / 'metadata.sexp'
    meta = metrics.parse(metadata_path.read_text())
    check(meta[0] == 'terminal-host-exact-binary-export' and field(meta[1:], 'original_reference') == chosen
          and field(meta[1:], 'verified_sha256') == GDS_SHA, 'Binary export metadata retains exact original reference and verified hash')
    check(result['mode'] == stat.S_IMODE(exported.stat().st_mode) == 0o600
          and result['directory_mode'] == stat.S_IMODE(exported.parent.stat().st_mode) == 0o700
          and stat.S_IMODE(metadata_path.stat().st_mode) == 0o600, 'Binary file/metadata 0600; directory 0700')
    check(len((args.evidence / 'binary-viewer-calls.jsonl').read_text().splitlines()) == 1
          and calls() == warm, 'One explicit binary viewer launch; all artifact reads/export provider-free')
    fixture = args.evidence / 'read-exported-gds.py'
    fixture.write_text('import json, pya\nlayout = pya.Layout()\nlayout.read(' + repr(str(exported)) + ')\n' +
                       'tops = [{"name": c.name, "bbox": str(c.bbox())} for c in layout.top_cells()]\n' +
                       'assert tops and all(not c.bbox().empty() for c in layout.top_cells())\n' +
                       'open(' + repr(str(args.evidence / 'klayout-layout.json')) + ', "w").write(json.dumps({"dbu": layout.dbu, "top_cells": tops}))\n')
    env = dict(session.env, QT_QPA_PLATFORM='offscreen')
    env.pop('DISPLAY', None)
    env.pop('WAYLAND_DISPLAY', None)
    argv = [str(args.klayout), '-b', '-r', str(fixture)]
    start = time.monotonic()
    p = subprocess.run(argv, env=env, capture_output=True, timeout=min(90, session.deadline - start))
    (args.evidence / 'klayout.stdout').write_bytes(p.stdout)
    (args.evidence / 'klayout.stderr').write_bytes(p.stderr)
    save(args.evidence / 'klayout-command.json', dict(argv=argv, returncode=p.returncode, seconds=time.monotonic() - start))
    check(p.returncode == 0, 'Actual headless KLayout loads exported GDS; see retained stdout/stderr')
    layout = load(args.evidence / 'klayout-layout.json')
    check(any(c['name'] == 'tt_um_controlled_fifo' for c in layout['top_cells']), 'Actual GDS top cell and nonempty bbox recorded')
    save(args.evidence / 'binary-result.json', dict(export=result, layout=layout, metadata=meta,
         interpretation='Read-only layout loading, not signoff or a new physical flow',
         png_catalog=[record(a) for a in catalog if field(a, 'path').lower().endswith('.png')]))
    terminal.key(b'\x1b')
    terminal.key(b'\x1b')
    check(calls() == warm, 'KLayout read and closing viewer do not invoke provider')


def main():
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=Path('/tmp/opencode/workbench-fs1-physical-w0rftdi0/workbench-inputs.json'))
    parser.add_argument('--operation', type=Path, default=Path('/tmp/opencode/workbench-fs1-acceptance-5oa67d8u/operation.json'))
    parser.add_argument('--provider', type=Path, default=Path('/tmp/opencode/workbench-fs1-inspection-provider/current/bin/hardcaml-asic-flow'))
    parser.add_argument('--klayout', type=Path, default=Path('/nix/store/nn9dc4rwi8qxpgnbi13dg18hln7x50pn-klayout-0.30.4-1/bin/klayout'))
    parser.add_argument('--source-state', type=Path, default=Path('/tmp/opencode/workbench-fs0-91em64rl/real/state'))
    parser.add_argument('--example-root', type=Path, default=repo.parent / 'hardcaml_asic_example')
    parser.add_argument('--client', type=Path, default=repo / '_build/default/terminal/main.exe')
    parser.add_argument('--daemon', type=Path, default=repo / '_build/default/daemon/main.exe')
    parser.add_argument('--domain', choices=['all'] + list(DEFAULTS), default='all')
    parser.add_argument('--skip-binary', action='store_true')
    parser.add_argument('--budget', type=int, default=600)
    parser.add_argument('--outer-timeout', type=int, default=90)
    args = parser.parse_args()
    require(60 <= args.budget <= 600 and 1 <= args.outer_timeout <= 90, 'Budget 60..600 seconds, per-query timeout 1..90')
    for key in ('inputs', 'operation', 'provider', 'source_state', 'example_root', 'client', 'daemon'):
        setattr(args, key, getattr(args, key).resolve(strict=True))
    args.klayout = args.klayout.resolve(strict=not args.skip_binary)
    for path in (args.provider, args.client, args.daemon) + (() if args.skip_binary else (args.klayout,)):
        require(path.is_file() and os.access(path, os.X_OK), 'Existing executable required: ' + str(path))
    os.umask(0o077)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:20])
    args.domains = list(DEFAULTS) if args.domain == 'all' else [args.domain]
    args.evidence = Path(tempfile.mkdtemp(prefix='workbench-fs1-investigation-', dir='/tmp/opencode'))
    args.deadline = time.monotonic() + args.budget
    save(args.evidence / 'commands.json', dict(argv=sys.argv, options={k: str(v) for k, v in vars(args).items()},
         affinity=sorted(os.sched_getaffinity(0)), pty=dict(width=120, height=40)))
    print('Evidence: ' + str(args.evidence), flush=True)

    def interrupted(signum, _frame):
        raise KeyboardInterrupt('FS1 investigation interrupted/budget exhausted: %s' % signum)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
        signal.signal(sig, interrupted)
    signal.alarm(args.budget)
    try:
        exercise(args)
    finally:
        signal.alarm(0)
    print('PASS: retained-real FS1 investigation / PTY / cache / binary', flush=True)


if __name__ == '__main__':
    main()
