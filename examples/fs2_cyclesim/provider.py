#!/usr/bin/env python3
"""Project-owned FS2 v1 wrapper for a real, prebuilt Hardcaml Cyclesim counter.

Only stdout from the tiny hardware checker is translated; the Workbench never
infers outcomes from logs. No builds, shell, ASIC dependencies, or background jobs.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
# Share the strict portable codec with deterministic acceptance fixtures.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts' / 'fixtures'))
from fs2_wire import EventWriter, parse, record, sexp, catalog


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--counter', required=True, type=Path)
    p.add_argument('--calls', type=Path, help='optional append-only invocation evidence')
    p.add_argument('operation', choices=['discover', 'run'])
    p.add_argument('--protocol-version', required=True, type=int, choices=[1])
    p.add_argument('--request', type=Path)
    p.add_argument('--events', type=Path)
    p.add_argument('--artifact-dir', type=Path)
    a = p.parse_args()
    if a.calls:
        with a.calls.open('a') as out:
            out.write(json.dumps(dict(operation=a.operation, provider='real-cyclesim',
                request=parse(a.request.read_text()) if a.request else None)) + '\n')
    if a.operation == 'discover':
        print(sexp(catalog('counter', ['wrap', 'reset', 'seeded'], [
            ('cycles', '64', []), ('step', '1', ['1', '3', '7']),
            ('inject_failure', 'false', ['false', 'true'])])))
        return
    request = record(parse(a.request.read_text()))
    assert request['protocol_version'] == '1'
    selection = record(request['selection'])
    assert selection['suite'] == 'counter' and not selection['asic_inputs']
    params = record(selection['parameters'])
    # Decimal -> bit pattern accepts the whole protocol uint64 domain.
    seed = int(selection['seed'])
    assert 0 <= seed < 2**64
    signed_seed = seed if seed < 2**63 else seed - 2**64
    events = EventWriter(a.events, request['attempt_id'])
    events.emit('Started')
    failed = False
    for case in selection['cases']:
        assert case in ('wrap', 'reset', 'seeded')
        events.emit(['Case_started', case])
        trace = a.artifact_dir / (case + '.vcd')
        argv = [str(a.counter), case, str(signed_seed), params['cycles'],
                params['step'], str(trace), params['inject_failure']]
        report = []
        outcome = None
        with subprocess.Popen(argv, stdout=subprocess.PIPE, text=True) as child:
            for line in child.stdout:
                print(case + ': ' + line, end='', flush=True)
                report.append(line)
                if line.startswith('PROGRESS '):
                    _, completed, total = line.split()
                    events.progress(case, int(completed), int(total))
                if line.startswith('RESULT '):
                    assert outcome is None
                    outcome = line.split()[1]
            code = child.wait()
        if code != 0 or outcome not in ('Passed', 'Failed'):
            raise RuntimeError('Cyclesim checker exited without valid result: ' + str(code))
        events.artifact(case + '-vcd', case, 'waveform', 'application/vnd.gtkwave.vcd', trace.name)
        report_path = a.artifact_dir / (case + '-report.txt')
        report_path.write_text('seed=' + selection['seed'] + '\nparameters=' + json.dumps(params, sort_keys=True) + '\n' + ''.join(report))
        events.artifact(case + '-report', case, 'failure-report' if outcome == 'Failed' else 'report', 'text/plain', report_path.name)
        failed |= outcome == 'Failed'
        events.finish_case(case, outcome, 'Counter reference-model mismatch; see report' if outcome == 'Failed' else None)
    events.emit(['Finished', 'Failed' if failed else 'Passed'])


if __name__ == '__main__':
    main()
