#!/usr/bin/env python3
"""Parent-run FS1 Finalize/artifact lifecycle acceptance using existing binaries.

Default: collect the retained physical execution. --accept: external acceptance.
--cancel: external acceptance, cancelled at real postcheck/transport progress.
Run modes serially. No physical implementation, build, Git, install or download.
Every mode has an inclusive 1800-second budget and retains private evidence,
including assertion-failure screens, under /tmp/opencode.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import traceback

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location(
    'terminal_results', Path(__file__).with_name('test-fs1-terminal-results.py'))
terminal_results = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terminal_results)
metrics, fs0, dashboard = terminal_results.metrics, terminal_results.fs0, terminal_results.dashboard
field, record, require = fs0.field, fs0.record, fs0.require
load, sha256 = terminal_results.load, terminal_results.sha256


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def processes():
    result = {}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            s = (p / 'stat').read_text().rsplit(')', 1)[1].split()
            result[int(p.name)] = dict(pid=int(p.name), state=s[0], ppid=int(s[1]),
                                       start=s[19], argv=(p / 'cmdline').read_bytes().decode(
                                           errors='replace').rstrip('\0').split('\0'))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return result


def alive(identity, table):
    p = table.get(identity['pid'])
    return p is not None and p['start'] == identity['start'] and p['state'] != 'Z'


class Tracker:
    """Retain PID/start identities even when a producer reparents its children."""
    def __init__(self, session):
        self.session, self.seen = session, {}
        self.done = threading.Event()
        self.thread = threading.Thread(target=self.watch, daemon=True)
        self.thread.start()

    def sample(self):
        table = processes()
        roots = {self.session.process.pid}
        roots.update(p['pid'] for p in list(self.seen.values()) if alive(p, table))
        selected = set(roots)
        while True:
            children = {pid for pid, p in table.items() if p['ppid'] in selected}
            if children <= selected:
                break
            selected.update(children)
        for pid in selected - {self.session.process.pid}:
            if pid in table:
                p = table[pid]
                self.seen[(pid, p['start'])] = p
        return table

    def watch(self):
        while not self.done.wait(.05):
            self.sample()

    def close(self):
        self.done.set()
        self.thread.join(timeout=2)
        save(self.session.evidence / 'descendants.json', list(self.seen.values()))


class Session(terminal_results.Session):
    def command(self, extra, label, timeout=90, success=True):
        remaining = self.deadline - time.monotonic()
        require(remaining > 0, 'Lifecycle work budget exhausted')
        return super().command(extra, label, timeout=min(timeout, remaining), success=success)


class Terminal(metrics.Terminal):
    def __init__(self, session):
        # Only interactive clients get the fixture flag. Keep plain RPC invocation
        # and the real client binary recorded in args unchanged.
        original = session.args
        session.args = argparse.Namespace(**vars(original))
        session.args.client = session.viewer_client
        try:
            super().__init__(session)
        finally:
            session.args = original

    def capture(self, label, expected=(), absent=()):
        # Viewer strings are contractual, including case and offsets.
        deadline = min(self.session.deadline, time.monotonic() + 12)
        while True:
            text = self.drain(.2)
            if all(s in text for s in expected) and all(s not in text for s in absent):
                self.save(label, text)
                return text
            if time.monotonic() >= deadline:
                self.save(label, text)
                raise AssertionError('%s: expected %r, absent %r\n%s' % (label, expected, absent, text))

    def close(self):
        self.save('pty-final-' + str(time.time_ns()), fs0.terminal_screen(
            bytes(self.data), width=120, height=self.height))
        super().close()


def acceptance_inputs(args):
    request = load(args.acceptance_evidence / 'operation.json')['request']
    values = {k: request[k] for k in (
        'support_tools', 'precheck_python', 'testbench', 'testbench_top', 'replay_trace')}
    require(values['replay_trace'] == str(args.acceptance_evidence / 'trace-export.stdout'),
            'Acceptance replay must be the retained real exported trace')
    for key, value in values.items():
        require(isinstance(value, str) and value, 'Missing acceptance input: ' + key)
        if key != 'testbench_top':
            require(Path(value).is_absolute() and Path(value).exists(), 'Missing real collateral: ' + value)
    wrapper = args.acceptance_evidence / 'bin/nix-shell'
    # Inspect (never execute) the retained wrapper before admitting it to PATH.
    text = wrapper.read_text()
    tree = ast.parse(text)
    assignments = {n.targets[0].id: n.value for n in tree.body if isinstance(n, ast.Assign)
                   and isinstance(n.targets[0], ast.Name)}
    argv_node = assignments.get('argv')
    require(isinstance(argv_node, ast.BinOp) and isinstance(argv_node.left, ast.BinOp),
            'Cached Nix wrapper shape changed; inspect before acceptance')
    argv = ast.literal_eval(argv_node.left.left)
    expected_options = {'max-jobs': '0', 'builders': '', 'substitute': 'false',
                        'substituters': '', 'restrict-eval': 'true', 'allowed-uris': '',
                        'allow-import-from-derivation': 'false'}
    require(argv[0] == '/usr/bin/nix-shell' and Path(argv[0]).is_file()
            and os.access(wrapper, os.X_OK), 'Cached Nix wrapper/executable missing')
    actual_options = {argv[i + 1]: argv[i + 2] for i, v in enumerate(argv) if v == '--option'}
    require(actual_options == expected_options, 'Cached Nix wrapper must forbid builds/downloads')
    source = next(v.split('=', 1)[1] for v in argv if v.startswith('nixpkgs=/nix/store/'))
    require((Path(source) / 'default.nix').is_file(), 'Retained cached nixpkgs is no longer available')
    require('os.execv(argv[0], argv)' in text and 'sys.argv[1:]' in text,
            'Cached Nix wrapper must forward the real precheck command')
    save(args.evidence / 'acceptance-inputs.json', dict(inputs=values, wrapper=str(wrapper),
         wrapper_sha256=sha256(wrapper), cached_nixpkgs=source, options=actual_options))
    return values


def prepare(args, receipt, inputs, acceptance):
    root = args.evidence / 'project'
    root.mkdir()
    (args.evidence / 'state').mkdir()
    results = args.evidence / 'results'
    results.mkdir()
    store = results / 'finalizations'
    store.mkdir()
    (root / 'dune-project').write_text('(lang dune 3.17)\n(name fs1_lifecycle_acceptance)\n')
    cfg = metrics.parse((args.example_root / 'hardcaml-workbench-asic.sexp').read_text())
    provider = receipt['config']['provider']
    require(Path(provider).is_absolute() and Path(provider).is_file(), 'Exact adopted provider unavailable')
    allocation, execution = inputs['allocation'], inputs['execution_file']
    producer = ['finalize', execution, '--operation-store', str(store), '--json']
    if acceptance is not None:
        producer += ['--accept']
        for key, value in acceptance.items():
            producer += ['--' + key.replace('_', '-'), value]
    relay = args.evidence / 'provider-relay'
    # exec preserves the real producer's early streamed allocation and signal/process
    # group semantics. The installed provider and all original execution bytes stay exact.
    relay.write_text('#!' + sys.executable + '\n' + '''import fcntl, json, os, pathlib, sys, time
base = pathlib.Path(BASE)
a = sys.argv[1:]
allocation = ALLOCATION
execution = EXECUTION
store = pathlib.Path(STORE)
producer = PRODUCER
ok = a == ["--version", "--json"] or a == ["report", execution, "--json"]
ok = ok or a == ["observation", "inspect", allocation["attempt"], "--json"]
ok = ok or (len(a) == 8 and a[:3] == ["observation", "read-updates", allocation["attempt"]]
    and a[3:6] == ["--stream-id", allocation["stream_id"], "--after"]
    and a[6].isdigit() and a[7:] == ["--json"])
if len(a) == 3 and a[0] == "finalization-inspect" and a[2] == "--json":
    p = pathlib.Path(a[1])
    try:
        j = json.loads((p / "operation.json").read_text())
        ok = (p.is_absolute() and p.parent == store and p.resolve() == p
              and j["request"]["execution"] == execution
              and j["contract"] == "hardcaml-asic.segment-finalization")
    except (OSError, ValueError, KeyError):
        ok = False
with (base / "provider-calls.jsonl").open("a+") as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    f.seek(0)
    previous = [json.loads(line) for line in f]
    if a == producer:
        ok = not any(c["argv"][0] == "finalize" and c["allowed"] for c in previous)
    f.seek(0, 2)
    f.write(json.dumps(dict(argv=a, allowed=ok, pid=os.getpid(), time=time.time(),
                           path=os.environ.get("PATH"))) + "\\n")
    f.flush()
if not ok:
    sys.exit("FS1 lifecycle relay rejected non-allowlisted or duplicate command")
os.execv(PROVIDER, [PROVIDER] + a)
'''.replace('BASE', repr(str(args.evidence))).replace('ALLOCATION', repr(allocation))
        .replace('EXECUTION', repr(execution)).replace('STORE', repr(str(store)))
        .replace('PRODUCER', repr(producer)).replace('PROVIDER', repr(provider)))
    relay.chmod(0o700)
    deny = args.evidence / 'no-project-execution'
    deny.write_text('#!' + sys.executable + '\nimport sys\nsys.exit("No physical/project execution in lifecycle acceptance")\n')
    deny.chmod(0o700)
    for key, value in (('provider_executable', str(relay)), ('project_executable', str(deny)),
                       ('results_root', str(results))):
        cfg = metrics.put(cfg, key, value)
    (root / 'hardcaml-workbench-asic.sexp').write_text(fs0.sexp(cfg) + '\n')
    save(args.evidence / 'relay-policy.json', dict(provider=provider, sha256=sha256(provider), producer=producer))
    return root, store


def sanitized(text):
    return ''.join(c for c in text if (ord(c) in (9, 10) or ord(c) >= 32)
                   and not (127 <= ord(c) <= 159 or 0x202a <= ord(c) <= 0x202e
                            or 0x2066 <= ord(c) <= 0x2069))


def prepare_viewer(session):
    """A real executable observer, never a user's desktop application."""
    tmp = session.evidence / 'client-tmp'
    tmp.mkdir(mode=0o700)
    session.env['TMPDIR'] = str(tmp)
    viewer = session.evidence / 'fixture-artifact-viewer'
    viewer.write_text('#!' + sys.executable + '\n' + '''import hashlib, json, os, pathlib, stat, sys
base = pathlib.Path(BASE)
assert len(sys.argv) == 2, "viewer requires exactly one local text path"
p = pathlib.Path(sys.argv[1])
raw = p.read_bytes()
text = raw.decode("utf-8")
result = dict(argv=sys.argv, local_path=str(p), mode=stat.S_IMODE(p.stat().st_mode),
              directory_mode=stat.S_IMODE(p.parent.stat().st_mode),
              sha256=hashlib.sha256(raw).hexdigest(), text_length=len(text),
              byte_length=len(raw), pid=os.getpid())
with (base / "viewer-invocations.jsonl").open("a") as f:
    f.write(json.dumps(result) + "\\n")
temporary = base / ("viewer-" + str(os.getpid()) + ".tmp")
temporary.write_text(json.dumps(result, indent=2) + "\\n")
os.replace(temporary, base / "viewer.json")
'''.replace('BASE', repr(str(session.evidence))))
    viewer.chmod(0o700)
    wrapper = session.evidence / 'viewer-enabled-client'
    wrapper.write_text('#!' + sys.executable + '\nimport os, sys\n' +
                       'os.execv(' + repr(str(session.args.client)) + ', [' +
                       repr(str(session.args.client)) + ', "--artifact-viewer", ' +
                       repr(str(viewer)) + '] + sys.argv[1:])\n')
    wrapper.chmod(0o700)
    session.viewer_client = wrapper
    save(session.evidence / 'viewer-config.json', dict(executable=str(viewer),
         client=str(session.args.client), wrapper=str(wrapper), tmpdir=str(tmp)))


