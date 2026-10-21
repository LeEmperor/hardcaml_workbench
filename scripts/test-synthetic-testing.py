#!/usr/bin/env python3
"""Private synthetic FS2 provider + real native HTTP/PTY acceptance; never builds.

No actual EDA, hardware simulator, root fixtures or live demo state are used.
Explicit --daemon/--client/--preset-export select already built native executables.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import termios
import time
import traceback

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parent.parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


flow = module('synthetic_flow_acceptance', REPO / 'scripts/test-synthetic-flow.py')
demo, require, wait_for = flow.demo, flow.require, flow.wait_for
provider = demo.provider
simulation = demo.simulation_provider
Client, field, parse, sexp = flow.Client, flow.field, flow.parse, flow.sexp


def standalone(base):
    """Copied provider runs with stdlib only, empty PYTHONPATH, unrelated cwd."""
    isolated = base / 'isolated'
    isolated.mkdir()
    source = isolated / 'provider'
    shutil.copytree(base / 'project/synthetic-provider', source)
    env = dict(os.environ, PYTHONPATH='', PYTHONNOUSERSITE='1')
    executable = [sys.executable, '-S', str(source / 'simulation_provider.py')]
    result = subprocess.run(executable + ['discover', '--protocol-version', '1'],
                            cwd=isolated, env=env, check=True, capture_output=True, timeout=5)
    require(parse(result.stdout.decode()) == parse(simulation.sexp(simulation.catalog())),
            'standalone copied provider exact bounded catalog')
    outputs = []
    for index in range(2):
        artifacts = isolated / ('artifacts-' + str(index))
        artifacts.mkdir()
        request = isolated / 'request.sexp'
        request.write_text(sexp([('protocol_version', 1), ('attempt_id', 'isolated-check'),
                                 ('selection', simulation.selection(True))]))
        events = isolated / ('events-' + str(index))
        events.touch()
        args = ['run', '--protocol-version', '1', '--request', str(request),
                '--events', str(events), '--artifact-dir', str(artifacts)]
        result = subprocess.run(executable + args, cwd=isolated, env=env,
                                capture_output=True, timeout=5)
        require(result.returncode == 0 and b'SYNTHETIC' in result.stdout and
                b'intentional mismatch' in result.stderr, 'standalone semantic failure exits zero with human logs')
        lines = events.read_text().splitlines()
        decoded = [parse(line) for line in lines]
        require([int(field(e, 'sequence')) for e in decoded] == list(range(len(decoded))),
                'strict contiguous FS2 events')
        require(field(decoded[0], 'payload') == 'Started' and
                field(decoded[-1], 'payload') == ['Finished', 'Failed'], 'strict complete failed stream')
        outputs.append((events.read_bytes(), {p.name: p.read_bytes() for p in artifacts.iterdir()}))
    require(outputs[0] == outputs[1], 'same seed/parameters produce byte-identical events/reports/traces')
    request.write_text(sexp([('protocol_version', 1), ('attempt_id', 'invalid'),
                            ('selection', [('suite', 'undeclared')])]))
    result = subprocess.run(executable + args, cwd=isolated, env=env, capture_output=True, timeout=5)
    require(result.returncode != 0, 'invalid provider inputs are process failure, not semantic failure')
    provider.save(base / 'standalone-verified.json', dict(status='passed', stdlib_only=True,
        artifact_sha256={k: hashlib.sha256(v).hexdigest() for k, v in outputs[0][1].items()}))


def upgrade_checks(base):
    legacy = demo.prepare(base / 'legacy-upgrade', delay=.01)
    root = legacy / 'project'
    sentinel = legacy / 'saved-user-evidence.txt'
    sentinel.write_bytes(b'preserve layouts/state/pins/evidence\x00\xff')
    manifest = provider.load(legacy / 'manifest.json')
    owned = manifest.pop('simulation_install')
    provider.save(legacy / 'manifest.json', manifest)
    for name in owned['sha256']:
        (root / name).unlink()
    demo.install_simulation(legacy)
    require(sentinel.read_bytes().endswith(b'\x00\xff'), 'legacy additive upgrade preserves evidence')
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    config = root / 'hardcaml-workbench-simulation.sexp'
    original = config.read_bytes()
    config.write_text('USER CONFIGURATION - preserve me\n')
    try:
        demo.install_simulation(legacy)
    except RuntimeError as error:
        require('Refusing to overwrite' in str(error) and 'NEW_DIRECTORY' in str(error),
                'config conflict is actionable')
    else:
        raise AssertionError('unrelated configuration overwritten')
    require(config.read_text() == 'USER CONFIGURATION - preserve me\n', 'unrelated config bytes retained')
    config.write_bytes(original)
    copied = root / 'synthetic-provider/simulation_wire.py'
    original = copied.read_bytes()
    copied.write_bytes(b'# user-owned implementation\n')
    try:
        demo.install_simulation(legacy)
    except RuntimeError as error:
        require('Refusing to overwrite' in str(error), 'edited provider conflict explicit')
    else:
        raise AssertionError('edited provider overwritten')
    copied.write_bytes(original)
    require(before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}, 'upgrade preflight preserves other files')
    provider.save(base / 'upgrade-verified.json', dict(status='passed', legacy=str(legacy)))


class Terminal:
    def __init__(self, base, args, client, width=120, height=40):
        self.base, self.width, self.height = base, width, height
        self.data = bytearray()
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
        self.process = subprocess.Popen(demo.switch_command([
            args.client, '--connect', client.url, '--project-root', base / 'project',
            '--environment', 'opam:' + demo.switch_name()]),
            stdin=slave, stdout=slave, stderr=slave, start_new_session=True,
            env=dict(os.environ, TERM='xterm-256color', XDG_STATE_HOME=str(base / 'client-state')))
        os.close(slave)

    def drain(self, seconds=.2):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if select.select([self.master], [], [], .05)[0]:
                try:
                    data = os.read(self.master, 65536)
                except OSError:
                    break
                if data:
                    self.data.extend(data)
        require(self.process.poll() is None, 'native PTY client remains running')
        return flow.fs0_screen.terminal_screen(bytes(self.data), width=self.width, height=self.height)

    def key(self, value):
        os.write(self.master, value)
        self.drain(.15)

    def capture(self, label, expected):
        deadline = time.monotonic() + 12
        while True:
            text = self.drain()
            if all(value.casefold() in text.casefold() for value in expected):
                break
            if time.monotonic() >= deadline:
                self.save(label, text)
                raise AssertionError(label + ': expected ' + repr(expected) + '\n' + text)
        self.save(label, text)
        return text

    def save(self, label, text):
        stem = self.base / ('pty-%dx%d-%s' % (self.width, self.height, label))
        stem.with_suffix('.txt').write_text(text)
        stem.with_suffix('.ansi').write_bytes(self.data)

    def palette(self, title):
        for key in (b' ', b'c', b'c'):
            self.key(key)
        self.key(title.encode())
        self.capture('palette', ['COMMAND PALETTE', title[:35], title[-60:]])
        self.key(b'\r')

    def focus_simulation(self):
        # Commands are intentionally scoped to the focused tile. Discover the
        # simulation focus through the real palette rather than fixed tab counts.
        for _ in range(8):
            for key in (b' ', b'c', b'c'):
                self.key(key)
            self.key(b'Simulation: Discover suites explicitly')
            text = self.drain()
            self.key(b'\x1b')
            if 'No matching commands' not in text and 'Simulation: Discover' in text:
                return
            self.key(b'\t')
        raise AssertionError('Could not focus the native simulation tile')

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)
        os.close(self.master)


def details(client, attempt):
    return field(client.rpc('(Observe %s)' % sexp(attempt), domain='simulation', wait=False), 'detail')[0]


def ensure_legacy_simulation(client, name='Legacy simulation'):
    """An explicit independent legacy/full tile, separate from cooperative Testing.

    Use public mutations only; this must not change any provider/attempt identity.
    """
    def snapshot():
        return client.rpc(domain='workspace', wait=False)

    def mutate(operation):
        current = snapshot()
        return client.rpc('(Mutate (expected_revision %s) (mutation %s))' %
                          (field(current, 'revision'), operation), domain='workspace', wait=False)

    current = snapshot()
    matches = [w for w in field(current, 'workspaces') if field(w, 'name') == name]
    if matches:
        return matches[0]
    window = field(field(current, 'workspaces')[0], 'window')
    current = mutate('(Create_workspace (window %s) (name %s) (context %s))' %
                     (sexp(window), sexp(name), sexp(field(current, 'main_context'))))
    workspace = next(w for w in field(current, 'workspaces') if field(w, 'name') == name)
    wid = field(workspace, 'id')
    mutate('(Make_independent %s)' % sexp(wid))
    mutate('(Create_tile (workspace %s) (kind simulation) '
           '(geometry ((x 0) (y 0) (width 120) (height 36))))' % sexp(wid))
    return next(w for w in field(snapshot(), 'workspaces') if field(w, 'id') == wid)


def attempts(client):
    return field(client.rpc(domain='simulation', wait=False), 'attempts')


def artifact_bytes(client, detail, artifact):
    data = bytearray()
    while True:
        result = client.rpc('(Read_artifact_bytes (attempt_id %s) (artifact_id %s) '
                            '(sha256 %s) (offset %d) (limit 97))' % (
                                sexp(field(detail, 'id')), sexp(field(artifact, 'id')),
                                sexp(field(artifact, 'sha256')[0]), len(data)), domain='simulation', wait=False)
        page = field(result, 'byte_page')[0]
        raw = bytes.fromhex(field(page, 'bytes_hex'))
        require(int(field(page, 'offset')) == len(data) and int(field(page, 'next_offset')) == len(data) + len(raw),
                'raw-byte paging offsets')
        data.extend(raw)
        if field(page, 'eof') == 'true':
            require(int(field(page, 'total_size')) == len(data), 'raw-byte total size')
            break
        require(raw, 'non-EOF page advances')
    require(hashlib.sha256(data).hexdigest() == field(artifact, 'sha256')[0], 'raw bytes match artifact digest')
    return bytes(data)


def native(base, args):
    discovery = base / 'discovery'
    discovery.mkdir()
    log = (base / 'daemon.log').open('ab')
    daemon = None
    client = None
    result = dict(status='failed', checks=[])

    def check(ok, label):
        require(ok, label)
        result['checks'].append(label)

    def start():
        metadata = discovery / 'daemon.sexp'
        metadata.unlink(missing_ok=True)
        process = subprocess.Popen(demo.switch_command([
            args.daemon, '--port', '0', '--discovery-dir', discovery, '--state-dir', base / 'state']),
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        wait_for(lambda: metadata.exists() or process.poll() is not None, 'daemon startup')
        require(process.poll() is None, 'daemon startup; see daemon.log')
        return process, field(parse(metadata.read_text()), 'endpoint')

    def calls():
        path = base / 'project/simulation-calls.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def runs():
        return [entry for entry in calls() if entry['operation'] == 'run']

    def mutate(operation):
        return client.mutate(client.rpc(domain='workspace'), operation)

    try:
        daemon, url = start()
        client = Client(url, base / 'project', switch=demo.switch_name())
        check(field(client.raw('/api/v1/snapshot', [('instance_id', client.instance)]), 'jobs') == [],
              'daemon/project startup launches no jobs before explicit seed')
        # Capture a reservation while active, then emulate an interrupted explicit
        # seed. Retry exact recorded payload after BOTH config and catalog revisions.
        original_poll = demo.simulation_poll
        def interrupted_poll(*_args, **_kwargs):
            raise InterruptedError('private acceptance interruption after reservation')
        demo.simulation_poll = interrupted_poll
        try:
            demo.seed_simulation(base, client)
        except InterruptedError:
            pass
        finally:
            demo.simulation_poll = original_poll
        receipt = provider.load(base / 'simulation-seed.json')['submissions']['synthetic-fs2-v1-pass']
        first = details(client, receipt['attempt_id'])
        retry = field(client.rpc(receipt['operation'], domain='simulation', wait=False), 'detail')[0]
        check(field(first, 'id') == field(retry, 'id') and field(first, 'job') == field(retry, 'job') and
              field(first, 'lifecycle') in ('Queued', 'Running'), 'active stable-key retry retains exact reservation/job')
        live = demo.simulation_poll(client, '(Observe %s)' % sexp(receipt['attempt_id']),
            lambda s: any(field(c, 'progress') for c in field(field(s, 'detail')[0], 'cases')),
            'live structured progress')
        check(field(field(live, 'detail')[0], 'lifecycle') == 'Running',
              'flushed structured case progress visible while provider is running')
        config = base / 'project/hardcaml-workbench-simulation.sexp'
        source = base / 'project/synthetic-provider/simulation_provider.py'
        saved_config, saved_source = config.read_bytes(), source.read_bytes()
        config.write_text(config.read_text().replace('"20"', '"19"'))
        source.write_text(source.read_text().replace("('label', LABEL)", "('label', LABEL + ' revised catalog')"))
        pending = provider.load(base / 'simulation-seed.json')
        pending['submissions']['synthetic-fs2-v1-failure'] = dict(
            label='SYNTHETIC unreserved stale receipt', operation=
            '(Launch (submission_key synthetic-fs2-v1-failure) (discovery_digest %s) (selection %s))' %
            (sexp('0' * 64), sexp(simulation.selection(True))))
        provider.save(base / 'simulation-seed.json', pending)
        demo.seed_simulation(base, client)
        check(len(attempts(client)) == 2 and len(runs()) == 2, 'config/catalog revision retries retained keys without duplication')
        config.write_bytes(saved_config)
        source.write_bytes(saved_source)
        client, _ = demo.seed(base, url, args.preset_export)
        check(len(attempts(client)) == 2 and len(runs()) == 2, 'fresh full seed creates exactly two representative attempts')
        layout = client.rpc(domain='workspace')
        presets = demo.workspace_presets(args.preset_export)
        starter_mappings = field(layout, 'config_workspaces')
        starter_windows = field(layout, 'config_windows')
        expected_instances = [(field(window, 'key'), field(instance, 'key'),
                               field(instance, 'definition'))
                              for window in field(presets.config, 'windows')
                              for instance in field(window, 'workspaces')]
        check(field(layout, 'defaults_initialized') == 'true' and
              field(layout, 'configuration_pending') == 'false' and
              [(field(p, 'window_key'), field(p, 'workspace_key'), field(p, 'reference'))
               for p in starter_mappings] == expected_instances and
              {field(p, 'workspace') for p in starter_mappings} ==
              {field(w, 'id') for w in field(layout, 'workspaces')},
              'fresh seed initializes exactly the canonical three workspace instances and their provenance')
        for identity in ('overview', 'timing', 'testing'):
            workspaces = [w for w in field(layout, 'workspaces') if field(w, 'preset') == [identity]]
            check(len(workspaces) == 1, 'one stable ' + identity + ' workspace')
            definition = next(d for d in field(presets.config, 'definitions')
                              if field(d, 'key') == identity)
            policy = next(p for p in starter_mappings
                          if field(p, 'workspace') == field(workspaces[0], 'id'))
            tiles = [t for t in field(layout, 'tiles')
                     if field(t, 'workspace') == field(workspaces[0], 'id')]
            views = [[['kind', field(t, 'kind')], ['hidden', field(t, 'hidden')],
                      ['geometry', field(t, 'requested_geometry')]] for t in tiles]
            check(views == field(field(definition, 'template'), 'views') and
                  field(policy, 'definition') == definition and
                  field(policy, 'policy_detached') == 'false' and
                  field(policy, 'tiles') == [[field(spec, 'key'), field(tile, 'id')]
                                           for spec, tile in zip(field(definition, 'tiles'), tiles)],
                  identity + ' preserves exact canonical views, frozen policy and tile-key identities')
        legacy = Client(url, base / 'legacy-upgrade/project', switch=demo.switch_name())
        legacy_layout = legacy.rpc(domain='workspace')
        legacy_layout = legacy.mutate(legacy_layout,
            '(Create_workspace (window %s) (name Testing) (context %s))' % (
                sexp(field(field(legacy_layout, 'windows')[0], 'id')),
                sexp(field(legacy_layout, 'main_context'))))
        collision = field(legacy_layout, 'workspaces')[-1]
        legacy_layout = demo.ensure_workspaces(legacy, legacy_layout, presets)
        legacy_layout = demo.apply_workspace_presets(legacy, legacy_layout, presets)
        check(next(w for w in field(legacy_layout, 'workspaces') if field(w, 'id') == field(collision, 'id')) == collision and
              len([w for w in field(legacy_layout, 'workspaces') if field(w, 'preset') == ['testing']]) == 1 and
              field(next(w for w in field(legacy_layout, 'workspaces') if field(w, 'preset') == ['testing']), 'name') != 'Testing',
              'missing Testing installed without adopting/overwriting custom name collision')
        receipts = provider.load(base / 'simulation-seed.json')['submissions']
        pass_id = receipts['synthetic-fs2-v1-pass']['attempt_id']
        fail_id = receipts['synthetic-fs2-v1-failure']['attempt_id']
        for aid, outcome in ((pass_id, 'Passed'), (fail_id, 'Failed')):
            detail = details(client, aid)
            check(field(detail, 'outcome') == outcome and field(detail, 'exit_code') == ['0'],
                  outcome + ' semantic outcome separate from process exit')
            selection = field(field(detail, 'captured'), 'selection')
            check(field(selection, 'asic_inputs') == [] and
                  all(field(c, 'progress') for c in field(detail, 'cases')), 'structured progress and no fabricated ASIC association')
            for artifact in field(detail, 'artifacts'):
                check(field(artifact, 'availability') == 'Available', 'captured report/trace available')
                case = field(artifact, 'case_id')[0]
                report, trace = simulation.evidence(case, dict(selection), dict(field(selection, 'parameters')))
                expected = trace if field(artifact, 'kind') == 'synthetic-trace' else report
                raw = artifact_bytes(client, detail, artifact)
                check(raw == expected, 'byte-exact synthetic ' + field(artifact, 'kind') + ' ' + case)
                (base / (outcome + '-' + case + ('.trace' if raw == trace else '.json'))).write_bytes(raw)
            logs = client.raw('/api/v1/read-log', [('instance_id', client.instance),
                ('job', field(detail, 'job')), ('offset', 0), ('max_records', 100), ('max_bytes', 65536)])
            records = field(logs, 'records')
            check(any(field(r, 'stream') == 'Stdout' and 'SYNTHETIC inputs seed=' in field(r, 'data') for r in records),
                  'supervisor stdout contains labeled synthetic inputs')
            if outcome == 'Failed':
                check(any(field(r, 'stream') == 'Stderr' and 'intentional mismatch' in field(r, 'data') for r in records),
                      'supervisor stderr contains labeled synthetic mismatch')
            provider.save(base / ('logs-' + outcome + '.json'), logs)
        if not args.skip_pty:
            terminal_checks(base, args, client, pass_id, fail_id, check)
        # Rename the stable preset; add a user tile and pin it. Create custom name
        # collisions too; seed must never infer ownership from a display name.
        layout = client.rpc(domain='workspace')
        testing = next(w for w in field(layout, 'workspaces') if field(w, 'preset') == ['testing'])
        wid = field(testing, 'id')
        mutate('(Rename_workspace (workspace %s) (name "My retained tests"))' % sexp(wid))
        layout = mutate('(Create_tile (workspace %s) (kind notes) '
                        '(geometry ((x 3)(y 4)(width 23)(height 9))))' % sexp(wid))
        extra = field(field(layout, 'tiles')[-1], 'id')
        asic = client.rpc(wait=False)
        run = field(field(asic, 'runs')[0], 'run')
        layout = mutate('(Set_tile_binding (tile %s) (binding (Pin_run %s)))' % (sexp(extra), sexp(run)))
        preserved = next(t for t in field(layout, 'tiles') if field(t, 'id') == extra)
        context_id = field(testing, 'context')
        context = next(c for c in field(layout, 'contexts') if field(c, 'id') == context_id)
        layout = mutate('(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' % (
            sexp(wid), sexp(context_id), field(context, 'selection_revision'), sexp(run)))
        saved_context = next(c for c in field(layout, 'contexts') if field(c, 'id') == context_id)
        layout = mutate('(Create_workspace (window %s) (name Testing) (context %s))' %
                        (sexp(field(testing, 'window')), sexp(field(layout, 'main_context'))))
        custom = field(field(layout, 'workspaces')[-1], 'id')
        before_ids = {field(a, 'id') for a in attempts(client)}
        demo.seed(base, url, args.preset_export)
        after = client.rpc(domain='workspace')
        check(len([w for w in field(after, 'workspaces') if field(w, 'preset') == ['testing']]) == 1 and
              field(next(w for w in field(after, 'workspaces') if field(w, 'id') == wid), 'name') == 'My retained tests',
              'renamed Testing reseed retains one stable preset instance')
        check(next(t for t in field(after, 'tiles') if field(t, 'id') == extra) == preserved and
              field(next(w for w in field(after, 'workspaces') if field(w, 'id') == custom), 'preset') == [],
              'reseed preserves custom-name workspace and exact extra tile geometry/pin')
        check(next(c for c in field(after, 'contexts') if field(c, 'id') == context_id) == saved_context,
              'reseed preserves retained user context/selection revision')
        check(field(after, 'config_workspaces') == starter_mappings and
              field(after, 'config_windows') == starter_windows,
              'reseed preserves all three canonical starter mappings and frozen policies despite user rename/extras')
        check({field(a, 'id') for a in attempts(client)} == before_ids,
              'repeated full seed creates no duplicate attempts')
        cleared = mutate('(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run ()))' % (
            sexp(wid), sexp(context_id), field(saved_context, 'selection_revision')))
        cleared_context = next(c for c in field(cleared, 'contexts') if field(c, 'id') == context_id)
        demo.seed(base, url, args.preset_export)
        cleared_after = client.rpc(domain='workspace')
        check(next(c for c in field(cleared_after, 'contexts') if field(c, 'id') == context_id) == cleared_context,
              'reseed preserves an explicitly cleared user selection')
        before_calls = calls()
        for _ in range(3):
            attempts(client)
            details(client, pass_id)
        if not args.skip_pty:
            navigation_files = list((base / 'client-state/hardcaml-workbench/terminal').glob('navigation-*.sexp'))
            require(len(navigation_files) == 1, 'Exactly one private project navigation sidecar')
            navigation = parse(navigation_files[0].read_text())
            active = field(navigation, 'active')[0]
            saved_workspace = next(w for w in field(cleared_after, 'workspaces') if field(w, 'id') == active)
            saved_view = next(w for w in field(navigation, 'workspaces') if field(w, 'id') == active)
            check(field(saved_workspace, 'name') == 'Legacy simulation' and
                  any(field(tile, 'id') in field(saved_view, 'focus') and
                      field(tile, 'workspace') == active and field(tile, 'kind') == 'simulation'
                      for tile in field(cleared_after, 'tiles')),
                  'Saved navigation records the actual last active Legacy workspace and simulation focus')
            provider.save(base / 'restart-navigation.json', navigation)
            terminal = Terminal(base, args, client)
            try:
                terminal.capture('restart-restored-navigation', ['Legacy simulation',
                    'Structured simulation', 'Space c c commands'])
                check(True, 'Client restart restores the saved Legacy workspace and focused simulation view')
                terminal.palette('Switch to My retained tests')
                terminal.capture('restart-retained-testing', ['My retained tests',
                    'simulation-catalog', 'simulation-attempts', 'simulation-cases',
                    'simulation-detail', 'simulation-artifacts', 'simulation-logs',
                    'Suite: synthetic-checks', 'seeded-pattern', '[Available]'])
                retained = client.rpc(domain='workspace')
                check(field(retained, 'config_workspaces') == starter_mappings and
                      next(t for t in field(retained, 'tiles') if field(t, 'id') == extra) == preserved,
                      'Explicit post-restart Testing navigation preserves frozen starter policy and exact extra pin/geometry')
            finally:
                terminal.close()
        check(calls() == before_calls, 'Get/Observe/navigation/client restart launches no provider processes')
        # Durable seed receipts survive daemon instance and provider-config changes.
        daemon.terminate()
        daemon.wait(timeout=15)
        daemon, url = start()
        client, _ = demo.seed(base, url, args.preset_export)
        restarted = client.rpc(domain='workspace')
        check(field(restarted, 'config_workspaces') == starter_mappings and
              field(restarted, 'config_windows') == starter_windows,
              'daemon restart and reseed retain exact canonical starter provenance and tile identities')
        check({field(a, 'id') for a in attempts(client)} == before_ids and len(runs()) == len(before_ids),
              'daemon restart and reseed preserve reservations without replay')
        result.update(status='passed', url=url, attempts=attempts(client), receipts=receipts)
    except BaseException:
        result['error'] = traceback.format_exc()
        raise
    finally:
        if client:
            provider.save(base / 'testing-http.json', client.history)
        if daemon and daemon.poll() is None:
            os.killpg(daemon.pid, signal.SIGTERM)
            try:
                daemon.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(daemon.pid, signal.SIGKILL)
                daemon.wait(timeout=5)
        log.close()
        provider.save(base / 'testing-result.json', result)


def terminal_checks(base, args, client, pass_id, fail_id, check):
    before = {field(a, 'id') for a in attempts(client)}
    ensure_legacy_simulation(client)
    terminal = Terminal(base, args, client)
    try:
        terminal.capture('overview', ['Overview', 'Timing', 'Testing', 'Session', 'Stage checklist'])
        terminal.palette('Switch to Timing')
        terminal.capture('timing', ['Timing', 'Session', 'Timing · Paths', 'Timing · Provenance'])
        terminal.palette('Switch to Testing')
        terminal.capture('testing', ['Testing', 'session', 'project-tests', 'execution',
            'simulation-catalog', 'simulation-attempts', 'simulation-cases',
            'simulation-detail', 'simulation-artifacts', 'simulation-logs',
            'Suite: synthetic-checks', 'Finished/Passed', 'Finished/Failed',
            'seeded-pattern: Passed', 'injected-mismatch: Failed', '[Available]', '[stdout]'])
        terminal.focus_simulation()
        terminal.palette('Simulation: Reopen ' + pass_id + ' synthetic-checks')
        terminal.palette('Simulation: Select case seeded-pattern')
        terminal.capture('testing-cooperative-selected-case', ['simulation-cases',
            '> seeded-pattern: Passed', 'simulation-detail', 'Passed / Finished',
            'simulation-artifacts', '[Available]', 'simulation-logs', '[stdout]'])
        check({field(a, 'id') for a in attempts(client)} == before,
              'Cooperative Testing reopen/case selection updates real panes without allocating attempts')
        terminal.palette('Switch to Legacy simulation')
        terminal.capture('legacy-testing', ['Structured simulation', 'seed=314159', 'seed=42'])
        terminal.focus_simulation()
        terminal.palette('Simulation: Reopen ' + fail_id + ' synthetic-checks')
        terminal.capture('failure', ['Failed', 'SYNTHETIC', '314159'])
        terminal.palette('Simulation: Reopen ' + pass_id + ' synthetic-checks')
        terminal.palette('Simulation: Select case seeded-pattern')
        terminal.capture('selected-case', ['> seeded-pattern: Passed'])
        terminal.palette('Appearance: C - Minimal')
        terminal.capture('theme', ['> seeded-pattern: Passed', 'Legacy simulation'])
        terminal.palette('Zoom focused tile')
        terminal.palette('Simulation: Toggle stream-labelled job logs')
        terminal.capture('logs', ['JOB LOG'])
        terminal.palette('Simulation: Toggle stream-labelled job logs')
        check({field(a, 'id') for a in attempts(client)} == before, 'PTY workspace browsing/case selection/logs launch no attempts')
        terminal.palette('Simulation: Rerun case seeded-pattern (original inputs; current project)')
        submitted = wait_for(lambda: [a for a in attempts(client) if field(a, 'id') not in before], 'PTY targeted rerun')
        require(len(submitted) == 1, 'one PTY rerun allocation')
        aid = field(submitted[0], 'id')
        snapshot = demo.simulation_poll(client, '(Observe %s)' % sexp(aid),
            lambda s: field(field(s, 'detail')[0], 'lifecycle') not in ('Queued', 'Running'), 'PTY rerun')
        child = field(snapshot, 'detail')[0]
        parent = details(client, pass_id)
        captured = dict(field(field(child, 'captured'), 'selection'))
        expected = dict(field(field(parent, 'captured'), 'selection'), cases=['seeded-pattern'])
        check(field(child, 'job') != field(parent, 'job') and field(child, 'id') != pass_id and
              field(field(child, 'parent')[0], 'attempt_id') == pass_id and captured == expected and
              field(child, 'outcome') == 'Passed', 'PTY targeted rerun creates new job/attempt with exact original seed/parameters')
        terminal.capture('rerun', ['Rerun of', 'Passed'])
        provider.save(base / 'pty-rerun.json', child)
        terminal.palette('Unzoom workspace')
        terminal.capture('testing-rerun-full', ['Legacy simulation', 'Structured simulation', 'seed: 42', 'Passed'])
    finally:
        terminal.close()
    terminal = Terminal(base, args, client, width=180, height=55)
    try:
        # Navigation preferences intentionally restore the previous active desk;
        # select Overview explicitly before asserting its larger-viewport content.
        terminal.capture('restored-navigation-large', ['Space c c commands'])
        terminal.palette('Switch to Overview')
        terminal.capture('overview-large', ['Overview', 'Testing', 'Session'])
        terminal.palette('Switch to Timing')
        terminal.capture('timing-large', ['Session', 'Timing · Paths', 'Timing · Provenance'])
        terminal.palette('Switch to Testing')
        terminal.capture('testing-large', ['session', 'project-tests', 'execution',
            'simulation-catalog', 'simulation-attempts', 'simulation-cases',
            'simulation-detail', 'simulation-artifacts', 'simulation-logs',
            'Suite: synthetic-checks', 'seeded-pattern', '[Available]', '[stdout]'])
        terminal.palette('Switch to Legacy simulation')
        terminal.capture('legacy-testing-large', ['Structured simulation', 'synthetic-checks'])
        terminal.focus_simulation()
        terminal.palette('Simulation: Reopen ' + fail_id + ' synthetic-checks')
        terminal.capture('failure-large', ['314159', 'Failed', 'injected-mismatch', 'SYNTHETIC'])
    finally:
        terminal.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    build = Path('/tmp/opencode/testing-provider/default')
    parser.add_argument('--daemon', type=Path, default=build / 'daemon/main.exe')
    parser.add_argument('--client', type=Path, default=build / 'terminal/main.exe')
    parser.add_argument('--preset-export', type=Path, default=build / 'terminal/workspaces/export_presets.exe')
    parser.add_argument('--evidence', type=Path, help='NEW private directory, existing parent')
    parser.add_argument('--smoke', action='store_true', help='standalone provider and upgrade checks only')
    parser.add_argument('--skip-pty', action='store_true', help='HTTP diagnostic; full acceptance requires PTY')
    args = parser.parse_args()
    os.umask(0o077)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('synthetic Testing acceptance budget exhausted')))
    signal.alarm(240)
    base = demo.prepare(args.evidence, delay=.01)
    print('SYNTHETIC Testing evidence: ' + str(base), flush=True)
    standalone(base)
    upgrade_checks(base)
    if not args.smoke:
        for name in ('daemon', 'client', 'preset_export'):
            setattr(args, name, getattr(args, name).resolve(strict=True))
        native(base, args)
    print('PASS synthetic Testing ' + ('standalone/upgrade' if args.smoke else 'native HTTP' + ('' if args.skip_pty else '/PTY')), flush=True)


if __name__ == '__main__':
    main()
