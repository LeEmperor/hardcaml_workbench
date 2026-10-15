#!/usr/bin/env python3
"""Injected public-boundary fixture: no EDA, provider imports, or shell."""
import json
import os
import signal
import sys
import time

args = sys.argv[1:]
root = os.getcwd()
with open(os.path.join(root, 'calls'), 'a') as out:
    out.write(json.dumps(args) + '\n')


def option(flag, default=None):
    return args[args.index(flag) + 1] if flag in args else default


def emit(value):
    print(json.dumps(value), flush=True)


def envelope(contract, version=1, **fields):
    return dict(contract='hardcaml-asic.' + contract, schema_version=version, **fields)


def plan():
    return envelope('methodology-plan', plan_identity='a' * 64,
                    bundle_identity='b' * 64)


if args == ['lifecycle-exit']:
    sys.exit(0)
elif args[:1] in [['lifecycle-wait'], ['lifecycle-output'], ['lifecycle-malformed'], ['lifecycle-cancel']]:
    mode = args[0]

    def stop_fixture(_signal, _frame):
        with open(os.path.join(root, mode + '-terminated'), 'w') as out:
            out.write('owned process received SIGTERM')
        # Do not flush a buffered oversized stdout record during failure cleanup.
        os._exit(130)

    signal.signal(signal.SIGTERM, stop_fixture)
    if mode == 'lifecycle-malformed':
        print('not-json', flush=True)
    else:
        emit(dict(ready=True))
    if mode == 'lifecycle-output':
        # No newline: exercise the per-record budget, not JSON parser behaviour.
        for _ in range(9):
            sys.stdout.write('x' * (1024 * 1024))
            sys.stdout.flush()
    time.sleep(30)
elif args == ['--version', '--json']:
    emit(dict(cli_contract=dict(version=4, capabilities=dict(namedflow1=True))))
elif args[:2] == ['flow', 'list']:
    emit(envelope('flow-list', declaration=envelope('flow-catalog', entries=[
        dict(methodology=dict(id='standard'), default_profile='balanced',
             profiles=[dict(id='balanced'), dict(id='synth_delay')])],
        default=dict(flow='standard', profile='balanced'))))
elif args[:2] == ['flow', 'describe']:
    emit(envelope('flow-describe', id=option('--flow')))
elif args[:2] == ['flow', 'plan']:
    emit(plan())
elif args[:2] == ['flow', 'run']:
    profile = option('--profile')
    attempt = os.path.join(root, 'attempt-' + profile)
    os.makedirs(attempt, exist_ok=True)
    stream = 'stream-' + profile

    def terminate(_signal, _frame):
        with open(os.path.join(attempt, 'terminated'), 'w') as out:
            out.write('owned launcher received SIGTERM')
        sys.exit(130)

    signal.signal(signal.SIGTERM, terminate)
    emit(envelope('stage-observation', event='observation_allocated',
                  attempt=attempt, stream_id=stream))
    time.sleep(0.6 if not os.path.exists('hold') else 30)
    with open(os.path.join(attempt, 'done'), 'w') as out:
        out.write('done')
    emit(envelope('stage-observation', event='observation_terminal',
                  execution_file=os.path.join(attempt, 'execution.json')))
elif args[:2] == ['observation', 'read-updates']:
    emit(envelope('stage-observation', 2, stream_id=option('--stream-id'),
                  after=int(option('--after')), cursor=0, events=[]))
elif args[:2] == ['observation', 'inspect']:
    attempt = args[2]
    stream = 'stream-' + os.path.basename(attempt).removeprefix('attempt-')
    done = os.path.exists(os.path.join(attempt, 'done'))
    missing = os.path.exists('missing')
    method = envelope('historical-methodology', state='recorded' if done else 'pending',
                      plan_identity='a' * 64, bundle_identity='b' * 64,
                      reference=dict(attempt_id=stream),
                      launch=dict(attempt_id=stream, expected_plan_identity='a' * 64))
    emit(envelope('stage-observation', 2, stream_id=stream, cursor=0,
                  writer_active=not done, observation_status='final' if done else 'active',
                  state=dict(outcome=dict(status='completed', exit_code=0) if done else None),
                  methodology=method,
                  execution_file=os.path.join(attempt, 'execution.json') if done and not missing else None))
elif args[:1] == ['report']:
    attempt = os.path.dirname(args[1])
    profile = os.path.basename(attempt).removeprefix('attempt-')
    stream = 'stream-' + profile
    count = 50 if profile == 'balanced' else 73
    if os.path.exists('revision'):
        count += 1
    emit(envelope('report', execution=dict(attempt_id=stream, status='completed'),
                  acceptance='not_evaluated',
                  methodology=envelope('historical-methodology', state='recorded',
                                       plan_identity='a' * 64, bundle_identity='b' * 64,
                                       reference=dict(attempt_id=stream)),
                  checkpoints=[dict(reference=dict(path=attempt, boundary='synthesis', identity=str(count)),
                                    metric_origin=dict(scope='boundary_snapshot'),
                                    metrics=[dict(raw_key='design__instance__count', availability='available', value=count)],
                                    supplementary=[dict(mapped_cell_types={'cell': count})])]))
else:
    print('Unsupported fixture argv: ' + repr(args), file=sys.stderr)
    sys.exit(2)