def export_text(session, terminal, chosen, check, calls):
    evidence = session.evidence
    result_path = evidence / 'viewer.json'
    invocations = evidence / 'viewer-invocations.jsonl'
    check(not result_path.exists() and not invocations.exists(), 'Viewer has not run before explicit x')
    before = calls()
    producer_count = sum(json.loads(line)['argv'][0] == 'finalize' for line in before.splitlines())
    terminal.key(b'x')
    deadline = min(session.deadline, time.monotonic() + 125)
    while not result_path.exists():
        screen = terminal.drain(.2)
        if time.monotonic() >= deadline or 'External text export failed:' in screen:
            terminal.save('artifact-export-failure', screen)
            raise AssertionError('Explicit x did not invoke fixture viewer within export budget:\n' + screen)
    terminal.capture('artifact-export-invoked', ['REPORTS / ARTIFACTS', 'Offset 0'])
    result = load(result_path)
    exported = Path(result['local_path'])
    check(result['argv'] == [str(evidence / 'fixture-artifact-viewer'), str(exported)],
          'Viewer executable receives ONLY the local text path as its argument')
    check(exported.is_absolute() and exported.name == 'artifact.txt'
          and exported.resolve() == exported and not exported.is_symlink()
          and exported.is_relative_to(evidence / 'client-tmp')
          and str(exported) != field(chosen, 'path'),
          'Export is a retained canonical terminal-host file under private client TMPDIR, not daemon path')
    raw = Path(field(chosen, 'path')).read_bytes()
    expected = sanitized(raw.decode('utf-8')).encode('utf-8')
    actual = exported.read_bytes()
    digest = hashlib.sha256(expected).hexdigest()
    check(actual == expected and result['sha256'] == digest == sha256(exported)
          and result['byte_length'] == len(expected)
          and result['text_length'] == len(expected.decode('utf-8')),
          'Export contains complete canonical artifact sanitized UTF-8, with exact hash and lengths')
    metadata_path = exported.parent / 'metadata.sexp'
    metadata = metrics.parse(metadata_path.read_text())
    check(metadata[0] == 'terminal-host-sanitized-text-export', 'Export metadata declares sanitized terminal-host format')
    meta = record(metadata[1:])
    check(meta['original_reference'] == chosen
          and field(meta['original_reference'], 'sha256') == sha256(field(chosen, 'path'))
          and meta['exported_text_sha256'] == digest
          and meta['content'] == 'Sanitized UTF-8 text; not byte-identical provider raw bytes',
          'Metadata preserves exact original reference/hash, exported hash and explicit sanitized-content declaration')
    check(stat.S_IMODE(exported.stat().st_mode) == result['mode'] == 0o600
          and stat.S_IMODE(exported.parent.stat().st_mode) == result['directory_mode'] == 0o700
          and stat.S_IMODE(metadata_path.stat().st_mode) == 0o600,
          'Export artifact/metadata modes are 0600 and private directory mode is 0700')
    check(len(invocations.read_text().splitlines()) == 1, 'Explicit x invokes the fixture viewer exactly once')
    check(calls() == before and sum(json.loads(line)['argv'][0] == 'finalize'
          for line in calls().splitlines()) == producer_count,
          'Explicit x export pages invoke no provider and do not change producer count')
    result.update(status='passed', metadata_path=str(metadata_path), metadata=meta,
                  original_sha256=field(chosen, 'sha256'), sanitized=True,
                  invocations=1, provider_calls_unchanged=True, producer_count=producer_count)
    save(evidence / 'artifact-export-result.json', result)
    return result


