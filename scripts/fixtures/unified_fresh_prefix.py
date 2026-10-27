#!/usr/bin/env python3
"""Private fresh-prefix producers. Synthetic evidence only; never invokes EDA."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import time

PREFIX = ['synthesis', 'floorplan', 'placement', 'cts', 'routing', 'timing', 'signoff']


def compact(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(contract, payload):
    return sha(json.dumps(dict(contract=contract, schema_version=1, payload=payload),
                          sort_keys=True, separators=(',', ':')).encode())


def event(root, kind, **data):
    raw = (compact(dict(kind=kind, time_ns=time.time_ns(), pid=os.getpid(),
                        pgid=os.getpgrp(), **data)) + '\n').encode()
    fd = os.open(root / 'events.jsonl', os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)


def gate(root, stage):
    control = root / (stage + '-mode')
    mode = control.read_text().strip() if control.exists() else 'success'
    if mode == 'fail':
        raise RuntimeError('INJECTED ' + stage + ' failure')
    if mode == 'hold':
        def stop(*_):
            event(root, stage + '-stopped')
            raise SystemExit(130)
        signal.signal(signal.SIGTERM, stop)
        event(root, stage + '-held')
        deadline = time.monotonic() + 60
        while not (root / (stage + '-release')).exists():
            if time.monotonic() > deadline:
                raise TimeoutError(stage + ' gate timed out')
            time.sleep(.025)
    return mode


def main():
    role, root = sys.argv[1], Path(sys.argv[2])
    args = sys.argv[3:]
    def option(flag):
        return args[args.index(flag) + 1]
    if role == 'build':
        event(root, 'build-start')
        gate(root, 'build')
        # The build product is independently copied from source by a real Dune rule.
        Path('publisher.exe').write_bytes((root / 'publisher-source').read_bytes())
        Path('publisher.exe').chmod(0o700)
        event(root, 'build-finished')
    elif role == 'emit':
        assert args[:2] == ['flow', 'emit'], args
        event(root, 'emit-start', argv=args)
        mode = gate(root, 'emit')
        if mode == 'malformed':
            print('{broken receipt')
            return
        config = compact(dict(DESIGN_NAME='fresh-source-only', generation=(root / 'generation').read_text())) + '\n'
        payload = dict(schema_version=1, project='fresh-source-only',
                       files=[dict(path='src/config.json', sha256=sha(config.encode()))])
        bundle_id = sha(compact(payload).encode())
        manifest = dict(identity=bundle_id, **payload)
        output = Path(option('--results-root')) / 'bundles' / bundle_id
        reused = output.exists()
        (output / 'src').mkdir(parents=True, exist_ok=True)
        (output / 'src/config.json').write_text(config)
        (output / 'manifest.json').write_text(compact(manifest))
        stages = PREFIX[:PREFIX.index(option('--endpoint')) + 1]
        assignments = [dict(key=args[i + 1].split('=', 1)[0], value=args[i + 1].split('=', 1)[1])
                       for i, value in enumerate(args) if value == '--set']
        snapshot = dict(contract='hardcaml-asic.flow-snapshot', schema_version=1,
                        declaration={}, definition={}, profile={},
                        selected=dict(flow=option('--flow'), profile=option('--profile')),
                        endpoint=option('--endpoint'), stages=stages, request=assignments, parameters=[])
        methodology = dict(snapshot=snapshot, project_assignments=[], effective_parameters=[],
                           translation={}, recipe=dict(schema_version=4, stages=stages, initial_boundary=None))
        plan = dict(contract='hardcaml-asic.methodology-plan', schema_version=1,
                    methodology=methodology,
                    methodology_hash=identity('hardcaml-asic.methodology-hash', methodology),
                    project_name='fresh-source-only', bundle_identity=bundle_id,
                    bundle_manifest=compact(manifest), configuration_bytes=config)
        plan['plan_identity'] = identity('hardcaml-asic.plan-identity', plan)
        receipt = dict(schema_version=1, kind='bundle_emission', bundle_identity=bundle_id,
                       plan_identity=plan['plan_identity'], output_dir=str(output), reused=reused, plan=plan)
        receipt_path = root / ('receipt-' + str(time.time_ns()) + '.json')
        receipt_path.write_text(compact(receipt))
        event(root, 'emit-finished', receipt=str(receipt_path), bundle_identity=bundle_id,
              plan_identity=plan['plan_identity'], reused=reused)
        print(compact(receipt), flush=True)
    elif role == 'provider':
        event(root, 'provider-call', argv=args)
        historical = (args[:1] == ['observation'] and (Path(args[2]) / 'observation.json').exists()) or (
            args[:1] == ['report'] and (Path(args[1]).parent / 'observation.json').exists())
        if historical:
            sys.argv = [str(root / 'synthetic-provider/provider.py'), *args]
            runpy.run_path(sys.argv[0], run_name='__main__')
            return
        if args[:1] == ['stages']:
            plan_path = Path(option('--methodology-plan'))
            raw = plan_path.read_bytes()
            plan = json.loads(raw)
            unsigned = dict(plan)
            pid = unsigned.pop('plan_identity')
            assert identity('hardcaml-asic.plan-identity', unsigned) == pid
            assert pid == option('--expected-plan-identity')
            assert plan['methodology_hash'] == identity('hardcaml-asic.methodology-hash', plan['methodology'])
            manifest = json.loads((Path(args[1]) / 'manifest.json').read_text())
            assert manifest == json.loads(plan['bundle_manifest'])
            payload = dict(manifest)
            bundle_id = payload.pop('identity')
            assert sha(compact(payload).encode()) == bundle_id == plan['bundle_identity']
            for member in manifest['files']:
                assert sha((Path(args[1]) / member['path']).read_bytes()) == member['sha256']
            assert (Path(args[1]) / 'src/config.json').read_text() == plan['configuration_bytes']
            recipe = plan['methodology']['recipe']
            assert recipe['stages'] == PREFIX[:PREFIX.index(plan['methodology']['snapshot']['endpoint']) + 1]
            assert '--endpoint' not in args and '--checkpoint' not in args
            for flag, suffix in [('--support-tools', 'support'), ('--pdk-root', 'pdk'), ('--python', 'python')]:
                assert option(flag) == str(root / ('configured-' + suffix)), args
            assert option('--timeout') == '45'
            event(root, 'physical-admitted', argv=args, plan_sha256=sha(raw),
                  plan_identity=pid, bundle_identity=plan['bundle_identity'], stages=recipe['stages'])
        # Reuse the backend owner's exact observation fixture, copied at setup.
        sys.argv = [str(root / 'physical.py'), *args]
        runpy.run_path(str(root / 'physical.py'), run_name='__main__')
    elif role == 'pinned':
        event(root, 'pinned-call', argv=args)
        assert args[:2] != ['flow', 'run'], 'Pinned flow run bypass forbidden'
        if args[:2] == ['flow', 'list']:
            gate(root, 'discovery')
            control = root / 'catalog-mode'
            if control.exists():
                mode = control.read_text().strip()
                command = [sys.executable, str(root / 'synthetic-provider/provider.py'), *args]
                payload = json.loads(subprocess.check_output(command))
                entry = payload['declaration']['entries'][0]
                if mode == 'default-not-first':
                    decoy = json.loads(json.dumps(entry))
                    decoy['methodology']['id'] = 'decoy-first'
                    payload['declaration']['entries'].insert(0, decoy)
                if mode == 'nonfresh':
                    payload['capabilities']['input'] = 'checkpoint'
                    entry['methodology']['input'] = 'checkpoint'
                if mode in ('unsupported-endpoint', 'withdraw-placement'):
                    entry['methodology']['endpoints'].remove('placement' if mode == 'withdraw-placement' else 'routing')
                print(compact(payload), flush=True)
                return
        sys.argv = [str(root / 'synthetic-provider/provider.py'), *args]
        runpy.run_path(sys.argv[0], run_name='__main__')
    else:
        raise ValueError(role)


if __name__ == '__main__':
    main()
