#!/usr/bin/env python3
"""Parent-run, bounded physical specimen using the already adopted executable pair.

No builds, installs, Git operations, acceptance runs, or active config writes.
The printed evidence directory contains logs, exact public references and summary.json.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


EXAMPLE = Path('/home/wayne/devel/jane/hardcaml_asic_example')
PROJECT = EXAMPLE / '_build_namedflow_real/default/bin/project.exe'
PROVIDER = Path('/tmp/opencode/namedflow-real-20261015/provider/bin/hardcaml-asic-flow')
TOOLS = EXAMPLE / '_flow_tools'
THREAD_ENV = {
    key: '20' for key in (
        'OMP_NUM_THREADS', 'OMP_THREAD_LIMIT', 'OPENBLAS_NUM_THREADS',
        'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'RAYON_NUM_THREADS',
        'NUM_CORES', 'NPROC', 'OPENROAD_THREADS', '_OPENLANE_MAX_CORES',
    )
}
cancelled = None


def on_signal(number, _frame):
    global cancelled
    if cancelled is None:
        cancelled = number


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, value):
    # All destinations are inside this invocation's freshly allocated namespace.
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    os.replace(temporary, path)


def load(path):
    with path.open() as source:
        return json.load(source)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=PROJECT,
                        help='absolute prebuilt project executable (default: adopted pair)')
    parser.add_argument('--provider', type=Path, default=PROVIDER,
                        help='absolute installed provider executable (default: adopted pair)')
    parser.add_argument('--stage-timeout', type=int,
                        help='positive per-segment/publication seconds; needs a project supporting --timeout')
    parser.add_argument('--timeout', type=int, default=3600,
                        help='outer physical subprocess budget, 61..3600 seconds')
    parser.add_argument('--finalization-timeout', type=int, default=1800,
                        help='outer collection budget, 1..1800 seconds')
    args = parser.parse_args()
    if not 61 <= args.timeout <= 3600 or not 1 <= args.finalization_timeout <= 1800:
        parser.error('timeout must be 61..3600; finalization-timeout must be 1..1800')
    if not args.project.is_absolute() or not args.provider.is_absolute():
        parser.error('--project and --provider must be absolute paths')
    if args.stage_timeout is not None and not 1 <= args.stage_timeout < args.timeout - 60:
        parser.error('--stage-timeout must be positive and less than the client budget (--timeout minus 60)')
    project, provider = args.project, args.provider

    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, on_signal)
    root = Path(tempfile.mkdtemp(prefix='workbench-fs1-physical-', dir='/tmp/opencode'))
    print(root, flush=True)
    summary = {
        'contract': 'workbench.fs1-physical-evidence', 'schema_version': 1,
        'started_at': now(), 'evidence': str(root), 'status': 'running',
        'project': str(project), 'provider': str(provider),
        'stage_timeout_seconds': args.stage_timeout,
        'acceptance': 'not_evaluated', 'commands': [],
        'thread_environment': THREAD_ENV, 'cleanup_grace_seconds': 60,
        'physical_receipt': str(root / 'physical.json'),
    }
    environment = dict(os.environ, **THREAD_ENV)
    affinity = sorted(os.sched_getaffinity(0))[:20] if hasattr(os, 'sched_getaffinity') else None
    summary['child_cpu_affinity'] = affinity

    def persist():
        save(root / 'summary.json', summary)

    def child_limits():
        if affinity is not None:
            os.sched_setaffinity(0, affinity)

    def run(name, argv, budget):
        if cancelled is not None:
            raise InterruptedError('harness cancellation requested')
        record = {
            'name': name, 'argv': [str(v) for v in argv], 'cwd': str(EXAMPLE),
            'started_at': now(), 'timeout_seconds': budget,
            'stdout': str(root / (name + '.stdout')),
            'stderr': str(root / (name + '.stderr')),
        }
        summary['commands'].append(record)
        persist()
        started = time.monotonic()
        with open(record['stdout'], 'xb') as out, open(record['stderr'], 'xb') as err:
            process = subprocess.Popen(
                record['argv'], cwd=EXAMPLE, env=environment, stdin=subprocess.DEVNULL,
                stdout=out, stderr=err, start_new_session=True,
                preexec_fn=child_limits if affinity is not None else None,
            )
            record['pid'] = process.pid
            persist()
            try:
                while process.poll() is None:
                    if cancelled is not None or time.monotonic() - started >= budget:
                        record['termination_reason'] = ('signal' if cancelled is not None else 'deadline')
                        record['signal_received'] = cancelled
                        # Only the new session/process group allocated by this call.
                        try:
                            os.killpg(process.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        try:
                            process.wait(timeout=60)  # exceeds provider cleanup's 30-second allowance
                        except subprocess.TimeoutExpired:
                            record['forced_kill'] = True
                            try:
                                os.killpg(process.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            process.wait(timeout=10)
                        break
                    try:
                        process.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                record['exit_code'] = process.poll()
                record['duration_seconds'] = time.monotonic() - started
                record['ended_at'] = now()
                persist()
        return record

    persist()
    code = 1
    try:
        for executable in (project, provider, TOOLS / '.venv/bin/python'):
            require(executable.is_file() and os.access(executable, os.X_OK),
                    'missing adopted executable: ' + str(executable))
        summary['executable_sha256'] = {str(p): sha256(p) for p in (project, provider)}
        receipt_path = root / 'physical.json'
        physical = run('physical', [
            sys.executable, '-B', EXAMPLE / 'scripts/headless_flow.py',
            '--project', project, '--provider', provider, '--source-root', EXAMPLE,
            '--results-root', root / 'results', '--toolchain', TOOLS,
            '--python', TOOLS / '.venv/bin/python', '--support-tools', TOOLS / 'tt',
            '--pdk-root', TOOLS / 'pdk', '--flow', 'standard', '--profile', 'balanced',
            '--endpoint', 'signoff', '--poll', '1',
            # Leave time for the client's own cancellation/receipt publication.
            # Omission preserves the adopted pair's behavior. Opt-in forwarding
            # requires a newly linked project with public flow run --timeout.
            '--timeout', str(args.timeout - 60), '--receipt', receipt_path,
        ] + (['--stage-timeout', str(args.stage_timeout)]
             if args.stage_timeout is not None else []), args.timeout)
        require(receipt_path.is_file(), 'headless client returned no receipt; see physical.stderr')
        receipt = load(receipt_path)
        summary['allocation'] = receipt.get('allocation')
        summary['execution_file'] = receipt.get('execution_file')
        persist()
        require(cancelled is None, 'harness cancelled')
        require(physical['exit_code'] == 0 and not physical.get('termination_reason'),
                'physical client failed or exceeded deadline; exact receipt/logs retained')
        require(receipt.get('execution_completed') is True, 'execution did not complete')
        execution = receipt.get('execution_file')
        require(isinstance(execution, str) and Path(execution).is_absolute(),
                'missing exact absolute execution reference')
        report = receipt.get('report', {})
        require(report.get('completion', {}).get('physical') == 'full',
                'public stage report did not establish full physical completion')
        save(root / 'stage-report.json', report)
        expected_execution_hash = sha256(Path(execution))
        summary['execution_sha256'] = expected_execution_hash
        persist()

        finalization = run('finalization', [
            provider, 'finalize', execution, '--operation-store', root / 'operations', '--json',
        ], args.finalization_timeout)
        # Read allocation independently of exit status; no newest-directory guessing.
        messages = []
        delivery_errors = []
        with open(finalization['stdout']) as source:
            for line_number, line in enumerate(source, 1):
                if line.strip():
                    try:
                        message = json.loads(line)
                        require(isinstance(message, dict), 'JSONL message must be an object')
                        messages.append(message)
                    except (ValueError, TypeError) as exc:
                        delivery_errors.append({'line': line_number, 'error': str(exc)})
        summary['finalization_delivery_errors'] = delivery_errors
        persist()
        allocated = [r for r in messages if r.get('event') == 'allocated']
        require(len(allocated) == 1, 'finalization did not return one exact allocation')
        allocation = allocated[0]
        require(allocation.get('contract') == 'hardcaml-asic.segment-finalization'
                and allocation.get('schema_version') == 1, 'unexpected allocation contract')
        attempt = allocation['attempt']
        require(isinstance(attempt, str) and Path(attempt).is_absolute(), 'invalid operation reference')
        summary['finalization_allocation'] = allocation
        summary['finalization_attempt'] = attempt
        persist()
        inspected = run('finalization-inspect', [
            provider, 'finalization-inspect', attempt, '--json',
        ], 60)
        require(inspected['exit_code'] == 0 and not inspected.get('termination_reason'),
                'finalization inspection failed')
        operation = load(Path(inspected['stdout']))
        save(root / 'operation.json', operation)
        require(operation.get('attempt_id') == allocation.get('attempt_id'), 'operation identity mismatch')
        require(operation.get('execution', {}).get('path') == str(Path(execution).resolve())
                and operation['execution'].get('sha256') == expected_execution_hash
                and operation['execution'].get('attempt_id') == receipt['allocation']['stream_id'],
                'finalization execution reference mismatch')
        summary['acceptance'] = operation.get('acceptance')
        summary['external_postcheck'] = operation.get('external_postcheck')
        result_ref = operation.get('results')
        if result_ref is not None:
            result_path = Path(result_ref['path'])
            require(result_path.is_absolute(), 'results reference must be absolute')
            actual_hash = sha256(result_path)
            require(actual_hash == result_ref['sha256'], 'results SHA-256 mismatch')
            results = load(result_path)
            summary['results'] = dict(result_ref, sha256_verified=True)
            save(root / 'normalized-results.json', results)
            save(root / 'workbench-inputs.json', {
                'execution_file': execution, 'allocation': receipt['allocation'],
                'physical_receipt': str(receipt_path),
                'plan_identity': receipt.get('plan_identity'),
                'stage_report': str(root / 'stage-report.json'),
                'operation_attempt': attempt, 'operation': str(root / 'operation.json'),
                'results': result_ref, 'acceptance': operation.get('acceptance'),
                'external_postcheck': operation.get('external_postcheck'),
            })
        require(finalization['exit_code'] == 0 and not finalization.get('termination_reason')
                and operation.get('status') == 'completed' and operation.get('exit_code') == 0,
                'finalization failed, interrupted or exceeded deadline')
        require(not delivery_errors, 'finalization JSONL delivery was malformed; receipt inspection retained')
        require(result_ref is not None, 'completed finalization has no results')
        require(operation.get('acceptance') == 'not_evaluated'
                and operation.get('external_postcheck') == 'not_evaluated',
                'unexpected acceptance/postcheck state for collection-only operation')
        summary['status'] = 'completed'
        code = 0
    except Exception as exc:
        summary['status'] = 'interrupted' if cancelled is not None else 'failed'
        summary['error'] = {'type': type(exc).__name__, 'detail': str(exc)}
        code = 128 + cancelled if cancelled is not None else 1
        print(str(exc), file=sys.stderr, flush=True)
    finally:
        summary['ended_at'] = now()
        summary['exit_code'] = code
        persist()
        print('Summary: ' + str(root / 'summary.json'), flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