def artifacts(session, terminal, run, attempt, check, calls):
    warm = calls()
    response = session.command(['--api', '--asic-operation', '(List_artifacts %s)' % fs0.sexp(run),
                                '--wait', '--wait-timeout-seconds', str(session.args.outer_timeout)],
                               'list-real-artifacts', success=False)
    parsed = metrics.parse(response.stdout.decode())
    check(parsed[0] == 'Ok', 'Backend List_artifacts returned a typed snapshot: ' + repr(parsed))
    snap = parsed[1]
    failed = [record(o) for o in field(snap, 'operations')
              if field(o, 'kind') == 'artifacts' and field(o, 'state') == 'failed']
    check(not failed, 'Backend List_artifacts must accept actual retained files (including size limits): ' + repr(failed))
    check(response.returncode == 0, 'Backend List_artifacts completed successfully; see list-real-artifacts evidence')
    catalog = field(snap, 'artifacts')
    check(bool(catalog) and len(catalog) <= 32, 'Real nonempty bounded artifact catalog')
    save(session.evidence / 'artifact-catalog.json', [record(a) for a in catalog])
    for a in catalog:
        check(field(a, 'run') == run and field(a, 'terminal_attempt') == attempt,
              'Artifact reference is bound to exact run and finalization')
        path = Path(field(a, 'path'))
        check(path.is_file() and int(field(a, 'size')) == path.stat().st_size
              and field(a, 'sha256') == sha256(path), 'Exact real artifact size/SHA256: ' + str(path))

    def page(a, offset):
        snap = session.rpc('asic', '(Read_artifact (run %s) (artifact_id %s) (offset %d) (limit 4096))' % (
            fs0.sexp(run), fs0.sexp(field(a, 'id')), offset), wait=True)
        matches = [p for p in field(snap, 'artifact_pages') if field(p, 'run') == run
                   and field(p, 'artifact_id') == field(a, 'id') and int(field(p, 'offset')) == offset
                   and int(field(p, 'limit')) == 4096]
        check(bool(matches), 'Typed exact-offset artifact page returned')
        p = matches[0]
        check(field(p, 'sha256') == field(a, 'sha256') and field(p, 'terminal_attempt') == attempt
              and int(field(p, 'limit')) == 4096,
              'Reader page pins exact hash, attempt and limit4096')
        raw = Path(field(a, 'path')).read_bytes()
        if field(a, 'kind') == 'binary':
            check(bool(field(p, 'error')) and field(p, 'text') == ''
                  and int(field(p, 'next_offset')) == offset and field(p, 'eof') == 'false',
                  'Binary artifacts return metadata/error without decoded text')
        else:
            end = min(offset + 4096, len(raw))
            while end > offset:
                try:
                    text = raw[offset:end].decode('utf-8')
                    break
                except UnicodeDecodeError:
                    end -= 1
            if end == offset:
                text = ''
            check(field(p, 'error') == [] and int(field(p, 'next_offset')) == end
                  and field(p, 'eof') == str(end == len(raw)).lower()
                  and field(p, 'text') == sanitized(text), 'Exact bounded bytes/UTF-8 offset/EOF/text')
        return p

    # First, next and final pages of every text file, plus explicit empty EOF.
    # This covers large real files without making thousands of redundant RPCs.
    for a in catalog:
        first = page(a, 0)
        if field(a, 'kind') == 'text':
            if field(first, 'eof') == 'false':
                page(a, int(field(first, 'next_offset')))
            raw = Path(field(a, 'path')).read_bytes()
            offset = max(0, len(raw) - 4096)
            while offset < len(raw) and raw[offset] & 0xc0 == 0x80:
                offset += 1
            page(a, offset)
            page(a, len(raw))
    # A real multipage text entry is essential for n/p history coverage.
    index, chosen = next((i, a) for i, a in enumerate(catalog)
                         if field(a, 'kind') == 'text' and int(field(a, 'size')) > 4096)
    first = page(chosen, 0)
    next_offset = int(field(first, 'next_offset'))
    second = page(chosen, next_offset)
    terminal.palette('Browse reports/artifacts asic/' + field(run, 'id'))
    terminal.capture('artifacts-catalog', ['REPORTS / ARTIFACTS', 'Enter: read', 'Esc: close'])
    for _ in range(index):
        terminal.key(b'\x1b[B')
    terminal.key(b'\r')
    terminal.capture('artifacts-enter', ['Daemon-host path:', 'SHA256: ' + field(chosen, 'sha256'),
        'Offset 0', 'next %d' % next_offset, 'x: export sanitized text', 'n/p: page', 'Esc: back'])
    terminal.key(b'n')
    terminal.capture('artifacts-next', ['Offset %d' % next_offset,
        'next %s' % field(second, 'next_offset'), 'EOF ' + field(second, 'eof')])
    terminal.key(b'p')
    terminal.capture('artifacts-previous', ['Offset 0', 'next %d' % next_offset])
    exported = export_text(session, terminal, chosen, check, calls)
    terminal.key(b'\x1b')
    terminal.capture('artifacts-back-catalog', ['Enter: read', 'Esc: close'], ['Daemon-host path:'])
    binary = next(((i, a) for i, a in enumerate(catalog) if field(a, 'kind') == 'binary'), None)
    if binary is not None:
        binary_index, binary_reference = binary
        for _ in range(abs(binary_index - index)):
            terminal.key(b'\x1b[B' if binary_index > index else b'\x1b[A')
        terminal.key(b'\r')
        terminal.capture('artifacts-binary-export-unavailable', ['Daemon-host path:',
            'SHA256: ' + field(binary_reference, 'sha256'), 'x: unavailable (non-text/over 16 MiB)'])
        terminal.key(b'x')
        terminal.capture('artifacts-binary-x-rejected', ['External text view unavailable for binary/non-text artifacts'])
        check(len((session.evidence / 'viewer-invocations.jsonl').read_text().splitlines()) == 1,
              'Binary x is unavailable and cannot invoke the external viewer')
        terminal.key(b'\x1b')
        terminal.capture('artifacts-binary-back', ['Enter: read', 'Esc: close'])
        exported['binary_export_unavailable'] = True
    terminal.key(b'\x1b')
    terminal.capture('artifacts-close', absent=['REPORTS / ARTIFACTS'])
    check(calls() == warm, 'All catalog/page/PTY reads are provider-free: no EDA or warm-page launches')
    check(len((session.evidence / 'viewer-invocations.jsonl').read_text().splitlines()) == 1,
          'Paging/back/close do not relaunch external viewer')
    save(session.evidence / 'artifact-export-result.json', exported)
    return exported


