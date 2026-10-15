#!/usr/bin/env python3
"""Run external acceptance for an exact completed FS1 physical execution.

Parent-run only: no builds, installs, Git, implementation reruns or active config
writes. All output goes into a new /tmp/opencode evidence namespace. Nix uses
the cached pinned source with URI access/builds/substitution disabled.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time


EXAMPLE = Path('/home/wayne/devel/jane/hardcaml_asic_example')
TOOLS = EXAMPLE / '_flow_tools'
THREAD_ENV = {key: '20' for key in (
    'OMP_NUM_THREADS', 'OMP_THREAD_LIMIT', 'OPENBLAS_NUM_THREADS',
    'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'RAYON_NUM_THREADS',
    'NUM_CORES', 'NPROC', 'OPENROAD_THREADS', '_OPENLANE_MAX_CORES', 'NIX_BUILD_CORES',
)}
cancelled = None


def on_signal(number, _frame):
    global cancelled
    if cancelled is None:
        cancelled = number


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    with path.open() as source:
        return json.load(source)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    os.replace(temporary, path)


def cached_nixpkgs(default_nix):
    # Read only the cache's tarball entry, not its downloaded archive-file entry.
    # Never invoke fetchTarball just to find out whether its source is cached.
    urls = re.findall(r'fetchTarball\s+"([^"]+)"', default_nix.read_text())
    require(len(urls) == 1 and re.fullmatch(
        r'https://github\.com/NixOS/nixpkgs/archive/[0-9a-f]{40}\.tar\.gz', urls[0]),
        'precheck must declare exactly one commit-pinned nixpkgs tarball')
    cache_home = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache')))
    cache = cache_home / 'nix/fetcher-cache-v1.sqlite'
    require(cache.is_file(), 'missing Nix fetcher cache; no download attempted: ' + str(cache))
    connection = sqlite3.connect(cache.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        rows = connection.execute('SELECT input, path FROM Cache').fetchall()
    finally:
        connection.close()
    paths = set()
    for raw, path in rows:
        entry = json.loads(raw)
        if entry.get('type') == 'tarball' and entry.get('url') == urls[0]:
            candidate = Path(path)
            if re.fullmatch(r'/nix/store/[0-9a-z]{32}-[0-9A-Za-z+._?=-]+', path) \
                    and (candidate / 'default.nix').is_file():
                paths.add(path)
    require(len(paths) == 1, 'no unique retained nixpkgs source for ' + urls[0]
            + '; no fetch/build attempted')
    return {'url': urls[0], 'source': paths.pop(), 'cache': str(cache), 'cache_access': 'read_only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--physical-evidence', type=Path, required=True)
    parser.add_argument('--trace-exporter', type=Path, required=True,
                        help='already built acceptance/export_trace.exe; never built by this harness')
    parser.add_argument('--timeout', type=int, default=900,
                        help='shared deadline in seconds, 120..900, plus owned-process cleanup')
    args = parser.parse_args()
    if not args.physical_evidence.is_absolute() or not args.trace_exporter.is_absolute():
        parser.error('both input paths must be absolute')
    if not 120 <= args.timeout <= 900:
        parser.error('--timeout must be 120..900 seconds')
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, on_signal)

    root = Path(tempfile.mkdtemp(prefix='workbench-fs1-acceptance-', dir='/tmp/opencode'))
    print(root, flush=True)
    deadline = time.monotonic() + args.timeout
    environment = dict(os.environ, **THREAD_ENV)
    affinity = sorted(os.sched_getaffinity(0))[:20] if hasattr(os, 'sched_getaffinity') else None
    summary = {
        'contract': 'workbench.fs1-acceptance-evidence', 'schema_version': 1,
        'started_at': now(), 'evidence': str(root), 'status': 'running',
        'physical_evidence': str(args.physical_evidence),
        'trace_exporter': str(args.trace_exporter), 'acceptance_requested': True,
        'acceptance': None, 'external_postcheck': None, 'operation_status': None,
        'timeout_seconds': args.timeout, 'cleanup_grace_seconds': 60,
        'thread_environment': THREAD_ENV, 'child_cpu_affinity': affinity, 'commands': [],
    }

    def persist():
        save(root / 'summary.json', summary)

    def child_limits():
        if affinity is not None:
            os.sched_setaffinity(0, affinity)

    def run(name, argv, budget):
        require(cancelled is None, 'harness cancellation requested')
        budget = min(budget, deadline - time.monotonic())
        require(budget > 0, 'shared deadline exhausted before ' + name)
        record = {
            'name': name, 'argv': [str(v) for v in argv], 'cwd': str(EXAMPLE),
            'started_at': now(), 'timeout_seconds': budget,
            'stdout': str(root / (name + '.stdout')), 'stderr': str(root / (name + '.stderr')),
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
                        record['termination_reason'] = 'signal' if cancelled is not None else 'deadline'
                        record['signal_received'] = cancelled
                        try:
                            os.killpg(process.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        try:
                            process.wait(timeout=60)
                        except subprocess.TimeoutExpired:
                            record['forced_kill'] = True
                            try:
                                os.killpg(process.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            process.wait(timeout=10)
                        break
                    try:
                        process.wait(timeout=0.25)
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                record.update(exit_code=process.poll(), ended_at=now(),
                              duration_seconds=time.monotonic() - started)
                persist()
        return record

    persist()
    code = 1
    try:
        inputs_path = args.physical_evidence / 'workbench-inputs.json'
        inputs = load(inputs_path)
        physical_summary = load(args.physical_evidence / 'summary.json')
        require(physical_summary.get('status') == 'completed', 'physical harness did not complete')
        execution = Path(inputs['execution_file'])
        require(execution.is_absolute(), 'execution reference must be absolute')
        execution_hash = sha256(execution)
        record = load(execution)
        require(record.get('status') == 'completed' and record.get('exit_code') == 0
                and record.get('attempt_id') == inputs['allocation']['stream_id'],
                'selected execution did not complete or stream identity differs')
        original_operation = load(Path(inputs['operation']))
        require(original_operation.get('execution', {}).get('sha256') == execution_hash
                and original_operation['execution'].get('path') == str(execution.resolve()),
                'physical collection execution reference mismatch')
        original_results = Path(inputs['results']['path'])
        require(sha256(original_results) == inputs['results']['sha256'], 'physical results hash mismatch')
        provider = Path(physical_summary['provider'])
        python = TOOLS / '.venv-precheck/bin/python'
        bench = EXAMPLE / 'acceptance/replay.v'
        nix = shutil.which('nix-shell')
        docker = original_operation.get('binding', {}).get('engine_identity', {}).get('executable')
        missing = []
        for executable in (provider, args.trace_exporter, python, Path(docker) if docker else None):
            if executable is None or not executable.is_file() or not os.access(executable, os.X_OK):
                missing.append(str(executable) if executable is not None else 'bound Docker executable')
        for path in (
            bench, TOOLS / 'tt/precheck/default.nix', TOOLS / 'tt/precheck/tool-versions.json',
            TOOLS / 'tt/precheck/precheck.py', TOOLS / 'tt/tech',
            TOOLS / 'pdk/ihp-sg13cmos5l/libs.ref/sg13cmos5l_io/verilog/sg13cmos5l_io.v',
            TOOLS / 'pdk/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/verilog/sg13cmos5l_udp.v',
            TOOLS / 'pdk/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/verilog/sg13cmos5l_stdcell.v',
        ):
            if not path.exists():
                missing.append(str(path))
        if nix is None:
            missing.append('nix-shell on PATH')
        summary.update(execution_file=str(execution), execution_sha256=execution_hash,
                       provider=str(provider), missing_collateral=missing)
        persist()
        require(not missing, 'missing external collateral; no installation attempted: ' + ', '.join(missing))
        summary['input_sha256'] = {str(p): sha256(p) for p in (inputs_path, provider, args.trace_exporter, bench)}

        # The provider owns precheck orchestration. Limit its nix-shell invocations
        # to already cached dependencies without modifying provider or TT files.
        pinned = cached_nixpkgs(TOOLS / 'tt/precheck/default.nix')
        summary['cached_nixpkgs'] = pinned
        persist()
        require(not any(c.isspace() for c in sys.executable), 'Python shebang path contains whitespace')
        binaries = root / 'bin'
        binaries.mkdir()
        # Preserve argv[0]'s nix-shell spelling (Nix installations may use a
        # multicall symlink); disable remote builders as well as local builds.
        # Legacy nix-shell 2.18.1 has no --offline flag. Override the default
        # fetchTarball argument using the cache entry for that exact URL, then
        # deny URI access and import-from-derivation during actual evaluation.
        # The real default.nix, mkShell and provider version checks still run.
        nix_prefix = [os.path.abspath(nix), '--option', 'max-jobs', '0',
                      '--option', 'builders', '', '--option', 'substitute', 'false',
                      '--option', 'substituters', '', '--option', 'restrict-eval', 'true',
                      '--option', 'allowed-uris', '',
                      '--option', 'allow-import-from-derivation', 'false',
                      '-I', 'nixpkgs=' + pinned['source'],
                      '--arg', 'pkgs', 'import ' + pinned['source'] + ' {}']
        wrapper = binaries / 'nix-shell'
        wrapper.write_text('#!' + sys.executable + '\nimport os,sys\n'
                           + 'os.environ["NIX_PATH"] = ' + repr('nixpkgs=' + pinned['source']) + '\n'
                           + 'argv = ' + repr(nix_prefix)
                           + ' + ["-I", "precheck=" + os.getcwd()] + sys.argv[1:]\n'
                           + 'os.execv(argv[0], argv)\n')
        wrapper.chmod(0o700)
        environment['PATH'] = str(binaries) + os.pathsep + environment.get('PATH', '')
        summary['nix_shell_prefix'] = nix_prefix
        summary['nix_shell_wrapper_sha256'] = sha256(wrapper)
        persist()

        exported = run('trace-export', [args.trace_exporter], 30)
        trace = Path(exported['stdout'])
        require(exported['exit_code'] == 0 and not exported.get('termination_reason') and trace.stat().st_size > 0,
                'trace exporter failed or produced no trace')
        summary['trace'] = {'path': str(trace), 'sha256': sha256(trace), 'bytes': trace.stat().st_size}
        persist()
        finalization = run('finalization', [
            provider, 'finalize', execution, '--operation-store', root / 'operations',
            '--accept', '--support-tools', TOOLS / 'tt', '--precheck-python', python,
            '--testbench', bench, '--testbench-top', 'replay', '--replay-trace', trace, '--json',
        ], deadline - time.monotonic() - 100)

        messages, delivery_errors = [], []
        with open(finalization['stdout']) as source:
            for number, line in enumerate(source, 1):
                if line.strip():
                    try:
                        message = json.loads(line)
                        require(isinstance(message, dict), 'JSONL message must be an object')
                        messages.append(message)
                    except (ValueError, TypeError) as exc:
                        delivery_errors.append({'line': number, 'error': str(exc)})
        summary['delivery_errors'] = delivery_errors
        allocated = [r for r in messages if r.get('event') == 'allocated']
        require(len(allocated) == 1, 'no unique returned finalization allocation; see logs')
        allocation = allocated[0]
        require(allocation.get('contract') == 'hardcaml-asic.segment-finalization'
                and allocation.get('schema_version') == 1, 'unexpected allocation contract')
        attempt = Path(allocation['attempt'])
        require(attempt.is_absolute(), 'operation attempt must be absolute')
        summary['allocation'] = allocation
        summary['operation_attempt'] = str(attempt)
        persist()
        inspected = run('finalization-inspect', [provider, 'finalization-inspect', attempt, '--json'], 30)
        require(inspected['exit_code'] == 0 and not inspected.get('termination_reason'), 'operation inspection failed')
        operation = load(Path(inspected['stdout']))
        save(root / 'operation.json', operation)
        # Record outcomes before evaluating them: rejection and tool failure remain
        # independent of whether receipt/results retrieval succeeded.
        summary.update(operation_status=operation.get('status'), acceptance=operation.get('acceptance'),
                       external_postcheck=operation.get('external_postcheck'),
                       operation_error=operation.get('error'), operation_exit_code=operation.get('exit_code'))
        persist()
        require(operation.get('attempt_id') == allocation.get('attempt_id'), 'operation identity mismatch')
        selected = operation.get('execution', {})
        require(selected.get('path') == str(execution.resolve()) and selected.get('sha256') == execution_hash
                and selected.get('attempt_id') == inputs['allocation']['stream_id'], 'selected execution mismatch')
        require(operation.get('request', {}).get('accept') is True, 'acceptance request mismatch')
        for name in ('results', 'acceptance_report'):
            reference = operation.get(name)
            if reference is not None:
                path = Path(reference['path'])
                require(path.is_absolute() and sha256(path) == reference['sha256'], name + ' hash mismatch')
                summary[name] = dict(reference, sha256_verified=True)
                if name == 'results':
                    save(root / 'normalized-results.json', load(path))
        if operation.get('postcheck_record'):
            path = Path(operation['postcheck_record'])
            require(path.is_absolute() and sha256(path) == operation['postcheck_sha256'], 'postcheck hash mismatch')
            postcheck = load(path)
            save(root / 'postcheck.json', postcheck)
            summary['postcheck_checks'] = postcheck.get('checks')
        save(root / 'workbench-inputs.json', {
            'physical_evidence': str(args.physical_evidence), 'execution_file': str(execution),
            'allocation': inputs['allocation'], 'plan_identity': inputs.get('plan_identity'),
            'stage_report': inputs['stage_report'], 'operation_attempt': str(attempt),
            'operation': str(root / 'operation.json'), 'results': operation.get('results'),
            'operation_status': operation.get('status'), 'acceptance': operation.get('acceptance'),
            'external_postcheck': operation.get('external_postcheck'),
        })
        summary['evidence_recorded'] = True
        passed = (finalization['exit_code'] == 0 and not finalization.get('termination_reason')
                  and not delivery_errors and operation.get('status') == 'completed'
                  and operation.get('exit_code') == 0 and operation.get('acceptance') == 'pass'
                  and operation.get('external_postcheck') == 'completed' and operation.get('results') is not None)
        summary['status'] = 'completed' if passed else 'failed'
        code = 0 if passed else 1
    except Exception as exc:
        summary['status'] = 'interrupted' if cancelled is not None else 'failed'
        summary['error'] = {'type': type(exc).__name__, 'detail': str(exc)}
        code = 128 + cancelled if cancelled is not None else 1
        print(str(exc), file=sys.stderr, flush=True)
    finally:
        summary.update(ended_at=now(), exit_code=code)
        persist()
        print('Summary: ' + str(root / 'summary.json'), flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
