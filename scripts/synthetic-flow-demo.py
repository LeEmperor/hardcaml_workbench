#!/usr/bin/env python3
"""Prepare/seed an isolated SYNTHETIC no-EDA project. Never builds a binary.

prepare prints commands; daemon/client explicitly exec an already built binary.
seed uses real daemon HTTP, including registration, summaries, FS1, FS2 and layouts.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'demo/synthetic_flow'))
import provider
import simulation_provider
from http_client import Client, field, parse, sexp


def switch_name():
    return os.environ.get('OPAM_SWITCH', '5.2.0+ox')


def switch_command(argv):
    return ['/bin/bash', str(REPO / 'scripts/with-switch.sh'), *map(str, argv)]


def prepare(directory=None, manual=False, delay=1.5):
    base = Path(directory).expanduser().resolve() if directory else Path(tempfile.mkdtemp(
        prefix='synthetic-flow-', dir='/tmp/opencode'))
    if directory:
        base.mkdir(exist_ok=False)
    root = base / 'project'
    root.mkdir()
    source = root / 'synthetic-provider'
    source.mkdir()
    for name in ('provider.py', 'scenarios.json'):
        shutil.copyfile(REPO / 'demo/synthetic_flow' / name, source / name)
    wrapper = root / 'synthetic-flow'
    wrapper.write_text('#!' + sys.executable + '\nimport runpy\nrunpy.run_path(' +
                       repr(str(source / 'provider.py')) + ', run_name="__main__")\n')
    wrapper.chmod(0o700)
    (root / 'dune-project').write_text('(lang dune 3.17)\n(name synthetic_flow_demo)\n')
    (root / 'dune').write_text('; SYNTHETIC project: no EDA or build targets required.\n')
    provider.save(root / 'synthetic-settings.json', dict(manual=manual, delay_seconds=delay, max_run_seconds=120))
    results = base / 'results'
    results.mkdir()
    config = [['schema_version', '1'], ['project_executable', str(wrapper)],
              ['provider_executable', str(wrapper)], ['results_root', str(results)],
              ['toolchain', str(root)], ['python', []], ['support_tools', []],
              ['pdk_root', []], ['stage_timeout_seconds', []]]
    (root / 'hardcaml-workbench-asic.sexp').write_text(sexp(config) + '\n')
    runs = provider.seed(results)
    provider.save(base / 'manifest.json', dict(synthetic=True, label=provider.LABEL,
        project_root=str(root), results_root=str(results), runs=runs))
    install_simulation(base)
    return base


def install_simulation(base):
    """Explicit, additive prepare/seed upgrade; preflight every owned destination."""
    manifest_path = base / 'manifest.json'
    manifest = provider.load(manifest_path)
    root = base / 'project'
    if (manifest.get('synthetic') is not True or manifest.get('label') != provider.LABEL or
            manifest.get('project_root') != str(root) or
            manifest.get('results_root') != str(base / 'results') or
            not isinstance(manifest.get('runs'), list)):
        raise RuntimeError('Refusing upgrade: manifest.json is not this prepared SYNTHETIC demo. '
                           'Use prepare --dir NEW_DIRECTORY, or restore its original manifest.')
    previous = manifest.get('simulation_install', {})
    if previous and (previous.get('owner') != 'synthetic-flow-fs2' or previous.get('version') != 1):
        raise RuntimeError('Unsupported synthetic FS2 ownership/version; use a new prepared directory.')
    source = root / 'synthetic-provider'
    config = [['schema_version', '1'], ['provider_executable', str(Path(sys.executable).resolve())],
              ['provider_args', [str(source / 'simulation_provider.py')]],
              ['discovery_timeout_seconds', '10'], ['run_timeout_seconds', '20']]
    files = {root / 'hardcaml-workbench-simulation.sexp': (sexp(config) + '\n').encode()}
    for name in ('simulation_provider.py', 'simulation_wire.py'):
        files[source / name] = (REPO / 'demo/synthetic_flow' / name).read_bytes()
    hashes = {}
    for path, data in files.items():
        relative = str(path.relative_to(root))
        hashes[relative] = hashlib.sha256(data).hexdigest()
        # Symlink parents must never redirect an additive upgrade outside the demo.
        if any(p.is_symlink() for p in (base, root, path.parent, path)):
            raise RuntimeError('Refusing synthetic upgrade through symlink: ' + str(path))
        if path.exists():
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            owned = previous.get('sha256', {}).get(relative)
            if actual != hashes[relative] and actual != owned:
                raise RuntimeError('Refusing to overwrite unrelated or edited file: ' + str(path) +
                    '. Keep your configuration/provider; prepare --dir NEW_DIRECTORY for the demo, '
                    'or explicitly relocate this conflicting file before seed.')
    source.mkdir(exist_ok=True)
    for path, data in files.items():
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
    manifest['simulation_install'] = dict(owner='synthetic-flow-fs2', version=1, sha256=hashes)
    provider.save(manifest_path, manifest)
    return manifest


def workspace_presets(executable=None):
    """Read the OCaml source of truth; never synthesize fallback Python layouts."""
    executable = Path(executable or os.environ.get('WORKBENCH_PRESET_EXPORT',
        REPO / '_build/default/terminal/workspaces/export_presets.exe')).expanduser().resolve()
    if not executable.is_file():
        raise RuntimeError('Build terminal/workspaces/export_presets.exe and pass --preset-export; missing ' + str(executable))
    output = subprocess.run(switch_command([executable]), check=True, capture_output=True,
                            text=True, timeout=15).stdout
    presets = parse(output)
    ids = [field(p, 'id') for p in presets]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate OCaml preset IDs')
    return {field(p, 'id'): p for p in presets}


def apply_workspace_presets(client, snapshot, presets):
    """Add defaults without resetting pins, custom geometry or user-owned extras."""
    for arrangement in field(snapshot, 'workspaces'):
        identity = field(arrangement, 'preset')
        definition = presets.get(identity[0]) if identity else None
        if definition is None:
            continue
        specs = [[field(tile, 'kind'), field(tile, 'geometry')]
                 for tile in field(definition, 'tiles')]
        snapshot = client.mutate(snapshot,
            '(Apply_preset (workspace %s) (preset %s) (tiles %s))' %
            (sexp(field(arrangement, 'id')), sexp(field(definition, 'id')), sexp(specs)))
    return snapshot


def ensure_workspaces(client, snapshot, presets):
    """Stable preset identity wins over display names, including custom collisions."""
    for identity in ('overview', 'timing', 'testing'):
        if any(field(w, 'preset') == [identity] for w in field(snapshot, 'workspaces')):
            continue
        before = {field(w, 'id') for w in field(snapshot, 'workspaces')}
        names = {field(w, 'name') for w in field(snapshot, 'workspaces')}
        name = field(presets[identity], 'name')
        if name in names:
            name += ' (synthetic default)'
            while name in names:
                name += '+'
        snapshot = client.mutate(snapshot,
            '(Create_workspace (window %s) (name %s) (context %s))' %
            (sexp(field(field(snapshot, 'windows')[0], 'id')), sexp(name),
             sexp(field(snapshot, 'main_context'))))
        created = next(w for w in field(snapshot, 'workspaces') if field(w, 'id') not in before)
        specs = [[field(t, 'kind'), field(t, 'geometry')] for t in field(presets[identity], 'tiles')]
        snapshot = client.mutate(snapshot,
            '(Apply_preset (workspace %s) (preset %s) (tiles %s))' %
            (sexp(field(created, 'id')), sexp(identity), sexp(specs)))
    return snapshot


def simulation_poll(client, operation, predicate, label, seconds=30):
    """FS2 rpc returns promptly: explicitly Observe/Get, never ASIC wait semantics."""
    deadline = time.monotonic() + seconds
    notice = 0
    while True:
        snapshot = client.rpc(operation, domain='simulation', wait=False)
        if predicate(snapshot):
            return snapshot
        now = time.monotonic()
        if now >= deadline:
            raise TimeoutError('SYNTHETIC ' + label + ' timed out; retry explicit seed with the same directory/keys.')
        if now >= notice:
            print('SYNTHETIC waiting: ' + label, flush=True)
            notice = now + 2
        time.sleep(.1)


def discover_simulation(client):
    snapshot = client.rpc('Discover', domain='simulation', wait=False)
    job = field(snapshot, 'discovery_job')[0]
    deadline = time.monotonic() + 30
    notice = 0
    while True:
        snapshot = client.raw('/api/v1/snapshot', [['instance_id', client.instance]])
        found = next((j for j in field(snapshot, 'jobs') if field(j, 'id') == job), None)
        if found and field(found, 'state') in ('Complete', 'Failed', 'Cancelled'):
            break
        now = time.monotonic()
        if now >= deadline:
            raise TimeoutError('SYNTHETIC discovery timed out; retry seed (active discovery coalesces).')
        if now >= notice:
            print('SYNTHETIC waiting: FS2 Discover job ' + str(job), flush=True)
            notice = now + 2
        time.sleep(.1)
    snapshot = client.rpc(domain='simulation', wait=False)
    if field(snapshot, 'discovery_error') or not field(snapshot, 'discovery_digest'):
        raise RuntimeError('SYNTHETIC FS2 discovery failed: ' + sexp(snapshot))
    return field(snapshot, 'discovery_digest')[0]


def seed_simulation(base, client):
    digest = discover_simulation(client)
    path = base / 'simulation-seed.json'
    receipts = provider.load(path) if path.exists() else {'version': 1, 'submissions': {}}
    if receipts.get('version') != 1:
        raise RuntimeError('Unsupported simulation-seed.json version; preserve it and use a new demo.')
    for label, failed in (('pass', False), ('failure', True)):
        key = 'synthetic-fs2-v1-' + label
        receipt = receipts['submissions'].get(key)
        if receipt is None:
            operation = '(Launch (submission_key %s) (discovery_digest %s) (selection %s))' % (
                sexp(key), sexp(digest), sexp(simulation_provider.selection(failed)))
            receipt = dict(label='SYNTHETIC representative ' + label, operation=operation)
            receipts['submissions'][key] = receipt
            # Persist exact payload BEFORE submitting: recovery across catalog/config
            # revisions retries the original reservation, not a changed digest.
            provider.save(path, receipts)
        print('SYNTHETIC FS2 seed: ' + label + ' (' + key + ')', flush=True)
        try:
            snapshot = client.rpc(receipt['operation'], domain='simulation', wait=False)
        except RuntimeError as error:
            # These exact errors occur only AFTER durable reservation lookup. A
            # never-accepted/evicted payload may adopt the freshly discovered digest.
            if 'Stale simulation discovery digest' not in str(error):
                raise
            old = parse(receipt['operation'])
            for entry in old[1:]:
                if entry[0] == 'discovery_digest':
                    entry[1] = digest
            receipt['operation'] = '(' + old[0] + ' ' + ' '.join(sexp(v) for v in old[1:]) + ')'
            provider.save(path, receipts)
            snapshot = client.rpc(receipt['operation'], domain='simulation', wait=False)
        detail = field(snapshot, 'detail')[0]
        receipt.update(attempt_id=field(detail, 'id'), job=field(detail, 'job'))
        provider.save(path, receipts)
        snapshot = simulation_poll(client, '(Observe %s)' % sexp(receipt['attempt_id']),
            lambda s: field(field(s, 'detail')[0], 'lifecycle') not in ('Queued', 'Running'),
            label + ' attempt ' + receipt['attempt_id'])
        detail = field(snapshot, 'detail')[0]
        if field(detail, 'outcome') != ('Failed' if failed else 'Passed') or field(detail, 'exit_code') != ['0']:
            raise RuntimeError('SYNTHETIC representative attempt did not finish as declared: ' + sexp(detail))
        receipt['detail'] = detail
        provider.save(path, receipts)
        print('SYNTHETIC FS2 ' + label + ': ' + field(detail, 'outcome') +
              ', process exit 0, reports/traces retained.', flush=True)
    return receipts


def seed(base, url, preset_export=None):
    manifest = install_simulation(base)
    print('SYNTHETIC seed: owned FS2 files/config verified; importing retained ASIC evidence.', flush=True)
    presets = workspace_presets(preset_export)
    # Explicit selection also works with an externally started daemon whose PATH
    # lacks Dune. The terminal must use the same selection/project-session key.
    client = Client(url, manifest['project_root'], switch=switch_name())
    client.rpc('Discover')
    client.rpc('(Describe synthetic)')
    registered = []
    for reference in manifest['runs']:
        print('SYNTHETIC importing: ' + reference['stream_id'], flush=True)
        ref = [['attempt', reference['attempt']], ['stream_id', reference['stream_id']]]
        snapshot = client.rpc('(Register %s)' % sexp(ref))
        run = next(field(r, 'run') for r in field(snapshot, 'runs')
                   if field(field(r, 'reference'), 'stream_id') == reference['stream_id'])
        client.rpc('(Observe %s)' % sexp(run))
        client.rpc('(Load_summary %s)' % sexp(run))
        snapshot = client.rpc('(Inspect_finalization (run %s) (attempt %s))' %
                             (sexp(run), sexp(reference['finalization'])))
        for domain, stage in [('timing', 'signoff'), ('clocks', 'signoff'),
                              ('physical', 'placement'), ('routing', 'routing')]:
            client.rpc('(Inspect (run %s) (domain %s) (stage %s) (refresh true))' %
                       (sexp(run), domain, stage))
        client.rpc('(List_artifacts %s)' % sexp(run))
        registered.append(run)
    # Stable existing workspace IDs; avoid duplicating tiles on repeated seed.
    ws = client.rpc(domain='workspace')
    ws = ensure_workspaces(client, ws, presets)
    overview = next((w for w in field(ws, 'workspaces') if field(w, 'preset') == ['overview']), None)
    if overview is None:
        raise RuntimeError('Synthetic seed requires a workspace with stable preset ID overview')
    workspace = field(overview, 'id')
    context_id = field(overview, 'context')
    context = next(c for c in field(ws, 'contexts') if field(c, 'id') == context_id)
    if not field(context, 'selected_run') and not (base / 'seeded.json').exists():
        ws = client.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' %
            (workspace, context_id, field(context, 'selection_revision'), sexp(registered[0])))
    ws = apply_workspace_presets(client, ws, presets)
    seed_simulation(base, client)
    provider.save(base / 'workspace-presets.json', presets)
    provider.save(base / 'seed-http.json', client.history)
    provider.save(base / 'seeded.json', dict(url=url, project=client.project, runs=registered, workspace=ws))
    print('SYNTHETIC reference and failed candidate registered; FS1 and FS2 evidence imported.', flush=True)
    return client, registered


def commands(base, daemon, client, url=None, preset_export=None):
    q = lambda value: shlex.quote(str(value))
    script = REPO / 'scripts/synthetic-flow-demo.py'
    print('SYNTHETIC demo: ' + str(base))
    print('1. ' + ' '.join(map(q, [sys.executable, script, 'daemon', '--dir', base, '--daemon', daemon])))
    connection = ['--url', url] if url else []
    export = ['--preset-export', preset_export] if preset_export else []
    print('2. ' + ' '.join(map(q, [sys.executable, script, 'seed', '--dir', base] + connection + export)))
    print('3. ' + ' '.join(map(q, [sys.executable, script, 'client', '--dir', base, '--client', client])) +
          (' --url ' + q(url) if url else ''))
    if url:
        print('Exact plain-client planning command: ' + ' '.join(map(q, switch_command([client, '--connect', url,
            '--environment', 'opam:' + switch_name(),
            '--project-root', base / 'project', '--plain', '--api', '--asic-operation',
            '(Plan ((flow synthetic) (profile success) (endpoint placement) (assignments ())))', '--wait']))))
    print('Checklist: j/k selects; r plans a NEW prefix run; Space c c → Launch / Launch and view.')
    print('Manual advance (for a newly allocated attempt): ' + q(base / 'project/synthetic-flow') +
          ' advance /ABSOLUTE/ATTEMPT [--cancel]')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'seed', 'daemon', 'client', 'commands'])
    parser.add_argument('--dir', type=Path, help='prepare: NEW directory with existing parent; others: existing demo')
    parser.add_argument('--url')
    parser.add_argument('--preset-export', type=Path, help='OCaml export_presets.exe (or WORKBENCH_PRESET_EXPORT)')
    parser.add_argument('--manual', action='store_true', help='runs wait for explicit provider advance; 120s bound')
    parser.add_argument('--delay', type=float, default=1.5, help='seconds per stage, .01..2 (default: 1.5)')
    parser.add_argument('--daemon', type=Path, default=REPO / '_build/default/daemon/main.exe')
    parser.add_argument('--client', type=Path, default=REPO / '_build/default/terminal/main.exe')
    args = parser.parse_args()
    if not .01 <= args.delay <= 2:
        parser.error('--delay must be .01..2')
    if args.command == 'prepare':
        base = prepare(args.dir, args.manual, args.delay)
        commands(base, args.daemon, args.client, preset_export=args.preset_export)
        return
    if args.dir is None:
        parser.error('--dir required')
    base = args.dir.expanduser().resolve()
    if args.command in ('seed', 'client') and not args.url:
        metadata = base / 'discovery/daemon.sexp'
        if not metadata.exists():
            parser.error('--url required unless this demo has discovery/daemon.sexp')
        args.url = field(parse(metadata.read_text()), 'endpoint')
    if args.command == 'seed':
        seed(base, args.url, args.preset_export)
        commands(base, args.daemon, args.client, args.url, args.preset_export)
    elif args.command == 'daemon':
        discovery = base / 'discovery'
        discovery.mkdir(exist_ok=True)
        argv = switch_command([args.daemon.resolve(), '--port', '0', '--discovery-dir', discovery,
                               '--state-dir', base / 'state'])
        os.execv(argv[0], argv)
    elif args.command == 'client':
        os.environ['XDG_STATE_HOME'] = str(base / 'client-state')
        argv = switch_command([args.client.resolve(), '--connect', args.url, '--project-root', base / 'project',
                               '--environment', 'opam:' + switch_name()])
        os.execv(argv[0], argv)
    else:
        commands(base, args.daemon, args.client, args.url, args.preset_export)


if __name__ == '__main__':
    main()