def exercise(args):
    inputs = load(args.inputs)
    receipt_path = Path(inputs['physical_receipt'])
    receipt = load(receipt_path)
    require(inputs['allocation'] == receipt['allocation']
            and inputs['execution_file'] == receipt['execution_file'], 'Original allocation/execution mismatch')
    require(load(inputs['execution_file'])['status'] == 'completed', 'Retained completed execution required')
    acceptance = acceptance_inputs(args) if args.accept or args.cancel else None
    watched = [args.inputs.parent, receipt_path.parent, Path(receipt['config']['results_root']),
               Path(receipt['config']['provider']).parent.parent,
               args.example_root / 'hardcaml-workbench-asic.sexp', args.acceptance_evidence]
    if acceptance:
        watched += [Path(acceptance[k]) for k in ('support_tools', 'precheck_python', 'testbench', 'replay_trace')]
    before = dashboard.inventory(watched)
    save(args.evidence / 'files-before.json', before)
    outcome = dict(status='failed', mode='cancel' if args.cancel else 'accept' if args.accept else 'collect', checks=[])
    session = terminal = tracker = None
    original_containers = None
    owned_key = None

    def check(ok, message):
        outcome['checks'].append(dict(passed=bool(ok), expectation=message))
        require(ok, message)

    def calls():
        p = args.evidence / 'provider-calls.jsonl'
        return p.read_bytes() if p.exists() else b''

    def producer_count():
        return sum(json.loads(line)['argv'][0] == 'finalize' for line in calls().splitlines())

    def container_inventory(label):
        docker = shutil.which('docker', path=session.env.get('PATH'))
        check(bool(docker), 'Existing Docker required to verify real transport cleanup')
        p = subprocess.run([docker, 'ps', '--no-trunc', '--format', '{{json .}}'],
                           env=session.env, capture_output=True,
                           timeout=min(10, max(.1, session.deadline - time.monotonic())))
        (args.evidence / (label + '.stdout')).write_bytes(p.stdout)
        (args.evidence / (label + '.stderr')).write_bytes(p.stderr)
        check(p.returncode == 0, 'Read-only Docker inventory succeeds: ' + label)
        return {j['ID']: j['Names'] for j in (json.loads(line) for line in p.stdout.splitlines())}

    def retry(operation, label, wait=False):
        # Plain mode can return Ok(snapshot) with nonzero exit for a failed or
        # restarted/detached task. Keep that outcome separate from RPC rejection.
        extra = ['--api', '--asic-operation', operation]
        if wait:
            extra += ['--wait', '--wait-timeout-seconds', str(args.outer_timeout)]
        response = session.command(extra, label, success=False)
        parsed = metrics.parse(response.stdout.decode())
        check(parsed[0] == 'Ok', label + ': request accepted independently of operation outcome')
        return parsed[1]

    def finalization(snap):
        values = field(snap, 'finalizations')
        check(len(values) == 1, 'Exactly one typed finalization reservation')
        return values[0]

    def poll(predicate, label):
        while True:
            require(time.monotonic() < session.deadline, label + ': mode budget exhausted')
            snap = session.rpc('asic')
            if not field(snap, 'finalizations'):
                time.sleep(.2)
                continue
            f = finalization(snap)
            with (args.evidence / 'finalization-polls.jsonl').open('a') as out:
                out.write(json.dumps(dict(time=time.time(), value=record(f),
                                         operations=field(snap, 'operations'))) + '\n')
            if predicate(f, snap):
                return f, snap
            time.sleep(.2)

    try:
        root, store = prepare(args, receipt, inputs, acceptance)
        session = Session(args, args.evidence, root)
        session.deadline = args.deadline - 35  # cleanup/inventory reserve inside total budget
        prepare_viewer(session)
        if acceptance:
            session.env['PATH'] = str(args.acceptance_evidence / 'bin') + os.pathsep + session.env.get('PATH', '')
        metrics.guard_generic_builds(session)
        session.start()
        tracker = Tracker(session)
        original_containers = container_inventory('containers-before')
        check(field(session.rpc('asic'), 'runs') == [], 'Private daemon has no preexisting allocation')
        ref = [[k, inputs['allocation'][k]] for k in ('attempt', 'stream_id')]
        snap = session.rpc('asic', '(Register %s)' % fs0.sexp(ref), wait=True)
        check(len(field(snap, 'runs')) == 1 and field(field(snap, 'runs')[0], 'reference') == ref,
              'Register adopts exact original public allocation')
        run = field(field(snap, 'runs')[0], 'run')
        snap = session.rpc('asic', '(Load_summary %s)' % fs0.sexp(run), wait=True)
        summary = next(s for s in field(snap, 'summaries') if field(s, 'run') == run)
        check(field(summary, 'execution_file') == inputs['execution_file'] and field(summary, 'completion') == 'completed'
              and field(summary, 'terminal') == [], 'Load original completed stage summary before Finalize')
        ws = session.rpc('workspace')
        ws = session.mutate(ws, '(Create_workspace (window %s) (name "FS1 Lifecycle Private") (context %s))' % (
            field(field(ws, 'windows')[0], 'id'), field(ws, 'main_context')))
        workspace = field(ws, 'workspaces')[-1]
        ws = session.mutate(ws, '(Create_tile (workspace %s) (kind finalization) (geometry ((x 0) (y 0) (width 110) (height 34))))' % field(workspace, 'id'))
        tile = field(field(ws, 'tiles')[-1], 'id')
        context = next(c for c in field(ws, 'contexts') if field(c, 'id') == field(workspace, 'context'))
        ws = session.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' % (
            field(workspace, 'id'), field(context, 'id'), field(context, 'selection_revision'), fs0.sexp(run)))
        session.mutate(ws, '(Set_zoom (workspace %s) (tile (%s)))' % (field(workspace, 'id'), tile))
        terminal = Terminal(session)
        terminal.palette('Switch to FS1 Lifecycle Private')
        check(producer_count() == 0, 'Summary/layout/selection launch no producer')
        if acceptance:
            terminal.palette('Finalize and accept asic/' + field(run, 'id'))
            terminal.capture('acceptance-form', ['FINALIZE AND ACCEPT', 'All five values are explicit strings'])
            terminal.key(b'\x1b[200~' + fs0.sexp([[k, v] for k, v in acceptance.items()]).encode() + b'\x1b[201~')
            terminal.capture('acceptance-collateral', ['FINALIZE AND ACCEPT', 'replay_trace'])
            terminal.key(b'\r')
        else:
            terminal.palette('Finalize (collect) asic/' + field(run, 'id'))
        f, snap = poll(lambda f, _: bool(field(f, 'attempt')), 'early streamed allocation')
        attempt, key = field(f, 'attempt')[0], field(f, 'key')
        owned_key = key
        check(Path(attempt).parent == store and field(f, 'owned') == 'true'
              and field(f, 'operation_status') in ([], ['running']), 'Early allocation delivered while daemon owns live producer')
        check(producer_count() == 1, 'Actual palette submission launched exactly one producer')
        terminal.capture('early-allocation')
        terminal.close()
        terminal = None
        # Identical retries are genuine API submissions, never palette commands with new keys.
        request = '(Finalize (key %s) (run %s) (execution_file %s) (acceptance %s))' % (
            fs0.sexp(key), fs0.sexp(run), fs0.sexp(inputs['execution_file']),
            fs0.sexp([] if acceptance is None else [[[k, v] for k, v in acceptance.items()]]))
        retry(request, 'same-key-in-flight')
        bad = request.replace('(execution_file ' + fs0.sexp(inputs['execution_file']) + ')',
                              '(execution_file ' + fs0.sexp(str(args.evidence / 'different-execution.json')) + ')')
        response = session.command(['--api', '--asic-operation', bad], 'mismatched-key', success=False)
        parsed = metrics.parse(response.stdout.decode())
        check(parsed[0] == 'Error' and 'different inputs' in response.stdout.decode(),
              'Same key with mismatched exact inputs is rejected explicitly')
        if args.cancel:
            def progressed(f, _):
                # Real provider phase, never a timer or a fabricated pause.
                return field(f, 'phase') == ['external_postcheck'] and field(f, 'operation_status') == ['running']
            f, snap = poll(progressed, 'actual external postcheck phase')
            save(args.evidence / 'cancel-progress.json', record(f))
            tracker.sample()
            check(field(f, 'owned') == 'true', 'Cancellation targets only this daemon-owned finalization')
            session.rpc('asic', '(Cancel %s)' % fs0.sexp(key))
        f, snap = poll(lambda f, s: field(f, 'owned') == 'false' and
                       any(field(o, 'key') == 'finalize:' + key and field(o, 'state') in ('completed', 'failed', 'cancelled')
                           for o in field(s, 'operations')), 'producer completion after client detach')
        operation = load(Path(attempt) / 'operation.json')
        check(operation['request'] == dict(execution=inputs['execution_file'],
              accept=acceptance is not None, **(acceptance or dict.fromkeys(
                  ('support_tools', 'precheck_python', 'testbench', 'testbench_top', 'replay_trace')))),
              'Receipt preserves every exact requested execution/acceptance input')
        check(operation['execution']['path'] == inputs['execution_file']
              and operation['execution']['sha256'] == sha256(inputs['execution_file']), 'Operation binds exact original execution bytes')
        check(field(f, 'operation_status') == [operation['status']] and field(f, 'phase') == [operation['phase']]
              and field(f, 'acceptance') == [operation['acceptance']], 'Typed phase/status/acceptance match independent receipt facts')
        pending = next(o for o in field(snap, 'operations') if field(o, 'key') == 'finalize:' + key)
        save(args.evidence / 'operation-outcome.json', dict(finalization=record(f), pending=record(pending), receipt=operation))
        if args.cancel:
            check(operation['status'] == 'interrupted' and operation['exit_code'] != 0
                  and operation['acceptance'] != 'pass' and field(pending, 'state') != 'completed',
                  'Cancelled operation has interrupted receipt, separate failed/cancelled task outcome, no acceptance pass')
        else:
            check(operation['status'] == 'completed' and operation['exit_code'] == 0
                  and field(pending, 'state') == 'completed', 'Detached producer finishes and task completes independently')
            check(operation['acceptance'] == ('pass' if args.accept else 'not_evaluated')
                  and operation['external_postcheck'] == ('completed' if args.accept else 'not_evaluated'),
                  'Explicit acceptance verdict versus collect-only not_evaluated')
            normalized = load(operation['results']['path'])
            check(Path(operation['results']['path']).is_relative_to(Path(attempt))
                  and Path(attempt).is_relative_to(store), 'Produced results are confined to private finalization storage')
            check(sha256(operation['results']['path']) == operation['results']['sha256'], 'Actual normalized results SHA256')
            summary = next(s for s in field(snap, 'summaries') if field(s, 'run') == run)
            imported = field(summary, 'terminal')[0]
            check(field(imported, 'attempt') == attempt and field(imported, 'operation_status') == operation['status']
                  and field(imported, 'acceptance') == operation['acceptance']
                  and json.loads(field(imported, 'evidence')) == dict(operation=operation, results=normalized),
                  'Original receipt/results automatically imported after client detachment')
        retry(request, 'same-key-terminal')
        check(producer_count() == 1, 'In-flight and terminal same-key retries produce no duplicate')
        # All producer descendants (including reparented processes) must have exited.
        deadline = min(session.deadline, time.monotonic() + 20)
        while True:
            table = tracker.sample()
            survivors = [p for p in list(tracker.seen.values()) if alive(p, table)]
            if not survivors or time.monotonic() >= deadline:
                break
            time.sleep(.1)
        save(args.evidence / 'survivors.json', survivors)
        check(not survivors, 'No live owned producer/query descendants remain')
        check(container_inventory('containers-after') == original_containers,
              'No producer transport containers remain and original container owners are unchanged')
        metrics.no_generic_jobs(session, 'completed lifecycle')
        terminal = Terminal(session)
        terminal.palette('Switch to FS1 Lifecycle Private')
        if not args.cancel:
            outcome['artifact_export'] = artifacts(session, terminal, run, attempt, check, calls)
        terminal.close()
        terminal = None
        tracker.close()
        tracker = None
        warm = calls()
        old_instance = session.metadata['instance_id']
        session.stop()
        session.start()
        check(session.metadata['instance_id'] != old_instance, 'Private daemon restarted with new identity')
        restored = finalization(session.rpc('asic'))
        check(field(restored, 'key') == key and field(restored, 'attempt') == [attempt]
              and field(restored, 'owned') == 'false', 'Restart retains reference without reacquiring ownership')
        check(calls() == warm, 'Restart never replays producer or queries provider')
        retry(request, 'same-key-restarted')
        check(calls() == warm, 'Persisted same-key retry never replays producer')
        observed = retry('(Observe_finalization %s)' % fs0.sexp(key), 'observe-restarted', wait=True)
        check(field(finalization(observed), 'owned') == 'false' and producer_count() == 1,
              'Observe_finalization remains read-only and cannot reacquire ownership')
        new_calls = [json.loads(line) for line in calls()[len(warm):].splitlines()]
        check(bool(new_calls) and all(c['argv'][0] in ('--version', 'finalization-inspect', 'report') for c in new_calls),
              'Explicit post-restart observation uses only exact-reference reads')
        check(all(json.loads(line)['allowed'] for line in calls().splitlines()), 'Every relay invocation satisfies exact allowlist')
        check(len(field(observed, 'runs')) == 1 and field(field(observed, 'runs')[0], 'reference') == ref,
              'No new physical allocation; original public owner/reference retained')
        metrics.no_generic_jobs(session, 'after restart/observe')
        outcome.update(status='passed', key=key, attempt=attempt, provider_calls=len(calls().splitlines()),
                       producer_count=producer_count(), finalization=record(finalization(observed)))
    except BaseException:
        outcome['error'] = traceback.format_exc()
        if terminal:
            try:
                terminal.save('assertion-failure', fs0.terminal_screen(bytes(terminal.data), width=120, height=terminal.height))
            except BaseException:
                pass
        raise
    finally:
        try:
            if terminal:
                terminal.close()
        finally:
            if session and session.process and session.process.poll() is None and owned_key:
                try:
                    # On assertion failure, ask the private daemon to clean up its
                    # sole producer before stopping it. Never signal public owners.
                    snap = session.rpc('asic')
                    values = field(snap, 'finalizations')
                    if any(field(f, 'key') == owned_key and field(f, 'owned') == 'true' for f in values):
                        session.deadline = min(args.deadline - 5, time.monotonic() + 20)
                        retry('(Cancel %s)' % fs0.sexp(owned_key), 'failure-owned-cancel', wait=True)
                except BaseException:
                    save(args.evidence / 'cleanup-error.json', dict(error=traceback.format_exc()))
            if tracker:
                tracker.close()
            if session and session.process:
                session.stop()
            after = dashboard.inventory(watched)
            save(args.evidence / 'files-after.json', after)
            outcome['input_files_unchanged'] = before == after
            if before != after:
                outcome['status'] = 'failed'
            save(args.evidence / 'result.json', outcome)
            require(before == after, 'Original evidence/config/provider/collateral changed; inspect inventories')


