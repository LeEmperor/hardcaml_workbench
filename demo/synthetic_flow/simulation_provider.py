#!/usr/bin/env python3
"""SYNTHETIC FS2 demonstration, not hardware simulation or EDA evidence.

Only Python's standard library and the adjacent copied simulation_wire are used.
Semantic failures intentionally exit zero after a complete Failed event stream.
Invalid requests instead exit nonzero without manufacturing case results.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
from simulation_wire import EventWriter, parse, sexp

SUITE = 'synthetic-checks'
CASES = ('reset-sequence', 'seeded-pattern', 'injected-mismatch')
PARAMETERS = {'steps': ('8', ['8', '16', '32']),
              'pattern': ('walking', ['walking', 'alternating'])}
LABEL = 'SYNTHETIC FS2 demo - no hardware simulation'


def catalog():
    return [('protocol_version', 1), ('suites', [[
        ('id', SUITE), ('label', LABEL),
        ('cases', [[('id', case), ('label', 'SYNTHETIC ' + case)] for case in CASES]),
        ('parameters', [[('key', key), ('label', 'Synthetic ' + key),
                         ('default', default), ('choices', choices)]
                        for key, (default, choices) in sorted(PARAMETERS.items())]),
        ('default_seed', '42')]])]


def selection(failed=False):
    return [('suite', SUITE),
            ('cases', ['seeded-pattern', 'injected-mismatch'] if failed else
             ['reset-sequence', 'seeded-pattern']),
            ('seed', '314159' if failed else '42'),
            ('parameters', [('pattern', 'alternating' if failed else 'walking'),
                            ('steps', '16' if failed else '8')]),
            ('asic_inputs', [])]


def validate(request):
    req = dict(request)
    if set(req) != {'protocol_version', 'attempt_id', 'selection'} or req['protocol_version'] != '1':
        raise ValueError('Expected FS2 v1 request')
    sel = dict(req['selection'])
    if set(sel) != {'suite', 'cases', 'seed', 'parameters', 'asic_inputs'}:
        raise ValueError('Unexpected selection fields')
    cases = sel['cases']
    if sel['suite'] != SUITE or not cases or len(set(cases)) != len(cases) or not set(cases) <= set(CASES):
        raise ValueError('Select unique declared synthetic cases')
    seed = sel['seed']
    if not seed.isascii() or not seed.isdecimal() or str(int(seed)) != seed or int(seed) > 2**64 - 1:
        raise ValueError('Seed must be canonical uint64')
    params = dict(sel['parameters'])
    if len(params) != len(sel['parameters']) or set(params) != set(PARAMETERS):
        raise ValueError('Supply exactly the declared synthetic parameters')
    if any(params[key] not in choices for key, (_, choices) in PARAMETERS.items()):
        raise ValueError('Invalid synthetic parameter choice')
    if sel['asic_inputs']:
        raise ValueError('This synthetic demonstration accepts no ASIC inputs')
    return req, sel, params


def evidence(case, sel, params):
    """Deterministic bytes, independent of attempt/job identity and wall clock."""
    description = dict(synthetic=True, disclaimer=LABEL, case=case, seed=sel['seed'],
                       parameters=params, outcome='Failed' if case == 'injected-mismatch' else 'Passed')
    report = (json.dumps(description, indent=2, sort_keys=True) + '\n').encode()
    # Deliberately binary: raw-byte API/export must preserve NUL, 0xff and CRLF.
    trace = b'SYNTHETIC TRACE v1 - NOT HARDWARE\r\n\x00\xff' + report
    for step in range(int(params['steps'])):
        trace += hashlib.sha256(report + str(step).encode()).digest()
    return report, trace


def run(args):
    req, sel, params = validate(parse(args.request.read_text()))
    print(LABEL + '; attempt=' + req['attempt_id'], flush=True)
    print('SYNTHETIC inputs seed=' + sel['seed'] + ' parameters=' + json.dumps(params, sort_keys=True), flush=True)
    failed = False
    with args.events.open('a', encoding='utf-8', newline='\n') as stream:
        writer = EventWriter(stream, req['attempt_id'])
        writer.emit('Started')
        for case in sel['cases']:
            writer.emit(['Case_started', case])
            total = int(params['steps'])
            writer.progress(case, 0, total)
            for step in range(1, total + 1):
                time.sleep(.025)
                writer.progress(case, step, total)
            report, trace = evidence(case, sel, params)
            bad = case == 'injected-mismatch'
            failed |= bad
            for suffix, data, kind, media, label in (
                ('.json', report, 'failure-report' if bad else 'report', 'application/json', 'SYNTHETIC report '),
                ('.trace', trace, 'synthetic-trace', 'application/octet-stream', 'SYNTHETIC trace (not hardware) '),
            ):
                path = case + suffix
                (args.artifact_dir / path).write_bytes(data)
                writer.artifact(case, label + case, kind, media, path)
            status = 'Failed' if bad else 'Passed'
            message = 'SYNTHETIC intentional mismatch: expected 7, observed 6' if bad else None
            print('SYNTHETIC case=' + case + ' result=' + status, flush=True)
            if message:
                print(message, file=sys.stderr, flush=True)
            writer.emit(['Case_finished', [('case_id', case), ('status', status),
                                           ('message', [] if message is None else [message])]])
        writer.emit(['Finished', 'Failed' if failed else 'Passed'])
    print('SYNTHETIC complete; semantic=' + ('Failed' if failed else 'Passed') + '; process exit=0', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['discover', 'run'])
    parser.add_argument('--protocol-version', type=int, required=True, choices=[1])
    parser.add_argument('--request', type=Path)
    parser.add_argument('--events', type=Path)
    parser.add_argument('--artifact-dir', type=Path)
    args = parser.parse_args()
    with (Path(__file__).resolve().parent.parent / 'simulation-calls.jsonl').open('a') as calls:
        calls.write(json.dumps(dict(operation=args.operation,
            request=parse(args.request.read_text()) if args.request else None)) + '\n')
    if args.operation == 'discover':
        print(sexp(catalog()))
    else:
        if not all((args.request, args.events, args.artifact_dir)):
            parser.error('run requires --request, --events and --artifact-dir')
        run(args)


if __name__ == '__main__':
    main()
