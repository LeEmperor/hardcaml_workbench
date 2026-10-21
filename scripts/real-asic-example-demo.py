#!/usr/bin/env python3
"""Adopt retained real ASIC evidence through public APIs. Never builds or runs EDA.

prepare validates explicit references, backs up and pins the example config, and
copies supplied Workbench binaries into persistent demo storage. seed only reads
provider evidence and registers it with an explicitly selected daemon.
refresh-binaries explicitly replaces prepared copies from existing binaries and
records before/after hashes; restart is required, and live processes are untouched.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'demo/synthetic_flow'))
from http_client import Client, field, parse, sexp

DOMAINS = [('timing', 'signoff'), ('clocks', 'signoff'),
           ('physical', 'placement'), ('routing', 'routing')]
EXAMPLE = REPO.parent / 'hardcaml_asic_example'
EVIDENCE = '_flow_results/reorg-ad290d8-20261015'
OBSERVATION = 'observations/20261015T083637970284Z_344ac175'
FINALIZATION = 'finalizations/20261015T090320118823Z_a22d3963'
STREAM = '344ac175531e46fcbd021a1d4c79c361'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def inventory(paths):
    """Byte inventory of explicit canonical inputs, including symlink identities."""
    result = {}
    for root in map(Path, paths):
        entries = [root, *sorted(root.rglob('*'))] if root.is_dir() else [root]
        for path in entries:
            if path.is_symlink():
                result[str(path)] = {'symlink': os.readlink(path)}
            elif path.is_file():
                result[str(path)] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
    return result


def query(executable, args, root, receipts, name):
    process = subprocess.run([str(executable), *map(str, args)], cwd=root,
                             capture_output=True, timeout=30)
    (receipts / (name + '.stdout')).write_bytes(process.stdout)
    (receipts / (name + '.stderr')).write_bytes(process.stderr)
    require(process.returncode == 0, name + ': ' + process.stderr.decode(errors='replace'))
    return json.loads(process.stdout)


def verify(root, provider, receipts):
    evidence = root / EVIDENCE
    # Read original allocation records. Directory ordering never establishes identity.
    allocation = json.loads((evidence / 'client/run.stdout.jsonl').read_text().splitlines()[0])
    finalization = json.loads((evidence / 'client/finalize.stdout.jsonl').read_text().splitlines()[0])
    require(allocation['attempt'] == str(evidence / OBSERVATION)
            and allocation['stream_id'] == STREAM, 'Unexpected original observation allocation')
    require(finalization['attempt'] == str(evidence / FINALIZATION), 'Unexpected original finalization allocation')
    version = query(provider, ['--version', '--json'], root, receipts, 'version')
    contract = version['cli_contract']
    require(contract['version'] == 4 and contract['capabilities']['namedflow1'] is True,
            'Requires CLI4 + namedflow1')
    require('inspect' in contract['capabilities']['json_commands'], 'Provider lacks rich inspect')
    observed = query(provider, ['observation', 'inspect', allocation['attempt'], '--json'],
                     root, receipts, 'observation')
    execution = observed['execution_file']
    report = query(provider, ['report', execution, '--json'], root, receipts, 'report')
    operation = query(provider, ['finalization-inspect', finalization['attempt'], '--json'],
                      root, receipts, 'finalization')
    require(observed['writer_active'] is False and observed['observation_status'] == 'final'
            and report['execution']['status'] == 'completed', 'Execution is not completed')
    require(observed['stream_id'] == report['execution']['attempt_id'] == operation['execution']['attempt_id'] == STREAM,
            'Attempt identity mismatch')
    require(execution == operation['execution']['path'], 'Execution path mismatch')
    require(observed['methodology']['reference'] == report['methodology']['reference'], 'Methodology mismatch')
    key = lambda x: (x['boundary'], x['path'], x['identity'])
    require([key(c['reference']) for c in report['checkpoints']]
            == [key(c) for c in operation['selected_checkpoints']]
            == [key(c) for c in report['execution']['artifacts']], 'Checkpoint selection mismatch')
    require(operation['status'] == 'completed' and operation['acceptance'] == 'pass', 'Finalization did not pass')
    references = [operation['execution'], operation['results'], operation['acceptance_report'],
                  {'path': operation['postcheck_record'], 'sha256': operation['postcheck_sha256']},
                  {'path': observed['methodology']['reference']['snapshot_path'],
                   'sha256': observed['methodology']['reference']['snapshot_sha256']}]
    references += [dict(path=str(Path(finalization['attempt']) / p), sha256=v['sha256'])
                   for p, v in operation['mapped_files'].items()]
    references += [dict(path=str(Path(v['path']) / 'manifest.json'), sha256=v['manifest_sha256'])
                   for v in operation['selected_evidence'] if 'manifest_sha256' in v]
    for reference in references:
        require(digest(reference['path']) == reference['sha256'], 'Hash mismatch: ' + reference['path'])
    indexes = []
    for domain, stage in DOMAINS:
        index = query(provider, ['inspect', execution, '--domain', domain, '--stage', stage, '--json'],
                      root, receipts, 'inspect-' + domain)
        require(index['attempt_id'] == STREAM and index['execution_file'] == execution
                and index['execution_sha256'] == digest(execution), 'Inspection identity mismatch')
        require(bool(index['rows']), 'No retained rows for ' + domain)
        indexes.append(dict(domain=domain, stage=stage, rows=len(index['rows']),
                            source_digest=index['source_digest'], diagnostics=index['diagnostics']))
    return dict(project_root=str(root), provider=str(provider), provider_sha256=digest(provider),
                allocation={k: allocation[k] for k in ('attempt', 'stream_id')},
                finalization=finalization['attempt'], execution_file=execution,
                hashes=references, inspections=indexes, version=version,
                methodology=observed['methodology']['reference'])


def switch_command(argv):
    return ['/bin/bash', str(REPO / 'scripts/with-switch.sh'), *map(str, argv)]


def verify_binaries(base, manifest):
    for name, expected in manifest['binaries'].items():
        require(digest(base / 'bin' / name) == expected, 'Prepared binary differs from manifest: ' + name)


def refresh_binaries(args, base):
    """Stage all three inputs before publishing; replace inodes, never running processes."""
    with (base / 'refresh-binaries.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest_file = base / 'manifest.json'
        original = manifest_file.read_bytes()
        manifest = json.loads(original)
        verify_binaries(base, manifest)
        receipts = base / 'receipts' / ('refresh-binaries-' + uuid.uuid4().hex)
        receipts.mkdir()
        (receipts / 'manifest-before.json').write_bytes(original)
        staged = receipts / 'staged'
        backup = receipts / 'before'
        staged.mkdir()
        backup.mkdir()
        result = dict(status='staging', restart_required=True, sources={},
                      before=manifest['binaries'], manifest_before_sha256=digest(manifest_file))
        published = []
        manifest_published = False
        try:
            for name, source in [('daemon', args.daemon), ('client', args.client), ('preset-export', args.preset_export)]:
                source = source.resolve(strict=True)
                require(os.access(source, os.X_OK), 'Source binary is not executable: ' + str(source))
                expected = digest(source)
                shutil.copy2(source, staged / name)
                require(digest(staged / name) == expected == digest(source), 'Source changed during copy: ' + str(source))
                shutil.copy2(base / 'bin' / name, backup / name)
                require(digest(backup / name) == manifest['binaries'][name], 'Prepared binary changed during backup')
                result['sources'][name] = dict(path=str(source), sha256=expected)
            result['after'] = {name: value['sha256'] for name, value in result['sources'].items()}
            manifest['binaries'] = result['after']
            manifest['binary_refresh_receipts'] = str(receipts)
            save(receipts / 'manifest-after.json', manifest)
            result['status'] = 'publishing'
            save(receipts / 'result.json', result)
            # Stage manifest beside its destination for a final atomic rename.
            pending = base / ('.manifest-' + uuid.uuid4().hex)
            pending.write_bytes((receipts / 'manifest-after.json').read_bytes())
            try:
                for name in result['after']:
                    os.replace(staged / name, base / 'bin' / name)
                    published.append(name)
                verify_binaries(base, manifest)
                os.replace(pending, manifest_file)
                manifest_published = True
            finally:
                pending.unlink(missing_ok=True)
            result.update(status='completed', manifest_after_sha256=digest(manifest_file))
            save(receipts / 'result.json', result)
        except BaseException as error:
            # Before manifest publication restore the previous complete candidate.
            # Crash interruption remains visible as publishing + manifest mismatch.
            if not manifest_published:
                for name in reversed(published):
                    os.replace(backup / name, base / 'bin' / name)
            result.update(status='failed', error=str(error), manifest_published=manifest_published)
            save(receipts / 'result.json', result)
            raise
        print('Refreshed prepared binaries: ' + str(receipts))
        print('Restart required to use the new binaries. Existing live processes were left running.')


def prepare(args, base):
    require(not (base / 'manifest.json').exists(), 'Demo already prepared; use daemon/seed/client or a new --dir')
    require(args.provider is not None, 'prepare requires an explicit immutable --provider')
    root = args.project_root.resolve(strict=True)
    provider = args.provider.resolve(strict=True)
    require('/generations/' in str(provider) and '/tmp/' not in str(provider), 'Use a persistent immutable generation')
    base.mkdir(parents=True, exist_ok=True)
    for name in ('receipts', 'bin', 'state', 'discovery', 'client-state', 'config', 'results'):
        (base / name).mkdir(exist_ok=True)
    receipts = base / 'receipts' / ('prepare-' + uuid.uuid4().hex)
    receipts.mkdir()
    before = inventory([root / EVIDENCE])
    save(receipts / 'inputs-before.json', before)
    manifest = verify(root, provider, receipts)
    project = root / '_build_namedflow_real/default/bin/project.exe'
    query(project, ['flow', 'list', '--json'], root, receipts, 'flows')
    query(project, ['flow', 'describe', '--flow', 'standard', '--json'], root, receipts, 'description')
    for name, source in [('daemon', args.daemon), ('client', args.client), ('preset-export', args.preset_export)]:
        source = source.resolve(strict=True)
        destination = base / 'bin' / name
        require(not destination.exists(), 'Refusing to overwrite demo binary: ' + str(destination))
        shutil.copy2(source, destination)
    config = root / 'hardcaml-workbench-asic.sexp'
    original = config.read_bytes()
    (receipts / 'config-before.sexp').write_bytes(original)
    fields = parse(original.decode())
    for item in fields:
        if item[0] == 'provider_executable':
            item[1] = str(provider)
        elif item[0] == 'results_root':
            item[1] = str(base / 'results')
    require(dict(fields)['project_executable'] == str(project), 'Unexpected project executable; refusing replacement')
    after = inventory([root / EVIDENCE])
    save(receipts / 'inputs-after.json', after)
    require(before == after, 'Canonical evidence changed during verification')
    config.write_text(sexp(fields) + '\n')
    manifest.update(schema_version=1, synthetic=False, base=str(base), prepare_receipts=str(receipts),
                    project_executable=str(project), project_sha256=digest(project),
                    config_before_sha256=hashlib.sha256(original).hexdigest(), config_sha256=digest(config),
                    binaries={name: digest(base / 'bin' / name) for name in ('daemon', 'client', 'preset-export')})
    save(base / 'manifest.json', manifest)
    commands(base)


def seed(base, url, receipt_dir=None):
    print('REAL ASIC seed: verifying pinned binaries, configuration and retained evidence.', flush=True)
    manifest = json.loads((base / 'manifest.json').read_text())
    verify_binaries(base, manifest)
    root = Path(manifest['project_root'])
    require(digest(root / 'hardcaml-workbench-asic.sexp') == manifest['config_sha256'], 'Demo config changed')
    require(digest(manifest['provider']) == manifest['provider_sha256'], 'Provider changed')
    require(digest(manifest['project_executable']) == manifest['project_sha256'], 'Project executable changed')
    for reference in manifest['hashes']:
        require(digest(reference['path']) == reference['sha256'], 'Evidence changed: ' + reference['path'])
    receipts = receipt_dir or base / 'receipts' / ('seed-' + uuid.uuid4().hex)
    receipts.mkdir(parents=True, exist_ok=True)
    print('REAL ASIC seed: opening ' + str(root) + ' at ' + url, flush=True)
    client = Client(url, root, switch=os.environ.get('OPAM_SWITCH', '5.2.0+ox'))
    try:
        print('REAL ASIC seed: discovering supported flows (no EDA launch).', flush=True)
        client.rpc('Discover')
        client.rpc('(Describe standard)')
        reference = [[key, manifest['allocation'][key]] for key in ('attempt', 'stream_id')]
        print('REAL ASIC seed: registering the exact retained observation.', flush=True)
        snap = client.rpc('(Register %s)' % sexp(reference))
        run = next(field(r, 'run') for r in field(snap, 'runs') if field(r, 'reference') == reference)
        client.rpc('(Observe %s)' % sexp(run))
        print('REAL ASIC seed: loading synthesis and retained finalization evidence.', flush=True)
        client.rpc('(Load_summary %s)' % sexp(run))
        snap = client.rpc('(Inspect_finalization (run %s) (attempt %s))' % (sexp(run), sexp(manifest['finalization'])))
        for domain, stage in DOMAINS:
            print('REAL ASIC seed: loading ' + domain + ' / ' + stage + ' inspection.', flush=True)
            snap = client.rpc('(Inspect (run %s) (domain %s) (stage %s) (refresh true))' % (sexp(run), domain, stage))
        summary = next(s for s in field(snap, 'summaries') if field(s, 'run') == run)
        require(field(summary, 'cell_count') == ['673'] and field(summary, 'freshness') == 'Validated',
                'Real synthesis summary was not validated')
        # Consume the same complete startup composition as the native client. An
        # existing session wins; legacy unfinished bootstrap uses exported templates.
        config = parse(subprocess.run([str(base / 'bin/preset-export'), '--workspace-config'],
                                      check=True, capture_output=True, text=True, timeout=15).stdout)
        save(receipts / 'workspace-config.json', config)
        ws = client.rpc('(Initialize_config %s)' % sexp(config), domain='workspace')
        if field(ws, 'defaults_initialized') == 'false':
            definitions = {field(d, 'key'): d for d in field(config, 'definitions')}
            templates = [field(definitions[field(w, 'definition')[1]], 'template')
                         for window in field(config, 'windows')
                         for w in field(window, 'workspaces')]
            ws = client.rpc('(Bootstrap %s)' % sexp(templates), domain='workspace')
        # Add defaults to legacy preset instances without resetting user geometry.
        presets = parse(subprocess.run([str(base / 'bin/preset-export')], check=True,
                                      capture_output=True, text=True, timeout=15).stdout)
        for arrangement in field(ws, 'workspaces'):
            definition = next((p for p in presets if [field(p, 'id')] == field(arrangement, 'preset')), None)
            if definition is not None and field(arrangement, 'preset') in (['overview'], ['timing']):
                specs = [[field(t, 'kind'), field(t, 'geometry')] for t in field(definition, 'tiles')]
                ws = client.mutate(ws, '(Apply_preset (workspace %s) (preset %s) (tiles %s))' %
                                   (sexp(field(arrangement, 'id')), sexp(field(definition, 'id')), sexp(specs)))
        for arrangement in field(ws, 'workspaces'):
            if field(arrangement, 'preset') in (['overview'], ['timing']):
                context = next(c for c in field(ws, 'contexts') if field(c, 'id') == field(arrangement, 'context'))
                ws = client.mutate(ws, '(Select_run (workspace %s) (context %s) (expected_selection_revision %s) (run (%s)))' %
                                   (sexp(field(arrangement, 'id')), sexp(field(context, 'id')),
                                    field(context, 'selection_revision'), sexp(run)))
        save(receipts / 'adoption.json', dict(synthetic=False, project_root=str(root), run=run,
                                             allocation=manifest['allocation'], finalization=manifest['finalization'],
                                             snapshot=snap, workspace=ws))
        print('REAL ASIC seed: evidence loaded; start the client. Receipts: ' + str(receipts), flush=True)
        return client, run
    finally:
        save(receipts / 'http.json', client.history)


def commands(base):
    script = REPO / 'scripts/real-asic-example-demo.py'
    for command in ('daemon', 'seed', 'client'):
        print(shlex.join([sys.executable, str(script), command, '--dir', str(base)]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'refresh-binaries', 'daemon', 'seed', 'client', 'commands'])
    parser.add_argument('--project-root', type=Path, default=EXAMPLE)
    parser.add_argument('--dir', type=Path)
    parser.add_argument('--provider', type=Path)
    parser.add_argument('--daemon', type=Path, help='prepare/refresh-binaries only: source daemon (default: _build/default/daemon/main.exe)')
    parser.add_argument('--client', type=Path, help='prepare/refresh-binaries only: source client (default: _build/default/terminal/main.exe)')
    parser.add_argument('--preset-export', type=Path, help='prepare/refresh-binaries only: source exporter (default: _build/default/terminal/workspaces/export_presets.exe)')
    parser.add_argument('--url')
    args = parser.parse_args()
    if args.command not in ('prepare', 'refresh-binaries') and any((args.daemon, args.client, args.preset_export)):
        parser.error('--daemon/--client/--preset-export apply only to prepare or refresh-binaries; launch uses prepared copies')
    args.daemon = args.daemon or REPO / '_build/default/daemon/main.exe'
    args.client = args.client or REPO / '_build/default/terminal/main.exe'
    args.preset_export = args.preset_export or REPO / '_build/default/terminal/workspaces/export_presets.exe'
    base = (args.dir or args.project_root / '.dev/workbench-real-demo').expanduser().resolve()
    if args.command == 'prepare':
        prepare(args, base)
    elif args.command == 'refresh-binaries':
        refresh_binaries(args, base)
    elif args.command == 'commands':
        commands(base)
    else:
        manifest = json.loads((base / 'manifest.json').read_text())
        verify_binaries(base, manifest)
        if args.command == 'daemon':
            argv = switch_command([base / 'bin/daemon', '--port', '0', '--discovery-dir', base / 'discovery', '--state-dir', base / 'state'])
        else:
            url = args.url or field(parse((base / 'discovery/daemon.sexp').read_text()), 'endpoint')
            if args.command == 'seed':
                _, run = seed(base, url)
                print('Retained real signoff adopted: ' + sexp(run))
                return
            os.environ['XDG_STATE_HOME'] = str(base / 'client-state')
            os.environ['XDG_CONFIG_HOME'] = str(base / 'config')
            argv = switch_command([base / 'bin/client', '--connect', url, '--project-root', manifest['project_root'],
                                   '--environment', 'opam:' + os.environ.get('OPAM_SWITCH', '5.2.0+ox')])
        os.execv(argv[0], argv)


if __name__ == '__main__':
    main()
