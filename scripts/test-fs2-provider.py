#!/usr/bin/env python3
"""Real standalone Cyclesim proof. Requires prebuilt --counter; never builds."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / 'fixtures'))
from fs2_wire import parse, record, sexp


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--counter', type=Path, default=Path('/tmp/opencode/fs2-build-provider/default/counter.exe'))
    a = p.parse_args()
    a.counter = a.counter.resolve(strict=True)
    os.umask(0o077)
    evidence = Path(tempfile.mkdtemp(prefix='fs2-provider-', dir='/tmp/opencode'))
    provider = Path(__file__).resolve().parents[1] / 'examples/fs2_cyclesim/provider.py'
    command = [sys.executable, str(provider), '--counter', str(a.counter)]
    discovery = subprocess.check_output(command + ['discover', '--protocol-version', '1'], timeout=10)
    (evidence / 'discovery.sexp').write_bytes(discovery)
    assert record(parse(discovery.decode()))['protocol_version'] == '1'
    results = []
    for name, seed, step, inject in [('directed', '42', '1', 'false'),
                                    ('uint64', '18446744073709551615', '7', 'false'),
                                    ('repeat', '18446744073709551615', '7', 'false'),
                                    ('failure', '42', '3', 'true')]:
        run = evidence / name
        run.mkdir()
        artifacts = run / 'artifacts'; artifacts.mkdir()
        request = [('protocol_version', 1), ('attempt_id', name), ('selection', [
            ('suite', 'counter'), ('cases', ['wrap', 'reset', 'seeded']), ('seed', seed),
            ('parameters', [('cycles', '64'), ('step', step), ('inject_failure', inject)]), ('asic_inputs', [])])]
        (run / 'request.sexp').write_text(sexp(request))
        events = run / 'events.sexp'
        proc = subprocess.run(command + ['run', '--protocol-version', '1', '--request', str(run / 'request.sexp'),
                              '--events', str(events), '--artifact-dir', str(artifacts)], capture_output=True, timeout=20)
        (run / 'stdout').write_bytes(proc.stdout); (run / 'stderr').write_bytes(proc.stderr)
        assert proc.returncode == 0, proc.stderr.decode()
        stream = [record(parse(line)) for line in events.read_text().splitlines()]
        assert [int(e['sequence']) for e in stream] == list(range(len(stream)))
        expected = 'Failed' if inject == 'true' else 'Passed'
        assert stream[-1]['payload'] == ['Finished', expected]
        cases = [record(e['payload'][1]) for e in stream if e['payload'][0] == 'Case_finished']
        assert len(cases) == 3 and all(c['status'] == expected for c in cases)
        for vcd in artifacts.glob('*.vcd'):
            raw = vcd.read_bytes()
            assert b'$enddefinitions' in raw and b'count' in raw and b'#' in raw and len(raw) > 1000
            # Hardcaml's VCD header contains wall-clock date; compare signal body.
            if name == 'repeat':
                old = (evidence / 'uint64/artifacts' / vcd.name).read_bytes()
                assert raw.split(b'$enddefinitions', 1)[1] == old.split(b'$enddefinitions', 1)[1]
        results.append(dict(name=name, outcome=expected, events=len(stream),
                            artifacts={f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in artifacts.iterdir()}))
    (evidence / 'result.json').write_text(json.dumps(dict(status='passed', runs=results), indent=2))
    print('PASS real Cyclesim reference checks, uint64 seed, deterministic replay, injected assertions and actual VCD: ' + str(evidence))


if __name__ == '__main__':
    main()
