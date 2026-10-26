#!/usr/bin/env python3
"""Private WB004 frontend fixture: selected-flow publication only, no EDA."""
import hashlib
import json
from pathlib import Path
import sys
import time


def compact(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def identity(contract, payload):
    return digest(json.dumps(dict(contract=contract, schema_version=1, payload=payload),
                             sort_keys=True, separators=(',', ':')))


def main():
    args = sys.argv[1:]
    assert args[:2] == ['flow', 'emit'], 'Only EDA-less publication is permitted'
    def arg(name):
        return args[args.index(name) + 1]
    root = Path(arg('--source-root'))
    with (root / 'preparation-calls.jsonl').open('a') as out:
        out.write(json.dumps(args) + '\n')
    print('WB004 exact emission log', file=sys.stderr, flush=True)
    mode = (root / 'preparation-mode').read_text().strip()
    if mode == 'fail':
        raise SystemExit('WB004 deliberate emission failure')
    if mode == 'hold':
        while True:
            time.sleep(.1)
    config = '{"DESIGN_NAME":"WB004 published config"}\n'
    payload = dict(schema_version=1, project='frontend-fixture',
                   files=[dict(path='src/config.json', sha256=digest(config))])
    bundle_id = digest(compact(payload))
    manifest = dict(identity=bundle_id, **payload)
    output = Path(arg('--results-root')) / 'bundles' / bundle_id
    (output / 'src').mkdir(parents=True, exist_ok=True)
    (output / 'src/config.json').write_text(config)
    (output / 'manifest.json').write_text(compact(manifest))
    assignments = []
    for i, value in enumerate(args):
        if value == '--set':
            key, val = args[i + 1].split('=', 1)
            assignments.append(dict(key=key, value={'true': True, 'false': False}.get(val, val)))
    snapshot = dict(contract='hardcaml-asic.flow-snapshot', schema_version=1,
                    declaration={}, definition={}, profile={},
                    selected=dict(flow=arg('--flow'), profile=arg('--profile')),
                    endpoint=arg('--endpoint'), stages=[arg('--endpoint')],
                    request=assignments, parameters=[])
    methodology = dict(snapshot=snapshot, project_assignments=[], effective_parameters=[],
                       translation={}, recipe=dict(schema_version=4, stages=snapshot['stages'], initial_boundary=None))
    plan = dict(contract='hardcaml-asic.methodology-plan', schema_version=1,
                methodology=methodology,
                methodology_hash=identity('hardcaml-asic.methodology-hash', methodology),
                project_name='frontend-fixture', bundle_identity=bundle_id,
                bundle_manifest=compact(manifest), configuration_bytes=config)
    plan_id = identity('hardcaml-asic.plan-identity', plan)
    plan['plan_identity'] = plan_id
    print(compact(dict(schema_version=1, kind='bundle_emission', bundle_identity=bundle_id,
                       plan_identity=plan_id, output_dir=str(output), reused=False, plan=plan)))


if __name__ == '__main__':
    main()
