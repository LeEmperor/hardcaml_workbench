#!/usr/bin/env python3
"""Prepare/seed an isolated SYNTHETIC no-EDA project. Never builds a binary.

prepare prints commands; daemon/client explicitly exec an already built binary.
seed uses real daemon HTTP, including registration, summaries, FS1 and layouts.
"""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'demo/synthetic_flow'))
import provider
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
    return base


def seed(base, url):
    manifest = provider.load(base / 'manifest.json')
    # Explicit selection also works with an externally started daemon whose PATH
    # lacks Dune. The terminal must use the same selection/project-session key.
    client = Client(url, manifest['project_root'], switch=switch_name())
    client.rpc('Discover')
    client.rpc('(Describe synthetic)')
    registered = []
    for reference in manifest['runs']:
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
    overview = field(ws, 'workspaces')[0]
    workspace = field(overview, 'id')
    context_id = field(overview, 'context')
    context = next(c for c in field(ws, 'contexts') if field(c, 'id') == context_id)
    ws = client.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' %
        (workspace, context_id, field(context, 'selection_revision'), sexp(registered[0])))
    # Seed before the first terminal opens: revision > 0 deliberately bypasses
    # initialize_host_layout's revision-zero additive default preset. Re-seeding
    # also hides obsolete/extra tiles from earlier demo layouts, without deletion.
    layouts = {
        'Overview': [('workspace-tabs', 28, 6), ('live-status', 32, 8), ('run-selector', 32, 10),
                     ('stage-checklist', 40, 13), ('synthesis', 56, 12), ('timing', 40, 10),
                     ('placement', 40, 10), ('checks', 40, 10), ('finalization', 40, 10)],
        'Timing': [('workspace-tabs', 28, 6), ('live-status', 32, 8), ('run-selector', 32, 10),
                   ('timing', 56, 12), ('placement', 40, 10), ('cts', 40, 10),
                   ('routing', 40, 10), ('checks', 40, 10), ('finalization', 40, 10)],
    }
    for arrangement in field(ws, 'workspaces'):
        name = field(arrangement, 'name')
        if name not in layouts:
            continue
        wid = field(arrangement, 'id')
        specs = layouts[name]
        chosen = []
        for kind, width, height in specs:
            tiles = [t for t in field(ws, 'tiles') if field(t, 'workspace') == wid and field(t, 'kind') == kind]
            geometry = '((x 0) (y 0) (width %d) (height %d))' % (width, height)
            if not tiles:
                ws = client.mutate(ws, '(Create_tile (workspace %s) (kind %s) (geometry %s))' % (wid, kind, geometry))
                tile = field(ws, 'tiles')[-1]
            else:
                tile = tiles[0]
            tid = field(tile, 'id')
            chosen.append(tid)
            ws = client.mutate(ws, '(Resize_tile (tile %s) (geometry %s))' % (tid, geometry))
            ws = client.mutate(ws, '(Set_tile_hidden (tile %s) (hidden false))' % tid)
            ws = client.mutate(ws, '(Reorder_tile (tile %s) (before ()))' % tid)
        for tile in field(ws, 'tiles'):
            if field(tile, 'workspace') == wid and field(tile, 'id') not in chosen and field(tile, 'hidden') != 'true':
                ws = client.mutate(ws, '(Set_tile_hidden (tile %s) (hidden true))' % field(tile, 'id'))
    provider.save(base / 'seed-http.json', client.history)
    provider.save(base / 'seeded.json', dict(url=url, project=client.project, runs=registered, workspace=ws))
    print('SYNTHETIC reference and failed candidate registered; FS1 evidence imported.')
    return client, registered


def commands(base, daemon, client, url=None):
    q = lambda value: shlex.quote(str(value))
    script = REPO / 'scripts/synthetic-flow-demo.py'
    print('SYNTHETIC demo: ' + str(base))
    print('1. ' + ' '.join(map(q, [sys.executable, script, 'daemon', '--dir', base, '--daemon', daemon])))
    connection = ['--url', url] if url else []
    print('2. ' + ' '.join(map(q, [sys.executable, script, 'seed', '--dir', base] + connection)))
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
    parser.add_argument('--manual', action='store_true', help='runs wait for explicit provider advance; 120s bound')
    parser.add_argument('--delay', type=float, default=1.5, help='seconds per stage, .01..2 (default: 1.5)')
    parser.add_argument('--daemon', type=Path, default=REPO / '_build/default/daemon/main.exe')
    parser.add_argument('--client', type=Path, default=REPO / '_build/default/terminal/main.exe')
    args = parser.parse_args()
    if not .01 <= args.delay <= 2:
        parser.error('--delay must be .01..2')
    if args.command == 'prepare':
        base = prepare(args.dir, args.manual, args.delay)
        commands(base, args.daemon, args.client)
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
        seed(base, args.url)
        commands(base, args.daemon, args.client, args.url)
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
        commands(base, args.daemon, args.client, args.url)


if __name__ == '__main__':
    main()