def main():
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--accept', action='store_true')
    mode.add_argument('--cancel', action='store_true')
    parser.add_argument('--inputs', type=Path, default=Path('/tmp/opencode/workbench-fs1-physical-w0rftdi0/workbench-inputs.json'))
    parser.add_argument('--acceptance-evidence', type=Path, default=Path('/tmp/opencode/workbench-fs1-acceptance-5oa67d8u'))
    parser.add_argument('--example-root', type=Path, default=repo.parent / 'hardcaml_asic_example')
    parser.add_argument('--client', type=Path, default=repo / '_build/default/terminal/main.exe')
    parser.add_argument('--daemon', type=Path, default=repo / '_build/default/daemon/main.exe')
    parser.add_argument('--budget', type=int, default=1800)
    parser.add_argument('--outer-timeout', type=int, default=90)
    args = parser.parse_args()
    require(60 <= args.budget <= 1800 and 1 <= args.outer_timeout <= 300, 'Budget 60..1800; query timeout 1..300')
    for key in ('inputs', 'acceptance_evidence', 'example_root', 'client', 'daemon'):
        setattr(args, key, getattr(args, key).resolve())
    require(args.client.is_file() and args.daemon.is_file(), 'Existing binaries required; parent alone builds/runs')
    args.evidence = Path(tempfile.mkdtemp(prefix='workbench-fs1-lifecycle-', dir='/tmp/opencode'))
    args.deadline = time.monotonic() + args.budget
    save(args.evidence / 'commands.json', dict(argv=sys.argv, options={k: str(v) for k, v in vars(args).items()},
                                             pty=dict(width=120, height=40)))
    print('Evidence: ' + str(args.evidence), flush=True)

    def interrupted(signum, _frame):
        raise KeyboardInterrupt('Lifecycle acceptance interrupted: %s' % signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGALRM, interrupted)
    signal.alarm(args.budget)
    try:
        exercise(args)
    except BaseException:
        if not (args.evidence / 'result.json').exists():
            save(args.evidence / 'result.json', dict(status='failed', error=traceback.format_exc()))
        raise
    finally:
        signal.alarm(0)
    print('PASS: private FS1 lifecycle / PTY / artifacts / restart', flush=True)


if __name__ == '__main__':
    main()
